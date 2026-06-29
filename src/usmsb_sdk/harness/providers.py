"""Harness 的真实 LLM 接线（把脚本化假 LLM 换成真大脑）。

`LLMChatProvider` 把 harness 的 messages 列表适配到任何具备
`async generate(prompt, system_prompt)` 或 `async chat(message, system_prompt)` 的
LLM 对象（如 meta_agent 的 LLMManager）。

`make_minimax_provider()` 一步构造一个 MiniMax 驱动的 provider，复用 USMSB 现有
MiniMax 配置；无 API Key 时优雅降级（返回 fallback 文案，不抛异常）。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from .base_harness import ChatProvider

logger = logging.getLogger(__name__)

_DEFAULT_FALLBACK = '{"action":"say","text":"（LLM 暂不可用，请稍后再试）"}'


class LLMChatProvider(ChatProvider):
    """把 harness messages 适配到 LLMManager。provider-agnostic。"""

    def __init__(self, llm: Any, *, fallback: str = _DEFAULT_FALLBACK):
        self.llm = llm
        self.fallback = fallback

    async def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        system_prompt = "\n\n".join(
            m.get("content", "") for m in messages if m.get("role") == "system"
        )
        convo = [m for m in messages if m.get("role") in ("user", "assistant")]
        user_prompt = self._flatten(convo)
        try:
            if hasattr(self.llm, "generate"):
                out = await self.llm.generate(
                    prompt=user_prompt, system_prompt=system_prompt, **kwargs
                )
            elif hasattr(self.llm, "chat"):
                out = await self.llm.chat(message=user_prompt, system_prompt=system_prompt)
            else:
                return self.fallback
            return out if isinstance(out, str) and out.strip() else self.fallback
        except Exception as e:  # noqa: BLE001
            logger.warning("[LLMChatProvider] generate failed: %s", e)
            return self.fallback

    @staticmethod
    def _flatten(convo: list[dict[str, str]]) -> str:
        if not convo:
            return "（无对话内容，请按系统指令输出下一步动作）"
        # 单条 user 直接给原文；多轮拼成带角色标签的串
        if len(convo) == 1 and convo[0].get("role") == "user":
            return convo[0].get("content", "")
        lines = []
        for m in convo:
            tag = "用户" if m.get("role") == "user" else "助手"
            lines.append(f"{tag}：{m.get('content', '')}")
        return "\n".join(lines)


@dataclass
class _MiniMaxLLMConfig:
    """LLMManager 所需的最小配置（鸭子类型，按属性读取）。"""

    api_key: str
    model: str = "MiniMax-M2.5"
    base_url: str = "https://api.minimaxi.com/v1"
    provider: str = "minimax"
    temperature: float = 0.6
    max_tokens: int = 2000
    reasoning_split: bool | None = None
    service_tier: str | None = None


async def make_minimax_provider(
    *,
    api_key: str | None = None,
    model: str = "MiniMax-M2.5",
    base_url: str | None = None,
    temperature: float = 0.6,
    max_tokens: int = 2000,
    fallback: str = _DEFAULT_FALLBACK,
) -> LLMChatProvider:
    """构造一个 MiniMax 驱动的 harness ChatProvider。

    api_key 缺省读环境变量 MINIMAX_API_KEY。无 key 时返回一个永远 fallback 的 provider
    （让上层在没有真实大脑时也能跑通流程，不崩）。
    """
    from usmsb_sdk.meta_agent.llm.manager import LLMManager

    key = api_key or os.environ.get("MINIMAX_API_KEY", "")
    if not key:
        logger.warning("[make_minimax_provider] no MINIMAX_API_KEY; returning fallback provider")
        return LLMChatProvider(_NullLLM(), fallback=fallback)

    cfg = _MiniMaxLLMConfig(
        api_key=key,
        model=model,
        base_url=base_url or "https://api.minimaxi.com/v1",
        temperature=temperature,
        max_tokens=max_tokens,
    )
    manager = LLMManager(cfg)
    await manager.init()
    return LLMChatProvider(manager, fallback=fallback)


class _NullLLM:
    """无 key 时的占位 LLM：始终触发 fallback。"""

    async def generate(self, prompt: str, system_prompt: str | None = None, **kwargs: Any) -> str:
        return ""
