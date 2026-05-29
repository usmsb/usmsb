"""
CustomA2A SQLite Task Store

SQLite-backed persistence for Custom A2A tasks.
"""

import aiosqlite
import json
import asyncio
from typing import Any

from usmsb_sdk.protocol.types.custom_a2a import CustomTask, CustomTaskStatus


class CustomTaskStore:
    """Abstract task store interface for Custom A2A."""

    async def get(self, task_id: str) -> CustomTask | None:
        raise NotImplementedError

    async def save(self, task: CustomTask) -> None:
        raise NotImplementedError

    async def update(self, task_id: str, task: CustomTask) -> None:
        raise NotImplementedError

    async def delete(self, task_id: str) -> bool:
        raise NotImplementedError

    async def list(
        self,
        page: int = 0,
        page_size: int = 50,
        query: str | None = None,
    ) -> tuple[list[CustomTask], int]:
        raise NotImplementedError

    async def exists(self, task_id: str) -> bool:
        raise NotImplementedError


class SQLiteCustomTaskStore(CustomTaskStore):
    """
    SQLite persistence for Custom A2A tasks.

    Schema:
    tasks (
        id TEXT PRIMARY KEY,
        task_id TEXT,
        delegator TEXT,
        delegatee TEXT,
        description TEXT,
        status TEXT,
        input_data TEXT,
        output_data TEXT,
        error TEXT,
        created_at REAL,
        accepted_at REAL,
        completed_at REAL,
        deadline REAL,
        reward REAL,
        currency TEXT,
        metadata TEXT
    )
    """

    def __init__(self, db_path: str = "custom_a2a_tasks.db"):
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
                        task_id TEXT,
                        delegator TEXT,
                        delegatee TEXT,
                        description TEXT,
                        status TEXT,
                        input_data TEXT,
                        output_data TEXT,
                        error TEXT,
                        created_at REAL,
                        accepted_at REAL,
                        completed_at REAL,
                        deadline REAL,
                        reward REAL,
                        currency TEXT,
                        metadata TEXT
                    )
                """)
                await self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tasks_delegator ON tasks(delegator)"
                )
                await self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tasks_delegatee ON tasks(delegatee)"
                )
                await self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)"
                )
                await self._conn.commit()

    async def _get_conn(self) -> aiosqlite.Connection:
        await self._ensure_table()
        return self._conn

    def _task_to_row(self, task: CustomTask) -> tuple:
        """将 CustomTask 转为数据库行"""
        return (
            task.id,
            task.task_id,
            task.delegator,
            task.delegatee,
            task.description,
            task.status.value if task.status else CustomTaskStatus.PENDING.value,
            json.dumps(task.input_data) if task.input_data else "{}",
            json.dumps(task.output_data) if task.output_data else None,
            task.error,
            task.created_at,
            task.accepted_at,
            task.completed_at,
            task.deadline,
            task.reward,
            task.currency,
            json.dumps(task.metadata) if task.metadata else "{}",
        )

    def _row_to_task(self, row: tuple) -> CustomTask:
        """将数据库行转为 CustomTask"""
        (
            id, task_id, delegator, delegatee, description, status,
            input_data, output_data, error, created_at, accepted_at,
            completed_at, deadline, reward, currency, metadata,
        ) = row

        return CustomTask(
            id=id,
            task_id=task_id or "",
            delegator=delegator or "",
            delegatee=delegatee or "",
            description=description or "",
            status=CustomTaskStatus(status) if status else CustomTaskStatus.PENDING,
            input_data=json.loads(input_data) if input_data else {},
            output_data=json.loads(output_data) if output_data else None,
            error=error,
            created_at=created_at,
            accepted_at=accepted_at,
            completed_at=completed_at,
            deadline=deadline,
            reward=reward or 0.0,
            currency=currency or "USDC",
            metadata=json.loads(metadata) if metadata else {},
        )

    async def get(self, task_id: str) -> CustomTask | None:
        conn = await self._get_conn()
        async with self._lock:
            async with conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_task(row)

    async def save(self, task: CustomTask) -> None:
        conn = await self._get_conn()
        row = self._task_to_row(task)
        async with self._lock:
            await conn.execute("""
                INSERT OR REPLACE INTO tasks
                (id, task_id, delegator, delegatee, description, status,
                 input_data, output_data, error, created_at, accepted_at,
                 completed_at, deadline, reward, currency, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, row)
            await conn.commit()

    async def update(self, task_id: str, task: CustomTask) -> None:
        conn = await self._get_conn()
        row = self._task_to_row(task)
        async with self._lock:
            await conn.execute("""
                UPDATE tasks SET
                task_id = ?, delegator = ?, delegatee = ?, description = ?,
                status = ?, input_data = ?, output_data = ?, error = ?,
                accepted_at = ?, completed_at = ?, deadline = ?, reward = ?,
                currency = ?, metadata = ?
                WHERE id = ?
            """, row[1:] + (task_id,))
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
    ) -> tuple[list[CustomTask], int]:
        conn = await self._get_conn()
        sql = "SELECT * FROM tasks"
        params: list[Any] = []

        if query:
            sql += " WHERE id LIKE ? OR task_id LIKE ? OR delegator LIKE ? OR delegatee LIKE ?"
            q = f"%{query}%"
            params = [q, q, q, q]

        count_sql = f"SELECT COUNT(*) FROM ({sql})"
        async with conn.execute(count_sql, params) as cursor:
            row = await cursor.fetchone()
            total = row[0] if row else 0

        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([page_size, page * page_size])

        async with conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()

        return [self._row_to_task(row) for row in rows], total

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


class InMemoryCustomTaskStore(CustomTaskStore):
    """In-memory task store (default for backwards compatibility)."""

    def __init__(self):
        self._tasks: dict[str, CustomTask] = {}
        self._lock = asyncio.Lock()

    async def get(self, task_id: str) -> CustomTask | None:
        async with self._lock:
            return self._tasks.get(task_id)

    async def save(self, task: CustomTask) -> None:
        async with self._lock:
            self._tasks[task.id] = task

    async def update(self, task_id: str, task: CustomTask) -> None:
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
    ) -> tuple[list[CustomTask], int]:
        async with self._lock:
            tasks = list(self._tasks.values())
            total = len(tasks)

            if query:
                q = query.lower()
                tasks = [
                    t for t in tasks
                    if q in t.id.lower() or q in t.task_id.lower()
                    or q in t.delegator.lower() or q in t.delegatee.lower()
                ]

            start = page * page_size
            end = start + page_size
            return tasks[start:end], total

    async def exists(self, task_id: str) -> bool:
        async with self._lock:
            return task_id in self._tasks
