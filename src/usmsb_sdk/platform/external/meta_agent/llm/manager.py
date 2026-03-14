"""
LLM Manager - 多 LLM 支持
"""

import logging

from usmsb_sdk.intelligence_adapters.base import IntelligenceSourceConfig, IntelligenceSourceType
from usmsb_sdk.intelligence_adapters.llm.minimax_adapter import MiniMaxAdapter

logger = logging.getLogger(__name__)


class LLMManager:
    """LLM 管理器，支持多 LLM"""

    def __init__(self, config):
        self.config = config
        self.provider = config.provider
        self.model = config.model
        self._adapter = None

    async def init(self):
        """初始化"""
        if self.provider == "minimax":
            await self._init_minimax()
        logger.info(f"LLM Manager initialized with {self.provider}/{self.model}")

    async def _init_minimax(self):
        """初始化 MiniMax 适配器"""
        if not self.config.api_key:
            raise ValueError("MINIMAX_API_KEY is required. Please set it in .env file.")

        config = IntelligenceSourceConfig(
            name="minimax",
            type=IntelligenceSourceType.LLM,
            api_key=self.config.api_key,
            model=self.model or "MiniMax-M2.5",
            extra_params={
                "base_url": self.config.base_url or "https://api.minimaxi.com/anthropic",
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            },
        )
        self._adapter = MiniMaxAdapter(config)
        await self._adapter.initialize()
        logger.info("MiniMax adapter initialized in LLM Manager")

    async def chat(self, message: str, system_prompt: str | None = None) -> str:
        """聊天"""
        if self.provider == "minimax" and self._adapter:
            return await self._adapter.generate_with_system(
                system_prompt=system_prompt or "你是一个有用的AI助手。",
                user_prompt=message,
            )
        elif self.provider == "openai":
            return await self._chat_openai(message, system_prompt)
        elif self.provider == "claude":
            return await self._chat_claude(message, system_prompt)
        elif self.provider == "local":
            return await self._chat_local(message, system_prompt)
        return "LLM not configured"

    async def _chat_openai(self, message: str, system_prompt: str | None) -> str:
        """OpenAI 聊天"""
        return f"OpenAI response to: {message}"

    async def _chat_claude(self, message: str, system_prompt: str | None) -> str:
        """Claude 聊天"""
        return f"Claude response to: {message}"

    async def _chat_local(self, message: str, system_prompt: str | None) -> str:
        """本地 LLM 聊天"""
        return f"Local LLM response to: {message}"
