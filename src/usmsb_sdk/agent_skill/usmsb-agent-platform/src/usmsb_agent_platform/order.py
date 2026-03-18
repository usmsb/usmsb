"""
Order API for USMSB Agent Platform Skill.

Provides order lifecycle management:
- Create order from pre-match or formal negotiation
- Order state transitions (confirm, start, deliver, accept, dispute, cancel)
- Query orders by agent, status, role
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class OrderStatus(Enum):
    """Order lifecycle status."""
    CREATED = "created"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REFUNDED = "refunded"


@dataclass
class OrderTerms:
    """Agreed order terms between parties."""
    price: float
    delivery_time: Optional[str] = None
    delivery_description: str = ""
    quality_guarantees: dict[str, Any] = None
    payment_terms: str = "escrow"  # "upfront", "escrow", "milestone"
    milestones: list[dict[str, Any]] = None
    additional_conditions: dict[str, Any] = None

    def __post_init__(self):
        if self.quality_guarantees is None:
            self.quality_guarantees = {}
        if self.milestones is None:
            self.milestones = []
        if self.additional_conditions is None:
            self.additional_conditions = {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "price": self.price,
            "delivery_time": self.delivery_time,
            "delivery_description": self.delivery_description,
            "quality_guarantees": self.quality_guarantees,
            "payment_terms": self.payment_terms,
            "milestones": self.milestones,
            "additional_conditions": self.additional_conditions,
        }


@dataclass
class Deliverable:
    """A deliverable artifact."""
    artifact_id: str
    description: str
    artifact_type: str  # "text", "code", "document", "link"
    url_or_content: str
    submitted_at: str
    verified: bool = False


@dataclass
class Order:
    """Order data returned from API."""
    order_id: str
    source: str
    source_session_id: Optional[str]
    demand_agent_id: str
    supply_agent_id: str
    task_description: str
    terms: dict[str, Any]
    pool_id: Optional[str]
    status: str
    priority: str
    delivery_deadline: Optional[str]
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    completion_reason: Optional[str]
    deliverables: list[dict[str, Any]]
    acceptance_data: dict[str, Any]
    chain_order_id: Optional[str]
    chain_tx_hash: Optional[str]
    vibe_locked: float
    metadata: dict[str, Any]
    available_actions: list[str]
    state_history: list[dict[str, Any]]
    is_terminal: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Order":
        return cls(
            order_id=data["order_id"],
            source=data.get("source", ""),
            source_session_id=data.get("source_session_id"),
            demand_agent_id=data["demand_agent_id"],
            supply_agent_id=data["supply_agent_id"],
            task_description=data.get("task_description", ""),
            terms=data.get("terms", {}),
            pool_id=data.get("pool_id"),
            status=data.get("status", "created"),
            priority=data.get("priority", "normal"),
            delivery_deadline=data.get("delivery_deadline"),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            completed_at=data.get("completed_at"),
            completion_reason=data.get("completion_reason"),
            deliverables=data.get("deliverables", []),
            acceptance_data=data.get("acceptance_data", {}),
            chain_order_id=data.get("chain_order_id"),
            chain_tx_hash=data.get("chain_tx_hash"),
            vibe_locked=data.get("vibe_locked", 0.0),
            metadata=data.get("metadata", {}),
            available_actions=data.get("available_actions", []),
            state_history=data.get("state_history", []),
            is_terminal=data.get("is_terminal", False),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "source": self.source,
            "source_session_id": self.source_session_id,
            "demand_agent_id": self.demand_agent_id,
            "supply_agent_id": self.supply_agent_id,
            "task_description": self.task_description,
            "terms": self.terms,
            "pool_id": self.pool_id,
            "status": self.status,
            "priority": self.priority,
            "delivery_deadline": self.delivery_deadline,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "completion_reason": self.completion_reason,
            "deliverables": self.deliverables,
            "acceptance_data": self.acceptance_data,
            "chain_order_id": self.chain_order_id,
            "chain_tx_hash": self.chain_tx_hash,
            "vibe_locked": self.vibe_locked,
            "metadata": self.metadata,
            "available_actions": self.available_actions,
            "state_history": self.state_history,
            "is_terminal": self.is_terminal,
        }
