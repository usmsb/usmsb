"""
Environment management endpoints.

Authentication:
- POST requires X-API-Key + X-Agent-ID headers
- GET endpoints are public for discovery
"""

from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Depends

from usmsb_sdk.api.database import (
    create_environment as db_create_environment,
    get_environment as db_get_environment,
    get_all_environments as db_get_all_environments,
)
from usmsb_sdk.api.rest.schemas.environment import EnvironmentCreate
from usmsb_sdk.api.rest.services.utils import safe_json_loads
from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
from usmsb_sdk.core.elements import Environment, EnvironmentType

router = APIRouter(prefix="/environments", tags=["Environments"])


@router.post("", status_code=201)
async def create_environment_endpoint(
    env_create: EnvironmentCreate,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """
    Create a new environment.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    try:
        env_type = EnvironmentType(env_create.type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid environment type. Valid types: {[t.value for t in EnvironmentType]}"
        )

    environment = Environment(
        name=env_create.name,
        type=env_type,
        state=env_create.state,
    )

    # Save to database
    env_data = {
        'id': environment.id,
        'name': environment.name,
        'type': environment.type.value,
        'state': environment.state,
    }
    db_create_environment(env_data)

    return {"id": environment.id, "name": environment.name, "type": environment.type.value}


@router.get("")
async def list_environments(limit: int = Query(100, ge=1, le=1000)):
    """List all environments."""
    # Get from database
    envs_data = db_get_all_environments(limit=limit)

    result = []
    for e in envs_data:
        state = safe_json_loads(e.get('state', '{}'), {})
        result.append({
            "id": e['id'],
            "name": e['name'],
            "type": e['type'],
            "state": state,
        })
    return result


@router.get("/{env_id}")
async def get_environment_endpoint(env_id: str):
    """Get an environment by ID."""
    env_data = db_get_environment(env_id)
    if not env_data:
        raise HTTPException(status_code=404, detail="Environment not found")

    state = safe_json_loads(env_data.get('state', '{}'), {})
    return {"id": env_data['id'], "name": env_data['name'], "type": env_data['type'], "state": state}
