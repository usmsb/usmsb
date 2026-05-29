"""
增量更新器

CausalDiscoveryEngine 的增量更新组件

支持：
1. 增量更新：添加新记录后局部调整因果图
2. 定期全量重构：累积一定量后完全重新计算
"""

from typing import Any

import numpy as np

from ...models.causal_graph import CausalGraph, CausalEdge


class IncrementalUpdater:
    """
    增量更新器

    当新任务记录到来时，不需要完全重新运行 PC Algorithm
    而是：
    1. 检查新记录是否支持现有边
    2. 检查是否需要添加新边
    3. 检查现有边的强度是否需要调整
    4. 如果变化太大，触发全量重构
    """

    def __init__(
        self,
        ci_tester,
        incremental_update_interval: int = 10,
        full_rebuild_interval: int = 50,
        change_threshold: float = 0.2,
    ):
        """
        初始化

        Args:
            ci_tester: ConditionalIndependenceTest 实例
            incremental_update_interval: 增量更新间隔（新记录数）
            full_rebuild_interval: 全量重构间隔（增量更新次数）
            change_threshold: 变化阈值，超过则触发全量重构
        """
        self.ci_tester = ci_tester
        self.incremental_update_interval = incremental_update_interval
        self.full_rebuild_interval = full_rebuild_interval
        self.change_threshold = change_threshold

        # 内部状态
        self._update_count = 0  # 增量更新次数
        self._pending_records = []  # 待处理的记录

    def should_full_rebuild(self) -> bool:
        """检查是否应该触发全量重构"""
        return self._update_count >= self.full_rebuild_interval

    def should_incremental_update(self) -> bool:
        """检查是否应该触发增量更新"""
        return len(self._pending_records) >= self.incremental_update_interval

    def add_record(self, record) -> None:
        """
        添加新记录

        Args:
            record: TaskRecord 对象
        """
        self._pending_records.append(record)

    def reset_pending(self) -> None:
        """清空待处理记录"""
        self._pending_records = []

    def reset_update_count(self) -> None:
        """重置更新计数"""
        self._update_count = 0

    def incremental_update(
        self,
        current_graph: CausalGraph,
        new_records: list,
        variables: list[str],
        data: dict[str, np.ndarray],
    ) -> tuple[CausalGraph, bool]:
        """
        增量更新因果图

        Args:
            current_graph: 当前的因果图
            new_records: 新任务记录
            variables: 变量名列表
            data: 当前所有数据

        Returns:
            (updated_graph, triggered_full_rebuild)
            - updated_graph: 更新后的因果图
            - triggered_full_rebuild: 是否触发了全量重构
        """
        self._update_count += 1

        # 如果应该全量重构，直接返回触发信号
        if self.should_full_rebuild():
            self._update_count = 0
            return current_graph, True

        # 检查变化
        changes = self._detect_changes(current_graph, new_records, variables, data)

        # 如果变化太大，触发全量重构
        if changes["magnitude"] > self.change_threshold:
            return current_graph, True

        # 应用增量更新
        updated_graph = self._apply_incremental_changes(
            current_graph, changes, variables, data
        )

        return updated_graph, False

    def _detect_changes(
        self,
        current_graph: CausalGraph,
        new_records: list,
        variables: list[str],
        data: dict[str, np.ndarray],
    ) -> dict[str, Any]:
        """
        检测新数据相对于当前图的变化

        Returns:
            {
                "added_edges": [(source, target), ...],
                "removed_edges": [(source, target), ...],
                "strength_changes": {(source, target): delta_strength, ...},
                "magnitude": float  # 总体变化大小
            }
        """
        changes = {
            "added_edges": [],
            "removed_edges": [],
            "strength_changes": {},
            "magnitude": 0.0,
        }

        # 构建当前边的集合
        current_edges = set()
        for edge in current_graph.edges:
            current_edges.add((edge.source, edge.target))

        # 对每条现有边，检查是否仍然显著
        for edge in current_graph.edges:
            x_data = data.get(edge.source)
            y_data = data.get(edge.target)

            if x_data is None or y_data is None:
                continue

            # 计算新的 CMI
            cmi, p_value = self.ci_tester.ci_test(x_data, y_data, None, method="cmi")

            # 如果不再显著，标记为移除
            if p_value > self.ci_tester.alpha:
                changes["removed_edges"].append((edge.source, edge.target))
                changes["strength_changes"][(edge.source, edge.target)] = -edge.strength
            else:
                # 计算强度变化
                old_strength = edge.strength
                # 重新估计强度（简化版）
                new_strength = min(abs(cmi) / 2, 1.0) * (1 if cmi > 0 else -1)
                delta = abs(new_strength - old_strength)
                changes["strength_changes"][(edge.source, edge.target)] = delta

        # 检查是否需要添加新边
        # 简化：只检查与新记录相关的变量
        # 实际实现中应该更复杂

        # 计算总体变化大小
        n_changes = (
            len(changes["added_edges"])
            + len(changes["removed_edges"])
            + len(changes["strength_changes"])
        )
        total_delta = sum(abs(v) for v in changes["strength_changes"].values())

        changes["magnitude"] = min(total_delta / max(len(current_edges), 1), 1.0)

        return changes

    def _apply_incremental_changes(
        self,
        current_graph: CausalGraph,
        changes: dict[str, Any],
        variables: list[str],
        data: dict[str, np.ndarray],
    ) -> CausalGraph:
        """
        应用增量变化到因果图
        """
        import copy

        updated_graph = copy.deepcopy(current_graph)

        # 移除不再显著的边
        for source, target in changes["removed_edges"]:
            # 找到边并移除（使用列表推导式避免迭代中修改问题）
            updated_graph.edges = [
                edge for edge in updated_graph.edges
                if not (edge.source == source and edge.target == target)
            ]

        # 更新强度变化的边
        for (source, target), delta in changes["strength_changes"].items():
            for edge in updated_graph.edges:
                if edge.source == source and edge.target == target:
                    # 更新强度
                    new_strength = edge.strength + delta * 0.1  # 缓慢调整
                    edge.strength = max(-1.0, min(1.0, new_strength))
                    # 更新置信度
                    edge.confidence = max(0.0, edge.confidence - 0.05)
                    # 添加新证据
                    edge.evidence.append(f"incremental_update_{self._update_count}")
                    break

        # 添加新边（如果有）
        for source, target in changes["added_edges"]:
            x_data = data.get(source)
            y_data = data.get(target)

            if x_data is None or y_data is None:
                continue

            cmi, p_value = self.ci_tester.ci_test(x_data, y_data, None, method="cmi")

            new_edge = CausalEdge(
                edge_id=f"{source}_{target}_{self._update_count}",
                source=source,
                target=target,
                strength=min(abs(cmi) / 2, 1.0) * (1 if cmi > 0 else -1),
                confidence=0.7,
                evidence=[f"incremental_update_{self._update_count}"],
                is_directed=True,
            )
            updated_graph.add_edge(new_edge)

        updated_graph.updated_at = np.datetime64("now").astype(float)

        return updated_graph


