"""
SQLiteTaskStore - SQLite 持久化实现
"""

import aiosqlite
import json
import asyncio
from datetime import datetime

from usmsb_sdk.protocol.types.google_a2a import Task
from usmsb_sdk.protocol.google_a2a.persistence.base import TaskStore


class SQLiteTaskStore(TaskStore):
    """
    SQLite 持久化

    适用于单机部署或轻量级生产环境。
    """

    def __init__(self, db_path: str = "a2a_tasks.db"):
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def _ensure_table(self) -> None:
        """确保表存在"""
        async with self._lock:
            if self._conn is None:
                self._conn = await aiosqlite.connect(self._db_path)
                await self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id TEXT PRIMARY KEY,
                        context_id TEXT,
                        status TEXT,
                        artifacts TEXT,
                        history TEXT,
                        metadata TEXT,
                        created_at REAL,
                        updated_at REAL
                    )
                """)
                await self._conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_context_id ON tasks(context_id)
                """)
                await self._conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)
                """)
                await self._conn.commit()

    async def _get_conn(self) -> aiosqlite.Connection:
        await self._ensure_table()
        return self._conn

    def _task_to_row(self, task: Task) -> tuple:
        """将 Task 转为数据库行"""
        return (
            task.id,
            task.context_id,
            task.status.model_dump_json() if task.status else None,
            json.dumps([a.model_dump() for a in task.artifacts]) if task.artifacts else "[]",
            json.dumps([m.model_dump() for m in task.history]) if task.history else "[]",
            json.dumps(task.metadata) if task.metadata else "{}",
            task.metadata.get("_created_at", datetime.now().timestamp()),
            datetime.now().timestamp(),
        )

    async def get(self, task_id: str) -> Task | None:
        conn = await self._get_conn()
        async with self._lock:
            async with conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_task(row)

    def _row_to_task(self, row: tuple) -> Task:
        """将数据库行转为 Task"""
        from usmsb_sdk.protocol.types.google_a2a import TaskStatus, Artifact, Message

        task_id, context_id, status_json, artifacts_json, history_json, metadata_json, created_at, updated_at = row

        status = None
        if status_json:
            status = TaskStatus.model_validate_json(status_json)

        artifacts = []
        if artifacts_json:
            artifacts = [Artifact.model_validate(a) for a in json.loads(artifacts_json)]

        history = []
        if history_json:
            history = [Message.model_validate(m) for m in json.loads(history_json)]

        metadata = {}
        if metadata_json:
            metadata = json.loads(metadata_json)
        metadata["_created_at"] = created_at

        return Task(
            id=task_id,
            context_id=context_id or "",
            status=status,
            artifacts=artifacts,
            history=history,
            metadata=metadata,
        )

    async def save(self, task: Task) -> None:
        conn = await self._get_conn()
        row = self._task_to_row(task)
        async with self._lock:
            await conn.execute(
                """
                INSERT OR REPLACE INTO tasks
                (id, context_id, status, artifacts, history, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                row,
            )
            await conn.commit()

    async def update(self, task_id: str, task: Task) -> None:
        conn = await self._get_conn()
        row = self._task_to_row(task)
        async with self._lock:
            await conn.execute(
                """
                UPDATE tasks SET
                context_id = ?, status = ?, artifacts = ?, history = ?,
                metadata = ?, updated_at = ?
                WHERE id = ?
                """,
                row[1:] + (task_id,),
            )
            await conn.commit()

    async def delete(self, task_id: str) -> bool:
        conn = await self._get_conn()
        async with self._lock:
            cursor = await conn.execute(
                "DELETE FROM tasks WHERE id = ?", (task_id,)
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def list(
        self,
        page: int = 0,
        page_size: int = 50,
        query: str | None = None,
    ) -> tuple[list[Task], int]:
        conn = await self._get_conn()

        # 构建查询
        sql = "SELECT * FROM tasks"
        params: list = []

        if query:
            sql += " WHERE id LIKE ? OR context_id LIKE ?"
            q = f"%{query}%"
            params = [q, q]

        # 获取总数
        count_sql = f"SELECT COUNT(*) FROM ({sql})"
        async with conn.execute(count_sql, params) as cursor:
            row = await cursor.fetchone()
            total = row[0] if row else 0

        # 分页
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([page_size, page * page_size])

        async with conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

        tasks = [self._row_to_task(row) for row in rows]
        return tasks, total

    async def exists(self, task_id: str) -> bool:
        conn = await self._get_conn()
        async with self._lock:
            async with conn.execute(
                "SELECT 1 FROM tasks WHERE id = ? LIMIT 1", (task_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None

    async def close(self) -> None:
        async with self._lock:
            if self._conn:
                await self._conn.close()
                self._conn = None
