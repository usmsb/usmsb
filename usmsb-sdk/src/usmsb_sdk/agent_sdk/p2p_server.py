"""
P2P Server for Agents

Provides P2P communication capability for Agents:
- Decentralized peer discovery
- Direct peer-to-peer messaging
- DHT-based agent lookup
- Seamless integration with BaseAgent
"""

import asyncio
import hashlib
import json
import logging
import socket
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from usmsb_sdk.agent_sdk.base_agent import BaseAgent

logger = logging.getLogger(__name__)


@dataclass
class PeerInfo:
    """Information about a P2P peer"""
    peer_id: str
    address: str
    port: int
    name: str = ""
    capabilities: List[str] = None
    last_seen: float = 0.0
    latency: float = 0.0

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "peer_id": self.peer_id,
            "address": self.address,
            "port": self.port,
            "name": self.name,
            "capabilities": self.capabilities,
            "last_seen": self.last_seen,
            "latency": self.latency,
        }


class DHT:
    """
    Simple Distributed Hash Table for P2P agent discovery.

    In a production environment, this would use a proper DHT implementation
    like Kademlia.
    """

    def __init__(self, local_id: str):
        self.local_id = local_id
        self._data: Dict[str, Any] = {}
        self._peers: Dict[str, PeerInfo] = {}

    def store(self, key: str, value: Any) -> None:
        """Store a value in the DHT"""
        self._data[key] = {
            "value": value,
            "timestamp": time.time(),
            "owner": self.local_id,
        }

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the DHT"""
        entry = self._data.get(key)
        if entry:
            return entry["value"]
        return None

    def register_peer(self, peer: PeerInfo) -> None:
        """Register a peer"""
        self._peers[peer.peer_id] = peer
        peer.last_seen = time.time()

    def unregister_peer(self, peer_id: str) -> None:
        """Unregister a peer"""
        self._peers.pop(peer_id, None)

    def find_peers(self, capability: str = None) -> List[PeerInfo]:
        """Find peers, optionally filtered by capability"""
        peers = list(self._peers.values())
        if capability:
            peers = [p for p in peers if capability in p.capabilities]
        return peers

    def get_peer(self, peer_id: str) -> Optional[PeerInfo]:
        """Get a specific peer"""
        return self._peers.get(peer_id)


class P2PServer:
    """
    P2P Server for Agent

    Provides P2P communication capabilities for Agents, enabling
    decentralized communication without a central server.

    Usage:
        server = P2PServer(agent, port=9001)
        await server.start()

        # Discover peers
        peers = await server.discover_peers()

        # Send message to peer
        await server.send_to_peer(peer_id, message)

    Features:
        - Peer discovery via DHT
        - Direct peer-to-peer messaging
        - Capability-based peer lookup
        - Heartbeat and health monitoring
    """

    def __init__(
        self,
        agent: "BaseAgent",
        host: str = "0.0.0.0",
        port: int = 9001,
        bootstrap_peers: List[Tuple[str, int]] = None,
    ):
        """
        Initialize P2P Server

        Args:
            agent: Agent instance
            host: Listen address
            port: Listen port
            bootstrap_peers: List of (address, port) tuples for bootstrap peers
        """
        self.agent = agent
        self.host = host
        self.port = port
        self.bootstrap_peers = bootstrap_peers or []

        # Generate peer ID from agent ID
        self.peer_id = self._generate_peer_id(agent.agent_id)

        # DHT for peer discovery
        self.dht = DHT(self.peer_id)

        # Server state
        self._server: Optional[asyncio.Server] = None
        self._running = False
        self._connections: Dict[str, asyncio.StreamWriter] = {}

        # Message handlers
        self._handlers: Dict[str, Callable] = {}
        self._register_default_handlers()

        logger.info(f"P2PServer created for {agent.name} (peer_id: {self.peer_id[:8]}...)")

    def _generate_peer_id(self, agent_id: str) -> str:
        """Generate a unique peer ID from agent ID"""
        data = f"{agent_id}:{time.time()}:{uuid.uuid4()}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _register_default_handlers(self) -> None:
        """Register default message handlers"""
        self._handlers["ping"] = self._handle_ping
        self._handlers["pong"] = self._handle_pong
        self._handlers["discover"] = self._handle_discover
        self._handlers["message"] = self._handle_message
        self._handlers["heartbeat"] = self._handle_heartbeat

    async def start(self) -> bool:
        """
        Start P2P server

        Returns:
            True if server started successfully
        """
        try:
            # Start TCP server
            self._server = await asyncio.start_server(
                self._handle_connection,
                self.host,
                self.port,
            )

            self._running = True

            # Register self in DHT
            self.dht.store(f"agent:{self.agent.agent_id}", {
                "peer_id": self.peer_id,
                "name": self.agent.name,
                "capabilities": [c.name for c in self.agent.capabilities],
                "address": self._get_local_address(),
                "port": self.port,
            })

            # Connect to bootstrap peers
            await self._connect_bootstrap_peers()

            # Start background tasks
            asyncio.create_task(self._heartbeat_loop())
            asyncio.create_task(self._peer_maintenance_loop())

            logger.info(f"P2P Server started: {self.host}:{self.port}")
            logger.info(f"   Peer ID: {self.peer_id[:16]}...")

            return True

        except Exception as e:
            logger.error(f"Failed to start P2P server: {e}")
            return False

    async def stop(self) -> None:
        """Stop P2P server"""
        self._running = False

        # Close all connections
        for peer_id, writer in self._connections.items():
            writer.close()
            try:
                await writer.wait_closed()
            except:
                pass

        self._connections.clear()

        # Close server
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        logger.info(f"P2P Server stopped for {self.agent.name}")

    def _get_local_address(self) -> str:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            address = s.getsockname()[0]
            s.close()
            return address
        except:
            return "127.0.0.1"

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle incoming P2P connection"""
        addr = writer.get_extra_info('peername')
        logger.debug(f"New P2P connection from {addr}")

        try:
            while self._running:
                # Read message length (4 bytes)
                length_data = await reader.read(4)
                if not length_data:
                    break

                length = int.from_bytes(length_data, 'big')

                # Read message data
                data = await reader.read(length)
                if not data:
                    break

                # Parse message
                try:
                    message = json.loads(data.decode('utf-8'))
                    await self._process_message(message, writer)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid message format: {e}")

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug(f"Connection error: {e}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except:
                pass

    async def _process_message(
        self,
        message: Dict[str, Any],
        writer: asyncio.StreamWriter
    ) -> None:
        """Process incoming P2P message"""
        msg_type = message.get("type", "unknown")
        sender_id = message.get("sender_id", "unknown")

        # Register connection
        if sender_id not in self._connections:
            self._connections[sender_id] = writer

        # Update peer info
        peer_info = self.dht.get_peer(sender_id)
        if peer_info:
            peer_info.last_seen = time.time()

        # Call handler
        handler = self._handlers.get(msg_type)
        if handler:
            await handler(message, writer)
        else:
            logger.warning(f"No handler for message type: {msg_type}")

    async def _handle_ping(
        self,
        message: Dict[str, Any],
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle ping message"""
        response = {
            "type": "pong",
            "sender_id": self.peer_id,
            "timestamp": time.time(),
            "original_timestamp": message.get("timestamp"),
        }
        await self._send_message(writer, response)

    async def _handle_pong(
        self,
        message: Dict[str, Any],
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle pong message"""
        original_time = message.get("original_timestamp", 0)
        latency = time.time() - original_time

        sender_id = message.get("sender_id")
        peer_info = self.dht.get_peer(sender_id)
        if peer_info:
            peer_info.latency = latency
            peer_info.last_seen = time.time()

    async def _handle_discover(
        self,
        message: Dict[str, Any],
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle peer discovery request"""
        capability = message.get("capability")
        peers = self.dht.find_peers(capability)

        response = {
            "type": "discover_response",
            "sender_id": self.peer_id,
            "peers": [p.to_dict() for p in peers],
        }
        await self._send_message(writer, response)

    async def _handle_message(
        self,
        message: Dict[str, Any],
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle generic P2P message"""
        payload = message.get("payload", {})

        # Forward to agent's message handler
        from usmsb_sdk.agent_sdk.communication import Message, MessageType

        internal_message = Message(
            type=MessageType.REQUEST,
            sender_id=message.get("sender_id", "unknown"),
            receiver_id=self.agent.agent_id,
            content=payload,
        )

        response = await self.agent.handle_message(internal_message)

        # Send response if any
        if response:
            response_msg = {
                "type": "message_response",
                "sender_id": self.peer_id,
                "original_message_id": message.get("message_id"),
                "payload": response.content if hasattr(response, 'content') else response,
            }
            await self._send_message(writer, response_msg)

    async def _handle_heartbeat(
        self,
        message: Dict[str, Any],
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle heartbeat message"""
        sender_id = message.get("sender_id")
        peer_info = self.dht.get_peer(sender_id)
        if peer_info:
            peer_info.last_seen = time.time()

        # Send heartbeat response
        response = {
            "type": "heartbeat_ack",
            "sender_id": self.peer_id,
            "timestamp": time.time(),
            "state": self.agent.state.value,
        }
        await self._send_message(writer, response)

    async def _send_message(
        self,
        writer: asyncio.StreamWriter,
        message: Dict[str, Any]
    ) -> None:
        """Send a message through a connection"""
        try:
            data = json.dumps(message).encode('utf-8')
            length = len(data).to_bytes(4, 'big')
            writer.write(length + data)
            await writer.drain()
        except Exception as e:
            logger.debug(f"Failed to send message: {e}")

    async def send_to_peer(
        self,
        peer_id: str,
        message: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Send a message to a specific peer

        Args:
            peer_id: Target peer ID
            message: Message to send
            timeout: Response timeout

        Returns:
            Response from peer, or None
        """
        peer_info = self.dht.get_peer(peer_id)
        if not peer_info:
            logger.warning(f"Peer not found: {peer_id}")
            return None

        # Check if we have an existing connection
        writer = self._connections.get(peer_id)

        if not writer:
            # Create new connection
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(peer_info.address, peer_info.port),
                    timeout=5.0
                )
                self._connections[peer_id] = writer
            except Exception as e:
                logger.warning(f"Failed to connect to peer {peer_id}: {e}")
                return None

        # Add message metadata
        message["sender_id"] = self.peer_id
        message["timestamp"] = time.time()
        message["message_id"] = str(uuid.uuid4())

        await self._send_message(writer, message)
        return None  # Response will be handled asynchronously

    async def discover_peers(
        self,
        capability: str = None,
        timeout: float = 10.0
    ) -> List[PeerInfo]:
        """
        Discover peers in the network

        Args:
            capability: Optional capability filter
            timeout: Discovery timeout

        Returns:
            List of discovered peers
        """
        # First, check local DHT
        local_peers = self.dht.find_peers(capability)

        # Query connected peers for more peers
        discover_msg = {
            "type": "discover",
            "capability": capability,
        }

        for peer_id, writer in list(self._connections.items()):
            try:
                await self._send_message(writer, discover_msg)
            except:
                pass

        return local_peers

    async def _connect_bootstrap_peers(self) -> None:
        """Connect to bootstrap peers"""
        for address, port in self.bootstrap_peers:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(address, port),
                    timeout=5.0
                )

                # Send ping to register
                peer_id = f"bootstrap_{address}_{port}"
                self._connections[peer_id] = writer

                ping_msg = {
                    "type": "ping",
                    "sender_id": self.peer_id,
                    "timestamp": time.time(),
                }
                await self._send_message(writer, ping_msg)

                logger.info(f"Connected to bootstrap peer: {address}:{port}")

            except Exception as e:
                logger.debug(f"Failed to connect to bootstrap peer {address}:{port}: {e}")

    async def _heartbeat_loop(self) -> None:
        """Periodic heartbeat to maintain connections"""
        while self._running:
            try:
                await asyncio.sleep(30)  # Heartbeat every 30 seconds

                heartbeat_msg = {
                    "type": "heartbeat",
                    "sender_id": self.peer_id,
                    "timestamp": time.time(),
                    "state": self.agent.state.value,
                }

                for peer_id, writer in list(self._connections.items()):
                    try:
                        await self._send_message(writer, heartbeat_msg)
                    except:
                        # Remove broken connection
                        self._connections.pop(peer_id, None)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Heartbeat loop error: {e}")

    async def _peer_maintenance_loop(self) -> None:
        """Periodic peer maintenance (cleanup stale peers)"""
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute

                # Remove stale peers (not seen for 5 minutes)
                current_time = time.time()
                stale_threshold = 300  # 5 minutes

                stale_peers = [
                    peer_id for peer_id, peer in self.dht._peers.items()
                    if current_time - peer.last_seen > stale_threshold
                ]

                for peer_id in stale_peers:
                    self.dht.unregister_peer(peer_id)
                    self._connections.pop(peer_id, None)
                    logger.debug(f"Removed stale peer: {peer_id}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Peer maintenance error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get P2P server statistics"""
        return {
            "peer_id": self.peer_id,
            "address": self._get_local_address(),
            "port": self.port,
            "running": self._running,
            "connected_peers": len(self._connections),
            "known_peers": len(self.dht._peers),
            "dht_entries": len(self.dht._data),
        }


async def run_agent_with_p2p(
    agent: "BaseAgent",
    p2p_port: int = 9001,
    bootstrap_peers: List[Tuple[str, int]] = None,
) -> None:
    """
    Run Agent with P2P server

    Args:
        agent: Agent instance
        p2p_port: P2P listen port
        bootstrap_peers: List of (address, port) tuples for bootstrap peers
    """
    # Create P2P server
    p2p_server = P2PServer(
        agent=agent,
        port=p2p_port,
        bootstrap_peers=bootstrap_peers,
    )

    try:
        # Start agent
        await agent.start()

        # Start P2P server
        await p2p_server.start()

        logger.info(f"{agent.name} running with P2P on port {p2p_port}")
        logger.info(f"   Peer ID: {p2p_server.peer_id[:16]}...")

        # Wait for stop signal
        while agent.is_running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info(f"Received interrupt signal for {agent.name}")
    finally:
        await p2p_server.stop()
        await agent.stop()


__all__ = [
    "P2PServer",
    "PeerInfo",
    "DHT",
    "run_agent_with_p2p",
]
