"""
Agent management endpoints.

Unified agent registration, management, and discovery endpoints.

Authentication:
- Public endpoints: list, discover, get, create (registration)
- Protected endpoints (require X-API-Key + X-Agent-ID): update, delete, stake, wallet operations
"""

import json
import time
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from usmsb_sdk.api.database import (
    get_agent as db_get_agent,
    get_all_agents as db_get_all_agents,
    create_agent as db_create_agent,
    update_agent_heartbeat,
    update_agent_stake,
    update_agent_balance,
    delete_agent as db_delete_agent,
    has_wallet_binding,
    get_agent_wallet,
    create_agent_wallet as db_create_agent_wallet,
    update_agent_binding_status,
)
from usmsb_sdk.api.cache import cache_manager, generate_cache_key
from usmsb_sdk.api.rest.schemas.agent import (
    AgentCreate,
    AgentResponse,
    AgentUpdate,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentListFilter,
    AgentStatus,
    AgentProtocol,
)
from usmsb_sdk.api.rest.schemas.environment import GoalCreate
from usmsb_sdk.api.rest.services.utils import safe_json_loads
from usmsb_sdk.api.rest.unified_auth import (
    get_current_user_unified,
    get_optional_user_unified,
    verify_agent_access,
    ErrorCode,
)
from usmsb_sdk.api.rest.api_key_manager import get_stake_tier, get_tier_benefits

router = APIRouter(prefix="/agents", tags=["Agents"])


def _parse_agent_row(row: dict) -> dict:
    """Parse database row to response format with JSON fields.

    Also checks wallet binding status for auto-unregister protection.
    """
    agent_id = row.get('agent_id', row.get('id', ''))

    return {
        'agent_id': agent_id,
        'name': row.get('name', ''),
        'agent_type': row.get('agent_type', row.get('type', 'ai_agent')),
        'description': row.get('description', ''),
        'capabilities': safe_json_loads(row.get('capabilities', '[]'), []),
        'skills': safe_json_loads(row.get('skills', '[]'), []),
        'endpoint': row.get('endpoint', '') or '',
        'chat_endpoint': row.get('chat_endpoint', '') or '',
        'protocol': row.get('protocol', 'standard'),
        'stake': float(row.get('stake', 0) or 0),
        'balance': float(row.get('balance', 0) or 0),
        'status': row.get('status', 'offline'),
        'reputation': float(row.get('reputation', 0.5) or 0.5),
        'heartbeat_interval': row.get('heartbeat_interval', 30) or 30,
        'ttl': row.get('ttl', 90) or 90,
        'metadata': safe_json_loads(row.get('metadata', '{}'), {}),
        'registered_at': float(row.get('created_at', 0) or 0),
        'last_heartbeat': float(row.get('last_heartbeat', 0) or 0),
        'updated_at': float(row.get('updated_at', 0) or 0),
        'has_wallet_binding': has_wallet_binding(agent_id),
        'binding_status': row.get('binding_status', 'unbound'),
        'owner_wallet': row.get('owner_wallet'),
        'bound_at': row.get('bound_at'),
    }


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(agent_create: AgentCreate):
    """Create/register a new agent.

    This is the primary endpoint for agent registration with full configuration.
    """
    # Generate agent_id if not provided
    agent_id = agent_create.agent_id or f"agent_{uuid.uuid4().hex[:12]}"

    # Calculate TTL if not provided (3x heartbeat_interval)
    ttl = agent_create.ttl or (agent_create.heartbeat_interval * 3)

    agent_data = {
        'agent_id': agent_id,
        'name': agent_create.name,
        'agent_type': agent_create.agent_type,
        'description': agent_create.description,
        'capabilities': agent_create.capabilities,
        'skills': agent_create.skills,
        'endpoint': agent_create.endpoint,
        'chat_endpoint': agent_create.chat_endpoint,
        'protocol': agent_create.protocol,
        'stake': agent_create.stake,
        'balance': agent_create.balance,
        'status': 'online',  # New registration means online
        'heartbeat_interval': agent_create.heartbeat_interval,
        'ttl': ttl,
        'metadata': agent_create.metadata,
    }

    # Save to database
    created = db_create_agent(agent_data)

    # 失效agents缓存
    cache_manager.agents.invalidate_prefix("agents:")

    return AgentResponse(
        agent_id=agent_id,
        name=agent_create.name,
        agent_type=agent_create.agent_type,
        description=agent_create.description,
        capabilities=agent_create.capabilities,
        skills=agent_create.skills,
        endpoint=agent_create.endpoint,
        protocol=agent_create.protocol,
        stake=agent_create.stake,
        balance=agent_create.balance,
        status='online',
        reputation=0.5,
        heartbeat_interval=agent_create.heartbeat_interval,
        metadata=agent_create.metadata,
        registered_at=created.get('created_at', time.time()),
        last_heartbeat=time.time(),
    )


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    type: Optional[str] = Query(None, description="Filter by agent type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    protocol: Optional[str] = Query(None, description="Filter by protocol"),
    limit: int = Query(100, ge=1, le=1000),
):
    """List all agents with optional filtering.

    Returns agents from the database with their current status.
    Results are cached for 120 seconds.
    """
    # 生成缓存键
    cache_key = generate_cache_key("agents", type=type, status=status, protocol=protocol, limit=limit)

    # 尝试从缓存获取
    cached = cache_manager.agents.get(cache_key)
    if cached is not None:
        return cached

    # 从数据库查询
    result = []
    agents_data = db_get_all_agents(agent_type=type, status=status, protocol=protocol, limit=limit)

    for row in agents_data:
        parsed = _parse_agent_row(row)
        result.append(AgentResponse(**parsed))

    # 设置缓存 (120秒)
    cache_manager.agents.set(cache_key, result, ttl=120)

    return result


