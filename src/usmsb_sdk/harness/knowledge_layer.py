# -*- coding: utf-8 -*-
"""
知识供给层 - Knowledge Layer

三层知识体系：
1. 参数化知识 (Parametric) - 结构化数据、配置、规则
2. 非参数化知识 (Non-Parametric) - RAG、文档、向量检索
3. 经验知识 (Experience) - 历史轨迹、案例库、模式库
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class KnowledgeType(Enum):
    """知识类型"""
    PARAMETRIC = "parametric"      # 参数化：配置、规则
    NON_PARAMETRIC = "non_parametric"  # 非参数化：文档、RAG
    EXPERIENCE = "experience"       # 经验：轨迹、案例


@dataclass
class KnowledgeEntry:
    """知识条目"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    knowledge_type: KnowledgeType = KnowledgeType.PARAMETRIC
    content: Any = None
    source: str = "unknown"
    embedding: list[float] | None = None
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    access_count: int = 0
    last_accessed: float | None = None
    
    def access(self) -> None:
        """访问知识"""
        self.access_count += 1
        self.last_accessed = datetime.now().timestamp()
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.knowledge_type.value,
            "content": str(self.content)[:100],
            "source": self.source,
            "access_count": self.access_count,
        }


class ParametricKnowledge:
    """
    参数化知识
    
    存储结构化数据：配置、规则、策略参数
    """
    
    def __init__(self):
        self._knowledge: dict[str, Any] = {}
        self._index: dict[str, list[str]] = {}  # category -> ids
    
    def add(self, key: str, value: Any, category: str = "default") -> str:
        """添加参数化知识"""
        entry = KnowledgeEntry(
            knowledge_type=KnowledgeType.PARAMETRIC,
            content={"key": key, "value": value},
            source="parametric",
            metadata={"category": category}
        )
        self._knowledge[entry.id] = entry
        
        if category not in self._index:
            self._index[category] = []
        self._index[category].append(entry.id)
        
        return entry.id
    
    def get(self, key: str) -> Any | None:
        """获取参数化知识"""
        for entry in self._knowledge.values():
            if entry.content.get("key") == key:
                entry.access()
                return entry.content.get("value")
        return None
    
    def list_by_category(self, category: str) -> list[KnowledgeEntry]:
        """按类别列出知识"""
        ids = self._index.get(category, [])
        return [self._knowledge[i] for i in ids if i in self._knowledge]
    
    def get_statistics(self) -> dict:
        return {
            "total": len(self._knowledge),
            "categories": len(self._index),
        }


class NonParametricKnowledge:
    """
    非参数化知识
    
    基于 RAG 的文档检索知识
    """
    
    def __init__(self):
        self._documents: dict[str, KnowledgeEntry] = {}
        self._chunks: dict[str, KnowledgeEntry] = {}
    
    def add_document(self, doc_id: str, content: str, metadata: dict | None = None) -> str:
        """添加文档"""
        entry = KnowledgeEntry(
            id=doc_id,
            knowledge_type=KnowledgeType.NON_PARAMETRIC,
            content=content,
            source="document",
            metadata=metadata or {}
        )
        self._documents[doc_id] = entry
        return doc_id
    
    def add_chunk(self, chunk_id: str, content: str, doc_id: str, 
                  embedding: list[float] | None = None) -> str:
        """添加文档块"""
        entry = KnowledgeEntry(
            id=chunk_id,
            knowledge_type=KnowledgeType.NON_PARAMETRIC,
            content=content,
            source="chunk",
            embedding=embedding,
            metadata={"doc_id": doc_id}
        )
        self._chunks[chunk_id] = entry
        return chunk_id
    
    def retrieve(self, query_embedding: list[float], top_k: int = 5) -> list[KnowledgeEntry]:
        """向量检索"""
        # 简单余弦相似度
        def cosine_sim(a: list[float], b: list[float]) -> float:
            if not a or not b or len(a) != len(b):
                return 0.0
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(x * x for x in b) ** 0.5
            return dot / (norm_a * norm_b + 1e-8)
        
        results = []
        for chunk in self._chunks.values():
            if chunk.embedding:
                sim = cosine_sim(query_embedding, chunk.embedding)
                results.append((sim, chunk))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:top_k]]
    
    def get_statistics(self) -> dict:
        return {
            "documents": len(self._documents),
            "chunks": len(self._chunks),
        }


