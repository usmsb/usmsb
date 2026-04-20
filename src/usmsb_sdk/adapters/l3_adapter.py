"""
L3 Adapter Re-export

Re-exports L3Adapter from meta_agent.adapters.l3_adapter to provide
backwards-compatible import path: usmsb_sdk.adapters.l3_adapter
"""

from usmsb_sdk.meta_agent.adapters.l3_adapter import (
    L3Adapter,
    Goal,
    MotivationSignal,
)

__all__ = ["L3Adapter", "Goal", "MotivationSignal"]
