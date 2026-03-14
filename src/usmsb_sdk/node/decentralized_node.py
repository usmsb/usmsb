"""
Decentralized P2P Node Architecture

This module implements a fully decentralized, distributed node architecture
where each node:
- Auto-registers as a service provider
- Participates in service discovery
- Can act as both client and server
- Contributes to the network's resilience

Key components:
- P2P networking layer
- Distributed service registry
- Service discovery protocol
- Node identity and reputation
- Distributed state management
"""

import asyncio
import hashlib
import json
import logging
import socket
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class NodeStatus(StrEnum):
    """Status of a node in the network."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    BUSY = "busy"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class ServiceType(StrEnum):
    """Types of services a node can provide."""
    LLM_INFERENCE = "llm_inference"
    AGENT_HOSTING = "agent_hosting"
    COMPUTE = "compute"
    STORAGE = "storage"
    BLOCKCHAIN = "blockchain"
    ORACLE = "oracle"
    SKILL_PROVIDER = "skill_provider"
    COORDINATION = "coordination"
    GATEWAY = "gateway"


@dataclass
class NodeIdentity:
    """Identity of a node in the network."""
    node_id: str
    public_key: str
    address: str  # Network address
    port: int
    created_at: float = field(default_factory=time.time)
    reputation: float = 1.0
    stake: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "public_key": self.public_key,
            "address": self.address,
            "port": self.port,
            "created_at": self.created_at,
            "reputation": self.reputation,
            "stake": self.stake,
            "metadata": self.metadata,
        }


@dataclass
class ServiceEndpoint:
    """Endpoint for a service provided by a node."""
    service_id: str
    service_type: ServiceType
    provider_node: str
    endpoint: str
    capabilities: list[str] = field(default_factory=list)
    load: float = 0.0
    max_capacity: float = 100.0
    cost_per_request: float = 0.001
    avg_latency: float = 0.0
    uptime: float = 1.0
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_available(self) -> bool:
        """Check if service is available."""
        return self.load < self.max_capacity and self.uptime > 0.9

    def to_dict(self) -> dict[str, Any]:
        return {
            "service_id": self.service_id,
            "service_type": self.service_type.value,
            "provider_node": self.provider_node,
            "endpoint": self.endpoint,
            "capabilities": self.capabilities,
            "load": self.load,
            "max_capacity": self.max_capacity,
            "cost_per_request": self.cost_per_request,
            "avg_latency": self.avg_latency,
            "uptime": self.uptime,
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
        }


@dataclass
class ServiceRequest:
    """Request for a service."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    service_type: ServiceType = ServiceType.LLM_INFERENCE
    requester_node: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    max_cost: float = 1.0
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    timeout: float = 30.0


@dataclass
class ServiceResponse:
    """Response from a service."""
    request_id: str = ""
    provider_node: str = ""
    success: bool = False
    result: Any = None
    error: str | None = None
    cost: float = 0.0
    latency: float = 0.0
    timestamp: float = field(default_factory=time.time)


