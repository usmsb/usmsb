# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
# OpenHarness Adapter Layer for USMSB Platform

"""
USMSB OpenHarness Adapter Layer

This module provides integration between USMSB's Goal Layer (L3-L5) and
OpenHarness's infrastructure layer (Tool Registry, Permission System,
Memory Management, Swarm Coordination).

Architecture:
    USMSB Goal Layer (L3-L5) → Adapters → OpenHarness Foundation (L2)

Adapters:
    - ToolAdapter: Wraps OH ToolRegistry (43+ tools)
    - PermissionAdapter: Wraps OH PermissionChecker
    - MemoryAdapter: Wraps OH Memory Manager
    - SwarmAdapter: Wraps OH TeamLifecycle
    - QueryAdapter: Wraps OH QueryEngine
    - HookAdapter: Wraps OH HookExecutor
    - MetaAgentAdapter: Wraps OH Agent Spawning

All adapters follow the Adapter Pattern to decouple USMSB from OH internals.
If OH is replaced in the future, only these adapters need to change.
"""

from usmsb_sdk.adapters.openharness import (
    ToolAdapter,
    PermissionAdapter,
    MemoryAdapter,
    SwarmAdapter,
    QueryAdapter,
    HookAdapter,
    MetaAgentAdapter,
    OpenHarnessConfig,
    OpenHarnessIntegration,
)

__all__ = [
    "ToolAdapter",
    "PermissionAdapter", 
    "MemoryAdapter",
    "SwarmAdapter",
    "QueryAdapter",
    "HookAdapter",
    "MetaAgentAdapter",
    "OpenHarnessConfig",
    "OpenHarnessIntegration",
]
