"""
AGI 动态知识图谱
支持实体关系、因果链、时序演化的智能知识图谱

USMSB九大要素映射：
- Agent知识: 主体相关
- Object知识: 客体相关
- Goal知识: 目标相关
- Resource知识: 资源相关
- Rule知识: 规则相关
- Information知识: 信息相关
- Value知识: 价值相关
- Risk知识: 风险相关
- Environment知识: 环境相关
"""

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class RelationType(StrEnum):
    IS_A = "is_a"
    HAS_A = "has_a"
    CAUSES = "causes"
    CAUSED_BY = "caused_by"
    USES = "uses"
    RELATES = "relates"
    TEMPORAL_BEFORE = "before"
    TEMPORAL_AFTER = "after"
    DEPENDS = "depends"
    CONTRADICTS = "contradicts"
    USMSB_AGENT = "agent"
    USMSB_OBJECT = "object"
    USMSB_GOAL = "goal"
    USMSB_RESOURCE = "resource"
    USMSB_RULE = "rule"
    USMSB_INFO = "info"
    USMSB_VALUE = "value"
    USMSB_RISK = "risk"
    USMSB_ENV = "environment"


class KnowledgeStatus(StrEnum):
    NEW = "new"
    CONFIRMED = "confirmed"
    STRENGTHENED = "strengthened"
    WEAKENED = "weakened"
    ARCHIVED = "archived"


@dataclass
class KnowledgeNode:
    id: str
    content: str
    usmsb_element: str | None = None
    status: KnowledgeStatus = KnowledgeStatus.NEW
    confidence: float = 0.5
    importance: float = 0.5
    access_count: int = 0
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "usmsb_element": self.usmsb_element,
            "status": self.status.value,
            "confidence": self.confidence,
            "importance": self.importance,
            "access_count": self.access_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass
class KnowledgeEdge:
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType = RelationType.RELATES
    weight: float = 1.0
    confidence: float = 0.5
    evidence: list[str] = field(default_factory=list)
    temporal_start: float | None = None
    temporal_end: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalChain:
    id: str
    nodes: list[str] = field(default_factory=list)
    edges: list[str] = field(default_factory=list)
    confidence: float = 0.0
    description: str = ""


