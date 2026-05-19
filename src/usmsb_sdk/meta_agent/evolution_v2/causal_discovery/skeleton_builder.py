"""
骨架构建器

PC Algorithm 的核心组件

从完全图开始，通过条件独立性检验逐步删除边
构建因果图的骨架（无向图）
"""

import math
from typing import Any

import numpy as np


class SkeletonBuilder:
    """
    骨架构建器

    PC Algorithm 的骨架构建步骤：

    1. 从完全图开始（所有节点两两相连）
    2. 对每条边 (X, Y)：
       对每个大小为 k 的条件集 S：
         如果 CMI(X, Y | S) 表明条件独立：
           删除边 (X, Y)
           break
    3. k 从 0 开始，逐渐增加，直到没有边可以删除
    """

    def __init__(
        self,
        ci_tester,
        alpha: float = 0.05,
        max_condition_set_size: int = 3,
    ):
        """
        初始化

        Args:
            ci_tester: ConditionalIndependenceTest 实例
            alpha: 显著性水平
            max_condition_set_size: 最大条件集大小
        """
        self.ci_tester = ci_tester
        self.alpha = alpha
        self.max_condition_set_size = max_condition_set_size

    def build_skeleton(
        self,
        variables: list[str],
        data: dict[str, np.ndarray],
    ) -> tuple[dict[tuple[str, str], float], dict[tuple[str, str], frozenset[str]]]:
        """
        构建骨架

        Args:
            variables: 变量名列表
            data: 变量名 -> 数据数组 的字典

        Returns:
            (
                sep_sets,  # separator sets: (X, Y) -> Z (使得 X ⊥ Y | Z)
                edge_weights  # 边的权重（CMI 值）
            )

            未删除的边表示存在因果/相关关系
            删除了的边表示条件独立
        """
        n = len(variables)
        sep_sets: dict[tuple[str, str], frozenset[str]] = {}

        # 初始化：完全图
        # adjacent[v] = 与 v 相邻的所有节点
        adjacent: dict[str, set[str]] = {v: set(variables) - {v} for v in variables}

        # 边的 CMI 权重
        edge_weights: dict[tuple[str, str], float] = {}

        # k 从 0 开始
        k = 0

        # 记录是否删除了边
        edge_removed = True

        while edge_removed and k <= self.max_condition_set_size:
            edge_removed = False

            # 遍历所有边
            for x in variables:
                # 获取 x 的邻居
                neighbors = list(adjacent[x])

                for y in neighbors:
                    if y not in adjacent[x]:
                        continue

                    # 获取 x 和 y 的共同邻居（排除 x 和 y 本身）
                    possible_conds = list(adjacent[x] - {y})
                    possible_conds_y = list(adjacent[y] - {x})
                    possible_conds = list(set(possible_conds) & set(possible_conds_y))

                    if len(possible_conds) < k:
                        continue

                    # 尝试所有大小为 k 的条件集
                    found_indep = False

                    for cond_set in self._combinations(possible_conds, k):
                        # 构建条件集数据
                        z_data = np.array([data[z] for z in cond_set]).T if cond_set else None

                        # 执行条件独立性检验
                        cmi, p_value = self.ci_tester.ci_test(
                            data[x], data[y], z_data, method="cmi"
                        )

                        # 记录边的权重
                        edge_key = tuple(sorted([x, y]))
                        if edge_key not in edge_weights or cmi > edge_weights[edge_key]:
                            edge_weights[edge_key] = cmi

                        # 如果条件独立，删除边
                        if p_value > self.alpha:
                            # 记录 separator set
                            sep_sets[(x, y)] = frozenset(cond_set)
                            sep_sets[(y, x)] = frozenset(cond_set)

                            # 删除边
                            adjacent[x].discard(y)
                            adjacent[y].discard(x)

                            edge_removed = True
                            found_indep = True
                            break

                    if found_indep:
                        break

            k += 1

        return sep_sets, edge_weights

    def _combinations(self, items: list[str], k: int):
        """
        生成所有大小为 k 的组合

        这是一个生成器，避免一次性生成所有组合
        """
        if k == 0:
            yield tuple()
            return

        if k >= len(items):
            yield tuple(items)
            return

        # 使用递归生成
        def _gen(i: int, current: tuple):
            if len(current) == k:
                yield current
                return

            for j in range(i, len(items)):
                yield from _gen(j + 1, current + (items[j],))

        yield from _gen(0, tuple())

    def get_skeleton_edges(
        self, variables: list[str], data: dict[str, np.ndarray]
    ) -> list[tuple[str, str]]:
        """
        获取骨架中的边

        Args:
            variables: 变量名列表
            data: 变量名 -> 数据数组 的字典

        Returns:
            边的列表 [(var1, var2), ...]
        """
        adjacent: dict[str, set[str]] = {v: set(variables) - {v} for v in variables}

        # k 从 0 开始
        k = 0
        edge_removed = True

        while edge_removed and k <= self.max_condition_set_size:
            edge_removed = False

            for x in variables:
                neighbors = list(adjacent[x])

                for y in neighbors:
                    if y not in adjacent[x]:
                        continue

                    possible_conds = list(adjacent[x] - {y})
                    possible_conds_y = list(adjacent[y] - {x})
                    possible_conds = list(set(possible_conds) & set(possible_conds_y))

                    if len(possible_conds) < k:
                        continue

                    found_indep = False

                    for cond_set in self._combinations(possible_conds, k):
                        z_data = np.array([data[z] for z in cond_set]).T if cond_set else None

                        _, p_value = self.ci_tester.ci_test(
                            data[x], data[y], z_data, method="cmi"
                        )

                        if p_value > self.alpha:
                            adjacent[x].discard(y)
                            adjacent[y].discard(x)
                            edge_removed = True
                            found_indep = True
                            break

                    if found_indep:
                        break

            k += 1

        # 收集所有边
        edges = set()
        for x in variables:
            for y in adjacent[x]:
                edge = tuple(sorted([x, y]))
                edges.add(edge)

        return list(edges)


