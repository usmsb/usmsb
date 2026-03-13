"""
Base System Agent Module

Provides the foundation class for all system-level agents in the USMSB SDK platform.
System agents have elevated privileges and access to platform-level resources.

Features:
    - System-level permission management
    - Platform configuration access
    - Enhanced security checks
    - Resource access control
"""

from abc import abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import asyncio
import logging

from usmsb_sdk.agent_sdk.base_agent import BaseAgent, AgentState
from usmsb_sdk.agent_sdk.agent_config import (
    AgentConfig,
    CapabilityDefinition,
    SkillDefinition,
    SkillParameter,
)
from usmsb_sdk.agent_sdk.communication import Message, MessageType, Session


class SystemAgentPermission(Enum):
    """System agent permission levels"""

    READ_ONLY = "read_only"  # Read system data only
    MONITOR = "monitor"  # Monitoring and alerting
    CONFIGURE = "configure"  # Configuration changes
    CONTROL = "control"  # Start/stop/restart agents
    ADMIN = "admin"  # Full administrative access
    SUPERUSER = "superuser"  # Unlimited access (platform internal)


class SystemAgentConfig:
    """
    Configuration for system agents.

    Attributes:
        permission_level: The permission level for this system agent
        allowed_resources: Set of resources this agent can access
        rate_limit: Maximum operations per minute
        audit_enabled: Whether to audit all operations
        audit_log_path: Path to audit log file
    """

    def __init__(
        self,
        permission_level: SystemAgentPermission = SystemAgentPermission.READ_ONLY,
        allowed_resources: Optional[Set[str]] = None,
        rate_limit: int = 1000,
        audit_enabled: bool = True,
        audit_log_path: Optional[str] = None,
    ):
        """
        Initialize system agent configuration.

        Args:
            permission_level: Permission level for the agent
            allowed_resources: Resources the agent can access (None = all)
            rate_limit: Max operations per minute
            audit_enabled: Enable operation auditing
            audit_log_path: Path for audit logs
        """
        self.permission_level = permission_level
        self.allowed_resources = allowed_resources or set()
        self.rate_limit = rate_limit
        self.audit_enabled = audit_enabled
        self.audit_log_path = audit_log_path

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "permission_level": self.permission_level.value,
            "allowed_resources": list(self.allowed_resources),
            "rate_limit": self.rate_limit,
            "audit_enabled": self.audit_enabled,
            "audit_log_path": self.audit_log_path,
        }


