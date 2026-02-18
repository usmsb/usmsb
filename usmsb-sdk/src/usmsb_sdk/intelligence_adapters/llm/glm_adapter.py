"""
GLM-5 LLM Adapter (智谱AI)

Implementation of the ILLMAdapter interface for Zhipu AI's GLM-5 models.
Supports GLM-4, GLM-4-Plus, GLM-4-Air, GLM-4-Flash and other Chinese domestic models.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx

from usmsb_sdk.intelligence_adapters.base import (
    ILLMAdapter,
    IntelligenceSourceConfig,
    IntelligenceSourceStatus,
    IntelligenceSourceType,
)

logger = logging.getLogger(__name__)


class GLMAdapter(ILLMAdapter):
    """
    GLM-5 LLM Adapter (智谱AI).

    Provides integration with Zhipu AI's language models including
    GLM-4, GLM-4-Plus, GLM-4-Air, GLM-4-Flash, and GLM-5 series.

    This adapter supports Chinese domestic LLM with full capabilities:
    - Text generation
    - Intent understanding
    - Reasoning
    - Embeddings
    - Function calling
    """

    DEFAULT_MODEL = "glm-4"
    DEFAULT_EMBEDDING_MODEL = "embedding-3"
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_TEMPERATURE = 0.7
    API_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

    # Model pricing per 1K tokens (RMB)
    MODEL_PRICING = {
        "glm-4": {"input": 0.1, "output": 0.1},
        "glm-4-plus": {"input": 0.05, "output": 0.05},
        "glm-4-air": {"input": 0.001, "output": 0.001},
        "glm-4-airx": {"input": 0.01, "output": 0.01},
        "glm-4-flash": {"input": 0.0001, "output": 0.0001},
        "glm-5": {"input": 0.015, "output": 0.015},
        "glm-5-plus": {"input": 0.02, "output": 0.02},
    }

    def __init__(self, config: Optional[IntelligenceSourceConfig] = None):
        """
        Initialize GLM adapter.

        Args:
            config: Configuration for the adapter. If None, uses environment variables.
        """
        if config is None:
            config = IntelligenceSourceConfig(
                name="glm",
                type=IntelligenceSourceType.LLM,
                api_key=os.getenv("ZHIPU_API_KEY"),
                model=os.getenv("GLM_MODEL", self.DEFAULT_MODEL),
            )

        super().__init__(config)

        self.model = config.model or self.DEFAULT_MODEL
        self.embedding_model = config.extra_params.get("embedding_model", self.DEFAULT_EMBEDDING_MODEL)
        self.max_tokens = config.extra_params.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        self.temperature = config.extra_params.get("temperature", self.DEFAULT_TEMPERATURE)
        self.base_url = config.endpoint or self.API_BASE_URL

        self._client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> bool:
        """Initialize the GLM client."""
        if not self.config.api_key:
            logger.error("Zhipu AI API key not provided")
            self.status = IntelligenceSourceStatus.ERROR
            return False

        try:
            self.status = IntelligenceSourceStatus.INITIALIZING

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.config.timeout,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
            )

            # Test connection
            is_available = await self.is_available()
            if is_available:
                self.status = IntelligenceSourceStatus.READY
                logger.info(f"GLM adapter initialized successfully with model {self.model}")
                return True
            else:
                self.status = IntelligenceSourceStatus.ERROR
                return False

        except Exception as e:
            logger.error(f"Failed to initialize GLM adapter: {e}")
            self.status = IntelligenceSourceStatus.ERROR
            return False

    async def shutdown(self) -> None:
        """Shutdown the GLM client."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self.status = IntelligenceSourceStatus.SHUTDOWN
        logger.info("GLM adapter shutdown complete")

    async def is_available(self) -> bool:
        """Check if GLM API is available."""
        if not self._client:
            return False

        try:
            # Simple test - generate a minimal response
            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 5,
                },
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"GLM API not available: {e}")
            return False

    async def generate_text(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: Input prompt
            context: Additional context
            **kwargs: Additional parameters

        Returns:
            Generated text
        """
        start_time = time.time()

        try:
            self.status = IntelligenceSourceStatus.BUSY

            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                    "temperature": kwargs.get("temperature", self.temperature),
                    "top_p": kwargs.get("top_p", 0.9),
                },
            )
            response.raise_for_status()

            data = response.json()
            result = data["choices"][0]["message"]["content"]
            latency = time.time() - start_time

            usage = data.get("usage", {})
            self._record_request(
                success=True,
                tokens=usage.get("total_tokens", 0),
                cost=self._calculate_cost(usage),
                latency=latency,
            )

            self.status = IntelligenceSourceStatus.READY
            return result

        except Exception as e:
            latency = time.time() - start_time
            self._record_request(success=False, latency=latency)
            self.status = IntelligenceSourceStatus.READY
            logger.error(f"GLM text generation failed: {e}")
            raise

    async def generate_with_system(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Generate text with system and user prompts.

        Args:
            system_prompt: System-level instructions
            user_prompt: User input
            context: Additional context
            **kwargs: Additional parameters

        Returns:
            Generated text
        """
        start_time = time.time()

        try:
            self.status = IntelligenceSourceStatus.BUSY

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Add context messages if provided
            if context and "conversation_history" in context:
                for msg in context["conversation_history"]:
                    messages.insert(-1, msg)

            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": messages,
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                    "temperature": kwargs.get("temperature", self.temperature),
                    "top_p": kwargs.get("top_p", 0.9),
                },
            )
            response.raise_for_status()

            data = response.json()
            result = data["choices"][0]["message"]["content"]
            latency = time.time() - start_time

            usage = data.get("usage", {})
            self._record_request(
                success=True,
                tokens=usage.get("total_tokens", 0),
                cost=self._calculate_cost(usage),
                latency=latency,
            )

            self.status = IntelligenceSourceStatus.READY
            return result

        except Exception as e:
            latency = time.time() - start_time
            self._record_request(success=False, latency=latency)
            self.status = IntelligenceSourceStatus.READY
            logger.error(f"GLM generation with system prompt failed: {e}")
            raise

    async def understand_intent(
        self,
        text: str,
        schema: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Understand intent from text using GLM's Chinese NLU capabilities."""
        start_time = time.time()

        try:
            self.status = IntelligenceSourceStatus.BUSY

            system_prompt = """你是一个意图分析系统。分析用户的文本并提取：
1. 主要意图（用户想要做什么）
2. 提及的实体（人物、地点、事物、时间等）
3. 情感（正面、负面、中性）
4. 紧急程度（低、中、高）

以JSON格式回复，包含键：intent, entities (列表), sentiment, urgency, confidence (0-1)。"""

            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text},
                    ],
                    "max_tokens": kwargs.get("max_tokens", 1000),
                    "temperature": 0.3,
                },
            )
            response.raise_for_status()

            data = response.json()
            result_text = data["choices"][0]["message"]["content"]
            result = json.loads(result_text)

            latency = time.time() - start_time
            usage = data.get("usage", {})
            self._record_request(
                success=True,
                tokens=usage.get("total_tokens", 0),
                latency=latency,
            )

            self.status = IntelligenceSourceStatus.READY
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse intent JSON: {e}")
            return {"intent": "unknown", "entities": [], "error": str(e)}
        except Exception as e:
            latency = time.time() - start_time
            self._record_request(success=False, latency=latency)
            self.status = IntelligenceSourceStatus.READY
            logger.error(f"Intent understanding failed: {e}")
            raise

    async def reason(
        self,
        facts: List[str],
        query: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Perform reasoning over facts using GLM's reasoning capabilities."""
        facts_text = "\n".join([f"- {fact}" for fact in facts])

        prompt = f"""给定以下事实：
{facts_text}

问题：{query}

请逐步推理并给出你的答案。"""

        return await self.generate_text(prompt, context, temperature=0.5, **kwargs)

    async def evaluate(
        self,
        item: Any,
        criteria: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Evaluate an item against criteria."""
        start_time = time.time()

        try:
            self.status = IntelligenceSourceStatus.BUSY

            system_prompt = """你是一个评估系统。根据指定标准评估给定项目。
提供：
1. 0.0到1.0之间的分数
2. 分数的详细理由
3. 发现的优点
4. 发现的缺点
5. 改进建议

以JSON格式回复，包含键：score, reasoning, strengths (列表), weaknesses (列表), suggestions (列表)。"""

            prompt = f"""待评估项目：
{json.dumps(item) if isinstance(item, (dict, list)) else str(item)}

评估标准：{criteria}"""

            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": kwargs.get("max_tokens", 1000),
                    "temperature": 0.3,
                },
            )
            response.raise_for_status()

            data = response.json()
            result_text = data["choices"][0]["message"]["content"]
            result = json.loads(result_text)

            latency = time.time() - start_time
            usage = data.get("usage", {})
            self._record_request(
                success=True,
                tokens=usage.get("total_tokens", 0),
                latency=latency,
            )

            self.status = IntelligenceSourceStatus.READY
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse evaluation JSON: {e}")
            return {"score": 0.5, "reasoning": "Failed to parse evaluation", "error": str(e)}
        except Exception as e:
            latency = time.time() - start_time
            self._record_request(success=False, latency=latency)
            self.status = IntelligenceSourceStatus.READY
            logger.error(f"Evaluation failed: {e}")
            raise

    async def embed(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[float]:
        """Generate embeddings for text."""
        start_time = time.time()

        try:
            self.status = IntelligenceSourceStatus.BUSY

            response = await self._client.post(
                "/embeddings",
                json={
                    "model": kwargs.get("embedding_model", self.embedding_model),
                    "input": text,
                },
            )
            response.raise_for_status()

            data = response.json()
            embedding = data["data"][0]["embedding"]
            latency = time.time() - start_time

            usage = data.get("usage", {})
            self._record_request(
                success=True,
                tokens=usage.get("total_tokens", 0),
                latency=latency,
            )

            self.status = IntelligenceSourceStatus.READY
            return embedding

        except Exception as e:
            latency = time.time() - start_time
            self._record_request(success=False, latency=latency)
            self.status = IntelligenceSourceStatus.READY
            logger.error(f"Embedding generation failed: {e}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Generate text with streaming."""
        try:
            self.status = IntelligenceSourceStatus.BUSY

            async with self._client.stream(
                "POST",
                "/chat/completions",
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                    "temperature": kwargs.get("temperature", self.temperature),
                    "stream": True,
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if data["choices"][0].get("delta", {}).get("content"):
                                yield data["choices"][0]["delta"]["content"]
                        except json.JSONDecodeError:
                            continue

            self.status = IntelligenceSourceStatus.READY

        except Exception as e:
            self.status = IntelligenceSourceStatus.READY
            logger.error(f"Streaming generation failed: {e}")
            raise

    async def function_call(
        self,
        prompt: str,
        functions: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute function calling with GLM models.

        Args:
            prompt: User prompt
            functions: List of function definitions
            context: Additional context
            **kwargs: Additional parameters

        Returns:
            Function call result with name and arguments
        """
        start_time = time.time()

        try:
            self.status = IntelligenceSourceStatus.BUSY

            response = await self._client.post(
                "/chat/completions",
                json={
                    "model": kwargs.get("model", self.model),
                    "messages": [{"role": "user", "content": prompt}],
                    "tools": [{"type": "function", "function": f} for f in functions],
                    "tool_choice": kwargs.get("tool_choice", "auto"),
                },
            )
            response.raise_for_status()

            data = response.json()
            message = data["choices"][0]["message"]

            result = {
                "content": message.get("content"),
                "tool_calls": message.get("tool_calls", []),
            }

            latency = time.time() - start_time
            usage = data.get("usage", {})
            self._record_request(
                success=True,
                tokens=usage.get("total_tokens", 0),
                latency=latency,
            )

            self.status = IntelligenceSourceStatus.READY
            return result

        except Exception as e:
            latency = time.time() - start_time
            self._record_request(success=False, latency=latency)
            self.status = IntelligenceSourceStatus.READY
            logger.error(f"Function calling failed: {e}")
            raise

    def _calculate_cost(self, usage: Dict[str, int]) -> float:
        """Calculate cost based on token usage (in RMB)."""
        if not usage:
            return 0.0

        pricing = self.MODEL_PRICING.get(self.model, {"input": 0.01, "output": 0.01})
        input_cost = (usage.get("prompt_tokens", 0) / 1000) * pricing["input"]
        output_cost = (usage.get("completion_tokens", 0) / 1000) * pricing["output"]

        return input_cost + output_cost
