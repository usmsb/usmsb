"""
MiniMax LLM Adapter

Implementation of the ILLMAdapter interface for MiniMax M2.5 models.
Uses httpx to call MiniMax API directly with proper Authorization header.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

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
    Uses httpx directly for proper Bearer token authentication.
    """

    DEFAULT_MODEL = "abab6.5s-chat"
    DEFAULT_EMBEDDING_MODEL = "embo-01"
    DEFAULT_MAX_TOKENS = 4096
    DEFAULT_TEMPERATURE = 0.7
    EMBEDDING_BASE_URL = "https://api.minimaxi.com"

    # MiniMax 有两个 API 端点：
    # - Anthropic 兼容: https://api.minimaxi.com/anthropic (工具调用有问题，报错 2013)
    # - OpenAI 兼容: https://api.minimaxi.com/v1 (工具调用正常)
    # 默认使用 OpenAI 兼容端点
    OPENAI_COMPAT_BASE_URL = "https://api.minimaxi.com/v1"

    def __init__(self, config: Optional[IntelligenceSourceConfig] = None):
        """
        Initialize MiniMax adapter.

        Args:
            config: Configuration for the adapter. If None, uses environment variables.

        Note:
            使用 OpenAI 兼容端点 (https://api.minimaxi.com/v1) 而不是 Anthropic 端点，
            因为 Anthropic 端点的工具调用功能存在问题 (错误代码 2013)。
        """
        if config is None:
            config = IntelligenceSourceConfig(
                name="minimax",
                type=IntelligenceSourceType.LLM,
                api_key=os.getenv("MINIMAX_API_KEY"),
                model=os.getenv("MINIMAX_MODEL", self.DEFAULT_MODEL),
                extra_params={
                    "base_url": os.getenv("MINIMAX_BASE_URL", self.OPENAI_COMPAT_BASE_URL),
                },
            )

        super().__init__(config)

        self.model = config.model or self.DEFAULT_MODEL
        self.embedding_model = config.extra_params.get(
            "embedding_model", self.DEFAULT_EMBEDDING_MODEL
        )
        self.max_tokens = config.extra_params.get("max_tokens", self.DEFAULT_MAX_TOKENS)
        self.temperature = config.extra_params.get("temperature", self.DEFAULT_TEMPERATURE)
        self.base_url = config.extra_params.get("base_url", self.OPENAI_COMPAT_BASE_URL)

        self._client: Optional[httpx.AsyncClient] = None
        self._embedding_client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> bool:
        """Initialize the MiniMax client."""
        if not self.config.api_key:
            logger.error("MiniMax API key not provided")
            self.status = IntelligenceSourceStatus.ERROR
            return False

        try:
            # Create httpx client with proper Bearer token authentication
            # MiniMax requires Authorization: Bearer {api_key}
            # 增加超时时间以避免连接断开
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(300.0, connect=30.0),  # 增加到5分钟超时，30秒连接超时
            )

            # Create embedding client for MiniMax embedding API
            self._embedding_client = httpx.AsyncClient(
                base_url=self.EMBEDDING_BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(60.0, connect=10.0),
            )

            self.status = IntelligenceSourceStatus.READY
            logger.info(f"MiniMax adapter initialized with model {self.model} using Bearer auth")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize MiniMax adapter: {e}")
            self.status = IntelligenceSourceStatus.ERROR
            return False

    async def shutdown(self):
        """Shutdown the MiniMax client."""
        if self._client:
            await self._client.aclose()
        if self._embedding_client:
            await self._embedding_client.aclose()
        self._client = None
        self._embedding_client = None
        self.status = IntelligenceSourceStatus.SHUTDOWN
        logger.info("MiniMax adapter shutdown complete")

    async def health_check(self) -> bool:
        """Check if MiniMax API is available."""
        if not self._client:
            return False
        try:
            response = await self._raw_chat_request(
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=1,
            )
            return response is not None
        except Exception as e:
            logger.warning(f"MiniMax API not available: {e}")
            return False

    async def _raw_chat_request(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Make a raw chat request to MiniMax API.

        使用 OpenAI 兼容端点 /v1/text/chatcompletion_v2 进行请求，
        因为 Anthropic 兼容端点的工具调用功能存在问题 (错误代码 2013)。
        """
        if not self._client:
            await self.initialize()

        if not self._client:
            raise RuntimeError("MiniMax client not initialized")

        # 构建 OpenAI 兼容格式的 payload
        payload = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "temperature": temperature if temperature is not None else self.temperature,
            "messages": messages,
        }

        # 添加系统消息（如果有）
        if system:
            # 在 OpenAI 格式中，系统消息放在 messages 数组的开头
            payload["messages"] = [{"role": "system", "content": system}] + messages

        if tools:
            payload["tools"] = tools
            # 打印 payload 中的 tools 结构
            print(f"🔍 [MINIMAX PAYLOAD] tools[0] structure: {json.dumps(tools[0], ensure_ascii=False)[:500]}")
            logger.info(f"MiniMax payload tools[0]: {json.dumps(tools[0], ensure_ascii=False)[:500]}")
            print(f"DEBUG: Sending {len(tools)} tools to MiniMax")
            # Print all tool names
            print("DEBUG: All tool names in minimax_adapter:")
            for i, t in enumerate(tools):
                func = t.get("function", {})
                name = func.get("name", "EMPTY")
                print(f"  Tool {i}: '{name}'")
            logger.info(f"MiniMax API: sending {len(tools)} tools")
            # Detailed check for all tools
            for i, t in enumerate(tools):
                func = t.get("function", {})
                name = func.get("name", "")
                params = func.get("parameters", {})

                if not name:
                    print(f"DEBUG: Tool {i}: EMPTY NAME")
                    logger.info(f"Tool {i}: EMPTY NAME")
                    continue

                if not params:
                    print(f"DEBUG: Tool {i} ({name}): EMPTY parameters")
                    logger.info(f"Tool {i} ({name}): EMPTY parameters")
                    continue

                props = params.get("properties", {})

                # Check for empty properties
                if not props or props == {}:
                    print(f"DEBUG: Tool {i} ({name}): EMPTY properties")
                    logger.info(f"Tool {i} ({name}): EMPTY properties")
                    continue

                for pname, pval in props.items():
                    if pval is None:
                        print(f"DEBUG: Tool {i} ({name}): param {pname} is None")
                        logger.info(f"Tool {i} ({name}): param {pname} is None")

            # Log first tool as sample
            if tools:
                sample = json.dumps(tools[0], ensure_ascii=False)[:300]
                print(f"DEBUG: First tool: {sample}")
                logger.info(f"Sample tool: {sample}")

        max_retries = 3
        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                # 使用 OpenAI 兼容端点
                # 注意：base_url 已经是 https://api.minimaxi.com/v1，所以这里只需要路径 /text/chatcompletion_v2
                response = await self._client.post("/text/chatcompletion_v2", json=payload)

                print(f"🔍 [MINIMAX] status_code: {response.status_code}")
                logger.info(f"MiniMax status_code: {response.status_code}")

                # 先解析响应
                raw_response = response.json()
                print(f"🔍 [MINIMAX RAW] response keys: {raw_response.keys()}")
                print(f"🔍 [MINIMAX RAW] response: {json.dumps(raw_response, ensure_ascii=False)[:500]}")
                logger.info(f"MiniMax raw response: {raw_response}")

                # 检查是否有 API 错误
                base_resp = raw_response.get("base_resp", {})
                if base_resp.get("status_code") != 0:
                    error_msg = base_resp.get("status_msg", "Unknown error")
                    logger.error(f"MiniMax API error: {error_msg}")
                    raise RuntimeError(f"MiniMax API error: {error_msg}")

                return raw_response
            except httpx.ConnectError as e:
                last_error = e
                retry_count += 1
                logger.warning(f"MiniMax connection error (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(2 ** retry_count)  # 指数退避
                    continue
                raise
            except httpx.ReadTimeout as e:
                last_error = e
                retry_count += 1
                logger.warning(f"MiniMax read timeout (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(2 ** retry_count)
                    continue
                raise
            except httpx.HTTPError as e:
                logger.error(f"MiniMax HTTP error: {e}")
                raise

        # 如果所有重试都失败
        if last_error:
            raise last_error

    def _extract_text_from_response(self, response: Dict[str, Any]) -> str:
        """
        Extract text content from MiniMax response.

        支持 OpenAI 格式的响应：
        {"choices": [{"message": {"content": "..."}}]}
        """
        # OpenAI 格式
        choices = response.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            return message.get("content", "") or ""

        # 兼容旧的 Anthropic 格式
        content = response.get("content", [])
        text_parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        return "".join(text_parts)

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
        try:
            max_tokens = kwargs.get("max_tokens", self.max_tokens)
            temperature = kwargs.get("temperature", self.temperature)

            response = await self._raw_chat_request(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            return self._extract_text_from_response(response)
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
        max_retries = 3
        retry_count = 0
        last_error = None

        while retry_count < max_retries:
            try:
                max_tokens = kwargs.get("max_tokens", self.max_tokens)
                temperature = kwargs.get("temperature", self.temperature)

                response = await self._raw_chat_request(
                    messages=[{"role": "user", "content": user_prompt}],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                )

                return self._extract_text_from_response(response)
            except (httpx.ConnectError, httpx.ReadTimeout, ConnectionResetError) as e:
                last_error = e
                retry_count += 1
                logger.warning(f"MiniMax generation error (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(2 ** retry_count)
                    continue
                logger.error(f"MiniMax generation with system prompt failed after {max_retries} retries: {e}")
                raise
            except Exception as e:
                logger.error(f"MiniMax generation with system prompt failed: {e}")
                raise

        if last_error:
            raise last_error

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

            response = await self._raw_chat_request(
                messages=chat_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else None,
            )

            return self._extract_text_from_response(response)
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
        """
        Generate embeddings for text using MiniMax embedding API.

        Args:
            text: Text to embed
            context: Additional context (unused)
            **kwargs: Additional parameters (can override embedding_model)

        Returns:
            Embedding vector
        """
        if not self._embedding_client:
            await self.initialize()

        if not self._embedding_client:
            raise RuntimeError("MiniMax embedding client not initialized")

        model = kwargs.get("embedding_model", self.embedding_model)

        # MiniMax embedding API format - requires "texts" and "type"
        # embed用于查询，用"query"类型
        payload = {
            "model": model,
            "texts": [text],  # MiniMax requires texts as array
            "type": "query",  # Required for query
        }

        try:
            logger.info(
                f"MiniMax embed request: model={model}, texts={payload.get('texts')}, type={payload.get('type')}"
            )
            response = await self._embedding_client.post("/v1/embeddings", json=payload)
            logger.info(f"MiniMax embed response: {response.status_code} - {response.text[:300]}")

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"MiniMax embedding API error: {response.status_code} - {error_text}")
                raise RuntimeError(
                    f"MiniMax embedding API error: {response.status_code} - {error_text}"
                )

            result = response.json()
            logger.debug(f"MiniMax embedding response: {result}")

            # Handle different response formats
            if "vectors" in result:
                # MiniMax native format: {"vectors": [...], "base_resp": {...}}
                vectors = result["vectors"]
                # Check for errors in base_resp
                base_resp = result.get("base_resp", {})
                status_code = base_resp.get("status_code", 0)
                status_msg = base_resp.get("status_msg", "")

                if status_code != 0:
                    logger.error(f"MiniMax embedding API error: {status_code} - {status_msg}")
                    raise RuntimeError(f"MiniMax embedding API error: {status_code} - {status_msg}")

                if isinstance(vectors, list) and len(vectors) > 0:
                    # Each vector is a list of floats
                    embedding = vectors[0] if isinstance(vectors[0], list) else vectors
                else:
                    logger.error(f"Empty vectors in MiniMax response. Full response: {result}")
                    raise ValueError("Empty vectors in MiniMax response")
            elif "data" in result:
                # OpenAI-compatible format
                embedding = result["data"][0]["embedding"]
            elif "embeddings" in result:
                # Alternative format (some MiniMax versions)
                embedding = (
                    result["embeddings"][0]
                    if isinstance(result["embeddings"][0], list)
                    else result["embeddings"][0].get("embedding", result["embeddings"][0])
                )
            elif "vector" in result:
                # Another alternative format
                embedding = result["vector"]
            else:
                logger.error(f"Unexpected MiniMax embedding response format: {result.keys()}")
                raise ValueError(f"Unexpected embedding response format: {list(result.keys())}")

            logger.debug(f"Generated embedding with dimension {len(embedding)}")
            return embedding

        except httpx.HTTPError as e:
            logger.error(f"MiniMax embedding HTTP error: {e}")
            raise

    async def embed_batch(
        self, texts: List[str], context: Optional[Dict[str, Any]] = None, **kwargs
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts using MiniMax embedding API.

        Args:
            texts: List of texts to embed
            context: Additional context (unused)
            **kwargs: Additional parameters (can override embedding_model)

        Returns:
            List of embedding vectors
        """
        if not self._embedding_client:
            await self.initialize()

        if not self._embedding_client:
            raise RuntimeError("MiniMax embedding client not initialized")

        model = kwargs.get("embedding_model", self.embedding_model)

        # MiniMax embedding API format - requires "texts" and "type"
        # embed_batch用于建知识库，用"db"类型
        payload = {
            "model": model,
            "texts": texts,
            "type": "db",
        }

        try:
            response = await self._embedding_client.post("/v1/embeddings", json=payload)

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"MiniMax embedding API error: {response.status_code} - {error_text}")
                raise RuntimeError(
                    f"MiniMax embedding API error: {response.status_code} - {error_text}"
                )

            result = response.json()
            logger.debug(f"MiniMax batch embedding response: {result}")

            # Handle different response formats
            if "vectors" in result:
                # MiniMax native format: {"vectors": [[...], [...]], "base_resp": {...}}
                embeddings = result["vectors"]
            elif "data" in result:
                # OpenAI-compatible format
                # Sort by index to ensure correct order
                embeddings_data = sorted(result["data"], key=lambda x: x.get("index", 0))
                embeddings = [item["embedding"] for item in embeddings_data]
            else:
                logger.error(f"Unexpected MiniMax batch embedding response format: {result.keys()}")
                raise ValueError(
                    f"Unexpected batch embedding response format: {list(result.keys())}"
                )

            logger.debug(
                f"Generated {len(embeddings)} embeddings with dimension {len(embeddings[0]) if embeddings else 0}"
            )
            return embeddings

        except httpx.HTTPError as e:
            logger.error(f"MiniMax batch embedding HTTP error: {e}")
            raise

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
            return {
                "content": "LLM 不可用（未配置 API Key）",
                "tool_calls": [],
                "raw_content_blocks": [],
            }

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
                        # Convert Anthropic format to string for OpenAI endpoint
                        text_parts = []
                        for block in content:
                            if isinstance(block, dict):
                                if block.get("type") == "text":
                                    text_parts.append(block.get("text", ""))
                                elif block.get("type") == "tool_result":
                                    # Include tool result as text
                                    text_parts.append(f"Tool result: {block.get('content', '')}")
                        chat_messages.append({"role": role, "content": " ".join(text_parts)})
                    elif isinstance(content, str):
                        chat_messages.append({"role": role, "content": content})
                    else:
                        chat_messages.append(
                            {"role": role, "content": str(content) if content else ""}
                        )

            if not chat_messages:
                chat_messages = [{"role": "user", "content": "Hello"}]

            response = await self._raw_chat_request(
                messages=chat_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else None,
                tools=tools if tools else None,
            )

            # Parse OpenAI format response
            text_content = ""
            tool_calls = []
            raw_content_blocks = []

            # OpenAI 格式: {"choices": [{"message": {"content": "...", "tool_calls": [...]}}]}
            choices = response.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                text_content = message.get("content", "") or ""

                # Parse tool calls from OpenAI format
                openai_tool_calls = message.get("tool_calls", [])
                for tc in openai_tool_calls:
                    tool_call = {
                        "id": tc.get("id", f"call_{len(tool_calls)}"),
                        "function": {
                            "name": tc.get("function", {}).get("name", ""),
                            "arguments": tc.get("function", {}).get("arguments", {}),
                        },
                    }
                    tool_calls.append(tool_call)
                    raw_content_blocks.append({
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": tc.get("function", {}).get("name", ""),
                        "input": tc.get("function", {}).get("arguments", {}),
                    })

                raw_content_blocks.insert(0, {"type": "text", "text": text_content})

            # Fallback: parse tool calls from text content if not in structured format
            if not tool_calls and text_content:
                tool_calls = self._parse_tool_calls_from_text(text_content)

            # 记录返回值
            print(f"🔍 [MINIMAX] chat_with_tools 返回: content_len={len(text_content)}, tool_calls={len(tool_calls)}")
            if tool_calls:
                print(f"🔍 [MINIMAX] tool_calls详情: {tool_calls}")
            logger.info(f"MiniMax chat_with_tools 返回: content_len={len(text_content)}, tool_calls={len(tool_calls)}, text_content={text_content[:200] if text_content else 'EMPTY'}")

            return {
                "content": text_content,
                "tool_calls": tool_calls,
                "raw_content_blocks": raw_content_blocks,
                "stop_reason": choices[0].get("finish_reason") if choices else None,
            }

        except Exception as e:
            logger.error(f"MiniMax chat with tools failed: {e}")
            return {
                "content": f"LLM 调用失败: {str(e)}",
                "tool_calls": [],
                "raw_content_blocks": [],
                "error": str(e),
            }

    def _parse_tool_calls_from_text(self, text_content: str) -> List[Dict[str, Any]]:
        """Parse tool calls from text content when LLM returns them as text."""
        import re
        import xml.etree.ElementTree as ET

        print(f"🔍 [_parse_tool_calls_from_text] START, text_content={text_content[:300]}")
        tool_calls = []
        try:
            # 方法1: 匹配 [TOOL_CALL] 格式
            pattern = r'\[TOOL_CALL\]\s*\{[^}]*tool\s*=>\s*"([^"]+)"[^}]*args\s*=>\s*(\{[^}]*\})\s*\}\s*\[/TOOL_CALL\]'
            matches = re.findall(pattern, text_content, re.IGNORECASE | re.DOTALL)

            for match in matches:
                tool_name = match[0]
                args_str = match[1]

                # Parse arguments
                try:
                    # Convert JS-style args to JSON
                    args_json = args_str.replace("=>", ":").replace("'", '"')
                    # Handle empty braces
                    if args_json.strip() == "{}":
                        args = {}
                    else:
                        args = json.loads(args_json)
                except json.JSONDecodeError:
                    args = {}

                tool_call = {
                    "id": f"call_{len(tool_calls)}",
                    "function": {
                        "name": tool_name,
                        "arguments": args,
                    },
                }
                tool_calls.append(tool_call)

            # 方法2: 匹配 XML 格式 <invoke name="search_web">...</invoke>
            if not tool_calls:
                try:
                    # 匹配 <invoke name="tool_name">...</invoke>
                    xml_pattern = r'<invoke\s+name="([^"]+)"[^>]*>(.*?)</invoke>'
                    xml_matches = re.findall(xml_pattern, text_content, re.DOTALL)

                    for tool_name, args_text in xml_matches:
                        # 解析参数
                        args = {}
                        # 匹配 <parameter name="key">value</parameter>
                        param_pattern = r'<parameter\s+name="([^"]+)"[^>]*>([^<]*)</parameter>'
                        param_matches = re.findall(param_pattern, args_text)

                        for param_name, param_value in param_matches:
                            args[param_name] = param_value.strip()

                        tool_call = {
                            "id": f"call_{len(tool_calls)}",
                            "function": {
                                "name": tool_name,
                                "arguments": args,
                            },
                        }
                        tool_calls.append(tool_call)

                    if tool_calls:
                        logger.info(f"Parsed {len(tool_calls)} tool calls from XML format")
                except Exception as e:
                    logger.warning(f"Failed to parse XML tool calls: {e}")

            if tool_calls:
                logger.info(f"Parsed {len(tool_calls)} tool calls from text content")

        except Exception as e:
            logger.warning(f"Failed to parse tool calls from text: {e}")

        return tool_calls
