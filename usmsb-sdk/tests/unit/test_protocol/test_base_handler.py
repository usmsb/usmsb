"""
Unit Tests for Protocol Base Handler

Regression baseline tests for protocol handler base classes.
These tests ensure the core protocol functionality remains stable during refactoring.
"""
import pytest
import asyncio
import time

from usmsb_sdk.platform.external.protocol.base_handler import (
    ExternalAgentStatus,
    ExternalAgentResponse,
    SkillDefinition,
    ProtocolConfig,
    ProtocolMessage,
    ProtocolResponse,
    ConnectionInfo,
)


class TestExternalAgentStatus:
    """Tests for ExternalAgentStatus enum."""

    def test_all_status_values(self):
        """Test all status values are defined."""
        expected = {"online", "offline", "busy", "error"}
        actual = {s.value for s in ExternalAgentStatus}
        assert expected == actual

    def test_status_comparison(self):
        """Test status enum comparison."""
        assert ExternalAgentStatus.ONLINE == ExternalAgentStatus.ONLINE
        assert ExternalAgentStatus.ONLINE != ExternalAgentStatus.OFFLINE


class TestExternalAgentResponse:
    """Tests for ExternalAgentResponse dataclass."""

    def test_response_creation_success(self):
        """Test successful response creation."""
        response = ExternalAgentResponse(
            success=True,
            data={"result": "ok"},
            status=ExternalAgentStatus.ONLINE,
        )
        assert response.success is True
        assert response.data["result"] == "ok"
        assert response.error is None

    def test_response_creation_error(self):
        """Test error response creation."""
        response = ExternalAgentResponse(
            success=False,
            error="Connection failed",
            status=ExternalAgentStatus.ERROR,
        )
        assert response.success is False
        assert response.error == "Connection failed"

    def test_response_defaults(self):
        """Test response default values."""
        response = ExternalAgentResponse(success=True)
        assert response.data is None
        assert response.error is None
        assert response.status == ExternalAgentStatus.ONLINE


class TestSkillDefinition:
    """Tests for SkillDefinition dataclass."""

    def test_skill_definition_creation(self):
        """Test basic skill definition creation."""
        skill = SkillDefinition(
            skill_id="skill-001",
            name="translate",
            description="Translate text between languages",
        )
        assert skill.skill_id == "skill-001"
        assert skill.name == "translate"
        assert skill.description == "Translate text between languages"

    def test_skill_definition_with_schemas(self):
        """Test skill definition with input/output schemas."""
        skill = SkillDefinition(
            skill_id="skill-002",
            name="analyze",
            description="Analyze text sentiment",
            input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"sentiment": {"type": "string"}}},
        )
        assert "text" in skill.input_schema["properties"]
        assert "sentiment" in skill.output_schema["properties"]

    def test_skill_definition_metadata(self):
        """Test skill definition metadata."""
        skill = SkillDefinition(
            skill_id="skill-003",
            name="search",
            description="Search documents",
            metadata={"version": "1.0", "author": "test"},
        )
        assert skill.metadata["version"] == "1.0"


class TestProtocolConfig:
    """Tests for ProtocolConfig dataclass."""

    def test_protocol_config_defaults(self):
        """Test protocol config default values."""
        config = ProtocolConfig()
        assert config.timeout == 60.0
        assert config.retry_count == 3
        assert config.retry_delay == 1.0
        assert config.keep_alive is True
        assert config.keep_alive_interval == 30.0

    def test_protocol_config_custom(self):
        """Test custom protocol configuration."""
        config = ProtocolConfig(
            timeout=120.0,
            retry_count=5,
            max_message_size=20 * 1024 * 1024,
        )
        assert config.timeout == 120.0
        assert config.retry_count == 5
        assert config.max_message_size == 20 * 1024 * 1024

    def test_protocol_config_metadata(self):
        """Test protocol config metadata."""
        config = ProtocolConfig(
            metadata={"custom_key": "custom_value"}
        )
        assert config.metadata["custom_key"] == "custom_value"


