"""
Environment Broadcast Service

This module implements environment-wide broadcast capabilities:
- Supply/Demand availability announcements
- Agent status broadcasts
- Market signal distribution
- Event notification system
- Topic-based pub/sub

The service enables AI Agents to broadcast their state and receive
notifications about relevant changes in the environment.
"""

import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, AsyncIterator

logger = logging.getLogger(__name__)


class BroadcastType(str, Enum):
    """Types of broadcast messages."""
    SUPPLY_AVAILABLE = "supply_available"
    DEMAND_SEEKING = "demand_seeking"
    AGENT_ONLINE = "agent_online"
    AGENT_OFFLINE = "agent_offline"
    MARKET_SIGNAL = "market_signal"
    NEGOTIATION_REQUEST = "negotiation_request"
    TRANSACTION_COMPLETE = "transaction_complete"
    ENVIRONMENT_UPDATE = "environment_update"
    SKILL_REGISTERED = "skill_registered"
    PRICE_UPDATE = "price_update"
    ALERT = "alert"
    HEARTBEAT = "heartbeat"


class BroadcastPriority(str, Enum):
    """Priority levels for broadcasts."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class BroadcastScope(str, Enum):
    """Scope of broadcast delivery."""
    GLOBAL = "global"         # All agents in environment
    REGION = "region"         # Agents in a region
    TOPIC = "topic"           # Agents subscribed to topic
    DIRECT = "direct"         # Specific target agents
    CAPABILITY = "capability"  # Agents with specific capability


@dataclass
class BroadcastMessage:
    """A broadcast message."""
    message_id: str
    broadcast_type: BroadcastType
    sender_id: str
    sender_name: str
    content: Dict[str, Any]
    scope: BroadcastScope = BroadcastScope.GLOBAL
    priority: BroadcastPriority = BroadcastPriority.NORMAL
    topics: List[str] = field(default_factory=list)
    target_agents: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)
    ttl: float = 300.0  # Time to live in seconds
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.created_at + self.ttl

    def is_expired(self) -> bool:
        """Check if message has expired."""
        return time.time() > self.expires_at if self.expires_at else False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "broadcast_type": self.broadcast_type.value,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "content": self.content,
            "scope": self.scope.value,
            "priority": self.priority.value,
            "topics": self.topics,
            "target_agents": self.target_agents,
            "required_capabilities": self.required_capabilities,
            "ttl": self.ttl,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BroadcastMessage":
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            broadcast_type=BroadcastType(data.get("broadcast_type", "environment_update")),
            sender_id=data.get("sender_id", ""),
            sender_name=data.get("sender_name", "Unknown"),
            content=data.get("content", {}),
            scope=BroadcastScope(data.get("scope", "global")),
            priority=BroadcastPriority(data.get("priority", "normal")),
            topics=data.get("topics", []),
            target_agents=data.get("target_agents", []),
            required_capabilities=data.get("required_capabilities", []),
            ttl=data.get("ttl", 300.0),
            created_at=data.get("created_at", time.time()),
            expires_at=data.get("expires_at"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Subscription:
    """A subscription to broadcast topics."""
    subscription_id: str
    agent_id: str
    topics: List[str]
    broadcast_types: List[BroadcastType] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    active: bool = True
    callback: Optional[Callable] = None
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)

    def matches(self, message: BroadcastMessage) -> bool:
        """Check if this subscription matches a message."""
        if not self.active:
            return False

        # Check broadcast type
        if self.broadcast_types and message.broadcast_type not in self.broadcast_types:
            return False

        # Check topics
        if self.topics:
            topic_match = any(t in message.topics for t in self.topics)
            if not topic_match:
                return False

        # Check capabilities
        if self.capabilities and message.required_capabilities:
            cap_match = any(c in message.required_capabilities for c in self.capabilities)
            if not cap_match:
                return False

        return True


@dataclass
class BroadcastStats:
    """Statistics for the broadcast service."""
    total_messages: int = 0
    messages_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    active_subscriptions: int = 0
    total_deliveries: int = 0
    failed_deliveries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_messages": self.total_messages,
            "messages_by_type": dict(self.messages_by_type),
            "active_subscriptions": self.active_subscriptions,
            "total_deliveries": self.total_deliveries,
            "failed_deliveries": self.failed_deliveries,
        }


class EnvironmentBroadcastService:
    """
    Environment Broadcast Service.

    This service provides environment-wide broadcast capabilities for:
    - Supply/Demand availability announcements
    - Agent status updates
    - Market signals and alerts
    - Topic-based pub/sub messaging

    Features:
    - Multiple broadcast scopes (global, topic, capability-based)
    - TTL-based message expiration
    - Priority-based delivery
    - Subscription management
    - Message history and replay
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize the Environment Broadcast Service.

        Args:
            max_history: Maximum number of messages to keep in history
        """
        self.max_history = max_history

        # Subscriptions
        self._subscriptions: Dict[str, Subscription] = {}

        # Message history
        self._message_history: List[BroadcastMessage] = []

        # Agent registry for capability-based routing
        self._agent_capabilities: Dict[str, List[str]] = {}

        # Agent queues for direct delivery
        self._agent_queues: Dict[str, asyncio.Queue] = {}

        # Statistics
        self._stats = BroadcastStats()

        # Topic index for fast lookup
        self._topic_subscribers: Dict[str, Set[str]] = defaultdict(set)

        # Running state
        self._running = False
        self._delivery_task: Optional[asyncio.Task] = None

        # Callbacks
        self.on_message_broadcast: Optional[Callable[[BroadcastMessage, int], None]] = None
        self.on_subscription_added: Optional[Callable[[Subscription], None]] = None

    async def start(self) -> None:
        """Start the broadcast service."""
        self._running = True
        self._delivery_task = asyncio.create_task(self._delivery_loop())
        logger.info("Environment Broadcast Service started")

    async def stop(self) -> None:
        """Stop the broadcast service."""
        self._running = False
        if self._delivery_task:
            self._delivery_task.cancel()
            try:
                await self._delivery_task
            except asyncio.CancelledError:
                pass
        logger.info("Environment Broadcast Service stopped")

    async def _delivery_loop(self) -> None:
        """Background task for message delivery."""
        while self._running:
            try:
                await asyncio.sleep(0.1)
                # Process any pending deliveries
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in delivery loop: {e}")

    # ========== Broadcasting ==========

    async def broadcast(
        self,
        broadcast_type: BroadcastType,
        sender_id: str,
        sender_name: str,
        content: Dict[str, Any],
        scope: BroadcastScope = BroadcastScope.GLOBAL,
        priority: BroadcastPriority = BroadcastPriority.NORMAL,
        topics: Optional[List[str]] = None,
        target_agents: Optional[List[str]] = None,
        required_capabilities: Optional[List[str]] = None,
        ttl: float = 300.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BroadcastMessage:
        """
        Broadcast a message to the environment.

        Args:
            broadcast_type: Type of broadcast
            sender_id: ID of sending agent
            sender_name: Name of sending agent
            content: Message content
            scope: Delivery scope
            priority: Message priority
            topics: Topics for topic-based delivery
            target_agents: Specific target agents for direct delivery
            required_capabilities: Required capabilities for capability-based delivery
            ttl: Time to live in seconds
            metadata: Additional metadata

        Returns:
            The broadcast message
        """
        message = BroadcastMessage(
            message_id=str(uuid.uuid4()),
            broadcast_type=broadcast_type,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            scope=scope,
            priority=priority,
            topics=topics or [],
            target_agents=target_agents or [],
            required_capabilities=required_capabilities or [],
            ttl=ttl,
            metadata=metadata or {},
        )

        # Add to history
        self._message_history.append(message)
        if len(self._message_history) > self.max_history:
            self._message_history.pop(0)

        # Update stats
        self._stats.total_messages += 1
        self._stats.messages_by_type[broadcast_type.value] += 1

        # Deliver message
        delivery_count = await self._deliver_message(message)

        if self.on_message_broadcast:
            self.on_message_broadcast(message, delivery_count)

        logger.debug(f"Broadcast {message.message_id} delivered to {delivery_count} agents")
        return message

    async def _deliver_message(self, message: BroadcastMessage) -> int:
        """Deliver a message to matching subscribers."""
        delivery_count = 0

        for subscription in self._subscriptions.values():
            if not subscription.active:
                continue

            # Check if subscription matches
            if not self._should_deliver(message, subscription):
                continue

            # Deliver based on method
            if subscription.callback:
                try:
                    if asyncio.iscoroutinefunction(subscription.callback):
                        await subscription.callback(message)
                    else:
                        subscription.callback(message)
                    delivery_count += 1
                    self._stats.total_deliveries += 1
                except Exception as e:
                    logger.error(f"Callback delivery failed: {e}")
                    self._stats.failed_deliveries += 1

            elif subscription.queue:
                try:
                    await subscription.queue.put(message)
                    delivery_count += 1
                    self._stats.total_deliveries += 1
                except Exception as e:
                    logger.error(f"Queue delivery failed: {e}")
                    self._stats.failed_deliveries += 1

        # Also deliver to agent queues for direct delivery
        if message.scope == BroadcastScope.DIRECT and message.target_agents:
            for agent_id in message.target_agents:
                if agent_id in self._agent_queues:
                    try:
                        await self._agent_queues[agent_id].put(message)
                        delivery_count += 1
                    except Exception as e:
                        logger.error(f"Direct delivery failed: {e}")
                        self._stats.failed_deliveries += 1

        return delivery_count

    def _should_deliver(self, message: BroadcastMessage, subscription: Subscription) -> bool:
        """Check if a message should be delivered to a subscription."""
        # Don't deliver to sender
        if subscription.agent_id == message.sender_id:
            return False

        # Check scope
        if message.scope == BroadcastScope.DIRECT:
            return subscription.agent_id in message.target_agents

        if message.scope == BroadcastScope.CAPABILITY:
            agent_caps = self._agent_capabilities.get(subscription.agent_id, [])
            return any(c in message.required_capabilities for c in agent_caps)

        if message.scope == BroadcastScope.TOPIC:
            return any(t in message.topics for t in subscription.topics)

        # Global scope - deliver to all matching subscriptions
        return subscription.matches(message)

    # ========== Supply/Demand Broadcasts ==========

    async def broadcast_supply_available(
        self,
        agent_id: str,
        agent_name: str,
        resource: Dict[str, Any],
        price_range: Optional[Dict[str, float]] = None,
        availability: str = "now",
        topics: Optional[List[str]] = None,
    ) -> BroadcastMessage:
        """
        Broadcast supply availability.

        Args:
            agent_id: Supplier agent ID
            agent_name: Supplier agent name
            resource: Resource being offered
            price_range: Price range
            availability: Availability status
            topics: Related topics

        Returns:
            The broadcast message
        """
        content = {
            "resource": resource,
            "price_range": price_range or {"min": 0, "max": 1000},
            "availability": availability,
            "timestamp": time.time(),
        }

        return await self.broadcast(
            broadcast_type=BroadcastType.SUPPLY_AVAILABLE,
            sender_id=agent_id,
            sender_name=agent_name,
            content=content,
            scope=BroadcastScope.GLOBAL,
            topics=topics or ["supply", resource.get("type", "general")],
        )

    async def broadcast_demand_seeking(
        self,
        agent_id: str,
        agent_name: str,
        requirement: Dict[str, Any],
        budget: Optional[Dict[str, float]] = None,
        deadline: Optional[str] = None,
        topics: Optional[List[str]] = None,
    ) -> BroadcastMessage:
        """
        Broadcast demand seeking.

        Args:
            agent_id: Demander agent ID
            agent_name: Demander agent name
            requirement: Requirement specification
            budget: Budget range
            deadline: Deadline
            topics: Related topics

        Returns:
            The broadcast message
        """
        content = {
            "requirement": requirement,
            "budget": budget or {"min": 0, "max": 10000},
            "deadline": deadline,
            "timestamp": time.time(),
        }

        return await self.broadcast(
            broadcast_type=BroadcastType.DEMAND_SEEKING,
            sender_id=agent_id,
            sender_name=agent_name,
            content=content,
            scope=BroadcastScope.GLOBAL,
            topics=topics or ["demand", requirement.get("type", "general")],
        )

    async def broadcast_negotiation_request(
        self,
        from_agent_id: str,
        from_agent_name: str,
        to_agent_id: str,
        context: Dict[str, Any],
    ) -> BroadcastMessage:
        """
        Broadcast a negotiation request.

        Args:
            from_agent_id: Initiator agent ID
            from_agent_name: Initiator agent name
            to_agent_id: Target agent ID
            context: Negotiation context

        Returns:
            The broadcast message
        """
        return await self.broadcast(
            broadcast_type=BroadcastType.NEGOTIATION_REQUEST,
            sender_id=from_agent_id,
            sender_name=from_agent_name,
            content=context,
            scope=BroadcastScope.DIRECT,
            target_agents=[to_agent_id],
            priority=BroadcastPriority.HIGH,
        )

    # ========== Agent Status Broadcasts ==========

    async def broadcast_agent_online(
        self,
        agent_id: str,
        agent_name: str,
        capabilities: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BroadcastMessage:
        """Broadcast that an agent is online."""
        # Update capabilities
        self._agent_capabilities[agent_id] = capabilities

        content = {
            "capabilities": capabilities,
            "status": "online",
            "timestamp": time.time(),
            **(metadata or {}),
        }

        return await self.broadcast(
            broadcast_type=BroadcastType.AGENT_ONLINE,
            sender_id=agent_id,
            sender_name=agent_name,
            content=content,
            scope=BroadcastScope.GLOBAL,
        )

    async def broadcast_agent_offline(
        self,
        agent_id: str,
        agent_name: str,
    ) -> BroadcastMessage:
        """Broadcast that an agent is offline."""
        # Remove capabilities
        if agent_id in self._agent_capabilities:
            del self._agent_capabilities[agent_id]

        return await self.broadcast(
            broadcast_type=BroadcastType.AGENT_OFFLINE,
            sender_id=agent_id,
            sender_name=agent_name,
            content={"status": "offline", "timestamp": time.time()},
            scope=BroadcastScope.GLOBAL,
        )

    async def broadcast_heartbeat(
        self,
        agent_id: str,
        agent_name: str,
        status: Dict[str, Any],
    ) -> BroadcastMessage:
        """Broadcast a heartbeat signal."""
        return await self.broadcast(
            broadcast_type=BroadcastType.HEARTBEAT,
            sender_id=agent_id,
            sender_name=agent_name,
            content=status,
            scope=BroadcastScope.GLOBAL,
            ttl=60.0,  # Short TTL for heartbeats
        )

    # ========== Market Signals ==========

    async def broadcast_market_signal(
        self,
        signal_type: str,
        data: Dict[str, Any],
        priority: BroadcastPriority = BroadcastPriority.NORMAL,
    ) -> BroadcastMessage:
        """
        Broadcast a market signal.

        Args:
            signal_type: Type of signal
            data: Signal data
            priority: Signal priority

        Returns:
            The broadcast message
        """
        return await self.broadcast(
            broadcast_type=BroadcastType.MARKET_SIGNAL,
            sender_id="environment",
            sender_name="Environment",
            content={"signal_type": signal_type, "data": data},
            scope=BroadcastScope.GLOBAL,
            priority=priority,
            topics=["market", signal_type],
        )

    async def broadcast_price_update(
        self,
        resource_type: str,
        price: float,
        change: float,
        currency: str = "USD",
    ) -> BroadcastMessage:
        """Broadcast a price update."""
        content = {
            "resource_type": resource_type,
            "price": price,
            "change": change,
            "currency": currency,
            "timestamp": time.time(),
        }

        return await self.broadcast(
            broadcast_type=BroadcastType.PRICE_UPDATE,
            sender_id="environment",
            sender_name="Environment",
            content=content,
            scope=BroadcastScope.GLOBAL,
            topics=["price", resource_type],
        )

    async def broadcast_alert(
        self,
        alert_level: str,
        message: str,
        affected_agents: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BroadcastMessage:
        """Broadcast an alert."""
        priority = BroadcastPriority.HIGH if alert_level in ["critical", "high"] else BroadcastPriority.NORMAL

        return await self.broadcast(
            broadcast_type=BroadcastType.ALERT,
            sender_id="environment",
            sender_name="Environment",
            content={
                "alert_level": alert_level,
                "message": message,
                **(metadata or {}),
            },
            scope=BroadcastScope.DIRECT if affected_agents else BroadcastScope.GLOBAL,
            target_agents=affected_agents or [],
            priority=priority,
            ttl=3600.0,  # Longer TTL for alerts
        )

    # ========== Subscriptions ==========

    async def subscribe(
        self,
        agent_id: str,
        topics: Optional[List[str]] = None,
        broadcast_types: Optional[List[BroadcastType]] = None,
        capabilities: Optional[List[str]] = None,
        callback: Optional[Callable] = None,
    ) -> Subscription:
        """
        Subscribe to broadcasts.

        Args:
            agent_id: Subscriber agent ID
            topics: Topics to subscribe to
            broadcast_types: Types of broadcasts to receive
            capabilities: Filter by capabilities
            callback: Optional callback function

        Returns:
            The subscription
        """
        subscription = Subscription(
            subscription_id=str(uuid.uuid4()),
            agent_id=agent_id,
            topics=topics or [],
            broadcast_types=broadcast_types or [],
            capabilities=capabilities or [],
            callback=callback,
        )

        self._subscriptions[subscription.subscription_id] = subscription

        # Update topic index
        for topic in (topics or []):
            self._topic_subscribers[topic].add(subscription.subscription_id)

        # Create agent queue if not exists
        if agent_id not in self._agent_queues:
            self._agent_queues[agent_id] = asyncio.Queue()

        self._stats.active_subscriptions = len([
            s for s in self._subscriptions.values() if s.active
        ])

        if self.on_subscription_added:
            self.on_subscription_added(subscription)

        logger.info(f"Agent {agent_id} subscribed with {subscription.subscription_id}")
        return subscription

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from broadcasts."""
        if subscription_id not in self._subscriptions:
            return False

        subscription = self._subscriptions[subscription_id]
        subscription.active = False

        # Remove from topic index
        for topic in subscription.topics:
            self._topic_subscribers[topic].discard(subscription_id)

        del self._subscriptions[subscription_id]

        self._stats.active_subscriptions = len([
            s for s in self._subscriptions.values() if s.active
        ])

        logger.info(f"Subscription {subscription_id} unsubscribed")
        return True

    async def get_messages_for_agent(
        self,
        agent_id: str,
        timeout: float = 1.0,
    ) -> List[BroadcastMessage]:
        """Get pending messages for an agent."""
        messages = []

        if agent_id in self._agent_queues:
            queue = self._agent_queues[agent_id]

            try:
                while True:
                    message = queue.get_nowait()
                    messages.append(message)
            except asyncio.QueueEmpty:
                pass

        return messages

    # ========== History and Replay ==========

    def get_message_history(
        self,
        broadcast_type: Optional[BroadcastType] = None,
        sender_id: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 100,
    ) -> List[BroadcastMessage]:
        """
        Get message history.

        Args:
            broadcast_type: Filter by type
            sender_id: Filter by sender
            topic: Filter by topic
            limit: Maximum messages to return

        Returns:
            List of messages
        """
        history = [
            m for m in self._message_history
            if not m.is_expired()
        ]

        if broadcast_type:
            history = [m for m in history if m.broadcast_type == broadcast_type]

        if sender_id:
            history = [m for m in history if m.sender_id == sender_id]

        if topic:
            history = [m for m in history if topic in m.topics]

        return history[-limit:]

    async def replay_to_agent(
        self,
        agent_id: str,
        since: float,
        broadcast_types: Optional[List[BroadcastType]] = None,
    ) -> int:
        """
        Replay messages to an agent since a timestamp.

        Args:
            agent_id: Target agent ID
            since: Unix timestamp
            broadcast_types: Types to replay

        Returns:
            Number of messages replayed
        """
        messages = [
            m for m in self._message_history
            if m.created_at >= since and not m.is_expired()
        ]

        if broadcast_types:
            messages = [m for m in messages if m.broadcast_type in broadcast_types]

        if agent_id not in self._agent_queues:
            return 0

        queue = self._agent_queues[agent_id]
        count = 0

        for message in messages:
            try:
                await queue.put(message)
                count += 1
            except Exception as e:
                logger.error(f"Replay failed: {e}")

        return count

    # ========== Utility Methods ==========

    def register_agent_capabilities(
        self,
        agent_id: str,
        capabilities: List[str],
    ) -> None:
        """Register capabilities for an agent."""
        self._agent_capabilities[agent_id] = capabilities

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent completely."""
        # Remove capabilities
        if agent_id in self._agent_capabilities:
            del self._agent_capabilities[agent_id]

        # Remove queue
        if agent_id in self._agent_queues:
            del self._agent_queues[agent_id]

        # Remove subscriptions
        to_remove = [
            sid for sid, sub in self._subscriptions.items()
            if sub.agent_id == agent_id
        ]

        for sid in to_remove:
            del self._subscriptions[sid]

    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            **self._stats.to_dict(),
            "total_topics": len(self._topic_subscribers),
            "registered_agents": len(self._agent_capabilities),
            "history_size": len(self._message_history),
        }

    def get_active_topics(self) -> List[str]:
        """Get list of active topics."""
        return list(self._topic_subscribers.keys())
