"""
OpenAI LLM Adapter

Implementation of the ILLMAdapter interface for OpenAI's GPT models.
Supports GPT-4, GPT-4-turbo, GPT-3.5-turbo and other OpenAI models.
"""

import json
import logging
import os
import time
from typing import Any

try:
    from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from usmsb_sdk.intelligence_adapters.base import (
    ILLMAdapter,
    IntelligenceSourceConfig,
    IntelligenceSourceStatus,
    IntelligenceSourceType,
)

logger = logging.getLogger(__name__)


class OpenAIAdapter(ILLMAdapter):
    """
    OpenAI LLM Adapter.

    Provides integration with OpenAI's language models including
    GPT-4, GPT-4-turbo, and GPT-3.5-turbo.
    """

    DEFAULT_MODEL = "gpt-4-turbo-preview"
    DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_TEMPERATURE = 0.7

    def __init__(self, config: IntelligenceSourceConfig | None = None):
        """
        Initialize OpenAI adapter.

        Args:
            config: Configuration for the adapter. If None, uses environment variables.
        """
        if config is None:
            config = IntelligenceSourceConfig(
                name="openai",
                type=IntelligenceSourceType.LLM,
                api_key=os.getenv("OPENAI_API_KEY"),
                model=os.getenv("OPENAI_MODEL", self.DEFAULT_MODEL),
            )

        super().__init__(config)

        self.model = config.model or self.DEFAULT_MODEL
        self.embedding_model = config.extra_params.get("embedding_model", self.DEFAULT_EMBEDDING_MODEL)
        self.max_tokens = config.extra_params.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        self.temperature = config.extra_params.get("temperature", self.DEFAULT_TEMPERATURE)

        self._client: AsyncOpenAI | None = None

    async def initialize(self) -> bool:
        """Initialize the OpenAI client."""
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI package not installed. Install with: pip install openai")
            self.status = IntelligenceSourceStatus.ERROR
            return False

        if not self.config.api_key:
            logger.error("OpenAI API key not provided")
            self.status = IntelligenceSourceStatus.ERROR
            return False

        try:
            self.status = IntelligenceSourceStatus.INITIALIZING

            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.endpoint,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
            )

            # Test connection
            is_available = await self.is_available()
            if is_available:
                self.status = IntelligenceSourceStatus.READY
                logger.info(f"OpenAI adapter initialized successfully with model {self.model}")
                return True
            else:
                self.status = IntelligenceSourceStatus.ERROR
                return False

        except Exception as e:
            logger.error(f"Failed to initialize OpenAI adapter: {e}")
            self.status = IntelligenceSourceStatus.ERROR
            return False

    async def shutdown(self) -> None:
        """Shutdown the OpenAI client."""
        if self._client:
            await self._client.close()
            self._client = None
        self.status = IntelligenceSourceStatus.SHUTDOWN
        logger.info("OpenAI adapter shutdown complete")

    async def is_available(self) -> bool:
        """Check if OpenAI API is available."""
        if not self._client:
            return False

        try:
            # Simple test - list models (lightweight operation)
            await self._client.models.list()
            return True
        except Exception as e:
            logger.warning(f"OpenAI API not available: {e}")
            return False

    async def generate_text(
        self,
        prompt: str,
        context: dict[str, Any] | None = None,
        **kwargs
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: Input prompt
            context: Additional context (unused for basic generation)
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Generated text
        """
        start_time = time.time()

        try:
            self.status = IntelligenceSourceStatus.BUSY

            response = await self._client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                top_p=kwargs.get("top_p", 1.0),
                frequency_penalty=kwargs.get("frequency_penalty", 0.0),
                presence_penalty=kwargs.get("presence_penalty", 0.0),
            )

            result = response.choices[0].message.content
            latency = time.time() - start_time

            self._record_request(
                success=True,
                tokens=response.usage.total_tokens if response.usage else 0,
                cost=self._calculate_cost(response.usage) if response.usage else 0,
                latency=latency,
            )

            self.status = IntelligenceSourceStatus.READY
            return result

        except Exception as e:
            latency = time.time() - start_time
            self._record_request(success=False, latency=latency)
            self.status = IntelligenceSourceStatus.READY
            logger.error(f"OpenAI text generation failed: {e}")
            raise

    async def generate_with_system(
        self,
        system_prompt: str,
        user_prompt: str,
        context: dict[str, Any] | None = None,
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

            response = await self._client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=messages,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                top_p=kwargs.get("top_p", 1.0),
            )

            result = response.choices[0].message.content
            latency = time.time() - start_time

            self._record_request(
                success=True,
                tokens=response.usage.total_tokens if response.usage else 0,
                cost=self._calculate_cost(response.usage) if response.usage else 0,
                latency=latency,
            )

            self.status = IntelligenceSourceStatus.READY
            return result

        except Exception as e:
            latency = time.time() - start_time
            self._record_request(success=False, latency=latency)
            self.status = IntelligenceSourceStatus.READY
            logger.error(f"OpenAI generation with system prompt failed: {e}")
            raise

    async def understand_intent(
        self,
        text: str,
        schema: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        Understand intent from text.

        Uses structured output to extract intent and entities.
        """
        start_time = time.time()

        try:
            self.status = IntelligenceSourceStatus.BUSY

            system_prompt = """You are an intent analysis system. Analyze the user's text and extract:
1. Primary intent (what the user wants to do)
2. Entities mentioned (people, places, things, times, etc.)
3. Sentiment (positive, negative, neutral)
4. Urgency level (low, medium, high)

Respond in JSON format with keys: intent, entities (list), sentiment, urgency, confidence (0-1)."""

            response = await self._client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                max_tokens=kwargs.get("max_tokens", 1000),
                temperature=0.3,  # Lower temperature for more consistent output
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            latency = time.time() - start_time
            self._record_request(
                success=True,
                tokens=response.usage.total_tokens if response.usage else 0,
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
        facts: list[str],
        query: str,
        context: dict[str, Any] | None = None,
        **kwargs
    ) -> str:
        """
        Perform reasoning over facts.

        Uses chain-of-thought reasoning to answer queries.
        """
        facts_text = "\n".join([f"- {fact}" for fact in facts])

        prompt = f"""Given the following facts:
{facts_text}

Question: {query}

Please reason through this step by step and provide your answer."""

        return await self.generate_text(prompt, context, temperature=0.5, **kwargs)

    async def evaluate(
        self,
        item: Any,
        criteria: str,
        context: dict[str, Any] | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        Evaluate an item against criteria.

        Returns structured evaluation with score and reasoning.
        """
        start_time = time.time()

        try:
            self.status = IntelligenceSourceStatus.BUSY

            system_prompt = """You are an evaluation system. Evaluate the given item against the specified criteria.
Provide:
1. A score from 0.0 to 1.0
2. Detailed reasoning for the score
3. Strengths identified
4. Weaknesses identified
5. Improvement suggestions

Respond in JSON format with keys: score, reasoning, strengths (list), weaknesses (list), suggestions (list)."""

            prompt = f"""Item to evaluate:
{json.dumps(item) if isinstance(item, (dict, list)) else str(item)}

Criteria: {criteria}"""

            response = await self._client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=kwargs.get("max_tokens", 1000),
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            latency = time.time() - start_time
            self._record_request(
                success=True,
                tokens=response.usage.total_tokens if response.usage else 0,
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
        context: dict[str, Any] | None = None,
        **kwargs
    ) -> list[float]:
        """
        Generate embeddings for text.

        Args:
            text: Text to embed
            context: Additional context
            **kwargs: Additional parameters

        Returns:
            Embedding vector
        """
        start_time = time.time()

        try:
            self.status = IntelligenceSourceStatus.BUSY

            response = await self._client.embeddings.create(
                model=kwargs.get("embedding_model", self.embedding_model),
                input=text,
            )

            embedding = response.data[0].embedding
            latency = time.time() - start_time

            self._record_request(
                success=True,
                tokens=response.usage.total_tokens if response.usage else 0,
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
        context: dict[str, Any] | None = None,
        **kwargs
    ):
        """
        Generate text with streaming.

        Yields chunks of generated text.
        """
        try:
            self.status = IntelligenceSourceStatus.BUSY

            stream = await self._client.chat.completions.create(
                model=kwargs.get("model", self.model),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            self.status = IntelligenceSourceStatus.READY

        except Exception as e:
            self.status = IntelligenceSourceStatus.READY
            logger.error(f"Streaming generation failed: {e}")
            raise

    def _calculate_cost(self, usage) -> float:
        """Calculate cost based on token usage."""
        if not usage:
            return 0.0

        # Pricing per 1K tokens (as of 2024, adjust as needed)
        pricing = {
            "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        }

        model_pricing = pricing.get(self.model, {"input": 0.01, "output": 0.03})
        input_cost = (usage.prompt_tokens / 1000) * model_pricing["input"]
        output_cost = (usage.completion_tokens / 1000) * model_pricing["output"]

        return input_cost + output_cost
