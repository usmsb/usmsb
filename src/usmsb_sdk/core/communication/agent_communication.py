"""
Inter-Agent Communication System

This module provides comprehensive communication capabilities between agents:
- P2P messaging with direct and broadcast modes
- Pub/Sub pattern for event-driven communication
- Request-Reply pattern for synchronous communication
- Message routing and delivery guarantees
- Communication channels and topics
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class MessageType(StrEnum):
    """Types of messages agents can exchange."""
    REQUEST = "request"           # Request for action/information
    RESPONSE = "response"         # Response to a request
    NOTIFICATION = "notification"  # One-way notification
    BROADCAST = "broadcast"       # Broadcast to all interested agents
    QUERY = "query"              # Query for information
    COMMAND = "command"          # Command to execute
    EVENT = "event"              # Event notification
    TRANSACTION = "transaction"  # Transaction-related message


class MessagePriority(StrEnum):
    """Priority levels for messages."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class DeliveryStatus(StrEnum):
    """Delivery status of messages."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class AgentAddress:
    """Address identifying an agent in the network."""
    agent_id: str
    node_id: str  # Node where the agent is running
    capabilities: list[str] = field(default_factory=list)
    public_key: str | None = None  # For encrypted communication

    def __str__(self) -> str:
        return f"{self.agent_id}@{self.node_id}"


@dataclass
class Message:
    """
    Message exchanged between agents.

    Supports various communication patterns and includes
    metadata for routing, tracking, and security.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.NOTIFICATION
    priority: MessagePriority = MessagePriority.NORMAL
    sender: AgentAddress = None
    recipient: AgentAddress | None = None  # None for broadcast
    topic: str | None = None  # For pub/sub
    subject: str = ""
    content: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None  # TTL for message
    correlation_id: str | None = None  # For request/response matching
    reply_to: str | None = None  # Queue/topic for replies
    requires_ack: bool = False
    signature: str | None = None  # Message signature for verification

    def to_dict(self) -> dict[str, Any]:
        """Serialize message to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "priority": self.priority.value,
            "sender": str(self.sender) if self.sender else None,
            "recipient": str(self.recipient) if self.recipient else None,
            "topic": self.topic,
            "subject": self.subject,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "requires_ack": self.requires_ack,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        """Deserialize message from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=MessageType(data.get("type", "notification")),
            priority=MessagePriority(data.get("priority", "normal")),
            subject=data.get("subject", ""),
            content=data.get("content"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", time.time()),
            expires_at=data.get("expires_at"),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
            requires_ack=data.get("requires_ack", False),
            topic=data.get("topic"),
        )

    def is_expired(self) -> bool:
        """Check if message has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def create_response(self, content: Any) -> "Message":
        """Create a response message to this message."""
        return Message(
            type=MessageType.RESPONSE,
            sender=self.recipient,
            recipient=self.sender,
            subject=f"Re: {self.subject}",
            content=content,
            correlation_id=self.id,
            reply_to=self.reply_to,
        )


@dataclass
class MessageReceipt:
    """Receipt confirming message delivery."""
    message_id: str
    status: DeliveryStatus
    recipient: AgentAddress
    timestamp: float = field(default_factory=time.time)
    error: str | None = None


class CommunicationChannel(ABC):
    """Abstract base class for communication channels."""

    @abstractmethod
    async def send(self, message: Message) -> MessageReceipt:
        """Send a message."""
        pass

    @abstractmethod
    async def receive(self, timeout: float | None = None) -> Message | None:
        """Receive a message."""
        pass

    @abstractmethod
    async def subscribe(self, topic: str, handler: Callable[[Message], None]) -> str:
        """Subscribe to a topic."""
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a topic."""
        pass


