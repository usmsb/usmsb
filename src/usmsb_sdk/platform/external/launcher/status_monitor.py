"""
Status Monitor
==============

Real-time platform status monitoring.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class MetricType(Enum):
    """Metric type enumeration."""
    GAUGE = "gauge"
    COUNTER = "counter"
    HISTOGRAM = "histogram"


@dataclass
class Metric:
    """Metric data container."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "unit": self.unit,
        }


@dataclass
class NodeMetrics:
    """Node metrics container."""
    node_id: str
    status: str
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    network_in_bytes: int = 0
    network_out_bytes: int = 0
    active_connections: int = 0
    last_update: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "status": self.status,
            "cpu_percent": round(self.cpu_percent, 2),
            "memory_percent": round(self.memory_percent, 2),
            "disk_percent": round(self.disk_percent, 2),
            "network_in_bytes": self.network_in_bytes,
            "network_out_bytes": self.network_out_bytes,
            "active_connections": self.active_connections,
            "last_update": self.last_update.isoformat(),
        }


@dataclass
class AgentMetrics:
    """Agent metrics container."""
    total_agents: int = 0
    active_agents: int = 0
    idle_agents: int = 0
    busy_agents: int = 0
    tasks_completed: int = 0
    tasks_pending: int = 0
    tasks_failed: int = 0
    avg_task_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_agents": self.total_agents,
            "active_agents": self.active_agents,
            "idle_agents": self.idle_agents,
            "busy_agents": self.busy_agents,
            "tasks_completed": self.tasks_completed,
            "tasks_pending": self.tasks_pending,
            "tasks_failed": self.tasks_failed,
            "avg_task_duration_ms": round(self.avg_task_duration_ms, 2),
        }


@dataclass
class StorageMetrics:
    """Storage metrics container."""
    type: str = "sqlite"
    total_size_bytes: int = 0
    available_bytes: int = 0
    document_count: int = 0
    index_count: int = 0
    read_ops_per_sec: float = 0.0
    write_ops_per_sec: float = 0.0
    avg_latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "total_size_bytes": self.total_size_bytes,
            "available_bytes": self.available_bytes,
            "document_count": self.document_count,
            "index_count": self.index_count,
            "read_ops_per_sec": round(self.read_ops_per_sec, 2),
            "write_ops_per_sec": round(self.write_ops_per_sec, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
        }


@dataclass
class PlatformSummary:
    """Platform status summary."""
    status: str
    uptime_seconds: float
    node_count: int
    healthy_nodes: int
    total_agents: int
    active_agents: int
    storage_used_percent: float
    last_update: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "node_count": self.node_count,
            "healthy_nodes": self.healthy_nodes,
            "total_agents": self.total_agents,
            "active_agents": self.active_agents,
            "storage_used_percent": round(self.storage_used_percent, 2),
            "last_update": self.last_update.isoformat(),
        }


