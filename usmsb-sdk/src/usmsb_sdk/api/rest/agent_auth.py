"""
Agent Authentication Router

Provides authentication endpoints for AI agents.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-auth", tags=["Agent Authentication"])


class AgentRegisterRequest(BaseModel):
    """Agent registration request."""
    agent_id: str
    name: str
    description: Optional[str] = None
    wallet_address: Optional[str] = None
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


# In-memory storage for demo purposes
_registered_agents = {}


@router.post("/register", response_model=AgentAuthResponse)
async def register_agent(request: AgentRegisterRequest):
    """Register a new AI agent."""
    logger.info(f"Registering agent: {request.agent_id}")

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
        message="Agent registered successfully"
    )


@router.get("/agents")
async def list_agents():
    """List all registered agents."""
    return {"agents": list(_registered_agents.values())}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent by ID."""
    if agent_id not in _registered_agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _registered_agents[agent_id]


@router.post("/agents/{agent_id}/heartbeat")
async def agent_heartbeat(agent_id: str):
    """Update agent heartbeat."""
    if agent_id not in _registered_agents:
        raise HTTPException(status_code=404, detail="Agent not found")

    _registered_agents[agent_id]["last_heartbeat"] = datetime.utcnow().isoformat()
    _registered_agents[agent_id]["status"] = "online"

    return {"status": "ok", "agent_id": agent_id}


@router.delete("/agents/{agent_id}")
async def unregister_agent(agent_id: str):
    """Unregister an agent."""
    if agent_id not in _registered_agents:
        raise HTTPException(status_code=404, detail="Agent not found")

    del _registered_agents[agent_id]
    return {"status": "ok", "message": f"Agent {agent_id} unregistered"}
