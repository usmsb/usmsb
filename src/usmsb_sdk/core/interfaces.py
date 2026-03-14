"""
USMSB Universal Action Interfaces

This module defines the 9 universal action interfaces of the USMSB model:
- IPerceptionService: From environment acquire and understand information
- IDecisionService: Choose action plans based on goals, rules, information
- IExecutionService: Implement decisions, transform abstract actions to concrete operations
- IInteractionService: Information exchange between agents or agent-environment
- ITransformationService: Transform resource forms, data formats
- IEvaluationService: Measure alignment of results with goals
- IFeedbackService: Process evaluation results as input for adjustments
- ILearningService: Acquire knowledge from experience, optimize behavior
- IRiskManagementService: Identify, assess, avoid, and mitigate risks
"""

from abc import ABC, abstractmethod
from typing import Any

from usmsb_sdk.core.elements import (
    Agent,
    Environment,
    Goal,
    Information,
    Resource,
    Risk,
    Value,
)


class IPerceptionService(ABC):
    """
    Perception Service Interface.

    Provides perception capabilities such as text understanding,
    image recognition, data analysis, and environment sensing.
    """

    @abstractmethod
    async def perceive(
        self,
        input_data: Any,
        context: dict[str, Any] | None = None
    ) -> Information:
        """
        Perceive and process input data.

        Args:
            input_data: Raw input data (text, image, sensor data, etc.)
            context: Optional context for perception

        Returns:
            Information: Processed information object
        """
        pass

    @abstractmethod
    async def batch_perceive(
        self,
        input_list: list[Any],
        context: dict[str, Any] | None = None
    ) -> list[Information]:
        """
        Process multiple inputs in batch.

        Args:
            input_list: List of raw input data
            context: Optional context for perception

        Returns:
            List[Information]: List of processed information objects
        """
        pass


