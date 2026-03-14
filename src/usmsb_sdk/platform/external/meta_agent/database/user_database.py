"""
User Database Module

This module provides user-isolated database management for Meta Agent.
Each user has their own SQLite databases for conversations, memory, and knowledge.
"""

import asyncio
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

# ============ Data Models ============

@dataclass
class Conversation:
    """Conversation data model"""
    id: str
    owner_id: str
    status: str  # active, ended
    context: str | None = None
    summary: str | None = None
    created_at: float | None = None
    updated_at: float | None = None
    ended_at: float | None = None


@dataclass
class Message:
    """Message data model"""
    id: str
    conversation_id: str
    role: str  # user, assistant, tool
    content: str
    tool_calls: str | None = None
    timestamp: float | None = None


@dataclass
class UserProfile:
    """User profile data model"""
    user_id: str
    preferences: dict | None = None
    commitments: dict | None = None
    knowledge: dict | None = None
    last_updated: float | None = None


@dataclass
class ConversationSummary:
    """Conversation summary data model"""
    id: str
    conversation_id: str
    summary: str
    key_topics: str | None = None
    decisions: str | None = None
    created_at: float | None = None
    message_count: int | None = None


@dataclass
class ImportantMemory:
    """Important memory data model"""
    id: str
    user_id: str
    content: str
    memory_type: str | None = None
    importance: float | None = None
    created_at: float | None = None


@dataclass
class KnowledgeItem:
    """Knowledge item data model"""
    id: str
    user_id: str
    content: str
    category: str | None = None
    source: str | None = None
    embedding: bytes | None = None
    created_at: float | None = None
    is_private: bool = True


# ============ Database Schema ============

CONVERSATIONS_DB_SCHEMA = """
-- 会话表
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    status TEXT NOT NULL,
    context TEXT,
    summary TEXT,
    created_at REAL,
    updated_at REAL,
    ended_at REAL
);

CREATE INDEX IF NOT EXISTS idx_conv_owner ON conversations(owner_id);
CREATE INDEX IF NOT EXISTS idx_conv_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conv_created ON conversations(created_at);

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_calls TEXT,
    timestamp REAL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_msg_timestamp ON messages(timestamp);
"""


MEMORY_DB_SCHEMA = """
-- 对话摘要表
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    key_topics TEXT,
    decisions TEXT,
    created_at REAL,
    message_count INTEGER
);

CREATE INDEX IF NOT EXISTS idx_summ_conv ON conversation_summaries(conversation_id);
CREATE INDEX IF NOT EXISTS idx_summ_created ON conversation_summaries(created_at);

-- 用户画像表
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY,
    preferences TEXT,
    commitments TEXT,
    knowledge TEXT,
    last_updated REAL
);

-- 重要记忆表
CREATE TABLE IF NOT EXISTS important_memories (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    memory_type TEXT,
    importance REAL,
    created_at REAL
);

CREATE INDEX IF NOT EXISTS idx_mem_user ON important_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_mem_importance ON important_memories(importance);
CREATE INDEX IF NOT EXISTS idx_mem_type ON important_memories(memory_type);
"""


KNOWLEDGE_DB_SCHEMA = """
-- 知识条目表
CREATE TABLE IF NOT EXISTS knowledge_items (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT,
    source TEXT,
    embedding BLOB,
    created_at REAL,
    is_private INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_knowledge_user ON knowledge_items(user_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge_items(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_created ON knowledge_items(created_at);
"""


# ============ UserDatabase Class ============