class InMemoryCommunicationChannel(CommunicationChannel):
    """
    In-memory communication channel for local testing and development.

    Messages are delivered immediately within the same process.
    """

    def __init__(self):
        self._inbox: asyncio.Queue = asyncio.Queue()
        self._subscriptions: dict[str, list[Callable]] = defaultdict(list)
        self._subscription_counter = 0
        self._message_store: dict[str, Message] = {}

    async def send(self, message: Message) -> MessageReceipt:
        """Send a message to the inbox."""
        if message.is_expired():
            return MessageReceipt(
                message_id=message.id,
                status=DeliveryStatus.FAILED,
                recipient=message.recipient,
                error="Message expired",
            )

        self._message_store[message.id] = message
        await self._inbox.put(message)

        # Handle topic subscriptions
        if message.topic:
            for handler in self._subscriptions.get(message.topic, []):
                await handler(message)

        return MessageReceipt(
            message_id=message.id,
            status=DeliveryStatus.DELIVERED,
            recipient=message.recipient,
        )

    async def receive(self, timeout: float | None = None) -> Message | None:
        """Receive a message from the inbox."""
        try:
            if timeout:
                message = await asyncio.wait_for(self._inbox.get(), timeout=timeout)
            else:
                message = await self._inbox.get()
            return message
        except TimeoutError:
            return None

    async def subscribe(self, topic: str, handler: Callable[[Message], None]) -> str:
        """Subscribe to a topic."""
        self._subscription_counter += 1
        subscription_id = f"sub_{self._subscription_counter}"
        self._subscriptions[topic].append(handler)
        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a topic."""
        # Find and remove subscription
        for _topic, handlers in self._subscriptions.items():
            for i, handler in enumerate(handlers):
                if id(handler) == int(subscription_id.split("_")[1]):
                    handlers.pop(i)
                    return True
        return False


class P2PCommunicationChannel(CommunicationChannel):
    """
    P2P communication channel for distributed agent communication.

    Uses a peer-to-peer network for message routing between nodes.
    """

    def __init__(self, node_id: str, bootstrap_peers: list[str] | None = None):
        self.node_id = node_id
        self.bootstrap_peers = bootstrap_peers or []
        self._peers: dict[str, str] = {}  # peer_id -> address
        self._agent_locations: dict[str, str] = {}  # agent_id -> node_id
        self._inbox: asyncio.Queue = asyncio.Queue()
        self._subscriptions: dict[str, list[Callable]] = defaultdict(list)
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._message_handlers: dict[MessageType, Callable] = {}

    async def connect_to_network(self) -> bool:
        """Connect to the P2P network."""
        # In a real implementation, this would establish P2P connections
        logger.info(f"Node {self.node_id} connecting to P2P network")
        return True

    async def register_agent(self, agent_id: str) -> None:
        """Register an agent with this node."""
        self._agent_locations[agent_id] = self.node_id
        logger.info(f"Agent {agent_id} registered on node {self.node_id}")

    async def discover_agent(self, agent_id: str) -> str | None:
        """Discover which node an agent is on."""
        return self._agent_locations.get(agent_id)

    async def send(self, message: Message) -> MessageReceipt:
        """Send a message to another agent."""
        if message.is_expired():
            return MessageReceipt(
                message_id=message.id,
                status=DeliveryStatus.FAILED,
                recipient=message.recipient,
                error="Message expired",
            )

        # Route message to recipient
        if message.recipient:
            recipient_node = await self.discover_agent(message.recipient.agent_id)

            if recipient_node == self.node_id:
                # Local delivery
                await self._inbox.put(message)
            elif recipient_node:
                # Remote delivery - would use P2P routing
                logger.info(f"Routing message {message.id} to node {recipient_node}")
                await self._inbox.put(message)  # Simplified for demo
            else:
                return MessageReceipt(
                    message_id=message.id,
                    status=DeliveryStatus.FAILED,
                    recipient=message.recipient,
                    error="Agent not found",
                )

        # Broadcast message
        elif message.type == MessageType.BROADCAST:
            logger.info(f"Broadcasting message {message.id}")
            await self._inbox.put(message)

        # Topic-based message
        elif message.topic:
            for handler in self._subscriptions.get(message.topic, []):
                await handler(message)

        return MessageReceipt(
            message_id=message.id,
            status=DeliveryStatus.DELIVERED,
            recipient=message.recipient,
        )

    async def receive(self, timeout: float | None = None) -> Message | None:
        """Receive a message."""
        try:
            if timeout:
                return await asyncio.wait_for(self._inbox.get(), timeout=timeout)
            else:
                return await self._inbox.get()
        except TimeoutError:
            return None

    async def subscribe(self, topic: str, handler: Callable[[Message], None]) -> str:
        """Subscribe to a topic."""
        subscription_id = f"{topic}_{len(self._subscriptions[topic])}"
        self._subscriptions[topic].append(handler)
        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a topic."""
        topic = subscription_id.rsplit("_", 1)[0]
        if topic in self._subscriptions:
            idx = int(subscription_id.rsplit("_", 1)[1])
            if 0 <= idx < len(self._subscriptions[topic]):
                self._subscriptions[topic].pop(idx)
                return True
        return False

    async def request(
        self,
        recipient: AgentAddress,
        subject: str,
        content: Any,
        timeout: float = 30.0,
    ) -> Message | None:
        """
        Send a request and wait for response.

        Implements request-reply pattern with timeout.
        """
        request = Message(
            type=MessageType.REQUEST,
            recipient=recipient,
            subject=subject,
            content=content,
            requires_ack=True,
        )

        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request.id] = future

        # Send request
        receipt = await self.send(request)
        if receipt.status != DeliveryStatus.DELIVERED:
            del self._pending_requests[request.id]
            return None

        # Wait for response
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except TimeoutError:
            del self._pending_requests[request.id]
            logger.warning(f"Request {request.id} timed out")
            return None

    async def handle_response(self, message: Message) -> None:
        """Handle incoming response messages."""
        if message.correlation_id in self._pending_requests:
            future = self._pending_requests.pop(message.correlation_id)
            future.set_result(message)


