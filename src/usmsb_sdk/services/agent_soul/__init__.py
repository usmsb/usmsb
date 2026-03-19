"""
Agent Soul Module.

Phase 1 of USMSB Agent Platform implementation.

Exports:
- AgentSoul, DeclaredSoul, InferredSoul models
- AgentSoulManager for Soul lifecycle management
"""

from usmsb_sdk.services.agent_soul.manager import AgentSoulManager
from usmsb_sdk.services.agent_soul.models import AgentSoul, DeclaredSoul, InferredSoul

__all__ = [
    "AgentSoul",
    "DeclaredSoul",
    "InferredSoul",
    "AgentSoulManager",
]
