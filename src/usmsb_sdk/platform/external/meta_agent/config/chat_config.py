"""
Chat 配置类

将所有硬编码的阈值、限制、关键词等移至配置类，
实现统一配置管理。
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ChatConfig:
    """
    Chat 方法配置类

    集中管理 chat 方法的所有可配置参数，
    避免在代码中硬编码魔法数字和字符串。
    """

    # ========== 上下文限制 ==========
    # 历史消息 token 限制
    max_history_tokens: int = 2000
    # LLM 上下文限制
    max_context_tokens: int = 4000
    # 知识库检索结果数量
    max_knowledge_results: int = 5
    # 历史消息数量限制
    max_history_messages: int = 20

    # ========== 搜索限制 ==========
    # 搜索候选项数量
    search_candidates_limit: int = 30
    # 显示候选数量
    display_candidates_limit: int = 3
    # LLM 候选分析数量
    llm_candidates_limit: int = 20

    # ========== 内容截断 ==========
    # 消息内容截断长度
    content_preview_length: int = 300
    # 候选消息截断长度
    candidate_content_length: int = 200
    # LLM 分析内容长度
    llm_content_length: int = 500

    # ========== 消息长度判断 ==========
    # 简单消息长度阈值
    simple_message_threshold: int = 20

    # ========== 工具调用配置 ==========
    # 最大工具调用迭代次数
    max_tool_iterations: int = 20
    # 工具执行超时时间（秒）
    tool_execution_timeout: int = 300

    # ========== 后台任务配置 ==========
    # 后台任务超时时间（秒）
    background_task_timeout: int = 300
    # 任务跟踪容量
    task_tracker_capacity: int = 100

    # ========== API 配置 ==========
    # 外部 API 调用超时时间（秒）
    api_timeout: int = 5
    # API 重试次数
    api_retry_attempts: int = 3

    # ========== 调试配置 ==========
    # 调试模式
    debug_mode: bool = False
    # 日志级别
    log_level: str = "INFO"

    # ========== 消息模板 ==========
    # 后台任务开始消息
    background_task_start_message: str = "🔄 后台任务开始执行..."
    # 后台任务完成消息模板
    background_task_complete_template: str = "✅ 后台任务完成\n\n{result}"
    # 后台任务错误消息模板
    background_task_error_template: str = "⚠️ 后台任务执行遇到问题\n\n{error}\n\n请查看服务器日志获取详细错误信息。"
    # 后台任务失败消息模板
    background_task_fail_template: str = "❌ 后台任务执行失败\n\n错误: {error}\n\n详情:\n{detail}"
    # 任务提交消息
    task_submitted_message: str = "⏳ 您的请求已提交后台处理，完成后结果将自动保存到会话历史中。请稍后查看历史记录获取结果。"
    # LLM 不可用消息
    llm_unavailable_message: str = "抱歉，我现在无法处理你的请求。请稍后再试。"
    # LLM 超时消息
    llm_timeout_message: str = "抱歉，这个问题需要处理较长时间，请稍后再试。或者你可以尝试简化问题。"
    # 简单消息阈值
    simple_message_threshold: int = 20

    # ========== 意图识别配置 ==========
    # 使用 LLM 进行意图识别
    use_llm_intent_recognition: bool = True
    # 意图识别缓存大小
    intent_cache_size: int = 100

    # ========== 关键词配置（降级时使用） ==========
    # 简单问候关键词
    simple_keywords: list[str] = field(default_factory=lambda: [
        "你好", "hi", "hello", "嗨", "您好", "hey"
    ])
    # 工具相关关键词
    tool_keywords: list[str] = field(default_factory=lambda: [
        "搜索", "查找", "执行", "运行", "计算", "获取", "查询", "列出", "读取", "写", "创建",
        "search", "find", "execute", "run", "query", "create", "get", "list", "read", "write"
    ])

    @classmethod
    def from_env(cls) -> "ChatConfig":
        """从环境变量加载配置"""
        return cls(
            max_history_tokens=int(os.getenv("CHAT_MAX_HISTORY_TOKENS", "2000")),
            max_context_tokens=int(os.getenv("CHAT_MAX_CONTEXT_TOKENS", "4000")),
            max_tool_iterations=int(os.getenv("CHAT_MAX_TOOL_ITERATIONS", "20")),
            tool_execution_timeout=int(os.getenv("CHAT_TOOL_TIMEOUT", "300")),
            debug_mode=os.getenv("CHAT_DEBUG_MODE", "false").lower() == "true",
            log_level=os.getenv("CHAT_LOG_LEVEL", "INFO"),
        )

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> "ChatConfig":
        """从字典加载配置"""
        return cls(
            **{k: v for k, v in config_dict.items() if hasattr(cls, k)}
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "max_history_tokens": self.max_history_tokens,
            "max_context_tokens": self.max_context_tokens,
            "max_knowledge_results": self.max_knowledge_results,
            "max_history_messages": self.max_history_messages,
            "search_candidates_limit": self.search_candidates_limit,
            "display_candidates_limit": self.display_candidates_limit,
            "llm_candidates_limit": self.llm_candidates_limit,
            "content_preview_length": self.content_preview_length,
            "candidate_content_length": self.candidate_content_length,
            "llm_content_length": self.llm_content_length,
            "simple_message_threshold": self.simple_message_threshold,
            "max_tool_iterations": self.max_tool_iterations,
            "tool_execution_timeout": self.tool_execution_timeout,
            "background_task_timeout": self.background_task_timeout,
            "task_tracker_capacity": self.task_tracker_capacity,
            "api_timeout": self.api_timeout,
            "api_retry_attempts": self.api_retry_attempts,
            "debug_mode": self.debug_mode,
            "log_level": self.log_level,
            "use_llm_intent_recognition": self.use_llm_intent_recognition,
            "intent_cache_size": self.intent_cache_size,
        }