@router.get("/discover", response_model=List[AgentResponse])
async def discover_agents(
    online: bool = Query(False, description="Filter for online agents"),
    limit: int = Query(100, ge=1, le=1000),
):
    """Discover available agents.

    This endpoint is used by the SDK for agent discovery.
    """
    # Filter by status if online=true
    status = "online" if online else None

    agents_data = db_get_all_agents(status=status, limit=limit)

    result = []
    for row in agents_data:
        parsed = _parse_agent_row(row)
        result.append(AgentResponse(**parsed))

    return result


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent_endpoint(agent_id: str):
    """Get an agent by ID."""
    agent_data = db_get_agent(agent_id)

    if not agent_data:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    parsed = _parse_agent_row(agent_data)
    return AgentResponse(**parsed)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    agent_update: AgentUpdate,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Update agent configuration.

    Only provided fields will be updated.

    Requires:
        - X-API-Key header
        - X-Agent-ID header (must match agent_id)
    """
    # Verify agent_id matches authenticated agent
    verify_agent_access(user, agent_id)

    # Build update data
    update_data = {'agent_id': agent_id}
    if agent_update.name is not None:
        update_data['name'] = agent_update.name
    if agent_update.description is not None:
        update_data['description'] = agent_update.description
    if agent_update.capabilities is not None:
        update_data['capabilities'] = agent_update.capabilities
    if agent_update.skills is not None:
        update_data['skills'] = agent_update.skills
    if agent_update.endpoint is not None:
        update_data['endpoint'] = agent_update.endpoint
    if agent_update.protocol is not None:
        update_data['protocol'] = agent_update.protocol
    if agent_update.status is not None:
        update_data['status'] = agent_update.status
    if agent_update.heartbeat_interval is not None:
        update_data['heartbeat_interval'] = agent_update.heartbeat_interval
        update_data['ttl'] = agent_update.heartbeat_interval * 3  # Update TTL accordingly
    if agent_update.metadata is not None:
        update_data['metadata'] = agent_update.metadata

    # Update in database
    updated = db_create_agent(update_data)  # Uses INSERT OR REPLACE

    # 失效agents缓存
    cache_manager.agents.invalidate_prefix("agents:")

    # Fetch and return updated agent
    agent_data = db_get_agent(agent_id)
    parsed = _parse_agent_row(agent_data)
    return AgentResponse(**parsed)


@router.post("/{agent_id}/heartbeat", response_model=AgentHeartbeatResponse)
async def agent_heartbeat(
    agent_id: str,
    request: AgentHeartbeatRequest = None,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Update agent heartbeat.

    Agents should call this endpoint periodically (based on heartbeat_interval)
    to maintain their online status. If no heartbeat is received within TTL seconds,
    the agent will be marked as offline.

    Requires:
        - X-API-Key header
        - X-Agent-ID header (must match agent_id)
    """
    # Verify agent_id matches authenticated agent
    verify_agent_access(user, agent_id)

    status_value = request.status if request else "online"
    success = update_agent_heartbeat(agent_id, status_value)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update heartbeat")

    now = time.time()
    ttl_remaining = user.get('ttl', 90) if isinstance(user.get('ttl'), (int, float)) else 90

    return AgentHeartbeatResponse(
        success=True,
        agent_id=agent_id,
        status=status_value,
        timestamp=now,
        ttl_remaining=ttl_remaining,
        renew_registration=False,
    )


