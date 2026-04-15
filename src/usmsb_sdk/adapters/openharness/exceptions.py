# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
# OpenHarness Adapter Exceptions

"""
Custom exceptions for the OpenHarness adapter layer.

All exceptions inherit from OpenHarnessAdapterError and provide
structured error information for debugging and error handling.

Exception Hierarchy:
    OpenHarnessAdapterError (base)
    ├── ToolExecutionError
    ├── PermissionDeniedError
    ├── MemoryAccessError
    ├── SwarmError
    │   ├── TeamCreationError
    │   ├── AgentRegistrationError
    │   └── TaskAssignmentError
    ├── QueryError
    ├── HookError
    │   ├── PreHookError
    │   └── PostHookError
    └── AgentSpawnError
"""

from __future__ import annotations


class OpenHarnessAdapterError(Exception):
    """
    Base exception for all OpenHarness adapter errors.
    
    Attributes:
        message: Human-readable error message
        details: Additional error context (dict)
        tool_name: Name of the tool involved (if applicable)
        agent_id: ID of the agent involved (if applicable)
    """

    def __init__(
        self,
        message: str,
        details: dict | None = None,
        tool_name: str | None = None,
        agent_id: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.tool_name = tool_name
        self.agent_id = agent_id

    def __repr__(self) -> str:
        parts = [f"OpenHarnessAdapterError({self.message!r}"]
        if self.tool_name:
            parts.append(f"tool_name={self.tool_name!r}")
        if self.agent_id:
            parts.append(f"agent_id={self.agent_id!r}")
        parts.append(")")
        return " ".join(parts)

    def to_dict(self) -> dict:
        """Convert exception to dictionary for serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "tool_name": self.tool_name,
            "agent_id": self.agent_id,
        }


class ToolExecutionError(OpenHarnessAdapterError):
    """
    Raised when tool execution fails.
    
    Causes:
        - Tool not found in registry
        - Tool timeout
        - Tool validation failure
        - Underlying tool implementation error
    """

    def __init__(
        self,
        tool_name: str,
        message: str,
        details: dict | None = None,
        agent_id: str | None = None,
    ):
        super().__init__(
            message=f"Tool execution failed for '{tool_name}': {message}",
            details=details,
            tool_name=tool_name,
            agent_id=agent_id,
        )
        self.tool_name = tool_name


class PermissionDeniedError(OpenHarnessAdapterError):
    """
    Raised when a tool execution is denied by permission checker.
    
    Causes:
        - Tool not in allowed list
        - Path access denied
        - Command matches deny pattern
        - Permission mode blocks action
    """

    def __init__(
        self,
        tool_name: str,
        reason: str,
        requires_confirmation: bool = False,
        details: dict | None = None,
        agent_id: str | None = None,
    ):
        super().__init__(
            message=f"Permission denied for '{tool_name}': {reason}",
            details={
                **(details or {}),
                "requires_confirmation": requires_confirmation,
                "reason": reason,
            },
            tool_name=tool_name,
            agent_id=agent_id,
        )
        self.tool_name = tool_name
        self.reason = reason
        self.requires_confirmation = requires_confirmation


class MemoryAccessError(OpenHarnessAdapterError):
    """
    Raised when memory operations fail.
    
    Causes:
        - Memory file not found
        - Memory corruption
        - Disk I/O error
        - Memory limit exceeded
    """

    def __init__(
        self,
        operation: str,
        message: str,
        path: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(
            message=f"Memory {operation} failed: {message}",
            details={**(details or {}), "operation": operation, "path": path},
        )
        self.operation = operation
        self.path = path


class SwarmError(OpenHarnessAdapterError):
    """
    Base exception for swarm coordination errors.
    """
    pass


class TeamCreationError(SwarmError):
    """
    Raised when team creation fails.
    
    Causes:
        - Team name already exists
        - Invalid team configuration
        - Storage write failure
    """

    def __init__(
        self,
        team_name: str,
        message: str,
        details: dict | None = None,
    ):
        super().__init__(
            message=f"Team creation failed for '{team_name}': {message}",
            details={**(details or {}), "team_name": team_name},
        )
        self.team_name = team_name


class AgentRegistrationError(SwarmError):
    """
    Raised when agent registration fails.
    
    Causes:
        - Agent ID already exists
        - Invalid agent capabilities
        - Team not found
    """

    def __init__(
        self,
        agent_id: str,
        message: str,
        team_name: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(
            message=f"Agent registration failed for '{agent_id}': {message}",
            details={**(details or {}), "agent_id": agent_id, "team_name": team_name},
        )
        self.agent_id = agent_id
        self.team_name = team_name


class TaskAssignmentError(SwarmError):
    """
    Raised when task assignment fails.
    
    Causes:
        - Task validation failure
        - Assignee not found
        - Team not found
        - Task queue full
    """

    def __init__(
        self,
        task_id: str,
        message: str,
        team_name: str | None = None,
        assignee_id: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(
            message=f"Task assignment failed for '{task_id}': {message}",
            details={
                **(details or {}),
                "task_id": task_id,
                "team_name": team_name,
                "assignee_id": assignee_id,
            },
        )
        self.task_id = task_id
        self.team_name = team_name
        self.assignee_id = assignee_id


class QueryError(OpenHarnessAdapterError):
    """
    Raised when LLM query execution fails.
    
    Causes:
        - API key invalid
        - Network error
        - Model not found
        - Token limit exceeded
        - Context window overflow
    """

    def __init__(
        self,
        message: str,
        model: str | None = None,
        details: dict | None = None,
        agent_id: str | None = None,
    ):
        super().__init__(
            message=f"Query execution failed: {message}",
            details={**(details or {}), "model": model},
            agent_id=agent_id,
        )
        self.model = model


class HookError(OpenHarnessAdapterError):
    """
    Base exception for hook-related errors.
    """
    pass


class PreHookError(HookError):
    """
    Raised when a pre-tool hook fails.
    
    Causes:
        - Hook timeout
        - Hook execution error
        - Hook validation failure
    """

    def __init__(
        self,
        tool_name: str,
        hook_name: str,
        message: str,
        blocked: bool = False,
        details: dict | None = None,
    ):
        super().__init__(
            message=f"Pre-hook '{hook_name}' failed for '{tool_name}': {message}",
            details={
                **(details or {}),
                "hook_name": hook_name,
                "blocked": blocked,
            },
            tool_name=tool_name,
        )
        self.tool_name = tool_name
        self.hook_name = hook_name
        self.blocked = blocked


class PostHookError(HookError):
    """
    Raised when a post-tool hook fails.
    
    Causes:
        - Hook timeout
        - Hook execution error
        - Hook processing failure
    """

    def __init__(
        self,
        tool_name: str,
        hook_name: str,
        message: str,
        details: dict | None = None,
    ):
        super().__init__(
            message=f"Post-hook '{hook_name}' failed for '{tool_name}': {message}",
            details={
                **(details or {}),
                "hook_name": hook_name,
            },
            tool_name=tool_name,
        )
        self.tool_name = tool_name
        self.hook_name = hook_name


class AgentSpawnError(OpenHarnessAdapterError):
    """
    Raised when agent spawning fails.
    
    Causes:
        - Spawn configuration invalid
        - Backend allocation failure
        - Init script error
        - Resource limit exceeded
    """

    def __init__(
        self,
        agent_type: str,
        message: str,
        details: dict | None = None,
    ):
        super().__init__(
            message=f"Agent spawn failed for type '{agent_type}': {message}",
            details={**(details or {}), "agent_type": agent_type},
        )
        self.agent_type = agent_type


class ConfigurationError(OpenHarnessAdapterError):
    """
    Raised when configuration is invalid or missing.
    
    Causes:
        - Required config missing
        - Config validation failure
        - Environment variable not set
    """

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        details: dict | None = None,
    ):
        super().__init__(
            message=f"Configuration error: {message}",
            details={**(details or {}), "config_key": config_key},
        )
        self.config_key = config_key


class OpenHarnessNotAvailableError(OpenHarnessAdapterError):
    """
    Raised when OpenHarness package is not installed.
    
    This is a critical error that prevents any OH integration.
    Resolution: pip install openharness-ai
    """

    def __init__(self, message: str = "OpenHarness is not installed"):
        super().__init__(
            message=message,
            details={
                "resolution": "pip install openharness-ai",
                "package_name": "openharness-ai",
            },
        )