class IDecisionService(ABC):
    """
    Decision Service Interface.

    Provides decision-making capabilities such as action selection,
    strategy generation, and path planning.
    """

    @abstractmethod
    async def decide(
        self,
        agent: Agent,
        goal: Goal,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Make a decision for the agent towards a goal.

        Args:
            agent: The agent making the decision
            goal: The target goal
            context: Additional context for decision-making

        Returns:
            Dict containing decision details:
                - action: The decided action
                - reasoning: Explanation of the decision
                - alternatives: Alternative actions considered
                - confidence: Decision confidence (0.0 to 1.0)
                - required_resources: Resources needed
                - expected_outcome: Predicted outcome
        """
        pass

    @abstractmethod
    async def plan_actions(
        self,
        agent: Agent,
        goal: Goal,
        constraints: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Generate a sequence of actions to achieve a goal.

        Args:
            agent: The agent planning actions
            goal: The target goal
            constraints: Constraints on the plan

        Returns:
            List of action dictionaries in execution order
        """
        pass


class IExecutionService(ABC):
    """
    Execution Service Interface.

    Provides execution capabilities such as code execution,
    API calls, and simulated operations.
    """

    @abstractmethod
    async def execute(
        self,
        action: dict[str, Any],
        agent: Agent,
        context: dict[str, Any] | None = None
    ) -> Any:
        """
        Execute an action.

        Args:
            action: The action to execute
            agent: The agent executing the action
            context: Additional context for execution

        Returns:
            Execution result
        """
        pass

    @abstractmethod
    async def execute_sequence(
        self,
        actions: list[dict[str, Any]],
        agent: Agent,
        context: dict[str, Any] | None = None
    ) -> list[Any]:
        """
        Execute a sequence of actions.

        Args:
            actions: List of actions to execute
            agent: The agent executing the actions
            context: Additional context for execution

        Returns:
            List of execution results
        """
        pass

    @abstractmethod
    async def execute_tool(
        self,
        tool_name: str,
        params: dict[str, Any],
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Execute a specific tool.

        Args:
            tool_name: Name of the tool to execute
            params: Parameters for the tool
            context: Additional context

        Returns:
            Tool execution result
        """
        pass


class IInteractionService(ABC):
    """
    Interaction Service Interface.

    Provides interaction capabilities for multi-agent communication,
    human-machine dialogue, and environment interaction.
    """

    @abstractmethod
    async def interact(
        self,
        sender: Agent,
        receiver: Agent,
        message: Any,
        context: dict[str, Any] | None = None
    ) -> Any:
        """
        Facilitate interaction between two agents.

        Args:
            sender: The agent sending the message
            receiver: The agent receiving the message
            message: The message content
            context: Additional context

        Returns:
            Response from the receiver
        """
        pass

    @abstractmethod
    async def broadcast(
        self,
        sender: Agent,
        receivers: list[Agent],
        message: Any,
        context: dict[str, Any] | None = None
    ) -> list[Any]:
        """
        Broadcast a message to multiple agents.

        Args:
            sender: The agent sending the message
            receivers: List of receiving agents
            message: The message content
            context: Additional context

        Returns:
            List of responses from receivers
        """
        pass

    @abstractmethod
    async def negotiate(
        self,
        agents: list[Agent],
        topic: str,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Facilitate negotiation between agents.

        Args:
            agents: Agents participating in negotiation
            topic: Topic of negotiation
            context: Additional context

        Returns:
            Negotiation result
        """
        pass


class ITransformationService(ABC):
    """
    Transformation Service Interface.

    Provides transformation capabilities for resource form changes,
    data format conversions, and value addition processes.
    """

    @abstractmethod
    async def transform(
        self,
        input_data: Any,
        target_type: str,
        context: dict[str, Any] | None = None
    ) -> Any:
        """
        Transform input to target type.

        Args:
            input_data: Data to transform
            target_type: Target type/format
            context: Additional context

        Returns:
            Transformed data
        """
        pass

    @abstractmethod
    async def transform_resource(
        self,
        resource: Resource,
        target_type: str,
        agent: Agent,
        context: dict[str, Any] | None = None
    ) -> Resource:
        """
        Transform a resource to a different form.

        Args:
            resource: Resource to transform
            target_type: Target resource type
            agent: Agent performing transformation
            context: Additional context

        Returns:
            Transformed resource
        """
        pass


class IEvaluationService(ABC):
    """
    Evaluation Service Interface.

    Provides evaluation capabilities for measuring effectiveness,
    assessing value, and calculating risk.
    """

    @abstractmethod
    async def evaluate(
        self,
        item: Any,
        criteria: str,
        context: dict[str, Any] | None = None
    ) -> Value:
        """
        Evaluate an item against criteria.

        Args:
            item: Item to evaluate
            criteria: Evaluation criteria
            context: Additional context

        Returns:
            Value object representing evaluation result
        """
        pass

    @abstractmethod
    async def evaluate_goal_progress(
        self,
        agent: Agent,
        goal: Goal,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Evaluate progress towards a goal.

        Args:
            agent: The agent
            goal: The goal to evaluate
            context: Additional context

        Returns:
            Dict containing:
                - progress: Progress percentage (0.0 to 1.0)
                - metrics: Key metrics
                - blockers: Identified blockers
                - recommendations: Improvement recommendations
        """
        pass

    @abstractmethod
    async def evaluate_action_outcome(
        self,
        action: dict[str, Any],
        outcome: Any,
        goal: Goal,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Evaluate the outcome of an action.

        Args:
            action: The executed action
            outcome: The action outcome
            goal: Related goal
            context: Additional context

        Returns:
            Evaluation result
        """
        pass


class IFeedbackService(ABC):
    """
    Feedback Service Interface.

    Provides feedback processing capabilities for user feedback analysis,
    system adaptive adjustment, and learning feedback loops.
    """

    @abstractmethod
    async def process_feedback(
        self,
        feedback_data: Any,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Process feedback data.

        Args:
            feedback_data: Raw feedback data
            context: Additional context

        Returns:
            Processed feedback with:
                - sentiment: Feedback sentiment
                - key_points: Extracted key points
                - action_items: Suggested actions
                - priority: Priority level
        """
        pass

    @abstractmethod
    async def generate_feedback(
        self,
        agent: Agent,
        action: dict[str, Any],
        outcome: Any,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Generate feedback for an agent action.

        Args:
            agent: The agent
            action: The action taken
            outcome: The outcome
            context: Additional context

        Returns:
            Generated feedback
        """
        pass


class ILearningService(ABC):
    """
    Learning Service Interface.

    Provides learning capabilities for model fine-tuning,
    knowledge updates, and behavior optimization.
    """

    @abstractmethod
    async def learn(
        self,
        experience_data: Any,
        agent: Agent,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Learn from experience data.

        Args:
            experience_data: Data from experiences
            agent: The agent learning
            context: Additional context

        Returns:
            Learning result with:
                - knowledge_gained: New knowledge acquired
                - behavior_adjustments: Suggested behavior changes
                - confidence: Learning confidence
        """
        pass

    @abstractmethod
    async def update_knowledge(
        self,
        agent: Agent,
        new_knowledge: dict[str, Any],
        context: dict[str, Any] | None = None
    ) -> bool:
        """
        Update agent's knowledge base.

        Args:
            agent: The agent
            new_knowledge: New knowledge to add
            context: Additional context

        Returns:
            Success status
        """
        pass

    @abstractmethod
    async def optimize_behavior(
        self,
        agent: Agent,
        performance_metrics: dict[str, Any],
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Optimize agent behavior based on metrics.

        Args:
            agent: The agent
            performance_metrics: Performance data
            context: Additional context

        Returns:
            Optimization result with suggested changes
        """
        pass


class IRiskManagementService(ABC):
    """
    Risk Management Service Interface.

    Provides risk management capabilities for risk identification,
    assessment, avoidance, and mitigation.
    """

    @abstractmethod
    async def identify_risks(
        self,
        context: dict[str, Any]
    ) -> list[Risk]:
        """
        Identify potential risks in a context.

        Args:
            context: Context to analyze for risks

        Returns:
            List of identified risks
        """
        pass

    @abstractmethod
    async def assess_risk(
        self,
        risk: Risk,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Assess a risk's probability and impact.

        Args:
            risk: Risk to assess
            context: Additional context

        Returns:
            Assessment result with probability, impact, severity
        """
        pass

    @abstractmethod
    async def manage_risk(
        self,
        risk: Risk,
        agent: Agent,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Manage a risk (mitigate, transfer, accept, or avoid).

        Args:
            risk: Risk to manage
            agent: Agent managing the risk
            context: Additional context

        Returns:
            Management result with chosen strategy and actions
        """
        pass

    @abstractmethod
    async def monitor_risks(
        self,
        agent: Agent,
        environment: Environment,
        context: dict[str, Any] | None = None
    ) -> list[Risk]:
        """
        Monitor for new and changing risks.

        Args:
            agent: Agent to monitor for
            environment: Current environment
            context: Additional context

        Returns:
            List of current risks
        """
        pass