class AgentCommunicationManager:
    """
    Manager for agent communication capabilities.

    Provides a high-level API for agents to communicate.
    """

    def __init__(self, agent_id: str, channel: CommunicationChannel):
        self.agent_id = agent_id
        self.channel = channel
        self.address = AgentAddress(agent_id=agent_id, node_id="local")
        self._message_handlers: dict[MessageType, Callable] = {}
        self._running = False
        self._receive_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start listening for messages."""
        self._running = True
        self._receive_task = asyncio.create_task(self._receive_loop())
        logger.info(f"Agent {self.agent_id} communication started")

    async def stop(self) -> None:
        """Stop listening for messages."""
        self._running = False
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Agent {self.agent_id} communication stopped")

    async def _receive_loop(self) -> None:
        """Background task to receive and process messages."""
        while self._running:
            try:
                message = await self.channel.receive(timeout=1.0)
                if message:
                    await self._handle_message(message)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in receive loop: {e}")

    async def _handle_message(self, message: Message) -> None:
        """Handle an incoming message."""
        handler = self._message_handlers.get(message.type)
        if handler:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Error handling message {message.id}: {e}")
        else:
            logger.debug(f"No handler for message type {message.type}")

    def on_message(self, message_type: MessageType, handler: Callable) -> None:
        """Register a handler for a message type."""
        self._message_handlers[message_type] = handler

    async def send(
        self,
        recipient: AgentAddress,
        subject: str,
        content: Any,
        message_type: MessageType = MessageType.NOTIFICATION,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> MessageReceipt:
        """Send a message to another agent."""
        message = Message(
            type=message_type,
            priority=priority,
            sender=self.address,
            recipient=recipient,
            subject=subject,
            content=content,
        )
        return await self.channel.send(message)

    async def broadcast(
        self,
        subject: str,
        content: Any,
        topic: str | None = None,
    ) -> MessageReceipt:
        """Broadcast a message to all agents or topic subscribers."""
        message = Message(
            type=MessageType.BROADCAST,
            sender=self.address,
            topic=topic,
            subject=subject,
            content=content,
        )
        return await self.channel.send(message)

    async def request(
        self,
        recipient: AgentAddress,
        subject: str,
        content: Any,
        timeout: float = 30.0,
    ) -> Message | None:
        """Send a request and wait for response."""
        if isinstance(self.channel, P2PCommunicationChannel):
            return await self.channel.request(recipient, subject, content, timeout)

        # Fallback for non-P2P channels
        request = Message(
            type=MessageType.REQUEST,
            sender=self.address,
            recipient=recipient,
            subject=subject,
            content=content,
            requires_ack=True,
        )
        await self.channel.send(request)

        # Wait for response (simplified)
        start_time = time.time()
        while time.time() - start_time < timeout:
            message = await self.channel.receive(timeout=0.1)
            if message and message.correlation_id == request.id:
                return message

        return None

    async def respond(self, request: Message, content: Any) -> MessageReceipt:
        """Respond to a request message."""
        response = request.create_response(content)
        response.sender = self.address
        return await self.channel.send(response)

    async def subscribe(self, topic: str, handler: Callable[[Message], None]) -> str:
        """Subscribe to a topic."""
        return await self.channel.subscribe(topic, handler)

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a topic."""
        return await self.channel.unsubscribe(subscription_id)


