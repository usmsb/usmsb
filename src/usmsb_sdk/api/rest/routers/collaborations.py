"""
Collaborative Matching API endpoints.

Stake Requirements:
- create: 100 VIBE minimum
- join: No stake required
- contribute: 100 VIBE minimum
- execute: 100 VIBE minimum
- list/get/stats: No stake required
"""

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from usmsb_sdk.api.database import (
    create_collaboration as db_create_collaboration,
)
from usmsb_sdk.api.database import (
    get_collaboration as db_get_collaboration,
)
from usmsb_sdk.api.database import (
    get_collaborations as db_get_collaborations,
)
from usmsb_sdk.api.rest.schemas.collaboration import CollaborationCreateRequest
from usmsb_sdk.api.rest.unified_auth import (
    get_current_user_unified,
    require_stake_unified,
)

router = APIRouter(prefix="/collaborations", tags=["Collaborations"])


@router.post("")
async def create_collaboration_endpoint(
    request: CollaborationCreateRequest,
    user: dict[str, Any] = Depends(require_stake_unified(100))
):
    """Create a new collaboration session.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Minimum 100 VIBE stake
    """
    agent_id = user.get('agent_id') or user.get('user_id')
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
        "creator_id": agent_id,
    }

    db_create_collaboration(collab_data)

    return {
        "session_id": session_id,
        "goal": goal_data,
        "plan": plan_data,
        "status": "analyzing",
        "participants": [],
        "coordinator_id": request.coordinator_agent_id,
        "creator_id": agent_id,
    }


@router.get("")
async def get_collaborations_endpoint(status: str | None = Query(None)):
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
async def execute_collaboration(
    session_id: str,
    user: dict[str, Any] = Depends(require_stake_unified(100))
):
    """Execute a collaboration session.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Minimum 100 VIBE stake
    """
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


@router.post("/{session_id}/join")
async def join_collaboration(
    session_id: str,
    user: dict[str, Any] = Depends(get_current_user_unified)
):
    """Join a collaboration session.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - No stake required
    """
    session = db_get_collaboration(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Collaboration not found")

    # Parse participants
    participants = session.get('participants', [])
    if isinstance(participants, str):
        participants = json.loads(participants)

    # Check if already joined
    agent_id = user.get('agent_id') or user.get('user_id')
    for p in participants:
        if p.get('agent_id') == agent_id:
            raise HTTPException(status_code=400, detail="Already joined this collaboration")

    # Add agent to participants
    participants.append({
        "agent_id": agent_id,
        "joined_at": datetime.now().timestamp(),
        "status": "active",
        "contributions": []
    })

    # Update session
    with __import__('usmsb_sdk.api.database', fromlist=['get_db']).get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE collaborations SET participants = ?, updated_at = ? WHERE session_id = ?',
            (json.dumps(participants), datetime.now().timestamp(), session_id)
        )

    return {
        "session_id": session_id,
        "agent_id": agent_id,
        "status": "joined",
        "participants": participants
    }


@router.post("/{session_id}/contribute")
async def submit_contribution(
    session_id: str,
    contribution: dict = Body(...),
    user: dict[str, Any] = Depends(require_stake_unified(100))
):
    """Submit contribution to a collaboration session.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Minimum 100 VIBE stake
    """
    session = db_get_collaboration(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Collaboration not found")

    agent_id = user.get('agent_id') or user.get('user_id')

    # Parse participants
    participants = session.get('participants', [])
    if isinstance(participants, str):
        participants = json.loads(participants)

    # Find the agent in participants
    found = False
    for p in participants:
        if p.get('agent_id') == agent_id:
            found = True
            if 'contributions' not in p:
                p['contributions'] = []
            p['contributions'].append({
                "content": contribution,
                "submitted_at": datetime.now().timestamp()
            })
            break

    if not found:
        raise HTTPException(status_code=400, detail="Must join collaboration before contributing")

    # Update session
    with __import__('usmsb_sdk.api.database', fromlist=['get_db']).get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE collaborations SET participants = ?, updated_at = ? WHERE session_id = ?',
            (json.dumps(participants), datetime.now().timestamp(), session_id)
        )

    return {
        "session_id": session_id,
        "agent_id": agent_id,
        "contribution": contribution,
        "status": "contributed"
    }


@router.post("/{session_id}/complete")
async def complete_collaboration(
    session_id: str,
    user: dict[str, Any] = Depends(get_current_user_unified)
):
    """Complete a collaboration session.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    session = db_get_collaboration(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Collaboration not found")

    # Update status
    with __import__('usmsb_sdk.api.database', fromlist=['get_db']).get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE collaborations SET status = ?, updated_at = ? WHERE session_id = ?',
            ("completed", datetime.now().timestamp(), session_id)
        )

    return {
        "session_id": session_id,
        "status": "completed"
    }
