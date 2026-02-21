"""
Unit Tests for Agent SDK Configuration

Regression baseline tests for agent configuration module.
These tests ensure the core configuration functionality remains stable during refactoring.
"""
import pytest
import json

from usmsb_sdk.agent_sdk.agent_config import (
    AgentConfig,
    CapabilityDefinition,
    SkillDefinition,
    SkillParameter,
    ProtocolConfig,
    ProtocolType,
    TransportType,
    NetworkConfig,
    SecurityConfig,
)


class TestSkillParameter:
    """Tests for SkillParameter dataclass."""

    def test_skill_parameter_creation(self):
        """Test basic skill parameter creation."""
        param = SkillParameter(
            name="query",
            type="string",
            description="Search query string",
            required=True,
        )
        assert param.name == "query"
        assert param.type == "string"
        assert param.required is True
        assert param.default is None

    def test_skill_parameter_with_constraints(self):
        """Test skill parameter with validation constraints."""
        param = SkillParameter(
            name="count",
            type="integer",
            description="Number of results",
            required=False,
            default=10,
            min_value=1,
            max_value=100,
        )
        assert param.default == 10
        assert param.min_value == 1
        assert param.max_value == 100

    def test_skill_parameter_with_enum(self):
        """Test skill parameter with enum values."""
        param = SkillParameter(
            name="format",
            type="string",
            description="Output format",
            enum=["json", "xml", "csv"],
        )
        assert param.enum == ["json", "xml", "csv"]

    def test_skill_parameter_with_pattern(self):
        """Test skill parameter with regex pattern."""
        param = SkillParameter(
            name="email",
            type="string",
            description="Email address",
            pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        )
        assert param.pattern is not None


class TestSkillDefinition:
    """Tests for SkillDefinition dataclass."""

    def test_skill_definition_creation(self):
        """Test basic skill definition creation."""
        skill = SkillDefinition(
            name="search",
            description="Search for information",
        )
        assert skill.name == "search"
        assert skill.description == "Search for information"
        assert skill.timeout == 30
        assert skill.deprecated is False

    def test_skill_definition_with_parameters(self):
        """Test skill definition with parameters."""
        skill = SkillDefinition(
            name="translate",
            description="Translate text",
            parameters=[
                SkillParameter(name="text", type="string", description="Text to translate"),
                SkillParameter(name="target_lang", type="string", description="Target language"),
            ],
        )
        assert len(skill.parameters) == 2

    def test_skill_definition_to_dict(self):
        """Test skill definition serialization."""
        skill = SkillDefinition(
            name="analyze",
            description="Analyze data",
            timeout=60,
            rate_limit=50,
            tags=["data", "analysis"],
        )
        result = skill.to_dict()
        assert result["name"] == "analyze"
        assert result["timeout"] == 60
        assert "data" in result["tags"]

    def test_skill_definition_from_dict(self):
        """Test skill definition deserialization."""
        data = {
            "name": "process",
            "description": "Process data",
            "parameters": [
                {"name": "input", "type": "string", "description": "Input data"}
            ],
            "timeout": 45,
        }
        skill = SkillDefinition.from_dict(data)
        assert skill.name == "process"
        assert skill.timeout == 45
        assert len(skill.parameters) == 1


class TestCapabilityDefinition:
    """Tests for CapabilityDefinition dataclass."""

    def test_capability_creation(self):
        """Test basic capability creation."""
        cap = CapabilityDefinition(
            name="nlp",
            description="Natural Language Processing",
            category="nlp",
        )
        assert cap.name == "nlp"
        assert cap.level == "basic"

    def test_capability_with_level(self):
        """Test capability with expertise level."""
        cap = CapabilityDefinition(
            name="vision",
            description="Computer Vision",
            category="vision",
            level="expert",
        )
        assert cap.level == "expert"

    def test_capability_serialization(self):
        """Test capability serialization round-trip."""
        cap = CapabilityDefinition(
            name="reasoning",
            description="Logical reasoning",
            category="cognitive",
            level="advanced",
            dependencies=["nlp"],
        )
        data = cap.to_dict()
        restored = CapabilityDefinition.from_dict(data)
        assert restored.name == cap.name
        assert restored.level == cap.level
        assert "nlp" in restored.dependencies


class TestProtocolConfig:
    """Tests for ProtocolConfig dataclass."""

    def test_protocol_config_creation(self):
        """Test basic protocol config creation."""
        config = ProtocolConfig(protocol_type=ProtocolType.HTTP)
        assert config.protocol_type == ProtocolType.HTTP
        assert config.enabled is True
        assert config.port == 0

    def test_protocol_config_with_tls(self):
        """Test protocol config with TLS settings."""
        config = ProtocolConfig(
            protocol_type=ProtocolType.HTTP,
            tls_enabled=True,
            tls_cert_path="/path/to/cert.pem",
            tls_key_path="/path/to/key.pem",
        )
        assert config.tls_enabled is True
        assert config.tls_cert_path is not None

    def test_protocol_config_serialization(self):
        """Test protocol config serialization."""
        config = ProtocolConfig(
            protocol_type=ProtocolType.WEBSOCKET,
            host="localhost",
            port=8765,
            max_connections=200,
        )
        data = config.to_dict()
        assert data["protocol_type"] == "websocket"
        assert data["port"] == 8765

        restored = ProtocolConfig.from_dict(data)
        assert restored.protocol_type == ProtocolType.WEBSOCKET


