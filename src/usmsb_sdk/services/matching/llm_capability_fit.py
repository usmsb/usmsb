"""LLM 能力匹配度（语义判断"这组能力胜不胜任这个任务"）。

走查升级用：替代 services 里 `any(kw.lower() in desc)` 的关键词子串匹配。
匹配是"判断/智能" → 走 LLM；无 LLM/失败时回退关键词重叠（graceful degradation，
即 LLM-first not LLM-only）。返回 0..1 的匹配度。
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class LLMCapabilityFit:
    """判断一组能力与任务的语义匹配度。"""

    _SYS = (
        "你是 AI 服务市场撮合器。判断【能力清单】是否真的能胜任【任务】（语义理解，"
        "不是字面是否包含某词；例如『视觉传达』能胜任『做海报』）。"
        '严格返回 JSON：{"fit":0到1的小数,"reason":"<简短>"}。完全不相关给 0，完美胜任给 1。'
    )

    def __init__(self, chat: Any | None):
        self.chat = chat  # ChatProvider: async complete(messages) -> str

    async def score(self, capabilities: list[str], task: str) -> float:
        caps = [c for c in (capabilities or []) if c]
        if not caps or not task:
            return 0.0
        if self.chat is None:
            return self._keyword_fallback(caps, task)
        try:
            raw = await self.chat.complete([
                {"role": "system", "content": self._SYS},
                {"role": "user", "content": f"任务：{task}\n能力清单：{', '.join(caps)}"},
            ])
            return self._parse_fit(raw)
        except Exception as e:  # noqa: BLE001
            logger.warning("[capability_fit] LLM 评分失败：%s，回退关键词", e)
            return self._keyword_fallback(caps, task)

    async def interested(self, capabilities: list[str], task: str, threshold: float = 0.2) -> bool:
        return await self.score(capabilities, task) >= threshold

    @staticmethod
    def _parse_fit(raw: str) -> float:
        s = (raw or "").strip()
        st, en = s.find("{"), s.rfind("}")
        if st >= 0 and en > st:
            try:
                obj = json.loads(s[st:en + 1])
                return max(0.0, min(1.0, float(obj.get("fit", 0.0))))
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        return 0.0

    @staticmethod
    def _keyword_fallback(capabilities: list[str], task: str) -> float:
        """无 LLM 时的关键词重叠回退（仅作降级，不是主路径）。"""
        task_lower = task.lower()
        hits = sum(1 for c in capabilities if c.lower() in task_lower)
        return hits / max(len(capabilities), 1)
