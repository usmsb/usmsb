"""
Task Executor

Purpose:
=========
1. Analyze user requests and generate execution plans
2. Execute tasks step by step (each step < 60 seconds)
3. Support task confirmation flow for complex tasks
4. Persist task progress to database

Core Principles:
- Simple tasks: Direct execution (current flow)
- Complex tasks: Plan -> Confirm -> Step-by-step execution
- Each step can be independently retried
- Support task resumption
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from ..models.task_plan import (
    StepResult,
    StepStatus,
    TaskComplexity,
    TaskPlan,
    TaskStatus,
    TaskStep,
    detect_task_complexity,
    should_confirm_plan,
    should_use_step_by_step,
)
from ..services.task_progress_store import TaskProgressStore, TaskProgressRecord

if TYPE_CHECKING:
    from ..agent import MetaAgent

logger = logging.getLogger(__name__)


class TaskExecutor:
    """
    Task execution manager

    Responsibilities:
    1. Analyze task complexity
    2. Generate execution steps via LLM
    3. Execute steps sequentially
    4. Manage task state and persistence
    """

    def __init__(self, agent: "MetaAgent"):
        self.agent = agent
        self._active_tasks: Dict[str, TaskPlan] = {}
        self._progress_store: Optional[TaskProgressStore] = None

    def init_progress_store(self, db_path: str):
        """Initialize progress store"""
        self._progress_store = TaskProgressStore(db_path)
        logger.info(f"[TaskExecutor] Progress store initialized: {db_path}")

    # ==================== Planning ====================

    async def analyze_and_plan(
        self,
        user_request: str,
        wallet_address: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> TaskPlan:
        """
        Analyze task and generate execution plan

        Args:
            user_request: User request
            wallet_address: User wallet address
            conversation_id: Conversation ID

        Returns:
            Task plan
        """
        task_id = f"task_{uuid.uuid4().hex[:12]}"

        # Detect complexity
        complexity = detect_task_complexity(user_request)
        logger.info(f"[TaskExecutor] Task complexity: {complexity.value}")

        plan = TaskPlan(
            task_id=task_id,
            user_request=user_request,
            complexity=complexity,
            wallet_address=wallet_address,
            conversation_id=conversation_id,
            status=TaskStatus.PLANNING,
        )

        # Generate steps for complex tasks
        if should_use_step_by_step(complexity):
            steps = await self._generate_steps(user_request, complexity)
            plan.steps = steps

            if should_confirm_plan(complexity):
                plan.status = TaskStatus.AWAITING_CONFIRM
            else:
                plan.status = TaskStatus.EXECUTING
        else:
            # Simple task - single step
            plan.steps = [
                TaskStep(
                    step_id=f"{task_id}_step_1",
                    name="Execute Request",
                    description=user_request,
                    action="direct_execute",
                    params={"request": user_request},
                    estimated_time=30,
                )
            ]
            plan.status = TaskStatus.EXECUTING

        plan.updated_at = datetime.now()
        self._active_tasks[task_id] = plan

        # Save progress
        await self._save_progress(plan)

        return plan

    async def _generate_steps(
        self,
        user_request: str,
        complexity: TaskComplexity,
    ) -> List[TaskStep]:
        """
        Use LLM to generate execution steps with detailed English prompts.
        """

        # ========== SYSTEM PROMPT ==========
        system_prompt = """You are a TASK PLANNING EXPERT specialized in breaking down complex user requests into specific, executable steps.

## YOUR ROLE
- Analyze technical architecture of user requirements
- Design reasonable project structures
- Plan specific implementation steps

## CRITICAL CONSTRAINTS (MUST FOLLOW)
1. Each step MUST be independently executable
2. Each step execution time MUST NOT exceed 60 seconds
3. Steps must have clear dependency relationships
4. You MUST generate MULTIPLE steps (minimum 3-5), NEVER generate only one step
5. For creating complete systems/platforms/websites, you MUST generate 5-10 steps

## ACTION TYPES (CHOOSE ONE FOR EACH STEP)
- create_directory: Create directories/folders (use "path" or "paths" in params)
- create_file: Create configuration files like package.json, requirements.txt, config.yaml (use "path" and "content" in params)
- write_code: Write actual code content (main work, use "path" and "content" in params)
- install_dependencies: Install dependency packages
- test: Run tests
- direct_execute: Use LLM to execute directly

