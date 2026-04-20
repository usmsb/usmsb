# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
"""
SSEManager - SSE 进度通道

SSE 通道职责：
- 推送流式文本 (text_delta)
- 推送工具调用 (tool_call, tool_result)
- 推送进度更新 (progress, step_complete)
- 推送计划就绪 (plan_ready)

OpenHarness 精髓：
- Server-Sent Events 单向通道
- AsyncIterator[StreamEvent] 模式
- 每个事件携带增量数据
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator

from .protocol import ChatStreamEvent, ChatEventType

logger = logging.getLogger(__name__)


class SSEManager:
    """
    SSE 管理器

    职责：
    1. 管理 SSE 连接
    2. 为每个 session 创建 SSE 流
    3. 推送 ChatStreamEvent 到前端

    OpenHarness 精髓：
    - 使用 AsyncIterator 实现流式推送
    - 每个事件都是独立的增量数据
    - 前端通过 EventSource 接收

    Usage:
        # 前端
        const eventSource = new EventSource('/api/meta-agent/sse/chat/{session_id}');
        eventSource.addEventListener('text_delta', (e) => {
            const data = JSON.parse(e.data);
            document.getElementById('output').textContent += data.text;
        });

        # 后端推送
        async for event in sse_manager.create_stream(session_id):
            yield event.to_sse_format()
    """

    def __init__(self):
        self._queues: dict[str, asyncio.Queue] = {}  # session_id -> Queue
        self._running_sessions: set[str] = set()

    # ==================== Connection Management ====================

    def subscribe(self, session_id: str) -> asyncio.Queue:
        """
        订阅 session 的 SSE 事件

        Args:
            session_id: 会话 ID

        Returns:
            asyncio.Queue - 事件队列
        """
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue(maxsize=100)
        return self._queues[session_id]

    def unsubscribe(self, session_id: str) -> None:
        """
        取消订阅

        Args:
            session_id: 会话 ID
        """
        if session_id in self._queues:
            del self._queues[session_id]
        self._running_sessions.discard(session_id)

    # ==================== Event Broadcasting ====================

    async def push_event(self, session_id: str, event: ChatStreamEvent) -> None:
        """
        推送事件到 session

        Args:
            session_id: 会话 ID
            event: 流式事件
        """
        if session_id not in self._queues:
            return

        try:
            self._queues[session_id].put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(f"[SSEManager] Queue full for {session_id}, dropping event")

    async def push_text_delta(self, session_id: str, text: str, metadata: dict = None) -> None:
        """推送文本增量"""
        await self.push_event(
            session_id,
            ChatStreamEvent(
                event_type=ChatEventType.TEXT_DELTA,
                data={"text": text},
                metadata=metadata or {},
            ),
        )

    async def push_tool_call(
        self,
        session_id: str,
        tool_name: str,
        tool_input: dict,
        metadata: dict = None,
    ) -> None:
        """推送工具调用"""
        await self.push_event(
            session_id,
            ChatStreamEvent(
                event_type=ChatEventType.TOOL_CALL,
                data={
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                },
                metadata=metadata or {},
            ),
        )

    async def push_tool_result(
        self,
        session_id: str,
        tool_name: str,
        output: str,
        is_error: bool = False,
        metadata: dict = None,
    ) -> None:
        """推送工具结果"""
        await self.push_event(
            session_id,
            ChatStreamEvent(
                event_type=ChatEventType.TOOL_RESULT,
                data={
                    "tool_name": tool_name,
                    "output": output,
                    "is_error": is_error,
                },
                metadata=metadata or {},
            ),
        )

    async def push_progress(
        self,
        session_id: str,
        step_index: int,
        total_steps: int,
        message: str = None,
        metadata: dict = None,
    ) -> None:
        """推送进度更新"""
        percentage = (step_index / total_steps * 100) if total_steps > 0 else 0
        await self.push_event(
            session_id,
            ChatStreamEvent(
                event_type=ChatEventType.PROGRESS,
                data={
                    "step_index": step_index,
                    "total_steps": total_steps,
                    "percentage": percentage,
                    "message": message,
                },
                metadata=metadata or {},
            ),
        )

    async def push_plan_ready(
        self,
        session_id: str,
        plan_id: str,
        steps: list,
        estimated_time: int,
        metadata: dict = None,
    ) -> None:
        """推送计划就绪"""
        await self.push_event(
            session_id,
            ChatStreamEvent(
                event_type=ChatEventType.PLAN_READY,
                data={
                    "plan_id": plan_id,
                    "steps": steps,
                    "estimated_time_seconds": estimated_time,
                    "confirmation_phrase": "确认执行",
                },
                metadata=metadata or {},
            ),
        )

    async def push_error(self, session_id: str, error: str, metadata: dict = None) -> None:
        """推送错误"""
        await self.push_event(
            session_id,
            ChatStreamEvent(
                event_type=ChatEventType.ERROR,
                data={"error": error},
                metadata=metadata or {},
            ),
        )

    async def push_complete(self, session_id: str, metadata: dict = None) -> None:
        """推送完成"""
        await self.push_event(
            session_id,
            ChatStreamEvent(
                event_type=ChatEventType.STREAM_END,
                data=None,
                metadata=metadata or {},
                done=True,
            ),
        )

    # ==================== Stream Generation ====================

    async def create_stream(
        self,
        session_id: str,
    ) -> AsyncIterator[str]:
        """
        创建 SSE 流

        这是 FastAPI 的 SSE endpoint 调用的方法

        Args:
            session_id: 会话 ID

        Yields:
            SSE 格式的事件字符串
        """
        queue = self.subscribe(session_id)
        self._running_sessions.add(session_id)

        logger.info(f"[SSEManager] SSE stream started for {session_id}")

        try:
            while True:
                try:
                    # 等待事件
                    event: ChatStreamEvent = await asyncio.wait_for(
                        queue.get(),
                        timeout=30.0,
                    )

                    # 转换为 SSE 格式
                    yield event.to_sse_format()

                    # 检查是否结束
                    if event.done:
                        break

                except asyncio.TimeoutError:
                    # 发送心跳
                    yield f"data: {json.dumps({'event': 'heartbeat', 'data': None})}\n\n"
                    continue

        except asyncio.CancelledError:
            logger.info(f"[SSEManager] SSE stream cancelled for {session_id}")
        finally:
            self.unsubscribe(session_id)
            logger.info(f"[SSEManager] SSE stream ended for {session_id}")

    # ==================== Utility ====================

    def get_active_count(self) -> int:
        """获取活跃 SSE 连接数"""
        return len(self._running_sessions)

    def get_queue_size(self, session_id: str) -> int:
        """获取队列大小"""
        if session_id not in self._queues:
            return 0
        return self._queues[session_id].qsize()
