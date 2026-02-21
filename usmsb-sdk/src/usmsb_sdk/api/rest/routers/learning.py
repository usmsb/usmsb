"""
Proactive Learning API endpoints.
"""

import json
from typing import Any, Dict

from fastapi import APIRouter, Query

from usmsb_sdk.api.database import (
    get_agent as db_get_agent,
    get_ai_agent as db_get_ai_agent,
    get_all_ai_agents as db_get_all_ai_agents,
    get_metrics as db_get_metrics,
)

router = APIRouter(prefix="/learning", tags=["Proactive Learning"])

# In-memory storage for learning data
learning_store: Dict[str, Any] = {}


@router.post("/analyze")
async def analyze_agent_learning(agent_id: str = Query(...)):
    """Analyze agent's match history for learning insights."""
    # Get agent data from database
    agent_data = db_get_ai_agent(agent_id)
    if not agent_data:
        agent_data = db_get_agent(agent_id)

    if agent_data:
        capabilities = json.loads(agent_data.get("capabilities", "[]")) if isinstance(agent_data.get("capabilities"), str) else agent_data.get("capabilities", [])
        reputation = agent_data.get("reputation", 0.5)

        return {
            "agent_id": agent_id,
            "insights_count": len(capabilities),
            "success_patterns": [f"Strong performance in {cap}" for cap in capabilities[:3]] if capabilities else ["No historical patterns yet"],
            "recommendations": [
                "Build reputation through successful transactions",
                f"Leverage your {', '.join(capabilities[:2])} capabilities" if len(capabilities) >= 2 else "Add more capabilities to your profile",
            ],
            "reputation": reputation,
            "status": agent_data.get("status", "unknown"),
        }

    return {
        "agent_id": agent_id,
        "insights_count": 0,
        "success_patterns": [],
        "recommendations": ["Register as an agent to start learning"],
    }


@router.get("/insights/{agent_id}")
async def get_learning_insights(agent_id: str):
    """Get learning insights for an agent."""
    # Get agent data from database
    agent_data = db_get_ai_agent(agent_id)
    if not agent_data:
        agent_data = db_get_agent(agent_id)

    insights = []
    if agent_data:
        capabilities = json.loads(agent_data.get("capabilities", "[]")) if isinstance(agent_data.get("capabilities"), str) else agent_data.get("capabilities", [])
        reputation = agent_data.get("reputation", 0.5)

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


@router.get("/strategy/{agent_id}")
async def get_optimized_strategy(agent_id: str):
    """Get optimized matching strategy for an agent."""
    # Get agent data from database
    agent_data = db_get_ai_agent(agent_id)
    if not agent_data:
        agent_data = db_get_agent(agent_id)

    if agent_data:
        capabilities = json.loads(agent_data.get("capabilities", "[]")) if isinstance(agent_data.get("capabilities"), str) else agent_data.get("capabilities", [])
        reputation = agent_data.get("reputation", 0.5)
        stake = agent_data.get("stake", 0)

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
            },
        }

    return {
        "agent_id": agent_id,
        "strategy": {
            "preferred_partner_types": [],
            "optimal_price_range": {"min": 0, "max": 0},
            "recommended_negotiation_strategy": "none",
            "best_contact_timing": "none",
        },
    }


@router.get("/market/{agent_id}")
async def get_market_insight(agent_id: str):
    """Get market insights for an agent."""
    # Get environment state for market insights
    all_agents = db_get_all_ai_agents()
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
    for agent in all_agents:
        skills = json.loads(agent.get('skills', '[]')) if isinstance(agent.get('skills'), str) else agent.get('skills', [])
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
    }
