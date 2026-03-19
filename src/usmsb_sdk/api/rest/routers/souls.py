"""
Agent Soul API Endpoints.

Phase 1 of USMSB Agent Platform implementation.

Endpoints:
- POST   /api/agents/soul/register     - Register a new Agent Soul
- GET    /api/agents/soul/{agent_id}  - Get Agent Soul
- PUT    /api/agents/soul/{agent_id}  - Update Agent Soul (declared)
- DELETE /api/agents/soul/{agent_id}  - Delete Agent Soul (exit platform)
- GET    /api/agents/soul/{agent_id}/export    - Export Soul data (portability)
- GET    /api/agents/soul/{agent_id}/reputation - Get reputation score
- PUT    /api/agents/soul/{agent_id}/environment - Update environment state
- GET    /api/agents/soul/{agent_id}/compatible - Get compatible agents (simple filter)

Authentication:
- Public: register (no auth needed for new agents)
- Protected (require X-API-Key + X-Agent-ID): get, update, delete, export
"""

import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from usmsb_sdk.api.database import (
    get_agent as db_get_agent,
)
from usmsb_sdk.api.rest.unified_auth import (
    get_current_user_unified,
    verify_agent_access,
)
from usmsb_sdk.core.elements import Goal, Value
from usmsb_sdk.services.agent_soul.manager import AgentSoulManager
from usmsb_sdk.services.schema import create_session

router = APIRouter(prefix="/agents/soul", tags=["Agent Souls"])


# ============== Request/Response Models ==============


class GoalRequest(BaseModel):
    """Goal in Soul declaration."""
    id: str = Field(default="", description="Goal ID")
    name: str = Field(..., description="Goal name")
    description: str = Field(default="", description="Goal description")
    priority: int = Field(default=0, description="Priority (higher = more important)")
    status: str = Field(default="pending", description="Status")


class ValueRequest(BaseModel):
    """Value seeking in Soul declaration."""
    id: str = Field(default="", description="Value ID")
    name: str = Field(..., description="Value name")
    type: str = Field(default="economic", description="Value type")
    metric: float | None = Field(default=None, description="Metric value")


class DeclaredSoulRequest(BaseModel):
    """Request to declare/update Agent Soul."""
    goals: list[GoalRequest] = Field(default_factory=list, description="Agent's goals")
    value_seeking: list[ValueRequest] = Field(
        default_factory=list, description="Value types the Agent seeks"
    )
    capabilities: list[str] = Field(
        default_factory=list, description="What the Agent can provide"
    )
    risk_tolerance: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Risk tolerance (0.0=averse, 1.0=tolerant)"
    )
    collaboration_style: str = Field(
        default="balanced",
        description="conservative | balanced | aggressive"
    )
    preferred_contract_type: str = Field(
        default="any",
        description="task | project | any"
    )
    pricing_strategy: str = Field(
        default="negotiable",
        description="fixed | negotiable | market"
    )
    base_price_vibe: float | None = Field(
        default=None, ge=0.0,
        description="Base price reference in VIBE"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional declared metadata"
    )


class SoulResponse(BaseModel):
    """Response containing Agent Soul data."""
    agent_id: str
    declared: dict[str, Any]
    inferred: dict[str, Any] | None
    environment_state: dict[str, Any]
    soul_version: int
    soul_declared_at: float | None
    soul_updated_at: float | None
    created_at: float
    updated_at: float


class SoulUpdateRequest(BaseModel):
    """Request to update declared Soul."""
    declared: DeclaredSoulRequest
    expected_version: int | None = Field(
        default=None,
        description="Expected Soul version for optimistic locking"
    )


class EnvironmentStateUpdate(BaseModel):
    """Request to update environment state."""
    busy_level: float | None = Field(default=None, ge=0.0, le=1.0)
    current_load: float | None = Field(default=None, ge=0.0)
    online_status: str | None = Field(default=None)
    custom_state: dict[str, Any] = Field(default_factory=dict)


class CompatibleAgentsResponse(BaseModel):
    """Response for compatible agents query."""
    agent_id: str
    compatible_agents: list[SoulResponse]
    total: int


class ReputationResponse(BaseModel):
    """Response for reputation query."""
    agent_id: str
    reputation: float
    breakdown: dict[str, Any]


# ============== Helper ==============


def get_soul_manager() -> AgentSoulManager:
    """Get AgentSoulManager instance with current DB session."""
    session = create_session()
    return AgentSoulManager(session)


