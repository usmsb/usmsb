"""
Order API Endpoints

REST API for order lifecycle management:
- Create order from pre-match or formal negotiation
- Order state transitions (confirm, start, deliver, accept, dispute, cancel)
- Query orders by agent, status, role

Security fixes:
- No global mutable state (uses contextvars)
- Price validation with upper bound
- Participant validation on all operations
"""

import logging
from contextvars import ContextVar
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from usmsb_sdk.api.database import get_db
from usmsb_sdk.api.rest.unified_auth import (
    get_current_user_unified,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["Orders"])

# Maximum order price to prevent financial exploits
MAX_ORDER_PRICE = 1_000_000.0  # 1M VIBE

# Request-scoped service references (thread-safe, replaces global variables)
_order_service_ctx: ContextVar[Any | None] = ContextVar("_order_service_ctx", default=None)
_pre_match_service_ctx: ContextVar[Any | None] = ContextVar("_pre_match_service_ctx", default=None)


def set_order_service(service):
    """Set order service for this request context."""
    _order_service_ctx.set(service)


def set_pre_match_service(service):
    """Set pre-match service for this request context."""
    _pre_match_service_ctx.set(service)


def _get_order_service() -> Any | None:
    """Get order service from request context."""
    return _order_service_ctx.get()


def _get_pre_match_service() -> Any | None:
    """Get pre-match service from request context."""
    return _pre_match_service_ctx.get()


# ==================== Request Models ====================

class CreateOrderFromPreMatchRequest(BaseModel):
    """Create order from confirmed pre-match negotiation"""
    negotiation_id: str
    task_description: str | None = None


class CreateOrderFromNegotiationRequest(BaseModel):
    """Create order from formal negotiation"""
    negotiation_session_id: str
    price: float = Field(gt=0, le=MAX_ORDER_PRICE)
    delivery_time: datetime | None = None
    delivery_description: str = ""
    payment_terms: str = "escrow"
    milestones: list[dict[str, Any]] = Field(default_factory=list)
    task_description: str
    demand_agent_id: str
    supply_agent_id: str


class ConfirmOrderRequest(BaseModel):
    pass


class StartWorkRequest(BaseModel):
    pass


class SubmitDeliverableRequest(BaseModel):
    description: str
    artifact_type: str = "text"
    url_or_content: str = ""


class AcceptDeliverableRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = ""


class RaiseDisputeRequest(BaseModel):
    reason: str = Field(min_length=1)


class CancelOrderRequest(BaseModel):
    reason: str = ""


class OrderResponse(BaseModel):
    order_id: str
    source: str
    source_session_id: str | None
    demand_agent_id: str
    supply_agent_id: str
    task_description: str | None
    terms: dict[str, Any]
    pool_id: str | None
    status: str
    priority: str
    delivery_deadline: str | None
    created_at: str
    updated_at: str
    completed_at: str | None
    completion_reason: str | None
    deliverables: list[dict[str, Any]]
    acceptance_data: dict[str, Any]
    chain_order_id: str | None
    chain_tx_hash: str | None
    vibe_locked: float
    metadata: dict[str, Any]
    available_actions: list[str]


# ==================== Helpers ====================

def _require_agent(user: dict[str, Any]) -> str:
    """Extract agent_id from user, raise if missing."""
    agent_id = user.get("agent_id") or user.get("user_id")
    if not agent_id:
        raise HTTPException(status_code=401, detail="No agent_id in credentials")
    return agent_id


def _require_order_service():
    """Get order service or raise 503."""
    svc = _get_order_service()
    if not svc:
        raise HTTPException(status_code=503, detail="Order service not available")
    return svc


def _check_order_access(user: dict[str, Any], order) -> None:
    """Verify user is a party to the order."""
    agent_id = _require_agent(user)
    if agent_id not in [order.demand_agent_id, order.supply_agent_id]:
        raise HTTPException(status_code=403, detail="Not a party to this order")


