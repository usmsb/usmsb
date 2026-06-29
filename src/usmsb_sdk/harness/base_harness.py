"""USMSB BaseHarness（支柱①：个体=经济公民）。

借鉴 opc-platform/peas/pea_core/harness.py 的"一切皆 LLM"循环：
    perceive → think(LLM) → act(tools) → observe → 迭代
并增加 USMSB 核心增量 —— **guard 阶段**：

    受约束 Loop Engineering：LLM 管判断/规划，代码管安全/幂等/副作用/钱包限额。

LLM 决定"做什么"；guard（纯代码）决定"允不允许、要不要人工闸门"。
子类只实现少量接线钩子，核心循环只此一份、无业务 if-else。
"""

from __future__ import annotations

import abc
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

WINDOW = 12       # 近窗口保留消息数
MAX_STEPS = 12    # 单轮 harness 最多工具步数


@runtime_checkable
class ChatProvider(Protocol):
    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str: ...


@dataclass
class TurnResult:
    reply: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    blocked: list[dict[str, Any]] = field(default_factory=list)  # 被 guard 拦下的动作
    requires_human: bool = False
    state: dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardDecision:
    allowed: bool
    reason: str = ""
    requires_human: bool = False


def parse_action(raw: str) -> dict[str, Any]:
    """把 LLM 文本解析为结构化动作。无法解析时降级为 say。"""
    s = (raw or "").strip()
    if s.startswith("```"):
        s = s.strip("`")
        s = s[4:] if s.startswith("json") else s
    st, en = s.find("{"), s.rfind("}")
    if st >= 0 and en > st:
        try:
            obj = json.loads(s[st:en + 1])
            if isinstance(obj, dict) and obj.get("action") in ("say", "tool", "request_human", "settle"):
                return obj
        except json.JSONDecodeError:
            pass
    return {"action": "say", "text": s or "我在的，您说。"}


