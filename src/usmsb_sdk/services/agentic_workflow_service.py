"""
Agentic Workflow Service

Service for orchestrating complex agentic workflows including
task decomposition, planning, tool execution, and multi-agent coordination.
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from usmsb_sdk.core.elements import Agent
from usmsb_sdk.intelligence_adapters.base import IAgenticFrameworkAdapter, ILLMAdapter

logger = logging.getLogger(__name__)


class WorkflowStatus(StrEnum):
    """Status of a workflow."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    id: str
    name: str
    description: str
    action: dict[str, Any]
    dependencies: list[str] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: Any | None = None
    error: str | None = None
    started_at: float | None = None
    completed_at: float | None = None


@dataclass
class Workflow:
    """A complete workflow definition."""
    id: str
    name: str
    description: str
    steps: list[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    started_at: float | None = None
    completed_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    workflow_id: str
    status: WorkflowStatus
    step_results: dict[str, Any]
    total_steps: int
    completed_steps: int
    failed_steps: int
    execution_time: float
    error: str | None = None


class AgenticWorkflowService:
    """
    Agentic Workflow Service.

    Provides capabilities for:
    - Task decomposition
    - Action planning
    - Tool execution
    - Multi-agent coordination
    - Workflow orchestration
    """

    def __init__(
        self,
        llm_adapter: ILLMAdapter,
        agentic_adapter: IAgenticFrameworkAdapter | None = None,
        max_concurrent_steps: int = 5,
    ):
        """
        Initialize the Agentic Workflow Service.

        Args:
            llm_adapter: LLM adapter for reasoning
            agentic_adapter: Optional agentic framework adapter
            max_concurrent_steps: Maximum concurrent step executions
        """
        self.llm = llm_adapter
        self.agentic_adapter = agentic_adapter
        self.max_concurrent_steps = max_concurrent_steps

        self._workflows: dict[str, Workflow] = {}
        self._tools: dict[str, dict[str, Any]] = {}
        self._step_semaphore = asyncio.Semaphore(max_concurrent_steps)

        # Callbacks
        self.on_step_start: Callable[[WorkflowStep], None] | None = None
        self.on_step_complete: Callable[[WorkflowStep], None] | None = None
        self.on_step_error: Callable[[WorkflowStep, Exception], None] | None = None

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Callable,
    ) -> None:
        """
        Register a tool for use in workflows.

        Args:
            name: Tool name
            description: Tool description
            parameters: Parameter schema
            handler: Function to execute the tool
        """
        self._tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler,
        }

        if self.agentic_adapter:
            self.agentic_adapter.register_tool(name, description, parameters, handler)

        logger.info(f"Registered tool: {name}")

    async def create_workflow(
        self,
        task_description: str,
        agent: Agent,
        available_tools: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> Workflow:
        """
        Create a workflow from a task description.

        Args:
            task_description: Natural language task description
            agent: The agent to execute the workflow
            available_tools: List of available tool names
            context: Additional context

        Returns:
            Created workflow
        """
        # Use agentic adapter if available, otherwise use LLM directly
        if self.agentic_adapter:
            steps = await self.agentic_adapter.plan_action_sequence(
                goal=task_description,
                current_state=agent.state,
                available_tools=available_tools or list(self._tools.keys()),
                context=context,
            )
        else:
            steps = await self._plan_with_llm(
                task_description, agent, available_tools, context
            )

        workflow_id = f"wf_{datetime.now().timestamp()}"

        workflow = Workflow(
            id=workflow_id,
            name=f"Workflow for: {task_description[:50]}...",
            description=task_description,
            steps=[
                WorkflowStep(
                    id=f"step_{i}",
                    name=step.get("name", f"Step {i+1}"),
                    description=step.get("description", ""),
                    action=step.get("action", {}),
                    dependencies=step.get("dependencies", []),
                )
                for i, step in enumerate(steps)
            ],
        )

        self._workflows[workflow_id] = workflow
        logger.info(f"Created workflow {workflow_id} with {len(workflow.steps)} steps")

        return workflow

    async def execute_workflow(
        self,
        workflow_id: str,
        agent: Agent,
        context: dict[str, Any] | None = None,
    ) -> WorkflowResult:
        """
        Execute a workflow.

        Args:
            workflow_id: ID of the workflow to execute
            agent: Agent executing the workflow
            context: Additional context

        Returns:
            Workflow execution result
        """
        if workflow_id not in self._workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        workflow = self._workflows[workflow_id]
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now().timestamp()

        step_results = {}
        completed_steps = 0
        failed_steps = 0

        try:
            # Execute steps in dependency order
            executed_steps = set()

            while len(executed_steps) < len(workflow.steps):
                # Find steps ready to execute
                ready_steps = [
                    step for step in workflow.steps
                    if step.id not in executed_steps
                    and all(dep in executed_steps for dep in step.dependencies)
                ]

                if not ready_steps:
                    # Check for circular dependencies or all steps done
                    remaining = [s for s in workflow.steps if s.id not in executed_steps]
                    if remaining:
                        raise RuntimeError("Cannot progress: remaining steps have unmet dependencies")
                    break

                # Execute ready steps (with concurrency limit)
                tasks = [
                    self._execute_step(step, agent, context)
                    for step in ready_steps[:self.max_concurrent_steps]
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for step, result in zip(ready_steps[:len(tasks)], results, strict=False):
                    if isinstance(result, Exception):
                        step.status = WorkflowStatus.FAILED
                        step.error = str(result)
                        failed_steps += 1
                        if self.on_step_error:
                            self.on_step_error(step, result)
                        logger.error(f"Step {step.id} failed: {result}")
                    else:
                        step.status = WorkflowStatus.COMPLETED
                        step.result = result
                        completed_steps += 1
                        if self.on_step_complete:
                            self.on_step_complete(step)

                    step_results[step.id] = {
                        "status": step.status.value,
                        "result": step.result,
                        "error": step.error,
                    }
                    executed_steps.add(step.id)

            workflow.status = WorkflowStatus.COMPLETED if failed_steps == 0 else WorkflowStatus.FAILED
            workflow.completed_at = datetime.now().timestamp()

        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            logger.error(f"Workflow {workflow_id} failed: {e}")
            raise

        execution_time = (workflow.completed_at or datetime.now().timestamp()) - workflow.started_at

        return WorkflowResult(
            workflow_id=workflow_id,
            status=workflow.status,
            step_results=step_results,
            total_steps=len(workflow.steps),
            completed_steps=completed_steps,
            failed_steps=failed_steps,
            execution_time=execution_time,
        )

    async def _execute_step(
        self,
        step: WorkflowStep,
        agent: Agent,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a single workflow step."""
        async with self._step_semaphore:
            step.status = WorkflowStatus.RUNNING
            step.started_at = datetime.now().timestamp()

            if self.on_step_start:
                self.on_step_start(step)

            action = step.action
            action_type = action.get("type", "unknown")

            try:
                if action_type == "tool_call":
                    return await self._execute_tool_call(action, context)
                elif action_type == "llm_reasoning":
                    return await self._execute_llm_reasoning(action, context)
                elif action_type == "agent_action":
                    return await self._execute_agent_action(action, agent, context)
                else:
                    # Default: try tool call
                    return await self._execute_tool_call(action, context)

            finally:
                step.completed_at = datetime.now().timestamp()

    async def _execute_tool_call(
        self,
        action: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a tool call action."""
        tool_name = action.get("tool") or action.get("name")
        params = action.get("parameters", {})

        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        tool = self._tools[tool_name]
        handler = tool["handler"]

        if asyncio.iscoroutinefunction(handler):
            return await handler(**params)
        else:
            return handler(**params)

    async def _execute_llm_reasoning(
        self,
        action: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Execute an LLM reasoning action."""
        prompt = action.get("prompt", "")
        return await self.llm.generate_text(prompt, context=context)

    async def _execute_agent_action(
        self,
        action: dict[str, Any],
        agent: Agent,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Execute an agent-specific action."""
        # This would integrate with the agent's execution service
        action_type = action.get("action", "unknown")
        logger.info(f"Executing agent action: {action_type}")
        return {"action": action_type, "status": "completed"}

    async def _plan_with_llm(
        self,
        task_description: str,
        agent: Agent,
        available_tools: list[str] | None,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Plan workflow steps using LLM."""
        tools_info = "\n".join([
            f"- {name}: {info['description']}"
            for name, info in self._tools.items()
            if available_tools is None or name in available_tools
        ])

        prompt = f"""Create a step-by-step plan to accomplish the following task.

Task: {task_description}

Agent Capabilities: {agent.capabilities}

Available Tools:
{tools_info if tools_info else "No tools available"}

Create a plan with clear steps. Each step should have:
- name: Short name for the step
- description: Detailed description
- action: The action to take (type: "tool_call", "llm_reasoning", or "agent_action")
- dependencies: List of step indices this depends on (0-indexed)

Respond with a JSON array of steps."""

        response = await self.llm.generate_text(prompt, context=context, temperature=0.7)

        # Parse JSON from response
        import json
        import re
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                return json.loads(json_match.group())
            return [{"name": "Execute task", "description": task_description, "action": {"type": "llm_reasoning"}}]

    async def coordinate_agents(
        self,
        task: str,
        agents: list[Agent],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Coordinate multiple agents for a task.

        Args:
            task: Task description
            agents: List of agents to coordinate
            context: Additional context

        Returns:
            Coordination result
        """
        if self.agentic_adapter:
            agent_specs = [
                {"id": a.id, "name": a.name, "capabilities": a.capabilities}
                for a in agents
            ]
            return await self.agentic_adapter.coordinate_agents(task, agent_specs, context)

        # Fallback: use LLM to plan coordination
        prompt = f"""Coordinate multiple agents to accomplish a task.

Task: {task}

Agents:
{chr(10).join([f"- {a.name}: {a.capabilities}" for a in agents])}

Plan how these agents should work together. Include:
1. Task decomposition
2. Agent assignments
3. Communication protocol
4. Expected outcome

Respond in JSON format."""

        response = await self.llm.generate_text(prompt, context=context)
        import json
        try:
            return json.loads(response)
        except:
            return {"plan": response}

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        if workflow_id in self._workflows:
            self._workflows[workflow_id].status = WorkflowStatus.CANCELLED
            return True
        return False

    def list_workflows(self, status: WorkflowStatus | None = None) -> list[Workflow]:
        """List workflows, optionally filtered by status."""
        workflows = list(self._workflows.values())
        if status:
            workflows = [w for w in workflows if w.status == status]
        return workflows
