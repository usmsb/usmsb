"""
Meta Agent - 超级 Agent
基于 USMSB 模型，具备自主运营、自主学习、自主进化能力
"""

from .agent import MetaAgent
from .config import MetaAgentConfig

__all__ = [
    "MetaAgent",
    "MetaAgentConfig",
]

__version__ = "1.0.0"
