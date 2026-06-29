"""远程 A2A 端点单测：HTTP server + client 跨"网络"派单。

用 httpx.ASGITransport 把请求直送 ASGI app（不开真实端口），端到端验证
Agent Card / JSON-RPC 派单 / tasks-get / 远程结算 / 错误。
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport

from usmsb_sdk.economic.pea_market import LLMCapabilityMatcher, PeaMarket
from usmsb_sdk.economic.vibe_settlement import VibeSettlementBackend, make_ledger_transfer_fn
from usmsb_sdk.protocol.a2a_runtime import (
    SETTLEMENT_SETTLED,
    A2AClient,
    A2ARemoteError,
    AgentRuntimeConfig,
    EchoAgentHandler,
    EscrowSettlementHook,
    LocalA2ARuntime,
)
from usmsb_sdk.protocol.a2a_runtime.server import create_a2a_app


def _remote_runtime(tmp_path, ledger, *, agent_id="seller"):
    backend = VibeSettlementBackend(make_ledger_transfer_fn(ledger))
    hook = EscrowSettlementHook(backend, payee=agent_id)
    cfg = AgentRuntimeConfig(
        agent_id=agent_id, name=agent_id, description="远程设计供应商",
        base_url=f"http://{agent_id}", data_dir=tmp_path / agent_id,
        execute_inline_on_submit=True, settlement_enabled=True,
    )
    return LocalA2ARuntime(cfg, EchoAgentHandler(), settlement_hook=hook)


def _client_for(runtime, base="http://seller") -> A2AClient:
    app = create_a2a_app(runtime)
    return A2AClient(base, transport=ASGITransport(app=app))


# ── Agent Card / 健康检查（HTTP）────────────────────────────────────────────
async def test_agent_card_over_http(tmp_path):
    client = _client_for(_remote_runtime(tmp_path, {}))
    card = await client.get_agent_card()
    assert card["protocolVersion"] == "0.3.0"
    assert card["capabilities"]["vibeSettlement"] is True
    assert (await client.health())["status"] == "ok"


# ── JSON-RPC 派单 + tasks/get（HTTP）────────────────────────────────────────
async def test_remote_submit_and_get_task(tmp_path):
    client = _client_for(_remote_runtime(tmp_path, {}))
    task = await client.submit({
        "message": {"parts": [{"kind": "text", "text": "hello remote"}]},
        "metadata": {"usmsb": {"caller_id": "buyer"}},
    })
    assert task["status"]["state"] == "completed"
    assert "echo: hello remote" in task["status"]["message"]["parts"][0]["text"]

    fetched = await client.get_task(task["id"])
    assert fetched["id"] == task["id"] and fetched["status"]["state"] == "completed"


# ── 未知方法 → 远程错误 ────────────────────────────────────────────────────
async def test_remote_unknown_method_raises(tmp_path):
    client = _client_for(_remote_runtime(tmp_path, {}))
    with pytest.raises(A2ARemoteError) as ei:
        await client._rpc("does/not/exist", {})
    assert ei.value.code == -32601


# ── 市场经远程供应商派单 + 远程结算 ────────────────────────────────────────
async def test_market_delegates_to_remote_supplier_and_settles(tmp_path):
    # 共享账本（同进程内模拟跨"网络"；真实跨机器时结算轨是链）
    ledger: dict[str, float] = {"buyer": 1000.0, "__vibe_escrow__": 0.0, "seller": 0.0}
    runtime = _remote_runtime(tmp_path, ledger, agent_id="seller")
    client = _client_for(runtime, base="http://seller")

    market = PeaMarket(ledger=ledger, matcher=LLMCapabilityMatcher(None))
    market.register_remote_supplier(
        agent_id="seller", url="http://seller", capabilities="海报设计", client=client,
    )

    res = await market.delegate(from_id="buyer", task="做促销海报", vibe_amount=150.0)

    # 经 HTTP/JSON-RPC 远程派单 → 远程 runtime 执行 + 结算
    assert res["delegated_to"] == "seller"
    assert res["state"] == "completed"
    assert res["settlement"] == SETTLEMENT_SETTLED
    assert ledger["buyer"] == 850.0 and ledger["seller"] == 150.0
    assert ledger["__vibe_escrow__"] == 0.0


# ── 无端点供应商 → 优雅失败 ───────────────────────────────────────────────
async def test_supplier_without_endpoint_fails_gracefully(tmp_path):
    market = PeaMarket(ledger={"buyer": 100.0}, matcher=LLMCapabilityMatcher(None))
    market.register_remote_supplier(agent_id="ghost", url="", capabilities="x", client=None)
    res = await market.delegate(from_id="buyer", task="t", vibe_amount=0, to_id="ghost")
    assert res["state"] == "failed"
