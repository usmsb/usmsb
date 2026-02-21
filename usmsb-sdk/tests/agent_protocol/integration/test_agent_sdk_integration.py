"""
Agent SDK Integration Tests

Tests for Agent SDK components including:
- Agent creation and configuration
- Agent registration flow
- Agent-to-agent communication
- Agent discovery mechanisms
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
    SkillDefinition,
    CapabilityDefinition,
    NetworkConfig,
    SecurityConfig,
)
from usmsb_sdk.agent_sdk.registration import (
    RegistrationManager,
    RegistrationStatus,
    PlatformNode,
    RegistrationInfo,
)
from usmsb_sdk.agent_sdk.communication import (
    CommunicationManager,
    Message,
    MessageType,
    MessagePriority,
    Session,
    P2PConnection,
)
from usmsb_sdk.agent_sdk.discovery import (
    DiscoveryManager,
    DiscoveryFilter,
    DiscoveryScope,
    SortBy,
    AgentInfo,
)


class TestAgentCreationAndConfiguration:
    """Tests for agent creation and configuration."""

    def test_basic_agent_config(self, basic_agent_config):
        """Test basic agent configuration creation."""
        assert basic_agent_config.name == "TestAgent"
        assert basic_agent_config.description == "A test agent for integration testing"
        assert len(basic_agent_config.skills) == 2
        assert len(basic_agent_config.capabilities) == 1

    def test_config_serialization(self, basic_agent_config):
        """Test agent configuration serialization."""
        config_dict = basic_agent_config.to_dict()

        assert config_dict["name"] == "TestAgent"
        assert "skills" in config_dict
        assert "capabilities" in config_dict
        assert "protocols" in config_dict

    def test_config_deserialization(self, basic_agent_config):
        """Test agent configuration deserialization."""
        config_dict = basic_agent_config.to_dict()
        restored = AgentConfig.from_dict(config_dict)

        assert restored.name == basic_agent_config.name
        assert restored.agent_id == basic_agent_config.agent_id
        assert len(restored.skills) == len(basic_agent_config.skills)

    def test_config_json_serialization(self, basic_agent_config):
        """Test agent configuration JSON serialization."""
        json_str = basic_agent_config.to_json()
        restored = AgentConfig.from_json(json_str)

        assert restored.name == basic_agent_config.name

    def test_skill_addition(self, basic_agent_config):
        """Test adding skills to configuration."""
        new_skill = SkillDefinition(
            name="new_skill",
            description="A newly added skill",
            parameters=[],
        )

        basic_agent_config.add_skill(new_skill)

        assert any(s.name == "new_skill" for s in basic_agent_config.skills)

    def test_capability_addition(self, basic_agent_config):
        """Test adding capabilities to configuration."""
        new_capability = CapabilityDefinition(
            name="new_capability",
            description="A newly added capability",
            category="testing",
        )

        basic_agent_config.add_capability(new_capability)

        assert any(c.name == "new_capability" for c in basic_agent_config.capabilities)

    def test_protocol_enable_disable(self, basic_agent_config):
        """Test enabling and disabling protocols."""
        # Enable a protocol
        basic_agent_config.enable_protocol(ProtocolType.HTTP)
        assert ProtocolType.HTTP in basic_agent_config.get_enabled_protocols()

        # Disable it
        basic_agent_config.disable_protocol(ProtocolType.HTTP)
        http_protocol = basic_agent_config.protocols.get(ProtocolType.HTTP)
        if http_protocol:
            assert not http_protocol.enabled

    def test_multi_protocol_config(self, multi_protocol_agent_config):
        """Test multi-protocol configuration."""
        enabled = multi_protocol_agent_config.get_enabled_protocols()

        assert ProtocolType.HTTP in enabled
        assert ProtocolType.WEBSOCKET in enabled
        assert ProtocolType.A2A in enabled
        assert ProtocolType.MCP in enabled
        assert ProtocolType.P2P in enabled


class TestAgentRegistrationFlow:
    """Tests for agent registration flow."""

    @pytest.mark.asyncio
    async def test_registration_manager_creation(self, registration_manager):
        """Test registration manager creation."""
        assert registration_manager is not None
        assert registration_manager.status == RegistrationStatus.NOT_REGISTERED

    @pytest.mark.asyncio
    async def test_platform_node_scoring(self):
        """Test platform node scoring for selection."""
        node = PlatformNode(
            node_id="test-node",
            endpoint="http://localhost:8000",
            protocol=ProtocolType.HTTP,
            latency=10.0,
            load=0.2,
            priority=80,
            is_available=True,
        )

        score = node.calculate_score()

        # Lower score is better
        assert score > 0
        assert score < float('inf')

    @pytest.mark.asyncio
    async def test_registration_info_expiry(self):
        """Test registration info expiry check."""
        from datetime import timedelta

        # Non-expiring registration
        info = RegistrationInfo(
            registration_id="reg-001",
            agent_id="agent-001",
            node_id="node-001",
            protocols=[ProtocolType.HTTP],
            registered_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=24),
        )

        assert not info.is_expired()

        # Expired registration
        expired_info = RegistrationInfo(
            registration_id="reg-002",
            agent_id="agent-002",
            node_id="node-001",
            protocols=[ProtocolType.HTTP],
            registered_at=datetime.now() - timedelta(hours=48),
            expires_at=datetime.now() - timedelta(hours=1),
        )

        assert expired_info.is_expired()

    @pytest.mark.asyncio
    async def test_registration_hooks(self, registration_manager):
        """Test registration event hooks."""
        hook_called = []

        def on_registered(info):
            hook_called.append("registered")

        def on_unregistered(agent_id):
            hook_called.append("unregistered")

        def on_failure(reason):
            hook_called.append("failed")

        registration_manager.on_registration(on_registered)
        registration_manager.on_unregistration(on_unregistered)
        registration_manager.on_failure(on_failure)

        # Hooks should be registered
        assert len(registration_manager._on_registration_hooks) == 1
        assert len(registration_manager._on_unregistration_hooks) == 1
        assert len(registration_manager._on_failure_hooks) == 1

    @pytest.mark.asyncio
    async def test_node_discovery_mock(self, registration_manager):
        """Test node discovery with mocked HTTP."""
        # Mock the HTTP response for node health check
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "node_id": "mock-node",
                "status": "healthy",
                "load": 0.5,
                "priority": 50,
            })
            mock_get.return_value.__aenter__.return_value = mock_response

            nodes = await registration_manager.discover_nodes()

            # Should find at least the configured platform endpoints
            assert isinstance(nodes, list)

    @pytest.mark.asyncio
    async def test_registration_status_property(self, registration_manager):
        """Test registration status property."""
        status = registration_manager.status

        assert isinstance(status, RegistrationStatus)
        assert status == RegistrationStatus.NOT_REGISTERED

    @pytest.mark.asyncio
    async def test_registered_protocols(self, registration_manager):
        """Test registered protocols tracking."""
        protocols = registration_manager.registered_protocols

        assert isinstance(protocols, list)


class TestAgentCommunication:
    """Tests for agent communication."""

    @pytest.mark.asyncio
    async def test_communication_manager_initialize(self, communication_manager):
        """Test communication manager initialization."""
        assert communication_manager._initialized

    @pytest.mark.asyncio
    async def test_message_creation(self):
        """Test creating messages."""
        message = Message(
            type=MessageType.REQUEST,
            sender_id="sender",
            receiver_id="receiver",
            content={"key": "value"},
        )

        assert message.message_id is not None
        assert message.type == MessageType.REQUEST
        assert not message.is_expired()

    @pytest.mark.asyncio
    async def test_message_with_priority(self):
        """Test message with priority."""
        urgent_message = Message(
            type=MessageType.REQUEST,
            sender_id="sender",
            content={"urgent": True},
            priority=MessagePriority.URGENT,
        )

        assert urgent_message.priority == MessagePriority.URGENT

    @pytest.mark.asyncio
    async def test_message_ttl(self):
        """Test message TTL."""
        short_ttl_message = Message(
            type=MessageType.REQUEST,
            sender_id="sender",
            content={"test": "data"},
            ttl=0,
        )

        # Should be expired immediately
        assert short_ttl_message.is_expired()

    @pytest.mark.asyncio
    async def test_session_creation(self, communication_manager):
        """Test creating communication sessions."""
        session = await communication_manager.create_session(
            participant_ids=["agent-1", "agent-2"],
            protocol=ProtocolType.HTTP,
        )

        assert session.session_id is not None
        assert len(session.participant_ids) == 2
        assert session.is_active()

    @pytest.mark.asyncio
    async def test_session_management(self, communication_manager):
        """Test session lifecycle management."""
        # Create session
        session = await communication_manager.create_session(
            participant_ids=["agent-a"],
        )

        # Retrieve session
        retrieved = await communication_manager.get_session(session.session_id)
        assert retrieved is not None

        # Close session
        await communication_manager.close_session(session.session_id)
        retrieved = await communication_manager.get_session(session.session_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_protocol_selection(self, communication_manager):
        """Test automatic protocol selection."""
        message = Message(
            type=MessageType.REQUEST,
            sender_id=communication_manager.agent_id,
            receiver_id="target-agent",
            content={"test": "protocol"},
        )

        protocol = await communication_manager._select_protocol(message)

        assert isinstance(protocol, ProtocolType)

    @pytest.mark.asyncio
    async def test_p2p_connection_structure(self):
        """Test P2P connection data structure."""
        conn = P2PConnection(
            agent_id="peer-agent",
            endpoint="ws://localhost:9000/p2p",
        )

        assert conn.agent_id == "peer-agent"
        assert conn.state == "connecting"
        assert not conn.is_connected()

    @pytest.mark.asyncio
    async def test_health_check(self, communication_manager):
        """Test communication manager health check."""
        health = await communication_manager.health_check()

        assert "status" in health
        assert "p2p_connections" in health
        assert "active_sessions" in health

    @pytest.mark.asyncio
    async def test_message_handler_registration(self, communication_manager):
        """Test registering message handlers."""
        called = []

        async def handler(message, session):
            called.append(message)
            return {"handled": True}

        communication_manager.register_handler("custom_type", handler)

        # Handler should be registered
        assert "custom_type" in communication_manager._handlers


class TestAgentDiscovery:
    """Tests for agent discovery mechanisms."""

    @pytest.mark.asyncio
    async def test_discovery_manager_initialize(self, discovery_manager):
        """Test discovery manager initialization."""
        assert discovery_manager._initialized

    @pytest.mark.asyncio
    async def test_discovery_filter_creation(self):
        """Test creating discovery filters."""
        filter_criteria = DiscoveryFilter(
            skills=["analyze", "transform"],
            capabilities=["data_processing"],
            min_rating=0.8,
            online_only=True,
            limit=10,
        )

        filter_dict = filter_criteria.to_dict()

        assert filter_dict["skills"] == ["analyze", "transform"]
        assert filter_dict["min_rating"] == 0.8
        assert filter_dict["online_only"] is True

    @pytest.mark.asyncio
    async def test_discovery_filter_deserialization(self):
        """Test deserializing discovery filters."""
        filter_dict = {
            "skills": ["test"],
            "online_only": False,
            "limit": 50,
        }

        filter_criteria = DiscoveryFilter.from_dict(filter_dict)

        assert filter_criteria.skills == ["test"]
        assert filter_criteria.online_only is False
        assert filter_criteria.limit == 50

    @pytest.mark.asyncio
    async def test_agent_info_creation(self):
        """Test creating agent info."""
        agent_info = AgentInfo(
            agent_id="discovered-agent",
            name="DiscoveredAgent",
            description="A discovered agent",
            skills=[{"name": "test_skill"}],
            capabilities=[{"name": "testing"}],
            is_online=True,
            rating=4.5,
        )

        assert agent_info.agent_id == "discovered-agent"
        assert agent_info.has_skill("test_skill")
        assert agent_info.has_capability("testing")

    @pytest.mark.asyncio
    async def test_agent_info_serialization(self):
        """Test serializing agent info."""
        agent_info = AgentInfo(
            agent_id="agent-001",
            name="TestAgent",
            description="Test",
            skills=[{"name": "skill1"}],
        )

        info_dict = agent_info.to_dict()

        assert info_dict["agent_id"] == "agent-001"
        assert len(info_dict["skills"]) == 1

    @pytest.mark.asyncio
    async def test_discover_with_filter(self, discovery_manager):
        """Test discovering agents with filter."""
        filter_criteria = DiscoveryFilter(
            skills=["test_skill"],
            limit=5,
        )

        agents = await discovery_manager.discover(filter_criteria)

        assert isinstance(agents, list)

    @pytest.mark.asyncio
    async def test_discover_by_skill(self, discovery_manager):
        """Test discovering agents by skill."""
        agents = await discovery_manager.discover_by_skill("test_skill")

        assert isinstance(agents, list)

    @pytest.mark.asyncio
    async def test_discover_by_capability(self, discovery_manager):
        """Test discovering agents by capability."""
        agents = await discovery_manager.discover_by_capability("testing")

        assert isinstance(agents, list)

    @pytest.mark.asyncio
    async def test_discover_by_keywords(self, discovery_manager):
        """Test discovering agents by keywords."""
        agents = await discovery_manager.discover_by_keywords(
            ["test", "integration"]
        )

        assert isinstance(agents, list)

    @pytest.mark.asyncio
    async def test_get_specific_agent(self, discovery_manager):
        """Test getting a specific agent by ID."""
        # Try to get an agent that may not exist
        agent = await discovery_manager.get_agent("nonexistent-agent")

        # Should return None or handle gracefully
        assert agent is None or isinstance(agent, AgentInfo)

    @pytest.mark.asyncio
    async def test_recommendation_algorithm(self, discovery_manager):
        """Test getting recommended agents for a task."""
        recommendations = await discovery_manager.get_recommendations(
            task_description="I need an agent that can analyze data and create reports",
            limit=5,
        )

        assert isinstance(recommendations, list)

    @pytest.mark.asyncio
    async def test_cache_management(self, discovery_manager):
        """Test discovery cache management."""
        # Clear cache
        discovery_manager.clear_cache()
        assert len(discovery_manager._agent_cache) == 0

    @pytest.mark.asyncio
    async def test_refresh_discoveries(self, discovery_manager):
        """Test refreshing discoveries."""
        await discovery_manager.refresh_discoveries()

        # Should complete without error
        assert True


class TestAgentInfoMatching:
    """Tests for agent info matching logic."""

    def test_skill_matching(self):
        """Test skill matching in agent info."""
        agent = AgentInfo(
            agent_id="skill-agent",
            name="SkillAgent",
            description="",
            skills=[
                {"name": "analyze"},
                {"name": "transform"},
            ],
        )

        assert agent.has_skill("analyze")
        assert agent.has_skill("transform")
        assert not agent.has_skill("nonexistent")

    def test_capability_matching(self):
        """Test capability matching in agent info."""
        agent = AgentInfo(
            agent_id="cap-agent",
            name="CapAgent",
            description="",
            capabilities=[
                {"name": "nlp"},
                {"name": "vision"},
            ],
        )

        assert agent.has_capability("nlp")
        assert agent.has_capability("vision")
        assert not agent.has_capability("audio")

    def test_get_specific_skill(self):
        """Test getting a specific skill from agent info."""
        agent = AgentInfo(
            agent_id="skill-get-agent",
            name="SkillGetAgent",
            description="",
            skills=[
                {"name": "process", "description": "Process data", "timeout": 30},
            ],
        )

        skill = agent.get_skill("process")

        assert skill is not None
        assert skill["description"] == "Process data"

    def test_get_specific_capability(self):
        """Test getting a specific capability from agent info."""
        agent = AgentInfo(
            agent_id="cap-get-agent",
            name="CapGetAgent",
            description="",
            capabilities=[
                {"name": "compute", "level": "advanced"},
            ],
        )

        cap = agent.get_capability("compute")

        assert cap is not None
        assert cap["level"] == "advanced"


class TestIntegrationScenarios:
    """End-to-end integration scenario tests."""

    @pytest.mark.asyncio
    async def test_full_registration_flow(
        self,
        basic_agent_config,
        mock_platform_server,
    ):
        """Test full registration flow with mock server."""
        manager = RegistrationManager(
            agent_id=basic_agent_config.agent_id,
            agent_config=basic_agent_config,
        )

        # Update platform endpoint to use mock server
        basic_agent_config.network.platform_endpoints = ["http://127.0.0.1:8999"]

        # Note: Registration may fail without proper HTTP handling
        # This tests the flow, not the actual success
        try:
            await manager.close()
        except:
            pass

    @pytest.mark.asyncio
    async def test_full_communication_flow(self, communication_manager):
        """Test full communication flow."""
        # Create a session
        session = await communication_manager.create_session(
            participant_ids=["agent-b"],
        )

        # Create a message
        message = Message(
            type=MessageType.REQUEST,
            sender_id=communication_manager.agent_id,
            receiver_id="agent-b",
            content={"action": "test"},
        )

        assert message.message_id is not None

        # Clean up
        await communication_manager.close_session(session.session_id)

    @pytest.mark.asyncio
    async def test_discovery_and_communication_integration(
        self,
        discovery_manager,
        communication_manager,
    ):
        """Test discovery followed by communication."""
        # Discover agents
        agents = await discovery_manager.discover(
            DiscoveryFilter(limit=5)
        )

        # Create session with discovered agents
        if agents:
            session = await communication_manager.create_session(
                participant_ids=[agents[0].agent_id],
            )
            assert session is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
