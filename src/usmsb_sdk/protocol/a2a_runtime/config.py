"""USMSB 生产级 A2A 运行时 —— 配置对象。

移植自 opc-platform/agents/local_a2a_runtime，去掉 OPC 耦合字段，
泛化为 USMSB 经济 Agent 通用配置。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AgentSkill:
    """Agent Card 中对外公布的一项技能。"""

    id: str
    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    input_modes: list[str] = field(default_factory=lambda: ["text/plain", "application/json"])
    output_modes: list[str] = field(default_factory=lambda: ["application/json", "text/plain"])

    def to_agent_card_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "examples": self.examples,
            "inputModes": self.input_modes,
            "outputModes": self.output_modes,
        }


@dataclass
class AgentRuntimeConfig:
    """一个独立部署的经济 Agent 的运行时配置。"""

    agent_id: str
    name: str
    description: str
    base_url: str
    data_dir: Path | str
    version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = 9501
    skills: list[AgentSkill] = field(default_factory=list)
    default_input_modes: list[str] = field(default_factory=lambda: ["text/plain", "application/json"])
    default_output_modes: list[str] = field(default_factory=lambda: ["application/json", "text/plain"])
    max_concurrency: int = 1
    lock_seconds: int = 300
    poll_interval_seconds: float = 1.0
    execute_inline_on_submit: bool = False
    max_attempts: int = 3
    # 是否在本 Agent 上启用 VIBE 结算闭环（escrow → settle / refund）
    settlement_enabled: bool = False

    @property
    def root_dir(self) -> Path:
        return Path(self.data_dir)

    @property
    def db_path(self) -> Path:
        return self.root_dir / "a2a_jobs.db"

    @property
    def assets_dir(self) -> Path:
        return self.root_dir / "assets"

    @property
    def logs_dir(self) -> Path:
        return self.root_dir / "logs"

    @property
    def rpc_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/a2a"

    @property
    def agent_card_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/.well-known/agent.json"
