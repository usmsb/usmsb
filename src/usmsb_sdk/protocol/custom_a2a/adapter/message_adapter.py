"""
MessageAdapter - 消息适配器

将 A2AEnvelope 适配到 CustomA2AHandler 的消息格式。
"""

import asyncio
import logging
from typing import Callable

from usmsb_sdk.protocol.types.custom_a2a import (
    CustomMessageType,
    CustomMessage,
)
from usmsb_sdk.protocol.types.envelope import A2AEnvelope


logger = logging.getLogger(__name__)


class MessageAdapter:
    """
    消息适配器

    在 A2AEnvelope 和 CustomMessage 之间进行转换。
    """

    def __init__(
        self,
        agent_id: str,
        message_handler: Callable[[A2AEnvelope], None] | None = None,
    ):
        self._agent_id = agent_id
        self._message_handler = message_handler
        self._inbox: list[A2AEnvelope] = []
        self._outbox: list[A2AEnvelope] = []

    def envelope_to_message(self, envelope: A2AEnvelope) -> CustomMessage:
        """将 A2AEnvelope 转换为 CustomMessage"""
        # 转换消息类型
        msg_type_map = {
            "task": CustomMessageType.TASK,
            "query": CustomMessageType.QUERY,
            "response": CustomMessageType.RESPONSE,
            "error": CustomMessageType.ERROR,
            "heartbeat": CustomMessageType.HEARTBEAT,
            "discovery": CustomMessageType.DISCOVERY,
            "negotiation": CustomMessageType.NEGOTIATION,
            "broadcast": CustomMessageType.BROADCAST,
        }

        return CustomMessage(
            id=envelope.correlation_id or envelope.message_type,
            type=msg_type_map.get(envelope.message_type, CustomMessageType.QUERY),
            from_agent=envelope.sender_id,
            to_agent=envelope.receiver_id,
            subject="",
            payload=envelope.payload,
            reply_to="",
            timestamp=envelope.timestamp,
            expires_at=envelope.timestamp + envelope.ttl if envelope.ttl else None,
            metadata=envelope.metadata,
        )

    def message_to_envelope(self, message: CustomMessage) -> A2AEnvelope:
        """将 CustomMessage 转换为 A2AEnvelope"""
        return A2AEnvelope(
            sender_id=message.from_agent,
            receiver_id=message.to_agent,
            message_type=message.type.value,
            payload=message.payload,
            correlation_id=message.reply_to or message.id,
            timestamp=message.timestamp,
            ttl=int(message.expires_at - message.timestamp) if message.expires_at else 3600,
            metadata=message.metadata,
        )

    async def deliver_envelope(self, envelope: A2AEnvelope) -> bool:
        """
        投递信封到收件箱

        Args:
            envelope: A2AEnvelope

        Returns:
            是否投递成功
        """
        # 忽略发给自己的消息
        if envelope.receiver_id == self._agent_id:
            return False

        # 检查过期
        if envelope.is_expired():
            return False

        self._inbox.append(envelope)

        # 如果有消息处理器，调用它
        if self._message_handler:
            if asyncio.iscoroutinefunction(self._message_handler):
                await self._message_handler(envelope)
            else:
                self._message_handler(envelope)

        return True

    def receive_envelope(self, timeout: float = 0) -> A2AEnvelope | None:
        """
        接收信封

        Args:
            timeout: 超时时间（秒），0 = 非阻塞

        Returns:
            A2AEnvelope 或 None
        """
        if timeout > 0:
            import time
            start = time.time()
            while time.time() - start < timeout:
                if self._inbox:
                    return self._inbox.pop(0)
                time.sleep(0.1)
            return None

        if self._inbox:
            return self._inbox.pop(0)
        return None

    def get_pending_messages(self) -> list[A2AEnvelope]:
        """获取所有待处理消息"""
        return self._inbox.copy()

    def clear_inbox(self) -> None:
        """清空收件箱"""
        self._inbox.clear()

    def send_envelope(self, envelope: A2AEnvelope) -> None:
        """发送信封到发件箱"""
        self._outbox.append(envelope)

    def get_outbox(self) -> list[A2AEnvelope]:
        """获取发件箱"""
        return self._outbox.copy()

    def clear_outbox(self) -> None:
        """清空发件箱"""
        self._outbox.clear()
