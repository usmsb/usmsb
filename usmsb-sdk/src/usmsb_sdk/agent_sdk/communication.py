"""
Agent Communication Module

Implements the unified communication system for agents, including:
- Multi-protocol message sending
- Message receiving and routing
- Session management
- P2P direct connection capability
- WebSocket and gRPC support
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import uuid4
import asyncio
import aiohttp
import json
import logging
import struct
import websockets

from usmsb_sdk.agent_sdk.agent_config import (
    AgentConfig,
    ProtocolType,
    ProtocolConfig,
)


class MessageType(Enum):
    """Types of messages"""
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    NOTIFICATION = "notification"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    DISCOVERY = "discovery"
    SKILL_CALL = "skill_call"
    SKILL_RESPONSE = "skill_response"
    P2P_HANDSHAKE = "p2p_handshake"
    P2P_DATA = "p2p_data"


class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class Message:
    """A message exchanged between agents"""
    type: MessageType
    sender_id: str
    content: Any
    message_id: str = field(default_factory=lambda: str(uuid4()))
    receiver_id: Optional[str] = None
    correlation_id: Optional[str] = None  # For request/response matching
    timestamp: datetime = field(default_factory=datetime.now)
    priority: MessagePriority = MessagePriority.NORMAL
    ttl: int = 60  # Time-to-live in seconds
    protocol: Optional[ProtocolType] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if message has expired"""
        return datetime.now() > self.timestamp + timedelta(seconds=self.ttl)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "message_id": self.message_id,
            "type": self.type.value,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "content": self.content,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "ttl": self.ttl,
            "protocol": self.protocol.value if self.protocol else None,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary"""
        return cls(
            message_id=data.get("message_id", str(uuid4())),
            type=MessageType(data["type"]),
            sender_id=data["sender_id"],
            receiver_id=data.get("receiver_id"),
            content=data["content"],
            correlation_id=data.get("correlation_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if isinstance(data.get("timestamp"), str) else datetime.now(),
            priority=MessagePriority(data.get("priority", 1)),
            ttl=data.get("ttl", 60),
            protocol=ProtocolType(data["protocol"]) if data.get("protocol") else None,
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))

    def create_response(self, content: Any) -> "Message":
        """Create a response message for this message"""
        return Message(
            type=MessageType.RESPONSE,
            sender_id=self.receiver_id,
            receiver_id=self.sender_id,
            content=content,
            correlation_id=self.message_id,
            protocol=self.protocol,
        )

    def create_error(self, error_message: str, error_code: Optional[str] = None) -> "Message":
        """Create an error response for this message"""
        return Message(
            type=MessageType.ERROR,
            sender_id=self.receiver_id,
            receiver_id=self.sender_id,
            content={
                "error": error_message,
                "code": error_code,
            },
            correlation_id=self.message_id,
            protocol=self.protocol,
        )


@dataclass
class Session:
    """Represents a communication session between agents"""
    session_id: str
    initiator_id: str
    participant_ids: Set[str]
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    state: str = "active"
    protocol: Optional[ProtocolType] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_count: int = 0

    def is_active(self) -> bool:
        """Check if session is active"""
        return self.state == "active"

    def touch(self) -> None:
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
        self.message_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "session_id": self.session_id,
            "initiator_id": self.initiator_id,
            "participant_ids": list(self.participant_ids),
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "state": self.state,
            "protocol": self.protocol.value if self.protocol else None,
            "metadata": self.metadata,
            "message_count": self.message_count,
        }


@dataclass
class P2PConnection:
    """Represents a P2P connection to another agent"""
    agent_id: str
    endpoint: str
    connected_at: datetime = field(default_factory=datetime.now)
    state: str = "connecting"
    bytes_sent: int = 0
    bytes_received: int = 0
    latency: float = 0.0
    websocket: Optional[Any] = None
    protocol: ProtocolType = ProtocolType.P2P

    def is_connected(self) -> bool:
        """Check if connection is active"""
        return self.state == "connected" and self.websocket is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without websocket)"""
        return {
            "agent_id": self.agent_id,
            "endpoint": self.endpoint,
            "connected_at": self.connected_at.isoformat(),
            "state": self.state,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "latency": self.latency,
            "protocol": self.protocol.value,
        }


