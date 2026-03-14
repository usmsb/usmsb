"""
AGI Reasoning Engine Module

支持复杂推理的AGI推理引擎，包含：
- 逻辑推理（演绎、归纳、溯因）
- 因果推理（因果关系、反事实推理）
- 类比推理（相似性映射）
- 空间推理（位置、方向、距离）
- 时间推理（时序、持续时间、频率）
- 常识推理（物理常识、社会常识）
- 元推理（关于推理的推理）
"""

from usmsb_sdk.reasoning.base import (
    BaseReasoningEngine,
    ReasoningChain,
    ReasoningContext,
)
from usmsb_sdk.reasoning.chain_manager import (
    ChainExecutionResult,
    ReasoningChainManager,
)
from usmsb_sdk.reasoning.engines import (
    AbductiveEngine,
    AnalogicalEngine,
    CausalEngine,
    CommonsenseEngine,
    DeductiveEngine,
    InductiveEngine,
    MetaReasoningEngine,
    SpatialEngine,
    TemporalEngine,
)
from usmsb_sdk.reasoning.interfaces import (
    ConfidenceScore,
    IKnowledgeGraphAdapter,
    IReasoningChain,
    IReasoningEngine,
    ReasoningResult,
    ReasoningStep,
    ReasoningType,
    UncertaintyMeasure,
)
from usmsb_sdk.reasoning.knowledge_integration import (
    ConceptNode,
    KnowledgeGraphIntegration,
    RelationEdge,
    TripleStore,
)
from usmsb_sdk.reasoning.uncertainty import (
    BayesianNetwork,
    DempsterShafer,
    FuzzySet,
    ProbabilityDistribution,
    UncertaintyManager,
)

__all__ = [
    # Interfaces
    "IReasoningEngine",
    "IReasoningChain",
    "IKnowledgeGraphAdapter",
    "ReasoningType",
    "ReasoningResult",
    "ReasoningStep",
    "ConfidenceScore",
    "UncertaintyMeasure",
    # Base classes
    "BaseReasoningEngine",
    "ReasoningContext",
    "ReasoningChain",
    # Engines
    "DeductiveEngine",
    "InductiveEngine",
    "AbductiveEngine",
    "CausalEngine",
    "AnalogicalEngine",
    "SpatialEngine",
    "TemporalEngine",
    "CommonsenseEngine",
    "MetaReasoningEngine",
    # Uncertainty
    "ProbabilityDistribution",
    "FuzzySet",
    "DempsterShafer",
    "BayesianNetwork",
    "UncertaintyManager",
    # Chain management
    "ReasoningChainManager",
    "ChainExecutionResult",
    # Knowledge integration
    "KnowledgeGraphIntegration",
    "TripleStore",
    "ConceptNode",
    "RelationEdge",
]
