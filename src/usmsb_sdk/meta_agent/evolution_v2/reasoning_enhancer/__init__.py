"""
推理增强层

ReasoningEnhancer - 完整实现

子模块：
- enhancer.py: 主类
- structured_output.py: 强制 CoT 格式
- multi_path_check.py: 多路径一致性检查
- counterexample.py: 反例驱动修正
"""

from .enhancer import ReasoningEnhancer, ReasoningResult, LightweightReasoningEnhancer
from .structured_output import (
    ReasoningParser,
    ReasoningStep,
    ReasoningTrace,
    ReasoningConsistencyChecker,
    REASONING_TEMPLATE,
)
from .multi_path_check import (
    MultiPathConsistencyChecker,
    MultiPathResult,
    SelfConsistencyChecker,
)
from .counterexample import (
    CounterexampleDrivenCorrector,
    Counterexample,
    ReflectiveCorrector,
)

__all__ = [
    "ReasoningEnhancer",
    "ReasoningResult",
    "LightweightReasoningEnhancer",
    "ReasoningParser",
    "ReasoningStep",
    "ReasoningTrace",
    "ReasoningConsistencyChecker",
    "REASONING_TEMPLATE",
    "MultiPathConsistencyChecker",
    "MultiPathResult",
    "SelfConsistencyChecker",
    "CounterexampleDrivenCorrector",
    "Counterexample",
    "ReflectiveCorrector",
]
