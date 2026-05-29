"""
EventQueue - 任务事件队列
"""

import asyncio
from typing import Any

from pydantic import BaseModel


class TaskStatusUpdateEvent(BaseModel):
    """任务状态更新事件"""
    task_id: str
    event_type: str  # "status", "artifact", "message"
    data: dict[str, Any]


class EventQueue:
    """
    SSE 事件队列管理器

    管理任务的 SSE 订阅者，支持：
    - 多订阅者订阅同一任务
    - 异步事件推送
    """

    def __init__(self):
        # task_id -> list of queues
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, task_id: str) -> asyncio.Queue:
        """
        订阅任务事件

        Args:
            task_id: 任务 ID

        Returns:
            asyncio.Queue: 事件队列
        """
        queue = asyncio.Queue()
        async with self._lock:
            if task_id not in self._subscribers:
                self._subscribers[task_id] = []
            self._subscribers[task_id].append(queue)
        return queue

    async def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        """
        取消订阅

        Args:
            task_id: 任务 ID
            queue: 要取消的队列
        """
        async with self._lock:
            if task_id in self._subscribers:
                if queue in self._subscribers[task_id]:
                    self._subscribers[task_id].remove(queue)
                if not self._subscribers[task_id]:
                    del self._subscribers[task_id]

    async def push(self, task_id: str, event: TaskStatusUpdateEvent) -> None:
        """
        推送事件到所有订阅者

        Args:
            task_id: 任务 ID
            event: 事件数据
        """
        async with self._lock:
            queues = self._subscribers.get(task_id, []).copy()

        for queue in queues:
            try:
                await queue.put(event)
            except Exception:
                # 忽略推送失败（如订阅者已断开）
                pass

    async def get_subscriber_count(self, task_id: str) -> int:
        """获取订阅者数量"""
        async with self._lock:
            return len(self._subscribers.get(task_id, []))
