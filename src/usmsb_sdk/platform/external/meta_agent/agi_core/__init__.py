"""
AGI Core - 知识库与记忆系统核心模块

整合专业版组件的统一接口：
- evolution_v2/  - 专业进化系统
- reasoning/     - 专业推理系统
- agi_core/      - 记忆系统和知识图谱（本地实现）
"""

from .memory import AGIMemorySystem, MemoryLayer, MemoryItem, MemoryConfig
from .knowledge_graph import DynamicKnowledgeGraph, KnowledgeNode, KnowledgeEdge, RelationType
from .integration import AGICoreSystem, AGICoreConfig

from usmsb_sdk.platform.external.meta_agent.evolution_v2 import (
    SelfEvolutionEngine,
    create_evolution_engine,
    EvolutionPhase,
    KnowledgeState,
)

from usmsb_sdk.reasoning import (
    IReasoningEngine,
    ReasoningResult,
    ReasoningType,
    ReasoningChainManager,
    DeductiveEngine,
    InductiveEngine,
    AbductiveEngine,
    CausalEngine,
    AnalogicalEngine,
)

__all__ = [
    "AGICoreSystem",
    "AGICoreConfig",
    "AGIMemorySystem",
    "MemoryLayer",
    "MemoryItem",
    "MemoryConfig",
    "DynamicKnowledgeGraph",
    "KnowledgeNode",
    "KnowledgeEdge",
    "RelationType",
    "SelfEvolutionEngine",
    "create_evolution_engine",
    "EvolutionPhase",
    "KnowledgeState",
    "IReasoningEngine",
    "ReasoningResult",
    "ReasoningType",
    "ReasoningChainManager",
    "DeductiveEngine",
    "InductiveEngine",
    "AbductiveEngine",
    "CausalEngine",
    "AnalogicalEngine",
]
