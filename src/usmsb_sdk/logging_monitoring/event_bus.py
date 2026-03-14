"""
Event Bus Implementation

Async event bus for pub/sub messaging within the SDK.
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Priority levels for events."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class EventType(Enum):
    """Standard event types in the SDK."""
    # Agent events
    AGENT_CREATED = "agent.created"
    AGENT_UPDATED = "agent.updated"
    AGENT_DELETED = "agent.deleted"
    AGENT_STATE_CHANGED = "agent.state_changed"

    # Goal events
    GOAL_CREATED = "goal.created"
    GOAL_UPDATED = "goal.updated"
    GOAL_COMPLETED = "goal.completed"
    GOAL_FAILED = "goal.failed"

    # Action events
    ACTION_STARTED = "action.started"
    ACTION_COMPLETED = "action.completed"
    ACTION_FAILED = "action.failed"

    # Resource events
    RESOURCE_CREATED = "resource.created"
    RESOURCE_CONSUMED = "resource.consumed"
    RESOURCE_DEPLETED = "resource.depleted"

    # Interaction events
    INTERACTION_STARTED = "interaction.started"
    INTERACTION_COMPLETED = "interaction.completed"

    # System events
    SYSTEM_STARTED = "system.started"
    SYSTEM_STOPPED = "system.stopped"
    SYSTEM_ERROR = "system.error"

    # Simulation events
    SIMULATION_STARTED = "simulation.started"
    SIMULATION_STEP = "simulation.step"
    SIMULATION_COMPLETED = "simulation.completed"

    # Custom events
    CUSTOM = "custom"


@dataclass
class Event:
    """Represents an event in the system."""
    event_type: str
    source: str
    data: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid4())[:8])
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    priority: EventPriority = EventPriority.NORMAL
    target: str | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "target": self.target,
            "data": self.data,
            "timestamp": self.timestamp,
            "priority": self.priority.value,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        """Create event from dictionary."""
        return cls(
            event_id=data.get("event_id", str(uuid4())[:8]),
            event_type=data["event_type"],
            source=data["source"],
            target=data.get("target"),
            data=data.get("data", {}),
            timestamp=data.get("timestamp", datetime.now().timestamp()),
            priority=EventPriority(data.get("priority", 5)),
            correlation_id=data.get("correlation_id"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Subscription:
    """Represents a subscription to events."""
    subscription_id: str
    event_pattern: str  # Supports wildcards like "agent.*" or "agent.created"
    handler: Callable[[Event], Any]
    is_async: bool = False
    priority: int = 0
    active: bool = True


class EventBus:
    """
    Async Event Bus for pub/sub messaging.

    Features:
    - Pattern-based subscriptions (supports wildcards)
    - Priority-based handler execution
    - Async and sync handler support
    - Event correlation and tracing
    - Dead letter queue for failed events
    """

    def __init__(
        self,
        max_queue_size: int = 10000,
        dead_letter_enabled: bool = True,
    ):
        """
        Initialize the Event Bus.

        Args:
            max_queue_size: Maximum size of the event queue
            dead_letter_enabled: Whether to enable dead letter queue
        """
        self._subscriptions: dict[str, list[Subscription]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._dead_letter_queue: list[Event] = [] if dead_letter_enabled else None
        self._dead_letter_enabled = dead_letter_enabled
        self._running = False
        self._processor_task: asyncio.Task | None = None
        self._event_history: list[Event] = []
        self._history_size = 1000

    async def start(self) -> None:
        """Start the event bus processor."""
        if self._running:
            return

        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")

    async def stop(self) -> None:
        """Stop the event bus processor."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Event bus stopped")

    def subscribe(
        self,
        event_pattern: str,
        handler: Callable[[Event], Any],
        is_async: bool = False,
        priority: int = 0,
    ) -> str:
        """
        Subscribe to events matching a pattern.

        Args:
            event_pattern: Pattern to match (e.g., "agent.*", "agent.created", "*")
            handler: Function to call when event matches
            is_async: Whether the handler is async
            priority: Handler priority (higher = executed first)

        Returns:
            Subscription ID for unsubscribing
        """
        subscription_id = str(uuid4())[:8]
        subscription = Subscription(
            subscription_id=subscription_id,
            event_pattern=event_pattern,
            handler=handler,
            is_async=is_async,
            priority=priority,
        )

        if event_pattern not in self._subscriptions:
            self._subscriptions[event_pattern] = []
        self._subscriptions[event_pattern].append(subscription)

        # Sort by priority
        self._subscriptions[event_pattern].sort(key=lambda s: s.priority, reverse=True)

        logger.debug(f"Subscription {subscription_id} created for pattern: {event_pattern}")
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events.

        Args:
            subscription_id: ID of the subscription to remove

        Returns:
            True if subscription was found and removed
        """
        for _pattern, subs in self._subscriptions.items():
            for i, sub in enumerate(subs):
                if sub.subscription_id == subscription_id:
                    subs.pop(i)
                    logger.debug(f"Subscription {subscription_id} removed")
                    return True
        return False

    async def publish(
        self,
        event: Event,
        immediate: bool = False,
    ) -> None:
        """
        Publish an event.

        Args:
            event: The event to publish
            immediate: If True, process immediately instead of queuing
        """
        if immediate:
            await self._dispatch_event(event)
        else:
            try:
                await self._event_queue.put(event)
                logger.debug(f"Event {event.event_id} queued: {event.event_type}")
            except asyncio.QueueFull:
                logger.error(f"Event queue full, dropping event: {event.event_id}")
                if self._dead_letter_enabled:
                    self._dead_letter_queue.append(event)

    async def emit(
        self,
        event_type: str,
        source: str,
        data: dict[str, Any],
        target: str | None = None,
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: str | None = None,
    ) -> str:
        """
        Convenience method to create and publish an event.

        Args:
            event_type: Type of event
            source: Source identifier
            data: Event data
            target: Optional target identifier
            priority: Event priority
            correlation_id: Optional correlation ID for tracing

        Returns:
            Event ID
        """
        event = Event(
            event_type=event_type,
            source=source,
            data=data,
            target=target,
            priority=priority,
            correlation_id=correlation_id,
        )
        await self.publish(event)
        return event.event_id

    async def _process_events(self) -> None:
        """Process events from the queue."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                await self._dispatch_event(event)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    async def _dispatch_event(self, event: Event) -> None:
        """Dispatch an event to matching handlers."""
        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._history_size:
            self._event_history.pop(0)

        matching_handlers = []

        # Find matching subscriptions
        for pattern, subs in self._subscriptions.items():
            if self._matches_pattern(event.event_type, pattern):
                for sub in subs:
                    if sub.active:
                        matching_handlers.append(sub)

        # Sort by priority
        matching_handlers.sort(key=lambda s: s.priority, reverse=True)

        # Execute handlers
        for sub in matching_handlers:
            try:
                if sub.is_async:
                    await sub.handler(event)
                else:
                    sub.handler(event)
            except Exception as e:
                logger.error(
                    f"Handler {sub.subscription_id} failed for event {event.event_id}: {e}"
                )
                if self._dead_letter_enabled:
                    self._dead_letter_queue.append(event)

    def _matches_pattern(self, event_type: str, pattern: str) -> bool:
        """Check if an event type matches a pattern."""
        if pattern == "*":
            return True

        if "." not in pattern:
            return event_type == pattern

        # Handle wildcards like "agent.*"
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return event_type.startswith(prefix + ".")

        # Handle patterns like "agent.c*"
        if "*" in pattern:
            import fnmatch
            return fnmatch.fnmatch(event_type, pattern)

        return event_type == pattern

    def get_event_history(
        self,
        event_type: str | None = None,
        source: str | None = None,
        limit: int = 100,
    ) -> list[Event]:
        """
        Get event history.

        Args:
            event_type: Filter by event type
            source: Filter by source
            limit: Maximum number of events to return

        Returns:
            List of events
        """
        events = self._event_history

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if source:
            events = [e for e in events if e.source == source]

        return events[-limit:]

    def get_dead_letter_events(self) -> list[Event]:
        """Get events in the dead letter queue."""
        return self._dead_letter_queue.copy() if self._dead_letter_queue else []

    def clear_dead_letter_queue(self) -> int:
        """Clear the dead letter queue and return count of removed events."""
        if self._dead_letter_queue:
            count = len(self._dead_letter_queue)
            self._dead_letter_queue.clear()
            return count
        return 0

    def get_stats(self) -> dict[str, Any]:
        """Get event bus statistics."""
        return {
            "running": self._running,
            "queue_size": self._event_queue.qsize(),
            "subscription_count": sum(len(subs) for subs in self._subscriptions.values()),
            "history_size": len(self._event_history),
            "dead_letter_size": len(self._dead_letter_queue) if self._dead_letter_queue else 0,
        }


# Global event bus instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


async def init_event_bus() -> EventBus:
    """Initialize and start the global event bus."""
    bus = get_event_bus()
    await bus.start()
    return bus
