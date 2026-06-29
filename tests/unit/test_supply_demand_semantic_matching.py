"""SupplyDemandMatchingService 关键词搜索语义匹配单测。

走查升级：`any(kw in desc)` 子串匹配 → LLM 语义匹配（复用 LLMCapabilityFit）。
原则：撮合是"判断/智能" → 走 LLM；无 LLM 时回退关键词子串（向后兼容）。
对照 tests/unit/test_llm_capability_fit.py 的写法。
"""

from __future__ import annotations

from typing import Any

from usmsb_sdk.services.supply_demand_matching_service import (
    DemandListing,
    SupplyDemandMatchingService,
    SupplyListing,
)


class SemanticChat:
    """按【任务】（description）语义返回 fit：设计/视觉/海报类高分，其余 0。

    只看 "任务：" 段、忽略 "能力清单：" 段，避免被 keywords 字面污染判断。
    """

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        user = messages[-1]["content"]
        task = user.split("能力清单：")[0]  # 只看任务（description）部分
        if any(k in task for k in ("设计", "视觉", "海报")):
            return '{"fit":0.9,"reason":"视觉/设计语义命中"}'
        return '{"fit":0.0,"reason":"无关"}'


def _service(chat: Any | None) -> SupplyDemandMatchingService:
    # search_* 仅依赖 listings 与 chat；三个协作服务不参与搜索，传 None 即可。
    return SupplyDemandMatchingService(None, None, None, chat=chat)


def _supply(listing_id: str, description: str) -> SupplyListing:
    return SupplyListing(
        listing_id=listing_id,
        agent_id=f"agent-{listing_id}",
        agent_name=listing_id,
        resource={"description": description},
        price_range={"min": 0, "max": 100},
    )


def _demand(listing_id: str, description: str) -> DemandListing:
    return DemandListing(
        listing_id=listing_id,
        agent_id=f"agent-{listing_id}",
        agent_name=listing_id,
        requirement={"description": description},
        budget={"min": 0, "max": 100},
    )


async def test_supply_search_llm_semantic_beats_substring():
    # keywords"海报"字面不在任一 description 中：子串法会全部漏掉；LLM 命中"设计/视觉"供给
    svc = _service(SemanticChat())
    svc._supply_listings = {
        "design": _supply("design", "专业视觉传达与品牌设计服务"),
        "tax": _supply("tax", "代理记账报税服务"),
    }
    results = await svc.search_supply_listings(keywords=["海报"])
    assert {r.listing_id for r in results} == {"design"}


async def test_supply_search_no_llm_falls_back_to_substring():
    # 无 LLM → 关键词子串（向后兼容）：'设计'∈design 命中；'海报'谁都不含 → 空
    svc = _service(None)
    svc._supply_listings = {
        "design": _supply("design", "专业视觉传达与品牌设计服务"),
        "tax": _supply("tax", "代理记账报税服务"),
    }
    assert {r.listing_id for r in await svc.search_supply_listings(keywords=["设计"])} == {"design"}
    assert await svc.search_supply_listings(keywords=["海报"]) == []


async def test_demand_search_llm_semantic_beats_substring():
    # 供方能力 keywords"视觉传达"字面不在需求描述里：子串法漏掉；LLM 命中"海报"需求
    svc = _service(SemanticChat())
    svc._demand_listings = {
        "poster": _demand("poster", "需要做一张促销海报，要求冲击力强"),
        "report": _demand("report", "需要一份月度财务报表"),
    }
    results = await svc.search_demand_listings(keywords=["视觉传达"])
    assert {r.listing_id for r in results} == {"poster"}


async def test_demand_search_no_llm_falls_back_to_substring():
    # 无 LLM：'海报'∈poster 命中；'视觉传达'非任一子串 → 空（与升级前一致）
    svc = _service(None)
    svc._demand_listings = {
        "poster": _demand("poster", "需要做一张促销海报，要求冲击力强"),
        "report": _demand("report", "需要一份月度财务报表"),
    }
    assert {r.listing_id for r in await svc.search_demand_listings(keywords=["海报"])} == {"poster"}
    assert await svc.search_demand_listings(keywords=["视觉传达"]) == []


async def test_no_keywords_returns_all_active():
    # 不传 keywords → 不触发语义/子串过滤，全量返回（有无 LLM 行为一致）
    svc = _service(SemanticChat())
    svc._supply_listings = {
        "a": _supply("a", "服务A"),
        "b": _supply("b", "服务B"),
    }
    assert len(await svc.search_supply_listings()) == 2
