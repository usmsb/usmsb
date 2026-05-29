"""
GoogleA2AHandler - Google A2A 协议处理器核心实现

完整实现 Google A2A Spec 1.0
"""

import asyncio
import logging
import time
import uuid
from typing import Any, AsyncIterator, Callable

from usmsb_sdk.protocol.types.google_a2a import (
    TaskState,
    Role,
    MessageType,
    Part,
    Message,
    TaskStatus,
    Artifact,
    Task,
    AgentCard,
    SendMessageRequest,
    GetTaskRequest,
    CancelTaskRequest,
    ListTasksRequest,
    SubscribeToTaskRequest,
)
from usmsb_sdk.protocol.google_a2a.persistence.base import TaskStore
from usmsb_sdk.protocol.google_a2a.persistence.memory import InMemoryTaskStore
from usmsb_sdk.protocol.google_a2a.events.event_queue import EventQueue, TaskStatusUpdateEvent
from usmsb_sdk.protocol.google_a2a.events.sse_streamer import SSEStreamer
from usmsb_sdk.protocol.google_a2a.events.push_notifier import PushNotifier
from usmsb_sdk.protocol.google_a2a.request_handlers.interceptor import InterceptorChain, InterceptorContext

logger = logging.getLogger(__name__)


class AgentExecutor:
    """
    Agent 执行器接口

    用户需要实现此接口来执行实际的任务。
    """

    async def execute(
        self,
        task_id: str,
        message: Message,
        context_id: str,
    ) -> AsyncIterator[TaskStatus] | TaskStatus:
        """
        执行任务

        Args:
            task_id: 任务 ID
            message: 消息内容
            context_id: 上下文 ID

        Returns:
            TaskStatus 或 TaskStatus 的异步迭代器（用于流式更新）
        """
        raise NotImplementedError

    async def cancel(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务 ID

        Returns:
            是否成功取消
        """
        raise NotImplementedError


class SimpleAgentExecutor(AgentExecutor):
    """
    简单同步执行器

    适用于简单的同步执行场景。
    """

    def __init__(
        self,
        handler: Callable[[Message], Any],
        is_async: bool = False,
    ):
        self._handler = handler
        self._is_async = is_async

    async def execute(
        self,
        task_id: str,
        message: Message,
        context_id: str,
    ) -> TaskStatus:
        try:
            if self._is_async:
                result = await self._handler(message)
            else:
                result = self._handler(message)

            return TaskStatus(
                state=TaskState.COMPLETED,
                message=Message(
                    message_id=str(uuid.uuid4()),
                    task_id=task_id,
                    role=Role.AGENT,
                    parts=[Part(text=str(result))],
                ),
            )
        except Exception as e:
            return TaskStatus(
                state=TaskState.FAILED,
                message=Message(
                    message_id=str(uuid.uuid4()),
                    task_id=task_id,
                    role=Role.AGENT,
                    parts=[Part(text=f"Error: {e}")],
                ),
            )

    async def cancel(self, task_id: str) -> bool:
        return True


class GoogleA2AHandler:
    """
    Google A2A 协议处理器 - 完整实现 Spec 1.0

    核心方法：
    - on_send_task()         → 处理 tasks/send
    - on_get_task()          → 处理 tasks/get
    - on_cancel_task()       → 处理 tasks/cancel
    - on_list_tasks()        → 处理 tasks/list
    - on_subscribe_task()    → 处理 tasks/subscribe (SSE)
    - on_get_agent_card()     → 处理 agents/card
    - on_get_extended_agent_card() → 处理 agents/extended_card

    Task 状态机（Spec 1.0）：
    submitted → working → completed
                          → failed
                          → input-required (等待用户输入)
                          → canceled
                          → rejected
                          → auth-required
    """

    WELL_KNOWN_PATH = "/.well-known/agent.json"

    def __init__(
        self,
        agent_card: AgentCard,
        agent_executor: AgentExecutor,
        task_store: TaskStore | None = None,
        event_queue: EventQueue | None = None,
        push_notifier: PushNotifier | None = None,
        extended_agent_card: AgentCard | None = None,
        interceptor_chain: InterceptorChain | None = None,
    ):
        self._agent_card = agent_card
        self._agent_executor = agent_executor
        self._task_store = task_store or InMemoryTaskStore()
        self._event_queue = event_queue or EventQueue()
        self._sse_streamer = SSEStreamer(self._event_queue)
        self._push_notifier = push_notifier or PushNotifier()
        self._extended_agent_card = extended_agent_card
        self._interceptor_chain = interceptor_chain or InterceptorChain()
        self._running_tasks: dict[str, asyncio.Task] = {}

    @property
    def agent_card(self) -> AgentCard:
        """获取 AgentCard"""
        return self._agent_card

    @property
    def extended_agent_card(self) -> AgentCard | None:
        """获取扩展 AgentCard"""
        return self._extended_agent_card

    # === JSON-RPC 请求处理 ===

    async def on_send_task(
        self,
        params: SendMessageRequest,
    ) -> Task | AsyncIterator[Task]:
        """
        处理 tasks/send 请求

        流程：
        1. 验证请求
        2. 创建或获取 Task
        3. 启动 AgentExecutor.execute()
        4. 返回 Task 或 SSE 流
        """
        context = InterceptorContext(
            method="tasks/send",
            params=params.model_dump(),
        )

        async def do_send() -> Task | AsyncIterator[Task]:
            # 创建或更新任务
            task = await self._get_or_create_task(params)

            # 如果配置了 return_immediately 且支持流式，立即返回流
            config = params.configuration
            if config and config.return_immediately and self._agent_card.capabilities.streaming:
                return self._stream_task_execution(task.id)

            # 执行任务
            await self._execute_task(task.id, params.message)
            task = await self._task_store.get(task.id)
            return task

        return await self._interceptor_chain.execute(context, do_send)

    async def on_get_task(self, params: GetTaskRequest) -> Task | None:
        """处理 tasks/get 请求"""
        context = InterceptorContext(
            method="tasks/get",
            params=params.model_dump(),
        )

        async def do_get() -> Task | None:
            return await self._task_store.get(params.task_id)

        return await self._interceptor_chain.execute(context, do_get)

    async def on_cancel_task(self, params: CancelTaskRequest) -> Task | None:
        """处理 tasks/cancel 请求"""
        context = InterceptorContext(
            method="tasks/cancel",
            params=params.model_dump(),
        )

        async def do_cancel() -> Task | None:
            task = await self._task_store.get(params.task_id)
            if not task:
                return None

            # 取消运行中的任务
            if params.task_id in self._running_tasks:
                running_task = self._running_tasks[params.task_id]
                running_task.cancel()
                del self._running_tasks[params.task_id]

            # 更新任务状态
            task.status = TaskStatus(
                state=TaskState.CANCELED,
                timestamp=time.time(),
            )
            await self._task_store.update(params.task_id, task)

            # 推送状态更新
            await self._push_status_update(params.task_id, task)

            return task

        return await self._interceptor_chain.execute(context, do_cancel)

    async def on_list_tasks(self, params: ListTasksRequest) -> tuple[list[Task], int]:
        """处理 tasks/list 请求"""
        context = InterceptorContext(
            method="tasks/list",
            params=params.model_dump(),
        )

        async def do_list() -> tuple[list[Task], int]:
            return await self._task_store.list(
                page=params.page or 0,
                page_size=params.page_size or 50,
                query=params.query,
            )

        return await self._interceptor_chain.execute(context, do_list)

    async def on_subscribe_task(
        self,
        params: SubscribeToTaskRequest,
    ) -> AsyncIterator[TaskStatusUpdateEvent]:
        """
        SSE 流式订阅任务更新

        响应：text/event-stream
        事件类型：
        - task_status: 状态变更
        - artifact_update: 新产物
        - message: 新消息
        """
        queue = await self._event_queue.subscribe(params.task_id)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            await self._event_queue.unsubscribe(params.task_id, queue)

    async def on_get_agent_card(self) -> AgentCard:
        """处理 agents/card 请求"""
        return self._agent_card

    async def on_get_extended_agent_card(self) -> AgentCard | None:
        """处理 agents/extended_card 请求"""
        return self._extended_agent_card

    # === 内部方法 ===

    async def _get_or_create_task(self, params: SendMessageRequest) -> Task:
        """获取或创建任务"""
        message = params.message
        context_id = message.context_id or str(uuid.uuid4())

        # 如果有 task_id，获取现有任务
        if message.task_id:
            task = await self._task_store.get(message.task_id)
            if task:
                return task

        # 创建新任务
        task_id = message.task_id or str(uuid.uuid4())
        task = Task(
            id=task_id,
            context_id=context_id,
            status=TaskStatus(
                state=TaskState.SUBMITTED,
                message=message,
                timestamp=time.time(),
            ),
            metadata={"skill_id": params.skill_id} if params.skill_id else {},
        )
        await self._task_store.save(task)
        return task

    async def _execute_task(self, task_id: str, message: Message) -> None:
        """异步执行任务，更新状态"""
        # 更新为 working 状态
        task = await self._task_store.get(task_id)
        if not task:
            return

        task.status = TaskStatus(
            state=TaskState.WORKING,
            timestamp=time.time(),
        )
        await self._task_store.update(task_id, task)
        await self._push_status_update(task_id, task)

        # 在后台执行任务
        bg_task = asyncio.create_task(self._run_executor(task_id, message))
        self._running_tasks[task_id] = bg_task

    async def _run_executor(self, task_id: str, message: Message) -> None:
        """运行执行器"""
        try:
            result = await self._agent_executor.execute(
                task_id=task_id,
                message=message,
                context_id=task_id,  # 临时使用 task_id 作为 context_id
            )

            task = await self._task_store.get(task_id)
            if not task:
                return

            # 处理流式结果
            if hasattr(result, "__aiter__"):
                async for status_update in result:
                    await self._handle_status_update(task_id, status_update)
            else:
                await self._handle_status_update(task_id, result)

        except asyncio.CancelledError:
            logger.info(f"Task cancelled: {task_id}")
            task = await self._task_store.get(task_id)
            if task:
                task.status = TaskStatus(
                    state=TaskState.CANCELED,
                    timestamp=time.time(),
                )
                await self._task_store.update(task_id, task)
                await self._push_status_update(task_id, task)
        except Exception as e:
            logger.error(f"Task execution error: {task_id}, error={e}")
            task = await self._task_store.get(task_id)
            if task:
                task.status = TaskStatus(
                    state=TaskState.FAILED,
                    message=Message(
                        message_id=str(uuid.uuid4()),
                        task_id=task_id,
                        role=Role.AGENT,
                        parts=[Part(text=f"Error: {e}")],
                    ),
                    timestamp=time.time(),
                )
                await self._task_store.update(task_id, task)
                await self._push_status_update(task_id, task)
        finally:
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]

    async def _handle_status_update(self, task_id: str, status: TaskStatus) -> None:
        """处理状态更新"""
        task = await self._task_store.get(task_id)
        if not task:
            return

        task.status = status
        await self._task_store.update(task_id, task)
        await self._push_status_update(task_id, task)

    async def _push_status_update(self, task_id: str, task: Task) -> None:
        """推送状态更新到 SSE 队列和 Webhook"""
        # SSE 推送
        event = TaskStatusUpdateEvent(
            task_id=task_id,
            event_type="status",
            data={
                "state": task.status.state.value,
                "timestamp": task.status.timestamp,
            },
        )
        await self._event_queue.push(task_id, event)

        # Webhook 推送（如果配置了）
        # TODO: 从任务配置中获取 push_notification_config

    async def _stream_task_execution(self, task_id: str) -> AsyncIterator[Task]:
        """流式执行任务"""
        task = await self._task_store.get(task_id)
        if not task:
            return

        yield task

        # 等待任务完成
        while task_id in self._running_tasks:
            await asyncio.sleep(0.1)
            task = await self._task_store.get(task_id)
            if task:
                yield task

    def __repr__(self) -> str:
        return f"GoogleA2AHandler(agent={self._agent_card.name}, tasks={len(self._running_tasks)})"
