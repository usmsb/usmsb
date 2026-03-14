"""
Decision Support Service

Service for providing decision support based on USMSB model elements.
Supports multi-criteria decision analysis, risk assessment, and
recommendation generation.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from usmsb_sdk.core.elements import Agent, Goal, Information, Resource, Risk, Rule
from usmsb_sdk.intelligence_adapters.base import ILLMAdapter

logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of decisions supported."""
    SINGLE_CHOICE = "single_choice"
    MULTI_CHOICE = "multi_choice"
    SEQUENTIAL = "sequential"
    RESOURCE_ALLOCATION = "resource_allocation"
    RISK_MITIGATION = "risk_mitigation"
    STRATEGIC = "strategic"
    OPERATIONAL = "operational"


class DecisionStatus(Enum):
    """Status of a decision."""
    PENDING = "pending"
    ANALYZING = "analyzing"
    DECIDED = "decided"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DecisionOption:
    """A single decision option."""
    id: str
    name: str
    description: str
    expected_outcome: str
    resource_requirements: dict[str, float] = field(default_factory=dict)
    risk_level: float = 0.0
    estimated_value: float = 0.0
    constraints: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionCriteria:
    """Criteria for evaluating decision options."""
    name: str
    description: str
    weight: float = 1.0
    is_cost: bool = False  # True if lower is better
    min_value: float | None = None
    max_value: float | None = None


@dataclass
class DecisionContext:
    """Context for decision making."""
    agent: Agent
    goals: list[Goal]
    resources: list[Resource]
    risks: list[Risk]
    rules: list[Rule]
    information: list[Information]
    constraints: dict[str, Any] = field(default_factory=dict)
    preferences: dict[str, float] = field(default_factory=dict)
    time_horizon: int = 1


@dataclass
class DecisionAnalysis:
    """Result of decision analysis."""
    option_scores: dict[str, dict[str, float]]
    weighted_scores: dict[str, float]
    rankings: list[tuple[str, float]]
    sensitivity_analysis: dict[str, Any]
    tradeoffs: list[dict[str, Any]]
    confidence: float
    reasoning: str


