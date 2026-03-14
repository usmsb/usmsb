"""
Health Checker
==============

Platform health checking functionality.
"""

import asyncio
import logging
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""
    name: str
    status: HealthStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class HealthReport:
    """Complete health report."""
    platform_name: str
    overall_status: HealthStatus
    checks: list[HealthCheckResult]
    generated_at: datetime = field(default_factory=datetime.now)
    summary: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate summary after initialization."""
        self.summary = self._calculate_summary()

    def _calculate_summary(self) -> dict[str, int]:
        """Calculate summary statistics."""
        return {
            "total": len(self.checks),
            "healthy": sum(1 for c in self.checks if c.status == HealthStatus.HEALTHY),
            "degraded": sum(1 for c in self.checks if c.status == HealthStatus.DEGRADED),
            "unhealthy": sum(1 for c in self.checks if c.status == HealthStatus.UNHEALTHY),
            "unknown": sum(1 for c in self.checks if c.status == HealthStatus.UNKNOWN),
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "platform_name": self.platform_name,
            "overall_status": self.overall_status.value,
            "generated_at": self.generated_at.isoformat(),
            "summary": self.summary,
            "checks": [c.to_dict() for c in self.checks],
        }


class HealthChecker:
    """
    Platform health checker.

    Performs health checks on nodes, storage, and network connectivity.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize health checker.

        Args:
            config: Platform configuration dictionary.
        """
        self.config = config or {}
        self._logger = logging.getLogger("usmsb.health_checker")
        self._check_registry: dict[str, callable] = {}

        # Register default checks
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """Register default health checks."""
        self.register_check("disk_space", self._check_disk_space)
        self.register_check("memory", self._check_memory)
        self.register_check("network", self._check_network)

    def register_check(self, name: str, check_func: callable) -> None:
        """
        Register a custom health check.

        Args:
            name: Check name.
            check_func: Async function that returns HealthCheckResult.
        """
        self._check_registry[name] = check_func
        self._logger.debug(f"Registered health check: {name}")

    def unregister_check(self, name: str) -> None:
        """
        Unregister a health check.

        Args:
            name: Check name to remove.
        """
        if name in self._check_registry:
            del self._check_registry[name]
            self._logger.debug(f"Unregistered health check: {name}")

    async def run_all_checks(self, platform_name: str = "usmsb-platform") -> HealthReport:
        """
        Run all registered health checks.

        Args:
            platform_name: Name of the platform.

        Returns:
            Complete health report.
        """
        self._logger.info("Running health checks...")
        checks = []

        # Run registered checks
        for name, check_func in self._check_registry.items():
            try:
                result = await self._run_check(name, check_func)
                checks.append(result)
            except Exception as e:
                self._logger.error(f"Health check '{name}' failed: {e}")
                checks.append(HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Check failed: {str(e)}",
                ))

        # Determine overall status
        overall_status = self._determine_overall_status(checks)

        report = HealthReport(
            platform_name=platform_name,
            overall_status=overall_status,
            checks=checks,
        )

        self._logger.info(f"Health check complete: {overall_status.value}")
        return report

    async def _run_check(self, name: str, check_func: callable) -> HealthCheckResult:
        """
        Run a single health check with timing.

        Args:
            name: Check name.
            check_func: Check function.

        Returns:
            Health check result.
        """
        start_time = time.time()

        try:
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()

            # Ensure result is HealthCheckResult
            if not isinstance(result, HealthCheckResult):
                result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    message="Check passed",
                    details=result if isinstance(result, dict) else {},
                )

            result.duration_ms = (time.time() - start_time) * 1000
            return result

        except Exception as e:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check error: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )

    def _determine_overall_status(self, checks: list[HealthCheckResult]) -> HealthStatus:
        """Determine overall status from individual checks."""
        if not checks:
            return HealthStatus.UNKNOWN

        statuses = [c.status for c in checks]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif HealthStatus.UNKNOWN in statuses:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    async def check_node_health(self, node_config: dict[str, Any]) -> HealthCheckResult:
        """
        Check health of a specific node.

        Args:
            node_config: Node configuration.

        Returns:
            Health check result.
        """
        node_id = node_config.get("node_id", "unknown")
        host = node_config.get("host", "localhost")
        port = node_config.get("port", 8080)

        start_time = time.time()

        try:
            # Try to connect to node
            is_reachable = await self._check_port(host, port, timeout=5)

            if is_reachable:
                return HealthCheckResult(
                    name=f"node_{node_id}",
                    status=HealthStatus.HEALTHY,
                    message=f"Node {node_id} is responsive",
                    details={"host": host, "port": port},
                    duration_ms=(time.time() - start_time) * 1000,
                )
            else:
                return HealthCheckResult(
                    name=f"node_{node_id}",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Node {node_id} is not reachable",
                    details={"host": host, "port": port},
                    duration_ms=(time.time() - start_time) * 1000,
                )

        except Exception as e:
            return HealthCheckResult(
                name=f"node_{node_id}",
                status=HealthStatus.UNKNOWN,
                message=f"Check failed: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )

    async def check_storage_connection(self, storage_config: dict[str, Any]) -> HealthCheckResult:
        """
        Check storage connection.

        Args:
            storage_config: Storage configuration.

        Returns:
            Health check result.
        """
        storage_type = storage_config.get("type", "sqlite")
        start_time = time.time()

        try:
            if storage_type == "sqlite":
                path = Path(storage_config.get("path", "./data/usmsb.db"))
                parent_exists = path.parent.exists()

                if parent_exists:
                    # Check disk space
                    stat = self._get_disk_stats(path.parent)
                    return HealthCheckResult(
                        name="storage",
                        status=HealthStatus.HEALTHY,
                        message="SQLite storage accessible",
                        details={
                            "type": storage_type,
                            "path": str(path),
                            "disk_free_gb": round(stat["free"] / (1024**3), 2),
                        },
                        duration_ms=(time.time() - start_time) * 1000,
                    )
                else:
                    return HealthCheckResult(
                        name="storage",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Storage directory does not exist: {path.parent}",
                        details={"type": storage_type, "path": str(path)},
                        duration_ms=(time.time() - start_time) * 1000,
                    )

            else:
                # Network storage
                host = storage_config.get("host", "localhost")
                port = storage_config.get("port", 5432)

                is_reachable = await self._check_port(host, port, timeout=5)

                if is_reachable:
                    return HealthCheckResult(
                        name="storage",
                        status=HealthStatus.HEALTHY,
                        message=f"{storage_type} storage is reachable",
                        details={"type": storage_type, "host": host, "port": port},
                        duration_ms=(time.time() - start_time) * 1000,
                    )
                else:
                    return HealthCheckResult(
                        name="storage",
                        status=HealthStatus.UNHEALTHY,
                        message=f"{storage_type} storage is not reachable",
                        details={"type": storage_type, "host": host, "port": port},
                        duration_ms=(time.time() - start_time) * 1000,
                    )

        except Exception as e:
            return HealthCheckResult(
                name="storage",
                status=HealthStatus.UNKNOWN,
                message=f"Storage check failed: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )

    async def check_network_connectivity(self, targets: list[dict[str, Any]]) -> HealthCheckResult:
        """
        Check network connectivity to targets.

        Args:
            targets: List of target configurations.

        Returns:
            Health check result.
        """
        start_time = time.time()
        results = []

        for target in targets:
            host = target.get("host", "localhost")
            port = target.get("port", 80)

            try:
                is_reachable = await self._check_port(host, port, timeout=3)
                results.append({
                    "host": host,
                    "port": port,
                    "reachable": is_reachable,
                })
            except Exception as e:
                results.append({
                    "host": host,
                    "port": port,
                    "reachable": False,
                    "error": str(e),
                })

        reachable_count = sum(1 for r in results if r["reachable"])
        total_count = len(results)

        if total_count == 0:
            status = HealthStatus.UNKNOWN
            message = "No network targets configured"
        elif reachable_count == total_count:
            status = HealthStatus.HEALTHY
            message = f"All {total_count} targets reachable"
        elif reachable_count > 0:
            status = HealthStatus.DEGRADED
            message = f"{reachable_count}/{total_count} targets reachable"
        else:
            status = HealthStatus.UNHEALTHY
            message = "No targets reachable"

        return HealthCheckResult(
            name="network",
            status=status,
            message=message,
            details={"targets": results},
            duration_ms=(time.time() - start_time) * 1000,
        )

    async def _check_port(self, host: str, port: int, timeout: float = 5) -> bool:
        """
        Check if a port is reachable.

        Args:
            host: Host address.
            port: Port number.
            timeout: Connection timeout.

        Returns:
            True if port is reachable.
        """
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (TimeoutError, OSError):
            return False

    async def _check_disk_space(self) -> HealthCheckResult:
        """Check disk space availability."""
        try:
            stat = self._get_disk_stats(Path.cwd())

            free_gb = stat["free"] / (1024**3)
            total_gb = stat["total"] / (1024**3)
            used_percent = (stat["used"] / stat["total"]) * 100

            if used_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"Disk nearly full: {used_percent:.1f}% used"
            elif used_percent > 80:
                status = HealthStatus.DEGRADED
                message = f"Disk usage high: {used_percent:.1f}% used"
            else:
                status = HealthStatus.HEALTHY
                message = f"Disk space OK: {free_gb:.1f} GB free"

            return HealthCheckResult(
                name="disk_space",
                status=status,
                message=message,
                details={
                    "free_gb": round(free_gb, 2),
                    "total_gb": round(total_gb, 2),
                    "used_percent": round(used_percent, 1),
                },
            )

        except Exception as e:
            return HealthCheckResult(
                name="disk_space",
                status=HealthStatus.UNKNOWN,
                message=f"Could not check disk space: {str(e)}",
            )

    async def _check_memory(self) -> HealthCheckResult:
        """Check memory availability."""
        try:
            import psutil

            memory = psutil.virtual_memory()
            used_percent = memory.percent
            available_gb = memory.available / (1024**3)

            if used_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = f"Memory nearly exhausted: {used_percent:.1f}% used"
            elif used_percent > 80:
                status = HealthStatus.DEGRADED
                message = f"Memory usage high: {used_percent:.1f}% used"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory OK: {available_gb:.1f} GB available"

            return HealthCheckResult(
                name="memory",
                status=status,
                message=message,
                details={
                    "available_gb": round(available_gb, 2),
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_percent": round(used_percent, 1),
                },
            )

        except ImportError:
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message="psutil not available for memory check",
            )
        except Exception as e:
            return HealthCheckResult(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message=f"Could not check memory: {str(e)}",
            )

    async def _check_network(self) -> HealthCheckResult:
        """Check basic network connectivity."""
        try:
            # Try to resolve a well-known host
            socket.gethostbyname("google.com")
            return HealthCheckResult(
                name="network",
                status=HealthStatus.HEALTHY,
                message="Network connectivity OK",
                details={"dns": "reachable"},
            )
        except socket.gaierror:
            return HealthCheckResult(
                name="network",
                status=HealthStatus.UNHEALTHY,
                message="No network connectivity",
                details={"dns": "unreachable"},
            )
        except Exception as e:
            return HealthCheckResult(
                name="network",
                status=HealthStatus.UNKNOWN,
                message=f"Network check failed: {str(e)}",
            )

    def _get_disk_stats(self, path: Path) -> dict[str, int]:
        """Get disk statistics for a path."""
        import shutil
        stat = shutil.disk_usage(path)
        return {
            "total": stat.total,
            "used": stat.used,
            "free": stat.free,
        }
