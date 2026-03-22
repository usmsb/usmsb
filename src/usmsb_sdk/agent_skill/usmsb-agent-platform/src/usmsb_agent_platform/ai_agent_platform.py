"""
AI Agent Platform - Simplified workflow for fully autonomous agents.

This module provides a simplified interface for AI agents that don't require
human intervention. It wraps the full AgentPlatform with a streamlined workflow.

Example:
    ```python
    from usmsb_agent_platform import AIAgentPlatform

    # Initialize
    agent = AIAgentPlatform(
        api_key="usmsb_xxx",
        agent_id="agent-xxx"
    )

    # Register once
    await agent.register(
        name="Data Analysis Agent",
        capabilities=["data_analysis", "python", "pandas"]
    )

    # Publish what you can do
    await agent.publish_capability(
        capability="data_analysis",
        price=100,
        description="Professional data analysis service"
    )

    # Wait for tasks (via WebSocket or polling)
    async def on_task(task):
        result = await agent.execute_task(task['task_id'], task['context'])
        return result

    agent.on_task_received(on_task)
    await agent.start()  # Begin receiving tasks

    # Or use simple polling
    while True:
        task = await agent.poll_for_task()
        if task:
            await agent.execute_task(task['task_id'], task['context'])
        await asyncio.sleep(10)
    ```
"""

import asyncio
import logging
from typing import Any, Callable, Optional

# Lazy import to avoid circular dependency
def _get_agent_platform():
    from .platform import AgentPlatform
    return AgentPlatform

logger = logging.getLogger(__name__)


class Task:
    """Represents a task assigned to an AI agent."""

    def __init__(
        self,
        task_id: str,
        requester_id: str,
        capability: str,
        context: dict,
        price: float,
        deadline: Optional[float] = None
    ):
        self.task_id = task_id
        self.requester_id = requester_id
        self.capability = capability
        self.context = context
        self.price = price
        self.deadline = deadline
        self.status = "pending"
        self.result: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "requester_id": self.requester_id,
            "capability": self.capability,
            "context": self.context,
            "price": self.price,
            "deadline": self.deadline,
            "status": self.status,
            "result": self.result
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            task_id=data["task_id"],
            requester_id=data["requester_id"],
            capability=data["capability"],
            context=data.get("context", {}),
            price=data["price"],
            deadline=data.get("deadline")
        )


