"""Narrow, fail-closed bindings for the pinned OpenHarness release.

The rest of USMSB imports OpenHarness through this module instead of depending
on its fast-moving internal layout.  Upgrading OpenHarness therefore requires
changing this file and the accompanying contract tests together.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib import metadata
from typing import Any

from usmsb_sdk.adapters.openharness.exceptions import OpenHarnessNotAvailableError

OPENHARNESS_DISTRIBUTION = "openharness-ai"
OPENHARNESS_VERSION = "0.1.9"
OPENHARNESS_TAG = "v0.1.9"
OPENHARNESS_COMMIT = "a0f8552c69d6d0b25d613af288823212a8b6b59a"


@dataclass(frozen=True)
class OpenHarnessCapabilities:
    """Runtime capability probe returned without triggering external work."""

    available: bool
    version: str | None
    query_engine: bool
    tool_registry: bool
    permissions: bool
    hooks: bool
    memory: bool
    compaction: bool
    swarm: bool
    error: str | None = None

    @property
    def compatible(self) -> bool:
        return bool(
            self.available
            and self.version == OPENHARNESS_VERSION
            and self.query_engine
            and self.tool_registry
            and self.permissions
            and self.hooks
            and self.memory
            and self.compaction
            and self.swarm
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["compatible"] = self.compatible
        value["expected_version"] = OPENHARNESS_VERSION
        value["expected_commit"] = OPENHARNESS_COMMIT
        return value


def probe_openharness() -> OpenHarnessCapabilities:
    """Inspect the exact API surface consumed by USMSB.

    This intentionally imports every required subsystem.  A partially
    compatible installation is reported as unavailable rather than silently
    degrading to a fixed local workflow.
    """

    try:
        version = metadata.version(OPENHARNESS_DISTRIBUTION)

        from openharness.engine.query_engine import QueryEngine  # noqa: F401
        from openharness.tools.base import (  # noqa: F401
            BaseTool,
            ToolExecutionContext,
            ToolRegistry,
            ToolResult,
        )
        from openharness.permissions.checker import PermissionChecker  # noqa: F401
        from openharness.hooks import HookEvent, HookExecutor  # noqa: F401
        from openharness.memory.manager import (  # noqa: F401
            add_memory_entry,
            list_memory_files,
            remove_memory_entry,
        )
        from openharness.memory.search import find_relevant_memories  # noqa: F401
        from openharness.services.compact import (  # noqa: F401
            build_post_compact_messages,
            compact_messages,
            try_context_collapse,
        )
        from openharness.swarm.mailbox import TeammateMailbox  # noqa: F401
        from openharness.swarm.team_lifecycle import TeamLifecycleManager  # noqa: F401
    except Exception as error:  # import/version probing must be fail-closed
        return OpenHarnessCapabilities(
            available=False,
            version=None,
            query_engine=False,
            tool_registry=False,
            permissions=False,
            hooks=False,
            memory=False,
            compaction=False,
            swarm=False,
            error=f"{type(error).__name__}: {error}",
        )

    exact = version == OPENHARNESS_VERSION
    return OpenHarnessCapabilities(
        available=True,
        version=version,
        query_engine=exact,
        tool_registry=exact,
        permissions=exact,
        hooks=exact,
        memory=exact,
        compaction=exact,
        swarm=exact,
        error=None if exact else f"expected {OPENHARNESS_VERSION}, installed {version}",
    )


def require_openharness_019() -> OpenHarnessCapabilities:
    """Return compatible capabilities or reject before any model/tool call."""

    capabilities = probe_openharness()
    if not capabilities.compatible:
        raise OpenHarnessNotAvailableError(
            "OpenHarness compatibility check failed; install "
            f"{OPENHARNESS_DISTRIBUTION}=={OPENHARNESS_VERSION}. "
            f"Probe: {capabilities.to_dict()}"
        )
    return capabilities

