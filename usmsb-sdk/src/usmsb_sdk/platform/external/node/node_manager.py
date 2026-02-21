"""
Node Manager Module

This module implements the core node management functionality, including:
- Node lifecycle management (start, stop, restart)
- Node state tracking
- Connection management to other nodes
- Event handling and callbacks
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from .config import NodeConfig, NodeRole

logger = logging.getLogger(__name__)


class NodeState(str, Enum):
    """States a node can be in."""
    CREATED = "created"
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"


class ConnectionStatus(str, Enum):
    """Status of a connection to another node."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    READY = "ready"
    CLOSING = "closing"
    ERROR = "error"


@dataclass
class NodeConnection:
    """Represents a connection to another node."""
    connection_id: str
    remote_node_id: str
    remote_address: str
    remote_port: int
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    connected_at: Optional[float] = None
    last_activity: float = field(default_factory=time.time)
    bytes_sent: int = 0
    bytes_received: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    latency_ms: float = 0.0
    error_count: int = 0
    last_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # WebSocket connection (set at runtime)
    websocket: Optional[Any] = None

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def record_send(self, bytes_count: int) -> None:
        """Record bytes sent."""
        self.bytes_sent += bytes_count
        self.messages_sent += 1
        self.update_activity()

    def record_receive(self, bytes_count: int) -> None:
        """Record bytes received."""
        self.bytes_received += bytes_count
        self.messages_received += 1
        self.update_activity()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "connection_id": self.connection_id,
            "remote_node_id": self.remote_node_id,
            "remote_address": self.remote_address,
            "remote_port": self.remote_port,
            "status": self.status.value,
            "connected_at": self.connected_at,
            "last_activity": self.last_activity,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "latency_ms": self.latency_ms,
            "error_count": self.error_count,
            "last_error": self.last_error,
        }


@dataclass
class NodeMetrics:
    """Runtime metrics for a node."""
    uptime_seconds: float = 0.0
    total_connections: int = 0
    active_connections: int = 0
    total_messages_sent: int = 0
    total_messages_received: int = 0
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    sync_operations: int = 0
    broadcast_operations: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "uptime_seconds": self.uptime_seconds,
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "total_messages_sent": self.total_messages_sent,
            "total_messages_received": self.total_messages_received,
            "total_bytes_sent": self.total_bytes_sent,
            "total_bytes_received": self.total_bytes_received,
            "sync_operations": self.sync_operations,
            "broadcast_operations": self.broadcast_operations,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "disk_usage": self.disk_usage,
        }