# ============== Endpoints ==============


@router.post(
    "/register",
    response_model=SoulResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new Agent Soul",
    description="Register a new Agent Soul when joining the platform. Agent must declare its Soul.",
)
async def register_soul(
    agent_id: str = Query(..., description="Agent ID to register"),
    soul: DeclaredSoulRequest = ...,
):
    """Register a new Agent Soul."""
    manager = get_soul_manager()

    # Check if agent exists in the system
    agent = db_get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found. Please register agent first.",
        )

    # Check if Soul already exists
    existing = await manager.get_soul(agent_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent {agent_id} already has a Soul registered. Use PUT to update.",
        )

    # Convert request to DeclaredSoul
    from usmsb_sdk.services.agent_soul.models import DeclaredSoul

    declared = DeclaredSoul(
        goals=[
            Goal(
                id=g.id or str(time.time()),
                name=g.name,
                description=g.description,
                priority=g.priority,
            )
            for g in soul.goals
        ],
        value_seeking=[
            Value(
                id=v.id or str(time.time()),
                name=v.name,
                type=v.type,
                metric=v.metric,
            )
            for v in soul.value_seeking
        ],
        capabilities=soul.capabilities,
        risk_tolerance=soul.risk_tolerance,
        collaboration_style=soul.collaboration_style,
        preferred_contract_type=soul.preferred_contract_type,
        pricing_strategy=soul.pricing_strategy,
        base_price_vibe=soul.base_price_vibe,
        metadata=soul.metadata,
    )

    try:
        result = await manager.register_soul(agent_id, declared)
        return SoulResponse(
            agent_id=result.agent_id,
            declared=result.declared.to_dict(),
            inferred=result.inferred.to_dict() if result.inferred else None,
            environment_state=result.environment_state,
            soul_version=result.soul_version,
            soul_declared_at=result.soul_declared_at,
            soul_updated_at=result.soul_updated_at,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{agent_id}",
    response_model=SoulResponse,
    summary="Get Agent Soul",
    description="Get an Agent's Soul by agent_id.",
)
async def get_soul(
    agent_id: str,
    _current_user: dict = Depends(get_current_user_unified),
):
    """Get Agent Soul."""
    manager = get_soul_manager()

    result = await manager.get_soul(agent_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} Soul not found",
        )

    return SoulResponse(
        agent_id=result.agent_id,
        declared=result.declared.to_dict(),
        inferred=result.inferred.to_dict() if result.inferred else None,
        environment_state=result.environment_state,
        soul_version=result.soul_version,
        soul_declared_at=result.soul_declared_at,
        soul_updated_at=result.soul_updated_at,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.put(
    "/{agent_id}",
    response_model=SoulResponse,
    summary="Update Agent Soul",
    description="Update an Agent's declared Soul. Requires Soul version for optimistic locking.",
)
async def update_soul(
    agent_id: str,
    request: SoulUpdateRequest,
    _current_user: dict = Depends(get_current_user_unified),
):
    """Update Agent Soul (declared part)."""
    manager = get_soul_manager()

    # Convert request to DeclaredSoul
    from usmsb_sdk.services.agent_soul.models import DeclaredSoul

    declared = DeclaredSoul(
        goals=[
            Goal(
                id=g.id or str(time.time()),
                name=g.name,
                description=g.description,
                priority=g.priority,
            )
            for g in request.declared.goals
        ],
        value_seeking=[
            Value(
                id=v.id or str(time.time()),
                name=v.name,
                type=v.type,
                metric=v.metric,
            )
            for v in request.declared.value_seeking
        ],
        capabilities=request.declared.capabilities,
        risk_tolerance=request.declared.risk_tolerance,
        collaboration_style=request.declared.collaboration_style,
        preferred_contract_type=request.declared.preferred_contract_type,
        pricing_strategy=request.declared.pricing_strategy,
        base_price_vibe=request.declared.base_price_vibe,
        metadata=request.declared.metadata,
    )

    try:
        result = await manager.update_declared(
            agent_id, declared, request.expected_version
        )
        return SoulResponse(
            agent_id=result.agent_id,
            declared=result.declared.to_dict(),
            inferred=result.inferred.to_dict() if result.inferred else None,
            environment_state=result.environment_state,
            soul_version=result.soul_version,
            soul_declared_at=result.soul_declared_at,
            soul_updated_at=result.soul_updated_at,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Agent Soul (Exit Platform)",
    description="Delete an Agent's Soul. This removes the Agent from the platform.",
)
async def delete_soul(
    agent_id: str,
    _current_user: dict = Depends(get_current_user_unified),
):
    """Delete Agent Soul (exit platform)."""
    manager = get_soul_manager()

    deleted = await manager.delete_soul(agent_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} Soul not found",
        )
    return None