class AdaptiveIncrementalUpdater(IncrementalUpdater):
    """
    自适应增量更新器

    根据数据特性自动调整更新策略
    """

    def __init__(
        self,
        ci_tester,
        incremental_update_interval: int = 10,
        full_rebuild_interval: int = 50,
        change_threshold: float = 0.2,
        min_stability_period: int = 5,
    ):
        super().__init__(
            ci_tester,
            incremental_update_interval,
            full_rebuild_interval,
            change_threshold,
        )
        self.min_stability_period = min_stability_period
        self._consecutive_small_changes = 0

    def incremental_update(
        self,
        current_graph: CausalGraph,
        new_records: list,
        variables: list[str],
        data: dict[str, np.ndarray],
    ) -> tuple[CausalGraph, bool]:
        """
        自适应增量更新

        如果连续多次小变化，降低更新频率
        如果有大变化，提高更新频率
        """
        self._update_count += 1

        changes = self._detect_changes(current_graph, new_records, variables, data)

        if changes["magnitude"] < 0.05:
            self._consecutive_small_changes += 1
        else:
            self._consecutive_small_changes = 0

        # 如果连续多次小变化，触发全量重构（确保没有遗漏）
        if self._consecutive_small_changes >= self.min_stability_period:
            self._consecutive_small_changes = 0
            return current_graph, True

        if changes["magnitude"] > self.change_threshold:
            return current_graph, True

        updated_graph = self._apply_incremental_changes(
            current_graph, changes, variables, data
        )

        return updated_graph, False