class StatusMonitor:
    """
    Real-time platform status monitor.

    Monitors node status, agent activity, and storage usage.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize status monitor.

        Args:
            config: Platform configuration dictionary.
        """
        self.config = config or {}
        self._logger = logging.getLogger("usmsb.status_monitor")

        # Metrics storage
        self._node_metrics: Dict[str, NodeMetrics] = {}
        self._agent_metrics = AgentMetrics()
        self._storage_metrics = StorageMetrics()
        self._custom_metrics: Dict[str, Metric] = {}

        # State tracking
        self._start_time: Optional[datetime] = None
        self._platform_status: str = "unknown"
        self._is_running = False
        self._monitor_task: Optional[asyncio.Task] = None

        # Event handlers
        self._status_change_handlers: List[Callable] = []
        self._alert_handlers: List[Callable] = []

        # Configuration
        self._monitor_interval = self.config.get("monitor_interval", 10)
        self._alert_thresholds = self.config.get("alert_thresholds", {
            "cpu_percent": 80,
            "memory_percent": 80,
            "disk_percent": 90,
        })

    async def start(self) -> None:
        """Start the status monitor."""
        if self._is_running:
            self._logger.warning("Status monitor is already running")
            return

        self._is_running = True
        self._start_time = datetime.now()
        self._platform_status = "running"

        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self._logger.info("Status monitor started")

    async def stop(self) -> None:
        """Stop the status monitor."""
        if not self._is_running:
            return

        self._is_running = False
        self._platform_status = "stopped"

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        self._logger.info("Status monitor stopped")

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._is_running:
            try:
                await self._collect_metrics()
                await self._check_alerts()
                await asyncio.sleep(self._monitor_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(5)

    async def _collect_metrics(self) -> None:
        """Collect all metrics."""
        await self._collect_node_metrics()
        await self._collect_agent_metrics()
        await self._collect_storage_metrics()

    async def _collect_node_metrics(self) -> None:
        """Collect node metrics."""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()

            # Update system-level metrics
            for node_id in self._node_metrics:
                self._node_metrics[node_id].cpu_percent = cpu_percent
                self._node_metrics[node_id].memory_percent = memory.percent
                self._node_metrics[node_id].last_update = datetime.now()

        except ImportError:
            self._logger.debug("psutil not available for detailed metrics")
        except Exception as e:
            self._logger.error(f"Error collecting node metrics: {e}")

    async def _collect_agent_metrics(self) -> None:
        """Collect agent metrics."""
        # In a real implementation, this would query the agent manager
        # For now, we'll keep simulated values
        pass

    async def _collect_storage_metrics(self) -> None:
        """Collect storage metrics."""
        try:
            import shutil

            storage_config = self.config.get("storage", {})
            storage_type = storage_config.get("type", "sqlite")

            if storage_type == "sqlite":
                path = storage_config.get("path", "./data/usmsb.db")
                from pathlib import Path
                db_path = Path(path)

                if db_path.exists():
                    self._storage_metrics.total_size_bytes = db_path.stat().st_size

                # Get disk usage
                if db_path.parent.exists():
                    usage = shutil.disk_usage(db_path.parent)
                    self._storage_metrics.available_bytes = usage.free

            self._storage_metrics.type = storage_type

        except Exception as e:
            self._logger.error(f"Error collecting storage metrics: {e}")

    async def _check_alerts(self) -> None:
        """Check for alert conditions."""
        thresholds = self._alert_thresholds

        # Check node alerts
        for node_id, metrics in self._node_metrics.items():
            if metrics.cpu_percent > thresholds.get("cpu_percent", 80):
                await self._trigger_alert(
                    "high_cpu",
                    f"Node {node_id} CPU usage is {metrics.cpu_percent:.1f}%",
                    metrics.to_dict(),
                )

            if metrics.memory_percent > thresholds.get("memory_percent", 80):
                await self._trigger_alert(
                    "high_memory",
                    f"Node {node_id} memory usage is {metrics.memory_percent:.1f}%",
                    metrics.to_dict(),
                )

    async def _trigger_alert(self, alert_type: str, message: str,
                             details: Dict[str, Any]) -> None:
        """Trigger an alert."""
        alert = {
            "type": alert_type,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }

        self._logger.warning(f"Alert: {message}")

        for handler in self._alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                self._logger.error(f"Alert handler error: {e}")

    # Node management
    def register_node(self, node_id: str, node_type: str = "generic") -> None:
        """Register a node for monitoring."""
        self._node_metrics[node_id] = NodeMetrics(
            node_id=node_id,
            status="active",
        )
        self._logger.info(f"Registered node: {node_id}")

    def unregister_node(self, node_id: str) -> None:
        """Unregister a node from monitoring."""
        if node_id in self._node_metrics:
            del self._node_metrics[node_id]
            self._logger.info(f"Unregistered node: {node_id}")

    def update_node_status(self, node_id: str, status: str) -> None:
        """Update node status."""
        if node_id in self._node_metrics:
            self._node_metrics[node_id].status = status
            self._node_metrics[node_id].last_update = datetime.now()

    # Agent metrics update
    def update_agent_metrics(self, **kwargs) -> None:
        """Update agent metrics."""
        for key, value in kwargs.items():
            if hasattr(self._agent_metrics, key):
                setattr(self._agent_metrics, key, value)

    # Storage metrics update
    def update_storage_metrics(self, **kwargs) -> None:
        """Update storage metrics."""
        for key, value in kwargs.items():
            if hasattr(self._storage_metrics, key):
                setattr(self._storage_metrics, key, value)

    # Custom metrics
    def record_metric(self, name: str, value: float,
                      metric_type: MetricType = MetricType.GAUGE,
                      tags: Optional[Dict[str, str]] = None,
                      unit: str = "") -> None:
        """Record a custom metric."""
        self._custom_metrics[name] = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            tags=tags or {},
            unit=unit,
        )

    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a specific metric."""
        return self._custom_metrics.get(name)

    # Event handlers
    def on_status_change(self, handler: Callable) -> None:
        """Register a status change handler."""
        self._status_change_handlers.append(handler)

    def on_alert(self, handler: Callable) -> None:
        """Register an alert handler."""
        self._alert_handlers.append(handler)

    # API endpoints
    def get_node_metrics(self, node_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get node metrics.

        Args:
            node_id: Specific node ID, or None for all nodes.

        Returns:
            Node metrics dictionary.
        """
        if node_id:
            if node_id in self._node_metrics:
                return self._node_metrics[node_id].to_dict()
            return {}

        return {nid: m.to_dict() for nid, m in self._node_metrics.items()}

    def get_agent_metrics(self) -> Dict[str, Any]:
        """Get agent metrics."""
        return self._agent_metrics.to_dict()

    def get_storage_metrics(self) -> Dict[str, Any]:
        """Get storage metrics."""
        return self._storage_metrics.to_dict()

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        return {
            "nodes": self.get_node_metrics(),
            "agents": self.get_agent_metrics(),
            "storage": self.get_storage_metrics(),
            "custom": {k: v.to_dict() for k, v in self._custom_metrics.items()},
            "collected_at": datetime.now().isoformat(),
        }

    def get_summary(self) -> PlatformSummary:
        """Get platform status summary."""
        uptime = 0.0
        if self._start_time:
            uptime = (datetime.now() - self._start_time).total_seconds()

        healthy_nodes = sum(
            1 for m in self._node_metrics.values()
            if m.status == "active"
        )

        storage_used_percent = 0.0
        if self._storage_metrics.total_size_bytes > 0:
            storage_used_percent = (
                self._storage_metrics.total_size_bytes /
                (self._storage_metrics.total_size_bytes +
                 self._storage_metrics.available_bytes)
            ) * 100

        return PlatformSummary(
            status=self._platform_status,
            uptime_seconds=uptime,
            node_count=len(self._node_metrics),
            healthy_nodes=healthy_nodes,
            total_agents=self._agent_metrics.total_agents,
            active_agents=self._agent_metrics.active_agents,
            storage_used_percent=storage_used_percent,
        )

    def get_status_api(self) -> Dict[str, Any]:
        """
        Get status for monitoring API.

        Returns:
            Complete status dictionary.
        """
        summary = self.get_summary()

        return {
            "summary": summary.to_dict(),
            "metrics": self.get_all_metrics(),
            "config": {
                "monitor_interval": self._monitor_interval,
                "alert_thresholds": self._alert_thresholds,
            },
        }

    def set_platform_status(self, status: str) -> None:
        """Set platform status and notify handlers."""
        old_status = self._platform_status
        self._platform_status = status

        if old_status != status:
            for handler in self._status_change_handlers:
                try:
                    handler(old_status, status)
                except Exception as e:
                    self._logger.error(f"Status change handler error: {e}")
