"""
P2P Protocol Handler

This module provides the handler for Peer-to-Peer (P2P) protocol,
enabling decentralized communication between agents.
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

from usmsb_sdk.protocol.base import (
    BaseProtocolHandler,
    ProtocolConfig,
    ExternalAgentStatus,
    SkillDefinition,
)


logger = logging.getLogger(__name__)


@dataclass
class P2PNodeInfo:
    """Information about a P2P node."""
    node_id: str
    address: str
    port: int
    name: str = ""
    public_key: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    status: str = "unknown"
    last_seen: float = 0.0
    reputation: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "address": self.address,
            "port": self.port,
            "name": self.name,
            "public_key": self.public_key,
            "capabilities": self.capabilities,
            "skills": self.skills,
            "status": self.status,
            "last_seen": self.last_seen,
            "reputation": self.reputation,
            "metadata": self.metadata,
        }


@dataclass
class P2PMessage:
    """P2P protocol message."""
    message_id: str
    message_type: str
    sender_id: str
    receiver_id: Optional[str]  # None for broadcast
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    ttl: int = 5  # Hop limit for broadcast
    signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "message_type": self.message_type,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "signature": self.signature,
        }


@dataclass
class P2PSkillRequest:
    """P2P skill execution request."""
    request_id: str
    skill_name: str
    arguments: Dict[str, Any]
    timeout: float = 60.0
    priority: int = 0
    broadcast: bool = False  # Whether to broadcast to multiple nodes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "skill_name": self.skill_name,
            "arguments": self.arguments,
            "timeout": self.timeout,
            "priority": self.priority,
            "broadcast": self.broadcast,
        }


@dataclass
class P2PSkillResponse:
    """P2P skill execution response."""
    request_id: str
    node_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "node_id": self.node_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
        }


@dataclass
class P2PDHTEntry:
    """Distributed Hash Table entry."""
    key: str
    value: Any
    owner_id: str
    timestamp: float
    ttl: int = 3600
    replication: int = 3


class P2PHandler(BaseProtocolHandler):
    """
    Handler for P2P (Peer-to-Peer) protocol.

    This handler implements decentralized communication between
    agents in a P2P network.

    Features:
    - Peer discovery and management
    - Direct peer communication
    - Distributed skill execution
    - Basic DHT for service discovery
    - Node reputation tracking
    """

    MESSAGE_TYPES = {
        "ping": "Ping for node discovery",
        "pong": "Pong response",
        "discover": "Request peer list",
        "discover_response": "Response with peer list",
        "skill_request": "Request skill execution",
        "skill_response": "Response from skill execution",
        "broadcast": "Broadcast message",
        "dht_store": "Store in DHT",
        "dht_lookup": "Lookup in DHT",
        "dht_response": "DHT lookup response",
    }

    def __init__(
        self,
        config: Optional[ProtocolConfig] = None,
        node_id: Optional[str] = None,
        node_name: str = "",
        port: int = 0,
    ):
        """
        Initialize the P2P handler.

        Args:
            config: Protocol configuration.
            node_id: Unique node identifier. If None, generates one.
            node_name: Human-readable node name.
            port: Local port for P2P communication.
        """
        super().__init__(config)
        self._node_id = node_id or self._generate_node_id()
        self._node_name = node_name or f"Node-{self._node_id[:8]}"
        self._port = port
        self._peers: Dict[str, P2PNodeInfo] = {}
        self._dht: Dict[str, P2PDHTEntry] = {}
        self._seen_messages: Set[str] = set()  # For deduplication
        self._p2p_message_handlers: Dict[str, Callable] = {}

        # Register default message handlers
        self._register_default_handlers()

        logger.info(f"P2PHandler initialized: node_id={self._node_id}")

    def _generate_node_id(self) -> str:
        """Generate a unique node ID."""
        data = f"{uuid.uuid4()}{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _register_default_handlers(self) -> None:
        """Register default P2P message handlers."""
        self._p2p_message_handlers["ping"] = self._handle_ping
        self._p2p_message_handlers["discover"] = self._handle_discover
        self._p2p_message_handlers["skill_request"] = self._handle_skill_request
        self._p2p_message_handlers["dht_lookup"] = self._handle_dht_lookup

    # ========== Protocol-Specific Implementation ==========

    async def _do_connect(self, endpoint: str) -> bool:
        """
        Connect to the P2P network.

        Args:
            endpoint: Bootstrap node address (host:port).

        Returns:
            True if connection successful.
        """
        try:
            # Parse bootstrap endpoint
            if ":" in endpoint:
                host, port = endpoint.rsplit(":", 1)
                port = int(port)
            else:
                host = endpoint
                port = 9000  # Default P2P port

            # Start local P2P server (in real implementation)
            logger.info(f"P2P connecting to bootstrap node: {host}:{port}")

            # Add bootstrap node as peer
            bootstrap_node = P2PNodeInfo(
                node_id="bootstrap",
                address=host,
                port=port,
                name="Bootstrap Node",
                status="online",
                last_seen=time.time(),
            )
            self._peers["bootstrap"] = bootstrap_node

            # Perform peer discovery
            await self._discover_peers()

            return True

        except Exception as e:
            logger.error(f"P2P connection error: {e}")
            return False

    async def _do_disconnect(self) -> None:
        """Disconnect from the P2P network."""
        # Notify peers of disconnection
        for peer_id in list(self._peers.keys()):
            await self._send_to_peer(peer_id, "goodbye", {})

        self._peers.clear()
        self._dht.clear()
        self._seen_messages.clear()

        logger.info("P2P disconnected from network")

    async def _do_call_skill(
        self,
        skill_name: str,
        arguments: Dict[str, Any],
        timeout: float,
    ) -> Any:
        """
        Execute a skill on a P2P node.

        Args:
            skill_name: Name of the skill to execute.
            arguments: Arguments for the skill.
            timeout: Timeout for execution.

        Returns:
            Result from the skill execution.
        """
        # Find peers with the requested skill
        capable_peers = [
            peer for peer in self._peers.values()
            if skill_name in peer.skills and peer.status == "online"
        ]

        if not capable_peers:
            # Broadcast skill request to discover capable nodes
            await self._broadcast("skill_discover", {"skill": skill_name})
            await asyncio.sleep(0.5)

            capable_peers = [
                peer for peer in self._peers.values()
                if skill_name in peer.skills and peer.status == "online"
            ]

        if not capable_peers:
            raise Exception(f"No peers available with skill: {skill_name}")

        # Select best peer (highest reputation)
        best_peer = max(capable_peers, key=lambda p: p.reputation)

        # Send skill request
        request = P2PSkillRequest(
            request_id=str(uuid.uuid4()),
            skill_name=skill_name,
            arguments=arguments,
            timeout=timeout,
        )

        response = await self._send_skill_request(best_peer.node_id, request)

        if response.success:
            return response.result
        else:
            raise Exception(response.error or "Skill execution failed")

    async def _do_discover_skills(self) -> List[SkillDefinition]:
        """
        Discover skills from P2P network.

        Returns:
            List of discovered skills.
        """
        skills: Dict[str, SkillDefinition] = {}

        # Collect skills from all peers
        for peer in self._peers.values():
            for skill_name in peer.skills:
                if skill_name not in skills:
                    skills[skill_name] = SkillDefinition(
                        skill_id=f"p2p-{skill_name}",
                        name=skill_name,
                        description=f"P2P skill: {skill_name}",
                        category="p2p",
                        metadata={"provider_node": peer.node_id},
                    )

        # Also query network for more skills
        await self._broadcast("skill_list_request", {})

        return list(skills.values())

    async def _do_check_status(self) -> ExternalAgentStatus:
        """
        Check P2P network status.

        Returns:
            Current network status.
        """
        online_peers = sum(
            1 for peer in self._peers.values()
            if peer.status == "online"
        )

        if online_peers == 0:
            return ExternalAgentStatus.OFFLINE
        elif online_peers < 3:
            return ExternalAgentStatus.BUSY
        else:
            return ExternalAgentStatus.ONLINE

    # ========== P2P-Specific Methods ==========

    async def _discover_peers(self) -> None:
        """Discover peers in the P2P network."""
        for peer_id, peer in list(self._peers.items()):
            if peer.status == "online":
                try:
                    await self._send_to_peer(
                        peer_id,
                        "discover",
                        {"node_id": self._node_id},
                    )
                except Exception as e:
                    logger.warning(f"Failed to discover from peer {peer_id}: {e}")

    async def _send_to_peer(
        self,
        peer_id: str,
        message_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        Send a message to a specific peer.

        Args:
            peer_id: Target peer ID.
            message_type: Type of message.
            payload: Message payload.
        """
        if peer_id not in self._peers:
            raise Exception(f"Unknown peer: {peer_id}")

        peer = self._peers[peer_id]

        message = P2PMessage(
            message_id=str(uuid.uuid4()),
            message_type=message_type,
            sender_id=self._node_id,
            receiver_id=peer_id,
            payload=payload,
        )

        logger.debug(f"P2P sending {message_type} to peer {peer_id}")

        # In real implementation, send via TCP/UDP
        await asyncio.sleep(0.01)

        # Update peer activity
        peer.last_seen = time.time()

    async def _broadcast(
        self,
        message_type: str,
        payload: Dict[str, Any],
        exclude_peers: Optional[Set[str]] = None,
    ) -> None:
        """
        Broadcast a message to all peers.

        Args:
            message_type: Type of message.
            payload: Message payload.
            exclude_peers: Set of peer IDs to exclude from broadcast.
        """
        exclude = exclude_peers or set()

        message = P2PMessage(
            message_id=str(uuid.uuid4()),
            message_type=message_type,
            sender_id=self._node_id,
            receiver_id=None,  # Broadcast
            payload=payload,
        )

        logger.debug(f"P2P broadcasting {message_type}")

        for peer_id, peer in self._peers.items():
            if peer_id not in exclude and peer.status == "online":
                try:
                    await self._send_to_peer(peer_id, message_type, payload)
                except Exception as e:
                    logger.warning(f"Broadcast failed to peer {peer_id}: {e}")

    async def _send_skill_request(
        self,
        peer_id: str,
        request: P2PSkillRequest,
    ) -> P2PSkillResponse:
        """
        Send a skill execution request to a peer.

        Args:
            peer_id: Target peer ID.
            request: Skill request.

        Returns:
            Skill execution response.
        """
        await self._send_to_peer(
            peer_id,
            "skill_request",
            request.to_dict(),
        )

        # Wait for response (simplified)
        await asyncio.sleep(0.2)

        # Simulated response
        return P2PSkillResponse(
            request_id=request.request_id,
            node_id=peer_id,
            success=True,
            result={"output": f"Executed {request.skill_name} on peer {peer_id}"},
            execution_time=0.1,
        )

    # ========== Message Handlers ==========

    async def _handle_ping(
        self,
        message: P2PMessage,
        sender: P2PNodeInfo,
    ) -> Optional[P2PMessage]:
        """Handle ping message."""
        # Respond with pong
        return P2PMessage(
            message_id=str(uuid.uuid4()),
            message_type="pong",
            sender_id=self._node_id,
            receiver_id=sender.node_id,
            payload={"timestamp": time.time()},
        )

    async def _handle_discover(
        self,
        message: P2PMessage,
        sender: P2PNodeInfo,
    ) -> Optional[P2PMessage]:
        """Handle peer discovery request."""
        peer_list = [
            {
                "node_id": peer.node_id,
                "address": peer.address,
                "port": peer.port,
                "skills": peer.skills,
            }
            for peer in self._peers.values()
            if peer.status == "online"
        ]

        return P2PMessage(
            message_id=str(uuid.uuid4()),
            message_type="discover_response",
            sender_id=self._node_id,
            receiver_id=sender.node_id,
            payload={"peers": peer_list},
        )

    async def _handle_skill_request(
        self,
        message: P2PMessage,
        sender: P2PNodeInfo,
    ) -> Optional[P2PMessage]:
        """Handle incoming skill request."""
        # In real implementation, execute the skill locally
        payload = message.payload
        skill_name = payload.get("skill_name")

        logger.info(f"P2P received skill request: {skill_name} from {sender.node_id}")

        # Simulated skill execution
        return P2PMessage(
            message_id=str(uuid.uuid4()),
            message_type="skill_response",
            sender_id=self._node_id,
            receiver_id=sender.node_id,
            payload={
                "request_id": payload.get("request_id"),
                "success": True,
                "result": {"output": f"Executed {skill_name}"},
            },
        )

    async def _handle_dht_lookup(
        self,
        message: P2PMessage,
        sender: P2PNodeInfo,
    ) -> Optional[P2PMessage]:
        """Handle DHT lookup request."""
        key = message.payload.get("key")

        if key in self._dht:
            entry = self._dht[key]
            return P2PMessage(
                message_id=str(uuid.uuid4()),
                message_type="dht_response",
                sender_id=self._node_id,
                receiver_id=sender.node_id,
                payload={
                    "key": key,
                    "value": entry.value,
                    "owner_id": entry.owner_id,
                },
            )

        return None

    # ========== DHT Operations ==========

    async def dht_store(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Store a value in the DHT.

        Args:
            key: Key to store.
            value: Value to store.
            ttl: Time-to-live in seconds.

        Returns:
            True if stored successfully.
        """
        entry = P2PDHTEntry(
            key=key,
            value=value,
            owner_id=self._node_id,
            timestamp=time.time(),
            ttl=ttl,
        )

        self._dht[key] = entry

        # Replicate to peers
        await self._broadcast(
            "dht_store",
            {"key": key, "value": value, "ttl": ttl},
        )

        return True

    async def dht_lookup(self, key: str, timeout: float = 10.0) -> Optional[Any]:
        """
        Look up a value in the DHT.

        Args:
            key: Key to look up.
            timeout: Lookup timeout.

        Returns:
            Value if found, None otherwise.
        """
        # Check local DHT first
        if key in self._dht:
            entry = self._dht[key]
            if time.time() - entry.timestamp < entry.ttl:
                return entry.value

        # Query network
        await self._broadcast("dht_lookup", {"key": key})

        # Wait for response (simplified)
        await asyncio.sleep(0.5)

        # Check again
        if key in self._dht:
            return self._dht[key].value

        return None

    # ========== Utility Methods ==========

    def get_peers(self) -> List[P2PNodeInfo]:
        """Get list of known peers."""
        return list(self._peers.values())

    def get_peer(self, peer_id: str) -> Optional[P2PNodeInfo]:
        """Get a specific peer by ID."""
        return self._peers.get(peer_id)

    def get_node_id(self) -> str:
        """Get local node ID."""
        return self._node_id

    def get_network_stats(self) -> Dict[str, Any]:
        """Get P2P network statistics."""
        return {
            "node_id": self._node_id,
            "node_name": self._node_name,
            "total_peers": len(self._peers),
            "online_peers": sum(
                1 for p in self._peers.values() if p.status == "online"
            ),
            "dht_entries": len(self._dht),
            "skills_available": len(set(
                skill for peer in self._peers.values()
                for skill in peer.skills
            )),
        }
