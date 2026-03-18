"""
Order Service

Core order management service that bridges negotiation results
into executable orders with full lifecycle management.

Key Responsibilities:
1. Create Order from negotiation session (pre-match or formal negotiation)
2. Manage order state transitions via OrderStateMachine
3. Coordinate with JointOrderService for pool/demand creation
4. Integrate with blockchain for fund托管
5. Emit events for downstream services (reputation, notifications, etc.)
"""

import asyncio
import json
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

try:
    from sqlalchemy import Boolean, Column, DateTime, Float, String, Text
    from sqlalchemy.ext.declarative import declarative_base
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

from usmsb_sdk.agent_sdk.negotiation import NegotiationTerms
from usmsb_sdk.services.joint_order_service import JointOrderService
from usmsb_sdk.services.order_state_machine import OrderStateMachine, OrderStatus, OrderEvent
from usmsb_sdk.services.pre_match_negotiation import PreMatchNegotiationService

logger = logging.getLogger(__name__)

if SQLALCHEMY_AVAILABLE:
    Base = declarative_base()
else:
    Base = None


class OrderSource(Enum):
    """Source of the order"""
    PRE_MATCH_NEGOTIATION = "pre_match_negotiation"
    FORMAL_NEGOTIATION = "formal_negotiation"
    DIRECT_CREATE = "direct_create"


