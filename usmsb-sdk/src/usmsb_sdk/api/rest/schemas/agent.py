"""
Agent-related Pydantic schemas.

Unified schemas for agent registration, management, and communication.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent status enumeration."""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class AgentProtocol(str, Enum):
    """Supported communication protocols."""
    STANDARD = "standard"  # HTTP REST
    MCP = "mcp"  # Model Context Protocol
    A2A = "a2a"  # Agent-to-Agent Protocol
    WEBSOCKET = "websocket"
    GRPC = "grpc"
    P2P = "p2p"


# ==================== Base Schemas ====================

class AgentCreate(BaseModel):
    """Schema for creating an agent (unified)."""

    agent_id: Optional[str] = Field(None, description="Unique agent identifier, auto-generated if not provided")
    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    agent_type: str = Field(default="ai_agent", description="Type of agent")
    description: str = Field(default="", description="Agent description")
    capabilities: List[str] = Field(default_factory=list, description="List of capabilities")
    skills: List[Dict[str, Any]] = Field(default_factory=list, description="List of skills with levels")
    endpoint: str = Field(default="", description="Agent endpoint URL for communication")
    chat_endpoint: str = Field(default="", description="Chat endpoint URL for Meta Agent conversations")
    protocol: str = Field(default="standard", description="Communication protocol")
    stake: float = Field(default=0.0, ge=0, description="Staked amount")
    balance: float = Field(default=0.0, ge=0, description="Account balance")
    heartbeat_interval: int = Field(default=30, ge=5, le=300, description="Heartbeat interval in seconds")
    ttl: int = Field(default=90, ge=30, le=600, description="Time to live in seconds (3x heartbeat_interval recommended)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AgentResponse(BaseModel):
    """Schema for agent response - matches frontend expectations."""

    agent_id: str
    name: str
    agent_type: str = "ai_agent"
    description: str = ""
    capabilities: List[str] = []
    skills: List[Dict[str, Any]] = []
    endpoint: str = ""
    chat_endpoint: str = ""
    protocol: str = "standard"
    stake: float = 0.0
    balance: float = 0.0
    status: str = "offline"
    reputation: float = 0.5
    heartbeat_interval: int = 30
    ttl: int = 90
    metadata: Dict[str, Any] = {}
    registered_at: float = 0.0
    last_heartbeat: float = 0.0
    updated_at: float = 0.0
    has_wallet_binding: bool = Field(False, description="Whether agent has wallet binding for auto-unregister protection")
    unregistered_at: Optional[float] = Field(None, description="Timestamp when agent was unregistered (None if still registered)")


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    skills: Optional[List[Dict[str, Any]]] = None
    endpoint: Optional[str] = None
    chat_endpoint: Optional[str] = None
    protocol: Optional[str] = None
    status: Optional[str] = None
    heartbeat_interval: Optional[int] = Field(None, ge=5, le=300)
    ttl: Optional[int] = Field(None, ge=30, le=600)
    metadata: Optional[Dict[str, Any]] = None


class AgentHeartbeatRequest(BaseModel):
    """Schema for agent heartbeat."""

    status: str = Field(default="online", description="Current agent status")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Optional metrics")


class AgentHeartbeatResponse(BaseModel):
    """Schema for heartbeat response."""

    success: bool
    agent_id: str
    status: str
    timestamp: float
    ttl_remaining: float = 0.0
    renew_registration: bool = False


# ==================== Registration Schemas ====================

class AgentRegistrationRequest(BaseModel):
    """Schema for AI Agent registration (standard protocol)."""

    agent_id: Optional[str] = Field(None, description="Unique agent identifier")
    name: str = Field(..., min_length=1, max_length=100)
    agent_type: str = Field(default="ai_agent")
    description: str = ""
    capabilities: List[str] = Field(default_factory=list)
    skills: List[Dict[str, Any]] = Field(default_factory=list)
    endpoint: str = Field(..., description="Agent endpoint URL")
    protocol: str = Field(default="standard")
    stake: float = Field(default=0.0, ge=0)
    balance: float = Field(default=0.0, ge=0)
    heartbeat_interval: int = Field(default=30, ge=5, le=300)
    ttl: int = Field(default=90, ge=30, le=600)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPRegistrationRequest(BaseModel):
    """Schema for MCP protocol registration."""

    agent_id: Optional[str] = Field(None)
    name: str = Field(..., min_length=1, max_length=100)
    mcp_endpoint: str = Field(..., description="MCP server endpoint URL")
    capabilities: List[str] = Field(default_factory=list)
    description: str = ""
    stake: float = Field(default=0.0, ge=0)
    heartbeat_interval: int = Field(default=30, ge=5, le=300)


class A2ARegistrationRequest(BaseModel):
    """Schema for A2A protocol registration."""

    agent_card: Dict[str, Any] = Field(..., description="A2A agent card")
    endpoint: str = Field(..., description="Agent endpoint URL")
    heartbeat_interval: int = Field(default=30, ge=5, le=300)


class SkillMDRegistrationRequest(BaseModel):
    """Schema for skill.md registration."""

    skill_url: str = Field(..., description="URL to skill.md file")
    agent_id: Optional[str] = Field(None)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    endpoint: str = Field(default="")
    heartbeat_interval: int = Field(default=30, ge=5, le=300)


# ==================== Test/Communication Schemas ====================

class AgentTestRequest(BaseModel):
    """Schema for testing an agent."""

    input: str = Field(..., description="Test input message")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class AgentTestResponse(BaseModel):
    """Schema for test response."""

    success: bool
    agent_id: str
    output: str = ""
    latency_ms: float = 0.0
    error: Optional[str] = None


# ==================== List/Query Schemas ====================

class AgentListFilter(BaseModel):
    """Schema for filtering agent list."""

    agent_type: Optional[str] = None
    status: Optional[str] = None
    protocol: Optional[str] = None
    capability: Optional[str] = None
    search: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


# ==================== Legacy Compatibility ====================

# For backward compatibility with old code using 'type' instead of 'agent_type'
class AgentCreateLegacy(BaseModel):
    """Legacy schema for backward compatibility."""

    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(default="ai_agent")
    capabilities: List[str] = Field(default_factory=list)
    state: Dict[str, Any] = Field(default_factory=dict)
