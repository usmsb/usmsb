"""
意图识别模块

使用 LLM 智能识别用户意图，替代简单的关键词匹配
"""

from .recognizer import (
    Intent,
    IntentRecognizer,
    IntentResult,
    IntentType,
)

__all__ = [
    "IntentRecognizer",
    "Intent",
    "IntentType",
    "IntentResult",
]