class DistributedServiceRegistry:
    """
    Distributed service registry using gossip protocol.

    Each node maintains a local copy of the registry and
    synchronizes with peers through gossip.
    """

    GOSSIP_INTERVAL = 5.0  # seconds
    REGISTRY_TTL = 300.0   # 5 minutes

    def __init__(self, node_id: str):
        self.node_id = node_id
        self._services: dict[str, ServiceEndpoint] = {}
        self._nodes: dict[str, NodeIdentity] = {}
        self._service_by_type: dict[ServiceType, set[str]] = {
            st: set() for st in ServiceType
        }
        self._gossip_task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        """Start the gossip protocol."""
        self._running = True
        self._gossip_task = asyncio.create_task(self._gossip_loop())
        logger.info(f"Service registry started on {self.node_id}")

    async def stop(self) -> None:
        """Stop the gossip protocol."""
        self._running = False
        if self._gossip_task:
            self._gossip_task.cancel()

    async def register_service(self, service: ServiceEndpoint) -> None:
        """Register a service."""
        self._services[service.service_id] = service
        self._service_by_type[service.service_type].add(service.service_id)
        logger.info(f"Registered service: {service.service_id} ({service.service_type.value})")

    async def unregister_service(self, service_id: str) -> bool:
        """Unregister a service."""
        if service_id in self._services:
            service = self._services.pop(service_id)
            self._service_by_type[service.service_type].discard(service_id)
            return True
        return False

    async def discover_services(
        self,
        service_type: ServiceType | None = None,
        capabilities: list[str] | None = None,
        min_reputation: float = 0.0,
        max_cost: float | None = None,
    ) -> list[ServiceEndpoint]:
        """Discover available services."""
        candidates = []

        # Get services by type
        if service_type:
            service_ids = self._service_by_type.get(service_type, set())
            candidates = [self._services[sid] for sid in service_ids if sid in self._services]
        else:
            candidates = list(self._services.values())

        # Filter by availability
        candidates = [s for s in candidates if s.is_available()]

        # Filter by capabilities
        if capabilities:
            candidates = [
                s for s in candidates
                if all(cap in s.capabilities for cap in capabilities)
            ]

        # Filter by cost
        if max_cost is not None:
            candidates = [s for s in candidates if s.cost_per_request <= max_cost]

        # Filter by reputation
        if min_reputation > 0:
            candidates = [
                s for s in candidates
                if self._nodes.get(s.provider_node, NodeIdentity("", "", "", 0)).reputation >= min_reputation
            ]

        # Sort by load and latency
        candidates.sort(key=lambda s: (s.load / s.max_capacity, s.avg_latency))

        return candidates

    async def update_heartbeat(self, service_id: str) -> None:
        """Update service heartbeat."""
        if service_id in self._services:
            self._services[service_id].last_heartbeat = time.time()

    async def cleanup_stale_services(self) -> int:
        """Remove services that haven't sent heartbeat."""
        now = time.time()
        stale = [
            sid for sid, s in self._services.items()
            if now - s.last_heartbeat > self.REGISTRY_TTL
        ]
        for sid in stale:
            await self.unregister_service(sid)
        return len(stale)

    async def register_node(self, node: NodeIdentity) -> None:
        """Register a node."""
        self._nodes[node.node_id] = node

    async def get_node(self, node_id: str) -> NodeIdentity | None:
        """Get node by ID."""
        return self._nodes.get(node_id)

    async def get_registry_state(self) -> dict[str, Any]:
        """Get current registry state for gossip."""
        return {
            "services": {sid: s.to_dict() for sid, s in self._services.items()},
            "nodes": {nid: n.to_dict() for nid, n in self._nodes.items()},
            "timestamp": time.time(),
        }

    async def merge_registry_state(self, state: dict[str, Any]) -> None:
        """Merge received registry state (gossip)."""
        # Merge services
        for sid, s_data in state.get("services", {}).items():
            if sid not in self._services or s_data["last_heartbeat"] > self._services[sid].last_heartbeat:
                service = ServiceEndpoint(
                    service_id=s_data["service_id"],
                    service_type=ServiceType(s_data["service_type"]),
                    provider_node=s_data["provider_node"],
                    endpoint=s_data["endpoint"],
                    capabilities=s_data.get("capabilities", []),
                    load=s_data.get("load", 0),
                    max_capacity=s_data.get("max_capacity", 100),
                    cost_per_request=s_data.get("cost_per_request", 0.001),
                    avg_latency=s_data.get("avg_latency", 0),
                    uptime=s_data.get("uptime", 1.0),
                    last_heartbeat=s_data.get("last_heartbeat", time.time()),
                )
                await self.register_service(service)

        # Merge nodes
        for _nid, n_data in state.get("nodes", {}).items():
            node = NodeIdentity(
                node_id=n_data["node_id"],
                public_key=n_data["public_key"],
                address=n_data["address"],
                port=n_data["port"],
                reputation=n_data.get("reputation", 1.0),
                stake=n_data.get("stake", 0),
            )
            await self.register_node(node)

    async def _gossip_loop(self) -> None:
        """Gossip registry state to peers."""
        while self._running:
            try:
                await asyncio.sleep(self.GOSSIP_INTERVAL)
                # Cleanup stale services
                stale_count = await self.cleanup_stale_services()
                if stale_count > 0:
                    logger.info(f"Cleaned up {stale_count} stale services")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in gossip loop: {e}")


