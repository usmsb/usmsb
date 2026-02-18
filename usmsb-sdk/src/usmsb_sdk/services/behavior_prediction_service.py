"""
Behavior Prediction Service

Service for predicting agent behaviors, system evolution trends,
and potential outcomes based on USMSB model elements.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from usmsb_sdk.core.elements import Agent, Environment, Goal, Information
from usmsb_sdk.intelligence_adapters.base import ILLMAdapter

logger = logging.getLogger(__name__)


@dataclass
class BehaviorPrediction:
    """Result of a behavior prediction."""
    predicted_actions: List[Dict[str, Any]]
    confidence: float
    reasoning: str
    alternative_scenarios: List[Dict[str, Any]] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class SystemEvolutionPrediction:
    """Result of a system evolution prediction."""
    predicted_state: Dict[str, Any]
    timeline: List[Dict[str, Any]]
    key_drivers: List[str]
    confidence: float
    assumptions: List[str]
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class BehaviorPredictionService:
    """
    Behavior Prediction Service.

    Uses LLM and USMSB model to predict:
    - Individual agent behavior
    - Multi-agent system evolution
    - Emergent patterns
    - Risk assessment
    """

    def __init__(
        self,
        llm_adapter: ILLMAdapter,
        confidence_threshold: float = 0.7,
    ):
        """
        Initialize the Behavior Prediction Service.

        Args:
            llm_adapter: LLM adapter for reasoning
            confidence_threshold: Minimum confidence for predictions
        """
        self.llm = llm_adapter
        self.confidence_threshold = confidence_threshold

    async def predict_agent_behavior(
        self,
        agent: Agent,
        environment: Environment,
        goal: Optional[Goal] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> BehaviorPrediction:
        """
        Predict an agent's behavior.

        Args:
            agent: The agent to predict
            environment: Current environment
            goal: Target goal (uses highest priority if None)
            context: Additional context

        Returns:
            BehaviorPrediction with predicted actions
        """
        if goal is None:
            goal = agent.get_highest_priority_goal()
            if goal is None:
                raise ValueError("No goal specified and no active goals found")

        # Build prediction prompt
        prompt = self._build_behavior_prediction_prompt(agent, environment, goal)

        try:
            # Get LLM prediction
            response = await self.llm.generate_with_system(
                system_prompt=self._get_system_prompt(),
                user_prompt=prompt,
                context=context,
            )

            # Parse response
            prediction = await self._parse_prediction_response(response)

            return prediction

        except Exception as e:
            logger.error(f"Behavior prediction failed: {e}")
            # Return low-confidence fallback prediction
            return BehaviorPrediction(
                predicted_actions=[],
                confidence=0.0,
                reasoning=f"Prediction failed: {str(e)}",
                risk_factors=["prediction_error"],
            )

    async def predict_system_evolution(
        self,
        agents: List[Agent],
        environment: Environment,
        time_horizon: int = 10,
        context: Optional[Dict[str, Any]] = None,
    ) -> SystemEvolutionPrediction:
        """
        Predict how a multi-agent system will evolve.

        Args:
            agents: List of agents in the system
            environment: Current environment
            time_horizon: Number of time steps to predict
            context: Additional context

        Returns:
            SystemEvolutionPrediction with timeline
        """
        prompt = self._build_evolution_prediction_prompt(agents, environment, time_horizon)

        try:
            response = await self.llm.generate_with_system(
                system_prompt=self._get_system_prompt(),
                user_prompt=prompt,
                context=context,
            )

            prediction = await self._parse_evolution_response(response, time_horizon)
            return prediction

        except Exception as e:
            logger.error(f"System evolution prediction failed: {e}")
            return SystemEvolutionPrediction(
                predicted_state={},
                timeline=[],
                key_drivers=[],
                confidence=0.0,
                assumptions=[f"Prediction failed: {str(e)}"],
            )

    async def analyze_behavior_patterns(
        self,
        historical_data: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze patterns in historical behavior data.

        Args:
            historical_data: List of historical behavior records
            context: Additional context

        Returns:
            Analysis results with identified patterns
        """
        if not historical_data:
            return {"patterns": [], "insights": "No historical data provided"}

        prompt = f"""Analyze the following historical behavior data and identify:
1. Recurring patterns
2. Trends over time
3. Anomalies
4. Key drivers of behavior

Historical data (sample):
{self._format_historical_data(historical_data[:20])}

Provide your analysis in JSON format with keys: patterns (list), trends (list), anomalies (list), drivers (list), insights (string)."""

        try:
            response = await self.llm.generate_text(
                prompt,
                context=context,
                temperature=0.5,
            )
            return await self._parse_json_response(response)
        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            return {"patterns": [], "insights": f"Analysis failed: {str(e)}"}

    async def predict_interaction_outcome(
        self,
        agent1: Agent,
        agent2: Agent,
        interaction_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Predict the outcome of an interaction between two agents.

        Args:
            agent1: First agent
            agent2: Second agent
            interaction_type: Type of interaction (negotiate, collaborate, compete, etc.)
            context: Additional context

        Returns:
            Predicted outcome
        """
        prompt = f"""Predict the outcome of an interaction between two agents.

Agent 1: {agent1.name} (Type: {agent1.type.value})
- Capabilities: {agent1.capabilities}
- Active Goals: {[g.name for g in agent1.get_active_goals()]}

Agent 2: {agent2.name} (Type: {agent2.type.value})
- Capabilities: {agent2.capabilities}
- Active Goals: {[g.name for g in agent2.get_active_goals()]}

Interaction Type: {interaction_type}

Predict:
1. Likely outcome
2. Each agent's strategy
3. Potential conflicts
4. Synergies
5. Confidence level

Respond in JSON format."""

        try:
            response = await self.llm.generate_text(prompt, context=context, temperature=0.6)
            return await self._parse_json_response(response)
        except Exception as e:
            logger.error(f"Interaction prediction failed: {e}")
            return {"outcome": "unknown", "error": str(e)}

    def _get_system_prompt(self) -> str:
        """Get the system prompt for behavior prediction."""
        return """You are an expert behavior prediction system based on the USMSB (Universal System Model of Social Behavior) framework.

Your role is to:
1. Analyze agent characteristics, goals, resources, and constraints
2. Consider environmental factors and rules
3. Predict likely behaviors and actions
4. Identify risks and alternative scenarios
5. Provide confidence levels for predictions

Always provide structured, well-reasoned predictions in JSON format."""

    def _build_behavior_prediction_prompt(
        self,
        agent: Agent,
        environment: Environment,
        goal: Goal,
    ) -> str:
        """Build the prompt for behavior prediction."""
        return f"""Predict the behavior of an agent working towards a goal.

AGENT PROFILE:
- Name: {agent.name}
- Type: {agent.type.value}
- Capabilities: {agent.capabilities}
- Current State: {agent.state}

GOAL:
- Name: {goal.name}
- Description: {goal.description}
- Priority: {goal.priority}
- Status: {goal.status.value}

ENVIRONMENT:
- Type: {environment.type.value}
- Current State: {environment.state}
- Constraints: {environment.constraints}

AVAILABLE RESOURCES:
{self._format_resources(agent.resources)}

APPLICABLE RULES:
{self._format_rules(agent.rules)}

Based on the USMSB model, predict:
1. The most likely sequence of actions the agent will take
2. Confidence in this prediction (0.0 to 1.0)
3. Reasoning for the prediction
4. Alternative scenarios
5. Risk factors

Respond in JSON format with keys: predicted_actions (list), confidence (float), reasoning (string), alternative_scenarios (list), risk_factors (list)."""

    def _build_evolution_prediction_prompt(
        self,
        agents: List[Agent],
        environment: Environment,
        time_horizon: int,
    ) -> str:
        """Build the prompt for system evolution prediction."""
        agent_summaries = [
            f"- {a.name} ({a.type.value}): Goals={[g.name for g in a.get_active_goals()]}"
            for a in agents
        ]

        return f"""Predict how a multi-agent system will evolve over {time_horizon} time steps.

AGENTS IN SYSTEM:
{chr(10).join(agent_summaries)}

ENVIRONMENT:
- Type: {environment.type.value}
- State: {environment.state}

Predict:
1. System state at each time step
2. Key drivers of evolution
3. Emergent behaviors
4. Confidence level
5. Key assumptions

Respond in JSON format with keys: predicted_state (object), timeline (list of {time_horizon} steps), key_drivers (list), confidence (float), assumptions (list)."""

    def _format_resources(self, resources) -> str:
        """Format resources for prompt."""
        if not resources:
            return "No resources available"
        return "\n".join([
            f"- {r.name}: {r.quantity} {r.unit or ''} ({r.type.value})"
            for r in resources
        ])

    def _format_rules(self, rules) -> str:
        """Format rules for prompt."""
        if not rules:
            return "No rules defined"
        return "\n".join([
            f"- {r.name}: {r.description[:100]}..." if len(r.description) > 100
            else f"- {r.name}: {r.description}"
            for r in rules[:5]  # Limit to 5 rules
        ])

    def _format_historical_data(self, data: List[Dict]) -> str:
        """Format historical data for prompt."""
        import json
        return json.dumps(data, indent=2, default=str)[:2000]  # Limit length

    async def _parse_prediction_response(self, response: str) -> BehaviorPrediction:
        """Parse LLM response into BehaviorPrediction."""
        parsed = await self._parse_json_response(response)

        return BehaviorPrediction(
            predicted_actions=parsed.get("predicted_actions", []),
            confidence=float(parsed.get("confidence", 0.5)),
            reasoning=parsed.get("reasoning", ""),
            alternative_scenarios=parsed.get("alternative_scenarios", []),
            risk_factors=parsed.get("risk_factors", []),
        )

    async def _parse_evolution_response(
        self,
        response: str,
        time_horizon: int
    ) -> SystemEvolutionPrediction:
        """Parse LLM response into SystemEvolutionPrediction."""
        parsed = await self._parse_json_response(response)

        return SystemEvolutionPrediction(
            predicted_state=parsed.get("predicted_state", {}),
            timeline=parsed.get("timeline", []),
            key_drivers=parsed.get("key_drivers", []),
            confidence=float(parsed.get("confidence", 0.5)),
            assumptions=parsed.get("assumptions", []),
        )

    async def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        import json
        try:
            # Try direct parse
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            return {}
