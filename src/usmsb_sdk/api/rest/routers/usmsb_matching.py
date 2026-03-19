"""
USMSB Matching API Endpoints.

Phase 3 of USMSB Agent Platform implementation.

Provides USMSB-based three-dimensional matching endpoints:
- GET  /api/usmsb/match/{agent_id} - Find collaboration opportunities
- GET  /api/usmsb/match/{agent_id}/stats - Get emergence statistics
- POST /api/usmsb/match/broadcast/goal - Broadcast a goal
- POST /api/usmsb/match/broadcast/capability - Broadcast a capability
- GET  /api/usmsb/match/broadcasts - Get active broadcasts
- GET  /api/usmsb/match/threshold - Get emergence trigger thresholds

Authentication: Require X-API-Key + X-Agent-ID
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
from usmsb_sdk.services.matching import (
    USMSBMatchingEngine,
    EmergenceDiscovery,
    CollaborationOpportunity,
    EmergenceStats,
)

router = APIRouter(prefix="/usmsb/match", tags=["USMSB Matching"])


# ============== Request Models ==============


class BroadcastGoalRequest(BaseModel):
    """Broadcast a goal to find collaboration opportunities."""
    goal: str = Field(..., description="Goal description")
    requirements: list[str] = Field(default_factory=list, description="What you need")


class BroadcastCapabilityRequest(BaseModel):
    """Broadcast a capability offering."""
    capability: str = Field(..., description="Capability you offer")
    offering: str = Field(..., description="What you're offering")


# ============== Response Models ==============


class MatchScoreBreakdown(BaseModel):
    """Breakdown of match scores."""
    goal_match: float
    capability_match: float
    value_alignment: float
    overall: float


class OpportunityResponse(BaseModel):
    """Collaboration opportunity response."""
    opportunity_id: str
    opportunity_type: str
    demand_agent_id: str
    supply_agent_id: str | None
    scores: MatchScoreBreakdown
    value_chain_potential: float
    match_reasons: list[str]
    identified_risks: list[str]
    recommended_terms: dict
    discovered_at: float
    expires_at: float


class MatchingResponse(BaseModel):
    """Matching result response."""
    agent_id: str
    opportunities: list[OpportunityResponse]
    total: int
    emergence_enabled: bool


class EmergenceStatsResponse(BaseModel):
    """Emergence statistics response."""
    active_agents: int
    collaboration_success_rate: float
    soul_completeness: float
    total_collaborations: int
    emergence_enabled: bool


class ThresholdResponse(BaseModel):
    """Emergence threshold response."""
    min_active_agents: int
    min_collaboration_rate: float
    min_soul_completeness: float


# ============== Endpoints ==============


@router.get("/{agent_id}", response_model=MatchingResponse)
async def find_opportunities(
    agent_id: str,
    opportunity_type: str = Query(
        default="all",
        description="Filter: task | project | collaboration | all"
    ),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(get_current_user_unified),
):
    """
    Find collaboration opportunities for an agent.

    Uses USMSB three-dimensional matching:
    - Goal match: Does the opportunity serve the Agent's goals?
    - Capability match: Does the Agent have what the opportunity needs?
    - Value alignment: Is the value exchange fair?
    """
    engine = USMSBMatchingEngine()

    try:
        opportunities = await engine.find_collaboration_opportunities(
            agent_id=agent_id,
            opportunity_type=opportunity_type,
            limit=limit,
        )

        # Get emergence stats
        discovery = EmergenceDiscovery()
        stats = await discovery.get_emergence_stats()

        return MatchingResponse(
            agent_id=agent_id,
            opportunities=[
                OpportunityResponse(
                    opportunity_id=opp.opportunity_id,
                    opportunity_type=opp.opportunity_type,
                    demand_agent_id=opp.demand_agent_id,
                    supply_agent_id=opp.supply_agent_id,
                    scores=MatchScoreBreakdown(
                        goal_match=opp.goal_match_score,
                        capability_match=opp.capability_match_score,
                        value_alignment=opp.value_alignment_score,
                        overall=opp.overall_score,
                    ),
                    value_chain_potential=opp.value_chain_potential,
                    match_reasons=opp.match_reasons,
                    identified_risks=opp.identified_risks,
                    recommended_terms=opp.recommended_terms,
                    discovered_at=opp.discovered_at,
                    expires_at=opp.expires_at,
                )
                for opp in opportunities
            ],
            total=len(opportunities),
            emergence_enabled=stats.emergence_enabled,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/stats", response_model=EmergenceStatsResponse)
async def get_emergence_stats(
    agent_id: str,
    current_user: dict = Depends(get_current_user_unified),
):
    """Get platform emergence statistics for an agent."""
    discovery = EmergenceDiscovery()
    stats = await discovery.get_emergence_stats()

    return EmergenceStatsResponse(
        active_agents=stats.active_agents,
        collaboration_success_rate=stats.collaboration_success_rate,
        soul_completeness=stats.soul_completeness,
        total_collaborations=stats.total_collaborations,
        emergence_enabled=stats.emergence_enabled,
    )


@router.post("/broadcast/goal")
async def broadcast_goal(
    request: BroadcastGoalRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """Broadcast a goal to find collaboration opportunities."""
    agent_id = current_user.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent ID not found")

    discovery = EmergenceDiscovery()

    try:
        broadcast_id = await discovery.broadcast_goal(
            agent_id=agent_id,
            goal=request.goal,
            requirements=request.requirements,
        )
        return {
            "success": True,
            "broadcast_id": broadcast_id,
            "message": "Goal broadcasted. Responses will be collected."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/broadcast/capability")
async def broadcast_capability(
    request: BroadcastCapabilityRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """Broadcast a capability offering."""
    agent_id = current_user.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent ID not found")

    discovery = EmergenceDiscovery()

    try:
        broadcast_id = await discovery.broadcast_capability(
            agent_id=agent_id,
            capability=request.capability,
            offering=request.offering,
        )
        return {
            "success": True,
            "broadcast_id": broadcast_id,
            "message": "Capability broadcasted."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/broadcasts")
async def get_broadcasts(
    agent_id: str = Query(default=None, description="Filter by agent"),
    current_user: dict = Depends(get_current_user_unified),
):
    """Get active broadcasts."""
    discovery = EmergenceDiscovery()
    broadcasts = discovery.get_active_broadcasts(agent_id)

    return {
        "broadcasts": broadcasts,
        "total": len(broadcasts),
    }


@router.get("/threshold", response_model=ThresholdResponse)
async def get_threshold(
    current_user: dict = Depends(get_current_user_unified),
):
    """Get current emergence trigger thresholds."""
    discovery = EmergenceDiscovery()
    threshold = discovery.get_emergence_threshold()

    return ThresholdResponse(
        min_active_agents=threshold["min_active_agents"],
        min_collaboration_rate=threshold["min_collaboration_rate"],
        min_soul_completeness=threshold["min_soul_completeness"],
    )
