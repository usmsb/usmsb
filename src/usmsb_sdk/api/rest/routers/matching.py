"""
Active Matching API endpoints.

Stake Requirements:
- search_demands, search_suppliers: No stake required
- initiate_negotiation: No stake required
- submit_proposal: No stake required
- accept_negotiation: 100 VIBE minimum

Hybrid Matching:
- Uses vector embeddings for semantic similarity (recall phase)
- Uses LLM for intelligent reranking and explanation (precision phase)
"""

import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from usmsb_sdk.api.database import (
    get_agent as db_get_agent,
)
from usmsb_sdk.api.database import (
    get_all_agents as db_get_all_agents,
)
from usmsb_sdk.api.database import (
    get_db,
)
from usmsb_sdk.api.database import (
    search_demands as db_search_demands,
)
from usmsb_sdk.api.rest.schemas.demand import (
    SearchDemandsRequest,
    SearchSuppliersRequest,
)
from usmsb_sdk.api.rest.schemas.matching import (
    NegotiationRequest,
    ProposalRequest,
)
from usmsb_sdk.api.rest.services.utils import safe_json_loads
from usmsb_sdk.api.rest.unified_auth import (
    get_current_user_unified,
    require_stake_unified,
)
from usmsb_sdk.services.hybrid_matching_service import (
    HybridMatchingService,
    init_hybrid_matching_service,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/matching", tags=["Active Matching"])

# Global reference to matching engine (set by main.py) - kept for backwards compatibility
_matching_engine = None

# Hybrid matching service instance
_hybrid_matching_service: HybridMatchingService | None = None

# In-memory storage for matching (in production, use database)
negotiations_store: dict[str, Any] = {}


def set_matching_engine(engine):
    """Set the matching engine instance (legacy, kept for compatibility)."""
    global _matching_engine
    _matching_engine = engine


async def get_matching_service() -> HybridMatchingService:
    """Get or initialize the hybrid matching service."""
    global _hybrid_matching_service
    if _hybrid_matching_service is None:
        _hybrid_matching_service = await init_hybrid_matching_service()
    return _hybrid_matching_service


@router.post("/search-demands")
async def search_demands(
    request: SearchDemandsRequest,
    user: dict[str, Any] = Depends(get_current_user_unified)
):
    """Search for demands that match the agent's capabilities.

    Uses hybrid matching:
    - Vector embeddings for semantic similarity (recall)
    - LLM for intelligent reranking (precision)

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - agent_id in request must match authenticated agent
    """
    agent_id = user.get('agent_id') or user.get('user_id')
    # Verify ownership
    if agent_id != request.agent_id:
        raise HTTPException(
            status_code=403,
            detail="agent_id in request must match your authenticated agent ID"
        )

    # Get agent info
    agent_data = db_get_agent(request.agent_id)
    if not agent_data:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get capabilities from agent or request
    capabilities = request.capabilities
    if not capabilities:
        capabilities = safe_json_loads(agent_data.get('capabilities', '[]'), [])

    # Build supply info
    supply_info = {
        "id": request.agent_id,
        "agent_id": request.agent_id,
        "capabilities": capabilities,
        "price": agent_data.get('hourly_rate', 100) if isinstance(agent_data, dict) else 100,
        "reputation": agent_data.get('reputation', 0.5) if isinstance(agent_data, dict) else 0.5,
        "availability": agent_data.get('availability', 'available') if isinstance(agent_data, dict) else 'available',
        "description": agent_data.get('bio', '') if isinstance(agent_data, dict) else '',
    }

    # Search demands from database - use expanded capabilities for better recall
    demands_data = db_search_demands(
        capabilities=capabilities,
        budget_min=request.budget_min,
        budget_max=request.budget_max,
    )

    # Convert to dict format for matching service
    demands = []
    for d in demands_data:
        demand_dict = {
            "id": d.get('id'),
            "agent_id": d.get('agent_id'),
            "title": d.get('title'),
            "description": d.get('description', ''),
            "required_skills": safe_json_loads(d.get('required_skills', '[]'), []),
            "budget_range": {
                "min": d.get('budget_min', 0),
                "max": d.get('budget_max', 10000),
            },
            "deadline": d.get('deadline'),
        }
        demands.append(demand_dict)

    # Use hybrid matching service
    matching_service = await get_matching_service()
    matches = await matching_service.match_supply_to_demands(
        supply=supply_info,
        demands=demands,
        min_score=0.3,
        max_results=10,
    )

    # Format response
    results = []
    for match in matches:
        demand_dict = {
            "id": match.candidate.id,
            "agent_id": match.candidate.agent_id,
            "title": match.candidate.name,
            "description": match.candidate.description,
            "required_skills": match.candidate.capabilities,
        }
        # Get demand agent info
        demand_agent = db_get_agent(match.candidate.agent_id)
        results.append({
            "opportunity_id": f"opp-{match.candidate.id}",
            "counterpart_agent_id": match.candidate.agent_id,
            "counterpart_name": demand_agent.get('name', 'Unknown') if demand_agent else 'Unknown',
            "opportunity_type": "demand",
            "details": demand_dict,
            "match_score": {
                "overall": match.score,
                "vector_score": match.candidate.vector_score,
                "llm_score": match.candidate.llm_score,
            },
            "explanation": match.explanation,
            "match_reasons": match.match_reasons,
            "status": "discovered",
            "created_at": datetime.now().timestamp(),
        })

    return results


@router.post("/search-suppliers")
async def search_suppliers(
    request: SearchSuppliersRequest,
    user: dict[str, Any] = Depends(get_current_user_unified)
):
    """Search for suppliers that match the agent's requirements.

    Uses hybrid matching:
    - Vector embeddings for semantic similarity (recall)
    - LLM for intelligent reranking (precision)

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - agent_id in request must match authenticated agent
    """
    agent_id = user.get('agent_id') or user.get('user_id')
    # Verify ownership
    if agent_id != request.agent_id:
        raise HTTPException(
            status_code=403,
            detail="agent_id in request must match your authenticated agent ID"
        )

    # Build demand info from request
    demand_info = {
        "id": request.agent_id,
        "agent_id": request.agent_id,
        "required_skills": request.required_skills,
        "budget_range": {
            "min": request.budget_min or 0,
            "max": request.budget_max or 10000,
        },
        "description": f"寻找具有 {', '.join(request.required_skills)} 技能的供应商",
    }

    # Get all agents as potential suppliers
    all_agents = db_get_all_agents()

    # Build supplier list - don't pre-filter, let vector matching handle it
    suppliers = []
    for agent in all_agents:
        if agent.get('status') != 'offline':
            # Safe JSON parsing (handle double-encoded JSON)
            try:
                caps = agent.get('capabilities', '[]')
                if isinstance(caps, str):
                    agent_capabilities = json.loads(caps)
                    if isinstance(agent_capabilities, str):
                        agent_capabilities = json.loads(agent_capabilities)
                else:
                    agent_capabilities = caps or []
            except (json.JSONDecodeError, TypeError):
                agent_capabilities = []

            try:
                sks = agent.get('skills', '[]')
                if isinstance(sks, str):
                    agent_skills = json.loads(sks)
                    if isinstance(agent_skills, str):
                        agent_skills = json.loads(agent_skills)
                else:
                    agent_skills = sks or []
            except (json.JSONDecodeError, TypeError):
                agent_skills = []

            # Combine capabilities and skills for matching
            all_caps = list(set(agent_capabilities + agent_skills))

            suppliers.append({
                "id": agent.get('agent_id'),
                "agent_id": agent.get('agent_id'),
                "name": agent.get('name'),
                "capabilities": all_caps,
                "skills": agent_skills,
                "price": agent.get('stake', 100) / 10,  # Estimate price from stake
                "reputation": agent.get('reputation', 0.5),
                "availability": "available" if agent.get('status') == 'online' else "busy",
                "description": agent.get('bio', '') or f"Agent with skills: {', '.join(all_caps[:5])}",
            })

    # Also check regular agents with services
    services_query = "SELECT * FROM services WHERE status = 'active'"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(services_query)
        services = cursor.fetchall()

        # Batch load all agents for services to avoid N+1 queries
        agent_ids = set()
        for service in services:
            service_dict = dict(service) if hasattr(service, 'keys') else service
            svc_agent_id = service_dict.get('agent_id', '') if isinstance(service_dict, dict) else service['agent_id']
            if svc_agent_id:
                agent_ids.add(svc_agent_id)

        # Load all agents in one query
        agents_by_id: dict[str, Any] = {}
        if agent_ids:
            placeholders = ','.join(['?' for _ in agent_ids])
            cursor.execute(f'SELECT * FROM agents WHERE agent_id IN ({placeholders})', list(agent_ids))
            for row in cursor.fetchall():
                row_dict = dict(row)
                agents_by_id[row_dict['agent_id']] = row_dict

        for service in services:
            # Safe JSON parsing (sqlite3.Row doesn't have .get(), use dict())
            service_dict = dict(service) if hasattr(service, 'keys') else service
            try:
                sks = service_dict.get('skills', '[]') if isinstance(service_dict, dict) else service['skills']
                if isinstance(sks, str):
                    service_skills = json.loads(sks)
                    if isinstance(service_skills, str):
                        service_skills = json.loads(service_skills)
                else:
                    service_skills = sks or []
            except (json.JSONDecodeError, TypeError, KeyError):
                service_skills = []

            # Check if not already added
            service_agent_id = service_dict.get('agent_id', '') if isinstance(service_dict, dict) else service['agent_id']
            if not any(s.get('id') == service_agent_id for s in suppliers):
                # Get agent from pre-loaded cache
                service_agent = agents_by_id.get(service_agent_id)
                if service_agent:
                    suppliers.append({
                        "id": service_agent_id,
                        "agent_id": service_agent_id,
                        "name": service_agent.get('name', 'Unknown'),
                        "capabilities": service_skills,
                        "skills": service_skills,
                        "price": service_dict.get('price', 100) if isinstance(service_dict, dict) else service['price'],
                        "reputation": service_agent.get('reputation', 0.5),
                        "availability": "available",
                        "description": service_dict.get('description', '') if isinstance(service_dict, dict) else service['description'],
                    })

    # Use hybrid matching service
    matching_service = await get_matching_service()
    matches = await matching_service.match_demand_to_supplies(
        demand=demand_info,
        supplies=suppliers,
        min_score=0.2,  # Lower threshold for better recall
        max_results=10,
    )

    # Format response
    results = []
    for match in matches:
        results.append({
            "opportunity_id": f"opp-{match.candidate.id}",
            "counterpart_agent_id": match.candidate.agent_id,
            "counterpart_name": match.candidate.name,
            "opportunity_type": "supply",
            "details": {
                "capabilities": match.candidate.capabilities,
                "skills": match.candidate.capabilities,
                "price_per_request": match.candidate.price,
                "reputation": match.candidate.reputation,
                "availability": match.candidate.availability,
            },
            "match_score": {
                "overall": match.score,
                "vector_score": match.candidate.vector_score,
                "llm_score": match.candidate.llm_score,
            },
            "explanation": match.explanation,
            "match_reasons": match.match_reasons,
            "status": "discovered",
            "created_at": datetime.now().timestamp(),
        })

    return results


@router.post("/negotiate")
async def initiate_negotiation(
    request: NegotiationRequest,
    user: dict[str, Any] = Depends(get_current_user_unified)
):
    """Initiate a negotiation with another agent.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - No stake required
    """
    agent_id = user.get('agent_id') or user.get('user_id')
    session_id = f"neg-{len(negotiations_store) + 1}"
    negotiation = {
        "session_id": session_id,
        "initiator_id": agent_id,
        "counterpart_id": request.counterpart_id,
        "context": request.context,
        "status": "pending",
        "rounds": [],
        "final_terms": None,
        "created_at": datetime.now().timestamp(),
    }
    negotiations_store[session_id] = negotiation
    return negotiation


@router.get("/negotiations")
async def get_negotiations(
    user: dict[str, Any] = Depends(get_current_user_unified)
):
    """Get all negotiations for the authenticated agent.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    agent_id = user.get('agent_id') or user.get('user_id')
    return [
        n for n in negotiations_store.values()
        if n["initiator_id"] == agent_id or n["counterpart_id"] == agent_id
    ]


@router.post("/negotiations/{session_id}/proposal")
async def submit_proposal(
    session_id: str,
    proposal: ProposalRequest,
    user: dict[str, Any] = Depends(get_current_user_unified)
):
    """Submit a proposal in a negotiation.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    agent_id = user.get('agent_id') or user.get('user_id')
    if session_id not in negotiations_store:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    negotiation = negotiations_store[session_id]

    # Verify user is part of this negotiation
    if negotiation["initiator_id"] != agent_id and negotiation["counterpart_id"] != agent_id:
        raise HTTPException(status_code=403, detail="Not authorized to participate in this negotiation")

    round_number = len(negotiation["rounds"]) + 1

    negotiation["rounds"].append({
        "round_number": round_number,
        "proposer_id": agent_id,
        "proposal": proposal.dict(),
        "response": "counter" if round_number < 3 else "accepted",
    })

    negotiation["status"] = "in_progress"
    return negotiation


@router.post("/negotiations/{session_id}/accept")
async def accept_negotiation(
    session_id: str,
    user: dict[str, Any] = Depends(require_stake_unified(100))
):
    """Accept a negotiation and finalize the terms.

    This commits both parties to the agreement.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Minimum 100 VIBE stake
    """
    agent_id = user.get('agent_id') or user.get('user_id')
    if session_id not in negotiations_store:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    negotiation = negotiations_store[session_id]

    # Verify user is part of this negotiation
    if negotiation["initiator_id"] != agent_id and negotiation["counterpart_id"] != agent_id:
        raise HTTPException(status_code=403, detail="Not authorized to participate in this negotiation")

    if negotiation["status"] == "accepted":
        raise HTTPException(status_code=400, detail="Negotiation already accepted")

    # Accept the negotiation
    negotiation["status"] = "accepted"
    negotiation["accepted_at"] = datetime.now().timestamp()
    negotiation["accepted_by"] = agent_id

    # Get the last proposal as final terms
    if negotiation["rounds"]:
        negotiation["final_terms"] = negotiation["rounds"][-1]["proposal"]

    return {
        "success": True,
        "session_id": session_id,
        "status": "accepted",
        "final_terms": negotiation["final_terms"],
        "accepted_at": negotiation["accepted_at"]
    }


@router.post("/negotiations/{session_id}/reject")
async def reject_negotiation(
    session_id: str,
    user: dict[str, Any] = Depends(get_current_user_unified)
):
    """Reject a negotiation.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    agent_id = user.get('agent_id') or user.get('user_id')
    if session_id not in negotiations_store:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    negotiation = negotiations_store[session_id]

    # Verify user is part of this negotiation
    if negotiation["initiator_id"] != agent_id and negotiation["counterpart_id"] != agent_id:
        raise HTTPException(status_code=403, detail="Not authorized to participate in this negotiation")

    if negotiation["status"] == "accepted":
        raise HTTPException(status_code=400, detail="Cannot reject an accepted negotiation")

    negotiation["status"] = "rejected"
    negotiation["rejected_at"] = datetime.now().timestamp()
    negotiation["rejected_by"] = agent_id

    return {
        "success": True,
        "session_id": session_id,
        "status": "rejected"
    }


@router.get("/opportunities")
async def get_opportunities(
    user: dict[str, Any] = Depends(get_current_user_unified)
):
    """Get all opportunities for the authenticated agent.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    user.get('agent_id') or user.get('user_id')
    # In production, filter by agent_id
    return []


@router.get("/stats")
async def get_matching_stats(
    user: dict[str, Any] = Depends(get_current_user_unified)
):
    """Get matching statistics for the authenticated agent.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    agent_id = user.get('agent_id') or user.get('user_id')
    return {
        "agent_id": agent_id,
        "total_opportunities": 12,
        "active_negotiations": 3,
        "successful_matches": 8,
        "pending_responses": 5,
    }
