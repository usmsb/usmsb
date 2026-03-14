"""
Heartbeat endpoints for Agent Platform.

Provides heartbeat operations:
- Send heartbeat to indicate online status
- Get heartbeat status

Authentication: All endpoints require X-API-Key + X-Agent-ID headers.
"""

import time

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from usmsb_sdk.api.database import get_db, update_agent_heartbeat
from usmsb_sdk.api.rest.unified_auth import ErrorCode, get_current_user_unified

router = APIRouter(prefix="/heartbeat", tags=["Heartbeat"])

# Constants
DEFAULT_TTL = 90  # Default TTL in seconds (3x default heartbeat interval of 30s)
DEFAULT_HEARTBEAT_INTERVAL = 30  # Default heartbeat interval in seconds


# ==================== Request/Response Models ====================

class HeartbeatRequest(BaseModel):
    """Heartbeat request."""
    status: str = Field("online", description="Agent status: online, busy, offline")
    metadata: dict | None = Field(None, description="Optional metadata")


class HeartbeatResponse(BaseModel):
    """Heartbeat response."""
    success: bool = True
    agent_id: str
    status: str
    ttl_remaining: int
    last_heartbeat: float
    is_alive: bool
    message: str


class HeartbeatStatusResponse(BaseModel):
    """Heartbeat status response."""
    success: bool = True
    agent_id: str
    status: str
    last_heartbeat: float
    ttl_remaining: int
    is_alive: bool
    heartbeat_interval: int
    ttl: int


# ==================== Helper Functions ====================

def get_agent_heartbeat_info(agent_id: str) -> dict:
    """Get agent's heartbeat information from database."""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT status, last_heartbeat, heartbeat_interval, ttl
            FROM agents
            WHERE agent_id = ?
        """, (agent_id,))

        row = cursor.fetchone()
        if row:
            return dict(row)

    return {
        "status": "offline",
        "last_heartbeat": 0,
        "heartbeat_interval": DEFAULT_HEARTBEAT_INTERVAL,
        "ttl": DEFAULT_TTL
    }


def calculate_ttl_remaining(last_heartbeat: float, ttl: int) -> int:
    """Calculate remaining TTL in seconds."""
    now = time.time()
    elapsed = now - last_heartbeat
    remaining = ttl - elapsed
    return max(0, int(remaining))


def update_heartbeat_status(agent_id: str, new_status: str = "online") -> bool:
    """Update agent's heartbeat timestamp and status."""
    return update_agent_heartbeat(agent_id, new_status)


# ==================== Endpoints ====================

@router.post("", response_model=HeartbeatResponse)
async def send_heartbeat(
    request: HeartbeatRequest,
    user: dict = Depends(get_current_user_unified)
):
    """
    Send heartbeat to indicate agent is online.

    Requires:
    - X-API-Key header
    - X-Agent-ID header

    Body:
    - status: Agent status (online, busy, offline)
    - metadata: Optional metadata

    The agent will be considered offline if no heartbeat is received
    within TTL seconds (default: 90s).
    """
    agent_id = user.get("agent_id") or user.get("user_id")

    # Validate status
    valid_statuses = ["online", "busy", "offline"]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid status",
                "code": "INVALID_PARAMETER",
                "message": f"Status must be one of: {', '.join(valid_statuses)}"
            }
        )

    # Update heartbeat
    success = update_heartbeat_status(agent_id, request.status)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to update heartbeat",
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "Could not update heartbeat status"
            }
        )

    # Get updated info
    info = get_agent_heartbeat_info(agent_id)
    ttl_remaining = calculate_ttl_remaining(time.time(), info["ttl"])

    # Determine message
    if request.status == "online":
        message = "Heartbeat received, agent is online"
    elif request.status == "busy":
        message = "Heartbeat received, agent is busy"
    else:
        message = "Heartbeat received, agent is going offline"

    return HeartbeatResponse(
        agent_id=agent_id,
        status=request.status,
        ttl_remaining=ttl_remaining,
        last_heartbeat=time.time(),
        is_alive=request.status != "offline",
        message=message
    )


@router.get("/status", response_model=HeartbeatStatusResponse)
async def get_status(
    user: dict = Depends(get_current_user_unified)
):
    """
    Get agent's heartbeat status.

    Requires:
    - X-API-Key header
    - X-Agent-ID header

    Returns:
    - Current status (online, offline, busy)
    - Last heartbeat timestamp
    - TTL remaining (seconds until considered offline)
    - Is alive flag
    - Heartbeat interval
    - TTL configuration
    """
    agent_id = user.get("agent_id") or user.get("user_id")

    # Get heartbeat info
    info = get_agent_heartbeat_info(agent_id)

    last_heartbeat = info.get("last_heartbeat", 0) or 0
    ttl = info.get("ttl", DEFAULT_TTL) or DEFAULT_TTL
    heartbeat_interval = info.get("heartbeat_interval", DEFAULT_HEARTBEAT_INTERVAL) or DEFAULT_HEARTBEAT_INTERVAL
    status = info.get("status", "offline") or "offline"

    # Calculate TTL remaining
    ttl_remaining = calculate_ttl_remaining(last_heartbeat, ttl)

    # Determine if alive
    is_alive = ttl_remaining > 0 and status != "offline"

    # Update status if TTL expired
    if ttl_remaining <= 0 and status != "offline":
        status = "offline"

    return HeartbeatStatusResponse(
        agent_id=agent_id,
        status=status,
        last_heartbeat=last_heartbeat,
        ttl_remaining=ttl_remaining,
        is_alive=is_alive,
        heartbeat_interval=heartbeat_interval,
        ttl=ttl
    )


@router.post("/offline", response_model=HeartbeatResponse)
async def go_offline(
    user: dict = Depends(get_current_user_unified)
):
    """
    Mark agent as offline.

    Requires:
    - X-API-Key header
    - X-Agent-ID header

    Use this endpoint when agent is shutting down gracefully.
    """
    agent_id = user.get("agent_id") or user.get("user_id")

    # Update status to offline
    success = update_heartbeat_status(agent_id, "offline")

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to update status",
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "Could not set agent offline"
            }
        )

    return HeartbeatResponse(
        agent_id=agent_id,
        status="offline",
        ttl_remaining=0,
        last_heartbeat=time.time(),
        is_alive=False,
        message="Agent marked as offline"
    )


@router.post("/busy", response_model=HeartbeatResponse)
async def set_busy(
    user: dict = Depends(get_current_user_unified)
):
    """
    Mark agent as busy.

    Requires:
    - X-API-Key header
    - X-Agent-ID header

    Use this endpoint when agent is working on a task
    and may not respond to new requests immediately.
    """
    agent_id = user.get("agent_id") or user.get("user_id")

    # Update status to busy
    success = update_heartbeat_status(agent_id, "busy")

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to update status",
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "Could not set agent busy"
            }
        )

    info = get_agent_heartbeat_info(agent_id)
    ttl_remaining = calculate_ttl_remaining(time.time(), info["ttl"])

    return HeartbeatResponse(
        agent_id=agent_id,
        status="busy",
        ttl_remaining=ttl_remaining,
        last_heartbeat=time.time(),
        is_alive=True,
        message="Agent marked as busy"
    )
