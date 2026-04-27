# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
# OpenHarnessIntegration - Unified Integration Class (v0.1.0 compatible)

"""
OpenHarnessIntegration - Simplified OpenHarness 0.1.0 Integration for USMSB.

This module provides a simplified integration layer for OpenHarness 0.1.0,
which provides basic tools (file read/write, search, run_tests) and
a Harness system for agent execution.

OpenHarness 0.1.0 Components:
    - Tools: ReadFileTool, WriteFileTool, SearchTool, RunTestsTool
    - Harness: SimpleHarness, Harness (base class)
    - TrajectoryStore: For recording execution trajectories

Usage:
    >>> from usmsb_sdk.adapters.openharness import OpenHarnessIntegration
    >>> integration = OpenHarnessIntegration()
    >>> await integration.initialize()
    >>> 
    >>> # Execute a tool directly
    >>> result = integration.execute_tool("read_file", path="/tmp/test.txt")
    >>> 
    >>> # Use Harness for multi-step tasks
    >>> harness = integration.create_harness(tools=[...], tasks=[...])
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openharness.tools.tool import Tool
from openharness.tools.read_file import ReadFileTool
from openharness.tools.write_file import WriteFileTool
from openharness.tools.search import SearchTool
from openharness.tools.run_tests import RunTestsTool
from openharness.core.harness import SimpleHarness, Harness
from openharness.trajectory.store import TrajectoryStore

OPENHARNESS_AVAILABLE = True

from usmsb_sdk.adapters.openharness.config import (
    OpenHarnessConfig,
    USMSBConfig,
    ToolConfig,
    PermissionConfig,
    MemoryConfig,
    SwarmConfig,
    HookConfig,
    LLMConfig,
)
from usmsb_sdk.adapters.openharness.exceptions import (
    OpenHarnessNotAvailableError,
    ConfigurationError,
    ToolExecutionError,
)

log = logging.getLogger(__name__)


@dataclass
class IntegrationStatistics:
    """Statistics for the integration."""
    tools_executed: int = 0
    total_execution_time_ms: float = 0.0
    harness_episodes: int = 0
    successful_episodes: int = 0
    failed_episodes: int = 0
    last_reset: float = field(default_factory=time.time)


class OpenHarnessIntegration:
    """
    Simplified OpenHarness 0.1.0 Integration.
    
    This class provides a simple interface to OpenHarness's core functionality:
    - Direct tool execution (read_file, write_file, search, run_tests)
    - Harness-based multi-step task execution
    - Trajectory recording for learning
    
    Note: OpenHarness 0.1.0 is a simplified version. Full features like
    PermissionChecker, QueryEngine, HookExecutor, SwarmAdapter, etc. are
    not available in this version.
    """

    # Tool name mapping
    OH_TOOLS = {
        "read_file": ReadFileTool,
        "write_file": WriteFileTool,
        "search": SearchTool,
        "run_tests": RunTestsTool,
    }

    def __init__(
        self,
        config: OpenHarnessConfig | None = None,
        usmsb_config: USMSBConfig | None = None,
        cwd: str | Path = ".",
    ):
        """
        Initialize OpenHarness integration.
        
        Args:
            config: OH configuration (optional)
            usmsb_config: USMSB-specific configuration (optional)
            cwd: Current working directory
        """
        if not OPENHARNESS_AVAILABLE:
            raise OpenHarnessNotAvailableError(
                "OpenHarness is not installed. Install with: pip install openharness"
            )
        
        self._config = config or OpenHarnessConfig()
        self._usmsb_config = usmsb_config or USMSBConfig()
        self._cwd = Path(cwd).resolve()
        self._start_time = time.time()
        
        # Tool instances
        self._tools: dict[str, Tool] = {}
        
        # Trajectory store for recording episodes
        self._trajectory_store = TrajectoryStore()
        
        # Statistics
        self._stats = IntegrationStatistics()
        
        # Track initialization
        self._initialized = False
        
        log.info("OpenHarnessIntegration created (version 0.1.0 compatible)")

    @classmethod
    def from_env(
        cls,
        usmsb_config: USMSBConfig | None = None,
        cwd: str | Path = ".",
    ) -> "OpenHarnessIntegration":
        """Create integration from environment variables."""
        config = OpenHarnessConfig.from_env()
        return cls(config=config, usmsb_config=usmsb_config, cwd=cwd)

    async def initialize(self) -> None:
        """
        Initialize the integration.
        
        This method must be called before using any tools or harnesses.
        """
        if self._initialized:
            log.warning("Integration already initialized")
            return
        
        log.info("Initializing OpenHarness 0.1.0 integration...")
        
        try:
            # Initialize tools
            self._tools = {
                "read_file": ReadFileTool(base_dir=str(self._cwd)),
                "write_file": WriteFileTool(base_dir=str(self._cwd)),
                "search": SearchTool(base_dir=str(self._cwd)),
                "run_tests": RunTestsTool(base_dir=str(self._cwd)),
            }
            log.info("Initialized %d tools: %s", len(self._tools), list(self._tools.keys()))
            
            self._initialized = True
            log.info("OpenHarness integration initialized successfully")
            
        except Exception as e:
            log.error("Failed to initialize integration: %s", e)
            raise ConfigurationError(message=f"Initialization failed: {e}") from e

    @property
    def initialized(self) -> bool:
        """Check if integration is initialized."""
        return self._initialized

    @property
    def tool_names(self) -> list[str]:
        """Return list of available tool names."""
        return list(self._tools.keys())

    def get_tool(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        """List all available tools with metadata."""
        result = []
        for name, tool in self._tools.items():
            result.append({
                "name": name,
                "description": tool.get_description(),
            })
        return result

    def execute_tool(
        self,
        tool_name: str,
        check_permission: bool = False,
        **kwargs: Any,
    ) -> str:
        """
        Execute a tool directly.
        
        Args:
            tool_name: Name of the tool (read_file, write_file, search, run_tests)
            check_permission: Ignored in 0.1.0 (no permission system)
            **kwargs: Tool-specific arguments
            
        Returns:
            Tool output as string
            
        Raises:
            ToolExecutionError: If tool execution fails
        """
        self._check_initialized()
        
        tool = self._tools.get(tool_name)
        if not tool:
            raise ToolExecutionError(f"Tool '{tool_name}' not found. Available: {list(self._tools.keys())}")
        
        start_time = time.time()
        try:
            result = tool.run(**kwargs)
            self._stats.tools_executed += 1
            self._stats.total_execution_time_ms += (time.time() - start_time) * 1000
            return result
        except Exception as e:
            raise ToolExecutionError(f"Tool '{tool_name}' failed: {e}") from e

    def create_harness(
        self,
        tools: list[Tool] | None = None,
        tasks: list[dict[str, Any]] | None = None,
        max_steps: int = 10,
    ) -> SimpleHarness:
        """
        Create a SimpleHarness for multi-step task execution.
        
        Args:
            tools: List of tools (uses default OH tools if None)
            tasks: List of task definitions
            max_steps: Maximum steps per episode
            
        Returns:
            SimpleHarness instance
        """
        self._check_initialized()
        
        if tools is None:
            tools = list(self._tools.values())
        
        harness = SimpleHarness(tools=tools, tasks=tasks or [])
        harness.max_steps = max_steps
        log.info("Created SimpleHarness with %d tools, %d tasks", len(tools), len(tasks or []))
        return harness

    def get_trajectory_store(self) -> TrajectoryStore:
        """Get the trajectory store for recording episodes."""
        return self._trajectory_store

    def get_statistics(self) -> IntegrationStatistics:
        """Get integration statistics."""
        return self._stats

    def reset_statistics(self) -> None:
        """Reset statistics counters."""
        self._stats = IntegrationStatistics()

    def inject_oh_tools_into_registry(
        self,
        usmsb_tool_registry: Any,
        capability_filter: str | None = None,
    ) -> int:
        """
        Inject OH tools into USMSB ToolRegistry.
        
        Args:
            usmsb_tool_registry: USMSB's ToolRegistry instance
            capability_filter: Ignored in 0.1.0
            
        Returns:
            Number of tools injected
        """
        from usmsb_sdk.meta_agent.tools.registry import Tool
        
        self._check_initialized()
        injected = 0
        
        for name, tool in self._tools.items():
            # Check if tool already exists
            if hasattr(usmsb_tool_registry, "get_tool"):
                if usmsb_tool_registry.get_tool(name):
                    continue
            elif hasattr(usmsb_tool_registry, "tool_names"):
                if name in usmsb_tool_registry.tool_names:
                    continue
            
            # Create handler that wraps synchronous tool.run()
            # USMSB calls: handler(params=dict) for no-session tools
            def make_handler(_name=name, _tool=tool):
                async def handler(params: dict = None, **kw):
                    # Get arguments from params dict
                    args = params if params is not None else kw
                    return _tool.run(**args)
                return handler
            
            # Create USMSB Tool wrapper
            schema = self._get_tool_schema(name)
            usmsb_tool = Tool(
                name=name,
                description=tool.get_description(),
                handler=make_handler(),
                required_permissions=[],
                security_level="medium",
                requires_session=False,
                parameters=schema,
            )
            
            try:
                if hasattr(usmsb_tool_registry, "register"):
                    usmsb_tool_registry.register(usmsb_tool)
                elif hasattr(usmsb_tool_registry, "register_tool"):
                    usmsb_tool_registry.register_tool(usmsb_tool)
                injected += 1
            except Exception as e:
                log.warning("Failed to inject OH tool %s: %s", name, e)
        
        log.info("OH tool injection: %d/%d registered", injected, len(self._tools))
        return injected

    def _get_tool_schema(self, tool_name: str) -> dict[str, Any]:
        """Get tool parameter schema based on actual OpenHarness 0.1.0 API."""
        schemas = {
            "read_file": {
                "properties": {
                    "path": {"type": "string", "description": "File path to read"}
                },
                "required": ["path"]
            },
            "write_file": {
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Content to write"}
                },
                "required": ["path", "content"]
            },
            "search": {
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "path": {"type": "string", "description": "Directory to search (default: current directory)"}
                },
                "required": ["pattern"]
            },
            "run_tests": {
                "properties": {
                    "test_path": {"type": "string", "description": "Path to test file or directory"}
                },
                "required": ["test_path"]
            },
        }
        return schemas.get(tool_name, {})

    def _check_initialized(self) -> None:
        """Check if initialized, raise if not."""
        if not self._initialized:
            raise ConfigurationError(
                "Integration not initialized. Call await initialize() first."
            )

    def __repr__(self) -> str:
        return (
            f"OpenHarnessIntegration("
            f"initialized={self._initialized}, "
            f"tools={len(self._tools)}, "
            f"version=0.1.0)"
        )


# Backward compatibility alias
OpenHarnessIntegration_v1 = OpenHarnessIntegration
