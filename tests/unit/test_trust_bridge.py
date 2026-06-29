"""TrustBridge 单测（Task 5：门禁→声誉/争议映射）。

覆盖：
- 质量门通过的交付 → 受托方声誉加分。
- 质量门失败 → 声誉扣分 + 开争议。
- 不可恢复失败（异常）→ 退款 + 声誉扣分 + 开争议。
- 闭环：TrustBridge 接 ReputationService + 注入 DisputeOpener，挂进 LocalA2ARuntime。
"""

from __future__ import annotations

from typing import Any

import pytest

from usmsb_sdk.protocol.a2a_runtime import (
    AgentRuntimeConfig,
    EscrowSettlementHook,
    InMemoryLedgerBackend,
    LocalA2ARuntime,
)
from usmsb_sdk.services.reputation_service import ReputationService
from usmsb_sdk.trust import TrustBridge


class _RecordingDispute:
    def __init__(self) -> None:
        self.opened: list[dict[str, Any]] = []

    async def open_dispute(self, *, job_id, claimant, respondent, amount, reason) -> dict[str, Any]:
        rec = {"job_id": job_id, "claimant": claimant, "respondent": respondent,
               "amount": amount, "reason": reason}
        self.opened.append(rec)
        return {"dispute_id": f"d_{job_id}", **rec}


class _PassHandler:
    async def handle(self, context) -> dict:
        return {"output": "ok", "quality_gate": "passed"}


class _FailQualityHandler:
    async def handle(self, context) -> dict:
        return {"output": "差", "quality_gate": "failed"}


class _ExplodeHandler:
    async def handle(self, context) -> dict:
        raise RuntimeError("provider crashed")


def _runtime(tmp_path, handler, *, settlement=True, trust=None, agent_id="provider"):
    ledger = {"buyer": 1000.0, "__esc__": 0.0, agent_id: 0.0}
    backend = InMemoryLedgerBackend(balances=ledger)
    hook = EscrowSettlementHook(backend, payee=agent_id)
    cfg = AgentRuntimeConfig(
        agent_id=agent_id, name="p", description="provider pea",
        base_url="http://127.0.0.1:9504", data_dir=tmp_path / agent_id,
        execute_inline_on_submit=True, settlement_enabled=settlement, max_attempts=1,
    )
    rt = LocalA2ARuntime(cfg, handler, settlement_hook=hook, trust_hook=trust)
    rt.initialize()
    return rt, ledger


def _submit(rt, *, vibe=100.0):
    return rt.submit({
        "message": {"parts": [{"kind": "text", "text": "task"}]},
        "metadata": {"vibe_amount": vibe, "usmsb": {"caller_id": "buyer"}},
    })


# ── 成功交付 → 声誉加分 ────────────────────────────────────────────────────
async def test_quality_passed_raises_reputation(tmp_path):
    rep = ReputationService()
    rep.initialize_agent("provider")
    before = rep.get_score("provider").dimensions["reliability"]

    bridge = TrustBridge(rep)
    rt, _ = _runtime(tmp_path, _PassHandler(), trust=bridge)
    task = await _submit(rt)

    assert task["status"]["state"] == "completed"
    after = rep.get_score("provider").dimensions["reliability"]
    assert after > before  # 可靠性上升


# ── 质量门失败 → 声誉扣分 + 开争议 ─────────────────────────────────────────
async def test_quality_failed_lowers_reputation_and_opens_dispute(tmp_path):
    rep = ReputationService()
    rep.initialize_agent("provider")
    # 先垫高可靠性，便于观察下降
    rep.record_transaction_completed(agent_id="provider", was_successful=True, on_time=True)
    before = rep.get_score("provider").dimensions["reliability"]

    dispute = _RecordingDispute()
    bridge = TrustBridge(rep, dispute_opener=dispute)
    rt, _ = _runtime(tmp_path, _FailQualityHandler(), trust=bridge)
    task = await _submit(rt, vibe=150.0)

    after = rep.get_score("provider").dimensions["reliability"]
    assert after < before                       # 声誉扣分
    assert len(dispute.opened) == 1             # 已开争议
    assert dispute.opened[0]["respondent"] == "provider"
    assert dispute.opened[0]["claimant"] == "buyer"
    assert dispute.opened[0]["amount"] == 150.0


# ── 异常失败 → 退款 + 声誉扣分 + 争议 ─────────────────────────────────────
async def test_terminal_failure_refunds_and_opens_dispute(tmp_path):
    rep = ReputationService()
    rep.initialize_agent("provider")
    dispute = _RecordingDispute()
    bridge = TrustBridge(rep, dispute_opener=dispute)

    rt, ledger = _runtime(tmp_path, _ExplodeHandler(), trust=bridge)
    task = await _submit(rt, vibe=120.0)

    assert task["status"]["state"] == "failed"
    assert ledger["buyer"] == 1000.0           # 已退款
    assert len(dispute.opened) == 1            # 已开争议


# ── 无声誉服务时优雅降级（不报错）─────────────────────────────────────────
async def test_trust_bridge_degrades_without_services(tmp_path):
    bridge = TrustBridge(reputation_service=None, dispute_opener=None)
    rt, _ = _runtime(tmp_path, _PassHandler(), trust=bridge)
    task = await _submit(rt)
    assert task["status"]["state"] == "completed"  # 不抛异常
