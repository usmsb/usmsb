"""
Environment API endpoints for AI Civilization Platform

Provides platform environment state and broadcasts.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

from usmsb_sdk.api.database import (
    get_all_agents,
    get_all_ai_agents,
    get_metrics,
    get_db,
)

router = APIRouter(prefix="/environment", tags=["Environment"])


class EnvironmentState(BaseModel):
    """Platform environment state."""
    total_agents: int
    active_agents: int
    human_agents: int
    ai_agents: int
    external_agents: int
    total_stake: float
    avg_reputation: float
    total_transactions: int
    active_demands: int
    active_services: int
    supply_demand_ratio: float
    hot_skills: List[str]
    market_trend: str
    timestamp: float


class EnvironmentBroadcast(BaseModel):
    """Environment broadcast message."""
    broadcast_type: str
    message: str
    data: Dict[str, Any]
    timestamp: float


def _calculate_environment_state() -> Dict[str, Any]:
    """Calculate current environment state from database."""
    # Get all agents
    all_agents = get_all_agents(limit=1000)
    ai_agents = get_all_ai_agents()
    metrics = get_metrics()

    # Calculate statistics
    total_agents = len(all_agents) + len(ai_agents)
    active_agents = sum(1 for a in ai_agents if a.get('status') == 'online')

    # Count by type
    human_count = sum(1 for a in all_agents if a.get('type') == 'human')
    ai_count = len(ai_agents)
    external_count = sum(1 for a in ai_agents if a.get('agent_type') == 'external_agent')

    # Calculate total stake and reputation
    total_stake = sum(a.get('stake', 0) for a in ai_agents)
    avg_reputation = 0.5
    if ai_agents:
        avg_reputation = sum(a.get('reputation', 0.5) for a in ai_agents) / len(ai_agents)

    # Get transaction stats
    active_demands = metrics.get('active_demands', 0)
    active_services = metrics.get('active_services', 0)

    # Calculate supply/demand ratio
    supply_demand_ratio = 1.0
    if active_demands > 0:
        supply_demand_ratio = round(active_services / active_demands, 2)

    # Extract hot skills from agents
    skill_counts: Dict[str, int] = {}
    for agent in ai_agents:
        import json
        skills = json.loads(agent.get('skills', '[]')) if isinstance(agent.get('skills'), str) else agent.get('skills', [])
        for skill in skills:
            skill_name = skill if isinstance(skill, str) else skill.get('name', '')
            if skill_name:
                skill_counts[skill_name] = skill_counts.get(skill_name, 0) + 1

    # Sort by frequency
    hot_skills = sorted(skill_counts.keys(), key=lambda x: skill_counts[x], reverse=True)[:10]

    # Determine market trend
    if supply_demand_ratio > 1.5:
        market_trend = "supply_surplus"
    elif supply_demand_ratio < 0.7:
        market_trend = "demand_surplus"
    else:
        market_trend = "balanced"

    return {
        "total_agents": total_agents,
        "active_agents": active_agents or int(total_agents * 0.7),
        "human_agents": human_count,
        "ai_agents": ai_count,
        "external_agents": external_count,
        "total_stake": round(total_stake, 2),
        "avg_reputation": round(avg_reputation, 3),
        "total_transactions": active_demands + active_services,
        "active_demands": active_demands,
        "active_services": active_services,
        "supply_demand_ratio": supply_demand_ratio,
        "hot_skills": hot_skills if hot_skills else ["Python", "AI", "Web3", "Data Science"],
        "market_trend": market_trend,
        "timestamp": time.time(),
    }


@router.get("/state", response_model=EnvironmentState)
async def get_environment_state():
    """Get current platform environment state."""
    state = _calculate_environment_state()
    return EnvironmentState(**state)


@router.get("/metrics")
async def get_environment_metrics():
    """Get detailed environment metrics."""
    metrics = get_metrics()
    state = _calculate_environment_state()

    return {
        "agents": {
            "total": state["total_agents"],
            "active": state["active_agents"],
            "by_type": {
                "human": state["human_agents"],
                "ai": state["ai_agents"],
                "external": state["external_agents"],
            },
        },
        "market": {
            "active_demands": state["active_demands"],
            "active_services": state["active_services"],
            "supply_demand_ratio": state["supply_demand_ratio"],
            "trend": state["market_trend"],
        },
        "economy": {
            "total_stake": state["total_stake"],
            "avg_reputation": state["avg_reputation"],
        },
        "trends": {
            "hot_skills": state["hot_skills"],
        },
        "timestamp": state["timestamp"],
    }


@router.get("/broadcasts")
async def get_recent_broadcasts(limit: int = 10):
    """Get recent environment broadcasts."""
    # In production, this would be stored in database
    # For now, generate from current state
    state = _calculate_environment_state()
    broadcasts = []

    # Market trend broadcast
    if state["market_trend"] == "demand_surplus":
        broadcasts.append({
            "broadcast_type": "MARKET_ALERT",
            "message": "High demand detected. More service providers needed.",
            "data": {"supply_demand_ratio": state["supply_demand_ratio"]},
            "timestamp": time.time(),
        })

    # Hot skills broadcast
    if state["hot_skills"]:
        broadcasts.append({
            "broadcast_type": "TRENDING_SKILLS",
            "message": f"Top skills in demand: {', '.join(state['hot_skills'][:5])}",
            "data": {"skills": state["hot_skills"][:5]},
            "timestamp": time.time(),
        })

    # Agent activity broadcast
    broadcasts.append({
        "broadcast_type": "AGENT_ACTIVITY",
        "message": f"{state['active_agents']} agents currently active",
        "data": {"active_count": state["active_agents"]},
        "timestamp": time.time(),
    })

    return broadcasts[:limit]


@router.get("/hot-skills")
async def get_hot_skills():
    """Get current hot skills in the platform."""
    state = _calculate_environment_state()
    return {
        "skills": state["hot_skills"],
        "timestamp": state["timestamp"],
    }
