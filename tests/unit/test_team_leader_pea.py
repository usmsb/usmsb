"""TeamLeaderPea 单测（#2：团队=多 PEA over A2A，替代 dict-CRUD stub）。

覆盖：LLM 拆解、组队（能力发现）、联合订单 Shapley 分账、products.team 安全导入。
"""

from __future__ import annotations

from typing import Any

import pytest

from usmsb_sdk.economic.joint_order import LLMContributionAssessor
from usmsb_sdk.economic.pea import (
    LedgerWallet, PeaIdentity, PersonalEconomicAgent, Policy, Principal,
)
from usmsb_sdk.economic.pea_market import (
    CapabilityDiscovery, LLMCapabilityMatcher, LLMQualityGate,
    MarketPeaHarness, PeaA2AHandler, PeaMarket,
)
from usmsb_sdk.products.team import LLMTaskDecomposer, TeamLeaderPea
from usmsb_sdk.services.matching.llm_capability_fit import LLMCapabilityFit


class ScriptedChat:
    def __init__(self, responses: list[str]):
        self._responses = list(responses)

    async def complete(self, messages, **kwargs: Any) -> str:
        return self._responses.pop(0) if self._responses else '{"action":"say","text":"完成。"}'


class SeqFit:
    """按顺序返回 fit；用于能力发现逐候选打分。"""

    def __init__(self, fits: list[float]):
        self._fits = list(fits)

    async def complete(self, messages, **kwargs: Any) -> str:
        f = self._fits.pop(0) if self._fits else 0.0
        return f'{{"fit":{f}}}'


def _member(market, agent_id, ledger, reply):
    ledger[agent_id] = 0.0
    pea = PersonalEconomicAgent(
        PeaIdentity(agent_id, agent_id, Principal(f"0x{agent_id}")),
        LedgerWallet(agent_id, ledger, daily_limit=100000.0),
        Policy(max_per_tx=100000.0, daily_limit=100000.0),
    )
    return MarketPeaHarness(pea, ScriptedChat([f'{{"action":"say","text":"{reply}"}}']), market)


# ── LLM 拆解 ───────────────────────────────────────────────────────────────
async def test_decomposer_llm_and_fallback():
    d = LLMTaskDecomposer(ScriptedChat(['{"subtasks":["做VI","写文案","拍短片"]}']))
    assert await d.decompose("品牌全案") == ["做VI", "写文案", "拍短片"]
    d2 = LLMTaskDecomposer(None)
    assert await d2.decompose("品牌全案") == ["品牌全案"]   # 无 LLM → 整体单任务


# ── 团队端到端：拆解→组队→联合订单 Shapley 分账 ─────────────────────────
async def test_team_project_decompose_assemble_split(tmp_path):
    ledger: dict[str, float] = {"brand_co": 1000.0}
    # 能力发现：每个子任务对每个候选打分（设计/文案两候选）
    # 子任务1"做主视觉"：design 0.9 / copy 0.1；子任务2"写文案"：design 0.1 / copy 0.9
    discovery = CapabilityDiscovery(LLMCapabilityFit(SeqFit([0.9, 0.1, 0.1, 0.9])))
    market = PeaMarket(ledger=ledger, matcher=LLMCapabilityMatcher(None), discovery=discovery)
    qg = LLMQualityGate(None)

    for aid, reply in [("design", "主视觉完成"), ("copy", "文案完成")]:
        h = _member(market, aid, ledger, reply)
        market.make_supplier_runtime(agent_id=aid, handler=PeaA2AHandler(h, quality_gate=qg),
                                     data_dir=str(tmp_path / aid), capabilities=aid)

    decomposer = LLMTaskDecomposer(ScriptedChat(['{"subtasks":["做主视觉","写文案"]}']))
    assessor = LLMContributionAssessor(ScriptedChat(['{"design":0.6,"copy":0.4}']))
    leader = TeamLeaderPea("brand_co", market, decomposer, contribution_assessor=assessor)

    res = await leader.run_project("品牌全案", total_reward=200.0)

    assert res["status"] == "settled"
    assert res["subtasks"] == ["做主视觉", "写文案"]
    assert res["assignments"] == {"design": "做主视觉", "copy": "写文案"}  # 各得其位
    assert abs(ledger["brand_co"] - 800.0) < 1e-9        # 付了 200
    assert abs(ledger["design"] - 120.0) < 1e-9          # 200 * 0.6
    assert abs(ledger["copy"] - 80.0) < 1e-9             # 200 * 0.4


async def test_no_team_when_no_members(tmp_path):
    ledger: dict[str, float] = {"brand_co": 1000.0}
    market = PeaMarket(ledger=ledger, matcher=LLMCapabilityMatcher(None))
    leader = TeamLeaderPea("brand_co", market, LLMTaskDecomposer(None))
    res = await leader.run_project("做点啥", total_reward=100.0)
    assert res["status"] == "no_team"
    assert abs(ledger["brand_co"] - 1000.0) < 1e-9       # 没花钱


# ── products.team 安全导入 ─────────────────────────────────────────────────
def test_team_package_imports_safely():
    import usmsb_sdk.products.team as team
    assert team.TeamLeaderPea is not None
    assert hasattr(team, "TeamLeader")   # 旧 stub 即使坏了也只是 None
