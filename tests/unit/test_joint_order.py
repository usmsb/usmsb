"""联合订单 + Shapley 单测（#B：多 PEA 组队公平分账）。

覆盖：Shapley 精确值、协同分摊、固定报酬分配、joint_order 端到端（托管→分账/退款）。
"""

from __future__ import annotations

from typing import Any

import pytest

from usmsb_sdk.economic.joint_order import (
    LLMContributionAssessor,
    additive_with_synergy,
    distribute,
    shapley_values,
)
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


# ── Shapley 数学 ───────────────────────────────────────────────────────────
def test_shapley_classic_superadditive():
    # v({a})=10, v({b})=20, v({a,b})=50
    def v(s):
        s = set(s)
        if s == {"a"}: return 10.0
        if s == {"b"}: return 20.0
        if s == {"a", "b"}: return 50.0
        return 0.0
    sh = shapley_values(["a", "b"], v)
    assert sh["a"] == 20.0 and sh["b"] == 30.0      # 协同 20 平分
    assert sh["a"] + sh["b"] == 50.0                # 有效性：求和=大联盟价值


def test_shapley_symmetric_synergy_split():
    v = additive_with_synergy({"a": 10.0, "b": 20.0}, synergy_bonus=10.0)
    sh = shapley_values(["a", "b"], v)
    # 协同 10 对称分摊：各 +5
    assert sh["a"] == 15.0 and sh["b"] == 25.0


def test_distribute_fixed_reward():
    pay = distribute(100.0, {"a": 15.0, "b": 25.0})
    assert abs(pay["a"] - 37.5) < 1e-9 and abs(pay["b"] - 62.5) < 1e-9
    assert abs(sum(pay.values()) - 100.0) < 1e-9


def test_shapley_three_players_sums_to_total():
    v = additive_with_synergy({"a": 5, "b": 5, "c": 5}, synergy_bonus=6.0)
    sh = shapley_values(["a", "b", "c"], v)
    assert abs(sum(sh.values()) - v(frozenset({"a", "b", "c"}))) < 1e-9


# ── LLM 贡献评估 ───────────────────────────────────────────────────────────
async def test_contribution_assessor_llm_and_fallback():
    a = LLMContributionAssessor(ScriptedChat(['{"m1":0.8,"m2":0.2}']))
    assert await a.assess("t", {"m1": "好", "m2": "一般"}) == {"m1": 0.8, "m2": 0.2}
    a2 = LLMContributionAssessor(None)
    assert await a2.assess("t", {"m1": "x", "m2": "y"}) == {"m1": 1.0, "m2": 1.0}  # 均等


# ── joint_order 端到端 ─────────────────────────────────────────────────────
def _member(agent_id, ledger, market, reply):
    ledger[agent_id] = 0.0
    pea = PersonalEconomicAgent(
        PeaIdentity(agent_id, agent_id, Principal(f"0x{agent_id}")),
        LedgerWallet(agent_id, ledger, daily_limit=5000.0),
        Policy(max_per_tx=500.0, daily_limit=5000.0),
    )
    chat = ScriptedChat([f'{{"action":"say","text":"{reply}"}}'])
    return MarketPeaHarness(pea, chat, market)


async def test_joint_order_settles_by_shapley(tmp_path):
    ledger: dict[str, float] = {"coord": 1000.0}
    market = PeaMarket(ledger=ledger, matcher=LLMCapabilityMatcher(None))
    qg = LLMQualityGate(None)  # 交付非空→passed

    for mid, rep in [("m1", "主视觉部分完成"), ("m2", "文案部分完成")]:
        h = _member(mid, ledger, market, rep)
        market.make_supplier_runtime(
            agent_id=mid, handler=PeaA2AHandler(h, quality_gate=qg),
            data_dir=str(tmp_path / mid), capabilities=f"{mid} 能力",
        )

    # 贡献不均：m1 0.7 / m2 0.3 → Shapley 按基值分（synergy=0 → 即基值比例）
    assessor = LLMContributionAssessor(ScriptedChat(['{"m1":0.7,"m2":0.3}']))
    res = await market.joint_order(
        from_id="coord", task="品牌全案",
        assignments={"m1": "做主视觉", "m2": "写文案"},
        total_reward=200.0, contribution_assessor=assessor,
    )

    assert res["status"] == "settled"
    assert abs(ledger["coord"] - 800.0) < 1e-9        # 付了 200
    assert abs(ledger["m1"] - 140.0) < 1e-9           # 200 * 0.7
    assert abs(ledger["m2"] - 60.0) < 1e-9            # 200 * 0.3
    assert abs(ledger["__vibe_escrow__"]) < 1e-9      # 托管清零


async def test_joint_order_refunds_on_quality_fail(tmp_path):
    ledger: dict[str, float] = {"coord": 1000.0}
    market = PeaMarket(ledger=ledger, matcher=LLMCapabilityMatcher(None))

    # m1 质量门通过；m2 质量门失败（QG 判 failed）
    qg_pass = LLMQualityGate(None)
    qg_fail = LLMQualityGate(ScriptedChat(['{"verdict":"failed","reason":"没做"}']))

    h1 = _member("m1", ledger, market, "做好了")
    market.make_supplier_runtime(agent_id="m1", handler=PeaA2AHandler(h1, quality_gate=qg_pass),
                                 data_dir=str(tmp_path / "m1"), capabilities="x")
    h2 = _member("m2", ledger, market, "敷衍交付")
    market.make_supplier_runtime(agent_id="m2", handler=PeaA2AHandler(h2, quality_gate=qg_fail),
                                 data_dir=str(tmp_path / "m2"), capabilities="y")

    res = await market.joint_order(
        from_id="coord", task="全案",
        assignments={"m1": "a", "m2": "b"}, total_reward=200.0,
    )
    assert res["status"] == "quality_failed"
    assert abs(ledger["coord"] - 1000.0) < 1e-9       # 整单退款
    assert ledger.get("m1", 0) == 0.0 and ledger.get("m2", 0) == 0.0
