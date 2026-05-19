"""
边定向器

PC Algorithm 的核心组件

根据 v-结构和传散规则定向因果边
"""

from typing import Any


class EdgeOrienter:
    """
    边定向器

    PC Algorithm 的边定向步骤：

    1. v-结构识别
       如果 X-Z-Y，且 X 和 Y 不相邻，且 Z 不在 separator(X, Y) 中
       则定向为 X→Z←Y

    2. 边定向（传散规则）
       规则1：如果 X→Y，且 Y-Z 有边（未定向）
             且 X 和 Z 不相邻，则定向 Y→Z
       规则2：如果 X→Y←Z，则 X→Z

    3. 处理未定向边
       - 优先定向高置信度的边
       - 使用其他约束（如时间顺序、专家知识）
    """

    def orient_edges(
        self,
        skeleton_edges: list[tuple[str, str]],
        sep_sets: dict[tuple[str, str], frozenset[str]],
        variable_adjacency: dict[str, set[str]],
    ) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        """
        定向边

        Args:
            skeleton_edges: 骨架中的边（无向）[(var1, var2), ...]
            sep_sets: separator sets {(x, y): frozenset({z1, z2, ...}), ...}
            variable_adjacency: 每个变量的邻居集合

        Returns:
            (
                directed_edges,  # 已定向的边 [(from, to), ...]
                undirected_edges  # 仍未定向的边 [(var1, var2), ...]
            )
        """
        # 构建邻接表（用于快速查找）
        adjacency: dict[str, set[str]] = {v: set() for v in self._get_all_nodes(skeleton_edges)}

        for x, y in skeleton_edges:
            adjacency[x].add(y)
            adjacency[y].add(x)

        # 记录已定向的边方向
        # direction[(x, y)] = True 表示 x → y
        direction: dict[tuple[str, str], bool] = {}

        # 第一步：识别 v-结构
        v_structures = self._find_v_structures(skeleton_edges, sep_sets, adjacency)

        # 定向 v-结构中的边
        for x, z, y in v_structures:
            direction[(x, z)] = True  # x → z
            direction[(z, y)] = True  # z → y
            direction[(x, y)] = False  # x ← y（不是边）

        # 第二步：应用传散规则定向其他边
        changed = True
        max_iterations = 100  # 防止无限循环
        iteration = 0

        while changed and iteration < max_iterations:
            changed = False
            iteration += 1

            for x, y in skeleton_edges:
                edge = tuple(sorted([x, y]))

                # 检查这条边是否已经定向
                if edge in direction:
                    continue

                # 获取邻居
                neighbors_x = set(adjacency[x]) - {y}
                neighbors_y = set(adjacency[y]) - {x}

                # 规则1：如果 x→z，且 y-z 有边（未定向），且 x 和 y 不相邻
                # 则定向 z→y
                for z in neighbors_x:
                    if (x, z) in direction and direction[(x, z)]:
                        # x → z
                        if z in neighbors_y:
                            edge_z = tuple(sorted([z, y]))
                            if edge_z not in direction:
                                # z 和 y 之间有边（未定向）
                                if y not in neighbors_x:
                                    # x 和 y 不相邻
                                    direction[(z, y)] = True  # z → y
                                    changed = True

                        # 规则2：如果 x→z←y，则 x→y
                        for w in neighbors_y:
                            if (w, z) in direction and direction[(w, z)]:
                                # w → z
                                if x == w:
                                    continue
                                if x not in adjacency[w] and w not in adjacency[x]:
                                    # x 和 w 不相邻
                                    direction[(x, z)] = True  # x → z（确认）
                                    direction[(w, z)] = True  # w → z（确认）
                                    edge_xy = tuple(sorted([x, y]))
                                    if edge_xy not in direction:
                                        direction[(x, y)] = True if x < y else False  # x → y
                                        changed = True

        # 第三步：处理仍未定向的边
        undirected = []
        for x, y in skeleton_edges:
            edge = tuple(sorted([x, y]))
            if edge not in direction:
                undirected.append((x, y))

        # 转换已定向边为 (from, to) 格式
        directed = []
        for edge, is_x_to_y in direction.items():
            x, y = edge
            if is_x_to_y:
                directed.append((x, y))
            else:
                directed.append((y, x))

        return directed, undirected

    def _find_v_structures(
        self,
        skeleton_edges: list[tuple[str, str]],
        sep_sets: dict[tuple[str, str], frozenset[str]],
        adjacency: dict[str, set[str]],
    ) -> list[tuple[str, str, str]]:
        """
        识别 v-结构

        v-结构：X → Z ← Y，其中 X 和 Y 不相邻，且 Z 不在 separator(X, Y) 中

        Args:
            skeleton_edges: 骨架边
            sep_sets: separator sets
            adjacency: 邻接表

        Returns:
            v-结构列表 [(x, z, y), ...]
        """
        v_structures = []

        # 构建边集合（用于快速查找）
        edge_set = set()
        for x, y in skeleton_edges:
            edge_set.add(tuple(sorted([x, y])))

        # 遍历所有三元组
        all_nodes = list(adjacency.keys())
        for z in all_nodes:
            # 找到 z 的所有邻居
            neighbors = list(adjacency[z])

            for i, x in enumerate(neighbors):
                for y in neighbors[i + 1:]:
                    # 检查 x 和 y 是否相邻
                    edge_xy = tuple(sorted([x, y]))
                    if edge_xy in edge_set:
                        # x 和 y 相邻，不是 v-结构
                        continue

                    # 检查 Z 是否在 separator(X, Y) 中
                    sep_xy = sep_sets.get((x, y), frozenset())
                    sep_yx = sep_sets.get((y, x), frozenset())
                    sep = sep_xy if sep_xy else sep_yx

                    if z not in sep:
                        # 这是一个 v-结构：x → z ← y
                        v_structures.append((x, z, y))

        return v_structures

    def _get_all_nodes(self, edges: list[tuple[str, str]]) -> set[str]:
        """获取所有节点"""
        nodes = set()
        for x, y in edges:
            nodes.add(x)
            nodes.add(y)
        return nodes

    def orient_with_constraints(
        self,
        directed_edges: list[tuple[str, str]],
        undirected_edges: list[tuple[str, str]],
        orientation_constraints: list[tuple[str, str, str]] | None = None,
    ) -> list[tuple[str, str]]:
        """
        使用约束定向边

        Args:
            directed_edges: 已定向边
            undirected_edges: 未定向边
            orientation_constraints: 方向约束 [(var1, var2, direction), ...]
                direction: "->" 表示 var1 → var2, "<-" 表示 var1 ← var2

        Returns:
            完整定向边列表
        """
        # 从已定向边开始
        result = list(directed_edges)

        # 构建已定向边的集合
        directed_set = set()
        for x, y in directed_edges:
            directed_set.add((x, y))
            directed_set.add((y, x))  # 双向标记

        # 应用约束
        if orientation_constraints:
            for x, y, direction in orientation_constraints:
                edge = tuple(sorted([x, y]))
                if direction == "->":
                    result.append((x, y))
                    directed_set.add((x, y))
                    directed_set.add((y, x))
                elif direction == "<-":
                    result.append((y, x))
                    directed_set.add((y, x))
                    directed_set.add((x, y))

        # 尝试定向剩余的未定向边
        for x, y in undirected_edges:
            edge = tuple(sorted([x, y]))
            if edge in directed_set:
                continue

            # 使用简单的启发式方法：
            # 1. 如果只有一个方向有效，定向
            # 2. 否则，保持未定向

            # 这里可以添加更多启发式规则
            # 例如：时间顺序（原因在结果之前）

            result.append((x, y))  # 默认任意定向

        return result


