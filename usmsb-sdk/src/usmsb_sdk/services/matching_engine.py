"""
Matching Engine Service

A standalone matching engine that can work without the full SDK dependencies.
Provides real matching algorithms for the REST API.
"""
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MatchScore:
    """Score for a supply-demand match."""
    overall: float
    capability_match: float
    price_match: float
    reputation_match: float
    time_match: float
    semantic_match: float = 0.0
    suggested_price_range: Dict[str, float] = field(default_factory=dict)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": round(self.overall, 3),
            "capability_match": round(self.capability_match, 3),
            "price_match": round(self.price_match, 3),
            "reputation_match": round(self.reputation_match, 3),
            "time_match": round(self.time_match, 3),
            "semantic_match": round(self.semantic_match, 3),
            "suggested_price_range": self.suggested_price_range,
            "reasoning": self.reasoning,
        }


@dataclass
class MatchResult:
    """Result of a matching operation."""
    match_id: str
    demand_id: str
    supply_id: str
    score: MatchScore
    status: str = "pending"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "demand_id": self.demand_id,
            "supply_id": self.supply_id,
            "score": self.score.to_dict(),
            "status": self.status,
            "created_at": self.created_at,
        }


class MatchingEngine:
    """
    Core matching engine for supply-demand matching.

    Implements multiple matching algorithms:
    1. Capability matching - skill/ability overlap
    2. Price matching - budget alignment
    3. Reputation matching - trust scoring
    4. Time matching - availability/deadline alignment
    5. Semantic matching - description similarity
    """

    # Weights for overall score calculation
    WEIGHTS = {
        "capability": 0.35,
        "price": 0.20,
        "reputation": 0.20,
        "time": 0.10,
        "semantic": 0.15,
    }

    def __init__(self, llm_adapter=None):
        """
        Initialize matching engine.

        Args:
            llm_adapter: Optional LLM adapter for semantic matching
        """
        self.llm = llm_adapter
        self._match_history: List[Dict[str, Any]] = []

    def calculate_capability_match(
        self,
        required_skills: List[str],
        offered_capabilities: List[str],
    ) -> float:
        """
        Calculate capability match score.

        Uses Jaccard similarity with bonus for exact matches.

        Args:
            required_skills: List of required skills
            offered_capabilities: List of offered capabilities

        Returns:
            Match score between 0 and 1
        """
        """
        Calculate capability match score.

        Uses Jaccard similarity with bonus for exact matches.
        """
        if not required_skills:
            return 1.0  # No requirements = perfect match

        if not offered_capabilities:
            return 0.0

        # Normalize to lowercase for comparison
        required = set(s.lower().strip() for s in required_skills)
        offered = set(c.lower().strip() for c in offered_capabilities)

        # Direct overlap
        intersection = required & offered
        union = required | offered

        if not union:
            return 1.0

        jaccard = len(intersection) / len(union)

        # Bonus for covering all requirements
        coverage = len(intersection) / len(required) if required else 1.0

        # Combine with weights
        score = jaccard * 0.5 + coverage * 0.5

        return min(score, 1.0)

    def calculate_price_match(
        self,
        budget_range: Dict[str, float],
        price: float,
        price_type: str = "hourly",
    ) -> float:
        """
        Calculate price match score.

        Higher score when price is within budget and closer to middle.

        Args:
            budget_range: Dict with 'min' and 'max' budget values
            price: Provider's price
            price_type: Type of pricing (hourly, fixed, etc.)

        Returns:
            Match score between 0 and 1
        """
        """
        Calculate price match score.

        Higher score when price is within budget and closer to middle.
        """
        budget_min = budget_range.get("min", 0)
        budget_max = budget_range.get("max", float("inf"))

        if price < budget_min:
            # Price too low (might indicate quality issues)
            return 0.7
        elif price > budget_max:
            # Over budget - score decreases with overage percentage
            if budget_max > 0:
                overage = (price - budget_max) / budget_max
                return max(0.0, 0.5 - overage * 0.5)
            return 0.3
        else:
            # Within budget - score based on position in range
            if budget_max > budget_min:
                position = (price - budget_min) / (budget_max - budget_min)
                # Prefer middle of range
                return 0.8 + 0.2 * (1 - abs(0.5 - position) * 2)
            return 1.0

    def calculate_reputation_match(
        self,
        reputation: float,
        min_threshold: float = 0.3,
    ) -> float:
        """
        Calculate reputation match score.

        Higher reputation = higher score, with threshold filter.

        Args:
            reputation: Provider's reputation score (0-1)
            min_threshold: Minimum reputation threshold

        Returns:
            Match score between 0 and 1
        """
        """
        Calculate reputation match score.

        Higher reputation = higher score, with threshold filter.
        """
        if reputation < min_threshold:
            return 0.0

        # Scale from threshold to 1.0
        score = (reputation - min_threshold) / (1.0 - min_threshold)
        return min(max(score, 0.0), 1.0)

    def calculate_time_match(
        self,
        deadline: Optional[str],
        availability: str,
        estimated_duration: Optional[str] = None,
    ) -> float:
        """
        Calculate time match score.

        Considers deadline alignment and availability.
        """
        # Parse availability
        if availability == "now" or availability == "immediate":
            availability_score = 1.0
        elif availability == "available":
            availability_score = 0.9
        elif availability == "busy":
            availability_score = 0.3
        elif availability == "unavailable":
            availability_score = 0.0
        else:
            availability_score = 0.5

        # Check deadline if provided
        deadline_score = 1.0
        if deadline:
            try:
                from datetime import datetime, timedelta
                # Try to parse deadline
                if deadline.endswith('Z'):
                    deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                else:
                    deadline_dt = datetime.fromisoformat(deadline)

                now = datetime.now(deadline_dt.tzinfo) if deadline_dt.tzinfo else datetime.now()
                time_until_deadline = (deadline_dt - now).total_seconds()

                if time_until_deadline < 0:
                    deadline_score = 0.0  # Already past deadline
                elif time_until_deadline < 86400:  # Less than 1 day
                    deadline_score = 0.5
                elif time_until_deadline < 604800:  # Less than 1 week
                    deadline_score = 0.8
                else:
                    deadline_score = 1.0
            except Exception as e:
                logger.debug(f"Could not parse deadline: {e}")
                deadline_score = 0.7

        return availability_score * 0.6 + deadline_score * 0.4

    async def calculate_semantic_match(
        self,
        demand_description: str,
        supply_description: str,
    ) -> float:
        """
        Calculate semantic similarity using LLM.

        Falls back to keyword matching if LLM not available.
        """
        if self.llm:
            try:
                prompt = f"""
Compare these two descriptions and rate their semantic similarity on a scale of 0 to 1.

Description 1 (Demand):
{demand_description}

Description 2 (Supply):
{supply_description}

Consider:
- Topic relevance
- Domain alignment
- Service/need match

Respond with only a number between 0 and 1.
"""
                response = await self.llm.generate_text(prompt, temperature=0.1)
                score = float(response.strip())
                return min(max(score, 0.0), 1.0)
            except Exception as e:
                logger.warning(f"LLM semantic matching failed: {e}")

        # Fallback: keyword matching
        words1 = set(demand_description.lower().split())
        words2 = set(supply_description.lower().split())

        # Remove common words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                      "have", "has", "had", "do", "does", "did", "will", "would", "could",
                      "should", "may", "might", "must", "shall", "can", "need", "to", "for",
                      "of", "in", "on", "at", "by", "with", "from", "as", "into", "through"}

        words1 -= stop_words
        words2 -= stop_words

        if not words1 or not words2:
            return 0.5

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.5

    def calculate_overall_score(
        self,
        capability_match: float,
        price_match: float,
        reputation_match: float,
        time_match: float,
        semantic_match: float = 0.5,
    ) -> float:
        """
        Calculate weighted overall score.
        """
        return (
            capability_match * self.WEIGHTS["capability"] +
            price_match * self.WEIGHTS["price"] +
            reputation_match * self.WEIGHTS["reputation"] +
            time_match * self.WEIGHTS["time"] +
            semantic_match * self.WEIGHTS["semantic"]
        )

    def suggest_price_range(
        self,
        budget_range: Dict[str, float],
        provider_price: float,
        market_data: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """
        Suggest a fair price range for negotiation.
        """
        budget_min = budget_range.get("min", provider_price * 0.5)
        budget_max = budget_range.get("max", provider_price * 1.5)

        # Start with provider's price as baseline
        if market_data:
            avg_price = market_data.get("average", provider_price)
            min_price = market_data.get("min", provider_price * 0.8)
            max_price = market_data.get("max", provider_price * 1.2)
        else:
            avg_price = provider_price
            min_price = provider_price * 0.8
            max_price = provider_price * 1.2

        # Find overlap with budget
        suggested_min = max(budget_min, min_price)
        suggested_max = min(budget_max, max_price)

        if suggested_min > suggested_max:
            # No overlap, suggest midpoint
            midpoint = (budget_max + provider_price) / 2
            return {
                "min": round(midpoint * 0.9, 2),
                "max": round(midpoint * 1.1, 2),
            }

        return {
            "min": round(suggested_min, 2),
            "max": round(suggested_max, 2),
        }

    def generate_reasoning(
        self,
        capability_match: float,
        price_match: float,
        reputation_match: float,
        time_match: float,
        demand: Dict[str, Any],
        supply: Dict[str, Any],
    ) -> str:
        """
        Generate human-readable reasoning for the match.
        """
        reasons = []

        # Capability reasoning
        if capability_match >= 0.8:
            reasons.append("Excellent skill match")
        elif capability_match >= 0.5:
            reasons.append("Partial skill overlap")
        else:
            reasons.append("Limited capability alignment")

        # Price reasoning
        if price_match >= 0.8:
            reasons.append("price within budget")
        elif price_match >= 0.5:
            reasons.append("price negotiable")
        else:
            reasons.append("price may need adjustment")

        # Reputation reasoning
        reputation = supply.get("reputation", 0.5)
        if reputation >= 0.8:
            reasons.append("highly trusted provider")
        elif reputation >= 0.5:
            reasons.append("reputable provider")
        else:
            reasons.append("new provider")

        # Time reasoning
        if time_match >= 0.8:
            reasons.append("good availability")
        elif time_match >= 0.5:
            reasons.append("limited availability")

        return "; ".join(reasons) + "."

    async def match_demand_to_supplies(
        self,
        demand: Dict[str, Any],
        supplies: List[Dict[str, Any]],
        min_score: float = 0.3,
        max_results: int = 10,
    ) -> List[MatchResult]:
        """
        Match a demand to multiple supplies.

        Args:
            demand: Demand details including required_skills, budget, deadline
            supplies: List of supply details
            min_score: Minimum score threshold
            max_results: Maximum number of results

        Returns:
            List of match results sorted by score
        """
        results = []

        required_skills = demand.get("required_skills", [])
        budget_range = demand.get("budget_range", demand.get("budget", {}))
        deadline = demand.get("deadline")
        demand_description = demand.get("description", demand.get("title", ""))

        for supply in supplies:
            # Get supply details
            capabilities = supply.get("capabilities", supply.get("skills", []))
            price = supply.get("price", supply.get("price_per_request", 0))
            reputation = supply.get("reputation", 0.5)
            availability = supply.get("availability", "available")
            supply_description = supply.get("description", supply.get("service_name", ""))

            # Calculate individual scores
            capability_score = self.calculate_capability_match(required_skills, capabilities)
            price_score = self.calculate_price_match(budget_range, price)
            reputation_score = self.calculate_reputation_match(reputation)
            time_score = self.calculate_time_match(deadline, availability)
            semantic_score = await self.calculate_semantic_match(demand_description, supply_description)

            # Calculate overall score
            overall_score = self.calculate_overall_score(
                capability_score, price_score, reputation_score, time_score, semantic_score
            )

            # Skip if below threshold
            if overall_score < min_score:
                continue

            # Generate reasoning
            reasoning = self.generate_reasoning(
                capability_score, price_score, reputation_score, time_score,
                demand, supply
            )

            # Suggest price range
            suggested_price = self.suggest_price_range(budget_range, price)

            match_score = MatchScore(
                overall=overall_score,
                capability_match=capability_score,
                price_match=price_score,
                reputation_match=reputation_score,
                time_match=time_score,
                semantic_match=semantic_score,
                suggested_price_range=suggested_price,
                reasoning=reasoning,
            )

            match_result = MatchResult(
                match_id=str(uuid.uuid4()),
                demand_id=demand.get("id", ""),
                supply_id=supply.get("id", supply.get("agent_id", "")),
                score=match_score,
            )

            results.append(match_result)

        # Sort by overall score
        results.sort(key=lambda x: x.score.overall, reverse=True)

        return results[:max_results]

    async def match_supply_to_demands(
        self,
        supply: Dict[str, Any],
        demands: List[Dict[str, Any]],
        min_score: float = 0.3,
        max_results: int = 10,
    ) -> List[MatchResult]:
        """
        Match a supply to multiple demands.

        Args:
            supply: Supply details including capabilities, price, availability
            demands: List of demand details
            min_score: Minimum score threshold
            max_results: Maximum number of results

        Returns:
            List of match results sorted by score
        """
        results = []

        capabilities = supply.get("capabilities", supply.get("skills", []))
        price = supply.get("price", supply.get("price_per_request", 0))
        reputation = supply.get("reputation", 0.5)
        availability = supply.get("availability", "available")
        supply_description = supply.get("description", supply.get("service_name", ""))

        for demand in demands:
            # Get demand details
            required_skills = demand.get("required_skills", [])
            budget_range = demand.get("budget_range", demand.get("budget", {}))
            deadline = demand.get("deadline")
            demand_description = demand.get("description", demand.get("title", ""))

            # Calculate individual scores
            capability_score = self.calculate_capability_match(required_skills, capabilities)
            price_score = self.calculate_price_match(budget_range, price)
            reputation_score = self.calculate_reputation_match(reputation)
            time_score = self.calculate_time_match(deadline, availability)
            semantic_score = await self.calculate_semantic_match(demand_description, supply_description)

            # Calculate overall score
            overall_score = self.calculate_overall_score(
                capability_score, price_score, reputation_score, time_score, semantic_score
            )

            # Skip if below threshold
            if overall_score < min_score:
                continue

            # Generate reasoning
            reasoning = self.generate_reasoning(
                capability_score, price_score, reputation_score, time_score,
                demand, supply
            )

            # Suggest price range
            suggested_price = self.suggest_price_range(budget_range, price)

            match_score = MatchScore(
                overall=overall_score,
                capability_match=capability_score,
                price_match=price_score,
                reputation_match=reputation_score,
                time_match=time_score,
                semantic_match=semantic_score,
                suggested_price_range=suggested_price,
                reasoning=reasoning,
            )

            match_result = MatchResult(
                match_id=str(uuid.uuid4()),
                demand_id=demand.get("id", ""),
                supply_id=supply.get("id", supply.get("agent_id", "")),
                score=match_score,
            )

            results.append(match_result)

        # Sort by overall score
        results.sort(key=lambda x: x.score.overall, reverse=True)

        return results[:max_results]
