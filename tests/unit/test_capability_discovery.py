"""CapabilityDiscovery 单测（#A：从名录按 LLM语义×声誉 检索；#1：扩到全网目录）。"""

from __future__ import annotations

from typing import Any

import pytest

from usmsb_sdk.economic.agent_directory import (
    CompositeDirectoryProvider,
    RegistryDirectoryProvider,
    StaticDirectoryProvider,
)
from usmsb_sdk.economic.pea_market import CapabilityDiscovery, SupplierInfo
from usmsb_sdk.services.matching.llm_capability_fit import LLMCapabilityFit


class SeqChat:
    """按调用顺序返回 fit 分（search 按供应商顺序逐个打分）。"""

    def __init__(self, fits: list[float]):
        self._fits = list(fits)

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        f = self._fits.pop(0) if self._fits else 0.0
        return f'{{"fit":{f}}}'


def _suppliers():
    return [
        SupplierInfo("design", "海报/视觉设计", reputation=0.6),
        SupplierInfo("copy", "文案写作", reputation=0.9),
        SupplierInfo("legal", "法律合规", reputation=0.5),
    ]


# ── #A 本地名录排序 ────────────────────────────────────────────────────────
async def test_ranks_by_semantic_fit_then_reputation():
    fit = LLMCapabilityFit(SeqChat([0.9, 0.2, 0.0]))   # design / copy / legal
    disc = CapabilityDiscovery(fit)
    ranked = await disc.search("做一张促销海报", _suppliers(), top_k=3)
    assert [r.agent_id for r in ranked] == ["design", "copy"]   # legal fit=0 过滤
    assert ranked[0].fit == 0.9


async def test_best_picks_top():
    fit = LLMCapabilityFit(SeqChat([0.3, 0.95, 0.1]))
    disc = CapabilityDiscovery(fit)
    assert await disc.best("写促销文案", _suppliers()) == "copy"


async def test_reputation_fn_modulates_ranking():
    fit = LLMCapabilityFit(SeqChat([0.8, 0.8]))
    live_rep = {"a": 0.2, "b": 1.0}
    disc = CapabilityDiscovery(fit, reputation_fn=lambda aid: live_rep[aid])
    sup = [SupplierInfo("a", "设计", 0.5), SupplierInfo("b", "设计", 0.5)]
    ranked = await disc.search("做海报", sup, top_k=2)
    assert ranked[0].agent_id == "b" and ranked[0].reputation == 1.0


async def test_no_llm_falls_back_to_keyword_then_reputation():
    disc = CapabilityDiscovery(LLMCapabilityFit(None))
    sup = [SupplierInfo("a", "海报", 0.6), SupplierInfo("b", "财务", 0.9)]
    ranked = await disc.search("做海报", sup, top_k=3)
    assert [r.agent_id for r in ranked] == ["a"]


# ── #1 全网目录（StaticDirectoryProvider）────────────────────────────────
async def test_discover_over_static_directory():
    disc = CapabilityDiscovery(LLMCapabilityFit(SeqChat([0.9, 0.0])))  # law fit=0 → 过滤
    provider = StaticDirectoryProvider([
        SupplierInfo("design", "视觉设计", 0.6),
        SupplierInfo("law", "法律", 0.8),
    ])
    ranked = await disc.discover("做海报", provider, top_k=5)
    assert [r.agent_id for r in ranked] == ["design"]


# ── #1 全网目录（真实 AgentRegistry）─────────────────────────────────────
async def test_discover_over_real_agent_registry():
    from usmsb_sdk.core_services.agent_registry import (
        AgentProfile,
        AgentRegistry,
        AgentStatus,
    )

    reg = AgentRegistry()
    reg.register(AgentProfile(
        id="ag_design", name="设计师Agent", description="平面与海报设计",
        capabilities=["海报设计", "VI"], reputation=0.7, status=AgentStatus.ONLINE,
    ))
    reg.register(AgentProfile(
        id="ag_acct", name="会计Agent", description="财税记账",
        capabilities=["记账", "报税"], reputation=0.9, status=AgentStatus.ONLINE,
    ))

    provider = RegistryDirectoryProvider(reg, online_only=True)
    suppliers = await provider.list_suppliers()
    assert {s.agent_id for s in suppliers} == {"ag_design", "ag_acct"}

    # 语义：设计 fit 高、会计 fit 低 → 检索到设计（即便会计声誉更高）
    disc = CapabilityDiscovery(LLMCapabilityFit(SeqChat([0.85, 0.05])))
    ranked = await disc.discover("我要做一张促销海报", provider, top_k=3)
    assert ranked[0].agent_id == "ag_design"
    assert ranked[0].reputation == 0.7   # 用的是注册表里的真实声誉


# ── #1 多目录合并去重 ─────────────────────────────────────────────────────
async def test_composite_directory_dedups():
    p1 = StaticDirectoryProvider([SupplierInfo("a", "x", 0.5), SupplierInfo("b", "y", 0.6)])
    p2 = StaticDirectoryProvider([SupplierInfo("b", "y2", 0.9), SupplierInfo("c", "z", 0.7)])
    comp = CompositeDirectoryProvider(p1, p2)
    sup = await comp.list_suppliers()
    assert {s.agent_id for s in sup} == {"a", "b", "c"}
    # 去重先到先得：b 用 p1 的描述
    assert next(s for s in sup if s.agent_id == "b").capabilities == "y"
