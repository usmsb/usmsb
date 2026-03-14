"""
Platform Launcher
=================

Main platform startup and management functionality.
"""

import asyncio
import logging
import signal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class PlatformStatus(Enum):
    """Platform status enumeration."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    RESTARTING = "restarting"


@dataclass
class NodeInfo:
    """Node information container."""
    node_id: str
    node_type: str
    host: str
    port: int
    status: str = "unknown"
    last_heartbeat: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "host": self.host,
            "port": self.port,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "metadata": self.metadata,
        }


class PlatformLauncher:
    """
    Platform launcher for managing USMSB platform lifecycle.

    Handles platform startup, shutdown, restart, and node management.
    """

    def __init__(self, config_path: str):
        """
        Initialize platform launcher.

        Args:
            config_path: Path to the platform configuration file.
        """
        self.config_path = Path(config_path)
        self.config: dict[str, Any] = {}
        self.status = PlatformStatus.STOPPED
        self.nodes: dict[str, NodeInfo] = {}
        self._shutdown_event = asyncio.Event()
        self._logger = logging.getLogger("usmsb.platform.launcher")
        self._startup_time: datetime | None = None
        self._tasks: list[asyncio.Task] = []
        self._signal_handlers_installed = False

        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f) or {}

        self._logger.info(f"Loaded configuration from {self.config_path}")

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        if self._signal_handlers_installed:
            return

        loop = asyncio.get_running_loop()

        def signal_handler(sig):
            self._logger.info(f"Received signal {sig.name}, initiating graceful shutdown...")
            self._shutdown_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
                self._logger.debug(f"Registered handler for {sig.name}")
            except NotImplementedError:
                # Windows doesn't support add_signal_handler
                signal.signal(sig, lambda s, f: self._shutdown_event.set())

        self._signal_handlers_installed = True

    async def start(self) -> bool:
        """
        Start the platform.

        Returns:
            True if platform started successfully, False otherwise.
        """
        if self.status == PlatformStatus.RUNNING:
            self._logger.warning("Platform is already running")
            return True

        try:
            self.status = PlatformStatus.STARTING
            self._logger.info("Starting platform...")

            # Setup signal handlers
            self._setup_signal_handlers()

            # Initialize nodes from config
            await self._initialize_nodes()

            # Start core services
            await self._start_services()

            # Start monitoring task
            monitor_task = asyncio.create_task(self._monitor_loop())
            self._tasks.append(monitor_task)

            self.status = PlatformStatus.RUNNING
            self._startup_time = datetime.now()
            self._logger.info("Platform started successfully")

            return True

        except Exception as e:
            self.status = PlatformStatus.ERROR
            self._logger.error(f"Failed to start platform: {e}")
            return False

    async def stop(self) -> bool:
        """
        Stop the platform.

        Returns:
            True if platform stopped successfully, False otherwise.
        """
        if self.status == PlatformStatus.STOPPED:
            self._logger.warning("Platform is already stopped")
            return True

        try:
            self.status = PlatformStatus.STOPPING
            self._logger.info("Stopping platform...")

            # Signal shutdown
            self._shutdown_event.set()

            # Stop services
            await self._stop_services()

            # Cancel running tasks
            for task in self._tasks:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            self._tasks.clear()

            # Update node statuses
            for node in self.nodes.values():
                node.status = "stopped"

            self.status = PlatformStatus.STOPPED
            self._logger.info("Platform stopped successfully")

            return True

        except Exception as e:
            self.status = PlatformStatus.ERROR
            self._logger.error(f"Failed to stop platform: {e}")
            return False

    async def restart(self) -> bool:
        """
        Restart the platform.

        Returns:
            True if platform restarted successfully, False otherwise.
        """
        self._logger.info("Restarting platform...")
        self.status = PlatformStatus.RESTARTING

        if not await self.stop():
            self._logger.error("Failed to stop platform during restart")
            return False

        # Reset shutdown event
        self._shutdown_event.clear()

        if not await self.start():
            self._logger.error("Failed to start platform during restart")
            return False

        self._logger.info("Platform restarted successfully")
        return True

    def get_status(self) -> dict[str, Any]:
        """
        Get platform status.

        Returns:
            Dictionary containing platform status information.
        """
        return {
            "status": self.status.value,
            "uptime": self._get_uptime(),
            "startup_time": self._startup_time.isoformat() if self._startup_time else None,
            "node_count": len(self.nodes),
            "active_nodes": sum(1 for n in self.nodes.values() if n.status == "active"),
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "config_path": str(self.config_path),
        }

    def _get_uptime(self) -> str | None:
        """Get platform uptime as string."""
        if not self._startup_time:
            return None

        delta = datetime.now() - self._startup_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    async def add_node(self, node_config: dict[str, Any]) -> str | None:
        """
        Add a new node to the platform.

        Args:
            node_config: Node configuration dictionary.

        Returns:
            Node ID if added successfully, None otherwise.
        """
        try:
            node_id = node_config.get("node_id") or self._generate_node_id()

            node = NodeInfo(
                node_id=node_id,
                node_type=node_config.get("node_type", "generic"),
                host=node_config.get("host", "localhost"),
                port=node_config.get("port", 8080),
                metadata=node_config.get("metadata", {}),
            )

            # Initialize node
            await self._initialize_node(node)

            self.nodes[node_id] = node
            self._logger.info(f"Added node {node_id} of type {node.node_type}")

            return node_id

        except Exception as e:
            self._logger.error(f"Failed to add node: {e}")
            return None

    async def remove_node(self, node_id: str) -> bool:
        """
        Remove a node from the platform.

        Args:
            node_id: ID of the node to remove.

        Returns:
            True if node removed successfully, False otherwise.
        """
        if node_id not in self.nodes:
            self._logger.warning(f"Node {node_id} not found")
            return False

        try:
            node = self.nodes[node_id]

            # Shutdown node
            await self._shutdown_node(node)

            del self.nodes[node_id]
            self._logger.info(f"Removed node {node_id}")

            return True

        except Exception as e:
            self._logger.error(f"Failed to remove node {node_id}: {e}")
            return False

    def _generate_node_id(self) -> str:
        """Generate a unique node ID."""
        import uuid
        return f"node_{uuid.uuid4().hex[:8]}"

    async def _initialize_nodes(self) -> None:
        """Initialize nodes from configuration."""
        nodes_config = self.config.get("nodes", [])

        for node_config in nodes_config:
            await self.add_node(node_config)

    async def _initialize_node(self, node: NodeInfo) -> None:
        """Initialize a single node."""
        # Simulate node initialization
        await asyncio.sleep(0.1)
        node.status = "active"
        node.last_heartbeat = datetime.now()
        self._logger.debug(f"Initialized node {node.node_id}")

    async def _shutdown_node(self, node: NodeInfo) -> None:
        """Shutdown a single node."""
        # Simulate node shutdown
        await asyncio.sleep(0.1)
        node.status = "stopped"
        self._logger.debug(f"Shutdown node {node.node_id}")

    async def _start_services(self) -> None:
        """Start platform services."""
        services = self.config.get("services", {})

        for service_name, _service_config in services.items():
            self._logger.info(f"Starting service: {service_name}")
            # Simulate service startup
            await asyncio.sleep(0.1)

    async def _stop_services(self) -> None:
        """Stop platform services."""
        services = self.config.get("services", {})

        for service_name in reversed(list(services.keys())):
            self._logger.info(f"Stopping service: {service_name}")
            # Simulate service shutdown
            await asyncio.sleep(0.1)

    async def _monitor_loop(self) -> None:
        """Monitor platform health and node status."""
        while not self._shutdown_event.is_set():
            try:
                await self._check_nodes_health()
                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(5)

    async def _check_nodes_health(self) -> None:
        """Check health of all nodes."""
        for node in self.nodes.values():
            # Simulate health check
            if node.status == "active":
                node.last_heartbeat = datetime.now()

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        await self._shutdown_event.wait()
