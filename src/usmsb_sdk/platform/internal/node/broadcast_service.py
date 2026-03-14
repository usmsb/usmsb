"""
Node Broadcast Service Module

This module implements real-time broadcasting using WebSocket:
- Message broadcasting to connected nodes
- Message format definitions
- Acknowledgment and delivery tracking
- Topic-based pub/sub messaging
"""

import asyncio
import gzip
import hashlib
import json
import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class BroadcastMessageType(StrEnum):
    """Types of broadcast messages."""
    # Node messages
    NODE_ANNOUNCE = "node_announce"
    NODE_LEAVE = "node_leave"
    NODE_STATUS = "node_status"

    # Data messages
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    DATA_SYNC = "data_sync"

    # Service messages
    SERVICE_REGISTER = "service_register"
    SERVICE_UNREGISTER = "service_unregister"
    SERVICE_REQUEST = "service_request"
    SERVICE_RESPONSE = "service_response"

    # Consensus messages
    PROPOSAL = "proposal"
    VOTE = "vote"
    COMMIT = "commit"

    # System messages
    HEARTBEAT = "heartbeat"
    PING = "ping"
    PONG = "pong"
    ACK = "ack"
    ERROR = "error"

    # Custom messages
    CUSTOM = "custom"


class MessagePriority(StrEnum):
    """Priority levels for messages."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class DeliveryGuarantee(StrEnum):
    """Delivery guarantee levels."""
    BEST_EFFORT = "best_effort"      # No guarantee
    AT_LEAST_ONCE = "at_least_once"  # May deliver duplicates
    EXACTLY_ONCE = "exactly_once"    # Ensure exactly one delivery


@dataclass
class MessageAck:
    """Acknowledgment for a broadcast message."""
    message_id: str
    node_id: str
    status: str  # "received", "processed", "failed"
    timestamp: float = field(default_factory=time.time)
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "node_id": self.node_id,
            "status": self.status,
            "timestamp": self.timestamp,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class BroadcastMessage:
    """A broadcast message."""
    message_id: str
    message_type: BroadcastMessageType
    sender_id: str
    payload: dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    guarantee: DeliveryGuarantee = DeliveryGuarantee.AT_LEAST_ONCE
    topic: str | None = None
    target_nodes: list[str] = field(default_factory=list)
    exclude_nodes: list[str] = field(default_factory=list)
    ttl: float = 300.0
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    sequence_num: int = 0
    correlation_id: str | None = None
    reply_to: str | None = None
    compressed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.created_at + self.ttl

    def is_expired(self) -> bool:
        """Check if message has expired."""
        return time.time() > (self.expires_at or 0)

    def compute_hash(self) -> str:
        """Compute message hash for deduplication."""
        content = f"{self.message_id}:{self.message_type.value}:{self.sender_id}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "payload": self.payload,
            "priority": self.priority.value,
            "guarantee": self.guarantee.value,
            "topic": self.topic,
            "target_nodes": self.target_nodes,
            "exclude_nodes": self.exclude_nodes,
            "ttl": self.ttl,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "sequence_num": self.sequence_num,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "compressed": self.compressed,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    def serialize(self) -> bytes:
        """Serialize message for transmission."""
        data = self.to_json()
        if self.compressed:
            return gzip.compress(data.encode())
        return data.encode()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BroadcastMessage":
        """Create message from dictionary."""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            message_type=BroadcastMessageType(data.get("message_type", "custom")),
            sender_id=data.get("sender_id", ""),
            payload=data.get("payload", {}),
            priority=MessagePriority(data.get("priority", "normal")),
            guarantee=DeliveryGuarantee(data.get("guarantee", "at_least_once")),
            topic=data.get("topic"),
            target_nodes=data.get("target_nodes", []),
            exclude_nodes=data.get("exclude_nodes", []),
            ttl=data.get("ttl", 300.0),
            created_at=data.get("created_at", time.time()),
            expires_at=data.get("expires_at"),
            sequence_num=data.get("sequence_num", 0),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
            compressed=data.get("compressed", False),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def deserialize(cls, data: bytes) -> "BroadcastMessage":
        """Deserialize message from bytes."""
        try:
            # Try decompressing first
            try:
                decompressed = gzip.decompress(data).decode()
                json_data = json.loads(decompressed)
                json_data["compressed"] = True
            except gzip.BadGzipFile:
                json_data = json.loads(data.decode())
            return cls.from_dict(json_data)
        except Exception as e:
            raise ValueError(f"Failed to deserialize message: {e}")


@dataclass
class PendingMessage:
    """Tracks a message waiting for acknowledgments."""
    message: BroadcastMessage
    sent_at: float = field(default_factory=time.time)
    target_nodes: set[str] = field(default_factory=set)
    acked_nodes: set[str] = field(default_factory=set)
    retry_count: int = 0
    max_retries: int = 3
    timeout: float = 30.0

    def is_complete(self) -> bool:
        """Check if all acknowledgments received."""
        return self.acked_nodes >= self.target_nodes

    def get_pending_nodes(self) -> set[str]:
        """Get nodes that haven't acknowledged."""
        return self.target_nodes - self.acked_nodes

    def is_timed_out(self) -> bool:
        """Check if message has timed out."""
        return time.time() - self.sent_at > self.timeout


