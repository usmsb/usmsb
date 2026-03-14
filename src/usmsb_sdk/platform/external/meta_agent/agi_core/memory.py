"""
AGI 多层记忆系统
基于认知科学的永不遗忘记忆架构

记忆层次：
- 工作记忆 (Working Memory): 7±2项，秒级
- 情景记忆 (Episodic Memory): 个人经历，小时-天
- 语义记忆 (Semantic Memory): 事实概念，长期
- 程序记忆 (Procedural Memory): 技能习惯，永久
- 永久记忆 (Permanent Memory): 关键信息，永不丢失
"""

import asyncio
import hashlib
import json
import logging
import math
import os
import sqlite3
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class MemoryLayer(StrEnum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    PERMANENT = "permanent"


class ConsolidationStatus(StrEnum):
    ENCODED = "encoded"
    CONSOLIDATING = "consolidating"
    CONSOLIDATED = "consolidated"
    PERMANENT = "permanent"


@dataclass
class MemoryItem:
    id: str
    content: str
    layer: MemoryLayer = MemoryLayer.EPISODIC
    importance: float = 0.5
    emotional_intensity: float = 0.0
    access_count: int = 0
    last_accessed: float = field(default_factory=lambda: datetime.now().timestamp())
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    consolidation: ConsolidationStatus = ConsolidationStatus.ENCODED
    forgetting_strength: float = 1.0
    next_review: float = field(default_factory=lambda: datetime.now().timestamp())
    review_interval: int = 1
    keywords: list[str] = field(default_factory=list)
    associations: set[str] = field(default_factory=set)
    context: dict[str, Any] = field(default_factory=dict)
    usmsb_element: str | None = None
    user_id: str = ""
    embedding_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "layer": self.layer.value,
            "importance": self.importance,
            "emotional_intensity": self.emotional_intensity,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "created_at": self.created_at,
            "consolidation": self.consolidation.value,
            "forgetting_strength": self.forgetting_strength,
            "keywords": self.keywords,
            "associations": list(self.associations),
            "usmsb_element": self.usmsb_element,
            "user_id": self.user_id,
        }


@dataclass
class MemoryConfig:
    working_capacity: int = 7
    max_episodic: int = 2000
    max_semantic: int = 10000
    permanent_threshold: float = 0.85
    consolidation_threshold: float = 0.6
    emotional_weight: float = 0.25
    frequency_weight: float = 0.25
    recency_weight: float = 0.2
    utility_weight: float = 0.3
    forgetting_rate: float = 0.25
    enable_auto_consolidation: bool = True
    consolidation_interval: int = 300


class ImportanceEvaluator:
    _CRITICAL_PATTERNS = ["必须", "重要", "关键", "紧急", "核心", "致命", "严重", "记住", "别忘了"]
    _EMOTIONAL_PATTERNS = [
        "喜欢",
        "讨厌",
        "爱",
        "恨",
        "害怕",
        "担心",
        "希望",
        "遗憾",
        "开心",
        "伤心",
    ]
    _COMMITMENT_PATTERNS = ["承诺", "答应", "决定", "约定", "保证", "一定", "务必"]
    _PREFERENCE_PATTERNS = ["偏好", "总是", "从不", "习惯", "通常", "倾向"]

    def __init__(self, config: MemoryConfig):
        self.config = config

    def evaluate(
        self, content: str, context: dict[str, Any] | None = None
    ) -> tuple[float, float, list[str]]:
        frequency_score = self._eval_frequency(content)
        emotional_score = self._eval_emotional(content)
        utility_score = self._eval_utility(content, context)
        recency_score = 0.5

        importance = (
            frequency_score * self.config.frequency_weight
            + emotional_score * self.config.emotional_weight
            + utility_score * self.config.utility_weight
            + recency_score * self.config.recency_weight
        )

        keywords = self._extract_keywords(content)
        return min(1.0, importance), emotional_score, keywords

    def _eval_frequency(self, content: str) -> float:
        return min(1.0, len(set(content.split())) / 50)

    def _eval_emotional(self, content: str) -> float:
        score = 0.0
        for pattern in self._CRITICAL_PATTERNS:
            if pattern in content:
                score += 0.25
        for pattern in self._EMOTIONAL_PATTERNS:
            if pattern in content:
                score += 0.2
        for pattern in self._COMMITMENT_PATTERNS:
            if pattern in content:
                score += 0.2
        for pattern in self._PREFERENCE_PATTERNS:
            if pattern in content:
                score += 0.15
        return min(1.0, score)

    def _eval_utility(self, content: str, context: dict[str, Any] | None) -> float:
        score = 0.5
        if context:
            if context.get("is_question"):
                score += 0.2
            if context.get("involves_decision"):
                score += 0.3
            if context.get("user_emphasis"):
                score += 0.2
        return min(1.0, score)

    def _extract_keywords(self, content: str) -> list[str]:
        keywords = []
        all_patterns = (
            self._CRITICAL_PATTERNS
            + self._EMOTIONAL_PATTERNS
            + self._COMMITMENT_PATTERNS
            + self._PREFERENCE_PATTERNS
        )
        for pattern in all_patterns:
            if pattern in content and pattern not in keywords:
                keywords.append(pattern)
        return keywords[:10]