class OrderPriority(Enum):
    """Order priority level"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# ==================== Database Model ====================

if SQLALCHEMY_AVAILABLE:
    class OrderDB(Base):
        """Database model for orders"""
        __tablename__ = "orders"

        order_id = Column(String(64), primary_key=True)
        source = Column(String(32), nullable=False)
        source_session_id = Column(String(128))

        demand_agent_id = Column(String(64), nullable=False)
        supply_agent_id = Column(String(64), nullable=False)
        task_description = Column(Text, nullable=False)
        agreed_terms = Column(Text)
        pool_id = Column(String(128))
        status = Column(String(32), default=OrderStatus.CREATED.value)
        priority = Column(String(16), default=OrderPriority.NORMAL.value)
        delivery_deadline = Column(DateTime)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        completed_at = Column(DateTime)
        completion_reason = Column(Text)
        deliverables = Column(Text)
        acceptance_data = Column(Text)
        chain_order_id = Column(String(256))
        chain_tx_hash = Column(String(256))
        vibe_locked = Column(Float, default=0.0)
        metadata = Column(Text)
        is_cancelled = Column(Boolean, default=False)
else:
    # Dummy class when SQLAlchemy not available
    class OrderDB:
        pass


# ==================== Data Classes ====================

@dataclass
class OrderTerms:
    """Agreed order terms (normalized from negotiation terms)"""
    price: float
    delivery_time: datetime | None = None
    delivery_description: str = ""
    quality_guarantees: dict[str, Any] = field(default_factory=dict)
    payment_terms: str = "escrow"  # upfront, escrow, milestone
    milestones: list[dict[str, Any]] = field(default_factory=list)
    additional_conditions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_negotiation_terms(cls, terms: NegotiationTerms) -> "OrderTerms":
        return cls(
            price=terms.price,
            delivery_time=terms.delivery_time,
            delivery_description=terms.delivery_description,
            quality_guarantees=terms.quality_guarantees,
            payment_terms=terms.payment_terms,
            milestones=terms.milestones,
            additional_conditions=terms.additional_conditions,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OrderTerms":
        delivery_time = None
        if data.get("delivery_time"):
            if isinstance(data["delivery_time"], str):
                delivery_time = datetime.fromisoformat(data["delivery_time"])
            else:
                delivery_time = data["delivery_time"]
        return cls(
            price=data.get("price", 0),
            delivery_time=delivery_time,
            delivery_description=data.get("delivery_description", ""),
            quality_guarantees=data.get("quality_guarantees", {}),
            payment_terms=data.get("payment_terms", "escrow"),
            milestones=data.get("milestones", []),
            additional_conditions=data.get("additional_conditions", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "price": self.price,
            "delivery_time": self.delivery_time.isoformat() if self.delivery_time else None,
            "delivery_description": self.delivery_description,
            "quality_guarantees": self.quality_guarantees,
            "payment_terms": self.payment_terms,
            "milestones": self.milestones,
            "additional_conditions": self.additional_conditions,
        }


@dataclass
class Deliverable:
    """A deliverable artifact"""
    artifact_id: str
    description: str
    artifact_type: str  # file, link, text, code, etc.
    url_or_content: str
    submitted_at: datetime = field(default_factory=datetime.utcnow)
    verified: bool = False


@dataclass
class Order:
    """In-memory order representation"""
    order_id: str
    source: OrderSource
    source_session_id: str | None

    demand_agent_id: str
    supply_agent_id: str
    task_description: str

    terms: OrderTerms

    pool_id: str | None = None
    status: OrderStatus = OrderStatus.CREATED

    priority: OrderPriority = OrderPriority.NORMAL
    delivery_deadline: datetime | None = None

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    completion_reason: str | None = None

    deliverables: list[Deliverable] = field(default_factory=list)
    acceptance_data: dict[str, Any] = field(default_factory=dict)

    chain_order_id: str | None = None
    chain_tx_hash: str | None = None
    vibe_locked: float = 0.0

    metadata: dict[str, Any] = field(default_factory=dict)

    _state_machine: OrderStateMachine = field(default_factory=OrderStateMachine, repr=False)

    @classmethod
    def from_db(cls, row: OrderDB) -> "Order":
        state_machine = OrderStateMachine(OrderStatus(row.status))

        terms = OrderTerms.from_dict(json.loads(row.agreed_terms)) if row.agreed_terms else OrderTerms(price=0)

        deliverables = []
        if row.deliverables:
            for d in json.loads(row.deliverables):
                deliverables.append(Deliverable(
                    artifact_id=d.get("artifact_id", ""),
                    description=d.get("description", ""),
                    artifact_type=d.get("artifact_type", ""),
                    url_or_content=d.get("url_or_content", ""),
                    submitted_at=datetime.fromisoformat(d["submitted_at"]) if isinstance(d.get("submitted_at"), str) else datetime.utcnow(),
                    verified=d.get("verified", False),
                ))

        return cls(
            order_id=row.order_id,
            source=OrderSource(row.source),
            source_session_id=row.source_session_id,
            demand_agent_id=row.demand_agent_id,
            supply_agent_id=row.supply_agent_id,
            task_description=row.task_description,
            terms=terms,
            pool_id=row.pool_id,
            status=OrderStatus(row.status),
            priority=OrderPriority(row.priority),
            delivery_deadline=row.delivery_deadline,
            created_at=row.created_at or datetime.utcnow(),
            updated_at=row.updated_at or datetime.utcnow(),
            completed_at=row.completed_at,
            completion_reason=row.completion_reason,
            deliverables=deliverables,
            acceptance_data=json.loads(row.acceptance_data) if row.acceptance_data else {},
            chain_order_id=row.chain_order_id,
            chain_tx_hash=row.chain_tx_hash,
            vibe_locked=row.vibe_locked,
            metadata=json.loads(row.metadata) if row.metadata else {},
            _state_machine=state_machine,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "order_id": self.order_id,
            "source": self.source.value,
            "source_session_id": self.source_session_id,
            "demand_agent_id": self.demand_agent_id,
            "supply_agent_id": self.supply_agent_id,
            "task_description": self.task_description,
            "terms": self.terms.to_dict(),
            "pool_id": self.pool_id,
            "status": self.status.value,
            "priority": self.priority.value,
            "delivery_deadline": self.delivery_deadline.isoformat() if self.delivery_deadline else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "completion_reason": self.completion_reason,
            "deliverables": [
                {
                    "artifact_id": d.artifact_id,
                    "description": d.description,
                    "artifact_type": d.artifact_type,
                    "url_or_content": d.url_or_content,
                    "submitted_at": d.submitted_at.isoformat(),
                    "verified": d.verified,
                }
                for d in self.deliverables
            ],
            "acceptance_data": self.acceptance_data,
            "chain_order_id": self.chain_order_id,
            "chain_tx_hash": self.chain_tx_hash,
            "vibe_locked": self.vibe_locked,
            "metadata": self.metadata,
            "state_machine": self._state_machine.to_dict(),
        }


# ==================== Main Service ====================

class OrderService:
    """
    Order Service — the bridge from negotiation to executable orders.

    Responsibilities:
    1. Create orders from pre-match or formal negotiation results
    2. Manage order lifecycle via state machine
    3. Coordinate with JointOrderService for pool creation
    4. Handle fund locking, delivery, acceptance
    5. Emit events for reputation, notifications
    """

    DEFAULT_DELIVERY_HOURS = 72  # 3 days default

    def __init__(
        self,
        db_session=None,
        joint_order_service: JointOrderService | None = None,
        pre_match_negotiation: PreMatchNegotiationService | None = None,
        logger: logging.Logger | None = None,
    ):
        self.db = db_session
        self.joint_order = joint_order_service
        self.pre_match_negotiation = pre_match_negotiation
        self.logger = logger or logging.getLogger(__name__)

        # In-memory cache
        self._orders: dict[str, Order] = {}

        # Event callbacks
        self.on_order_created: Callable[[Order], None] | None = None
        self.on_order_confirmed: Callable[[Order], None] | None = None
        self.on_order_completed: Callable[[Order], None] | None = None
        self.on_order_disputed: Callable[[Order, str], None] | None = None
        self.on_order_cancelled: Callable[[Order, str], None] | None = None

    # ==================== Order Creation ====================

    async def create_order_from_pre_match(
        self,
        negotiation_id: str,
        agent_id: str,
    ) -> Order | None:
        """
        Create an order from a confirmed pre-match negotiation.

        This is called after pre_match_negotiation.confirm_match() returns confirmed.
        It reads the negotiation's agreed_terms and creates a formal order.

        Args:
            negotiation_id: The pre-match negotiation ID
            agent_id: The agent requesting order creation (must be a party)

        Returns:
            Created Order or None
        """
        if not self.pre_match_negotiation:
            self.logger.error("PreMatchNegotiationService not available")
            return None

        neg = await self.pre_match_negotiation.get_negotiation(negotiation_id)
        if not neg:
            self.logger.error(f"Pre-match negotiation {negotiation_id} not found")
            return None

        if neg["status"] != "confirmed":
            raise ValueError(f"Negotiation {negotiation_id} is not confirmed, status: {neg['status']}")

        # Only participants can create orders
        if agent_id not in [neg["demand_agent_id"], neg["supply_agent_id"]]:
            raise PermissionError(f"Agent {agent_id} is not a party to negotiation {negotiation_id}")

        # Determine demand/supply
        if agent_id == neg["demand_agent_id"]:
            demand_agent_id = neg["demand_agent_id"]
            supply_agent_id = neg["supply_agent_id"]
        else:
            demand_agent_id = neg["supply_agent_id"]
            supply_agent_id = neg["demand_agent_id"]

        # Parse agreed terms
        agreed_terms_data = neg.get("agreed_terms") or neg.get("proposed_terms", {})
        if isinstance(agreed_terms_data, str):
            agreed_terms_data = json.loads(agreed_terms_data)
        terms = OrderTerms.from_dict(agreed_terms_data.get("terms", agreed_terms_data))

        # Calculate delivery deadline
        delivery_deadline = None
        if terms.delivery_time:
            delivery_deadline = terms.delivery_time
        elif terms.milestones:
            # Use last milestone deadline
            last = terms.milestones[-1]
            if isinstance(last.get("deadline"), (int, float)):
                delivery_deadline = datetime.fromtimestamp(last["deadline"])
        if not delivery_deadline:
            delivery_deadline = datetime.utcnow() + timedelta(hours=self.DEFAULT_DELIVERY_HOURS)

        order_id = f"order-{uuid.uuid4().hex[:12]}"

        order = Order(
            order_id=order_id,
            source=OrderSource.PRE_MATCH_NEGOTIATION,
            source_session_id=negotiation_id,
            demand_agent_id=demand_agent_id,
            supply_agent_id=supply_agent_id,
            task_description=neg.get("scope_confirmation", {}).get("deliverables", ["Task"]) or ["Task"],
            terms=terms,
            priority=OrderPriority.NORMAL,
            delivery_deadline=delivery_deadline,
        )

        # Persist to DB
        await self._save_order(order)

        self._orders[order_id] = order
        self.logger.info(f"Order {order_id} created from pre-match negotiation {negotiation_id}")

        if self.on_order_created:
            self.on_order_created(order)

        return order

    async def create_order_from_negotiation(
        self,
        negotiation_session_id: str,
        terms: NegotiationTerms,
        demand_agent_id: str,
        supply_agent_id: str,
        task_description: str,
    ) -> Order:
        """
        Create an order from a formal negotiation session.

        Called after negotiation.accept() successfully returns with accepted status.

        Args:
            negotiation_session_id: The negotiation session ID
            terms: The accepted negotiation terms
            demand_agent_id: Demand side agent ID
            supply_agent_id: Supply side agent ID
            task_description: Task description

        Returns:
            Created Order
        """
        order_id = f"order-{uuid.uuid4().hex[:12]}"

        # Determine deadline
        delivery_deadline = terms.delivery_time if terms.delivery_time else (
            datetime.utcnow() + timedelta(hours=self.DEFAULT_DELIVERY_HOURS)
        )

        order = Order(
            order_id=order_id,
            source=OrderSource.FORMAL_NEGOTIATION,
            source_session_id=negotiation_session_id,
            demand_agent_id=demand_agent_id,
            supply_agent_id=supply_agent_id,
            task_description=task_description,
            terms=OrderTerms.from_negotiation_terms(terms),
            delivery_deadline=delivery_deadline,
        )

        await self._save_order(order)
        self._orders[order_id] = order

        self.logger.info(f"Order {order_id} created from negotiation {negotiation_session_id}")

        if self.on_order_created:
            self.on_order_created(order)

        return order

    # ==================== State Transitions ====================

    async def confirm_order(self, order_id: str, confirming_agent_id: str) -> Order:
        """
        Confirm order — both parties must call this.

        First call transitions CREATED → CONFIRMED.
        """
        order = await self._get_order(order_id)

        if confirming_agent_id not in [order.demand_agent_id, order.supply_agent_id]:
            raise PermissionError(f"Agent {confirming_agent_id} is not a party to order {order_id}")

        # Determine which confirmation this is
        already_confirmed = order.metadata.get("_demand_confirmed") and order.metadata.get("_supply_confirmed")
        is_demand = confirming_agent_id == order.demand_agent_id

        if is_demand:
            order.metadata["_demand_confirmed"] = True
        else:
            order.metadata["_supply_confirmed"] = True

        both_confirmed = order.metadata.get("_demand_confirmed") and order.metadata.get("_supply_confirmed")

        if both_confirmed and not already_confirmed:
            # First time both confirmed → transition state
            new_status = order._state_machine.transition(
                OrderEvent.both_confirmed,
                triggered_by=confirming_agent_id,
                reason="Both parties confirmed the order"
            )
            order.status = new_status
            await self._save_order(order)

            self.logger.info(f"Order {order_id} confirmed by both parties")

            if self.on_order_confirmed:
                self.on_order_confirmed(order)
        else:
            self.logger.info(
                f"Order {order_id} partial confirmation: "
                f"demand={order.metadata.get('_demand_confirmed')}, "
                f"supply={order.metadata.get('_supply_confirmed')}"
            )

        return order

    async def start_work(self, order_id: str, agent_id: str) -> Order:
        """Transition CONFIRMED → IN_PROGRESS (supply agent starts work)."""
        order = await self._get_order(order_id)

        if agent_id != order.supply_agent_id:
            raise PermissionError("Only the supply agent can start work")

        new_status = order._state_machine.transition(
            OrderEvent.work_started,
            triggered_by=agent_id,
        )
        order.status = new_status
        await self._save_order(order)

        self.logger.info(f"Order {order_id} work started by {agent_id}")
        return order

    async def submit_deliverable(
        self,
        order_id: str,
        agent_id: str,
        description: str,
        artifact_type: str,
        url_or_content: str,
    ) -> Order:
        """Transition IN_PROGRESS → DELIVERED (submit deliverable)."""
        order = await self._get_order(order_id)

        if agent_id != order.supply_agent_id:
            raise PermissionError("Only the supply agent can submit deliverables")

        deliverable = Deliverable(
            artifact_id=f"art-{uuid.uuid4().hex[:8]}",
            description=description,
            artifact_type=artifact_type,
            url_or_content=url_or_content,
        )
        order.deliverables.append(deliverable)

        # Count total expected deliverables
        expected_count = len(order.terms.milestones) if order.terms.milestones else 1
        submitted_count = len(order.deliverables)

        # Auto-transition when all deliverables submitted
        if submitted_count >= expected_count:
            new_status = order._state_machine.transition(
                OrderEvent.deliverable_submitted,
                triggered_by=agent_id,
            )
            order.status = new_status
            self.logger.info(f"Order {order_id} all deliverables submitted, moved to DELIVERED")

        await self._save_order(order)
        return order

    async def accept_deliverable(
        self,
        order_id: str,
        agent_id: str,
        rating: int,
        comment: str = "",
    ) -> Order:
        """Transition DELIVERED → COMPLETED (demand agent accepts)."""
        order = await self._get_order(order_id)

        if agent_id != order.demand_agent_id:
            raise PermissionError("Only the demand agent can accept deliverables")

        if not (1 <= rating <= 5):
            raise ValueError("Rating must be between 1 and 5")

        new_status = order._state_machine.transition(
            OrderEvent.accepted,
            triggered_by=agent_id,
        )

        order.status = new_status
        order.acceptance_data = {
            "rating": rating,
            "comment": comment,
            "accepted_at": datetime.utcnow().isoformat(),
        }
        order.completed_at = datetime.utcnow()
        order.completion_reason = "Accepted by demand side"

        await self._save_order(order)

        self.logger.info(f"Order {order_id} accepted (rating: {rating})")

        if self.on_order_completed:
            self.on_order_completed(order)

        return order

    async def raise_dispute(
        self,
        order_id: str,
        agent_id: str,
        reason: str,
    ) -> Order:
        """Raise a dispute on an order."""
        order = await self._get_order(order_id)

        if agent_id not in [order.demand_agent_id, order.supply_agent_id]:
            raise PermissionError(f"Agent {agent_id} is not a party to order {order_id}")

        if not order._state_machine.can_transition(OrderEvent.dispute_raised):
            raise ValueError(f"Cannot raise dispute from status {order.status.value}")

        new_status = order._state_machine.transition(
            OrderEvent.dispute_raised,
            triggered_by=agent_id,
            reason=reason,
        )
        order.status = new_status
        order.metadata["dispute_reason"] = reason
        order.metadata["dispute_raised_by"] = agent_id

        await self._save_order(order)

        self.logger.warning(f"Dispute raised on order {order_id}: {reason}")

        if self.on_order_disputed:
            self.on_order_disputed(order, reason)

        return order

    async def cancel_order(
        self,
        order_id: str,
        agent_id: str,
        reason: str = "",
    ) -> Order:
        """Cancel an order."""
        order = await self._get_order(order_id)

        if agent_id not in [order.demand_agent_id, order.supply_agent_id]:
            raise PermissionError(f"Agent {agent_id} is not a party to order {order_id}")

        if not order._state_machine.can_transition(OrderEvent.cancelled):
            raise ValueError(f"Cannot cancel order from status {order.status.value}")

        new_status = order._state_machine.transition(
            OrderEvent.cancelled,
            triggered_by=agent_id,
            reason=reason,
        )
        order.status = new_status
        order.completion_reason = reason

        await self._save_order(order)

        self.logger.info(f"Order {order_id} cancelled by {agent_id}: {reason}")

        if self.on_order_cancelled:
            self.on_order_cancelled(order, reason)

        return order

    # ==================== JointOrder Integration ====================

    async def create_joint_order_pool(
        self,
        order_id: str,
        creator_private_key: str | None = None,
    ) -> str | None:
        """
        Create a JointOrder pool from an order.

        This locks VIBE into the blockchain contract.

        Args:
            order_id: The order to create pool for
            creator_private_key: Private key for signing (if on-chain)

        Returns:
            pool_id from JointOrderService or None
        """
        if not self.joint_order:
            self.logger.warning("JointOrderService not available, skipping pool creation")
            return None

        order = await self._get_order(order_id)

        # Create demand for this order's terms
        from usmsb_sdk.services.joint_order_service import Demand
        demand = await self.joint_order.create_demand(
            user_id=order.demand_agent_id,
            service_type=order.metadata.get("service_type", "general"),
            budget=order.terms.price,
            requirements={
                "task_description": order.task_description,
                "order_id": order_id,
            },
            deadline=order.delivery_deadline.timestamp() if order.delivery_deadline else None,
        )

        # Try to aggregate into existing pool or create new
        pool, is_new = await self.joint_order.aggregate_demands(demand)

        if pool:
            order.pool_id = pool.pool_id
            await self._save_order(order)
            self.logger.info(f"Order {order_id} joined/created pool {pool.pool_id}")
            return pool.pool_id

        return None

    # ==================== Queries ====================

    async def get_order(self, order_id: str) -> Order | None:
        """Get an order by ID."""
        return await self._get_order(order_id)

    async def get_orders_for_agent(
        self,
        agent_id: str,
        status: OrderStatus | None = None,
        role: str | None = None,  # "demand" or "supply"
        limit: int = 50,
    ) -> list[Order]:
        """Get all orders involving an agent."""
        if not self.db:
            # Return from memory
            orders = [o for o in self._orders.values()]
        else:
            query = self.db.query(OrderDB).filter(
                (OrderDB.demand_agent_id == agent_id) |
                (OrderDB.supply_agent_id == agent_id)
            )
            if status:
                query = query.filter(OrderDB.status == status.value)
            orders = [Order.from_db(row) for row in query.limit(limit).all()]

        # Filter by role
        if role == "demand":
            orders = [o for o in orders if o.demand_agent_id == agent_id]
        elif role == "supply":
            orders = [o for o in orders if o.supply_agent_id == agent_id]

        return sorted(orders, key=lambda o: o.updated_at, reverse=True)[:limit]

    async def get_active_orders(self, agent_id: str) -> list[Order]:
        """Get all active orders for an agent (not terminal states)."""
        terminal = [OrderStatus.COMPLETED.value, OrderStatus.CANCELLED.value, OrderStatus.EXPIRED.value, OrderStatus.REFUNDED.value]
        if not self.db:
            return [
                o for o in self._orders.values()
                if agent_id in [o.demand_agent_id, o.supply_agent_id]
                and o.status.value not in terminal
            ]

        rows = self.db.query(OrderDB).filter(
            (OrderDB.demand_agent_id == agent_id) | (OrderDB.supply_agent_id == agent_id),
            ~OrderDB.status.in_(terminal),
        ).all()

        return [Order.from_db(row) for row in rows]

    # ==================== Internal ====================

    async def _get_order(self, order_id: str) -> Order:
        """Get order from cache or DB."""
        if order_id in self._orders:
            return self._orders[order_id]

        if self.db and SQLALCHEMY_AVAILABLE:
            row = self.db.query(OrderDB).filter(OrderDB.order_id == order_id).first()
            if row:
                order = Order.from_db(row)
                self._orders[order_id] = order
                return order

        raise ValueError(f"Order {order_id} not found")

    async def _save_order(self, order: Order) -> None:
        """Persist order to database."""
        if not self.db or not SQLALCHEMY_AVAILABLE:
            # Store in memory only
            self._orders[order.order_id] = order
            return

        row = self.db.query(OrderDB).filter(OrderDB.order_id == order.order_id).first()

        now = datetime.utcnow()
        if not row:
            row = OrderDB(
                order_id=order.order_id,
                source=order.source.value,
                source_session_id=order.source_session_id,
                demand_agent_id=order.demand_agent_id,
                supply_agent_id=order.supply_agent_id,
                task_description=(
                    order.task_description[0]
                    if isinstance(order.task_description, list)
                    else order.task_description
                ),
                agreed_terms=json.dumps(order.terms.to_dict()),
                pool_id=order.pool_id,
                status=order.status.value,
                priority=order.priority.value,
                delivery_deadline=order.delivery_deadline,
                created_at=order.created_at,
                updated_at=now,
                completed_at=order.completed_at,
                completion_reason=order.completion_reason,
                deliverables=json.dumps([
                    {
                        "artifact_id": d.artifact_id,
                        "description": d.description,
                        "artifact_type": d.artifact_type,
                        "url_or_content": d.url_or_content,
                        "submitted_at": d.submitted_at.isoformat(),
                        "verified": d.verified,
                    }
                    for d in order.deliverables
                ]),
                acceptance_data=json.dumps(order.acceptance_data),
                chain_order_id=order.chain_order_id,
                chain_tx_hash=order.chain_tx_hash,
                vibe_locked=order.vibe_locked,
                metadata=json.dumps(order.metadata),
            )
            self.db.add(row)
        else:
            row.status = order.status.value
            row.updated_at = now
            row.completed_at = order.completed_at
            row.completion_reason = order.completion_reason
            row.deliverables = json.dumps([
                {
                    "artifact_id": d.artifact_id,
                    "description": d.description,
                    "artifact_type": d.artifact_type,
                    "url_or_content": d.url_or_content,
                    "submitted_at": d.submitted_at.isoformat(),
                    "verified": d.verified,
                }
                for d in order.deliverables
            ])
            row.acceptance_data = json.dumps(order.acceptance_data)
            row.pool_id = order.pool_id
            row.chain_order_id = order.chain_order_id
            row.chain_tx_hash = order.chain_tx_hash
            row.vibe_locked = order.vibe_locked
            row.metadata = json.dumps(order.metadata)

        self.db.commit()
