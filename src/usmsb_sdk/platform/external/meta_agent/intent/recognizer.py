"""
意图识别器

使用 LLM 智能识别用户意图，替代简单的关键词匹配。
支持多种意图类型，可扩展。
"""

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ..llm.manager import LLMManager

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """意图类型枚举"""

    SIMPLE_CHAT = "simple_chat"           # 简单问候、闲聊
    TOOL_CALL = "tool_call"               # 需要工具调用，执行复杂操作
    INFO_RETRIEVAL = "info_retrieval"     # 请求检索历史信息
    DATA_OPERATION = "data_operation"     # 数据操作（CRUD）
    SYSTEM_OPERATION = "system_operation" # 系统状态查询、健康检查等
    HELP_REQUEST = "help_request"         # 请求帮助信息
    LEARNING_REQUEST = "learning_request" # 请求学习/记住某些信息
    UNKNOWN = "unknown"                   # 未知意图


@dataclass
class Intent:
    """识别出的意图"""

    type: IntentType
    confidence: float
    parameters: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""

    def is_tool_call(self) -> bool:
        """是否需要工具调用"""
        return self.type in (
            IntentType.TOOL_CALL,
            IntentType.DATA_OPERATION,
            IntentType.SYSTEM_OPERATION,
        )

    def needs_background(self) -> bool:
        """是否需要后台执行"""
        return self.type in (
            IntentType.DATA_OPERATION,
            IntentType.SYSTEM_OPERATION,
            IntentType.TOOL_CALL,
        )

    def is_simple(self) -> bool:
        """是否是简单对话"""
        return self.type == IntentType.SIMPLE_CHAT

    def needs_retrieval(self) -> bool:
        """是否需要信息检索"""
        return self.type == IntentType.INFO_RETRIEVAL


@dataclass
class IntentResult:
    """意图识别结果"""

    success: bool
    intent: Intent | None = None
    error: str = ""
    raw_response: str = ""


