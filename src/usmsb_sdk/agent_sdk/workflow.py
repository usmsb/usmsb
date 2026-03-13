"""
Workflow Module

Manages agent workflows and task execution.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from usmsb_sdk.agent_sdk.platform_client import PlatformClient, APIResponse


logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow status"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Step status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """A single step in a workflow"""
    step_id: str
    name: str
    description: str
    tool: str
    parameters: Dict[str, Any]
    dependencies: List[str]
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def is_complete(self) -> bool:
        return self.status in ["completed", "skipped"]

    @property
    def is_failed(self) -> bool:
        return self.status == "failed"

    @property
    def can_run(self) -> bool:
        """Check if all dependencies are complete"""
        return self.status == "pending"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowStep":
        return cls(
            step_id=data.get("step_id", data.get("id", "")),
            name=data.get("name", ""),
            description=data.get("description", ""),
            tool=data.get("tool", ""),
            parameters=data.get("parameters", {}),
            dependencies=data.get("dependencies", []),
            status=data.get("status", "pending"),
            result=data.get("result"),
            error=data.get("error"),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "description": self.description,
            "tool": self.tool,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "status": self.status,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class Workflow:
    """A workflow definition"""
    workflow_id: str
    name: str
    task_description: str
    steps: List[WorkflowStep]
    status: str
    current_step: int
    agent_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def completed_steps(self) -> int:
        return sum(1 for s in self.steps if s.is_complete)

    @property
    def failed_steps(self) -> int:
        return sum(1 for s in self.steps if s.is_failed)

    @property
    def progress(self) -> float:
        if not self.steps:
            return 0.0
        return self.completed_steps / len(self.steps)

    @property
    def is_complete(self) -> bool:
        return self.status == "completed"

    @property
    def is_running(self) -> bool:
        return self.status == "running"

    @property
    def execution_time(self) -> float:
        """Get execution time in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        if self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Workflow":
        # Parse steps
        steps = []
        steps_data = data.get("steps", [])
        if isinstance(steps_data, str):
            try:
                steps_data = json.loads(steps_data)
            except (json.JSONDecodeError, TypeError):
                steps_data = []
        for s in steps_data:
            steps.append(WorkflowStep.from_dict(s))

        # Parse result
        result_data = data.get("result")
        if isinstance(result_data, str):
            try:
                result_data = json.loads(result_data)
            except (json.JSONDecodeError, TypeError):
                pass

        return cls(
            workflow_id=data.get("id", data.get("workflow_id", "")),
            name=data.get("name", ""),
            task_description=data.get("task_description", ""),
            steps=steps,
            status=data.get("status", "pending"),
            current_step=data.get("current_step", 0),
            agent_id=data.get("agent_id", ""),
            created_at=datetime.fromtimestamp(data["created_at"]) if isinstance(data.get("created_at"), (int, float)) else None,
            updated_at=datetime.fromtimestamp(data["updated_at"]) if isinstance(data.get("updated_at"), (int, float)) else None,
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            result=result_data,
            error=data.get("error"),
        )


@dataclass
class WorkflowResult:
    """Result of workflow execution"""
    workflow_id: str
    status: str
    total_steps: int
    completed_steps: int
    failed_steps: int
    execution_time: float
    step_results: Dict[str, Any]
    final_result: Any

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowResult":
        return cls(
            workflow_id=data.get("workflow_id", ""),
            status=data.get("status", "pending"),
            total_steps=data.get("total_steps", 0),
            completed_steps=data.get("completed_steps", 0),
            failed_steps=data.get("failed_steps", 0),
            execution_time=data.get("execution_time", 0),
            step_results=data.get("step_results", {}),
            final_result=data.get("result", data.get("final_result")),
        )


