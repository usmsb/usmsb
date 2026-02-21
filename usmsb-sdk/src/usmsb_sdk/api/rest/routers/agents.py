"""
Agent management endpoints.
"""

import json
import time
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from usmsb_sdk.api.database import (
    get_db,
    get_agent as db_get_agent,
    get_all_agents as db_get_all_agents,
    delete_agent as db_delete_agent,
)
from usmsb_sdk.api.rest.schemas.agent import AgentCreate, AgentResponse
from usmsb_sdk.api.rest.schemas.environment import GoalCreate
from usmsb_sdk.api.rest.services.utils import safe_json_loads
from usmsb_sdk.core.elements import Agent, AgentType

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(agent_create: AgentCreate):
    """Create a new agent."""
    from usmsb_sdk.api.database import create_agent as db_create_agent

    try:
        agent_type = AgentType(agent_create.type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent type. Valid types: {[t.value for t in AgentType]}"
        )

    agent = Agent(
        name=agent_create.name,
        type=agent_type,
        capabilities=agent_create.capabilities,
        state=agent_create.state,
    )

    # Save to database
    agent_data = {
        'id': agent.id,
        'name': agent.name,
        'type': agent.type.value,
        'capabilities': agent.capabilities,
        'state': agent.state,
        'goals_count': len(agent.goals),
        'resources_count': len(agent.resources),
    }
    db_create_agent(agent_data)

    return AgentResponse(
        agent_id=agent.id,
        name=agent.name,
        agent_type=agent.type.value,
        capabilities=agent.capabilities,
        skills=[],
        endpoint="",
        protocol="standard",
        stake=0.0,
        balance=0.0,
        description="",
        metadata={},
        status="offline",
        reputation=0.5,
        registered_at=agent.created_at,
        last_heartbeat=0.0,
    )


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    type: Optional[str] = Query(None, description="Filter by agent type"),
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
    limit: int = Query(100, ge=1, le=1000),
):
    """List all agents (includes both database agents and registered external agents)."""
    result = []

    # Get from database
    agents_data = db_get_all_agents(agent_type=type, limit=limit)

    for a in agents_data:
        # Parse JSON fields safely
        capabilities = safe_json_loads(a.get('capabilities', '[]'), [])
        skills = safe_json_loads(a.get('skills', '[]'), [])
        metadata = safe_json_loads(a.get('metadata', '{}'), {})

        result.append(AgentResponse(
            agent_id=a['id'],
            name=a['name'],
            agent_type=a.get('type', 'unknown'),
            capabilities=capabilities,
            skills=skills if isinstance(skills, list) else [],
            endpoint=a.get('endpoint', ''),
            protocol=a.get('protocol', 'standard'),
            stake=float(a.get('stake', 0)),
            balance=float(a.get('balance', 0)),
            description=a.get('description', ''),
            metadata=metadata,
            status=a.get('status', 'offline'),
            reputation=float(a.get('reputation', 0.5)),
            registered_at=float(a.get('created_at', 0)),
            last_heartbeat=float(a.get('last_heartbeat', 0)),
        ))

    # Also get registered external agents from agent_auth module
    try:
        from usmsb_sdk.api.rest.agent_auth import _registered_agents
        for agent_id_key, agent_data in _registered_agents.items():
            # Determine agent type from capabilities
            agent_type = "external"
            capabilities = agent_data.get("capabilities", [])
            if "supply" in capabilities:
                agent_type = "supplier"
            elif "purchase" in capabilities:
                agent_type = "buyer"
            elif "prediction" in capabilities:
                agent_type = "predictor"
            elif "matching" in capabilities:
                agent_type = "matcher"

            # Determine protocol from protocols list
            protocols = agent_data.get("protocols", [])
            agent_protocol_str = "standard"
            if "mcp" in protocols:
                agent_protocol_str = "mcp"
            elif "a2a" in protocols:
                agent_protocol_str = "a2a"
            elif "websocket" in protocols:
                agent_protocol_str = "standard"

            # Filter by type if specified
            if type and agent_type != type:
                continue

            # Filter by protocol if specified
            if protocol and agent_protocol_str != protocol:
                continue

            # Convert skills list to proper format
            skills_list = agent_data.get("skills", [])
            skills = [{"name": s, "level": "intermediate"} if isinstance(s, str) else s for s in skills_list]

            # Convert registered_at ISO string to timestamp float
            registered_at = agent_data.get("registered_at", "")
            created_timestamp = time.time()
            if registered_at:
                try:
                    dt = datetime.fromisoformat(registered_at.replace('Z', '+00:00'))
                    created_timestamp = dt.timestamp()
                except (ValueError, TypeError):
                    pass

            result.append(AgentResponse(
                agent_id=agent_data.get("agent_id", agent_id_key),
                name=agent_data.get("name", agent_id_key),
                agent_type=agent_type,
                capabilities=capabilities,
                skills=skills,
                endpoint=agent_data.get("endpoint", ""),
                protocol=agent_protocol_str,
                stake=float(agent_data.get("stake_amount", 0)),
                balance=0.0,
                description=agent_data.get("description", ""),
                metadata={},
                status=agent_data.get("status", "online"),
                reputation=0.5,
                registered_at=created_timestamp,
                last_heartbeat=created_timestamp,
            ))
    except ImportError:
        pass  # agent_auth module not available

    return result[:limit]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent_endpoint(agent_id: str):
    """Get an agent by ID."""
    # First check database
    agent_data = db_get_agent(agent_id)

    if agent_data:
        # Parse JSON fields safely
        capabilities = safe_json_loads(agent_data.get('capabilities', '[]'), [])
        skills = safe_json_loads(agent_data.get('skills', '[]'), [])
        metadata = safe_json_loads(agent_data.get('metadata', '{}'), {})

        return AgentResponse(
            agent_id=agent_data['id'],
            name=agent_data['name'],
            agent_type=agent_data.get('type', 'unknown'),
            capabilities=capabilities,
            skills=skills if isinstance(skills, list) else [],
            endpoint=agent_data.get('endpoint', ''),
            protocol=agent_data.get('protocol', 'standard'),
            stake=float(agent_data.get('stake', 0)),
            balance=float(agent_data.get('balance', 0)),
            description=agent_data.get('description', ''),
            metadata=metadata,
            status=agent_data.get('status', 'offline'),
            reputation=float(agent_data.get('reputation', 0.5)),
            registered_at=float(agent_data.get('created_at', 0)),
            last_heartbeat=float(agent_data.get('last_heartbeat', 0)),
        )

    # Check registered external agents
    try:
        from usmsb_sdk.api.rest.agent_auth import _registered_agents
        if agent_id in _registered_agents:
            agent_data = _registered_agents[agent_id]

            # Determine agent type
            agent_type = "external"
            capabilities = agent_data.get("capabilities", [])
            if "supply" in capabilities:
                agent_type = "supplier"
            elif "purchase" in capabilities:
                agent_type = "buyer"
            elif "prediction" in capabilities:
                agent_type = "predictor"
            elif "matching" in capabilities:
                agent_type = "matcher"

            # Determine protocol
            protocols = agent_data.get("protocols", [])
            protocol = "standard"
            if "mcp" in protocols:
                protocol = "mcp"
            elif "a2a" in protocols:
                protocol = "a2a"

            # Convert skills
            skills_list = agent_data.get("skills", [])
            skills = [{"name": s, "level": "intermediate"} if isinstance(s, str) else s for s in skills_list]

            # Convert timestamps
            registered_at = agent_data.get("registered_at", "")
            created_timestamp = time.time()
            if registered_at:
                try:
                    dt = datetime.fromisoformat(registered_at.replace('Z', '+00:00'))
                    created_timestamp = dt.timestamp()
                except (ValueError, TypeError):
                    pass

            return AgentResponse(
                agent_id=agent_data.get("agent_id", agent_id),
                name=agent_data.get("name", agent_id),
                agent_type=agent_type,
                capabilities=capabilities,
                skills=skills,
                endpoint=agent_data.get("endpoint", ""),
                protocol=protocol,
                stake=float(agent_data.get("stake_amount", 0)),
                balance=0.0,
                description=agent_data.get("description", ""),
                metadata={},
                status=agent_data.get("status", "online"),
                reputation=0.5,
                registered_at=created_timestamp,
                last_heartbeat=created_timestamp,
            )
    except ImportError:
        pass

    raise HTTPException(status_code=404, detail="Agent not found")


