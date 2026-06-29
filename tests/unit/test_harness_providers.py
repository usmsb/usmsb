"""harness LLM provider 单测（#1a：给 harness 接真实 LLM）。

覆盖：messages→LLMManager 适配、单/多轮展平、异常 fallback、无 key 降级。
"""

from __future__ import annotations

from typing import Any

import pytest

from usmsb_sdk.harness.providers import LLMChatProvider, make_minimax_provider


class _FakeLLM:
    def __init__(self, reply: str = "ok", raises: bool = False):
        self.reply = reply
        self.raises = raises
        self.last_prompt: str | None = None
        self.last_system: str | None = None

    async def generate(self, prompt: str, system_prompt: str | None = None, **kwargs: Any) -> str:
        if self.raises:
            raise RuntimeError("llm down")
        self.last_prompt = prompt
        self.last_system = system_prompt
        return self.reply


async def test_provider_routes_to_llm_generate():
    llm = _FakeLLM(reply='{"action":"say","text":"hi"}')
    provider = LLMChatProvider(llm)
    out = await provider.complete([
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": "你好"},
    ])
    assert out == '{"action":"say","text":"hi"}'
    assert llm.last_system == "你是助手"
    assert llm.last_prompt == "你好"  # 单条 user 直接给原文


async def test_provider_merges_system_and_flattens_multiturn():
    llm = _FakeLLM()
    provider = LLMChatProvider(llm)
    await provider.complete([
        {"role": "system", "content": "S1"},
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
        {"role": "system", "content": "STATE:{}"},
    ])
    assert "S1" in llm.last_system and "STATE:{}" in llm.last_system  # 多个 system 合并
    assert "用户：u1" in llm.last_prompt and "助手：a1" in llm.last_prompt  # 多轮带角色标签


async def test_provider_fallback_on_exception():
    provider = LLMChatProvider(_FakeLLM(raises=True), fallback="FALLBACK")
    out = await provider.complete([{"role": "user", "content": "x"}])
    assert out == "FALLBACK"


async def test_provider_fallback_on_empty_reply():
    provider = LLMChatProvider(_FakeLLM(reply="   "), fallback="FB")
    out = await provider.complete([{"role": "user", "content": "x"}])
    assert out == "FB"


async def test_make_minimax_provider_degrades_without_key(monkeypatch):
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    provider = await make_minimax_provider(api_key=None, fallback="NOKEY")
    out = await provider.complete([{"role": "user", "content": "hi"}])
    assert out == "NOKEY"  # 无 key → 永远 fallback，不崩
