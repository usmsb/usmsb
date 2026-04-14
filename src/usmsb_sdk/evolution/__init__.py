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
]
