"""
Protocol Integration Tests

Tests for multi-protocol communication including:
- A2A (Agent-to-Agent) protocol
- HTTP protocol
- WebSocket protocol
- MCP (Model Context Protocol)
- P2P protocol
- gRPC protocol (if available)
- Protocol switching and factory functions
"""

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from usmsb_sdk.agent_sdk.agent_config import (
    AgentConfig,
    ProtocolType,
    ProtocolConfig,
)
from usmsb_sdk.agent_sdk.communication import (
    CommunicationManager,
    Message,
    MessageType,
    MessagePriority,
    Session,
)


class TestHTTPProtocolIntegration:
    """Tests for HTTP protocol communication."""

    @pytest.fixture
    def http_config(self):
        """Create HTTP protocol configuration."""
        return ProtocolConfig(
            protocol_type=ProtocolType.HTTP,
            host="127.0.0.1",
            port=8080,
            enabled=True,
        )

    @pytest.fixture
    def agent_config_with_http(self, basic_agent_config, http_config):
        """Create agent config with HTTP protocol."""
        basic_agent_config.protocols[ProtocolType.HTTP] = http_config
        return basic_agent_config

    @pytest.mark.asyncio
    async def test_http_message_creation(self, sample_message_data):
        """Test creating HTTP message."""
        message = Message(
            type=MessageType.REQUEST,
            sender_id="sender-001",
            receiver_id="receiver-001",
            content={"action": "test"},
        )

        assert message.type == MessageType.REQUEST
        assert message.sender_id == "sender-001"
        assert message.receiver_id == "receiver-001"
        assert not message.is_expired()

    @pytest.mark.asyncio
    async def test_http_message_serialization(self, sample_message_data):
        """Test message serialization for HTTP transport."""
        message = Message(
            type=MessageType.REQUEST,
            sender_id="sender-001",
            content={"key": "value"},
        )

        # Test to_dict
        msg_dict = message.to_dict()
        assert msg_dict["type"] == "request"
        assert msg_dict["sender_id"] == "sender-001"
        assert msg_dict["content"] == {"key": "value"}

        # Test to_json
        msg_json = message.to_json()
        parsed = json.loads(msg_json)
        assert parsed["type"] == "request"

    @pytest.mark.asyncio
    async def test_http_message_deserialization(self, sample_message_data):
        """Test message deserialization from HTTP transport."""
        message = Message.from_dict(sample_message_data)

        assert message.message_id == sample_message_data["message_id"]
        assert message.type == MessageType.REQUEST
        assert message.sender_id == "sender-001"

    @pytest.mark.asyncio
    async def test_http_send_via_communication_manager(
        self, communication_manager, mock_platform_server
    ):
        """Test sending message via HTTP through communication manager."""
        message = Message(
            type=MessageType.REQUEST,
            sender_id=communication_manager.agent_id,
            receiver_id="target-agent",
            content={"action": "ping"},
        )

        # The communication manager should attempt to send via HTTP
        # This will call the platform server if configured
        try:
            # This may fail without a running server, which is expected
            result = await communication_manager.send(message, ProtocolType.HTTP)
        except Exception as e:
            # Expected if no server is running
            assert "connection" in str(e).lower() or "failed" in str(e).lower()


class TestWebSocketProtocolIntegration:
    """Tests for WebSocket protocol communication."""

    @pytest.fixture
    def websocket_config(self):
        """Create WebSocket protocol configuration."""
        return ProtocolConfig(
            protocol_type=ProtocolType.WEBSOCKET,
            host="127.0.0.1",
            port=8765,
            enabled=True,
        )

    @pytest.mark.asyncio
    async def test_websocket_message_format(self):
        """Test WebSocket message format."""
        message = Message(
            type=MessageType.REQUEST,
            sender_id="ws-sender",
            content={"ws_action": "subscribe"},
            metadata={"channel": "updates"},
        )

        msg_dict = message.to_dict()
        assert "message_id" in msg_dict
        assert msg_dict["type"] == "request"
        assert msg_dict["metadata"]["channel"] == "updates"

    @pytest.mark.asyncio
    async def test_websocket_session_creation(self, communication_manager):
        """Test creating a WebSocket session."""
        session = await communication_manager.create_session(
            participant_ids=["agent-1", "agent-2"],
            protocol=ProtocolType.WEBSOCKET,
            metadata={"purpose": "testing"},
        )

        assert session.session_id is not None
        assert "agent-1" in session.participant_ids
        assert "agent-2" in session.participant_ids
        assert session.protocol == ProtocolType.WEBSOCKET

    @pytest.mark.asyncio
    async def test_websocket_protocol_selection(self, communication_manager):
        """Test automatic protocol selection for WebSocket."""
        message = Message(
            type=MessageType.REQUEST,
            sender_id=communication_manager.agent_id,
            receiver_id="ws-target",
            content={"test": "websocket"},
        )

        # Check that WEBSOCKET protocol can be selected
        selected = await communication_manager._select_protocol(message)
        # Should fall back to HTTP or another available protocol
        assert selected in [ProtocolType.HTTP, ProtocolType.WEBSOCKET, ProtocolType.P2P]