class BaseSystemAgent(BaseAgent):
    """
    Abstract base class for system-level agents.

    System agents are built-in agents that provide essential platform services.
    They inherit from BaseAgent and add system-level capabilities including:

    - Permission-based access control
    - Platform resource management
    - Enhanced auditing and logging
    - System configuration access

    Subclasses must implement:
        - initialize(): Custom initialization logic
        - handle_message(): Message handling logic
        - execute_skill(): Skill execution logic
        - shutdown(): Cleanup logic

    Example:
        class MySystemAgent(BaseSystemAgent):
            async def initialize(self):
                self.logger.info("Initializing system agent")
                # Setup system resources

            async def handle_message(self, message, session):
                # Handle system messages
                pass

            async def execute_skill(self, skill_name, params):
                # Execute system skills
                pass

            async def shutdown(self):
                # Cleanup system resources
                pass
    """

    # System agent type identifier
    SYSTEM_AGENT_TYPE: str = "base_system"

    def __init__(
        self,
        config: AgentConfig,
        system_config: Optional[SystemAgentConfig] = None,
    ):
        """
        Initialize the system agent.

        Args:
            config: Standard agent configuration
            system_config: System-specific configuration
        """
        super().__init__(config)

        # System configuration
        self._system_config = system_config or SystemAgentConfig()
        self._permission_level = self._system_config.permission_level
        self._allowed_resources = self._system_config.allowed_resources

        # System-level metrics
        self._system_metrics = {
            "operations_count": 0,
            "permission_denied_count": 0,
            "last_audit_time": None,
            "resource_access_count": {},
        }

        # Audit log
        self._audit_log: List[Dict[str, Any]] = []
        self._audit_lock = asyncio.Lock()

        # Register system capabilities
        self._register_system_capabilities()

        self.logger = logging.getLogger(f"system_agent.{self.name}")

    @property
    def permission_level(self) -> SystemAgentPermission:
        """Get current permission level"""
        return self._permission_level

    @property
    def system_config(self) -> SystemAgentConfig:
        """Get system configuration"""
        return self._system_config

    def _register_system_capabilities(self) -> None:
        """Register default system capabilities"""
        system_capability = CapabilityDefinition(
            name="system_access",
            description="Access to system-level resources",
            category="system",
            version="1.0.0",
        )
        self.add_capability(system_capability)

    # ==================== Permission Management ====================

    def check_permission(self, required_level: SystemAgentPermission) -> bool:
        """
        Check if the agent has sufficient permissions.

        Args:
            required_level: Required permission level

        Returns:
            True if permission is granted
        """
        permission_hierarchy = {
            SystemAgentPermission.READ_ONLY: 1,
            SystemAgentPermission.MONITOR: 2,
            SystemAgentPermission.CONFIGURE: 3,
            SystemAgentPermission.CONTROL: 4,
            SystemAgentPermission.ADMIN: 5,
            SystemAgentPermission.SUPERUSER: 6,
        }

        current_level = permission_hierarchy.get(self._permission_level, 0)
        required = permission_hierarchy.get(required_level, 0)

        return current_level >= required

    def require_permission(self, required_level: SystemAgentPermission) -> None:
        """
        Require a specific permission level, raising an exception if not met.

        Args:
            required_level: Required permission level

        Raises:
            PermissionError: If permission is denied
        """
        if not self.check_permission(required_level):
            self._system_metrics["permission_denied_count"] += 1
            raise PermissionError(
                f"Permission denied. Required: {required_level.value}, "
                f"Current: {self._permission_level.value}"
            )

    def can_access_resource(self, resource: str) -> bool:
        """
        Check if the agent can access a specific resource.

        Args:
            resource: Resource identifier

        Returns:
            True if access is allowed
        """
        # If no restrictions, allow all
        if not self._allowed_resources:
            return True

        # Check if resource matches any allowed pattern
        for allowed in self._allowed_resources:
            if resource == allowed or resource.startswith(f"{allowed}."):
                return True
            if allowed.endswith("*") and resource.startswith(allowed[:-1]):
                return True

        return False

    def require_resource_access(self, resource: str) -> None:
        """
        Require access to a specific resource.

        Args:
            resource: Resource identifier

        Raises:
            PermissionError: If resource access is denied
        """
        if not self.can_access_resource(resource):
            self._system_metrics["permission_denied_count"] += 1
            raise PermissionError(f"Access denied to resource: {resource}")

    # ==================== Auditing ====================

    async def audit_operation(
        self,
        operation: str,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
    ) -> None:
        """
        Record an operation in the audit log.

        Args:
            operation: Operation name
            details: Operation details
            success: Whether the operation succeeded
        """
        if not self._system_config.audit_enabled:
            return

        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id,
            "agent_type": self.SYSTEM_AGENT_TYPE,
            "operation": operation,
            "details": details or {},
            "success": success,
            "permission_level": self._permission_level.value,
        }

        async with self._audit_lock:
            self._audit_log.append(audit_entry)
            self._system_metrics["last_audit_time"] = datetime.now()
            self._system_metrics["operations_count"] += 1

            # Track resource access
            if "resource" in details:
                resource = details["resource"]
                self._system_metrics["resource_access_count"][resource] = (
                    self._system_metrics["resource_access_count"].get(resource, 0) + 1
                )

        self.logger.debug(f"Audited operation: {operation}")

    async def get_audit_log(
        self,
        limit: int = 100,
        operation_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get audit log entries.

        Args:
            limit: Maximum number of entries to return
            operation_filter: Filter by operation name

        Returns:
            List of audit log entries
        """
        async with self._audit_lock:
            entries = list(self._audit_log)

        if operation_filter:
            entries = [e for e in entries if e["operation"] == operation_filter]

        return entries[-limit:]

    # ==================== System Metrics ====================

    @property
    def system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics"""
        return {
            **self._system_metrics,
            "permission_level": self._permission_level.value,
            "audit_enabled": self._system_config.audit_enabled,
            "audit_log_size": len(self._audit_log),
        }

    def increment_operation_count(self) -> None:
        """Increment the operation counter"""
        self._system_metrics["operations_count"] += 1

    # ==================== Rate Limiting ====================

    async def check_rate_limit(self) -> bool:
        """
        Check if the agent is within rate limits.

        Returns:
            True if within rate limits
        """
        # Simple implementation - can be enhanced with sliding window
        return self._system_metrics["operations_count"] < self._system_config.rate_limit

    async def require_rate_limit(self) -> None:
        """
        Require rate limit compliance.

        Raises:
            RuntimeError: If rate limit exceeded
        """
        if not await self.check_rate_limit():
            raise RuntimeError("Rate limit exceeded")

    # ==================== Abstract Methods ====================

    @abstractmethod
    async def initialize(self) -> None:
        """
        User-defined initialization logic for system agents.

        Override this method to:
        - Initialize system resources
        - Setup platform connections
        - Register system event handlers
        """
        pass

    @abstractmethod
    async def handle_message(
        self, message: Message, session: Optional[Session] = None
    ) -> Optional[Message]:
        """
        Handle incoming messages.

        Args:
            message: The incoming message
            session: Optional session context

        Returns:
            Optional response message
        """
        pass

    @abstractmethod
    async def execute_skill(self, skill_name: str, params: Dict[str, Any]) -> Any:
        """
        Execute a skill by name.

        Args:
            skill_name: Name of the skill to execute
            params: Parameters for the skill

        Returns:
            Skill execution result
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        User-defined cleanup logic.

        Override this method to:
        - Release system resources
        - Save state
        - Close platform connections
        """
        pass

    # ==================== Serialization ====================

    def to_dict(self) -> Dict[str, Any]:
        """Convert system agent info to dictionary"""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "system_agent_type": self.SYSTEM_AGENT_TYPE,
                "system_config": self._system_config.to_dict(),
                "system_metrics": self.system_metrics,
            }
        )
        return base_dict

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}("
            f"id={self.agent_id}, "
            f"name={self.name}, "
            f"permission={self._permission_level.value}, "
            f"state={self._state.value})>"
        )