class TestNetworkConfig:
    """Tests for NetworkConfig dataclass."""

    def test_network_config_defaults(self):
        """Test network config default values."""
        config = NetworkConfig()
        assert "http://localhost:8000" in config.platform_endpoints
        assert config.p2p_listen_port == 9000

    def test_network_config_custom(self):
        """Test custom network configuration."""
        config = NetworkConfig(
            platform_endpoints=["http://platform.example.com"],
            p2p_bootstrap_nodes=["http://node1.example.com:9000"],
            connection_pool_size=100,
        )
        assert len(config.platform_endpoints) == 1
        assert len(config.p2p_bootstrap_nodes) == 1

    def test_network_config_serialization(self):
        """Test network config serialization round-trip."""
        config = NetworkConfig(
            platform_endpoints=["http://api.example.com"],
            p2p_listen_port=9100,
        )
        data = config.to_dict()
        restored = NetworkConfig.from_dict(data)
        assert restored.p2p_listen_port == 9100


class TestSecurityConfig:
    """Tests for SecurityConfig dataclass."""

    def test_security_config_defaults(self):
        """Test security config default values."""
        config = SecurityConfig()
        assert config.auth_enabled is True
        assert config.rate_limiting_enabled is True
        assert config.encryption_enabled is True

    def test_security_config_api_key_hidden(self):
        """Test that API key is hidden in serialization."""
        config = SecurityConfig(api_key="secret-key-123")
        data = config.to_dict()
        assert data["api_key"] == "***"

    def test_security_config_trusted_agents(self):
        """Test trusted agents set."""
        config = SecurityConfig(
            trusted_agents={"agent-1", "agent-2"}
        )
        assert "agent-1" in config.trusted_agents
        data = config.to_dict()
        assert "agent-1" in data["trusted_agents"]


class TestAgentConfig:
    """Tests for AgentConfig dataclass."""

    def test_agent_config_creation(self):
        """Test basic agent config creation."""
        config = AgentConfig(
            name="TestAgent",
            description="A test agent",
        )
        assert config.name == "TestAgent"
        assert config.version == "1.0.0"
        assert config.agent_id is not None

    def test_agent_config_auto_protocols(self):
        """Test that protocols are auto-initialized."""
        config = AgentConfig(
            name="TestAgent",
            description="Test",
        )
        assert len(config.protocols) > 0
        assert ProtocolType.HTTP in config.protocols

    def test_agent_config_add_skill(self):
        """Test adding skills to config."""
        config = AgentConfig(
            name="TestAgent",
            description="Test",
        )
        skill = SkillDefinition(name="test_skill", description="A test skill")
        config.add_skill(skill)
        assert len(config.skills) == 1

    def test_agent_config_add_capability(self):
        """Test adding capabilities to config."""
        config = AgentConfig(
            name="TestAgent",
            description="Test",
        )
        cap = CapabilityDefinition(
            name="test_cap",
            description="A test capability",
            category="test",
        )
        config.add_capability(cap)
        assert len(config.capabilities) == 1

    def test_agent_config_enable_disable_protocol(self):
        """Test enabling and disabling protocols."""
        config = AgentConfig(
            name="TestAgent",
            description="Test",
        )
        config.disable_protocol(ProtocolType.GRPC)
        assert ProtocolType.GRPC not in config.get_enabled_protocols()

        config.enable_protocol(ProtocolType.GRPC)
        assert ProtocolType.GRPC in config.get_enabled_protocols()

    def test_agent_config_to_dict(self):
        """Test agent config serialization."""
        config = AgentConfig(
            name="TestAgent",
            description="A test agent",
            version="2.0.0",
            tags=["test", "demo"],
        )
        data = config.to_dict()
        assert data["name"] == "TestAgent"
        assert data["version"] == "2.0.0"
        assert "test" in data["tags"]

    def test_agent_config_from_dict(self):
        """Test agent config deserialization."""
        data = {
            "name": "RestoredAgent",
            "description": "Restored from dict",
            "version": "1.5.0",
            "skills": [
                {"name": "skill1", "description": "First skill"}
            ],
            "capabilities": [
                {"name": "cap1", "description": "First capability", "category": "test"}
            ],
        }
        config = AgentConfig.from_dict(data)
        assert config.name == "RestoredAgent"
        assert config.version == "1.5.0"
        assert len(config.skills) == 1
        assert len(config.capabilities) == 1

    def test_agent_config_json_round_trip(self):
        """Test JSON serialization round-trip."""
        original = AgentConfig(
            name="JSONAgent",
            description="JSON test agent",
            version="3.0.0",
            metadata={"custom": "value"},
        )
        json_str = original.to_json()
        restored = AgentConfig.from_json(json_str)
        assert restored.name == original.name
        assert restored.version == original.version
        assert restored.metadata["custom"] == "value"


class TestProtocolTypeEnum:
    """Tests for ProtocolType enum."""

    def test_all_protocol_types(self):
        """Test all protocol types are defined."""
        expected = {"a2a", "mcp", "p2p", "http", "websocket", "grpc"}
        actual = {p.value for p in ProtocolType}
        assert expected == actual


class TestTransportTypeEnum:
    """Tests for TransportType enum."""

    def test_all_transport_types(self):
        """Test all transport types are defined."""
        expected = {"tcp", "udp", "quic", "tls"}
        actual = {t.value for t in TransportType}
        assert expected == actual