class P2PNode:
    """
    Decentralized P2P Node.

    Each node:
    - Auto-discovers peers
    - Registers services it provides
    - Discovers and consumes services from other nodes
    - Participates in distributed consensus
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.node_id = self._generate_node_id()
        self.status = NodeStatus.INITIALIZING

        # Generate identity
        self.identity = NodeIdentity(
            node_id=self.node_id,
            public_key=self._generate_public_key(),
            address=self.config.get("address", self._get_local_ip()),
            port=self.config.get("port", 8080),
            metadata=self.config.get("metadata", {}),
        )

        # Service registry
        self.registry = DistributedServiceRegistry(self.node_id)

        # Local services
        self._local_services: dict[str, ServiceEndpoint] = {}
        self._service_handlers: dict[str, Callable] = {}

        # Peer management
        self._peers: dict[str, NodeIdentity] = {}
        self._bootstrap_peers: list[str] = self.config.get("bootstrap_peers", [])

        # Client capabilities
        self._pending_requests: dict[str, asyncio.Future] = {}

        # Server
        self._server: asyncio.Server | None = None
        self._running = False

    def _generate_node_id(self) -> str:
        """Generate unique node ID."""
        return "node_" + hashlib.sha256(f"{time.time()}{uuid.uuid4()}".encode()).hexdigest()[:16]

    def _generate_public_key(self) -> str:
        """Generate public key for node identity."""
        return hashlib.sha256(f"{self.node_id}_public".encode()).hexdigest()

    def _get_local_ip(self) -> str:
        """Get local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    async def start(self) -> bool:
        """Start the P2P node."""
        try:
            self.status = NodeStatus.INITIALIZING

            # Start service registry
            await self.registry.start()

            # Register self
            await self.registry.register_node(self.identity)

            # Start TCP server
            self._server = await asyncio.start_server(
                self._handle_connection,
                self.identity.address,
                self.identity.port,
            )

            self._running = True

            # Start background tasks
            asyncio.create_task(self._server_loop())
            asyncio.create_task(self._heartbeat_loop())

            # Connect to bootstrap peers
            await self._connect_to_bootstrap_peers()

            # Auto-register local services
            await self._auto_register_services()

            self.status = NodeStatus.ACTIVE
            logger.info(f"P2P Node started: {self.node_id} at {self.identity.address}:{self.identity.port}")

            return True

        except Exception as e:
            logger.error(f"Failed to start P2P node: {e}")
            self.status = NodeStatus.OFFLINE
            return False

    async def stop(self) -> None:
        """Stop the P2P node."""
        self._running = False

        if self._server:
            self._server.close()
            await self._server.wait_closed()

        await self.registry.stop()
        self.status = NodeStatus.OFFLINE
        logger.info(f"P2P Node stopped: {self.node_id}")

    async def _server_loop(self) -> None:
        """Server loop for accepting connections."""
        async with self._server:
            await self._server.serve_forever()

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle incoming connection."""
        try:
            data = await reader.read(1024 * 1024)  # Max 1MB
            message = json.loads(data.decode())

            response = await self._handle_message(message)

            writer.write(json.dumps(response).encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        except Exception as e:
            logger.error(f"Error handling connection: {e}")

    async def _handle_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Handle incoming message."""
        msg_type = message.get("type")

        if msg_type == "service_request":
            return await self._handle_service_request(message)
        elif msg_type == "registry_gossip":
            await self.registry.merge_registry_state(message.get("registry", {}))
            return {"type": "gossip_ack", "node_id": self.node_id}
        elif msg_type == "ping":
            return {"type": "pong", "node_id": self.node_id, "status": self.status.value}
        elif msg_type == "discover":
            services = await self.registry.discover_services(
                ServiceType(message.get("service_type")) if message.get("service_type") else None
            )
            return {"type": "discover_response", "services": [s.to_dict() for s in services]}
        else:
            return {"type": "error", "message": f"Unknown message type: {msg_type}"}

    async def _handle_service_request(self, message: dict[str, Any]) -> dict[str, Any]:
        """Handle service request."""
        service_id = message.get("service_id")
        request_id = message.get("request_id")
        payload = message.get("payload", {})

        handler = self._service_handlers.get(service_id)
        if not handler:
            return {
                "type": "service_response",
                "request_id": request_id,
                "success": False,
                "error": "Service not found",
            }

        try:
            start_time = time.time()
            result = await handler(payload)
            latency = time.time() - start_time

            # Update service metrics
            if service_id in self._local_services:
                service = self._local_services[service_id]
                service.avg_latency = (service.avg_latency + latency) / 2

            return {
                "type": "service_response",
                "request_id": request_id,
                "success": True,
                "result": result,
                "latency": latency,
            }

        except Exception as e:
            return {
                "type": "service_response",
                "request_id": request_id,
                "success": False,
                "error": str(e),
            }

    async def _connect_to_bootstrap_peers(self) -> None:
        """Connect to bootstrap peers."""
        for peer_addr in self._bootstrap_peers:
            try:
                # Parse address
                host, port = peer_addr.rsplit(":", 1)
                port = int(port)

                # Ping peer
                reader, writer = await asyncio.open_connection(host, port)
                writer.write(json.dumps({"type": "ping"}).encode())
                await writer.drain()

                data = await reader.read(4096)
                response = json.loads(data.decode())

                if response.get("type") == "pong":
                    node_id = response.get("node_id")
                    self._peers[node_id] = NodeIdentity(
                        node_id=node_id,
                        public_key="",
                        address=host,
                        port=port,
                    )
                    logger.info(f"Connected to peer: {node_id}")

                writer.close()
                await writer.wait_closed()

            except Exception as e:
                logger.warning(f"Failed to connect to bootstrap peer {peer_addr}: {e}")

    async def _auto_register_services(self) -> None:
        """Auto-register services this node provides."""
        # Auto-register based on capabilities
        capabilities = self.config.get("capabilities", [])

        if "llm" in capabilities:
            await self.register_service(
                service_type=ServiceType.LLM_INFERENCE,
                capabilities=["text_generation", "embeddings", "reasoning"],
                endpoint=f"http://{self.identity.address}:{self.identity.port}/llm",
            )

        if "agent_hosting" in capabilities:
            await self.register_service(
                service_type=ServiceType.AGENT_HOSTING,
                capabilities=["create_agent", "run_agent", "agent_communication"],
                endpoint=f"http://{self.identity.address}:{self.identity.port}/agents",
            )

        if "compute" in capabilities:
            await self.register_service(
                service_type=ServiceType.COMPUTE,
                capabilities=["cpu", "gpu", "distributed"],
                endpoint=f"http://{self.identity.address}:{self.identity.port}/compute",
            )

    async def _heartbeat_loop(self) -> None:
        """Send heartbeats for local services."""
        while self._running:
            try:
                for service_id in self._local_services:
                    await self.registry.update_heartbeat(service_id)
                await asyncio.sleep(10.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    # ============== Public API ==============

    async def register_service(
        self,
        service_type: ServiceType,
        capabilities: list[str],
        endpoint: str,
        cost_per_request: float = 0.001,
        max_capacity: float = 100.0,
        handler: Callable | None = None,
    ) -> ServiceEndpoint:
        """Register a service provided by this node."""
        service_id = f"{self.node_id}_{service_type.value}"

        service = ServiceEndpoint(
            service_id=service_id,
            service_type=service_type,
            provider_node=self.node_id,
            endpoint=endpoint,
            capabilities=capabilities,
            cost_per_request=cost_per_request,
            max_capacity=max_capacity,
        )

        self._local_services[service_id] = service
        if handler:
            self._service_handlers[service_id] = handler

        await self.registry.register_service(service)

        return service

    async def discover_services(
        self,
        service_type: ServiceType | None = None,
        capabilities: list[str] | None = None,
    ) -> list[ServiceEndpoint]:
        """Discover services in the network."""
        return await self.registry.discover_services(
            service_type=service_type,
            capabilities=capabilities,
        )

    async def request_service(
        self,
        service_type: ServiceType,
        payload: dict[str, Any],
        max_cost: float = 1.0,
        timeout: float = 30.0,
    ) -> ServiceResponse:
        """Request a service from the network."""
        # Discover available services
        services = await self.registry.discover_services(
            service_type=service_type,
            max_cost=max_cost,
        )

        if not services:
            return ServiceResponse(
                success=False,
                error="No available services",
            )

        # Select best service (lowest load)
        service = services[0]

        # Create request
        request = ServiceRequest(
            service_type=service_type,
            requester_node=self.node_id,
            payload=payload,
            max_cost=max_cost,
            timeout=timeout,
        )

        # Send request to provider
        try:
            reader, writer = await asyncio.open_connection(
                service.endpoint.split("://")[1].split("/")[0].split(":")[0],
                int(service.endpoint.split(":")[-1].split("/")[0]),
            )

            message = {
                "type": "service_request",
                "service_id": service.service_id,
                "request_id": request.request_id,
                "payload": payload,
            }

            writer.write(json.dumps(message).encode())
            await writer.drain()

            data = await asyncio.wait_for(reader.read(1024 * 1024), timeout=timeout)
            response_data = json.loads(data.decode())

            writer.close()
            await writer.wait_closed()

            return ServiceResponse(
                request_id=request.request_id,
                provider_node=service.provider_node,
                success=response_data.get("success", False),
                result=response_data.get("result"),
                error=response_data.get("error"),
                latency=response_data.get("latency", 0),
            )

        except TimeoutError:
            return ServiceResponse(
                request_id=request.request_id,
                success=False,
                error="Request timeout",
            )
        except Exception as e:
            return ServiceResponse(
                request_id=request.request_id,
                success=False,
                error=str(e),
            )

    async def get_node_info(self) -> dict[str, Any]:
        """Get information about this node."""
        return {
            "node_id": self.node_id,
            "identity": self.identity.to_dict(),
            "status": self.status.value,
            "local_services": len(self._local_services),
            "known_peers": len(self._peers),
            "registry_services": len(self.registry._services),
        }


class DecentralizedPlatform:
    """
    Main entry point for the decentralized AI Civilization Platform.

    Orchestrates:
    - P2P node
    - Service discovery
    - Agent management
    - Blockchain integration
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.node = P2PNode(self.config)

        # Components (to be initialized)
        self._blockchain = None
        self._agent_manager = None
        self._llm_adapters = {}

    async def start(self) -> bool:
        """Start the platform."""
        success = await self.node.start()
        if success:
            logger.info("Decentralized Platform started successfully")
        return success

    async def stop(self) -> None:
        """Stop the platform."""
        await self.node.stop()
        logger.info("Decentralized Platform stopped")

    async def register_llm_service(self, adapter: Any, capabilities: list[str]) -> None:
        """Register LLM inference service."""
        async def llm_handler(payload: dict[str, Any]) -> dict[str, Any]:
            method = payload.get("method", "generate")
            if method == "generate":
                return {"text": await adapter.generate_text(payload.get("prompt", ""))}
            elif method == "embed":
                return {"embedding": await adapter.embed(payload.get("text", ""))}
            else:
                raise ValueError(f"Unknown method: {method}")

        await self.node.register_service(
            service_type=ServiceType.LLM_INFERENCE,
            capabilities=capabilities,
            endpoint=f"http://{self.node.identity.address}:{self.node.identity.port}/llm",
            handler=llm_handler,
        )

    async def get_status(self) -> dict[str, Any]:
        """Get platform status."""
        return {
            "node": await self.node.get_node_info(),
            "config": self.config,
        }
