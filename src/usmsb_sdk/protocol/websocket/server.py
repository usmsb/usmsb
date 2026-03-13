"""
WebSocket Protocol Server

This module provides the WebSocket server implementation for real-time bidirectional communication.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class WebSocketServerConfig:
    """WebSocket server configuration."""
    host: str = "0.0.0.0"
    port: int = 8765
    ping_interval: float = 30.0
    ping_timeout: float = 10.0
    max_size: int = 10 * 1024 * 1024  # 10MB
    max_connections: int = 1000
    compression: bool = False
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None


@dataclass
class WebSocketConnection:
    """Represents a WebSocket connection."""
    connection_id: str
    remote_address: str
    connected_at: float
    last_activity: float = field(default_factory=time.time)
    messages_received: int = 0
    messages_sent: int = 0
    subscriptions: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "remote_address": self.remote_address,
            "connected_at": self.connected_at,
            "last_activity": self.last_activity,
            "messages_received": self.messages_received,
            "messages_sent": self.messages_sent,
            "subscriptions": list(self.subscriptions),
        }


class WebSocketServer:
    """
    WebSocket Server for real-time bidirectional communication.

    Features:
    - Multiple client connections
    - Event broadcasting
    - Room/channel support
    - Ping/pong heartbeat
    - Message routing
    """

    def __init__(
        self,
        config: Optional[WebSocketServerConfig] = None,
        host: str = "0.0.0.0",
        port: int = 8765,
    ):
        """
        Initialize the WebSocket server.

        Args:
            config: Server configuration.
            host: Host to bind to (overrides config).
            port: Port to listen on (overrides config).
        """
        self._config = config or WebSocketServerConfig(host=host, port=port)
        self._server: Optional[Any] = None
        self._running = False
        self._connections: Dict[str, WebSocketConnection] = {}
        self._rooms: Dict[str, Set[str]] = {}  # room_id -> connection_ids
        self._message_handlers: Dict[str, Callable] = {}
        self._connection_handlers: List[Callable] = []
        self._disconnection_handlers: List[Callable] = []

        # Register default handlers
        self._register_default_handlers()

        logger.info(f"WebSocketServer initialized on {self._config.host}:{self._config.port}")

    @property
    def config(self) -> WebSocketServerConfig:
        """Get server configuration."""
        return self._config

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running

    @property
    def connection_count(self) -> int:
        """Get number of active connections."""
        return len(self._connections)

    def _register_default_handlers(self) -> None:
        """Register default message handlers."""
        self._message_handlers["ping"] = self._handle_ping
        self._message_handlers["subscribe"] = self._handle_subscribe
        self._message_handlers["unsubscribe"] = self._handle_unsubscribe

    # ========== Server Control ==========

    async def start(self) -> bool:
        """
        Start the WebSocket server.

        Returns:
            True if server started successfully.
        """
        try:
            logger.info(f"Starting WebSocket server on {self._config.host}:{self._config.port}")

            # In real implementation, use websockets library
            # For now, simulate server startup
            self._running = True
            self._server = {
                "host": self._config.host,
                "port": self._config.port,
                "started_at": time.time(),
            }

            logger.info(f"WebSocket server started on {self._config.host}:{self._config.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            return False

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        if not self._running:
            return

        logger.info("Stopping WebSocket server")

        # Close all connections
        for connection_id in list(self._connections.keys()):
            await self._close_connection(connection_id)

        self._running = False
        self._server = None

        logger.info("WebSocket server stopped")

    async def serve_forever(self) -> None:
        """Run the server until interrupted."""
        if not self._running:
            await self.start()

        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await self.stop()

    # ========== Connection Management ==========

    async def _add_connection(self, remote_address: str) -> str:
        """
        Add a new connection.

        Args:
            remote_address: Client's remote address.

        Returns:
            Connection ID.
        """
        connection_id = str(uuid.uuid4())

        connection = WebSocketConnection(
            connection_id=connection_id,
            remote_address=remote_address,
            connected_at=time.time(),
        )

        self._connections[connection_id] = connection

        # Notify connection handlers
        for handler in self._connection_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(connection)
                else:
                    handler(connection)
            except Exception as e:
                logger.error(f"Connection handler error: {e}")

        logger.info(f"WebSocket connection added: {connection_id} from {remote_address}")
        return connection_id

    async def _close_connection(self, connection_id: str) -> None:
        """
        Close a connection.

        Args:
            connection_id: Connection to close.
        """
        if connection_id not in self._connections:
            return

        connection = self._connections[connection_id]

        # Remove from all rooms
        for room_id in list(self._rooms.keys()):
            self._rooms[room_id].discard(connection_id)
            if not self._rooms[room_id]:
                del self._rooms[room_id]

        # Notify disconnection handlers
        for handler in self._disconnection_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(connection)
                else:
                    handler(connection)
            except Exception as e:
                logger.error(f"Disconnection handler error: {e}")

        del self._connections[connection_id]

        logger.info(f"WebSocket connection closed: {connection_id}")

    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """
        Get a connection by ID.

        Args:
            connection_id: Connection ID.

        Returns:
            Connection or None.
        """
        return self._connections.get(connection_id)

    def get_connections(self) -> List[WebSocketConnection]:
        """Get all active connections."""
        return list(self._connections.values())

    # ========== Message Handling ==========

    def on_message(self, message_type: str) -> Callable:
        """Decorator for registering message handlers."""
        def decorator(handler: Callable) -> Callable:
            self._message_handlers[message_type] = handler
            return handler
        return decorator

    def on_connect(self, handler: Callable) -> Callable:
        """Register a connection handler."""
        self._connection_handlers.append(handler)
        return handler

    def on_disconnect(self, handler: Callable) -> Callable:
        """Register a disconnection handler."""
        self._disconnection_handlers.append(handler)
        return handler

    async def handle_message(
        self,
        connection_id: str,
        message: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Handle an incoming message.

        Args:
            connection_id: Connection that sent the message.
            message: The message.

        Returns:
            Optional response.
        """
        if connection_id not in self._connections:
            return {"error": "Unknown connection"}

        connection = self._connections[connection_id]
        connection.last_activity = time.time()
        connection.messages_received += 1

        message_type = message.get("type", "unknown")
        payload = message.get("payload", {})

        handler = self._message_handlers.get(message_type)
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    return await handler(connection, payload)
                else:
                    return handler(connection, payload)
            except Exception as e:
                logger.error(f"Message handler error: {e}")
                return {"error": str(e)}

        return None

    # ========== Default Handlers ==========

    async def _handle_ping(
        self,
        connection: WebSocketConnection,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle ping message."""
        return {"type": "pong", "timestamp": time.time()}

    async def _handle_subscribe(
        self,
        connection: WebSocketConnection,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle subscribe message."""
        room_id = payload.get("room")
        if not room_id:
            return {"error": "Room ID required"}

        if room_id not in self._rooms:
            self._rooms[room_id] = set()

        self._rooms[room_id].add(connection.connection_id)
        connection.subscriptions.add(room_id)

        return {"type": "subscribed", "room": room_id}

    async def _handle_unsubscribe(
        self,
        connection: WebSocketConnection,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle unsubscribe message."""
        room_id = payload.get("room")
        if not room_id:
            return {"error": "Room ID required"}

        if room_id in self._rooms:
            self._rooms[room_id].discard(connection.connection_id)
            if not self._rooms[room_id]:
                del self._rooms[room_id]

        connection.subscriptions.discard(room_id)

        return {"type": "unsubscribed", "room": room_id}

    # ========== Broadcasting ==========

    async def send_to(
        self,
        connection_id: str,
        message: Dict[str, Any],
    ) -> bool:
        """
        Send a message to a specific connection.

        Args:
            connection_id: Target connection.
            message: Message to send.

        Returns:
            True if sent successfully.
        """
        if connection_id not in self._connections:
            return False

        connection = self._connections[connection_id]
        connection.messages_sent += 1
        connection.last_activity = time.time()

        # In real implementation, send via websocket
        logger.debug(f"Sending message to {connection_id}: {message.get('type', 'unknown')}")

        return True

    async def broadcast(
        self,
        message: Dict[str, Any],
        exclude: Optional[Set[str]] = None,
    ) -> int:
        """
        Broadcast a message to all connections.

        Args:
            message: Message to broadcast.
            exclude: Connection IDs to exclude.

        Returns:
            Number of connections messaged.
        """
        exclude = exclude or set()
        count = 0

        for connection_id in self._connections:
            if connection_id not in exclude:
                if await self.send_to(connection_id, message):
                    count += 1

        return count

    async def broadcast_to_room(
        self,
        room_id: str,
        message: Dict[str, Any],
        exclude: Optional[Set[str]] = None,
    ) -> int:
        """
        Broadcast a message to a room.

        Args:
            room_id: Room to broadcast to.
            message: Message to broadcast.
            exclude: Connection IDs to exclude.

        Returns:
            Number of connections messaged.
        """
        if room_id not in self._rooms:
            return 0

        exclude = exclude or set()
        count = 0

        for connection_id in self._rooms[room_id]:
            if connection_id not in exclude:
                if await self.send_to(connection_id, message):
                    count += 1

        return count

    # ========== Utility Methods ==========

    def get_rooms(self) -> List[str]:
        """Get list of active rooms."""
        return list(self._rooms.keys())

    def get_room_members(self, room_id: str) -> List[str]:
        """Get members of a room."""
        if room_id not in self._rooms:
            return []
        return list(self._rooms[room_id])

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        return {
            "host": self._config.host,
            "port": self._config.port,
            "running": self._running,
            "connections": len(self._connections),
            "rooms": len(self._rooms),
            "uptime": time.time() - self._server["started_at"] if self._server else 0,
        }