class BaseHarness(abc.ABC):
    """经济公民的通用 harness。子类提供 system_prompt + 钩子，其余由本类完成。

    动作协议（LLM 输出 JSON）：
        {"action": "say", "text": "..."}
        {"action": "tool", "name": "...", "args": {...}}        # args 可带 vibe_cost
        {"action": "request_human", "reason": "..."}             # 主动进人工闸门
        {"action": "settle", "amount": 100, "payee": "0x..."}    # VIBE 结算
    """

    # ── 接线钩子（子类实现）─────────────────────────────────────────────
    @property
    @abc.abstractmethod
    def system_prompt(self) -> str: ...

    @property
    @abc.abstractmethod
    def chat(self) -> ChatProvider: ...

    @abc.abstractmethod
    async def load_history(self, conv: Any) -> list[dict[str, str]]:
        """返回 [{role, content}]，按时间升序。"""

    @abc.abstractmethod
    async def save_message(self, conv: Any, role: str, content: str) -> None: ...

    @abc.abstractmethod
    async def compute_state(self, conv: Any) -> dict[str, Any]:
        """返回注入每轮上下文的经济 STATE：
        {wallet:{available,daily_remaining}, policy:{max_per_tx,blocked_actions},
         reputation, principal, ...}
        """

    @abc.abstractmethod
    def known_tool(self, name: str) -> bool: ...

    @abc.abstractmethod
    def tool_is_side_effect(self, name: str) -> bool:
        """该工具是否有外部副作用（写库/发布/花钱）。只读工具返回 False。"""

    @abc.abstractmethod
    async def dispatch(self, conv: Any, name: str, args: dict[str, Any]) -> dict[str, Any]: ...

    # ── 可选钩子（有默认实现）───────────────────────────────────────────
    def estimate_cost(self, name: str, args: dict[str, Any]) -> float:
        """该工具调用要花多少 VIBE（默认读 args.vibe_cost）。"""
        try:
            return float(args.get("vibe_cost", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    async def can_spend(self, amount: float, state: dict[str, Any]) -> GuardDecision:
        """钱包/限额检查（默认基于 STATE 里的 wallet/policy）。子类可覆盖接真实钱包。"""
        if amount <= 0:
            return GuardDecision(True)
        wallet = state.get("wallet") or {}
        policy = state.get("policy") or {}
        available = float(wallet.get("available", 0) or 0)
        daily_remaining = float(wallet.get("daily_remaining", available) or available)
        max_per_tx = float(policy.get("max_per_tx", float("inf")) or float("inf"))
        if amount > available:
            return GuardDecision(False, f"余额不足（需 {amount}，可用 {available}）", requires_human=True)
        if amount > max_per_tx:
            return GuardDecision(False, f"超单笔限额（{amount} > {max_per_tx}）", requires_human=True)
        if amount > daily_remaining:
            return GuardDecision(False, f"超当日限额（剩 {daily_remaining}）", requires_human=True)
        return GuardDecision(True)

    async def settle(self, conv: Any, amount: float, payee: str, state: dict[str, Any]) -> dict[str, Any]:
        """执行 VIBE 结算。默认不支持（子类接钱包/EscrowSettlement 后覆盖）。"""
        return {"settled": False, "reason": "settlement not wired"}

    # ── guard：纯代码安全闸门（USMSB 核心增量）──────────────────────────
    async def _guard_tool(self, name: str, args: dict[str, Any], state: dict[str, Any]) -> GuardDecision:
        if not self.known_tool(name):
            return GuardDecision(False, f"未知工具：{name}")
        if self.tool_is_side_effect(name):
            blocked = set((state.get("policy") or {}).get("blocked_actions") or [])
            if name in blocked:
                return GuardDecision(False, f"主人规则禁止：{name}", requires_human=True)
            cost = self.estimate_cost(name, args)
            if cost > 0:
                return await self.can_spend(cost, state)
        return GuardDecision(True)

    # ── 核心循环（共享）──────────────────────────────────────────────────
    def _assemble(self, system: str, history: list[dict[str, str]], state: dict[str, Any]) -> list[dict[str, str]]:
        recent = history[-WINDOW:] if len(history) > WINDOW else history
        msgs: list[dict[str, str]] = [{"role": "system", "content": system}]
        msgs.extend(recent)
        msgs.append({"role": "system", "content": "STATE:" + json.dumps(state, ensure_ascii=False)})
        return msgs

    async def run_turn(self, conv: Any, user_text: str) -> TurnResult:
        await self.save_message(conv, "user", user_text)
        steps: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        reply = ""
        requires_human = False

        for _ in range(MAX_STEPS):
            state = await self.compute_state(conv)
            history = await self.load_history(conv)
            msgs = self._assemble(self.system_prompt, history, state)
            raw = await self.chat.complete(msgs)
            action = parse_action(raw)
            kind = action.get("action")

            if kind == "say":
                reply = str(action.get("text", "")).strip()
                await self.save_message(conv, "assistant", reply)
                break

            if kind == "request_human":
                requires_human = True
                reply = str(action.get("reason") or "需要主人确认后再继续。")
                await self.save_message(conv, "assistant", f"[人工闸门] {reply}")
                break

            if kind == "settle":
                amount = self._to_float(action.get("amount"))
                guard = await self.can_spend(amount, state)
                if not guard.allowed:
                    blocked.append({"action": "settle", "amount": amount, "reason": guard.reason})
                    requires_human = requires_human or guard.requires_human
                    await self.save_message(conv, "system", f"[guard] 结算被拦：{guard.reason}")
                    continue
                res = await self.settle(conv, amount, str(action.get("payee", "")), state)
                steps.append({"settle": amount, "result": res})
                await self.save_message(conv, "system", f"[settle] {json.dumps(res, ensure_ascii=False)[:200]}")
                continue

            # kind == "tool"
            name = str(action.get("name", ""))
            args = action.get("args") or {}
            guard = await self._guard_tool(name, args, state)
            if not guard.allowed:
                blocked.append({"action": "tool", "name": name, "reason": guard.reason})
                requires_human = requires_human or guard.requires_human
                # 把拦截原因反馈给 LLM，让它换路径（而不是直接报错退出）
                await self.save_message(conv, "system", f"[guard] 工具 {name} 被拦：{guard.reason}")
                if guard.requires_human:
                    reply = f"该操作需要主人确认：{guard.reason}"
                    break
                continue

            result = await self.dispatch(conv, name, args)
            steps.append({"tool": name, "args": args, "result": result})
            await self.save_message(
                conv, "system",
                f"[工具 {name}] {json.dumps(result, ensure_ascii=False)[:240]}",
            )
        else:
            reply = "（已尽力，稍后继续为您处理）"
            await self.save_message(conv, "assistant", reply)

        state = await self.compute_state(conv)
        return TurnResult(
            reply=reply, steps=steps, blocked=blocked,
            requires_human=requires_human, state=state,
        )

    @staticmethod
    def _to_float(v: Any) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def new_idempotency_key() -> str:
        return uuid.uuid4().hex