## OUTPUT FORMAT (STRICT JSON)
You MUST return a valid JSON array with this exact structure:
```json
{
  "steps": [
    {
      "name": "Step name (max 30 characters)",
      "description": "Detailed description of what this step does and why",
      "action": "One of: create_directory, create_file, write_code, install_dependencies, test, direct_execute",
      "params": {"path": "file or directory path", "content": "file content description"},
      "dependencies": ["name of dependent step or empty array"],
      "estimated_time": 30
    }
  ]
}
```

## STRICT RULES
1. For complex tasks, you MUST generate at least 5-10 steps
2. Each step's "action" MUST match the actual work
3. "dependencies" must use step names defined earlier
4. "params" must include all required parameters (path, content, etc.)
5. DO NOT generate actual code in "content" field - just describe what the file should contain
6. Your output MUST be ONLY valid JSON - no explanations, no markdown, no text before or after

## EXAMPLE
For "create an e-commerce system", generate:
1. Create project directory structure
2. Create package.json
3. Create database models
4. Create backend API routes
5. Create frontend components
6. Install dependencies
7. Initialize database
8. Run tests"""

        # ========== USER PROMPT ==========
        user_prompt = f"""## USER REQUEST
{user_request}

## TASK COMPLEXITY
{complexity.value}

## ANALYSIS REQUIREMENTS
1. First analyze what technical components this task needs
2. Determine the overall project structure
3. Plan the implementation order of each component
4. Consider dependency relationships between steps

## OUTPUT REQUIREMENTS
Generate detailed execution steps ensuring:
- Each step is independently executable
- Step order is reasonable (dependencies come first)
- Include sufficient detail (description, params, etc.)
- For complex tasks, generate at least 5-10 steps

