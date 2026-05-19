"""
CausalDiscoveryEngine

因果发现引擎 - PC Algorithm 完整实现

主类，协调所有组件发现因果图
"""

import uuid
from datetime import datetime
from typing import Any

import numpy as np

from ...models.causal_graph import CausalGraph, CausalEdge
from ...models.task_record import TaskRecord, FEATURE_CATEGORIES, STRATEGY_FEATURES, OUTCOME_FEATURES
from .conditional_independence import ConditionalIndependenceTest
from .skeleton_builder import SkeletonBuilder, PCSkeletonBuilder
from .edge_orienter import EdgeOrienter, MeekRulesOrienter
from .strength_estimator import StrengthEstimator, RobustStrengthEstimator
from .incremental_updater import IncrementalUpdater, AdaptiveIncrementalUpdater


class CausalDiscoveryEngine:
    """
    因果发现引擎

    PC Algorithm 完整实现流程：

    1. 数据准备
       - 从 TaskRecord 提取变量
       - 构建特征-策略-效果变量表

    2. 建骨架
       - 从完全图开始
       - 通过条件独立性检验删边

    3. 定向边
       - v-结构识别
       - 传散规则定向

    4. 估计因果强度
       - 因果效应大小
       - 置信度

    5. 增量更新
       - 新记录局部调整
       - 定期全量重构
    """

    def __init__(
        self,
        alpha: float = 0.05,
        max_condition_set_size: int = 3,
        min_causal_strength: float = 0.1,
        min_confidence: float = 0.5,
        incremental_update_interval: int = 10,
        full_rebuild_interval: int = 50,
        use_robust_estimator: bool = True,
        use_adaptive_updater: bool = True,
    ):
        """
        初始化

        Args:
            alpha: 条件独立性检验显著性水平
            max_condition_set_size: 最大条件集大小
            min_causal_strength: 最小因果强度
            min_confidence: 最小置信度
            incremental_update_interval: 增量更新间隔
            full_rebuild_interval: 全量重构间隔
            use_robust_estimator: 使用鲁棒强度估计器
            use_adaptive_updater: 使用自适应增量更新器
        """
        self.alpha = alpha
        self.max_condition_set_size = max_condition_set_size

        # 初始化组件
        self.ci_tester = ConditionalIndependenceTest(alpha=alpha)

        self.skeleton_builder = PCSkeletonBuilder(
            ci_tester=self.ci_tester,
            alpha=alpha,
            max_condition_set_size=max_condition_set_size,
        )

        self.edge_orienter = MeekRulesOrienter()

        if use_robust_estimator:
            self.strength_estimator = RobustStrengthEstimator(
                min_causal_strength=min_causal_strength,
                min_confidence=min_confidence,
            )
        else:
            self.strength_estimator = StrengthEstimator(
                min_causal_strength=min_causal_strength,
                min_confidence=min_confidence,
            )

        if use_adaptive_updater:
            self.updater = AdaptiveIncrementalUpdater(
                ci_tester=self.ci_tester,
                incremental_update_interval=incremental_update_interval,
                full_rebuild_interval=full_rebuild_interval,
            )
        else:
            self.updater = IncrementalUpdater(
                ci_tester=self.ci_tester,
                incremental_update_interval=incremental_update_interval,
                full_rebuild_interval=full_rebuild_interval,
            )

        # 当前因果图
        self._current_graph: CausalGraph | None = None

        # 所有变量的数据
        self._all_data: dict[str, list] = {}

    async def initialize(self) -> None:
        """初始化引擎"""
        pass

    def discover(
        self,
        task_records: list[TaskRecord],
    ) -> CausalGraph:
        """
        从任务记录发现因果图

        Args:
            task_records: 任务记录列表

        Returns:
            CausalGraph: 发现的因果图
        """
        if len(task_records) < 10:
            # 样本太少，无法可靠发现
            return self._create_empty_graph()

        # Step 1: 准备数据
        variables, data = self._prepare_data(task_records)

        if len(variables) < 2:
            return self._create_empty_graph()

        # Step 2: 建骨架
        sep_sets, edge_weights = self.skeleton_builder.build_skeleton(variables, data)

        skeleton_edges = self.skeleton_builder.get_skeleton_edges(variables, data)

        if not skeleton_edges:
            return self._create_empty_graph()

        # 构建邻接表
        adjacency = self._build_adjacency(skeleton_edges)

        # Step 3: 定向边
        directed_edges, undirected_edges = self.edge_orienter.orient_edges_meek(
            skeleton_edges, sep_sets, adjacency
        )

        # Step 4: 估计因果强度
        edge_strengths = self.strength_estimator.estimate_strengths(
            variables, data, directed_edges, sep_sets
        )

        # 构建因果图
        graph = self._build_causal_graph(
            variables,
            data,
            directed_edges,
            undirected_edges,
            edge_strengths,
            sep_sets,
        )

        self._current_graph = graph
        self._all_data = {k: v.tolist() for k, v in data.items()}

        return graph

    def discover_incremental(
        self,
        new_records: list[TaskRecord],
    ) -> tuple[CausalGraph, bool]:
        """
        增量发现

        Args:
            new_records: 新任务记录

        Returns:
            (updated_graph, triggered_full_rebuild)
        """
        if self._current_graph is None:
            return self.discover(new_records), False

        # 添加新记录到数据中
        variables, data = self._prepare_data(new_records)

        # 更新所有数据
        for var in variables:
            if var in self._all_data:
                self._all_data[var].extend(data[var].tolist())
            else:
                self._all_data[var] = data[var].tolist()

        # 转换为 numpy 数组
        data = {k: np.array(v) for k, v in self._all_data.items()}

        # 增量更新
        updated_graph, triggered = self.updater.incremental_update(
            self._current_graph, new_records, variables, data
        )

        self._current_graph = updated_graph

        return updated_graph, triggered

    def full_rebuild(
        self,
        all_records: list[TaskRecord],
    ) -> CausalGraph:
        """
        全量重构

        Args:
            all_records: 所有任务记录

        Returns:
            CausalGraph: 重构后的因果图
        """
        self.updater.reset_update_count()
        self.updater.reset_pending()

        return self.discover(all_records)

    def get_current_graph(self) -> CausalGraph | None:
        """获取当前因果图"""
        return self._current_graph

    def _prepare_data(
        self, task_records: list[TaskRecord]
    ) -> tuple[list[str], dict[str, np.ndarray]]:
        """
        准备数据

        Args:
            task_records: 任务记录

        Returns:
            (variables, data)
            - variables: 变量名列表
            - data: 变量名 -> 数据数组 的字典
        """
        # 提取变量
        variables = []
        data_arrays: dict[str, list] = {}

        for record in task_records:
            # 任务特征
            features = record.features.to_dict()
            for cat, features_list in FEATURE_CATEGORIES.items():
                for feat in features_list:
                    if feat in features:
                        val = features[feat]
                        if isinstance(val, bool):
                            val = 1.0 if val else 0.0
                        elif not isinstance(val, (int, float)):
                            continue

                        if feat not in data_arrays:
                            data_arrays[feat] = []
                            variables.append(feat)
                        data_arrays[feat].append(val)

            # 策略特征
            strategy = record.strategy.to_dict()
            for cat, features_list in STRATEGY_FEATURES.items():
                for feat in features_list:
                    if feat in strategy:
                        val = strategy[feat]
                        if isinstance(val, bool):
                            val = 1.0 if val else 0.0
                        elif isinstance(val, (int, float)):
                            pass
                        else:
                            continue

                        if feat not in data_arrays:
                            data_arrays[feat] = []
                            variables.append(feat)
                        data_arrays[feat].append(val)

            # 效果特征
            outcome = record.outcome.to_dict()
            for cat, features_list in OUTCOME_FEATURES.items():
                for feat in features_list:
                    if feat in outcome:
                        val = outcome[feat]
                        if feat == "error_type":
                            val = 1.0 if val else 0.0
                        elif isinstance(val, bool):
                            val = 1.0 if val else 0.0
                        elif not isinstance(val, (int, float)):
                            continue

                        if feat not in data_arrays:
                            data_arrays[feat] = []
                            variables.append(feat)
                        data_arrays[feat].append(val)

        # 转换为 numpy 数组
        data = {k: np.array(v) for k, v in data_arrays.items()}

        # 过滤掉数据太少的变量
        valid_variables = [v for v in variables if len(data_arrays[v]) >= 10]

        return valid_variables, {k: data[k] for k in valid_variables}

    def _build_adjacency(
        self, skeleton_edges: list[tuple[str, str]]
    ) -> dict[str, set[str]]:
        """构建邻接表"""
        adjacency: dict[str, set[str]] = {}

        for x, y in skeleton_edges:
            if x not in adjacency:
                adjacency[x] = set()
            if y not in adjacency:
                adjacency[y] = set()
            adjacency[x].add(y)
            adjacency[y].add(x)

        return adjacency

    def _build_causal_graph(
        self,
        variables: list[str],
        data: dict[str, np.ndarray],
        directed_edges: list[tuple[str, str]],
        undirected_edges: list[tuple[str, str]],
        edge_strengths: dict[tuple[str, str], dict[str, float]],
        sep_sets: dict[tuple[str, str], frozenset[str]],
    ) -> CausalGraph:
        """
        构建因果图对象
        """
        graph_id = f"causal_graph_{uuid.uuid4().hex[:8]}"
        graph = CausalGraph(
            graph_id=graph_id,
            nodes=set(variables),
            metadata={
                "n_variables": len(variables),
                "n_records": len(data[variables[0]]) if variables else 0,
            },
            created_at=datetime.now().timestamp(),
            updated_at=datetime.now().timestamp(),
        )

        # 添加已定向边
        for source, target in directed_edges:
            strength_info = edge_strengths.get((source, target), {})
            strength = strength_info.get("strength", 0.0)
            confidence = strength_info.get("confidence", 0.5)

            sep = sep_sets.get((source, target), frozenset())

            edge = CausalEdge(
                edge_id=f"{source}_{target}_{uuid.uuid4().hex[:4]}",
                source=source,
                target=target,
                strength=strength,
                confidence=confidence,
                conditions=list(sep),
                evidence=[f"pc_algorithm"],
                is_directed=True,
            )
            graph.add_edge(edge)

        # 添加未定向边
        for x, y in undirected_edges:
            graph.add_undirected_edge(x, y)

        return graph

    def _create_empty_graph(self) -> CausalGraph:
        """创建空因果图"""
        return CausalGraph(
            graph_id=f"causal_graph_empty_{uuid.uuid4().hex[:8]}",
            nodes=set(),
            edges=[],
            metadata={"reason": "insufficient_data"},
        )