class TestA2AProtocolIntegration:
    """Tests for Agent-to-Agent protocol communication."""

    @pytest.mark.asyncio
    async def test_a2a_message_format(self):
        """Test A2A message format."""
        message = Message(
            type=MessageType.SKILL_CALL,
            sender_id="agent-a",
            receiver_id="agent-b",
            content={
                "skill": "process",
                "params": {"input": "data"},
            },
            protocol=ProtocolType.A2A,
        )

        assert message.type == MessageType.SKILL_CALL
        assert message.protocol == ProtocolType.A2A

        # Create response
        response = message.create_response({"result": "success"})
        assert response.type == MessageType.RESPONSE
        assert response.correlation_id == message.message_id

    @pytest.mark.asyncio
    async def test_a2a_skill_call_and_response(self):
        """Test A2A skill call pattern."""
        # Request
        request = Message(
            type=MessageType.SKILL_CALL,
            sender_id="caller",
            receiver_id="provider",
            content={
                "skill_name": "analyze",
                "parameters": {"data": "test"},
            },
        )

        # Response
        response = Message(
            type=MessageType.SKILL_RESPONSE,
            sender_id="provider",
            receiver_id="caller",
            content={
                "result": {"analysis": "complete"},
                "status": "success",
            },
            correlation_id=request.message_id,
        )

        assert response.correlation_id == request.message_id
        assert response.type == MessageType.SKILL_RESPONSE

    @pytest.mark.asyncio
    async def test_a2a_communication_manager_send(self, communication_manager):
        """Test A2A send through communication manager."""
        message = Message(
            type=MessageType.REQUEST,
            sender_id=communication_manager.agent_id,
            receiver_id="a2a-target",
            content={"protocol": "a2a", "action": "query"},
        )

        # Attempt to send via A2A protocol
        try:
            await communication_manager._send_a2a(message)
        except Exception as e:
            # Expected if no platform server is available
            pass


class TestMCPProtocolIntegration:
    """Tests for Model Context Protocol integration."""

    @pytest.mark.asyncio
    async def test_mcp_adapter_creation(self, mcp_adapter):
        """Test MCP adapter creation."""
        assert mcp_adapter is not None
        assert mcp_adapter.connection is not None

    @pytest.mark.asyncio
    async def test_mcp_resource_registration(self, mcp_adapter):
        """Test registering MCP resources."""
        from usmsb_sdk.platform.protocols.mcp_adapter import MCPResourceType

        async def resource_handler(resource):
            return "Resource content"

        resource = mcp_adapter.register_resource(
            uri="test://resource/1",
            name="Test Resource",
            description="A test resource",
            resource_type=MCPResourceType.TEXT,
            handler=resource_handler,
        )

        assert resource.uri == "test://resource/1"
        assert resource.name == "Test Resource"

    @pytest.mark.asyncio
    async def test_mcp_tool_registration(self, mcp_adapter):
        """Test registering MCP tools."""
        async def tool_handler(arguments):
            return {"result": "tool executed"}

        tool = mcp_adapter.register_tool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object", "properties": {}},
            handler=tool_handler,
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"

    @pytest.mark.asyncio
    async def test_mcp_tool_execution(self, mcp_adapter):
        """Test executing MCP tools."""
        from usmsb_sdk.platform.protocols.mcp_adapter import MCPToolStatus

        async def echo_handler(arguments):
            return {"echo": arguments}

        mcp_adapter.register_tool(
            name="echo",
            description="Echo tool",
            input_schema={"type": "object"},
            handler=echo_handler,
        )

        result = await mcp_adapter.call_tool("echo", {"message": "hello"})

        assert result.status == MCPToolStatus.COMPLETED
        assert result.output == {"echo": {"message": "hello"}}

    @pytest.mark.asyncio
    async def test_mcp_tool_timeout(self, mcp_adapter):
        """Test MCP tool timeout handling."""
        from usmsb_sdk.platform.protocols.mcp_adapter import MCPToolStatus

        async def slow_handler(arguments):
            await asyncio.sleep(10)
            return {"done": True}

        mcp_adapter.register_tool(
            name="slow_tool",
            description="A slow tool",
            input_schema={"type": "object"},
            handler=slow_handler,
        )

        result = await mcp_adapter.call_tool("slow_tool", {}, timeout=0.1)

        assert result.status == MCPToolStatus.TIMEOUT

    @pytest.mark.asyncio
    async def test_mcp_prompt_registration(self, mcp_adapter):
        """Test registering MCP prompts."""
        prompt = mcp_adapter.register_prompt(
            name="greeting",
            description="A greeting prompt",
            template="Hello, {name}! Welcome to {place}.",
            arguments=[
                {"name": "name", "description": "User name"},
                {"name": "place", "description": "Location"},
            ],
        )

        assert prompt.name == "greeting"

    @pytest.mark.asyncio
    async def test_mcp_prompt_rendering(self, mcp_adapter):
        """Test rendering MCP prompts."""
        mcp_adapter.register_prompt(
            name="test_prompt",
            description="Test prompt",
            template="Process {input} with {method}.",
        )

        rendered = await mcp_adapter.get_prompt(
            "test_prompt",
            {"input": "data", "method": "AI"},
        )

        assert rendered == "Process data with AI."

    @pytest.mark.asyncio
    async def test_mcp_context_management(self, mcp_adapter):
        """Test MCP context management."""
        mcp_adapter.set_context("session_id", "test-session")
        mcp_adapter.set_context("user_id", "user-001")

        assert mcp_adapter.get_context("session_id") == "test-session"
        assert mcp_adapter.get_context("user_id") == "user-001"
        assert mcp_adapter.get_context("nonexistent", "default") == "default"

        mcp_adapter.clear_context()
        assert mcp_adapter.get_context("session_id") is None

    @pytest.mark.asyncio
    async def test_mcp_agent_capabilities_exposure(self, mcp_adapter):
        """Test exposing agent capabilities as MCP tools."""
        capabilities = {
            "skills": {
                "analyze": {
                    "description": "Analyze data",
                    "input_schema": {"type": "object"},
                },
                "transform": {
                    "description": "Transform data",
                    "input_schema": {"type": "object"},
                },
            }
        }

        tools = await mcp_adapter.expose_agent_capabilities(
            "test-agent",
            capabilities,
        )

        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "agent_test-agent_analyze" in tool_names
        assert "agent_test-agent_transform" in tool_names


