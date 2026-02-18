"""
Reputation Service for AI Civilization Platform

Implements a comprehensive reputation system:
- Multi-dimensional scoring
- Decay over time
- Weights based on stake
- Transaction-based updates
- Periodic recalculation
"""
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ReputationDimension(str, Enum):
    """Dimensions of reputation."""
    RELIABILITY = "reliability"      # Completes transactions
    QUALITY = "quality"              # Quality of work
    RESPONSIVENESS = "responsiveness" # Response time
    FAIRNESS = "fairness"            # Fair in negotiations
    CONTRIBUTION = "contribution"    # Platform contribution


@dataclass
class ReputationScore:
    """Multi-dimensional reputation score."""
    overall: float
    dimensions: Dict[str, float]
    confidence: float  # Based on number of data points
    last_updated: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall": round(self.overall, 4),
            "dimensions": {k: round(v, 4) for k, v in self.dimensions.items()},
            "confidence": round(self.confidence, 4),
            "lastUpdated": self.last_updated,
        }


@dataclass
class ReputationEvent:
    """A reputation-affecting event."""
    event_id: str
    agent_id: str
    event_type: str
    dimension: str
    impact: float  # -1.0 to 1.0
    weight: float  # Based on stake/importance
    metadata: Dict[str, Any]
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "eventId": self.event_id,
            "agentId": self.agent_id,
            "eventType": self.event_type,
            "dimension": self.dimension,
            "impact": self.impact,
            "weight": self.weight,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class ReputationLevel:
    """Reputation level with benefits."""
    level: int
    name: str
    min_score: float
    max_score: float
    benefits: Dict[str, Any]

    # Predefined levels
    LEVELS = [
        {"level": 1, "name": "Newcomer", "min": 0.0, "max": 0.3, "benefits": {"feeDiscount": 0, "transactionLimit": 100}},
        {"level": 2, "name": "Beginner", "min": 0.3, "max": 0.45, "benefits": {"feeDiscount": 0, "transactionLimit": 500}},
        {"level": 3, "name": "Intermediate", "min": 0.45, "max": 0.6, "benefits": {"feeDiscount": 0.05, "transactionLimit": 2000}},
        {"level": 4, "name": "Advanced", "min": 0.6, "max": 0.75, "benefits": {"feeDiscount": 0.1, "transactionLimit": 10000}},
        {"level": 5, "name": "Expert", "min": 0.75, "max": 0.85, "benefits": {"feeDiscount": 0.15, "transactionLimit": 50000}},
        {"level": 6, "name": "Master", "min": 0.85, "max": 0.95, "benefits": {"feeDiscount": 0.2, "transactionLimit": 100000}},
        {"level": 7, "name": "Legend", "min": 0.95, "max": 1.0, "benefits": {"feeDiscount": 0.25, "transactionLimit": 1000000}},
    ]

    @classmethod
    def get_level(cls, score: float) -> 'ReputationLevel':
        """Get level for a score."""
        for level_data in cls.LEVELS:
            if level_data["min"] <= score < level_data["max"]:
                return ReputationLevel(
                    level=level_data["level"],
                    name=level_data["name"],
                    min_score=level_data["min"],
                    max_score=level_data["max"],
                    benefits=level_data["benefits"],
                )
        # Default to highest level
        return ReputationLevel(
            level=7,
            name="Legend",
            min_score=0.95,
            max_score=1.0,
            benefits={"feeDiscount": 0.25, "transactionLimit": 1000000},
        )


