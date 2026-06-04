"""
向量知识库 - 基于 SQLite 的本地向量存储和检索

使用轻量级方案：
- SQLite 存储向量和元数据
- 支持三种 Embedding Provider（见 EMBEDDING_PROVIDER 环境变量）：
    1. minimax - MiniMax Embedding API（付费）
    2. sentence_transformers - Sentence Transformers 本地模型（免费，需预下载或网络访问）
    3. local_hash - Local Hash 伪向量（默认，无语义理解）
- 余弦相似度进行检索

不依赖大型数据库或分布式存储
"""

import asyncio
import hashlib
import json
import logging
import math
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeItem:
    """知识条目"""

    id: str
    content: str
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"
    category: str = "general"
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    access_count: int = 0
    relevance_score: float = 0.0


@dataclass
class SearchResult:
    """搜索结果"""

    item: KnowledgeItem
    score: float
    distance: float

    @property
    def id(self) -> str:
        return self.item.id

    @property
    def content(self) -> str:
        return self.item.content

    @property
    def metadata(self) -> dict[str, Any]:
        return self.item.metadata

    @property
    def source(self) -> str:
        return self.item.source

    @property
    def category(self) -> str:
        return self.item.category

    @property
    def timestamp(self) -> float:
        return self.item.created_at

    @property
    def importance(self) -> float:
        return self.item.relevance_score or self.score or 0.5

    @property
    def user_emphasized(self) -> bool:
        return bool(self.item.metadata.get("user_emphasized", False))

    @property
    def success(self) -> bool | None:
        return self.item.metadata.get("success")


def _get_embedding_provider() -> str:
    """从环境变量读取 embedding provider，默认 local_hash"""
    return os.getenv("EMBEDDING_PROVIDER", "local_hash").lower()


def _get_st_model_path() -> str | None:
    """获取 SentenceTransformer 模型本地路径"""
    return os.getenv("SENTENCE_TRANSFORMERS_MODEL_PATH")


