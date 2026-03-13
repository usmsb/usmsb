"""
Node Discovery Service Module

This module implements node discovery and health monitoring:
- Discovery of nodes from seed nodes
- Peer exchange protocol
- Node health checking
- Node list maintenance and scoring
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class NodeHealthStatus(str, Enum):
    """Health status of a discovered node."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    BANNED = "banned"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    node_id: str
    status: NodeHealthStatus
    latency_ms: float = 0.0
    response_code: int = 200
    error_message: Optional[str] = None
    checked_at: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "response_code": self.response_code,
            "error_message": self.error_message,
            "checked_at": self.checked_at,
            "details": self.details,
        }


@dataclass
class DiscoveredNode:
    """Information about a discovered node."""
    node_id: str
    address: str
    port: int
    name: str = ""
    version: str = ""
    services: List[str] = field(default_factory=list)
    capabilities: Dict[str, Any] = field(default_factory=dict)
    last_seen: float = field(default_factory=time.time)
    first_seen: float = field(default_factory=time.time)
    health_status: NodeHealthStatus = NodeHealthStatus.UNKNOWN
    last_health_check: Optional[float] = None
    latency_ms: float = 0.0
    success_rate: float = 1.0
    total_checks: int = 0
    failed_checks: int = 0
    reputation: float = 1.0
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""  # Where this node was discovered from

    def update_health(self, result: HealthCheckResult) -> None:
        """Update health status based on check result."""
        self.total_checks += 1
        self.last_health_check = time.time()
        self.health_status = result.status
        self.latency_ms = result.latency_ms

        if result.status == NodeHealthStatus.HEALTHY:
            self.last_seen = time.time()
        else:
            self.failed_checks += 1

        # Calculate success rate
        self.success_rate = 1.0 - (self.failed_checks / self.total_checks)

        # Calculate score
        self._calculate_score()

    def _calculate_score(self) -> None:
        """Calculate node score for ranking."""
        # Factors: health, latency, success rate, reputation
        health_factor = {
            NodeHealthStatus.HEALTHY: 1.0,
            NodeHealthStatus.DEGRADED: 0.5,
            NodeHealthStatus.UNHEALTHY: 0.1,
            NodeHealthStatus.UNKNOWN: 0.3,
            NodeHealthStatus.BANNED: 0.0,
        }.get(self.health_status, 0.0)

        # Latency factor (lower is better, normalize to 0-1)
        latency_factor = max(0, 1.0 - (self.latency_ms / 1000.0))

        self.score = (
            health_factor * 0.4 +
            latency_factor * 0.2 +
            self.success_rate * 0.2 +
            self.reputation * 0.2
        )

    def is_stale(self, max_age: float = 3600.0) -> bool:
        """Check if node info is stale."""
        return time.time() - self.last_seen > max_age

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "address": self.address,
            "port": self.port,
            "name": self.name,
            "version": self.version,
            "services": self.services,
            "capabilities": self.capabilities,
            "last_seen": self.last_seen,
            "first_seen": self.first_seen,
            "health_status": self.health_status.value,
            "last_health_check": self.last_health_check,
            "latency_ms": self.latency_ms,
            "success_rate": self.success_rate,
            "total_checks": self.total_checks,
            "failed_checks": self.failed_checks,
            "reputation": self.reputation,
            "score": self.score,
            "metadata": self.metadata,
            "source": self.source,
        }


@dataclass
class DiscoveryStats:
    """Statistics for the discovery service."""
    total_discovered: int = 0
    active_nodes: int = 0
    healthy_nodes: int = 0
    unhealthy_nodes: int = 0
    total_health_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    discovery_rounds: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_discovered": self.total_discovered,
            "active_nodes": self.active_nodes,
            "healthy_nodes": self.healthy_nodes,
            "unhealthy_nodes": self.unhealthy_nodes,
            "total_health_checks": self.total_health_checks,
            "successful_checks": self.successful_checks,
            "failed_checks": self.failed_checks,
            "discovery_rounds": self.discovery_rounds,
        }


