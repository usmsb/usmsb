# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
# PermissionAdapter - OpenHarness Permission System Integration

"""
OpenHarness PermissionAdapter for USMSB.

This adapter wraps the OpenHarness PermissionChecker to provide:
- Multi-level permission evaluation
- PreTool and PostTool hooks
- Path-based access control
- Command pattern matching
- USMSB-specific permission policies

The adapter extends OH's permission system with USMSB's
value-based access control for agent actions.

Usage:
    >>> adapter = PermissionAdapter(checker=oh_checker)
    >>> decision = adapter.check_tool_permission("agent_001", "file_read", {"path": "/tmp/test"})
    >>> if decision.allowed:
    ...     result = await tool_adapter.execute("file_read", path="/tmp/test")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Protocol

try:
    from openharness.permissions.checker import PermissionChecker, PermissionDecision as OHPermissionDecision
    from openharness.permissions.modes import PermissionMode as OHPermissionMode
    from openharness.config.settings import PermissionSettings
    OPENHARNESS_AVAILABLE = True
except ImportError:
    OPENHARNESS_AVAILABLE = False
    PermissionChecker = None
    OHPermissionDecision = None
    OHPermissionMode = None
    PermissionSettings = None

from usmsb_sdk.adapters.openharness.config import PermissionConfig, PermissionMode
from usmsb_sdk.adapters.openharness.exceptions import (
    PermissionDeniedError,
    ConfigurationError,
    OpenHarnessNotAvailableError,
)

log = logging.getLogger(__name__)


@dataclass
class PermissionDecision:
    """
    Result of a permission check.
    
    Attributes:
        allowed: Whether the action is permitted
        reason: Human-readable explanation
        requires_confirmation: If True, user must confirm before proceeding
        blocked: If True, this decision blocks the action entirely
        policy_matched: Name of the policy that matched (if any)
    """
    allowed: bool
    reason: str = ""
    requires_confirmation: bool = False
    blocked: bool = False
    policy_matched: str | None = None


@dataclass
class PathRule:
    """
    A path-based permission rule.
    
    Attributes:
        pattern: Glob pattern for path matching
        allow: True = allow, False = deny
        tool_name: Tool this rule applies to (None = all tools)
        description: Human-readable description
    """
    pattern: str
    allow: bool
    tool_name: str | None = None
    description: str = ""


@dataclass
class Policy:
    """
    A named permission policy.
    
    Policies combine rules, tool restrictions, and conditions
    into reusable access control configurations.
    """
    name: str
    description: str = ""
    rules: list[PathRule] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    denied_tools: list[str] = field(default_factory=list)
    conditions: dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher = evaluated first


class PreHookCallable(Protocol):
    """Protocol for pre-permission hooks."""
    async def __call__(
        self,
        agent_id: str,
        tool_name: str,
        params: dict[str, Any],
    ) -> PermissionDecision | None:
        """
        Check permission.
        
        Returns:
            PermissionDecision to override, or None to continue with normal checks
        """
        ...


class PostHookCallable(Protocol):
    """Protocol for post-permission hooks."""
    async def __call__(
        self,
        agent_id: str,
        tool_name: str,
        params: dict[str, Any],
        decision: PermissionDecision,
        result: Any = None,
    ) -> None:
        """
        Post-permission hook.
        
        Args:
            agent_id: Agent requesting access
            tool_name: Tool being accessed
            params: Tool parameters
            decision: Permission decision made
            result: Execution result (if executed)
        """
        ...


class PermissionAdapter:
    """
    OpenHarness PermissionChecker Adapter.
    
    This adapter wraps OH's PermissionChecker and extends it with:
    - USMSB-specific permission policies
    - PreTool and PostTool hooks
    - Path-based access control
    - Agent-specific permission profiles
    
    The adapter supports multiple permission modes:
    - FULL_AUTO: Allow all actions
    - MODERATE: Require confirmation for mutating tools
    - PLAN: Block mutating tools until plan mode exits
    
    Example:
        >>> from openharness.config.settings import PermissionSettings
        >>> settings = PermissionSettings()
        >>> checker = PermissionChecker(settings)
        >>> adapter = PermissionAdapter(checker=checker)
        >>> 
        >>> # Check a tool
        >>> decision = adapter.check_tool_permission(
        ...     agent_id="agent_001",
        ...     tool_name="file_read",
        ...     params={"path": "/tmp/test.txt"}
        ... )
        >>> print(f"Allowed: {decision.allowed}")
    """

    def __init__(
        self,
        checker: PermissionChecker | None = None,
        config: PermissionConfig | None = None,
        cwd: str | Path = ".",
    ):
        """
        Initialize PermissionAdapter.
        
        Args:
            checker: OH PermissionChecker instance. If None, creates one from config.
            config: Permission configuration
            cwd: Current working directory for path resolution
        """
        if not OPENHARNESS_AVAILABLE:
            raise OpenHarnessNotAvailableError()
        
        self._config = config or PermissionConfig()
        self._cwd = Path(cwd).resolve()
        
        # Create OH checker if not provided
        if checker is None:
            settings = self._build_oh_settings()
            self._checker = PermissionChecker(settings)
        else:
            self._checker = checker
        
        # USMSB-specific extensions
        self._policies: dict[str, Policy] = {}
        self._agent_profiles: dict[str, dict[str, Any]] = {}
        self._pre_hooks: list[PreHookCallable] = []
        self._post_hooks: list[PostHookCallable] = []
        self._path_rules: list[PathRule] = []
        
        # Build USMSB-specific path rules
        self._build_default_rules()
        
        log.info("PermissionAdapter initialized with mode: %s", self._config.mode)

    @property
    def checker(self) -> PermissionChecker:
        """Expose the verified OpenHarness checker to QueryEngine/ToolAdapter."""

        return self._checker

    def _build_oh_settings(self) -> PermissionSettings:
        """Build OH PermissionSettings from USMSB config."""
        # Import here to avoid circular reference
        from openharness.permissions.modes import PermissionMode as OHModes
        
        # Map our config mode to OH mode
        mode_map = {
            PermissionMode.FULL_AUTO: OHModes.FULL_AUTO,
            PermissionMode.MODERATE: OHModes.DEFAULT,
            PermissionMode.PLAN: OHModes.PLAN,
        }
        
        return PermissionSettings(
            mode=mode_map.get(self._config.mode, OHModes.DEFAULT),
            denied_tools=self._config.denied_tools,
            allowed_tools=self._config.allowed_tools,
            denied_commands=self._config.denied_commands,
            path_rules=self._config.path_rules,
        )

    def _build_default_rules(self) -> None:
        """Build default USMSB-specific path rules."""
        # Deny access to credential files
        self._path_rules.extend([
            PathRule(
                pattern="*/.ssh/*",
                allow=False,
                description="Deny SSH key access"
            ),
            PathRule(
                pattern="*/.aws/credentials",
                allow=False,
                description="Deny AWS credentials"
            ),
            PathRule(
                pattern="*/.config/gcloud/*",
                allow=False,
                description="Deny GCP credentials"
            ),
            PathRule(
                pattern="*/.openharness/credentials.json",
                allow=False,
                description="Deny OH credentials"
            ),
        ])
        
        # Default allow for USMSB working directories
        usmsb_paths = [
            "*/usmsb/*",
            "*/projects/*",
            "/tmp/*",
        ]
        for pattern in usmsb_paths:
            self._path_rules.append(PathRule(
                pattern=pattern,
                allow=True,
                description="Allow USMSB working directories"
            ))

    def check_tool_permission(
        self,
        agent_id: str,
        tool_name: str,
        params: dict[str, Any] | None = None,
        execute_pre_hooks: bool = True,
    ) -> PermissionDecision:
        """
        Check if an agent has permission to execute a tool.
        
        This method:
        1. Runs pre-hooks (if any return a decision, use it)
        2. Checks USMSB-specific policies
        3. Delegates to OH PermissionChecker
        4. Returns combined decision
        
        Args:
            agent_id: ID of the agent requesting access
            tool_name: Name of the tool to execute
            params: Tool parameters (for path/command checking)
            execute_pre_hooks: Whether to run pre-hooks
            
        Returns:
            PermissionDecision with allowed status and reason
        """
        params = params or {}
        
        # Execute pre-hooks
        if execute_pre_hooks:
            for hook in self._pre_hooks:
                try:
                    result = hook(agent_id, tool_name, params)
                    if result is not None and not result.allowed:
                        return result
                except Exception as e:
                    log.warning("Pre-hook failed: %s", e)
        
        # Check agent-specific profile
        agent_profile = self._agent_profiles.get(agent_id, {})
        if agent_denied := agent_profile.get("denied_tools", []):
            if tool_name in agent_denied:
                return PermissionDecision(
                    allowed=False,
                    reason=f"Tool '{tool_name}' is denied for agent '{agent_id}'",
                    policy_matched="agent_profile",
                )
        
        if agent_allowed := agent_profile.get("allowed_tools", []):
            if tool_name in agent_allowed:
                return PermissionDecision(
                    allowed=True,
                    reason=f"Tool '{tool_name}' is explicitly allowed for agent '{agent_id}'",
                    policy_matched="agent_profile",
                )
        
        # Check USMSB path rules
        if path := params.get("path") or params.get("file_path"):
            decision = self._check_path_rules(tool_name, path)
            if decision is not None:
                return decision
        
        # Check command patterns
        if command := params.get("command"):
            decision = self._check_command_rules(command)
            if decision is not None:
                return decision
        
        # Delegate to OH checker
        try:
            oh_decision = self._checker.evaluate(
                tool_name=tool_name,
                is_read_only=params.get("is_read_only", False),
                file_path=params.get("path") or params.get("file_path"),
                command=params.get("command"),
            )
            
            return PermissionDecision(
                allowed=oh_decision.allowed,
                reason=oh_decision.reason,
                requires_confirmation=oh_decision.requires_confirmation,
                blocked=False,
                policy_matched="oh_checker",
            )
        except Exception as e:
            log.error("OH permission check failed: %s", e)
            return PermissionDecision(
                allowed=False,
                reason=f"Permission check error: {e}",
                blocked=True,
                policy_matched="error",
            )

    def check_path_permission(
        self,
        agent_id: str,
        path: str,
        operation: str = "read",
    ) -> PermissionDecision:
        """
        Check if an agent has permission to access a path.
        
        Args:
            agent_id: ID of the agent
            path: Path to check
            operation: Operation type ("read", "write", "execute")
            
        Returns:
            PermissionDecision
        """
        # Check path rules
        decision = self._check_path_rules(None, path)
        if decision is not None:
            return decision
        
        # Delegate to OH
        try:
            # OH doesn't have direct path checking, use tool-level check
            tool_name = "file_write" if operation == "write" else "file_read"
            oh_decision = self._checker.evaluate(
                tool_name=tool_name,
                is_read_only=(operation == "read"),
                file_path=path,
            )
            
            return PermissionDecision(
                allowed=oh_decision.allowed,
                reason=oh_decision.reason,
                requires_confirmation=oh_decision.requires_confirmation,
                policy_matched="oh_path_check",
            )
        except Exception as e:
            return PermissionDecision(
                allowed=False,
                reason=f"Path permission check error: {e}",
                blocked=True,
            )

    def _check_path_rules(
        self,
        tool_name: str | None,
        path: str,
    ) -> PermissionDecision | None:
        """
        Check path against USMSB-specific rules.
        
        Returns:
            PermissionDecision if a rule matched, None otherwise
        """
        import fnmatch
        
        normalized = str(Path(path).resolve())
        
        for rule in self._path_rules:
            # Check tool restriction
            if rule.tool_name and tool_name and rule.tool_name != tool_name:
                continue
            
            # Check pattern
            if fnmatch.fnmatch(normalized, rule.pattern) or fnmatch.fnmatch(
                normalized.rstrip("/"), rule.pattern.rstrip("/")
            ):
                return PermissionDecision(
                    allowed=rule.allow,
                    reason=rule.description or f"Path rule: {rule.pattern}",
                    policy_matched=f"path_rule:{rule.pattern}",
                )
        
        return None

    def _check_command_rules(self, command: str) -> PermissionDecision | None:
        """Check command against deny patterns."""
        import fnmatch
        
        for pattern in self._config.denied_commands:
            if fnmatch.fnmatch(command, pattern):
                return PermissionDecision(
                    allowed=False,
                    reason=f"Command matches deny pattern: {pattern}",
                    policy_matched=f"command_deny:{pattern}",
                )
        
        return None

    async def execute_post_hooks(
        self,
        agent_id: str,
        tool_name: str,
        params: dict[str, Any],
        decision: PermissionDecision,
        result: Any = None,
    ) -> None:
        """
        Execute post-permission hooks.
        
        Args:
            agent_id: Agent ID
            tool_name: Tool name
            params: Tool parameters
            decision: Permission decision
            result: Execution result (if executed)
        """
        for hook in self._post_hooks:
            try:
                await hook(agent_id, tool_name, params, decision, result)
            except Exception as e:
                log.warning("Post-hook failed: %s", e)

    def add_policy(self, policy: Policy) -> None:
        """
        Add a named permission policy.
        
        Args:
            policy: Policy to add
        """
        self._policies[policy.name] = policy
        log.info("Added permission policy: %s", policy.name)

    def get_policy(self, name: str) -> Policy | None:
        """Get a policy by name."""
        return self._policies.get(name)

    def set_agent_profile(
        self,
        agent_id: str,
        allowed_tools: list[str] | None = None,
        denied_tools: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Set permission profile for an agent.
        
        Args:
            agent_id: Agent ID
            allowed_tools: Tools this agent is allowed to use
            denied_tools: Tools this agent is denied from using
            **kwargs: Additional profile settings
        """
        self._agent_profiles[agent_id] = {
            **(self._agent_profiles.get(agent_id, {})),
            "allowed_tools": allowed_tools or [],
            "denied_tools": denied_tools or [],
            **kwargs,
        }
        log.info("Updated permission profile for agent: %s", agent_id)

    def register_pre_hook(self, hook: PreHookCallable) -> None:
        """Register a pre-permission hook."""
        self._pre_hooks.append(hook)
        log.debug("Registered pre-hook: %s", getattr(hook, "__name__", repr(hook)))

    def register_post_hook(self, hook: PostHookCallable) -> None:
        """Register a post-permission hook."""
        self._post_hooks.append(hook)
        log.debug("Registered post-hook: %s", getattr(hook, "__name__", repr(hook)))

    def add_path_rule(
        self,
        pattern: str,
        allow: bool,
        tool_name: str | None = None,
        description: str = "",
    ) -> None:
        """
        Add a path-based permission rule.
        
        Args:
            pattern: Glob pattern for path matching
            allow: True to allow, False to deny
            tool_name: Optional tool restriction
            description: Human-readable description
        """
        rule = PathRule(
            pattern=pattern,
            allow=allow,
            tool_name=tool_name,
            description=description,
        )
        self._path_rules.append(rule)
        log.info("Added path rule: %s = %s", pattern, allow)

    def set_mode(self, mode: PermissionMode) -> None:
        """
        Change the permission mode.
        
        Args:
            mode: New permission mode
        """
        self._config.mode = mode
        
        # Recreate OH checker with new mode
        settings = self._build_oh_settings()
        self._checker = PermissionChecker(settings)
        
        log.info("Permission mode changed to: %s", mode)

    def get_mode(self) -> PermissionMode:
        """Get current permission mode."""
        return self._config.mode

    def get_statistics(self) -> dict[str, Any]:
        """Get permission statistics."""
        return {
            "mode": self._config.mode.value,
            "policies_count": len(self._policies),
            "agents_with_profiles": len(self._agent_profiles),
            "pre_hooks_count": len(self._pre_hooks),
            "post_hooks_count": len(self._post_hooks),
            "path_rules_count": len(self._path_rules),
        }

    def to_oh_settings(self) -> PermissionSettings:
        """Export current config as OH PermissionSettings."""
        return self._build_oh_settings()
