"""
Goal-Action-Outcome Loop Engine

The Goal-Action-Outcome Loop is the primary driver of agent behavior in USMSB.
It implements the continuous cycle of:
1. Goal Selection: Identify the highest priority goal
2. Action Planning: Generate actions to achieve the goal
3. Action Execution: Execute the planned actions
4. Outcome Evaluation: Assess the results
5. Feedback Processing: Learn and adjust for next iteration
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from usmsb_sdk.core.elements import Agent, Goal, GoalStatus, Information, Value
from usmsb_sdk.core.interfaces import (
    IDecisionService,
    IEvaluationService,
    IExecutionService,
    IFeedbackService,
    IPerceptionService,
)

logger = logging.getLogger(__name__)


class LoopStatus(str, Enum):
    """Status of the Goal-Action-Outcome loop."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ActionResult:
    """Result of an action execution."""
    action_id: str
    action_type: str
    success: bool
    outcome: Any
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoopIteration:
    """Record of a single loop iteration."""
    iteration_number: int
    goal: Goal
    selected_action: Dict[str, Any]
    execution_result: ActionResult
    evaluation_result: Dict[str, Any]
    feedback: Dict[str, Any]
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class GoalActionOutcomeLoop:
    """
    Goal-Action-Outcome Loop Engine.

    This engine drives agent behavior through a continuous cycle of
    goal selection, action planning, execution, evaluation, and learning.
    """

    def __init__(
        self,
        perception_service: IPerceptionService,
        decision_service: IDecisionService,
        execution_service: IExecutionService,
        evaluation_service: IEvaluationService,
        feedback_service: IFeedbackService,
        max_iterations: int = 100,
        iteration_delay: float = 0.1,
        decision_timeout: float = 30.0,
        execution_timeout: float = 60.0,
        evaluation_timeout: float = 30.0,
        feedback_timeout: float = 30.0,
    ):
        """
        Initialize the Goal-Action-Outcome Loop.

        Args:
            perception_service: Service for perception operations
            decision_service: Service for decision-making
            execution_service: Service for action execution
            evaluation_service: Service for outcome evaluation
            feedback_service: Service for feedback processing
            max_iterations: Maximum loop iterations before stopping
            iteration_delay: Delay between iterations in seconds
            decision_timeout: Timeout for decision service calls in seconds
            execution_timeout: Timeout for execution service calls in seconds
            evaluation_timeout: Timeout for evaluation service calls in seconds
            feedback_timeout: Timeout for feedback service calls in seconds
        """
        self.perception_service = perception_service
        self.decision_service = decision_service
        self.execution_service = execution_service
        self.evaluation_service = evaluation_service
        self.feedback_service = feedback_service

        self.max_iterations = max_iterations
        self.iteration_delay = iteration_delay
        self.decision_timeout = decision_timeout
        self.execution_timeout = execution_timeout
        self.evaluation_timeout = evaluation_timeout
        self.feedback_timeout = feedback_timeout

        self.status = LoopStatus.IDLE
        self.current_iteration = 0
        self.iteration_history: List[LoopIteration] = []
        self._stop_flag = False
        self._pause_flag = False

        # Callbacks for hooks
        self.on_goal_selected: Optional[Callable[[Goal], None]] = None
        self.on_action_planned: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_action_executed: Optional[Callable[[ActionResult], None]] = None
        self.on_evaluation_complete: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_feedback_processed: Optional[Callable[[Dict[str, Any]], None]] = None

    async def run(
        self,
        agent: Agent,
        environment: Any = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run the Goal-Action-Outcome loop for an agent.

        Args:
            agent: The agent to run the loop for
            environment: The environment context
            context: Additional context

        Returns:
            Summary of the loop execution
        """
        self.status = LoopStatus.RUNNING
        self._stop_flag = False
        self.current_iteration = 0
        self.iteration_history.clear()

        context = context or {}

        try:
            while not self._stop_flag and self.current_iteration < self.max_iterations:
                # Handle pause
                while self._pause_flag and not self._stop_flag:
                    await asyncio.sleep(0.1)

                if self._stop_flag:
                    break

                # Run single iteration
                iteration_result = await self._run_iteration(agent, environment, context)
                self.iteration_history.append(iteration_result)
                self.current_iteration += 1

                # Check if all goals are achieved
                active_goals = agent.get_active_goals()
                if not active_goals:
                    logger.info(f"All goals achieved for agent {agent.id}")
                    self.status = LoopStatus.COMPLETED
                    break

                # Delay between iterations
                if self.iteration_delay > 0:
                    await asyncio.sleep(self.iteration_delay)

            if self.status == LoopStatus.RUNNING:
                self.status = LoopStatus.COMPLETED if not self._stop_flag else LoopStatus.IDLE

        except Exception as e:
            logger.error(f"Error in Goal-Action-Outcome loop: {e}")
            self.status = LoopStatus.FAILED
            raise

        return self._generate_summary(agent)

    async def _run_iteration(
        self,
        agent: Agent,
        environment: Any,
        context: Dict[str, Any],
    ) -> LoopIteration:
        """Run a single iteration of the loop."""
        logger.debug(f"Starting iteration {self.current_iteration + 1}")

        # Step 1: Select Goal
        goal = agent.get_highest_priority_goal()
        if not goal:
            raise ValueError("No active goals to pursue")

        goal.status = GoalStatus.IN_PROGRESS
        if self.on_goal_selected:
            self.on_goal_selected(goal)

        logger.debug(f"Selected goal: {goal.name}")

        # Step 2: Perceive current state
        perception_context = {
            **context,
            "environment": environment,
            "agent_state": agent.state,
        }
        # Get current information from environment
        # perception = await self.perception_service.perceive(environment, perception_context)

        # Step 3: Decide on action (with timeout)
        decision_context = {
            **context,
            "environment": environment,
            "iteration": self.current_iteration,
        }
        try:
            decision = await asyncio.wait_for(
                self.decision_service.decide(agent, goal, decision_context),
                timeout=self.decision_timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Decision service timed out after {self.decision_timeout}s")
            raise TimeoutError(f"Decision service timed out after {self.decision_timeout}s")
        selected_action = decision.get("action", {})

        if self.on_action_planned:
            self.on_action_planned(selected_action)

        logger.debug(f"Selected action: {selected_action.get('type', 'unknown')}")

        # Step 4: Execute action (with timeout)
        execution_context = {
            **context,
            "decision": decision,
        }
        try:
            outcome = await asyncio.wait_for(
                self.execution_service.execute(
                    selected_action, agent, execution_context
                ),
                timeout=self.execution_timeout
            )
            action_result = ActionResult(
                action_id=selected_action.get("id", "unknown"),
                action_type=selected_action.get("type", "unknown"),
                success=True,
                outcome=outcome,
            )
        except asyncio.TimeoutError:
            logger.error(f"Execution service timed out after {self.execution_timeout}s")
            action_result = ActionResult(
                action_id=selected_action.get("id", "unknown"),
                action_type=selected_action.get("type", "unknown"),
                success=False,
                outcome=None,
                error=f"Execution timed out after {self.execution_timeout}s",
            )
        except Exception as e:
            action_result = ActionResult(
                action_id=selected_action.get("id", "unknown"),
                action_type=selected_action.get("type", "unknown"),
                success=False,
                outcome=None,
                error=str(e),
            )

        if self.on_action_executed:
            self.on_action_executed(action_result)

        # Step 5: Evaluate outcome (with timeout)
        try:
            evaluation = await asyncio.wait_for(
                self.evaluation_service.evaluate_action_outcome(
                    selected_action, action_result.outcome, goal, context
                ),
                timeout=self.evaluation_timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Evaluation service timed out after {self.evaluation_timeout}s")
            evaluation = {"goal_achieved": False, "error": "Evaluation timed out"}

        if self.on_evaluation_complete:
            self.on_evaluation_complete(evaluation)

        # Check if goal is achieved
        if evaluation.get("goal_achieved", False):
            goal.update_status(GoalStatus.COMPLETED)
            logger.info(f"Goal '{goal.name}' achieved!")

        # Step 6: Process feedback (with timeout)
        try:
            feedback = await asyncio.wait_for(
                self.feedback_service.generate_feedback(
                    agent, selected_action, action_result.outcome, context
                ),
                timeout=self.feedback_timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Feedback service timed out after {self.feedback_timeout}s")
            feedback = {"error": "Feedback generation timed out"}

        if self.on_feedback_processed:
            self.on_feedback_processed(feedback)

        return LoopIteration(
            iteration_number=self.current_iteration,
            goal=goal,
            selected_action=selected_action,
            execution_result=action_result,
            evaluation_result=evaluation,
            feedback=feedback,
        )

    def pause(self) -> None:
        """Pause the loop execution."""
        self._pause_flag = True
        self.status = LoopStatus.PAUSED
        logger.info("Goal-Action-Outcome loop paused")

    def resume(self) -> None:
        """Resume the loop execution."""
        self._pause_flag = False
        self.status = LoopStatus.RUNNING
        logger.info("Goal-Action-Outcome loop resumed")

    def stop(self) -> None:
        """Stop the loop execution."""
        self._stop_flag = True
        self.status = LoopStatus.IDLE
        logger.info("Goal-Action-Outcome loop stopped")

    def _generate_summary(self, agent: Agent) -> Dict[str, Any]:
        """Generate a summary of the loop execution."""
        completed_goals = [g for g in agent.goals if g.status == GoalStatus.COMPLETED]
        failed_goals = [g for g in agent.goals if g.status == GoalStatus.FAILED]
        pending_goals = [g for g in agent.goals if g.status == GoalStatus.PENDING]
        in_progress_goals = [g for g in agent.goals if g.status == GoalStatus.IN_PROGRESS]

        successful_actions = sum(
            1 for i in self.iteration_history if i.execution_result.success
        )
        failed_actions = len(self.iteration_history) - successful_actions

        return {
            "status": self.status.value,
            "total_iterations": self.current_iteration,
            "goals_summary": {
                "total": len(agent.goals),
                "completed": len(completed_goals),
                "failed": len(failed_goals),
                "pending": len(pending_goals),
                "in_progress": len(in_progress_goals),
            },
            "actions_summary": {
                "total": len(self.iteration_history),
                "successful": successful_actions,
                "failed": failed_actions,
                "success_rate": successful_actions / max(len(self.iteration_history), 1),
            },
            "completed_goals": [{"id": g.id, "name": g.name} for g in completed_goals],
            "failed_goals": [{"id": g.id, "name": g.name} for g in failed_goals],
        }


class GoalManager:
    """
    Manager for agent goals.

    Handles goal creation, prioritization, decomposition, and tracking.
    """

    def __init__(self, agent: Agent):
        """
        Initialize GoalManager for an agent.

        Args:
            agent: The agent whose goals are managed
        """
        self.agent = agent

    def add_goal(
        self,
        name: str,
        description: str = "",
        priority: int = 0,
        parent_goal_id: Optional[str] = None,
    ) -> Goal:
        """
        Add a new goal to the agent.

        Args:
            name: Goal name
            description: Goal description
            priority: Goal priority (higher = more important)
            parent_goal_id: ID of parent goal if this is a sub-goal

        Returns:
            The created goal
        """
        goal = Goal(
            name=name,
            description=description,
            priority=priority,
            parent_goal_id=parent_goal_id,
            associated_agent_id=self.agent.id,
        )
        self.agent.add_goal(goal)
        return goal

    def decompose_goal(
        self,
        goal: Goal,
        sub_goals: List[Dict[str, Any]],
    ) -> List[Goal]:
        """
        Decompose a goal into sub-goals.

        Args:
            goal: The goal to decompose
            sub_goals: List of sub-goal specifications

        Returns:
            List of created sub-goals
        """
        created_goals = []
        for i, sg_spec in enumerate(sub_goals):
            sub_goal = Goal(
                name=sg_spec.get("name", f"Sub-goal {i+1}"),
                description=sg_spec.get("description", ""),
                priority=sg_spec.get("priority", goal.priority),
                parent_goal_id=goal.id,
                associated_agent_id=self.agent.id,
            )
            self.agent.add_goal(sub_goal)
            created_goals.append(sub_goal)
        return created_goals

    def update_priority(self, goal_id: str, new_priority: int) -> bool:
        """
        Update a goal's priority.

        Args:
            goal_id: ID of goal to update
            new_priority: New priority value

        Returns:
            True if successful, False if goal not found
        """
        for goal in self.agent.goals:
            if goal.id == goal_id:
                goal.priority = new_priority
                return True
        return False

    def mark_completed(self, goal_id: str) -> bool:
        """Mark a goal as completed."""
        for goal in self.agent.goals:
            if goal.id == goal_id:
                goal.update_status(GoalStatus.COMPLETED)
                return True
        return False

    def mark_failed(self, goal_id: str) -> bool:
        """Mark a goal as failed."""
        for goal in self.agent.goals:
            if goal.id == goal_id:
                goal.update_status(GoalStatus.FAILED)
                return True
        return False

    def get_goal_tree(self, goal_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the goal tree starting from a specific goal or all root goals.

        Args:
            goal_id: Starting goal ID, or None for all root goals

        Returns:
            Nested dictionary representing goal tree
        """
        def build_tree(g: Goal) -> Dict[str, Any]:
            children = [
                build_tree(cg)
                for cg in self.agent.goals
                if cg.parent_goal_id == g.id
            ]
            return {
                "id": g.id,
                "name": g.name,
                "status": g.status.value,
                "priority": g.priority,
                "children": children,
            }

        if goal_id:
            for goal in self.agent.goals:
                if goal.id == goal_id:
                    return build_tree(goal)
            return {}

        # Return all root goals (goals without parents)
        root_goals = [g for g in self.agent.goals if g.parent_goal_id is None]
        return [build_tree(g) for g in root_goals]