class ForgettingCurve:
    def __init__(self, rate: float = 0.25):
        self.rate = rate
        self._intervals = [1, 3, 7, 14, 30, 60, 120, 365]

    def retention(self, hours: float, reviews: int) -> float:
        adjusted = self.rate / (1 + 0.1 * reviews)
        return math.exp(-adjusted * hours)

    def next_review(self, reviews: int, strength: float) -> float:
        idx = min(reviews, len(self._intervals) - 1)
        days = self._intervals[idx] * strength
        return datetime.now().timestamp() + days * 86400

    def update_strength(self, current: float, success: bool) -> float:
        if success:
            return min(1.0, current * 1.2 + 0.1)
        return max(0.1, current * 0.8)


class AGIMemorySystem:
    """
    AGI多层记忆系统
    实现永不遗忘的智能记忆管理
    """

    def __init__(
        self,
        db_path: str = "agi_memory.db",
        config: MemoryConfig | None = None,
        llm_manager=None,
    ):
        self.db_path = db_path
        self.config = config or MemoryConfig()
        self.llm_manager = llm_manager
        self._initialized = False

        self.evaluator = ImportanceEvaluator(self.config)
        self.forgetting = ForgettingCurve(self.config.forgetting_rate)

        self._working: list[MemoryItem] = []
        self._cache: dict[str, MemoryItem] = {}
        self._associations: dict[str, set[str]] = defaultdict(set)
        self._lock = threading.RLock()
        self._consolidation_task: asyncio.Task | None = None

    async def init(self):
        if self._initialized:
            return

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._init_db)
        await loop.run_in_executor(None, self._load_cache)

        if self.config.enable_auto_consolidation:
            self._consolidation_task = asyncio.create_task(self._consolidation_loop())

        self._initialized = True
        logger.info(f"AGI Memory System initialized: {self.db_path}")

    def _init_db(self):
        os.makedirs(
            os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                layer TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                emotional_intensity REAL DEFAULT 0.0,
                access_count INTEGER DEFAULT 0,
                last_accessed REAL,
                created_at REAL,
                consolidation TEXT,
                forgetting_strength REAL DEFAULT 1.0,
                next_review REAL,
                review_interval INTEGER DEFAULT 1,
                keywords TEXT,
                associations TEXT,
                context TEXT,
                usmsb_element TEXT,
                user_id TEXT,
                embedding_hash TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS associations (
                source_id TEXT,
                target_id TEXT,
                strength REAL DEFAULT 0.5,
                created_at REAL,
                PRIMARY KEY (source_id, target_id)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_layer ON memories(layer)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user ON memories(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_review ON memories(next_review)")

        conn.commit()
        conn.close()

    def _load_cache(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM memories WHERE layer = ?", (MemoryLayer.PERMANENT.value,))
        for row in cursor.fetchall():
            mem = self._row_to_memory(row)
            self._cache[mem.id] = mem

        cursor.execute("SELECT * FROM associations")
        for row in cursor.fetchall():
            self._associations[row[0]].add(row[1])

        conn.close()

    def _row_to_memory(self, row: tuple) -> MemoryItem:
        return MemoryItem(
            id=row[0],
            content=row[1],
            layer=MemoryLayer(row[2]),
            importance=row[3],
            emotional_intensity=row[4],
            access_count=row[5],
            last_accessed=row[6],
            created_at=row[7],
            consolidation=ConsolidationStatus(row[8]),
            forgetting_strength=row[9],
            next_review=row[10],
            review_interval=row[11],
            keywords=json.loads(row[12]) if row[12] else [],
            associations=set(json.loads(row[13])) if row[13] else set(),
            context=json.loads(row[14]) if row[14] else {},
            usmsb_element=row[15],
            user_id=row[16] or "",
            embedding_hash=row[17] or "",
        )

    async def memorize(
        self,
        content: str,
        user_id: str = "",
        layer: MemoryLayer = MemoryLayer.EPISODIC,
        context: dict[str, Any] | None = None,
        usmsb_element: str | None = None,
    ) -> MemoryItem:
        """记忆内容，自动评估重要性并分配到合适层级"""
        await self.init()

        importance, emotional, keywords = self.evaluator.evaluate(content, context)

        if importance >= self.config.permanent_threshold:
            layer = MemoryLayer.PERMANENT

        memory = MemoryItem(
            id=self._gen_id(content),
            content=content,
            layer=layer,
            importance=importance,
            emotional_intensity=emotional,
            keywords=keywords,
            context=context or {},
            usmsb_element=usmsb_element,
            user_id=user_id,
            embedding_hash=self._hash_content(content),
        )

        if memory.layer == MemoryLayer.PERMANENT:
            memory.consolidation = ConsolidationStatus.PERMANENT
            memory.forgetting_strength = 1.0

        await self._store(memory)
        await self._update_associations(memory)

        with self._lock:
            if len(self._working) >= self.config.working_capacity:
                oldest = self._working.pop(0)
                if oldest.importance >= self.config.consolidation_threshold:
                    asyncio.create_task(self._promote(oldest))
            self._working.append(memory)

        return memory

    async def recall(
        self,
        query: str,
        user_id: str = "",
        top_k: int = 10,
        layers: list[MemoryLayer] | None = None,
    ) -> list[tuple[MemoryItem, float]]:
        """智能召回相关记忆"""
        await self.init()

        memories = await self._get_relevant(user_id)
        if layers:
            memories = [m for m in memories if m.layer in layers]

        query_words = set(query.lower().split())
        scored = []

        for mem in memories:
            score = self._calc_relevance(query, query_words, mem)
            if score > 0.1:
                scored.append((mem, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        for mem, _ in scored[:top_k]:
            mem.access_count += 1
            mem.last_accessed = datetime.now().timestamp()
            await self._update_access(mem)

        return scored[:top_k]

    async def get_permanent(self, user_id: str = "") -> list[MemoryItem]:
        """获取永久记忆"""
        await self.init()
        with self._lock:
            return [
                m
                for m in self._cache.values()
                if m.layer == MemoryLayer.PERMANENT and (not user_id or m.user_id == user_id)
            ]

    async def build_context_prompt(self, query: str, user_id: str = "") -> str:
        """构建上下文提示词"""
        relevant = await self.recall(query, user_id, top_k=7)

        parts = ["## 相关记忆"]

        permanent = [m for m, _ in relevant if m.layer == MemoryLayer.PERMANENT]
        if permanent:
            parts.append("\n### 永久记忆（永不遗忘）")
            for m in permanent[:3]:
                parts.append(f"- {m.content[:200]}")

        semantic = [m for m, _ in relevant if m.layer == MemoryLayer.SEMANTIC]
        if semantic:
            parts.append("\n### 已巩固知识")
            for m in semantic[:2]:
                parts.append(f"- {m.content[:150]}")

        episodic = [m for m, _ in relevant if m.layer == MemoryLayer.EPISODIC]
        if episodic:
            parts.append("\n### 相关经历")
            for m in episodic[:2]:
                parts.append(f"- {m.content[:150]}")

        return "\n".join(parts) if len(parts) > 1 else ""

    def _calc_relevance(self, query: str, query_words: set[str], mem: MemoryItem) -> float:
        content_words = set(mem.content.lower().split())
        overlap = len(query_words & content_words) / max(len(query_words), 1)

        keyword_score = (
            len(set(mem.keywords) & query_words) / max(len(mem.keywords), 1) if mem.keywords else 0
        )

        recency = math.exp(-(datetime.now().timestamp() - mem.last_accessed) / 604800)

        score = (
            0.4 * overlap + 0.3 * keyword_score + 0.2 * mem.importance + 0.1 * recency
        ) * mem.forgetting_strength

        return min(1.0, score)

    async def _store(self, memory: MemoryItem):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._insert_db, memory)
        with self._lock:
            self._cache[memory.id] = memory

    def _insert_db(self, memory: MemoryItem):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO memories
            (id, content, layer, importance, emotional_intensity, access_count,
             last_accessed, created_at, consolidation, forgetting_strength,
             next_review, review_interval, keywords, associations, context,
             usmsb_element, user_id, embedding_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                memory.id,
                memory.content,
                memory.layer.value,
                memory.importance,
                memory.emotional_intensity,
                memory.access_count,
                memory.last_accessed,
                memory.created_at,
                memory.consolidation.value,
                memory.forgetting_strength,
                memory.next_review,
                memory.review_interval,
                json.dumps(memory.keywords),
                json.dumps(list(memory.associations)),
                json.dumps(memory.context),
                memory.usmsb_element,
                memory.user_id,
                memory.embedding_hash,
            ),
        )
        conn.commit()
        conn.close()

    async def _update_associations(self, memory: MemoryItem):
        for existing in list(self._cache.values())[:100]:
            if existing.id == memory.id:
                continue
            overlap = self._assoc_strength(memory, existing)
            if overlap > 0.3:
                memory.associations.add(existing.id)
                existing.associations.add(memory.id)

    def _assoc_strength(self, m1: MemoryItem, m2: MemoryItem) -> float:
        k1, k2 = set(m1.keywords), set(m2.keywords)
        if not k1 or not k2:
            return 0.0
        return len(k1 & k2) / max(len(k1), len(k2))

    async def _update_access(self, memory: MemoryItem):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._update_access_db, memory)

    def _update_access_db(self, memory: MemoryItem):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE memories SET access_count = ?, last_accessed = ?,
            importance = MIN(1.0, importance + 0.03)
            WHERE id = ?
        """,
            (memory.access_count, memory.last_accessed, memory.id),
        )
        conn.commit()
        conn.close()

    async def _get_relevant(self, user_id: str) -> list[MemoryItem]:
        with self._lock:
            memories = list(self._working)
            memories.extend(
                [m for m in self._cache.values() if not user_id or m.user_id == user_id]
            )
        return memories

    async def _promote(self, memory: MemoryItem):
        """升级记忆层级"""
        if memory.layer == MemoryLayer.PERMANENT:
            return

        promotions = {
            MemoryLayer.WORKING: MemoryLayer.EPISODIC,
            MemoryLayer.EPISODIC: MemoryLayer.SEMANTIC,
            MemoryLayer.SEMANTIC: MemoryLayer.PERMANENT,
        }

        if memory.layer in promotions:
            memory.layer = promotions[memory.layer]
            memory.consolidation = ConsolidationStatus.CONSOLIDATED
            if memory.layer == MemoryLayer.PERMANENT:
                memory.consolidation = ConsolidationStatus.PERMANENT
                memory.forgetting_strength = 1.0
            await self._store(memory)
            logger.info(f"Promoted memory {memory.id} to {memory.layer.value}")

    async def _consolidation_loop(self):
        """自动巩固循环"""
        while True:
            await asyncio.sleep(self.config.consolidation_interval)
            try:
                await self._run_consolidation()
            except Exception as e:
                logger.error(f"Consolidation error: {e}")

    async def _run_consolidation(self):
        """执行记忆巩固"""
        loop = asyncio.get_event_loop()
        candidates = await loop.run_in_executor(None, self._get_consolidation_candidates)

        for mem in candidates:
            if mem.importance >= self.config.consolidation_threshold:
                await self._promote(mem)

    def _get_consolidation_candidates(self) -> list[MemoryItem]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM memories WHERE consolidation = ?
            AND layer != ? ORDER BY importance DESC LIMIT 50
        """,
            (ConsolidationStatus.ENCODED.value, MemoryLayer.PERMANENT.value),
        )
        memories = [self._row_to_memory(row) for row in cursor.fetchall()]
        conn.close()
        return memories

    def _gen_id(self, content: str) -> str:
        import uuid

        return f"mem_{hashlib.sha256(content.encode()).hexdigest()[:12]}_{uuid.uuid4().hex[:8]}"

    def _hash_content(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()[:16]

    async def close(self):
        if self._consolidation_task:
            self._consolidation_task.cancel()
        logger.info("AGI Memory System closed")
