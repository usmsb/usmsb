"""
配置模块
"""

from .chat_config import ChatConfig

__all__ = ["ChatConfig"]

# 向后兼容：从父目录导入 MetaAgentConfig
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
try:
    from ..meta_agent_config import MetaAgentConfig
    __all__.append("MetaAgentConfig")
except ImportError:
    pass
