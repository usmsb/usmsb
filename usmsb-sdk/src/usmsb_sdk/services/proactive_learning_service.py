"""
Proactive Learning Service

This module implements proactive learning capabilities for AI Agents:
- Learn from match history
- Optimize matching strategies
- Analyze market trends
- Improve negotiation approaches

Key Features:
1. Historical Analysis: Analyze past matches for patterns
2. Strategy Optimization: Adjust matching parameters based on learning
3. Market Analysis: Understand market trends and opportunities
4. Pattern Recognition: Identify successful patterns
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from usmsb_sdk.core.elements import Agent
from usmsb_sdk.intelligence_adapters.base import ILLMAdapter

logger = logging.getLogger(__name__)


class LearningType(str, Enum):
    """Type of learning."""
    MATCH_PATTERN = "match_pattern"
    NEGOTIATION_STRATEGY = "negotiation_strategy"
    PRICING = "pricing"
    TIMING = "timing"
    PARTNER_PREFERENCE = "partner_preference"


class InsightCategory(str, Enum):
    """Category of learning insight."""
    SUCCESS_PATTERNS = "success_patterns"
    FAILURE_REASONS = "failure_reasons"
    OPTIMAL_STRATEGY = "optimal_strategy"
    MARKET_TRENDS = "market_trends"
    RECOMMENDATIONS = "recommendations"


@dataclass
class LearningInsight:
    """A learning insight from analysis."""
    insight_id: str
    category: InsightCategory
    title: str
    description: str
    confidence: float  # 0-1
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "recommendations": self.recommendations,
            "created_at": self.created_at,
        }


@dataclass
class OptimizedStrategy:
    """An optimized matching strategy."""
    strategy_id: str
    preferred_partner_types: List[str] = field(default_factory=list)
    optimal_price_range: Dict[str, float] = field(default_factory=dict)  # min, max
    recommended_negotiation_strategy: str = "balanced"
    best_contact_timing: str = "anytime"
    capability_highlighting: List[str] = field(default_factory=list)
    target_capabilities: List[str] = field(default_factory=list)
    min_reputation_threshold: float = 0.5
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "preferred_partner_types": self.preferred_partner_types,
            "optimal_price_range": self.optimal_price_range,
            "recommended_negotiation_strategy": self.recommended_negotiation_strategy,
            "best_contact_timing": self.best_contact_timing,
            "capability_highlighting": self.capability_highlighting,
            "target_capabilities": self.target_capabilities,
            "min_reputation_threshold": self.min_reputation_threshold,
            "created_at": self.created_at,
        }


@dataclass
class MarketInsight:
    """Market analysis insight."""
    insight_id: str
    demand_level: str  # high, medium, low
    supply_level: str
    price_trends: Dict[str, Any] = field(default_factory=dict)
    opportunity_areas: List[str] = field(default_factory=list)
    competitive_analysis: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "demand_level": self.demand_level,
            "supply_level": self.supply_level,
            "price_trends": self.price_trends,
            "opportunity_areas": self.opportunity_areas,
            "competitive_analysis": self.competitive_analysis,
            "recommendations": self.recommendations,
            "created_at": self.created_at,
        }


class ProactiveLearningService:
    """
    Proactive Learning Service

    Enables agents to learn from their experiences and optimize
    their matching and negotiation strategies.
    """

    def __init__(
        self,
        llm_adapter: ILLMAdapter,
        history_store: Optional[Any] = None,  # Optional persistence
    ):
        """
        Initialize the Proactive Learning Service.

        Args:
            llm_adapter: For intelligent analysis
            history_store: Optional storage for learning history
        """
        self.llm = llm_adapter
        self.history_store = history_store

        # Learning cache per agent
        self._agent_insights: Dict[str, List[LearningInsight]] = {}
        self._agent_strategies: Dict[str, OptimizedStrategy] = {}
        self._market_insights: Dict[str, MarketInsight] = {}

        # Callbacks
        self.on_insight_generated: Optional[Callable[[str, LearningInsight], None]] = None

    async def learn_from_match_history(
        self,
        agent: Agent,
    ) -> List[LearningInsight]:
        """
        Learn from agent's match history.

        Analyzes past matches to identify:
        - Success patterns
        - Failure reasons
        - Optimal strategies

        Args:
            agent: The agent to learn for

        Returns:
            List of learning insights
        """
        history = agent.get_match_history()

        if not history:
            return []

        # Prepare history for analysis
        history_summary = self._prepare_history_summary(history)

        # Use LLM to analyze patterns
        analysis_prompt = f"""
        分析以下Agent的匹配历史，找出成功模式：

        Agent: {agent.name}
        能力: {agent.capabilities}

        匹配历史:
        {json.dumps(history_summary, indent=2, ensure_ascii=False)}

        请分析并返回JSON格式：
        {{
            "insights": [
                {{
                    "category": "success_patterns/failure_reasons/optimal_strategy",
                    "title": "标题",
                    "description": "详细描述",
                    "confidence": 0.0-1.0,
                    "evidence": [{{"match_id": "xxx", "details": "yyy"}}],
                    "recommendations": ["建议1", "建议2"]
                }}
            ]
        }}
        """

        try:
            response = await self.llm.generate_text(analysis_prompt)
            result = json.loads(response)

            insights = []
            for insight_data in result.get("insights", []):
                insight = LearningInsight(
                    insight_id=str(time.time()) + "_" + str(len(insights)),
                    category=InsightCategory(insight_data.get("category", "success_patterns")),
                    title=insight_data.get("title", ""),
                    description=insight_data.get("description", ""),
                    confidence=insight_data.get("confidence", 0.5),
                    evidence=insight_data.get("evidence", []),
                    recommendations=insight_data.get("recommendations", []),
                )
                insights.append(insight)

            # Store insights
            if agent.id not in self._agent_insights:
                self._agent_insights[agent.id] = []
            self._agent_insights[agent.id].extend(insights)

            # Trigger callback
            if self.on_insight_generated:
                for insight in insights:
                    self.on_insight_generated(agent.id, insight)

            return insights

        except Exception as e:
            logger.error(f"Learning analysis error: {e}")
            return []

    def _prepare_history_summary(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare match history for analysis."""
        summary = []
        for match in history[-50:]:  # Analyze last 50 matches
            summary.append({
                "match_id": match.get("id", ""),
                "success": match.get("success", False),
                "counterpart_type": match.get("counterpart_type", ""),
                "price": match.get("price", 0),
                "time_to_match": match.get("time_to_match", 0),
                "negotiation_rounds": match.get("negotiation_rounds", 0),
                "capabilities_matched": match.get("capabilities_matched", []),
            })
        return summary

    async def optimize_match_strategy(
        self,
        agent: Agent,
    ) -> OptimizedStrategy:
        """
        Optimize matching strategy based on learning.

        Args:
            agent: The agent to optimize for

        Returns:
            Optimized strategy
        """
        # Get insights
        insights = await self.learn_from_match_history(agent)

        # Get negotiation history
        negotiation_history = agent.metadata.get("negotiation_history", [])

        # Use LLM to create optimized strategy
        strategy_prompt = f"""
        基于以下分析结果，为Agent生成优化的匹配策略：

        Agent能力: {agent.capabilities}

        学习洞察:
        {json.dumps([i.to_dict() for i in insights], indent=2, ensure_ascii=False)}

        协商历史:
        {json.dumps(negotiation_history[-20:], indent=2, ensure_ascii=False)}

        请返回JSON格式的优化策略：
        {{
            "preferred_partner_types": ["human", "ai_agent"],
            "optimal_price_range": {{"min": 0, "max": 100}},
            "recommended_negotiation_strategy": "aggressive/balanced/conservative",
            "best_contact_timing": "morning/afternoon/evening/anytime",
            "capability_highlighting": ["skill1", "skill2"],
            "target_capabilities": ["needed_skill1"],
            "min_reputation_threshold": 0.5
        }}
        """

        try:
            response = await self.llm.generate_text(strategy_prompt)
            result = json.loads(response)

            strategy = OptimizedStrategy(
                strategy_id=str(time.time()),
                preferred_partner_types=result.get("preferred_partner_types", []),
                optimal_price_range=result.get("optimal_price_range", {}),
                recommended_negotiation_strategy=result.get("recommended_negotiation_strategy", "balanced"),
                best_contact_timing=result.get("best_contact_timing", "anytime"),
                capability_highlighting=result.get("capability_highlighting", []),
                target_capabilities=result.get("target_capabilities", []),
                min_reputation_threshold=result.get("min_reputation_threshold", 0.5),
            )

            # Store strategy
            self._agent_strategies[agent.id] = strategy

            return strategy

        except Exception as e:
            logger.error(f"Strategy optimization error: {e}")
            # Return default strategy
            return OptimizedStrategy(strategy_id=str(time.time()))

    async def analyze_negotiation_patterns(
        self,
        agent: Agent,
    ) -> Dict[str, Any]:
        """
        Analyze negotiation patterns from history.

        Args:
            agent: The agent to analyze

        Returns:
            Analysis results
        """
        negotiation_history = agent.metadata.get("negotiation_history", [])

        if not negotiation_history:
            return {
                "patterns": [],
                "success_rate": 0.5,
                "average_rounds": 0,
                "recommendations": ["Start negotiating to build history"],
            }

        # Calculate basic statistics
        total = len(negotiation_history)
        successful = sum(1 for n in negotiation_history if n.get("success", False))
        avg_rounds = sum(n.get("rounds", 0) for n in negotiation_history) / total

        # Analyze patterns
        initial_responses = [n.get("initial_response") for n in negotiation_history]
        final_prices = [n.get("final_price", 0) for n in negotiation_history if n.get("final_price")]

        return {
            "total_negotiations": total,
            "successful_negotiations": successful,
            "success_rate": successful / total,
            "average_rounds": avg_rounds,
            "price_range": {
                "min": min(final_prices) if final_prices else 0,
                "max": max(final_prices) if final_prices else 0,
            },
            "patterns": {
                "aggressive_count": sum(1 for r in initial_responses if r == "aggressive"),
                "conservative_count": sum(1 for r in initial_responses if r == "conservative"),
                "balanced_count": sum(1 for r in initial_responses if r == "balanced"),
            },
            "recommendations": self._generate_negotiation_recommendations(
                successful / total, avg_rounds
            ),
        }

    def _generate_negotiation_recommendations(
        self,
        success_rate: float,
        avg_rounds: float,
    ) -> List[str]:
        """Generate recommendations based on negotiation analysis."""
        recommendations = []

        if success_rate < 0.3:
            recommendations.append("Consider being more flexible in negotiations")
            recommendations.append("Review opponent's profiles before negotiating")
        elif success_rate > 0.7:
            recommendations.append("Your negotiation strategy is working well")
            recommendations.append("Consider mentoring other agents")

        if avg_rounds > 5:
            recommendations.append("Try to reach agreement faster")
        elif avg_rounds < 2:
            recommendations.append("Don't rush - take time to evaluate offers")

        return recommendations

    async def proactive_market_analysis(
        self,
        agent: Agent,
    ) -> MarketInsight:
        """
        Perform proactive market analysis.

        Analyzes market trends and opportunities to help
        agent make better matching decisions.

        Args:
            agent: The agent to analyze for

        Returns:
            Market insights
        """
        # Gather market data
        market_data = await self._collect_market_data(agent.capabilities)

        # Use LLM to analyze
        analysis_prompt = f"""
        分析以下市场数据，为Agent提供策略建议：

        Agent能力: {agent.capabilities}

        市场数据:
        {json.dumps(market_data, indent=2, ensure_ascii=False)}

        请返回JSON格式的市场分析：
        {{
            "demand_level": "high/medium/low",
            "supply_level": "high/medium/low",
            "price_trends": {{"trend": "increasing/decreasing/stable", "change_percent": 0}},
            "opportunity_areas": ["area1", "area2"],
            "competitive_analysis": {{"main_competitors": [], "your_advantage": ""}},
            "recommendations": ["建议1", "建议2"]
        }}
        """

        try:
            response = await self.llm.generate_text(analysis_prompt)
            result = json.loads(response)

            insight = MarketInsight(
                insight_id=str(time.time()),
                demand_level=result.get("demand_level", "medium"),
                supply_level=result.get("supply_level", "medium"),
                price_trends=result.get("price_trends", {}),
                opportunity_areas=result.get("opportunity_areas", []),
                competitive_analysis=result.get("competitive_analysis", {}),
                recommendations=result.get("recommendations", []),
            )

            # Cache insight
            self._market_insights[agent.id] = insight

            return insight

        except Exception as e:
            logger.error(f"Market analysis error: {e}")
            return MarketInsight(
                insight_id=str(time.time()),
                demand_level="medium",
                supply_level="medium",
            )

    async def _collect_market_data(
        self,
        capabilities: List[str],
    ) -> Dict[str, Any]:
        """Collect market data for analysis."""
        # This would normally query the registry and match history
        # For now, return placeholder data
        return {
            "agent_capabilities": capabilities,
            "market_timestamp": time.time(),
            "sample_size": 0,
            "average_prices": {},
            "demand_signals": [],
        }

    def get_insights(
        self,
        agent_id: str,
        category: Optional[InsightCategory] = None,
    ) -> List[LearningInsight]:
        """Get stored insights for an agent."""
        insights = self._agent_insights.get(agent_id, [])

        if category:
            insights = [i for i in insights if i.category == category]

        return insights

    def get_strategy(
        self,
        agent_id: str,
    ) -> Optional[OptimizedStrategy]:
        """Get optimized strategy for an agent."""
        return self._agent_strategies.get(agent_id)

    def get_market_insight(
        self,
        agent_id: str,
    ) -> Optional[MarketInsight]:
        """Get market insight for an agent."""
        return self._market_insights.get(agent_id)

    def apply_strategy_to_agent(
        self,
        agent: Agent,
        strategy: OptimizedStrategy,
    ) -> None:
        """Apply an optimized strategy to an agent."""
        agent.metadata["optimized_strategy"] = strategy.to_dict()
        agent.metadata["preferred_partners"] = strategy.preferred_partner_types
        agent.metadata["price_range"] = strategy.optimal_price_range
        agent.metadata["negotiation_strategy"] = strategy.recommended_negotiation_strategy

    async def continuous_learning(
        self,
        agent: Agent,
    ) -> Dict[str, Any]:
        """
        Perform continuous learning cycle.

        Runs a complete learning cycle including:
        - Match history analysis
        - Strategy optimization
        - Market analysis

        Args:
            agent: The agent to learn for

        Returns:
            Learning results
        """
        results = {
            "agent_id": agent.id,
            "timestamp": time.time(),
        }

        # Learn from match history
        insights = await self.learn_from_match_history(agent)
        results["insights_count"] = len(insights)

        # Optimize strategy
        strategy = await self.optimize_match_strategy(agent)
        self.apply_strategy_to_agent(agent, strategy)
        results["strategy_optimized"] = True

        # Market analysis
        market_insight = await self.proactive_market_analysis(agent)
        results["market_analyzed"] = True

        return results
