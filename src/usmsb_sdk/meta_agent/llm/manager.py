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
                "base_url": self.config.base_url or "https://api.minimaxi.com/v1",
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

    async def generate_with_system(self, system_prompt: str, user_prompt: str) -> str:
        """
        标准接口：system + user prompt → LLM 响应。
        供 GeneCapsuleAdapter 等组件使用，实现 LLM 驱动的体验生成。
        """
        return await self.chat(message=user_prompt, system_prompt=system_prompt)

    def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        同步补全方法（供 PurposeGenerator 等使用）
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            max_tokens: 最大 token 数
            temperature: 温度参数
            **kwargs: 其他参数
            
        Returns:
            str: LLM 响应文本
        """
        import asyncio
        import concurrent.futures
        
        def run_async():
            """在线程中运行异步代码"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.chat(prompt, system_prompt))
            finally:
                loop.close()
        
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async)
                return future.result(timeout=60)
        except Exception as e:
            logger.error(f"[LLMManager] complete() error: {e}")
            return f"LLM error: {str(e)}"

    async def _chat_openai(self, message: str, system_prompt: str | None) -> str:
        """OpenAI 聊天"""
        return f"OpenAI response to: {message}"

    async def _chat_claude(self, message: str, system_prompt: str | None) -> str:
        """Claude 聊天"""
        return f"Claude response to: {message}"

    async def _chat_local(self, message: str, system_prompt: str | None) -> str:
        """本地 LLM 聊天"""
        return f"Local LLM response to: {message}"
