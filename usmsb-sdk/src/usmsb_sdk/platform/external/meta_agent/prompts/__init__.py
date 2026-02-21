"""
Prompts module for Meta Agent
"""

from .system_prompt import SYSTEM_PROMPT, PERSONALITY, CAPABILITIES
from .tool_prompts import TOOL_DESCRIPTIONS, get_tool_prompt

__all__ = [
    "SYSTEM_PROMPT",
    "PERSONALITY",
    "CAPABILITIES",
    "TOOL_DESCRIPTIONS",
    "get_tool_prompt",
]