# ============== Communication Protocol for Agent Coordination ==============

class AgentCoordinationProtocol:
    """
    Protocol for coordinating multiple agents.

    Provides patterns for:
    - Task delegation
    - Consensus building
    - Collaborative problem solving
    - Resource sharing
    """

    def __init__(self, comm_manager: AgentCommunicationManager):
        self.comm = comm_manager
        self._pending_tasks: dict[str, dict] = {}
        self._votes: dict[str, dict[str, Any]] = defaultdict(dict)

    async def delegate_task(
        self,
        agent: AgentAddress,
        task: dict[str, Any],
        timeout: float = 60.0,
    ) -> dict[str, Any] | None:
        """
        Delegate a task to another agent.

        Args:
            agent: Agent to delegate to
            task: Task description and parameters
            timeout: Time to wait for completion

        Returns:
            Task result or None if failed/timeout
        """
        response = await self.comm.request(
            recipient=agent,
            subject="task_delegation",
            content=task,
            timeout=timeout,
        )

        if response:
            return response.content
        return None

    async def propose_consensus(
        self,
        participants: list[AgentAddress],
        proposal: dict[str, Any],
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """
        Propose something for consensus among participants.

        Args:
            participants: List of agents to participate
            proposal: The proposal to vote on
            timeout: Time for voting

        Returns:
            Consensus result with votes
        """
        proposal_id = str(uuid.uuid4())
        self._votes[proposal_id] = {}

        # Broadcast proposal to all participants
        for participant in participants:
            await self.comm.send(
                recipient=participant,
                subject="consensus_proposal",
                content={
                    "proposal_id": proposal_id,
                    "proposal": proposal,
                },
                message_type=MessageType.REQUEST,
            )

        # Wait for votes
        await asyncio.sleep(timeout)

        # Tally votes
        votes = self._votes[proposal_id]
        result = {
            "proposal_id": proposal_id,
            "total_participants": len(participants),
            "votes_received": len(votes),
            "votes": votes,
            "approved": sum(1 for v in votes.values() if v.get("approve", False)),
            "rejected": sum(1 for v in votes.values() if not v.get("approve", True)),
        }

        del self._votes[proposal_id]
        return result

    async def vote(
        self,
        proposal_id: str,
        approve: bool,
        reason: str | None = None,
    ) -> None:
        """Cast a vote on a proposal."""
        self._votes[proposal_id][self.comm.agent_id] = {
            "approve": approve,
            "reason": reason,
            "timestamp": time.time(),
        }

    async def request_resource(
        self,
        owner: AgentAddress,
        resource_id: str,
        duration: float,
        timeout: float = 10.0,
    ) -> bool:
        """
        Request to use a resource from another agent.

        Args:
            owner: Resource owner
            resource_id: ID of the resource
            duration: How long the resource is needed
            timeout: Time to wait for response

        Returns:
            True if resource is granted
        """
        response = await self.comm.request(
            recipient=owner,
            subject="resource_request",
            content={
                "resource_id": resource_id,
                "duration": duration,
                "requester": self.comm.agent_id,
            },
            timeout=timeout,
        )

        if response:
            return response.content.get("granted", False)
        return False

    async def share_information(
        self,
        recipients: list[AgentAddress],
        information: dict[str, Any],
    ) -> int:
        """
        Share information with other agents.

        Returns:
            Number of successful deliveries
        """
        success_count = 0
        for recipient in recipients:
            receipt = await self.comm.send(
                recipient=recipient,
                subject="information_share",
                content=information,
            )
            if receipt.status == DeliveryStatus.DELIVERED:
                success_count += 1
        return success_count
