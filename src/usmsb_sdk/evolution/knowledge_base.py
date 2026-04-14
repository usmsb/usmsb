"""
KnowledgeBase - 共享知识库

Agent 间共享知识的系统：
- 知识存储和检索
- 语义搜索
- 知识贡献追踪
- 知识质量评分
"""

import uuid
import hashlib
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class KnowledgeEntry:
    """知识条目"""
    id: str
    author_id: str
    title: str
    content: str
    category: str
    tags: list[str]
    created_at: float
    updated_at: float
    access_count: int = 0
    usefulness_score: float = 0.0
    verified: bool = False


@dataclass
class KnowledgeContribution:
    """知识贡献"""
    agent_id: str
    entries_created: int = 0
    entries_edited: int = 0
    helpful_votes: int = 0
    total_usefulness: float = 0.0


class KnowledgeBase:
    """
    共享知识库
    
    支持：
    - 知识存储和检索
    - 分类和标签
    - 贡献者追踪
    - 质量评分
    """
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/knowledge_base.db"
        
        from pathlib import Path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_entries (
                id TEXT PRIMARY KEY,
                author_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                access_count INTEGER DEFAULT 0,
                usefulness_score REAL DEFAULT 0.0,
                verified INTEGER DEFAULT 0,
                content_hash TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_votes (
                id TEXT PRIMARY KEY,
                entry_id TEXT NOT NULL,
                voter_id TEXT NOT NULL,
                vote_type TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contributions (
                agent_id TEXT PRIMARY KEY,
                entries_created INTEGER DEFAULT 0,
                entries_edited INTEGER DEFAULT 0,
                helpful_votes INTEGER DEFAULT 0,
                total_usefulness REAL DEFAULT 0.0
            )
        """)
        
        # 全文搜索索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_category ON knowledge_entries(category)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_author ON knowledge_entries(author_id)
        """)
        
        conn.commit()
        conn.close()
    
    def add_entry(
        self,
        author_id: str,
        title: str,
        content: str,
        category: str,
        tags: list[str] = None
    ) -> str:
        """添加知识条目"""
        import json
        
        entry_id = str(uuid.uuid4())
        now = datetime.now().timestamp()
        
        # 内容哈希（去重）
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO knowledge_entries
            (id, author_id, title, content, category, tags, created_at, updated_at, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry_id, author_id, title, content, category,
            json.dumps(tags or []), now, now, content_hash
        ))
        
        # 更新贡献统计
        cursor.execute("""
            INSERT INTO contributions (agent_id, entries_created)
            VALUES (?, 1)
            ON CONFLICT(agent_id) DO UPDATE SET
                entries_created = entries_created + 1
        """, (author_id,))
        
        conn.commit()
        conn.close()
        
        return entry_id
    
    def update_entry(
        self,
        entry_id: str,
        editor_id: str,
        title: str = None,
        content: str = None,
        tags: list[str] = None
    ) -> bool:
        """更新知识条目"""
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if title:
            updates.append("title = ?")
            params.append(title)
        
        if content:
            updates.append("content = ?")
            params.append(content)
            updates.append("content_hash = ?")
            params.append(hashlib.sha256(content.encode()).hexdigest())
        
        if tags:
            updates.append("tags = ?")
            params.append(json.dumps(tags))
        
        updates.append("updated_at = ?")
        params.append(datetime.now().timestamp())
        
        params.append(entry_id)
        
        cursor.execute(f"""
            UPDATE knowledge_entries
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        
        # 更新编辑统计
        if cursor.rowcount > 0:
            cursor.execute("""
                INSERT INTO contributions (agent_id, entries_edited)
                VALUES (?, 1)
                ON CONFLICT(agent_id) DO UPDATE SET
                    entries_edited = entries_edited + 1
            """, (editor_id,))
            
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    
    def get_entry(self, entry_id: str) -> KnowledgeEntry | None:
        """获取知识条目"""
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, author_id, title, content, category, tags, created_at, updated_at,
                   access_count, usefulness_score, verified
            FROM knowledge_entries
            WHERE id = ?
        """, (entry_id,))
        
        row = cursor.fetchone()
        
        if row:
            # 增加访问计数
            cursor.execute("""
                UPDATE knowledge_entries SET access_count = access_count + 1 WHERE id = ?
            """, (entry_id,))
            conn.commit()
        
        conn.close()
        
        if row:
            return KnowledgeEntry(
                id=row[0],
                author_id=row[1],
                title=row[2],
                content=row[3],
                category=row[4],
                tags=json.loads(row[5]),
                created_at=row[6],
                updated_at=row[7],
                access_count=row[8],
                usefulness_score=row[9],
                verified=bool(row[10])
            )
        
        return None
    
    def search(
        self,
        query: str,
        category: str = None,
        tags: list[str] = None,
        limit: int = 20
    ) -> list[KnowledgeEntry]:
        """搜索知识库（简化版关键词搜索）"""
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = """
            SELECT id, author_id, title, content, category, tags, created_at, updated_at,
                   access_count, usefulness_score, verified
            FROM knowledge_entries
            WHERE (title LIKE ? OR content LIKE ?)
        """
        params = [f"%{query}%", f"%{query}%"]
        
        if category:
            sql += " AND category = ?"
            params.append(category)
        
        if tags:
            for tag in tags:
                sql += " AND tags LIKE ?"
                params.append(f"%{tag}%")
        
        sql += " ORDER BY usefulness_score DESC, access_count DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            KnowledgeEntry(
                id=row[0],
                author_id=row[1],
                title=row[2],
                content=row[3],
                category=row[4],
                tags=json.loads(row[5]),
                created_at=row[6],
                updated_at=row[7],
                access_count=row[8],
                usefulness_score=row[9],
                verified=bool(row[10])
            )
            for row in rows
        ]
    
    def get_by_category(self, category: str, limit: int = 50) -> list[KnowledgeEntry]:
        """按分类获取"""
        return self.search("", category=category, limit=limit)
    
    def vote(
        self,
        entry_id: str,
        voter_id: str,
        vote_type: str = "helpful"
    ) -> bool:
        """投票"""
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 检查是否已投票
        cursor.execute("""
            SELECT id FROM knowledge_votes
            WHERE entry_id = ? AND voter_id = ?
        """, (entry_id, voter_id))
        
        if cursor.fetchone():
            conn.close()
            return False  # 已投票
        
        # 记录投票
        cursor.execute("""
            INSERT INTO knowledge_votes (id, entry_id, voter_id, vote_type, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), entry_id, voter_id, vote_type, datetime.now().timestamp()))
        
        # 更新 usefulness_score
        if vote_type == "helpful":
            cursor.execute("""
                UPDATE knowledge_entries
                SET usefulness_score = usefulness_score + 1
                WHERE id = ?
            """, (entry_id,))
            
            # 更新贡献者统计
            cursor.execute("""
                UPDATE contributions
                SET helpful_votes = helpful_votes + 1,
                    total_usefulness = total_usefulness + 1
                WHERE agent_id = (
                    SELECT author_id FROM knowledge_entries WHERE id = ?
                )
            """, (entry_id,))
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_contributions(self, agent_id: str) -> KnowledgeContribution | None:
        """获取贡献统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT entries_created, entries_edited, helpful_votes, total_usefulness
            FROM contributions
            WHERE agent_id = ?
        """, (agent_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return KnowledgeContribution(
                agent_id=agent_id,
                entries_created=row[0],
                entries_edited=row[1],
                helpful_votes=row[2],
                total_usefulness=row[3]
            )
        
        return None
    
    def get_top_contributors(self, limit: int = 10) -> list[dict]:
        """获取 top 贡献者"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT agent_id, entries_created, helpful_votes, total_usefulness
            FROM contributions
            ORDER BY total_usefulness DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "agent_id": row[0],
                "entries_created": row[1],
                "helpful_votes": row[2],
                "total_usefulness": row[3]
            }
            for row in rows
        ]
    
    def get_statistics(self) -> dict:
        """获取知识库统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*), SUM(access_count), AVG(usefulness_score) FROM knowledge_entries")
        total, accesses, avg_usefulness = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(DISTINCT author_id) FROM knowledge_entries")
        unique_authors = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM knowledge_votes")
        total_votes = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_entries": total or 0,
            "total_accesses": accesses or 0,
            "avg_usefulness": avg_usefulness or 0,
            "unique_authors": unique_authors or 0,
            "total_votes": total_votes or 0
        }