class DynamicKnowledgeGraph:
    """
    动态知识图谱
    支持USMSB九大要素的知识组织
    """

    def __init__(self, db_path: str = "knowledge_graph.db"):
        self.db_path = db_path
        self._initialized = False

        self._nodes: dict[str, KnowledgeNode] = {}
        self._edges: dict[str, KnowledgeEdge] = {}
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        self._reverse_adjacency: dict[str, set[str]] = defaultdict(set)
        self._usmsb_index: dict[str, set[str]] = defaultdict(set)
        self._entity_index: dict[str, str] = {}

    async def init(self):
        if self._initialized:
            return

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._init_db)
        await loop.run_in_executor(None, self._load_from_db)
        self._initialized = True
        logger.info(
            f"Knowledge Graph initialized: {len(self._nodes)} nodes, {len(self._edges)} edges"
        )

    def _init_db(self):
        os.makedirs(
            os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                usmsb_element TEXT,
                status TEXT,
                confidence REAL,
                importance REAL,
                access_count INTEGER,
                created_at REAL,
                updated_at REAL,
                source TEXT,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT,
                weight REAL,
                confidence REAL,
                evidence TEXT,
                temporal_start REAL,
                temporal_end REAL,
                metadata TEXT
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_node_usmsb ON nodes(usmsb_element)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edge_source ON edges(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edge_target ON edges(target_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edge_type ON edges(relation_type)")

        conn.commit()
        conn.close()

    def _load_from_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM nodes")
        for row in cursor.fetchall():
            node = KnowledgeNode(
                id=row[0],
                content=row[1],
                usmsb_element=row[2],
                status=KnowledgeStatus(row[3]) if row[3] else KnowledgeStatus.NEW,
                confidence=row[4] or 0.5,
                importance=row[5] or 0.5,
                access_count=row[6] or 0,
                created_at=row[7] or datetime.now().timestamp(),
                updated_at=row[8] or datetime.now().timestamp(),
                source=row[9],
                metadata=json.loads(row[10]) if row[10] else {},
            )
            self._nodes[node.id] = node
            self._entity_index[node.content[:50]] = node.id
            if node.usmsb_element:
                self._usmsb_index[node.usmsb_element].add(node.id)

        cursor.execute("SELECT * FROM edges")
        for row in cursor.fetchall():
            edge = KnowledgeEdge(
                id=row[0],
                source_id=row[1],
                target_id=row[2],
                relation_type=RelationType(row[3]) if row[3] else RelationType.RELATES,
                weight=row[4] or 1.0,
                confidence=row[5] or 0.5,
                evidence=json.loads(row[6]) if row[6] else [],
                temporal_start=row[7],
                temporal_end=row[8],
                metadata=json.loads(row[9]) if row[9] else {},
            )
            self._edges[edge.id] = edge
            self._adjacency[edge.source_id].add(edge.id)
            self._reverse_adjacency[edge.target_id].add(edge.id)

        conn.close()

    async def add_node(
        self,
        content: str,
        usmsb_element: str | None = None,
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeNode:
        """添加知识节点"""
        await self.init()

        node_id = self._gen_id(content)
        node = KnowledgeNode(
            id=node_id,
            content=content,
            usmsb_element=usmsb_element,
            source=source,
            metadata=metadata or {},
        )

        self._nodes[node_id] = node
        self._entity_index[content[:50]] = node_id
        if usmsb_element:
            self._usmsb_index[usmsb_element].add(node_id)

        await self._store_node(node)
        return node

    async def add_edge(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType = RelationType.RELATES,
        weight: float = 1.0,
        confidence: float = 0.5,
        evidence: list[str] | None = None,
    ) -> KnowledgeEdge:
        """添加关系边"""
        await self.init()

        edge_id = self._gen_id(f"{source_id}_{target_id}_{relation_type.value}")
        edge = KnowledgeEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            confidence=confidence,
            evidence=evidence or [],
        )

        self._edges[edge_id] = edge
        self._adjacency[source_id].add(edge_id)
        self._reverse_adjacency[target_id].add(edge_id)

        await self._store_edge(edge)
        return edge

    async def query(
        self,
        query: str,
        usmsb_elements: list[str] | None = None,
        max_depth: int = 2,
        limit: int = 20,
    ) -> list[tuple[KnowledgeNode, float]]:
        """查询相关知识"""
        await self.init()

        candidates = []
        query_words = set(query.lower().split())

        for node in self._nodes.values():
            if usmsb_elements and node.usmsb_element not in usmsb_elements:
                continue

            content_words = set(node.content.lower().split())
            overlap = len(query_words & content_words) / max(len(query_words), 1)

            if overlap > 0.1:
                score = overlap * 0.5 + node.importance * 0.3 + node.confidence * 0.2
                candidates.append((node, score))

        candidates.sort(key=lambda x: x[1], reverse=True)

        for node, _ in candidates[:limit]:
            node.access_count += 1
            node.updated_at = datetime.now().timestamp()

        return candidates[:limit]

    async def get_neighbors(
        self, node_id: str, depth: int = 1, relation_types: list[RelationType] | None = None
    ) -> list[KnowledgeNode]:
        """获取邻居节点"""
        await self.init()

        neighbors = []
        visited = set()
        queue = [(node_id, 0)]

        while queue:
            current_id, current_depth = queue.pop(0)

            if current_id in visited or current_depth > depth:
                continue

            visited.add(current_id)

            if current_id in self._nodes and current_id != node_id:
                neighbors.append(self._nodes[current_id])

            if current_depth < depth:
                for edge_id in self._adjacency.get(current_id, set()):
                    edge = self._edges.get(edge_id)
                    if edge:
                        if relation_types and edge.relation_type not in relation_types:
                            continue
                        queue.append((edge.target_id, current_depth + 1))

        return neighbors

    async def find_causal_chain(
        self, start_id: str, end_id: str, max_depth: int = 5
    ) -> CausalChain | None:
        """发现因果链"""
        await self.init()

        visited = set()
        queue = [(start_id, [start_id], [])]

        while queue:
            current_id, path, edge_path = queue.pop(0)

            if current_id == end_id:
                return CausalChain(
                    id=self._gen_id(f"chain_{start_id}_{end_id}"),
                    nodes=path,
                    edges=edge_path,
                    confidence=self._calc_chain_confidence(edge_path),
                )

            if current_id in visited or len(path) > max_depth:
                continue

            visited.add(current_id)

            for edge_id in self._adjacency.get(current_id, set()):
                edge = self._edges.get(edge_id)
                if edge and edge.relation_type in [RelationType.CAUSES, RelationType.CAUSED_BY]:
                    queue.append((edge.target_id, path + [edge.target_id], edge_path + [edge_id]))

        return None

    def _calc_chain_confidence(self, edge_ids: list[str]) -> float:
        if not edge_ids:
            return 0.0
        confidences = [self._edges[eid].confidence for eid in edge_ids if eid in self._edges]
        return sum(confidences) / len(confidences) if confidences else 0.0

    async def get_usmsb_knowledge(self, element: str) -> list[KnowledgeNode]:
        """获取特定USMSB要素的知识"""
        await self.init()
        node_ids = self._usmsb_index.get(element, set())
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    async def _store_node(self, node: KnowledgeNode):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._insert_node_db, node)

    def _insert_node_db(self, node: KnowledgeNode):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO nodes
            (id, content, usmsb_element, status, confidence, importance,
             access_count, created_at, updated_at, source, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                node.id,
                node.content,
                node.usmsb_element,
                node.status.value,
                node.confidence,
                node.importance,
                node.access_count,
                node.created_at,
                node.updated_at,
                node.source,
                json.dumps(node.metadata),
            ),
        )
        conn.commit()
        conn.close()

    async def _store_edge(self, edge: KnowledgeEdge):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._insert_edge_db, edge)

    def _insert_edge_db(self, edge: KnowledgeEdge):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO edges
            (id, source_id, target_id, relation_type, weight, confidence,
             evidence, temporal_start, temporal_end, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                edge.id,
                edge.source_id,
                edge.target_id,
                edge.relation_type.value,
                edge.weight,
                edge.confidence,
                json.dumps(edge.evidence),
                edge.temporal_start,
                edge.temporal_end,
                json.dumps(edge.metadata),
            ),
        )
        conn.commit()
        conn.close()

    def _gen_id(self, content: str) -> str:
        import uuid

        return f"kg_{hashlib.sha256(content.encode()).hexdigest()[:12]}_{uuid.uuid4().hex[:8]}"

    def get_stats(self) -> dict[str, Any]:
        return {
            "nodes": len(self._nodes),
            "edges": len(self._edges),
            "usmsb_distribution": {k: len(v) for k, v in self._usmsb_index.items()},
            "relation_distribution": self._count_relations(),
        }

    def _count_relations(self) -> dict[str, int]:
        counts = defaultdict(int)
        for edge in self._edges.values():
            counts[edge.relation_type.value] += 1
        return dict(counts)
