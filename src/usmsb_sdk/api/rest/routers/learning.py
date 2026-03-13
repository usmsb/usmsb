"""
Proactive Learning API endpoints.

Authentication: All endpoints require authentication (no stake required)
"""

import json
from typing import Any, Dict

from fastapi import APIRouter, Query, Depends

from usmsb_sdk.api.database import (
    get_agent as db_get_agent,
    get_all_agents as db_get_all_agents,
    get_metrics as db_get_metrics,
)
from usmsb_sdk.api.rest.unified_auth import get_current_user_unified

router = APIRouter(prefix="/learning", tags=["Proactive Learning"])

# In-memory storage for learning data
learning_store: Dict[str, Any] = {}


@router.post("/analyze")
async def analyze_agent_learning(user: Dict[str, Any] = Depends(get_current_user_unified)):
    """Analyze agent's match history for learning insights.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    agent_id = user.get('agent_id') or user.get('user_id')

    capabilities = user.get('capabilities', [])
    reputation = user.get('staked_amount', 0) / 1000 + 0.5  # Estimate from stake

    return {
        "agent_id": agent_id,
        "insights_count": len(capabilities),
        "success_patterns": [f"Strong performance in {cap}" for cap in capabilities[:3]] if capabilities else ["No historical patterns yet"],
        "recommendations": [
            "Build reputation through successful transactions",
            f"Leverage your {', '.join(capabilities[:2])} capabilities" if len(capabilities) >= 2 else "Add more capabilities to your profile",
        ],
        "reputation": min(reputation, 1.0),
        "stake_tier": user.get('stake_tier', 'NONE'),
        "status": user.get('status', 'unknown'),
    }


@router.get("/insights")
async def get_learning_insights(user: Dict[str, Any] = Depends(get_current_user_unified)):
    """Get learning insights for the authenticated agent.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    agent_id = user.get('agent_id') or user.get('user_id')

    capabilities = user.get('capabilities', [])
    reputation = min(user.get('staked_amount', 0) / 1000 + 0.5, 1.0)

    insights = []
    for i, cap in enumerate(capabilities[:5]):
        insights.append({
            "insight_id": f"insight-{i+1}",
            "category": "capability_analysis",
            "title": f"{cap} Performance",
            "description": f"Your {cap} capability has a reputation score of {reputation:.0%}",
            "confidence": reputation,
        })

    return {
        "agent_id": agent_id,
        "insights": insights if insights else [{"insight_id": "none", "category": "info", "title": "No insights yet", "description": "Complete transactions to generate insights", "confidence": 0.0}],
    }


@router.get("/strategy")
async def get_optimized_strategy(user: Dict[str, Any] = Depends(get_current_user_unified)):
    """Get optimized matching strategy for the authenticated agent.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    agent_id = user.get('agent_id') or user.get('user_id')

    capabilities = user.get('capabilities', [])
    reputation = min(user.get('staked_amount', 0) / 1000 + 0.5, 1.0)
    stake = user.get('staked_amount', 0)

    # Calculate optimal price range based on reputation and stake
    min_price = max(10, int(stake * 0.1))
    max_price = max(min_price + 50, int(stake * 0.5))

    return {
        "agent_id": agent_id,
        "strategy": {
            "preferred_partner_types": ["human", "ai_agent"],
            "optimal_price_range": {"min": min_price, "max": max_price},
            "recommended_negotiation_strategy": "balanced" if reputation > 0.5 else "conservative",
            "best_contact_timing": "anytime",
            "focus_capabilities": capabilities[:3] if capabilities else [],
            "stake_tier": user.get('stake_tier', 'NONE'),
        },
    }


@router.get("/market")
async def get_market_insight(user: Dict[str, Any] = Depends(get_current_user_unified)):
    """Get market insights for the authenticated agent.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    agent_id = user.get('agent_id') or user.get('user_id')

    # Get environment state for market insights
    all_agents = db_get_all_agents()
    metrics = db_get_metrics()

    total_agents = len(all_agents)
    active_demands = metrics.get('active_demands', 0)
    active_services = metrics.get('active_services', 0)

    # Calculate supply/demand ratio
    supply_demand_ratio = 1.0
    if active_demands > 0:
        supply_demand_ratio = round(active_services / active_demands, 2)

    # Determine market state
    if supply_demand_ratio > 1.5:
        demand_level = "low"
        supply_level = "high"
    elif supply_demand_ratio < 0.7:
        demand_level = "high"
        supply_level = "low"
    else:
        demand_level = "medium"
        supply_level = "medium"

    # Extract hot skills
    skill_counts: Dict[str, int] = {}
    for agt in all_agents:
        skills = json.loads(agt.get('skills', '[]')) if isinstance(agt.get('skills'), str) else agt.get('skills', [])
        for skill in skills:
            skill_name = skill if isinstance(skill, str) else skill.get('name', '')
            if skill_name:
                skill_counts[skill_name] = skill_counts.get(skill_name, 0) + 1

    hot_skills = sorted(skill_counts.keys(), key=lambda x: skill_counts[x], reverse=True)[:5]

    return {
        "agent_id": agent_id,
        "demand_level": demand_level,
        "supply_level": supply_level,
        "opportunity_areas": hot_skills if hot_skills else ["No data yet"],
        "recommendations": [f"Consider offering {skill} services" for skill in hot_skills[:2]] if hot_skills else ["Register to see personalized recommendations"],
        "total_agents": total_agents,
        "active_demands": active_demands,
        "active_services": active_services,
        "your_tier": user.get('stake_tier', 'NONE'),
    }