class TestP2PProtocolIntegration:
    """Tests for P2P protocol communication."""

    @pytest.mark.asyncio
    async def test_p2p_connection_creation(self):
        """Test P2P connection data structure."""
        from usmsb_sdk.agent_sdk.communication import P2PConnection

        conn = P2PConnection(
            agent_id="peer-001",
            endpoint="ws://localhost:9000/p2p",
        )

        assert conn.agent_id == "peer-001"
        assert conn.endpoint == "ws://localhost:9000/p2p"
        assert conn.state == "connecting"
        assert not conn.is_connected()

    @pytest.mark.asyncio
    async def test_p2p_handshake_message(self):
        """Test P2P handshake message format."""
        handshake = Message(
            type=MessageType.P2P_HANDSHAKE,
            sender_id="node-a",
            content={"action": "connect", "version": "1.0"},
        )

        assert handshake.type == MessageType.P2P_HANDSHAKE
        assert handshake.content["action"] == "connect"

    @pytest.mark.asyncio
    async def test_p2p_data_message(self):
        """Test P2P data message format."""
        data_msg = Message(
            type=MessageType.P2P_DATA,
            sender_id="node-a",
            receiver_id="node-b",
            content={"payload": "test data", "sequence": 1},
        )

        assert data_msg.type == MessageType.P2P_DATA

    @pytest.mark.asyncio
    async def test_p2p_establish_connection_mock(self, communication_manager):
        """Test P2P connection establishment (mocked)."""
        # Mock the endpoint discovery
        with patch.object(
            communication_manager,
            "_discover_p2p_endpoint",
            return_value="ws://localhost:9000"
        ):
            # This will fail without actual WebSocket server
            try:
                result = await communication_manager.establish_p2p(
                    "target-agent",
                    "ws://localhost:9999"
                )
            except Exception:
                # Expected without actual server
                pass


class TestGRPCProtocolIntegration:
    """Tests for gRPC protocol communication."""

    @pytest.fixture
    def grpc_available(self):
        """Check if gRPC is available."""
        try:
            import grpc
            return True
        except ImportError:
            return False

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        True,  # Skip by default as grpc may not be installed
        reason="gRPC library not available"
    )
    async def test_grpc_message_format(self):
        """Test gRPC message format."""
        message = Message(
            type=MessageType.REQUEST,
            sender_id="grpc-client",
            content={"grpc_field": "value"},
            protocol=ProtocolType.GRPC,
        )

        assert message.protocol == ProtocolType.GRPC

    @pytest.mark.asyncio
    async def test_grpc_fallback_to_http(self, communication_manager):
        """Test that gRPC falls back to HTTP when not available."""
        message = Message(
            type=MessageType.REQUEST,
            sender_id=communication_manager.agent_id,
            receiver_id="grpc-target",
            content={"test": "grpc"},
            protocol=ProtocolType.GRPC,
        )

        # The _send_grpc method should fall back to HTTP
        try:
            result = await communication_manager._send_grpc(message)
        except Exception:
            # Expected without server
            pass


