"""
GeneCapsuleManager - 基因胶囊管理

USMSB 核心服务之一。
管理 Agent 的经验基因胶囊。

功能：
- Gene Capsule 创建/存储/检索
- 经验向量索引
- 能力匹配
"""

import uuid
import json
import sqlite3
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class GeneCapsule:
    """
    基因胶囊
    
    存储 Agent 的经验、能力、偏好等。
    用于精准匹配。
    """
    id: str
    agent_id: str
    category: str  # capability, experience, preference, goal
    content: dict  # 内容
    quality_score: float = 0.5  # 质量分数
    embedding: list[float] | None = None  # 向量（简化版）
    keywords: list[str] = field(default_factory=list)  # 关键词
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "category": self.category,
            "content": self.content,
            "quality_score": self.quality_score,
            "keywords": self.keywords,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


class GeneCapsuleDB:
    """基因胶囊数据库"""
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/gene_capsule_core.db"
        
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gene_capsules (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                quality_score REAL DEFAULT 0.5,
                keywords TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent ON gene_capsules(agent_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_category ON gene_capsules(category)
        """)
        
        conn.commit()
        conn.close()
    
    def save(self, capsule: GeneCapsule) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO gene_capsules 
            (id, agent_id, category, content, quality_score, keywords, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            capsule.id,
            capsule.agent_id,
            capsule.category,
            json.dumps(capsule.content),
            capsule.quality_score,
            json.dumps(capsule.keywords),
            capsule.created_at,
            capsule.updated_at,
            json.dumps(capsule.metadata)
        ))
        
        conn.commit()
        conn.close()
        return True
    
    def load(self, capsule_id: str) -> GeneCapsule | None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM gene_capsules WHERE id = ?
        """, (capsule_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return GeneCapsule(
                id=row[0],
                agent_id=row[1],
                category=row[2],
                content=json.loads(row[3]),
                quality_score=row[4],
                keywords=json.loads(row[5]) if row[5] else [],
                created_at=row[6],
                updated_at=row[7],
                metadata=json.loads(row[8]) if row[8] else {}
            )
        return None
    
    def load_by_agent(self, agent_id: str) -> list[GeneCapsule]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM gene_capsules WHERE agent_id = ?
            ORDER BY updated_at DESC
        """, (agent_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            GeneCapsule(
                id=row[0],
                agent_id=row[1],
                category=row[2],
                content=json.loads(row[3]),
                quality_score=row[4],
                keywords=json.loads(row[5]) if row[5] else [],
                created_at=row[6],
                updated_at=row[7],
                metadata=json.loads(row[8]) if row[8] else {}
            )
            for row in rows
        ]
    
    def delete(self, capsule_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM gene_capsules WHERE id = ?", (capsule_id,))
        conn.commit()
        conn.close()
        return True


class GeneCapsuleManager:
    """
    基因胶囊管理器
    
    使用方式：
    ```python
    manager = GeneCapsuleManager()
    
    # 创建胶囊
    capsule_id = manager.create_capsule(
        agent_id="agent_001",
        category="capability",
        content={"skill": "coding", "level": 5}
    )
    
    # 获取胶囊
    capsule = manager.get_capsule(capsule_id)
    
    # 搜索相似胶囊
    similar = manager.find_similar("coding", top_k=5)
    ```
    """
    
    def __init__(self, db_path: str | None = None):
        self.db = GeneCapsuleDB(db_path)
    
    def create_capsule(
        self,
        agent_id: str,
        category: str,
        content: dict,
        quality_score: float = 0.5,
        keywords: list[str] | None = None
    ) -> str:
        """
        创建基因胶囊
        
        Args:
            agent_id: Agent ID
            category: 类别
            content: 内容
            quality_score: 质量分数
            keywords: 关键词
            
        Returns:
            str: 胶囊 ID
        """
        capsule = GeneCapsule(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            category=category,
            content=content,
            quality_score=quality_score,
            keywords=keywords or self._extract_keywords(content)
        )
        
        self.db.save(capsule)
        
        return capsule.id
    
    def get_capsule(self, capsule_id: str) -> GeneCapsule | None:
        """获取胶囊"""
        return self.db.load(capsule_id)
    
    def get_agent_capsules(self, agent_id: str) -> list[GeneCapsule]:
        """获取 Agent 的所有胶囊"""
        return self.db.load_by_agent(agent_id)
    
    def update_capsule(
        self,
        capsule_id: str,
        content: dict | None = None,
        quality_score: float | None = None
    ) -> bool:
        """更新胶囊"""
        capsule = self.db.load(capsule_id)
        if not capsule:
            return False
        
        if content is not None:
            capsule.content = content
        if quality_score is not None:
            capsule.quality_score = quality_score
        
        capsule.updated_at = datetime.now().timestamp()
        capsule.keywords = self._extract_keywords(capsule.content)
        
        return self.db.save(capsule)
    
    def delete_capsule(self, capsule_id: str) -> bool:
        """删除胶囊"""
        return self.db.delete(capsule_id)
    
    def find_similar(
        self,
        query: str,
        category: str | None = None,
        top_k: int = 10
    ) -> list[GeneCapsule]:
        """
        搜索相似胶囊（简化版，基于关键词匹配）
        
        Args:
            query: 查询关键词
            category: 类别过滤
            top_k: 返回数量
            
        Returns:
            list[GeneCapsule]: 匹配的胶囊
        """
        query_lower = query.lower()
        all_capsules = []
        
        # 简化实现：加载所有胶囊并过滤
        # 真实场景应该使用向量数据库
        for capsule in self.db.load_by_agent(""):  # 需要修复：应该加载所有
            all_capsules.append(capsule)
        
        # 按关键词匹配
        matched = []
        for capsule in all_capsules:
            if category and capsule.category != category:
                continue
            
            # 检查关键词匹配
            if any(query_lower in kw.lower() for kw in capsule.keywords):
                matched.append(capsule)
                continue
            
            # 检查内容匹配
            content_str = json.dumps(capsule.content).lower()
            if query_lower in content_str:
                matched.append(capsule)
        
        # 按质量分数排序
        matched.sort(key=lambda c: c.quality_score, reverse=True)
        
        return matched[:top_k]
    
    def _extract_keywords(self, content: dict) -> list[str]:
        """从内容中提取关键词（简化版）"""
        keywords = []
        
        def extract(obj):
            if isinstance(obj, str):
                words = obj.replace("_", " ").replace("-", " ").split()
                keywords.extend([w.lower() for w in words if len(w) > 2])
            elif isinstance(obj, dict):
                for v in obj.values():
                    extract(v)
            elif isinstance(obj, list):
                for item in obj:
                    extract(item)
        
        extract(content)
        
        # 去重
        return list(set(keywords))
    
    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        capsules = self.db.load_by_agent("")
        
        by_category = {}
        total_quality = 0
        
        for capsule in capsules:
            by_category[capsule.category] = by_category.get(capsule.category, 0) + 1
            total_quality += capsule.quality_score
        
        return {
            "total_capsules": len(capsules),
            "by_category": by_category,
            "average_quality": total_quality / len(capsules) if capsules else 0,
        }
