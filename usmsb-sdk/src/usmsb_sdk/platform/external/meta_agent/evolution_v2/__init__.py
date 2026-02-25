"""
自主进化系统 - Self Evolution System V2

基于USMSB理论的AGI自主进化框架
"""

from .models import (
    EvolutionPhase,
    EvolutionState,
    KnowledgeState,
    CapabilityLevel,
    LearningType,
    GoalPriority,
    KnowledgeUnit,
    Capability,
    LearningGoal,
    ExplorationResult,
    MetaLearningRecord,
    SelfReflection,
    CapabilityTransfer,
    PerformanceMetric,
)

from .meta_learner import (
    MetaLearner,
    LearningStrategy,
    LearningContext,
)

from .capability_assessor import (
    CapabilityAssessor,
    AssessmentContext,
    WeaknessAnalysis,
)

from .knowledge_solidifier import (
    KnowledgeSolidifier,
    SolidificationRule,
    SolidificationResult,
)

from .curiosity_engine import (
    CuriosityEngine,
    CuriosityDomain,
    ExplorationPath,
)

from .self_optimizer import (
    SelfOptimizer,
    OptimizationParameter,
    OptimizationResult,
    StrategyAdjustment,
)

from .goal_generator import (
    GoalGenerator,
    GoalTemplate,
)

from .engine import (
    SelfEvolutionEngine,
    create_evolution_engine,
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
