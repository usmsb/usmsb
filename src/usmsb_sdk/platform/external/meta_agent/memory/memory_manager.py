"""
分层记忆系统 - 智能记忆方案

设计三层记忆架构：
1. 短期记忆：最近 N 条消息（对话窗口）
2. 摘要记忆：对更早对话的摘要（保留关键信息）
3. 用户画像：用户偏好、承诺、重要决定（持久存储）

这样可以让 Agent 记住更长时间跨度的上下文
"""

import asyncio
import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MemoryConfig:
    """记忆配置"""

    short_term_messages: int = 20  # 短期记忆保留消息数
    summary_threshold: int = 30  # 超过此数量进行摘要
    max_summaries: int = 10  # 最大保留摘要数
    extract_preferences: bool = True  # 是否提取用户偏好
    importance_threshold: float = 0.7  # 重要信息提取阈值


@dataclass
class ConversationSummary:
    """对话摘要"""

    id: str
    conversation_id: str
    summary: str
    key_topics: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    message_count: int = 0


@dataclass
class UserProfile:
    """用户画像"""

    user_id: str
    preferences: dict[str, Any] = field(default_factory=dict)
    commitments: list[str] = field(default_factory=list)
    knowledge: dict[str, Any] = field(default_factory=dict)
    last_updated: float = field(default_factory=lambda: datetime.now().timestamp())


class MemoryManager:
    """
    分层记忆管理器

    管理三层记忆：
    - 短期：原始消息（通过 ConversationManager）
    - 中期：对话摘要
    - 长期：用户画像
    """

    def __init__(
        self,
        db_path: str = "memory.db",
        config: MemoryConfig | None = None,
        llm_manager=None,
    ):
        self.db_path = db_path
        self.config = config or MemoryConfig()
        self.llm_manager = llm_manager
        self._initialized = False

    async def init(self):
        """初始化"""
        if self._initialized:
            return

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._init_db)
        self._initialized = True
        logger.info("Memory Manager initialized")

    def _init_db(self):
        """初始化数据库表"""
        os.makedirs(
            os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 对话摘要表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                summary TEXT NOT NULL,
                key_topics TEXT,
                decisions TEXT,
                created_at REAL,
                message_count INTEGER DEFAULT 0
            )
        """)

        # 用户画像表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                preferences TEXT,
                commitments TEXT,
                knowledge TEXT,
                last_updated REAL
            )
        """)

        # 重要信息表（从对话中提取）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS important_memories (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                memory_type TEXT,
                importance REAL DEFAULT 0.5,
                created_at REAL,
                context TEXT,
                recall_count INTEGER DEFAULT 0,
                last_recalled_at REAL,
                from_recall INTEGER DEFAULT 0
            )
        """)

        conn.commit()
        conn.close()

    async def process_conversation(
        self,
        conversation_id: str,
        user_id: str,
        messages: list[dict[str, str]],
    ):
        """
        处理对话，提取和管理记忆

        Args:
            conversation_id: 对话 ID
            user_id: 用户 ID
            messages: 对话消息列表
        """
        await self.init()

        # 1. 检查是否需要生成摘要
        if len(messages) > self.config.summary_threshold:
            await self._generate_summary(
                conversation_id,
                messages,
                user_id,
            )

        # 2. 提取重要信息
        if self.config.extract_preferences:
            await self._extract_important_info(user_id, messages)

    async def _generate_summary(
        self,
        conversation_id: str,
        messages: list[dict[str, str]],
        user_id: str,
    ):
        """生成对话摘要"""
        # 获取需要摘要的消息（最早的 N 条，不包括最近的短期记忆）
        messages_to_summarize = messages[: -self.config.short_term_messages]

        if len(messages_to_summarize) < 10:
            return

        try:
            # 使用 LLM 生成摘要
            if self.llm_manager:
                summary_prompt = f"""请对以下对话进行精简摘要，要求：
1. 保留关键信息和主题
2. 记录重要的决定和承诺
3. 提取用户偏好和需求
4. 用简洁的中文表述

对话内容：
{self._format_messages(messages_to_summarize)}