IMPORTANT: Output ONLY valid JSON, nothing else. Start with {{ and end with }}"""

        # Call LLM with retry
        max_retries = 3
        retry_count = 0
        last_error = None
        response = None

        while retry_count < max_retries:
            try:
                logger.info(f"[TaskExecutor] Calling LLM (attempt {retry_count + 1}/{max_retries})")
                response = await self.agent.llm_manager.chat(user_prompt, system_prompt=system_prompt)
                logger.info(f"[TaskExecutor] LLM response length: {len(response)}")
                break
            except Exception as e:
                last_error = e
                retry_count += 1
                logger.warning(f"[TaskExecutor] LLM call failed (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    await asyncio.sleep(2)
                else:
                    logger.error(f"[TaskExecutor] LLM call failed after {max_retries} retries: {e}")

        if response is None:
            raise ValueError(f"LLM call failed: {last_error}")

        try:
            # Parse JSON
            steps_data = self._parse_steps_json(response)

            if not steps_data:
                raise ValueError("LLM returned empty steps data")

            # Build TaskStep objects
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            steps = []
            name_to_id = {}

            for i, step_data in enumerate(steps_data):
                step_id = f"{task_id}_step_{i+1}"
                name = step_data.get("name", f"Step {i+1}")
                name_to_id[name] = step_id

                # Resolve dependencies
                dep_ids = []
                for dep_name in step_data.get("dependencies", []):
                    if dep_name in name_to_id:
                        dep_ids.append(name_to_id[dep_name])

                step = TaskStep(
                    step_id=step_id,
                    name=name,
                    description=step_data.get("description", ""),
                    action=step_data.get("action", "direct_execute"),
                    params=step_data.get("params", {}),
                    dependencies=dep_ids,
                    estimated_time=step_data.get("estimated_time", 30),
                )
                steps.append(step)

            logger.info(f"[TaskExecutor] Generated {len(steps)} steps")
            return steps

        except Exception as e:
            logger.error(f"[TaskExecutor] Failed to generate steps: {e}")
            # Fallback to single step
            return [
                TaskStep(
                    step_id=f"task_default_step",
                    name="Execute Request",
                    description=user_request,
                    action="direct_execute",
                    params={"request": user_request},
                    estimated_time=60,
                )
            ]

    def _parse_steps_json(self, response: str) -> List[Dict]:
        """Parse steps JSON - supports multiple formats"""
        logger.info(f"[TaskExecutor] Parsing steps JSON, response length: {len(response)}")

        import re
        import json

        # Method 1: Direct JSON
        try:
            data = json.loads(response)
            steps = data.get("steps", [])
            if steps:
                logger.info(f"[TaskExecutor] Parsed {len(steps)} steps via direct JSON")
                return steps
        except json.JSONDecodeError as e:
            logger.warning(f"[TaskExecutor] Direct JSON parse failed: {e}")

        # Method 2: ```json``` block
        start_marker = "```json"
        end_marker = "```"
        start_idx = response.find(start_marker)
        if start_idx != -1:
            start_idx += len(start_marker)
            end_idx = response.rfind(end_marker, start_idx)
            if end_idx != -1:
                json_str = response[start_idx:end_idx].strip()
                try:
                    data = json.loads(json_str)
                    steps = data.get("steps", [])
                    if steps:
                        logger.info(f"[TaskExecutor] Parsed {len(steps)} steps via ```json block")
                        return steps
                except json.JSONDecodeError as e:
                    logger.warning(f"[TaskExecutor] JSON block parse failed: {e}")

        # Method 3: Extract "steps": [...]
        steps_pattern = r'"steps"\s*:\s*\['
        match = re.search(steps_pattern, response)
        if match:
            start_bracket = match.end() - 1
            bracket_count = 0
            i = start_bracket
            while i < len(response):
                if response[i] == '[':
                    bracket_count += 1
                elif response[i] == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        break
                i += 1

            if bracket_count == 0:
                arr_str = response[start_bracket:i+1]
                try:
                    steps = json.loads(arr_str)
                    if steps and isinstance(steps[0], dict):
                        logger.info(f"[TaskExecutor] Parsed {len(steps)} steps via array extraction")
                        return steps
                except json.JSONDecodeError as e:
                    logger.warning(f"[TaskExecutor] Array extraction failed: {e}")

        logger.warning(f"[TaskExecutor] All parse methods failed")
        return []

    # ==================== Execution ====================

    async def execute_plan(
        self,
        plan: TaskPlan,
        progress_callback: Optional[Callable[[TaskPlan], None]] = None,
    ) -> TaskPlan:
        """
        Execute task plan

        Args:
            plan: Task plan
            progress_callback: Progress callback

        Returns:
            Updated task plan
        """
        plan.status = TaskStatus.EXECUTING
        plan.updated_at = datetime.now()

        logger.info(f"[TaskExecutor] Executing plan {plan.task_id}, steps count: {len(plan.steps)}")

        for i, step in enumerate(plan.steps):
            logger.info(f"[TaskExecutor] Step {i+1}: {step.name}, action: {step.action}")
            if step.status == StepStatus.COMPLETED:
                continue

            plan.current_step_index = i

            # Check dependencies
            if not plan.can_execute_step(step):
                logger.warning(f"[TaskExecutor] Step {step.name} dependencies not met, skipping")
                step.status = StepStatus.SKIPPED
                continue

            # Execute step
            result = await self._execute_step(step, plan)

            logger.info(f"[TaskExecutor] Step {step.name} executed, success={result.success}")

            # Update step status
            if result.success:
                step.status = StepStatus.COMPLETED
                step.result = result.data
            else:
                step.status = StepStatus.FAILED
                step.error = result.error
                step.retry_count += 1

                # Retry logic
                if step.retry_count < step.max_retries:
                    step.status = StepStatus.PENDING
                    i -= 1

            plan.updated_at = datetime.now()

            # Call progress callback
            if progress_callback:
                progress_callback(plan)

            # Save progress
            await self._save_progress(plan)

        # Update plan status
        completed = len(plan.get_completed_steps())
        if completed == len(plan.steps):
            plan.status = TaskStatus.COMPLETED
        else:
            plan.status = TaskStatus.FAILED

        # Save final status
        await self._save_progress(plan)

        return plan

    async def _execute_step(
        self,
        step: TaskStep,
        plan: TaskPlan,
    ) -> StepResult:
        """
        Execute single step (max 60 seconds)
        """
        start_time = time.time()
        step.status = StepStatus.RUNNING

        try:
            # Route to appropriate executor
            if step.action == "direct_execute":
                result = await self._execute_direct(step, plan)
            elif step.action == "create_directory":
                result = await self._execute_create_directory(step, plan)
            elif step.action == "create_file":
                result = await self._execute_create_file(step, plan)
            elif step.action == "write_code":
                result = await self._execute_write_code(step, plan)
            elif step.action == "execute":
                result = await self._execute_command(step, plan)
            else:
                # Default: use LLM
                result = await self._execute_with_llm(step, plan)

            execution_time = time.time() - start_time

            return StepResult(
                step_id=step.step_id,
                success=True,
                output=result.get("output", ""),
                data=result,
                execution_time=execution_time,
            )

        except asyncio.TimeoutError:
            return StepResult(
                step_id=step.step_id,
                success=False,
                error="Step timeout (60 seconds)",
                execution_time=60.0,
            )
        except Exception as e:
            logger.error(f"[TaskExecutor] Step execution failed: {e}")
            return StepResult(
                step_id=step.step_id,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
            )

    async def _execute_direct(
        self,
        step: TaskStep,
        plan: TaskPlan,
    ) -> Dict[str, Any]:
        """Execute directly (simple task)"""
        logger.info(f"[TaskExecutor] _execute_direct called for step: {step.name}")
        request = step.params.get("request", plan.user_request)
        logger.info(f"[TaskExecutor] Executing request: {request[:50]}...")

        prompt = f"""User request: {request}

