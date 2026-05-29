"""
Custom A2A Enums - USMSB 私有协议枚举
"""

from enum import Enum


class CustomTaskStatus(str, Enum):
    """
    Custom A2A 任务状态 - 自定义状态机

    状态流转：
    pending → accepted → in_progress → completed
                                       → failed
                                       → canceled
    """

    PENDING = "pending"  # 待处理
    ACCEPTED = "accepted"  # 已接受
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消

    def is_terminal(self) -> bool:
        """是否为终态"""
        return self in (
            CustomTaskStatus.COMPLETED,
            CustomTaskStatus.FAILED,
            CustomTaskStatus.CANCELLED,
        )


class CustomMessageType(str, Enum):
    """
    Custom A2A 消息类型
    """

    TASK = "task"  # 任务消息
    QUERY = "query"  # 查询消息
    RESPONSE = "response"  # 响应消息
    ERROR = "error"  # 错误消息
    HEARTBEAT = "heartbeat"  # 心跳消息
    DISCOVERY = "discovery"  # 发现消息
    NEGOTIATION = "negotiation"  # 协商消息
    BROADCAST = "broadcast"  # 广播消息
