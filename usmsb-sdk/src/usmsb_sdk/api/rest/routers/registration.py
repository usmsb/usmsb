"""
AI Agent Registration API endpoints.
"""

import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException

from usmsb_sdk.api.database import (
    get_ai_agent as db_get_ai_agent,
    create_ai_agent as db_create_ai_agent,
    update_ai_agent_heartbeat as db_update_ai_agent_heartbeat,
    update_ai_agent_stake as db_update_ai_agent_stake,
    delete_ai_agent as db_delete_ai_agent,
)
from usmsb_sdk.api.rest.schemas.agent import (
    AgentRegistrationRequest,
    MCPRegistrationRequest,
    A2ARegistrationRequest,
    SkillMDRegistrationRequest,
    AgentTestRequest,
)

router = APIRouter(tags=["AI Agent Registration"])

# In-memory storage for registered agents
ai_agents_store: Dict[str, Any] = {}


@router.post("/agents/register")
async def register_ai_agent(request: AgentRegistrationRequest):
    """Register an AI Agent to the platform."""
    now = datetime.now().timestamp()
    agent_data = {
        "agent_id": request.agent_id,
        "name": request.name,
        "agent_type": request.agent_type,
        "capabilities": json.dumps(request.capabilities),
        "skills": json.dumps(request.skills),
        "endpoint": request.endpoint,
        "protocol": request.protocol,
        "stake": request.stake,
        "description": request.description,
        "metadata": json.dumps(request.metadata),
        "status": "online",
        "reputation": 0.5,
        "registered_at": now,
        "last_heartbeat": now,
    }
    # Save to database
    db_create_ai_agent(agent_data)
    return {
        "success": True,
        "agent_id": request.agent_id,
        "message": "Agent registered successfully",
    }


@router.post("/agents/register/mcp")
async def register_via_mcp(request: MCPRegistrationRequest):
    """Register an AI Agent via MCP protocol."""
    agent_id = request.agent_id or f"mcp-{uuid.uuid4().hex[:8]}"
    now = datetime.now().timestamp()
    agent_data = {
        "agent_id": agent_id,
        "name": request.name,
        "agent_type": "ai_agent",
        "capabilities": json.dumps(request.capabilities),
        "skills": "[]",
        "endpoint": request.mcp_endpoint,
        "protocol": "mcp",
        "stake": request.stake,
        "description": f"MCP agent: {request.name}",
        "metadata": "{}",
        "status": "online",
        "reputation": 0.5,
        "registered_at": now,
        "last_heartbeat": now,
    }
    # Save to database
    db_create_ai_agent(agent_data)
    return {
        "success": True,
        "agent_id": agent_id,
        "message": "Agent registered via MCP protocol",
    }


@router.post("/agents/register/a2a")
async def register_via_a2a(request: A2ARegistrationRequest):
    """Register an AI Agent via A2A protocol."""
    agent_card = request.agent_card
    agent_id = agent_card.get("agent_id", f"a2a-{uuid.uuid4().hex[:8]}")
    now = datetime.now().timestamp()
    agent_data = {
        "agent_id": agent_id,
        "name": agent_card.get("name", "Unknown"),
        "agent_type": "ai_agent",
        "capabilities": json.dumps(agent_card.get("capabilities", [])),
        "skills": json.dumps(agent_card.get("skills", [])),
        "endpoint": request.endpoint,
        "protocol": "a2a",
        "stake": 0.0,
        "description": agent_card.get("description", ""),
        "metadata": "{}",
        "status": "online",
        "reputation": 0.5,
        "registered_at": now,
        "last_heartbeat": now,
    }
    # Save to database
    db_create_ai_agent(agent_data)
    return {
        "success": True,
        "agent_id": agent_id,
        "message": "Agent registered via A2A protocol",
    }