class IntentRecognizer:
    """
    意图识别器

    使用 LLM 智能识别用户意图，替代硬编码关键词匹配。
    当 LLM 不可用时，降级到基于规则的简单识别。
    """

    def __init__(
        self,
        llm_manager: Optional["LLMManager"] = None,
        use_cache: bool = True,
    ):
        self.llm_manager = llm_manager
        self.use_cache = use_cache
        self._intent_cache: dict[str, Intent] = {}

    async def recognize(self, message: str, context: dict[str, Any] | None = None) -> Intent:
        """
        识别用户消息的意图

        Args:
            message: 用户消息
            context: 可选的上下文信息

        Returns:
                识别出的意图
        """
        if not message or not message.strip():
            return Intent(
                type=IntentType.SIMPLE_CHAT,
                confidence=1.0,
                parameters={},
                reasoning="Empty message",
            )

        # 检查缓存
        cache_key = self._get_cache_key(message)
        if self.use_cache and cache_key in self._intent_cache:
            return self._intent_cache[cache_key]

        # 如果没有 LLM Manager，使用基于规则的简单识别
        if not self.llm_manager:
            return self._rule_based_recognition(message)

        # 使用 LLM 识别意图
        try:
            intent = await self._llm_based_recognition(message, context)
            if self.use_cache:
                self._intent_cache[cache_key] = intent
            return intent
        except Exception as e:
            logger.warning(f"LLM intent recognition failed: {e}, falling back to rule-based")
            return self._rule_based_recognition(message)

    def _get_cache_key(self, message: str) -> str:
        """生成缓存键"""
        return f"intent_{hash(message) % 10000}"

    async def _llm_based_recognition(
        self,
        message: str,
        context: dict[str, Any] | None = None
    ) -> Intent:
        """
        使用 LLM 识别意图

        Args:
            message: 用户消息
            context: 可选的上下文信息

        Returns:
                识别出的意图
        """
        context_str = ""
        if context:
            context_str = f"\n\nAdditional context:\n{json.dumps(context, ensure_ascii=False)}"

        prompt = f"""Analyze the user's message and determine their intent.

User message: {message}
{context_str}

Please classify the intent into one of these categories:
1. simple_chat - Simple greeting, casual conversation, or brief question
2. tool_call - Request to use a tool, execute an action, or perform an operation
3. info_retrieval - Request to retrieve previously provided information (credentials, settings, etc.)
4. data_operation - Request to query, create, update, or delete data
5. system_operation - Request to check system status, monitor, or manage system
6. help_request - Request for help, documentation, or guidance
7. learning_request - Request to learn, remember, or be taught something

Response format (JSON):
{{
    "intent_type": "one of the intent types above",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of why this intent was chosen",
    "parameters": {{
        "tool_hint": "suggested tool name if tool_call",
        "info_type_hint": "type of info to retrieve if info_retrieval",
        "urgency": "low/medium/high"
    }}
}}

Important:
- simple_chat should have high confidence for greetings (hi, hello, 你好, 嗨) and short messages
- If the message contains action words like "search", "query", "execute", "create", it's likely tool_call or data_operation
- If the user asks about previously provided info like "my password", "the api key", it's info_retrieval
- Be generous with confidence scores - above 0.7 is good

Respond only with the JSON object, no other text."""

        try:
            response = await self.llm_manager.chat(prompt)
            return self._parse_llm_response(response)
        except Exception as e:
            logger.error(f"LLM call failed in intent recognition: {e}")
            raise

    def _parse_llm_response(self, response: str) -> Intent:
        """解析 LLM 响应"""
        try:
            # 尝试提取 JSON
            json_match = re.search(r"\{{[\s\S]*\}}", response)
            if json_match:
                data = json.loads(json_match.group())
                intent_type_str = data.get("intent_type", "unknown")
                confidence = float(data.get("confidence", 0.5))
                reasoning = data.get("reasoning", "")
                parameters = data.get("parameters", {})

                # 转换意图类型
                try:
                    intent_type = IntentType(intent_type_str)
                except ValueError:
                    intent_type = IntentType.UNKNOWN

                return Intent(
                    type=intent_type,
                    confidence=confidence,
                    parameters=parameters,
                    reasoning=reasoning,
                )
        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")

        # 解析失败，返回未知意图
        return Intent(
            type=IntentType.UNKNOWN,
            confidence=0.0,
            parameters={},
            reasoning=f"Failed to parse response: {response[:100]}",
        )

    def _rule_based_recognition(self, message: str) -> Intent:
        """
        基于规则的意图识别（降级方案）

        当 LLM 不可用时使用。
        """
        message_lower = message.lower().strip()

        # 简单问候检测
        greetings = ["hi", "hello", "你好", "嗨", "您好", "hey"]
        if any(g in message_lower for g in greetings) and len(message) < 30:
            return Intent(
                type=IntentType.SIMPLE_CHAT,
                confidence=0.9,
                parameters={},
                reasoning="Greeting detected",
            )

        # 帮助请求检测
        help_patterns = ["help", "帮助", "怎么", "如何", "what is", "什么是"]
        if any(p in message_lower for p in help_patterns):
            return Intent(
                type=IntentType.HELP_REQUEST,
                confidence=0.7,
                parameters={},
                reasoning="Help-related keywords detected",
            )

        # 信息检索检测
        retrieval_patterns = ["我的", "之前", "上次", "my password", "the key", "记得", "密码", "token", "api key"]
        if any(p in message_lower for p in retrieval_patterns):
            return Intent(
                type=IntentType.INFO_RETRIEVAL,
                confidence=0.6,
                parameters={},
                reasoning="Retrieval-related keywords detected",
            )

        # 工具调用检测
        tool_patterns = ["搜索", "查找", "执行", "运行", "计算", "获取", "查询", "列出", "读取", "写", "创建", "search", "find", "execute", "run", "query", "create"]
        if any(p in message_lower for p in tool_patterns):
            return Intent(
                type=IntentType.TOOL_CALL,
                confidence=0.6,
                parameters={},
                reasoning="Action-related keywords detected",
            )

        # 默认：简单对话
        return Intent(
            type=IntentType.SIMPLE_CHAT,
            confidence=0.5,
            parameters={},
            reasoning="Default classification",
        )

    def clear_cache(self) -> None:
        """清除意图缓存"""
        self._intent_cache.clear()

    def get_supported_intents(self) -> list[str]:
        """获取支持的意图类型列表"""
        return [intent.value for intent in IntentType]
