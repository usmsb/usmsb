# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
# OpenHarness Adapter Module for USMSB Platform

"""
OpenHarness Adapter Layer for USMSB

This module provides a complete integration layer between USMSB's 
cognitive architecture (L3-L5) and OpenHarness's infrastructure.

Key Components:
    1. ToolAdapter      - 43+ tool registration and execution
    2. PermissionAdapter - Multi-level permission system with hooks
    3. MemoryAdapter   - Persistent memory with context compaction
    4. SwarmAdapter    - Multi-agent team coordination
    5. QueryAdapter    - LLM query engine with streaming
    6. HookAdapter     - Pre/Post tool execution hooks
    7. MetaAgentAdapter - Agent spawning and lifecycle management

Integration Classes:
    - OHL2Agent: L2 Agent with OpenHarness (LLM + Tools)
    - L3OrchestratorWithOH: L3 Goal Loop with OpenHarness
    - MetaAgentWithOH: L5 Collective Intelligence with OpenHarness

Integration Phases:
    Phase 1: L2 基础集成 (Tool/Permission/Memory)
    Phase 2: L2 Agent Loop + QueryAdapter
    Phase 3: L4 Swarm 集成
    Phase 4: L3 Hook 增强 (Self-Observation)
    Phase 5: Meta Agent 集成

Usage:
    >>> from usmsb_sdk.adapters.openharness import OpenHarnessIntegration
    >>> integration = OpenHarnessIntegration()
    >>> tool_adapter = integration.tool_adapter
    >>> result = await tool_adapter.execute_tool("file_read", path="/tmp/test.txt")
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Import OpenHarness components (installed separately)
try:
    from openharness.tools.base import BaseTool, ToolRegistry, ToolResult, ToolExecutionContext
    from openharness.permissions.checker import PermissionChecker, PermissionDecision
    from openharness.permissions.modes import PermissionMode
    from openharness.memory.manager import (
        list_memory_files,
        add_memory_entry,
        remove_memory_entry,
    )
    from openharness.memory.types import MemoryHeader
    from openharness.memory.paths import get_project_memory_dir, get_memory_entrypoint
    from openharness.swarm.team_lifecycle import (
        TeamLifecycleManager,
        TeamMember,
        TeamFile,
        AllowedPath,
        sanitize_name,
        sanitize_agent_name,
    )
    from openharness.swarm.registry import TeamRegistry
    from openharness.swarm.types import BackendType
    from openharness.engine.query_engine import QueryEngine
    from openharness.engine.messages import ConversationMessage, TextBlock, ToolResultBlock
    from openharness.engine.stream_events import StreamEvent
    from openharness.api.client import (
        ApiMessageRequest,
        ApiStreamEvent,
        ApiTextDeltaEvent,
        ApiMessageCompleteEvent,
        SupportsStreamingMessages,
    )
    from openharness.hooks.executor import HookExecutor, HookExecutionContext
    from openharness.hooks.events import HookEvent
    from openharness.hooks.types import HookResult, AggregatedHookResult
    from openharness.config.settings import PermissionSettings
    from openharness.api.openai_client import OpenAIChatClient
    OPENHARNESS_AVAILABLE = True
except ImportError:
    OPENHARNESS_AVAILABLE = False
    # Stub types for when OH is not installed
    BaseTool = None
    ToolRegistry = None
    ToolResult = None
    ToolExecutionContext = None
    PermissionChecker = None
    PermissionDecision = None
    PermissionMode = None
    # ... other stubs

from usmsb_sdk.adapters.openharness.config import (
    OpenHarnessConfig,
    USMSBConfig,
    PermissionMode as USMSBPermissionMode,
    SwarmBackend,
    LLMProvider,
    ToolConfig,
    PermissionConfig,
    MemoryConfig,
    SwarmConfig,
    HookConfig,
    LLMConfig,
)
from usmsb_sdk.adapters.openharness.exceptions import (
    OpenHarnessAdapterError,
    ToolExecutionError,
    PermissionDeniedError,
    MemoryAccessError,
    SwarmError,
    QueryError,
    HookError,
    AgentSpawnError,
    ConfigurationError,
    OpenHarnessNotAvailableError,
)
from usmsb_sdk.adapters.openharness.tool_adapter import (
    ToolAdapter,
    ToolMetadata,
    ToolExecutionResult,
    ToolValidator,
)
from usmsb_sdk.adapters.openharness.permission_adapter import (
    PermissionAdapter,
    PermissionDecision as USMSBPermissionDecision,
    PathRule,
    Policy,
)
from usmsb_sdk.adapters.openharness.memory_adapter import (
    MemoryAdapter,
    MemoryEntry,
    MemoryIndex,
)
from usmsb_sdk.adapters.openharness.swarm_adapter import (
    SwarmAdapter,
    AgentInfo,
    AgentStatus,
    Task,
    TaskStatus,
    TeamInfo,
    MailboxMessage,
)
from usmsb_sdk.adapters.openharness.query_adapter import (
    QueryAdapter,
    CostSummary,
    QueryResult,
    StreamEvent as USMSBStreamEvent,
)
from usmsb_sdk.adapters.openharness.hook_adapter import (
    HookAdapter,
    USMSBHookResult,
    USMSBHookRegistry,
)
from usmsb_sdk.adapters.openharness.meta_agent_adapter import (
    MetaAgentAdapter,
    AgentSpec,
    SpawnedAgent,
    AgentState,
    TaskResult,
    DelegatedTask,
)
from usmsb_sdk.adapters.openharness.openharness_integration import (
    OpenHarnessIntegration,
    IntegrationStatistics,
)

# L2/L3/L5 Integration with OpenHarness
from usmsb_sdk.adapters.openharness.ohl2_agent import OHL2Agent, OHL2Config
from usmsb_sdk.adapters.openharness.ohl3_orchestrator import L3OrchestratorWithOH, GoalExecutionContext
from usmsb_sdk.adapters.openharness.oh_meta_agent import MetaAgentWithOH, ChildAgentInfo

__version__ = "0.2.0"

__all__ = [
    # Version
    "__version__",
    "OPENHARNESS_AVAILABLE",
    # Config
    "OpenHarnessConfig",
    "USMSBConfig",
    "PermissionMode",
    "SwarmBackend",
    "LLMProvider",
    "ToolConfig",
    "PermissionConfig",
    "MemoryConfig",
    "SwarmConfig",
    "HookConfig",
    "LLMConfig",
    # Exceptions
    "OpenHarnessAdapterError",
    "ToolExecutionError",
    "PermissionDeniedError",
    "MemoryAccessError",
    "SwarmError",
    "QueryError",
    "HookError",
    "AgentSpawnError",
    "ConfigurationError",
    "OpenHarnessNotAvailableError",
    # Tool
    "ToolAdapter",
    "ToolMetadata",
    "ToolExecutionResult",
    "ToolValidator",
    # Permission
    "PermissionAdapter",
    "PermissionDecision",
    "PathRule",
    "Policy",
    # Memory
    "MemoryAdapter",
    "MemoryEntry",
    "MemoryIndex",
    # Swarm
    "SwarmAdapter",
    "AgentInfo",
    "AgentStatus",
    "Task",
    "TaskStatus",
    "TeamInfo",
    "MailboxMessage",
    # Query
    "QueryAdapter",
    "CostSummary",
    "QueryResult",
    "StreamEvent",
    # Hook
    "HookAdapter",
    "USMSBHookResult",
    "USMSBHookRegistry",
    # MetaAgent
    "MetaAgentAdapter",
    "AgentSpec",
    "SpawnedAgent",
    "AgentState",
    "TaskResult",
    "DelegatedTask",
    # Integration
    "OpenHarnessIntegration",
    "IntegrationStatistics",
    # L2/L3/L5 Integration
    "OHL2Agent",
    "OHL2Config",
    "L3OrchestratorWithOH",
    "GoalExecutionContext",
    "MetaAgentWithOH",
    "ChildAgentInfo",
]