@router.post("/agents/register/skill-md")
async def register_via_skill_md(request: SkillMDRegistrationRequest):
    """Register an AI Agent via skill.md."""
    # In production, this would fetch and parse skill.md
    agent_id = request.agent_id or f"skill-{uuid.uuid4().hex[:8]}"
    now = datetime.now().timestamp()
    agent_data = {
        "agent_id": agent_id,
        "name": f"Agent from {request.skill_url}",
        "agent_type": "ai_agent",
        "capabilities": json.dumps(["general"]),
        "skills": "[]",
        "endpoint": request.skill_url,
        "protocol": "skill_md",
        "skill_url": request.skill_url,
        "stake": 0.0,
        "description": "Agent registered via skill.md",
        "metadata": "{}",
        "status": "online",
        "reputation": 0.5,
        "registered_at": now,
        "last_heartbeat": now,
    }
    # Save to database
    db_create_ai_agent(agent_data)
    return {
        "success": True,
        "agent_id": agent_id,
        "message": "Agent registered via skill.md",
    }


@router.post("/agents/{agent_id}/heartbeat")
async def agent_heartbeat_endpoint(agent_id: str, status: str = "online"):
    """AI Agent sends heartbeat to stay active."""
    # Check if agent exists
    agent = db_get_ai_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update heartbeat in database
    db_update_ai_agent_heartbeat(agent_id, status)
    return {"success": True, "message": "Heartbeat received"}


@router.delete("/agents/{agent_id}/unregister")
async def unregister_ai_agent(agent_id: str):
    """Unregister an AI Agent."""
    agent = db_get_ai_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Delete from database
    db_delete_ai_agent(agent_id)
    return {"success": True, "message": "Agent unregistered"}


@router.post("/agents/{agent_id}/test")
async def test_ai_agent(agent_id: str, request: AgentTestRequest):
    """Test an AI Agent by sending a test input."""
    agent = db_get_ai_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    endpoint = agent.get("endpoint")
    protocol = agent.get("protocol", "standard")

    start_time = time.time()
    test_result = {
        "agent_id": agent_id,
        "protocol": protocol,
        "endpoint": endpoint,
        "input": request.input,
        "success": False,
        "response": None,
        "error": None,
        "latency_ms": 0,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try different endpoints based on protocol
            if protocol == "mcp":
                # MCP uses SSE or specific endpoints
                response = await client.post(
                    f"{endpoint}/invoke",
                    json={"input": request.input, "context": request.context},
                )
            elif protocol == "a2a":
                # A2A protocol
                response = await client.post(
                    f"{endpoint}/message",
                    json={"content": request.input, "context": request.context},
                )
            else:
                # Standard REST endpoint
                response = await client.post(
                    f"{endpoint}/invoke",
                    json={"input": request.input, "context": request.context},
                )

            end_time = time.time()
            test_result["latency_ms"] = round((end_time - start_time) * 1000, 2)

            if response.status_code == 200:
                try:
                    test_result["response"] = response.json()
                except (json.JSONDecodeError, ValueError):
                    test_result["response"] = response.text
                test_result["success"] = True
            else:
                test_result["error"] = f"HTTP {response.status_code}: {response.text[:500]}"

    except httpx.TimeoutException:
        end_time = time.time()
        test_result["latency_ms"] = round((end_time - start_time) * 1000, 2)
        test_result["error"] = "Request timed out after 30 seconds"
    except httpx.ConnectError as e:
        end_time = time.time()
        test_result["latency_ms"] = round((end_time - start_time) * 1000, 2)
        test_result["error"] = f"Connection failed: {str(e)}"
    except Exception as e:
        end_time = time.time()
        test_result["latency_ms"] = round((end_time - start_time) * 1000, 2)
        test_result["error"] = f"Error: {str(e)}"

    return test_result


@router.post("/agents/{agent_id}/stake")
async def agent_stake_endpoint(agent_id: str, amount: float):
    """Stake VIBE tokens for an AI Agent."""
    # Check if agent exists
    agent = db_get_ai_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update stake in database
    db_update_ai_agent_stake(agent_id, amount)

    # Get updated agent data
    updated_agent = db_get_ai_agent(agent_id)
    current_stake = updated_agent.get("stake", 0)

    # Calculate reputation based on stake
    reputation = min(0.5 + (current_stake / 1000), 1.0)

    return {
        "success": True,
        "total_stake": current_stake,
        "reputation": reputation,
    }
