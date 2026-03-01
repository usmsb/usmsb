"""
Pre-Match Negotiation API Endpoints

API routes for pre-match negotiation including:
- Negotiation session management
- Clarification Q&A
- Capability verification
- Match confirmation/decline

Authentication:
- All endpoints require X-API-Key + X-Agent-ID headers
- Actions must be performed by a participant in the negotiation
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from usmsb_sdk.api.rest.unified_auth import (
    get_current_user_unified,
    require_stake_unified,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/negotiations/pre-match", tags=["Pre-Match Negotiation"])

# Global reference to service (set by main.py)
_pre_match_service = None


def set_pre_match_service(service):
    """Set the pre-match negotiation service instance."""
    global _pre_match_service
    _pre_match_service = service


# ==================== Request/Response Models ====================

class InitiateNegotiationRequest(BaseModel):
    """Request to initiate pre-match negotiation"""
    demand_agent_id: str
    supply_agent_id: str
    demand_id: str
    initial_message: Optional[str] = None
    expiration_hours: int = Field(default=24, ge=1, le=168)


class AskQuestionRequest(BaseModel):
    """Request to ask a clarification question"""
    question: str
    asker_id: str


class AnswerQuestionRequest(BaseModel):
    """Request to answer a question"""
    answer: str
    answerer_id: str


class VerificationRequestModel(BaseModel):
    """Request for capability verification"""
    capability: str
    verification_type: str  # portfolio, test_task, reference, gene_capsule
    request_detail: str


class VerificationResponseModel(BaseModel):
    """Response to verification request"""
    response: str
    attachments: Optional[List[str]] = None


class ScopeConfirmationRequest(BaseModel):
    """Request to confirm scope"""
    deliverables: List[str] = []
    timeline: Optional[str] = None
    milestones: List[Dict[str, Any]] = []
    exclusions: List[str] = []
    assumptions: List[str] = []


class ProposeTermsRequest(BaseModel):
    """Request to propose terms"""
    terms: Dict[str, Any]
    proposer_id: str


class DeclineMatchRequest(BaseModel):
    """Request to decline match"""
    reason: str
    decliner_id: str


class CancelNegotiationRequest(BaseModel):
    """Request to cancel negotiation"""
    reason: str
    canceller_id: str


# ==================== Endpoints ====================

@router.post("")
async def initiate_negotiation(
    request: InitiateNegotiationRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """
    Initiate a pre-match negotiation between agents.

    Creates a negotiation session for agents to:
    - Ask clarification questions
    - Verify capabilities
    - Confirm scope
    - Agree on terms

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Must be either demand_agent or supply_agent
    """
    # Verify agent is a participant
    agent_id = user.get('agent_id') or user.get('user_id')
    if agent_id not in [request.demand_agent_id, request.supply_agent_id]:
        raise HTTPException(
            status_code=403,
            detail="You must be a participant in the negotiation"
        )

    if not _pre_match_service:
        raise HTTPException(status_code=503, detail="Pre-match service not available")

    try:
        result = await _pre_match_service.initiate(
            demand_agent_id=request.demand_agent_id,
            supply_agent_id=request.supply_agent_id,
            demand_id=request.demand_id,
            initial_message=request.initial_message,
            expiration_hours=request.expiration_hours,
        )
        return result
    except Exception as e:
        logger.error(f"Error initiating negotiation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{negotiation_id}")
async def get_negotiation(
    negotiation_id: str,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """
    Get negotiation details.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Must be a participant in the negotiation
    """
    if not _pre_match_service:
        raise HTTPException(status_code=503, detail="Pre-match service not available")

    try:
        result = await _pre_match_service.get_negotiation(negotiation_id)

        if not result:
            raise HTTPException(status_code=404, detail="Negotiation not found")

        # Verify agent is a participant
        agent_id = user.get('agent_id') or user.get('user_id')
        if agent_id not in [result.get('demand_agent_id'), result.get('supply_agent_id')]:
            raise HTTPException(
                status_code=403,
                detail="You must be a participant in the negotiation"
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting negotiation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{negotiation_id}/questions")
async def ask_question(
    negotiation_id: str,
    request: AskQuestionRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """
    Ask a clarification question.

    Either agent can ask questions to clarify requirements or capabilities.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - asker_id must match authenticated agent
    """
    # Verify ownership
    agent_id = user.get('agent_id') or user.get('user_id')
    if agent_id != request.asker_id:
        raise HTTPException(
            status_code=403,
            detail="asker_id must match your agent ID"
        )

    if not _pre_match_service:
        raise HTTPException(status_code=503, detail="Pre-match service not available")

    try:
        result = await _pre_match_service.ask_question(
            negotiation_id=negotiation_id,
            question=request.question,
            asker_id=request.asker_id,
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error asking question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{negotiation_id}/questions/{question_id}/answer")
async def answer_question(
    negotiation_id: str,
    question_id: str,
    request: AnswerQuestionRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """
    Answer a clarification question.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - answerer_id must match authenticated agent
    """
    # Verify ownership
    agent_id = user.get('agent_id') or user.get('user_id')
    if agent_id != request.answerer_id:
        raise HTTPException(
            status_code=403,
            detail="answerer_id must match your agent ID"
        )

    if not _pre_match_service:
        raise HTTPException(status_code=503, detail="Pre-match service not available")

    try:
        result = await _pre_match_service.answer_question(
            negotiation_id=negotiation_id,
            question_id=question_id,
            answer=request.answer,
            answerer_id=request.answerer_id,
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{negotiation_id}/verify")
async def request_verification(
    negotiation_id: str,
    request: VerificationRequestModel,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """
    Request capability verification from supply agent.

    Verification types:
    - portfolio: Request portfolio/work samples
    - test_task: Request completion of a small test task
    - reference: Request references from past clients
    - gene_capsule: Request gene capsule evidence

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Must be demand_agent in the negotiation
    """
    if not _pre_match_service:
        raise HTTPException(status_code=503, detail="Pre-match service not available")

    try:
        # Get negotiation and verify agent is demand_agent
        negotiation = await _pre_match_service.get_negotiation(negotiation_id)
        if not negotiation:
            raise HTTPException(status_code=404, detail="Negotiation not found")

        agent_id = user.get('agent_id') or user.get('user_id')
        if agent_id != negotiation.get('demand_agent_id'):
            raise HTTPException(
                status_code=403,
                detail="Only demand agent can request verification"
            )

        from usmsb_sdk.services.pre_match_negotiation import VerificationType

        verification_type = VerificationType(request.verification_type)

        result = await _pre_match_service.request_capability_verification(
            negotiation_id=negotiation_id,
            capability=request.capability,
            verification_type=verification_type,
            request_detail=request.request_detail,
        )
        return result.to_dict()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error requesting verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{negotiation_id}/verify/{request_id}/respond")
async def respond_to_verification(
    negotiation_id: str,
    request_id: str,
    request: VerificationResponseModel,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """
    Respond to a capability verification request.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Must be supply_agent in the negotiation
    """
    if not _pre_match_service:
        raise HTTPException(status_code=503, detail="Pre-match service not available")

    try:
        # Get negotiation and verify agent is supply_agent
        negotiation = await _pre_match_service.get_negotiation(negotiation_id)
        if not negotiation:
            raise HTTPException(status_code=404, detail="Negotiation not found")

        agent_id = user.get('agent_id') or user.get('user_id')
        if agent_id != negotiation.get('supply_agent_id'):
            raise HTTPException(
                status_code=403,
                detail="Only supply agent can respond to verification"
            )

        result = await _pre_match_service.respond_to_verification(
            negotiation_id=negotiation_id,
            request_id=request_id,
            response=request.response,
            attachments=request.attachments,
        )
        return result.to_dict()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error responding to verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{negotiation_id}/scope")
async def confirm_scope(
    negotiation_id: str,
    request: ScopeConfirmationRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """
    Confirm the scope of the engagement.

    Defines:
    - Deliverables
    - Timeline
    - Milestones
    - Exclusions
    - Assumptions

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Must be a participant in the negotiation
    """
    if not _pre_match_service:
        raise HTTPException(status_code=503, detail="Pre-match service not available")

    try:
        # Get negotiation and verify agent is participant
        negotiation = await _pre_match_service.get_negotiation(negotiation_id)
        if not negotiation:
            raise HTTPException(status_code=404, detail="Negotiation not found")

        agent_id = user.get('agent_id') or user.get('user_id')
        if agent_id not in [negotiation.get('demand_agent_id'), negotiation.get('supply_agent_id')]:
            raise HTTPException(
                status_code=403,
                detail="You must be a participant in the negotiation"
            )

        from usmsb_sdk.services.pre_match_negotiation import ScopeConfirmation

        scope = ScopeConfirmation(
            deliverables=request.deliverables,
            timeline=request.timeline,
            milestones=request.milestones,
            exclusions=request.exclusions,
            assumptions=request.assumptions,
        )

        result = await _pre_match_service.confirm_scope(
            negotiation_id=negotiation_id,
            scope=scope,
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error confirming scope: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{negotiation_id}/terms/propose")
async def propose_terms(
    negotiation_id: str,
    request: ProposeTermsRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """
    Propose terms for the engagement.

    Can include:
    - Price/payment terms
    - Timeline
    - Deliverables
    - Communication expectations

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - proposer_id must match authenticated agent
    """
    # Verify ownership
    agent_id = user.get('agent_id') or user.get('user_id')
    if agent_id != request.proposer_id:
        raise HTTPException(
            status_code=403,
            detail="proposer_id must match your agent ID"
        )

    if not _pre_match_service:
        raise HTTPException(status_code=503, detail="Pre-match service not available")

    try:
        result = await _pre_match_service.propose_terms(
            negotiation_id=negotiation_id,
            terms=request.terms,
            proposer_id=request.proposer_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error proposing terms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{negotiation_id}/terms/agree")
async def agree_to_terms(
    negotiation_id: str,
    user: Dict[str, Any] = Depends(get_current_user_unified),
    terms: Optional[Dict[str, Any]] = None,
):
    """
    Agree to proposed terms.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Must be a participant in the negotiation
    """
    if not _pre_match_service:
        raise HTTPException(status_code=503, detail="Pre-match service not available")

    try:
        # Get negotiation and verify agent is participant
        negotiation = await _pre_match_service.get_negotiation(negotiation_id)
        if not negotiation:
            raise HTTPException(status_code=404, detail="Negotiation not found")

        agent_id = user.get('agent_id') or user.get('user_id')
        if agent_id not in [negotiation.get('demand_agent_id'), negotiation.get('supply_agent_id')]:
            raise HTTPException(
                status_code=403,
                detail="You must be a participant in the negotiation"
            )

        result = await _pre_match_service.agree_to_terms(
            negotiation_id=negotiation_id,
            terms=terms,
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error agreeing to terms: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{negotiation_id}/confirm")
async def confirm_match(
    negotiation_id: str,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """
    Confirm the match.

    Both parties must confirm for the match to be finalized.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Must be a participant in the negotiation
    """
    if not _pre_match_service:
        raise HTTPException(status_code=503, detail="Pre-match service not available")

    try:
        # Get negotiation and verify agent is participant
        negotiation = await _pre_match_service.get_negotiation(negotiation_id)
        if not negotiation:
            raise HTTPException(status_code=404, detail="Negotiation not found")

        agent_id = user.get('agent_id') or user.get('user_id')
        if agent_id not in [negotiation.get('demand_agent_id'), negotiation.get('supply_agent_id')]:
            raise HTTPException(
                status_code=403,
                detail="You must be a participant in the negotiation"
            )

        result = await _pre_match_service.confirm_match(
            negotiation_id=negotiation_id,
            confirmer_id=agent_id,
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error confirming match: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{negotiation_id}/decline")
async def decline_match(
    negotiation_id: str,
    request: DeclineMatchRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """
    Decline the match.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - decliner_id must match authenticated agent
    """
    # Verify ownership
    agent_id = user.get('agent_id') or user.get('user_id')
    if agent_id != request.decliner_id:
        raise HTTPException(
            status_code=403,
            detail="decliner_id must match your agent ID"
        )

    if not _pre_match_service:
        raise HTTPException(status_code=503, detail="Pre-match service not available")

    try:
        result = await _pre_match_service.decline_match(
            negotiation_id=negotiation_id,
            reason=request.reason,
            decliner_id=request.decliner_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error declining match: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{negotiation_id}/cancel")
async def cancel_negotiation(
    negotiation_id: str,
    request: CancelNegotiationRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """
    Cancel the negotiation.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - canceller_id must match authenticated agent
    """
    # Verify ownership
    agent_id = user.get('agent_id') or user.get('user_id')
    if agent_id != request.canceller_id:
        raise HTTPException(
            status_code=403,
            detail="canceller_id must match your agent ID"
        )

    if not _pre_match_service:
        raise HTTPException(status_code=503, detail="Pre-match service not available")

    try:
        result = await _pre_match_service.cancel_negotiation(
            negotiation_id=negotiation_id,
            reason=request.reason,
            canceller_id=request.canceller_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling negotiation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/{agent_id}")
async def get_agent_negotiations(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user_unified),
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Get all negotiations for an agent.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Can only view own negotiations
    """
    # Verify ownership - can only view own negotiations
    if user.get('agent_id') or user.get('user_id') != agent_id:
        raise HTTPException(
            status_code=403,
            detail="You can only view your own negotiations"
        )

    if not _pre_match_service:
        raise HTTPException(status_code=503, detail="Pre-match service not available")

    try:
        from usmsb_sdk.services.pre_match_negotiation import NegotiationStatus

        status_enum = None
        if status:
            try:
                status_enum = NegotiationStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        result = await _pre_match_service.get_negotiations_for_agent(
            agent_id=agent_id,
            status=status_enum,
            limit=limit,
        )
        return {"negotiations": result, "count": len(result)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting agent negotiations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
