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
import sqlite3
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

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
    key_topics: List[str] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    message_count: int = 0


@dataclass
class UserProfile:
    """用户画像"""

    user_id: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    commitments: List[str] = field(default_factory=list)
    knowledge: Dict[str, Any] = field(default_factory=dict)
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
        config: Optional[MemoryConfig] = None,
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
                context TEXT
            )
        """)

        conn.commit()
        conn.close()

    async def process_conversation(
        self,
        conversation_id: str,
        user_id: str,
        messages: List[Dict[str, str]],
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
        messages: List[Dict[str, str]],
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

    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
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
        key_topics: List[str],
        decisions: List[str],
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
        key_topics: List[str],
        decisions: List[str],
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
        messages: List[Dict[str, str]],
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

    async def _update_user_profile(self, user_id: str, data: Dict[str, Any]):
        """更新用户画像"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._merge_profile,
            user_id,
            data,
        )

    def _merge_profile(self, user_id: str, data: Dict[str, Any]):
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
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
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

    def _get_summaries(self, conversation_id: str) -> List[Dict]:
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

    def _get_user_profile(self, user_id: str) -> Optional[Dict]:
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

    def _get_important_memories(self, user_id: str) -> List[Dict]:
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

    def build_context_prompt(self, context: Dict[str, Any]) -> str:
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
