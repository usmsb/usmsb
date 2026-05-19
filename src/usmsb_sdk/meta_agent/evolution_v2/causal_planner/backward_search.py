"""
因果逆向搜索

CausalPlanner 的组件

从目标出发，逆向搜索需要的因果边
"""

from collections import deque
from dataclasses import dataclass
from typing import Any

from ...models.causal_graph import CausalGraph, CausalEdge


@dataclass
class CausalPath:
    """因果路径"""
    nodes: list[str]
    edges: list[CausalEdge]
    cost: float = 0.0
    coverage: float = 0.0


class BackwardSearch:
    """
    因果逆向搜索引擎

    从目标出发，逆向遍历因果图
    找到所有导致目标的原因链
    """

    def __init__(self, causal_graph: CausalGraph):
        """
        初始化

        Args:
            causal_graph: 因果图
        """
        self.graph = causal_graph

    def search(
        self,
        target_nodes: list[str],
        max_depth: int = 10,
    ) -> list[CausalPath]:
        """
        逆向搜索

        从目标节点出发，搜索所有可能的因果链

        Args:
            target_nodes: 目标节点列表
            max_depth: 最大搜索深度

        Returns:
            因果路径列表
        """
        all_paths = []

        for target in target_nodes:
            paths = self._dfs_search(target, max_depth)
            all_paths.extend(paths)

        return all_paths

    def _dfs_search(
        self,
        node: str,
        max_depth: int,
        current_path: list[str] | None = None,
        current_edges: list[CausalEdge] | None = None,
    ) -> list[CausalPath]:
        """
        深度优先搜索

        Args:
            node: 当前节点
            max_depth: 剩余最大深度
            current_path: 当前路径
            current_edges: 当前边列表

        Returns:
            路径列表
        """
        if current_path is None:
            current_path = []
        if current_edges is None:
            current_edges = []

        # 添加当前节点到路径
        path = current_path + [node]

        # 达到最大深度
        if max_depth <= 0:
            return [CausalPath(nodes=path, edges=current_edges)]

        # 获取父节点（直接因）
        parent_edges = self._get_parent_edges(node)

        if not parent_edges:
            # 没有父节点，返回当前路径作为叶子
            return [CausalPath(nodes=path, edges=current_edges)]

        all_paths = []

        for edge in parent_edges:
            # 添加边到路径
            edge_path = current_edges + [edge]

            # 递归搜索父节点
            sub_paths = self._dfs_search(
                edge.source,
                max_depth - 1,
                path,
                edge_path,
            )

            all_paths.extend(sub_paths)

        return all_paths

    def _get_parent_edges(self, node: str) -> list[CausalEdge]:
        """
        获取节点的父节点边

        Args:
            node: 节点

        Returns:
            父节点边列表
        """
        parent_edges = []

        for edge in self.graph.edges:
            if edge.target == node:
                parent_edges.append(edge)

        # 也考虑未定向边
        for source, target in self.graph.undirected_edges:
            if target == node:
                # 创建一个虚拟边表示未定向关系
                parent_edges.append(CausalEdge(
                    edge_id=f"undirected_{source}_{target}",
                    source=source,
                    target=target,
                    strength=0.5,
                    confidence=0.3,
                    is_directed=False,
                ))

        return parent_edges

    def get_required_causes(
        self,
        target_nodes: list[str],
    ) -> list[CausalEdge]:
        """
        获取达到目标所需的所有因果边

        Args:
            target_nodes: 目标节点

        Returns:
            所需因果边列表
        """
        all_edges = set()

        for target in target_nodes:
            parents = self._collect_all_parents(target)
            for parent in parents:
                edge = self.graph.get_edge(parent, target)
                if edge:
                    all_edges.add(edge)

        return list(all_edges)

    def _collect_all_parents(self, node: str) -> set[str]:
        """
        递归收集所有父节点

        Args:
            node: 节点

        Returns:
            父节点集合
        """
        parents = set()

        for edge in self.graph.edges:
            if edge.target == node:
                parents.add(edge.source)
                # 递归获取父节点的父节点
                parents.update(self._collect_all_parents(edge.source))

        return parents


class GreedyBackwardSearch(BackwardSearch):
    """
    贪心逆向搜索

    优先选择高强度、高置信度的边
    """

    def _get_parent_edges(self, node: str) -> list[CausalEdge]:
        """获取父节点边，按强度排序"""
        edges = super()._get_parent_edges(node)

        # 按强度和置信度排序
        edges.sort(
            key=lambda e: abs(e.strength) * e.confidence,
            reverse=True,
        )

        return edges


class CostAwareBackwardSearch(BackwardSearch):
    """
    成本感知的逆向搜索

    考虑边的执行成本
    """

    def __init__(self, causal_graph: CausalGraph, edge_costs: dict[str, float] | None = None):
        super().__init__(causal_graph)
        self.edge_costs = edge_costs or {}

    def search(
        self,
        target_nodes: list[str],
        max_depth: int = 10,
        max_cost: float | None = None,
    ) -> list[CausalPath]:
        """
        搜索最优路径

        Args:
            target_nodes: 目标节点
            max_depth: 最大深度
            max_cost: 最大成本

        Returns:
            路径列表
        """
        all_paths = []

        for target in target_nodes:
            paths = self._dfs_search_with_cost(
                target,
                max_depth,
                max_cost or float("inf"),
            )
            all_paths.extend(paths)

        # 计算每个路径的成本和覆盖率
        for path in all_paths:
            path.cost = self._calculate_path_cost(path)
            path.coverage = self._calculate_coverage(path)

        # 按成本排序
        all_paths.sort(key=lambda p: p.cost)

        return all_paths

    def _dfs_search_with_cost(
        self,
        node: str,
        max_depth: int,
        max_cost: float,
        current_path: list[str] | None = None,
        current_edges: list[CausalEdge] | None = None,
        current_cost: float = 0.0,
    ) -> list[CausalPath]:
        """带成本的深度优先搜索"""
        if current_path is None:
            current_path = []
        if current_edges is None:
            current_edges = []

        path = current_path + [node]

        if max_depth <= 0 or current_cost > max_cost:
            return [CausalPath(nodes=path, edges=current_edges, cost=current_cost)]

        parent_edges = self._get_parent_edges(node)

        if not parent_edges:
            return [CausalPath(nodes=path, edges=current_edges, cost=current_cost)]

        all_paths = []

        for edge in parent_edges:
            edge_cost = self.edge_costs.get(edge.edge_id, 1.0)
            new_cost = current_cost + edge_cost

            if new_cost > max_cost:
                continue

            edge_path = current_edges + [edge]
            sub_paths = self._dfs_search_with_cost(
                edge.source,
                max_depth - 1,
                max_cost,
                path,
                edge_path,
                new_cost,
            )
            all_paths.extend(sub_paths)

        return all_paths

    def _calculate_path_cost(self, path: CausalPath) -> float:
        """计算路径成本"""
        return sum(
            self.edge_costs.get(e.edge_id, 1.0)
            for e in path.edges
        )

    def _calculate_coverage(self, path: CausalPath) -> float:
        """计算路径覆盖率"""
        if not self.graph.edges:
            return 0.0

        covered = len(set(e.edge_id for e in path.edges))
        total = len(self.graph.edges)

        return covered / total if total > 0 else 0.0
