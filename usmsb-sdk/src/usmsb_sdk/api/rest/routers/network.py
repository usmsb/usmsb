"""
Network Explorer API endpoints.

Authentication: All endpoints require authentication (no stake required)
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, Depends, Body

from usmsb_sdk.api.database import (
    get_all_agents as db_get_all_agents,
)
from usmsb_sdk.api.rest.schemas.matching import (
    NetworkExploreRequest,
    RecommendationRequest,
)
from usmsb_sdk.api.rest.unified_auth import get_current_user_unified

router = APIRouter(prefix="/network", tags=["Network Explorer"])

# In-memory storage for network stats
network_stats_store: Dict[str, Any] = {}


@router.post("/explore")
async def explore_network(
    request: NetworkExploreRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Explore the network to discover new agents.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    agent_id = user.get('agent_id') or user.get('user_id')

    # Get all AI agents from database
    all_agents = db_get_all_agents()

    discovered = []
    for agt in all_agents:
        # Skip the requesting agent
        if agt.get("agent_id") == agent_id:
            continue

        # Parse capabilities
        capabilities = json.loads(agt.get("capabilities", "[]")) if isinstance(agt.get("capabilities"), str) else agt.get("capabilities", [])
        skills = json.loads(agt.get("skills", "[]")) if isinstance(agt.get("skills"), str) else agt.get("skills", [])

        # Filter by target capabilities if specified
        if request.target_capabilities:
            # Check if agent has any of the requested capabilities
            has_capability = any(
                any(tc.lower() in c.lower() for c in capabilities)
                for tc in request.target_capabilities
            )
            if not has_capability:
                continue

        discovered.append({
            "agent_id": agt.get("agent_id"),
            "agent_name": agt.get("name"),
            "capabilities": capabilities,
            "skills": skills,
            "reputation": agt.get("reputation", 0.5),
            "status": agt.get("status", "offline"),
        })

        # Limit results
        if len(discovered) >= 20:
            break

    return discovered


@router.post("/recommendations")
async def request_recommendations(
    request: RecommendationRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Request recommendations from the network.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    agent_id = user.get('agent_id') or user.get('user_id')

    # Get all AI agents from database
    all_agents = db_get_all_agents()

    recommendations = []
    for agt in all_agents:
        # Skip the requesting agent
        if agt.get("agent_id") == agent_id:
            continue

        # Parse capabilities
        capabilities = json.loads(agt.get("capabilities", "[]")) if isinstance(agt.get("capabilities"), str) else agt.get("capabilities", [])

        # Calculate capability match score
        capability_match = 0.0
        target_lower = request.target_capability.lower()
        for cap in capabilities:
            if isinstance(cap, str) and target_lower in cap.lower():
                capability_match = min(1.0, 0.7 + agt.get("reputation", 0.5) * 0.3)
                break

        # Skip if no capability match
        if capability_match == 0:
            continue

        trust_score = agt.get("reputation", 0.5)

        recommendations.append({
            "recommended_agent_id": agt.get("agent_id"),
            "recommended_agent_name": agt.get("name"),
            "capability_match": round(capability_match, 2),
            "trust_score": round(trust_score, 2),
            "reason": "High reputation agent with matching capabilities" if trust_score > 0.7 else "Matches your capability requirements",
        })

    # Sort by capability match then trust score
    recommendations.sort(key=lambda x: (x["capability_match"], x["trust_score"]), reverse=True)

    return recommendations[:10]


@router.get("/stats")
async def get_network_stats(user: Dict[str, Any] = Depends(get_current_user_unified)):
    """Get network exploration statistics.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    agent_id = user.get('agent_id') or user.get('user_id')
    # Get all AI agents from database
    all_agents = db_get_all_agents()

    total_agents = len(all_agents)
    active_agents = sum(1 for a in all_agents if a.get("status") == "online")

    # Calculate trusted agents (reputation >= 0.7)
    trusted_agents = sum(1 for a in all_agents if a.get("reputation", 0) >= 0.7)

    return {
        "agent_id": agent_id,
        "total_explorations": total_agents,  # Total agents discovered
        "total_discovered": total_agents,
        "network_size": active_agents,  # Currently active agents
        "trusted_agents": trusted_agents,
        "your_tier": user.get('stake_tier', 'NONE'),
    }
