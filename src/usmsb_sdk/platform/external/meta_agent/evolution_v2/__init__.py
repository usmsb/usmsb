"""
自主进化系统 - Self Evolution System V2

基于USMSB理论的AGI自主进化框架
"""

from .capability_assessor import (
    AssessmentContext,
    CapabilityAssessor,
    WeaknessAnalysis,
)
from .curiosity_engine import (
    CuriosityDomain,
    CuriosityEngine,
    ExplorationPath,
)
from .engine import (
    SelfEvolutionEngine,
    create_evolution_engine,
)
from .goal_generator import (
    GoalGenerator,
    GoalTemplate,
)
from .knowledge_solidifier import (
    KnowledgeSolidifier,
    SolidificationResult,
    SolidificationRule,
)
from .meta_learner import (
    LearningContext,
    LearningStrategy,
    MetaLearner,
)
from .models import (
    Capability,
    CapabilityLevel,
    CapabilityTransfer,
    EvolutionPhase,
    EvolutionState,
    ExplorationResult,
    GoalPriority,
    KnowledgeState,
    KnowledgeUnit,
    LearningGoal,
    LearningType,
    MetaLearningRecord,
    PerformanceMetric,
    SelfReflection,
)
from .self_optimizer import (
    OptimizationParameter,
    OptimizationResult,
    SelfOptimizer,
    StrategyAdjustment,
)

__all__ = [
    "EvolutionPhase",
    "EvolutionState",
    "KnowledgeState",
    "CapabilityLevel",
    "LearningType",
    "GoalPriority",
    "KnowledgeUnit",
    "Capability",
    "LearningGoal",
    "ExplorationResult",
    "MetaLearningRecord",
    "SelfReflection",
    "CapabilityTransfer",
    "PerformanceMetric",
    "MetaLearner",
    "LearningStrategy",
    "LearningContext",
    "CapabilityAssessor",
    "AssessmentContext",
    "WeaknessAnalysis",
    "KnowledgeSolidifier",
    "SolidificationRule",
    "SolidificationResult",
    "CuriosityEngine",
    "CuriosityDomain",
    "ExplorationPath",
    "SelfOptimizer",
    "OptimizationParameter",
    "OptimizationResult",
    "StrategyAdjustment",
    "GoalGenerator",
    "GoalTemplate",
    "SelfEvolutionEngine",
    "create_evolution_engine",
]
