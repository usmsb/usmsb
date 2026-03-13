"""
WebSocket Notifications for Pre-Match Negotiation

Provides real-time notifications for:
- Negotiation status changes
- New questions and answers
- Verification requests and responses
- Terms proposals and agreements
- Match confirmations and declines
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of negotiation notifications"""
    # Negotiation lifecycle
    NEGOTIATION_INITIATED = "negotiation_initiated"
    NEGOTIATION_STATUS_CHANGED = "negotiation_status_changed"
    NEGOTIATION_EXPIRED = "negotiation_expired"
    NEGOTIATION_CANCELLED = "negotiation_cancelled"

    # Q&A
    QUESTION_ASKED = "question_asked"
    QUESTION_ANSWERED = "question_answered"

    # Verification
    VERIFICATION_REQUESTED = "verification_requested"
    VERIFICATION_RESPONDED = "verification_responded"
    VERIFICATION_COMPLETED = "verification_completed"

    # Scope
    SCOPE_PROPOSED = "scope_proposed"
    SCOPE_CONFIRMED = "scope_confirmed"

    # Terms
    TERMS_PROPOSED = "terms_proposed"
    TERMS_AGREED = "terms_agreed"

    # Match
    MATCH_CONFIRMATION_PENDING = "match_confirmation_pending"
    MATCH_CONFIRMED = "match_confirmed"
    MATCH_DECLINED = "match_declined"


@dataclass
class NegotiationNotification:
    """Negotiation notification"""
    notification_id: str
    notification_type: NotificationType
    negotiation_id: str
    recipient_id: str
    sender_id: Optional[str] = None
    title: str = ""
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    read: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "notification_type": self.notification_type.value,
            "negotiation_id": self.negotiation_id,
            "recipient_id": self.recipient_id,
            "sender_id": self.sender_id,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "read": self.read,
        }