@dataclass
class BroadcastStats:
    """Statistics for the broadcast service."""
    total_messages_sent: int = 0
    total_messages_received: int = 0
    total_acks_sent: int = 0
    total_acks_received: int = 0
    messages_by_type: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    failed_deliveries: int = 0
    retries: int = 0
    avg_latency_ms: float = 0.0
    active_subscriptions: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_messages_sent": self.total_messages_sent,
            "total_messages_received": self.total_messages_received,
            "total_acks_sent": self.total_acks_sent,
            "total_acks_received": self.total_acks_received,
            "messages_by_type": dict(self.messages_by_type),
            "failed_deliveries": self.failed_deliveries,
            "retries": self.retries,
            "avg_latency_ms": self.avg_latency_ms,
            "active_subscriptions": self.active_subscriptions,
        }


@dataclass
class Subscription:
    """A subscription to broadcast topics."""
    subscription_id: str
    subscriber_id: str
    topics: list[str]
    message_types: list[BroadcastMessageType] = field(default_factory=list)
    callback: Callable[[BroadcastMessage], None] | None = None
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    active: bool = True
    created_at: float = field(default_factory=time.time)

    def matches(self, message: BroadcastMessage) -> bool:
        """Check if subscription matches a message."""
        if not self.active:
            return False

        # Check topic
        if self.topics and message.topic:
            if message.topic not in self.topics:
                return False

        # Check message type
        if self.message_types:
            if message.message_type not in self.message_types:
                return False

        return True