def _order_to_response(order) -> dict[str, Any]:
    """Convert Order dataclass to API response dict."""
    sm = order._state_machine

    deliverables = []
    for d in order.deliverables:
        deliverables.append({
            "artifact_id": d.artifact_id,
            "description": d.description,
            "artifact_type": d.artifact_type,
            "url_or_content": d.url_or_content,
            "submitted_at": d.submitted_at.isoformat() if hasattr(d, "submitted_at") and d.submitted_at else None,
            "verified": d.verified,
        })

    return {
        "order_id": order.order_id,
        "source": order.source.value if hasattr(order, "source") else str(order.source),
        "source_session_id": order.source_session_id,
        "demand_agent_id": order.demand_agent_id,
        "supply_agent_id": order.supply_agent_id,
        "task_description": (
            order.task_description[0]
            if isinstance(order.task_description, list)
            else order.task_description
        ),
        "terms": order.terms.to_dict(),
        "pool_id": order.pool_id,
        "status": order.status.value,
        "priority": order.priority.value if hasattr(order, "priority") else "normal",
        "delivery_deadline": (
            order.delivery_deadline.isoformat()
            if order.delivery_deadline
            else None
        ),
        "created_at": order.created_at.isoformat() if hasattr(order, "created_at") and order.created_at else None,
        "updated_at": order.updated_at.isoformat() if hasattr(order, "updated_at") and order.updated_at else None,
        "completed_at": order.completed_at.isoformat() if order.completed_at else None,
        "completion_reason": order.completion_reason,
        "deliverables": deliverables,
        "acceptance_data": order.acceptance_data,
        "chain_order_id": order.chain_order_id,
        "chain_tx_hash": order.chain_tx_hash,
        "vibe_locked": order.vibe_locked,
        "metadata": order.metadata,
        "available_actions": [e.value for e in sm.get_available_events()],
        "state_history": [t.to_dict() for t in sm.history],
        "is_terminal": sm.is_terminal(),
    }


# ==================== Endpoints ====================

@router.post("/from-pre-match", status_code=201)
async def create_order_from_pre_match_endpoint(
    request: CreateOrderFromPreMatchRequest,
    user: dict[str, Any] = Depends(get_current_user_unified),
):
    """Create an order from a confirmed pre-match negotiation."""
    svc = _require_order_service()
    agent_id = _require_agent(user)

    result = await svc.create_order_from_pre_match(
        negotiation_id=request.negotiation_id,
        agent_id=agent_id,
    )
    if not result:
        raise HTTPException(status_code=400, detail="Failed to create order from pre-match negotiation")

    return _order_to_response(result)


@router.post("/from-negotiation", status_code=201)
async def create_order_from_negotiation_endpoint(
    request: CreateOrderFromNegotiationRequest,
    user: dict[str, Any] = Depends(get_current_user_unified),
):
    """Create an order from a formal negotiation session."""
    svc = _require_order_service()
    agent_id = _require_agent(user)

    # Participant validation
    if agent_id not in [request.demand_agent_id, request.supply_agent_id]:
        raise HTTPException(
            status_code=403,
            detail="You must be either the demand or supply agent to create this order"
        )

    from usmsb_sdk.agent_sdk.negotiation import NegotiationTerms
    terms = NegotiationTerms(
        price=request.price,
        delivery_time=request.delivery_time,
        delivery_description=request.delivery_description,
        payment_terms=request.payment_terms,
        milestones=request.milestones,
    )

    order = await svc.create_order_from_negotiation(
        negotiation_session_id=request.negotiation_session_id,
        terms=terms,
        demand_agent_id=request.demand_agent_id,
        supply_agent_id=request.supply_agent_id,
        task_description=request.task_description,
    )
    return _order_to_response(order)


@router.get("")
async def list_orders_endpoint(
    status: str | None = Query(None),
    role: str | None = Query(None),
    active_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    user: dict[str, Any] = Depends(get_current_user_unified),
):
    """List orders for the authenticated agent."""
    svc = _require_order_service()
    agent_id = _require_agent(user)

    if active_only:
        orders = await svc.get_active_orders(agent_id)
    else:
        from usmsb_sdk.services.order_state_machine import OrderStatus as OS
        status_filter = OS(status) if status else None
        orders = await svc.get_orders_for_agent(
            agent_id=agent_id,
            status=status_filter,
            role=role,
            limit=limit,
        )
    return [_order_to_response(o) for o in orders]


@router.get("/{order_id}")
async def get_order_endpoint(
    order_id: str,
    user: dict[str, Any] = Depends(get_current_user_unified),
):
    """Get a specific order by ID."""
    svc = _require_order_service()
    order = await svc.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    _check_order_access(user, order)
    return _order_to_response(order)