Directly execute this task and return the result. If you need to create files or execute code, return the code content directly."""

        try:
            result = await self.agent.llm_manager.chat(prompt)
            logger.info(f"[TaskExecutor] _execute_direct result length: {len(str(result))}")
            return {"output": result}
        except Exception as e:
            logger.error(f"[TaskExecutor] LLM execution failed: {e}")
            return {"output": f"Error: {str(e)}"}

    async def _execute_create_directory(
        self,
        step: TaskStep,
        plan: TaskPlan,
    ) -> Dict[str, Any]:
        """Create directory"""
        path = step.params.get("path", "")

        result = await self.agent._execute_tool(
            tool_name="create_directory",
            tool_args={"path": path},
            user_session=None,
        )

        return result

    async def _execute_create_file(
        self,
        step: TaskStep,
        plan: TaskPlan,
    ) -> Dict[str, Any]:
        """Create file"""
        file_path = step.params.get("file_path", "")
        content = step.params.get("content", "")

        result = await self.agent._execute_tool(
            tool_name="write_file",
            tool_args={"file_path": file_path, "content": content},
            user_session=None,
        )

        return result

    async def _execute_write_code(
        self,
        step: TaskStep,
        plan: TaskPlan,
    ) -> Dict[str, Any]:
        """Write code via LLM"""
        code_request = step.params.get("code_request", step.description)

        prompt = f"""Generate code for:

{code_request}

Return only the code, no explanations."""

        code = await self.agent.llm_manager.chat(prompt)

        # Write to file if path specified
        file_path = step.params.get("file_path")
        if file_path:
            await self.agent._execute_tool(
                tool_name="write_file",
                tool_args={"file_path": file_path, "content": code},
                user_session=None,
            )

        return {"output": code, "file_path": file_path}

    async def _execute_command(
        self,
        step: TaskStep,
        plan: TaskPlan,
    ) -> Dict[str, Any]:
        """Execute command"""
        command = step.params.get("command", "")
        cwd = step.params.get("cwd", "/workspace")

        result = await self.agent._execute_tool(
            tool_name="execute_command",
            tool_args={"command": command, "cwd": cwd},
            user_session=None,
        )

        return result

    async def _execute_with_llm(
        self,
        step: TaskStep,
        plan: TaskPlan,
    ) -> Dict[str, Any]:
        """Execute via LLM"""
        prompt = f"""Execute step:

Name: {step.name}
Description: {step.description}
Params: {json.dumps(step.params, ensure_ascii=False)}

User request: {plan.user_request}

Completed steps:
{self._format_completed_steps(plan)}