@router.delete("/{agent_id}")
async def delete_agent_endpoint(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Delete/unregister an agent.

    Requires:
        - X-API-Key header
        - X-Agent-ID header (must match agent_id)
    """
    # Verify agent_id matches authenticated agent
    verify_agent_access(user, agent_id)

    # Delete from database
    success = db_delete_agent(agent_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete agent")

    # 失效agents缓存
    cache_manager.agents.invalidate_prefix("agents:")

    return {"status": "deleted", "agent_id": agent_id}


@router.post("/{agent_id}/goals", status_code=status.HTTP_201_CREATED)
async def add_goal_to_agent(
    agent_id: str,
    goal_create: GoalCreate,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Add a goal to an agent.

    Requires:
        - X-API-Key header
        - X-Agent-ID header (must match agent_id)
    """
    # Verify agent_id matches authenticated agent
    verify_agent_access(user, agent_id)

    # Create goal with unique ID
    goal_id = str(uuid.uuid4())

    # Note: Goals are stored in a separate table, not in agent metadata
    # This is kept for backward compatibility

    return {"goal_id": goal_id, "status": "created", "agent_id": agent_id}


@router.get("/{agent_id}/transactions")
async def get_agent_transactions(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Get transactions for an agent.

    Requires:
        - Bearer token (Authorization header) OR
        - X-API-Key + X-Agent-ID headers
    """
    # Verify agent_id matches authenticated agent
    verify_agent_access(user, agent_id)

    # Return empty transactions list for now
    # TODO: Implement transaction queries
    return []


@router.post("/{agent_id}/stake")
async def add_agent_stake(
    agent_id: str,
    amount: float = Query(..., ge=0),
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Add stake to an agent.

    This increases the agent's stake and reputation score.

    Note: This endpoint is deprecated. Stake should be managed through
    the binding flow (POST /agents/v2/{id}/request-binding).

    Requires:
        - X-API-Key header
        - X-Agent-ID header (must match agent_id)
    """
    # Verify agent_id matches authenticated agent
    verify_agent_access(user, agent_id)

    success = update_agent_stake(agent_id, amount)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update stake")

    # Get updated agent
    updated = db_get_agent(agent_id)

    return {
        "success": True,
        "agent_id": agent_id,
        "stake": updated.get('stake', 0),
        "reputation": updated.get('reputation', 0.5),
    }


# ==================== Agent Wallet Endpoints ====================

class WalletBindRequest(BaseModel):
    """Request to bind/create an agent wallet."""
    wallet_address: str = Field(..., description="Owner's wallet address")
    owner_id: str = Field(..., description="Owner ID (user ID)")
    initial_balance: float = Field(default=0.0, ge=0, description="Initial VIBE balance")
    max_per_tx: float = Field(default=100.0, ge=0, description="Maximum spend per transaction")
    daily_limit: float = Field(default=1000.0, ge=0, description="Daily spending limit")


class WalletResponse(BaseModel):
    """Agent wallet response."""
    id: str
    agent_id: str
    owner_id: str
    wallet_address: str
    agent_address: str
    vibe_balance: float
    staked_amount: float
    stake_status: str
    max_per_tx: float
    daily_limit: float
    daily_spent: float
    has_wallet_binding: bool = True


@router.get("/{agent_id}/wallet", response_model=Optional[WalletResponse])
async def get_agent_wallet_endpoint(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Get agent's wallet information.

    Returns the agent's wallet details including balance, stake, and limits.
    Returns null if the agent has no wallet binding.

    Requires:
        - Bearer token (Authorization header) OR
        - X-API-Key + X-Agent-ID headers
        - X-API-Key header
        - X-Agent-ID header (must match agent_id)
    """
    # Verify agent_id matches authenticated agent
    verify_agent_access(user, agent_id)

    wallet = get_agent_wallet(agent_id)
    if not wallet:
        return None

    return WalletResponse(
        id=wallet.get('id', ''),
        agent_id=wallet.get('agent_id', agent_id),
        owner_id=wallet.get('owner_id', ''),
        wallet_address=wallet.get('wallet_address', ''),
        agent_address=wallet.get('agent_address', ''),
        vibe_balance=wallet.get('vibe_balance', 0),
        staked_amount=wallet.get('staked_amount', 0),
        stake_status=wallet.get('stake_status', 'unstaked'),
        max_per_tx=wallet.get('max_per_tx', 100),
        daily_limit=wallet.get('daily_limit', 1000),
        daily_spent=wallet.get('daily_spent', 0),
        has_wallet_binding=True,
    )


@router.post("/{agent_id}/wallet", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def create_or_bind_wallet(
    agent_id: str,
    request: WalletBindRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Create or bind a wallet for an agent.

    This creates a new agent wallet with the specified owner's wallet address.
    The agent will then be protected from auto-unregistration.

    Note: This endpoint is deprecated. Use the binding flow instead:
    POST /agents/v2/{id}/request-binding

    Requires:
        - X-API-Key header
        - X-Agent-ID header (must match agent_id)

    Args:
        agent_id: The agent's ID
        request: Wallet binding request with owner's wallet address and limits
    """
    # Verify agent_id matches authenticated agent
    verify_agent_access(user, agent_id)

    # Check if wallet already exists
    existing_wallet = get_agent_wallet(agent_id)
    if existing_wallet:
        raise HTTPException(
            status_code=400,
            detail=f"Agent {agent_id} already has a wallet binding. Use PATCH to update."
        )

    # Generate wallet ID and agent address
    wallet_id = f"wallet_{uuid.uuid4().hex[:12]}"
    agent_address = f"0x{uuid.uuid4().hex}"

    # Create wallet data
    wallet_data = {
        'id': wallet_id,
        'agent_id': agent_id,
        'owner_id': request.owner_id,
        'wallet_address': request.wallet_address,
        'agent_address': agent_address,
        'vibe_balance': request.initial_balance,
        'staked_amount': 0,
        'stake_status': 'unstaked',
        'locked_stake': 0,
        'max_per_tx': request.max_per_tx,
        'daily_limit': request.daily_limit,
        'daily_spent': 0,
        'last_reset_time': time.time(),
        'registry_registered': False,
    }

    # Create wallet in database
    created_wallet = db_create_agent_wallet(wallet_data)

    # Update agent binding status
    update_agent_binding_status(agent_id, 'bound', request.wallet_address)

    return WalletResponse(
        id=created_wallet.get('id', wallet_id),
        agent_id=agent_id,
        owner_id=request.owner_id,
        wallet_address=request.wallet_address,
        agent_address=agent_address,
        vibe_balance=request.initial_balance,
        staked_amount=0,
        stake_status='unstaked',
        max_per_tx=request.max_per_tx,
        daily_limit=request.daily_limit,
        daily_spent=0,
        has_wallet_binding=True,
    )


@router.delete("/{agent_id}/wallet")
async def unbind_agent_wallet(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Unbind/delete an agent's wallet.

    This removes the wallet binding from the agent.
    The agent will then be subject to auto-unregistration if offline for too long.

    Requires:
        - X-API-Key header
        - X-Agent-ID header (must match agent_id)
    """
    from usmsb_sdk.api.database import delete_agent_wallet

    # Verify agent_id matches authenticated agent
    verify_agent_access(user, agent_id)

    # Check if wallet exists
    wallet = get_agent_wallet(agent_id)
    if not wallet:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} has no wallet binding")

    # Delete wallet
    success = delete_agent_wallet(agent_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to unbind wallet")

    return {"status": "unbound", "agent_id": agent_id}


# ============================================================================
# Agent 消息转发 (用于前端 Send Test 功能)
# ============================================================================

class AgentInvokeRequest(BaseModel):
    """Request to invoke an agent method."""
    method: str = Field(default="chat", description="Method to invoke")
    params: dict = Field(default_factory=dict, description="Method parameters")


class AgentInvokeResponse(BaseModel):
    """Response from agent invocation."""
    success: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    agent_id: str


@router.post("/{agent_id}/invoke", response_model=AgentInvokeResponse)
async def invoke_agent(
    agent_id: str,
    request: AgentInvokeRequest = None,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Invoke an agent method.

    This endpoint forwards requests to registered agents.
    If the agent has an endpoint configured, it will try to call it directly.
    Otherwise, it returns a mock response for demo purposes.

    This enables the frontend "Send Test" functionality to work with agents.

    Requires:
        - X-API-Key header
        - X-Agent-ID header (must match agent_id being invoked)
    """
    import logging
    import httpx

    logger = logging.getLogger(__name__)

    # Verify agent_id matches authenticated agent
    verify_agent_access(user, agent_id)

    # Get agent from database
    agent_data = db_get_agent(agent_id)
    if not agent_data:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    agent_endpoint = agent_data.get("endpoint")
    method = request.method if request else "chat"

    # If agent has endpoint, try to call it
    if agent_endpoint:
        try:
            # 禁用代理，因为本地开发环境可能有代理干扰
            async with httpx.AsyncClient(
                timeout=10.0,
                trust_env=False
            ) as client:
                response = await client.post(
                    f"{agent_endpoint}/invoke",
                    json={
                        "method": method,
                        "params": request.params if request else {"message": "test"}
                    }
                )

                if response.status_code == 200:
                    return AgentInvokeResponse(
                        success=True,
                        result=response.json(),
                        agent_id=agent_id
                    )
                else:
                    logger.warning(f"Agent {agent_id} returned status {response.status_code}")
                    return AgentInvokeResponse(
                        success=False,
                        error=f"Agent service unavailable (status {response.status_code}). Please ensure the agent is running at {agent_endpoint}",
                        agent_id=agent_id
                    )
        except Exception as e:
            logger.warning(f"Failed to invoke agent {agent_id} at {agent_endpoint}: {e}")
            return AgentInvokeResponse(
                success=False,
                error=f"Agent service unavailable. Cannot connect to {agent_endpoint}. Please ensure the agent is running.",
                agent_id=agent_id
            )

    # No endpoint configured
    return AgentInvokeResponse(
        success=False,
        error=f"Agent {agent_data.get('name', agent_id)} has no endpoint configured. Cannot process request.",
        agent_id=agent_id
    )