@router.get(
    "/{agent_id}/export",
    summary="Export Agent Soul",
    description="Export complete Soul data for portability when exiting the platform.",
)
async def export_soul(
    agent_id: str,
    _current_user: dict = Depends(get_current_user_unified),
):
    """Export Agent Soul for portability."""
    manager = get_soul_manager()

    try:
        data = await manager.export_soul(agent_id)
        return {"soul_data": data}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/{agent_id}/reputation",
    response_model=ReputationResponse,
    summary="Get Agent Reputation",
    description="Get Agent's reputation score based on Inferred Soul.",
)
async def get_reputation(
    agent_id: str,
    _current_user: dict = Depends(get_current_user_unified),
):
    """Get Agent reputation score."""
    manager = get_soul_manager()

    soul = await manager.get_soul(agent_id)
    if not soul:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} Soul not found",
        )

    reputation = await manager.get_reputation(agent_id)

    breakdown = {}
    if soul.inferred:
        breakdown = {
            "success_rate": soul.inferred.actual_success_rate,
            "value_alignment": soul.inferred.value_alignment_score,
            "collaboration_count": soul.inferred.collaboration_count,
        }

    return ReputationResponse(
        agent_id=agent_id,
        reputation=reputation,
        breakdown=breakdown,
    )


@router.put(
    "/{agent_id}/environment",
    response_model=SoulResponse,
    summary="Update Agent Environment State",
    description="Update Agent's current environment state (busy_level, online_status, etc.).",
)
async def update_environment(
    agent_id: str,
    request: EnvironmentStateUpdate,
    _current_user: dict = Depends(get_current_user_unified),
):
    """Update Agent environment state."""
    manager = get_soul_manager()

    state_updates = {}
    if request.busy_level is not None:
        state_updates["busy_level"] = request.busy_level
    if request.current_load is not None:
        state_updates["current_load"] = request.current_load
    if request.online_status is not None:
        state_updates["online_status"] = request.online_status
    if request.custom_state:
        state_updates.update(request.custom_state)

    try:
        result = await manager.update_environment_state(agent_id, state_updates)
        return SoulResponse(
            agent_id=result.agent_id,
            declared=result.declared.to_dict(),
            inferred=result.inferred.to_dict() if result.inferred else None,
            environment_state=result.environment_state,
            soul_version=result.soul_version,
            soul_declared_at=result.soul_declared_at,
            soul_updated_at=result.soul_updated_at,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{agent_id}/compatible",
    response_model=CompatibleAgentsResponse,
    summary="Get Compatible Agents",
    description="Get agents compatible with the given agent (simple capability filter, not full matching).",
)
async def get_compatible_agents(
    agent_id: str,
    capabilities: str | None = Query(
        default=None,
        description="Comma-separated list of required capabilities",
    ),
    min_reputation: float | None = Query(
        default=None, ge=0.0, le=1.0,
        description="Minimum reputation score filter",
    ),
    collaboration_style: str | None = Query(
        default=None,
        description="Filter by collaboration style",
    ),
    _current_user: dict = Depends(get_current_user_unified),
):
    """Get compatible agents (simple filter)."""
    manager = get_soul_manager()

    # Build filter criteria
    filter_criteria = {}
    if capabilities:
        filter_criteria["capabilities"] = [c.strip() for c in capabilities.split(",")]
    if min_reputation is not None:
        filter_criteria["min_reputation"] = min_reputation
    if collaboration_style:
        filter_criteria["collaboration_style"] = collaboration_style

    souls = await manager.get_compatible_agents(
        agent_id,
        filter_criteria if filter_criteria else None,
    )

    return CompatibleAgentsResponse(
        agent_id=agent_id,
        compatible_agents=[
            SoulResponse(
                agent_id=s.agent_id,
                declared=s.declared.to_dict(),
                inferred=s.inferred.to_dict() if s.inferred else None,
                environment_state=s.environment_state,
                soul_version=s.soul_version,
                soul_declared_at=s.soul_declared_at,
                soul_updated_at=s.soul_updated_at,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in souls
        ],
        total=len(souls),
    )
