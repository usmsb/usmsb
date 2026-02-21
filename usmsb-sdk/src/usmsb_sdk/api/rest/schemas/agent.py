"""
Agent-related Pydantic schemas.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    """Schema for creating an agent."""

    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(default="ai_agent")
    capabilities: List[str] = Field(default_factory=list)
    state: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Schema for agent response - matches frontend expectations."""

    agent_id: str
    name: str
    agent_type: str
    capabilities: List[str] = []
    skills: List[Dict[str, Any]] = []
    endpoint: str = ""
    protocol: str = "standard"
    stake: float = 0.0
    balance: float = 0.0
    description: str = ""
    metadata: Dict[str, Any] = {}
    status: str = "offline"
    reputation: float = 0.5
    registered_at: float = 0.0
    last_heartbeat: float = 0.0


class AgentRegistrationRequest(BaseModel):
    """Schema for AI Agent registration."""

    agent_id: str
    name: str
    agent_type: str = "ai_agent"
    capabilities: List[str]
    skills: List[Dict[str, Any]] = Field(default_factory=list)
    endpoint: str
    protocol: str  # "mcp", "a2a", "skill_md"
    stake: float = 0.0
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPRegistrationRequest(BaseModel):
    """Schema for MCP protocol registration."""

    agent_id: str
    name: str
    mcp_endpoint: str
    capabilities: List[str]
    stake: float = 0.0


class A2ARegistrationRequest(BaseModel):
    """Schema for A2A protocol registration."""

    agent_card: Dict[str, Any]
    endpoint: str


class SkillMDRegistrationRequest(BaseModel):
    """Schema for skill.md registration."""

    skill_url: str
    agent_id: str = ""


class AgentTestRequest(BaseModel):
    """Schema for testing an agent."""

    input: str
    context: Dict[str, Any] = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    capabilities: Optional[List[str]] = None
    state: Optional[Dict[str, Any]] = None
