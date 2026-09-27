"""VIBE 实验托管后端：持久预留、逐笔结果和不确定状态留存。

相比 a2a_runtime.InMemoryLedgerBackend（纯内存账本，演示/单测用），本模块提供
**托管账户（custodial escrow）模型**，并把转账抽象成可插拔的 `TransferFn`：

    open_escrow:    payer  → escrow_account   （委托方资金进托管）
    release_escrow: escrow → payee            （质量门通过，释放给受托方）
    refund_escrow:  escrow → payer            （失败/争议，退回委托方）

TransferFn 提供不同的转账适配点，但替换它本身并不证明生产支付闭环：
    - make_ledger_transfer_fn(dict)         → 无链（测试/本地演示）
    - make_wallet_transfer_fn(registry, …)  → 真实 WalletManager / VIBEToken（测试网/主网）

真实资金还需要整数单位、最终交易回执、持久幂等及人工对账恢复方案。
本模块不自动重试未知转账，不将模拟账本余额或布尔返回当作银行审计。
"""

from __future__ import annotations

import json
import logging
import math
import sqlite3
from dataclasses import dataclass
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

# (from_id, to_id, amount) -> 是否成功
TransferFn = Callable[[str, str, float], Awaitable[bool]]

ESCROW_ACCOUNT = "__vibe_escrow__"


class VibeSettlementBackend:
    """Write-ahead escrow journal; uncertain transfers are never retried automatically.

    No journal_path means an in-memory *test* journal. A wallet-backed adapter
    requires a durable file. This legacy float API is not a fiat payment rail:
    a live provider still needs integer units, final receipts and reconciliation.
    """

    def __init__(self, transfer_fn: TransferFn, *, escrow_account: str = ESCROW_ACCOUNT,
                 journal_path: str | None = None):
        if getattr(transfer_fn, "requires_durable_journal", False) and (
            not journal_path or str(journal_path) == ":memory:"
        ):
            raise ValueError("Wallet transfers require a durable escrow journal")
        self.transfer_fn = transfer_fn
        self.escrow_account = escrow_account
        self._db = sqlite3.connect(str(journal_path or ":memory:"), timeout=20)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("CREATE TABLE IF NOT EXISTS escrows (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def _get(self, escrow_id: str) -> dict | None:
        row = self._db.execute("SELECT data FROM escrows WHERE id=?", (escrow_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def _save(self, escrow_id: str, esc: dict) -> None:
        self._db.execute("INSERT INTO escrows VALUES (?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                         (escrow_id, json.dumps(esc, allow_nan=False, sort_keys=True)))

    @staticmethod
    def _positive(amount) -> bool:
        return type(amount) in (float, int) and math.isfinite(amount) and amount > 0

    async def _attempt(self, escrow_id: str, esc: dict, source: str, target: str,
                       amount: float) -> bool:
        attempt = {"source": source, "target": target, "amount": amount, "status": "attempting"}
        esc["attempts"].append(attempt)
        with self._db:
            self._save(escrow_id, esc)
        try:
            ok = await self.transfer_fn(source, target, amount)
        except BaseException as exc:
            attempt["status"] = "unknown"
            esc["state"] = "uncertain"
            with self._db:
                self._save(escrow_id, esc)
            if not isinstance(exc, Exception):
                raise
            return False
        # Boolean False cannot distinguish a definite rejection from a timeout
        # inside a third-party adapter. Preserve the hold for reconciliation.
        attempt["status"] = "confirmed" if ok is True else "unknown"
        if ok is not True:
            esc["state"] = "uncertain"
        with self._db:
            self._save(escrow_id, esc)
        return ok is True

    async def open_escrow(self, *, escrow_id: str, payer: str, payee: str, amount: float) -> bool:
        if (not self._positive(amount) or not all(isinstance(v, str) and v.strip()
                for v in (escrow_id, payer, payee)) or self.escrow_account in (payer, payee)):
            return False
        terms = {"payer": payer, "payee": payee, "amount": amount, "account": self.escrow_account}
        with self._db:
            self._db.execute("BEGIN IMMEDIATE")
            existing = self._get(escrow_id)
            if existing:
                return existing["terms"] == terms and existing["state"] == "open"
            esc = {"terms": terms, "state": "opening", "attempts": []}
            self._save(escrow_id, esc)
        if not await self._attempt(escrow_id, esc, payer, self.escrow_account, amount):
            return False
        esc["state"] = "open"
        with self._db:
            self._save(escrow_id, esc)
        return True

    async def _finish(self, escrow_id: str, operation: str, splits: dict | None = None) -> bool:
        with self._db:
            self._db.execute("BEGIN IMMEDIATE")
            esc = self._get(escrow_id)
            if not esc or esc["state"] != "open" or esc["terms"]["account"] != self.escrow_account:
                return False
            terms = esc["terms"]
            if splits is None:
                splits = {terms["payer"] if operation == "refund" else terms["payee"]: terms["amount"]}
            if (not isinstance(splits, dict) or not splits or any(
                not isinstance(p, str) or not p.strip() or p == self.escrow_account
                or not self._positive(a) for p, a in splits.items()
            )):
                return False
            if not math.isclose(math.fsum(splits.values()), terms["amount"], rel_tol=0, abs_tol=1e-9):
                return False
            esc.update(state="transferring", operation=operation, plan=dict(splits))
            self._save(escrow_id, esc)
        for payee, amount in splits.items():
            if not await self._attempt(escrow_id, esc, self.escrow_account, payee, amount):
                return False
        esc["state"] = "refunded" if operation == "refund" else "released"
        with self._db:
            self._save(escrow_id, esc)
        return True

    async def release_escrow(self, *, escrow_id: str) -> bool:
        return await self._finish(escrow_id, "release")

    async def refund_escrow(self, *, escrow_id: str) -> bool:
        return await self._finish(escrow_id, "refund")

    async def settle_split(self, *, escrow_id: str, splits: dict[str, float]) -> bool:
        """Require a complete positive plan; partial/unknown payout stays on hold."""
        if not isinstance(splits, dict):
            return False
        return await self._finish(escrow_id, "split", splits)

    def escrow_state(self, escrow_id: str) -> str:
        esc = self._get(escrow_id)
        return esc["state"] if esc else "none"

    def escrow_record(self, escrow_id: str) -> dict | None:
        """Return journal evidence for reconciliation, never retry a transfer."""
        return self._get(escrow_id)


# ── TransferFn 工厂 ─────────────────────────────────────────────────────────
def make_ledger_transfer_fn(balances: dict[str, float]) -> TransferFn:
    """链下账本转账轨（无链；测试 / 本地演示）。直接持有传入 dict 以共享余额。"""

    async def _transfer(from_id: str, to_id: str, amount: float) -> bool:
        if not VibeSettlementBackend._positive(amount) or not from_id or not to_id or from_id == to_id:
            return False
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

    _transfer.requires_durable_journal = True
    return _transfer
