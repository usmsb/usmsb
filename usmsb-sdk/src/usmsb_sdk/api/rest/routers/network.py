"""
Network Explorer API endpoints.
"""

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query

from usmsb_sdk.api.database import (
    get_all_ai_agents as db_get_all_ai_agents,
)
from usmsb_sdk.api.rest.schemas.matching import (
    NetworkExploreRequest,
    RecommendationRequest,
)

router = APIRouter(prefix="/network", tags=["Network Explorer"])

# In-memory storage for network stats
network_stats_store: Dict[str, Any] = {}


@router.post("/explore")
async def explore_network(request: NetworkExploreRequest):
    """Explore the network to discover new agents."""
    # Get all AI agents from database
    all_agents = db_get_all_ai_agents()

    discovered = []
    for agent in all_agents:
        # Skip the requesting agent
        if agent.get("agent_id") == request.agent_id:
            continue

        # Parse capabilities
        capabilities = json.loads(agent.get("capabilities", "[]")) if isinstance(agent.get("capabilities"), str) else agent.get("capabilities", [])
        skills = json.loads(agent.get("skills", "[]")) if isinstance(agent.get("skills"), str) else agent.get("skills", [])

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
            "agent_id": agent.get("agent_id"),
            "agent_name": agent.get("name"),
            "capabilities": capabilities,
            "skills": skills,
            "reputation": agent.get("reputation", 0.5),
            "status": agent.get("status", "offline"),
        })

        # Limit results
        if len(discovered) >= 20:
            break

    return discovered


@router.post("/recommendations")
async def request_recommendations(request: RecommendationRequest):
    """Request recommendations from the network."""
    # Get all AI agents from database
    all_agents = db_get_all_ai_agents()

    recommendations = []
    for agent in all_agents:
        # Skip the requesting agent
        if agent.get("agent_id") == request.agent_id:
            continue

        # Parse capabilities
        capabilities = json.loads(agent.get("capabilities", "[]")) if isinstance(agent.get("capabilities"), str) else agent.get("capabilities", [])

        # Calculate capability match score
        capability_match = 0.0
        target_lower = request.target_capability.lower()
        for cap in capabilities:
            if isinstance(cap, str) and target_lower in cap.lower():
                capability_match = min(1.0, 0.7 + agent.get("reputation", 0.5) * 0.3)
                break

        # Skip if no capability match
        if capability_match == 0:
            continue

        trust_score = agent.get("reputation", 0.5)

        recommendations.append({
            "recommended_agent_id": agent.get("agent_id"),
            "recommended_agent_name": agent.get("name"),
            "capability_match": round(capability_match, 2),
            "trust_score": round(trust_score, 2),
            "reason": "High reputation agent with matching capabilities" if trust_score > 0.7 else "Matches your capability requirements",
        })

    # Sort by capability match then trust score
    recommendations.sort(key=lambda x: (x["capability_match"], x["trust_score"]), reverse=True)

    return recommendations[:10]


@router.get("/stats")
async def get_network_stats(agent_id: str = Query(...)):
    """Get network exploration statistics."""
    # Get all AI agents from database
    all_agents = db_get_all_ai_agents()

    total_agents = len(all_agents)
    active_agents = sum(1 for a in all_agents if a.get("status") == "online")

    # Calculate trusted agents (reputation >= 0.7)
    trusted_agents = sum(1 for a in all_agents if a.get("reputation", 0) >= 0.7)

    return {
        "total_explorations": total_agents,  # Total agents discovered
        "total_discovered": total_agents,
        "network_size": active_agents,  # Currently active agents
        "trusted_agents": trusted_agents,
    }
