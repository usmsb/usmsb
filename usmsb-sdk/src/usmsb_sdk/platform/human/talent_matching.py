"""
Talent Matching Service

Service for matching tasks with suitable human agents based on
skills, availability, preferences, and performance history.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from usmsb_sdk.platform.human.adapter import (
    AssignedTask,
    HumanAgentAdapter,
    HumanAgentProfile,
    HumanAgentStatus,
    Skill,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class MatchingStrategy(str, Enum):
    """Strategy for talent matching."""
    BEST_MATCH = "best_match"  # Highest skill match
    FASTEST = "fastest"  # Most available/quick
    COST_EFFECTIVE = "cost_effective"  # Lowest cost
    BALANCED = "balanced"  # Balance of all factors
    RANDOM = "random"  # Random selection


@dataclass
class MatchingCriteria:
    """Criteria for talent matching."""
    required_skills: List[str] = field(default_factory=list)
    min_skill_level: int = 1
    min_rating: float = 0.0
    max_hourly_rate: Optional[float] = None
    required_specializations: List[str] = field(default_factory=list)
    preferred_languages: List[str] = field(default_factory=list)
    timezone_preference: Optional[str] = None
    exclude_agent_ids: List[str] = field(default_factory=list)
    must_be_available: bool = True


@dataclass
class MatchingResult:
    """Result of talent matching."""
    agent_id: str
    score: float
    skill_match: float
    availability_score: float
    rating_score: float
    cost_score: float
    specializations_match: bool
    reasons: List[str] = field(default_factory=list)


@dataclass
class MatchingConfig:
    """Configuration for matching service."""
    strategy: MatchingStrategy = MatchingStrategy.BALANCED
    skill_weight: float = 0.4
    availability_weight: float = 0.3
    rating_weight: float = 0.2
    cost_weight: float = 0.1
    max_results: int = 10
    auto_assign_threshold: float = 0.9


class TalentMatchingService:
    """
    Talent Matching Service.

    Provides intelligent matching between tasks and human agents:
    - Skill-based matching
    - Availability scoring
    - Performance history consideration
    - Cost optimization
    - Auto-assignment
    """

    def __init__(
        self,
        human_adapter: HumanAgentAdapter,
        config: Optional[MatchingConfig] = None,
    ):
        """
        Initialize the Talent Matching Service.

        Args:
            human_adapter: Human agent adapter
            config: Matching configuration
        """
        self.adapter = human_adapter
        self.config = config or MatchingConfig()

        # Match history for learning
        self._match_history: List[Dict[str, Any]] = []

    def find_matches(
        self,
        criteria: MatchingCriteria,
        strategy: Optional[MatchingStrategy] = None,
    ) -> List[MatchingResult]:
        """
        Find matching agents for given criteria.

        Args:
            criteria: Matching criteria
            strategy: Matching strategy (overrides config)

        Returns:
            List of matching results sorted by score
        """
        strategy = strategy or self.config.strategy

        # Get all potential candidates
        candidates = self._filter_candidates(criteria)

        # Score each candidate
        results = []
        for profile in candidates:
            result = self._score_candidate(profile, criteria, strategy)
            if result.score > 0:
                results.append(result)

        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:self.config.max_results]

    def _filter_candidates(self, criteria: MatchingCriteria) -> List[HumanAgentProfile]:
        """Filter candidates based on hard criteria."""
        candidates = []

        for profile in self.adapter._profiles.values():
            # Exclude specified agents
            if profile.agent_id in criteria.exclude_agent_ids:
                continue

            # Check availability if required
            if criteria.must_be_available and profile.status != HumanAgentStatus.AVAILABLE:
                continue

            # Check minimum rating
            if profile.rating < criteria.min_rating:
                continue

            # Check hourly rate limit
            if criteria.max_hourly_rate and profile.hourly_rate > criteria.max_hourly_rate:
                continue

            # Check required skills
            if criteria.required_skills:
                has_all_skills = all(
                    profile.has_skill(skill, criteria.min_skill_level)
                    for skill in criteria.required_skills
                )
                if not has_all_skills:
                    continue

            # Check specializations
            if criteria.required_specializations:
                has_spec = any(
                    spec in profile.specializations
                    for spec in criteria.required_specializations
                )
                if not has_spec:
                    continue

            candidates.append(profile)

        return candidates

    def _score_candidate(
        self,
        profile: HumanAgentProfile,
        criteria: MatchingCriteria,
        strategy: MatchingStrategy,
    ) -> MatchingResult:
        """Score a candidate profile."""
        reasons = []

        # Calculate skill match score
        skill_match = self._calculate_skill_match(profile, criteria)
        if skill_match > 0:
            reasons.append(f"Skill match: {skill_match:.0%}")

        # Calculate availability score
        availability_score = self._calculate_availability_score(profile)
        if availability_score == 1.0:
            reasons.append("Currently available")

        # Calculate rating score
        rating_score = profile.rating / 5.0
        if profile.rating >= 4.5:
            reasons.append(f"High rating: {profile.rating:.1f}")

        # Calculate cost score (inverted - lower cost is better)
        cost_score = self._calculate_cost_score(profile, criteria)
        if cost_score > 0.8:
            reasons.append(f"Competitive rate: ${profile.hourly_rate:.2f}/hr")

        # Check specializations match
        specs_match = not criteria.required_specializations or any(
            spec in profile.specializations
            for spec in criteria.required_specializations
        )
        if specs_match and criteria.required_specializations:
            reasons.append("Has required specialization")

        # Calculate overall score based on strategy
        if strategy == MatchingStrategy.BEST_MATCH:
            score = skill_match * 0.8 + rating_score * 0.2
        elif strategy == MatchingStrategy.FASTEST:
            score = availability_score * 0.6 + skill_match * 0.4
        elif strategy == MatchingStrategy.COST_EFFECTIVE:
            score = cost_score * 0.6 + skill_match * 0.3 + rating_score * 0.1
        elif strategy == MatchingStrategy.BALANCED:
            score = (
                skill_match * self.config.skill_weight +
                availability_score * self.config.availability_weight +
                rating_score * self.config.rating_weight +
                cost_score * self.config.cost_weight
            )
        elif strategy == MatchingStrategy.RANDOM:
            import random
            score = random.random()

        return MatchingResult(
            agent_id=profile.agent_id,
            score=score,
            skill_match=skill_match,
            availability_score=availability_score,
            rating_score=rating_score,
            cost_score=cost_score,
            specializations_match=specs_match,
            reasons=reasons,
        )

    def _calculate_skill_match(
        self,
        profile: HumanAgentProfile,
        criteria: MatchingCriteria,
    ) -> float:
        """Calculate skill match score."""
        if not criteria.required_skills:
            return 1.0

        total_score = 0.0
        for skill_name in criteria.required_skills:
            level = profile.get_skill_level(skill_name)
            if level >= criteria.min_skill_level:
                # Bonus for higher levels
                total_score += min(level / 5.0, 1.0)

        return total_score / len(criteria.required_skills)

    def _calculate_availability_score(self, profile: HumanAgentProfile) -> float:
        """Calculate availability score."""
        if profile.status == HumanAgentStatus.AVAILABLE:
            return 1.0
        elif profile.status == HumanAgentStatus.AWAY:
            return 0.5
        elif profile.status == HumanAgentStatus.BUSY:
            return 0.2
        else:
            return 0.0

    def _calculate_cost_score(
        self,
        profile: HumanAgentProfile,
        criteria: MatchingCriteria,
    ) -> float:
        """Calculate cost score (higher is better/cheaper)."""
        if profile.hourly_rate == 0:
            return 1.0  # Free

        if criteria.max_hourly_rate:
            # Score based on how much under budget
            return 1.0 - (profile.hourly_rate / criteria.max_hourly_rate)

        # Score inversely to rate (capped at reasonable range)
        max_reasonable_rate = 200.0  # $200/hr
        return max(0, 1.0 - (profile.hourly_rate / max_reasonable_rate))

    def match_task(
        self,
        task: AssignedTask,
        strategy: Optional[MatchingStrategy] = None,
    ) -> Optional[MatchingResult]:
        """
        Find best match for a specific task.

        Args:
            task: Task to match
            strategy: Matching strategy

        Returns:
            Best matching result or None
        """
        criteria = MatchingCriteria(
            required_skills=task.required_skills,
            must_be_available=True,
        )

        matches = self.find_matches(criteria, strategy)
        return matches[0] if matches else None

    def auto_assign(
        self,
        task: AssignedTask,
        threshold: Optional[float] = None,
    ) -> Optional[str]:
        """
        Auto-assign a task if a good match is found.

        Args:
            task: Task to assign
            threshold: Score threshold (overrides config)

        Returns:
            Assigned agent ID or None
        """
        threshold = threshold or self.config.auto_assign_threshold

        match = self.match_task(task)
        if match and match.score >= threshold:
            # Auto-assign
            success = self.adapter.accept_task(task.id)
            if success:
                logger.info(f"Task {task.id} auto-assigned to {match.agent_id}")
                return match.agent_id

        return None

    def get_recommendations(
        self,
        task: AssignedTask,
        count: int = 3,
    ) -> List[Tuple[HumanAgentProfile, MatchingResult]]:
        """
        Get recommendations for a task.

        Args:
            task: Task to get recommendations for
            count: Number of recommendations

        Returns:
            List of (profile, result) tuples
        """
        criteria = MatchingCriteria(
            required_skills=task.required_skills,
            must_be_available=False,  # Include busy agents for recommendations
        )

        matches = self.find_matches(criteria)[:count]

        results = []
        for match in matches:
            profile = self.adapter.get_profile(match.agent_id)
            if profile:
                results.append((profile, match))

        return results

    def record_match_outcome(
        self,
        task_id: str,
        agent_id: str,
        success: bool,
        rating: Optional[float] = None,
        feedback: Optional[str] = None,
    ) -> None:
        """
        Record the outcome of a match for learning.

        Args:
            task_id: Task ID
            agent_id: Agent ID
            success: Whether the match was successful
            rating: Rating given
            feedback: Feedback provided
        """
        record = {
            "task_id": task_id,
            "agent_id": agent_id,
            "success": success,
            "rating": rating,
            "feedback": feedback,
            "timestamp": time.time(),
        }

        self._match_history.append(record)

        # Update agent performance metrics
        profile = self.adapter.get_profile(agent_id)
        if profile:
            # Update skill last used timestamps if successful
            if success and rating and rating >= 4.0:
                for skill in profile.skills:
                    skill.last_used = time.time()

    def get_match_statistics(self) -> Dict[str, Any]:
        """Get matching statistics."""
        if not self._match_history:
            return {"total_matches": 0}

        total = len(self._match_history)
        successful = sum(1 for r in self._match_history if r["success"])
        ratings = [r["rating"] for r in self._match_history if r["rating"]]

        return {
            "total_matches": total,
            "successful_matches": successful,
            "success_rate": successful / total,
            "average_rating": sum(ratings) / len(ratings) if ratings else None,
            "unique_agents_matched": len(set(r["agent_id"] for r in self._match_history)),
        }
