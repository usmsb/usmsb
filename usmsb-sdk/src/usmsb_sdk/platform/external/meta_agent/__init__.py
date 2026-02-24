"""
Meta Agent - 超级 Agent
基于 USMSB 模型，具备自主运营、自主学习、自主进化能力
"""

from .agent import MetaAgent
from .meta_agent_config import MetaAgentConfig
from .migrate.data_migration import DataMigration, MigrationProgress, MigrationResult

__all__ = [
    "MetaAgent",
    "MetaAgentConfig",
    "DataMigration",
    "MigrationProgress",
    "MigrationResult",
]

__version__ = "1.0.0"