class NegotiationNotificationManager:
    """
    Manages real-time notifications for pre-match negotiations.

    Features:
    - WebSocket-based real-time delivery
    - Notification persistence for offline users
    - Subscription management
    - Rate limiting
    """

    def __init__(
        self,
        ws_manager: Optional[Any] = None,
        persistence_enabled: bool = True,
    ):
        self.ws_manager = ws_manager
        self.persistence_enabled = persistence_enabled

        # Active WebSocket connections: agent_id -> set of connection_ids
        self._connections: Dict[str, Set[str]] = {}

        # Notification subscriptions: agent_id -> set of notification types
        self._subscriptions: Dict[str, Set[NotificationType]] = {}

        # Pending notifications for offline users
        self._pending_notifications: Dict[str, List[NegotiationNotification]] = {}

        # Notification callbacks
        self._callbacks: Dict[str, Callable] = {}

        # Rate limiting: agent_id -> list of notification timestamps
        self._rate_limits: Dict[str, List[datetime]] = {}
        self._rate_limit_window = 60  # seconds
        self._rate_limit_max = 30  # max notifications per window

        self._lock = asyncio.Lock()

    # ==================== Connection Management ====================

    async def register_connection(
        self,
        agent_id: str,
        connection_id: str,
    ) -> None:
        """Register a WebSocket connection for an agent"""
        async with self._lock:
            if agent_id not in self._connections:
                self._connections[agent_id] = set()
            self._connections[agent_id].add(connection_id)

            # Subscribe to all notification types by default
            if agent_id not in self._subscriptions:
                self._subscriptions[agent_id] = set(NotificationType)

            logger.info(f"Registered connection {connection_id} for agent {agent_id}")

            # Deliver pending notifications
            await self._deliver_pending_notifications(agent_id, connection_id)

    async def unregister_connection(
        self,
        agent_id: str,
        connection_id: str,
    ) -> None:
        """Unregister a WebSocket connection"""
        async with self._lock:
            if agent_id in self._connections:
                self._connections[agent_id].discard(connection_id)
                if not self._connections[agent_id]:
                    del self._connections[agent_id]

            logger.info(f"Unregistered connection {connection_id} for agent {agent_id}")

    def is_online(self, agent_id: str) -> bool:
        """Check if agent has active connections"""
        return agent_id in self._connections and len(self._connections[agent_id]) > 0

    # ==================== Subscription Management ====================

    async def subscribe(
        self,
        agent_id: str,
        notification_types: Optional[List[NotificationType]] = None,
    ) -> None:
        """Subscribe an agent to specific notification types"""
        async with self._lock:
            if notification_types:
                if agent_id not in self._subscriptions:
                    self._subscriptions[agent_id] = set()
                self._subscriptions[agent_id].update(notification_types)
            else:
                # Subscribe to all types
                self._subscriptions[agent_id] = set(NotificationType)

    async def unsubscribe(
        self,
        agent_id: str,
        notification_types: List[NotificationType],
    ) -> None:
        """Unsubscribe from specific notification types"""
        async with self._lock:
            if agent_id in self._subscriptions:
                self._subscriptions[agent_id].difference_update(notification_types)

    def is_subscribed(
        self,
        agent_id: str,
        notification_type: NotificationType,
    ) -> bool:
        """Check if agent is subscribed to a notification type"""
        if agent_id not in self._subscriptions:
            return True  # Default to subscribed
        return notification_type in self._subscriptions[agent_id]

    # ==================== Notification Sending ====================

    async def send_notification(
        self,
        notification_type: NotificationType,
        negotiation_id: str,
        recipient_id: str,
        sender_id: Optional[str] = None,
        title: str = "",
        message: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> NegotiationNotification:
        """
        Send a notification to an agent.

        If the agent is online, delivers immediately via WebSocket.
        If offline, stores for later delivery.
        """
        # Check subscription
        if not self.is_subscribed(recipient_id, notification_type):
            logger.debug(f"Agent {recipient_id} not subscribed to {notification_type}")
            return None

        # Rate limiting
        if not await self._check_rate_limit(recipient_id):
            logger.warning(f"Rate limit exceeded for agent {recipient_id}")
            return None

        notification = NegotiationNotification(
            notification_id=f"notif-{uuid4().hex[:12]}",
            notification_type=notification_type,
            negotiation_id=negotiation_id,
            recipient_id=recipient_id,
            sender_id=sender_id,
            title=title,
            message=message,
            data=data or {},
        )

        # Check if recipient is online
        if self.is_online(recipient_id):
            await self._deliver_notification(notification)
        else:
            # Store for later delivery
            await self._store_pending_notification(notification)

        # Trigger callback if registered
        await self._trigger_callback(notification)

        return notification

    async def broadcast_to_negotiation(
        self,
        negotiation_id: str,
        participant_ids: List[str],
        notification_type: NotificationType,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        sender_id: Optional[str] = None,
    ) -> List[NegotiationNotification]:
        """Broadcast notification to all negotiation participants"""
        notifications = []

        for recipient_id in participant_ids:
            notification = await self.send_notification(
                notification_type=notification_type,
                negotiation_id=negotiation_id,
                recipient_id=recipient_id,
                sender_id=sender_id,
                title=title,
                message=message,
                data=data,
            )
            if notification:
                notifications.append(notification)

        return notifications

    # ==================== Specific Notification Types ====================

    async def notify_negotiation_initiated(
        self,
        negotiation_id: str,
        demand_agent_id: str,
        supply_agent_id: str,
        demand_info: Dict[str, Any],
    ) -> List[NegotiationNotification]:
        """Notify both parties about new negotiation"""
        notifications = []

        # Notify supply agent
        notifications.append(await self.send_notification(
            notification_type=NotificationType.NEGOTIATION_INITIATED,
            negotiation_id=negotiation_id,
            recipient_id=supply_agent_id,
            sender_id=demand_agent_id,
            title="New Pre-Match Negotiation",
            message=f"You have received a new negotiation request",
            data={"demand_info": demand_info},
        ))

        # Notify demand agent (confirmation)
        notifications.append(await self.send_notification(
            notification_type=NotificationType.NEGOTIATION_INITIATED,
            negotiation_id=negotiation_id,
            recipient_id=demand_agent_id,
            title="Negotiation Initiated",
            message=f"Negotiation started with {supply_agent_id}",
            data={"supply_agent_id": supply_agent_id},
        ))

        return [n for n in notifications if n]

    async def notify_question_asked(
        self,
        negotiation_id: str,
        question: str,
        asker_id: str,
        recipient_id: str,
        question_id: str,
    ) -> NegotiationNotification:
        """Notify about new question"""
        return await self.send_notification(
            notification_type=NotificationType.QUESTION_ASKED,
            negotiation_id=negotiation_id,
            recipient_id=recipient_id,
            sender_id=asker_id,
            title="New Question",
            message=f"Question: {question[:100]}...",
            data={
                "question_id": question_id,
                "question": question,
            },
        )

    async def notify_question_answered(
        self,
        negotiation_id: str,
        answer: str,
        answerer_id: str,
        recipient_id: str,
        question_id: str,
        question: str,
    ) -> NegotiationNotification:
        """Notify about answered question"""
        return await self.send_notification(
            notification_type=NotificationType.QUESTION_ANSWERED,
            negotiation_id=negotiation_id,
            recipient_id=recipient_id,
            sender_id=answerer_id,
            title="Question Answered",
            message=f"Answer to: {question[:50]}...",
            data={
                "question_id": question_id,
                "question": question,
                "answer": answer,
            },
        )

    async def notify_verification_requested(
        self,
        negotiation_id: str,
        capability: str,
        requester_id: str,
        recipient_id: str,
        request_id: str,
        verification_type: str,
    ) -> NegotiationNotification:
        """Notify about verification request"""
        return await self.send_notification(
            notification_type=NotificationType.VERIFICATION_REQUESTED,
            negotiation_id=negotiation_id,
            recipient_id=recipient_id,
            sender_id=requester_id,
            title="Capability Verification Requested",
            message=f"Please verify your capability: {capability}",
            data={
                "request_id": request_id,
                "capability": capability,
                "verification_type": verification_type,
            },
        )

    async def notify_verification_responded(
        self,
        negotiation_id: str,
        capability: str,
        responder_id: str,
        recipient_id: str,
        request_id: str,
        status: str,
    ) -> NegotiationNotification:
        """Notify about verification response"""
        return await self.send_notification(
            notification_type=NotificationType.VERIFICATION_RESPONDED,
            negotiation_id=negotiation_id,
            recipient_id=recipient_id,
            sender_id=responder_id,
            title="Verification Response Received",
            message=f"Verification response for {capability}: {status}",
            data={
                "request_id": request_id,
                "capability": capability,
                "status": status,
            },
        )

    async def notify_terms_proposed(
        self,
        negotiation_id: str,
        proposer_id: str,
        recipient_id: str,
        terms: Dict[str, Any],
    ) -> NegotiationNotification:
        """Notify about terms proposal"""
        return await self.send_notification(
            notification_type=NotificationType.TERMS_PROPOSED,
            negotiation_id=negotiation_id,
            recipient_id=recipient_id,
            sender_id=proposer_id,
            title="Terms Proposed",
            message="New terms have been proposed for your review",
            data={"terms": terms},
        )

    async def notify_terms_agreed(
        self,
        negotiation_id: str,
        participant_ids: List[str],
        terms: Dict[str, Any],
    ) -> List[NegotiationNotification]:
        """Notify both parties about agreed terms"""
        return await self.broadcast_to_negotiation(
            negotiation_id=negotiation_id,
            participant_ids=participant_ids,
            notification_type=NotificationType.TERMS_AGREED,
            title="Terms Agreed",
            message="Both parties have agreed to the terms",
            data={"terms": terms},
        )

    async def notify_match_confirmation_pending(
        self,
        negotiation_id: str,
        confirmer_id: str,
        recipient_id: str,
    ) -> NegotiationNotification:
        """Notify that one party confirmed, waiting for other"""
        return await self.send_notification(
            notification_type=NotificationType.MATCH_CONFIRMATION_PENDING,
            negotiation_id=negotiation_id,
            recipient_id=recipient_id,
            sender_id=confirmer_id,
            title="Counterpart Confirmed",
            message="Your counterpart has confirmed. Please confirm to finalize the match.",
            data={"confirmer_id": confirmer_id},
        )

    async def notify_match_confirmed(
        self,
        negotiation_id: str,
        participant_ids: List[str],
    ) -> List[NegotiationNotification]:
        """Notify both parties that match is confirmed"""
        return await self.broadcast_to_negotiation(
            negotiation_id=negotiation_id,
            participant_ids=participant_ids,
            notification_type=NotificationType.MATCH_CONFIRMED,
            title="Match Confirmed!",
            message="Both parties have confirmed. The match is now active!",
            data={},
        )

    async def notify_match_declined(
        self,
        negotiation_id: str,
        decliner_id: str,
        recipient_id: str,
        reason: str,
    ) -> NegotiationNotification:
        """Notify about match decline"""
        return await self.send_notification(
            notification_type=NotificationType.MATCH_DECLINED,
            negotiation_id=negotiation_id,
            recipient_id=recipient_id,
            sender_id=decliner_id,
            title="Match Declined",
            message=f"The match has been declined. Reason: {reason}",
            data={
                "decliner_id": decliner_id,
                "reason": reason,
            },
        )

    async def notify_negotiation_expired(
        self,
        negotiation_id: str,
        participant_ids: List[str],
    ) -> List[NegotiationNotification]:
        """Notify both parties about expired negotiation"""
        return await self.broadcast_to_negotiation(
            negotiation_id=negotiation_id,
            participant_ids=participant_ids,
            notification_type=NotificationType.NEGOTIATION_EXPIRED,
            title="Negotiation Expired",
            message="The negotiation has expired without confirmation.",
            data={},
        )

    # ==================== Pending Notifications ====================

    async def get_pending_notifications(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get pending notifications for an agent"""
        async with self._lock:
            if agent_id not in self._pending_notifications:
                return []

            notifications = self._pending_notifications[agent_id][:limit]
            return [n.to_dict() for n in notifications]

    async def mark_notification_read(
        self,
        agent_id: str,
        notification_id: str,
    ) -> bool:
        """Mark a notification as read"""
        async with self._lock:
            if agent_id not in self._pending_notifications:
                return False

            for notification in self._pending_notifications[agent_id]:
                if notification.notification_id == notification_id:
                    notification.read = True
                    return True

            return False

    async def clear_pending_notifications(
        self,
        agent_id: str,
    ) -> int:
        """Clear all pending notifications for an agent"""
        async with self._lock:
            if agent_id not in self._pending_notifications:
                return 0

            count = len(self._pending_notifications[agent_id])
            del self._pending_notifications[agent_id]
            return count

    # ==================== Callbacks ====================

    async def register_callback(
        self,
        notification_type: NotificationType,
        callback: Callable[[NegotiationNotification], None],
    ) -> None:
        """Register a callback for a notification type"""
        self._callbacks[notification_type.value] = callback

    # ==================== Internal Methods ====================

    async def _deliver_notification(
        self,
        notification: NegotiationNotification,
    ) -> bool:
        """Deliver notification via WebSocket"""
        recipient_id = notification.recipient_id

        if recipient_id not in self._connections:
            return False

        message = {
            "type": "negotiation_notification",
            "data": notification.to_dict(),
        }

        delivered = False

        for connection_id in self._connections[recipient_id]:
            try:
                if self.ws_manager:
                    await self.ws_manager.send_to_connection(
                        connection_id,
                        json.dumps(message),
                    )
                    delivered = True
            except Exception as e:
                logger.error(f"Error delivering notification to {connection_id}: {e}")

        return delivered

    async def _deliver_pending_notifications(
        self,
        agent_id: str,
        connection_id: str,
    ) -> int:
        """Deliver pending notifications to newly connected agent"""
        if agent_id not in self._pending_notifications:
            return 0

        notifications = self._pending_notifications[agent_id]
        delivered = 0

        for notification in notifications:
            try:
                message = {
                    "type": "negotiation_notification",
                    "data": notification.to_dict(),
                }

                if self.ws_manager:
                    await self.ws_manager.send_to_connection(
                        connection_id,
                        json.dumps(message),
                    )
                    delivered += 1
            except Exception as e:
                logger.error(f"Error delivering pending notification: {e}")

        logger.info(f"Delivered {delivered} pending notifications to {agent_id}")
        return delivered

    async def _store_pending_notification(
        self,
        notification: NegotiationNotification,
    ) -> None:
        """Store notification for offline delivery"""
        async with self._lock:
            recipient_id = notification.recipient_id

            if recipient_id not in self._pending_notifications:
                self._pending_notifications[recipient_id] = []

            self._pending_notifications[recipient_id].append(notification)

            # Limit stored notifications
            if len(self._pending_notifications[recipient_id]) > 100:
                self._pending_notifications[recipient_id] = \
                    self._pending_notifications[recipient_id][-100:]

        logger.debug(f"Stored pending notification for {recipient_id}")

    async def _check_rate_limit(self, agent_id: str) -> bool:
        """Check if agent is within rate limits"""
        now = datetime.utcnow()

        async with self._lock:
            if agent_id not in self._rate_limits:
                self._rate_limits[agent_id] = []

            # Clean old timestamps
            cutoff = now - timedelta(seconds=self._rate_limit_window)
            self._rate_limits[agent_id] = [
                ts for ts in self._rate_limits[agent_id]
                if ts > cutoff
            ]

            # Check limit
            if len(self._rate_limits[agent_id]) >= self._rate_limit_max:
                return False

            # Add new timestamp
            self._rate_limits[agent_id].append(now)
            return True

    async def _trigger_callback(
        self,
        notification: NegotiationNotification,
    ) -> None:
        """Trigger registered callback for notification type"""
        callback = self._callbacks.get(notification.notification_type.value)

        if callback:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(notification)
                else:
                    callback(notification)
            except Exception as e:
                logger.error(f"Error in notification callback: {e}")
