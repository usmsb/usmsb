"""
UserDatabase - 用户数据库

管理用户专属的SQLite数据库，包括：
- 对话历史
- 记忆/画像
- 私有知识库
"""

from typing import Optional, List, Dict
from pathlib import Path
import sqlite3
from dataclasses import dataclass


@dataclass
class Conversation:
    """对话"""
    id: str
    owner_id: str
    status: str
    context: Optional[str]
    summary: Optional[str]
    created_at: float
    updated_at: float
    ended_at: Optional[float]


@dataclass
class Message:
    """消息"""
    id: str
    conversation_id: str
    role: str
    content: str
    tool_calls: Optional[str]
    timestamp: float


@dataclass
class UserProfile:
    """用户画像"""
    user_id: str
    preferences: Optional[Dict]
    commitments: Optional[Dict]
    knowledge: Optional[Dict]
    last_updated: float


@dataclass
class Memory:
    """记忆"""
    id: str
    user_id: str
    content: str
    memory_type: Optional[str]
    importance: Optional[float]
    created_at: float


@dataclass
class KnowledgeItem:
    """知识条目"""
    id: str
    user_id: str
    content: str
    category: Optional[str]
    source: Optional[str]
    created_at: float
    is_private: int


class UserDatabase:
    """
    用户数据库

    管理用户专属的SQLite数据库：
    1. 对话历史
    2. 记忆/画像
    3. 私有知识库
    """

    # ========== 属性 ==========

    wallet_address: str
    db_dir: Path                         # 数据库目录

    conversations_db: sqlite3.Connection
    memory_db: sqlite3.Connection
    knowledge_db: sqlite3.Connection

    # ========== 核心方法 ==========

    # 会话相关
    async def create_conversation(self) -> Conversation:
        pass

    async def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        pass

    async def get_active_conversation(self) -> Optional[Conversation]:
        pass

    async def add_message(self, conv_id: str, message: Message) -> None:
        pass

    async def get_messages(self, conv_id: str, limit: int) -> List[Message]:
        pass

    # 记忆相关
    async def get_profile(self) -> Optional[UserProfile]:
        pass

    async def update_profile(self, profile: UserProfile) -> None:
        pass

    async def add_memory(self, memory: Memory) -> None:
        pass

    async def get_memories(self, limit: int) -> List[Memory]:
        pass

    # 知识库相关
    async def add_knowledge(self, item: KnowledgeItem) -> None:
        pass

    async def search_knowledge(self, query: str, top_k: int) -> List[KnowledgeItem]:
        pass

    async def delete_knowledge(self, item_id: str) -> bool:
        pass

    # 数据导入导出
    async def export_data(self) -> Dict:
        pass

    async def import_data(self, data: Dict) -> None:
        pass
