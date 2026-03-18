"""
Order API Endpoints

REST API for order lifecycle management:
- Create order from pre-match or formal negotiation
- Order state transitions (confirm, start, deliver, accept, dispute, cancel)
- Query orders by agent, status, role

Authentication:
- All endpoints require X-API-Key + X-Agent-ID headers (API Key auth)
  or Bearer token (Wallet auth)
- Participants can only act on their own orders
"""

import logging
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

# Global service reference (set by main.py)
_order_service = None
_pre_match_service = None


def set_order_service(service):
    global _order_service
    _order_service = service


def set_pre_match_service(service):
    global _pre_match_service
    _pre_match_service = service


# ==================== Request Models ====================

class CreateOrderFromPreMatchRequest(BaseModel):
    """Create order from confirmed pre-match negotiation"""
    negotiation_id: str
    task_description: str | None = None


class CreateOrderFromNegotiationRequest(BaseModel):
    """Create order from formal negotiation"""
    negotiation_session_id: str
    price: float = Field(gt=0)
    delivery_time: datetime | None = None
    delivery_description: str = ""
    payment_terms: str = "escrow"
    milestones: list[dict[str, Any]] = Field(default_factory=list)
    task_description: str
    demand_agent_id: str
    supply_agent_id: str


class ConfirmOrderRequest(BaseModel):
    """Confirm an order (both parties must confirm)"""
    pass


class StartWorkRequest(BaseModel):
    """Start work on an order (supply agent only)"""
    pass


class SubmitDeliverableRequest(BaseModel):
    """Submit a deliverable for an order"""
    description: str
    artifact_type: str = "text"
    url_or_content: str = ""


class AcceptDeliverableRequest(BaseModel):
    """Accept deliverables and complete the order"""
    rating: int = Field(ge=1, le=5)
    comment: str = ""


class RaiseDisputeRequest(BaseModel):
    """Raise a dispute on an order"""
    reason: str = Field(min_length=1)


class CancelOrderRequest(BaseModel):
    """Cancel an order"""
    reason: str = ""


# ==================== Response Models ====================

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


# ==================== Endpoints ====================

@router.post("/from-pre-match", status_code=201)
async def create_order_from_pre_match_endpoint(
    request: CreateOrderFromPreMatchRequest,
    user: dict[str, Any] = Depends(get_current_user_unified),
):
    """Create an order from a confirmed pre-match negotiation.

    Requires:
        - X-API-Key + X-Agent-ID headers
        - Agent must be a party to the negotiation
        - Negotiation must already be confirmed
    """
    if not _order_service:
        raise HTTPException(status_code=503, detail="Order service not available")

    agent_id = user.get("agent_id") or user.get("user_id")

    result = await _order_service.create_order_from_pre_match(
        negotiation_id=request.negotiation_id,
        agent_id=agent_id,
    )

    if not result:
        raise HTTPException(status_code=400, detail="Failed to create order from pre-match negotiation")

    order = result
    return _order_to_response(order)


@router.post("/from-negotiation", status_code=201)
async def create_order_from_negotiation_endpoint(
    request: CreateOrderFromNegotiationRequest,
    user: dict[str, Any] = Depends(get_current_user_unified),
):
    """Create an order from a formal negotiation session.

    Requires:
        - X-API-Key + X-Agent-ID headers
        - Agent must be a party to the negotiation
    """
    if not _order_service:
        raise HTTPException(status_code=503, detail="Order service not available")

    from usmsb_sdk.agent_sdk.negotiation import NegotiationTerms

    terms = NegotiationTerms(
        price=request.price,
        delivery_time=request.delivery_time,
        delivery_description=request.delivery_description,
        payment_terms=request.payment_terms,
        milestones=request.milestones,
    )

    order = await _order_service.create_order_from_negotiation(
        negotiation_session_id=request.negotiation_session_id,
        terms=terms,
        demand_agent_id=request.demand_agent_id,
        supply_agent_id=request.supply_agent_id,
        task_description=request.task_description,
    )

    return _order_to_response(order)


