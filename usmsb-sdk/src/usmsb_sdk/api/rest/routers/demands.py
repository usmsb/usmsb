"""
Demand management endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from usmsb_sdk.api.database import (
    get_db,
    get_agent as db_get_agent,
    create_demand as db_create_demand,
    search_demands as db_search_demands,
)
from usmsb_sdk.api.rest.schemas.demand import DemandCreate
from usmsb_sdk.api.rest.services.utils import safe_json_loads

router = APIRouter(prefix="/demands", tags=["Demands"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_demand_endpoint(demand_create: DemandCreate):
    """Create a new demand."""
    # Check if agent exists
    agent = db_get_agent(demand_create.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    demand_data = {
        'agent_id': demand_create.agent_id,
        'title': demand_create.title,
        'description': demand_create.description,
        'category': demand_create.category,
        'required_skills': demand_create.required_skills,
        'budget_min': demand_create.budget_min,
        'budget_max': demand_create.budget_max,
        'deadline': demand_create.deadline,
        'priority': demand_create.priority,
        'quality_requirements': demand_create.quality_requirements,
        'status': 'active',
    }

    demand = db_create_demand(demand_data)
    return {
        "id": demand.get('id'),
        "agent_id": demand.get('agent_id'),
        "title": demand.get('title'),
        "status": demand.get('status'),
        "created_at": demand.get('created_at'),
    }


@router.get("")
async def list_demands(
    agent_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """List all demands."""
    demands = db_search_demands()

    if agent_id:
        demands = [d for d in demands if d.get('agent_id') == agent_id]
    if category:
        demands = [d for d in demands if d.get('category') == category]

    result = []
    for d in demands[:limit]:
        required_skills = safe_json_loads(d.get('required_skills', '[]'), [])
        result.append({
            "id": d.get('id'),
            "agent_id": d.get('agent_id'),
            "title": d.get('title'),
            "description": d.get('description'),
            "category": d.get('category'),
            "required_skills": required_skills,
            "budget_min": d.get('budget_min'),
            "budget_max": d.get('budget_max'),
            "status": d.get('status'),
            "created_at": d.get('created_at'),
        })
    return result


@router.delete("/{demand_id}")
async def delete_demand(demand_id: str):
    """Delete a demand."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM demands WHERE id = ?', (demand_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Demand not found")
    return {"status": "deleted"}
