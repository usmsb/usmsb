# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
# OpenHarnessIntegration - Unified Integration Class

"""
OpenHarnessIntegration - Unified OpenHarness Integration for USMSB.

This module provides the main OpenHarnessIntegration class that ties
all adapters together into a cohesive interface for USMSB's Goal Layer.

The integration class:
1. Initializes all OH adapters (Tool, Permission, Memory, Swarm, Query, Hook, MetaAgent)
2. Provides a unified interface for USMSB's cognitive architecture
3. Manages adapter lifecycle and dependencies
4. Tracks cross-adapter statistics

Usage:
    >>> from usmsb_sdk.adapters.openharness import OpenHarnessIntegration
    >>> 
    >>> integration = OpenHarnessIntegration()
    >>> 
    >>> # Execute a tool
    >>> result = await integration.tool_adapter.execute_tool("file_read", path="/tmp/test.txt")
    >>> 
    >>> # Spawn an agent
    >>> agent = await integration.meta_agent_adapter.spawn_agent(AgentSpec(agent_type="researcher"))
    >>> 
    >>> # Create a team
    >>> team = await integration.swarm_adapter.create_team("team_001", leader_id="agent_leader")
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from openharness.tools.base import ToolRegistry
    from openharness.permissions.checker import PermissionChecker
    from openharness.engine.query_engine import QueryEngine
    from openharness.hooks.executor import HookExecutor, HookExecutionContext
    OPENHARNESS_AVAILABLE = True
except ImportError:
    OPENHARNESS_AVAILABLE = False
    ToolRegistry = None
    PermissionChecker = None
    QueryEngine = None
    HookExecutor = None
    HookExecutionContext = None

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
)
from usmsb_sdk.adapters.openharness.tool_adapter import ToolAdapter
from usmsb_sdk.adapters.openharness.permission_adapter import PermissionAdapter
from usmsb_sdk.adapters.openharness.memory_adapter import MemoryAdapter
from usmsb_sdk.adapters.openharness.swarm_adapter import SwarmAdapter
from usmsb_sdk.adapters.openharness.query_adapter import QueryAdapter
from usmsb_sdk.adapters.openharness.hook_adapter import HookAdapter
from usmsb_sdk.adapters.openharness.meta_agent_adapter import MetaAgentAdapter

log = logging.getLogger(__name__)


@dataclass
class IntegrationStatistics:
    """
    Aggregated statistics from all adapters.
    
    This provides a comprehensive view of the integration's
    resource usage and performance.
    """
    tool_adapter: dict[str, Any] = field(default_factory=dict)
    permission_adapter: dict[str, Any] = field(default_factory=dict)
    memory_adapter: dict[str, Any] = field(default_factory=dict)
    swarm_adapter: dict[str, Any] = field(default_factory=dict)
    query_adapter: dict[str, Any] = field(default_factory=dict)
    hook_adapter: dict[str, Any] = field(default_factory=dict)
    meta_agent_adapter: dict[str, Any] = field(default_factory=dict)
    total_agents: int = 0
    total_tasks: int = 0
    uptime_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool_adapter": self.tool_adapter,
            "permission_adapter": self.permission_adapter,
            "memory_adapter": self.memory_adapter,
            "swarm_adapter": self.swarm_adapter,
            "query_adapter": self.query_adapter,
            "hook_adapter": self.hook_adapter,
            "meta_agent_adapter": self.meta_agent_adapter,
            "total_agents": self.total_agents,
            "total_tasks": self.total_tasks,
            "uptime_seconds": self.uptime_seconds,
        }


class OpenHarnessIntegration:
    """
    Unified OpenHarness Integration for USMSB.
    
    This class provides a single entry point for all OpenHarness
    functionality, managing adapters and their dependencies.
    
    It implements the Facade Pattern to simplify the complex
    OH adapter ecosystem for USMSB's Goal Layer.
    
    Example:
        >>> integration = OpenHarnessIntegration.from_env()
        >>> 
        >>> # Tool execution with permission checking
        >>> result = await integration.execute_tool(
        ...     agent_id="agent_001",
        ...     tool_name="file_read",
        ...     params={"path": "/tmp/test.txt"}
        ... )
        >>> 
        >>> # Create team and spawn agents
        >>> team = await integration.create_team("research_team")
        >>> agent = await integration.spawn_agent(
        ...     team_id="research_team",
        ...     agent_type="researcher"
        ... )
        >>> 
        >>> # Get unified statistics
        >>> stats = integration.get_statistics()
    """

    def __init__(
        self,
        config: OpenHarnessConfig | None = None,
        usmsb_config: USMSBConfig | None = None,
        cwd: str | Path = ".",
    ):
        """
        Initialize OpenHarness integration.
        
        Args:
            config: OH configuration
            usmsb_config: USMSB-specific configuration
            cwd: Current working directory
        """
        if not OPENHARNESS_AVAILABLE:
            raise OpenHarnessNotAvailableError()
        
        self._config = config or OpenHarnessConfig.from_env()
        self._usmsb_config = usmsb_config or USMSBConfig()
        self._cwd = Path(cwd).resolve()
        self._start_time = asyncio.get_event_loop().time()
        
        # Initialize core OH components
        self._tool_registry: ToolRegistry | None = None
        self._permission_checker: PermissionChecker | None = None
        self._query_engine: QueryEngine | None = None
        self._hook_executor: HookExecutor | None = None
        
        # Initialize adapters
        self._tool_adapter: ToolAdapter | None = None
        self._permission_adapter: PermissionAdapter | None = None
        self._memory_adapter: MemoryAdapter | None = None
        self._swarm_adapter: SwarmAdapter | None = None
        self._query_adapter: QueryAdapter | None = None
        self._hook_adapter: HookAdapter | None = None
        self._meta_agent_adapter: MetaAgentAdapter | None = None
        
        # Track initialization
        self._initialized = False
        
        log.info("OpenHarnessIntegration created (not yet initialized)")

    @classmethod
    def from_env(
        cls,
        usmsb_config: USMSBConfig | None = None,
        cwd: str | Path = ".",
    ) -> "OpenHarnessIntegration":
        """
        Create integration from environment variables.
        
        Environment variables:
            OPENHARNESS_* - See config.py for full list
            
        Args:
            usmsb_config: USMSB-specific configuration
            cwd: Current working directory
            
        Returns:
            OpenHarnessIntegration instance
        """
        config = OpenHarnessConfig.from_env()
        return cls(config=config, usmsb_config=usmsb_config, cwd=cwd)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        usmsb_config: USMSBConfig | None = None,
        cwd: str | Path = ".",
    ) -> "OpenHarnessIntegration":
        """
        Create integration from dictionary.
        
        Args:
            data: Configuration dictionary
            usmsb_config: USMSB-specific configuration
            cwd: Current working directory
            
        Returns:
            OpenHarnessIntegration instance
        """
        config = OpenHarnessConfig.from_dict(data)
        return cls(config=config, usmsb_config=usmsb_config, cwd=cwd)

    async def initialize(self) -> None:
        """
        Initialize the integration and all adapters.
        
        This method must be called before using any adapters.
        It sets up the OH core components and creates adapter instances.
        
        Raises:
            ConfigurationError: If required config is missing
            OpenHarnessNotAvailableError: If OH is not installed
        """
        if self._initialized:
            log.warning("Integration already initialized")
            return
        
        log.info("Initializing OpenHarness integration...")
        
        try:
            # 1. Initialize core OH ToolRegistry
            self._tool_registry = ToolRegistry()
            log.info("ToolRegistry initialized")
            
            # 2. Initialize OH PermissionChecker
            self._permission_checker = PermissionChecker(
                self._permission_adapter.to_oh_settings() if self._permission_adapter else
                self._build_permission_settings()
            )
            log.info("PermissionChecker initialized")
            
            # 3. Initialize HookExecutor
            hook_context = HookExecutionContext(
                cwd=self._cwd,
                api_client=None,  # Set when query engine is created
                default_model=self._config.llm.model,
            )
            from openharness.hooks.loader import HookRegistry
            self._hook_executor = HookExecutor(
                registry=HookRegistry(),
                context=hook_context,
            )
            log.info("HookExecutor initialized")
            
            # 4. Create adapters (in dependency order)
            
            # ToolAdapter
            self._tool_adapter = ToolAdapter(
                registry=self._tool_registry,
                permission_checker=self._permission_checker,
                cwd=self._cwd,
            )
            
            # PermissionAdapter
            self._permission_adapter = PermissionAdapter(
                checker=self._permission_checker,
                config=self._config.permission,
                cwd=self._cwd,
            )
            
            # MemoryAdapter
            self._memory_adapter = MemoryAdapter(
                cwd=self._cwd,
                config=self._config.memory,
            )
            
            # SwarmAdapter
            self._swarm_adapter = SwarmAdapter(
                config=self._config.swarm,
                teams_dir=self._config.swarm.teams_dir,
            )
            
            # QueryAdapter (needs api_client to be set later)
            self._query_adapter = QueryAdapter(
                engine=None,  # Set when QueryEngine is created
                config=self._config.llm,
                cwd=self._cwd,
            )
            
            # HookAdapter
            self._hook_adapter = HookAdapter(
                executor=self._hook_executor,
                config=self._config.hook,
                cwd=self._cwd,
            )
            
            # MetaAgentAdapter
            self._meta_agent_adapter = MetaAgentAdapter(
                config=self._config.swarm,
                teams_dir=self._config.swarm.teams_dir,
            )
            
            self._initialized = True
            log.info("OpenHarness integration initialized successfully")
            
        except Exception as e:
            log.error("Failed to initialize integration: %s", e)
            raise ConfigurationError(
                message=f"Initialization failed: {e}",
            )

    def _build_permission_settings(self):
        """Build OH PermissionSettings from config."""
        from openharness.permissions.modes import PermissionMode as OHModes
        
        mode_map = {
            PermissionConfig: OHModes.MODERATE,
        }
        
        class Settings:
            def __init__(self, config: PermissionConfig):
                self.mode = OHModes.MODERATE
                self.denied_tools = config.denied_tools
                self.allowed_tools = config.allowed_tools
                self.denied_commands = config.denied_commands
                self.path_rules = config.path_rules
        
        return Settings(self._config.permission)

    # -------------------------------------------------------------------------
    # Adapter Accessors
    # -------------------------------------------------------------------------

    @property
    def tool_adapter(self) -> ToolAdapter:
        """Get ToolAdapter instance."""
        self._check_initialized()
        return self._tool_adapter

    @property
    def permission_adapter(self) -> PermissionAdapter:
        """Get PermissionAdapter instance."""
        self._check_initialized()
        return self._permission_adapter

    @property
    def memory_adapter(self) -> MemoryAdapter:
        """Get MemoryAdapter instance."""
        self._check_initialized()
        return self._memory_adapter

    @property
    def swarm_adapter(self) -> SwarmAdapter:
        """Get SwarmAdapter instance."""
        self._check_initialized()
        return self._swarm_adapter

    @property
    def query_adapter(self) -> QueryAdapter:
        """Get QueryAdapter instance."""
        self._check_initialized()
        return self._query_adapter

    @property
    def hook_adapter(self) -> HookAdapter:
        """Get HookAdapter instance."""
        self._check_initialized()
        return self._hook_adapter

    @property
    def meta_agent_adapter(self) -> MetaAgentAdapter:
        """Get MetaAgentAdapter instance."""
        self._check_initialized()
        return self._meta_agent_adapter

    # -------------------------------------------------------------------------
    # Convenience Methods
    # -------------------------------------------------------------------------

    async def execute_tool(
        self,
        agent_id: str,
        tool_name: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute a tool with permission checking and hooks.
        
        This is a convenience method that:
        1. Checks permissions via PermissionAdapter
        2. Executes pre-hooks
        3. Executes the tool via ToolAdapter
        4. Executes post-hooks
        
        Args:
            agent_id: Agent executing the tool
            tool_name: Name of tool to execute
            params: Tool parameters
            
        Returns:
            Tool execution result
        """
        params = params or {}
        
        # Pre-hooks
        allowed, reason = await self.hook_adapter.execute_pre_hooks(
            agent_id, tool_name, params
        )
        
        if not allowed:
            await self.hook_adapter.execute_post_hooks(
                agent_id, tool_name, params, allowed=False, error=reason
            )
            from usmsb_sdk.adapters.openharness.exceptions import PermissionDeniedError
            raise PermissionDeniedError(
                tool_name=tool_name,
                reason=reason,
                agent_id=agent_id,
            )
        
        # Permission check
        decision = self.permission_adapter.check_tool_permission(
            agent_id, tool_name, params
        )
        
        if not decision.allowed:
            await self.hook_adapter.execute_post_hooks(
                agent_id, tool_name, params, allowed=False, error=decision.reason
            )
            from usmsb_sdk.adapters.openharness.exceptions import PermissionDeniedError
            raise PermissionDeniedError(
                tool_name=tool_name,
                reason=decision.reason,
                requires_confirmation=decision.requires_confirmation,
                agent_id=agent_id,
            )
        
        # Execute tool
        try:
            result = await self.tool_adapter.execute_tool(
                tool_name,
                check_permission=False,  # Already checked
                **params,
            )
            
            await self.hook_adapter.execute_post_hooks(
                agent_id, tool_name, params, allowed=True, result=result
            )
            
            return result
            
        except Exception as e:
            await self.hook_adapter.execute_post_hooks(
                agent_id, tool_name, params, allowed=True, error=str(e)
            )
            raise

    async def create_team(
        self,
        team_id: str,
        name: str | None = None,
        leader_id: str = "",
        description: str = "",
    ) -> Any:
        """Create a team with swarm coordination."""
        return await self.swarm_adapter.create_team(
            team_id=team_id,
            name=name,
            leader_id=leader_id,
            description=description,
        )

    async def spawn_agent(
        self,
        team_id: str | None,
        agent_type: str,
        name: str | None = None,
        capabilities: list[str] | None = None,
        model: str | None = None,
    ) -> Any:
        """Spawn an agent in a team."""
        from usmsb_sdk.adapters.openharness.meta_agent_adapter import AgentSpec
        
        spec = AgentSpec(
            agent_type=agent_type,
            name=name,
            capabilities=capabilities,
            model=model or self._config.llm.model,
        )
        
        return await self.meta_agent_adapter.spawn_agent(spec, team_id=team_id)

    async def delegate_task(
        self,
        agent_id: str,
        description: str,
        priority: int = 3,
    ) -> Any:
        """Delegate a task to an agent."""
        return await self.meta_agent_adapter.delegate_task(
            agent_id=agent_id,
            description=description,
            priority=priority,
        )

    def store_memory(
        self,
        key: str,
        value: Any,
        memory_type: str = "general",
    ) -> None:
        """Store a memory entry."""
        self.memory_adapter.store(key, value, memory_type)

    def retrieve_memory(self, key: str, default: Any = None) -> Any:
        """Retrieve a memory entry."""
        return self.memory_adapter.retrieve(key, default)

    def search_memory(self, query: str, limit: int = 10) -> list[Any]:
        """Search memory entries."""
        return self.memory_adapter.search(query, limit=limit)

    # -------------------------------------------------------------------------
    # Statistics and Lifecycle
    # -------------------------------------------------------------------------

    def _check_initialized(self) -> None:
        """Check if integration is initialized."""
        if not self._initialized:
            raise ConfigurationError(
                message="Integration not initialized. Call await integration.initialize() first.",
            )

    def get_statistics(self) -> IntegrationStatistics:
        """
        Get aggregated statistics from all adapters.
        
        Returns:
            IntegrationStatistics with cross-adapter metrics
        """
        self._check_initialized()
        
        uptime = asyncio.get_event_loop().time() - self._start_time
        
        stats = IntegrationStatistics(
            uptime_seconds=uptime,
        )
        
        if self._tool_adapter:
            stats.tool_adapter = self._tool_adapter.get_statistics()
        
        if self._permission_adapter:
            stats.permission_adapter = self._permission_adapter.get_statistics()
        
        if self._memory_adapter:
            stats.memory_adapter = self._memory_adapter.get_statistics()
        
        if self._swarm_adapter:
            stats.swarm_adapter = self._swarm_adapter.get_statistics()
        
        if self._query_adapter:
            stats.query_adapter = self._query_adapter.get_statistics()
        
        if self._hook_adapter:
            stats.hook_adapter = self._hook_adapter.get_statistics()
        
        if self._meta_agent_adapter:
            meta_stats = self._meta_agent_adapter.get_statistics()
            stats.meta_agent_adapter = meta_stats
            stats.total_agents = meta_stats.get("total_agents", 0)
            stats.total_tasks = meta_stats.get("total_tasks", 0)
        
        return stats

    async def shutdown(self) -> None:
        """
        Shutdown the integration.
        
        This stops all agents and releases resources.
        """
        log.info("Shutting down OpenHarness integration...")
        
        # Stop all agents
        if self._meta_agent_adapter:
            agents = self._meta_agent_adapter.list_agents()
            for agent in agents:
                await self._meta_agent_adapter.stop_agent(agent.agent_id)
        
        self._initialized = False
        log.info("OpenHarness integration shut down")

    def is_initialized(self) -> bool:
        """Check if integration is initialized."""
        return self._initialized

    @property
    def config(self) -> OpenHarnessConfig:
        """Get OH configuration."""
        return self._config

    @property
    def usmsb_config(self) -> USMSBConfig:
        """Get USMSB configuration."""
        return self._usmsb_config
