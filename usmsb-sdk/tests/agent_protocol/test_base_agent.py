"""
Tests for Agent SDK

Unit tests for BaseAgent, Registration, Communication, and Discovery modules.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Import agent SDK modules
from usmsb_sdk.agent_sdk import (
    BaseAgent,
    AgentConfig,
    AgentCapability,
    RegistrationManager,
    CommunicationManager,
    DiscoveryManager,
    create_agent,
)
from usmsb_sdk.agent_sdk.agent_config import (
    ProtocolType,
    SkillDefinition,
    ProtocolConfig,
)


class TestAgentConfig:
    """Tests for AgentConfig"""

    def test_create_config(self):
        """Test creating an agent configuration"""
        config = AgentConfig(
            agent_id="test-agent-001",
            name="TestAgent",
            description="A test agent",
            version="1.0.0",
        )
        assert config.agent_id == "test-agent-001"
        assert config.name == "TestAgent"
        assert config.description == "A test agent"
        assert config.version == "1.0.0"

    def test_config_with_skills(self):
        """Test configuration with skills"""
        skill = SkillDefinition(
            name="test_skill",
            description="A test skill",
        )
        config = AgentConfig(
            agent_id="test-agent-002",
            name="SkilledAgent",
            skills=[skill],
        )
        assert len(config.skills) == 1
        assert config.skills[0].name == "test_skill"

    def test_config_with_protocols(self):
        """Test configuration with multiple protocols"""
        http_protocol = ProtocolConfig(
            protocol_type=ProtocolType.HTTP,
        )
        ws_protocol = ProtocolConfig(
            protocol_type=ProtocolType.WEBSOCKET,
        )
        config = AgentConfig(
            agent_id="test-agent-003",
            name="MultiProtocolAgent",
            protocols={ProtocolType.HTTP: http_protocol, ProtocolType.WEBSOCKET: ws_protocol},
        )
        assert len(config.protocols) >= 2


class MockAgent(BaseAgent):
    """Mock agent for testing"""

    async def initialize(self):
        """Initialize the mock agent"""
        self.logger.info("MockAgent initialized")

    async def handle_message(self, message, session=None):
        """Handle incoming message"""
        self.logger.info(f"Handling message: {message}")
        return {"status": "handled", "message_id": message.message_id}

    async def execute_skill(self, skill_name, params):
        """Execute a skill"""
        if skill_name == "test_skill":
            return {"result": "success", "params": params}
        raise ValueError(f"Unknown skill: {skill_name}")

    async def shutdown(self):
        """Shutdown the mock agent"""
        self.logger.info("MockAgent shutdown")


class TestBaseAgent:
    """Tests for BaseAgent"""

    @pytest.fixture
    def agent_config(self):
        """Create a test agent configuration"""
        return AgentConfig(
            agent_id="test-agent-001",
            name="TestAgent",
            description="A test agent",
            version="1.0.0",
            skills=[
                SkillDefinition(
                    name="test_skill",
                    description="Test skill",
                )
            ],
        )

    @pytest.fixture
    def mock_agent(self, agent_config):
        """Create a mock agent instance"""
        return MockAgent(agent_config)

    def test_agent_creation(self, mock_agent):
        """Test agent creation"""
        assert mock_agent.agent_id == "test-agent-001"
        assert mock_agent.name == "TestAgent"
        assert mock_agent.description == "A test agent"

    def test_agent_skills(self, mock_agent):
        """Test agent skills"""
        skills = mock_agent.skills
        assert len(skills) == 1
        assert skills[0].name == "test_skill"

    @pytest.mark.asyncio
    async def test_agent_lifecycle(self, mock_agent):
        """Test agent lifecycle"""
        # Start agent
        await mock_agent.start()
        assert mock_agent.is_running

        # Stop agent
        await mock_agent.stop()
        assert not mock_agent.is_running

    @pytest.mark.asyncio
    async def test_skill_execution(self, mock_agent):
        """Test skill execution"""
        await mock_agent.start()
        result = await mock_agent.call_skill("test_skill", {"param": "value"})
        assert result["result"] == "success"
        await mock_agent.stop()


class TestRegistrationManager:
    """Tests for RegistrationManager"""

    @pytest.fixture
    def agent_config_for_reg(self):
        """Create a test agent configuration for registration"""
        return AgentConfig(
            agent_id="test-agent-001",
            name="TestAgent",
            description="Test agent for registration",
            protocols={
                ProtocolType.HTTP: ProtocolConfig(protocol_type=ProtocolType.HTTP)
            },
        )

    @pytest.fixture
    def registration_manager(self, agent_config_for_reg):
        """Create a registration manager instance"""
        return RegistrationManager(
            agent_id=agent_config_for_reg.agent_id,
            agent_config=agent_config_for_reg
        )

    def test_creation(self, registration_manager):
        """Test registration manager creation"""
        assert registration_manager is not None
        assert registration_manager.agent_id == "test-agent-001"

    @pytest.mark.asyncio
    async def test_register_agent(self, registration_manager):
        """Test agent registration (without actual network call)"""
        # Note: This tests the manager creation, not actual registration
        # Actual registration would require a running platform node
        assert registration_manager.status is not None


class TestCommunicationManager:
    """Tests for CommunicationManager"""

    @pytest.fixture
    def agent_config_for_comm(self):
        """Create a test agent configuration for communication"""
        return AgentConfig(
            agent_id="test-agent-comm",
            name="TestAgent",
            description="Test agent for communication",
        )

    @pytest.fixture
    def communication_manager(self, agent_config_for_comm):
        """Create a communication manager instance"""
        async def dummy_handler(message):
            pass
        return CommunicationManager(
            agent_id=agent_config_for_comm.agent_id,
            agent_config=agent_config_for_comm,
            message_handler=dummy_handler
        )

    def test_creation(self, communication_manager):
        """Test communication manager creation"""
        assert communication_manager is not None
        assert communication_manager.agent_id == "test-agent-comm"


class TestDiscoveryManager:
    """Tests for DiscoveryManager"""

    @pytest.fixture
    def agent_config_for_disc(self):
        """Create a test agent configuration for discovery"""
        return AgentConfig(
            agent_id="test-agent-disc",
            name="TestAgent",
            description="Test agent for discovery",
        )

    @pytest.fixture
    def communication_manager_for_disc(self, agent_config_for_disc):
        """Create a communication manager for discovery"""
        async def dummy_handler(message):
            pass
        return CommunicationManager(
            agent_id=agent_config_for_disc.agent_id,
            agent_config=agent_config_for_disc,
            message_handler=dummy_handler
        )

    @pytest.fixture
    def discovery_manager(self, agent_config_for_disc, communication_manager_for_disc):
        """Create a discovery manager instance"""
        return DiscoveryManager(
            agent_id=agent_config_for_disc.agent_id,
            agent_config=agent_config_for_disc,
            communication_manager=communication_manager_for_disc
        )

    def test_creation(self, discovery_manager):
        """Test discovery manager creation"""
        assert discovery_manager is not None
        assert discovery_manager.agent_id == "test-agent-disc"

    @pytest.mark.asyncio
    async def test_discover_by_capability(self, discovery_manager):
        """Test discovering agents by capability"""
        # This would require a running platform or mock
        # Just test that the method exists
        assert hasattr(discovery_manager, 'discover')
        assert hasattr(discovery_manager, 'discover_by_capability')


class TestCreateAgent:
    """Tests for create_agent factory function"""

    def test_create_simple_agent(self):
        """Test creating a simple agent"""
        agent = create_agent(
            agent_id="test-001",
            name="TestAgent",
            description="Test",
        )
        assert agent.agent_id == "test-001"
        assert agent.name == "TestAgent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
