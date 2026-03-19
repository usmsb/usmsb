"""
Feedback API Endpoints.

Phase 3 of USMSB Agent Platform implementation.

Provides feedback loop integration:
- POST /api/feedback/contract/{id} - Process contract completion feedback
- GET  /api/feedback/agent/{id} - Get agent's feedback history
- GET  /api/feedback/stats - Get platform feedback statistics

Authentication: Require X-API-Key + X-Agent-ID
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
from usmsb_sdk.services.feedback import CollaborationFeedbackLoop
from usmsb_sdk.services.schema import create_session

router = APIRouter(prefix="/feedback", tags=["Feedback"])


# ============== Request Models ==============


class ContractFeedbackRequest(BaseModel):
    """Request to process contract completion feedback."""
    success: bool = Field(..., description="Whether the contract was successfully completed")
    quality_score: float = Field(
        default=0.8, ge=0.0, le=1.0,
        description="Quality score of delivery (0.0-1.0)"
    )
    delivery_data: dict = Field(
        default_factory=dict,
        description="Detailed delivery data {deliverables, delivered_at, ...}"
    )
    issues: list[str] = Field(
        default_factory=list,
        description="List of issues if failed"
    )


# ============== Response Models ==============


class FeedbackResponse(BaseModel):
    """Feedback processing response."""
    success: bool
    contract_id: str
    evaluation: dict


class FeedbackHistoryResponse(BaseModel):
    """Agent's feedback history."""
    agent_id: str
    feedback_count: int
    recent_events: list[dict]


class PlatformFeedbackStats(BaseModel):
    """Platform-wide feedback statistics."""
    total_events: int
    success_rate: float
    avg_quality_score: float
    avg_value_match_score: float
    avg_on_time_score: float


# ============== Helpers ==============


def get_feedback_loop() -> CollaborationFeedbackLoop:
    session = create_session()
    return CollaborationFeedbackLoop(session)


# ============== Endpoints ==============


@router.post("/contract/{contract_id}")
async def process_contract_feedback(
    contract_id: str,
    request: ContractFeedbackRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    Process contract completion feedback.

    This is called after confirm_delivery to evaluate the contract outcome
    and update agents' Inferred Souls.
    """
    agent_id = current_user.get("agent_id")

    feedback_loop = get_feedback_loop()

    try:
        # Build actual outcome
        actual_outcome = {
            "success": request.success,
            "issues": request.issues,
        }

        # Add delivery details
        delivery_data = request.delivery_data.copy()
        delivery_data["quality_score"] = request.quality_score
        delivery_data["capability"] = delivery_data.get("capability")

        evaluation = await feedback_loop.process_contract_completion(
            contract_id=contract_id,
            actual_outcome=actual_outcome,
            delivery_data=delivery_data,
        )

        return FeedbackResponse(
            success=True,
            contract_id=contract_id,
            evaluation={
                "success": evaluation.success,
                "quality_score": evaluation.quality_score,
                "on_time_score": evaluation.on_time_score,
                "value_match_score": evaluation.value_match_score,
                "overall_score": evaluation.overall_score,
                "issues": evaluation.issues,
            },
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/{agent_id}", response_model=FeedbackHistoryResponse)
async def get_agent_feedback_history(
    agent_id: str,
    current_user: dict = Depends(get_current_user_unified),
):
    """Get an agent's feedback history."""
    from usmsb_sdk.services.schema import FeedbackEventDB

    session = create_session()

    events = session.query(FeedbackEventDB).filter(
        (FeedbackEventDB.demand_agent_id == agent_id) |
        (FeedbackEventDB.supply_agent_id == agent_id)
    ).order_by(
        FeedbackEventDB.created_at.desc()
    ).limit(50).all()

    recent = []
    for e in events:
        event_data = e.event_data or {}
        recent.append({
            "event_id": e.event_id,
            "contract_id": e.contract_id,
            "event_type": e.event_type,
            "success": event_data.get("success"),
            "quality_score": event_data.get("quality_score"),
            "created_at": float(e.created_at.timestamp()) if e.created_at else 0,
        })

    return FeedbackHistoryResponse(
        agent_id=agent_id,
        feedback_count=len(events),
        recent_events=recent,
    )


@router.get("/stats", response_model=PlatformFeedbackStats)
async def get_platform_feedback_stats(
    current_user: dict = Depends(get_current_user_unified),
):
    """Get platform-wide feedback statistics."""
    from usmsb_sdk.services.schema import FeedbackEventDB

    session = create_session()

    events = session.query(FeedbackEventDB).filter(
        FeedbackEventDB.process_status == "processed"
    ).all()

    if not events:
        return PlatformFeedbackStats(
            total_events=0,
            success_rate=0.0,
            avg_quality_score=0.0,
            avg_value_match_score=0.0,
            avg_on_time_score=0.0,
        )

    total = len(events)
    successes = sum(1 for e in events if e.event_data and e.event_data.get("success"))
    quality_scores = [
        e.event_data.get("quality_score", 0)
        for e in events if e.event_data
    ]
    value_matches = [
        e.event_data.get("value_match_score", 0)
        for e in events if e.event_data
    ]
    on_times = [
        e.event_data.get("on_time_score", 0)
        for e in events if e.event_data
    ]

    return PlatformFeedbackStats(
        total_events=total,
        success_rate=successes / total if total > 0 else 0.0,
        avg_quality_score=sum(quality_scores) / len(quality_scores) if quality_scores else 0.0,
        avg_value_match_score=sum(value_matches) / len(value_matches) if value_matches else 0.0,
        avg_on_time_score=sum(on_times) / len(on_times) if on_times else 0.0,
    )
