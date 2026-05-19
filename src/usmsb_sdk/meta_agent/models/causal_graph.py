"""
因果图数据模型

v2.1 因果学习系统的核心数据结构
用于表示因果关系结构

包含：
- CausalEdge: 因果边
- CausalGraph: 因果图
- CausalPattern: 因果模式（可跨任务迁移）
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CausalEdge:
    """
    因果边

    表示从 source（因）到 target（果）的因果关系
    """
    edge_id: str
    source: str  # 因
    target: str  # 果
    strength: float = 0.0  # 因果效应大小 (-1.0 ~ 1.0)
    confidence: float = 0.0  # 置信度 (0.0 ~ 1.0)
    conditions: list[str] = field(default_factory=list)  # 适用条件
    evidence: list[str] = field(default_factory=list)  # 支持证据（task_id 列表）
    is_directed: bool = True  # 是否已定向

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "edge_id": self.edge_id,
            "source": self.source,
            "target": self.target,
            "strength": self.strength,
            "confidence": self.confidence,
            "conditions": self.conditions,
            "evidence": self.evidence,
            "is_directed": self.is_directed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CausalEdge":
        """从字典创建"""
        return cls(
            edge_id=data["edge_id"],
            source=data["source"],
            target=data["target"],
            strength=data.get("strength", 0.0),
            confidence=data.get("confidence", 0.0),
            conditions=data.get("conditions", []),
            evidence=data.get("evidence", []),
            is_directed=data.get("is_directed", True),
        )


@dataclass
class CausalGraph:
    """
    因果图

    表示变量之间的因果关系结构
    """
    graph_id: str
    nodes: set[str] = field(default_factory=set)
    edges: list[CausalEdge] = field(default_factory=list)
    undirected_edges: set[tuple[str, str]] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=datetime.now().timestamp)
    updated_at: float = field(default_factory=datetime.now().timestamp)

    def add_edge(self, edge: CausalEdge) -> None:
        """添加因果边"""
        self.edges.append(edge)
        self.nodes.add(edge.source)
        self.nodes.add(edge.target)
        self.updated_at = datetime.now().timestamp()

    def add_undirected_edge(self, source: str, target: str) -> None:
        """添加未定向边"""
        self.undirected_edges.add((source, target))
        self.nodes.add(source)
        self.nodes.add(target)
        self.updated_at = datetime.now().timestamp()

    def get_parents(self, node: str) -> list[str]:
        """获取节点的直接因（父节点）"""
        return [e.source for e in self.edges if e.target == node]

    def get_children(self, node: str) -> list[str]:
        """获取节点的直接果（子节点）"""
        return [e.target for e in self.edges if e.source == node]

    def get_descendants(self, node: str) -> set[str]:
        """获取节点的所有后裔（递归）"""
        children = self.get_children(node)
        descendants = set(children)
        for child in children:
            descendants |= self.get_descendants(child)
        return descendants

    def get_ancestors(self, node: str) -> set[str]:
        """获取节点的所有祖先（递归）"""
        parents = self.get_parents(node)
        ancestors = set(parents)
        for parent in parents:
            ancestors |= self.get_ancestors(parent)
        return ancestors

    def find_path(self, source: str, target: str) -> list[str] | None:
        """在因果图中查找从 source 到 target 的路径"""
        from collections import deque

        queue = deque([(source, [source])])
        visited = {source}

        while queue:
            current, path = queue.popleft()

            if current == target:
                return path

            for child in self.get_children(current):
                if child not in visited:
                    visited.add(child)
                    queue.append((child, path + [child]))

        return None

    def has_edge(self, source: str, target: str) -> bool:
        """检查是否存在从 source 到 target 的边"""
        return any(e.source == source and e.target == target for e in self.edges)

    def has_undirected_edge(self, node1: str, node2: str) -> bool:
        """检查是否存在两个节点之间的未定向边"""
        return (node1, node2) in self.undirected_edges or (node2, node1) in self.undirected_edges

    def get_edge(self, source: str, target: str) -> CausalEdge | None:
        """获取指定边"""
        for e in self.edges:
            if e.source == source and e.target == target:
                return e
        return None

    def remove_edge(self, source: str, target: str) -> bool:
        """移除指定边"""
        for i, e in enumerate(self.edges):
            if e.source == source and e.target == target:
                self.edges.pop(i)
                self.updated_at = datetime.now().timestamp()
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "graph_id": self.graph_id,
            "nodes": list(self.nodes),
            "edges": [e.to_dict() for e in self.edges],
            "undirected_edges": [list(e) for e in self.undirected_edges],
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CausalGraph":
        """从字典创建"""
        graph = cls(
            graph_id=data["graph_id"],
            nodes=set(data.get("nodes", [])),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now().timestamp()),
            updated_at=data.get("updated_at", datetime.now().timestamp()),
        )
        for edge_data in data.get("edges", []):
            graph.add_edge(CausalEdge.from_dict(edge_data))
        for edge_data in data.get("undirected_edges", []):
            graph.add_undirected_edge(edge_data[0], edge_data[1])
        return graph


@dataclass
class CausalPattern:
    """
    因果模式（可跨任务迁移）

    表示一个抽象的因果结构，可应用于多个领域
    """
    pattern_id: str
    description: str
    abstract_structure: dict[str, Any]  # 抽象因果结构
    applicable_domains: list[str]  # 适用领域列表
    success_conditions: list[str]  # 成功条件
    failure_modes: list[str]  # 失败模式
    usage_count: int = 0
    success_rate: float = 0.0
    created_at: float = field(default_factory=datetime.now().timestamp)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "pattern_id": self.pattern_id,
            "description": self.description,
            "abstract_structure": self.abstract_structure,
            "applicable_domains": self.applicable_domains,
            "success_conditions": self.success_conditions,
            "failure_modes": self.failure_modes,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CausalPattern":
        """从字典创建"""
        return cls(
            pattern_id=data["pattern_id"],
            description=data["description"],
            abstract_structure=data["abstract_structure"],
            applicable_domains=data.get("applicable_domains", []),
            success_conditions=data.get("success_conditions", []),
            failure_modes=data.get("failure_modes", []),
            usage_count=data.get("usage_count", 0),
            success_rate=data.get("success_rate", 0.0),
            created_at=data.get("created_at", datetime.now().timestamp()),
        )
