"""
Learning Service for AI Civilization Platform

Enables agents to learn from:
- Transaction outcomes
- Feedback and ratings
- Market trends
- Peer behavior
"""
import logging
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class InsightType(StrEnum):
    """Types of learning insights."""
    PRICING = "pricing"               # Pricing strategy
    SKILL_GAP = "skill_gap"           # Missing skills
    MARKET_TREND = "market_trend"     # Market movements
    COMPETITOR = "competitor"         # Competitor analysis
    PERFORMANCE = "performance"        # Own performance
    OPPORTUNITY = "opportunity"        # New opportunities
    RISK = "risk"                      # Risk warnings
    RECOMMENDATION = "recommendation"   # Action recommendations


class InsightPriority(StrEnum):
    """Priority levels for insights."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class LearningInsight:
    """A learning insight for an agent."""
    insight_id: str
    agent_id: str
    insight_type: InsightType
    priority: InsightPriority
    title: str
    description: str
    data: dict[str, Any]
    confidence: float  # 0-1
    actionable: bool
    suggested_actions: list[str]
    created_at: float
    expires_at: float | None = None
    applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "insightId": self.insight_id,
            "agentId": self.agent_id,
            "insightType": self.insight_type.value,
            "priority": self.priority.value,
            "title": self.title,
            "description": self.description,
            "data": self.data,
            "confidence": round(self.confidence, 3),
            "actionable": self.actionable,
            "suggestedActions": self.suggested_actions,
            "createdAt": self.created_at,
            "expiresAt": self.expires_at,
            "applied": self.applied,
        }


@dataclass
class TransactionAnalysis:
    """Analysis of a completed transaction."""
    transaction_id: str
    agent_id: str
    role: str  # "buyer" or "seller"

    # Outcome
    success: bool
    rating: int | None
    amount: float
    duration: float  # seconds

    # Pricing analysis
    asked_price: float
    final_price: float
    price_negotiation_ratio: float  # final/asked

    # Timing analysis
    response_time: float  # seconds to first response
    delivery_time: float  # seconds to deliver

    # Match analysis
    match_score: float
    capability_match: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "transactionId": self.transaction_id,
            "agentId": self.agent_id,
            "role": self.role,
            "success": self.success,
            "rating": self.rating,
            "amount": self.amount,
            "duration": self.duration,
            "askedPrice": self.asked_price,
            "finalPrice": self.final_price,
            "priceNegotiationRatio": round(self.price_negotiation_ratio, 3),
            "responseTime": self.response_time,
            "deliveryTime": self.delivery_time,
            "matchScore": self.match_score,
            "capabilityMatch": self.capability_match,
        }


@dataclass
class StrategyRecommendation:
    """A strategy recommendation for an agent."""
    category: str
    current_value: Any
    recommended_value: Any
    reason: str
    expected_improvement: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "currentValue": self.current_value,
            "recommendedValue": self.recommended_value,
            "reason": self.reason,
            "expectedImprovement": self.expected_improvement,
            "confidence": round(self.confidence, 3),
        }


class LearningService:
    """
    Learning Service for agent improvement.

    Analyzes transaction history and generates insights.
    """

    # Configuration
    MIN_TRANSACTIONS_FOR_ANALYSIS = 5
    INSIGHT_EXPIRY_DAYS = 30
    CONFIDENCE_THRESHOLD = 0.6

    def __init__(self, db_connection=None, llm_adapter=None):
        """
        Initialize learning service.

        Args:
            db_connection: Database for data access
            llm_adapter: LLM for advanced analysis
        """
        self.db = db_connection
        self.llm = llm_adapter

        # Storage
        self._insights: dict[str, list[LearningInsight]] = {}
        self._transaction_history: dict[str, list[TransactionAnalysis]] = {}

        # Callbacks
        self.on_insight_created: Callable[[LearningInsight], None] | None = None

    # ==================== Transaction Learning ====================

    async def learn_from_transaction(
        self,
        transaction_data: dict[str, Any],
        agent_id: str,
        role: str,
    ) -> list[LearningInsight]:
        """
        Learn from a completed transaction.

        Args:
            transaction_data: Transaction details
            agent_id: The learning agent
            role: "buyer" or "seller"

        Returns:
            Generated insights
        """
        # Create analysis
        analysis = self._create_transaction_analysis(transaction_data, agent_id, role)

        # Store in history
        if agent_id not in self._transaction_history:
            self._transaction_history[agent_id] = []
        self._transaction_history[agent_id].append(analysis)

        # Generate insights
        insights = []

        # Pricing insights
        pricing_insight = await self._analyze_pricing(agent_id, analysis)
        if pricing_insight:
            insights.append(pricing_insight)

        # Performance insights
        perf_insight = await self._analyze_performance(agent_id, analysis)
        if perf_insight:
            insights.append(perf_insight)

        # Store insights
        for insight in insights:
            if agent_id not in self._insights:
                self._insights[agent_id] = []
            self._insights[agent_id].append(insight)

            if self.on_insight_created:
                self.on_insight_created(insight)

        return insights

    def _create_transaction_analysis(
        self,
        data: dict[str, Any],
        agent_id: str,
        role: str,
    ) -> TransactionAnalysis:
        """Create analysis object from transaction data."""
        return TransactionAnalysis(
            transaction_id=data.get("id", ""),
            agent_id=agent_id,
            role=role,
            success=data.get("status") == "completed",
            rating=data.get("rating"),
            amount=data.get("amount", 0),
            duration=data.get("completed_at", time.time()) - data.get("created_at", time.time()),
            asked_price=data.get("original_price", data.get("amount", 0)),
            final_price=data.get("amount", 0),
            price_negotiation_ratio=(
                data.get("amount", 0) / max(data.get("original_price", 1), 1)
            ),
            response_time=data.get("response_time", 0),
            delivery_time=data.get("delivery_time", 0),
            match_score=data.get("match_score", 0.5),
            capability_match=data.get("capability_match", 0.5),
        )

    async def _analyze_pricing(
        self,
        agent_id: str,
        analysis: TransactionAnalysis,
    ) -> LearningInsight | None:
        """Analyze pricing strategy."""
        history = self._transaction_history.get(agent_id, [])
        if len(history) < self.MIN_TRANSACTIONS_FOR_ANALYSIS:
            return None

        # Calculate average price negotiation ratio
        ratios = [t.price_negotiation_ratio for t in history if t.role == analysis.role]
        if not ratios:
            return None

        avg_ratio = statistics.mean(ratios)

        # Check if consistently negotiating down
        if avg_ratio < 0.8 and analysis.role == "seller":
            return LearningInsight(
                insight_id=f"ins-{time.time()}-{agent_id}",
                agent_id=agent_id,
                insight_type=InsightType.PRICING,
                priority=InsightPriority.HIGH,
                title="Pricing Strategy Needs Adjustment",
                description=f"Your average final price is {round((1-avg_ratio)*100)}% lower than your asking price. Consider adjusting your initial pricing.",
                data={
                    "averageNegotiationRatio": avg_ratio,
                    "recentRatios": ratios[-5:],
                },
                confidence=min(len(ratios) / 20, 0.9),
                actionable=True,
                suggested_actions=[
                    "Research market prices for similar services",
                    "Consider starting with a slightly higher asking price",
                    "Practice negotiation techniques",
                ],
                created_at=time.time(),
                expires_at=time.time() + self.INSIGHT_EXPIRY_DAYS * 86400,
            )

        # Check if prices are too high
        if avg_ratio > 1.0:
            return LearningInsight(
                insight_id=f"ins-{time.time()}-{agent_id}",
                agent_id=agent_id,
                insight_type=InsightType.PRICING,
                priority=InsightPriority.MEDIUM,
                title="Underpricing Detected",
                description="Your final prices are often higher than asking price, suggesting you may be underpricing initially.",
                data={
                    "averageNegotiationRatio": avg_ratio,
                },
                confidence=min(len(ratios) / 15, 0.85),
                actionable=True,
                suggested_actions=[
                    "Consider raising your base prices",
                    "Highlight unique value propositions",
                ],
                created_at=time.time(),
                expires_at=time.time() + self.INSIGHT_EXPIRY_DAYS * 86400,
            )

        return None

    async def _analyze_performance(
        self,
        agent_id: str,
        analysis: TransactionAnalysis,
    ) -> LearningInsight | None:
        """Analyze performance patterns."""
        history = self._transaction_history.get(agent_id, [])
        if len(history) < self.MIN_TRANSACTIONS_FOR_ANALYSIS:
            return None


        # Analyze ratings
        ratings = [t.rating for t in history if t.rating is not None]
        if ratings:
            avg_rating = statistics.mean(ratings)
            if avg_rating < 4.0:
                return LearningInsight(
                    insight_id=f"ins-{time.time()}-{agent_id}",
                    agent_id=agent_id,
                    insight_type=InsightType.PERFORMANCE,
                    priority=InsightPriority.HIGH,
                    title="Customer Satisfaction Needs Improvement",
                    description=f"Your average rating is {round(avg_rating, 1)}/5. Focus on quality improvement.",
                    data={
                        "averageRating": avg_rating,
                        "totalRatings": len(ratings),
                    },
                    confidence=min(len(ratings) / 10, 0.9),
                    actionable=True,
                    suggested_actions=[
                        "Review recent negative feedback",
                        "Improve communication with clients",
                        "Set clearer expectations upfront",
                        "Request detailed feedback from clients",
                    ],
                    created_at=time.time(),
                    expires_at=time.time() + self.INSIGHT_EXPIRY_DAYS * 86400,
                )

        # Analyze response times
        response_times = [t.response_time for t in history if t.response_time > 0]
        if response_times and statistics.mean(response_times) > 3600:  # > 1 hour
            return LearningInsight(
                insight_id=f"ins-{time.time()}-{agent_id}",
                agent_id=agent_id,
                insight_type=InsightType.PERFORMANCE,
                priority=InsightPriority.MEDIUM,
                title="Response Time Could Be Improved",
                description=f"Your average response time is {round(statistics.mean(response_times)/60)} minutes. Faster responses lead to better outcomes.",
                data={
                    "averageResponseTime": statistics.mean(response_times),
                },
                confidence=0.75,
                actionable=True,
                suggested_actions=[
                    "Enable mobile notifications",
                    "Set up auto-responses",
                    "Schedule regular check-ins",
                ],
                created_at=time.time(),
                expires_at=time.time() + self.INSIGHT_EXPIRY_DAYS * 86400,
            )

        return None

    # ==================== Market Learning ====================

    async def analyze_market_trends(
        self,
        agent_id: str,
        skills: list[str],
    ) -> list[LearningInsight]:
        """
        Analyze market trends relevant to an agent.

        Args:
            agent_id: Agent to analyze for
            skills: Agent's skills

        Returns:
            Market trend insights
        """
        insights = []

        # This would analyze actual market data
        # For now, return sample insights

        # Check for trending skills the agent doesn't have
        trending_skills = ["AI Development", "Web3", "Machine Learning"]
        missing_trending = [s for s in trending_skills if s not in skills]

        if missing_trending:
            insight = LearningInsight(
                insight_id=f"ins-market-{time.time()}-{agent_id}",
                agent_id=agent_id,
                insight_type=InsightType.MARKET_TREND,
                priority=InsightPriority.MEDIUM,
                title="Emerging Skill Opportunities",
                description=f"High demand skills you could learn: {', '.join(missing_trending)}",
                data={
                    "trendingSkills": trending_skills,
                    "missingSkills": missing_trending,
                },
                confidence=0.7,
                actionable=True,
                suggested_actions=[
                    f"Consider learning {skill}" for skill in missing_trending[:3]
                ],
                created_at=time.time(),
                expires_at=time.time() + 7 * 86400,  # 7 days
            )
            insights.append(insight)

        return insights

    # ==================== Strategy Recommendations ====================

    async def get_strategy_recommendations(
        self,
        agent_id: str,
    ) -> list[StrategyRecommendation]:
        """
        Get strategy recommendations for an agent.

        Args:
            agent_id: Agent to recommend for

        Returns:
            List of recommendations
        """
        history = self._transaction_history.get(agent_id, [])
        recommendations = []

        if len(history) >= self.MIN_TRANSACTIONS_FOR_ANALYSIS:
            # Pricing recommendation
            ratios = [t.price_negotiation_ratio for t in history]
            avg_ratio = statistics.mean(ratios) if ratios else 1.0

            if avg_ratio < 0.85:
                recommendations.append(StrategyRecommendation(
                    category="pricing",
                    current_value=f"{round((1-avg_ratio)*100)}% discount on average",
                    recommended_value="Reduce discount to <10%",
                    reason="Your prices are being negotiated down significantly",
                    expected_improvement="10-20% increase in revenue",
                    confidence=0.75,
                ))

            # Response time recommendation
            response_times = [t.response_time for t in history if t.response_time > 0]
            if response_times:
                avg_response = statistics.mean(response_times)
                if avg_response > 1800:  # > 30 minutes
                    recommendations.append(StrategyRecommendation(
                        category="responsiveness",
                        current_value=f"{round(avg_response/60)} min average response",
                        recommended_value="< 15 minutes",
                        reason="Faster response times improve conversion rates",
                        expected_improvement="15-25% higher match acceptance",
                        confidence=0.7,
                    ))

        return recommendations

    # ==================== Insight Management ====================

    def get_insights(
        self,
        agent_id: str,
        insight_type: InsightType = None,
        include_expired: bool = False,
    ) -> list[LearningInsight]:
        """Get insights for an agent."""
        insights = self._insights.get(agent_id, [])
        now = time.time()

        filtered = []
        for insight in insights:
            # Filter by type
            if insight_type and insight.insight_type != insight_type:
                continue

            # Filter expired
            if not include_expired and insight.expires_at and insight.expires_at < now:
                continue

            filtered.append(insight)

        # Sort by priority and creation time
        priority_order = {
            InsightPriority.CRITICAL: 0,
            InsightPriority.HIGH: 1,
            InsightPriority.MEDIUM: 2,
            InsightPriority.LOW: 3,
        }
        filtered.sort(key=lambda i: (priority_order[i.priority], -i.created_at))

        return filtered

    def mark_insight_applied(self, insight_id: str, agent_id: str) -> bool:
        """Mark an insight as applied."""
        insights = self._insights.get(agent_id, [])
        for insight in insights:
            if insight.insight_id == insight_id:
                insight.applied = True
                return True
        return False

    def dismiss_insight(self, insight_id: str, agent_id: str) -> bool:
        """Dismiss an insight."""
        insights = self._insights.get(agent_id, [])
        for i, insight in enumerate(insights):
            if insight.insight_id == insight_id:
                insights.pop(i)
                return True
        return False

    # ==================== Statistics ====================

    def get_learning_stats(self, agent_id: str) -> dict[str, Any]:
        """Get learning statistics for an agent."""
        history = self._transaction_history.get(agent_id, [])
        insights = self._insights.get(agent_id, [])

        # Calculate stats
        successful = sum(1 for t in history if t.success)
        ratings = [t.rating for t in history if t.rating]

        return {
            "totalTransactions": len(history),
            "successfulTransactions": successful,
            "successRate": successful / max(len(history), 1),
            "averageRating": statistics.mean(ratings) if ratings else None,
            "totalInsights": len(insights),
            "appliedInsights": sum(1 for i in insights if i.applied),
            "pendingInsights": sum(1 for i in insights if not i.applied and (not i.expires_at or i.expires_at > time.time())),
        }


# Global instance
_learning_service: LearningService | None = None


def get_learning_service() -> LearningService:
    """Get or create learning service instance."""
    global _learning_service
    if _learning_service is None:
        _learning_service = LearningService()
    return _learning_service
