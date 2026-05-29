"""
A2A Envelope - 统一协议信封

所有 A2A 协议（Google A2A 和 Custom A2A）共用同一个信封格式。
信封负责传输层面的路由，payload 内容由具体协议 handler 解析。
"""

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field


class A2AEnvelope(BaseModel):
    """
    统一 A2A 信封 - 所有协议共用

    设计原则：
    - sender_id / receiver_id: 全局唯一 Agent ID
    - message_type: 消息类型（协议无关）
    - payload: 协议特定内容（Google A2A 或 Custom A2A 格式）
    - correlation_id: 请求-响应关联
    - timestamp / ttl: 时间相关
    - signature: 签名（可选）
    - metadata: 扩展元数据

    Example:
        # Google A2A payload
        envelope = A2AEnvelope(
            sender_id="agent_001",
            receiver_id="agent_002",
            message_type="task",
            payload={
                "method": "tasks/send",
                "params": {...}
            },
            correlation_id="req_123",
        )

        # Custom A2A payload
        envelope = A2AEnvelope(
            sender_id="agent_001",
            receiver_id="",  # 广播
            message_type="discovery",
            payload={
                "capabilities": ["reasoning", "coding"]
            },
        )
    """

    version: str = "1.0"
    sender_id: str = ""
    receiver_id: str = ""
    message_type: str = ""  # task | query | response | error | heartbeat | discovery
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str = ""  # 用于匹配请求和响应
    timestamp: float = Field(default_factory=time.time)
    ttl: int = 3600  # 秒
    signature: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_broadcast(self) -> bool:
        """是否是广播消息"""
        return self.receiver_id == ""

    def is_expired(self) -> bool:
        """是否已过期"""
        if self.ttl <= 0:
            return False
        return time.time() > (self.timestamp + self.ttl)

    def new_response(
        self,
        payload: dict[str, Any],
        error: str | None = None,
    ) -> "A2AEnvelope":
        """
        创建一个响应信封

        Args:
            payload: 响应数据
            error: 错误信息

        Returns:
            A2AEnvelope: 响应信封
        """
        return A2AEnvelope(
            version=self.version,
            sender_id=self.receiver_id,
            receiver_id=self.sender_id,
            message_type="response" if not error else "error",
            payload=payload if not error else {"error": error},
            correlation_id=self.correlation_id,
            timestamp=time.time(),
            ttl=self.ttl,
        )

    def new_delegate_task(
        self,
        delegatee: str,
        task_data: dict[str, Any],
    ) -> "A2AEnvelope":
        """
        创建一个任务委托信封

        Args:
            delegatee: 被委托方 Agent ID
            task_data: 任务数据

        Returns:
            A2AEnvelope: 任务委托信封
        """
        return A2AEnvelope(
            version=self.version,
            sender_id=self.sender_id,
            receiver_id=delegatee,
            message_type="task",
            payload=task_data,
            correlation_id=str(uuid.uuid4()),
            timestamp=time.time(),
            ttl=self.ttl,
        )
