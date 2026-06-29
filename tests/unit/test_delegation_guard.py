"""递归转包护栏单测（#C：防转包链烧钱/无限深）。

覆盖：深度上限拦截、预算上限拦截、预算内放行、e2e 预算沿链传播并拦下递归转包。
"""

from __future__ import annotations

from typing import Any

import pytest

from usmsb_sdk.economic.pea import (
    LedgerWallet, PeaIdentity, PersonalEconomicAgent, Policy, Principal,
)
from usmsb_sdk.economic.pea_market import (
    LLMCapabilityMatcher, LLMQualityGate, MarketPeaHarness, PeaA2AHandler, PeaMarket,
)


class ScriptedChat:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    async def complete(self, messages, **kwargs: Any) -> str:
        return self._responses.pop(0) if self._responses else '{"action":"say","text":"完成。"}'


def _harness(market, *, balance=10000.0, max_depth=3, sub_ratio=1.0, chat=None):
    ledger = market.ledger
    ledger["coord"] = balance
    pea = PersonalEconomicAgent(
        PeaIdentity("coord", "coord", Principal("0xc")),
        LedgerWallet("coord", ledger, daily_limit=100000.0),
        Policy(max_per_tx=10000.0, daily_limit=100000.0),  # 基础限额放宽，单测聚焦链护栏
    )
    return MarketPeaHarness(pea, chat or ScriptedChat([]), market,
                            max_delegation_depth=max_depth, sub_budget_ratio=sub_ratio)


async def _state(h):
    return await h.compute_state("c")


# ── 深度护栏 ───────────────────────────────────────────────────────────────
async def test_depth_guard_blocks_when_too_deep():
    market = PeaMarket(ledger={}, matcher=LLMCapabilityMatcher(None))
    h = _harness(market, max_depth=2)
    h.set_inbound_context(depth=2)   # 已在深度 2，上限 2 → 不能再转包
    g = await h._guard_tool("delegate_via_a2a", {"task": "x", "vibe_cost": 10}, await _state(h))
    assert g.allowed is False and "转包链过深" in g.reason and g.requires_human


async def test_depth_guard_allows_within_limit():
    market = PeaMarket(ledger={}, matcher=LLMCapabilityMatcher(None))
    h = _harness(market, max_depth=3)
    h.set_inbound_context(depth=1)   # 深度 1 < 3 → 允许
    g = await h._guard_tool("delegate_via_a2a", {"task": "x", "vibe_cost": 10}, await _state(h))
    assert g.allowed is True


# ── 预算护栏 ───────────────────────────────────────────────────────────────
async def test_budget_guard_blocks_over_budget():
    market = PeaMarket(ledger={}, matcher=LLMCapabilityMatcher(None))
    h = _harness(market)
    h.set_inbound_context(depth=0, budget=100.0)   # 只能再转包 100
    g = await h._guard_tool("delegate_via_a2a", {"task": "x", "vibe_cost": 150}, await _state(h))
    assert g.allowed is False and "超转包预算" in g.reason


async def test_budget_guard_allows_within_budget():
    market = PeaMarket(ledger={}, matcher=LLMCapabilityMatcher(None))
    h = _harness(market)
    h.set_inbound_context(depth=0, budget=200.0)
    g = await h._guard_tool("delegate_via_a2a", {"task": "x", "vibe_cost": 150}, await _state(h))
    assert g.allowed is True


async def test_no_chain_budget_means_unlimited():
    market = PeaMarket(ledger={}, matcher=LLMCapabilityMatcher(None))
    h = _harness(market)  # 顶层协调者：未设 inbound budget → 不受链预算限制
    g = await h._guard_tool("delegate_via_a2a", {"task": "x", "vibe_cost": 9999}, await _state(h))
    assert g.allowed is True


# ── e2e：预算沿链传播，拦下设计PEA 的递归转包 ─────────────────────────────
def _supplier(market, agent_id, ledger, chat, *, max_depth=3):
    ledger[agent_id] = 0.0
    pea = PersonalEconomicAgent(
        PeaIdentity(agent_id, agent_id, Principal(f"0x{agent_id}")),
        LedgerWallet(agent_id, ledger, daily_limit=100000.0),
        Policy(max_per_tx=100000.0, daily_limit=100000.0),
    )
    return MarketPeaHarness(pea, chat, market, max_delegation_depth=max_depth)


async def test_e2e_budget_blocks_recursive_delegation(tmp_path):
    ledger: dict[str, float] = {"pea_miao": 1000.0}
    market = PeaMarket(ledger=ledger, matcher=LLMCapabilityMatcher(None))
    qg = LLMQualityGate(None)

    # 设计PEA 收单后想把"文案"转包 30，但上游只给了 15 的转包预算 → 被拦
    design_chat = ScriptedChat([
        '{"action":"tool","name":"delegate_via_a2a","args":{"task":"写文案","vibe_cost":30}}',
        '{"action":"say","text":"无法转包，待主人确认。"}',
    ])
    design = _supplier(market, "pea_design", ledger, design_chat)
    market.make_supplier_runtime(
        agent_id="pea_design", handler=PeaA2AHandler(design, quality_gate=qg),
        data_dir=str(tmp_path / "design"), capabilities="设计",
    )

    # 喵星球用 sub_budget_ratio=0.1 外包 150 → 设计PEA 只拿到 15 的再转包预算
    miao = _harness(market, balance=1000.0, sub_ratio=0.1,
                    chat=ScriptedChat([
                        '{"action":"tool","name":"delegate_via_a2a","args":{"task":"做海报","vibe_cost":150}}',
                        '{"action":"say","text":"已外包海报。"}',
                    ]))
    # 把协调者钱包对齐到 pea_miao 账本键
    ledger["pea_miao"] = 1000.0
    miao.pea.identity.agent_id = "pea_miao"
    miao.pea.wallet.address = "pea_miao"

    res = await miao.run_turn("c1", "做促销海报")

    # 设计PEA 的递归转包被预算拦下 → 文案PEA 从未被调用
    assert "pea_copy" not in ledger or ledger.get("pea_copy", 0) == 0.0
    deleg = [s for s in res.steps if s.get("tool") == "delegate_via_a2a"]
    assert deleg, "喵星球应已外包"
    # 设计PEA 转人工（递归被拦）→ 该 A2A 任务为 auth-required，托管未释放
    assert deleg[0]["result"]["state"] == "auth-required"
