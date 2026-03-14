"""
Monitor Agent Module

Provides system monitoring capabilities including:
    - Node health status monitoring
    - Agent activity and performance tracking
    - System metrics collection
    - Alert notification management
    - Threshold configuration

Skills:
    - health_check: Check health status of nodes/agents
    - get_metrics: Get collected system metrics
    - get_alerts: Get current alerts
    - set_threshold: Configure alert thresholds
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from usmsb_sdk.agent_sdk.agent_config import (
    AgentConfig,
    CapabilityDefinition,
    SkillDefinition,
    SkillParameter,
)
from usmsb_sdk.agent_sdk.communication import Message, MessageType, Session
from usmsb_sdk.platform.external.system_agents.base_system_agent import (
    BaseSystemAgent,
    SystemAgentConfig,
    SystemAgentPermission,
)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"
    OFFLINE = "offline"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Alert:
    """Represents a system alert"""

    def __init__(
        self,
        alert_id: str,
        title: str,
        message: str,
        severity: AlertSeverity,
        source: str,
        metadata: dict[str, Any] | None = None,
    ):
        self.alert_id = alert_id
        self.title = title
        self.message = message
        self.severity = severity
        self.source = source
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.acknowledged = False
        self.acknowledged_by: str | None = None
        self.resolved = False
        self.resolved_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "alert_id": self.alert_id,
            "title": self.title,
            "message": self.message,
            "severity": self.severity.value,
            "source": self.source,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class ThresholdConfig:
    """Configuration for monitoring thresholds"""

    def __init__(
        self,
        metric_name: str,
        warning_threshold: float | None = None,
        critical_threshold: float | None = None,
        comparison: str = "greater",  # "greater", "less", "equal"
        enabled: bool = True,
    ):
        self.metric_name = metric_name
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.comparison = comparison
        self.enabled = enabled

    def check(self, value: float) -> AlertSeverity | None:
        """Check if value exceeds thresholds"""
        if not self.enabled:
            return None

        if self.comparison == "greater":
            if self.critical_threshold and value >= self.critical_threshold:
                return AlertSeverity.CRITICAL
            if self.warning_threshold and value >= self.warning_threshold:
                return AlertSeverity.WARNING
        elif self.comparison == "less":
            if self.critical_threshold and value <= self.critical_threshold:
                return AlertSeverity.CRITICAL
            if self.warning_threshold and value <= self.warning_threshold:
                return AlertSeverity.WARNING

        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "metric_name": self.metric_name,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "comparison": self.comparison,
            "enabled": self.enabled,
        }


class MonitorAgent(BaseSystemAgent):
    """
    System monitoring agent for tracking health, performance, and alerts.

    This agent provides comprehensive monitoring capabilities for:
    - Platform nodes health status
    - Agent activities and performance metrics
    - System resource utilization
    - Alert generation and management

    Skills:
        - health_check: Perform health checks on nodes/agents
        - get_metrics: Retrieve collected metrics
        - get_alerts: Get active alerts
        - set_threshold: Configure monitoring thresholds

    Example:
        config = AgentConfig(
            agent_id="monitor-001",
            name="SystemMonitor",
            # ... other config
        )
        system_config = SystemAgentConfig(
            permission_level=SystemAgentPermission.MONITOR
        )
        monitor = MonitorAgent(config, system_config)
        await monitor.start()

        # Check health
        health = await monitor.call_skill("health_check", {"target": "node-001"})
    """

    SYSTEM_AGENT_TYPE = "monitor"

    def __init__(
        self,
        config: AgentConfig,
        system_config: SystemAgentConfig | None = None,
    ):
        """Initialize the monitor agent"""
        super().__init__(config, system_config)

        # Monitoring data
        self._node_health: dict[str, dict[str, Any]] = {}
        self._agent_health: dict[str, dict[str, Any]] = {}
        self._metrics_history: dict[str, list[dict[str, Any]]] = {}
        self._alerts: dict[str, Alert] = {}
        self._thresholds: dict[str, ThresholdConfig] = {}

        # Alert counter for unique IDs
        self._alert_counter = 0

        # Monitoring state
        self._monitoring_active = False
        self._monitor_interval = 30  # seconds

        # Initialize default thresholds
        self._init_default_thresholds()

        # Register monitor skills
        self._register_monitor_skills()

    def _init_default_thresholds(self) -> None:
        """Initialize default monitoring thresholds"""
        default_thresholds = [
            ThresholdConfig("cpu_usage", warning_threshold=70.0, critical_threshold=90.0),
            ThresholdConfig("memory_usage", warning_threshold=80.0, critical_threshold=95.0),
            ThresholdConfig("disk_usage", warning_threshold=80.0, critical_threshold=95.0),
            ThresholdConfig("response_time", warning_threshold=1000.0, critical_threshold=5000.0),
            ThresholdConfig("error_rate", warning_threshold=5.0, critical_threshold=20.0),
            ThresholdConfig("queue_size", warning_threshold=100, critical_threshold=500),
        ]

        for threshold in default_thresholds:
            self._thresholds[threshold.metric_name] = threshold

    def _register_monitor_skills(self) -> None:
        """Register monitoring skills"""
        skills = [
            SkillDefinition(
                name="health_check",
                description="Check health status of nodes or agents",
                parameters=[
                    SkillParameter(
                        name="target",
                        type="string",
                        description="Target to check (node ID, agent ID, or 'all')",
                        required=False,
                        default="all",
                    ),
                    SkillParameter(
                        name="target_type",
                        type="string",
                        description="Type of target: 'node', 'agent', or 'all'",
                        required=False,
                        default="all",
                        enum=["node", "agent", "all"],
                    ),
                    SkillParameter(
                        name="detailed",
                        type="boolean",
                        description="Include detailed health information",
                        required=False,
                        default=False,
                    ),
                ],
                returns="dict",
                tags=["monitoring", "health"],
            ),
            SkillDefinition(
                name="get_metrics",
                description="Get collected system metrics",
                parameters=[
                    SkillParameter(
                        name="metric_name",
                        type="string",
                        description="Name of metric to retrieve (or 'all')",
                        required=False,
                        default="all",
                    ),
                    SkillParameter(
                        name="time_range",
                        type="integer",
                        description="Time range in minutes",
                        required=False,
                        default=60,
                    ),
                    SkillParameter(
                        name="aggregation",
                        type="string",
                        description="Aggregation method: 'raw', 'avg', 'max', 'min'",
                        required=False,
                        default="raw",
                        enum=["raw", "avg", "max", "min"],
                    ),
                ],
                returns="dict",
                tags=["monitoring", "metrics"],
            ),
            SkillDefinition(
                name="get_alerts",
                description="Get current system alerts",
                parameters=[
                    SkillParameter(
                        name="severity",
                        type="string",
                        description="Filter by severity level",
                        required=False,
                        enum=["info", "warning", "error", "critical", "all"],
                        default="all",
                    ),
                    SkillParameter(
                        name="status",
                        type="string",
                        description="Filter by status: 'active', 'acknowledged', 'resolved', 'all'",
                        required=False,
                        default="active",
                        enum=["active", "acknowledged", "resolved", "all"],
                    ),
                    SkillParameter(
                        name="limit",
                        type="integer",
                        description="Maximum number of alerts to return",
                        required=False,
                        default=50,
                    ),
                ],
                returns="list",
                tags=["monitoring", "alerts"],
            ),
            SkillDefinition(
                name="set_threshold",
                description="Configure alert thresholds",
                parameters=[
                    SkillParameter(
                        name="metric_name",
                        type="string",
                        description="Name of the metric",
                        required=True,
                    ),
                    SkillParameter(
                        name="warning_threshold",
                        type="float",
                        description="Warning threshold value",
                        required=False,
                    ),
                    SkillParameter(
                        name="critical_threshold",
                        type="float",
                        description="Critical threshold value",
                        required=False,
                    ),
                    SkillParameter(
                        name="enabled",
                        type="boolean",
                        description="Enable or disable the threshold",
                        required=False,
                        default=True,
                    ),
                ],
                returns="dict",
                tags=["monitoring", "configuration"],
            ),
        ]

        for skill in skills:
            self.register_skill(skill)

    # ==================== Lifecycle Methods ====================

    async def initialize(self) -> None:
        """Initialize the monitor agent"""
        self.logger.info("Initializing Monitor Agent")

        # Register capabilities
        capabilities = [
            CapabilityDefinition(
                name="health_monitoring",
                description="Monitor health of system components",
                version="1.0.0",
            ),
            CapabilityDefinition(
                name="metrics_collection",
                description="Collect and aggregate system metrics",
                version="1.0.0",
            ),
            CapabilityDefinition(
                name="alert_management",
                description="Generate and manage system alerts",
                version="1.0.0",
            ),
        ]

        for cap in capabilities:
            self.add_capability(cap)

        self._monitoring_active = True

    async def handle_message(
        self,
        message: Message,
        session: Session | None = None
    ) -> Message | None:
        """Handle incoming messages"""
        await self.audit_operation("message_received", {
            "message_type": message.type.value if hasattr(message.type, 'value') else str(message.type),
            "sender": message.sender_id,
        })

        content = message.content if isinstance(message.content, dict) else {"data": message.content}

        # Handle health report messages
        if content.get("type") == "health_report":
            await self._process_health_report(content)
            return Message(
                type=MessageType.RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                content={"status": "acknowledged"},
            )

        # Handle metrics report messages
        if content.get("type") == "metrics_report":
            await self._process_metrics_report(content)
            return Message(
                type=MessageType.RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                content={"status": "acknowledged"},
            )

        return None

    async def execute_skill(self, skill_name: str, params: dict[str, Any]) -> Any:
        """Execute monitoring skills"""
        await self.audit_operation("skill_execution", {
            "skill": skill_name,
            "params": params,
        })

        if skill_name == "health_check":
            return await self._skill_health_check(params)
        elif skill_name == "get_metrics":
            return await self._skill_get_metrics(params)
        elif skill_name == "get_alerts":
            return await self._skill_get_alerts(params)
        elif skill_name == "set_threshold":
            return await self._skill_set_threshold(params)
        else:
            raise ValueError(f"Unknown skill: {skill_name}")

    async def shutdown(self) -> None:
        """Shutdown the monitor agent"""
        self.logger.info("Shutting down Monitor Agent")
        self._monitoring_active = False

    # ==================== Skill Implementations ====================

    async def _skill_health_check(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute health_check skill"""
        target = params.get("target", "all")
        target_type = params.get("target_type", "all")
        params.get("detailed", False)

        result = {
            "timestamp": datetime.now().isoformat(),
            "checks": {},
            "summary": {
                "total": 0,
                "healthy": 0,
                "warning": 0,
                "critical": 0,
                "unknown": 0,
            },
        }

        # Check nodes
        if target_type in ("node", "all"):
            if target == "all":
                nodes_to_check = list(self._node_health.keys())
            else:
                nodes_to_check = [target] if target in self._node_health else []

            for node_id in nodes_to_check:
                health = await self._check_node_health(node_id)
                result["checks"][f"node:{node_id}"] = health
                result["summary"]["total"] += 1
                result["summary"][health["status"]] += 1

        # Check agents
        if target_type in ("agent", "all"):
            if target == "all":
                agents_to_check = list(self._agent_health.keys())
            else:
                agents_to_check = [target] if target in self._agent_health else []

            for agent_id in agents_to_check:
                health = await self._check_agent_health(agent_id)
                result["checks"][f"agent:{agent_id}"] = health
                result["summary"]["total"] += 1
                result["summary"][health["status"]] += 1

        return result

    async def _skill_get_metrics(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute get_metrics skill"""
        metric_name = params.get("metric_name", "all")
        time_range = params.get("time_range", 60)
        aggregation = params.get("aggregation", "raw")

        cutoff_time = datetime.now() - timedelta(minutes=time_range)
        result = {
            "timestamp": datetime.now().isoformat(),
            "time_range_minutes": time_range,
            "aggregation": aggregation,
            "metrics": {},
        }

        metrics_to_get = [metric_name] if metric_name != "all" else list(self._metrics_history.keys())

        for name in metrics_to_get:
            if name not in self._metrics_history:
                continue

            # Filter by time range
            filtered = [
                m for m in self._metrics_history[name]
                if datetime.fromisoformat(m["timestamp"]) >= cutoff_time
            ]

            if not filtered:
                continue

            if aggregation == "raw":
                result["metrics"][name] = filtered
            else:
                values = [m["value"] for m in filtered]
                if aggregation == "avg":
                    aggregated = sum(values) / len(values)
                elif aggregation == "max":
                    aggregated = max(values)
                elif aggregation == "min":
                    aggregated = min(values)
                else:
                    aggregated = values

                result["metrics"][name] = {
                    "aggregation": aggregation,
                    "value": aggregated,
                    "count": len(values),
                }

        return result

    async def _skill_get_alerts(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Execute get_alerts skill"""
        severity = params.get("severity", "all")
        status = params.get("status", "active")
        limit = params.get("limit", 50)

        alerts = list(self._alerts.values())

        # Filter by severity
        if severity != "all":
            alerts = [a for a in alerts if a.severity.value == severity]

        # Filter by status
        if status == "active":
            alerts = [a for a in alerts if not a.resolved and not a.acknowledged]
        elif status == "acknowledged":
            alerts = [a for a in alerts if a.acknowledged and not a.resolved]
        elif status == "resolved":
            alerts = [a for a in alerts if a.resolved]

        # Sort by creation time (newest first) and limit
        alerts = sorted(alerts, key=lambda a: a.created_at, reverse=True)[:limit]

        return [a.to_dict() for a in alerts]

    async def _skill_set_threshold(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute set_threshold skill"""
        self.require_permission(SystemAgentPermission.CONFIGURE)

        metric_name = params.get("metric_name")
        if not metric_name:
            raise ValueError("metric_name is required")

        warning_threshold = params.get("warning_threshold")
        critical_threshold = params.get("critical_threshold")
        enabled = params.get("enabled", True)

        # Update or create threshold
        if metric_name in self._thresholds:
            threshold = self._thresholds[metric_name]
            if warning_threshold is not None:
                threshold.warning_threshold = warning_threshold
            if critical_threshold is not None:
                threshold.critical_threshold = critical_threshold
            threshold.enabled = enabled
        else:
            threshold = ThresholdConfig(
                metric_name=metric_name,
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
                enabled=enabled,
            )
            self._thresholds[metric_name] = threshold

        await self.audit_operation("threshold_updated", {
            "metric_name": metric_name,
            "threshold": threshold.to_dict(),
        })

        return {
            "status": "success",
            "threshold": threshold.to_dict(),
        }

    # ==================== Internal Methods ====================

    async def _check_node_health(self, node_id: str) -> dict[str, Any]:
        """Check health of a specific node"""
        if node_id not in self._node_health:
            return {"status": "unknown", "message": "Node not monitored"}

        health_data = self._node_health[node_id]
        last_update = health_data.get("last_update")

        # Check if node is stale (no update in 5 minutes)
        if last_update:
            last_time = datetime.fromisoformat(last_update)
            if datetime.now() - last_time > timedelta(minutes=5):
                return {"status": "offline", "message": "Node is not responding"}

        return health_data

    async def _check_agent_health(self, agent_id: str) -> dict[str, Any]:
        """Check health of a specific agent"""
        if agent_id not in self._agent_health:
            return {"status": "unknown", "message": "Agent not monitored"}

        health_data = self._agent_health[agent_id]
        last_update = health_data.get("last_update")

        # Check if agent is stale (no update in 3 minutes)
        if last_update:
            last_time = datetime.fromisoformat(last_update)
            if datetime.now() - last_time > timedelta(minutes=3):
                return {"status": "offline", "message": "Agent is not responding"}

        return health_data

    async def _process_health_report(self, report: dict[str, Any]) -> None:
        """Process incoming health report"""
        source_type = report.get("source_type")
        source_id = report.get("source_id")
        health_data = report.get("health", {})

        health_data["last_update"] = datetime.now().isoformat()

        if source_type == "node":
            self._node_health[source_id] = health_data
        elif source_type == "agent":
            self._agent_health[source_id] = health_data

        # Check thresholds and generate alerts
        await self._check_thresholds(source_type, source_id, health_data)

    async def _process_metrics_report(self, report: dict[str, Any]) -> None:
        """Process incoming metrics report"""
        source_id = report.get("source_id")
        metrics = report.get("metrics", {})
        timestamp = report.get("timestamp", datetime.now().isoformat())

        for metric_name, value in metrics.items():
            if metric_name not in self._metrics_history:
                self._metrics_history[metric_name] = []

            self._metrics_history[metric_name].append({
                "source_id": source_id,
                "timestamp": timestamp,
                "value": value,
            })

            # Keep only last 1000 entries per metric
            if len(self._metrics_history[metric_name]) > 1000:
                self._metrics_history[metric_name] = self._metrics_history[metric_name][-1000:]

            # Check thresholds
            await self._check_metric_threshold(source_id, metric_name, value)

    async def _check_thresholds(
        self,
        source_type: str,
        source_id: str,
        health_data: dict[str, Any]
    ) -> None:
        """Check health data against thresholds"""
        # Check common health metrics
        metrics_to_check = ["cpu_usage", "memory_usage", "disk_usage", "error_rate"]

        for metric in metrics_to_check:
            if metric in health_data:
                await self._check_metric_threshold(source_id, metric, health_data[metric])

    async def _check_metric_threshold(
        self,
        source_id: str,
        metric_name: str,
        value: float
    ) -> None:
        """Check a metric value against its threshold"""
        if metric_name not in self._thresholds:
            return

        threshold = self._thresholds[metric_name]
        severity = threshold.check(value)

        if severity:
            await self._create_alert(
                title=f"{metric_name} threshold exceeded",
                message=f"{metric_name} value {value} exceeded {severity.value} threshold on {source_id}",
                severity=severity,
                source=source_id,
                metadata={
                    "metric_name": metric_name,
                    "value": value,
                    "warning_threshold": threshold.warning_threshold,
                    "critical_threshold": threshold.critical_threshold,
                },
            )

    async def _create_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        source: str,
        metadata: dict[str, Any] | None = None,
    ) -> Alert:
        """Create a new alert"""
        self._alert_counter += 1
        alert_id = f"alert-{self._alert_counter:06d}"

        alert = Alert(
            alert_id=alert_id,
            title=title,
            message=message,
            severity=severity,
            source=source,
            metadata=metadata,
        )

        self._alerts[alert_id] = alert

        await self.audit_operation("alert_created", {
            "alert_id": alert_id,
            "title": title,
            "severity": severity.value,
            "source": source,
        })

        self.logger.warning(f"Alert created: {title} ({severity.value})")

        return alert

    # ==================== Public Helper Methods ====================

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        if alert_id not in self._alerts:
            return False

        alert = self._alerts[alert_id]
        alert.acknowledged = True
        alert.acknowledged_by = acknowledged_by

        await self.audit_operation("alert_acknowledged", {
            "alert_id": alert_id,
            "acknowledged_by": acknowledged_by,
        })

        return True

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        if alert_id not in self._alerts:
            return False

        alert = self._alerts[alert_id]
        alert.resolved = True
        alert.resolved_at = datetime.now()

        await self.audit_operation("alert_resolved", {
            "alert_id": alert_id,
        })

        return True

    def get_monitored_targets(self) -> dict[str, list[str]]:
        """Get list of monitored nodes and agents"""
        return {
            "nodes": list(self._node_health.keys()),
            "agents": list(self._agent_health.keys()),
        }
