"""
Collaborative Matching API endpoints.
"""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from usmsb_sdk.api.database import (
    create_collaboration as db_create_collaboration,
    get_collaborations as db_get_collaborations,
    get_collaboration as db_get_collaboration,
)
from usmsb_sdk.api.rest.schemas.collaboration import CollaborationCreateRequest

router = APIRouter(prefix="/collaborations", tags=["Collaborations"])


@router.post("")
async def create_collaboration_endpoint(request: CollaborationCreateRequest):
    """Create a new collaboration session."""
    session_id = f"collab-{int(datetime.now().timestamp() * 1000)}"

    # Create goal data
    goal_data = {
        "id": f"goal-{session_id}",
        "name": "Collaboration Goal",
        "description": request.goal_description,
    }

    # Create plan data
    plan_data = {
        "plan_id": f"plan-{session_id}",
        "mode": request.collaboration_mode,
        "roles": [
            {
                "role_id": f"role-{i}",
                "role_type": role_type,
                "required_skills": [request.required_skills[i]] if i < len(request.required_skills) else [],
                "status": "pending",
            }
            for i, role_type in enumerate(["primary", "specialist", "support"])
        ],
    }

    # Save to database
    collab_data = {
        "session_id": session_id,
        "goal": json.dumps(goal_data),
        "plan": plan_data,
        "participants": [],
        "status": "analyzing",
        "coordinator_id": request.coordinator_agent_id,
    }

    db_create_collaboration(collab_data)

    return {
        "session_id": session_id,
        "goal": goal_data,
        "plan": plan_data,
        "status": "analyzing",
        "participants": [],
        "coordinator_id": request.coordinator_agent_id,
    }


@router.get("")
async def get_collaborations_endpoint(status: Optional[str] = Query(None)):
    """Get all collaboration sessions."""
    sessions = db_get_collaborations()

    # Parse JSON fields
    result = []
    for s in sessions:
        session_data = dict(s)
        if isinstance(session_data.get('goal'), str):
            session_data['goal'] = json.loads(session_data['goal'])
        if isinstance(session_data.get('plan'), str):
            session_data['plan'] = json.loads(session_data['plan'])
        if isinstance(session_data.get('participants'), str):
            session_data['participants'] = json.loads(session_data['participants'])

        # Filter by status if provided
        if status and session_data.get('status') != status:
            continue
        result.append(session_data)

    return result


@router.get("/{session_id}")
async def get_collaboration_endpoint(session_id: str):
    """Get a specific collaboration session."""
    session = db_get_collaboration(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Collaboration not found")

    session_data = dict(session)
    if isinstance(session_data.get('goal'), str):
        session_data['goal'] = json.loads(session_data['goal'])
    if isinstance(session_data.get('plan'), str):
        session_data['plan'] = json.loads(session_data['plan'])
    if isinstance(session_data.get('participants'), str):
        session_data['participants'] = json.loads(session_data['participants'])

    return session_data


@router.post("/{session_id}/execute")
async def execute_collaboration(session_id: str):
    """Execute a collaboration session."""
    session = db_get_collaboration(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Collaboration not found")

    # Update status in database
    # Note: Would need to add update_collaboration function to database.py
    session_data = dict(session)
    session_data["status"] = "executing"
    session_data["started_at"] = datetime.now().timestamp()

    return session_data


@router.get("/stats")
async def get_collaboration_stats():
    """Get collaboration statistics."""
    sessions = db_get_collaborations()

    total = len(sessions)
    active = sum(1 for s in sessions if s.get("status") in ["analyzing", "organizing", "executing", "integrating"])
    completed = sum(1 for s in sessions if s.get("status") == "completed")
    failed = sum(1 for s in sessions if s.get("status") == "failed")

    return {
        "total_sessions": total,
        "active_sessions": active,
        "completed_sessions": completed,
        "failed_sessions": failed,
        "success_rate": completed / total if total > 0 else 0,
    }