class NodeDiscoveryService:
    """
    Node Discovery Service.

    This service handles:
    - Discovering nodes from seed nodes
    - Peer exchange protocol
    - Periodic health checking
    - Node scoring and ranking

    Usage:
        discovery = NodeDiscoveryService(
            seed_nodes=["seed1.example.com:8080", "seed2.example.com:8080"]
        )
        await discovery.start()

        # Get healthy nodes
        nodes = await discovery.get_healthy_nodes()

        # Discover specific service
        providers = await discovery.discover_service("llm_inference")

        await discovery.stop()
    """

    DEFAULT_HEALTH_CHECK_INTERVAL = 60.0    # seconds
    DEFAULT_DISCOVERY_INTERVAL = 300.0      # seconds
    DEFAULT_NODE_TIMEOUT = 10.0             # seconds
    DEFAULT_MAX_NODES = 1000
    DEFAULT_STALE_THRESHOLD = 3600.0        # seconds

    def __init__(
        self,
        seed_nodes: Optional[List[str]] = None,
        local_node_id: str = "",
        health_check_interval: float = DEFAULT_HEALTH_CHECK_INTERVAL,
        discovery_interval: float = DEFAULT_DISCOVERY_INTERVAL,
        max_nodes: int = DEFAULT_MAX_NODES,
        stale_threshold: float = DEFAULT_STALE_THRESHOLD,
    ):
        """
        Initialize the Discovery Service.

        Args:
            seed_nodes: Initial list of seed nodes
            local_node_id: ID of the local node (to exclude from discovery)
            health_check_interval: Interval between health checks
            discovery_interval: Interval between discovery rounds
            max_nodes: Maximum number of nodes to track
            stale_threshold: Time after which a node is considered stale
        """
        self.seed_nodes = seed_nodes or []
        self.local_node_id = local_node_id
        self.health_check_interval = health_check_interval
        self.discovery_interval = discovery_interval
        self.max_nodes = max_nodes
        self.stale_threshold = stale_threshold

        # Discovered nodes
        self._nodes: Dict[str, DiscoveredNode] = {}
        self._nodes_by_address: Dict[str, str] = {}  # "address:port" -> node_id

        # Services index
        self._services_index: Dict[str, Set[str]] = defaultdict(set)

        # Statistics
        self._stats = DiscoveryStats()

        # State
        self._running = False
        self._tasks: Set[asyncio.Task] = set()

        # Event handlers
        self._on_node_discovered: Optional[Callable[[DiscoveredNode], None]] = None
        self._on_node_lost: Optional[Callable[[str], None]] = None
        self._on_health_changed: Optional[Callable[[str, NodeHealthStatus], None]] = None

    # ==================== Lifecycle ====================

    async def start(self) -> None:
        """Start the discovery service."""
        if self._running:
            return

        self._running = True
        logger.info("Node Discovery Service starting")

        # Add seed nodes
        for seed in self.seed_nodes:
            await self._add_seed_node(seed)

        # Start background tasks
        task = asyncio.create_task(self._discovery_loop())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

        task = asyncio.create_task(self._health_check_loop())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

        task = asyncio.create_task(self._cleanup_loop())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

        logger.info(
            f"Node Discovery Service started with {len(self.seed_nodes)} seed nodes"
        )

    async def stop(self) -> None:
        """Stop the discovery service."""
        self._running = False

        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        logger.info("Node Discovery Service stopped")

    # ==================== Node Management ====================

    async def _add_seed_node(self, seed_address: str) -> None:
        """Add a seed node."""
        try:
            address, port = self._parse_address(seed_address)
            node_id = f"seed_{address}_{port}"

            node = DiscoveredNode(
                node_id=node_id,
                address=address,
                port=port,
                name=f"seed-{address}",
                source="seed",
                health_status=NodeHealthStatus.UNKNOWN,
            )

            await self._add_node(node)

        except Exception as e:
            logger.error(f"Failed to add seed node {seed_address}: {e}")

    async def _add_node(self, node: DiscoveredNode) -> bool:
        """Add or update a discovered node."""
        if node.node_id == self.local_node_id:
            return False

        # Check if already exists
        if node.node_id in self._nodes:
            # Update existing
            existing = self._nodes[node.node_id]
            existing.last_seen = time.time()
            existing.services = node.services or existing.services
            existing.capabilities = node.capabilities or existing.capabilities
            existing.metadata.update(node.metadata)
            return False

        # Check capacity
        if len(self._nodes) >= self.max_nodes:
            # Remove lowest scoring node
            await self._evict_worst_node()

        # Add new node
        self._nodes[node.node_id] = node
        address_key = f"{node.address}:{node.port}"
        self._nodes_by_address[address_key] = node.node_id

        # Index services
        for service in node.services:
            self._services_index[service].add(node.node_id)

        self._stats.total_discovered += 1

        if self._on_node_discovered:
            try:
                if asyncio.iscoroutinefunction(self._on_node_discovered):
                    await self._on_node_discovered(node)
                else:
                    self._on_node_discovered(node)
            except Exception as e:
                logger.error(f"Error in node discovered callback: {e}")

        logger.debug(f"Discovered node: {node.node_id} at {node.address}:{node.port}")
        return True

    async def _evict_worst_node(self) -> None:
        """Evict the lowest scoring node."""
        if not self._nodes:
            return

        # Find worst node (excluding seeds)
        worst_node = min(
            [n for n in self._nodes.values() if n.source != "seed"],
            key=lambda n: n.score,
            default=None
        )

        if worst_node:
            await self._remove_node(worst_node.node_id, "Evicted (capacity)")

    async def _remove_node(self, node_id: str, reason: str = "") -> None:
        """Remove a node from discovery."""
        if node_id not in self._nodes:
            return

        node = self._nodes.pop(node_id)
        address_key = f"{node.address}:{node.port}"
        self._nodes_by_address.pop(address_key, None)

        # Remove from services index
        for service in node.services:
            self._services_index[service].discard(node_id)

        if self._on_node_lost:
            try:
                if asyncio.iscoroutinefunction(self._on_node_lost):
                    await self._on_node_lost(node_id)
                else:
                    self._on_node_lost(node_id)
            except Exception as e:
                logger.error(f"Error in node lost callback: {e}")

        logger.debug(f"Removed node {node_id}: {reason}")

    def _parse_address(self, address: str) -> Tuple[str, int]:
        """Parse address string into host and port."""
        if ":" in address:
            host, port_str = address.rsplit(":", 1)
            return host, int(port_str)
        return address, 8080

    # ==================== Discovery ====================

    async def _discovery_loop(self) -> None:
        """Periodically discover new nodes."""
        while self._running:
            try:
                await asyncio.sleep(self.discovery_interval)
                await self._run_discovery()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in discovery loop: {e}")
                await asyncio.sleep(10.0)

    async def _run_discovery(self) -> None:
        """Run a discovery round."""
        self._stats.discovery_rounds += 1
        logger.debug(f"Running discovery round {self._stats.discovery_rounds}")

        # Query known nodes for their peer lists
        discovered_count = 0

        for node_id, node in list(self._nodes.items()):
            if node.health_status != NodeHealthStatus.HEALTHY:
                continue

            try:
                peers = await self._query_node_peers(node)
                for peer_info in peers:
                    peer_node = self._parse_peer_info(peer_info, source=node_id)
                    if peer_node and await self._add_node(peer_node):
                        discovered_count += 1

            except Exception as e:
                logger.debug(f"Failed to query peers from {node_id}: {e}")

        if discovered_count > 0:
            logger.info(f"Discovered {discovered_count} new nodes")

    async def _query_node_peers(self, node: DiscoveredNode) -> List[Dict[str, Any]]:
        """Query a node for its known peers."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(node.address, node.port),
                timeout=self.DEFAULT_NODE_TIMEOUT
            )

            # Request peer list
            request = {"type": "get_peers"}
            writer.write(json.dumps(request).encode() + b"\n")
            await writer.drain()

            # Read response
            data = await asyncio.wait_for(reader.readline(), timeout=5.0)
            response = json.loads(data.decode())

            writer.close()
            await writer.wait_closed()

            return response.get("peers", [])

        except Exception as e:
            logger.debug(f"Failed to query peers from {node.address}: {e}")
            return []

    def _parse_peer_info(
        self,
        peer_info: Dict[str, Any],
        source: str
    ) -> Optional[DiscoveredNode]:
        """Parse peer info into a DiscoveredNode."""
        try:
            node_id = peer_info.get("node_id", "")
            if not node_id:
                return None

            return DiscoveredNode(
                node_id=node_id,
                address=peer_info.get("address", ""),
                port=peer_info.get("port", 8080),
                name=peer_info.get("name", ""),
                version=peer_info.get("version", ""),
                services=peer_info.get("services", []),
                capabilities=peer_info.get("capabilities", {}),
                source=source,
            )
        except Exception:
            return None

    # ==================== Health Checking ====================

    async def _health_check_loop(self) -> None:
        """Periodically check health of nodes."""
        while self._running:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._run_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(10.0)

    async def _run_health_checks(self) -> None:
        """Run health checks on all nodes."""
        # Check nodes in parallel with limited concurrency
        semaphore = asyncio.Semaphore(10)

        async def check_with_limit(node: DiscoveredNode):
            async with semaphore:
                await self._check_node_health(node)

        tasks = [
            asyncio.create_task(check_with_limit(node))
            for node in self._nodes.values()
        ]

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Update stats
        self._update_health_stats()

    async def _check_node_health(self, node: DiscoveredNode) -> HealthCheckResult:
        """Check health of a single node."""
        self._stats.total_health_checks += 1

        try:
            start_time = time.time()

            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(node.address, node.port),
                timeout=self.DEFAULT_NODE_TIMEOUT
            )

            # Send ping
            writer.write(b'{"type": "ping"}\n')
            await writer.drain()

            # Wait for pong
            data = await asyncio.wait_for(reader.readline(), timeout=5.0)
            response = json.loads(data.decode())

            writer.close()
            await writer.wait_closed()

            latency_ms = (time.time() - start_time) * 1000

            result = HealthCheckResult(
                node_id=node.node_id,
                status=NodeHealthStatus.HEALTHY,
                latency_ms=latency_ms,
                response_code=200,
                details={"response": response},
            )

            self._stats.successful_checks += 1

        except asyncio.TimeoutError:
            result = HealthCheckResult(
                node_id=node.node_id,
                status=NodeHealthStatus.UNHEALTHY,
                error_message="Timeout",
                response_code=408,
            )
            self._stats.failed_checks += 1

        except ConnectionRefusedError:
            result = HealthCheckResult(
                node_id=node.node_id,
                status=NodeHealthStatus.UNHEALTHY,
                error_message="Connection refused",
                response_code=503,
            )
            self._stats.failed_checks += 1

        except Exception as e:
            result = HealthCheckResult(
                node_id=node.node_id,
                status=NodeHealthStatus.UNKNOWN,
                error_message=str(e),
                response_code=500,
            )
            self._stats.failed_checks += 1

        # Update node health
        old_status = node.health_status
        node.update_health(result)

        # Emit event if status changed
        if old_status != result.status and self._on_health_changed:
            try:
                if asyncio.iscoroutinefunction(self._on_health_changed):
                    await self._on_health_changed(node.node_id, result.status)
                else:
                    self._on_health_changed(node.node_id, result.status)
            except Exception as e:
                logger.error(f"Error in health changed callback: {e}")

        return result

    async def check_node(self, node_id: str) -> Optional[HealthCheckResult]:
        """Manually check health of a specific node."""
        if node_id not in self._nodes:
            return None

        return await self._check_node_health(self._nodes[node_id])

    def _update_health_stats(self) -> None:
        """Update health statistics."""
        self._stats.active_nodes = len(self._nodes)
        self._stats.healthy_nodes = len([
            n for n in self._nodes.values()
            if n.health_status == NodeHealthStatus.HEALTHY
        ])
        self._stats.unhealthy_nodes = len([
            n for n in self._nodes.values()
            if n.health_status in [NodeHealthStatus.UNHEALTHY, NodeHealthStatus.UNKNOWN]
        ])

    # ==================== Cleanup ====================

    async def _cleanup_loop(self) -> None:
        """Periodically clean up stale nodes."""
        while self._running:
            try:
                await asyncio.sleep(300.0)  # Every 5 minutes
                await self._cleanup_stale_nodes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_stale_nodes(self) -> None:
        """Remove stale nodes."""
        stale_nodes = [
            node_id for node_id, node in self._nodes.items()
            if node.is_stale(self.stale_threshold) and node.source != "seed"
        ]

        for node_id in stale_nodes:
            await self._remove_node(node_id, "Stale")

        if stale_nodes:
            logger.info(f"Cleaned up {len(stale_nodes)} stale nodes")

    # ==================== Public API ====================

    async def discover_service(self, service: str) -> List[DiscoveredNode]:
        """
        Discover nodes providing a specific service.

        Args:
            service: Service name to discover

        Returns:
            List of nodes providing the service, sorted by score
        """
        node_ids = self._services_index.get(service, set())
        nodes = [
            self._nodes[nid] for nid in node_ids
            if nid in self._nodes
            and self._nodes[nid].health_status == NodeHealthStatus.HEALTHY
        ]
        return sorted(nodes, key=lambda n: n.score, reverse=True)

    async def get_healthy_nodes(self, limit: int = 100) -> List[DiscoveredNode]:
        """
        Get list of healthy nodes.

        Args:
            limit: Maximum number of nodes to return

        Returns:
            List of healthy nodes, sorted by score
        """
        healthy = [
            node for node in self._nodes.values()
            if node.health_status == NodeHealthStatus.HEALTHY
        ]
        sorted_nodes = sorted(healthy, key=lambda n: n.score, reverse=True)
        return sorted_nodes[:limit]

    async def get_node(self, node_id: str) -> Optional[DiscoveredNode]:
        """Get a specific node by ID."""
        return self._nodes.get(node_id)

    async def get_random_nodes(self, count: int = 10) -> List[DiscoveredNode]:
        """Get random healthy nodes."""
        import random
        healthy = await self.get_healthy_nodes()
        if len(healthy) <= count:
            return healthy
        return random.sample(healthy, count)

    def get_all_nodes(self) -> List[DiscoveredNode]:
        """Get all discovered nodes."""
        return list(self._nodes.values())

    def get_stats(self) -> DiscoveryStats:
        """Get discovery statistics."""
        return self._stats

    async def add_node_manually(
        self,
        address: str,
        port: int,
        node_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DiscoveredNode:
        """Manually add a node to discovery."""
        node = DiscoveredNode(
            node_id=node_id or f"manual_{address}_{port}",
            address=address,
            port=port,
            source="manual",
            metadata=metadata or {},
        )
        await self._add_node(node)
        return node

    async def remove_node(self, node_id: str) -> bool:
        """Remove a node from discovery."""
        if node_id in self._nodes:
            await self._remove_node(node_id, "Manual removal")
            return True
        return False

    async def ban_node(self, node_id: str, reason: str = "") -> None:
        """Ban a node."""
        if node_id in self._nodes:
            node = self._nodes[node_id]
            node.health_status = NodeHealthStatus.BANNED
            node.metadata["ban_reason"] = reason
            node.metadata["banned_at"] = time.time()
            logger.info(f"Banned node {node_id}: {reason}")

    async def unban_node(self, node_id: str) -> None:
        """Unban a node."""
        if node_id in self._nodes:
            node = self._nodes[node_id]
            node.health_status = NodeHealthStatus.UNKNOWN
            node.metadata.pop("ban_reason", None)
            node.metadata.pop("banned_at", None)
            logger.info(f"Unbanned node {node_id}")

    # ==================== Event Handlers ====================

    def on_node_discovered(self, callback: Callable[[DiscoveredNode], None]) -> None:
        """Set callback for when a node is discovered."""
        self._on_node_discovered = callback

    def on_node_lost(self, callback: Callable[[str], None]) -> None:
        """Set callback for when a node is lost."""
        self._on_node_lost = callback

    def on_health_changed(
        self,
        callback: Callable[[str, NodeHealthStatus], None]
    ) -> None:
        """Set callback for when node health changes."""
        self._on_health_changed = callback

    # ==================== Peer Exchange ====================

    async def get_peers_for_exchange(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get peer list for peer exchange protocol."""
        healthy = await self.get_healthy_nodes(limit)
        return [
            {
                "node_id": node.node_id,
                "address": node.address,
                "port": node.port,
                "services": node.services,
            }
            for node in healthy
        ]