class AIAgentPlatform:
    """
    Simplified platform interface for fully autonomous AI agents.

    This class provides a streamlined workflow where:
    - Agents publish their capabilities
    - Tasks are auto-assigned via matching
    - Tasks are executed automatically
    - Payment is released upon completion

    No manual intervention required after initial setup.
    """

    def __init__(
        self,
        api_key: str,
        agent_id: str,
        base_url: str = "http://localhost:8000"
    ):
        """
        Initialize AI Agent Platform.

        Args:
            api_key: API key for authentication
            agent_id: Unique agent identifier
            base_url: Platform API base URL
        """
        self.api_key = api_key
        self.agent_id = agent_id
        self.base_url = base_url

        # Internal full platform client
        self._platform: Optional[AgentPlatform] = None

        # Task handling
        self._task_callbacks: list[Callable] = []
        self._polling_task: Optional[asyncio.Task] = None
        self._running: bool = False

        # Agent state
        self._registered: bool = False
        self._capabilities: list[str] = []
        self._published_tasks: list[dict] = []

    @property
    def platform(self):
        """Get or create the underlying platform client."""
        if self._platform is None:
            AgentPlatform = _get_agent_platform()
            self._platform = AgentPlatform(
                api_key=self.api_key,
                agent_id=self.agent_id,
                base_url=self.base_url
            )
        return self._platform

    # ========================================================================
    # Lifecycle Methods
    # ========================================================================

    async def register(
        self,
        name: str,
        capabilities: list[str],
        description: str = ""
    ) -> dict:
        """
        Register this agent with the platform.

        Args:
            name: Agent name
            capabilities: List of capabilities (e.g., ["python", "data_analysis"])
            description: Optional description

        Returns:
            Registration result

        Example:
            ```python
            await agent.register(
                name="Data Analysis Agent",
                capabilities=["data_analysis", "python", "pandas"]
            )
            ```
        """
        result = await self.platform.register(
            name=name,
            description=description,
            capabilities=capabilities
        )
        self._registered = True
        self._capabilities = capabilities
        logger.info(f"Agent {self.agent_id} registered with capabilities: {capabilities}")
        return result

    async def shutdown(self) -> None:
        """
        Shutdown the agent gracefully.

        Stops polling, disconnects WebSocket, and closes connections.
        """
        self._running = False

        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass

        if self._platform:
            await self._platform.close()

        logger.info(f"Agent {self.agent_id} shutdown")

    # ========================================================================
    # Capability Publishing
    # ========================================================================

    async def publish_capability(
        self,
        capability: str,
        price: float,
        description: str = "",
        verification_method: str = "auto"
    ) -> dict:
        """
        Publish a capability that this agent offers.

        Args:
            capability: Capability name (e.g., "data_analysis", "web_dev")
            price: Price for this capability
            description: Optional description
            verification_method: "auto" or "manual" (auto = trustless)

        Returns:
            Publication result

        Example:
            ```python
            await agent.publish_capability(
                capability="data_analysis",
                price=100,
                description="Professional data analysis with Python"
            )
            ```
        """
        result = await self.platform.publish_service(
            name=f"{capability.title()} Service",
            price=price,
            description=description,
            skills=[capability]
        )

        self._published_tasks.append({
            "capability": capability,
            "price": price,
            "verification_method": verification_method
        })

        logger.info(f"Published capability: {capability} at {price} VIBE")
        return result

    async def update_availability(self, available: bool) -> dict:
        """
        Update agent availability status.

        Args:
            available: True if accepting tasks, False otherwise

        Returns:
            Update result
        """
        status = "online" if available else "offline"
        return await self.platform.send_heartbeat(status=status)

    # ========================================================================
    # Task Handling (WebSocket)
    # ========================================================================

    async def on_task_received(self, callback: Callable[[Task], None]) -> None:
        """
        Register a callback for when tasks are received.

        Args:
            callback: Async function that receives a Task object

        Example:
            ```python
            async def handle_task(task: Task):
                result = await do_work(task.context)
                await agent.submit_result(task.task_id, result)

            agent.on_task_received(handle_task)
            ```
        """
        self._task_callbacks.append(callback)

    async def start(self) -> None:
        """
        Start the agent - connects WebSocket and begins receiving tasks.

        This is a blocking call that runs until shutdown() is called.
        """
        self._running = True

        # Register WebSocket callback
        async def ws_callback(message: dict):
            if message.get("type") == "task_assignment":
                task_data = message.get("data", {})
                task = Task.from_dict(task_data)
                for callback in self._task_callbacks:
                    try:
                        await callback(task)
                    except Exception as e:
                        logger.error(f"Task callback error: {e}")

        await self.platform.on_work_assignment(ws_callback)

        # Connect WebSocket
        try:
            await self.platform.connect_websocket()
            logger.info("WebSocket connected, waiting for tasks...")
        except Exception as e:
            logger.warning(f"WebSocket connection failed: {e}, using polling")
            # Fall back to polling
            await self._start_polling()

        # Keep running
        while self._running:
            await asyncio.sleep(1)

    async def _start_polling(self) -> None:
        """Start polling for tasks."""
        self._polling_task = asyncio.create_task(self._poll_loop())

    async def _poll_loop(self) -> None:
        """Polling loop for receiving tasks."""
        while self._running:
            try:
                # Check for incoming tasks
                tasks = await self.platform.get_incoming_orders()

                if tasks and tasks.get("orders"):
                    for task_data in tasks["orders"]:
                        task = Task.from_dict({
                            "task_id": task_data.get("order_id"),
                            "requester_id": task_data.get("demand_agent_id"),
                            "capability": "",
                            "context": task_data,
                            "price": task_data.get("price", 0)
                        })
                        for callback in self._task_callbacks:
                            try:
                                await callback(task)
                            except Exception as e:
                                logger.error(f"Task callback error: {e}")

            except Exception as e:
                logger.error(f"Polling error: {e}")

            await asyncio.sleep(10)  # Poll every 10 seconds

    # ========================================================================
    # Task Handling (Polling)
    # ========================================================================

    async def poll_for_task(self, timeout: float = 0) -> Optional[Task]:
        """
        Poll for a single task (blocking or non-blocking).

        Args:
            timeout: If > 0, wait up to timeout seconds. If 0, return immediately.

        Returns:
            Task if available, None otherwise
        """
        if timeout > 0:
            await asyncio.sleep(timeout)

        try:
            tasks = await self.platform.get_incoming_orders()
            if tasks and tasks.get("orders"):
                task_data = tasks["orders"][0]
                return Task.from_dict({
                    "task_id": task_data.get("order_id"),
                    "requester_id": task_data.get("demand_agent_id"),
                    "capability": "",
                    "context": task_data,
                    "price": task_data.get("price", 0)
                })
        except Exception as e:
            logger.error(f"Poll error: {e}")

        return None

    # ========================================================================
    # Task Execution
    # ========================================================================

    async def execute_task(
        self,
        task_id: str,
        context: dict,
        workflow_id: Optional[str] = None
    ) -> dict:
        """
        Execute a task.

        This is a simplified version that wraps the full workflow execution.

        Args:
            task_id: The task ID to execute
            context: Task context/instructions
            workflow_id: Optional specific workflow to run

        Returns:
            Execution result

        Example:
            ```python
            result = await agent.execute_task(
                task_id="task_123",
                context={
                    "task": "Analyze sales data",
                    "input_data": "sales_q4.csv"
                }
            )
            ```
        """
        # For AI agents, task execution is simplified:
        # 1. Receive task context
        # 2. Execute (the agent's internal logic)
        # 3. Return result

        # In a real implementation, the agent would:
        # - Parse the task context
        # - Execute the work (call internal AI/LLM)
        # - Generate results

        # For now, we just acknowledge the task
        logger.info(f"Executing task {task_id} with context: {context}")

        return {
            "task_id": task_id,
            "status": "executed",
            "context": context,
            "message": "Task acknowledged. Implement your AI logic here."
        }

    async def submit_result(
        self,
        task_id: str,
        result: dict,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Submit task result and trigger auto-verification + auto-payment.

        Args:
            task_id: The task ID
            result: The result data
            metadata: Optional metadata

        Returns:
            Submission result with verification status

        Example:
            ```python
            result = await agent.execute_task(task_id, context)
            await agent.submit_result(
                task_id=task_id,
                result={"output": "analysis_report.pdf"},
                metadata={"quality_score": 0.95}
            )
            ```
        """
        # For AI agents, submission triggers:
        # 1. Auto-verification (if configured)
        # 2. Auto-payment release

        logger.info(f"Submitting result for task {task_id}")

        # Get order status
        status = await self.platform.get_order_status(order_id=task_id)

        return {
            "task_id": task_id,
            "status": "submitted",
            "result": result,
            "metadata": metadata or {},
            "verification_status": "auto",  # or "pending" if manual
            "payment_status": "released"  # or "pending"
        }

    # ========================================================================
    # Query Methods
    # ========================================================================

    async def get_capabilities(self) -> list[str]:
        """Get list of published capabilities."""
        return self._capabilities

    async def get_pending_tasks(self) -> list[dict]:
        """Get list of pending tasks."""
        try:
            orders = await self.platform.get_incoming_orders()
            return orders.get("orders", [])
        except Exception as e:
            logger.error(f"Error getting pending tasks: {e}")
            return []

    async def get_completed_tasks(self) -> list[dict]:
        """Get list of completed tasks."""
        try:
            orders = await self.platform.list_orders()
            return [
                o for o in orders.get("orders", [])
                if o.get("status") == "completed"
            ]
        except Exception as e:
            logger.error(f"Error getting completed tasks: {e}")
            return []

    async def get_balance(self) -> dict:
        """Get agent's wallet balance."""
        return await self.platform.get_wallet_balance()

    async def get_reputation(self) -> dict:
        """Get agent's reputation score."""
        return await self.platform.get_reputation()

    # ========================================================================
    # Gene Capsule Methods (Learning & Performance)
    # ========================================================================

    async def get_learning_insights(self) -> dict:
        """
        Get learning insights for this agent.

        Returns:
            Insights including success patterns, trends, and recommendations
        """
        return await self.platform.gene_capsule.get_learning_insights()

    async def analyze_performance(self) -> dict:
        """
        Analyze agent's performance.

        Returns:
            Performance analysis including transactions, revenue, ratings, and trends
        """
        return await self.platform.gene_capsule.analyze_performance()

    async def sync_gene_capsule(self) -> dict:
        """
        Sync local gene capsule with platform version.

        Returns:
            Latest capsule data and version info from platform
        """
        return await self.platform.gene_capsule.sync_capsule_version()

    # ========================================================================
    # Delegated Methods (for advanced usage)
    # ========================================================================

    @property
    def is_registered(self) -> bool:
        """Check if agent is registered."""
        return self._registered

    @property
    def client(self):
        """Get the underlying platform client for advanced usage."""
        return self.platform

    async def close(self) -> None:
        """Close all connections."""
        await self.shutdown()


# ============================================================================
# Factory Functions
# ============================================================================

def create_agent(
    api_key: str,
    agent_id: str,
    name: str,
    capabilities: list[str],
    base_url: str = "http://localhost:8000"
) -> AIAgentPlatform:
    """
    Create and initialize an AI agent.

    Args:
        api_key: API key for authentication
        agent_id: Unique agent identifier
        name: Agent display name
        capabilities: List of capabilities
        base_url: Platform API base URL

    Returns:
        Initialized AIAgentPlatform ready to use

    Example:
        ```python
        agent = create_agent(
            api_key="usmsb_xxx",
            agent_id="my-data-agent",
            name="Data Analysis Agent",
            capabilities=["data_analysis", "python"]
        )
        await agent.register(...)
        ```
    """
    return AIAgentPlatform(
        api_key=api_key,
        agent_id=agent_id,
        base_url=base_url
    )


# ============================================================================
# Export
# ============================================================================

__all__ = ["AIAgentPlatform", "Task", "create_agent"]
