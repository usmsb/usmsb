"""
Agent Registration Module

Implements the registration system for agents, including:
- Multi-protocol registration support
- Automatic platform node selection
- Registration state management
- Heartbeat maintenance
- Failover and retry logic
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import aiohttp

from usmsb_sdk.agent_sdk.agent_config import (
    AgentConfig,
    ProtocolConfig,
    ProtocolType,
)


class RegistrationStatus(Enum):
    """Registration status states"""
    NOT_REGISTERED = "not_registered"
    REGISTERING = "registering"
    REGISTERED = "registered"
    RENEWING = "renewing"
    UNREGISTERING = "unregistering"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class PlatformNode:
    """Information about a platform node"""
    node_id: str
    endpoint: str
    protocol: ProtocolType
    latency: float = float('inf')
    load: float = 0.0
    priority: int = 0
    last_check: datetime | None = None
    is_available: bool = False

    def calculate_score(self) -> float:
        """Calculate node score for selection (lower is better)"""
        if not self.is_available:
            return float('inf')
        # Weight: latency (50%), load (30%), priority (20%)
        return (self.latency * 0.5) + (self.load * 0.3) + ((100 - self.priority) * 0.002)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "endpoint": self.endpoint,
            "protocol": self.protocol.value,
            "latency": self.latency,
            "load": self.load,
            "priority": self.priority,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "is_available": self.is_available,
        }


@dataclass
class RegistrationInfo:
    """Detailed registration information"""
    registration_id: str
    agent_id: str
    node_id: str
    protocols: list[ProtocolType]
    registered_at: datetime
    expires_at: datetime | None = None
    token: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "registration_id": self.registration_id,
            "agent_id": self.agent_id,
            "node_id": self.node_id,
            "protocols": [p.value for p in self.protocols],
            "registered_at": self.registered_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
        }


class RegistrationManager:
    """
    Manages agent registration with platform nodes.

    Features:
    - Automatic selection of nearest/best platform node
    - Multi-protocol registration support
    - Registration state management
    - Heartbeat maintenance
    - Failover to backup nodes
    - Retry with exponential backoff
    """

    def __init__(
        self,
        agent_id: str,
        agent_config: AgentConfig,
        logger: logging.Logger | None = None,
    ):
        self.agent_id = agent_id
        self.config = agent_config
        self.logger = logger or logging.getLogger(__name__)

        # State
        self._status = RegistrationStatus.NOT_REGISTERED
        self._registration_info: RegistrationInfo | None = None
        self._registered_protocols: set[ProtocolType] = set()

        # Platform nodes
        self._platform_nodes: dict[str, PlatformNode] = {}
        self._primary_node: PlatformNode | None = None
        self._backup_nodes: list[PlatformNode] = []

        # Session management
        self._http_session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()

        # Callbacks
        self._on_registration_hooks: list[Callable] = []
        self._on_unregistration_hooks: list[Callable] = []
        self._on_failure_hooks: list[Callable] = []

        # Retry configuration
        self._max_retries = 3
        self._retry_delay = 1.0
        self._retry_multiplier = 2.0

    @property
    def status(self) -> RegistrationStatus:
        return self._status

    @property
    def registration_info(self) -> RegistrationInfo | None:
        return self._registration_info

    @property
    def registered_protocols(self) -> list[ProtocolType]:
        return list(self._registered_protocols)

    # ==================== Node Discovery ====================

    async def discover_nodes(self) -> list[PlatformNode]:
        """
        Discover available platform nodes.

        This method:
        1. Queries configured platform endpoints
        2. Checks node health and latency
        3. Returns sorted list by score
        """
        nodes = []

        for endpoint in self.config.network.platform_endpoints:
            try:
                node = await self._probe_node(endpoint)
                if node:
                    nodes.append(node)
                    self._platform_nodes[node.node_id] = node
            except Exception as e:
                self.logger.warning(f"Failed to probe node at {endpoint}: {e}")

        # Also check P2P bootstrap nodes
        for bootstrap in self.config.network.p2p_bootstrap_nodes:
            try:
                node = await self._probe_p2p_node(bootstrap)
                if node:
                    nodes.append(node)
                    self._platform_nodes[node.node_id] = node
            except Exception as e:
                self.logger.warning(f"Failed to probe P2P node at {bootstrap}: {e}")

        # Sort by score
        nodes.sort(key=lambda n: n.calculate_score())
        return nodes

    async def _probe_node(self, endpoint: str) -> PlatformNode | None:
        """Probe a platform node for health and latency"""
        start_time = datetime.now()

        try:
            if not self._http_session:
                self._http_session = aiohttp.ClientSession()

            async with self._http_session.get(
                f"{endpoint}/health",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as response:
                latency = (datetime.now() - start_time).total_seconds() * 1000

                if response.status == 200:
                    data = await response.json()
                    return PlatformNode(
                        node_id=data.get("node_id", "unknown"),
                        endpoint=endpoint,
                        protocol=ProtocolType.HTTP,
                        latency=latency,
                        load=data.get("load", 0.0),
                        priority=data.get("priority", 50),
                        last_check=datetime.now(),
                        is_available=True,
                    )
        except TimeoutError:
            self.logger.warning(f"Timeout probing {endpoint}")
        except Exception as e:
            self.logger.warning(f"Error probing {endpoint}: {e}")

        return None

    async def _probe_p2p_node(self, address: str) -> PlatformNode | None:
        """Probe a P2P bootstrap node"""
        # P2P node probing would be implemented based on P2P protocol
        # For now, return a basic node info
        return PlatformNode(
            node_id=address,
            endpoint=address,
            protocol=ProtocolType.P2P,
            latency=0,
            load=0,
            priority=50,
            last_check=datetime.now(),
            is_available=True,
        )

    async def select_best_node(self) -> PlatformNode | None:
        """Select the best available platform node"""
        nodes = await self.discover_nodes()

        if not nodes:
            self.logger.error("No available platform nodes found")
            return None

        # Select node with best score
        best_node = nodes[0]
        self._primary_node = best_node
        self._backup_nodes = nodes[1:4] if len(nodes) > 1 else []

        self.logger.info(f"Selected primary node: {best_node.node_id} at {best_node.endpoint}")
        return best_node

    # ==================== Registration ====================

    async def register(self, protocols: list[ProtocolType] | None = None, endpoint_override: str | None = None) -> bool:
        """
        Register agent with the platform.

        Args:
            protocols: Specific protocols to register (all enabled if None)
            endpoint: Override endpoint URL (useful when HTTP server starts later)

        Returns:
            True if registration successful
        """
        async with self._lock:
            if self._status == RegistrationStatus.REGISTERED:
                self.logger.warning("Agent already registered")
                return True

            self._status = RegistrationStatus.REGISTERING

            # Select best node
            if not self._primary_node:
                await self.select_best_node()

            if not self._primary_node:
                self._status = RegistrationStatus.FAILED
                return False

            # Determine protocols to register
            if protocols is None:
                protocols = self.config.get_enabled_protocols()

            # Attempt registration with retries
            for attempt in range(self._max_retries):
                try:
                    result = await self._do_register(protocols)
                    if result:
                        self._status = RegistrationStatus.REGISTERED
                        await self._notify_registration_hooks()
                        return True
                except Exception as e:
                    self.logger.error(f"Registration attempt {attempt + 1} failed: {e}")
                    if attempt < self._max_retries - 1:
                        delay = self._retry_delay * (self._retry_multiplier ** attempt)
                        await asyncio.sleep(delay)

                        # Try backup node
                        if self._backup_nodes:
                            self._primary_node = self._backup_nodes.pop(0)
                            self.logger.info(f"Switching to backup node: {self._primary_node.node_id}")

            self._status = RegistrationStatus.FAILED
            await self._notify_failure_hooks("Registration failed after all retries")
            return False

    async def _do_register(self, protocols: list[ProtocolType]) -> bool:
        """Execute the registration with the platform"""
        node = self._primary_node
        if not node:
            return False

        # Get endpoint from protocol config
        endpoint = ""
        http_config = self.config.protocols.get(ProtocolType.HTTP)
        if http_config and http_config.enabled:
            endpoint = f"http://{http_config.host or 'localhost'}:{http_config.port}"
            self.logger.info(f"DEBUG: Setting endpoint to: {endpoint}")
        else:
            self.logger.info("DEBUG: HTTP not enabled or no config, endpoint stays empty")

        registration_payload = {
            "agent_id": self.agent_id,
            "name": self.config.name,
            "description": self.config.description,
            "version": self.config.version,
            "protocols": [p.value for p in protocols],
            "skills": [s.to_dict() for s in self.config.skills],
            # Platform expects List[str], not List[Dict]
            "capabilities": [c.name for c in self.config.capabilities],
            # Required field
            "endpoint": endpoint,
            "heartbeat_interval": self.config.heartbeat_interval,
            "ttl": self.config.ttl,
            "metadata": self.config.metadata,
        }

        # Register via appropriate protocol
        if node.protocol == ProtocolType.HTTP or node.protocol == ProtocolType.WEBSOCKET:
            return await self._register_http(node, registration_payload)
        elif node.protocol == ProtocolType.A2A:
            return await self._register_a2a(node, registration_payload)
        elif node.protocol == ProtocolType.MCP:
            return await self._register_mcp(node, registration_payload)
        elif node.protocol == ProtocolType.P2P:
            return await self._register_p2p(node, registration_payload)
        else:
            self.logger.error(f"Unsupported protocol: {node.protocol}")
            return False

    async def _register_http(self, node: PlatformNode, payload: dict) -> bool:
        """Register via HTTP protocol"""
        try:
            if not self._http_session:
                self._http_session = aiohttp.ClientSession()

            headers = {}
            if self.config.security.api_key:
                headers["Authorization"] = f"Bearer {self.config.security.api_key}"

            async with self._http_session.post(
                f"{node.endpoint}/agents/register",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status in (200, 201):
                    data = await response.json()
                    self._registration_info = RegistrationInfo(
                        registration_id=data.get("registration_id", ""),
                        agent_id=self.agent_id,
                        node_id=node.node_id,
                        protocols=[ProtocolType(p) for p in payload["protocols"]],
                        registered_at=datetime.now(),
                        expires_at=datetime.now() + timedelta(hours=24) if data.get("expires_in") else None,
                        token=data.get("token"),
                        metadata=data.get("metadata", {}),
                    )
                    self._registered_protocols = set(self._registration_info.protocols)
                    self.logger.info(f"Successfully registered via HTTP with node {node.node_id}")
                    return True
                else:
                    error = await response.text()
                    self.logger.error(f"HTTP registration failed: {response.status} - {error}")
                    return False
        except Exception as e:
            self.logger.error(f"HTTP registration error: {e}")
            return False

    async def _register_a2a(self, node: PlatformNode, payload: dict) -> bool:
        """Register via A2A protocol"""
        # A2A protocol registration implementation
        # This would involve A2A-specific message exchange
        self.logger.info(f"Registering via A2A protocol with node {node.node_id}")

        # For now, use HTTP as transport for A2A
        payload["protocol"] = "a2a"
        return await self._register_http(node, payload)

    async def _register_mcp(self, node: PlatformNode, payload: dict) -> bool:
        """Register via MCP (Model Context Protocol)"""
        # MCP protocol registration implementation
        self.logger.info(f"Registering via MCP protocol with node {node.node_id}")

        # MCP-specific registration format
        mcp_payload = {
            "jsonrpc": "2.0",
            "method": "agent/register",
            "params": payload,
            "id": str(datetime.now().timestamp()),
        }

        return await self._register_http(node, {"mcp": mcp_payload})

    async def _register_p2p(self, node: PlatformNode, payload: dict) -> bool:
        """Register via P2P protocol"""
        # P2P protocol registration implementation
        self.logger.info(f"Registering via P2P protocol with node {node.node_id}")

        # For P2P, we would connect directly to the bootstrap node
        # and announce our presence
        self._registration_info = RegistrationInfo(
            registration_id=f"p2p-{self.agent_id}",
            agent_id=self.agent_id,
            node_id=node.node_id,
            protocols=[ProtocolType.P2P],
            registered_at=datetime.now(),
            metadata={"endpoint": node.endpoint},
        )
        self._registered_protocols = {ProtocolType.P2P}
        return True

    # ==================== Unregistration ====================

    async def unregister(self) -> bool:
        """Unregister agent from the platform"""
        async with self._lock:
            if self._status != RegistrationStatus.REGISTERED:
                return True

            self._status = RegistrationStatus.UNREGISTERING

            try:
                if self._primary_node:
                    result = await self._do_unregister()
                    if result:
                        self._status = RegistrationStatus.NOT_REGISTERED
                        self._registration_info = None
                        self._registered_protocols.clear()
                        await self._notify_unregistration_hooks()
                        return True
            except Exception as e:
                self.logger.error(f"Unregistration error: {e}")

            self._status = RegistrationStatus.FAILED
            return False

    async def _do_unregister(self) -> bool:
        """Execute unregistration"""
        node = self._primary_node
        if not node or not self._registration_info:
            return False

        try:
            if not self._http_session:
                self._http_session = aiohttp.ClientSession()

            headers = {}
            if self._registration_info.token:
                headers["Authorization"] = f"Bearer {self._registration_info.token}"

            async with self._http_session.delete(
                f"{node.endpoint}/agents/{self.agent_id}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status in (200, 204, 404):
                    self.logger.info(f"Successfully unregistered from node {node.node_id}")
                    return True
                else:
                    self.logger.warning(f"Unregistration returned status {response.status}")
                    return False
        except Exception as e:
            self.logger.error(f"Unregistration error: {e}")
            return False

    # ==================== Heartbeat ====================

    async def send_heartbeat(self) -> bool:
        """Send heartbeat to maintain registration"""
        if self._status != RegistrationStatus.REGISTERED:
            return False

        node = self._primary_node
        if not node:
            return False

        try:
            if not self._http_session:
                self._http_session = aiohttp.ClientSession()

            headers = {}
            if self._registration_info and self._registration_info.token:
                headers["Authorization"] = f"Bearer {self._registration_info.token}"

            heartbeat_payload = {
                "agent_id": self.agent_id,
                "timestamp": datetime.now().isoformat(),
                "status": "active",
                "metrics": {
                    "protocols": [p.value for p in self._registered_protocols],
                },
            }

            async with self._http_session.post(
                f"{node.endpoint}/agents/{self.agent_id}/heartbeat",
                json=heartbeat_payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    # Update registration if needed
                    if data.get("action") == "renew":
                        await self.renew_registration()
                    return True
                elif response.status == 404:
                    # Registration lost, re-register
                    self.logger.warning("Registration lost, re-registering")
                    self._status = RegistrationStatus.EXPIRED
                    return await self.register()
                else:
                    self.logger.warning(f"Heartbeat failed: {response.status}")
                    return False
        except Exception as e:
            self.logger.error(f"Heartbeat error: {e}")
            return False

    async def renew_registration(self) -> bool:
        """Renew registration before expiry"""
        if self._status != RegistrationStatus.REGISTERED:
            return False

        self._status = RegistrationStatus.RENEWING

        try:
            result = await self.register(list(self._registered_protocols))
            if result:
                self._status = RegistrationStatus.REGISTERED
            return result
        except Exception as e:
            self.logger.error(f"Renewal error: {e}")
            self._status = RegistrationStatus.FAILED
            return False

    # ==================== Protocol-Specific Registration ====================

    async def register_protocol(self, protocol: ProtocolType, config: ProtocolConfig | None = None) -> bool:
        """Register for a specific protocol"""
        if self._status != RegistrationStatus.REGISTERED:
            # Full registration first
            return await self.register([protocol])

        # Add protocol to existing registration
        if protocol in self._registered_protocols:
            return True

        try:
            node = self._primary_node
            if not node or not self._http_session:
                return False

            headers = {}
            if self._registration_info and self._registration_info.token:
                headers["Authorization"] = f"Bearer {self._registration_info.token}"

            payload = {
                "protocol": protocol.value,
                "config": config.to_dict() if config else {},
            }

            async with self._http_session.post(
                f"{node.endpoint}/agents/{self.agent_id}/protocols",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    self._registered_protocols.add(protocol)
                    self.logger.info(f"Registered protocol: {protocol.value}")
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Protocol registration error: {e}")
            return False

    async def unregister_protocol(self, protocol: ProtocolType) -> bool:
        """Unregister a specific protocol"""
        if protocol not in self._registered_protocols:
            return True

        try:
            node = self._primary_node
            if not node or not self._http_session:
                return False

            headers = {}
            if self._registration_info and self._registration_info.token:
                headers["Authorization"] = f"Bearer {self._registration_info.token}"

            async with self._http_session.delete(
                f"{node.endpoint}/agents/{self.agent_id}/protocols/{protocol.value}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status in (200, 204):
                    self._registered_protocols.discard(protocol)
                    self.logger.info(f"Unregistered protocol: {protocol.value}")
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Protocol unregistration error: {e}")
            return False

    # ==================== Event Hooks ====================

    def on_registration(self, hook: Callable) -> None:
        """Register a hook for successful registration"""
        self._on_registration_hooks.append(hook)

    def on_unregistration(self, hook: Callable) -> None:
        """Register a hook for unregistration"""
        self._on_unregistration_hooks.append(hook)

    def on_failure(self, hook: Callable) -> None:
        """Register a hook for registration failures"""
        self._on_failure_hooks.append(hook)

    async def _notify_registration_hooks(self) -> None:
        """Notify registration hooks"""
        for hook in self._on_registration_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(self._registration_info)
                else:
                    hook(self._registration_info)
            except Exception as e:
                self.logger.error(f"Error in registration hook: {e}")

    async def _notify_unregistration_hooks(self) -> None:
        """Notify unregistration hooks"""
        for hook in self._on_unregistration_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(self.agent_id)
                else:
                    hook(self.agent_id)
            except Exception as e:
                self.logger.error(f"Error in unregistration hook: {e}")

    async def _notify_failure_hooks(self, reason: str) -> None:
        """Notify failure hooks"""
        for hook in self._on_failure_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(reason)
                else:
                    hook(reason)
            except Exception as e:
                self.logger.error(f"Error in failure hook: {e}")

    # ==================== Cleanup ====================

    async def close(self) -> None:
        """Cleanup resources"""
        if self._http_session:
            await self._http_session.close()
            self._http_session = None
