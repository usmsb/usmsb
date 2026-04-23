# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
"""
ChatSession - 核心会话管理

OpenHarness 精髓在这个模块的应用：

1. StreamEvent 模式:
   - chat_stream() 返回 AsyncIterator[ChatStreamEvent]
   - 每个事件携带增量数据，前端实时渲染

2. QueryEngine 的 Agent Loop:
   - 自动处理 LLM 调用循环
   - 多轮工具调用支持

3. Hook 机制:
   - PreTool/PostTool 钩子用于自我观察
   - 进度钩子用于实时推送

Usage:
    >>> session = ChatSession(wallet_address="0x...", meta_agent=agent)
    >>> async for event in session.chat_stream("帮我写一个网站"):
    ...     print(event.to_sse_format())
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from .protocol import (
    ChatMessageType,
    ChatEventType,
    ChatStreamEvent,
    ChatSessionState,
    TaskType,
    ToolCallEvent,
    ToolResultEvent,
    ProgressEvent,
    PlanReadyEvent,
)

logger = logging.getLogger(__name__)


@dataclass
class TaskContext:
    """
    任务执行上下文

    包含当前任务的全部状态
    """

    task_id: str
    task_type: TaskType
    user_message: str
    wallet_address: str | None
    state: ChatSessionState = ChatSessionState.IDLE
    plan_id: str | None = None
    current_step: int = 0
    total_steps: int = 0
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None

    @property
    def elapsed_seconds(self) -> float:
        """已执行时间"""
        if self.started_at is None:
            return 0.0
        end = self.completed_at or time.time()
        return end - self.started_at


class ChatSession:
    """
    核心会话管理类

    OpenHarness 精髓:
    1. 流式事件驱动 - 所有输出通过 AsyncIterator[ChatStreamEvent] 返回
    2. 状态机管理 - IDLE → PROCESSING → STREAMING → COMPLETE
    3. 工具调用循环 - 自动处理多轮 tool call
    4. Hook 机制 - 进度推送、自我观察

    Attributes:
        session_id: 会话唯一标识
        wallet_address: 钱包地址
        meta_agent: MetaAgent 实例
        state: 当前状态
        current_task: 当前任务上下文
    """

    def __init__(
        self,
        session_id: str,
        wallet_address: str | None,
        meta_agent: Any,  # MetaAgent type
    ):
        self.session_id = session_id
        self.wallet_address = wallet_address
        self.meta_agent = meta_agent
        self.state = ChatSessionState.IDLE
        self.current_task: TaskContext | None = None

        # SSE 订阅者
        self._sse_subscribers: set[asyncio.Queue] = set()

        # 统计
        self.stats = {
            "messages_processed": 0,
            "tool_calls": 0,
            "total_stream_events": 0,
        }

        logger.info(f"[ChatSession] {session_id} created for {wallet_address}")

    # ==================== Public API ====================

    async def chat_stream(
        self,
        message: str,
        task_type: TaskType | None = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        """
        核心聊天方法 - 流式版本

        OpenHarness StreamEvent 模式：
        - 返回 AsyncIterator，逐步 yield 事件
        - 每个事件携带增量数据
        - 前端可以实时渲染

        Args:
            message: 用户消息
            task_type: 任务类型（自动检测如果为 None）

        Yields:
            ChatStreamEvent: 流式事件
        """
        # 1. 状态转换
        self.state = ChatSessionState.PROCESSING
        self.stats["messages_processed"] += 1

        # 2. 创建任务上下文
        task_type = task_type or await self._detect_task_type(message)
        task_id = f"task_{int(time.time() * 1000)}"
        self.current_task = TaskContext(
            task_id=task_id,
            task_type=task_type,
            user_message=message,
            wallet_address=self.wallet_address,
        )

        # 3. 发送任务开始事件
        yield ChatStreamEvent(
            event_type=ChatEventType.TASK_START,
            data={"task_id": task_id, "task_type": task_type.value},
            metadata={"session_id": self.session_id},
        )

        # 4. 根据任务类型处理
        if task_type == TaskType.SIMPLE:
            async for event in self._handle_simple(message, task_id):
                yield event
        elif task_type == TaskType.TOOL_BASED:
            async for event in self._handle_tool_based(message, task_id):
                yield event
        elif task_type == TaskType.PLAN_BASED:
            async for event in self._handle_plan_based(message, task_id):
                yield event
        elif task_type == TaskType.BACKGROUND:
            async for event in self._handle_background(message, task_id):
                yield event

        # 5. 发送任务完成事件
        self.state = ChatSessionState.COMPLETE
        self.current_task.completed_at = time.time()

        yield ChatStreamEvent(
            event_type=ChatEventType.TASK_COMPLETE,
            data={
                "task_id": task_id,
                "elapsed_seconds": self.current_task.elapsed_seconds,
            },
            metadata={"session_id": self.session_id},
            done=True,
        )

    async def confirm_plan(
        self,
        plan_id: str,
    ) -> AsyncIterator[ChatStreamEvent]:
        """
        确认执行计划

        用户通过 WebSocket 发送确认后调用

        Args:
            plan_id: 计划 ID

        Yields:
            ChatStreamEvent: 执行过程中的事件
        """
        if not self.current_task:
            yield ChatStreamEvent(
                event_type=ChatEventType.ERROR,
                data={"message": "No active task"},
                done=True,
            )
            return

        self.state = ChatSessionState.PROCESSING

        yield ChatStreamEvent(
            event_type=ChatEventType.PLAN_CONFIRMED,
            data={"plan_id": plan_id},
            metadata={"session_id": self.session_id},
        )

        # 执行计划（使用 TaskExecutor）
        async for event in self._execute_plan_stream(plan_id):
            yield event

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务 ID

        Returns:
            是否成功取消
        """
        if not self.current_task or self.current_task.task_id != task_id:
            return False

        self.state = ChatSessionState.IDLE
        self.current_task = None

        logger.info(f"[ChatSession] {self.session_id} cancelled task {task_id}")
        return True

    def get_state(self) -> dict:
        """获取当前状态"""
        return {
            "session_id": self.session_id,
            "wallet_address": self.wallet_address,
            "state": self.state.value,
            "current_task": {
                "task_id": self.current_task.task_id,
                "task_type": self.current_task.task_type.value,
                "state": self.current_task.state.value,
                "current_step": self.current_task.current_step,
                "total_steps": self.current_task.total_steps,
            } if self.current_task else None,
            "stats": self.stats,
        }

    # ==================== Task Type Detection ====================

    async def _detect_task_type(self, message: str) -> TaskType:
        """
        检测任务类型

        参考 OpenHarness 的复杂度检测逻辑

        检测规则：
        - SIMPLE: 简短问题，直接回答
        - TOOL_BASED: 需要工具调用
        - PLAN_BASED: 复杂任务，需要分步
        - BACKGROUND: 长时间运行，后台处理
        """
        # 简短消息 = SIMPLE
        if len(message.strip()) < 50:
            return TaskType.SIMPLE

        # 关键词检测
        simple_keywords = ["?", "是什么", "如何", "怎么", "什么", "who", "what", "how", "when", "where"]
        tool_keywords = ["创建", "删除", "修改", "执行", "运行", "build", "create", "delete", "execute", "run"]
        plan_keywords = ["网站", "项目", "系统", "应用", "复杂", "website", "project", "system", "complex"]
        background_keywords = ["训练", "分析", "爬取", "大规模", "train", "analyze", "scrape", "large scale"]

        message_lower = message.lower()

        # 后台任务优先检测
        for kw in background_keywords:
            if kw in message_lower:
                return TaskType.BACKGROUND

        # 计划任务检测
        for kw in plan_keywords:
            if kw in message_lower:
                return TaskType.PLAN_BASED

        # 工具任务检测
        for kw in tool_keywords:
            if kw in message_lower:
                return TaskType.TOOL_BASED

        return TaskType.SIMPLE

    # ==================== Task Handlers ====================

    async def _handle_simple(
        self,
        message: str,
        task_id: str,
    ) -> AsyncIterator[ChatStreamEvent]:
        """
        处理简单任务 - 直接 LLM 响应

        OpenHarness 精髓：
        - 流式文本输出 (text_delta)
        - 无需工具调用
        """
        # 发送开始流式输出
        yield ChatStreamEvent(
            event_type=ChatMessageType.STREAM_START,
            data={"task_id": task_id},
            metadata={"session_id": self.session_id},
        )

        self.state = ChatSessionState.STREAMING

        # 直接调用 LLM（简化版本）
        # 实际应该调用 meta_agent._call_llm_simple()
        try:
            # 添加超时保护，避免 LLM 调用挂起
            response = await asyncio.wait_for(
                self.meta_agent._call_llm_simple([
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": message},
                ]),
                timeout=10.0  # 10 秒超时
            )

            # 分块返回
            for i in range(0, len(response), 10):
                await asyncio.sleep(0.01)  # 模拟延迟
                yield ChatStreamEvent(
                    event_type=ChatEventType.TEXT_DELTA,
                    data={"text": response[i:i+10]},
                    metadata={"task_id": task_id},
                )

        except asyncio.TimeoutError:
            yield ChatStreamEvent(
                event_type=ChatEventType.ERROR,
                data={"message": "LLM 响应超时，请稍后重试。"},
                metadata={"task_id": task_id},
                done=True,
            )
            return
        except Exception as e:
            logger.error(f"[ChatSession] LLM error: {e}")
            yield ChatStreamEvent(
                event_type=ChatEventType.ERROR,
                data={"message": str(e)},
                metadata={"task_id": task_id},
                done=True,
            )
            return

        yield ChatStreamEvent(
            event_type=ChatEventType.TEXT_COMPLETE,
            data=None,
            metadata={"task_id": task_id},
        )

    async def _handle_tool_based(
        self,
        message: str,
        task_id: str,
    ) -> AsyncIterator[ChatStreamEvent]:
        """
        处理工具任务 - LLM + 工具调用

        OpenHarness 精髓：
        - TOOL_CALL 事件携带工具名称和参数
        - TOOL_RESULT 事件携带执行结果
        - 多轮循环直到 LLM 决定完成
        """
        yield ChatStreamEvent(
            event_type=ChatMessageType.STREAM_START,
            data={"task_id": task_id},
            metadata={"session_id": self.session_id},
        )

        self.state = ChatSessionState.STREAMING

        # 获取可用工具
        tools = self.meta_agent.tool_registry.get_tools_schema(
            provider=self._get_llm_provider()
        )

        # 初始化消息
        messages = await self._build_messages(message)

        # Agent Loop（参考 OpenHarness QueryEngine）
        max_turns = 8
        current_turn = 0

        while current_turn < max_turns:
            current_turn += 1

            # 调用 LLM
            chat_result = await self.meta_agent._chat_with_llm(
                messages,
                tools=tools,
                conversation_id=self.session_id,
            )

            # 检查是否有文本输出
            if chat_result.content:
                for text_chunk in self._chunk_text(chat_result.content):
                    yield ChatStreamEvent(
                        event_type=ChatEventType.TEXT_DELTA,
                        data={"text": text_chunk},
                        metadata={"task_id": task_id, "turn": current_turn},
                    )

            # 检查是否有工具调用
            if chat_result.executed_tools:
                for tool_result in chat_result.tool_results:
                    # TOOL_CALL
                    yield ChatStreamEvent(
                        event_type=ChatEventType.TOOL_CALL,
                        data={
                            "tool_name": tool_result.tool_name,
                            "tool_input": tool_result.tool_input,
                            "call_id": tool_result.call_id,
                        },
                        metadata={"task_id": task_id, "turn": current_turn},
                    )

                    # TOOL_RESULT
                    yield ChatStreamEvent(
                        event_type=ChatEventType.TOOL_RESULT,
                        data={
                            "tool_name": tool_result.tool_name,
                            "output": tool_result.output,
                            "is_error": tool_result.is_error,
                            "execution_time_ms": tool_result.execution_time_ms,
                            "call_id": tool_result.call_id,
                        },
                        metadata={"task_id": task_id, "turn": current_turn},
                    )

                    # 添加到消息历史
                    messages.append({
                        "role": "user",
                        "content": f"[Tool Result: {tool_result.tool_name}] {tool_result.output}"
                    })

                    self.stats["tool_calls"] += 1

            # 检查是否完成
            if chat_result.is_complete:
                break

        yield ChatStreamEvent(
            event_type=ChatEventType.TEXT_COMPLETE,
            data=None,
            metadata={"task_id": task_id},
        )

    async def _handle_plan_based(
        self,
        message: str,
        task_id: str,
    ) -> AsyncIterator[ChatStreamEvent]:
        """
        处理计划任务 - 生成分步计划

        OpenHarness 精髓：
        - PLAN_GENERATING 事件推送生成进度
        - PLAN_READY 事件携带完整计划
        - 用户通过 WebSocket CONFIRM_PLAN 确认
        """
        yield ChatStreamEvent(
            event_type=ChatEventType.PLAN_GENERATING,
            data={"task_id": task_id, "message": "正在分析任务..."},
            metadata={"session_id": self.session_id},
        )

        # 使用 TaskExecutor 生成计划
        if not self.meta_agent.task_executor:
            yield ChatStreamEvent(
                event_type=ChatEventType.ERROR,
                data={"message": "TaskExecutor not available"},
                done=True,
            )
            return

        try:
            plan = await self.meta_agent.task_executor.analyze_and_plan(
                user_request=message,
                wallet_address=self.wallet_address,
                conversation_id=self.session_id,
            )

            # 更新任务上下文
            if self.current_task:
                self.current_task.plan_id = plan.plan_id
                self.current_task.total_steps = len(plan.steps)

            # 发送计划就绪事件
            yield ChatStreamEvent(
                event_type=ChatEventType.PLAN_READY,
                data=PlanReadyEvent(
                    task_id=task_id,
                    plan_id=plan.plan_id,
                    complexity=plan.complexity.value,
                    total_steps=len(plan.steps),
                    estimated_time_seconds=plan.estimated_time,
                    steps=[
                        {
                            "index": i,
                            "name": s.name,
                            "description": s.description,
                            "status": s.status.value,
                        }
                        for i, s in enumerate(plan.steps)
                    ],
                ).__dict__,
                metadata={"session_id": self.session_id},
            )

            # 等待确认（设置状态）
            self.state = ChatSessionState.AWAITING_CONFIRMATION

        except Exception as e:
            logger.error(f"[ChatSession] Plan generation failed: {e}")
            yield ChatStreamEvent(
                event_type=ChatEventType.ERROR,
                data={"message": f"计划生成失败: {str(e)}"},
                metadata={"task_id": task_id},
                done=True,
            )

    async def _handle_background(
        self,
        message: str,
        task_id: str,
    ) -> AsyncIterator[ChatStreamEvent]:
        """
        处理后台任务

        长时间运行任务，发送初始确认后后台执行
        """
        yield ChatStreamEvent(
            event_type=ChatEventType.TASK_START,
            data={
                "task_id": task_id,
                "message": "任务已提交后台执行",
                "check_status_url": f"/api/meta-agent/task/{task_id}/progress/stream",
            },
            metadata={"session_id": self.session_id},
        )

        # TODO: 启动后台任务处理
        # 实际应该使用 BackgroundTaskProcessor

        yield ChatStreamEvent(
            event_type=ChatEventType.TASK_COMPLETE,
            data={"task_id": task_id, "background": True},
            metadata={"session_id": self.session_id},
            done=True,
        )

    # ==================== Plan Execution ====================

    async def _execute_plan_stream(
        self,
        plan_id: str,
    ) -> AsyncIterator[ChatStreamEvent]:
        """
        执行计划 - 流式版本

        每个步骤开始/完成都推送事件
        """
        if not self.meta_agent.task_executor:
            yield ChatStreamEvent(
                event_type=ChatEventType.ERROR,
                data={"message": "TaskExecutor not available"},
                done=True,
            )
            return

        self.state = ChatSessionState.PROCESSING

        try:
            result = await self.meta_agent.task_executor.execute_plan_stream(plan_id)

            async for step_event in result:
                yield ChatStreamEvent(
                    event_type=ChatEventType.STEP_COMPLETE if step_event.get("complete") else ChatEventType.STEP_START,
                    data=step_event,
                    metadata={"plan_id": plan_id},
                )

                # 更新进度
                if self.current_task:
                    self.current_task.current_step = step_event.get("step_index", 0)
                    percentage = (self.current_task.current_step / self.current_task.total_steps) * 100

                    yield ChatStreamEvent(
                        event_type=ChatEventType.PROGRESS,
                        data=ProgressEvent(
                            task_id=plan_id,
                            step_index=self.current_task.current_step,
                            total_steps=self.current_task.total_steps,
                            percentage=percentage,
                        ).__dict__,
                        metadata={"session_id": self.session_id},
                    )

        except Exception as e:
            logger.error(f"[ChatSession] Plan execution failed: {e}")
            yield ChatStreamEvent(
                event_type=ChatEventType.TASK_FAILED,
                data={"error": str(e)},
                metadata={"plan_id": plan_id},
                done=True,
            )

    # ==================== Helper Methods ====================

    async def _call_llm_streaming(self, message: str, wallet_address: str | None) -> AsyncIterator[str]:
        """
        调用 LLM 并返回流式文本

        简化版本 - 实际应该使用 meta_agent._call_llm_simple()
        """
        try:
            response = await self.meta_agent._call_llm_simple([
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": message},
            ])

            # 分块返回
            for i in range(0, len(response), 10):
                await asyncio.sleep(0.01)  # 模拟延迟
                yield response[i:i+10]

        except Exception as e:
            yield f"Error: {str(e)}"

    async def _build_messages(self, message: str) -> list[dict]:
        """构建消息列表"""
        # 获取对话历史
        if self.meta_agent.conversation_manager:
            conversation = await self.meta_agent.conversation_manager.get_or_create_conversation(
                owner_id=self.wallet_address or "anonymous",
                owner_type=self.meta_agent.memory.conversation.ParticipantType.HUMAN,
            )
            history = await self.meta_agent.conversation_manager.get_messages_for_llm(
                conversation_id=conversation.id,
                accessor_id=self.wallet_address or "anonymous",
                max_tokens=80000,
            )
        else:
            history = []

        messages = []
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})

        return messages

    def _get_llm_provider(self) -> str:
        """获取 LLM provider"""
        if self.meta_agent.llm_manager:
            if self.meta_agent.llm_manager.provider == "minimax":
                return "anthropic"  # MiniMax 兼容 Claude 格式
        return "openai"

    def _chunk_text(self, text: str, chunk_size: int = 10) -> AsyncIterator[str]:
        """将文本分块"""
        for i in range(0, len(text), chunk_size):
            yield text[i:i+chunk_size]
