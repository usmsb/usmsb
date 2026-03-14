"""
Learning Module

Manages agent learning, optimization, and market insights.
Enables agents to improve their performance over time.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from usmsb_sdk.agent_sdk.platform_client import PlatformClient

logger = logging.getLogger(__name__)


class InsightCategory(Enum):
    """Categories of learning insights"""
    PRICING = "pricing"
    TIMING = "timing"
    CAPABILITY = "capability"
    PARTNER = "partner"
    MARKET = "market"
    PERFORMANCE = "performance"


class ConfidenceLevel(Enum):
    """Confidence levels for insights"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class LearningInsight:
    """A learning insight for the agent"""
    insight_id: str
    category: str
    title: str
    description: str
    confidence: float
    actionable_recommendations: list[str]
    supporting_data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None

    @property
    def confidence_level(self) -> str:
        if self.confidence >= 0.8:
            return "very_high"
        elif self.confidence >= 0.6:
            return "high"
        elif self.confidence >= 0.4:
            return "medium"
        return "low"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningInsight":
        return cls(
            insight_id=data.get("insight_id", ""),
            category=data.get("category", "performance"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            confidence=data.get("confidence", 0.5),
            actionable_recommendations=data.get("actionable_recommendations", data.get("recommendations", [])),
            supporting_data=data.get("supporting_data", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level,
            "actionable_recommendations": self.actionable_recommendations,
            "supporting_data": self.supporting_data,
        }


@dataclass
class SuccessPattern:
    """A pattern associated with successful outcomes"""
    pattern_id: str
    name: str
    description: str
    conditions: dict[str, Any]
    success_rate: float
    sample_size: int
    factors: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SuccessPattern":
        return cls(
            pattern_id=data.get("pattern_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            conditions=data.get("conditions", {}),
            success_rate=data.get("success_rate", 0.0),
            sample_size=data.get("sample_size", 0),
            factors=data.get("factors", []),
        )


@dataclass
class PerformanceAnalysis:
    """Analysis of agent performance"""
    agent_id: str
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    total_revenue: float
    average_rating: float
    completion_rate: float
    top_capabilities: list[str]
    improvement_areas: list[str]
    trends: dict[str, Any]

    @property
    def success_rate(self) -> float:
        if self.total_transactions == 0:
            return 0.0
        return self.successful_transactions / self.total_transactions

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PerformanceAnalysis":
        return cls(
            agent_id=data.get("agent_id", ""),
            total_transactions=data.get("total_transactions", 0),
            successful_transactions=data.get("successful_transactions", 0),
            failed_transactions=data.get("failed_transactions", 0),
            total_revenue=data.get("total_revenue", 0.0),
            average_rating=data.get("average_rating", 0.0),
            completion_rate=data.get("completion_rate", 0.0),
            top_capabilities=data.get("top_capabilities", []),
            improvement_areas=data.get("improvement_areas", []),
            trends=data.get("trends", {}),
        )


@dataclass
class MatchingStrategy:
    """Optimized matching strategy for the agent"""
    optimal_price_range: dict[str, float]
    best_contact_timing: list[str]
    preferred_partner_types: list[str]
    focus_capabilities: list[str]
    negotiation_approach: str
    recommended_availability: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MatchingStrategy":
        strategy = data.get("strategy", data)
        return cls(
            optimal_price_range=strategy.get("optimal_price_range", {"min": 0, "max": 0}),
            best_contact_timing=strategy.get("best_contact_timing", ["anytime"]),
            preferred_partner_types=strategy.get("preferred_partner_types", []),
            focus_capabilities=strategy.get("focus_capabilities", []),
            negotiation_approach=strategy.get("recommended_negotiation_strategy", "balanced"),
            recommended_availability=strategy.get("recommended_availability", "24/7"),
        )


@dataclass
class PriceRange:
    """Optimal price range"""
    min: float
    max: float
    recommended: float
    confidence: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PriceRange":
        return cls(
            min=data.get("min", 0),
            max=data.get("max", 0),
            recommended=data.get("recommended", (data.get("min", 0) + data.get("max", 0)) / 2),
            confidence=data.get("confidence", 0.5),
        )


@dataclass
class MarketInsights:
    """Market insights and analysis"""
    demand_level: str
    supply_level: str
    opportunity_areas: list[str]
    recommendations: list[str]
    hot_skills: list[str]
    trending_categories: list[str]
    average_prices: dict[str, float]
    competitor_count: int
    supply_demand_ratio: float
    market_trends: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MarketInsights":
        return cls(
            demand_level=data.get("demand_level", "medium"),
            supply_level=data.get("supply_level", "medium"),
            opportunity_areas=data.get("opportunity_areas", data.get("hot_skills", [])),
            recommendations=data.get("recommendations", []),
            hot_skills=data.get("hot_skills", []),
            trending_categories=data.get("trending_categories", []),
            average_prices=data.get("average_prices", {}),
            competitor_count=data.get("total_agents", data.get("competitor_count", 0)),
            supply_demand_ratio=1.0,
            market_trends=data.get("market_trends", []),
        )


@dataclass
class CompetitiveAnalysis:
    """Competitive analysis for a capability"""
    capability: str
    my_ranking: int
    total_competitors: int
    market_share: float
    competitive_advantages: list[str]
    improvement_suggestions: list[str]
    price_position: str  # budget, competitive, premium

    @property
    def percentile(self) -> float:
        if self.total_competitors == 0:
            return 100.0
        return (1 - (self.my_ranking - 1) / self.total_competitors) * 100


@dataclass
class DemandForecast:
    """Demand forecast for a capability"""
    capability: str
    current_demand: float
    predicted_demand_7d: float
    predicted_demand_30d: float
    trend: str  # increasing, stable, decreasing
    confidence: float
    factors: list[str]


@dataclass
class Experience:
    """An experience to report for learning"""
    experience_type: str  # transaction, negotiation, collaboration
    outcome: str  # success, failure, partial
    details: dict[str, Any]
    lessons_learned: list[str]
    rating: int | None = None
    feedback: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "experience_type": self.experience_type,
            "outcome": self.outcome,
            "details": self.details,
            "lessons_learned": self.lessons_learned,
            "rating": self.rating,
            "feedback": self.feedback,
        }


class LearningManager:
    """
    Manages agent learning and optimization.

    Features:
    - Performance analysis
    - Learning insights
    - Strategy optimization
    - Market analysis
    - Competitive intelligence
    """

    def __init__(
        self,
        platform_client: PlatformClient,
        agent_id: str,
        logger: logging.Logger | None = None,
    ):
        self._platform = platform_client
        self.agent_id = agent_id
        self.logger = logger or logging.getLogger(__name__)

        # Caches
        self._insights_cache: list[LearningInsight] | None = None
        self._strategy_cache: MatchingStrategy | None = None
        self._market_cache: MarketInsights | None = None
        self._cache_time: datetime | None = None
        self._cache_ttl = 300  # 5 minutes

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self._cache_time:
            return False
        return (datetime.now() - self._cache_time).total_seconds() < self._cache_ttl

    # ==================== Performance Analysis ====================

    async def analyze_performance(self) -> PerformanceAnalysis:
        """Analyze agent's performance"""
        response = await self._platform.analyze_learning()

        if response.success and response.data:
            return PerformanceAnalysis.from_dict(response.data)

        return PerformanceAnalysis(
            agent_id=self.agent_id,
            total_transactions=0,
            successful_transactions=0,
            failed_transactions=0,
            total_revenue=0,
            average_rating=0,
            completion_rate=0,
            top_capabilities=[],
            improvement_areas=[],
            trends={},
        )

    # ==================== Insights ====================

    async def get_insights(self) -> list[LearningInsight]:
        """Get learning insights for this agent"""
        if self._insights_cache and self._is_cache_valid():
            return self._insights_cache

        response = await self._platform.get_learning_insights()

        if response.success and response.data:
            insights_data = response.data.get("insights", [])
            self._insights_cache = [LearningInsight.from_dict(i) for i in insights_data]
            self._cache_time = datetime.now()
            return self._insights_cache

        return []

    async def get_insights_by_category(self, category: str) -> list[LearningInsight]:
        """Get insights filtered by category"""
        insights = await self.get_insights()
        return [i for i in insights if i.category == category]

    async def get_success_patterns(self) -> list[SuccessPattern]:
        """Get patterns associated with successful outcomes"""
        response = await self._platform.analyze_learning()

        if response.success and response.data:
            patterns_data = response.data.get("success_patterns", [])
            return [SuccessPattern.from_dict(p) for p in patterns_data]

        return []

    # ==================== Strategy Optimization ====================

    async def get_optimized_strategy(self) -> MatchingStrategy:
        """Get optimized matching strategy"""
        if self._strategy_cache and self._is_cache_valid():
            return self._strategy_cache

        response = await self._platform.get_optimized_strategy()

        if response.success and response.data:
            self._strategy_cache = MatchingStrategy.from_dict(response.data)
            self._cache_time = datetime.now()
            return self._strategy_cache

        # Default strategy
        return MatchingStrategy(
            optimal_price_range={"min": 50, "max": 200},
            best_contact_timing=["anytime"],
            preferred_partner_types=["human", "ai_agent"],
            focus_capabilities=[],
            negotiation_approach="balanced",
            recommended_availability="24/7",
        )

    async def get_optimal_pricing(self, service_type: str) -> PriceRange:
        """Get optimal pricing for a service type"""
        strategy = await self.get_optimized_strategy()
        price_range = strategy.optimal_price_range

        return PriceRange(
            min=price_range.get("min", 50),
            max=price_range.get("max", 200),
            recommended=price_range.get("recommended", (price_range.get("min", 50) + price_range.get("max", 200)) / 2),
            confidence=0.7,
        )

    async def get_optimal_availability(self) -> str:
        """Get recommended availability schedule"""
        strategy = await self.get_optimized_strategy()
        return strategy.recommended_availability

    # ==================== Market Analysis ====================

    async def get_market_insights(self) -> MarketInsights:
        """Get market insights"""
        if self._market_cache and self._is_cache_valid():
            return self._market_cache

        response = await self._platform.get_market_insights()

        if response.success and response.data:
            self._market_cache = MarketInsights.from_dict(response.data)
            self._cache_time = datetime.now()
            return self._market_cache

        # Default market insights
        return MarketInsights(
            demand_level="medium",
            supply_level="medium",
            opportunity_areas=[],
            recommendations=["Register to see personalized recommendations"],
            hot_skills=[],
            trending_categories=[],
            average_prices={},
            competitor_count=0,
            supply_demand_ratio=1.0,
            market_trends=[],
        )

    async def get_competitive_analysis(self, capability: str) -> CompetitiveAnalysis:
        """Get competitive analysis for a capability"""
        # TODO: Implement when platform API supports this
        return CompetitiveAnalysis(
            capability=capability,
            my_ranking=1,
            total_competitors=1,
            market_share=100.0,
            competitive_advantages=[],
            improvement_suggestions=[],
            price_position="competitive",
        )

    async def get_demand_forecast(self, capability: str) -> DemandForecast:
        """Get demand forecast for a capability"""
        # TODO: Implement when platform API supports this
        return DemandForecast(
            capability=capability,
            current_demand=1.0,
            predicted_demand_7d=1.0,
            predicted_demand_30d=1.0,
            trend="stable",
            confidence=0.5,
            factors=[],
        )

    # ==================== Experience Reporting ====================

    async def report_experience(self, experience: Experience) -> bool:
        """
        Report an experience for learning.

        Args:
            experience: The experience to report

        Returns:
            True if reported successfully
        """
        # TODO: Implement when platform API supports this
        self.logger.info(f"Experience reported: {experience.experience_type} - {experience.outcome}")

        # Invalidate cache
        self._insights_cache = None
        self._strategy_cache = None

        return True

    async def report_transaction_result(
        self,
        tx_id: str,
        success: bool,
        rating: int | None = None,
        feedback: str | None = None,
    ) -> bool:
        """Report a transaction result"""
        experience = Experience(
            experience_type="transaction",
            outcome="success" if success else "failure",
            details={"transaction_id": tx_id},
            lessons_learned=[],
            rating=rating,
            feedback=feedback,
        )
        return await self.report_experience(experience)

    async def report_collaboration_result(
        self,
        session_id: str,
        success: bool,
        role: str,
        contribution: str,
    ) -> bool:
        """Report a collaboration result"""
        experience = Experience(
            experience_type="collaboration",
            outcome="success" if success else "failure",
            details={
                "session_id": session_id,
                "role": role,
                "contribution": contribution,
            },
            lessons_learned=[],
        )
        return await self.report_experience(experience)

    async def report_negotiation_result(
        self,
        session_id: str,
        success: bool,
        final_price: float | None = None,
        rounds: int = 0,
    ) -> bool:
        """Report a negotiation result"""
        experience = Experience(
            experience_type="negotiation",
            outcome="success" if success else "failure",
            details={
                "session_id": session_id,
                "final_price": final_price,
                "rounds": rounds,
            },
            lessons_learned=[],
        )
        return await self.report_experience(experience)

    # ==================== Summary ====================

    async def get_learning_summary(self) -> dict[str, Any]:
        """Get complete learning summary"""
        performance = await self.analyze_performance()
        insights = await self.get_insights()
        strategy = await self.get_optimized_strategy()
        market = await self.get_market_insights()

        return {
            "performance": {
                "total_transactions": performance.total_transactions,
                "success_rate": performance.success_rate,
                "average_rating": performance.average_rating,
                "total_revenue": performance.total_revenue,
            },
            "insights": {
                "count": len(insights),
                "by_category": {
                    cat: len([i for i in insights if i.category == cat])
                    for cat in {i.category for i in insights}
                },
            },
            "strategy": {
                "negotiation_approach": strategy.negotiation_approach,
                "optimal_price_range": strategy.optimal_price_range,
                "focus_capabilities": strategy.focus_capabilities,
            },
            "market": {
                "demand_level": market.demand_level,
                "hot_skills": market.hot_skills[:5],
                "opportunity_areas": market.opportunity_areas[:5],
            },
        }

    def invalidate_cache(self):
        """Invalidate all caches"""
        self._insights_cache = None
        self._strategy_cache = None
        self._market_cache = None
        self._cache_time = None