class MeekRulesOrienter(EdgeOrienter):
    """
    使用 Meek 传散规则的边定向器

    Meek 规则更加完整：
    R1: 如果 u→v，v-w 是未定向边，且 u 和 w 不相邻，则 v→w
    R2: 如果 u→v，v→w，且 u-w 是未定向边，则 u→w
    R3: 如果 u→w，v→w，且 u-v 是未定向边，且 u 和 w 不相邻，则 u→v
    R4: 如果 v-w，v←w，且 u 和 w 不相邻，则 u→v
    """

    def orient_edges_meek(
        self,
        skeleton_edges: list[tuple[str, str]],
        sep_sets: dict[tuple[str, str], frozenset[str]],
        adjacency: dict[str, set[str]],
    ) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        """
        使用 Meek 规则定向边

        Args:
            skeleton_edges: 骨架中的边
            sep_sets: separator sets
            adjacency: 邻接表

        Returns:
            (directed_edges, undirected_edges)
        """
        # 构建边集合和邻居表
        edge_set = set()
        for x, y in skeleton_edges:
            edge_set.add(tuple(sorted([x, y])))

        # 方向记录：direction[(x, y)] = True 表示 x → y
        direction: dict[tuple[str, str], bool] = {}

        # 第一步：识别 v-结构
        v_structures = self._find_v_structures(skeleton_edges, sep_sets, adjacency)

        for x, z, y in v_structures:
            direction[(x, z)] = True
            direction[(z, y)] = True

        # 第二步：迭代应用 Meek 规则
        changed = True
        max_iterations = 100
        iteration = 0

        while changed and iteration < max_iterations:
            changed = False
            iteration += 1

            for edge in list(edge_set):
                x, y = edge

                # 跳过已定向的边
                if edge in direction:
                    continue

                # 获取邻居
                neighbors_x = set(adjacency.get(x, set())) - {y}
                neighbors_y = set(adjacency.get(y, set())) - {x}

                # R1: 如果 u→v，v-w 是未定向边，且 u 和 w 不相邻，则 v→w
                for u in neighbors_x:
                    if (x, u) not in direction or not direction[(x, u)]:
                        continue
                    # x → u

                    for w in neighbors_y:
                        w_edge = tuple(sorted([u, w]))
                        if w_edge in direction:
                            continue
                        # u-w 是未定向边

                        if w not in neighbors_x and x not in adjacency.get(u, set()):
                            # u 和 w 不相邻
                            direction[(u, w)] = True
                            changed = True

                # R2: 如果 u→v，v→w，且 u-w 是未定向边，则 u→w
                for u in neighbors_x:
                    if (x, u) not in direction or not direction[(x, u)]:
                        continue
                    # x → u

                    for v in neighbors_y:
                        if (v, y) not in direction or not direction[(v, y)]:
                            continue
                        # v → y

                        # 检查 x-v 是否有边
                        xv_edge = tuple(sorted([x, v]))
                        if xv_edge not in edge_set:
                            continue

                        if xv_edge not in direction:
                            direction[(x, v)] = True
                            changed = True

                # R3: 如果 u→w，v→w，且 u-v 是未定向边，且 u 和 w 不相邻，则 u→v
                for u in neighbors_x:
                    for v in neighbors_y:
                        if (x, u) not in direction or not direction[(x, u)]:
                            continue
                        if (v, y) not in direction or not direction[(v, y)]:
                            continue

                        uv_edge = tuple(sorted([u, v]))
                        if uv_edge in direction:
                            continue

                        # u-v 未定向
                        # 检查 u 和 w 是否不相邻
                        if v not in neighbors_x and u not in neighbors_y:
                            direction[(u, v)] = True
                            changed = True

                # R4: 如果 v-w，v←w，且 u 和 w 不相邻，则 u→v
                for w in neighbors_y:
                    wy_edge = tuple(sorted([v, w]))
                    # v ← w 意味着 w → v，但我们这里 v=y
                    # 检查 y 的邻居中是否有 w
                    if (y, w) in direction and direction[(y, w)]:
                        # y → w
                        for u in neighbors_x:
                            if u not in neighbors_y:
                                # u 和 w 不相邻
                                direction[(u, y)] = True
                                changed = True

        # 收集结果
        directed = []
        undirected = []

        for edge in edge_set:
            if edge in direction:
                x, y = edge
                if direction[edge]:
                    directed.append((x, y))
                else:
                    directed.append((y, x))
            else:
                undirected.append(edge)

        return directed, undirected
