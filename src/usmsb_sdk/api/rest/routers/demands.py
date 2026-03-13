"""
Demand management endpoints.

Authentication:
- create: Requires authentication (no stake)
- list: Public (no auth)
- delete: Requires authentication + ownership
"""

from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query, status, Depends

from usmsb_sdk.api.database import (
    get_db,
    get_agent as db_get_agent,
    create_demand as db_create_demand,
    search_demands as db_search_demands,
)
from usmsb_sdk.api.cache import cache_manager, generate_cache_key
from usmsb_sdk.api.rest.schemas.demand import DemandCreate
from usmsb_sdk.api.rest.services.utils import safe_json_loads
from usmsb_sdk.api.rest.unified_auth import (
    get_current_user_unified,
    verify_agent_access,
)

router = APIRouter(prefix="/demands", tags=["Demands"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_demand_endpoint(
    demand_create: DemandCreate,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Create a new demand.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - No stake required
    """
    # Use authenticated agent's ID
    agent_id = user.get('agent_id') or user.get('user_id')

    demand_data = {
        'agent_id': agent_id,
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

    # 失效demands缓存
    cache_manager.demands.invalidate_prefix("demands:")

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
    """List all demands.

    Results are cached for 60 seconds.
    """
    # 生成缓存键
    cache_key = generate_cache_key("demands", agent_id=agent_id, category=category, limit=limit)

    # 尝试从缓存获取
    cached = cache_manager.demands.get(cache_key)
    if cached is not None:
        return cached

    # 从数据库查询
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

    # 设置缓存 (60秒)
    cache_manager.demands.set(cache_key, result, ttl=60)

    return result


@router.delete("/{demand_id}")
async def delete_demand(
    demand_id: str,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Delete a demand.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Must be the owner of the demand
    """
    agent_id = user.get('agent_id') or user.get('user_id')
    with get_db() as conn:
        cursor = conn.cursor()

        # First check if demand exists and get owner
        cursor.execute('SELECT agent_id FROM demands WHERE id = ?', (demand_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Demand not found")

        # Verify ownership
        if row['agent_id'] != agent_id:
            raise HTTPException(
                status_code=403,
                detail="You can only delete your own demands"
            )

        # Delete the demand
        cursor.execute('DELETE FROM demands WHERE id = ?', (demand_id,))

    # 失效demands缓存
    cache_manager.demands.invalidate_prefix("demands:")

    return {"status": "deleted", "demand_id": demand_id}
