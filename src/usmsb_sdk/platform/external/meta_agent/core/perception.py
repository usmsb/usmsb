"""
感知服务 (Perception)
基于 USMSB Core - IPerceptionService
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PerceptionService:
    """
    感知服务

    提供感知能力:
    - 文本理解
    - 意图识别
    - 实体提取
    - 情感分析
    """

    def __init__(self, llm_manager):
        self.llm = llm_manager

    async def perceive(
        self, input_data: Any, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        感知输入数据，提取结构化信息

        Args:
            input_data: 输入数据
            context: 上下文

        Returns:
            感知结果
        """
        if isinstance(input_data, str):
            return await self._perceive_text(input_data, context)
        return {"type": "unknown", "data": input_data}

    async def _perceive_text(
        self, text: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """感知文本输入"""
        prompt = f"""分析以下用户输入，提取关键信息:

输入: {text}

请提取:
1. 意图 (intent)
2. 实体 (entities)
3. 情感 (sentiment)
4. 关键信息 (key_info)

以 JSON 格式返回:"""

        result = await self.llm.chat(prompt)

        return {
            "type": "text",
            "original": text,
            "intent": self._extract_intent(result),
            "entities": self._extract_entities(result),
            "sentiment": self._extract_sentiment(result),
            "processed": result,
        }

    def _extract_intent(self, text: str) -> str:
        """提取意图"""
        intents = ["query", "command", "question", "complaint", "suggestion"]
        for intent in intents:
            if intent in text.lower():
                return intent
        return "unknown"

    def _extract_entities(self, text: str) -> list[dict[str, str]]:
        """提取实体"""
        return []

    def _extract_sentiment(self, text: str) -> str:
        """提取情感"""
        positive = ["好", "棒", "赞", "喜欢", "good", "great", "excellent"]
        negative = ["差", "坏", "烂", "糟糕", "bad", "terrible"]

        for word in positive:
            if word in text.lower():
                return "positive"
        for word in negative:
            if word in text.lower():
                return "negative"
        return "neutral"

    async def extract_entities(
        self,
        text: str,
        entity_types: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """从文本中提取实体"""
        return {"entities": [], "types": entity_types or []}

    async def analyze_sentiment(
        self, text: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """分析文本情感"""
        sentiment = self._extract_sentiment(text)
        return {
            "sentiment": sentiment,
            "score": 1.0 if sentiment == "positive" else 0.5 if sentiment == "neutral" else 0.0,
        }