class WorkflowManager:
    """
    Manages workflow creation and execution.

    Features:
    - Create workflows from task descriptions
    - Execute workflows step by step
    - Pause/resume/cancel workflows
    - Track progress
    """

    def __init__(
        self,
        platform_client: PlatformClient,
        agent_id: str,
        logger: Optional[logging.Logger] = None,
    ):
        self._platform = platform_client
        self.agent_id = agent_id
        self.logger = logger or logging.getLogger(__name__)

        # Workflow cache
        self._workflows: Dict[str, Workflow] = {}

    # ==================== Workflow Creation ====================

    async def create(
        self,
        task_description: str,
        available_tools: Optional[List[str]] = None,
    ) -> Optional[Workflow]:
        """
        Create a new workflow.

        Args:
            task_description: Description of the task
            available_tools: Tools available for the workflow

        Returns:
            Created Workflow or None
        """
        response = await self._platform.create_workflow(
            task_description=task_description,
            available_tools=available_tools,
        )

        if response.success and response.data:
            workflow = Workflow.from_dict(response.data)
            self._workflows[workflow.workflow_id] = workflow
            self.logger.info(f"Workflow created: {workflow.workflow_id}")
            return workflow

        self.logger.error(f"Failed to create workflow: {response.error}")
        return None

    async def get(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID"""
        if workflow_id in self._workflows:
            return self._workflows[workflow_id]
        return None

    async def list_all(self) -> List[Workflow]:
        """List all workflows"""
        response = await self._platform.list_workflows()

        if response.success and response.data:
            workflows = []
            for w in response.data:
                workflow = Workflow.from_dict(w)
                self._workflows[workflow.workflow_id] = workflow
                workflows.append(workflow)
            return workflows

        return []

    # ==================== Execution ====================

    async def execute(self, workflow_id: str) -> Optional[WorkflowResult]:
        """
        Execute a workflow.

        Args:
            workflow_id: Workflow to execute

        Returns:
            WorkflowResult or None
        """
        response = await self._platform.execute_workflow(workflow_id)

        if response.success and response.data:
            result = WorkflowResult.from_dict(response.data)
            if result.status == "completed":
                self.logger.info(f"Workflow completed: {workflow_id}")
            else:
                self.logger.warning(f"Workflow {result.status}: {workflow_id}")
            return result

        self.logger.error(f"Failed to execute workflow: {response.error}")
        return None

    async def pause(self, workflow_id: str) -> bool:
        """Pause a running workflow"""
        # TODO: Implement when platform API supports pause
        self.logger.warning("Workflow pause not yet implemented")
        return False

    async def resume(self, workflow_id: str) -> bool:
        """Resume a paused workflow"""
        # TODO: Implement when platform API supports resume
        return False

    async def cancel(self, workflow_id: str) -> bool:
        """Cancel a workflow"""
        # TODO: Implement when platform API supports cancel
        return False

    # ==================== Status ====================

    async def get_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow status"""
        workflow = await self.get(workflow_id)
        if workflow:
            return {
                "workflow_id": workflow.workflow_id,
                "status": workflow.status,
                "progress": workflow.progress,
                "total_steps": workflow.total_steps,
                "completed_steps": workflow.completed_steps,
                "failed_steps": workflow.failed_steps,
                "current_step": workflow.current_step,
                "execution_time": workflow.execution_time,
            }
        return {"error": "Workflow not found"}

    async def get_current_step(self, workflow_id: str) -> Optional[WorkflowStep]:
        """Get the current step being executed"""
        workflow = await self.get(workflow_id)
        if workflow and 0 <= workflow.current_step < len(workflow.steps):
            return workflow.steps[workflow.current_step]
        return None

    # ==================== Step Management ====================

    async def skip_step(
        self,
        workflow_id: str,
        step_id: str,
        reason: str = "",
    ) -> bool:
        """Skip a step in the workflow"""
        workflow = await self.get(workflow_id)
        if workflow:
            for step in workflow.steps:
                if step.step_id == step_id:
                    step.status = "skipped"
                    self.logger.info(f"Step skipped: {step_id} - {reason}")
                    return True
        return False

    async def retry_step(self, workflow_id: str, step_id: str) -> bool:
        """Retry a failed step"""
        workflow = await self.get(workflow_id)
        if workflow:
            for step in workflow.steps:
                if step.step_id == step_id and step.is_failed:
                    step.status = "pending"
                    step.error = None
                    self.logger.info(f"Step queued for retry: {step_id}")
                    return True
        return False

    # ==================== Convenience Methods ====================

    async def run(
        self,
        task_description: str,
        tools: Optional[List[str]] = None,
    ) -> Optional[WorkflowResult]:
        """
        Convenience method to create and run a workflow.

        Args:
            task_description: Task to execute
            tools: Available tools

        Returns:
            WorkflowResult
        """
        workflow = await self.create(task_description, tools)
        if workflow:
            return await self.execute(workflow.workflow_id)
        return None
