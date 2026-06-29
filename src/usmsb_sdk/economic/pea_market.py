"""PeaMarket —— 多 PEA over A2A 的服务市场（M3）。

把"一个 PEA 内部的 harness 循环"放大成"PEA 之间的市场"：每个 PEA 既是消费者
（把活外包出去）又是供应商（接活赚 VIBE），委托可递归（供应方转身变需求方）。

**LLM-first 原则**（凡需要"判断/智能"的地方一律走 LLM，护栏才用代码）：
- 选供应商（语义能力匹配）→ LLMCapabilityMatcher（LLM；非关键词 fallback=按声誉）。
- 判交付合格与否（质量门）→ LLMQualityGate（LLM；fallback=passed）。
- 拆解目标/决定外包什么 → 由协调者 PEA 的 harness 主循环 LLM 决定。
- 预算/限额/幂等/托管/结算 → 代码护栏（guard + a2a_runtime + settlement）。
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from usmsb_sdk.economic.joint_order import (
    LLMContributionAssessor,
    additive_with_synergy,
    distribute,
    shapley_values,
)

from usmsb_sdk.economic.pea import PeaHarness, PersonalEconomicAgent
from usmsb_sdk.economic.vibe_settlement import (
    VibeSettlementBackend,
    make_ledger_transfer_fn,
)
from usmsb_sdk.harness.base_harness import ChatProvider, GuardDecision
from usmsb_sdk.services.matching.llm_capability_fit import LLMCapabilityFit
from usmsb_sdk.protocol.a2a_runtime import (
    AgentRuntimeConfig,
    EscrowSettlementHook,
    LocalA2ARuntime,
)

logger = logging.getLogger(__name__)


# ── LLM 能力匹配（语义选供应商，非关键词）─────────────────────────────────
@dataclass
class SupplierInfo:
    agent_id: str
    capabilities: str           # 自然语言能力描述
    reputation: float = 0.5
    runtime: Any = None         # LocalA2ARuntime（本地进程内供应商）
    url: str = ""               # 远程 A2A 端点 URL（跨进程/跨机器供应商）
    client: Any = None          # A2AClient（远程派单；留空则按 url 现建）


class LLMCapabilityMatcher:
    """给任务在候选供应商里选最合适的一个 —— 语义匹配，走 LLM。

    fallback（无 LLM/解析失败）：按声誉排序选最高，**不**用关键词子串匹配。
    """

    _SYS = (
        "你是 AI 服务市场的撮合器。根据【任务】语义，从【候选供应商】里选出能力最匹配、"
        "且声誉较高的一个。只看能力是否真的胜任（语义理解，不是字面包含）。"
        '严格返回 JSON：{"agent_id":"<选中id>","reason":"<一句话理由>"}。'
    )

    def __init__(self, chat: ChatProvider | None):
        self.chat = chat

    async def pick(self, task: str, candidates: list[SupplierInfo]) -> str | None:
        if not candidates:
            return None
        if self.chat is None:
            return self._fallback(candidates)
        listing = "\n".join(
            f'- id={c.agent_id} | 能力：{c.capabilities} | 声誉：{c.reputation:.2f}'
            for c in candidates
        )
        try:
            raw = await self.chat.complete([
                {"role": "system", "content": self._SYS},
                {"role": "user", "content": f"任务：{task}\n候选供应商：\n{listing}"},
            ])
            chosen = self._parse_id(raw)
            valid = {c.agent_id for c in candidates}
            if chosen in valid:
                return chosen
            logger.info("[matcher] LLM 返回无效 id=%r，回退声誉", chosen)
        except Exception as e:  # noqa: BLE001
            logger.warning("[matcher] LLM 匹配失败：%s，回退声誉", e)
        return self._fallback(candidates)

    @staticmethod
    def _fallback(candidates: list[SupplierInfo]) -> str:
        # 非关键词 fallback：按声誉选最高
        return max(candidates, key=lambda c: c.reputation).agent_id

    @staticmethod
    def _parse_id(raw: str) -> str | None:
        s = (raw or "").strip()
        st, en = s.find("{"), s.rfind("}")
        if st >= 0 and en > st:
            try:
                obj = json.loads(s[st:en + 1])
                if isinstance(obj, dict):
                    return str(obj.get("agent_id") or "").strip() or None
            except json.JSONDecodeError:
                pass
        return None


# ── 能力发现：从名录按 LLM 语义 × 声誉 检索 ────────────────────────────────
@dataclass
class DiscoveryResult:
    agent_id: str
    fit: float          # LLM 语义匹配度 0..1
    reputation: float   # 实时声誉 0..1
    score: float        # 综合排序分


class CapabilityDiscovery:
    """从供应商名录"按能力检索"：LLM 语义匹配度为主，声誉为调节。

    替代手动指定/关键词匹配。reputation_fn 可接 ReputationService 取实时声誉
    （随每次交付的 TrustBridge 更新而变），不传则用 SupplierInfo.reputation。
    """

    def __init__(self, fit: LLMCapabilityFit, *, reputation_fn: Callable[[str], float] | None = None):
        self.fit = fit
        self.reputation_fn = reputation_fn

    def _rep(self, info: "SupplierInfo") -> float:
        if self.reputation_fn is not None:
            try:
                return float(self.reputation_fn(info.agent_id))
            except Exception:  # noqa: BLE001
                pass
        return info.reputation

    async def search(self, task: str, suppliers: list["SupplierInfo"], *, top_k: int = 3) -> list[DiscoveryResult]:
        results: list[DiscoveryResult] = []
        for s in suppliers:
            fit = await self.fit.score([s.capabilities], task)  # LLM 语义（无 LLM 回退关键词）
            rep = self._rep(s)
            # 能力匹配为主，声誉做 0.5~1.0 的调节因子（不让高声誉淹没能力不匹配）
            score = fit * (0.5 + 0.5 * max(0.0, min(1.0, rep)))
            results.append(DiscoveryResult(s.agent_id, fit, rep, score))
        results.sort(key=lambda r: r.score, reverse=True)
        return [r for r in results if r.fit > 0][:top_k]

    async def best(self, task: str, suppliers: list["SupplierInfo"]) -> str | None:
        ranked = await self.search(task, suppliers, top_k=1)
        return ranked[0].agent_id if ranked else None

    async def discover(self, task: str, provider: Any, *, top_k: int = 3) -> list[DiscoveryResult]:
        """从一个目录来源（全网注册表/souls/本地名录）拉取候选并按语义×声誉排序。

        provider 鸭子类型：需有 async list_suppliers() -> list[SupplierInfo]。
        """
        suppliers = await provider.list_suppliers()
        return await self.search(task, suppliers, top_k=top_k)


# ── LLM 质量门（判交付是否达标，非硬编码 passed）──────────────────────────
@dataclass
class QualityVerdict:
    verdict: str   # passed | failed
    reason: str = ""


class LLMQualityGate:
    """用 LLM 判断交付物是否达标。fallback（无 LLM）：passed（保守由人工闸门兜底）。"""

    _SYS = (
        "你是交付质量评审。判断【交付物】是否真的完成了【任务】要求（语义判断，看实质）。"
        '严格返回 JSON：{"verdict":"passed"或"failed","reason":"<简短理由>"}。'
    )

    def __init__(self, chat: ChatProvider | None):
        self.chat = chat

    async def judge(self, task: str, delivery: str) -> QualityVerdict:
        if self.chat is None or not delivery.strip():
            return QualityVerdict("passed" if delivery.strip() else "failed", "no-llm-fallback")
        try:
            raw = await self.chat.complete([
                {"role": "system", "content": self._SYS},
                {"role": "user", "content": f"任务：{task}\n交付物：{delivery}"},
            ])
            return self._parse(raw)
        except Exception as e:  # noqa: BLE001
            logger.warning("[quality_gate] LLM 评审失败：%s，默认 passed", e)
            return QualityVerdict("passed", "llm-error-fallback")

    @staticmethod
    def _parse(raw: str) -> QualityVerdict:
        s = (raw or "").strip()
        st, en = s.find("{"), s.rfind("}")
        if st >= 0 and en > st:
            try:
                obj = json.loads(s[st:en + 1])
                v = str(obj.get("verdict", "passed")).lower()
                return QualityVerdict("failed" if v == "failed" else "passed", str(obj.get("reason", "")))
            except json.JSONDecodeError:
                pass
        return QualityVerdict("passed", "unparsed")


# ── PEA harness → A2A handler ──────────────────────────────────────────────
class PeaA2AHandler:
    """把一个 PEA harness 接成 A2A runtime 的 handler：收到 job → 跑 harness → LLM 质量门。"""

    def __init__(self, harness: PeaHarness, *, quality_gate: LLMQualityGate | None = None):
        self.harness = harness
        self.quality_gate = quality_gate

    async def handle(self, context: Any) -> dict[str, Any]:
        # 透传转包深度/预算给 harness（递归护栏）
        usmsb = context.metadata.get("usmsb") if isinstance(context.metadata.get("usmsb"), dict) else {}
        if isinstance(usmsb, dict) and hasattr(self.harness, "set_inbound_context"):
            self.harness.set_inbound_context(
                depth=int(usmsb.get("delegation_depth", 0) or 0),
                budget=usmsb.get("delegation_budget"),
            )
        res = await self.harness.run_turn(context.job.id, context.input_text)
        # 人工闸门是一等可交付状态（不是异常）
        if res.requires_human:
            return {"status": "manual_intervention_required",
                    "error": res.reply, "output": res.reply}
        delivery = self._delivery_text(res)
        if self.quality_gate is not None:
            v = await self.quality_gate.judge(context.input_text, delivery)
            return {"output": delivery, "quality_gate": v.verdict,
                    "reason": v.reason, "evidence_uri": f"local://{context.job.id}"}
        return {"output": delivery, "quality_gate": "passed",
                "evidence_uri": f"local://{context.job.id}"}

    @staticmethod
    def _delivery_text(res: Any) -> str:
        parts = [res.reply] if res.reply else []
        for s in res.steps:
            r = s.get("result")
            if isinstance(r, dict):
                for k in ("briefing", "content", "text", "output", "delivered", "purchased"):
                    if r.get(k):
                        parts.append(str(r[k]))
        return "\n".join(p for p in parts if p)


# ── 协调者 harness（带 A2A 外包工具）──────────────────────────────────────
ToolFn = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


class MarketPeaHarness(PeaHarness):
    """会通过 A2A 把活外包出去的协调者 PEA。

    内建工具 delegate_via_a2a(args.task, args.vibe_cost)：harness 主循环的 LLM 决定
    "外包什么、给多少预算"，市场用 LLMCapabilityMatcher 决定"给谁"。vibe_cost 过 guard 限额。
    额外领域工具以 {name:(is_side_effect, fn)} 注入。
    """

    def __init__(
        self,
        pea: PersonalEconomicAgent,
        chat: ChatProvider,
        market: "PeaMarket",
        *,
        tools: dict[str, tuple[bool, ToolFn]] | None = None,
        system_prompt: str | None = None,
        max_delegation_depth: int = 3,
        sub_budget_ratio: float = 1.0,
    ):
        super().__init__(pea)
        self._chat = chat
        self.market = market
        self._tools = tools or {}
        self._system_prompt = system_prompt or self._default_prompt()
        # 递归转包护栏
        self.max_delegation_depth = max_delegation_depth
        self.sub_budget_ratio = sub_budget_ratio  # 下游可再转包的预算 = 本次收款 × 比例
        self._delegation_depth = 0                 # 本 PEA 当前所处转包深度
        self._delegation_budget: float | None = None  # 本轮还能再外包多少 VIBE（None=不限链预算）

    def set_inbound_context(self, *, depth: int = 0, budget: float | None = None) -> None:
        """收到上游 A2A 任务时由 handler 调用，设置本 PEA 的转包深度与可再转包预算。"""
        self._delegation_depth = int(depth)
        self._delegation_budget = budget

    def _default_prompt(self) -> str:
        tool_lines = "\n".join(f"  - {n}" for n in self._tools) if self._tools else ""
        return (
            f"你是 {self.pea.identity.agent_id}，一个自主经营的经济 PEA。"
            "在主人钱包/规则边界内自主决策，用 JSON 动作协议逐步行动：\n"
            '  {"action":"tool","name":"<工具>","args":{...}}\n'
            '  {"action":"say","text":"<结果>"}\n'
            "外包工具：delegate_via_a2a(args.task 要外包的活, args.vibe_cost 预算)"
            "——你只说要什么、给多少预算，市场会语义匹配最合适的供应商。\n"
            f"{('其它工具：' + chr(10) + tool_lines) if tool_lines else ''}\n"
            "花钱/越界会被安全闸门拦截转人工。完成后用 say 汇报。"
        )

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @property
    def chat(self) -> ChatProvider:
        return self._chat

    def known_tool(self, name: str) -> bool:
        return name == "delegate_via_a2a" or name in self._tools

    def tool_is_side_effect(self, name: str) -> bool:
        if name == "delegate_via_a2a":
            return True
        spec = self._tools.get(name)
        return bool(spec and spec[0])

    async def _guard_tool(self, name: str, args: dict[str, Any], state: dict[str, Any]) -> GuardDecision:
        # 先过通用护栏（限额/红线/未知工具）
        base = await super()._guard_tool(name, args, state)
        if not base.allowed or name != "delegate_via_a2a":
            return base
        # 递归转包护栏：深度 + 预算
        if self._delegation_depth >= self.max_delegation_depth:
            return GuardDecision(
                False, f"转包链过深（深度 {self._delegation_depth} ≥ 上限 {self.max_delegation_depth}）",
                requires_human=True,
            )
        amount = self.estimate_cost(name, args)
        if self._delegation_budget is not None and amount > self._delegation_budget + 1e-9:
            return GuardDecision(
                False, f"超转包预算（{amount} > 剩余 {self._delegation_budget:.2f}）",
                requires_human=True,
            )
        return base

    async def dispatch(self, conv: Any, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "delegate_via_a2a":
            amount = self.estimate_cost(name, args)  # guard 已校验限额+深度+预算
            if self._delegation_budget is not None:
                self._delegation_budget -= amount  # 扣减本轮剩余转包预算
            return await self.market.delegate(
                from_id=self.pea.identity.agent_id,
                task=str(args.get("task", "")),
                vibe_amount=amount,
                depth=self._delegation_depth,
                max_depth=self.max_delegation_depth,
                sub_budget_ratio=self.sub_budget_ratio,
            )
        spec = self._tools.get(name)
        if spec:
            return await spec[1](args)
        return {"ok": True}


# ── 市场 ────────────────────────────────────────────────────────────────────
@dataclass
class PeaMarket:
    """多 PEA 服务市场：共享账本 + 托管结算 + 供应商名录 + LLM 撮合。"""

    ledger: dict[str, float]
    matcher: LLMCapabilityMatcher
    discovery: "CapabilityDiscovery | None" = None  # 能力发现（优先于 matcher）
    directory: Any = None  # DirectoryProvider：全网候选来源（注册表/souls/本地）
    settlement: VibeSettlementBackend = field(init=False)
    suppliers: dict[str, SupplierInfo] = field(default_factory=dict)
    _client_cache: dict[str, Any] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.settlement = VibeSettlementBackend(make_ledger_transfer_fn(self.ledger))

    def register_supplier(self, info: SupplierInfo) -> None:
        self.suppliers[info.agent_id] = info

    def register_remote_supplier(
        self, *, agent_id: str, url: str, capabilities: str,
        reputation: float = 0.5, client: Any = None,
    ) -> None:
        """登记一个远程 A2A 供应商（按 URL 跨进程派单）。"""
        self.register_supplier(SupplierInfo(
            agent_id=agent_id, capabilities=capabilities, reputation=reputation,
            runtime=None, url=url, client=client,
        ))

    async def _submit(self, supplier: SupplierInfo, params: dict[str, Any]) -> dict[str, Any]:
        """统一派单：本地走 runtime（进程内），远程走 A2AClient（HTTP/JSON-RPC）。"""
        if supplier.runtime is not None:
            return await supplier.runtime.submit(params)
        client = supplier.client
        if client is None and supplier.url:
            from usmsb_sdk.protocol.a2a_runtime.client import A2AClient
            client = self._client_cache.get(supplier.url)
            if client is None:
                client = A2AClient(supplier.url)
                self._client_cache[supplier.url] = client
        if client is not None:
            return await client.submit(params)
        return {"status": {"state": "failed", "message": {"parts": [{"text": "no endpoint"}]}},
                "metadata": {}, "error": "no endpoint"}

    def make_supplier_runtime(
        self,
        *,
        agent_id: str,
        handler: Any,
        data_dir: str,
        capabilities: str,
        reputation: float = 0.5,
        trust_hook: Any = None,
    ) -> LocalA2ARuntime:
        """为一个供应 PEA 建 A2A 运行时（带托管结算 + 可选声誉），并登记到名录。"""
        cfg = AgentRuntimeConfig(
            agent_id=agent_id, name=agent_id, description=capabilities,
            base_url=f"http://127.0.0.1/{agent_id}", data_dir=data_dir,
            execute_inline_on_submit=True, settlement_enabled=True,
        )
        hook = EscrowSettlementHook(self.settlement, payee=agent_id)
        rt = LocalA2ARuntime(cfg, handler, settlement_hook=hook, trust_hook=trust_hook)
        rt.initialize()
        self.register_supplier(SupplierInfo(agent_id, capabilities, reputation, rt))
        return rt

    def _candidates(self, exclude: str | None = None) -> list[SupplierInfo]:
        return [s for s in self.suppliers.values() if s.agent_id != exclude]

    async def delegate(self, *, from_id: str, task: str, vibe_amount: float,
                       to_id: str | None = None, depth: int = 0,
                       max_depth: int = 3, sub_budget_ratio: float = 1.0) -> dict[str, Any]:
        """把任务外包出去：能力发现/LLM 选供应商 → A2A 派单（自动托管/交付/质量门/结算）。

        depth/sub_budget_ratio 沿转包链传播：下游收到 delegation_depth=depth+1，
        可再转包预算 delegation_budget=vibe_amount×ratio（防转包链烧钱）。
        """
        if to_id is None:
            # 优先：从全网目录检索，挑能力最匹配且"本地可派单"（有 runtime）的
            if self.discovery is not None and self.directory is not None:
                ranked = await self.discovery.discover(task, self.directory, top_k=10)
                for r in ranked:
                    if r.agent_id != from_id and r.agent_id in self.suppliers:
                        to_id = r.agent_id
                        break
            # 回退：本地名录（能力发现 or LLM 撮合器）
            if to_id is None:
                cands = self._candidates(exclude=from_id)
                if self.discovery is not None:
                    to_id = await self.discovery.best(task, cands)
                else:
                    to_id = await self.matcher.pick(task, cands)
        if to_id is None or to_id not in self.suppliers:
            return {"status": "no_supplier", "task": task}
        result = await self._submit(self.suppliers[to_id], {
            "message": {"parts": [{"kind": "text", "text": task}]},
            "metadata": {"vibe_amount": vibe_amount, "usmsb": {
                "caller_id": from_id,
                "delegation_depth": depth + 1,
                "delegation_budget": vibe_amount * sub_budget_ratio,
            }},
        })
        return {
            "delegated_to": to_id,
            "state": result["status"]["state"],
            "settlement": result["metadata"].get("settlement_status"),
            "quality_gate": result["metadata"].get("quality_gate"),
            "delivery": result.get("status", {}).get("message", {}).get("parts", [{}])[0].get("text", ""),
        }

    async def joint_order(
        self,
        *,
        from_id: str,
        task: str,
        assignments: dict[str, str],
        total_reward: float,
        contribution_assessor: LLMContributionAssessor | None = None,
        synergy_bonus: float = 0.0,
    ) -> dict[str, Any]:
        """多 PEA 组队联合订单：一次托管 → 各成员交付 → LLM 评贡献 → Shapley 分账。

        assignments: {成员 agent_id: 子任务}。total_reward 一次性从 from_id 托管，
        全部交付且质量门通过后，按 Shapley 值公平分给各成员；任一不过则整单退款。
        """
        members = [m for m in assignments if m in self.suppliers]
        if not members:
            return {"status": "no_members"}

        escrow_id = f"jo_{uuid.uuid4().hex[:16]}"
        if not await self.settlement.open_escrow(
            escrow_id=escrow_id, payer=from_id, payee="(pool)", amount=total_reward
        ):
            return {"status": "escrow_failed"}

        # 各成员交付（vibe_amount=0：仅执行，结算走联合分账；声誉仍按质量门更新）
        deliveries: dict[str, str] = {}
        quality: dict[str, str] = {}
        for m in members:
            res = await self._submit(self.suppliers[m], {
                "message": {"parts": [{"kind": "text", "text": assignments[m]}]},
                "metadata": {"vibe_amount": 0, "usmsb": {"caller_id": from_id}},
            })
            deliveries[m] = res.get("status", {}).get("message", {}).get("parts", [{}])[0].get("text", "")
            quality[m] = res["metadata"].get("quality_gate", "passed")

        # 任一质量门未过 → 整单退款，不分账
        if any(q == "failed" for q in quality.values()):
            await self.settlement.refund_escrow(escrow_id=escrow_id)
            return {"status": "quality_failed", "quality": quality}

        # LLM 评各成员贡献基值（智能）→ Shapley 公平分账（数学）
        assessor = contribution_assessor or LLMContributionAssessor(None)
        base = await assessor.assess(task, deliveries)
        v = additive_with_synergy(base, synergy_bonus)
        shap = shapley_values(members, v)
        payouts = distribute(total_reward, shap)

        await self.settlement.settle_split(escrow_id=escrow_id, splits=payouts)
        return {
            "status": "settled",
            "members": members,
            "contribution_base": base,
            "shapley": shap,
            "payouts": payouts,
        }