class NodeManager:
    """
    Node Manager for lifecycle and connection management.

    This class manages:
    - Node startup and shutdown
    - State transitions
    - Connections to peer nodes
    - Event notifications
    - Metrics collection

    Usage:
        config = NodeConfig(seed_nodes=["seed1.example.com:8080"])
        manager = NodeManager(config)

        # Start the node
        await manager.start()

        # Connect to peers
        await manager.connect_to_peer("peer1.example.com:8080")

        # Get status
        status = await manager.get_status()

        # Stop the node
        await manager.stop()
    """

    def __init__(self, config: NodeConfig):
        """
        Initialize the Node Manager.

        Args:
            config: Node configuration
        """
        self.config = config
        self.state = NodeState.CREATED
        self.started_at: Optional[float] = None

        # Connections
        self._connections: Dict[str, NodeConnection] = {}
        self._connections_by_node: Dict[str, str] = {}  # node_id -> connection_id

        # Metrics
        self._metrics = NodeMetrics()

        # Event handlers
        self._event_handlers: Dict[str, List[Callable]] = {
            "state_change": [],
            "connection_opened": [],
            "connection_closed": [],
            "connection_error": [],
            "message_received": [],
            "error": [],
        }

        # Background tasks
        self._running = False
        self._tasks: Set[asyncio.Task] = set()

        # Server
        self._server: Optional[asyncio.Server] = None

        # Services (set externally)
        self._discovery_service: Optional[Any] = None
        self._broadcast_service: Optional[Any] = None
        self._sync_service: Optional[Any] = None

    # ==================== Lifecycle Management ====================

    async def start(self) -> bool:
        """
        Start the node.

        Returns:
            True if started successfully, False otherwise
        """
        if self.state == NodeState.RUNNING:
            logger.warning("Node is already running")
            return True

        try:
            self._set_state(NodeState.STARTING)
            self._running = True

            # Start TCP server for incoming connections
            self._server = await asyncio.start_server(
                self._handle_incoming_connection,
                self.config.network.bind_address,
                self.config.network.port,
            )

            self.started_at = time.time()
            self._set_state(NodeState.RUNNING)

            # Start background tasks
            task = asyncio.create_task(self._server_loop())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

            task = asyncio.create_task(self._metrics_loop())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

            task = asyncio.create_task(self._connection_maintenance_loop())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

            # Connect to seed nodes
            if self.config.seed_nodes:
                task = asyncio.create_task(self._connect_to_seeds())
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)

            logger.info(
                f"Node {self.config.node_id} started on "
                f"{self.config.network.address}:{self.config.network.port}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to start node: {e}")
            self._set_state(NodeState.ERROR)
            self._metrics.error_count += 1
            self._metrics.last_error = str(e)
            return False

    async def stop(self) -> None:
        """Stop the node gracefully."""
        if self.state == NodeState.STOPPED:
            return

        self._set_state(NodeState.STOPPING)
        self._running = False

        # Close all connections
        for conn_id, connection in list(self._connections.items()):
            await self._close_connection(conn_id, "Node shutting down")

        # Cancel background tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Close server
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        self._set_state(NodeState.STOPPED)
        logger.info(f"Node {self.config.node_id} stopped")

    async def restart(self) -> bool:
        """Restart the node."""
        await self.stop()
        await asyncio.sleep(1.0)  # Brief pause
        return await self.start()

    def _set_state(self, new_state: NodeState) -> None:
        """Set node state and emit event."""
        old_state = self.state
        self.state = new_state
        logger.debug(f"Node state changed: {old_state} -> {new_state}")
        self._emit_event("state_change", {
            "old_state": old_state.value,
            "new_state": new_state.value,
            "timestamp": time.time(),
        })

    # ==================== Connection Management ====================

    async def connect_to_peer(self, address: str, port: Optional[int] = None) -> Optional[NodeConnection]:
        """
        Connect to a peer node.

        Args:
            address: Peer address (host or host:port)
            port: Peer port (optional if included in address)

        Returns:
            NodeConnection if successful, None otherwise
        """
        # Parse address
        if ":" in address and port is None:
            address, port_str = address.rsplit(":", 1)
            port = int(port_str)
        elif port is None:
            port = 8080

        connection_id = f"conn_{address}_{port}_{time.time()}"

        try:
            connection = NodeConnection(
                connection_id=connection_id,
                remote_node_id="",  # Will be set after handshake
                remote_address=address,
                remote_port=port,
                status=ConnectionStatus.CONNECTING,
            )

            self._connections[connection_id] = connection
            self._metrics.total_connections += 1

            # Attempt connection
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(address, port),
                timeout=self.config.network.connection_timeout
            )

            connection.status = ConnectionStatus.CONNECTED
            connection.connected_at = time.time()

            # Perform handshake
            await self._perform_handshake(connection, writer)

            # Start message handler
            task = asyncio.create_task(
                self._handle_connection_messages(connection, reader, writer)
            )
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

            self._emit_event("connection_opened", connection.to_dict())
            logger.info(f"Connected to peer: {address}:{port}")

            return connection

        except asyncio.TimeoutError:
            logger.warning(f"Connection timeout to {address}:{port}")
            self._metrics.error_count += 1
            return None
        except Exception as e:
            logger.error(f"Failed to connect to {address}:{port}: {e}")
            self._metrics.error_count += 1
            self._metrics.last_error = str(e)
            return None

    async def disconnect_peer(self, node_id: str, reason: str = "Manual disconnect") -> bool:
        """
        Disconnect from a peer node.

        Args:
            node_id: ID of the peer to disconnect
            reason: Reason for disconnection

        Returns:
            True if disconnected, False if not connected
        """
        if node_id not in self._connections_by_node:
            return False

        connection_id = self._connections_by_node[node_id]
        return await self._close_connection(connection_id, reason)

    async def _close_connection(self, connection_id: str, reason: str = "") -> bool:
        """Close a connection."""
        if connection_id not in self._connections:
            return False

        connection = self._connections[connection_id]
        connection.status = ConnectionStatus.CLOSING

        if connection.websocket:
            try:
                await connection.websocket.close()
            except Exception:
                pass

        del self._connections[connection_id]
        if connection.remote_node_id in self._connections_by_node:
            del self._connections_by_node[connection.remote_node_id]

        self._emit_event("connection_closed", {
            "connection_id": connection_id,
            "remote_node_id": connection.remote_node_id,
            "reason": reason,
        })

        logger.info(f"Connection closed: {connection_id} - {reason}")
        return True

    async def _handle_incoming_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle incoming connection."""
        peer_addr = writer.get_extra_info('peername')
        connection_id = f"conn_incoming_{peer_addr[0]}_{peer_addr[1]}_{time.time()}"

        connection = NodeConnection(
            connection_id=connection_id,
            remote_node_id="",
            remote_address=peer_addr[0],
            remote_port=peer_addr[1],
            status=ConnectionStatus.CONNECTED,
            connected_at=time.time(),
        )

        self._connections[connection_id] = connection
        self._metrics.total_connections += 1

        self._emit_event("connection_opened", connection.to_dict())

        try:
            await self._handle_connection_messages(connection, reader, writer)
        except Exception as e:
            logger.error(f"Error handling incoming connection: {e}")
        finally:
            await self._close_connection(connection_id, "Connection ended")

    async def _perform_handshake(
        self,
        connection: NodeConnection,
        writer: asyncio.StreamWriter
    ) -> None:
        """Perform handshake with peer."""
        connection.status = ConnectionStatus.AUTHENTICATING

        # Send hello message
        hello_msg = {
            "type": "hello",
            "node_id": self.config.node_id,
            "version": self.config.version,
            "capabilities": self.config.capabilities.to_dict(),
            "timestamp": time.time(),
        }

        writer.write(json.dumps(hello_msg).encode() + b"\n")
        await writer.drain()

        connection.status = ConnectionStatus.AUTHENTICATED

    async def _handle_connection_messages(
        self,
        connection: NodeConnection,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle messages from a connection."""
        connection.status = ConnectionStatus.READY

        while self._running:
            try:
                data = await asyncio.wait_for(
                    reader.readline(),
                    timeout=self.config.network.idle_timeout
                )

                if not data:
                    break

                connection.record_receive(len(data))

                message = json.loads(data.decode().strip())
                await self._process_message(connection, message, writer)

            except asyncio.TimeoutError:
                # Send keepalive
                try:
                    writer.write(b'{"type": "ping"}\n')
                    await writer.drain()
                except Exception:
                    break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from {connection.remote_node_id}: {e}")
                connection.error_count += 1
            except Exception as e:
                logger.error(f"Error reading from connection: {e}")
                break

    async def _process_message(
        self,
        connection: NodeConnection,
        message: Dict[str, Any],
        writer: asyncio.StreamWriter
    ) -> None:
        """Process a received message."""
        msg_type = message.get("type")

        if msg_type == "hello":
            # Handle handshake
            connection.remote_node_id = message.get("node_id", "")
            if connection.remote_node_id:
                self._connections_by_node[connection.remote_node_id] = connection.connection_id
            logger.info(f"Handshake completed with {connection.remote_node_id}")

        elif msg_type == "ping":
            writer.write(b'{"type": "pong"}\n')
            await writer.drain()

        elif msg_type == "pong":
            # Pong received, connection is alive
            pass

        else:
            # Emit message received event
            self._emit_event("message_received", {
                "connection_id": connection.connection_id,
                "remote_node_id": connection.remote_node_id,
                "message": message,
            })

        self._metrics.total_messages_received += 1

    async def send_message(self, node_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a message to a connected node.

        Args:
            node_id: Target node ID
            message: Message to send

        Returns:
            True if sent successfully
        """
        if node_id not in self._connections_by_node:
            logger.warning(f"Not connected to node {node_id}")
            return False

        connection_id = self._connections_by_node[node_id]
        connection = self._connections.get(connection_id)

        if not connection or connection.websocket is None:
            return False

        try:
            data = json.dumps(message).encode()
            await connection.websocket.send(data)
            connection.record_send(len(data))
            self._metrics.total_messages_sent += 1
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {node_id}: {e}")
            return False

    async def broadcast_message(self, message: Dict[str, Any]) -> int:
        """
        Broadcast a message to all connected nodes.

        Args:
            message: Message to broadcast

        Returns:
            Number of nodes the message was sent to
        """
        count = 0
        for node_id in self._connections_by_node:
            if await self.send_message(node_id, message):
                count += 1
        self._metrics.broadcast_operations += 1
        return count

    # ==================== Background Tasks ====================

    async def _server_loop(self) -> None:
        """Server accept loop."""
        async with self._server:
            await self._server.serve_forever()

    async def _metrics_loop(self) -> None:
        """Periodically update metrics."""
        while self._running:
            try:
                self._metrics.uptime_seconds = time.time() - (self.started_at or time.time())
                self._metrics.active_connections = len([
                    c for c in self._connections.values()
                    if c.status in [ConnectionStatus.CONNECTED, ConnectionStatus.READY]
                ])

                # Get system metrics (simplified)
                # In production, use psutil or similar
                self._metrics.cpu_usage = 0.0
                self._metrics.memory_usage = 0.0
                self._metrics.disk_usage = 0.0

                await asyncio.sleep(10.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics loop: {e}")

    async def _connection_maintenance_loop(self) -> None:
        """Maintain connections (reconnect, cleanup)."""
        while self._running:
            try:
                # Clean up stale connections
                now = time.time()
                stale_threshold = self.config.network.idle_timeout * 2

                stale_connections = [
                    cid for cid, conn in self._connections.items()
                    if now - conn.last_activity > stale_threshold
                ]

                for cid in stale_connections:
                    await self._close_connection(cid, "Connection stale")

                await asyncio.sleep(30.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in connection maintenance: {e}")

    async def _connect_to_seeds(self) -> None:
        """Connect to seed nodes."""
        for seed in self.config.seed_nodes:
            try:
                await self.connect_to_peer(seed)
                await asyncio.sleep(1.0)  # Stagger connections
            except Exception as e:
                logger.warning(f"Failed to connect to seed {seed}: {e}")

    # ==================== Event Handling ====================

    def on(self, event: str, handler: Callable) -> None:
        """Register an event handler."""
        if event in self._event_handlers:
            self._event_handlers[event].append(handler)

    def off(self, event: str, handler: Callable) -> None:
        """Unregister an event handler."""
        if event in self._event_handlers and handler in self._event_handlers[event]:
            self._event_handlers[event].remove(handler)

    def _emit_event(self, event: str, data: Any) -> None:
        """Emit an event to all handlers."""
        for handler in self._event_handlers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(data))
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in event handler for {event}: {e}")

    # ==================== Status and Info ====================

    async def get_status(self) -> Dict[str, Any]:
        """Get current node status."""
        return {
            "node_id": self.config.node_id,
            "node_name": self.config.node_name,
            "state": self.state.value,
            "started_at": self.started_at,
            "uptime": time.time() - (self.started_at or time.time()),
            "connections": {
                "total": len(self._connections),
                "active": self._metrics.active_connections,
            },
            "metrics": self._metrics.to_dict(),
            "config": self.config.to_dict(),
        }

    def get_connections(self) -> List[Dict[str, Any]]:
        """Get list of all connections."""
        return [conn.to_dict() for conn in self._connections.values()]

    def get_connection(self, node_id: str) -> Optional[NodeConnection]:
        """Get connection to a specific node."""
        if node_id not in self._connections_by_node:
            return None
        return self._connections.get(self._connections_by_node[node_id])

    def get_metrics(self) -> NodeMetrics:
        """Get node metrics."""
        return self._metrics

    # ==================== Service Integration ====================

    def set_discovery_service(self, service: Any) -> None:
        """Set the discovery service."""
        self._discovery_service = service

    def set_broadcast_service(self, service: Any) -> None:
        """Set the broadcast service."""
        self._broadcast_service = service

    def set_sync_service(self, service: Any) -> None:
        """Set the sync service."""
        self._sync_service = service
