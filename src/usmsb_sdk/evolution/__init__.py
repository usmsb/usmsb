# -*- coding: utf-8 -*-
"""
Phase 5: Self-Evolution - Complete Implementation
"""

from .evolution_controller import (
    EvolutionController,
    MultiObjectiveFitnessEvaluator,
    FitnessResult,
    FitnessDimensions,
    Genome,
    Gene,
    GeneMutator,
    CrossoverOperator,
    SelfImprovementEngine,
    ImprovementSuggestion,
)

from .evo_map import (
    MemoryGraph,
    GeneRecommendation,
    GDIScorer,
    ExperienceGeneDB,
    ExperienceGene,
)

from .performance_tracker import (
    PerformanceTracker,
    PerformanceMetric,
    TaskExecution,
    AgentPerformanceReport,
)

from .knowledge_base import (
    KnowledgeBase,
    KnowledgeEntry,
    KnowledgeContribution,
)

from .experience_inheritance import (
    ExperienceInheritance,
    InheritedExperience,
    ExperienceSnapshot,
)

from .fitness_evaluator import (
    FitnessEvaluator,
    FitnessScore,
    FitnessHistory,
)

from .replication_engine import (
    ReplicationEngine,
    ReplicationRequest,
    Replica,
)

from .capability_growth import (
    CapabilityGrowth,
    CapabilityRecord,
    LearningEvent,
    CapabilityProfile,
)

from .auto_elimination import (
    AutoElimination,
)
from .gene_constraint_checker import (
    GeneConstraintChecker,
    ConstraintViolation,
    SafetyReport,
)

__all__ = [
    # Core Evolution
    "EvolutionController",
    "MultiObjectiveFitnessEvaluator",
    "FitnessResult",
    "FitnessDimensions",
    "Genome",
    "Gene",
    "GeneMutator",
    "CrossoverOperator",
    "SelfImprovementEngine",
    "ImprovementSuggestion",

    # EvoMap
    "MemoryGraph",
    "GeneRecommendation",
    "GDIScorer",
    "ExperienceGeneDB",
    "ExperienceGene",

    # Performance
    "PerformanceTracker",
    "PerformanceMetric",
    "TaskExecution",
    "AgentPerformanceReport",

    # Knowledge
    "KnowledgeBase",
    "KnowledgeEntry",
    "KnowledgeContribution",

    # Inheritance
    "ExperienceInheritance",
    "InheritedExperience",
    "ExperienceSnapshot",

    # Fitness
    "FitnessEvaluator",
    "FitnessScore",
    "FitnessHistory",

    # Replication
    "ReplicationEngine",
    "ReplicationRequest",
    "Replica",

    # Capability
    "CapabilityGrowth",
    "CapabilityRecord",
    "LearningEvent",
    "CapabilityProfile",

    # Constraints
    "GeneConstraintChecker",
    "AutoElimination",
    "EvolutionLoop",
    "ConstraintViolation",
    "SafetyReport",
]
