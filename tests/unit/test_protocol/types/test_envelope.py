"""
Tests for A2AEnvelope
"""

import pytest
import time

from usmsb_sdk.protocol.types import A2AEnvelope


class TestA2AEnvelope:
    """Test A2AEnvelope"""

    def test_create_envelope(self):
        """测试创建信封"""
        envelope = A2AEnvelope(
            sender_id="agent-001",
            receiver_id="agent-002",
            message_type="task",
            payload={"data": "test"},
        )

        assert envelope.sender_id == "agent-001"
        assert envelope.receiver_id == "agent-002"
        assert envelope.message_type == "task"
        assert envelope.payload == {"data": "test"}
        assert envelope.version == "1.0"

    def test_is_broadcast(self):
        """测试广播判断"""
        envelope = A2AEnvelope(
            sender_id="agent-001",
            receiver_id="",
            message_type="broadcast",
        )
        assert envelope.is_broadcast() is True

        envelope.receiver_id = "agent-002"
        assert envelope.is_broadcast() is False

    def test_is_expired(self):
        """测试过期判断"""
        envelope = A2AEnvelope(
            sender_id="agent-001",
            receiver_id="agent-002",
            message_type="task",
            ttl=3600,
        )
        assert envelope.is_expired() is False

        # 创建一个已过期的信封
        envelope_expired = A2AEnvelope(
            sender_id="agent-001",
            receiver_id="agent-002",
            message_type="task",
            timestamp=time.time() - 7200,
            ttl=3600,
        )
        assert envelope_expired.is_expired() is True

    def test_serialization(self):
        """测试序列化"""
        envelope = A2AEnvelope(
            sender_id="agent-001",
            receiver_id="agent-002",
            message_type="task",
            payload={"key": "value"},
        )

        data = envelope.model_dump()
        assert data["sender_id"] == "agent-001"
        assert data["payload"] == {"key": "value"}

        # 反序列化
        envelope2 = A2AEnvelope.model_validate(data)
        assert envelope2.sender_id == envelope.sender_id
        assert envelope2.payload == envelope.payload