class NodeBroadcastService:
    """
    Node Broadcast Service using WebSocket.

    This service provides real-time broadcasting capabilities:
    - Broadcast messages to all or specific nodes
    - Topic-based pub/sub messaging
    - Message acknowledgment and tracking
    - Automatic retries for failed deliveries

    Usage:
        broadcast = NodeBroadcastService(node_id="node_123")
        await broadcast.start()

        # Subscribe to topics
        await broadcast.subscribe("data_updates", callback=handle_update)

        # Broadcast a message
        await broadcast.broadcast(
            message_type=BroadcastMessageType.DATA_UPDATE,
            payload={"key": "value"},
            topic="data_updates"
        )

        await broadcast.stop()
    """

    DEFAULT_PORT = 8765
    DEFAULT_RETRY_TIMEOUT = 30.0
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_MESSAGE_TTL = 300.0
    MAX_PENDING_MESSAGES = 1000
    ACK_TIMEOUT = 30.0

    def __init__(
        self,
        node_id: str,
        port: int = DEFAULT_PORT,
        enable_compression: bool = True,
        compression_threshold: int = 1024,
    ):
        """
        Initialize the Broadcast Service.

        Args:
            node_id: ID of this node
            port: WebSocket server port
            enable_compression: Enable message compression
            compression_threshold: Bytes threshold for compression
        """
        self.node_id = node_id
        self.port = port
        self.enable_compression = enable_compression
        self.compression_threshold = compression_threshold

        # WebSocket server
        self._server: Any | None = None
        self._running = False

        # Connected clients (node_id -> websocket)
        self._connections: dict[str, Any] = {}

        # Subscriptions
        self._subscriptions: dict[str, Subscription] = {}
        self._topic_subscribers: dict[str, set[str]] = defaultdict(set)

        # Pending messages (for reliable delivery)
        self._pending_messages: dict[str, PendingMessage] = {}

        # Message deduplication
        self._seen_messages: dict[str, float] = {}
        self._seen_messages_ttl = 3600.0

        # Sequence numbers
        self._sequence_num = 0

        # Statistics
        self._stats = BroadcastStats()

        # Background tasks
        self._tasks: set[asyncio.Task] = set()

        # Event handlers
        self._on_message_received: Callable[[BroadcastMessage], None] | None = None
        self._on_client_connected: Callable[[str], None] | None = None
        self._on_client_disconnected: Callable[[str], None] | None = None

    # ==================== Lifecycle ====================

    async def start(self) -> bool:
        """Start the broadcast service."""
        if self._running:
            return True

        try:
            # Import websockets library
            import websockets.server

            self._running = True

            # Start WebSocket server
            self._server = await websockets.server.serve(
                self._handle_connection,
                "0.0.0.0",
                self.port,
            )

            # Start background tasks
            task = asyncio.create_task(self._cleanup_loop())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

            task = asyncio.create_task(self._retry_loop())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

            logger.info(f"Broadcast service started on port {self.port}")
            return True

        except ImportError:
            logger.warning("websockets library not installed, using fallback TCP")
            return await self._start_tcp_fallback()
        except Exception as e:
            logger.error(f"Failed to start broadcast service: {e}")
            return False

    async def _start_tcp_fallback(self) -> bool:
        """Start TCP server as fallback when websockets not available."""
        try:
            self._server = await asyncio.start_server(
                self._handle_tcp_connection,
                "0.0.0.0",
                self.port,
            )
            self._running = True

            task = asyncio.create_task(self._tcp_server_loop())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

            task = asyncio.create_task(self._cleanup_loop())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

            task = asyncio.create_task(self._retry_loop())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

            logger.info(f"Broadcast service started (TCP fallback) on port {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to start TCP fallback: {e}")
            return False

    async def stop(self) -> None:
        """Stop the broadcast service."""
        self._running = False

        # Close all connections
        for _node_id, ws in list(self._connections.items()):
            try:
                if hasattr(ws, 'close'):
                    await ws.close()
            except Exception:
                pass

        self._connections.clear()

        # Close server
        if self._server:
            if hasattr(self._server, 'close'):
                self._server.close()
                if hasattr(self._server, 'wait_closed'):
                    await self._server.wait_closed()

        # Cancel tasks
        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        logger.info("Broadcast service stopped")

    # ==================== Connection Handling ====================

    async def _handle_connection(self, websocket: Any, path: str = "") -> None:
        """Handle WebSocket connection."""
        remote_node_id = None

        try:
            # Wait for identification
            data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            msg = json.loads(data)

            if msg.get("type") == "identify":
                remote_node_id = msg.get("node_id")
                if remote_node_id:
                    self._connections[remote_node_id] = websocket

                    if self._on_client_connected:
                        self._on_client_connected(remote_node_id)

                    logger.debug(f"Client connected: {remote_node_id}")

            # Send acknowledgment
            await websocket.send(json.dumps({
                "type": "identify_ack",
                "node_id": self.node_id,
            }))

            # Handle messages
            async for data in websocket:
                await self._handle_message(data, remote_node_id)

        except TimeoutError:
            logger.warning("Client identification timeout")
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            if remote_node_id and remote_node_id in self._connections:
                del self._connections[remote_node_id]

                if self._on_client_disconnected:
                    self._on_client_disconnected(remote_node_id)

                logger.debug(f"Client disconnected: {remote_node_id}")

    async def _handle_tcp_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle TCP connection (fallback)."""
        writer.get_extra_info('peername')
        remote_node_id = None

        try:
            # Wait for identification
            data = await asyncio.wait_for(reader.readline(), timeout=10.0)
            msg = json.loads(data.decode().strip())

            if msg.get("type") == "identify":
                remote_node_id = msg.get("node_id")
                if remote_node_id:
                    self._connections[remote_node_id] = writer

            # Send acknowledgment
            response = json.dumps({
                "type": "identify_ack",
                "node_id": self.node_id,
            })
            writer.write(response.encode() + b"\n")
            await writer.drain()

            # Handle messages
            while self._running:
                data = await asyncio.wait_for(
                    reader.readline(),
                    timeout=60.0
                )
                if not data:
                    break
                await self._handle_message(data.decode().strip(), remote_node_id)

        except TimeoutError:
            pass
        except Exception as e:
            logger.debug(f"TCP connection error: {e}")
        finally:
            if remote_node_id and remote_node_id in self._connections:
                del self._connections[remote_node_id]
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _tcp_server_loop(self) -> None:
        """TCP server accept loop."""
        async with self._server:
            await self._server.serve_forever()

    async def _handle_message(self, data: str, sender_id: str | None) -> None:
        """Handle received message."""
        try:
            msg_data = json.loads(data)
            msg_type = msg_data.get("type")

            if msg_type == "ack":
                # Handle acknowledgment
                await self._handle_ack(msg_data)
            elif msg_type == "identify" or msg_type == "identify_ack":
                # Already handled in connection setup
                pass
            else:
                # Parse as broadcast message
                message = BroadcastMessage.from_dict(msg_data)
                await self._process_message(message)

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON message: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _process_message(self, message: BroadcastMessage) -> None:
        """Process a received broadcast message."""
        # Check expiration
        if message.is_expired():
            return

        # Check for duplicate
        msg_hash = message.compute_hash()
        if msg_hash in self._seen_messages:
            return

        # Mark as seen
        self._seen_messages[msg_hash] = time.time()

        # Update stats
        self._stats.total_messages_received += 1
        self._stats.messages_by_type[message.message_type.value] += 1

        # Send acknowledgment if required
        if message.guarantee != DeliveryGuarantee.BEST_EFFORT:
            await self._send_ack(message)

        # Deliver to subscribers
        await self._deliver_to_subscribers(message)

        # Call global handler
        if self._on_message_received:
            try:
                if asyncio.iscoroutinefunction(self._on_message_received):
                    await self._on_message_received(message)
                else:
                    self._on_message_received(message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")

    async def _deliver_to_subscribers(self, message: BroadcastMessage) -> int:
        """Deliver message to matching subscribers."""
        delivered = 0

        for subscription in self._subscriptions.values():
            if not subscription.matches(message):
                continue

            if subscription.callback:
                try:
                    if asyncio.iscoroutinefunction(subscription.callback):
                        await subscription.callback(message)
                    else:
                        subscription.callback(message)
                    delivered += 1
                except Exception as e:
                    logger.error(f"Error in subscriber callback: {e}")
            elif subscription.queue:
                try:
                    await subscription.queue.put(message)
                    delivered += 1
                except Exception as e:
                    logger.error(f"Error queueing message: {e}")

        return delivered

    async def _send_ack(self, message: BroadcastMessage) -> None:
        """Send acknowledgment for a message."""
        ack = MessageAck(
            message_id=message.message_id,
            node_id=self.node_id,
            status="received",
        )

        ack_data = {
            "type": "ack",
            **ack.to_dict(),
        }

        if message.sender_id in self._connections:
            try:
                ws = self._connections[message.sender_id]
                if hasattr(ws, 'send'):
                    await ws.send(json.dumps(ack_data))
                else:
                    # TCP fallback
                    ws.write((json.dumps(ack_data) + "\n").encode())
                    await ws.drain()

                self._stats.total_acks_sent += 1
            except Exception as e:
                logger.error(f"Failed to send ack: {e}")

    async def _handle_ack(self, ack_data: dict[str, Any]) -> None:
        """Handle received acknowledgment."""
        message_id = ack_data.get("message_id")
        node_id = ack_data.get("node_id")

        if message_id in self._pending_messages:
            pending = self._pending_messages[message_id]
            pending.acked_nodes.add(node_id)
            self._stats.total_acks_received += 1

            # Remove if complete
            if pending.is_complete():
                del self._pending_messages[message_id]

    # ==================== Broadcasting ====================

    async def broadcast(
        self,
        message_type: BroadcastMessageType,
        payload: dict[str, Any],
        topic: str | None = None,
        target_nodes: list[str] | None = None,
        exclude_nodes: list[str] | None = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        guarantee: DeliveryGuarantee = DeliveryGuarantee.AT_LEAST_ONCE,
        ttl: float = DEFAULT_MESSAGE_TTL,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Broadcast a message to connected nodes.

        Args:
            message_type: Type of message
            payload: Message payload
            topic: Optional topic for pub/sub
            target_nodes: Specific target nodes (None = all)
            exclude_nodes: Nodes to exclude from broadcast
            priority: Message priority
            guarantee: Delivery guarantee level
            ttl: Time to live in seconds
            metadata: Additional metadata

        Returns:
            Message ID
        """
        self._sequence_num += 1

        message = BroadcastMessage(
            message_id=str(uuid.uuid4()),
            message_type=message_type,
            sender_id=self.node_id,
            payload=payload,
            priority=priority,
            guarantee=guarantee,
            topic=topic,
            target_nodes=target_nodes or [],
            exclude_nodes=exclude_nodes or [],
            ttl=ttl,
            sequence_num=self._sequence_num,
            compressed=self.enable_compression and len(json.dumps(payload)) > self.compression_threshold,
            metadata=metadata or {},
        )

        # Determine targets
        targets = set(target_nodes) if target_nodes else set(self._connections.keys())
        targets -= set(exclude_nodes or [])
        targets.discard(self.node_id)  # Don't send to self

        if not targets:
            return message.message_id

        # Track pending message if reliable
        if guarantee != DeliveryGuarantee.BEST_EFFORT:
            pending = PendingMessage(
                message=message,
                target_nodes=targets,
                timeout=self.ACK_TIMEOUT,
            )
            self._pending_messages[message.message_id] = pending

        # Send to all targets
        await self._send_to_targets(message, targets)

        self._stats.total_messages_sent += 1
        self._stats.messages_by_type[message_type.value] += 1

        return message.message_id

    async def _send_to_targets(
        self,
        message: BroadcastMessage,
        targets: set[str]
    ) -> int:
        """Send message to target nodes."""
        sent = 0
        data = message.serialize()

        for node_id in targets:
            if node_id not in self._connections:
                continue

            try:
                ws = self._connections[node_id]
                if hasattr(ws, 'send'):
                    await ws.send(data)
                else:
                    # TCP fallback
                    ws.write(data + b"\n")
                    await ws.drain()
                sent += 1
            except Exception as e:
                logger.error(f"Failed to send to {node_id}: {e}")
                self._stats.failed_deliveries += 1

        return sent

    async def broadcast_to_topic(
        self,
        topic: str,
        message_type: BroadcastMessageType,
        payload: dict[str, Any],
        **kwargs
    ) -> str:
        """Broadcast to a specific topic."""
        return await self.broadcast(
            message_type=message_type,
            payload=payload,
            topic=topic,
            **kwargs
        )

    async def send_to_node(
        self,
        node_id: str,
        message_type: BroadcastMessageType,
        payload: dict[str, Any],
        **kwargs
    ) -> str:
        """Send message to a specific node."""
        return await self.broadcast(
            message_type=message_type,
            payload=payload,
            target_nodes=[node_id],
            **kwargs
        )

    # ==================== Subscriptions ====================

    async def subscribe(
        self,
        topics: str | list[str],
        callback: Callable[[BroadcastMessage], None] | None = None,
        message_types: list[BroadcastMessageType] | None = None,
    ) -> str:
        """
        Subscribe to broadcast topics.

        Args:
            topics: Topic(s) to subscribe to
            callback: Optional callback for messages
            message_types: Optional filter by message types

        Returns:
            Subscription ID
        """
        if isinstance(topics, str):
            topics = [topics]

        subscription = Subscription(
            subscription_id=str(uuid.uuid4()),
            subscriber_id=self.node_id,
            topics=topics,
            message_types=message_types or [],
            callback=callback,
        )

        self._subscriptions[subscription.subscription_id] = subscription

        # Update topic index
        for topic in topics:
            self._topic_subscribers[topic].add(subscription.subscription_id)

        self._stats.active_subscriptions = len(self._subscriptions)

        logger.debug(f"Subscribed to topics: {topics}")
        return subscription.subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from broadcasts."""
        if subscription_id not in self._subscriptions:
            return False

        subscription = self._subscriptions.pop(subscription_id)

        # Update topic index
        for topic in subscription.topics:
            self._topic_subscribers[topic].discard(subscription_id)

        self._stats.active_subscriptions = len(self._subscriptions)

        return True

    async def get_messages(
        self,
        subscription_id: str,
        timeout: float = 1.0,
        max_messages: int = 100,
    ) -> list[BroadcastMessage]:
        """Get pending messages for a subscription."""
        if subscription_id not in self._subscriptions:
            return []

        subscription = self._subscriptions[subscription_id]
        messages = []

        try:
            while len(messages) < max_messages:
                msg = subscription.queue.get_nowait()
                messages.append(msg)
        except asyncio.QueueEmpty:
            pass

        return messages

    # ==================== Connection Management ====================

    async def connect(
        self,
        address: str,
        port: int | None = None,
        timeout: float = 10.0,
    ) -> bool:
        """
        Connect to another broadcast service.

        Args:
            address: Server address
            port: Server port
            timeout: Connection timeout

        Returns:
            True if connected successfully
        """
        port = port or self.DEFAULT_PORT

        try:
            import websockets.client

            uri = f"ws://{address}:{port}"
            websocket = await asyncio.wait_for(
                websockets.client.connect(uri),
                timeout=timeout
            )

            # Send identification
            await websocket.send(json.dumps({
                "type": "identify",
                "node_id": self.node_id,
            }))

            # Wait for acknowledgment
            data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            ack = json.loads(data)

            if ack.get("type") == "identify_ack":
                remote_node_id = ack.get("node_id")
                if remote_node_id:
                    self._connections[remote_node_id] = websocket

                    # Start message handler
                    task = asyncio.create_task(
                        self._handle_connection_messages(websocket, remote_node_id)
                    )
                    self._tasks.add(task)
                    task.add_done_callback(self._tasks.discard)

                    logger.info(f"Connected to broadcast service at {address}:{port}")
                    return True

            await websocket.close()
            return False

        except ImportError:
            # TCP fallback
            return await self._connect_tcp(address, port, timeout)
        except Exception as e:
            logger.error(f"Failed to connect to {address}:{port}: {e}")
            return False

    async def _connect_tcp(
        self,
        address: str,
        port: int,
        timeout: float
    ) -> bool:
        """Connect using TCP (fallback)."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(address, port),
                timeout=timeout
            )

            # Send identification
            writer.write(json.dumps({
                "type": "identify",
                "node_id": self.node_id,
            }).encode() + b"\n")
            await writer.drain()

            # Wait for acknowledgment
            data = await asyncio.wait_for(reader.readline(), timeout=5.0)
            ack = json.loads(data.decode().strip())

            if ack.get("type") == "identify_ack":
                remote_node_id = ack.get("node_id")
                if remote_node_id:
                    self._connections[remote_node_id] = writer

                    # Start message handler
                    task = asyncio.create_task(
                        self._handle_tcp_messages(reader, writer, remote_node_id)
                    )
                    self._tasks.add(task)
                    task.add_done_callback(self._tasks.discard)

                    return True

            writer.close()
            await writer.wait_closed()
            return False

        except Exception as e:
            logger.error(f"TCP connection failed: {e}")
            return False

    async def _handle_connection_messages(
        self,
        websocket: Any,
        node_id: str
    ) -> None:
        """Handle messages from a WebSocket connection."""
        try:
            async for data in websocket:
                await self._handle_message(data, node_id)
        except Exception as e:
            logger.debug(f"Connection closed: {e}")
        finally:
            if node_id in self._connections:
                del self._connections[node_id]

    async def _handle_tcp_messages(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        node_id: str
    ) -> None:
        """Handle messages from a TCP connection."""
        try:
            while self._running:
                data = await asyncio.wait_for(reader.readline(), timeout=60.0)
                if not data:
                    break
                await self._handle_message(data.decode().strip(), node_id)
        except Exception as e:
            logger.debug(f"TCP connection closed: {e}")
        finally:
            if node_id in self._connections:
                del self._connections[node_id]
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def disconnect(self, node_id: str) -> bool:
        """Disconnect from a node."""
        if node_id not in self._connections:
            return False

        ws = self._connections[node_id]
        try:
            if hasattr(ws, 'close'):
                await ws.close()
        except Exception:
            pass

        del self._connections[node_id]
        return True

    # ==================== Background Tasks ====================

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of old data."""
        while self._running:
            try:
                await asyncio.sleep(60.0)

                # Clean up old seen messages
                now = time.time()
                expired = [
                    h for h, t in self._seen_messages.items()
                    if now - t > self._seen_messages_ttl
                ]
                for h in expired:
                    del self._seen_messages[h]

                # Clean up expired pending messages
                expired_pending = [
                    mid for mid, p in self._pending_messages.items()
                    if p.message.is_expired()
                ]
                for mid in expired_pending:
                    del self._pending_messages[mid]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _retry_loop(self) -> None:
        """Retry failed message deliveries."""
        while self._running:
            try:
                await asyncio.sleep(5.0)

                for message_id, pending in list(self._pending_messages.items()):
                    if pending.is_complete():
                        del self._pending_messages[message_id]
                        continue

                    if pending.is_timed_out():
                        if pending.retry_count < pending.max_retries:
                            # Retry
                            pending_nodes = pending.get_pending_nodes()
                            await self._send_to_targets(pending.message, pending_nodes)
                            pending.retry_count += 1
                            pending.sent_at = time.time()
                            self._stats.retries += 1
                        else:
                            # Give up
                            self._stats.failed_deliveries += len(pending.get_pending_nodes())
                            del self._pending_messages[message_id]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in retry loop: {e}")

    # ==================== Status and Info ====================

    def get_stats(self) -> BroadcastStats:
        """Get broadcast statistics."""
        return self._stats

    def get_connected_nodes(self) -> list[str]:
        """Get list of connected node IDs."""
        return list(self._connections.keys())

    def get_pending_count(self) -> int:
        """Get number of pending messages."""
        return len(self._pending_messages)

    def on_message_received(self, callback: Callable[[BroadcastMessage], None]) -> None:
        """Set callback for received messages."""
        self._on_message_received = callback

    def on_client_connected(self, callback: Callable[[str], None]) -> None:
        """Set callback for client connections."""
        self._on_client_connected = callback

    def on_client_disconnected(self, callback: Callable[[str], None]) -> None:
        """Set callback for client disconnections."""
        self._on_client_disconnected = callback
