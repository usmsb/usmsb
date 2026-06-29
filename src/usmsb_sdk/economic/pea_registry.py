"""PeaRegistry —— PEA 的创建 / 查询 / 运行入口（让经济公民可被创建调用）。

第一轮发现的窟窿之一：PEA 有了 harness 与钱包，却没有"入口"——无法被创建、查询、驱动。
PeaRegistry 补上这层：
- 统一在一个共享账本上创建 PEA（共享账本同时可背 vibe_settlement，支撑 PEA 间交易）。
- 注册各 PEA 的 harness（ButlerPea / 喵星球 等）。
- run_turn 便捷入口：按 agent_id 找到 harness 跑一轮。
"""

from __future__ import annotations

from dataclasses import dataclass

from usmsb_sdk.economic.pea import (
    LedgerWallet,
    PeaIdentity,
    PersonalEconomicAgent,
    Policy,
    Principal,
)
from usmsb_sdk.harness.base_harness import BaseHarness, TurnResult


@dataclass
class PeaRecord:
    pea: PersonalEconomicAgent
    harness: BaseHarness | None = None


class PeaRegistry:
    """进程内 PEA 注册表（M1/M2 入口；生产可换 DB 持久化）。"""

    def __init__(self, ledger: dict[str, float] | None = None):
        # 共享账本：同一 dict 既给各 PEA 钱包，也可给 vibe_settlement 做结算轨
        self.ledger: dict[str, float] = ledger if ledger is not None else {}
        self._peas: dict[str, PeaRecord] = {}

    def create(
        self,
        *,
        agent_id: str,
        principal_address: str,
        principal_name: str = "",
        balance: float = 0.0,
        max_per_tx: float = 500.0,
        daily_limit: float = 2000.0,
        blocked_actions: list[str] | None = None,
        reputation: float = 0.5,
        harness: BaseHarness | None = None,
    ) -> PersonalEconomicAgent:
        if agent_id in self._peas:
            raise ValueError(f"PEA already exists: {agent_id}")
        self.ledger[agent_id] = balance
        wallet = LedgerWallet(agent_id, self.ledger, daily_limit=daily_limit)
        identity = PeaIdentity(
            agent_id=agent_id,
            address=agent_id,
            principal=Principal(address=principal_address, name=principal_name),
            reputation=reputation,
        )
        policy = Policy(max_per_tx=max_per_tx, daily_limit=daily_limit,
                        blocked_actions=blocked_actions or [])
        pea = PersonalEconomicAgent(identity, wallet, policy)
        self._peas[agent_id] = PeaRecord(pea=pea, harness=harness)
        return pea

    def register_harness(self, agent_id: str, harness: BaseHarness) -> None:
        rec = self._peas.get(agent_id)
        if rec is None:
            raise KeyError(f"unknown PEA: {agent_id}")
        rec.harness = harness

    def get(self, agent_id: str) -> PersonalEconomicAgent | None:
        rec = self._peas.get(agent_id)
        return rec.pea if rec else None

    def get_harness(self, agent_id: str) -> BaseHarness | None:
        rec = self._peas.get(agent_id)
        return rec.harness if rec else None

    def list_ids(self) -> list[str]:
        return list(self._peas.keys())

    def balance_of(self, agent_id: str) -> float:
        return float(self.ledger.get(agent_id, 0.0))

    async def run_turn(self, agent_id: str, conv: str, text: str) -> TurnResult:
        harness = self.get_harness(agent_id)
        if harness is None:
            raise KeyError(f"PEA has no harness registered: {agent_id}")
        return await harness.run_turn(conv, text)
