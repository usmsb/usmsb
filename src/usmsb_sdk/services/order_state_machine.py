"""
Order State Machine

Defines the lifecycle states and transitions for a negotiated order.
This is the bridge between "negotiation accepted" and "task completed".
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """Order lifecycle status"""
    # Pre-order states
    CREATED = "created"              # Order created from negotiation
    CONFIRMED = "confirmed"          # Both parties confirmed

    # Active states
    IN_PROGRESS = "in_progress"      # Work started
    DELIVERED = "delivered"          # Work delivered, awaiting acceptance

    # Completion states
    COMPLETED = "completed"          # Accepted by demand side
    DISPUTED = "disputed"            # Dispute raised
    CANCELLED = "cancelled"          # Cancelled

    # Edge cases
    EXPIRED = "expired"              # Delivery deadline missed
    REFUNDED = "refunded"            # Refunded after cancellation


class OrderEvent(Enum):
    """Events that trigger state transitions"""
    ORDER_CREATED = "order_created"
    BOTH_CONFIRMED = "both_confirmed"
    WORK_STARTED = "work_started"
    DELIVERABLE_SUBMITTED = "deliverable_submitted"
    ACCEPTED = "accepted"
    DISPUTE_RAISED = "dispute_raised"
    CANCELLED = "cancelled"
    DEADLINE_MISSED = "deadline_missed"
    REFUND_PROCESSED = "refund_processed"
    EXPIRED = "expired"


# State transition table: (current_status, event) -> new_status
TRANSITIONS: dict[tuple[OrderStatus, OrderEvent], OrderStatus] = {
    # From CREATED
    (OrderStatus.CREATED, OrderEvent.both_confirmed): OrderStatus.CONFIRMED,
    (OrderStatus.CREATED, OrderEvent.cancelled): OrderStatus.CANCELLED,
    (OrderStatus.CREATED, OrderEvent.expired): OrderStatus.EXPIRED,

    # From CONFIRMED
    (OrderStatus.CONFIRMED, OrderEvent.work_started): OrderStatus.IN_PROGRESS,
    (OrderStatus.CONFIRMED, OrderEvent.cancelled): OrderStatus.CANCELLED,
    (OrderStatus.CONFIRMED, OrderEvent.expired): OrderStatus.EXPIRED,

    # From IN_PROGRESS
    (OrderStatus.IN_PROGRESS, OrderEvent.deliverable_submitted): OrderStatus.DELIVERED,
    (OrderStatus.IN_PROGRESS, OrderEvent.dispute_raised): OrderStatus.DISPUTED,
    (OrderStatus.IN_PROGRESS, OrderEvent.cancelled): OrderStatus.CANCELLED,
    (OrderStatus.IN_PROGRESS, OrderEvent.deadline_missed): OrderStatus.EXPIRED,

    # From DELIVERED
    (OrderStatus.DELIVERED, OrderEvent.accepted): OrderStatus.COMPLETED,
    (OrderStatus.DELIVERED, OrderEvent.dispute_raised): OrderStatus.DISPUTED,
    (OrderStatus.DELIVERED, OrderEvent.deadline_missed): OrderStatus.EXPIRED,

    # From DISPUTED
    (OrderStatus.DISPUTED, OrderEvent.accepted): OrderStatus.COMPLETED,
    (OrderStatus.DISPUTED, OrderEvent.refund_processed): OrderStatus.REFUNDED,
    (OrderStatus.DISPUTED, OrderEvent.cancelled): OrderStatus.CANCELLED,

    # From CANCELLED
    (OrderStatus.CANCELLED, OrderEvent.refund_processed): OrderStatus.REFUNDED,
}


VALID_TRANSITIONS: dict[OrderStatus, list[OrderEvent]] = {
    OrderStatus.CREATED: [OrderEvent.both_confirmed, OrderEvent.cancelled, OrderEvent.expired],
    OrderStatus.CONFIRMED: [OrderEvent.work_started, OrderEvent.cancelled, OrderEvent.expired],
    OrderStatus.IN_PROGRESS: [OrderEvent.deliverable_submitted, OrderEvent.dispute_raised, OrderEvent.cancelled, OrderEvent.deadline_missed],
    OrderStatus.DELIVERED: [OrderEvent.accepted, OrderEvent.dispute_raised, OrderEvent.deadline_missed],
    OrderStatus.DISPUTED: [OrderEvent.accepted, OrderEvent.refund_processed, OrderEvent.cancelled],
    OrderStatus.COMPLETED: [],
    OrderStatus.CANCELLED: [OrderEvent.refund_processed],
    OrderStatus.EXPIRED: [],
    OrderStatus.REFUNDED: [],
}


@dataclass
class OrderTransition:
    """A recorded state transition"""
    from_status: OrderStatus
    to_status: OrderStatus
    event: OrderEvent
    triggered_by: str  # agent_id
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_status": self.from_status.value,
            "to_status": self.to_status.value,
            "event": self.event.value,
            "triggered_by": self.triggered_by,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }


class OrderStateMachine:
    """
    Manages order state transitions with validation.
    """

    def __init__(self, initial_status: OrderStatus = OrderStatus.CREATED):
        self.current_status = initial_status
        self.history: list[OrderTransition] = []

    def can_transition(self, event: OrderEvent) -> bool:
        """Check if an event can trigger a valid transition from current status."""
        return (self.current_status, event) in TRANSITIONS

    def transition(self, event: OrderEvent, triggered_by: str, reason: str = "") -> OrderStatus:
        """
        Apply an event to transition the state machine.

        Args:
            event: The event to apply
            triggered_by: agent_id of who triggered this
            reason: Optional reason for the transition

        Returns:
            New status

        Raises:
            ValueError: If transition is invalid
        """
        key = (self.current_status, event)

        if key not in TRANSITIONS:
            valid = VALID_TRANSITIONS.get(self.current_status, [])
            raise ValueError(
                f"Invalid transition: {self.current_status.value} + {event.value}. "
                f"Valid events from {self.current_status.value}: {[e.value for e in valid]}"
            )

        old_status = self.current_status
        new_status = TRANSITIONS[key]

        transition_record = OrderTransition(
            from_status=old_status,
            to_status=new_status,
            event=event,
            triggered_by=triggered_by,
            reason=reason,
        )

        self.history.append(transition_record)
        self.current_status = new_status

        logger.info(
            f"Order state transition: {old_status.value} → {new_status.value} "
            f"(event: {event.value}, by: {triggered_by})"
        )

        return new_status

    def get_available_events(self) -> list[OrderEvent]:
        """Get list of events that can be triggered from current status."""
        return VALID_TRANSITIONS.get(self.current_status, [])

    def is_terminal(self) -> bool:
        """Check if current status is a terminal state (no further transitions)."""
        return len(self.history) > 0 and self.current_status in [
            OrderStatus.COMPLETED,
            OrderStatus.EXPIRED,
            OrderStatus.REFUNDED,
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_status": self.current_status.value,
            "available_events": [e.value for e in self.get_available_events()],
            "is_terminal": self.is_terminal(),
            "history": [t.to_dict() for t in self.history],
        }
