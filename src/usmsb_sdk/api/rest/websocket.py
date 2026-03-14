"""
WebSocket Manager for AI Civilization Platform

Provides real-time communication:
- Environment updates
- Transaction notifications
- Matching opportunities
- Chat messages
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class MessageType(StrEnum):
    """WebSocket message types."""
    # System
    PING = "ping"
    PONG = "pong"
    AUTH = "auth"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILED = "auth_failed"

    # Environment
    ENVIRONMENT_UPDATE = "environment_update"
    MARKET_CHANGE = "market_change"

    # Matching
    NEW_OPPORTUNITY = "new_opportunity"
    MATCH_UPDATE = "match_update"

    # Transactions
    TRANSACTION_UPDATE = "transaction_update"
    TRANSACTION_COMPLETE = "transaction_complete"

    # Notifications
    NOTIFICATION = "notification"
    PRICE_ALERT = "price_alert"

    # Chat
    CHAT_MESSAGE = "chat_message"
    TYPING = "typing"

    # Agent
    AGENT_STATUS = "agent_status"


@dataclass
class ConnectedClient:
    """A connected WebSocket client."""
    websocket: WebSocket
    agent_id: str | None = None
    session_id: str | None = None
    subscribed_topics: set[str] = field(default_factory=set)
    connected_at: float = field(default_factory=time.time)
    last_ping: float = field(default_factory=time.time)

    @property
    def is_authenticated(self) -> bool:
        return self.agent_id is not None


class WebSocketManager:
    """
    Manages WebSocket connections and message broadcasting.
    """

    def __init__(self):
        """Initialize the WebSocket manager."""
        # Active connections
        self._connections: dict[WebSocket, ConnectedClient] = {}

        # Agent to connections mapping (one agent can have multiple connections)
        self._agent_connections: dict[str, list[WebSocket]] = {}

        # Topic subscribers
        self._topic_subscribers: dict[str, set[WebSocket]] = {}

        # Background tasks
        self._running = False
        self._ping_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start background tasks."""
        self._running = True
        self._ping_task = asyncio.create_task(self._ping_loop())
        logger.info("WebSocket manager started")

    async def stop(self) -> None:
        """Stop background tasks and close all connections."""
        self._running = False

        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        for ws in list(self._connections.keys()):
            try:
                await ws.close()
            except Exception:
                pass

        self._connections.clear()
        self._agent_connections.clear()
        self._topic_subscribers.clear()
        logger.info("WebSocket manager stopped")

    async def _ping_loop(self) -> None:
        """Send periodic pings to keep connections alive."""
        while self._running:
            try:
                await asyncio.sleep(30)  # Ping every 30 seconds
                await self._broadcast_ping()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ping loop error: {e}")

    async def _broadcast_ping(self) -> None:
        """Send ping to all connections."""
        current_time = time.time()
        stale_connections = []

        for ws, client in self._connections.items():
            # Check for stale connections (no response for 60 seconds)
            if current_time - client.last_ping > 60:
                stale_connections.append(ws)
                continue

            try:
                await self._send_to_websocket(ws, {
                    "type": MessageType.PING,
                    "timestamp": current_time,
                })
            except Exception:
                stale_connections.append(ws)

        # Remove stale connections
        for ws in stale_connections:
            await self.disconnect(ws)

    # ==================== Connection Management ====================

    async def connect(self, websocket: WebSocket) -> ConnectedClient:
        """Accept a new WebSocket connection."""
        await websocket.accept()

        client = ConnectedClient(websocket=websocket)
        self._connections[websocket] = client

        logger.info(f"New WebSocket connection: {id(websocket)}")
        return client

    async def disconnect(self, websocket: WebSocket) -> None:
        """Handle WebSocket disconnection."""
        client = self._connections.get(websocket)
        if not client:
            return

        # Remove from agent connections
        if client.agent_id and client.agent_id in self._agent_connections:
            self._agent_connections[client.agent_id] = [
                ws for ws in self._agent_connections[client.agent_id]
                if ws != websocket
            ]
            if not self._agent_connections[client.agent_id]:
                del self._agent_connections[client.agent_id]

        # Remove from topic subscribers
        for topic in client.subscribed_topics:
            if topic in self._topic_subscribers:
                self._topic_subscribers[topic].discard(websocket)

        # Remove connection
        del self._connections[websocket]

        logger.info(f"WebSocket disconnected: {id(websocket)}, agent: {client.agent_id}")

    async def authenticate(
        self,
        websocket: WebSocket,
        agent_id: str,
        session_id: str,
    ) -> bool:
        """Authenticate a WebSocket connection."""
        client = self._connections.get(websocket)
        if not client:
            return False

        client.agent_id = agent_id
        client.session_id = session_id

        # Add to agent connections
        if agent_id not in self._agent_connections:
            self._agent_connections[agent_id] = []
        self._agent_connections[agent_id].append(websocket)

        # Subscribe to agent's personal topic
        await self.subscribe(websocket, f"agent:{agent_id}")

        await self._send_to_websocket(websocket, {
            "type": MessageType.AUTH_SUCCESS,
            "agentId": agent_id,
            "timestamp": time.time(),
        })

        logger.info(f"WebSocket authenticated: {agent_id}")
        return True

    # ==================== Topic Management ====================

    async def subscribe(self, websocket: WebSocket, topic: str) -> None:
        """Subscribe a connection to a topic."""
        client = self._connections.get(websocket)
        if not client:
            return

        client.subscribed_topics.add(topic)

        if topic not in self._topic_subscribers:
            self._topic_subscribers[topic] = set()
        self._topic_subscribers[topic].add(websocket)

        logger.debug(f"Subscribed to topic: {topic}")

    async def unsubscribe(self, websocket: WebSocket, topic: str) -> None:
        """Unsubscribe a connection from a topic."""
        client = self._connections.get(websocket)
        if not client:
            return

        client.subscribed_topics.discard(topic)

        if topic in self._topic_subscribers:
            self._topic_subscribers[topic].discard(websocket)

        logger.debug(f"Unsubscribed from topic: {topic}")

    # ==================== Message Handling ====================

    async def handle_message(self, websocket: WebSocket, message: dict) -> None:
        """Handle an incoming WebSocket message."""
        client = self._connections.get(websocket)
        if not client:
            return

        msg_type = message.get("type")

        if msg_type == MessageType.PONG:
            client.last_ping = time.time()

        elif msg_type == MessageType.AUTH:
            # Authenticate the connection
            agent_id = message.get("agentId")
            session_id = message.get("sessionId")
            if agent_id and session_id:
                await self.authenticate(websocket, agent_id, session_id)
            else:
                await self._send_to_websocket(websocket, {
                    "type": MessageType.AUTH_FAILED,
                    "error": "Missing agentId or sessionId",
                })

        elif msg_type == MessageType.CHAT_MESSAGE:
            # Handle chat message
            target_agent = message.get("targetAgentId")
            content = message.get("content")
            if client.agent_id and target_agent and content:
                await self.send_to_agent(target_agent, {
                    "type": MessageType.CHAT_MESSAGE,
                    "fromAgentId": client.agent_id,
                    "content": content,
                    "timestamp": time.time(),
                })

    # ==================== Broadcasting ====================

    async def _send_to_websocket(self, websocket: WebSocket, message: dict) -> bool:
        """Send a message to a specific WebSocket."""
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.warning(f"Failed to send to WebSocket: {e}")
            return False

    async def send_to_agent(self, agent_id: str, message: dict) -> int:
        """Send a message to all connections of an agent."""
        if agent_id not in self._agent_connections:
            return 0

        sent = 0
        for websocket in self._agent_connections[agent_id]:
            if await self._send_to_websocket(websocket, message):
                sent += 1

        return sent

    async def broadcast_to_topic(self, topic: str, message: dict) -> int:
        """Broadcast a message to all subscribers of a topic."""
        if topic not in self._topic_subscribers:
            return 0

        sent = 0
        for websocket in list(self._topic_subscribers[topic]):
            if await self._send_to_websocket(websocket, message):
                sent += 1

        return sent

    async def broadcast_all(self, message: dict) -> int:
        """Broadcast a message to all connections."""
        sent = 0
        for websocket in list(self._connections.keys()):
            if await self._send_to_websocket(websocket, message):
                sent += 1

        return sent

    async def broadcast_environment_update(self, state: dict) -> None:
        """Broadcast environment state update."""
        await self.broadcast_all({
            "type": MessageType.ENVIRONMENT_UPDATE,
            "data": state,
            "timestamp": time.time(),
        })

    async def send_notification(
        self,
        agent_id: str,
        title: str,
        message: str,
        data: dict = None,
    ) -> None:
        """Send a notification to an agent."""
        await self.send_to_agent(agent_id, {
            "type": MessageType.NOTIFICATION,
            "title": title,
            "message": message,
            "data": data or {},
            "timestamp": time.time(),
        })

    async def send_transaction_update(
        self,
        agent_id: str,
        transaction_id: str,
        status: str,
        data: dict = None,
    ) -> None:
        """Send a transaction status update."""
        await self.send_to_agent(agent_id, {
            "type": MessageType.TRANSACTION_UPDATE,
            "transactionId": transaction_id,
            "status": status,
            "data": data or {},
            "timestamp": time.time(),
        })

    async def send_opportunity(
        self,
        agent_id: str,
        opportunity: dict,
    ) -> None:
        """Send a new opportunity notification."""
        await self.send_to_agent(agent_id, {
            "type": MessageType.NEW_OPPORTUNITY,
            "data": opportunity,
            "timestamp": time.time(),
        })

    # ==================== Statistics ====================

    def get_stats(self) -> dict:
        """Get connection statistics."""
        authenticated = sum(1 for c in self._connections.values() if c.is_authenticated)

        return {
            "totalConnections": len(self._connections),
            "authenticatedConnections": authenticated,
            "uniqueAgents": len(self._agent_connections),
            "topicsCount": len(self._topic_subscribers),
        }


# Global WebSocket manager instance
_ws_manager: WebSocketManager | None = None


async def get_ws_manager() -> WebSocketManager:
    """Get or create WebSocket manager instance."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
        await _ws_manager.start()
    return _ws_manager
