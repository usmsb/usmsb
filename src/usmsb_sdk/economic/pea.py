"""个人经济智能体 PEA（Personal Economic Agent）—— 经济公民参考实现。

PEA = harness（感知-决策-交付）+ 身份（独立地址 + 主人锚点）+ 钱包（VIBE）+ 策略（主人边界）。
角色轴 R3（专业户），成熟度轴 M1（Dry-run，有真实钱包与 guard）。

设计要点：
- 钱包 LedgerWallet 背靠一个共享账本 dict（按地址记余额）。同一个账本既给 PEA 自己花钱
  （M1 guard 限额），又给 A2A 运行时的 InMemoryLedgerBackend 做托管结算（M2 两 PEA 交易）。
- PeaHarness 把 PEA 的经济状态注入 harness 的每轮 STATE，并用真实钱包做 can_spend。
- 具体业务（喵星球/雕刻时光/地牌堂）只需继承 PeaHarness 实现领域钩子。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from usmsb_sdk.harness.base_harness import BaseHarness, ChatProvider, GuardDecision


# ── 身份 / 策略 ────────────────────────────────────────────────────────────
@dataclass
class Principal:
    """主人锚点：PEA 行为的最终责任承担方（真人）。"""

    address: str
    name: str = ""


@dataclass
class Policy:
    """主人设定的行为边界（链上/TEE 强制；此处链下镜像供 guard 使用）。"""

    max_per_tx: float = 500.0
    daily_limit: float = 2000.0
    blocked_actions: list[str] = field(default_factory=list)


@dataclass
class PeaIdentity:
    agent_id: str
    address: str            # PEA 独立链上地址
    principal: Principal     # 关联主人
    reputation: float = 0.5


# ── 钱包 ────────────────────────────────────────────────────────────────────
class LedgerWallet:
    """链下账本钱包（M1 演示/单测）。

    背靠共享账本 dict（address -> balance）。可整体替换为 agent_sdk.WalletManager
    或链上 VIBEToken，而 PEA / harness 代码不变。
    """

    def __init__(self, address: str, ledger: dict[str, float], *, daily_limit: float = 2000.0):
        self.address = address
        self.ledger = ledger
        self.daily_limit = daily_limit
        self.daily_spent = 0.0
        self.ledger.setdefault(address, 0.0)

    def available(self) -> float:
        return float(self.ledger.get(self.address, 0.0))

    def daily_remaining(self) -> float:
        return max(0.0, self.daily_limit - self.daily_spent)

    def debit(self, amount: float) -> bool:
        if self.available() < amount:
            return False
        self.ledger[self.address] = self.available() - amount
        self.daily_spent += amount
        return True

    def credit(self, amount: float) -> None:
        self.ledger[self.address] = self.available() + amount


# ── 经济公民 ────────────────────────────────────────────────────────────────
class PersonalEconomicAgent:
    """经济公民：把身份/钱包/策略/harness 组装成一个可对话、可花钱、可追责的 Agent。"""

    def __init__(self, identity: PeaIdentity, wallet: LedgerWallet, policy: Policy):
        self.identity = identity
        self.wallet = wallet
        self.policy = policy

    def economic_state(self) -> dict[str, Any]:
        """注入 harness 每轮 STATE 的经济事实。"""
        return {
            "agent": self.identity.agent_id,
            "principal": self.identity.principal.address,
            "reputation": self.identity.reputation,
            "wallet": {
                "available": self.wallet.available(),
                "daily_remaining": self.wallet.daily_remaining(),
                "currency": "VIBE",
            },
            "policy": {
                "max_per_tx": self.policy.max_per_tx,
                "daily_limit": self.policy.daily_limit,
                "blocked_actions": list(self.policy.blocked_actions),
            },
        }


# ── PEA harness 桥接 ────────────────────────────────────────────────────────
class PeaHarness(BaseHarness):
    """把 PEA 的经济能力桥接进 BaseHarness。

    实现了 compute_state（来自 PEA 经济状态）、can_spend（用真实钱包）、
    以及内存版会话持久化（M1/单测；真实部署覆盖 load/save 接 ORM）。

    具体业务只需实现：system_prompt / chat / known_tool / tool_is_side_effect / dispatch。
    """

    def __init__(self, pea: PersonalEconomicAgent):
        self.pea = pea
        self._history: dict[str, list[dict[str, str]]] = {}

    # 会话持久化（内存版）
    async def load_history(self, conv: Any) -> list[dict[str, str]]:
        return list(self._history.get(str(conv), []))

    async def save_message(self, conv: Any, role: str, content: str) -> None:
        self._history.setdefault(str(conv), []).append({"role": role, "content": content})

    # 经济状态注入
    async def compute_state(self, conv: Any) -> dict[str, Any]:
        return self.pea.economic_state()

    # 用真实钱包做限额检查（覆盖默认基于 STATE 的实现，二者一致但这里更权威）
    async def can_spend(self, amount: float, state: dict[str, Any]) -> GuardDecision:
        if amount <= 0:
            return GuardDecision(True)
        if amount > self.pea.wallet.available():
            return GuardDecision(False, f"余额不足（需 {amount}，可用 {self.pea.wallet.available()}）", requires_human=True)
        if amount > self.pea.policy.max_per_tx:
            return GuardDecision(False, f"超单笔限额（{amount} > {self.pea.policy.max_per_tx}）", requires_human=True)
        if amount > self.pea.wallet.daily_remaining():
            return GuardDecision(False, f"超当日限额（剩 {self.pea.wallet.daily_remaining()}）", requires_human=True)
        return GuardDecision(True)

    # VIBE 结算：从本 PEA 钱包扣款给 payee（M1 内部支出；M2 走 A2A escrow）
    async def settle(self, conv: Any, amount: float, payee: str, state: dict[str, Any]) -> dict[str, Any]:
        if not self.pea.wallet.debit(amount):
            return {"settled": False, "reason": "insufficient balance"}
        if payee:
            self.pea.wallet.ledger[payee] = self.pea.wallet.ledger.get(payee, 0.0) + amount
        return {"settled": True, "amount": amount, "payee": payee}
