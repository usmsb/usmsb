"""
经验数据库 - 存储错误解决方案和成功经验
用于错误驱动学习系统
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class ExperienceDB:
    """
    经验数据库

    存储：
    1. 错误解决方案
    2. 成功经验
    3. 失败教训
    """

    def __init__(self, db_path: str = "experience.db"):
        self.db_path = db_path
        self._initialized = False

    async def init(self):
        """初始化数据库"""
        if self._initialized:
            return

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._init_db)
        self._initialized = True
        logger.info("Experience DB initialized")

    def _init_db(self):
        """初始化数据库表"""
        os.makedirs(
            os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".",
            exist_ok=True,
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 错误解决方案表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_solutions (
                id TEXT PRIMARY KEY,
                error_type TEXT NOT NULL,
                error_message TEXT,
                solution_type TEXT NOT NULL,
                solution_data TEXT,
                reasoning TEXT,
                prevent_future TEXT,
                tool_name TEXT,
                success_rate REAL DEFAULT 0.0,
                times_used INTEGER DEFAULT 0,
                times_succeeded INTEGER DEFAULT 0,
                created_at REAL,
                last_used_at REAL
            )
        """)

        # 成功经验表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS success_experiences (
                id TEXT PRIMARY KEY,
                experience_type TEXT NOT NULL,
                content TEXT NOT NULL,
                context TEXT,
                success_rate REAL DEFAULT 1.0,
                times_applied INTEGER DEFAULT 1,
                created_at REAL,
                last_used_at REAL
            )
        """)

        # 失败教训表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failure_lessons (
                id TEXT PRIMARY KEY,
                lesson_type TEXT NOT NULL,
                content TEXT NOT NULL,
                context TEXT,
                occurrence_count INTEGER DEFAULT 1,
                created_at REAL,
                last_occurred_at REAL
            )
        """)

        # 创建索引
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_error_solutions_type ON error_solutions(error_type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_error_solutions_tool ON error_solutions(tool_name)"
        )

        conn.commit()
        conn.close()

    async def add(self, experience: dict[str, Any]):
        """
        添加经验记录

        Args:
            experience: 经验数据
                - type: 经验类型 (error_solution, success_experience, failure_lesson)
                - 其他字段根据类型不同
        """
        await self.init()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._add_experience, experience)

    def _add_experience(self, experience: dict[str, Any]):
        """添加经验记录 - 内部方法"""
        exp_type = experience.get("type", "error_solution")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().timestamp()

        if exp_type == "error_solution":
            cursor.execute(
                """
                INSERT INTO error_solutions
                (id, error_type, error_message, solution_type, solution_data, reasoning,
                 prevent_future, tool_name, created_at, last_used_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    experience.get("error_type", ""),
                    experience.get("error_message", ""),
                    experience.get("solution_type", "retry"),
                    json.dumps(experience.get("solution_data", {})),
                    experience.get("reasoning", ""),
                    experience.get("prevent_future", ""),
                    experience.get("tool_name"),
                    now,
                    now,
                ),
            )

        elif exp_type == "success_experience":
            cursor.execute(
                """
                INSERT INTO success_experiences
                (id, experience_type, content, context, created_at, last_used_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    experience.get("experience_type", "general"),
                    experience.get("content", ""),
                    json.dumps(experience.get("context", {})) if experience.get("context") else None,
                    now,
                    now,
                ),
            )

        elif exp_type == "failure_lesson":
            cursor.execute(
                """
                INSERT INTO failure_lessons
                (id, lesson_type, content, context, created_at, last_occurred_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    experience.get("lesson_type", "general"),
                    experience.get("content", ""),
                    json.dumps(experience.get("context", {})) if experience.get("context") else None,
                    now,
                    now,
                ),
            )

        conn.commit()
        conn.close()

    async def search_solutions(
        self,
        error_type: str | None = None,
        tool_name: str | None = None,
    ) -> list[dict]:
        """
        搜索解决方案

        Args:
            error_type: 错误类型
            tool_name: 工具名称

        Returns:
            解决方案列表
        """
        await self.init()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._search_solutions, error_type, tool_name
        )

    def _search_solutions(
        self,
        error_type: str | None,
        tool_name: str | None,
    ) -> list[dict]:
        """搜索解决方案 - 内部方法"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM error_solutions WHERE 1=1"
        params = []

        if error_type:
            query += " AND error_type = ?"
            params.append(error_type)

        if tool_name:
            query += " AND tool_name = ?"
            params.append(tool_name)

        query += " ORDER BY success_rate DESC, times_used DESC LIMIT 10"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "error_type": row[1],
                "error_message": row[2],
                "solution_type": row[3],
                "solution_data": json.loads(row[4]) if row[4] else {},
                "reasoning": row[5],
                "prevent_future": row[6],
                "tool_name": row[7],
                "success_rate": row[8],
                "times_used": row[9],
                "times_succeeded": row[10],
            }
            for row in rows
        ]

    async def get_all_experiences(self) -> dict[str, list[dict]]:
        """获取所有经验"""
        await self.init()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_all_experiences)

    def _get_all_experiences(self) -> dict[str, list[dict]]:
        """获取所有经验 - 内部方法"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 获取错误解决方案
        cursor.execute(
            "SELECT * FROM error_solutions ORDER BY created_at DESC LIMIT 50"
        )
        error_solutions = cursor.fetchall()

        # 获取成功经验
        cursor.execute(
            "SELECT * FROM success_experiences ORDER BY created_at DESC LIMIT 50"
        )
        success_experiences = cursor.fetchall()

        # 获取失败教训
        cursor.execute(
            "SELECT * FROM failure_lessons ORDER BY created_at DESC LIMIT 50"
        )
        failure_lessons = cursor.fetchall()

        conn.close()

        return {
            "error_solutions": [
                {
                    "id": row[0],
                    "error_type": row[1],
                    "error_message": row[2],
                    "solution_type": row[3],
                    "solution_data": json.loads(row[4]) if row[4] else {},
                    "reasoning": row[5],
                }
                for row in error_solutions
            ],
            "success_experiences": [
                {
                    "id": row[0],
                    "experience_type": row[1],
                    "content": row[2],
                }
                for row in success_experiences
            ],
            "failure_lessons": [
                {
                    "id": row[0],
                    "lesson_type": row[1],
                    "content": row[2],
                }
                for row in failure_lessons
            ],
        }