class UserDatabase:
    """
    用户数据库

    管理用户专属的SQLite数据库：
    1. 对话历史 (conversations.db)
    2. 记忆/画像 (memory.db)
    3. 私有知识库 (knowledge.db)

    每个用户拥有独立的数据库文件，确保数据隔离。
    使用aiosqlite进行异步操作，支持连接池管理。
    """

    def __init__(
        self,
        wallet_address: str,
        data_dir: str = "/data/users"
    ):
        """
        Initialize UserDatabase

        Args:
            wallet_address: 用户钱包地址
            data_dir: 用户数据根目录
        """
        self.wallet_address = wallet_address
        self.db_dir = Path(data_dir) / wallet_address

        # Database connections
        self._conversations_db: aiosqlite.Connection | None = None
        self._memory_db: aiosqlite.Connection | None = None
        self._knowledge_db: aiosqlite.Connection | None = None

        # Connection locks for thread safety
        self._conv_lock = asyncio.Lock()
        self._memory_lock = asyncio.Lock()
        self._knowledge_lock = asyncio.Lock()

        # Connection pool management
        self._initialized = False

    async def init(self) -> None:
        """
        初始化数据库连接和表结构

        创建必要的目录和数据库文件，初始化表结构。
        """
        if self._initialized:
            return

        # Create database directory if it doesn't exist
        self.db_dir.mkdir(parents=True, exist_ok=True)

        # Initialize conversations database
        conv_db_path = self.db_dir / "conversations.db"
        self._conversations_db = await aiosqlite.connect(
            str(conv_db_path),
            isolation_level=None  # Autocommit mode
        )
        self._conversations_db.row_factory = aiosqlite.Row
        await self._conversations_db.executescript(CONVERSATIONS_DB_SCHEMA)

        # Initialize memory database
        memory_db_path = self.db_dir / "memory.db"
        self._memory_db = await aiosqlite.connect(
            str(memory_db_path),
            isolation_level=None
        )
        self._memory_db.row_factory = aiosqlite.Row
        await self._memory_db.executescript(MEMORY_DB_SCHEMA)

        # Initialize knowledge database
        knowledge_db_path = self.db_dir / "knowledge.db"
        self._knowledge_db = await aiosqlite.connect(
            str(knowledge_db_path),
            isolation_level=None
        )
        self._knowledge_db.row_factory = aiosqlite.Row
        await self._knowledge_db.executescript(KNOWLEDGE_DB_SCHEMA)

        self._initialized = True

    async def close(self) -> None:
        """
        关闭数据库连接

        优雅地关闭所有数据库连接，释放资源。
        """
        if self._conversations_db:
            await self._conversations_db.close()
            self._conversations_db = None

        if self._memory_db:
            await self._memory_db.close()
            self._memory_db = None

        if self._knowledge_db:
            await self._knowledge_db.close()
            self._knowledge_db = None

        self._initialized = False

    # ============ Connection Pool Management ============

    def _get_conv_db(self) -> aiosqlite.Connection:
        """Get conversations database connection"""
        if not self._conversations_db:
            raise RuntimeError("Database not initialized. Call init() first.")
        return self._conversations_db

    def _get_memory_db(self) -> aiosqlite.Connection:
        """Get memory database connection"""
        if not self._memory_db:
            raise RuntimeError("Database not initialized. Call init() first.")
        return self._memory_db

    def _get_knowledge_db(self) -> aiosqlite.Connection:
        """Get knowledge database connection"""
        if not self._knowledge_db:
            raise RuntimeError("Database not initialized. Call init() first.")
        return self._knowledge_db

    # ============ Conversation Methods ============

    async def create_conversation(
        self,
        context: str | None = None
    ) -> Conversation:
        """
        Create a new conversation

        Args:
            context: Optional initial context for the conversation

        Returns:
            The created Conversation object
        """
        conv_id = str(uuid.uuid4())
        now = datetime.now().timestamp()

        conv = Conversation(
            id=conv_id,
            owner_id=self.wallet_address,
            status="active",
            context=context,
            created_at=now,
            updated_at=now
        )

        db = self._get_conv_db()
        async with self._conv_lock:
            await db.execute(
                """
                INSERT INTO conversations (id, owner_id, status, context, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (conv.id, conv.owner_id, conv.status, conv.context, conv.created_at, conv.updated_at)
            )

        return conv

    async def get_conversation(self, conv_id: str) -> Conversation | None:
        """
        Get a conversation by ID

        Args:
            conv_id: The conversation ID

        Returns:
            The Conversation object if found, None otherwise
        """
        db = self._get_conv_db()
        async with self._conv_lock:
            cursor = await db.execute(
                """
                SELECT id, owner_id, status, context, summary, created_at, updated_at, ended_at
                FROM conversations WHERE id = ?
                """,
                (conv_id,)
            )
            row = await cursor.fetchone()

        if row:
            return Conversation(
                id=row["id"],
                owner_id=row["owner_id"],
                status=row["status"],
                context=row["context"],
                summary=row["summary"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                ended_at=row["ended_at"]
            )
        return None

    async def get_active_conversation(self) -> Conversation | None:
        """
        Get the most recent active conversation

        Returns:
            The most recent active Conversation object, None if no active conversation
        """
        db = self._get_conv_db()
        async with self._conv_lock:
            cursor = await db.execute(
                """
                SELECT id, owner_id, status, context, summary, created_at, updated_at, ended_at
                FROM conversations
                WHERE owner_id = ? AND status = 'active'
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (self.wallet_address,)
            )
            row = await cursor.fetchone()

        if row:
            return Conversation(
                id=row["id"],
                owner_id=row["owner_id"],
                status=row["status"],
                context=row["context"],
                summary=row["summary"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                ended_at=row["ended_at"]
            )
        return None

    async def update_conversation(
        self,
        conv_id: str,
        **kwargs
    ) -> bool:
        """
        Update conversation fields

        Args:
            conv_id: The conversation ID
            **kwargs: Fields to update (status, context, summary, ended_at)

        Returns:
            True if updated, False if not found
        """
        updates = []
        values = []

        for field in ["status", "context", "summary", "ended_at"]:
            if field in kwargs:
                updates.append(f"{field} = ?")
                values.append(kwargs[field])

        if not updates:
            return False

        updates.append("updated_at = ?")
        values.append(datetime.now().timestamp())
        values.append(conv_id)

        db = self._get_conv_db()
        async with self._conv_lock:
            cursor = await db.execute(
                f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?",
                values
            )
            await db.commit()

        return cursor.rowcount > 0

    async def get_all_conversations(
        self,
        status: str | None = None,
        limit: int = 50
    ) -> list[Conversation]:
        """
        Get all conversations for the user

        Args:
            status: Optional filter by status (active, ended)
            limit: Maximum number of conversations to return

        Returns:
            List of Conversation objects
        """
        query = """
            SELECT id, owner_id, status, context, summary, created_at, updated_at, ended_at
            FROM conversations WHERE owner_id = ?
        """
        params = [self.wallet_address]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        db = self._get_conv_db()
        async with self._conv_lock:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

        return [
            Conversation(
                id=row["id"],
                owner_id=row["owner_id"],
                status=row["status"],
                context=row["context"],
                summary=row["summary"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                ended_at=row["ended_at"]
            )
            for row in rows
        ]

    async def add_message(self, conv_id: str, message: Message) -> None:
        """
        Add a message to a conversation

        Args:
            conv_id: The conversation ID
            message: The Message object to add
        """
        if not message.timestamp:
            message.timestamp = datetime.now().timestamp()

        db = self._get_conv_db()
        async with self._conv_lock:
            await db.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, tool_calls, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (message.id, conv_id, message.role, message.content, message.tool_calls, message.timestamp)
            )

            # Update conversation updated_at
            await db.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (message.timestamp, conv_id)
            )

    async def get_messages(
        self,
        conv_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> list[Message]:
        """
        Get messages from a conversation

        Args:
            conv_id: The conversation ID
            limit: Maximum number of messages to return
            offset: Number of messages to skip

        Returns:
            List of Message objects
        """
        db = self._get_conv_db()
        async with self._conv_lock:
            cursor = await db.execute(
                """
                SELECT id, conversation_id, role, content, tool_calls, timestamp
                FROM messages WHERE conversation_id = ?
                ORDER BY timestamp ASC LIMIT ? OFFSET ?
                """,
                (conv_id, limit, offset)
            )
            rows = await cursor.fetchall()

        return [
            Message(
                id=row["id"],
                conversation_id=row["conversation_id"],
                role=row["role"],
                content=row["content"],
                tool_calls=row["tool_calls"],
                timestamp=row["timestamp"]
            )
            for row in rows
        ]

    async def get_message_count(self, conv_id: str) -> int:
        """
        Get the total number of messages in a conversation

        Args:
            conv_id: The conversation ID

        Returns:
            Number of messages
        """
        db = self._get_conv_db()
        async with self._conv_lock:
            cursor = await db.execute(
                "SELECT COUNT(*) as count FROM messages WHERE conversation_id = ?",
                (conv_id,)
            )
            row = await cursor.fetchone()

        return row["count"] if row else 0

    # ============ Memory Methods ============

    async def get_profile(self) -> UserProfile | None:
        """
        Get the user profile

        Returns:
            UserProfile object if found, None otherwise
        """
        db = self._get_memory_db()
        async with self._memory_lock:
            cursor = await db.execute(
                """
                SELECT user_id, preferences, commitments, knowledge, last_updated
                FROM user_profiles WHERE user_id = ?
                """,
                (self.wallet_address,)
            )
            row = await cursor.fetchone()

        if row:
            return UserProfile(
                user_id=row["user_id"],
                preferences=json.loads(row["preferences"]) if row["preferences"] else None,
                commitments=json.loads(row["commitments"]) if row["commitments"] else None,
                knowledge=json.loads(row["knowledge"]) if row["knowledge"] else None,
                last_updated=row["last_updated"]
            )
        return None

    async def update_profile(self, profile: dict) -> None:
        """
        Update the user profile

        Args:
            profile: Dictionary containing profile data (preferences, commitments, knowledge)
        """
        now = datetime.now().timestamp()
        preferences_json = json.dumps(profile.get("preferences", {}))
        commitments_json = json.dumps(profile.get("commitments", {}))
        knowledge_json = json.dumps(profile.get("knowledge", {}))

        db = self._get_memory_db()
        async with self._memory_lock:
            await db.execute(
                """
                INSERT INTO user_profiles (user_id, preferences, commitments, knowledge, last_updated)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    preferences = excluded.preferences,
                    commitments = excluded.commitments,
                    knowledge = excluded.knowledge,
                    last_updated = excluded.last_updated
                """,
                (self.wallet_address, preferences_json, commitments_json, knowledge_json, now)
            )

    async def add_memory(self, memory: dict) -> None:
        """
        Add an important memory

        Args:
            memory: Dictionary containing memory data (content, memory_type, importance)
        """
        mem_id = str(uuid.uuid4())
        now = datetime.now().timestamp()

        db = self._get_memory_db()
        async with self._memory_lock:
            await db.execute(
                """
                INSERT INTO important_memories (id, user_id, content, memory_type, importance, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    mem_id,
                    self.wallet_address,
                    memory["content"],
                    memory.get("memory_type"),
                    memory.get("importance", 1.0),
                    now
                )
            )

    async def get_memories(
        self,
        limit: int = 20,
        memory_type: str | None = None,
        min_importance: float | None = None
    ) -> list[ImportantMemory]:
        """
        Get important memories for the user

        Args:
            limit: Maximum number of memories to return
            memory_type: Optional filter by memory type
            min_importance: Optional minimum importance threshold

        Returns:
            List of ImportantMemory objects
        """
        query = """
            SELECT id, user_id, content, memory_type, importance, created_at
            FROM important_memories WHERE user_id = ?
        """
        params = [self.wallet_address]

        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)

        if min_importance:
            query += " AND importance >= ?"
            params.append(min_importance)

        query += " ORDER BY importance DESC, created_at DESC LIMIT ?"
        params.append(limit)

        db = self._get_memory_db()
        async with self._memory_lock:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

        return [
            ImportantMemory(
                id=row["id"],
                user_id=row["user_id"],
                content=row["content"],
                memory_type=row["memory_type"],
                importance=row["importance"],
                created_at=row["created_at"]
            )
            for row in rows
        ]

    async def add_conversation_summary(
        self,
        conv_id: str,
        summary: str,
        key_topics: list[str] | None = None,
        decisions: list[str] | None = None,
        message_count: int | None = None
    ) -> ConversationSummary:
        """
        Add a conversation summary

        Args:
            conv_id: The conversation ID
            summary: The summary text
            key_topics: Optional list of key topics
            decisions: Optional list of decisions made
            message_count: Optional number of messages summarized

        Returns:
            The created ConversationSummary object
        """
        summary_id = str(uuid.uuid4())
        now = datetime.now().timestamp()

        db = self._get_memory_db()
        async with self._memory_lock:
            await db.execute(
                """
                INSERT INTO conversation_summaries
                (id, conversation_id, summary, key_topics, decisions, created_at, message_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary_id,
                    conv_id,
                    summary,
                    json.dumps(key_topics) if key_topics else None,
                    json.dumps(decisions) if decisions else None,
                    now,
                    message_count
                )
            )

        return ConversationSummary(
            id=summary_id,
            conversation_id=conv_id,
            summary=summary,
            key_topics=json.dumps(key_topics) if key_topics else None,
            decisions=json.dumps(decisions) if decisions else None,
            created_at=now,
            message_count=message_count
        )

    async def get_conversation_summaries(
        self,
        conv_id: str | None = None,
        limit: int = 20
    ) -> list[ConversationSummary]:
        """
        Get conversation summaries

        Args:
            conv_id: Optional filter by conversation ID
            limit: Maximum number of summaries to return

        Returns:
            List of ConversationSummary objects
        """
        query = """
            SELECT id, conversation_id, summary, key_topics, decisions, created_at, message_count
            FROM conversation_summaries
        """
        params = []

        if conv_id:
            query += " WHERE conversation_id = ?"
            params.append(conv_id)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        db = self._get_memory_db()
        async with self._memory_lock:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()

        return [
            ConversationSummary(
                id=row["id"],
                conversation_id=row["conversation_id"],
                summary=row["summary"],
                key_topics=row["key_topics"],
                decisions=row["decisions"],
                created_at=row["created_at"],
                message_count=row["message_count"]
            )
            for row in rows
        ]

    # ============ Knowledge Methods ============

    async def add_knowledge(self, item: dict) -> KnowledgeItem:
        """
        Add a knowledge item

        Args:
            item: Dictionary containing knowledge data (content, category, source, embedding)

        Returns:
            The created KnowledgeItem object
        """
        item_id = str(uuid.uuid4())
        now = datetime.now().timestamp()

        db = self._get_knowledge_db()
        async with self._knowledge_lock:
            await db.execute(
                """
                INSERT INTO knowledge_items
                (id, user_id, content, category, source, embedding, created_at, is_private)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    self.wallet_address,
                    item["content"],
                    item.get("category"),
                    item.get("source"),
                    item.get("embedding"),
                    now,
                    item.get("is_private", True)
                )
            )

        return KnowledgeItem(
            id=item_id,
            user_id=self.wallet_address,
            content=item["content"],
            category=item.get("category"),
            source=item.get("source"),
            embedding=item.get("embedding"),
            created_at=now,
            is_private=item.get("is_private", True)
        )

    async def search_knowledge(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None
    ) -> list[dict]:
        """
        Search knowledge items

        This is a simple text-based search. For vector search,
        implement embedding-based similarity search.

        Args:
            query: The search query
            top_k: Maximum number of results to return
            category: Optional filter by category

        Returns:
            List of knowledge items as dictionaries
        """
        search_query = f"%{query}%"

        sql = """
            SELECT id, user_id, content, category, source, created_at, is_private
            FROM knowledge_items WHERE user_id = ? AND content LIKE ?
        """
        params = [self.wallet_address, search_query]

        if category:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(top_k)

        db = self._get_knowledge_db()
        async with self._knowledge_lock:
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()

        return [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "content": row["content"],
                "category": row["category"],
                "source": row["source"],
                "created_at": row["created_at"],
                "is_private": bool(row["is_private"])
            }
            for row in rows
        ]

    async def get_knowledge_by_id(self, item_id: str) -> KnowledgeItem | None:
        """
        Get a knowledge item by ID

        Args:
            item_id: The knowledge item ID

        Returns:
            KnowledgeItem object if found, None otherwise
        """
        db = self._get_knowledge_db()
        async with self._knowledge_lock:
            cursor = await db.execute(
                """
                SELECT id, user_id, content, category, source, embedding, created_at, is_private
                FROM knowledge_items WHERE id = ? AND user_id = ?
                """,
                (item_id, self.wallet_address)
            )
            row = await cursor.fetchone()

        if row:
            return KnowledgeItem(
                id=row["id"],
                user_id=row["user_id"],
                content=row["content"],
                category=row["category"],
                source=row["source"],
                embedding=row["embedding"],
                created_at=row["created_at"],
                is_private=bool(row["is_private"])
            )
        return None

    async def delete_knowledge(self, item_id: str) -> bool:
        """
        Delete a knowledge item

        Args:
            item_id: The knowledge item ID

        Returns:
            True if deleted, False if not found
        """
        db = self._get_knowledge_db()
        async with self._knowledge_lock:
            cursor = await db.execute(
                "DELETE FROM knowledge_items WHERE id = ? AND user_id = ?",
                (item_id, self.wallet_address)
            )

        return cursor.rowcount > 0

    async def get_all_knowledge(
        self,
        category: str | None = None,
        limit: int = 50
    ) -> list[dict]:
        """
        Get all knowledge items for the user

        Args:
            category: Optional filter by category
            limit: Maximum number of items to return

        Returns:
            List of knowledge items as dictionaries
        """
        sql = """
            SELECT id, user_id, content, category, source, created_at, is_private
            FROM knowledge_items WHERE user_id = ?
        """
        params = [self.wallet_address]

        if category:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        db = self._get_knowledge_db()
        async with self._knowledge_lock:
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()

        return [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "content": row["content"],
                "category": row["category"],
                "source": row["source"],
                "created_at": row["created_at"],
                "is_private": bool(row["is_private"])
            }
            for row in rows
        ]

    # ============ Data Import/Export ============

    async def export_data(self) -> dict[str, Any]:
        """
        Export all user data

        Returns:
            Dictionary containing all user data
        """
        export = {
            "wallet_address": self.wallet_address,
            "exported_at": datetime.now().isoformat(),
            "conversations": [],
            "profile": None,
            "memories": [],
            "knowledge": []
        }

        # Export conversations
        conversations = await self.get_all_conversations()
        for conv in conversations:
            conv_data = asdict(conv)
            conv_data["messages"] = []
            messages = await self.get_messages(conv.id, limit=1000)
            conv_data["messages"] = [asdict(msg) for msg in messages]
            export["conversations"].append(conv_data)

        # Export profile
        profile = await self.get_profile()
        if profile:
            export["profile"] = asdict(profile)

        # Export memories
        memories = await self.get_memories(limit=100)
        export["memories"] = [asdict(mem) for mem in memories]

        # Export knowledge
        knowledge = await self.get_all_knowledge(limit=100)
        export["knowledge"] = [
            {k: v for k, v in item.items() if k != "embedding"}
            for item in knowledge
        ]

        return export

    async def import_data(self, data: dict[str, Any]) -> None:
        """
        Import user data

        Args:
            data: Dictionary containing user data to import
        """
        # Import profile
        if "profile" in data and data["profile"]:
            profile_data = data["profile"]
            await self.update_profile({
                "preferences": profile_data.get("preferences"),
                "commitments": profile_data.get("commitments"),
                "knowledge": profile_data.get("knowledge")
            })

        # Import conversations and messages
        if "conversations" in data:
            for conv_data in data["conversations"]:
                conv = Conversation(
                    id=conv_data["id"],
                    owner_id=self.wallet_address,
                    status=conv_data["status"],
                    context=conv_data.get("context"),
                    summary=conv_data.get("summary"),
                    created_at=conv_data.get("created_at"),
                    updated_at=conv_data.get("updated_at"),
                    ended_at=conv_data.get("ended_at")
                )

                db = self._get_conv_db()
                async with self._conv_lock:
                    await db.execute(
                        """
                        INSERT OR REPLACE INTO conversations
                        (id, owner_id, status, context, summary, created_at, updated_at, ended_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            conv.id, conv.owner_id, conv.status, conv.context,
                            conv.summary, conv.created_at, conv.updated_at, conv.ended_at
                        )
                    )

                # Import messages
                if "messages" in conv_data:
                    for msg_data in conv_data["messages"]:
                        await self.add_message(
                            conv.id,
                            Message(**msg_data)
                        )

        # Import memories
        if "memories" in data:
            for mem_data in data["memories"]:
                await self.add_memory({
                    "content": mem_data["content"],
                    "memory_type": mem_data.get("memory_type"),
                    "importance": mem_data.get("importance", 1.0)
                })

        # Import knowledge
        if "knowledge" in data:
            for item_data in data["knowledge"]:
                await self.add_knowledge({
                    "content": item_data["content"],
                    "category": item_data.get("category"),
                    "source": item_data.get("source"),
                    "is_private": item_data.get("is_private", True)
                })

    # ============ Utility Methods ============

    async def get_db_info(self) -> dict[str, Any]:
        """
        Get database information

        Returns:
            Dictionary containing database statistics
        """
        info = {
            "wallet_address": self.wallet_address,
            "db_dir": str(self.db_dir),
            "initialized": self._initialized,
            "conversations": {
                "db_file": str(self.db_dir / "conversations.db"),
                "total_conversations": 0,
                "active_conversations": 0,
                "total_messages": 0
            },
            "memory": {
                "db_file": str(self.db_dir / "memory.db"),
                "has_profile": False,
                "total_memories": 0,
                "total_summaries": 0
            },
            "knowledge": {
                "db_file": str(self.db_dir / "knowledge.db"),
                "total_items": 0
            }
        }

        if self._initialized:
            # Conversations stats
            conv_db = self._get_conv_db()

            async with self._conv_lock:
                cursor = await conv_db.execute(
                    "SELECT COUNT(*) FROM conversations WHERE owner_id = ?",
                    (self.wallet_address,)
                )
                row = await cursor.fetchone()
                info["conversations"]["total_conversations"] = row[0]

                cursor = await conv_db.execute(
                    "SELECT COUNT(*) FROM conversations WHERE owner_id = ? AND status = 'active'",
                    (self.wallet_address,)
                )
                row = await cursor.fetchone()
                info["conversations"]["active_conversations"] = row[0]

                cursor = await conv_db.execute(
                    """
                    SELECT COUNT(*) FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE c.owner_id = ?
                    """,
                    (self.wallet_address,)
                )
                row = await cursor.fetchone()
                info["conversations"]["total_messages"] = row[0]

            # Memory stats
            mem_db = self._get_memory_db()

            # Get profile without holding the lock (to avoid deadlock)
            profile = await self.get_profile()
            info["memory"]["has_profile"] = profile is not None

            async with self._memory_lock:
                cursor = await mem_db.execute(
                    "SELECT COUNT(*) FROM important_memories WHERE user_id = ?",
                    (self.wallet_address,)
                )
                row = await cursor.fetchone()
                info["memory"]["total_memories"] = row[0]

                cursor = await mem_db.execute(
                    "SELECT COUNT(*) FROM conversation_summaries",
                    ()
                )
                row = await cursor.fetchone()
                info["memory"]["total_summaries"] = row[0]

            # Knowledge stats
            know_db = self._get_knowledge_db()

            async with self._knowledge_lock:
                cursor = await know_db.execute(
                    "SELECT COUNT(*) FROM knowledge_items WHERE user_id = ?",
                    (self.wallet_address,)
                )
                row = await cursor.fetchone()
                info["knowledge"]["total_items"] = row[0]

        return info

    async def vacuum(self) -> None:
        """
        Optimize database files

        Runs VACUUM on all databases to reclaim space.
        """
        if self._conversations_db:
            await self._conversations_db.execute("VACUUM")

        if self._memory_db:
            await self._memory_db.execute("VACUUM")

        if self._knowledge_db:
            await self._knowledge_db.execute("VACUUM")


# ============ Factory Function ============

async def create_user_database(
    wallet_address: str,
    data_dir: str = "/data/users"
) -> UserDatabase:
    """
    Create and initialize a UserDatabase

    Args:
        wallet_address: User wallet address
        data_dir: User data root directory

    Returns:
        Initialized UserDatabase instance
    """
    db = UserDatabase(wallet_address, data_dir)
    await db.init()
    return db
