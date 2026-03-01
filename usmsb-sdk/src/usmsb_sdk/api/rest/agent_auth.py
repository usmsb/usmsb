"""
Agent Authentication Router (DEPRECATED)

This router is DEPRECATED. Use the new v2 endpoints instead:

New Endpoints:
- POST /agents/v2/register - Self-registration with API Key
- POST /agents/v2/{id}/request-binding - Request owner binding
- GET /agents/v2/{id}/binding-status - Get binding status
- GET /agents/v2/profile - Get agent profile
- GET /agents/v2/{id}/api-keys - Manage API keys

Security Issues with this legacy router:
- Takes wallet_address directly in request (no verification)
- Uses predictable token: agent_token_{agent_id}
- No authentication on sensitive endpoints
- Uses in-memory storage

DO NOT USE IN PRODUCTION. This is kept for backward compatibility only.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-auth", tags=["Agent Authentication (DEPRECATED)"])

# DEPRECATION WARNING
DEPRECATION_NOTICE = """
This endpoint is DEPRECATED. Please use the new secure endpoints:

- POST /agents/v2/register - For registration with API Key
- POST /agents/v2/{agent_id}/request-binding - For owner binding
- GET /agents/v2/{agent_id}/binding-status - For binding status

See documentation for details.
"""


class AgentRegisterRequest(BaseModel):
    """Agent registration request."""
    agent_id: str
    name: str
    description: Optional[str] = None
    wallet_address: Optional[str] = None  # DEPRECATED: No longer used
    stake_amount: Optional[float] = 0.0
    capabilities: list = Field(default_factory=list)
    skills: list = Field(default_factory=list)
    endpoint: Optional[str] = None
    protocols: list = Field(default_factory=list)


class AgentAuthResponse(BaseModel):
    """Agent authentication response."""
    success: bool
    agent_id: Optional[str] = None
    token: Optional[str] = None
    message: Optional[str] = None
    deprecation_warning: Optional[str] = DEPRECATION_NOTICE


# In-memory storage for demo purposes
_registered_agents = {}


@router.post("/register", response_model=AgentAuthResponse, deprecated=True)
async def register_agent(request: AgentRegisterRequest):
    """
    DEPRECATED: Register a new AI agent.

    Use POST /agents/v2/register instead for secure registration with API Key.
    """
    logger.warning("Using deprecated /agent-auth/register endpoint")

    if request.agent_id in _registered_agents:
        return AgentAuthResponse(
            success=False,
            message=f"Agent {request.agent_id} already registered"
        )

    _registered_agents[request.agent_id] = {
        "agent_id": request.agent_id,
        "name": request.name,
        "description": request.description,
        "wallet_address": request.wallet_address,
        "stake_amount": request.stake_amount,
        "capabilities": request.capabilities,
        "skills": request.skills,
        "endpoint": request.endpoint,
        "protocols": request.protocols,
        "registered_at": datetime.utcnow().isoformat(),
        "status": "online"
    }

    return AgentAuthResponse(
        success=True,
        agent_id=request.agent_id,
        token=f"agent_token_{request.agent_id}",
        message="Agent registered successfully (DEPRECATED - use /agents/v2/register)"
    )


@router.get("/agents", deprecated=True)
async def list_agents():
    """
    DEPRECATED: List all registered agents.

    Use GET /agents instead.
    """
    # Get in-memory agents
    memory_agents = list(_registered_agents.values())

    # Get database agents
    from usmsb_sdk.api.database import get_all_agents as db_get_all_agents
    db_agents = db_get_all_agents() or []

    # Merge agents (database takes precedence for duplicates)
    memory_ids = {a["agent_id"] for a in memory_agents}
    merged = memory_agents + [a for a in db_agents if a.get("agent_id") not in memory_ids]

    return {"agents": merged, "deprecation_warning": "Use GET /agents instead"}


@router.get("/agents/{agent_id}", deprecated=True)
async def get_agent(agent_id: str):
    """
    DEPRECATED: Get agent by ID.

    Use GET /agents/{agent_id} instead.
    """
    # Check in-memory registry first
    if agent_id in _registered_agents:
        return _registered_agents[agent_id]

    # Check database
    from usmsb_sdk.api.database import get_agent_by_id
    db_agent = get_agent_by_id(agent_id)
    if db_agent:
        return db_agent

    raise HTTPException(status_code=404, detail="Agent not found")


@router.post("/agents/{agent_id}/heartbeat", deprecated=True)
async def agent_heartbeat(agent_id: str):
    """
    DEPRECATED: Update agent heartbeat.

    Use POST /agents/{agent_id}/heartbeat with X-API-Key header instead.
    """
    # Check in-memory registry first
    in_memory = agent_id in _registered_agents

    # Also check database
    from usmsb_sdk.api.database import get_agent_by_id, update_agent_heartbeat
    in_database = get_agent_by_id(agent_id) is not None

    if not in_memory and not in_database:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update in-memory if exists
    if in_memory:
        _registered_agents[agent_id]["last_heartbeat"] = datetime.utcnow().isoformat()
        _registered_agents[agent_id]["status"] = "online"

    # Always update database if exists
    if in_database:
        update_agent_heartbeat(agent_id, "online")

    return {"status": "ok", "agent_id": agent_id, "deprecation_warning": "Use POST /agents/{agent_id}/heartbeat with X-API-Key"}


@router.delete("/agents/{agent_id}", deprecated=True)
async def unregister_agent(agent_id: str):
    """
    DEPRECATED: Unregister an agent.

    Use DELETE /agents/{agent_id} with X-API-Key header instead.
    """
    # Remove from memory
    in_memory = agent_id in _registered_agents
    if in_memory:
        del _registered_agents[agent_id]

    # Remove from database
    from usmsb_sdk.api.database import delete_agent
    in_database = delete_agent(agent_id)

    if not in_memory and not in_database:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {"status": "ok", "message": f"Agent {agent_id} unregistered", "deprecation_warning": "Use DELETE /agents/{agent_id} with X-API-Key"}