@dataclass
class DecisionRecommendation:
    """Final decision recommendation."""
    recommended_option: DecisionOption
    alternatives: list[DecisionOption]
    analysis: DecisionAnalysis
    rationale: str
    expected_outcome: str
    risk_assessment: dict[str, Any]
    implementation_steps: list[str]
    confidence: float
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class DecisionSupportService:
    """
    Decision Support Service.

    Provides comprehensive decision support including:
    - Multi-criteria decision analysis (MCDA)
    - Risk-informed decision making
    - Goal-aligned recommendations
    - Resource-aware optimization
    - Sensitivity analysis
    """

    def __init__(
        self,
        llm_adapter: ILLMAdapter,
        default_criteria: list[DecisionCriteria] | None = None,
    ):
        """
        Initialize the Decision Support Service.

        Args:
            llm_adapter: LLM adapter for reasoning
            default_criteria: Default evaluation criteria
        """
        self.llm = llm_adapter
        self.default_criteria = default_criteria or self._get_default_criteria()
        self._decision_history: list[dict[str, Any]] = []

    def _get_default_criteria(self) -> list[DecisionCriteria]:
        """Get default decision criteria."""
        return [
            DecisionCriteria(
                name="goal_alignment",
                description="Alignment with primary goal",
                weight=1.0,
                is_cost=False,
            ),
            DecisionCriteria(
                name="resource_efficiency",
                description="Efficiency of resource utilization",
                weight=0.8,
                is_cost=True,
            ),
            DecisionCriteria(
                name="risk_level",
                description="Level of risk involved",
                weight=0.7,
                is_cost=True,
            ),
            DecisionCriteria(
                name="time_to_complete",
                description="Time required for implementation",
                weight=0.5,
                is_cost=True,
            ),
            DecisionCriteria(
                name="expected_value",
                description="Expected value creation",
                weight=0.9,
                is_cost=False,
            ),
        ]

    async def analyze_decision(
        self,
        options: list[DecisionOption],
        context: DecisionContext,
        criteria: list[DecisionCriteria] | None = None,
    ) -> DecisionAnalysis:
        """
        Analyze decision options using MCDA.

        Args:
            options: List of decision options
            context: Decision context
            criteria: Evaluation criteria (uses defaults if None)

        Returns:
            DecisionAnalysis with detailed scores and rankings
        """
        if criteria is None:
            criteria = self.default_criteria

        # Evaluate each option against each criterion
        option_scores: dict[str, dict[str, float]] = {}

        for option in options:
            option_scores[option.id] = await self._evaluate_option(
                option, context, criteria
            )

        # Normalize scores
        normalized_scores = self._normalize_scores(option_scores, criteria)

        # Calculate weighted scores
        weighted_scores = self._calculate_weighted_scores(normalized_scores, criteria)

        # Rank options
        rankings = sorted(
            weighted_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Perform sensitivity analysis
        sensitivity = await self._sensitivity_analysis(
            options, context, criteria, weighted_scores
        )

        # Identify tradeoffs
        tradeoffs = self._identify_tradeoffs(option_scores, criteria, rankings)

        # Calculate overall confidence
        confidence = self._calculate_confidence(option_scores, rankings)

        # Generate reasoning
        reasoning = await self._generate_analysis_reasoning(
            options, rankings, option_scores, criteria, context
        )

        return DecisionAnalysis(
            option_scores=option_scores,
            weighted_scores=weighted_scores,
            rankings=rankings,
            sensitivity_analysis=sensitivity,
            tradeoffs=tradeoffs,
            confidence=confidence,
            reasoning=reasoning,
        )

    async def recommend(
        self,
        options: list[DecisionOption],
        context: DecisionContext,
        criteria: list[DecisionCriteria] | None = None,
        decision_type: DecisionType = DecisionType.SINGLE_CHOICE,
    ) -> DecisionRecommendation:
        """
        Generate a decision recommendation.

        Args:
            options: List of decision options
            context: Decision context
            criteria: Evaluation criteria
            decision_type: Type of decision

        Returns:
            DecisionRecommendation with recommended option
        """
        # Perform analysis
        analysis = await self.analyze_decision(options, context, criteria)

        # Get recommended option
        recommended_id = analysis.rankings[0][0]
        recommended = next(o for o in options if o.id == recommended_id)

        # Get alternatives
        alternative_ids = [r[0] for r in analysis.rankings[1:]]
        alternatives = [o for o in options if o.id in alternative_ids]

        # Generate detailed rationale
        rationale = await self._generate_rationale(
            recommended, alternatives, analysis, context
        )

        # Generate expected outcome
        expected_outcome = await self._predict_outcome(
            recommended, context
        )

        # Risk assessment
        risk_assessment = await self._assess_risks(recommended, context)

        # Implementation steps
        implementation_steps = await self._generate_implementation_steps(
            recommended, context
        )

        recommendation = DecisionRecommendation(
            recommended_option=recommended,
            alternatives=alternatives,
            analysis=analysis,
            rationale=rationale,
            expected_outcome=expected_outcome,
            risk_assessment=risk_assessment,
            implementation_steps=implementation_steps,
            confidence=analysis.confidence,
        )

        # Record in history
        self._decision_history.append({
            "timestamp": datetime.now().isoformat(),
            "options": [o.id for o in options],
            "recommended": recommended.id,
            "confidence": analysis.confidence,
            "decision_type": decision_type.value,
        })

        return recommendation

    async def compare_options(
        self,
        options: list[DecisionOption],
        context: DecisionContext,
    ) -> dict[str, Any]:
        """
        Compare multiple decision options side by side.

        Args:
            options: Options to compare
            context: Decision context

        Returns:
            Comparison matrix and insights
        """
        comparison = {
            "options": {},
            "matrix": {},
            "advantages": {},
            "disadvantages": {},
            "best_for_criteria": {},
        }

        # Evaluate all options
        for option in options:
            scores = await self._evaluate_option(option, context, self.default_criteria)
            comparison["options"][option.id] = {
                "name": option.name,
                "scores": scores,
                "description": option.description,
            }

        # Create comparison matrix
        criteria_names = [c.name for c in self.default_criteria]
        for criterion in criteria_names:
            comparison["matrix"][criterion] = {
                o.id: comparison["options"][o.id]["scores"].get(criterion, 0)
                for o in options
            }

        # Identify advantages and disadvantages
        for option in options:
            advantages = []
            disadvantages = []

            for criterion in self.default_criteria:
                score = comparison["options"][option.id]["scores"].get(criterion.name, 0)
                avg_score = sum(
                    comparison["options"][o.id]["scores"].get(criterion.name, 0)
                    for o in options
                ) / len(options)

                if criterion.is_cost:
                    if score < avg_score:
                        advantages.append(f"Lower {criterion.description}")
                    elif score > avg_score:
                        disadvantages.append(f"Higher {criterion.description}")
                else:
                    if score > avg_score:
                        advantages.append(f"Better {criterion.description}")
                    elif score < avg_score:
                        disadvantages.append(f"Worse {criterion.description}")

            comparison["advantages"][option.id] = advantages
            comparison["disadvantages"][option.id] = disadvantages

        # Best option for each criterion
        for criterion in criteria_names:
            is_cost = any(c.name == criterion and c.is_cost for c in self.default_criteria)
            scores = comparison["matrix"][criterion]
            if is_cost:
                best_id = min(scores.items(), key=lambda x: x[1])[0]
            else:
                best_id = max(scores.items(), key=lambda x: x[1])[0]
            comparison["best_for_criteria"][criterion] = best_id

        return comparison

    async def what_if_analysis(
        self,
        base_option: DecisionOption,
        context: DecisionContext,
        scenarios: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Perform what-if analysis on different scenarios.

        Args:
            base_option: Base decision option
            context: Decision context
            scenarios: List of scenario variations

        Returns:
            Analysis results for each scenario
        """
        results = {}

        for i, scenario in enumerate(scenarios):
            # Create modified option
            modified_option = DecisionOption(
                id=f"{base_option.id}_scenario_{i}",
                name=f"{base_option.name} (Scenario {i+1})",
                description=scenario.get("description", base_option.description),
                expected_outcome=scenario.get("expected_outcome", base_option.expected_outcome),
                resource_requirements=scenario.get(
                    "resource_requirements",
                    base_option.resource_requirements.copy()
                ),
                risk_level=scenario.get("risk_level", base_option.risk_level),
                estimated_value=scenario.get("estimated_value", base_option.estimated_value),
                constraints=scenario.get("constraints", base_option.constraints.copy()),
                metadata=scenario.get("metadata", base_option.metadata.copy()),
            )

            # Evaluate modified option
            scores = await self._evaluate_option(
                modified_option, context, self.default_criteria
            )

            results[f"scenario_{i+1}"] = {
                "description": scenario.get("description", f"Scenario {i+1}"),
                "modifications": {
                    k: v for k, v in scenario.items()
                    if k != "description" and v != getattr(base_option, k, None)
                },
                "scores": scores,
                "weighted_score": sum(
                    scores.get(c.name, 0) * c.weight
                    for c in self.default_criteria
                ) / sum(c.weight for c in self.default_criteria),
            }

        return results

    async def _evaluate_option(
        self,
        option: DecisionOption,
        context: DecisionContext,
        criteria: list[DecisionCriteria],
    ) -> dict[str, float]:
        """Evaluate an option against all criteria."""
        scores = {}

        for criterion in criteria:
            score = await self._score_criterion(option, context, criterion)
            scores[criterion.name] = score

        return scores

    async def _score_criterion(
        self,
        option: DecisionOption,
        context: DecisionContext,
        criterion: DecisionCriteria,
    ) -> float:
        """Score an option on a single criterion using LLM."""
        prompt = f"""Evaluate a decision option on the following criterion.

OPTION:
- Name: {option.name}
- Description: {option.description}
- Expected Outcome: {option.expected_outcome}
- Resource Requirements: {option.resource_requirements}
- Risk Level: {option.risk_level}
- Estimated Value: {option.estimated_value}

CONTEXT:
- Agent: {context.agent.name} (Type: {context.agent.type.value})
- Goals: {[g.name for g in context.goals]}
- Available Resources: {[(r.name, r.quantity) for r in context.resources]}
- Known Risks: {[r.name for r in context.risks]}
- Constraints: {context.constraints}

CRITERION:
- Name: {criterion.name}
- Description: {criterion.description}
- Lower is better: {criterion.is_cost}

Provide a score between 0.0 and 1.0 where:
- 1.0 = Excellent performance on this criterion
- 0.5 = Average performance
- 0.0 = Poor performance

Respond with only a single float number representing the score."""

        try:
            response = await self.llm.generate_text(prompt, temperature=0.3)
            # Extract float from response
            import re
            match = re.search(r'[\d.]+', response)
            if match:
                score = float(match.group())
                return max(0.0, min(1.0, score))
            return 0.5
        except Exception as e:
            logger.error(f"Failed to score criterion {criterion.name}: {e}")
            return 0.5

    def _normalize_scores(
        self,
        option_scores: dict[str, dict[str, float]],
        criteria: list[DecisionCriteria],
    ) -> dict[str, dict[str, float]]:
        """Normalize scores to [0, 1] range."""
        normalized = {}

        for criterion in criteria:
            # Get all scores for this criterion
            scores = [
                option_scores[opt_id][criterion.name]
                for opt_id in option_scores
            ]

            min_score = min(scores)
            max_score = max(scores)
            range_score = max_score - min_score if max_score != min_score else 1.0

            for opt_id in option_scores:
                if opt_id not in normalized:
                    normalized[opt_id] = {}

                raw_score = option_scores[opt_id][criterion.name]

                if criterion.is_cost:
                    # For cost criteria, lower is better, so invert
                    normalized[opt_id][criterion.name] = (
                        1.0 - (raw_score - min_score) / range_score
                    ) if range_score > 0 else 0.5
                else:
                    normalized[opt_id][criterion.name] = (
                        (raw_score - min_score) / range_score
                    ) if range_score > 0 else 0.5

        return normalized

    def _calculate_weighted_scores(
        self,
        normalized_scores: dict[str, dict[str, float]],
        criteria: list[DecisionCriteria],
    ) -> dict[str, float]:
        """Calculate weighted scores for each option."""
        total_weight = sum(c.weight for c in criteria)
        weighted = {}

        for opt_id in normalized_scores:
            weighted[opt_id] = sum(
                normalized_scores[opt_id].get(c.name, 0) * c.weight
                for c in criteria
            ) / total_weight

        return weighted

    async def _sensitivity_analysis(
        self,
        options: list[DecisionOption],
        context: DecisionContext,
        criteria: list[DecisionCriteria],
        current_rankings: dict[str, float],
    ) -> dict[str, Any]:
        """Perform sensitivity analysis on criteria weights."""
        sensitivity = {
            "critical_criteria": [],
            "ranking_changes": {},
            "threshold_weights": {},
        }

        # Test weight variations
        for criterion in criteria:
            # Save original weight
            original_weight = criterion.weight

            # Test weight changes
            for delta in [-0.3, -0.1, 0.1, 0.3]:
                criterion.weight = max(0.1, original_weight + delta)

                # Recalculate rankings
                await self._evaluate_option(
                    options[0], context, criteria
                ) if options else {}

                # Check for ranking changes
                # (simplified - in practice would recalculate all)

            # Restore original weight
            criterion.weight = original_weight

        return sensitivity

    def _identify_tradeoffs(
        self,
        option_scores: dict[str, dict[str, float]],
        criteria: list[DecisionCriteria],
        rankings: list[tuple[str, float]],
    ) -> list[dict[str, Any]]:
        """Identify tradeoffs between options."""
        tradeoffs = []

        if len(rankings) < 2:
            return tradeoffs

        top_id = rankings[0][0]
        second_id = rankings[1][0]

        top_scores = option_scores[top_id]
        second_scores = option_scores[second_id]

        for criterion in criteria:
            diff = top_scores.get(criterion.name, 0) - second_scores.get(criterion.name, 0)

            if abs(diff) > 0.2:  # Significant difference
                tradeoffs.append({
                    "criterion": criterion.name,
                    "top_option_score": top_scores.get(criterion.name, 0),
                    "second_option_score": second_scores.get(criterion.name, 0),
                    "difference": diff,
                    "description": f"Top option {'wins' if diff > 0 else 'loses'} on {criterion.description}",
                })

        return tradeoffs

    def _calculate_confidence(
        self,
        option_scores: dict[str, dict[str, float]],
        rankings: list[tuple[str, float]],
    ) -> float:
        """Calculate overall confidence in the recommendation."""
        if len(rankings) < 2:
            return 0.7

        # Confidence based on margin between top and second option
        margin = rankings[0][1] - rankings[1][1]

        # Base confidence on margin (larger margin = higher confidence)
        confidence = 0.5 + min(0.5, margin * 2)

        return confidence

    async def _generate_analysis_reasoning(
        self,
        options: list[DecisionOption],
        rankings: list[tuple[str, float]],
        option_scores: dict[str, dict[str, float]],
        criteria: list[DecisionCriteria],
        context: DecisionContext,
    ) -> str:
        """Generate human-readable reasoning for the analysis."""
        top_option = next((o for o in options if o.id == rankings[0][0]), None)

        prompt = f"""Summarize the decision analysis results.

TOP OPTION: {top_option.name if top_option else 'Unknown'}
SCORE: {rankings[0][1]:.3f}

ALL OPTIONS AND SCORES:
{chr(10).join(f'- {o.name}: {rankings[i][1]:.3f}' for i, o in enumerate(options) if i < len(rankings))}

CRITERIA SCORES FOR TOP OPTION:
{chr(10).join(f'- {c.name}: {option_scores.get(rankings[0][0], {}).get(c.name, 0):.3f}' for c in criteria)}

CONTEXT:
- Agent: {context.agent.name}
- Primary Goal: {context.goals[0].name if context.goals else 'None'}

Provide a brief (2-3 sentences) explanation of why the top option was recommended."""

        try:
            return await self.llm.generate_text(prompt, temperature=0.5)
        except Exception as e:
            logger.error(f"Failed to generate reasoning: {e}")
            return f"Option {top_option.name if top_option else 'Unknown'} ranked highest based on weighted criteria analysis."

    async def _generate_rationale(
        self,
        recommended: DecisionOption,
        alternatives: list[DecisionOption],
        analysis: DecisionAnalysis,
        context: DecisionContext,
    ) -> str:
        """Generate detailed rationale for the recommendation."""
        prompt = f"""Generate a detailed rationale for a decision recommendation.

RECOMMENDED OPTION:
- Name: {recommended.name}
- Description: {recommended.description}
- Expected Outcome: {recommended.expected_outcome}
- Risk Level: {recommended.risk_level}
- Estimated Value: {recommended.estimated_value}

ALTERNATIVES:
{chr(10).join(f'- {a.name}: {a.description[:100]}' for a in alternatives[:3])}

ANALYSIS RESULTS:
- Confidence: {analysis.confidence:.2%}
- Key Tradeoffs: {[t['description'] for t in analysis.tradeoffs[:3]]}

CONTEXT:
- Agent Goals: {[g.name for g in context.goals]}
- Available Resources: {[(r.name, r.quantity) for r in context.resources]}

Provide a detailed rationale (3-5 sentences) explaining why this option is recommended."""

        try:
            return await self.llm.generate_text(prompt, temperature=0.5)
        except Exception as e:
            logger.error(f"Failed to generate rationale: {e}")
            return f"{recommended.name} is recommended based on multi-criteria analysis."

    async def _predict_outcome(
        self,
        option: DecisionOption,
        context: DecisionContext,
    ) -> str:
        """Predict the outcome of executing the recommended option."""
        prompt = f"""Predict the outcome of implementing this decision.

OPTION: {option.name}
Description: {option.description}
Expected Value: {option.estimated_value}
Risk Level: {option.risk_level}

AGENT CONTEXT:
- Name: {context.agent.name}
- Capabilities: {context.agent.capabilities}
- Goals: {[g.name for g in context.goals]}

RESOURCES AVAILABLE:
{chr(10).join(f'- {r.name}: {r.quantity}' for r in context.resources)}

Provide a brief prediction (1-2 sentences) of the likely outcome."""

        try:
            return await self.llm.generate_text(prompt, temperature=0.6)
        except Exception as e:
            logger.error(f"Failed to predict outcome: {e}")
            return option.expected_outcome

    async def _assess_risks(
        self,
        option: DecisionOption,
        context: DecisionContext,
    ) -> dict[str, Any]:
        """Assess risks associated with the recommended option."""
        prompt = f"""Assess the risks of implementing this decision.

OPTION: {option.name}
Description: {option.description}
Base Risk Level: {option.risk_level}

KNOWN RISKS:
{chr(10).join(f'- {r.name}: {r.description} (Probability: {r.probability}, Impact: {r.impact})' for r in context.risks[:5])}

CONSTRAINTS:
{chr(10).join(f'- {k}: {v}' for k, v in context.constraints.items())}

Provide a risk assessment in JSON format with keys:
- overall_risk_level (float 0-1)
- key_risks (list of strings)
- mitigation_strategies (list of strings)
- monitoring_points (list of strings)"""

        try:
            response = await self.llm.generate_text(prompt, temperature=0.5)
            import json
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return {"overall_risk_level": option.risk_level, "key_risks": [], "mitigation_strategies": []}
        except Exception as e:
            logger.error(f"Failed to assess risks: {e}")
            return {"overall_risk_level": option.risk_level, "key_risks": [], "mitigation_strategies": []}

    async def _generate_implementation_steps(
        self,
        option: DecisionOption,
        context: DecisionContext,
    ) -> list[str]:
        """Generate implementation steps for the recommended option."""
        prompt = f"""Generate implementation steps for this decision.

OPTION: {option.name}
Description: {option.description}
Expected Outcome: {option.expected_outcome}

AGENT:
- Name: {context.agent.name}
- Capabilities: {context.agent.capabilities}

RESOURCES AVAILABLE:
{chr(10).join(f'- {r.name}: {r.quantity}' for r in context.resources)}

Provide 3-7 implementation steps as a JSON list of strings."""

        try:
            response = await self.llm.generate_text(prompt, temperature=0.5)
            import json
            import re
            json_match = re.search(r'\[[\s\S]*?\]', response)
            if json_match:
                steps = json.loads(json_match.group())
                return steps if isinstance(steps, list) else [str(steps)]
            return ["Execute according to plan"]
        except Exception as e:
            logger.error(f"Failed to generate implementation steps: {e}")
            return ["Execute according to plan"]

    def get_decision_history(self) -> list[dict[str, Any]]:
        """Get the history of decisions made."""
        return self._decision_history.copy()

    def clear_history(self) -> None:
        """Clear the decision history."""
        self._decision_history.clear()
