"""
AI Agent Services endpoints.
"""

import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from usmsb_sdk.api.database import (
    get_db,
    get_ai_agent as db_get_ai_agent,
    create_service as db_create_service,
)

router = APIRouter(tags=["AI Agent Services", "Services"])


@router.post("/agents/{agent_id}/services")
async def register_agent_service(
    agent_id: str,
    service_type: str,
    service_name: str,
    capabilities: List[str],
    price: float,
):
    """Register a service provided by an AI Agent."""
    # Check if agent exists
    agent = db_get_ai_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    service_data = {
        "agent_id": agent_id,
        "service_name": service_name,
        "description": f"Service: {service_name}",
        "category": service_type,
        "skills": json.dumps(capabilities),
        "price": price,
        "price_type": "hourly",
        "availability": "24/7",
    }

    # Save to database
    service = db_create_service(service_data)

    return {"success": True, "service": service}


@router.get("/services")
async def list_services(
    agent_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """List all services."""
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
            "status": s.get('status'),
            "created_at": s.get('created_at'),
        })
    return result
