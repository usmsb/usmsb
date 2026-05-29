"""
SSEServer - Standalone SSE Server

用于独立的 SSE 流式推送服务。
"""

import asyncio
import json
import logging
from typing import AsyncIterator

from usmsb_sdk.protocol.google_a2a.events.event_queue import EventQueue, TaskStatusUpdateEvent
from usmsb_sdk.protocol.google_a2a.events.sse_streamer import SSEStreamer


logger = logging.getLogger(__name__)


class SSEServer:
    """
    SSE Server

    独立的 SSE 流式推送服务，可单独使用。
    """

    def __init__(self, event_queue: EventQueue | None = None):
        self._event_queue = event_queue or EventQueue()
        self._streamer = SSEStreamer(self._event_queue)

    async def subscribe(self, task_id: str) -> AsyncIterator[str]:
        """
        订阅任务事件

        Args:
            task_id: 任务 ID

        Yields:
            SSE 格式的事件字符串
        """
        return self._streamer.stream(task_id)

    async def push_status_update(self, task_id: str, status_data: dict) -> None:
        """推送任务状态更新"""
        await self._streamer.push_status_update(task_id, status_data)

    async def push_artifact(self, task_id: str, artifact_data: dict) -> None:
        """推送产物更新"""
        await self._streamer.push_artifact(task_id, artifact_data)

    async def push_message(self, task_id: str, message_data: dict) -> None:
        """推送消息"""
        await self._streamer.push_message(task_id, message_data)
