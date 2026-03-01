"""
Active Matching API endpoints.

Stake Requirements:
- search_demands, search_suppliers: No stake required
- initiate_negotiation: No stake required
- submit_proposal: No stake required
- accept_negotiation: 100 VIBE minimum
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends, Body

from usmsb_sdk.api.database import (
    get_db,
    get_agent as db_get_agent,
    get_all_agents as db_get_all_agents,
    search_demands as db_search_demands,
)
from usmsb_sdk.api.rest.schemas.matching import (
    NegotiationRequest,
    ProposalRequest,
)
from usmsb_sdk.api.rest.schemas.demand import (
    SearchDemandsRequest,
    SearchSuppliersRequest,
)
from usmsb_sdk.api.rest.services.utils import safe_json_loads
from usmsb_sdk.api.rest.unified_auth import (
    get_current_user_unified,
    require_stake_unified,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/matching", tags=["Active Matching"])

# Global reference to matching engine (set by main.py)
_matching_engine = None

# In-memory storage for matching (in production, use database)
negotiations_store: Dict[str, Any] = {}


def set_matching_engine(engine):
    """Set the matching engine instance."""
    global _matching_engine
    _matching_engine = engine


@router.post("/search-demands")
async def search_demands(
    request: SearchDemandsRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Search for demands that match the agent's capabilities.

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

    # Search demands from database
    demands_data = db_search_demands(
        capabilities=capabilities,
        budget_min=request.budget_min,
        budget_max=request.budget_max,
    )

    # Convert to dict format for matching engine
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

    # Use matching engine
    matches = await _matching_engine.match_supply_to_demands(
        supply=supply_info,
        demands=demands,
        min_score=0.3,
        max_results=10,
    )

    # Format response
    results = []
    for match in matches:
        demand = next((d for d in demands if d.get('id') == match.demand_id), None)
        if demand:
            # Get demand agent info
            demand_agent = db_get_agent(demand.get('agent_id', ''))
            results.append({
                "opportunity_id": match.match_id,
                "counterpart_agent_id": demand.get('agent_id', ''),
                "counterpart_name": demand_agent.get('name', 'Unknown') if demand_agent else 'Unknown',
                "opportunity_type": "demand",
                "details": demand,
                "match_score": match.score.to_dict(),
                "status": "discovered",
                "created_at": match.created_at,
            })

    return results


@router.post("/search-suppliers")
async def search_suppliers(
    request: SearchSuppliersRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Search for suppliers that match the agent's requirements.

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

    # Get demand from database
    demands = db_search_demands()
    agent_demands = [d for d in demands if d.get('agent_id') == request.agent_id]

    # Build demand info from request
    demand_info = {
        "id": request.agent_id,
        "agent_id": request.agent_id,
        "required_skills": request.required_skills,
        "budget_range": {
            "min": request.budget_min or 0,
            "max": request.budget_max or 10000,
        },
        "description": "",
    }

    # Get all AI agents as potential suppliers
    all_agents = db_get_all_agents()

    # Filter for active agents with relevant capabilities
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

            if any(cap.lower() in [c.lower() for c in agent_capabilities] for cap in request.required_skills):
                suppliers.append({
                    "id": agent.get('agent_id'),
                    "agent_id": agent.get('agent_id'),
                    "name": agent.get('name'),
                    "capabilities": agent_capabilities,
                    "skills": agent_skills,
                    "price": agent.get('stake', 100) / 10,  # Estimate price from stake
                    "reputation": agent.get('reputation', 0.5),
                    "availability": "available" if agent.get('status') == 'online' else "busy",
                    "description": "",
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
            agent_id = service_dict.get('agent_id', '') if isinstance(service_dict, dict) else service['agent_id']
            if agent_id:
                agent_ids.add(agent_id)

        # Load all agents in one query
        agents_by_id: Dict[str, Any] = {}
        if agent_ids:
            placeholders = ','.join(['?' for _ in agent_ids])
            cursor.execute(f'SELECT * FROM ai_agents WHERE agent_id IN ({placeholders})', list(agent_ids))
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

            if any(cap.lower() in [s.lower() for s in service_skills] for cap in request.required_skills):
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
                            "price": service_dict.get('price', 100) if isinstance(service_dict, dict) else service['price'],
                            "reputation": service_agent.get('reputation', 0.5),
                            "availability": "available",
                            "description": service_dict.get('description', '') if isinstance(service_dict, dict) else service['description'],
                        })

    # Use matching engine
    matches = await _matching_engine.match_demand_to_supplies(
        demand=demand_info,
        supplies=suppliers,
        min_score=0.3,
        max_results=10,
    )

    # Format response
    results = []
    for match in matches:
        supply = next((s for s in suppliers if s.get('id') == match.supply_id), None)
        if supply:
            results.append({
                "opportunity_id": match.match_id,
                "counterpart_agent_id": supply.get('agent_id', ''),
                "counterpart_name": supply.get('name', 'Unknown'),
                "opportunity_type": "supply",
                "details": {
                    "capabilities": supply.get('capabilities', []),
                    "skills": supply.get('skills', []),
                    "price_per_request": supply.get('price', 100),
                    "reputation": supply.get('reputation', 0.5),
                },
                "match_score": match.score.to_dict(),
                "status": "discovered",
                "created_at": match.created_at,
            })

    return results


@router.post("/negotiate")
async def initiate_negotiation(
    request: NegotiationRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified)
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
    user: Dict[str, Any] = Depends(get_current_user_unified)
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
    user: Dict[str, Any] = Depends(get_current_user_unified)
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
    user: Dict[str, Any] = Depends(require_stake_unified(100))
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
    user: Dict[str, Any] = Depends(get_current_user_unified)
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
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Get all opportunities for the authenticated agent.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    agent_id = user.get('agent_id') or user.get('user_id')
    # In production, filter by agent_id
    return []


@router.get("/stats")
async def get_matching_stats(
    user: Dict[str, Any] = Depends(get_current_user_unified)
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
