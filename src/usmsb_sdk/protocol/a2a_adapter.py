"""
A2A Adapter - Agent 间通信适配器

已废弃，请使用：
- usmsb_sdk.protocol.types.custom_a2a (Custom A2A 类型)

此模块保留用于向后兼容。
"""

import warnings

warnings.warn(
    "usmsb_sdk.protocol.a2a_adapter is deprecated, "
    "use usmsb_sdk.protocol.types.custom_a2a instead",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from new types for backward compatibility
from usmsb_sdk.protocol.types.custom_a2a import (
    CustomTaskStatus as TaskStatus,
    CustomMessageType as A2AMessageType,
    CustomMessage as A2AMessage,
    CustomTask as DelegatedTask,
)
from usmsb_sdk.protocol.types.custom_a2a.models import CustomPart

__all__ = [
    "TaskStatus",
    "A2AMessageType",
    "A2AMessage",
    "DelegatedTask",
    "CustomPart",
]


# ============================================================================
# Original implementation below - kept for backward compatibility
# ============================================================================

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class A2AMessageTypeEnum(Enum):
    """A2A 消息类型"""
    TASK = "task"                  # 任务消息
    QUERY = "query"               # 查询消息
    RESPONSE = "response"         # 响应消息
    ERROR = "error"               # 错误消息
    HEARTBEAT = "heartbeat"       # 心跳消息
    DISCOVERY = "discovery"        # 发现消息
    NEGOTIATION = "negotiation"    # 协商消息


class TaskStatusEnum(Enum):
    """任务状态"""
    PENDING = "pending"           # 待处理
    ACCEPTED = "accepted"         # 已接受
    IN_PROGRESS = "in_progress"    # 进行中
    COMPLETED = "completed"        # 已完成
    FAILED = "failed"             # 失败
    CANCELLED = "cancelled"       # 已取消


@dataclass
class A2AMessageClass:
    """A2A 消息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: A2AMessageTypeEnum = A2AMessageTypeEnum.QUERY
    from_agent: str = ""
    to_agent: str = ""  # 空 = 广播
    subject: str = ""
    payload: dict = field(default_factory=dict)
    reply_to: str = ""  # 回复的消息 ID
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    expires_at: float | None = None
    metadata: dict = field(default_factory=dict)

    def is_broadcast(self) -> bool:
        """是否是广播消息"""
        return self.to_agent == ""

    def is_expired(self) -> bool:
        """是否已过期"""
        if self.expires_at is None:
            return False
        return datetime.now().timestamp() > self.expires_at


@dataclass
class DelegatedTaskClass:
    """委托任务"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""  # 原始任务 ID
    delegator: str = ""  # 委托方
    delegatee: str = ""  # 被委托方
    description: str = ""
    status: TaskStatusEnum = TaskStatusEnum.PENDING
    input_data: dict = field(default_factory=dict)
    output_data: dict | None = None
    error: str | None = None
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    accepted_at: float | None = None
    completed_at: float | None = None
    deadline: float | None = None
    reward: float = 0.0
    currency: str = "USDC"


class A2AAdapter:
    """
    A2A 通信适配器

    使用方式：
    ```python
    adapter = A2AAdapter(agent_id="agent_001")

    # 发送消息
    adapter.send_message(
        to_agent="agent_002",
        subject="Task Request",
        payload={"task": "analysis"}
    )

    # 接收消息
    msg = adapter.receive_message()

    # 委托任务
    task_id = adapter.delegate_task(
        to_agent="agent_002",
        description="数据分析任务",
        input_data={"data": "..."}
    )
    ```

    Args:
        agent_id: Agent ID
        card_registry: AgentCardRegistry 实例
        message_handler: 消息处理器回调函数
    """

    def __init__(
        self,
        agent_id: str,
        card_registry=None,  # AgentCardRegistry
        message_handler: Callable[[A2AMessageClass], None] | None = None
    ):
        self.agent_id = agent_id
        self.card_registry = card_registry
        self.message_handler = message_handler

        # 消息队列
        self._inbox: list[A2AMessageClass] = []
        self._outbox: list[A2AMessageClass] = []

        # 任务存储
        self._tasks: dict[str, DelegatedTaskClass] = {}

        # 消息监听器
        self._listeners: dict[str, Callable] = {}

    def send_message(
        self,
        to_agent: str,
        message_type: A2AMessageTypeEnum,
        subject: str = "",
        payload: dict | None = None,
        reply_to: str = "",
        ttl: int = 3600
    ) -> A2AMessageClass:
        """
        发送消息

        Args:
            to_agent: 接收方 Agent ID
            message_type: 消息类型
            subject: 主题
            payload: 消息内容
            reply_to: 回复的消息 ID
            ttl: 生存时间（秒）

        Returns:
            A2AMessageClass: 发送的消息
        """
        message = A2AMessageClass(
            type=message_type,
            from_agent=self.agent_id,
            to_agent=to_agent,
            subject=subject,
            payload=payload or {},
            reply_to=reply_to,
            expires_at=datetime.now().timestamp() + ttl if ttl > 0 else None
        )

        self._outbox.append(message)

        return message

    def broadcast(
        self,
        message_type: A2AMessageTypeEnum,
        subject: str = "",
        payload: dict | None = None
    ) -> A2AMessageClass:
        """
        广播消息

        Args:
            message_type: 消息类型
            subject: 主题
            payload: 消息内容

        Returns:
            A2AMessageClass: 广播的消息
        """
        message = A2AMessageClass(
            type=message_type,
            from_agent=self.agent_id,
            to_agent="",  # 广播
            subject=subject,
            payload=payload or {}
        )

        self._outbox.append(message)

        return message

    def receive_message(self, timeout: float = 0) -> A2AMessageClass | None:
        """
        接收消息

        Args:
            timeout: 超时时间（秒），0 = 非阻塞

        Returns:
            A2AMessageClass 或 None
        """
        if timeout > 0:
            # 简化的超时处理
            import time
            start = datetime.now().timestamp()
            while datetime.now().timestamp() - start < timeout:
                if self._inbox:
                    return self._inbox.pop(0)
                time.sleep(0.1)
            return None

        if self._inbox:
            return self._inbox.pop(0)
        return None

    def deliver_message(self, message: A2AMessageClass) -> bool:
        """
        投递消息到收件箱（由外部调用）

        Args:
            message: 消息

        Returns:
            bool: 是否投递成功
        """
        # 忽略发给自己的消息
        if message.to_agent == self.agent_id:
            return False

        # 检查过期
        if message.is_expired():
            return False

        self._inbox.append(message)

        # 如果有消息处理器，调用它
        if self.message_handler:
            self.message_handler(message)

        return True

    def get_pending_messages(self) -> list[A2AMessageClass]:
        """获取所有待处理消息"""
        return self._inbox.copy()

    def clear_inbox(self) -> None:
        """清空收件箱"""
        self._inbox.clear()

    def delegate_task(
        self,
        to_agent: str,
        description: str,
        input_data: dict,
        reward: float = 0.0,
        currency: str = "USDC",
        deadline: float | None = None
    ) -> DelegatedTaskClass:
        """
        委托任务

        Args:
            to_agent: 被委托方
            description: 任务描述
            input_data: 输入数据
            reward: 报酬
            currency: 货币类型
            deadline: 截止时间

        Returns:
            DelegatedTaskClass: 委托任务
        """
        task = DelegatedTaskClass(
            task_id=str(uuid.uuid4()),
            delegator=self.agent_id,
            delegatee=to_agent,
            description=description,
            input_data=input_data,
            reward=reward,
            currency=currency,
            deadline=deadline
        )

        self._tasks[task.id] = task

        # 发送任务消息
        self.send_message(
            to_agent=to_agent,
            message_type=A2AMessageTypeEnum.TASK,
            subject=f"Task: {description[:50]}",
            payload={
                "task_id": task.id,
                "description": description,
                "input_data": input_data,
                "reward": reward,
                "currency": currency,
                "deadline": deadline
            }
        )

        return task

    def accept_task(self, task_id: str) -> bool:
        """
        接受任务

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否成功
        """
        if task_id not in self._tasks:
            return False

        task = self._tasks[task_id]
        if task.delegatee != self.agent_id:
            return False

        task.status = TaskStatusEnum.ACCEPTED
        task.accepted_at = datetime.now().timestamp()

        # 发送接受消息
        self.send_message(
            to_agent=task.delegator,
            message_type=A2AMessageTypeEnum.RESPONSE,
            subject="Task Accepted",
            payload={
                "task_id": task_id,
                "status": "accepted"
            }
        )

        return True

    def complete_task(self, task_id: str, output_data: dict) -> bool:
        """
        完成任务

        Args:
            task_id: 任务 ID
            output_data: 输出数据

        Returns:
            bool: 是否成功
        """
        if task_id not in self._tasks:
            return False

        task = self._tasks[task_id]
        task.status = TaskStatusEnum.COMPLETED
        task.output_data = output_data
        task.completed_at = datetime.now().timestamp()

        # 发送完成消息
        self.send_message(
            to_agent=task.delegator,
            message_type=A2AMessageTypeEnum.RESPONSE,
            subject="Task Completed",
            payload={
                "task_id": task_id,
                "status": "completed",
                "output_data": output_data
            }
        )

        return True

    def fail_task(self, task_id: str, error: str) -> bool:
        """
        标记任务失败

        Args:
            task_id: 任务 ID
            error: 错误信息

        Returns:
            bool: 是否成功
        """
        if task_id not in self._tasks:
            return False

        task = self._tasks[task_id]
        task.status = TaskStatusEnum.FAILED
        task.error = error

        # 发送失败消息
        self.send_message(
            to_agent=task.delegator,
            message_type=A2AMessageTypeEnum.ERROR,
            subject="Task Failed",
            payload={
                "task_id": task_id,
                "status": "failed",
                "error": error
            }
        )

        return True

    def get_task(self, task_id: str) -> DelegatedTaskClass | None:
        """获取任务"""
        return self._tasks.get(task_id)

    def get_delegated_tasks(self) -> list[DelegatedTaskClass]:
        """获取我被委托的任务"""
        return [
            task for task in self._tasks.values()
            if task.delegatee == self.agent_id
        ]

    def get_my_delegations(self) -> list[DelegatedTaskClass]:
        """获取我委托出去的任务"""
        return [
            task for task in self._tasks.values()
            if task.delegator == self.agent_id
        ]

    def register_listener(
        self,
        message_type: A2AMessageTypeEnum,
        handler: Callable[[A2AMessageClass], None]
    ) -> None:
        """注册消息监听器"""
        self._listeners[message_type.value] = handler

    def send_heartbeat(self) -> A2AMessageClass:
        """发送心跳"""
        return self.broadcast(
            message_type=A2AMessageTypeEnum.HEARTBEAT,
            subject="Heartbeat",
            payload={"agent_id": self.agent_id}
        )
