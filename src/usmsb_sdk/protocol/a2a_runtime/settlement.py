"""A2A 运行时的 VIBE 结算钩子。

这是 USMSB 相对 OPC A2A 的核心增量：OPC 的 A2A 有执行没结算。
USMSB 在 job 生命周期挂结算钩子，把每次服务交付变成可结算、可追责的经济事件：

    job 提交(带 vibe_amount) → on_escrow   ：委托方资金进托管
    job 成功 + 质量门通过     → on_settle   ：托管释放给受托方
    job 失败/不可恢复         → on_refund   ：托管退回委托方

`SettlementBackend` 是抽象后端：可由链下账本（M2 测试网/演示）或链上 Escrow 合约实现。
PEA 参考实现（Task 3）会提供 VIBE 钱包驱动的后端。
"""

from __future__ import annotations

import logging
import uuid
from typing import Protocol, runtime_checkable

from .store import (
    SETTLEMENT_ESCROWED,
    SETTLEMENT_REFUNDED,
    SETTLEMENT_SETTLED,
    JobRecord,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class SettlementBackend(Protocol):
    """结算后端抽象：链下账本或链上合约都实现这个接口。"""

    async def open_escrow(self, *, escrow_id: str, payer: str, payee: str, amount: float) -> bool: ...
    async def release_escrow(self, *, escrow_id: str) -> bool: ...
    async def refund_escrow(self, *, escrow_id: str) -> bool: ...


@runtime_checkable
class SettlementHook(Protocol):
    """运行时在 job 生命周期调用的结算钩子。返回写回 store 的字段。"""

    async def on_escrow(self, job: JobRecord, payee: str) -> dict: ...
    async def on_settle(self, job: JobRecord) -> dict: ...
    async def on_refund(self, job: JobRecord) -> dict: ...


class NoOpSettlementHook:
    """默认空实现：纯 A2A，不做结算。"""

    async def on_escrow(self, job: JobRecord, payee: str) -> dict:
        return {}

    async def on_settle(self, job: JobRecord) -> dict:
        return {}

    async def on_refund(self, job: JobRecord) -> dict:
        return {}


class EscrowSettlementHook:
    """基于 SettlementBackend 的标准托管结算钩子。

    payee = 本 Agent 的收款地址（受托方）。payer 从 job.caller_id 取。
    """

    def __init__(self, backend: SettlementBackend, payee: str):
        self.backend = backend
        self.payee = payee

    async def on_escrow(self, job: JobRecord, payee: str | None = None) -> dict:
        if job.vibe_amount <= 0:
            return {}
        escrow_id = job.escrow_id or f"esc_{uuid.uuid4().hex[:16]}"
        ok = await self.backend.open_escrow(
            escrow_id=escrow_id,
            payer=job.caller_id,
            payee=payee or self.payee,
            amount=job.vibe_amount,
        )
        if not ok:
            logger.warning("[settlement] open_escrow failed for job %s", job.id)
            return {}
        return {"escrow_id": escrow_id, "settlement_status": SETTLEMENT_ESCROWED}

    async def on_settle(self, job: JobRecord) -> dict:
        if not job.escrow_id or job.settlement_status != SETTLEMENT_ESCROWED:
            return {}
        ok = await self.backend.release_escrow(escrow_id=job.escrow_id)
        if not ok:
            logger.warning("[settlement] release_escrow failed for job %s", job.id)
            return {}
        return {"settlement_status": SETTLEMENT_SETTLED}

    async def on_refund(self, job: JobRecord) -> dict:
        if not job.escrow_id or job.settlement_status != SETTLEMENT_ESCROWED:
            return {}
        ok = await self.backend.refund_escrow(escrow_id=job.escrow_id)
        if not ok:
            logger.warning("[settlement] refund_escrow failed for job %s", job.id)
            return {}
        return {"settlement_status": SETTLEMENT_REFUNDED}


class InMemoryLedgerBackend:
    """链下内存账本结算后端（用于单测与本地演示，无需链）。

    维护一个 {address: balance} 账本 + escrow 暂存。
    open 时从 payer 扣款进 escrow；release 转给 payee；refund 退回 payer。
    """

    def __init__(self, balances: dict[str, float] | None = None):
        # 直接持有传入的 dict（不拷贝）：让 PEA 的 LedgerWallet 与结算后端共享同一账本，
        # 从而 escrow/release/refund 即时反映到各 PEA 钱包余额（支撑 M2 两 PEA 交易）。
        self.balances: dict[str, float] = balances if balances is not None else {}
        self._escrows: dict[str, dict] = {}  # escrow_id -> {payer, payee, amount, state}

    def balance_of(self, address: str) -> float:
        return self.balances.get(address, 0.0)

    async def open_escrow(self, *, escrow_id: str, payer: str, payee: str, amount: float) -> bool:
        if self.balances.get(payer, 0.0) < amount:
            return False
        self.balances[payer] = self.balances.get(payer, 0.0) - amount
        self._escrows[escrow_id] = {
            "payer": payer, "payee": payee, "amount": amount, "state": "open",
        }
        return True

    async def release_escrow(self, *, escrow_id: str) -> bool:
        esc = self._escrows.get(escrow_id)
        if not esc or esc["state"] != "open":
            return False
        self.balances[esc["payee"]] = self.balances.get(esc["payee"], 0.0) + esc["amount"]
        esc["state"] = "released"
        return True

    async def refund_escrow(self, *, escrow_id: str) -> bool:
        esc = self._escrows.get(escrow_id)
        if not esc or esc["state"] != "open":
            return False
        self.balances[esc["payer"]] = self.balances.get(esc["payer"], 0.0) + esc["amount"]
        esc["state"] = "refunded"
        return True