class TestProtocolMessage:
    """Tests for ProtocolMessage dataclass."""

    def test_message_creation(self):
        """Test basic message creation."""
        msg = ProtocolMessage(
            message_id="msg-001",
            message_type="request",
            payload={"action": "translate", "text": "hello"},
        )
        assert msg.message_id == "msg-001"
        assert msg.message_type == "request"
        assert msg.payload["action"] == "translate"

    def test_message_timestamp_auto(self):
        """Test message timestamp is auto-generated."""
        before = time.time()
        msg = ProtocolMessage(
            message_id="msg-002",
            message_type="request",
            payload={},
        )
        after = time.time()
        assert before <= msg.timestamp <= after

    def test_message_to_dict(self):
        """Test message serialization."""
        msg = ProtocolMessage(
            message_id="msg-003",
            message_type="response",
            payload={"result": "success"},
            headers={"content-type": "application/json"},
        )
        data = msg.to_dict()
        assert data["message_id"] == "msg-003"
        assert data["message_type"] == "response"
        assert "content-type" in data["headers"]

    def test_message_from_dict(self):
        """Test message deserialization."""
        data = {
            "message_id": "msg-004",
            "message_type": "request",
            "payload": {"query": "test"},
            "timestamp": 1234567890.0,
            "headers": {"authorization": "Bearer token"},
        }
        msg = ProtocolMessage.from_dict(data)
        assert msg.message_id == "msg-004"
        assert msg.payload["query"] == "test"
        assert msg.headers["authorization"] == "Bearer token"

    def test_message_from_dict_defaults(self):
        """Test message deserialization with defaults."""
        data = {"payload": {"key": "value"}}
        msg = ProtocolMessage.from_dict(data)
        assert msg.message_id is not None  # Auto-generated UUID
        assert msg.message_type == "unknown"
        assert msg.headers == {}


class TestProtocolResponse:
    """Tests for ProtocolResponse dataclass."""

    def test_response_creation_success(self):
        """Test successful response creation."""
        response = ProtocolResponse(
            message_id="resp-001",
            request_id="req-001",
            success=True,
            result={"data": "value"},
        )
        assert response.success is True
        assert response.result["data"] == "value"
        assert response.error is None

    def test_response_creation_error(self):
        """Test error response creation."""
        response = ProtocolResponse(
            message_id="resp-002",
            request_id="req-002",
            success=False,
            error="Processing failed",
        )
        assert response.success is False
        assert response.error == "Processing failed"

    def test_response_to_dict(self):
        """Test response serialization."""
        response = ProtocolResponse(
            message_id="resp-003",
            request_id="req-003",
            success=True,
            result={"status": "ok"},
            metadata={"duration_ms": 150},
        )
        data = response.to_dict()
        assert data["message_id"] == "resp-003"
        assert data["request_id"] == "req-003"
        assert data["success"] is True

    def test_response_from_dict(self):
        """Test response deserialization."""
        data = {
            "message_id": "resp-004",
            "request_id": "req-004",
            "success": True,
            "result": {"output": "processed"},
            "error": None,
        }
        response = ProtocolResponse.from_dict(data)
        assert response.message_id == "resp-004"
        assert response.result["output"] == "processed"


class TestConnectionInfo:
    """Tests for ConnectionInfo dataclass."""

    def test_connection_info_creation(self):
        """Test basic connection info creation."""
        info = ConnectionInfo(endpoint="http://localhost:8080")
        assert info.endpoint == "http://localhost:8080"
        assert info.connected is False
        assert info.connected_at is None

    def test_connection_info_statistics(self):
        """Test connection info statistics."""
        info = ConnectionInfo(
            endpoint="http://localhost:8080",
            connected=True,
            bytes_sent=1024,
            bytes_received=2048,
            messages_sent=10,
            messages_received=15,
        )
        assert info.bytes_sent == 1024
        assert info.bytes_received == 2048
        assert info.messages_sent == 10
        assert info.messages_received == 15

    def test_connection_info_errors(self):
        """Test connection info error tracking."""
        info = ConnectionInfo(
            endpoint="http://localhost:8080",
            errors=3,
        )
        assert info.errors == 3

    def test_connection_info_metadata(self):
        """Test connection info metadata."""
        info = ConnectionInfo(
            endpoint="http://localhost:8080",
            metadata={"protocol_version": "1.0"},
        )
        assert info.metadata["protocol_version"] == "1.0"
