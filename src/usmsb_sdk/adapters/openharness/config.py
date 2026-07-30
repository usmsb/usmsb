# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
# OpenHarness Configuration for USMSB Platform

"""
Configuration dataclasses for OpenHarness integration.

This module defines all configuration options needed to integrate
OpenHarness with USMSB. Configuration can be loaded from:
    1. Environment variables
    2. YAML config files
    3. Direct Python objects

Environment Variables:
    OPENHARNESS_VERSION: str (default: "==0.1.9")
    OPENHARNESS_API_BASE: str (default: "https://api.minimaxi.com")
    OPENHARNESS_API_KEY: str (optional)
    OPENHARNESS_MODEL: str (default: "minimax-m1")
    OPENHARNESS_MAX_TOKENS: int (default: 4096)
    OPENHARNESS_CONTEXT_WINDOW: int (default: 100000)
    OPENHARNESS_PERMISSION_MODE: str (default: "moderate")
    OPENHARNESS_MEMORY_DIR: str (default: "~/.usmsb/memory")
    OPENHARNESS_TEAMS_DIR: str (default: "~/.openharness/teams")
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class PermissionMode(str, Enum):
    """OpenHarness permission mode."""
    FULL_AUTO = "full_auto"
    MODERATE = "moderate"
    PLAN = "plan"


class SwarmBackend(str, Enum):
    """Swarm coordination backend."""
    TMUX = "tmux"
    SUBPROCESS = "subprocess"
    WORKTREE = "worktree"


class LLMProvider(str, Enum):
    """LLM provider selection."""
    MINIMAX = "minimax"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


@dataclass
class ToolConfig:
    """Tool execution configuration."""
    timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: float = 1.0


@dataclass
class PermissionConfig:
    """Permission system configuration."""
    mode: PermissionMode = PermissionMode.MODERATE
    denied_tools: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    denied_commands: list[str] = field(default_factory=list)
    allowed_paths: list[str] = field(default_factory=list)
    denied_paths: list[str] = field(default_factory=list)
    path_rules: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class MemoryConfig:
    """Memory management configuration."""
    persist_path: str = "~/.usmsb/memory"
    compact_threshold_tokens: int = 8000
    max_memory_files: int = 100
    auto_compact: bool = True


@dataclass
class SwarmConfig:
    """Swarm coordination configuration."""
    backend: SwarmBackend = SwarmBackend.SUBPROCESS
    teams_dir: str = "~/.openharness/teams"
    team_lifecycle_enabled: bool = True
    mailbox_enabled: bool = True


@dataclass
class HookConfig:
    """Hook system configuration."""
    pre_tool_hooks: list[str] = field(default_factory=list)
    post_tool_hooks: list[str] = field(default_factory=list)
    hook_timeout_seconds: int = 30
    hook_registry_path: Optional[str] = None


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: LLMProvider = LLMProvider.MINIMAX
    model: str = "minimax-m1"
    api_base_url: str = "https://api.minimaxi.com"
    api_key: Optional[str] = None
    max_tokens: int = 4096
    context_window_tokens: int = 100000
    max_turns: int = 8


@dataclass
class OpenHarnessConfig:
    """
    Master configuration for OpenHarness integration.
    
    This dataclass aggregates all sub-configurations and provides
    convenient loading from environment variables.
    
    Example:
        >>> config = OpenHarnessConfig.from_env()
        >>> integration = OpenHarnessIntegration(config)
    """
    # Version constraint
    oh_version: str = "==0.1.9"
    
    # Sub-configurations
    tool: ToolConfig = field(default_factory=ToolConfig)
    permission: PermissionConfig = field(default_factory=PermissionConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    swarm: SwarmConfig = field(default_factory=SwarmConfig)
    hook: HookConfig = field(default_factory=HookConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    
    # Runtime paths
    cwd: str = field(default_factory=lambda: os.getcwd())
    
    @classmethod
    def from_env(cls) -> "OpenHarnessConfig":
        """Load configuration from environment variables."""
        config = cls()
        
        # Tool config
        if timeout := os.getenv("OPENHARNESS_TOOL_TIMEOUT"):
            config.tool.timeout_seconds = int(timeout)
        if retries := os.getenv("OPENHARNESS_MAX_RETRIES"):
            config.tool.max_retries = int(retries)
            
        # Permission config
        if mode := os.getenv("OPENHARNESS_PERMISSION_MODE"):
            config.permission.mode = PermissionMode(mode.lower())
        if denied := os.getenv("OPENHARNESS_DENIED_TOOLS"):
            config.permission.denied_tools = denied.split(",")
        if allowed := os.getenv("OPENHARNESS_ALLOWED_TOOLS"):
            config.permission.allowed_tools = allowed.split(",")
            
        # Memory config
        if memory_path := os.getenv("OPENHARNESS_MEMORY_DIR"):
            config.memory.persist_path = memory_path
            
        # Swarm config
        if backend := os.getenv("OPENHARNESS_SWARM_BACKEND"):
            config.swarm.backend = SwarmBackend(backend.lower())
        if teams_dir := os.getenv("OPENHARNESS_TEAMS_DIR"):
            config.swarm.teams_dir = teams_dir
            
        # LLM config
        if provider := os.getenv("OPENHARNESS_LLM_PROVIDER"):
            config.llm.provider = LLMProvider(provider.lower())
        if model := os.getenv("OPENHARNESS_MODEL"):
            config.llm.model = model
        if api_base := os.getenv("OPENHARNESS_API_BASE"):
            config.llm.api_base_url = api_base
        if api_key := os.getenv("OPENHARNESS_API_KEY"):
            config.llm.api_key = api_key
        if max_tokens := os.getenv("OPENHARNESS_MAX_TOKENS"):
            config.llm.max_tokens = int(max_tokens)
            
        # Runtime
        if cwd := os.getenv("OPENHARNESS_CWD"):
            config.cwd = cwd
            
        return config
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OpenHarnessConfig":
        """Load configuration from dictionary."""
        config = cls()
        
        if "oh_version" in data:
            config.oh_version = data["oh_version"]
        if "tool" in data:
            for key, value in data["tool"].items():
                if hasattr(config.tool, key):
                    setattr(config.tool, key, value)
        if "permission" in data:
            for key, value in data["permission"].items():
                if hasattr(config.permission, key):
                    setattr(config.permission, key, value)
        if "memory" in data:
            for key, value in data["memory"].items():
                if hasattr(config.memory, key):
                    setattr(config.memory, key, value)
        if "swarm" in data:
            for key, value in data["swarm"].items():
                if hasattr(config.swarm, key):
                    setattr(config.swarm, key, value)
        if "hook" in data:
            for key, value in data["hook"].items():
                if hasattr(config.hook, key):
                    setattr(config.hook, key, value)
        if "llm" in data:
            for key, value in data["llm"].items():
                if hasattr(config.llm, key):
                    setattr(config.llm, key, value)
        if "cwd" in data:
            config.cwd = data["cwd"]
            
        return config
    
    def to_dict(self) -> dict[str, Any]:
        """Export configuration to dictionary."""
        return {
            "oh_version": self.oh_version,
            "tool": {
                "timeout_seconds": self.tool.timeout_seconds,
                "max_retries": self.tool.max_retries,
                "retry_delay_seconds": self.tool.retry_delay_seconds,
            },
            "permission": {
                "mode": self.permission.mode.value,
                "denied_tools": self.permission.denied_tools,
                "allowed_tools": self.permission.allowed_tools,
                "denied_commands": self.permission.denied_commands,
                "allowed_paths": self.permission.allowed_paths,
                "denied_paths": self.permission.denied_paths,
                "path_rules": self.permission.path_rules,
            },
            "memory": {
                "persist_path": self.memory.persist_path,
                "compact_threshold_tokens": self.memory.compact_threshold_tokens,
                "max_memory_files": self.memory.max_memory_files,
                "auto_compact": self.memory.auto_compact,
            },
            "swarm": {
                "backend": self.swarm.backend.value,
                "teams_dir": self.swarm.teams_dir,
                "team_lifecycle_enabled": self.swarm.team_lifecycle_enabled,
                "mailbox_enabled": self.swarm.mailbox_enabled,
            },
            "hook": {
                "pre_tool_hooks": self.hook.pre_tool_hooks,
                "post_tool_hooks": self.hook.post_tool_hooks,
                "hook_timeout_seconds": self.hook.hook_timeout_seconds,
                "hook_registry_path": self.hook.hook_registry_path,
            },
            "llm": {
                "provider": self.llm.provider.value,
                "model": self.llm.model,
                "api_base_url": self.llm.api_base_url,
                "max_tokens": self.llm.max_tokens,
                "context_window_tokens": self.llm.context_window_tokens,
                "max_turns": self.llm.max_turns,
            },
            "cwd": self.cwd,
        }


@dataclass 
class USMSBConfig:
    """
    USMSB-specific configuration for Goal Layer.
    
    These settings control how USMSB's cognitive architecture
    interacts with the OpenHarness infrastructure.
    """
    # Goal layer settings
    goal_generation_interval_seconds: int = 60
    max_concurrent_goals: int = 5
    goal_persistence_enabled: bool = True
    
    # Value layer settings
    value_token: str = "VIBE"
    value_threshold: float = 0.5
    
    # Evolution settings
    evolution_enabled: bool = True
    mutation_probability: float = 0.1
    elite_ratio: float = 0.1
    
    # L3 settings
    self_observation_enabled: bool = True
    intrinsic_motivation_enabled: bool = True
    
    # L4 settings
    theory_of_mind_enabled: bool = True
    emotional_response_enabled: bool = True
    
    # L5 settings
    gossip_protocol_enabled: bool = True
    collective_decision_enabled: bool = True
