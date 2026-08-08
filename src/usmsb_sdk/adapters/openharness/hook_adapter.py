# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
# HookAdapter - OpenHarness Hook System Integration

"""
OpenHarness HookAdapter for USMSB.

This adapter wraps the OpenHarness HookExecutor to provide:
- Pre-tool execution hooks
- Post-tool execution hooks
- Prompt hooks for LLM validation
- Agent hooks for autonomous decisions
- HTTP hooks for external integrations

The adapter integrates USMSB's L3 (Self-Observation) with OH's
hook system for agent introspection and control.

Usage:
    >>> adapter = HookAdapter(executor=oh_executor)
    >>> adapter.register_pre_hook("file_read", my_pre_hook)
    >>> adapter.register_post_hook("file_write", my_post_hook)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Awaitable

try:
    from openharness.hooks.executor import HookExecutor, HookExecutionContext
    from openharness.hooks.events import HookEvent
    from openharness.hooks.types import HookResult, AggregatedHookResult
    from openharness.hooks.loader import HookRegistry
    from openharness.hooks.schemas import (
        CommandHookDefinition,
        HttpHookDefinition,
        PromptHookDefinition,
        AgentHookDefinition,
    )
    OPENHARNESS_AVAILABLE = True
except ImportError:
    OPENHARNESS_AVAILABLE = False
    HookExecutor = None
    HookEvent = None
    HookResult = None
    AggregatedHookResult = None

from usmsb_sdk.adapters.openharness.config import HookConfig
from usmsb_sdk.adapters.openharness.exceptions import (
    HookError,
    PreHookError,
    PostHookError,
    OpenHarnessNotAvailableError,
)

log = logging.getLogger(__name__)


@dataclass
class USMSBHookResult:
    """
    Result of a hook execution.
    
    Attributes:
        success: Whether hook executed successfully
        output: Hook output (for prompt/agent hooks)
        blocked: Whether this hook blocks on failure
        reason: Error or explanation message
        hook_type: Type of hook (command, http, prompt, agent)
    """
    success: bool
    output: str = ""
    blocked: bool = False
    reason: str = ""
    hook_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# Type aliases for hook callables
PreToolHook = Callable[[str, str, dict[str, Any]], Awaitable[bool | None]]
"""Pre-tool hook: (agent_id, tool_name, params) -> bool to block, None to continue"""

PostToolHook = Callable[[str, str, dict[str, Any], bool, Any], Awaitable[None]]
"""Post-tool hook: (agent_id, tool_name, params, allowed, result) -> None"""


class USMSBHookRegistry:
    """
    Registry for USMSB-specific hooks.
    
    This provides a simpler interface for registering hooks
    compared to OH's schema-based approach.
    """
    
    def __init__(self):
        self._pre_hooks: dict[str, list[PreToolHook]] = {}
        self._post_hooks: dict[str, list[PostToolHook]] = {}
        self._global_pre_hooks: list[PreToolHook] = []
        self._global_post_hooks: list[PostToolHook] = []
    
    def register_pre_hook(
        self,
        tool_name: str | None,
        hook: PreToolHook,
    ) -> None:
        """
        Register a pre-tool hook.
        
        Args:
            tool_name: Tool to hook, or None for global hook
            hook: Hook function
        """
        if tool_name is None:
            self._global_pre_hooks.append(hook)
        else:
            self._pre_hooks.setdefault(tool_name, []).append(hook)
        log.debug("Registered pre-hook for tool: %s", tool_name or "*")
    
    def register_post_hook(
        self,
        tool_name: str | None,
        hook: PostToolHook,
    ) -> None:
        """
        Register a post-tool hook.
        
        Args:
            tool_name: Tool to hook, or None for global hook
            hook: Hook function
        """
        if tool_name is None:
            self._global_post_hooks.append(hook)
        else:
            self._post_hooks.setdefault(tool_name, []).append(hook)
        log.debug("Registered post-hook for tool: %s", tool_name or "*")
    
    async def execute_pre_hooks(
        self,
        agent_id: str,
        tool_name: str,
        params: dict[str, Any],
    ) -> tuple[bool, str]:
        """
        Execute all matching pre-hooks.
        
        Returns:
            Tuple of (allowed, reason). If any hook returns False, blocked.
        """
        all_hooks = (
            self._global_pre_hooks +
            self._pre_hooks.get(tool_name, []) +
            self._pre_hooks.get("*", [])
        )
        
        for hook in all_hooks:
            try:
                result = await hook(agent_id, tool_name, params)
                if result is False:
                    return False, f"Blocked by pre-hook: {getattr(hook, '__name__', repr(hook))}"
            except Exception as e:
                log.warning("Pre-hook failed: %s", e)
                return False, f"Pre-hook error: {e}"
        
        return True, ""
    
    async def execute_post_hooks(
        self,
        agent_id: str,
        tool_name: str,
        params: dict[str, Any],
        allowed: bool,
        result: Any,
    ) -> None:
        """Execute all matching post-hooks."""
        all_hooks = (
            self._global_post_hooks +
            self._post_hooks.get(tool_name, []) +
            self._post_hooks.get("*", [])
        )
        
        for hook in all_hooks:
            try:
                await hook(agent_id, tool_name, params, allowed, result)
            except Exception as e:
                log.warning("Post-hook failed: %s", e)


class HookAdapter:
    """
    OpenHarness HookExecutor Adapter.
    
    This adapter wraps OH's HookExecutor and extends it with:
    - USMSB-specific hook registry
    - Simplified hook registration
    - Self-Observation integration
    - Value tracking hooks
    
    Hooks enable USMSB's self-observation capabilities:
    - Pre-hooks: Record intended actions before execution
    - Post-hooks: Record outcomes and update value estimates
    
    Example:
        >>> adapter = HookAdapter()
        >>> 
        >>> # Record all tool calls
        >>> async def log_tool_call(agent_id, tool_name, params):
        ...     print(f"Agent {agent_id} will execute {tool_name}")
        ...     return None  # Allow execution
        >>> 
        >>> adapter.register_pre_hook("*", log_tool_call)
        >>> 
        >>> # Track outcomes
        >>> async def track_outcome(agent_id, tool_name, params, allowed, result):
        ...     print(f"Tool {tool_name} completed with result: {result}")
        ... 
        >>> adapter.register_post_hook("*", track_outcome)
    """

    def __init__(
        self,
        executor: HookExecutor | None = None,
        config: HookConfig | None = None,
        cwd: str | Path = ".",
        max_action_log_entries: int = 10_000,
    ):
        """
        Initialize HookAdapter.
        
        Args:
            executor: OH HookExecutor instance
            config: Hook configuration
            cwd: Current working directory
        """
        if not OPENHARNESS_AVAILABLE:
            raise OpenHarnessNotAvailableError()
        
        self._executor = executor
        self._config = config or HookConfig()
        self._cwd = Path(cwd).resolve()
        if (
            isinstance(max_action_log_entries, bool)
            or not isinstance(max_action_log_entries, int)
            or not 1 <= max_action_log_entries <= 1_000_000
        ):
            raise ValueError("max_action_log_entries must be an integer from 1 to 1000000")
        self._max_action_log_entries = max_action_log_entries
        
        # USMSB-specific hook registry
        self._usmsb_registry = USMSBHookRegistry()
        
        # Value tracking for Self-Observation
        self._action_log: list[dict[str, Any]] = []
        
        log.info("HookAdapter initialized")

    @property
    def executor(self) -> HookExecutor:
        """Return the underlying hook executor."""
        return self._executor

    def register_pre_hook(
        self,
        tool_name: str | None,
        hook: PreToolHook,
    ) -> None:
        """
        Register a pre-tool execution hook.
        
        Pre-hooks are called before tool execution and can:
        - Log the intended action
        - Validate parameters
        - Modify parameters
        - Block execution (return False)
        - Allow execution (return None)
        
        Args:
            tool_name: Tool to hook, or None for all tools
            hook: Async function(agent_id, tool_name, params) -> bool|None
            
        Example:
            >>> async def validate_path(agent_id, tool_name, params):
            ...     path = params.get("path", "")
            ...     if "/protected" in path:
            ...         print("Blocking access to protected path")
            ...         return False  # Block
            ...     return None  # Allow
            >>> 
            >>> adapter.register_pre_hook("file_read", validate_path)
        """
        self._usmsb_registry.register_pre_hook(tool_name, hook)

    def register_post_hook(
        self,
        tool_name: str | None,
        hook: PostToolHook,
    ) -> None:
        """
        Register a post-tool execution hook.
        
        Post-hooks are called after tool execution and can:
        - Log the outcome
        - Update internal state
        - Trigger follow-up actions
        - Record value metrics
        
        Args:
            tool_name: Tool to hook, or None for all tools
            hook: Async function(agent_id, tool_name, params, allowed, result)
            
        Example:
            >>> async def track_success(agent_id, tool_name, params, allowed, result):
            ...     if allowed and result:
            ...         print(f"Tool {tool_name} succeeded")
            ...         await update_metrics(agent_id, tool_name, success=True)
            >>> 
            >>> adapter.register_post_hook("*", track_success)
        """
        self._usmsb_registry.register_post_hook(tool_name, hook)

    async def execute_pre_hooks(
        self,
        agent_id: str,
        tool_name: str,
        params: dict[str, Any],
    ) -> tuple[bool, str]:
        """
        Execute all pre-hooks for a tool.
        
        Args:
            agent_id: Agent attempting execution
            tool_name: Tool being executed
            params: Tool parameters
            
        Returns:
            Tuple of (allowed, reason). If reason is non-empty, execution should be blocked.
        """
        # Log action
        self._append_action_log({
            "type": "pre_tool",
            "agent_id": agent_id,
            "tool_name": tool_name,
            "params": params,
            "timestamp": asyncio.get_event_loop().time(),
        })
        
        return await self._usmsb_registry.execute_pre_hooks(agent_id, tool_name, params)

    async def execute_post_hooks(
        self,
        agent_id: str,
        tool_name: str,
        params: dict[str, Any],
        allowed: bool,
        result: Any = None,
        error: str | None = None,
    ) -> None:
        """
        Execute all post-hooks for a tool.
        
        Args:
            agent_id: Agent that executed
            tool_name: Tool that was executed
            params: Original tool parameters
            allowed: Whether execution was allowed
            result: Tool result (if executed)
            error: Error message (if failed)
        """
        # Log outcome
        self._append_action_log({
            "type": "post_tool",
            "agent_id": agent_id,
            "tool_name": tool_name,
            "params": params,
            "allowed": allowed,
            "result": result,
            "error": error,
            "timestamp": asyncio.get_event_loop().time(),
        })
        
        await self._usmsb_registry.execute_post_hooks(
            agent_id, tool_name, params, allowed, result
        )

    def _append_action_log(self, entry: dict[str, Any]) -> None:
        self._action_log.append(entry)
        overflow = len(self._action_log) - self._max_action_log_entries
        if overflow > 0:
            del self._action_log[:overflow]

    async def execute_oh_hook(
        self,
        event: HookEvent,
        payload: dict[str, Any],
    ) -> USMSBHookResult:
        """
        Execute an OH-style hook (Command, HTTP, Prompt, Agent).
        
        This is for integration with OH's hook system using
        hook definitions (schemas) rather than Python callables.
        
        Args:
            event: OH HookEvent
            payload: Hook payload
            
        Returns:
            USMSBHookResult
        """
        if self._executor is None:
            return USMSBHookResult(
                success=False,
                reason="HookExecutor not initialized",
            )
        
        try:
            result: AggregatedHookResult = await self._executor.execute(event, payload)
            
            if not result.results:
                return USMSBHookResult(success=True)
            
            # Combine results
            first_result = result.results[0]
            return USMSBHookResult(
                success=first_result.success,
                output=first_result.output or "",
                blocked=first_result.blocked,
                reason=first_result.reason or "",
                hook_type=first_result.hook_type,
            )
            
        except Exception as e:
            return USMSBHookResult(
                success=False,
                reason=f"Hook execution failed: {e}",
            )

    def register_command_hook(
        self,
        name: str,
        command: str,
        event: str = "on_tool_call",
        matcher: str | None = None,
        timeout_seconds: int = 30,
        block_on_failure: bool = False,
    ) -> None:
        """
        Register a command-based hook via OH schema.
        
        Command hooks execute a shell command when triggered.
        
        Args:
            name: Hook name
            command: Shell command to execute ($ARGUMENTS is replaced with payload)
            event: Event to trigger on
            matcher: Optional fnmatch pattern to filter events
            timeout_seconds: Command timeout
            block_on_failure: Whether to block if command fails
        """
        if self._executor is None:
            log.warning("Cannot register command hook: executor not initialized")
            return
        
        hook_def = CommandHookDefinition(
            name=name,
            command=command,
            timeout_seconds=timeout_seconds,
            block_on_failure=block_on_failure,
            matcher=matcher,
        )
        
        # Register with OH executor
        registry = self._executor._registry
        registry.register(event, hook_def)
        
        log.info("Registered command hook: %s", name)

    def register_http_hook(
        self,
        name: str,
        url: str,
        event: str = "on_tool_call",
        matcher: str | None = None,
        headers: dict[str, str] | None = None,
        timeout_seconds: int = 30,
        block_on_failure: bool = False,
    ) -> None:
        """
        Register an HTTP-based hook via OH schema.
        
        HTTP hooks send a POST request when triggered.
        
        Args:
            name: Hook name
            url: URL to POST to
            event: Event to trigger on
            matcher: Optional fnmatch pattern
            headers: HTTP headers
            timeout_seconds: Request timeout
            block_on_failure: Whether to block if request fails
        """
        if self._executor is None:
            log.warning("Cannot register HTTP hook: executor not initialized")
            return
        
        hook_def = HttpHookDefinition(
            name=name,
            url=url,
            headers=headers or {},
            timeout_seconds=timeout_seconds,
            block_on_failure=block_on_failure,
            matcher=matcher,
        )
        
        registry = self._executor._registry
        registry.register(event, hook_def)
        
        log.info("Registered HTTP hook: %s", name)

    def register_prompt_hook(
        self,
        name: str,
        prompt: str,
        event: str = "on_tool_call",
        matcher: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 30,
        block_on_failure: bool = False,
    ) -> None:
        """
        Register a prompt-based hook via OH schema.
        
        Prompt hooks use an LLM to evaluate whether to allow an action.
        
        Args:
            name: Hook name
            prompt: Prompt template ($ARGUMENTS replaced with payload)
            event: Event to trigger on
            matcher: Optional fnmatch pattern
            model: LLM model to use
            timeout_seconds: LLM timeout
            block_on_failure: Whether to block if LLM rejects
        """
        if self._executor is None:
            log.warning("Cannot register prompt hook: executor not initialized")
            return
        
        hook_def = PromptHookDefinition(
            name=name,
            prompt=prompt,
            model=model,
            timeout_seconds=timeout_seconds,
            block_on_failure=block_on_failure,
            matcher=matcher,
        )
        
        registry = self._executor._registry
        registry.register(event, hook_def)
        
        log.info("Registered prompt hook: %s", name)

    def get_action_log(
        self,
        agent_id: str | None = None,
        tool_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get recent action log entries.
        
        Args:
            agent_id: Filter by agent
            tool_name: Filter by tool
            limit: Maximum entries to return
            
        Returns:
            List of action log entries
        """
        entries = self._action_log
        
        if agent_id:
            entries = [e for e in entries if e.get("agent_id") == agent_id]
        if tool_name:
            entries = [e for e in entries if e.get("tool_name") == tool_name]
        
        return entries[-limit:]

    def clear_action_log(self) -> None:
        """Clear the action log."""
        self._action_log.clear()

    def get_statistics(self) -> dict[str, Any]:
        """Get hook statistics."""
        pre_count = (
            len(self._usmsb_registry._global_pre_hooks) +
            sum(len(h) for h in self._usmsb_registry._pre_hooks.values())
        )
        post_count = (
            len(self._usmsb_registry._global_post_hooks) +
            sum(len(h) for h in self._usmsb_registry._post_hooks.values())
        )
        
        return {
            "pre_hooks_count": pre_count,
            "post_hooks_count": post_count,
            "action_log_entries": len(self._action_log),
            "config_pre_hooks": self._config.pre_tool_hooks,
            "config_post_hooks": self._config.post_tool_hooks,
        }