@router.get("/{order_id}/status")
async def get_order_status_endpoint(
    order_id: str,
    user: dict[str, Any] = Depends(get_current_user_unified),
):
    """Get order status summary with available actions."""
    svc = _require_order_service()
    order = await svc.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    _check_order_access(user, order)

    agent_id = _require_agent(user)
    sm = order._state_machine
    return {
        "order_id": order.order_id,
        "status": order.status.value,
        "is_supply": agent_id == order.supply_agent_id,
        "is_demand": agent_id == order.demand_agent_id,
        "price": order.terms.price,
        "delivery_deadline": (
            order.delivery_deadline.isoformat() if order.delivery_deadline else None
        ),
        "available_actions": [e.value for e in sm.get_available_events()],
        "state_history": [t.to_dict() for t in sm.history],
        "is_terminal": sm.is_terminal(),
    }


@router.post("/{order_id}/confirm")
async def confirm_order_endpoint(
    order_id: str,
    user: dict[str, Any] = Depends(get_current_user_unified),
):
    """Confirm an order. Both parties must confirm to proceed."""
    svc = _require_order_service()
    agent_id = _require_agent(user)
    try:
        order = await svc.confirm_order(order_id, agent_id)
        return _order_to_response(order)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/start")
async def start_work_endpoint(
    order_id: str,
    user: dict[str, Any] = Depends(get_current_user_unified),
):
    """Start work on an order. Supply agent only."""
    svc = _require_order_service()
    agent_id = _require_agent(user)
    try:
        order = await svc.start_work(order_id, agent_id)
        return _order_to_response(order)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/deliver")
async def submit_deliverable_endpoint(
    order_id: str,
    request: SubmitDeliverableRequest,
    user: dict[str, Any] = Depends(get_current_user_unified),
):
    """Submit a deliverable for an order. Supply agent only."""
    svc = _require_order_service()
    agent_id = _require_agent(user)
    try:
        order = await svc.submit_deliverable(
            order_id=order_id,
            agent_id=agent_id,
            description=request.description,
            artifact_type=request.artifact_type,
            url_or_content=request.url_or_content,
        )
        return _order_to_response(order)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/accept")
async def accept_deliverable_endpoint(
    order_id: str,
    request: AcceptDeliverableRequest,
    user: dict[str, Any] = Depends(get_current_user_unified),
):
    """Accept deliverables and complete the order. Demand agent only."""
    svc = _require_order_service()
    agent_id = _require_agent(user)
    try:
        order = await svc.accept_deliverable(
            order_id=order_id,
            agent_id=agent_id,
            rating=request.rating,
            comment=request.comment,
        )
        return _order_to_response(order)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/dispute")
async def raise_dispute_endpoint(
    order_id: str,
    request: RaiseDisputeRequest,
    user: dict[str, Any] = Depends(get_current_user_unified),
):
    """Raise a dispute on an order. Either party can raise."""
    svc = _require_order_service()
    agent_id = _require_agent(user)
    try:
        order = await svc.raise_dispute(order_id, agent_id, request.reason)
        return _order_to_response(order)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/cancel")
async def cancel_order_endpoint(
    order_id: str,
    request: CancelOrderRequest,
    user: dict[str, Any] = Depends(get_current_user_unified),
):
    """Cancel an order. Either party can cancel if state allows."""
    svc = _require_order_service()
    agent_id = _require_agent(user)
    try:
        order = await svc.cancel_order(order_id, agent_id, request.reason)
        return _order_to_response(order)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats")
async def get_order_stats(
    user: dict[str, Any] = Depends(get_current_user_unified),
):
    """Get order statistics for the authenticated agent."""
    svc = _require_order_service()
    agent_id = _require_agent(user)

    from usmsb_sdk.services.order_state_machine import OrderStatus as OS
    all_orders = await svc.get_orders_for_agent(agent_id, limit=1000)
    active_orders = await svc.get_active_orders(agent_id)

    status_counts: dict[str, int] = {}
    for o in all_orders:
        s = o.status.value
        status_counts[s] = status_counts.get(s, 0) + 1

    demand_count = sum(1 for o in all_orders if o.demand_agent_id == agent_id)
    supply_count = sum(1 for o in all_orders if o.supply_agent_id == agent_id)
    total_volume = sum(o.terms.price for o in all_orders if o.status == OS.COMPLETED)

    return {
        "total_orders": len(all_orders),
        "active_orders": len(active_orders),
        "as_demand": demand_count,
        "as_supply": supply_count,
        "by_status": status_counts,
        "total_completed_volume": total_volume,
    }
