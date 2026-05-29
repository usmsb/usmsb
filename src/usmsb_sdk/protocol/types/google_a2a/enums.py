"""
Google A2A Enums - 对齐官方 Spec 1.0
"""

from enum import Enum


class TaskState(str, Enum):
    """
    Task 状态机 - 对齐官方 Spec

    完整状态流转：
    submitted → working → completed
                          → failed
                          → canceled
                          → rejected
                          → input-required
                          → auth-required
    """

    UNSPECIFIED = ""
    SUBMITTED = "submitted"  # 任务已提交
    WORKING = "working"  # 任务执行中
    COMPLETED = "completed"  # 任务已完成
    FAILED = "failed"  # 任务失败
    CANCELED = "canceled"  # 任务已取消
    INPUT_REQUIRED = "input-required"  # 需要更多输入
    REJECTED = "rejected"  # 任务被拒绝
    AUTH_REQUIRED = "auth-required"  # 需要认证

    def is_terminal(self) -> bool:
        """是否为终态"""
        return self in (
            TaskState.COMPLETED,
            TaskState.FAILED,
            TaskState.CANCELED,
            TaskState.REJECTED,
        )


class Role(str, Enum):
    """消息角色"""

    UNSPECIFIED = ""
    USER = "user"  # 用户消息
    AGENT = "agent"  # Agent 消息


class MessageType(str, Enum):
    """A2A 消息类型"""

    TASK = "task"
    TASK_RESPONSE = "task_response"
    TASK_STATUS_UPDATE = "task_status_update"
    AGENT_CARD = "agent_card"
    ERROR = "error"
    CANCEL = "cancel"