Return the result of executing this step."""

        result = await self.agent.llm_manager.chat(prompt)

        return {"output": result}

    def _format_completed_steps(self, plan: TaskPlan) -> str:
        """Format completed steps"""
        completed = plan.get_completed_steps()
        if not completed:
            return ""

        lines = []
        for step in completed:
            lines.append(f"- {step.name}: {step.description}")

        return "\n".join(lines)

    async def _save_progress(self, plan: TaskPlan) -> None:
        """
        Save task progress to database
        """
        try:
            if self._progress_store and plan.wallet_address:
                record = TaskProgressRecord(
                    task_id=plan.task_id,
                    wallet_address=plan.wallet_address,
                    conversation_id=plan.conversation_id or "",
                    user_request=plan.user_request,
                    complexity=plan.complexity.value,
                    status=plan.status.value,
                    total_steps=len(plan.steps),
                    completed_steps=len(plan.get_completed_steps()),
                    created_at=plan.created_at,
                    updated_at=plan.updated_at,
                    plan_data=plan.to_dict(),
                )
                self._progress_store.save_task(record)
        except Exception as e:
            logger.warning(f"[TaskExecutor] Failed to save progress: {e}")

    # ==================== Task Management ====================

    def get_task(self, task_id: str) -> Optional[TaskPlan]:
        """Get task by ID"""
        task = self._active_tasks.get(task_id)
        if task:
            return task

        # Load from database
        if self._progress_store:
            record = self._progress_store.get_task(task_id)
            if record:
                return self._rebuild_plan_from_record(record)

        return None

    def _rebuild_plan_from_record(self, record: TaskProgressRecord) -> Optional[TaskPlan]:
        """Rebuild plan from database record"""
        try:
            plan_data = record.plan_data
            plan = TaskPlan(
                task_id=plan_data["task_id"],
                user_request=plan_data["user_request"],
                complexity=TaskComplexity(plan_data["complexity"]),
                status=TaskStatus(plan_data["status"]),
                wallet_address=record.wallet_address,
                conversation_id=record.conversation_id,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )

            # Rebuild steps
            for step_data in plan_data.get("steps", []):
                step = TaskStep(
                    step_id=step_data["step_id"],
                    name=step_data["name"],
                    description=step_data["description"],
                    action=step_data.get("action", "execute"),
                    params=step_data.get("params", {}),
                    dependencies=step_data.get("dependencies", []),
                    estimated_time=step_data.get("estimated_time", 30),
                    status=StepStatus(step_data.get("status", "pending")) if isinstance(step_data.get("status"), str) else StepStatus.PENDING
                )
                plan.steps.append(step)

            self._active_tasks[plan.task_id] = plan
            return plan
        except Exception as e:
            logger.error(f"[TaskExecutor] Failed to rebuild plan: {e}")
            return None

    def get_tasks_by_wallet(self, wallet_address: str) -> List[TaskPlan]:
        """Get all tasks for a wallet"""
        tasks = []

        # From memory
        for task in self._active_tasks.values():
            if task.wallet_address == wallet_address:
                tasks.append(task)

        # From database
        if self._progress_store:
            records = self._progress_store.get_tasks_by_wallet(wallet_address)
            for record in records:
                if record.task_id not in self._active_tasks:
                    rebuilt = self._rebuild_plan_from_record(record)
                    if rebuilt:
                        tasks.append(rebuilt)

        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        task = self._active_tasks.get(task_id)
        if task and task.status == TaskStatus.EXECUTING:
            task.status = TaskStatus.CANCELLED
            task.updated_at = datetime.now()

            if self._progress_store:
                self._progress_store.update_task_status(
                    task_id, TaskStatus.CANCELLED.value, len(task.get_completed_steps())
                )

            return True
        return False

    def confirm_plan(self, task_id: str) -> bool:
        """Confirm plan execution"""
        task = self._active_tasks.get(task_id)
        if task and task.status == TaskStatus.AWAITING_CONFIRM:
            task.status = TaskStatus.EXECUTING
            task.updated_at = datetime.now()

            if self._progress_store:
                self._progress_store.update_task_status(
                    task_id, TaskStatus.EXECUTING.value, 0
                )

            return True
        return False

    def modify_plan(
        self,
        task_id: str,
        modifications: Dict[str, Any],
    ) -> Optional[TaskPlan]:
        """Modify task plan"""
        task = self._active_tasks.get(task_id)
        if not task:
            return None

        task.updated_at = datetime.now()

        if self._progress_store and task.wallet_address:
            record = TaskProgressRecord(
                task_id=task.task_id,
                wallet_address=task.wallet_address,
                conversation_id=task.conversation_id or "",
                user_request=task.user_request,
                complexity=task.complexity.value,
                status=task.status.value,
                total_steps=len(task.steps),
                completed_steps=len(task.get_completed_steps()),
                created_at=task.created_at,
                updated_at=task.updated_at,
                plan_data=task.to_dict(),
            )
            self._progress_store.save_task(record)

        return task
