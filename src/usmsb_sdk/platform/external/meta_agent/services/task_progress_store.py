"""
任务进度存储服务

设计初衷：
============
复杂任务（如创建网站）需要分步执行，每步进度需要持久化存储：
1. 支持断点续传：任务执行中断后可恢复
2. 支持实时查询：前端可轮询获取进度
3. 支持历史记录：查看任务执行历史

数据库设计：
- task_progress: 存储任务计划
- step_results: 存储步骤执行结果
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TaskProgressRecord:
    """任务进度记录"""
    task_id: str
    wallet_address: str
    conversation_id: str
    user_request: str
    complexity: str
    status: str
    total_steps: int
    completed_steps: int
    created_at: datetime
    updated_at: datetime
    plan_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepResultRecord:
    """步骤结果记录"""
    task_id: str
    step_id: str
    step_name: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result_data: Optional[Dict[str, Any]]
    error_message: Optional[str]


class TaskProgressStore:
    """
    任务进度存储

    职责：
    1. 持久化存储任务计划
    2. 存储步骤执行结果
    3. 支持按钱包地址查询
    4. 支持断点续传
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self):
        """确保数据库表存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 任务进度表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_progress (
                task_id TEXT PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                conversation_id TEXT,
                user_request TEXT NOT NULL,
                complexity TEXT NOT NULL,
                status TEXT NOT NULL,
                total_steps INTEGER DEFAULT 0,
                completed_steps INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                plan_data TEXT
            )
        """)

        # 步骤结果表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS step_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                result_data TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES task_progress(task_id)
            )
        """)

        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_wallet
            ON task_progress(wallet_address)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_status
            ON task_progress(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_step_task
            ON step_results(task_id)
        """)

        conn.commit()
        conn.close()

    def save_task(self, record: TaskProgressRecord) -> bool:
        """保存任务进度"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO task_progress
                (task_id, wallet_address, conversation_id, user_request,
                 complexity, status, total_steps, completed_steps,
                 created_at, updated_at, plan_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.task_id,
                record.wallet_address,
                record.conversation_id,
                record.user_request,
                record.complexity,
                record.status,
                record.total_steps,
                record.completed_steps,
                record.created_at.isoformat(),
                record.updated_at.isoformat(),
                json.dumps(record.plan_data, ensure_ascii=False),
            ))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[TaskProgressStore] Failed to save task: {e}")
            return False

    def get_task(self, task_id: str) -> Optional[TaskProgressRecord]:
        """获取任务进度"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT task_id, wallet_address, conversation_id, user_request,
                       complexity, status, total_steps, completed_steps,
                       created_at, updated_at, plan_data
                FROM task_progress
                WHERE task_id = ?
            """, (task_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return TaskProgressRecord(
                    task_id=row[0],
                    wallet_address=row[1],
                    conversation_id=row[2],
                    user_request=row[3],
                    complexity=row[4],
                    status=row[5],
                    total_steps=row[6],
                    completed_steps=row[7],
                    created_at=datetime.fromisoformat(row[8]),
                    updated_at=datetime.fromisoformat(row[9]),
                    plan_data=json.loads(row[10]) if row[10] else {},
                )
            return None
        except Exception as e:
            logger.error(f"[TaskProgressStore] Failed to get task: {e}")
            return None

    def get_tasks_by_wallet(
        self,
        wallet_address: str,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> List[TaskProgressRecord]:
        """获取钱包地址的所有任务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if status:
                cursor.execute("""
                    SELECT task_id, wallet_address, conversation_id, user_request,
                           complexity, status, total_steps, completed_steps,
                           created_at, updated_at, plan_data
                    FROM task_progress
                    WHERE wallet_address = ? AND status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (wallet_address, status, limit))
            else:
                cursor.execute("""
                    SELECT task_id, wallet_address, conversation_id, user_request,
                           complexity, status, total_steps, completed_steps,
                           created_at, updated_at, plan_data
                    FROM task_progress
                    WHERE wallet_address = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (wallet_address, limit))

            rows = cursor.fetchall()
            conn.close()

            records = []
            for row in rows:
                records.append(TaskProgressRecord(
                    task_id=row[0],
                    wallet_address=row[1],
                    conversation_id=row[2],
                    user_request=row[3],
                    complexity=row[4],
                    status=row[5],
                    total_steps=row[6],
                    completed_steps=row[7],
                    created_at=datetime.fromisoformat(row[8]),
                    updated_at=datetime.fromisoformat(row[9]),
                    plan_data=json.loads(row[10]) if row[10] else {},
                ))
            return records
        except Exception as e:
            logger.error(f"[TaskProgressStore] Failed to get tasks: {e}")
            return []

    def update_task_status(
        self,
        task_id: str,
        status: str,
        completed_steps: int,
    ) -> bool:
        """更新任务状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE task_progress
                SET status = ?, completed_steps = ?, updated_at = ?
                WHERE task_id = ?
            """, (status, completed_steps, datetime.now().isoformat(), task_id))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[TaskProgressStore] Failed to update task: {e}")
            return False

    def save_step_result(self, record: StepResultRecord) -> bool:
        """保存步骤结果"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO step_results
                (task_id, step_id, step_name, status, started_at,
                 completed_at, result_data, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.task_id,
                record.step_id,
                record.step_name,
                record.status,
                record.started_at.isoformat() if record.started_at else None,
                record.completed_at.isoformat() if record.completed_at else None,
                json.dumps(record.result_data, ensure_ascii=False) if record.result_data else None,
                record.error_message,
            ))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[TaskProgressStore] Failed to save step result: {e}")
            return False

    def get_step_results(self, task_id: str) -> List[StepResultRecord]:
        """获取任务的所有步骤结果"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT task_id, step_id, step_name, status, started_at,
                       completed_at, result_data, error_message
                FROM step_results
                WHERE task_id = ?
                ORDER BY id
            """, (task_id,))

            rows = cursor.fetchall()
            conn.close()

            records = []
            for row in rows:
                records.append(StepResultRecord(
                    task_id=row[0],
                    step_id=row[1],
                    step_name=row[2],
                    status=row[3],
                    started_at=datetime.fromisoformat(row[4]) if row[4] else None,
                    completed_at=datetime.fromisoformat(row[5]) if row[5] else None,
                    result_data=json.loads(row[6]) if row[6] else None,
                    error_message=row[7],
                ))
            return records
        except Exception as e:
            logger.error(f"[TaskProgressStore] Failed to get step results: {e}")
            return []

    def delete_task(self, task_id: str) -> bool:
        """删除任务及其步骤结果"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 先删除步骤结果
            cursor.execute("DELETE FROM step_results WHERE task_id = ?", (task_id,))
            # 再删除任务
            cursor.execute("DELETE FROM task_progress WHERE task_id = ?", (task_id,))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"[TaskProgressStore] Failed to delete task: {e}")
            return False