class LocalEmbeddingService:
    """
    本地向量嵌入服务

    支持三种嵌入方式（通过 EMBEDDING_PROVIDER 环境变量切换）：
    1. minimax - MiniMax Embedding API（付费）
    2. sentence_transformers - Sentence Transformers 本地模型（免费）
       - 如设置 SENTENCE_TRANSFORMERS_MODEL_PATH，从本地路径加载
       - 否则从 HuggingFace 下载（需要网络访问）
    3. local_hash - 本地 hash 向量（默认，无语义理解）
    """

    _st_model = None  # 类级别缓存 SentenceTransformer 实例

    def __init__(self, llm_manager=None, vector_dim: int = 384):
        self.llm_manager = llm_manager
        self.vector_dim = vector_dim
        self._provider = _get_embedding_provider()
        self._use_api = (
            self._provider == "minimax"
            and llm_manager is not None
            and hasattr(llm_manager, "_adapter")
        )

    @classmethod
    def _get_st_model(cls):
        """获取或初始化 SentenceTransformer 模型（类级别单例）

        优先从 SENTENCE_TRANSFORMERS_MODEL_PATH 加载本地模型，
        否则从 HuggingFace 下载（需要网络访问）。
        建议预下载模型到本地目录，避免生产环境依赖网络。
        """
        if cls._st_model is None:
            try:
                from sentence_transformers import SentenceTransformer

                local_path = _get_st_model_path()
                # 设置 HF_HUB_OFFLINE=1 避免已缓存模型仍尝试联网校验
                os.environ.setdefault("HF_HUB_OFFLINE", "1")

                if local_path:
                    # 从本地路径加载预下载的模型
                    cls._st_model = SentenceTransformer(local_path, device="cpu")
                    logger.info(f"SentenceTransformer model loaded from local path: {local_path}")
                else:
                    # 从 HuggingFace 下载（需要网络访问）
                    cls._st_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
                    logger.info("SentenceTransformer model loaded: all-MiniLM-L6-v2 (downloaded)")
            except ImportError:
                raise ImportError(
                    "sentence-transformers not installed. "
                    "Run: pip install sentence-transformers"
                )
        return cls._st_model

    async def embed(self, text: str) -> list[float]:
        """生成文本向量"""
        if self._provider == "sentence_transformers":
            return await self._embed_with_st(text)
        elif self._provider == "local_hash":
            return self._embed_local(text)
        elif self._use_api:
            try:
                return await self._embed_with_api(text)
            except Exception as e:
                logger.warning(f"MiniMax API embedding failed, fallback to local_hash: {e}")
                return self._embed_local(text)
        else:
            # 没有 API 且非 sentence_transformers，走 local_hash
            return self._embed_local(text)

    async def _embed_with_api(self, text: str) -> list[float]:
        """使用 MiniMax API 生成向量"""
        if self.llm_manager and hasattr(self.llm_manager, "_adapter"):
            adapter = self.llm_manager._adapter
            if hasattr(adapter, "embed"):
                return await adapter.embed(text)

        raise ValueError("MiniMax embedding API not available")

    async def _embed_with_st(self, text: str) -> list[float]:
        """使用 Sentence Transformers 本地模型生成向量"""
        model = self._get_st_model()
        loop = asyncio.get_event_loop()
        # encode 是同步的，放在 executor 里避免阻塞事件循环
        embedding = await loop.run_in_executor(
            None, lambda: model.encode(text).tolist()
        )
        return embedding

    def _embed_local(self, text: str) -> list[float]:
        """
        本地生成简单向量（降级方案）
        基于 hash 和文本特征，无语义理解能力
        """
        vector = [0.0] * self.vector_dim

        text_lower = text.lower()
        text_hash = hashlib.md5(text.encode()).hexdigest()

        for i, char in enumerate(text_hash[: self.vector_dim // 4]):
            idx = int(char, 16) * 4
            if idx < self.vector_dim:
                vector[idx] = (ord(text_lower[i % len(text_lower)]) % 100) / 100.0

        for i, word in enumerate(text_lower.split()[:50]):
            word_hash = sum(ord(c) for c in word)
            idx = word_hash % self.vector_dim
            vector[idx] = min(1.0, vector[idx] + 0.1)

        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量生成向量"""
        return [await self.embed(text) for text in texts]


class VectorKnowledgeBase:
    """
    向量知识库

    基于 SQLite 实现本地向量存储和检索
    支持：
    - 文档向量化存储
    - 语义相似度搜索
    - 知识分类管理
    - 访问统计和热度排序
    """

    def __init__(
        self,
        db_path: str = "knowledge_base.db",
        llm_manager=None,
        vector_dim: int = 384,
    ):
        self.db_path = db_path
        self.embedding_service = LocalEmbeddingService(llm_manager, vector_dim)
        self.vector_dim = vector_dim
        self._initialized = False

    async def init(self):
        """初始化数据库"""
        if self._initialized:
            return

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._init_db)
        self._initialized = True
        logger.info(f"Vector Knowledge Base initialized: {self.db_path}")

    def _init_db(self):
        """初始化数据库表"""
        os.makedirs(
            os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                embedding BLOB,
                metadata TEXT,
                source TEXT DEFAULT 'unknown',
                category TEXT DEFAULT 'general',
                created_at REAL,
                updated_at REAL,
                access_count INTEGER DEFAULT 0,
                relevance_score REAL DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_graph (
                id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                source TEXT,
                created_at REAL,
                metadata TEXT
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_source ON knowledge(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_subject ON knowledge_graph(subject)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_object ON knowledge_graph(object)")

        conn.commit()
        conn.close()

    async def add_knowledge(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        source: str = "unknown",
        category: str = "general",
    ) -> str:
        """添加知识"""
        await self.init()

        import uuid

        knowledge_id = str(uuid.uuid4())[:8]

        embedding = await self.embedding_service.embed(content)

        item = KnowledgeItem(
            id=knowledge_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
            source=source,
            category=category,
        )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._insert_knowledge, item)

        logger.info(f"Added knowledge: {knowledge_id} (category: {category})")
        return knowledge_id

    def _insert_knowledge(self, item: KnowledgeItem):
        """插入知识"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        embedding_blob = json.dumps(item.embedding) if item.embedding else None

        cursor.execute(
            """
            INSERT OR REPLACE INTO knowledge
            (id, content, embedding, metadata, source, category, created_at, updated_at, access_count, relevance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                item.id,
                item.content,
                embedding_blob,
                json.dumps(item.metadata),
                item.source,
                item.category,
                item.created_at,
                item.updated_at,
                item.access_count,
                item.relevance_score,
            ),
        )

        conn.commit()
        conn.close()

    async def search(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """语义搜索"""
        await self.init()

        query_embedding = await self.embedding_service.embed(query)

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            self._search_vectors,
            query_embedding,
            top_k,
            category,
            min_score,
        )

        for result in results:
            await self._increment_access_count(result.item.id)

        return results

    async def search_knowledge_base(
        self,
        query: str,
        top_k: int = 10,
        category: str | None = None,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Compatibility wrapper used by IntelligentRecall."""
        return await self.search(
            query=query,
            top_k=top_k,
            category=category,
            min_score=min_score,
        )

    async def search_in_document(
        self,
        document_id: str,
        query: str,
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """Search within one document by matching common document metadata keys."""
        candidates = await self.search(
            query=query,
            top_k=max(top_k * 3, top_k),
            min_score=min_score,
        )
        if not document_id:
            return candidates[:top_k]

        filtered = []
        for result in candidates:
            metadata = result.metadata or {}
            if (
                metadata.get("document_id") == document_id
                or metadata.get("doc_id") == document_id
                or metadata.get("id") == document_id
                or result.source == document_id
            ):
                filtered.append(result)
        return filtered[:top_k]

    def _search_vectors(
        self,
        query_embedding: list[float],
        top_k: int,
        category: str | None,
        min_score: float,
    ) -> list[SearchResult]:
        """向量搜索"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if category:
            cursor.execute(
                "SELECT id, content, embedding, metadata, source, category, created_at, updated_at, access_count, relevance_score FROM knowledge WHERE category = ?",
                (category,),
            )
        else:
            cursor.execute(
                "SELECT id, content, embedding, metadata, source, category, created_at, updated_at, access_count, relevance_score FROM knowledge"
            )

        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            embedding = json.loads(row[2]) if row[2] else None
            if not embedding:
                continue

            score = self._cosine_similarity(query_embedding, embedding)
            distance = 1.0 - score

            if score >= min_score:
                item = KnowledgeItem(
                    id=row[0],
                    content=row[1],
                    embedding=embedding,
                    metadata=json.loads(row[3]) if row[3] else {},
                    source=row[4],
                    category=row[5],
                    created_at=row[6],
                    updated_at=row[7],
                    access_count=row[8],
                    relevance_score=row[9],
                )
                results.append(SearchResult(item=item, score=score, distance=distance))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def _increment_access_count(self, knowledge_id: str):
        """增加访问计数"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._update_access_count, knowledge_id)

    def _update_access_count(self, knowledge_id: str):
        """更新访问计数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE knowledge SET access_count = access_count + 1 WHERE id = ?", (knowledge_id,)
        )
        conn.commit()
        conn.close()

    async def add_knowledge_batch(
        self,
        items: list[dict[str, Any]],
    ) -> list[str]:
        """批量添加知识"""
        ids = []
        for item in items:
            kid = await self.add_knowledge(
                content=item.get("content", ""),
                metadata=item.get("metadata"),
                source=item.get("source", "batch"),
                category=item.get("category", "general"),
            )
            ids.append(kid)
        return ids

    async def get_by_category(self, category: str, limit: int = 100) -> list[KnowledgeItem]:
        """按类别获取知识"""
        await self.init()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._query_by_category,
            category,
            limit,
        )

    def _query_by_category(self, category: str, limit: int) -> list[KnowledgeItem]:
        """查询类别知识"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, content, embedding, metadata, source, category, created_at, updated_at, access_count, relevance_score FROM knowledge WHERE category = ? ORDER BY access_count DESC LIMIT ?",
            (category, limit),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            KnowledgeItem(
                id=row[0],
                content=row[1],
                embedding=json.loads(row[2]) if row[2] else None,
                metadata=json.loads(row[3]) if row[3] else {},
                source=row[4],
                category=row[5],
                created_at=row[6],
                updated_at=row[7],
                access_count=row[8],
                relevance_score=row[9],
            )
            for row in rows
        ]

    async def add_triple(
        self,
        subject: str,
        predicate: str,
        object: str,
        confidence: float = 1.0,
        source: str | None = None,
        metadata: dict | None = None,
    ) -> str:
        """添加知识图谱三元组"""
        await self.init()

        import uuid

        triple_id = str(uuid.uuid4())[:8]

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._insert_triple,
            triple_id,
            subject,
            predicate,
            object,
            confidence,
            source,
            metadata,
        )

        return triple_id

    def _insert_triple(
        self,
        triple_id: str,
        subject: str,
        predicate: str,
        object: str,
        confidence: float,
        source: str | None,
        metadata: dict | None,
    ):
        """插入三元组"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO knowledge_graph
            (id, subject, predicate, object, confidence, source, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                triple_id,
                subject,
                predicate,
                object,
                confidence,
                source,
                datetime.now().timestamp(),
                json.dumps(metadata) if metadata else None,
            ),
        )

        conn.commit()
        conn.close()

    async def query_graph(
        self,
        subject: str | None = None,
        predicate: str | None = None,
        object: str | None = None,
    ) -> list[dict[str, Any]]:
        """查询知识图谱"""
        await self.init()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._query_triples,
            subject,
            predicate,
            object,
        )

    def _query_triples(
        self,
        subject: str | None,
        predicate: str | None,
        object: str | None,
    ) -> list[dict[str, Any]]:
        """查询三元组"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT id, subject, predicate, object, confidence, source, created_at, metadata FROM knowledge_graph WHERE 1=1"
        params = []

        if subject:
            query += " AND subject = ?"
            params.append(subject)
        if predicate:
            query += " AND predicate = ?"
            params.append(predicate)
        if object:
            query += " AND object = ?"
            params.append(object)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row[0],
                "subject": row[1],
                "predicate": row[2],
                "object": row[3],
                "confidence": row[4],
                "source": row[5],
                "created_at": row[6],
                "metadata": json.loads(row[7]) if row[7] else {},
            }
            for row in rows
        ]

    async def get_stats(self) -> dict[str, Any]:
        """获取知识库统计"""
        await self.init()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_stats)

    def _get_stats(self) -> dict[str, Any]:
        """获取统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM knowledge")
        knowledge_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM knowledge_graph")
        graph_count = cursor.fetchone()[0]

        cursor.execute("SELECT category, COUNT(*) FROM knowledge GROUP BY category")
        categories = dict(cursor.fetchall())

        conn.close()

        return {
            "knowledge_count": knowledge_count,
            "graph_triples_count": graph_count,
            "categories": categories,
        }
