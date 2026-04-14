# -*- coding: utf-8 -*-
"""
Phase 3-5 完整实现

Phase 3: Intelligent Optimization
Phase 4: Emergence System
Phase 5: Self-Evolution
"""

# Phase 3: Intelligent Optimization
from .market_feedback_loop import (
    MarketFeedbackLoop,
    FeedbackRecord,
    TrendAnalysis,
    PriceRecommendation,
    DemandForecast,
    ABTestResult,
    MarketFeedbackDB,
    TrendDetector,
    PriceOptimizer,
    DemandForecaster,
    ABTestEngine,
)

# Phase 4: Emergence System
from .emergence_system import (
    EmergenceSystem,
    GossipProtocol,
    GossipMessage,
    NodeState,
    TeamFormationAlgorithm,
    Team,
    PatternDetection,
    GlobalCoordination,
    CoordinationAction,
)

# Phase 5: Self-Evolution
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
    # Phase 3: Intelligent Optimization
    "MarketFeedbackLoop",
    "FeedbackRecord",
    "TrendAnalysis",
    "PriceRecommendation",
    "DemandForecast",
    "ABTestResult",
    "MarketFeedbackDB",
    "TrendDetector",
    "PriceOptimizer",
    "DemandForecaster",
    "ABTestEngine",

    # Phase 4: Emergence System
    "EmergenceSystem",
    "GossipProtocol",
    "GossipMessage",
    "NodeState",
    "TeamFormationAlgorithm",
    "Team",
    "PatternDetection",
    "GlobalCoordination",
    "CoordinationAction",

    # Phase 5: Self-Evolution
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
