"""
TaskStore 抽象接口 - Google A2A 任务持久化
"""

from abc import ABC, abstractmethod
from typing import Any

from usmsb_sdk.protocol.types.google_a2a import Task


class TaskStore(ABC):
    """
    Task 持久化接口

    定义任务存储的标准接口，支持多种后端实现。
    """

    @abstractmethod
    async def get(self, task_id: str) -> Task | None:
        """获取任务"""
        pass

    @abstractmethod
    async def save(self, task: Task) -> None:
        """保存任务"""
        pass

    @abstractmethod
    async def update(self, task_id: str, task: Task) -> None:
        """更新任务"""
        pass

    @abstractmethod
    async def delete(self, task_id: str) -> bool:
        """删除任务"""
        pass

    @abstractmethod
    async def list(
        self,
        page: int = 0,
        page_size: int = 50,
        query: str | None = None,
    ) -> tuple[list[Task], int]:
        """
        列出任务

        Returns:
            (tasks, total_count)
        """
        pass

    @abstractmethod
    async def exists(self, task_id: str) -> bool:
        """检查任务是否存在"""
        pass