@router.post("/{agent_id}/goals", status_code=status.HTTP_201_CREATED)
async def add_goal_to_agent(agent_id: str, goal_create: GoalCreate):
    """Add a goal to an agent."""
    # Check if agent exists
    agent_data = db_get_agent(agent_id)
    if not agent_data:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Create goal with unique ID
    goal_id = str(uuid.uuid4())

    # Update goals_count in database
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE agents SET goals_count = goals_count + 1, updated_at = ? WHERE id = ?',
            (datetime.now().timestamp(), agent_id)
        )

    return {"goal_id": goal_id, "status": "created"}


@router.get("/{agent_id}/transactions")
async def get_agent_transactions(agent_id: str):
    """Get transactions for an agent."""
    # Check if agent exists (in database or registered)
    agent_data = db_get_agent(agent_id)
    if not agent_data:
        # Check registered agents
        try:
            from usmsb_sdk.api.rest.agent_auth import _registered_agents
            if agent_id not in _registered_agents:
                raise HTTPException(status_code=404, detail="Agent not found")
        except ImportError:
            raise HTTPException(status_code=404, detail="Agent not found")

    # Return empty transactions list for now
    return []


@router.delete("/{agent_id}")
async def delete_agent_endpoint(agent_id: str):
    """Delete an agent."""
    # Check if agent exists
    agent_data = db_get_agent(agent_id)
    if not agent_data:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Delete from database
    db_delete_agent(agent_id)
    return {"status": "deleted"}