class PCSkeletonBuilder(SkeletonBuilder):
    """
    PC Algorithm 骨架构建器的完整实现

    继承自 SkeletonBuilder，添加了更多功能：
    - 平行边检测
    - 边强度估计
    """

    def __init__(
        self,
        ci_tester,
        alpha: float = 0.05,
        max_condition_set_size: int = 3,
        min_edge_strength: float = 0.01,
    ):
        """
        初始化

        Args:
            ci_tester: ConditionalIndependenceTest 实例
            alpha: 显著性水平
            max_condition_set_size: 最大条件集大小
            min_edge_strength: 最小边强度阈值
        """
        super().__init__(ci_tester, alpha, max_condition_set_size)
        self.min_edge_strength = min_edge_strength

    def build_skeleton_complete(
        self,
        variables: list[str],
        data: dict[str, np.ndarray],
    ) -> dict[tuple[str, str], dict[str, Any]]:
        """
        完整骨架构建

        Args:
            variables: 变量名列表
            data: 变量名 -> 数据数组 的字典

        Returns:
            {
                (var1, var2): {
                    "separating_set": frozenset[str],
                    "cmi": float,
                    "p_value": float,
                    "is_edge": bool,
                }
            }
        """
        sep_sets, edge_weights = self.build_skeleton(variables, data)

        # 构建完整结果
        results = {}

        # 遍历所有可能的边
        for i, x in enumerate(variables):
            for y in variables[i + 1:]:
                edge_key = tuple(sorted([x, y]))

                # 计算完整的 CI 检验
                max_cmi = 0.0
                max_p_value = 0.0
                best_sep_set = None

                # 尝试所有可能大小的条件集
                neighbors_x = set(variables) - {x, y}
                neighbors_y = set(variables) - {x, y}
                common_neighbors = list(neighbors_x & neighbors_y)

                for k in range(min(3, len(common_neighbors) + 1)):
                    for cond_set in self._combinations(common_neighbors, k):
                        z_data = (
                            np.array([data[z] for z in cond_set]).T
                            if cond_set
                            else None
                        )

                        cmi, p_value = self.ci_tester.ci_test(
                            data[x], data[y], z_data, method="cmi"
                        )

                        if cmi > max_cmi:
                            max_cmi = cmi
                            max_p_value = p_value
                            best_sep_set = frozenset(cond_set) if cond_set else frozenset()

                is_edge = max_p_value <= self.alpha

                # 检查边强度
                if is_edge and max_cmi < self.min_edge_strength:
                    is_edge = False

                results[edge_key] = {
                    "separating_set": sep_sets.get(edge_key, best_sep_set),
                    "cmi": max_cmi,
                    "p_value": max_p_value,
                    "is_edge": is_edge,
                }

        return results
