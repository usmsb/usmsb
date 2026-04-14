# -*- coding: utf-8 -*-
"""
Phase 5: Self-Evolution
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

__all__ = [
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
]
