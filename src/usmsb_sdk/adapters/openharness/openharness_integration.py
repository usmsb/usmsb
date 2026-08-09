"""Unified USMSB facade for the pinned OpenHarness 0.1.9 runtime.

This facade deliberately does not recreate the removed 0.1.0 ``SimpleHarness``
API.  OpenHarness 0.1.9 exposes a ``QueryEngine`` agent loop plus independent
tool, permission, hook, memory and swarm subsystems; USMSB composes those
capabilities through narrow adapters and fails closed when the exact contract
is unavailable.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from usmsb_sdk.adapters.openharness.compatibility import (
    OPENHARNESS_VERSION,
    OpenHarnessCapabilities,
    require_openharness_019,
)
from usmsb_sdk.adapters.openharness.config import OpenHarnessConfig, USMSBConfig
from usmsb_sdk.adapters.openharness.exceptions import ConfigurationError
from usmsb_sdk.adapters.openharness.hook_adapter import HookAdapter
from usmsb_sdk.adapters.openharness.memory_adapter import MemoryAdapter
from usmsb_sdk.adapters.openharness.meta_agent_adapter import MetaAgentAdapter
from usmsb_sdk.adapters.openharness.permission_adapter import PermissionAdapter
from usmsb_sdk.adapters.openharness.query_adapter import QueryAdapter
from usmsb_sdk.adapters.openharness.swarm_adapter import SwarmAdapter
from usmsb_sdk.adapters.openharness.tool_adapter import ToolAdapter, ToolExecutionResult


@dataclass
class IntegrationStatistics:
    """Non-canonical operational counters for the adapter facade."""

    tools_executed: int = 0
    total_execution_time_ms: float = 0.0
    query_engines_bound: int = 0
    compatibility_checks: int = 0
    last_reset: float = field(default_factory=time.time)


class OpenHarnessIntegration:
    """Construct the 0.1.9 adapters without initiating external work."""

    def __init__(
        self,
        config: OpenHarnessConfig | None = None,
        usmsb_config: USMSBConfig | None = None,
        cwd: str | Path = ".",
        *,
        query_engine: Any | None = None,
    ) -> None:
        self._config = config or OpenHarnessConfig()
        self._usmsb_config = usmsb_config or USMSBConfig()
        self._cwd = Path(cwd).resolve()
        self._query_engine = query_engine
        self._capabilities: OpenHarnessCapabilities | None = None
        self._stats = IntegrationStatistics()
        self._initialized = False

        self.tool_adapter: ToolAdapter | None = None
        self.permission_adapter: PermissionAdapter | None = None
        self.memory_adapter: MemoryAdapter | None = None
        self.swarm_adapter: SwarmAdapter | None = None
        self.query_adapter: QueryAdapter | None = None
        self.hook_adapter: HookAdapter | None = None
        self.meta_agent_adapter: MetaAgentAdapter | None = None

    @classmethod
    def from_env(
        cls,
        usmsb_config: USMSBConfig | None = None,
        cwd: str | Path = ".",
        *,
        query_engine: Any | None = None,
    ) -> "OpenHarnessIntegration":
        return cls(
            config=OpenHarnessConfig.from_env(),
            usmsb_config=usmsb_config,
            cwd=cwd,
            query_engine=query_engine,
        )

    async def initialize(self) -> None:
        if self._initialized:
            return

        capabilities = require_openharness_019()
        self._stats.compatibility_checks += 1
        if self._config.oh_version != f"=={OPENHARNESS_VERSION}":
            raise ConfigurationError(
                message=(
                    "OpenHarnessConfig.oh_version must remain exactly "
                    f"=={OPENHARNESS_VERSION}; got {self._config.oh_version!r}"
                )
            )

        permission_adapter = PermissionAdapter(
            config=self._config.permission,
            cwd=self._cwd,
        )
        tool_adapter = ToolAdapter(
            permission_checker=permission_adapter.checker,
            cwd=self._cwd,
        )
        self.permission_adapter = permission_adapter
        self.tool_adapter = tool_adapter
        self.memory_adapter = MemoryAdapter(cwd=self._cwd, config=self._config.memory)
        self.hook_adapter = HookAdapter(config=self._config.hook, cwd=self._cwd)
        self.query_adapter = QueryAdapter(
            engine=self._query_engine,
            config=self._config.llm,
            cwd=self._cwd,
        )
        self.swarm_adapter = SwarmAdapter(config=self._config.swarm)
        self.meta_agent_adapter = MetaAgentAdapter(config=self._config.swarm)
        self._capabilities = capabilities
        self._initialized = True
        if self._query_engine is not None:
            self._stats.query_engines_bound += 1

    def is_initialized(self) -> bool:
        return self._initialized

    def runtime_status(self) -> dict[str, Any]:
        """Report physical readiness without equating adapters with a bound model."""

        query_engine_bound = self._query_engine is not None
        return {
            "adapter_initialized": self._initialized,
            "query_engine_bound": query_engine_bound,
            "cognitive_ready": self._initialized and query_engine_bound,
            "tool_bridge_mode": "explicit_adapter_only",
            "openharness_version": OPENHARNESS_VERSION,
        }

    @property
    def capabilities(self) -> OpenHarnessCapabilities:
        if self._capabilities is None:
            raise ConfigurationError(message="OpenHarness integration is not initialized")
        return self._capabilities

    async def bind_query_engine(self, engine: Any) -> None:
        """Bind the OPC-instrumented QueryEngine used for physical LLM calls."""

        if not self._initialized or self.query_adapter is None:
            self._query_engine = engine
            return
        await self.query_adapter.set_engine(engine)
        self._query_engine = engine
        self._stats.query_engines_bound += 1

    async def execute_tool(
        self,
        tool_name: str,
        *,
        check_permission: bool = True,
        **arguments: Any,
    ) -> ToolExecutionResult:
        if not self._initialized or self.tool_adapter is None:
            raise ConfigurationError(message="Call await initialize() before executing tools")
        started = time.monotonic()
        result = await self.tool_adapter.execute_tool(
            tool_name,
            check_permission=check_permission,
            **arguments,
        )
        self._stats.tools_executed += 1
        self._stats.total_execution_time_ms += (time.monotonic() - started) * 1000
        return result

    def get_statistics(self) -> IntegrationStatistics:
        return self._stats

    def reset_statistics(self) -> None:
        self._stats = IntegrationStatistics()

    def create_harness(self, *_: Any, **__: Any) -> None:
        """Reject the removed 0.1.0 API instead of returning a fake harness."""

        raise ConfigurationError(
            message=(
                "OpenHarness 0.1.9 has no SimpleHarness API. Bind a QueryEngine "
                "or use usmsb_sdk.growth_economic_harness.GrowthEconomicHarness."
            )
        )

    def __repr__(self) -> str:
        return (
            "OpenHarnessIntegration("
            f"initialized={self._initialized}, version={OPENHARNESS_VERSION!r})"
        )


OpenHarnessIntegration_v1 = OpenHarnessIntegration
