"""
Negotiated Order Manager

Agent SDK layer that bridges negotiation sessions to order creation.
Provides a single unified interface for:
- Pre-match negotiation → Order
- Formal negotiation → Order
- Direct order creation from agreed terms

This is the primary interface Agents use to go from "deal agreed" to "order created".
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from usmsb_sdk.agent_sdk.negotiation import (
    NegotiationManager,
    NegotiationTerms,
    NegotiationContext,
)
from usmsb_sdk.agent_sdk.platform_client import PlatformClient
from usmsb_sdk.services.order_service import (
    Order,
    OrderService,
    OrderTerms,
    OrderSource,
    OrderStatus,
)
from usmsb_sdk.services.pre_match_negotiation import PreMatchNegotiationService

logger = logging.getLogger(__name__)


@dataclass
class OrderCreationResult:
    """Result of creating an order from negotiation"""
    success: bool
    order: Order | None
    message: str
    negotiation_session_id: str | None = None


@dataclass
class NegotiationToOrderConfig:
    """Configuration for the negotiation-to-order bridge"""
    auto_create_order: bool = True
    auto_confirm_order: bool = False  # If True, skip second confirmation
    default_delivery_hours: int = 72
    create_joint_order_pool: bool = True


class NegotiatedOrderManager:
    """
    Bridges negotiation results to executable orders.

    This is the high-level manager Agents use after reaching agreement
    in either pre-match or formal negotiation. It handles the complete
    flow: terms normalization → order creation → state machine setup.

    Usage:
        # After pre-match negotiation confirmed
        result = await nom.create_order_from_pre_match(negotiation_id, my_agent_id)

        # After formal negotiation accepted
        result = await nom.create_order_from_negotiation(
            session_id=session_id,
            terms=accepted_terms,
            demand_agent_id=me,
            supply_agent_id=counterpart,
            task_description="..."
        )

        # Check order status
        order = await nom.get_order(order_id)
        print(f"Status: {order.status.value}")
    """

    def __init__(
        self,
        platform_client: PlatformClient,
        agent_id: str,
        order_service: OrderService | None = None,
        pre_match_negotiation: PreMatchNegotiationService | None = None,
        negotiation_manager: NegotiationManager | None = None,
        config: NegotiationToOrderConfig | None = None,
        logger: logging.Logger | None = None,
    ):
        self._platform = platform_client
        self.agent_id = agent_id
        self.order_service = order_service
        self.pre_match_negotiation = pre_match_negotiation
        self.negotiation_manager = negotiation_manager
        self.config = config or NegotiatedToOrderConfig()
        self.logger = logger or logging.getLogger(__name__)

    # ==================== Pre-match → Order ====================

    async def create_order_from_pre_match(
        self,
        negotiation_id: str,
        task_description: str | None = None,
    ) -> OrderCreationResult:
        """
        Create an order from a confirmed pre-match negotiation.

        Args:
            negotiation_id: The pre-match negotiation ID
            task_description: Override task description (optional)

        Returns:
            OrderCreationResult with created Order

        Raises:
            ValueError: If negotiation not confirmed
            PermissionError: If agent is not a party
        """
        if not self.order_service:
            return OrderCreationResult(
                success=False,
                order=None,
                message="OrderService not initialized",
            )

        try:
            order = await self.order_service.create_order_from_pre_match(
                negotiation_id=negotiation_id,
                agent_id=self.agent_id,
            )

            if not order:
                return OrderCreationResult(
                    success=False,
                    order=None,
                    message="Failed to create order from pre-match negotiation",
                    negotiation_session_id=negotiation_id,
                )

            # Override task description if provided
            if task_description:
                order.task_description = task_description

            self.logger.info(f"Created order {order.order_id} from pre-match {negotiation_id}")

            return OrderCreationResult(
                success=True,
                order=order,
                message=f"Order {order.order_id} created successfully",
                negotiation_session_id=negotiation_id,
            )

        except ValueError as e:
            return OrderCreationResult(
                success=False,
                order=None,
                message=str(e),
                negotiation_session_id=negotiation_id,
            )
        except PermissionError as e:
            return OrderCreationResult(
                success=False,
                order=None,
                message=str(e),
                negotiation_session_id=negotiation_id,
            )

    # ==================== Formal Negotiation → Order ====================

    async def create_order_from_negotiation(
        self,
        session_id: str,
        terms: NegotiationTerms,
        demand_agent_id: str,
        supply_agent_id: str,
        task_description: str,
    ) -> OrderCreationResult:
        """
        Create an order from a formal negotiation session.

        This is called after the negotiation.accept() returns successfully.

        Args:
            session_id: The negotiation session ID
            terms: The accepted negotiation terms
            demand_agent_id: Demand side agent ID
            supply_agent_id: Supply side agent ID
            task_description: Task description

        Returns:
            OrderCreationResult with created Order
        """
        if not self.order_service:
            return OrderCreationResult(
                success=False,
                order=None,
                message="OrderService not initialized",
            )

        try:
            order = await self.order_service.create_order_from_negotiation(
                negotiation_session_id=session_id,
                terms=terms,
                demand_agent_id=demand_agent_id,
                supply_agent_id=supply_agent_id,
                task_description=task_description,
            )

            self.logger.info(f"Created order {order.order_id} from negotiation {session_id}")

            return OrderCreationResult(
                success=True,
                order=order,
                message=f"Order {order.order_id} created successfully",
                negotiation_session_id=session_id,
            )

        except Exception as e:
            self.logger.error(f"Failed to create order from negotiation {session_id}: {e}")
            return OrderCreationResult(
                success=False,
                order=None,
                message=str(e),
                negotiation_session_id=session_id,
            )

    # ==================== Order Lifecycle ====================

    async def confirm_order(self, order_id: str) -> OrderCreationResult:
        """Confirm an order (both parties must call)."""
        if not self.order_service:
            return OrderCreationResult(success=False, order=None, message="OrderService not initialized")

        try:
            order = await self.order_service.confirm_order(order_id, self.agent_id)
            return OrderCreationResult(
                success=True,
                order=order,
                message=f"Order {order_id} confirmed",
            )
        except Exception as e:
            return OrderCreationResult(success=False, order=None, message=str(e))

    async def start_work(self, order_id: str) -> OrderCreationResult:
        """Start work on an order (supply agent only)."""
        if not self.order_service:
            return OrderCreationResult(success=False, order=None, message="OrderService not initialized")

        try:
            order = await self.order_service.start_work(order_id, self.agent_id)
            return OrderCreationResult(
                success=True,
                order=order,
                message=f"Order {order_id} work started",
            )
        except Exception as e:
            return OrderCreationResult(success=False, order=None, message=str(e))

    async def submit_deliverable(
        self,
        order_id: str,
        description: str,
        artifact_type: str = "text",
        url_or_content: str = "",
    ) -> OrderCreationResult:
        """Submit a deliverable for an order."""
        if not self.order_service:
            return OrderCreationResult(success=False, order=None, message="OrderService not initialized")

        try:
            order = await self.order_service.submit_deliverable(
                order_id=order_id,
                agent_id=self.agent_id,
                description=description,
                artifact_type=artifact_type,
                url_or_content=url_or_content,
            )
            return OrderCreationResult(
                success=True,
                order=order,
                message=f"Deliverable submitted for order {order_id}",
            )
        except Exception as e:
            return OrderCreationResult(success=False, order=None, message=str(e))

    async def accept_deliverable(
        self,
        order_id: str,
        rating: int,
        comment: str = "",
    ) -> OrderCreationResult:
        """Accept deliverables and complete the order (demand agent only)."""
        if not self.order_service:
            return OrderCreationResult(success=False, order=None, message="OrderService not initialized")

        try:
            order = await self.order_service.accept_deliverable(
                order_id=order_id,
                agent_id=self.agent_id,
                rating=rating,
                comment=comment,
            )
            return OrderCreationResult(
                success=True,
                order=order,
                message=f"Order {order_id} completed (rating: {rating})",
            )
        except Exception as e:
            return OrderCreationResult(success=False, order=None, message=str(e))

    async def raise_dispute(
        self,
        order_id: str,
        reason: str,
    ) -> OrderCreationResult:
        """Raise a dispute on an order."""
        if not self.order_service:
            return OrderCreationResult(success=False, order=None, message="OrderService not initialized")

        try:
            order = await self.order_service.raise_dispute(order_id, self.agent_id, reason)
            return OrderCreationResult(
                success=True,
                order=order,
                message=f"Dispute raised on order {order_id}: {reason}",
            )
        except Exception as e:
            return OrderCreationResult(success=False, order=None, message=str(e))

    async def cancel_order(
        self,
        order_id: str,
        reason: str = "",
    ) -> OrderCreationResult:
        """Cancel an order."""
        if not self.order_service:
            return OrderCreationResult(success=False, order=None, message="OrderService not initialized")

        try:
            order = await self.order_service.cancel_order(order_id, self.agent_id, reason)
            return OrderCreationResult(
                success=True,
                order=order,
                message=f"Order {order_id} cancelled: {reason}",
            )
        except Exception as e:
            return OrderCreationResult(success=False, order=None, message=str(e))

    # ==================== Queries ====================

    async def get_order(self, order_id: str) -> Order | None:
        """Get an order by ID."""
        if self.order_service:
            return await self.order_service.get_order(order_id)
        return None

    async def list_my_orders(
        self,
        as_role: str | None = None,  # "demand", "supply", or None for both
        active_only: bool = False,
    ) -> list[Order]:
        """List orders for this agent."""
        if not self.order_service:
            return []

        if active_only:
            return await self.order_service.get_active_orders(self.agent_id)

        role = None
        if as_role == "demand":
            role = "demand"
        elif as_role == "supply":
            role = "supply"

        return await self.order_service.get_orders_for_agent(self.agent_id, role=role)

    async def get_order_status(self, order_id: str) -> dict[str, Any] | None:
        """Get a summary of order status including available actions."""
        order = await self.get_order(order_id)
        if not order:
            return None

        available_events = order._state_machine.get_available_events()
        is_supply = self.agent_id == order.supply_agent_id
        is_demand = self.agent_id == order.demand_agent_id

        return {
            "order_id": order.order_id,
            "status": order.status.value,
            "is_supply": is_supply,
            "is_demand": is_demand,
            "price": order.terms.price,
            "delivery_deadline": order.delivery_deadline.isoformat() if order.delivery_deadline else None,
            "available_actions": [e.value for e in available_events],
            "next_expected_action": self._get_next_action(order, is_supply, is_demand),
            "progress": self._get_order_progress(order),
        }

    def _get_next_action(self, order: Order, is_supply: bool, is_demand: bool) -> str | None:
        """Determine what the next expected action is for this agent."""
        if order.status == OrderStatus.CREATED:
            return "confirm_order"
        elif order.status == OrderStatus.CONFIRMED and is_supply:
            return "start_work"
        elif order.status == OrderStatus.IN_PROGRESS and is_supply:
            return "submit_deliverable"
        elif order.status == OrderStatus.DELIVERED and is_demand:
            return "accept_deliverable"
        elif order.status in [OrderStatus.IN_PROGRESS, OrderStatus.DELIVERED]:
            return "wait"
        return None

    def _get_order_progress(self, order: Order) -> float:
        """Get a 0-1 progress indicator for the order."""
        progress_map = {
            OrderStatus.CREATED: 0.1,
            OrderStatus.CONFIRMED: 0.2,
            OrderStatus.IN_PROGRESS: 0.5,
            OrderStatus.DELIVERED: 0.8,
            OrderStatus.COMPLETED: 1.0,
            OrderStatus.DISPUTED: 0.5,
            OrderStatus.CANCELLED: 0.0,
            OrderStatus.EXPIRED: 0.0,
            OrderStatus.REFUNDED: 0.0,
        }
        return progress_map.get(order.status, 0.0)
