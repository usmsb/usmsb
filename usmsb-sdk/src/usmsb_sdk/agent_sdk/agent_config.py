"""
Agent Configuration Module

Provides configuration classes for agent setup including:
- Agent identity and metadata
- Protocol configurations
- Skill and capability definitions
- Network and security settings
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4
import json


class ProtocolType(Enum):
    """Supported communication protocol types"""
    A2A = "a2a"  # Agent-to-Agent Protocol
    MCP = "mcp"  # Model Context Protocol
    P2P = "p2p"  # Peer-to-Peer Protocol
    HTTP = "http"  # HTTP/REST Protocol
    WEBSOCKET = "websocket"  # WebSocket Protocol
    GRPC = "grpc"  # gRPC Protocol


class TransportType(Enum):
    """Transport layer types"""
    TCP = "tcp"
    UDP = "udp"
    QUIC = "quic"
    TLS = "tls"


@dataclass
class SkillParameter:
    """Definition of a skill parameter"""
    name: str
    type: str  # "string", "integer", "float", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None  # Regex pattern for string validation


@dataclass
class SkillDefinition:
    """Complete definition of an agent skill"""
    name: str
    description: str
    parameters: List[SkillParameter] = field(default_factory=list)
    returns: str = "object"
    timeout: int = 30  # seconds
    rate_limit: int = 100  # requests per minute
    requires_auth: bool = False
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    deprecated: bool = False
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                    "enum": p.enum,
                    "min_value": p.min_value,
                    "max_value": p.max_value,
                    "pattern": p.pattern,
                }
                for p in self.parameters
            ],
            "returns": self.returns,
            "timeout": self.timeout,
            "rate_limit": self.rate_limit,
            "requires_auth": self.requires_auth,
            "tags": self.tags,
            "version": self.version,
            "deprecated": self.deprecated,
            "examples": self.examples,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillDefinition":
        """Create from dictionary representation"""
        params = []
        for p in data.get("parameters", []):
            params.append(SkillParameter(
                name=p["name"],
                type=p["type"],
                description=p["description"],
                required=p.get("required", True),
                default=p.get("default"),
                enum=p.get("enum"),
                min_value=p.get("min_value"),
                max_value=p.get("max_value"),
                pattern=p.get("pattern"),
            ))

        return cls(
            name=data["name"],
            description=data["description"],
            parameters=params,
            returns=data.get("returns", "object"),
            timeout=data.get("timeout", 30),
            rate_limit=data.get("rate_limit", 100),
            requires_auth=data.get("requires_auth", False),
            tags=data.get("tags", []),
            version=data.get("version", "1.0.0"),
            deprecated=data.get("deprecated", False),
            examples=data.get("examples", []),
        )


@dataclass
class CapabilityDefinition:
    """Definition of an agent capability"""
    name: str
    description: str
    category: str  # e.g., "nlp", "vision", "data", "automation"
    level: str = "basic"  # "basic", "intermediate", "advanced", "expert"
    dependencies: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    certifications: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "level": self.level,
            "dependencies": self.dependencies,
            "metrics": self.metrics,
            "certifications": self.certifications,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapabilityDefinition":
        """Create from dictionary representation"""
        return cls(
            name=data["name"],
            description=data["description"],
            category=data["category"],
            level=data.get("level", "basic"),
            dependencies=data.get("dependencies", []),
            metrics=data.get("metrics", {}),
            certifications=data.get("certifications", []),
        )


@dataclass
class ProtocolConfig:
    """Configuration for a specific protocol"""
    protocol_type: ProtocolType
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 0  # 0 for auto-assign
    transport: TransportType = TransportType.TCP
    tls_enabled: bool = False
    tls_cert_path: Optional[str] = None
    tls_key_path: Optional[str] = None
    timeout: int = 30
    max_connections: int = 100
    retry_attempts: int = 3
    retry_delay: float = 1.0
    custom_settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "protocol_type": self.protocol_type.value,
            "enabled": self.enabled,
            "host": self.host,
            "port": self.port,
            "transport": self.transport.value,
            "tls_enabled": self.tls_enabled,
            "tls_cert_path": self.tls_cert_path,
            "tls_key_path": self.tls_key_path,
            "timeout": self.timeout,
            "max_connections": self.max_connections,
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay,
            "custom_settings": self.custom_settings,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProtocolConfig":
        """Create from dictionary representation"""
        return cls(
            protocol_type=ProtocolType(data["protocol_type"]),
            enabled=data.get("enabled", True),
            host=data.get("host", "0.0.0.0"),
            port=data.get("port", 0),
            transport=TransportType(data.get("transport", "tcp")),
            tls_enabled=data.get("tls_enabled", False),
            tls_cert_path=data.get("tls_cert_path"),
            tls_key_path=data.get("tls_key_path"),
            timeout=data.get("timeout", 30),
            max_connections=data.get("max_connections", 100),
            retry_attempts=data.get("retry_attempts", 3),
            retry_delay=data.get("retry_delay", 1.0),
            custom_settings=data.get("custom_settings", {}),
        )


@dataclass
class NetworkConfig:
    """Network configuration for the agent"""
    platform_endpoints: List[str] = field(default_factory=lambda: ["http://localhost:8000"])
    p2p_bootstrap_nodes: List[str] = field(default_factory=list)
    p2p_listen_port: int = 9000
    p2p_nat_traversal: bool = True
    p2p_relay_enabled: bool = True
    connection_pool_size: int = 50
    keepalive_interval: int = 30
    discovery_interval: int = 60

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "platform_endpoints": self.platform_endpoints,
            "p2p_bootstrap_nodes": self.p2p_bootstrap_nodes,
            "p2p_listen_port": self.p2p_listen_port,
            "p2p_nat_traversal": self.p2p_nat_traversal,
            "p2p_relay_enabled": self.p2p_relay_enabled,
            "connection_pool_size": self.connection_pool_size,
            "keepalive_interval": self.keepalive_interval,
            "discovery_interval": self.discovery_interval,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NetworkConfig":
        """Create from dictionary representation"""
        return cls(
            platform_endpoints=data.get("platform_endpoints", ["http://localhost:8000"]),
            p2p_bootstrap_nodes=data.get("p2p_bootstrap_nodes", []),
            p2p_listen_port=data.get("p2p_listen_port", 9000),
            p2p_nat_traversal=data.get("p2p_nat_traversal", True),
            p2p_relay_enabled=data.get("p2p_relay_enabled", True),
            connection_pool_size=data.get("connection_pool_size", 50),
            keepalive_interval=data.get("keepalive_interval", 30),
            discovery_interval=data.get("discovery_interval", 60),
        )


@dataclass
class SecurityConfig:
    """Security configuration for the agent"""
    auth_enabled: bool = True
    api_key: Optional[str] = None
    jwt_secret: Optional[str] = None
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    rate_limiting_enabled: bool = True
    max_requests_per_minute: int = 1000
    encryption_enabled: bool = True
    encryption_algorithm: str = "AES-256-GCM"
    signature_enabled: bool = True
    trusted_agents: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "auth_enabled": self.auth_enabled,
            "api_key": "***" if self.api_key else None,
            "jwt_secret": "***" if self.jwt_secret else None,
            "allowed_origins": self.allowed_origins,
            "rate_limiting_enabled": self.rate_limiting_enabled,
            "max_requests_per_minute": self.max_requests_per_minute,
            "encryption_enabled": self.encryption_enabled,
            "encryption_algorithm": self.encryption_algorithm,
            "signature_enabled": self.signature_enabled,
            "trusted_agents": list(self.trusted_agents),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SecurityConfig":
        """Create from dictionary representation"""
        return cls(
            auth_enabled=data.get("auth_enabled", True),
            api_key=data.get("api_key"),
            jwt_secret=data.get("jwt_secret"),
            allowed_origins=data.get("allowed_origins", ["*"]),
            rate_limiting_enabled=data.get("rate_limiting_enabled", True),
            max_requests_per_minute=data.get("max_requests_per_minute", 1000),
            encryption_enabled=data.get("encryption_enabled", True),
            encryption_algorithm=data.get("encryption_algorithm", "AES-256-GCM"),
            signature_enabled=data.get("signature_enabled", True),
            trusted_agents=set(data.get("trusted_agents", [])),
        )


@dataclass
class AgentConfig:
    """
    Complete configuration for an agent.

    This class contains all settings needed to initialize and run an agent,
    including identity, protocols, skills, capabilities, network, and security.
    """
    # Identity
    name: str
    description: str
    agent_id: str = field(default_factory=lambda: str(uuid4()))
    version: str = "1.0.0"
    owner: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # Capabilities and Skills
    capabilities: List[CapabilityDefinition] = field(default_factory=list)
    skills: List[SkillDefinition] = field(default_factory=list)

    # Protocol configurations
    protocols: Dict[ProtocolType, ProtocolConfig] = field(default_factory=dict)

    # Network configuration
    network: NetworkConfig = field(default_factory=NetworkConfig)

    # Security configuration
    security: SecurityConfig = field(default_factory=SecurityConfig)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Runtime settings
    auto_register: bool = True
    auto_discover: bool = True
    skip_http_auto_start: bool = False  # Skip auto-starting HTTP server
    log_level: str = "INFO"
    health_check_interval: int = 30
    heartbeat_interval: int = 30  # Heartbeat interval in seconds
    ttl: int = 90  # Time to live in seconds (3x heartbeat_interval recommended)

    def __post_init__(self):
        """Initialize default protocols if not specified"""
        if not self.protocols:
            # Enable all protocols by default
            for protocol_type in ProtocolType:
                self.protocols[protocol_type] = ProtocolConfig(protocol_type=protocol_type)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "owner": self.owner,
            "tags": self.tags,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "skills": [s.to_dict() for s in self.skills],
            "protocols": {k.value: v.to_dict() for k, v in self.protocols.items()},
            "network": self.network.to_dict(),
            "security": self.security.to_dict(),
            "metadata": self.metadata,
            "auto_register": self.auto_register,
            "auto_discover": self.auto_discover,
            "log_level": self.log_level,
            "health_check_interval": self.health_check_interval,
            "heartbeat_interval": self.heartbeat_interval,
            "ttl": self.ttl,
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        """Create from dictionary representation"""
        capabilities = [
            CapabilityDefinition.from_dict(c)
            for c in data.get("capabilities", [])
        ]

        skills = [
            SkillDefinition.from_dict(s)
            for s in data.get("skills", [])
        ]

        protocols = {}
        for k, v in data.get("protocols", {}).items():
            protocol_type = ProtocolType(k)
            protocols[protocol_type] = ProtocolConfig.from_dict(v)

        return cls(
            name=data["name"],
            description=data["description"],
            agent_id=data.get("agent_id", str(uuid4())),
            version=data.get("version", "1.0.0"),
            owner=data.get("owner"),
            tags=data.get("tags", []),
            capabilities=capabilities,
            skills=skills,
            protocols=protocols,
            network=NetworkConfig.from_dict(data.get("network", {})),
            security=SecurityConfig.from_dict(data.get("security", {})),
            metadata=data.get("metadata", {}),
            auto_register=data.get("auto_register", True),
            auto_discover=data.get("auto_discover", True),
            log_level=data.get("log_level", "INFO"),
            health_check_interval=data.get("health_check_interval", 30),
            heartbeat_interval=data.get("heartbeat_interval", 30),
            ttl=data.get("ttl", 90),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "AgentConfig":
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))

    def add_skill(self, skill: SkillDefinition) -> None:
        """Add a skill to the agent"""
        self.skills.append(skill)

    def add_capability(self, capability: CapabilityDefinition) -> None:
        """Add a capability to the agent"""
        self.capabilities.append(capability)

    def enable_protocol(self, protocol_type: ProtocolType, config: Optional[ProtocolConfig] = None) -> None:
        """Enable a specific protocol"""
        if config:
            self.protocols[protocol_type] = config
        elif protocol_type not in self.protocols:
            self.protocols[protocol_type] = ProtocolConfig(protocol_type=protocol_type)
        else:
            self.protocols[protocol_type].enabled = True

    def disable_protocol(self, protocol_type: ProtocolType) -> None:
        """Disable a specific protocol"""
        if protocol_type in self.protocols:
            self.protocols[protocol_type].enabled = False

    def get_enabled_protocols(self) -> List[ProtocolType]:
        """Get list of enabled protocols"""
        return [p for p, c in self.protocols.items() if c.enabled]
