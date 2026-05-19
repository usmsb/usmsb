# Meta Agent Models
"""
Meta Agent 数据模型

包含：
- ChatResult: LLM 调用结果数据结构
- ToolRetryInfo: 工具重试信息
- BackgroundTaskContext: 后台任务上下文
- TaskRecord: 任务执行记录（v2.1）
- CausalGraph: 因果图（v2.1）
"""

from .chat_result import BackgroundTaskContext, ChatResult, ToolRetryInfo
from .task_record import TaskRecord, TaskFeatures, Outcome, Strategy, StrategyFeatures
from .causal_graph import CausalGraph, CausalEdge, CausalPattern

__all__ = [
    "ChatResult",
    "ToolRetryInfo",
    "BackgroundTaskContext",
    "TaskRecord",
    "TaskFeatures",
    "Outcome",
    "Strategy",
    "StrategyFeatures",
    "CausalGraph",
    "CausalEdge",
    "CausalPattern",
]