class ReputationService:
    """
    Comprehensive Reputation Service.

    Features:
    - Multi-dimensional scoring
    - Time-weighted decay
    - Stake-based weights
    - Transaction-based updates
    - Periodic recalculation
    """

    # Configuration
    DECAY_RATE = 0.01  # 1% per day
    MIN_CONFIDENCE = 0.1
    MAX_CONFIDENCE = 1.0
    CONFIDENCE_INCREMENT = 0.05

    # Dimension weights for overall score
    DIMENSION_WEIGHTS = {
        ReputationDimension.RELIABILITY: 0.25,
        ReputationDimension.QUALITY: 0.25,
        ReputationDimension.RESPONSIVENESS: 0.15,
        ReputationDimension.FAIRNESS: 0.15,
        ReputationDimension.CONTRIBUTION: 0.20,
    }

    def __init__(self, db_connection=None, blockchain_service=None):
        """
        Initialize reputation service.

        Args:
            db_connection: Database connection for persistence
            blockchain_service: Blockchain service for on-chain reputation
        """
        self.db = db_connection
        self.blockchain = blockchain_service

        # In-memory cache
        self._scores: Dict[str, ReputationScore] = {}
        self._events: Dict[str, List[ReputationEvent]] = {}

        # Last recalculation time
        self._last_recalc: float = 0

    def initialize_agent(self, agent_id: str, initial_stake: float = 0) -> ReputationScore:
        """
        Initialize reputation for a new agent.

        Initial reputation is based on stake.
        """
        # Base reputation from stake
        base_score = 0.3 + min(initial_stake / 1000, 0.2)  # 0.3 to 0.5 based on stake

        dimensions = {dim.value: base_score for dim in ReputationDimension}

        score = ReputationScore(
            overall=base_score,
            dimensions=dimensions,
            confidence=self.MIN_CONFIDENCE,
            last_updated=time.time(),
        )

        self._scores[agent_id] = score
        self._events[agent_id] = []

        logger.info(f"Initialized reputation for {agent_id}: {base_score:.4f}")
        return score

    def record_event(
        self,
        agent_id: str,
        event_type: str,
        dimension: str,
        impact: float,
        weight: float = 1.0,
        metadata: Dict[str, Any] = None,
    ) -> ReputationEvent:
        """
        Record a reputation-affecting event.

        Args:
            agent_id: Agent ID
            event_type: Type of event (e.g., "transaction_completed", "rating_received")
            dimension: Which dimension this affects
            impact: Impact on reputation (-1.0 to 1.0)
            weight: Weight of this event (based on stake/importance)
            metadata: Additional context

        Returns:
            The created event
        """
        import uuid

        event = ReputationEvent(
            event_id=str(uuid.uuid4()),
            agent_id=agent_id,
            event_type=event_type,
            dimension=dimension,
            impact=max(-1.0, min(1.0, impact)),
            weight=max(0.1, min(10.0, weight)),
            metadata=metadata or {},
            timestamp=time.time(),
        )

        if agent_id not in self._events:
            self._events[agent_id] = []
        self._events[agent_id].append(event)

        # Update score
        self._apply_event(agent_id, event)

        logger.debug(f"Recorded reputation event for {agent_id}: {event_type} ({impact:+.2f})")
        return event

    def _apply_event(self, agent_id: str, event: ReputationEvent) -> None:
        """Apply an event to the agent's reputation."""
        if agent_id not in self._scores:
            self.initialize_agent(agent_id)

        score = self._scores[agent_id]

        # Calculate weighted impact
        weighted_impact = event.impact * event.weight * (1 - score.confidence * 0.5)

        # Update dimension
        dim = event.dimension
        if dim in score.dimensions:
            old_value = score.dimensions[dim]
            new_value = max(0.0, min(1.0, old_value + weighted_impact * 0.1))
            score.dimensions[dim] = new_value

        # Recalculate overall
        score.overall = self._calculate_overall(score.dimensions)

        # Increase confidence
        score.confidence = min(self.MAX_CONFIDENCE, score.confidence + self.CONFIDENCE_INCREMENT)

        score.last_updated = time.time()

    def _calculate_overall(self, dimensions: Dict[str, float]) -> float:
        """Calculate overall score from dimensions."""
        total = 0.0
        weight_sum = 0.0

        for dim, weight in self.DIMENSION_WEIGHTS.items():
            if dim.value in dimensions:
                total += dimensions[dim.value] * weight
                weight_sum += weight

        return total / weight_sum if weight_sum > 0 else 0.5

    def record_transaction_completed(
        self,
        agent_id: str,
        as_role: str,  # "buyer" or "seller"
        rating: Optional[int] = None,
        amount: float = 0,
        on_time: bool = True,
    ) -> None:
        """Record a completed transaction."""
        # Reliability boost
        reliability_impact = 0.1 if on_time else -0.05
        self.record_event(
            agent_id=agent_id,
            event_type="transaction_completed",
            dimension=ReputationDimension.RELIABILITY.value,
            impact=reliability_impact,
            weight=min(amount / 100, 2.0),  # Weight by amount
            metadata={"role": as_role, "onTime": on_time},
        )

        # Quality from rating
        if rating is not None:
            quality_impact = (rating - 3) / 10  # -0.3 to +0.2
            self.record_event(
                agent_id=agent_id,
                event_type="rating_received",
                dimension=ReputationDimension.QUALITY.value,
                impact=quality_impact,
                weight=min(amount / 100, 2.0),
                metadata={"rating": rating},
            )

    def record_response_time(
        self,
        agent_id: str,
        response_time_seconds: float,
        expected_seconds: float = 3600,  # 1 hour default
    ) -> None:
        """Record response time for responsiveness dimension."""
        # Calculate how much faster/slower than expected
        ratio = expected_seconds / max(response_time_seconds, 1)

        if ratio > 2:  # More than 2x faster
            impact = 0.15
        elif ratio > 1:  # Faster than expected
            impact = 0.05
        elif ratio > 0.5:  # Within 2x of expected
            impact = 0.0
        else:  # Much slower
            impact = -0.1

        self.record_event(
            agent_id=agent_id,
            event_type="response_recorded",
            dimension=ReputationDimension.RESPONSIVENESS.value,
            impact=impact,
            weight=0.5,
            metadata={"responseTime": response_time_seconds, "expected": expected_seconds},
        )

    def record_negotiation_outcome(
        self,
        agent_id: str,
        outcome: str,  # "agreed", "rejected", "timeout"
        was_fair: bool = True,
    ) -> None:
        """Record negotiation outcome for fairness dimension."""
        if outcome == "agreed":
            impact = 0.1 if was_fair else 0.0
        elif outcome == "rejected":
            impact = -0.05 if was_fair else -0.15
        else:  # timeout
            impact = -0.1

        self.record_event(
            agent_id=agent_id,
            event_type="negotiation_outcome",
            dimension=ReputationDimension.FAIRNESS.value,
            impact=impact,
            weight=0.5,
            metadata={"outcome": outcome, "wasFair": was_fair},
        )

    def record_contribution(
        self,
        agent_id: str,
        contribution_type: str,  # "referral", "content", "feedback", etc.
        value: float = 0.1,
    ) -> None:
        """Record a platform contribution."""
        self.record_event(
            agent_id=agent_id,
            event_type=f"contribution_{contribution_type}",
            dimension=ReputationDimension.CONTRIBUTION.value,
            impact=value,
            weight=0.3,
            metadata={"type": contribution_type},
        )

    def get_score(self, agent_id: str) -> Optional[ReputationScore]:
        """Get current reputation score for an agent."""
        return self._scores.get(agent_id)

    def get_level(self, agent_id: str) -> Optional[ReputationLevel]:
        """Get reputation level for an agent."""
        score = self.get_score(agent_id)
        if score:
            return ReputationLevel.get_level(score.overall)
        return None

    def get_events(
        self,
        agent_id: str,
        limit: int = 100,
        dimension: str = None,
    ) -> List[ReputationEvent]:
        """Get reputation events for an agent."""
        events = self._events.get(agent_id, [])

        if dimension:
            events = [e for e in events if e.dimension == dimension]

        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]

    def apply_decay(self, days: float = 1.0) -> int:
        """
        Apply time decay to all reputations.

        Returns number of agents affected.
        """
        decay_factor = 1 - (self.DECAY_RATE * days)
        count = 0

        for agent_id, score in self._scores.items():
            # Only decay if no recent activity
            time_since_update = time.time() - score.last_updated
            if time_since_update > 86400:  # More than 1 day
                # Decay each dimension towards neutral (0.5)
                for dim in score.dimensions:
                    current = score.dimensions[dim]
                    if current > 0.5:
                        score.dimensions[dim] = 0.5 + (current - 0.5) * decay_factor
                    else:
                        score.dimensions[dim] = 0.5 - (0.5 - current) * decay_factor

                # Recalculate overall
                score.overall = self._calculate_overall(score.dimensions)
                count += 1

        logger.info(f"Applied reputation decay to {count} agents")
        return count

    def recalculate_all(self) -> int:
        """
        Recalculate all reputation scores from events.

        Returns number of agents recalculated.
        """
        count = 0

        for agent_id, events in self._events.items():
            # Reset score
            score = ReputationScore(
                overall=0.5,
                dimensions={dim.value: 0.5 for dim in ReputationDimension},
                confidence=self.MIN_CONFIDENCE,
                last_updated=time.time(),
            )
            self._scores[agent_id] = score

            # Replay all events
            for event in sorted(events, key=lambda e: e.timestamp):
                self._apply_event(agent_id, event)

            count += 1

        self._last_recalc = time.time()
        logger.info(f"Recalculated reputation for {count} agents")
        return count

    def get_leaderboard(
        self,
        dimension: str = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get reputation leaderboard.

        Args:
            dimension: Specific dimension to rank by (None for overall)
            limit: Maximum entries

        Returns:
            List of {agent_id, score, level} dicts
        """
        results = []

        for agent_id, score in self._scores.items():
            if dimension:
                value = score.dimensions.get(dimension, 0.5)
            else:
                value = score.overall

            level = ReputationLevel.get_level(score.overall)
            results.append({
                "agentId": agent_id,
                "score": value,
                "level": level.name,
                "levelNumber": level.level,
                "confidence": score.confidence,
            })

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get reputation system statistics."""
        if not self._scores:
            return {
                "totalAgents": 0,
                "averageScore": 0,
                "distribution": {},
            }

        scores = [s.overall for s in self._scores.values()]

        # Distribution by level
        distribution = {}
        for score in self._scores.values():
            level = ReputationLevel.get_level(score.overall)
            distribution[level.name] = distribution.get(level.name, 0) + 1

        return {
            "totalAgents": len(self._scores),
            "averageScore": sum(scores) / len(scores),
            "minScore": min(scores),
            "maxScore": max(scores),
            "distribution": distribution,
            "totalEvents": sum(len(events) for events in self._events.values()),
            "lastRecalculation": self._last_recalc,
        }


# Global reputation service instance
_reputation_service: Optional[ReputationService] = None


def get_reputation_service() -> ReputationService:
    """Get or create reputation service instance."""
    global _reputation_service
    if _reputation_service is None:
        _reputation_service = ReputationService()
    return _reputation_service
