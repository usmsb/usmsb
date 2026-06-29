"""VIBE 链上结算后端（支柱③：把 A2A 服务交付变成真实可结算的经济事件）。

相比 a2a_runtime.InMemoryLedgerBackend（纯内存账本，演示/单测用），本模块提供
**托管账户（custodial escrow）模型**，并把转账抽象成可插拔的 `TransferFn`：

    open_escrow:    payer  → escrow_account   （委托方资金进托管）
    release_escrow: escrow → payee            （质量门通过，释放给受托方）
    refund_escrow:  escrow → payer            （失败/争议，退回委托方）

同一套 escrow 编排，换不同 TransferFn 即可在「链下账本」与「真实链上 VIBEToken」之间切换：
    - make_ledger_transfer_fn(dict)         → 无链（测试/本地演示）
    - make_wallet_transfer_fn(registry, …)  → 真实 WalletManager / VIBEToken（测试网/主网）

这就是 M2「链下演示 → 真实上链」闭环的关键：A2A 运行时无需感知结算细节，
只调用 SettlementBackend 接口；切换 TransferFn 即切换结算轨道。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

# (from_id, to_id, amount) -> 是否成功
TransferFn = Callable[[str, str, float], Awaitable[bool]]

ESCROW_ACCOUNT = "__vibe_escrow__"


class VibeSettlementBackend:
    """托管账户式 VIBE 结算后端，实现 a2a_runtime.SettlementBackend 协议。"""

    def __init__(self, transfer_fn: TransferFn, *, escrow_account: str = ESCROW_ACCOUNT):
        self.transfer_fn = transfer_fn
        self.escrow_account = escrow_account
        self._escrows: dict[str, dict] = {}  # escrow_id -> {payer, payee, amount, state}

    async def open_escrow(self, *, escrow_id: str, payer: str, payee: str, amount: float) -> bool:
        if amount <= 0 or not payer:
            return False
        ok = await self.transfer_fn(payer, self.escrow_account, amount)
        if not ok:
            logger.info("[vibe_settlement] open_escrow failed payer=%s amount=%s", payer, amount)
            return False
        self._escrows[escrow_id] = {
            "payer": payer, "payee": payee, "amount": amount, "state": "open",
        }
        return True

    async def release_escrow(self, *, escrow_id: str) -> bool:
        esc = self._escrows.get(escrow_id)
        if not esc or esc["state"] != "open":
            return False
        ok = await self.transfer_fn(self.escrow_account, esc["payee"], esc["amount"])
        if ok:
            esc["state"] = "released"
        return ok

    async def refund_escrow(self, *, escrow_id: str) -> bool:
        esc = self._escrows.get(escrow_id)
        if not esc or esc["state"] != "open":
            return False
        ok = await self.transfer_fn(self.escrow_account, esc["payer"], esc["amount"])
        if ok:
            esc["state"] = "refunded"
        return ok

    async def settle_split(self, *, escrow_id: str, splits: dict[str, float]) -> bool:
        """把一笔托管按 {payee: amount} 拆分释放给多方（联合订单 Shapley 分账用）。

        各份额之和不得超过托管额；多出的尾差留在托管账户（避免超额释放）。
        """
        esc = self._escrows.get(escrow_id)
        if not esc or esc["state"] != "open":
            return False
        total = sum(a for a in splits.values() if a > 0)
        if total > esc["amount"] + 1e-9:
            logger.warning("[vibe_settlement] split %.4f 超过托管 %.4f", total, esc["amount"])
            return False
        for payee, amount in splits.items():
            if amount > 0:
                await self.transfer_fn(self.escrow_account, payee, amount)
        esc["state"] = "released"
        return True

    def escrow_state(self, escrow_id: str) -> str:
        esc = self._escrows.get(escrow_id)
        return esc["state"] if esc else "none"


# ── TransferFn 工厂 ─────────────────────────────────────────────────────────
def make_ledger_transfer_fn(balances: dict[str, float]) -> TransferFn:
    """链下账本转账轨（无链；测试 / 本地演示）。直接持有传入 dict 以共享余额。"""

    async def _transfer(from_id: str, to_id: str, amount: float) -> bool:
        # 容忍浮点尾差（1e-9）：避免按额分账时末款因 1e-14 级误差被误判余额不足
        if balances.get(from_id, 0.0) + 1e-9 < amount:
            return False
        balances[from_id] = balances.get(from_id, 0.0) - amount
        balances[to_id] = balances.get(to_id, 0.0) + amount
        return True

    return _transfer


@dataclass
class WalletEntry:
    address: str
    wallet: object  # 鸭子类型：需有 async transfer(to_address, amount) -> {"success": bool}


class WalletRegistry:
    """agent_id → (链上地址, WalletManager) 注册表，供链上 TransferFn 解析。"""

    def __init__(self) -> None:
        self._entries: dict[str, WalletEntry] = {}

    def register(self, agent_id: str, address: str, wallet: object) -> None:
        self._entries[agent_id] = WalletEntry(address=address, wallet=wallet)

    def address_of(self, agent_id: str) -> str | None:
        e = self._entries.get(agent_id)
        return e.address if e else None

    def wallet_of(self, agent_id: str) -> object | None:
        e = self._entries.get(agent_id)
        return e.wallet if e else None


def make_wallet_transfer_fn(registry: WalletRegistry) -> TransferFn:
    """真实链上转账轨：用 from 方的 WalletManager 调 VIBEToken.transfer 到 to 方地址。

    无链/无私钥时 WalletManager.transfer 返回 success=False，本函数据此返回 False，
    上层（运行时结算钩子）据此不更新 settlement_status，整体优雅降级。
    """

    async def _transfer(from_id: str, to_id: str, amount: float) -> bool:
        from_wallet = registry.wallet_of(from_id)
        to_address = registry.address_of(to_id)
        if from_wallet is None or not to_address:
            return False
        try:
            res = await from_wallet.transfer(to_address, amount)  # type: ignore[attr-defined]
        except Exception as e:  # noqa: BLE001
            logger.error("[vibe_settlement] wallet transfer error: %s", e)
            return False
        return bool(isinstance(res, dict) and res.get("success"))

    return _transfer