请返回 JSON 格式：
{{
    "summary": "摘要内容",
    "key_topics": ["主题1", "主题2"],
    "decisions": ["决定1", "决定2"]
}}"""

                result = await self.llm_manager.chat(summary_prompt)

                # 解析结果
                try:
                    import re

                    json_match = re.search(r"\{[\s\S]*\}", result)
                    if json_match:
                        data = json.loads(json_match.group())
                        summary = data.get("summary", result[:500])
                        key_topics = data.get("key_topics", [])
                        decisions = data.get("decisions", [])
                    else:
                        summary = result[:500]
                        key_topics = []
                        decisions = []
                except:
                    summary = result[:500]
                    key_topics = []
                    decisions = []
            else:
                # 降级：简单拼接
                summary = f"对话包含 {len(messages_to_summarize)} 条消息"
                key_topics = []
                decisions = []

            # 保存摘要
            await self._save_summary(
                conversation_id=conversation_id,
                summary=summary,
                key_topics=key_topics,
                decisions=decisions,
                message_count=len(messages_to_summarize),
            )

            logger.info(f"Generated summary for conversation {conversation_id}")

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")

    def _format_messages(self, messages: list[dict[str, str]]) -> str:
        """格式化消息列表"""
        lines = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            lines.append(f"{role}: {content[:200]}")
        return "\n".join(lines)

    async def _save_summary(
        self,
        conversation_id: str,
        summary: str,
        key_topics: list[str],
        decisions: list[str],
        message_count: int,
    ):
        """保存摘要"""
        import uuid

        summary_id = f"sum_{uuid.uuid4().hex[:8]}"

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._insert_summary,
            summary_id,
            conversation_id,
            summary,
            key_topics,
            decisions,
            message_count,
        )

    def _insert_summary(
        self,
        summary_id: str,
        conversation_id: str,
        summary: str,
        key_topics: list[str],
        decisions: list[str],
        message_count: int,
    ):
        """插入摘要"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 清理旧摘要（保留最近的 N 个）
        cursor.execute(
            """
            DELETE FROM conversation_summaries
            WHERE conversation_id = ?
            AND id NOT IN (
                SELECT id FROM conversation_summaries
                WHERE conversation_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            )
        """,
            (conversation_id, conversation_id, self.config.max_summaries),
        )

        cursor.execute(
            """
            INSERT INTO conversation_summaries
            (id, summary, key_topics, decisions, created_at, message_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                summary_id,
                conversation_id,
                summary,
                json.dumps(key_topics),
                json.dumps(decisions),
                datetime.now().timestamp(),
                message_count,
            ),
        )

        conn.commit()
        conn.close()

    async def _extract_important_info(
        self,
        user_id: str,
        messages: list[dict[str, str]],
    ):
        """从对话中提取重要信息（用户偏好、承诺等）"""
        # 只处理用户消息
        user_messages = [m for m in messages if m.get("role") == "user"]

        if len(user_messages) < 5:
            return

        try:
            if self.llm_manager:
                prompt = f"""从以下用户消息中提取重要信息，包括：
1. 用户偏好（如喜欢的功能、风格）
2. 用户需求和目标
3. 用户的承诺或决定
4. 重要的事实信息

用户消息：
{self._format_messages(user_messages[-10:])}

请返回 JSON 格式：
{{
    "preferences": {{"key": "value"}},
    "commitments": ["承诺1", "承诺2"],
    "knowledge": {{"事实": "内容"}}
}}"""

                result = await self.llm_manager.chat(prompt)

                # 解析并保存
                try:
                    import re

                    json_match = re.search(r"\{[\s\S]*\}", result)
                    if json_match:
                        data = json.loads(json_match.group())
                        await self._update_user_profile(user_id, data)
                except Exception as e:
                    logger.warning(f"Failed to parse preferences: {e}")

        except Exception as e:
            logger.error(f"Failed to extract preferences: {e}")

    async def _update_user_profile(self, user_id: str, data: dict[str, Any]):
        """更新用户画像"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._merge_profile,
            user_id,
            data,
        )

    def _merge_profile(self, user_id: str, data: dict[str, Any]):
        """合并用户画像"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 获取现有画像
        cursor.execute("SELECT * FROM user_profiles WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if row:
            # 合并现有数据
            existing_prefs = json.loads(row[1]) if row[1] else {}
            existing_commitments = json.loads(row[2]) if row[2] else []
            existing_knowledge = json.loads(row[3]) if row[3] else {}

            # 合并新数据
            new_prefs = data.get("preferences", {})
            existing_prefs.update(new_prefs)

            new_commitments = data.get("commitments", [])
            for c in new_commitments:
                if c not in existing_commitments:
                    existing_commitments.append(c)

            new_knowledge = data.get("knowledge", {})
            existing_knowledge.update(new_knowledge)

            cursor.execute(
                """
                UPDATE user_profiles
                SET preferences = ?, commitments = ?, knowledge = ?, last_updated = ?
                WHERE user_id = ?
            """,
                (
                    json.dumps(existing_prefs),
                    json.dumps(existing_commitments),
                    json.dumps(existing_knowledge),
                    datetime.now().timestamp(),
                    user_id,
                ),
            )
        else:
            # 创建新画像
            cursor.execute(
                """
                INSERT INTO user_profiles
                (user_id, preferences, commitments, knowledge, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    json.dumps(data.get("preferences", {})),
                    json.dumps(data.get("commitments", [])),
                    json.dumps(data.get("knowledge", {})),
                    datetime.now().timestamp(),
                ),
            )

        conn.commit()
        conn.close()

    async def get_context(
        self,
        user_id: str,
        conversation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        获取完整上下文记忆

        Returns:
            包含短期、摘要、用户画像的字典
        """
        await self.init()

        context = {
            "summaries": [],
            "user_profile": None,
            "important_memories": [],
        }

        loop = asyncio.get_event_loop()

        # 获取对话摘要
        if conversation_id:
            summaries = await loop.run_in_executor(
                None,
                self._get_summaries,
                conversation_id,
            )
            context["summaries"] = summaries

        # 获取用户画像
        profile = await loop.run_in_executor(
            None,
            self._get_user_profile,
            user_id,
        )
        context["user_profile"] = profile

        # 获取重要记忆
        memories = await loop.run_in_executor(
            None,
            self._get_important_memories,
            user_id,
        )
        context["important_memories"] = memories

        return context

    def _get_summaries(self, conversation_id: str) -> list[dict]:
        """获取对话摘要"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT summary, key_topics, decisions, message_count, created_at
            FROM conversation_summaries
            WHERE conversation_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (conversation_id, self.config.max_summaries),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "summary": row[0],
                "topics": json.loads(row[1]) if row[1] else [],
                "decisions": json.loads(row[2]) if row[2] else [],
                "message_count": row[3],
                "created_at": row[4],
            }
            for row in rows
        ]

    def _get_user_profile(self, user_id: str) -> dict | None:
        """获取用户画像"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT preferences, commitments, knowledge, last_updated
            FROM user_profiles
            WHERE user_id = ?
        """,
            (user_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "preferences": json.loads(row[0]) if row[0] else {},
            "commitments": json.loads(row[1]) if row[1] else [],
            "knowledge": json.loads(row[2]) if row[2] else {},
            "last_updated": row[3],
        }

    def _get_important_memories(self, user_id: str) -> list[dict]:
        """获取重要记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT content, memory_type, importance, created_at
            FROM important_memories
            WHERE user_id = ? AND importance >= ?
            ORDER BY importance DESC, created_at DESC
            LIMIT 20
        """,
            (user_id, self.config.importance_threshold),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "content": row[0],
                "type": row[1],
                "importance": row[2],
                "created_at": row[3],
            }
            for row in rows
        ]

    def build_context_prompt(self, context: dict[str, Any]) -> str:
        """根据上下文构建提示词"""
        parts = []

        # 添加摘要
        if context.get("summaries"):
            parts.append("## 之前的对话摘要")
            for i, summary in enumerate(context["summaries"], 1):
                parts.append(f"\n【早期对话 {i}】({summary['message_count']} 条消息)")
                parts.append(summary["summary"])
                if summary.get("topics"):
                    parts.append(f"主题: {', '.join(summary['topics'])}")
                if summary.get("decisions"):
                    parts.append(f"决定: {', '.join(summary['decisions'])}")

        # 添加用户画像
        profile = context.get("user_profile")
        if profile:
            parts.append("\n## 用户画像")

            prefs = profile.get("preferences", {})
            if prefs:
                parts.append("\n用户偏好:")
                for k, v in prefs.items():
                    parts.append(f"- {k}: {v}")

            commitments = profile.get("commitments", [])
            if commitments:
                parts.append("\n用户的承诺/决定:")
                for c in commitments[-5:]:
                    parts.append(f"- {c}")

        # 添加重要记忆
        memories = context.get("important_memories", [])
        if memories:
            parts.append("\n## 重要记忆")
            for mem in memories[:5]:
                parts.append(f"- [{mem['type']}] {mem['content']}")

        return "\n".join(parts) if parts else ""

    # ==================== 智能召回所需方法 ====================

    async def search(self, query: str, limit: int = 20) -> list[dict]:
        """
        通用搜索 - 用于智能召回

        Args:
            query: 搜索关键词
            limit: 返回数量限制

        Returns:
            记忆列表
        """
        await self.init()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_memory, query, limit)

    def _search_memory(self, query: str, limit: int) -> list[dict]:
        """内部搜索方法"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 搜索重要记忆
        cursor.execute(
            """
            SELECT id, user_id, content, memory_type, importance, created_at
            FROM important_memories
            WHERE content LIKE ?
            ORDER BY importance DESC, created_at DESC
            LIMIT ?
            """,
            (f"%{query}%", limit),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "content": row[2],
                "type": row[3],
                "importance": row[4],
                "timestamp": row[5],
            }
            for row in rows
        ]

    async def search_by_keyword(self, keyword: str) -> list[dict]:
        """按关键词搜索"""
        return await self.search(keyword, limit=20)

    async def search_by_task_type(self, task_type: str) -> list[dict]:
        """按任务类型搜索"""
        await self.init()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_by_task_type, task_type)

    def _search_by_task_type(self, task_type: str) -> list[dict]:
        """按任务类型搜索 - 内部方法"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 搜索包含任务类型的记忆
        cursor.execute(
            """
            SELECT id, user_id, content, memory_type, importance, created_at
            FROM important_memories
            WHERE memory_type = ? OR content LIKE ?
            ORDER BY importance DESC
            LIMIT 20
            """,
            (task_type, f"%{task_type}%"),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "content": row[2],
                "type": row[3],
                "importance": row[4],
                "timestamp": row[5],
            }
            for row in rows
        ]

    async def search_by_time(self, time_range: str) -> list[dict]:
        """按时间范围搜索"""
        await self.init()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_by_time, time_range)

    def _search_by_time(self, time_range: str) -> list[dict]:
        """按时间范围搜索 - 内部方法"""
        import time

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = time.time()
        if time_range == "recent":
            # 最近1小时
            start_time = now - 3600
        elif time_range == "week":
            # 最近一周
            start_time = now - 7 * 24 * 3600
        elif time_range == "month":
            # 最近一月
            start_time = now - 30 * 24 * 3600
        else:  # all
            start_time = 0

        cursor.execute(
            """
            SELECT id, user_id, content, memory_type, importance, created_at
            FROM important_memories
            WHERE created_at >= ?
            ORDER BY created_at DESC
            LIMIT 20
            """,
            (start_time,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "content": row[2],
                "type": row[3],
                "importance": row[4],
                "timestamp": row[5],
            }
            for row in rows
        ]

    async def search_by_entity(self, entity: str) -> list[dict]:
        """按实体搜索"""
        return await self.search(entity, limit=20)

    async def search_by_success(self, success: bool) -> list[dict]:
        """按成功/失败标记搜索"""
        await self.init()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._search_by_success, success)

    def _search_by_success(self, success: bool) -> list[dict]:
        """按成功/失败搜索 - 内部方法"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 通过memory_type区分成功和失败经验
        memory_type = "success_experience" if success else "failure_lesson"

        cursor.execute(
            """
            SELECT id, user_id, content, memory_type, importance, created_at
            FROM important_memories
            WHERE memory_type = ?
            ORDER BY importance DESC
            LIMIT 20
            """,
            (memory_type,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "content": row[2],
                "type": row[3],
                "importance": row[4],
                "timestamp": row[5],
                "success": success,
            }
            for row in rows
        ]

    # ==================== 守护进程所需方法 ====================

    async def get_recent_conversations(self, limit: int = 20) -> list[dict]:
        """获取最近的对话"""
        await self.init()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_recent_conversations, limit)

    def _get_recent_conversations(self, limit: int) -> list[dict]:
        """获取最近的对话 - 内部方法"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, conversation_id, summary, created_at, message_count
            FROM conversation_summaries
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "conversation_id": row[1],
                "summary": row[2],
                "created_at": row[3],
                "message_count": row[4],
            }
            for row in rows
        ]

    async def get_recent_errors(self, limit: int = 10) -> list[dict]:
        """获取最近的错误记录"""
        # 从重要记忆中获取错误相关的内容
        await self.init()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_recent_errors, limit)

    def _get_recent_errors(self, limit: int) -> list[dict]:
        """获取最近的错误 - 内部方法"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, user_id, content, memory_type, importance, created_at
            FROM important_memories
            WHERE memory_type = 'error_record' OR content LIKE '%error%' OR content LIKE '%failed%'
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "content": row[2],
                "type": row[3],
                "importance": row[4],
                "timestamp": row[5],
            }
            for row in rows
        ]

    async def get_successful_conversations(self, limit: int = 10) -> list[dict]:
        """获取成功的对话"""
        await self.init()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_successful_conversations, limit)

    def _get_successful_conversations(self, limit: int) -> list[dict]:
        """获取成功的对话 - 内部方法"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, conversation_id, summary, created_at, message_count
            FROM conversation_summaries
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "conversation_id": row[1],
                "summary": row[2],
                "created_at": row[3],
                "message_count": row[4],
            }
            for row in rows
        ]

    async def get_pending_knowledge(self) -> list[dict]:
        """获取待验证的知识"""
        await self.init()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_pending_knowledge)

    def _get_pending_knowledge(self) -> list[dict]:
        """获取待验证的知识 - 内部方法"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, user_id, content, memory_type, importance, created_at
            FROM important_memories
            WHERE memory_type = 'pending_knowledge'
            ORDER BY created_at DESC
            LIMIT 10
            """,
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "content": row[2],
                "type": row[3],
                "importance": row[4],
                "timestamp": row[5],
                "source": "user_interaction",
            }
            for row in rows
        ]

    async def mark_knowledge_validated(self, knowledge_id: str):
        """标记知识已验证"""
        await self.init()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._mark_knowledge_validated, knowledge_id)

    def _mark_knowledge_validated(self, knowledge_id: str):
        """标记知识已验证 - 内部方法"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 更新memory_type为validated_knowledge
        cursor.execute(
            """
            UPDATE important_memories
            SET memory_type = 'validated_knowledge'
            WHERE id = ?
            """,
            (knowledge_id,),
        )

        conn.commit()
        conn.close()

    async def get_execution_logs(self, limit: int = 50) -> list[dict]:
        """获取执行日志"""
        # 从重要记忆中获取执行相关的记录
        await self.init()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_execution_logs, limit)

    def _get_execution_logs(self, limit: int) -> list[dict]:
        """获取执行日志 - 内部方法"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, user_id, content, memory_type, importance, created_at
            FROM important_memories
            WHERE memory_type = 'execution_log' OR content LIKE '%execute%' OR content LIKE '%tool%'
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "user_id": row[1],
                "content": row[2],
                "type": row[3],
                "importance": row[4],
                "timestamp": row[5],
            }
            for row in rows
        ]

    async def add_important_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str,
        importance: float = 0.5,
        context: dict | None = None,
    ):
        """添加重要记忆"""
        await self.init()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._add_important_memory, user_id, content, memory_type, importance, context
        )

    def _add_important_memory(
        self,
        user_id: str,
        content: str,
        memory_type: str,
        importance: float,
        context: dict | None,
    ):
        """添加重要记忆 - 内部方法"""
        import uuid

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO important_memories
            (id, user_id, content, memory_type, importance, created_at, context)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                user_id,
                content,
                memory_type,
                importance,
                datetime.now().timestamp(),
                json.dumps(context) if context else None,
            ),
        )

        conn.commit()
        conn.close()

    async def dynamic_update_from_recall(
        self, user_id: str, recalled_content: str, source: str = "recall"
    ):
        """
        动态更新从召回中发现的敏感信息

        被召回的内容中发现重要实体时，自动更新到 important_memories。

        Args:
            user_id: 用户ID
            recalled_content: 被召回的内容
            source: 来源标识（如 "smart_recall", "conversation_history"）
        """
        await self.init()

        if not self.llm_manager:
            return

        important_entity = await self._detect_important_entity(recalled_content, user_id)

        if important_entity:
            existing = await self._check_entity_exists(user_id, important_entity["content"])
            if existing:
                await self._increase_importance(existing["id"])
            else:
                await self.add_important_memory(
                    user_id=user_id,
                    content=important_entity["content"],
                    memory_type=important_entity["type"],
                    importance=0.8,
                    context={
                        "source": source,
                        "detected_at": datetime.now().isoformat(),
                        "entity_type": important_entity["entity_type"],
                    },
                )

    async def _detect_important_entity(self, content: str, user_id: str) -> dict | None:
        """使用 LLM 检测内容中的重要实体"""
        prompt = f"""分析以下内容，检测是否包含重要实体信息。

用户ID: {user_id}
内容:
{content[:2000]}

请返回 JSON 格式：
{{
    "has_important_entity": true/false,
    "entity_type": "api_key/password/private_key/token/wallet/phone/email/其他",
    "content": "需要记忆的具体信息（不要包含完整凭证，只保留关键标识）",
    "reasoning": "判断理由"
}}

注意：
1. 只返回确实重要的信息（如 API Key、密码、钱包地址等）
2. 如果是 API Key，只保留前缀如 "xialiao_xxx" 或 "sk-xxx"
3. 普通对话内容不要返回
4. 如果没有重要实体，返回 {{"has_important_entity": false}}"""

        try:
            response = await self.llm_manager.chat(prompt)

            import re

            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                data = json.loads(json_match.group())
                if data.get("has_important_entity") and data.get("content"):
                    return {
                        "content": data["content"],
                        "type": f"sensitive_info_{data.get('entity_type', 'unknown')}",
                        "entity_type": data.get("entity_type", "unknown"),
                    }
        except Exception as e:
            logger.warning(f"Failed to detect important entity: {e}")

        return None

    def _check_entity_exists(self, user_id: str, content: str) -> dict | None:
        """检查重要实体是否已存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, content, importance FROM important_memories
            WHERE user_id = ? AND content LIKE ?
            """,
            (user_id, f"%{content[:50]}%"),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return {"id": row[0], "content": row[1], "importance": row[2]}
        return None

    def _increase_importance(self, memory_id: str):
        """增加记忆的重要性"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE important_memories
            SET importance = MIN(1.0, importance + 0.1),
                recall_count = COALESCE(recall_count, 0) + 1,
                last_recalled_at = ?
            WHERE id = ?
            """,
            (datetime.now().timestamp(), memory_id),
        )

        conn.commit()
        conn.close()

    async def check_and_store_user_emphasis(self, user_id: str, message: str):
        """
        检测用户强调记忆的消息，并存储

        用户说"记住这个"、"请记住"等指令时，自动存储到重要记忆。

        Args:
            user_id: 用户ID
            message: 用户消息
        """
        await self.init()

        emphasis_patterns = [
            "记住这个",
            "记住这个信息",
            "请记住",
            "记住",
            "收藏",
            "标记为重要",
            "保存这个",
            "remember this",
            "save this",
            "keep this in mind",
            "don't forget",
            "memorize",
        ]

        has_emphasis = any(p in message.lower() for p in emphasis_patterns)

        if has_emphasis:
            await self.add_important_memory(
                user_id=user_id,
                content=message,
                memory_type="user_emphasized",
                importance=0.9,
                context={"source": "user_emphasis", "detected_at": datetime.now().isoformat()},
            )
