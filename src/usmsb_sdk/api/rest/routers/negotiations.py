"""
Negotiation API Endpoints.

Phase 2 of USMSB Agent Platform implementation.

Endpoints:
- POST   /api/negotiations                        - Start negotiation
- GET    /api/negotiations/{session_id}          - Get session
- POST   /api/negotiations/{session_id}/counter   - Submit counter-proposal
- POST   /api/negotiations/{session_id}/agree     - Agree on terms
- POST   /api/negotiations/{session_id}/cancel    - Cancel negotiation
- POST   /api/negotiations/{session_id}/auto      - Trigger AI auto-negotiation
- GET    /api/negotiations/agent/{agent_id}      - Get agent's active sessions

Authentication: Require X-API-Key + X-Agent-ID
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
from usmsb_sdk.services.schema import create_session
from usmsb_sdk.services.value_contract.negotiation import (
    ValueNegotiationService,
    ValueNegotiationSession,
)

router = APIRouter(prefix="/negotiations", tags=["Negotiations"])


# ============== Request Models ==============


class StartNegotiationRequest(BaseModel):
    """Start a new negotiation."""
    supply_agent_id: str = Field(..., description="Agent who will perform the task")
    initial_terms: dict | None = Field(
        default=None,
        description="Initial proposed terms {price_vibe: 5.0, deadline: 86400}"
    )
    template_id: str = Field(default="simple_task", description="Template to use")
    contract_id: str | None = Field(default=None, description="Existing contract to negotiate")
    timeout_seconds: int = Field(default=300, description="Session timeout")


class CounterProposalRequest(BaseModel):
    """Submit counter-proposal."""
    counter_changes: dict = Field(
        ...,
        description="Terms to change {price_vibe: 4.5, deadline: 172800}"
    )


class AutoNegotiateRequest(BaseModel):
    """Trigger AI auto-negotiation."""
    agent_a_soul: dict = Field(..., description="Soul profile of first agent")
    agent_b_soul: dict = Field(..., description="Soul profile of second agent")


class CancelNegotiationRequest(BaseModel):
    """Cancel a negotiation."""
    reason: str = Field(default="", description="Reason for cancellation")


# ============== Response Models ==============


class NegotiationSessionResponse(BaseModel):
    """Negotiation session response."""
    session_id: str
    contract_id: str | None
    participants: list[str]
    negotiation_rounds: list[dict]
    template_id: str
    status: str
    started_at: float
    expires_at: float
    agreed_at: float | None


# ============== Helper ==============


def get_negotiation_service() -> ValueNegotiationService:
    session = create_session()
    return ValueNegotiationService(session)


# ============== Endpoints ==============


@router.post("", status_code=status.HTTP_201_CREATED)
async def start_negotiation(
    request: StartNegotiationRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """Start a new negotiation session."""
    demand_agent_id = current_user.get("agent_id")
    if not demand_agent_id:
        raise HTTPException(status_code=401, detail="Agent ID not found")

    service = get_negotiation_service()

    try:
        session = await service.start_negotiation(
            demand_agent_id=demand_agent_id,
            supply_agent_id=request.supply_agent_id,
            initial_terms=request.initial_terms,
            template_id=request.template_id,
            contract_id=request.contract_id,
            timeout_seconds=request.timeout_seconds,
        )
        return NegotiationSessionResponse(
            session_id=session.session_id,
            contract_id=session.contract_id,
            participants=session.participants,
            negotiation_rounds=[r.__dict__ for r in session.negotiation_rounds],
            template_id=session.template_id,
            status=session.status,
            started_at=session.started_at,
            expires_at=session.expires_at,
            agreed_at=session.agreed_at if session.status == "agreed" else None,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}")
async def get_negotiation_session(
    session_id: str,
    current_user: dict = Depends(get_current_user_unified),
):
    """Get a negotiation session by ID."""
    service = get_negotiation_service()
    session = await service.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return NegotiationSessionResponse(
        session_id=session.session_id,
        contract_id=session.contract_id,
        participants=session.participants,
        negotiation_rounds=[
            {
                "round": r.round,
                "proposer_id": r.proposer_id,
                "proposed_changes": r.proposed_changes,
                "status": r.status,
                "responded_at": r.responded_at,
            }
            for r in session.negotiation_rounds
        ],
        template_id=session.template_id,
        status=session.status,
        started_at=session.started_at,
        expires_at=session.expires_at,
        agreed_at=session.agreed_at if session.status == "agreed" else None,
    )


@router.post("/{session_id}/counter")
async def submit_counter_proposal(
    session_id: str,
    request: CounterProposalRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """Submit a counter-proposal to an active negotiation."""
    agent_id = current_user.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent ID not found")

    service = get_negotiation_service()

    try:
        session = await service.submit_counter_proposal(
            session_id=session_id,
            agent_id=agent_id,
            counter_changes=request.counter_changes,
        )
        return NegotiationSessionResponse(
            session_id=session.session_id,
            contract_id=session.contract_id,
            participants=session.participants,
            negotiation_rounds=[
                {
                    "round": r.round,
                    "proposer_id": r.proposer_id,
                    "proposed_changes": r.proposed_changes,
                    "status": r.status,
                    "responded_at": r.responded_at,
                }
                for r in session.negotiation_rounds
            ],
            template_id=session.template_id,
            status=session.status,
            started_at=session.started_at,
            expires_at=session.expires_at,
            agreed_at=session.agreed_at if session.status == "agreed" else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/agree")
async def agree_on_terms(
    session_id: str,
    current_user: dict = Depends(get_current_user_unified),
):
    """Agree on terms and finalize negotiation."""
    agent_id = current_user.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent ID not found")

    service = get_negotiation_service()

    try:
        session, agreed_terms = await service.agree_on_terms(
            session_id=session_id,
            agent_id=agent_id,
        )
        return {
            "success": True,
            "session_id": session_id,
            "status": "agreed",
            "agreed_terms": agreed_terms,
            "agreed_at": session.agreed_at,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/cancel")
async def cancel_negotiation(
    session_id: str,
    request: CancelNegotiationRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """Cancel a negotiation session."""
    agent_id = current_user.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=401, detail="Agent ID not found")

    service = get_negotiation_service()

    try:
        await service.cancel_negotiation(
            session_id=session_id,
            agent_id=agent_id,
            reason=request.reason,
        )
        return {"success": True, "session_id": session_id, "status": "cancelled"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/auto")
async def auto_negotiate(
    session_id: str,
    request: AutoNegotiateRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """Trigger AI auto-negotiation for the session."""
    service = get_negotiation_service()

    try:
        session, agreed_terms = await service.auto_negotiate(
            session_id=session_id,
            agent_a_soul=request.agent_a_soul,
            agent_b_soul=request.agent_b_soul,
        )
        return {
            "success": True,
            "session_id": session_id,
            "status": "agreed",
            "agreed_terms": agreed_terms,
            "agreed_at": session.agreed_at,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/agent/{agent_id}")
async def get_agent_negotiations(
    agent_id: str,
    current_user: dict = Depends(get_current_user_unified),
):
    """Get all active negotiation sessions for an agent."""
    service = get_negotiation_service()

    sessions = await service.get_active_sessions_for_agent(agent_id)
    return {
        "agent_id": agent_id,
        "active_sessions": [
            {
                "session_id": s.session_id,
                "contract_id": s.contract_id,
                "participants": s.participants,
                "template_id": s.template_id,
                "status": s.status,
                "started_at": s.started_at,
                "expires_at": s.expires_at,
            }
            for s in sessions
        ],
        "total": len(sessions),
    }
