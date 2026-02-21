"""
MiniMax LLM Adapter

Implementation of the ILLMAdapter interface for MiniMax M2.5 models.
Uses Anthropic SDK to call MiniMax API.
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

try:
    from anthropic import AsyncAnthropic, APIError, RateLimitError

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from usmsb_sdk.intelligence_adapters.base import (
    ILLMAdapter,
    IntelligenceSourceConfig,
    IntelligenceSourceStatus,
    IntelligenceSourceType,
)

logger = logging.getLogger(__name__)


class MiniMaxAdapter(ILLMAdapter):
    """
    MiniMax LLM Adapter.

    Provides integration with MiniMax M2.5 models through Anthropic-compatible API.
    """

    DEFAULT_MODEL = "MiniMax-M2.5"
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_TEMPERATURE = 0.7

    def __init__(self, config: Optional[IntelligenceSourceConfig] = None):
        """
        Initialize MiniMax adapter.

        Args:
            config: Configuration for the adapter. If None, uses environment variables.
        """
        if config is None:
            config = IntelligenceSourceConfig(
                name="minimax",
                type=IntelligenceSourceType.LLM,
                api_key=os.getenv("MINIMAX_API_KEY"),
                model=os.getenv("MINIMAX_MODEL", self.DEFAULT_MODEL),
                extra_params={
                    "base_url": os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic"),
                },
            )

        super().__init__(config)

        self.model = config.model or self.DEFAULT_MODEL
        self.max_tokens = config.extra_params.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        self.temperature = config.extra_params.get("temperature", self.DEFAULT_TEMPERATURE)
        self.base_url = config.extra_params.get("base_url", "https://api.minimaxi.com/anthropic")

        self._client: Optional[AsyncAnthropic] = None

    async def initialize(self) -> bool:
        """Initialize the MiniMax client."""
        if not ANTHROPIC_AVAILABLE:
            logger.error("Anthropic package not installed. Install with: pip install anthropic")
            self.status = IntelligenceSourceStatus.ERROR
            return False

        if not self.config.api_key:
            logger.error("MiniMax API key not provided")
            self.status = IntelligenceSourceStatus.ERROR
            return False

        try:
            self._client = AsyncAnthropic(
                api_key=self.config.api_key,
                base_url=self.base_url,
            )
            self.status = IntelligenceSourceStatus.READY
            logger.info(f"MiniMax adapter initialized with model {self.model}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize MiniMax adapter: {e}")
            self.status = IntelligenceSourceStatus.ERROR
            return False

    async def shutdown(self):
        """Shutdown the MiniMax client."""
        self._client = None
        self.status = IntelligenceSourceStatus.SHUTDOWN
        logger.info("MiniMax adapter shutdown complete")

    async def health_check(self) -> bool:
        """Check if MiniMax API is available."""
        if not self._client:
            return False
        try:
            await self._client.messages.create(
                model=self.model, max_tokens=1, messages=[{"role": "user", "content": "Hi"}]
            )
            return True
        except Exception as e:
            logger.warning(f"MiniMax API not available: {e}")
            return False

    async def generate_text(
        self, prompt: str, context: Optional[Dict[str, Any]] = None, **kwargs
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: Input prompt
            context: Additional context
            **kwargs: Additional generation parameters

        Returns:
            Generated text
        """
        if not self._client:
            await self.initialize()

        try:
            max_tokens = kwargs.get("max_tokens", self.max_tokens)
            temperature = kwargs.get("temperature", self.temperature)

            response = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
                elif hasattr(block, "thinking"):
                    continue
            return str(response.content)
        except RateLimitError as e:
            logger.error(f"MiniMax rate limit exceeded: {e}")
            raise
        except APIError as e:
            logger.error(f"MiniMax API error: {e}")
            raise
        except Exception as e:
            logger.error(f"MiniMax text generation failed: {e}")
            raise

    async def generate_with_system(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """
        Generate text with separate system and user prompts.

        Args:
            system_prompt: System-level instructions
            user_prompt: User input
            context: Additional context
            **kwargs: Additional generation parameters

        Returns:
            Generated text
        """
        if not self._client:
            await self.initialize()

        try:
            max_tokens = kwargs.get("max_tokens", self.max_tokens)
            temperature = kwargs.get("temperature", self.temperature)

            response = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
                elif hasattr(block, "thinking"):
                    continue
            return str(response.content)
        except RateLimitError as e:
            logger.error(f"MiniMax rate limit exceeded: {e}")
            raise
        except APIError as e:
            logger.error(f"MiniMax API error: {e}")
            raise
        except Exception as e:
            logger.error(f"MiniMax generation with system prompt failed: {e}")
            raise

    async def chat_with_messages(
        self,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> str:
        """
        Chat with a list of messages (supports multi-turn conversation).

        Args:
            messages: List of messages with 'role' and 'content' keys.
                     First message with role='system' is used as system prompt.
            **kwargs: Additional generation parameters

        Returns:
            Generated text response
        """
        if not self._client:
            try:
                await self.initialize()
            except Exception:
                pass

        if not self._client:
            return "LLM 不可用（未配置 API Key）"

        try:
            max_tokens = kwargs.get("max_tokens", self.max_tokens)
            temperature = kwargs.get("temperature", self.temperature)

            # Separate system prompt from messages
            system_prompt = ""
            chat_messages = []

            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")

                if role == "system":
                    system_prompt = content
                elif role in ["user", "assistant"]:
                    chat_messages.append({"role": role, "content": content})

            # If no user message, use the last one
            if not chat_messages:
                chat_messages = [{"role": "user", "content": "Hello"}]

            response = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=chat_messages,
            )

            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
                elif hasattr(block, "thinking"):
                    continue
            return str(response.content)
        except RateLimitError as e:
            logger.error(f"MiniMax rate limit exceeded: {e}")
            raise
        except APIError as e:
            logger.error(f"MiniMax API error: {e}")
            raise
        except Exception as e:
            logger.error(f"MiniMax chat with messages failed: {e}")
            raise

    async def understand_intent(
        self,
        text: str,
        schema: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Understand intent from text.

        Args:
            text: Input text
            schema: Expected output schema
            context: Additional context
            **kwargs: Additional parameters

        Returns:
            Parsed intent understanding
        """
        system_prompt = """你是一个意图分析助手。根据用户输入，提取意图和参数。
返回JSON格式，包含intent和parameters字段。"""

        if schema:
            system_prompt += f"\n期望的输出格式: {schema}"

        try:
            result = await self.generate_with_system(
                system_prompt=system_prompt, user_prompt=f"分析以下输入的意图:\n{text}", **kwargs
            )
            return {"intent": "understood", "result": result, "raw": result}
        except Exception as e:
            logger.error(f"MiniMax intent understanding failed: {e}")
            return {"intent": "error", "error": str(e)}

    async def evaluate_quality(
        self, text: str, criteria: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        Evaluate text quality.

        Args:
            text: Text to evaluate
            criteria: Evaluation criteria
            **kwargs: Additional parameters

        Returns:
            Quality evaluation results
        """
        system_prompt = "你是一个质量评估助手。评估给定文本的质量并提供评分和反馈。"

        try:
            result = await self.generate_with_system(
                system_prompt=system_prompt, user_prompt=f"评估以下文本:\n{text}", **kwargs
            )
            return {"quality": "evaluated", "result": result}
        except Exception as e:
            logger.error(f"MiniMax quality evaluation failed: {e}")
            return {"quality": "error", "error": str(e)}

    async def summarize(self, text: str, max_length: Optional[int] = None, **kwargs) -> str:
        """
        Summarize text.

        Args:
            text: Text to summarize
            max_length: Maximum summary length
            **kwargs: Additional parameters

        Returns:
            Summary
        """
        system_prompt = "你是一个摘要助手。将给定文本精简为关键要点。"

        try:
            result = await self.generate_with_system(
                system_prompt=system_prompt, user_prompt=f"摘要以下文本:\n{text}", **kwargs
            )
            return result
        except Exception as e:
            logger.error(f"MiniMax summarization failed: {e}")
            raise

    async def translate(self, text: str, target_language: str = "Chinese", **kwargs) -> str:
        """
        Translate text.

        Args:
            text: Text to translate
            target_language: Target language
            **kwargs: Additional parameters

        Returns:
            Translated text
        """
        system_prompt = f"你是一个翻译助手。将文本翻译成{target_language}。"

        try:
            result = await self.generate_with_system(
                system_prompt=system_prompt, user_prompt=f"翻译以下文本:\n{text}", **kwargs
            )
            return result
        except Exception as e:
            logger.error(f"MiniMax translation failed: {e}")
            raise

    async def is_available(self) -> bool:
        """Check if adapter is available."""
        return await self.health_check()

    async def reason(
        self, facts: List[str], query: str, context: Optional[Dict[str, Any]] = None, **kwargs
    ) -> str:
        """Perform reasoning over facts."""
        system_prompt = "你是一个推理助手。根据给定的事实进行推理并回答问题。"
        facts_text = "\n".join([f"- {fact}" for fact in facts])
        try:
            result = await self.generate_with_system(
                system_prompt=system_prompt,
                user_prompt=f"事实:\n{facts_text}\n\n问题: {query}",
                **kwargs,
            )
            return result
        except Exception as e:
            logger.error(f"MiniMax reasoning failed: {e}")
            raise

    async def evaluate(
        self, item: Any, criteria: str, context: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Dict[str, Any]:
        """Evaluate an item against criteria."""
        system_prompt = "你是一个评估助手。根据标准评估给定的项目。"
        try:
            result = await self.generate_with_system(
                system_prompt=system_prompt,
                user_prompt=f"评估项目:\n{item}\n\n评估标准:\n{criteria}",
                **kwargs,
            )
            return {"evaluation": result, "criteria": criteria, "item": str(item)}
        except Exception as e:
            logger.error(f"MiniMax evaluation failed: {e}")
            return {"error": str(e)}

    async def embed(
        self, text: str, context: Optional[Dict[str, Any]] = None, **kwargs
    ) -> List[float]:
        """Generate embeddings for text."""
        raise NotImplementedError("Embeddings not supported for MiniMax M2.5")

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Chat with tools/skills support.

        Args:
            messages: Message history
            tools: Tools/Skills schemas in Function Calling format

        Returns:
            Dict with 'content', 'tool_calls', and 'raw_content_blocks' for Anthropic format
        """
        if not self._client:
            try:
                await self.initialize()
            except Exception:
                pass

        if not self._client:
            return {"content": "LLM 不可用（未配置 API Key）", "tool_calls": [], "raw_content_blocks": []}

        try:
            max_tokens = kwargs.get("max_tokens", self.max_tokens)
            temperature = kwargs.get("temperature", self.temperature)

            # Separate system prompt and build messages
            system_prompt = ""
            chat_messages = []

            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content")

                if role == "system":
                    if isinstance(content, str):
                        system_prompt = content
                elif role in ["user", "assistant"]:
                    # Support both string content and list content (Anthropic format)
                    if isinstance(content, list):
                        # Already in Anthropic format (list of content blocks)
                        chat_messages.append({"role": role, "content": content})
                    elif isinstance(content, str):
                        chat_messages.append({"role": role, "content": content})
                    else:
                        chat_messages.append({"role": role, "content": str(content) if content else ""})

            if not chat_messages:
                chat_messages = [{"role": "user", "content": "Hello"}]

            # Convert tools to Anthropic format
            anthropic_tools = tools

            response = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=chat_messages,
                tools=anthropic_tools,
            )

            # Parse response
            text_content = ""
            tool_calls = []
            raw_content_blocks = []  # Store raw content blocks for multi-turn conversation

            for block in response.content:
                block_dict = None

                # Handle different block types
                if hasattr(block, "type"):
                    block_type = block.type

                    if block_type == "text" and hasattr(block, "text") and block.text:
                        text_content += block.text
                        block_dict = {"type": "text", "text": block.text}

                    elif block_type == "thinking":
                        # Handle thinking blocks (extended thinking)
                        thinking_text = getattr(block, "thinking", "")
                        block_dict = {"type": "thinking", "thinking": thinking_text}

                    elif block_type == "tool_use":
                        tool_call = {
                            "id": block.id,
                            "function": {
                                "name": block.name,
                                "arguments": block.input,
                            },
                        }
                        tool_calls.append(tool_call)
                        block_dict = {
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }

                    elif block_type == "redacted_thinking":
                        # Handle redacted thinking blocks
                        block_dict = {"type": "redacted_thinking"}

                    else:
                        # Unknown block type, try to serialize
                        try:
                            block_dict = {"type": block_type, "data": str(block)}
                        except:
                            pass

                elif hasattr(block, "text") and block.text:
                    text_content += block.text
                    block_dict = {"type": "text", "text": block.text}

                if block_dict:
                    raw_content_blocks.append(block_dict)

            return {
                "content": text_content,
                "tool_calls": tool_calls,
                "raw_content_blocks": raw_content_blocks,  # For multi-turn conversation
                "stop_reason": getattr(response, "stop_reason", None),
            }

        except Exception as e:
            logger.error(f"MiniMax chat with tools failed: {e}")
            return {"content": f"LLM 调用失败: {str(e)}", "tool_calls": [], "raw_content_blocks": [], "error": str(e)}
