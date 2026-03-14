"""
AI Agent Services endpoints.

Stake Requirements:
- register_service: 100 VIBE minimum
- list/get services: No stake required
- delete service: Requires authentication and ownership
"""

import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from usmsb_sdk.api.cache import cache_manager, generate_cache_key
from usmsb_sdk.api.database import (
    create_service as db_create_service,
)
from usmsb_sdk.api.database import (
    get_db,
)
from usmsb_sdk.api.rest.unified_auth import (
    get_current_user_unified,
    require_stake_unified,
    verify_agent_access,
)

router = APIRouter(tags=["AI Agent Services", "Services"])


# ============================================================================
# Schemas
# ============================================================================

class AgentServiceCreate(BaseModel):
    """Schema for creating a service for an agent.

    This matches the fields sent by the Agent SDK (platform_client.py) and frontend (PublishService.tsx).
    """
    service_name: str
    service_type: str = "general"  # Also called 'category' in some places
    description: str = ""
    capabilities: list[str] = Field(default_factory=list)
    price: float = 0.0
    price_type: str = "hourly"  # hourly, fixed, negotiable
    availability: str = "24/7"  # full-time, part-time, always, limited


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/agents/{agent_id}/services")
async def register_agent_service(
    agent_id: str,
    service: AgentServiceCreate,
    user: dict[str, Any] = Depends(require_stake_unified(100))
):
    """Register a service provided by an AI Agent.

    This endpoint accepts a JSON body with service details.

    Requires:
        - X-API-Key header
        - X-Agent-ID header (must match agent_id in path)
        - Minimum 100 VIBE stake

    Args:
        agent_id: The ID of the agent offering this service
        service: Service details in JSON body

    Returns:
        Created service information
    """
    # Verify agent_id matches authenticated agent
    verify_agent_access(user, agent_id)

    # Generate service ID and timestamp
    service_id = f"svc_{uuid.uuid4().hex[:12]}"
    created_at = time.time()

    service_data = {
        "id": service_id,
        "agent_id": agent_id,
        "service_name": service.service_name,
        "description": service.description or f"Service: {service.service_name}",
        "category": service.service_type,
        "skills": json.dumps(service.capabilities),
        "price": service.price,
        "price_type": service.price_type,
        "availability": service.availability,
        "status": "active",
        "created_at": created_at,
    }

    # Save to database
    db_create_service(service_data)

    # 失效services缓存
    cache_manager.services.invalidate_prefix("services:")

    return {
        "success": True,
        "service_id": service_id,
        "message": "Service created successfully",
        "service": {
            "id": service_id,
            "agent_id": agent_id,
            "service_name": service.service_name,
            "description": service.description,
            "category": service.service_type,
            "capabilities": service.capabilities,
            "price": service.price,
            "price_type": service.price_type,
            "availability": service.availability,
            "status": "active",
            "created_at": created_at,
        }
    }


@router.get("/services")
async def list_services(
    agent_id: str | None = Query(None),
    category: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """List all services.

    Results are cached for 60 seconds.

    Args:
        agent_id: Filter by agent ID
        category: Filter by category
        limit: Maximum number of results

    Returns:
        List of services matching the filters
    """
    # 生成缓存键
    cache_key = generate_cache_key("services", agent_id=agent_id, category=category, limit=limit)

    # 尝试从缓存获取
    cached = cache_manager.services.get(cache_key)
    if cached is not None:
        return cached

    # 从数据库查询
    with get_db() as conn:
        cursor = conn.cursor()
        query = 'SELECT * FROM services WHERE status = "active"'
        params = []

        if agent_id:
            query += ' AND agent_id = ?'
            params.append(agent_id)
        if category:
            query += ' AND category = ?'
            params.append(category)

        query += f' LIMIT {limit}'
        cursor.execute(query, params)
        services = [dict(row) for row in cursor.fetchall()]

    result = []
    for s in services:
        result.append({
            "id": s.get('id'),
            "agent_id": s.get('agent_id'),
            "service_name": s.get('service_name'),
            "description": s.get('description'),
            "category": s.get('category'),
            "skills": json.loads(s.get('skills', '[]')),
            "price": s.get('price'),
            "price_type": s.get('price_type'),
            "availability": s.get('availability'),
            "status": s.get('status'),
            "created_at": s.get('created_at'),
        })

    # 设置缓存 (60秒)
    cache_manager.services.set(cache_key, result, ttl=60)

    return result


@router.get("/services/{service_id}")
async def get_service(service_id: str):
    """Get a specific service by ID.

    Args:
        service_id: The service ID

    Returns:
        Service details
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM services WHERE id = ?', (service_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Service not found")

        s = dict(row)
        return {
            "id": s.get('id'),
            "agent_id": s.get('agent_id'),
            "service_name": s.get('service_name'),
            "description": s.get('description'),
            "category": s.get('category'),
            "skills": json.loads(s.get('skills', '[]')),
            "price": s.get('price'),
            "price_type": s.get('price_type'),
            "availability": s.get('availability'),
            "status": s.get('status'),
            "created_at": s.get('created_at'),
        }


@router.delete("/services/{service_id}")
async def delete_service(
    service_id: str,
    user: dict[str, Any] = Depends(get_current_user_unified)
):
    """Delete a service (soft delete by setting status to 'inactive').

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Must be the owner of the service

    Args:
        service_id: The service ID to delete

    Returns:
        Success message
    """
    agent_id = user.get('agent_id') or user.get('user_id')
    with get_db() as conn:
        cursor = conn.cursor()

        # First check if service exists and get owner
        cursor.execute('SELECT agent_id FROM services WHERE id = ?', (service_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Service not found")

        # Verify ownership
        service_owner = row['agent_id']
        if service_owner != agent_id:
            raise HTTPException(
                status_code=403,
                detail="You can only delete your own services"
            )

        # Soft delete
        cursor.execute('UPDATE services SET status = ? WHERE id = ?', ('inactive', service_id))
        conn.commit()

    # Invalidate cache
    cache_manager.services.invalidate_prefix("services:")

    return {"success": True, "message": f"Service {service_id} deleted"}