@router.get("")
async def list_orders_endpoint(
    status: str | None = Query(None, description="Filter by status"),
    role: str | None = Query(None, description="Filter by role: demand or supply"),
    active_only: bool = Query(False, description="Only return active (non-terminal) orders"),
    limit: int = Query(50, ge=1, le=200),
    user: dict[str, Any] = Depends(get_current_user_unified),
):
    """List orders for the authenticated agent."""
    if not _order_service:
        raise HTTPException(status_code=503, detail="Order service not available")

    agent_id = user.get("agent_id") or user.get("user_id")

    if active_only:
        orders = await _order_service.get_active_orders(agent_id)
    else:
        from usmsb_sdk.services.order_state_machine import OrderStatus as OS
        status_filter = OS(status) if status else None
        orders = await _order_service.get_orders_for_agent(
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
    if not _order_service:
        raise HTTPException(status_code=503, detail="Order service not available")

    order = await _order_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Verify access
    agent_id = user.get("agent_id") or user.get("user_id")
    if agent_id not in [order.demand_agent_id, order.supply_agent_id]:
        raise HTTPException(status_code=403, detail="Not a party to this order")

    return _order_to_response(order)


@router.get("/{order_id}/status")
async def get_order_status_endpoint(
    order_id: str,
    user: dict[str, Any] = Depends(get_current_user_unified),
):
    """Get order status summary with available actions."""
    if not _order_service:
        raise HTTPException(status_code=503, detail="Order service not available")

    order = await _order_service.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    agent_id = user.get("agent_id") or user.get("user_id")
    if agent_id not in [order.demand_agent_id, order.supply_agent_id]:
        raise HTTPException(status_code=403, detail="Not a party to this order")

    is_supply = agent_id == order.supply_agent_id
    is_demand = agent_id == order.demand_agent_id
    sm = order._state_machine

    return {
        "order_id": order.order_id,
        "status": order.status.value,
        "is_supply": is_supply,
        "is_demand": is_demand,
        "price": order.terms.price,
        "delivery_deadline": order.delivery_deadline.isoformat() if order.delivery_deadline else None,
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
    if not _order_service:
        raise HTTPException(status_code=503, detail="Order service not available")

    agent_id = user.get("agent_id") or user.get("user_id")

    try:
        order = await _order_service.confirm_order(order_id, agent_id)
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
    if not _order_service:
        raise HTTPException(status_code=503, detail="Order service not available")

    agent_id = user.get("agent_id") or user.get("user_id")

    try:
        order = await _order_service.start_work(order_id, agent_id)
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
    if not _order_service:
        raise HTTPException(status_code=503, detail="Order service not available")

    agent_id = user.get("agent_id") or user.get("user_id")

    try:
        order = await _order_service.submit_deliverable(
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
    if not _order_service:
        raise HTTPException(status_code=503, detail="Order service not available")

    agent_id = user.get("agent_id") or user.get("user_id")

    try:
        order = await _order_service.accept_deliverable(
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
    if not _order_service:
        raise HTTPException(status_code=503, detail="Order service not available")

    agent_id = user.get("agent_id") or user.get("user_id")

    try:
        order = await _order_service.raise_dispute(order_id, agent_id, request.reason)
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
    if not _order_service:
        raise HTTPException(status_code=503, detail="Order service not available")

    agent_id = user.get("agent_id") or user.get("user_id")

    try:
        order = await _order_service.cancel_order(order_id, agent_id, request.reason)
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
    if not _order_service:
        raise HTTPException(status_code=503, detail="Order service not available")

    agent_id = user.get("agent_id") or user.get("user_id")

    from usmsb_sdk.services.order_state_machine import OrderStatus as OS

    all_orders = await _order_service.get_orders_for_agent(agent_id, limit=1000)
    active_orders = await _order_service.get_active_orders(agent_id)

    # Count by status
    status_counts: dict[str, int] = {}
    for o in all_orders:
        s = o.status.value
        status_counts[s] = status_counts.get(s, 0) + 1

    # Count as demand vs supply
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


# ==================== Helpers ====================

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
