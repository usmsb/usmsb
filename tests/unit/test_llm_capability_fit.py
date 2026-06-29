"""LLMCapabilityFit 单测（走查升级：关键词匹配→LLM 语义匹配）。"""

from __future__ import annotations

from typing import Any

import pytest

from usmsb_sdk.services.matching.llm_capability_fit import LLMCapabilityFit


class ScriptedChat:
    def __init__(self, reply: str, raises: bool = False):
        self.reply = reply
        self.raises = raises

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        if self.raises:
            raise RuntimeError("llm down")
        return self.reply


async def test_llm_semantic_score_beats_substring():
    # 能力"视觉传达"字面不含"海报"，关键词法会判 0；LLM 语义法应判高分
    fit = LLMCapabilityFit(ScriptedChat('{"fit":0.9,"reason":"视觉传达可做海报"}'))
    score = await fit.score(["视觉传达"], "做一张促销海报")
    assert score == 0.9
    # 对照：关键词回退确实判 0（证明升级的必要性）
    assert LLMCapabilityFit._keyword_fallback(["视觉传达"], "做一张促销海报") == 0.0


async def test_no_llm_uses_keyword_fallback():
    fit = LLMCapabilityFit(None)
    # 关键词回退=cap 是否为 task 子串："海报"∈"做海报"命中，"插画"不命中 → 1/2
    assert await fit.score(["海报", "插画"], "做海报") == 0.5
    assert await fit.score(["视觉传达"], "做海报") == 0.0


async def test_llm_error_falls_back_to_keyword():
    fit = LLMCapabilityFit(ScriptedChat("", raises=True))
    assert await fit.score(["海报"], "做海报需求") == 1.0          # 回退关键词


async def test_interested_threshold():
    fit = LLMCapabilityFit(ScriptedChat('{"fit":0.3}'))
    assert await fit.interested(["x"], "t", threshold=0.2) is True
    assert await fit.interested(["x"], "t", threshold=0.5) is False


async def test_parse_robustness():
    assert LLMCapabilityFit._parse_fit('noise {"fit":0.7} tail') == 0.7
    assert LLMCapabilityFit._parse_fit("not json") == 0.0
    assert LLMCapabilityFit._parse_fit('{"fit":2}') == 1.0       # clamp
    assert LLMCapabilityFit._parse_fit('{"fit":-1}') == 0.0      # clamp
