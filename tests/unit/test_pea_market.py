"""PeaMarket 单测（M3：多 PEA over A2A，智能点走 LLM）。

覆盖：
- LLMCapabilityMatcher：LLM 选供应商 / 非关键词 fallback。
- LLMQualityGate：LLM 判交付 / fallback。
- 递归外包闭环：喵星球→设计PEA→文案PEA，共享账本结算 + 声誉更新。
"""

from __future__ import annotations

from typing import Any

import pytest

from usmsb_sdk.economic.pea import (
    LedgerWallet,
    PeaIdentity,
    PersonalEconomicAgent,
    Policy,
    Principal,
)
from usmsb_sdk.economic.pea_market import (
    LLMCapabilityMatcher,
    LLMQualityGate,
    MarketPeaHarness,
    PeaA2AHandler,
    PeaMarket,
    SupplierInfo,
)
from usmsb_sdk.services.reputation_service import ReputationService
from usmsb_sdk.trust import TrustBridge


class ScriptedChat:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        return self._responses.pop(0) if self._responses else '{"action":"say","text":"完成。"}'


# ── LLM 能力匹配 ───────────────────────────────────────────────────────────
async def test_matcher_llm_picks_valid_id():
    m = LLMCapabilityMatcher(ScriptedChat(['{"agent_id":"pea_design","reason":"懂视觉"}']))
    cands = [SupplierInfo("pea_design", "平面/海报设计", 0.6),
             SupplierInfo("pea_copy", "文案写作", 0.7)]
    assert await m.pick("做一张促销海报", cands) == "pea_design"


async def test_matcher_invalid_id_falls_back_to_reputation():
    m = LLMCapabilityMatcher(ScriptedChat(['{"agent_id":"ghost"}']))
    cands = [SupplierInfo("a", "x", 0.4), SupplierInfo("b", "y", 0.9)]
    assert await m.pick("任务", cands) == "b"  # 非关键词 fallback：声誉最高


async def test_matcher_no_llm_uses_reputation():
    m = LLMCapabilityMatcher(None)
    cands = [SupplierInfo("a", "x", 0.8), SupplierInfo("b", "y", 0.3)]
    assert await m.pick("任务", cands) == "a"


# ── LLM 质量门 ─────────────────────────────────────────────────────────────
async def test_quality_gate_llm_verdict():
    qg = LLMQualityGate(ScriptedChat(['{"verdict":"failed","reason":"主体糊了"}']))
    v = await qg.judge("做海报", "一张模糊的图")
    assert v.verdict == "failed" and "糊" in v.reason


async def test_quality_gate_fallback_passed():
    qg = LLMQualityGate(None)
    assert (await qg.judge("t", "有内容的交付")).verdict == "passed"
    assert (await qg.judge("t", "   ")).verdict == "failed"  # 空交付


# ── 递归外包闭环：喵星球 → 设计 → 文案 ────────────────────────────────────
def _pea(agent_id: str, ledger: dict[str, float], balance: float, max_per_tx: float = 500.0):
    ledger[agent_id] = balance
    return PersonalEconomicAgent(
        identity=PeaIdentity(agent_id, agent_id, Principal(f"0x{agent_id}"), reputation=0.5),
        wallet=LedgerWallet(agent_id, ledger, daily_limit=5000.0),
        policy=Policy(max_per_tx=max_per_tx, daily_limit=5000.0, blocked_actions=[]),
    )


async def test_recursive_delegation_settles_across_three_peas(tmp_path):
    ledger: dict[str, float] = {}
    # 撮合器：第1次外包(海报)选设计，第2次(文案)选文案
    matcher = LLMCapabilityMatcher(ScriptedChat([
        '{"agent_id":"pea_design"}',
        '{"agent_id":"pea_copy"}',
    ]))
    market = PeaMarket(ledger=ledger, matcher=matcher)
    rep = ReputationService()
    for a in ("pea_design", "pea_copy"):
        rep.initialize_agent(a)
    rel0_design = rep.get_score("pea_design").dimensions["reliability"]
    rel0_copy = rep.get_score("pea_copy").dimensions["reliability"]
    trust = TrustBridge(rep)
    qg = LLMQualityGate(None)  # 交付非空→passed（质量门 LLM 路径另有单测）

    # 文案 PEA（叶子供应商）：write_copy → say
    copy_pea = _pea("pea_copy", ledger, balance=0.0)
    copy_chat = ScriptedChat([
        '{"action":"tool","name":"write_copy","args":{}}',
        '{"action":"say","text":"文案已交付。"}',
    ])

    async def _write_copy(args):
        return {"content": "标题：双十一，给毛孩子拍套写真，5 折"}

    copy_harness = MarketPeaHarness(
        copy_pea, copy_chat, market, tools={"write_copy": (False, _write_copy)},
    )
    market.make_supplier_runtime(
        agent_id="pea_copy", handler=PeaA2AHandler(copy_harness, quality_gate=qg),
        data_dir=str(tmp_path / "copy"), capabilities="文案写作", reputation=0.7, trust_hook=trust,
    )

    # 设计 PEA（供应商 + 二级需求方）：先外包文案，再出海报
    design_pea = _pea("pea_design", ledger, balance=100.0)  # 有周转资金垫付分包
    design_chat = ScriptedChat([
        '{"action":"tool","name":"delegate_via_a2a","args":{"task":"写促销文案","vibe_cost":30}}',
        '{"action":"tool","name":"make_poster","args":{}}',
        '{"action":"say","text":"海报已交付（含主视觉+文案）。"}',
    ])

    async def _make_poster(args):
        return {"content": "海报：双十一宠物写真 5 折主视觉"}

    design_harness = MarketPeaHarness(
        design_pea, design_chat, market, tools={"make_poster": (False, _make_poster)},
    )
    market.make_supplier_runtime(
        agent_id="pea_design", handler=PeaA2AHandler(design_harness, quality_gate=qg),
        data_dir=str(tmp_path / "design"), capabilities="平面/海报设计", reputation=0.6, trust_hook=trust,
    )

    # 喵星球（顶层需求方）：外包海报
    miao_pea = _pea("pea_miao", ledger, balance=1000.0)
    miao_chat = ScriptedChat([
        '{"action":"tool","name":"delegate_via_a2a","args":{"task":"设计双十一宠物写真促销海报","vibe_cost":150}}',
        '{"action":"say","text":"促销物料齐了。"}',
    ])
    miao = MarketPeaHarness(miao_pea, miao_chat, market)

    res = await miao.run_turn("c1", "搞个双十一促销，物料你安排")

    # 递归外包成功
    deleg = [s for s in res.steps if s.get("tool") == "delegate_via_a2a"]
    assert deleg and deleg[0]["result"]["delegated_to"] == "pea_design"
    assert deleg[0]["result"]["settlement"] == "settled"

    # 共享账本：钱按链路流动
    assert ledger["pea_miao"] == 850.0     # 付了 150
    assert ledger["pea_copy"] == 30.0      # 收了 30
    assert ledger["pea_design"] == 220.0   # 100 - 30(分包) + 150(收款) = 220
    assert ledger["__vibe_escrow__"] == 0.0  # 两笔托管都已清

    # 声誉：两个供应商都因交付通过而加分（相对各自初值上升）
    assert rep.get_score("pea_design").dimensions["reliability"] > rel0_design
    assert rep.get_score("pea_copy").dimensions["reliability"] > rel0_copy
