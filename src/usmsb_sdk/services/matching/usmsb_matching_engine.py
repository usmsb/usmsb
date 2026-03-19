"""
USMSB Matching Engine

Phase 3 of USMSB Agent Platform implementation.

Provides USMSB-based three-dimensional matching:
- Goal matching: What the Agent wants to achieve
- Capability matching: What the Agent can provide
- Value alignment: Whether the value exchange is fair

This is NOT simple skill-based matching. It's full USMSB profile matching.

Contrast with SimpleMatchingEngine:
- SimpleMatchingEngine: "You have skill X, task needs skill X" (1 dimension)
- USMSBMatchingEngine: "Your Goal + Capability + Value alignment matches this opportunity" (3 dimensions)
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from usmsb_sdk.services.agent_soul import AgentSoul, AgentSoulManager
from usmsb_sdk.services.agent_soul.models import DeclaredSoul
from usmsb_sdk.services.schema import create_session

logger = logging.getLogger(__name__)


@dataclass
class CollaborationOpportunity:
    """
    Represents a collaboration opportunity found by the matching engine.

    Includes:
    - The opportunity details
    - Match scores for each dimension (goal, capability, value)
    - Overall value chain potential
    """
    opportunity_id: str
    opportunity_type: str  # "task" | "project" | "collaboration"

    # Parties involved
    demand_agent_id: str
    supply_agent_id: str | None = None  # None if opportunity is open

    # Match scores (0.0 ~ 1.0)
    goal_match_score: float = 0.0
    capability_match_score: float = 0.0
    value_alignment_score: float = 0.0
    overall_score: float = 0.0

    # Value chain potential
    value_chain_potential: float = 0.0  # Estimated value that could be created

    # Opportunity details
    task_def: dict[str, Any] | None = None
    project_def: dict[str, Any] | None = None

    # Why this match was recommended
    match_reasons: list[str] = field(default_factory=list)

    # Risks identified
    identified_risks: list[str] = field(default_factory=list)

    # Recommended contract terms
    recommended_terms: dict[str, Any] = field(default_factory=dict)

    # Metadata
    discovered_at: float = 0.0
    expires_at: float = 0.0


class USMSBMatchingEngine:
    """
    USMSB-based three-dimensional matching engine.

    Finds collaboration opportunities based on:
    1. Goal alignment: Does the opportunity serve the Agent's goals?
    2. Capability match: Does the Agent have what the opportunity needs?
    3. Value alignment: Is the value exchange fair for both parties?

    Simple task threshold:
    - Tasks below complexity threshold → use centralized matching (faster)
    - Tasks above complexity threshold → use decentralized emergence discovery
    """

    # Complexity threshold: tasks with score < threshold are "simple"
    SIMPLE_TASK_THRESHOLD = 5.0

    # Minimum scores for a viable match
    MIN_GOAL_MATCH = 0.3
    MIN_CAPABILITY_MATCH = 0.4
    MIN_VALUE_ALIGNMENT = 0.3
    MIN_OVERALL_SCORE = 0.4

    def __init__(self):
        self.soul_manager = None  # Lazy initialization

    def _get_soul_manager(self) -> AgentSoulManager:
        if self.soul_manager is None:
            session = create_session()
            self.soul_manager = AgentSoulManager(session)
        return self.soul_manager

    async def find_collaboration_opportunities(
        self,
        agent_id: str,
        opportunity_type: str = "all",  # "task" | "project" | "collaboration" | "all"
        limit: int = 10,
    ) -> list[CollaborationOpportunity]:
        """
        Find collaboration opportunities for an Agent.

        This is the main entry point for the matching engine.

        Args:
            agent_id: Agent to find opportunities for
            opportunity_type: Filter by type
            limit: Maximum number of opportunities to return

        Returns:
            List of CollaborationOpportunities, sorted by overall_score
        """
        manager = self._get_soul_manager()
        agent_soul = await manager.get_soul(agent_id)

        if not agent_soul:
            logger.warning(f"Agent {agent_id} has no Soul, cannot match")
            return []

        opportunities = []

        # Find demand matches (Agent needs something)
        demand_opps = await self._find_demand_matches(agent_soul)
        opportunities.extend(demand_opps)

        # Find supply matches (Agent can provide something)
        supply_opps = await self._find_supply_matches(agent_soul)
        opportunities.extend(supply_opps)

        # Find collaboration matches (shared goals)
        collab_opps = await self._find_collaboration_matches(agent_soul)
        opportunities.extend(collab_opps)

        # Filter by type
        if opportunity_type != "all":
            opportunities = [
                o for o in opportunities
                if o.opportunity_type == opportunity_type
            ]

        # Sort by overall score
        opportunities.sort(key=lambda x: x.overall_score, reverse=True)

        return opportunities[:limit]

    async def _find_demand_matches(
        self,
        agent_soul: AgentSoul,
    ) -> list[CollaborationOpportunity]:
        """
        Find opportunities where this Agent is the demand side (they need something).

        Example: Agent has Goal "analyze market data" but lacks capability "data analysis"
        → Find agents who can provide "data analysis"
        """
        opportunities = []
        manager = self._get_soul_manager()

        # Get all agents who might supply what this agent needs
        all_agents = await self._get_all_agent_souls()
        agent_needs = self._extract_agent_needs(agent_soul)

        for supply_soul in all_agents:
            if supply_soul.agent_id == agent_soul.agent_id:
                continue

            # Calculate match score
            match_result = await self._calculate_match_score(
                demand_soul=agent_soul,
                supply_soul=supply_soul,
                match_type="demand",
            )

            if match_result["overall_score"] >= self.MIN_OVERALL_SCORE:
                opp = CollaborationOpportunity(
                    opportunity_id=f"opp-demand-{agent_soul.agent_id}-{supply_soul.agent_id}",
                    opportunity_type="task",
                    demand_agent_id=agent_soul.agent_id,
                    supply_agent_id=supply_soul.agent_id,
                    goal_match_score=match_result["goal_match"],
                    capability_match_score=match_result["capability_match"],
                    value_alignment_score=match_result["value_alignment"],
                    overall_score=match_result["overall_score"],
                    value_chain_potential=match_result["value_potential"],
                    match_reasons=match_result["reasons"],
                    identified_risks=match_result["risks"],
                    recommended_terms=match_result["recommended_terms"],
                    discovered_at=time.time(),
                    expires_at=time.time() + 3600,
                )
                opportunities.append(opp)

        return opportunities

    async def _find_supply_matches(
        self,
        agent_soul: AgentSoul,
    ) -> list[CollaborationOpportunity]:
        """
        Find opportunities where this Agent is the supply side (they can provide something).

        Example: Agent has capability "code generation"
        → Find agents who have Goals that need "code generation"
        """
        opportunities = []
        manager = self._get_soul_manager()

        all_agents = await self._get_all_agent_souls()
        agent_capabilities = self._extract_agent_capabilities(agent_soul)

        for demand_soul in all_agents:
            if demand_soul.agent_id == agent_soul.agent_id:
                continue

            match_result = await self._calculate_match_score(
                demand_soul=demand_soul,
                supply_soul=agent_soul,
                match_type="supply",
            )

            if match_result["overall_score"] >= self.MIN_OVERALL_SCORE:
                opp = CollaborationOpportunity(
                    opportunity_id=f"opp-supply-{agent_soul.agent_id}-{demand_soul.agent_id}",
                    opportunity_type="task",
                    demand_agent_id=demand_soul.agent_id,
                    supply_agent_id=agent_soul.agent_id,
                    goal_match_score=match_result["goal_match"],
                    capability_match_score=match_result["capability_match"],
                    value_alignment_score=match_result["value_alignment"],
                    overall_score=match_result["overall_score"],
                    value_chain_potential=match_result["value_potential"],
                    match_reasons=match_result["reasons"],
                    identified_risks=match_result["risks"],
                    recommended_terms=match_result["recommended_terms"],
                    discovered_at=time.time(),
                    expires_at=time.time() + 3600,
                )
                opportunities.append(opp)

        return opportunities

    async def _find_collaboration_matches(
        self,
        agent_soul: AgentSoul,
    ) -> list[CollaborationOpportunity]:
        """
        Find opportunities where multiple agents share similar Goals.

        Example: Two agents both have Goal "build a research platform"
        → They could collaborate rather than compete
        """
        opportunities = []
        manager = self._get_soul_manager()

        all_agents = await self._get_all_agent_souls()

        for other_soul in all_agents:
            if other_soul.agent_id == agent_soul.agent_id:
                continue

            # Check for shared goals
            shared_goals = self._find_shared_goals(agent_soul, other_soul)

            if shared_goals:
                # Calculate collaboration potential
                score = self._calculate_collaboration_score(agent_soul, other_soul, shared_goals)

                if score >= self.MIN_OVERALL_SCORE:
                    opp = CollaborationOpportunity(
                        opportunity_id=f"opp-collab-{agent_soul.agent_id}-{other_soul.agent_id}",
                        opportunity_type="collaboration",
                        demand_agent_id=agent_soul.agent_id,
                        supply_agent_id=other_soul.agent_id,
                        goal_match_score=score,
                        capability_match_score=score * 0.8,
                        value_alignment_score=score * 0.9,
                        overall_score=score,
                        value_chain_potential=score * 1.5,  # Collaboration has higher potential
                        match_reasons=[f"Shared goals: {g}" for g in shared_goals[:3]],
                        discovered_at=time.time(),
                        expires_at=time.time() + 86400,  # Collaborations expire slower
                    )
                    opportunities.append(opp)

        return opportunities

    async def _calculate_match_score(
        self,
        demand_soul: AgentSoul,
        supply_soul: AgentSoul,
        match_type: str,  # "demand" | "supply"
    ) -> dict[str, Any]:
        """
        Calculate the match score between demand and supply agents.

        Returns:
            dict with keys: goal_match, capability_match, value_alignment,
                           overall_score, value_potential, reasons, risks, recommended_terms
        """
        reasons = []
        risks = []

        # Goal match: How well does this match serve the demand agent's goals?
        goal_match = 0.0
        if demand_soul.declared.goals:
            # Check if supply's capabilities could serve demand's goals
            supply_caps = set(supply_soul.declared.capabilities)
            for goal in demand_soul.declared.goals:
                # Simple keyword matching (real impl would use embeddings)
                goal_keywords = goal.name.lower().split()
                for keyword in goal_keywords:
                    if keyword in " ".join(supply_caps).lower():
                        goal_match += 0.2
                        reasons.append(f"Supply capability matches demand Goal: {goal.name}")
                        break
            goal_match = min(1.0, goal_match)

        if goal_match < self.MIN_GOAL_MATCH:
            return {
                "goal_match": goal_match,
                "capability_match": 0.0,
                "value_alignment": 0.0,
                "overall_score": 0.0,
                "value_potential": 0.0,
                "reasons": ["Goal match too low"],
                "risks": risks,
                "recommended_terms": {},
            }

        # Capability match: How well does supply's capabilities match demand's needs?
        capability_match = 0.0
        supply_caps = set(supply_soul.declared.capabilities)

        if demand_soul.declared.capabilities:
            demand_caps = set(demand_soul.declared.capabilities)
            overlap = supply_caps.intersection(demand_caps)
            capability_match = len(overlap) / max(len(demand_caps), 1)
            if overlap:
                reasons.append(f"Capability overlap: {', '.join(overlap)}")

        # If demand is looking for supply (reverse case)
        if match_type == "supply" and not capability_match:
            # Check supply's reputation as proxy for capability
            if supply_soul.inferred and supply_soul.inferred.actual_success_rate > 0.7:
                capability_match = supply_soul.inferred.actual_success_rate
                reasons.append(f"High reputation ({capability_match:.0%}) indicates strong capability")

        capability_match = min(1.0, capability_match)

        # Value alignment: Is the proposed value exchange fair?
        value_alignment = self._calculate_value_alignment(demand_soul, supply_soul)

        # Overall score: weighted average
        overall_score = (
            goal_match * 0.35 +
            capability_match * 0.35 +
            value_alignment * 0.30
        )

        # Value potential: How much value could this collaboration create?
        value_potential = overall_score * (1.0 + capability_match * 0.5)

        # Risk assessment
        if supply_soul.inferred:
            if supply_soul.inferred.actual_success_rate < 0.5:
                risks.append("Supply agent has low success rate")
            if supply_soul.inferred.value_alignment_score < 0.4:
                risks.append("Value alignment concerns")

        # Reputation-based adjustments
        if supply_soul.inferred:
            rep_weight = 0.1
            overall_score += supply_soul.inferred.actual_success_rate * rep_weight
            overall_score = min(1.0, overall_score)

        # Recommended terms
        recommended_terms = self._generate_recommended_terms(
            demand_soul, supply_soul, capability_match
        )

        return {
            "goal_match": goal_match,
            "capability_match": capability_match,
            "value_alignment": value_alignment,
            "overall_score": overall_score,
            "value_potential": value_potential,
            "reasons": reasons,
            "risks": risks,
            "recommended_terms": recommended_terms,
        }

    def _calculate_value_alignment(
        self,
        demand_soul: AgentSoul,
        supply_soul: AgentSoul,
    ) -> float:
        """
        Calculate value alignment score between two agents.

        Higher score = more aligned in value expectations.
        """
        # Pricing strategy alignment
        pricing_alignment = 1.0 if (
            demand_soul.declared.pricing_strategy ==
            supply_soul.declared.pricing_strategy
        ) else 0.7

        # Risk tolerance alignment
        risk_diff = abs(
            demand_soul.declared.risk_tolerance -
            supply_soul.declared.risk_tolerance
        )
        risk_alignment = 1.0 - risk_diff

        # Collaboration style alignment
        style_alignment = 1.0 if (
            demand_soul.declared.collaboration_style ==
            supply_soul.declared.collaboration_style
        ) else 0.6

        # Weighted average
        value_alignment = (
            pricing_alignment * 0.4 +
            risk_alignment * 0.3 +
            style_alignment * 0.3
        )

        return min(1.0, value_alignment)

    def _calculate_collaboration_score(
        self,
        agent_a: AgentSoul,
        agent_b: AgentSoul,
        shared_goals: list[str],
    ) -> float:
        """Calculate collaboration potential based on shared goals and capabilities."""
        if not shared_goals:
            return 0.0

        # Base score from shared goals
        goal_score = min(1.0, len(shared_goals) * 0.3)

        # Capability complementarity
        caps_a = set(agent_a.declared.capabilities)
        caps_b = set(agent_b.declared.capabilities)
        complement = len(caps_a.union(caps_b)) - len(caps_a.intersection(caps_b))
        cap_score = min(1.0, complement / max(len(caps_a), len(caps_b), 1))

        # Collaboration style compatibility
        style_score = 1.0 if (
            agent_a.declared.collaboration_style ==
            agent_b.declared.collaboration_style
        ) else 0.6

        return goal_score * 0.5 + cap_score * 0.3 + style_score * 0.2

    def _generate_recommended_terms(
        self,
        demand_soul: AgentSoul,
        supply_soul: AgentSoul,
        capability_match: float,
    ) -> dict[str, Any]:
        """Generate recommended contract terms based on match analysis."""
        terms = {}

        # Price recommendation based on market rates
        if demand_soul.declared.base_price_vibe and supply_soul.declared.base_price_vibe:
            # Midpoint
            recommended_price = (
                demand_soul.declared.base_price_vibe +
                supply_soul.declared.base_price_vibe
            ) / 2
            terms["price_vibe"] = round(recommended_price, 2)
        elif supply_soul.declared.base_price_vibe:
            terms["price_vibe"] = supply_soul.declared.base_price_vibe
        else:
            terms["price_vibe"] = 10.0  # Default

        # Deadline based on task complexity
        if capability_match >= 0.8:
            terms["deadline"] = 86400  # 1 day for simple tasks
        elif capability_match >= 0.5:
            terms["deadline"] = 259200  # 3 days
        else:
            terms["deadline"] = 604800  # 7 days

        # Platform fee
        terms["platform_fee_percentage"] = 5.0

        return terms

    async def _get_all_agent_souls(self) -> list[AgentSoul]:
        """Get all registered agent souls."""
        manager = self._get_soul_manager()
        session = manager.db
        from usmsb_sdk.services.schema import AgentSoulDB

        db_records = session.query(AgentSoulDB).all()
        souls = [manager._db_to_soul(r) for r in db_records]
        return souls

    def _extract_agent_needs(self, soul: AgentSoul) -> list[str]:
        """Extract what an agent needs based on their goals."""
        needs = []
        for goal in soul.declared.goals:
            needs.append(goal.name)
            if goal.description:
                needs.extend(goal.description.split())
        return needs

    def _extract_agent_capabilities(self, soul: AgentSoul) -> list[str]:
        """Extract what an agent can provide."""
        return soul.declared.capabilities.copy()

    def _find_shared_goals(self, soul_a: AgentSoul, soul_b: AgentSoul) -> list[str]:
        """Find shared goals between two agents."""
        shared = []
        goals_a = {g.name.lower() for g in soul_a.declared.goals}
        goals_b = {g.name.lower() for g in soul_b.declared.goals}
        intersection = goals_a.intersection(goals_b)
        if intersection:
            # Get original goal names
            for goal in soul_a.declared.goals:
                if goal.name.lower() in intersection:
                    shared.append(goal.name)
        return shared
