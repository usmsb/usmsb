"""
SSEStreamer - Server-Sent Events 流式推送
"""

import asyncio
import json
from typing import AsyncIterator

from usmsb_sdk.protocol.google_a2a.events.event_queue import EventQueue, TaskStatusUpdateEvent


class SSEStreamer:
    """
    SSE 流式推送

    用于：
    - 任务状态实时更新推送
    - 产物（Artifact）增量推送
    - 消息推送

    客户端订阅：GET /tasks/{task_id}/events
    响应：text/event-stream
    """

    def __init__(self, event_queue: EventQueue):
        self._event_queue = event_queue

    async def stream(self, task_id: str) -> AsyncIterator[str]:
        """
        订阅任务事件流

        Args:
            task_id: 任务 ID

        Yields:
            SSE 格式的事件字符串
        """
        queue = await self._event_queue.subscribe(task_id)

        try:
            yield f"event: connected\ndata: {json.dumps({'task_id': task_id})}\n\n"

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield self._format_event(event)
                except asyncio.TimeoutError:
                    # 发送心跳
                    yield f"event: heartbeat\ndata: {json.dumps({'task_id': task_id})}\n\n"
                except asyncio.CancelledError:
                    break
        finally:
            await self._event_queue.unsubscribe(task_id, queue)

    def _format_event(self, event: TaskStatusUpdateEvent) -> str:
        """将事件格式化为 SSE 格式"""
        data = {
            "task_id": event.task_id,
            "event_type": event.event_type,
            **event.data,
        }
        return f"event: {event.event_type}\ndata: {json.dumps(data)}\n\n"

    async def push_status_update(self, task_id: str, status_data: dict) -> None:
        """推送任务状态更新"""
        event = TaskStatusUpdateEvent(
            task_id=task_id,
            event_type="status",
            data=status_data,
        )
        await self._event_queue.push(task_id, event)

    async def push_artifact(self, task_id: str, artifact_data: dict) -> None:
        """推送产物更新"""
        event = TaskStatusUpdateEvent(
            task_id=task_id,
            event_type="artifact",
            data=artifact_data,
        )
        await self._event_queue.push(task_id, event)

    async def push_message(self, task_id: str, message_data: dict) -> None:
        """推送消息"""
        event = TaskStatusUpdateEvent(
            task_id=task_id,
            event_type="message",
            data=message_data,
        )
        await self._event_queue.push(task_id, event)
