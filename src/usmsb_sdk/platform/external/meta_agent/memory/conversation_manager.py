"""
Conversation Manager - 会话管理器

基于 USMSB 模型实现：
- 私有会话隔离（Rule: 隐私规则）
- 会话持久化（Resource: 数据存储）
- 学习集成（Learning: 从对话学习）
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any

from .conversation import (
    Conversation,
    ConversationStatus,
    LearningOutcome,
    Message,
    MessageRole,
    Participant,
    ParticipantType,
)

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    会话管理器

    职责：
    1. 会话创建与隔离
    2. 消息存储与检索
    3. 学习产出管理
    4. 隐私访问控制
    """

    def __init__(self, db_path: str = "meta_agent.db"):
        self.db_path = db_path
        self._active_conversations: dict[str, Conversation] = {}
        self._initialized = False

    async def init(self):
        """初始化数据库"""
        if self._initialized:
            return

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._init_db)
        self._initialized = True
        logger.info("Conversation Manager initialized")

    def _init_db(self):
        """初始化数据库表"""
        os.makedirs(
            os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                owner_type TEXT NOT NULL,
                status TEXT NOT NULL,
                is_private INTEGER DEFAULT 1,
                access_list TEXT,
                context TEXT,
                summary TEXT,
                satisfaction_score REAL,
                created_at REAL,
                updated_at REAL,
                ended_at REAL,
                metadata TEXT
            )
        """)

        # 消息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                intent TEXT,
                entities TEXT,
                sentiment TEXT,
                tool_calls TEXT,
                timestamp REAL,
                quality REAL,
                metadata TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)

        # 会话目标表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_goals (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                name TEXT,
                description TEXT,
                status TEXT,
                priority INTEGER,
                created_at REAL,
                updated_at REAL,
                completed_at REAL,
                metadata TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)

        # 学习产出表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_outcomes (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                knowledge_type TEXT,
                content TEXT NOT NULL,
                confidence REAL,
                applicable_contexts TEXT,
                created_at REAL,
                applied_count INTEGER DEFAULT 0,
                effectiveness REAL DEFAULT 0,
                metadata TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_owner ON conversations(owner_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_learning_type ON learning_outcomes(knowledge_type)"
        )

        conn.commit()
        conn.close()

    async def create_conversation(
        self,
        owner_id: str,
        owner_type: ParticipantType = ParticipantType.HUMAN,
        participants: list[Participant] | None = None,
        context: dict[str, Any] | None = None,
    ) -> Conversation:
        """
        创建新会话

        每个会话属于特定的 owner，实现隐私隔离
        """
        await self.init()

        conversation = Conversation(
            owner_id=owner_id,
            owner_type=owner_type,
            participants=participants or [],
            context=context or {},
        )

        # 添加 Meta Agent 作为参与者
        meta_agent = Participant(
            id="meta_agent",
            type=ParticipantType.META_AGENT,
            name="Meta Agent",
        )
        conversation.participants.append(meta_agent)

        # 添加 owner 作为参与者
        owner_participant = Participant(
            id=owner_id,
            type=owner_type,
            name=context.get("owner_name") if context else None,
            wallet_address=owner_id if owner_type == ParticipantType.HUMAN else None,
        )
        conversation.participants.append(owner_participant)

        # 缓存活跃会话
        self._active_conversations[conversation.id] = conversation

        # 持久化
        await self._save_conversation(conversation)

        logger.info(f"Created conversation {conversation.id} for {owner_type.value} {owner_id}")
        return conversation

    async def get_conversation(
        self,
        conversation_id: str,
        accessor_id: str,
    ) -> Conversation | None:
        """
        获取会话（带访问控制）

        只有 owner 或 access_list 中的 ID 才能访问
        """
        # 先检查缓存
        if conversation_id in self._active_conversations:
            conv = self._active_conversations[conversation_id]
            if conv.can_access(accessor_id):
                return conv
            return None

        # 从数据库加载
        conv = await self._load_conversation(conversation_id)
        if conv and conv.can_access(accessor_id):
            self._active_conversations[conversation_id] = conv
            return conv

        return None

    async def get_or_create_conversation(
        self,
        owner_id: str,
        owner_type: ParticipantType = ParticipantType.HUMAN,
    ) -> Conversation:
        """
        获取或创建活跃会话

        每个 owner 同时只有一个活跃会话
        """
        await self.init()

        # 查找活跃会话
        active_conv = await self._find_active_conversation(owner_id)
        if active_conv:
            return active_conv

        # 创建新会话
        return await self.create_conversation(owner_id, owner_type)

    async def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        intent: str | None = None,
        entities: list[dict] | None = None,
        sentiment: str | None = None,
        tool_calls: list[dict] | None = None,
    ) -> Message:
        """添加消息到会话"""
        conversation = self._active_conversations.get(conversation_id)
        if not conversation:
            conversation = await self._load_conversation(conversation_id)
            if conversation:
                self._active_conversations[conversation_id] = conversation

        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        message = Message(
            role=role,
            content=content,
            intent=intent,
            entities=entities or [],
            sentiment=sentiment,
            tool_calls=tool_calls or [],
        )

        conversation.add_message(message)
        await self._save_message(conversation_id, message)
        await self._update_conversation_timestamp(conversation_id)

        return message

    async def get_conversation_history(
        self,
        conversation_id: str,
        accessor_id: str,
        limit: int = 50,
    ) -> list[Message]:
        """获取会话历史（带访问控制）"""
        conversation = await self.get_conversation(conversation_id, accessor_id)
        if not conversation:
            return []
        return conversation.get_last_n_messages(limit)

    async def get_messages_for_llm(
        self,
        conversation_id: str,
        accessor_id: str,
        max_tokens: int = 4000,
    ) -> list[dict[str, str]]:
        """获取用于 LLM 的消息格式"""
        conversation = await self.get_conversation(conversation_id, accessor_id)
        if not conversation:
            return []
        return conversation.get_messages_for_llm(max_tokens)

    async def end_conversation(
        self,
        conversation_id: str,
        accessor_id: str,
        satisfaction_score: float | None = None,
    ) -> bool:
        """结束会话"""
        conversation = await self.get_conversation(conversation_id, accessor_id)
        if not conversation:
            return False

        conversation.end()
        if satisfaction_score:
            conversation.satisfaction_score = satisfaction_score

        await self._update_conversation_status(conversation)

        if conversation_id in self._active_conversations:
            del self._active_conversations[conversation_id]

        return True

    async def add_learning_outcome(
        self,
        conversation_id: str,
        knowledge_type: str,
        content: str,
        confidence: float = 0.5,
        applicable_contexts: list[str] | None = None,
    ) -> LearningOutcome:
        """添加学习产出"""
        outcome = LearningOutcome(
            conversation_id=conversation_id,
            knowledge_type=knowledge_type,
            content=content,
            confidence=confidence,
            applicable_contexts=applicable_contexts or [],
        )

        await self._save_learning_outcome(outcome)

        if conversation_id in self._active_conversations:
            self._active_conversations[conversation_id].learning_outcomes.append(outcome)

        return outcome

    async def get_learning_outcomes(
        self,
        knowledge_type: str | None = None,
        min_confidence: float = 0.0,
        limit: int = 100,
    ) -> list[LearningOutcome]:
        """获取学习产出"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._query_learning_outcomes,
            knowledge_type,
            min_confidence,
            limit,
        )

    def _query_learning_outcomes(
        self,
        knowledge_type: str | None,
        min_confidence: float,
        limit: int,
    ) -> list[LearningOutcome]:
        """查询学习产出"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM learning_outcomes WHERE confidence >= ?"
        params = [min_confidence]

        if knowledge_type:
            query += " AND knowledge_type = ?"
            params.append(knowledge_type)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        outcomes = []
        for row in rows:
            outcome = LearningOutcome(
                id=row[0],
                conversation_id=row[1],
                knowledge_type=row[2],
                content=row[3],
                confidence=row[4],
                applicable_contexts=json.loads(row[5]) if row[5] else [],
                created_at=row[6],
                applied_count=row[7],
                effectiveness=row[8],
                metadata=json.loads(row[9]) if row[9] else {},
            )
            outcomes.append(outcome)

        return outcomes

    async def _find_active_conversation(self, owner_id: str) -> Conversation | None:
        """查找活跃会话"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._query_active_conversation, owner_id)

    def _query_active_conversation(self, owner_id: str) -> Conversation | None:
        """查询活跃会话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM conversations
            WHERE owner_id = ? AND status = 'active'
            ORDER BY updated_at DESC LIMIT 1
            """,
            (owner_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_conversation(row)

    async def _load_conversation(self, conversation_id: str) -> Conversation | None:
        """加载会话"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._query_conversation, conversation_id)

    def _query_conversation(self, conversation_id: str) -> Conversation | None:
        """查询会话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        conversation = self._row_to_conversation(row)

        # 加载消息
        cursor.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp",
            (conversation_id,),
        )
        for msg_row in cursor.fetchall():
            message = Message(
                id=msg_row[0],
                role=MessageRole(msg_row[2]),
                content=msg_row[3],
                intent=msg_row[4],
                entities=json.loads(msg_row[5]) if msg_row[5] else [],
                sentiment=msg_row[6],
                tool_calls=json.loads(msg_row[7]) if msg_row[7] else [],
                timestamp=msg_row[8],
                quality=msg_row[9],
                metadata=json.loads(msg_row[10]) if msg_row[10] else {},
            )
            conversation.messages.append(message)

        conn.close()
        return conversation

    def _row_to_conversation(self, row) -> Conversation:
        """数据库行转 Conversation 对象"""
        return Conversation(
            id=row[0],
            owner_id=row[1],
            owner_type=ParticipantType(row[2]),
            status=ConversationStatus(row[3]),
            is_private=bool(row[4]),
            access_list=json.loads(row[5]) if row[5] else [],
            context=json.loads(row[6]) if row[6] else {},
            summary=row[7],
            satisfaction_score=row[8],
            created_at=row[9],
            updated_at=row[10],
            ended_at=row[11],
            metadata=json.loads(row[12]) if row[12] else {},
        )

    async def _save_conversation(self, conversation: Conversation):
        """保存会话"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._insert_conversation, conversation)

    def _insert_conversation(self, conversation: Conversation):
        """插入会话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO conversations
            (id, owner_id, owner_type, status, is_private, access_list, context,
             summary, satisfaction_score, created_at, updated_at, ended_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conversation.id,
                conversation.owner_id,
                conversation.owner_type.value,
                conversation.status.value,
                1 if conversation.is_private else 0,
                json.dumps(conversation.access_list),
                json.dumps(conversation.context),
                conversation.summary,
                conversation.satisfaction_score,
                conversation.created_at,
                conversation.updated_at,
                conversation.ended_at,
                json.dumps(conversation.metadata),
            ),
        )

        conn.commit()
        conn.close()

    async def _save_message(self, conversation_id: str, message: Message):
        """保存消息"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._insert_message, conversation_id, message)

    def _insert_message(self, conversation_id: str, message: Message):
        """插入消息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO messages
            (id, conversation_id, role, content, intent, entities, sentiment,
             tool_calls, timestamp, quality, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message.id,
                conversation_id,
                message.role.value,
                message.content,
                message.intent,
                json.dumps(message.entities),
                message.sentiment,
                json.dumps(message.tool_calls),
                message.timestamp,
                message.quality,
                json.dumps(message.metadata),
            ),
        )

        conn.commit()
        conn.close()

    async def _update_conversation_timestamp(self, conversation_id: str):
        """更新会话时间戳"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._set_conversation_timestamp, conversation_id)

    def _set_conversation_timestamp(self, conversation_id: str):
        """设置会话时间戳"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (datetime.now().timestamp(), conversation_id),
        )
        conn.commit()
        conn.close()

    async def _update_conversation_status(self, conversation: Conversation):
        """更新会话状态"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._set_conversation_status, conversation)

    def _set_conversation_status(self, conversation: Conversation):
        """设置会话状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE conversations SET status = ?, ended_at = ?, satisfaction_score = ? WHERE id = ?",
            (
                conversation.status.value,
                conversation.ended_at,
                conversation.satisfaction_score,
                conversation.id,
            ),
        )
        conn.commit()
        conn.close()

    async def _save_learning_outcome(self, outcome: LearningOutcome):
        """保存学习产出"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._insert_learning_outcome, outcome)

    def _insert_learning_outcome(self, outcome: LearningOutcome):
        """插入学习产出"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO learning_outcomes
            (id, conversation_id, knowledge_type, content, confidence,
             applicable_contexts, created_at, applied_count, effectiveness, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                outcome.id,
                outcome.conversation_id,
                outcome.knowledge_type,
                outcome.content,
                outcome.confidence,
                json.dumps(outcome.applicable_contexts),
                outcome.created_at,
                outcome.applied_count,
                outcome.effectiveness,
                json.dumps(outcome.metadata),
            ),
        )

        conn.commit()
        conn.close()

    async def search_all_conversations(
        self, owner_id: str, query: str, limit: int = 20
    ) -> list[dict]:
        """
        跨会话搜索历史消息

        搜索用户所有会话中的消息，用于召回历史敏感信息等场景。

        Args:
            owner_id: 用户ID/钱包地址
            query: 搜索关键词
            limit: 返回结果数量限制

        Returns:
            消息列表，每条包含会话ID、消息内容、时间戳等
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._search_all_conversations, owner_id, query, limit
        )

    def _search_all_conversations(self, owner_id: str, query: str, limit: int) -> list[dict]:
        """跨会话搜索实现"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 检查是否包含敏感信息关键词
        has_sensitive = any(
            kw in query.lower() for kw in ["api", "key", "token", "密码", "密钥", "xialiao"]
        )

        if has_sensitive:
            # 搜索所有敏感信息，不限制角色，按时间升序（老消息在前）
            cursor.execute(
                """
                SELECT m.id, m.conversation_id, m.role, m.content, m.timestamp, c.summary
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.owner_id = ? AND m.content LIKE ?
                ORDER BY m.timestamp ASC
                LIMIT ?
                """,
                (owner_id, f"%{query}%", limit),
            )
        else:
            cursor.execute(
                """
                SELECT m.id, m.conversation_id, m.role, m.content, m.timestamp, c.summary
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.owner_id = ? AND m.content LIKE ?
                ORDER BY m.timestamp DESC
                LIMIT ?
                """,
                (owner_id, f"%{query}%", limit),
            )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "conversation_id": row[1],
                "role": row[2],
                "content": row[3],
                "timestamp": row[4],
                "conversation_title": row[5] if row[5] else "未命名会话",
            }
            for row in rows
        ]

    async def get_recent_conversations(self, owner_id: str, limit: int = 10) -> list[dict]:
        """获取用户最近的会话列表"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_recent_conversations, owner_id, limit)

    def _get_recent_conversations(self, owner_id: str, limit: int) -> list[dict]:
        """获取最近会话实现"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, summary, created_at, updated_at, status
            FROM conversations
            WHERE owner_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (owner_id, limit),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "title": row[1] if row[1] else "未命名会话",
                "created_at": row[2],
                "updated_at": row[3],
                "status": row[4],
            }
            for row in rows
        ]
