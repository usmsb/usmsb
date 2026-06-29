"""USMSB 生产级 A2A 运行时单测。

覆盖：幂等、job 生命周期、manual_intervention 一等状态、
VIBE 结算闭环（escrow→settle / escrow→refund）、Agent Card。
"""

from __future__ import annotations

import pytest

from usmsb_sdk.protocol.a2a_runtime import (
    SETTLEMENT_ESCROWED,
    SETTLEMENT_REFUNDED,
    SETTLEMENT_SETTLED,
    AgentJobContext,
    AgentRuntimeConfig,
    EchoAgentHandler,
    EscrowSettlementHook,
    InMemoryLedgerBackend,
    LocalA2ARuntime,
)


def _config(tmp_path, *, settlement=False, agent_id="agent-A") -> AgentRuntimeConfig:
    return AgentRuntimeConfig(
        agent_id=agent_id,
        name=f"Test {agent_id}",
        description="unit test agent",
        base_url="http://127.0.0.1:9501",
        data_dir=tmp_path / agent_id,
        execute_inline_on_submit=True,
        settlement_enabled=settlement,
    )


def _msg(text: str, *, idem: str | None = None, vibe: float = 0.0, caller: str = "buyer") -> dict:
    metadata: dict = {"usmsb": {"caller_id": caller}}
    if idem:
        metadata["idempotency_key"] = idem
    if vibe:
        metadata["vibe_amount"] = vibe
    return {"message": {"parts": [{"kind": "text", "text": text}]}, "metadata": metadata}


# ── 基础生命周期 ──────────────────────────────────────────────────────────
async def test_submit_executes_inline_and_completes(tmp_path):
    rt = LocalA2ARuntime(_config(tmp_path), EchoAgentHandler())
    rt.initialize()
    task = await rt.submit(_msg("hello"))
    assert task["status"]["state"] == "completed"
    assert "echo: hello" in task["status"]["message"]["parts"][0]["text"]


async def test_tasks_get_roundtrip(tmp_path):
    rt = LocalA2ARuntime(_config(tmp_path), EchoAgentHandler())
    rt.initialize()
    submitted = await rt.handle_jsonrpc(
        {"method": "message/send", "params": _msg("ping")}
    )
    job_id = submitted["id"]
    fetched = await rt.handle_jsonrpc({"method": "tasks/get", "params": {"taskId": job_id}})
    assert fetched["id"] == job_id
    assert fetched["status"]["state"] == "completed"


# ── 幂等 ──────────────────────────────────────────────────────────────────
async def test_idempotency_same_key_same_job(tmp_path):
    rt = LocalA2ARuntime(_config(tmp_path), EchoAgentHandler())
    rt.initialize()
    t1 = await rt.submit(_msg("buy", idem="order-123", vibe=0))
    t2 = await rt.submit(_msg("buy again different text", idem="order-123", vibe=0))
    assert t1["id"] == t2["id"]  # 幂等键相同 → 同一 job，不重复执行


# ── manual_intervention 一等状态 ──────────────────────────────────────────
class _ManualHandler:
    async def handle(self, context: AgentJobContext) -> dict:
        return {"status": "manual_intervention_required", "error": "needs human approval"}


async def test_manual_intervention_is_first_class(tmp_path):
    rt = LocalA2ARuntime(_config(tmp_path), _ManualHandler())
    rt.initialize()
    task = await rt.submit(_msg("risky publish"))
    assert task["status"]["state"] == "auth-required"
    assert task["metadata"]["local_status"] == "manual_intervention_required"


# ── 结算闭环：escrow → settle ─────────────────────────────────────────────
async def test_settlement_escrow_then_settle_on_success(tmp_path):
    ledger = InMemoryLedgerBackend(balances={"buyer": 1000.0, "agent-A": 0.0})
    hook = EscrowSettlementHook(ledger, payee="agent-A")
    rt = LocalA2ARuntime(
        _config(tmp_path, settlement=True, agent_id="agent-A"),
        EchoAgentHandler(),  # 返回 quality_gate=passed
        settlement_hook=hook,
    )
    rt.initialize()

    task = await rt.submit(_msg("deliver service", vibe=120.0, caller="buyer"))

    # 成功 + 质量门通过 → 托管释放给受托方
    assert task["status"]["state"] == "completed"
    assert task["metadata"]["settlement_status"] == SETTLEMENT_SETTLED
    assert ledger.balance_of("buyer") == 880.0
    assert ledger.balance_of("agent-A") == 120.0


async def test_settlement_insufficient_balance_no_escrow(tmp_path):
    ledger = InMemoryLedgerBackend(balances={"buyer": 50.0})
    hook = EscrowSettlementHook(ledger, payee="agent-A")
    rt = LocalA2ARuntime(
        _config(tmp_path, settlement=True), EchoAgentHandler(), settlement_hook=hook
    )
    rt.initialize()
    task = await rt.submit(_msg("deliver", vibe=120.0, caller="buyer"))
    # 余额不足 → 不开托管；但任务仍按普通 A2A 执行完成
    assert task["metadata"]["settlement_status"] == "none"
    assert ledger.balance_of("buyer") == 50.0


# ── 结算闭环：escrow → refund（不可恢复失败）────────────────────────────
class _AlwaysFailHandler:
    async def handle(self, context: AgentJobContext) -> dict:
        raise RuntimeError("provider exploded")


async def test_settlement_refund_on_terminal_failure(tmp_path):
    ledger = InMemoryLedgerBackend(balances={"buyer": 1000.0})
    hook = EscrowSettlementHook(ledger, payee="agent-A")
    cfg = _config(tmp_path, settlement=True)
    cfg.max_attempts = 1  # 一次即终态
    rt = LocalA2ARuntime(cfg, _AlwaysFailHandler(), settlement_hook=hook)
    rt.initialize()

    task = await rt.submit(_msg("deliver", vibe=200.0, caller="buyer"))
    assert task["status"]["state"] == "failed"
    assert task["metadata"]["settlement_status"] == SETTLEMENT_REFUNDED
    # 托管全额退回委托方
    assert ledger.balance_of("buyer") == 1000.0


async def test_escrow_held_before_execution(tmp_path):
    """提交（未 inline 执行）后，资金应已进托管。"""
    ledger = InMemoryLedgerBackend(balances={"buyer": 1000.0})
    hook = EscrowSettlementHook(ledger, payee="agent-A")
    cfg = _config(tmp_path, settlement=True)
    cfg.execute_inline_on_submit = False  # 只入队，不执行
    rt = LocalA2ARuntime(cfg, EchoAgentHandler(), settlement_hook=hook)
    rt.initialize()

    task = await rt.submit(_msg("deliver", vibe=120.0, caller="buyer"))
    assert task["status"]["state"] == "working"
    assert task["metadata"]["settlement_status"] == SETTLEMENT_ESCROWED
    assert ledger.balance_of("buyer") == 880.0  # 已扣进托管，尚未释放


# ── Agent Card ────────────────────────────────────────────────────────────
async def test_agent_card_declares_vibe_settlement(tmp_path):
    rt = LocalA2ARuntime(_config(tmp_path, settlement=True), EchoAgentHandler())
    card = rt.build_agent_card()
    assert card["protocolVersion"] == "0.3.0"
    assert card["capabilities"]["vibeSettlement"] is True
    assert any(m == "message/send" for m in card["supported_interfaces"][0]["methods"])
