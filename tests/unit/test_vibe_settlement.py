"""VIBE 链上结算后端单测（Task 4：补 transfer/escrow + 链上结算后端）。

覆盖：
- VibeSettlementBackend 托管账户模型：open→release / open→refund / 余额不足。
- make_wallet_transfer_fn：经 WalletManager.transfer 解析地址并转账（用 fake wallet）。
- WalletManager.transfer 无链优雅降级（不抛异常）。
- 闭环：LocalA2ARuntime + VibeSettlementBackend → escrow→settle（换 TransferFn 即上链）。
"""

from __future__ import annotations

from typing import Any

import pytest

from usmsb_sdk.agent_sdk.wallet import WalletManager
from usmsb_sdk.economic.vibe_settlement import (
    VibeSettlementBackend,
    WalletRegistry,
    make_ledger_transfer_fn,
    make_wallet_transfer_fn,
)
from usmsb_sdk.protocol.a2a_runtime import (
    SETTLEMENT_SETTLED,
    AgentRuntimeConfig,
    EscrowSettlementHook,
    LocalA2ARuntime,
)


# ── VibeSettlementBackend：托管账户模型 ─────────────────────────────────────
async def test_escrow_open_then_release():
    ledger = {"buyer": 1000.0, "__vibe_escrow__": 0.0, "seller": 0.0}
    backend = VibeSettlementBackend(make_ledger_transfer_fn(ledger))

    assert await backend.open_escrow(escrow_id="e1", payer="buyer", payee="seller", amount=150)
    assert ledger["buyer"] == 850.0
    assert ledger["__vibe_escrow__"] == 150.0  # 资金在托管

    assert await backend.release_escrow(escrow_id="e1")
    assert ledger["__vibe_escrow__"] == 0.0
    assert ledger["seller"] == 150.0
    assert backend.escrow_state("e1") == "released"


async def test_escrow_open_then_refund():
    ledger = {"buyer": 1000.0, "__vibe_escrow__": 0.0}
    backend = VibeSettlementBackend(make_ledger_transfer_fn(ledger))
    await backend.open_escrow(escrow_id="e1", payer="buyer", payee="seller", amount=200)
    assert ledger["buyer"] == 800.0

    assert await backend.refund_escrow(escrow_id="e1")
    assert ledger["buyer"] == 1000.0
    assert backend.escrow_state("e1") == "refunded"


async def test_escrow_insufficient_balance():
    ledger = {"buyer": 50.0, "__vibe_escrow__": 0.0}
    backend = VibeSettlementBackend(make_ledger_transfer_fn(ledger))
    assert await backend.open_escrow(escrow_id="e1", payer="buyer", payee="seller", amount=150) is False
    assert ledger["buyer"] == 50.0  # 未扣款
    # 未开成功的托管不能 release
    assert await backend.release_escrow(escrow_id="e1") is False


# ── make_wallet_transfer_fn：经 WalletManager 转账 ─────────────────────────
class _FakeWallet:
    """鸭子类型 wallet：async transfer + 共享账本。"""

    def __init__(self, address: str, ledger: dict[str, float]):
        self.address = address
        self.ledger = ledger

    async def transfer(self, to_address: str, amount: float) -> dict[str, Any]:
        if self.ledger.get(self.address, 0.0) < amount:
            return {"success": False, "reason": "insufficient"}
        self.ledger[self.address] -= amount
        self.ledger[to_address] = self.ledger.get(to_address, 0.0) + amount
        return {"success": True, "tx_hash": "0xfake"}


async def test_wallet_transfer_fn_routes_through_wallets():
    ledger = {"0xBuyer": 500.0, "0xEscrow": 0.0}
    reg = WalletRegistry()
    reg.register("buyer", "0xBuyer", _FakeWallet("0xBuyer", ledger))
    reg.register("__vibe_escrow__", "0xEscrow", _FakeWallet("0xEscrow", ledger))
    transfer_fn = make_wallet_transfer_fn(reg)

    ok = await transfer_fn("buyer", "__vibe_escrow__", 120.0)
    assert ok is True
    assert ledger["0xBuyer"] == 380.0
    assert ledger["0xEscrow"] == 120.0

    # 未注册的 agent → 优雅返回 False
    assert await transfer_fn("ghost", "__vibe_escrow__", 10.0) is False


# ── WalletManager.transfer 无链优雅降级 ────────────────────────────────────
async def test_wallet_manager_transfer_degrades_without_chain():
    wm = WalletManager()  # 无 platform / 无 vibe_token
    res = await wm.transfer("0xabc", 10.0)
    assert res["success"] is False
    assert "reason" in res  # 不抛异常，给出原因

    # 非正数金额直接拒绝
    res2 = await wm.transfer("0xabc", 0)
    assert res2["success"] is False


# ── 闭环：A2A 运行时 + VibeSettlementBackend ───────────────────────────────
class _DeliverHandler:
    async def handle(self, context) -> dict:
        return {"output": "交付完成", "quality_gate": "passed"}


async def test_closed_loop_runtime_with_vibe_backend(tmp_path):
    ledger = {"pea_buyer": 1000.0, "__vibe_escrow__": 0.0, "pea_seller": 0.0}
    backend = VibeSettlementBackend(make_ledger_transfer_fn(ledger))
    hook = EscrowSettlementHook(backend, payee="pea_seller")

    cfg = AgentRuntimeConfig(
        agent_id="pea_seller",
        name="seller",
        description="seller pea",
        base_url="http://127.0.0.1:9503",
        data_dir=tmp_path / "seller",
        execute_inline_on_submit=True,
        settlement_enabled=True,
    )
    rt = LocalA2ARuntime(cfg, _DeliverHandler(), settlement_hook=hook)
    rt.initialize()

    task = await rt.submit({
        "message": {"parts": [{"kind": "text", "text": "做设计"}]},
        "metadata": {"vibe_amount": 150.0, "usmsb": {"caller_id": "pea_buyer"}},
    })

    assert task["status"]["state"] == "completed"
    assert task["metadata"]["settlement_status"] == SETTLEMENT_SETTLED
    assert ledger["pea_buyer"] == 850.0
    assert ledger["pea_seller"] == 150.0
    assert ledger["__vibe_escrow__"] == 0.0  # 托管已清空