class ExperienceKnowledge:
    """
    经验知识
    
    存储历史轨迹、案例库、模式库
    """
    
    def __init__(self):
        self._trajectories: dict[str, list[dict]] = {}  # task_id -> trajectory
        self._cases: dict[str, KnowledgeEntry] = {}  # case_id -> entry
        self._patterns: dict[str, KnowledgeEntry] = {}  # pattern_id -> entry
    
    def record_trajectory(self, task_id: str, trajectory: list[dict]) -> None:
        """记录任务轨迹"""
        self._trajectories[task_id] = trajectory
    
    def get_trajectory(self, task_id: str) -> list[dict] | None:
        """获取任务轨迹"""
        return self._trajectories.get(task_id)
    
    def add_case(self, case_id: str, task: str, outcome: str, 
                 lessons: list[str], metadata: dict | None = None) -> str:
        """添加案例"""
        entry = KnowledgeEntry(
            id=case_id,
            knowledge_type=KnowledgeType.EXPERIENCE,
            content={
                "task": task,
                "outcome": outcome,
                "lessons": lessons
            },
            source="case",
            metadata=metadata or {}
        )
        self._cases[case_id] = entry
        return case_id
    
    def add_pattern(self, pattern_id: str, pattern: str, 
                    success_rate: float, usage_count: int) -> str:
        """添加模式"""
        entry = KnowledgeEntry(
            id=pattern_id,
            knowledge_type=KnowledgeType.EXPERIENCE,
            content={
                "pattern": pattern,
                "success_rate": success_rate,
                "usage_count": usage_count
            },
            source="pattern"
        )
        self._patterns[pattern_id] = entry
        return pattern_id
    
    def query_similar_cases(self, task: str, limit: int = 5) -> list[KnowledgeEntry]:
        """查询相似案例（简单关键词匹配）"""
        keywords = set(task.lower().split())
        results = []
        
        for case in self._cases.values():
            case_text = str(case.content).lower()
            matches = sum(1 for kw in keywords if kw in case_text)
            if matches > 0:
                results.append((matches, case))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:limit]]
    
    def get_statistics(self) -> dict:
        return {
            "trajectories": len(self._trajectories),
            "cases": len(self._cases),
            "patterns": len(self._patterns),
        }


class KnowledgeLayer:
    """
    知识供给层
    
    整合三层知识，提供统一接口
    """
    
    def __init__(self):
        self.parametric = ParametricKnowledge()
        self.non_parametric = NonParametricKnowledge()
        self.experience = ExperienceKnowledge()
    
    def query(self, query: str, knowledge_types: list[KnowledgeType] | None = None) -> list[KnowledgeEntry]:
        """
        统一查询接口
        
        Args:
            query: 查询内容
            knowledge_types: 限定知识类型，None 表示全部
            
        Returns:
            匹配的知识条目
        """
        results = []
        types = knowledge_types or [KnowledgeType.PARAMETRIC, KnowledgeType.NON_PARAMETRIC, KnowledgeType.EXPERIENCE]
        
        # 参数化知识
        if KnowledgeType.PARAMETRIC in types:
            for entry in self.parametric._knowledge.values():
                if query.lower() in str(entry.content).lower():
                    entry.access()
                    results.append(entry)
        
        # 经验知识
        if KnowledgeType.EXPERIENCE in types:
            cases = self.experience.query_similar_cases(query)
            results.extend(cases)
        
        return results
    
    def get_statistics(self) -> dict:
        return {
            "parametric": self.parametric.get_statistics(),
            "non_parametric": self.non_parametric.get_statistics(),
            "experience": self.experience.get_statistics(),
        }
    
    def store_knowledge(self, content: Any, knowledge_type: KnowledgeType, 
                        source: str = "unknown", metadata: dict | None = None) -> str:
        """
        存储知识（统一接口）
        
        Args:
            content: 知识内容
            knowledge_type: 知识类型
            source: 来源
            metadata: 元数据
            
        Returns:
            知识ID
        """
        entry = KnowledgeEntry(
            knowledge_type=knowledge_type,
            content=content,
            source=source,
            metadata=metadata or {}
        )
        
        if knowledge_type == KnowledgeType.PARAMETRIC:
            self.parametric._knowledge[entry.id] = entry
        elif knowledge_type == KnowledgeType.NON_PARAMETRIC:
            self.non_parametric._documents[entry.id] = entry
        elif knowledge_type == KnowledgeType.EXPERIENCE:
            self.experience._cases[entry.id] = entry
        
        return entry.id
