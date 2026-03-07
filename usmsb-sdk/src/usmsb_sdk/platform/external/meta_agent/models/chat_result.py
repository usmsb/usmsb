"""
ChatResult - LLM 调用结果数据结构

设计初衷：
1. 让 _chat_with_llm() 返回完整的状态信息，而不仅仅是文本内容
2. 避免 chat() 方法使用 _parse_tool_calls() 从文本中解析状态（容易误判）
3. 提供明确的标记来区分"已完成"和"需要后台处理"
4. 记录已执行的工具，避免后台任务重复执行

核心问题解决：
- 问题：_chat_with_llm() 内部已经执行了工具，但 chat() 不知道，导致重复执行
- 解决：通过 ChatResult.executed_tools 记录已执行的工具
- 问题：后台任务不知道第一次调用的状态，从头开始执行
- 解决：通过 ChatResult 传递完整状态，后台任务只做"延续/补救"
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ChatResult:
    """
    LLM 调用结果，包含完整状态信息

    设计原则：
    1. 单一来源：状态只由 _chat_with_llm() 确定
    2. 明确标记：通过布尔字段明确区分不同情况
    3. 完整追踪：记录所有执行过的工具和结果
    """

    # === 核心输出 ===
    content: str = ""
    """LLM 生成的最终回复内容"""

    # === 执行追踪 ===
    executed_tools: List[str] = field(default_factory=list)
    """已执行的工具名称列表，用于避免后台任务重复执行"""

    tool_results: List[Dict[str, Any]] = field(default_factory=list)
    """所有工具的执行结果，包含成功和失败的"""

    iterations_used: int = 0
    """使用的迭代次数，用于调试和日志"""

    # === 状态标记 ===
    is_complete: bool = True
    """
    任务是否完成

    True: LLM 已生成有效回复，不需要后续处理
    False: 任务未完成，需要后台继续处理
    """

    needs_background: bool = False
    """
    是否需要后台处理

    True: 需要启动后台任务
    False: 不需要后台任务，直接返回

    与 is_complete 的区别：
    - is_complete=False 且 needs_background=False: 任务失败，无法继续
    - is_complete=False 且 needs_background=True: 任务未完成，需要后台处理
    """

    # === 重试信息 ===
    needs_tool_retry: bool = False
    """
    是否有工具需要重试

    设计初衷：处理工具参数错误导致失败的情况
    场景：API Key 错误、缺少必要参数等
    解决：从历史记录中找到正确参数，修正后重新执行
    """

    retry_info: Optional[Dict[str, Any]] = None
    """
    重试所需信息

    结构：
    {
        "tool_name": "工具名称",
        "param_name": "缺失/错误的参数名",
        "info_type": "参数类型（credential/param/url/other）",
        "description": "需要的参数描述",
        "original_args": "原始参数",
        "error_message": "错误信息"
    }
    """

    # === 继续处理信息 ===
    needs_continuation: bool = False
    """
    是否需要继续处理

    设计初衷：处理 LLM "匆忙结束"的情况
    场景：LLM 返回"正在处理中"但实际上后续没有继续
    解决：传入"继续处理"的提示，让 LLM 完成任务
    """

    continuation_context: Optional[Dict[str, Any]] = None
    """
    继续处理所需的上下文

    结构：
    {
        "last_tool_results": "最后的工具结果",
        "pending_action": "待完成的动作描述"
    }
    """

    # === 错误信息 ===
    error: Optional[str] = None
    """如果发生错误，记录错误信息"""

    error_type: Optional[str] = None
    """错误类型：timeout, rate_limit, api_error, tool_error 等"""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于日志和序列化"""
        return {
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "executed_tools": self.executed_tools,
            "tool_results_count": len(self.tool_results),
            "iterations_used": self.iterations_used,
            "is_complete": self.is_complete,
            "needs_background": self.needs_background,
            "needs_tool_retry": self.needs_tool_retry,
            "needs_continuation": self.needs_continuation,
            "error": self.error,
        }


@dataclass
class ToolRetryInfo:
    """
    工具重试信息

    用于记录需要重试的工具调用详情
    """

    tool_name: str
    """需要重试的工具名称"""

    original_args: Dict[str, Any]
    """原始调用参数"""

    missing_param: Optional[str] = None
    """缺失或错误的参数名"""

    info_type: str = "other"
    """
    参数信息类型

    - credential: 凭证类（API Key、密码、Token）
    - param: 普通参数
    - url: URL 地址
    - other: 其他
    """

    description: str = ""
    """参数描述，用于从历史记录中提取"""

    error_message: str = ""
    """原始错误信息"""

    search_keywords: List[str] = field(default_factory=list)
    """用于搜索历史记录的关键词"""


@dataclass
class BackgroundTaskContext:
    """
    后台任务上下文

    设计初衷：
    后台任务不应该"从头开始"，而是"延续"第一次调用的状态。
    这个数据结构保存了第一次调用的完整上下文，供后台任务使用。
    """

    # 原始请求
    user_message: str
    """用户原始消息"""

    # 已完成的处理
    executed_tools: List[str]
    """已执行的工具列表，后台任务应避免重复执行"""

    tool_results: List[Dict[str, Any]]
    """工具执行结果"""

    # 当前状态
    current_messages: List[Dict[str, str]]
    """当前的对话消息列表"""

    # 处理类型
    task_type: str = "continuation"
    """
    任务类型

    - tool_retry: 工具参数错误，需要修正后重试
    - continuation: LLM 匆忙结束，需要继续处理
    - verification: 需要验证结果是否解决用户问题
    """

    # 重试信息（仅 tool_retry 类型使用）
    retry_info: Optional[ToolRetryInfo] = None

    # 最大重试次数
    max_retries: int = 3