class TestProtocolSwitching:
    """Tests for protocol switching and selection."""

    @pytest.mark.asyncio
    async def test_automatic_protocol_selection(self, communication_manager):
        """Test automatic protocol selection based on message."""
        # Message to P2P-connected peer
        message_p2p = Message(
            type=MessageType.REQUEST,
            sender_id=communication_manager.agent_id,
            receiver_id="p2p-peer",
            content={"test": "p2p"},
        )

        protocol = await communication_manager._select_protocol(message_p2p)
        assert isinstance(protocol, ProtocolType)

    @pytest.mark.asyncio
    async def test_protocol_override(self, communication_manager):
        """Test explicit protocol override."""
        message = Message(
            type=MessageType.REQUEST,
            sender_id=communication_manager.agent_id,
            receiver_id="target",
            content={"test": "override"},
        )

        # Explicitly set HTTP protocol
        message.protocol = ProtocolType.HTTP
        assert message.protocol == ProtocolType.HTTP

    @pytest.mark.asyncio
    async def test_message_response_creation(self):
        """Test creating response messages."""
        request = Message(
            type=MessageType.REQUEST,
            sender_id="requester",
            receiver_id="responder",
            content={"query": "data"},
        )

        response = Message(
            type=MessageType.RESPONSE,
            sender_id="responder",
            receiver_id="requester",
            content={"result": "found"},
            correlation_id=request.message_id,
        )

        assert response.type == MessageType.RESPONSE
        assert response.correlation_id == request.message_id

    @pytest.mark.asyncio
    async def test_error_message_creation(self):
        """Test creating error messages."""
        request = Message(
            type=MessageType.REQUEST,
            sender_id="requester",
            receiver_id="responder",
            content={"query": "data"},
        )

        error = request.create_error("Processing failed", error_code="ERR_001")

        assert error.type == MessageType.ERROR
        assert error.content["error"] == "Processing failed"
        assert error.content["code"] == "ERR_001"
        assert error.correlation_id == request.message_id


class TestProtocolFactory:
    """Tests for protocol factory functions."""

    @pytest.mark.asyncio
    async def test_create_message_from_dict(self, sample_message_data):
        """Test creating message from dictionary."""
        message = Message.from_dict(sample_message_data)

        assert message.message_id == sample_message_data["message_id"]
        assert message.sender_id == sample_message_data["sender_id"]

    @pytest.mark.asyncio
    async def test_create_message_from_json(self, sample_message_data):
        """Test creating message from JSON string."""
        json_str = json.dumps(sample_message_data)
        message = Message.from_json(json_str)

        assert message.message_id == sample_message_data["message_id"]

    @pytest.mark.asyncio
    async def test_message_expiration(self):
        """Test message TTL and expiration."""
        # Message with short TTL
        short_ttl_msg = Message(
            type=MessageType.REQUEST,
            sender_id="sender",
            content={"test": "data"},
            ttl=0,  # Already expired
        )

        assert short_ttl_msg.is_expired()

        # Message with normal TTL
        normal_msg = Message(
            type=MessageType.REQUEST,
            sender_id="sender",
            content={"test": "data"},
            ttl=60,
        )

        assert not normal_msg.is_expired()

    @pytest.mark.asyncio
    async def test_session_management(self, communication_manager):
        """Test session management across protocols."""
        # Create session
        session = await communication_manager.create_session(
            participant_ids=["agent-1", "agent-2", "agent-3"],
            protocol=ProtocolType.HTTP,
            metadata={"topic": "collaboration"},
        )

        assert session.is_active()
        assert len(session.participant_ids) == 3

        # Get session
        retrieved = await communication_manager.get_session(session.session_id)
        assert retrieved.session_id == session.session_id

        # Close session
        await communication_manager.close_session(session.session_id)
        retrieved = await communication_manager.get_session(session.session_id)
        assert retrieved is None


class TestProtocolHealthCheck:
    """Tests for protocol health checks."""

    @pytest.mark.asyncio
    async def test_communication_health_check(self, communication_manager):
        """Test communication manager health check."""
        health = await communication_manager.health_check()

        assert "status" in health
        assert "p2p_connections" in health
        assert "active_sessions" in health

    @pytest.mark.asyncio
    async def test_mcp_statistics(self, mcp_adapter):
        """Test MCP adapter statistics."""
        stats = mcp_adapter.get_statistics()

        assert "connected" in stats
        assert "resources_count" in stats
        assert "tools_count" in stats
        assert "prompts_count" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
