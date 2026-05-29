"""
InMemoryTaskStore - 内存存储实现
"""

import asyncio
from typing import Any

from usmsb_sdk.protocol.types.google_a2a import Task
from usmsb_sdk.protocol.google_a2a.persistence.base import TaskStore


class InMemoryTaskStore(TaskStore):
    """
    内存存储（默认）

    适用于单进程场景，生产环境建议使用持久化存储。
    """

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._lock = asyncio.Lock()

    async def get(self, task_id: str) -> Task | None:
        async with self._lock:
            return self._tasks.get(task_id)

    async def save(self, task: Task) -> None:
        async with self._lock:
            self._tasks[task.id] = task

    async def update(self, task_id: str, task: Task) -> None:
        async with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id] = task

    async def delete(self, task_id: str) -> bool:
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                return True
            return False

    async def list(
        self,
        page: int = 0,
        page_size: int = 50,
        query: str | None = None,
    ) -> tuple[list[Task], int]:
        async with self._lock:
            tasks = list(self._tasks.values())
            total = len(tasks)

            # 简单的查询过滤
            if query:
                query_lower = query.lower()
                tasks = [
                    t for t in tasks
                    if query_lower in t.id.lower()
                    or query_lower in t.context_id.lower()
                ]

            # 分页
            start = page * page_size
            end = start + page_size
            return tasks[start:end], total

    async def exists(self, task_id: str) -> bool:
        async with self._lock:
            return task_id in self._tasks