class CommunicationManager:
    """
    Manages all communication for an agent.

    Features:
    - Unified message sending interface across protocols
    - Message receiving and routing
    - Session management
    - P2P direct connection capability
    - WebSocket and HTTP transport support
    - Message queuing and retry logic
    """

    def __init__(
        self,
        agent_id: str,
        agent_config: AgentConfig,
        message_handler: Callable,
        logger: Optional[logging.Logger] = None,
    ):
        self.agent_id = agent_id
        self.config = agent_config
        self.message_handler = message_handler
        self.logger = logger or logging.getLogger(__name__)

        # Sessions
        self._sessions: Dict[str, Session] = {}
        self._session_lock = asyncio.Lock()

        # P2P connections
        self._p2p_connections: Dict[str, P2PConnection] = {}
        self._p2p_lock = asyncio.Lock()

        # HTTP/WebSocket
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._http_server: Optional[Any] = None  # HTTP REST server
        self._websocket_server: Optional[Any] = None
        self._active_websockets: Dict[str, websockets.WebSocketClientProtocol] = {}

        # Message routing
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._handlers: Dict[str, Callable] = {}

        # State
        self._initialized = False
        self._running = False

    @property
    def p2p_connections(self) -> Dict[str, P2PConnection]:
        return self._p2p_connections

    @property
    def sessions(self) -> Dict[str, Session]:
        return self._sessions

    # ==================== Initialization ====================

    async def initialize(self, skip_http_start: bool = False) -> None:
        """Initialize communication channels

        Args:
            skip_http_start: If True, skip auto-starting HTTP server (useful when starting manually later)
        """
        if self._initialized:
            return

        self._http_session = aiohttp.ClientSession()

        # Start protocols based on config
        protocols = self.config.get_enabled_protocols()

        if ProtocolType.HTTP in protocols and not skip_http_start:
            await self._start_http_server()

        if ProtocolType.WEBSOCKET in protocols:
            await self._start_websocket_server()

        if ProtocolType.P2P in protocols:
            await self._start_p2p_listener()

        # Start message processing
        self._running = True
        asyncio.create_task(self._process_messages())

        self._initialized = True
        self.logger.info(f"Communication manager initialized for agent {self.agent_id}")

    async def close(self) -> None:
        """Close all communication channels"""
        self._running = False

        # Close HTTP server
        if self._http_server:
            await self._http_server.stop()
            self._http_server = None

        # Close P2P connections
        for conn in list(self._p2p_connections.values()):
            await self.close_p2p(conn.agent_id)

        # Close WebSocket server
        if self._websocket_server:
            self._websocket_server.close()
            await self._websocket_server.wait_closed()

        # Close active WebSockets
        for ws in list(self._active_websockets.values()):
            await ws.close()

        # Close HTTP session
        if self._http_session:
            await self._http_session.close()

        self.logger.info(f"Communication manager closed for agent {self.agent_id}")

    # ==================== Message Sending ====================

    async def send(
        self,
        message: Message,
        protocol: Optional[ProtocolType] = None,
    ) -> Optional[Message]:
        """
        Send a message using the appropriate protocol.

        Args:
            message: The message to send
            protocol: Preferred protocol (auto-select if None)

        Returns:
            Response message if request/response pattern
        """
        if not self._initialized:
            raise RuntimeError("Communication manager not initialized")

        # Determine protocol
        if protocol is None:
            protocol = await self._select_protocol(message)

        message.protocol = protocol

        # Route by protocol
        if protocol == ProtocolType.P2P:
            return await self._send_p2p(message)
        elif protocol == ProtocolType.WEBSOCKET:
            return await self._send_websocket(message)
        elif protocol == ProtocolType.HTTP:
            return await self._send_http(message)
        elif protocol == ProtocolType.A2A:
            return await self._send_a2a(message)
        elif protocol == ProtocolType.MCP:
            return await self._send_mcp(message)
        elif protocol == ProtocolType.GRPC:
            return await self._send_grpc(message)
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")

    async def _select_protocol(self, message: Message) -> ProtocolType:
        """Select the best protocol for a message"""
        target_id = message.receiver_id

        # Check if P2P connection exists
        if target_id and target_id in self._p2p_connections:
            conn = self._p2p_connections[target_id]
            if conn.is_connected():
                return ProtocolType.P2P

        # Check if WebSocket connection exists
        if target_id and target_id in self._active_websockets:
            return ProtocolType.WEBSOCKET

        # Fall back to HTTP
        if ProtocolType.HTTP in self.config.protocols:
            return ProtocolType.HTTP

        # Use any available protocol
        enabled = self.config.get_enabled_protocols()
        return enabled[0] if enabled else ProtocolType.HTTP

    async def send_p2p(self, message: Message, target_id: str) -> Optional[Message]:
        """Send message via P2P connection"""
        if target_id not in self._p2p_connections:
            # Try to establish connection
            if not await self.establish_p2p(target_id):
                raise ConnectionError(f"Cannot establish P2P connection to {target_id}")

        return await self._send_p2p(message)

    async def _send_p2p(self, message: Message) -> Optional[Message]:
        """Internal P2P send implementation"""
        target_id = message.receiver_id
        if not target_id or target_id not in self._p2p_connections:
            raise ConnectionError(f"No P2P connection to {target_id}")

        conn = self._p2p_connections[target_id]
        if not conn.is_connected():
            raise ConnectionError(f"P2P connection to {target_id} is not active")

        try:
            # Send via WebSocket
            data = message.to_json()
            await conn.websocket.send(data)
            conn.bytes_sent += len(data.encode())

            # Wait for response if request message
            if message.type == MessageType.REQUEST:
                return await self._wait_for_response(message.message_id)

            return None
        except Exception as e:
            self.logger.error(f"P2P send error: {e}")
            conn.state = "error"
            raise

    async def _send_websocket(self, message: Message) -> Optional[Message]:
        """Send message via WebSocket"""
        target_id = message.receiver_id

        # Check existing connection
        if target_id and target_id in self._active_websockets:
            ws = self._active_websockets[target_id]
            try:
                await ws.send(message.to_json())

                if message.type == MessageType.REQUEST:
                    return await self._wait_for_response(message.message_id)
                return None
            except Exception as e:
                self.logger.error(f"WebSocket send error: {e}")
                del self._active_websockets[target_id]

        # Fall back to platform relay
        return await self._send_via_relay(message, "websocket")

    async def _send_http(self, message: Message) -> Optional[Message]:
        """Send message via HTTP"""
        if not self._http_session:
            raise RuntimeError("HTTP session not initialized")

        # Use platform endpoint to relay message
        platform_url = self.config.network.platform_endpoints[0] if self.config.network.platform_endpoints else "http://localhost:8000"

        headers = {}
        if self.config.security.api_key:
            headers["Authorization"] = f"Bearer {self.config.security.api_key}"

        try:
            async with self._http_session.post(
                f"{platform_url}/api/v1/messages/send",
                json=message.to_dict(),
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("response"):
                        return Message.from_dict(data["response"])
                    return None
                else:
                    error = await response.text()
                    raise Exception(f"HTTP send failed: {response.status} - {error}")
        except Exception as e:
            self.logger.error(f"HTTP send error: {e}")
            raise

    async def _send_a2a(self, message: Message) -> Optional[Message]:
        """Send message via A2A protocol"""
        # A2A uses HTTP as transport with specific headers
        if not self._http_session:
            raise RuntimeError("HTTP session not initialized")

        platform_url = self.config.network.platform_endpoints[0] if self.config.network.platform_endpoints else "http://localhost:8000"

        headers = {
            "X-Protocol": "A2A",
            "Content-Type": "application/json",
        }
        if self.config.security.api_key:
            headers["Authorization"] = f"Bearer {self.config.security.api_key}"

        a2a_message = {
            "protocol": "a2a",
            "version": "1.0",
            "message": message.to_dict(),
        }

        try:
            async with self._http_session.post(
                f"{platform_url}/api/v1/a2a/send",
                json=a2a_message,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("response"):
                        return Message.from_dict(data["response"])
                    return None
                raise Exception(f"A2A send failed: {response.status}")
        except Exception as e:
            self.logger.error(f"A2A send error: {e}")
            raise

    async def _send_mcp(self, message: Message) -> Optional[Message]:
        """Send message via MCP (Model Context Protocol)"""
        if not self._http_session:
            raise RuntimeError("HTTP session not initialized")

        platform_url = self.config.network.platform_endpoints[0] if self.config.network.platform_endpoints else "http://localhost:8000"

        mcp_message = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": message.to_dict(),
            "id": message.message_id,
        }

        headers = {"Content-Type": "application/json"}
        if self.config.security.api_key:
            headers["Authorization"] = f"Bearer {self.config.security.api_key}"

        try:
            async with self._http_session.post(
                f"{platform_url}/api/v1/mcp",
                json=mcp_message,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if "result" in data and data["result"].get("response"):
                        return Message.from_dict(data["result"]["response"])
                    return None
                raise Exception(f"MCP send failed: {response.status}")
        except Exception as e:
            self.logger.error(f"MCP send error: {e}")
            raise

    async def _send_grpc(self, message: Message) -> Optional[Message]:
        """Send message via gRPC"""
        # gRPC implementation would require grpcio library
        # For now, fall back to HTTP with gRPC-style message
        self.logger.warning("gRPC not fully implemented, using HTTP fallback")
        return await self._send_http(message)

    async def _send_via_relay(self, message: Message, protocol: str) -> Optional[Message]:
        """Send message via platform relay"""
        if not self._http_session:
            raise RuntimeError("HTTP session not initialized")

        platform_url = self.config.network.platform_endpoints[0] if self.config.network.platform_endpoints else "http://localhost:8000"

        headers = {
            "X-Relay-Protocol": protocol,
            "Content-Type": "application/json",
        }
        if self.config.security.api_key:
            headers["Authorization"] = f"Bearer {self.config.security.api_key}"

        try:
            async with self._http_session.post(
                f"{platform_url}/api/v1/relay/send",
                json={
                    "protocol": protocol,
                    "message": message.to_dict(),
                },
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("response"):
                        return Message.from_dict(data["response"])
                    return None
                raise Exception(f"Relay send failed: {response.status}")
        except Exception as e:
            self.logger.error(f"Relay send error: {e}")
            raise

    # ==================== P2P Connection Management ====================

    async def establish_p2p(self, target_id: str, endpoint: Optional[str] = None) -> bool:
        """
        Establish a P2P connection with another agent.

        Args:
            target_id: Target agent ID
            endpoint: Direct endpoint (discovered if not provided)

        Returns:
            True if connection established successfully
        """
        async with self._p2p_lock:
            if target_id in self._p2p_connections:
                conn = self._p2p_connections[target_id]
                if conn.is_connected():
                    return True

            # Discover endpoint if not provided
            if not endpoint:
                endpoint = await self._discover_p2p_endpoint(target_id)
                if not endpoint:
                    self.logger.error(f"Cannot discover P2P endpoint for {target_id}")
                    return False

            try:
                # Create connection record
                conn = P2PConnection(
                    agent_id=target_id,
                    endpoint=endpoint,
                    state="connecting",
                )
                self._p2p_connections[target_id] = conn

                # Connect via WebSocket
                ws = await websockets.connect(
                    f"{endpoint}/p2p/{target_id}",
                    extra_headers={
                        "X-Agent-ID": self.agent_id,
                    },
                )
                conn.websocket = ws
                conn.state = "connected"

                # Send handshake
                handshake = Message(
                    type=MessageType.P2P_HANDSHAKE,
                    sender_id=self.agent_id,
                    content={"action": "connect"},
                )
                await ws.send(handshake.to_json())

                # Start listening for messages
                asyncio.create_task(self._p2p_receiver(target_id))

                self.logger.info(f"P2P connection established with {target_id}")
                return True

            except Exception as e:
                self.logger.error(f"Failed to establish P2P connection: {e}")
                if target_id in self._p2p_connections:
                    self._p2p_connections[target_id].state = "failed"
                return False

    async def close_p2p(self, target_id: str) -> None:
        """Close P2P connection with an agent"""
        async with self._p2p_lock:
            if target_id not in self._p2p_connections:
                return

            conn = self._p2p_connections[target_id]
            if conn.websocket:
                try:
                    # Send close message
                    close_msg = Message(
                        type=MessageType.P2P_HANDSHAKE,
                        sender_id=self.agent_id,
                        content={"action": "disconnect"},
                    )
                    await conn.websocket.send(close_msg.to_json())
                    await conn.websocket.close()
                except Exception as e:
                    self.logger.warning(f"Error closing P2P connection: {e}")

            del self._p2p_connections[target_id]
            self.logger.info(f"P2P connection closed with {target_id}")

    async def _discover_p2p_endpoint(self, target_id: str) -> Optional[str]:
        """Discover P2P endpoint for an agent"""
        if not self._http_session:
            return None

        platform_url = self.config.network.platform_endpoints[0] if self.config.network.platform_endpoints else "http://localhost:8000"

        try:
            async with self._http_session.get(
                f"{platform_url}/agents/{target_id}/endpoint",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("p2p_endpoint")
        except Exception as e:
            self.logger.warning(f"Failed to discover P2P endpoint: {e}")

        return None

    async def _p2p_receiver(self, target_id: str) -> None:
        """Receive messages from P2P connection"""
        if target_id not in self._p2p_connections:
            return

        conn = self._p2p_connections[target_id]
        ws = conn.websocket

        try:
            async for data in ws:
                try:
                    message = Message.from_json(data)
                    conn.bytes_received += len(data.encode())

                    # Handle response matching
                    if message.correlation_id and message.correlation_id in self._pending_responses:
                        future = self._pending_responses.pop(message.correlation_id)
                        if not future.done():
                            future.set_result(message)
                    else:
                        # Queue for processing
                        await self._message_queue.put((message, None))

                except json.JSONDecodeError:
                    self.logger.warning(f"Invalid JSON from P2P connection: {target_id}")
                except Exception as e:
                    self.logger.error(f"Error processing P2P message: {e}")

        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"P2P connection closed by peer: {target_id}")
        except Exception as e:
            self.logger.error(f"P2P receiver error: {e}")
        finally:
            conn.state = "disconnected"

    async def _start_p2p_listener(self) -> None:
        """Start P2P listener server"""
        port = self.config.network.p2p_listen_port

        async def handle_connection(websocket, path):
            """Handle incoming P2P connection"""
            try:
                # Get peer agent ID
                peer_id = websocket.request_headers.get("X-Agent-ID", "unknown")

                # Create connection record
                conn = P2PConnection(
                    agent_id=peer_id,
                    endpoint=str(websocket.remote_address),
                    websocket=websocket,
                    state="connected",
                )
                self._p2p_connections[peer_id] = conn

                # Handle messages
                async for data in websocket:
                    message = Message.from_json(data)
                    conn.bytes_received += len(data.encode())

                    # Handle handshake
                    if message.type == MessageType.P2P_HANDSHAKE:
                        if message.content.get("action") == "disconnect":
                            break
                        continue

                    # Queue for processing
                    await self._message_queue.put((message, None))

            except Exception as e:
                self.logger.error(f"P2P listener error: {e}")
            finally:
                if peer_id in self._p2p_connections:
                    del self._p2p_connections[peer_id]

        self._websocket_server = await websockets.serve(
            handle_connection,
            "0.0.0.0",
            port,
        )
        self.logger.info(f"P2P listener started on port {port}")

    # ==================== WebSocket Server ====================

    async def _start_websocket_server(self) -> None:
        """Start WebSocket server for agent communication"""
        protocol_config = self.config.protocols.get(ProtocolType.WEBSOCKET)
        port = protocol_config.port if protocol_config and protocol_config.port else 8765

        async def handle_websocket(websocket, path):
            """Handle WebSocket connection"""
            peer_id = str(websocket.remote_address)
            self._active_websockets[peer_id] = websocket

            try:
                async for data in websocket:
                    message = Message.from_json(data)
                    await self._message_queue.put((message, None))
            except websockets.exceptions.ConnectionClosed:
                pass
            finally:
                del self._active_websockets[peer_id]

        self._websocket_server = await websockets.serve(
            handle_websocket,
            "0.0.0.0",
            port,
        )
        self.logger.info(f"WebSocket server started on port {port}")

    # ==================== Message Processing ====================

    async def _process_messages(self) -> None:
        """Process incoming messages from queue"""
        while self._running:
            try:
                message, session = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0,
                )

                if message.is_expired():
                    self.logger.debug(f"Dropping expired message: {message.message_id}")
                    continue

                # Handle message
                try:
                    response = await self.message_handler(message, session)

                    # Send response if returned
                    if response and message.sender_id:
                        response.correlation_id = message.message_id
                        response.receiver_id = message.sender_id
                        await self.send(response)

                except Exception as e:
                    self.logger.error(f"Error handling message: {e}")

                    # Send error response
                    error_msg = message.create_error(str(e))
                    await self.send(error_msg)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Message processing error: {e}")

    async def _wait_for_response(self, correlation_id: str, timeout: float = 30.0) -> Optional[Message]:
        """Wait for a response message"""
        future = asyncio.Future()
        self._pending_responses[correlation_id] = future

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending_responses.pop(correlation_id, None)
            raise TimeoutError(f"No response received for message {correlation_id}")

    # ==================== Session Management ====================

    async def create_session(
        self,
        participant_ids: List[str],
        protocol: Optional[ProtocolType] = None,
        metadata: Optional[Dict] = None,
    ) -> Session:
        """Create a new communication session"""
        session_id = str(uuid4())
        session = Session(
            session_id=session_id,
            initiator_id=self.agent_id,
            participant_ids=set(participant_ids),
            protocol=protocol,
            metadata=metadata or {},
        )

        async with self._session_lock:
            self._sessions[session_id] = session

        self.logger.info(f"Created session {session_id} with participants: {participant_ids}")
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self._sessions.get(session_id)

    async def close_session(self, session_id: str) -> None:
        """Close a session"""
        async with self._session_lock:
            if session_id in self._sessions:
                self._sessions[session_id].state = "closed"
                del self._sessions[session_id]

    # ==================== Health Check ====================

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on communication channels"""
        health = {
            "status": "healthy",
            "p2p_connections": len([c for c in self._p2p_connections.values() if c.is_connected()]),
            "active_sessions": len([s for s in self._sessions.values() if s.is_active()]),
            "pending_responses": len(self._pending_responses),
            "queue_size": self._message_queue.qsize(),
        }

        return health

    # ==================== Message Handlers ====================

    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register a handler for a specific message type"""
        self._handlers[message_type] = handler

    def unregister_handler(self, message_type: str) -> None:
        """Unregister a message handler"""
        self._handlers.pop(message_type, None)

    # ==================== HTTP Server ====================

    async def _start_http_server(self) -> None:
        """Start HTTP REST server for agent communication"""
        from usmsb_sdk.agent_sdk.http_server import HTTPServer

        protocol_config = self.config.protocols.get(ProtocolType.HTTP)
        port = protocol_config.port if protocol_config and protocol_config.port else 5001
        host = protocol_config.host if protocol_config and protocol_config.host else "0.0.0.0"

        # Create a minimal agent-like object for the HTTP server
        class AgentAdapter:
            """Adapter to make communication manager work with HTTPServer"""
            def __init__(self, comm_manager):
                self._comm = comm_manager
                self.agent_id = comm_manager.agent_id
                self.name = comm_manager.config.name
                self.description = comm_manager.config.description
                self.version = comm_manager.config.version
                self.config = comm_manager.config
                self.state = type('State', (), {'value': 'running'})()
                self.is_running = True
                self.skills = comm_manager.config.skills
                self.capabilities = comm_manager.config.capabilities

            async def handle_message(self, message):
                """Forward to communication manager's message handler"""
                return await self._comm.message_handler(message, None)

        adapter = AgentAdapter(self)
        self._http_server = HTTPServer(
            agent=adapter,
            host=host,
            port=port,
        )

        await self._http_server.start()
        self.logger.info(f"HTTP REST server started on port {port}")

    async def start_http_server(
        self,
        host: str = "0.0.0.0",
        port: int = 5001,
        platform_url: str = "http://localhost:8000",
    ) -> bool:
        """
        Manually start HTTP REST server.

        Args:
            host: Server host address
            port: Server port
            platform_url: Platform URL for registration

        Returns:
            True if started successfully
        """
        if self._http_server:
            self.logger.warning("HTTP server already running")
            return True

        from usmsb_sdk.agent_sdk.http_server import HTTPServer

        class AgentAdapter:
            def __init__(self, comm_manager):
                self._comm = comm_manager
                self.agent_id = comm_manager.agent_id
                self.name = comm_manager.config.name
                self.description = comm_manager.config.description
                self.version = comm_manager.config.version
                self.config = comm_manager.config
                self.state = type('State', (), {'value': 'running'})()
                self.is_running = True
                self.skills = comm_manager.config.skills
                self.capabilities = comm_manager.config.capabilities

            async def handle_message(self, message):
                return await self._comm.message_handler(message, None)

        adapter = AgentAdapter(self)
        self._http_server = HTTPServer(
            agent=adapter,
            host=host,
            port=port,
            platform_url=platform_url,
        )

        success = await self._http_server.start()
        if success:
            self.logger.info(f"HTTP REST server started on {host}:{port}")
        return success

    async def stop_http_server(self) -> None:
        """Stop HTTP REST server"""
        if self._http_server:
            await self._http_server.stop()
            self._http_server = None
            self.logger.info("HTTP REST server stopped")
