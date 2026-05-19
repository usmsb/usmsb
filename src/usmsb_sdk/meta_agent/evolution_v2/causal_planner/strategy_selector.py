"""
策略选择器

CausalPlanner 的组件

贪心选择能覆盖最多因果边的策略组合
"""

from dataclasses import dataclass
from typing import Any

from ...models.causal_graph import CausalEdge


@dataclass
class StrategyProfile:
    """策略画像"""
    strategy_id: str
    name: str
    activates_edges: list[str]  # 激活的因果边 ID
    produces_nodes: list[str]   # 产生的因果节点
    cost: float
    success_rate: float
    applicable_conditions: list[str]


@dataclass
class PlanningConstraints:
    """规划约束"""
    max_duration: float
    max_cost: float
    min_quality: float = 0.5


@dataclass
class StrategySelectionResult:
    """策略选择结果"""
    selected_strategies: list[StrategyProfile]
    covered_edges: set[str]
    total_cost: float
    expected_quality: float
    coverage_ratio: float


class StrategySelector:
    """
    策略选择器

    贪心算法选择能覆盖最多必需因果边的策略组合

    算法：
    1. 每次选择能覆盖最多未覆盖边的策略
    2. 直到所有必需边都被覆盖，或预算耗尽
    """

    def __init__(self, strategy_registry: dict[str, StrategyProfile] | None = None):
        """
        初始化

        Args:
            strategy_registry: 策略注册表
        """
        self.strategy_registry = strategy_registry or {}

    def select(
        self,
        required_edges: list[CausalEdge],
        constraints: PlanningConstraints,
        available_strategies: list[StrategyProfile] | None = None,
    ) -> StrategySelectionResult:
        """
        选择最优策略组合

        Args:
            required_edges: 必需的因果边
            constraints: 规划约束
            available_strategies: 可用策略列表（如果为 None，使用注册表中的所有策略）

        Returns:
            策略选择结果
        """
        if not available_strategies:
            available_strategies = list(self.strategy_registry.values())

        # 必需边的 ID 集合
        required_edge_ids = {e.edge_id for e in required_edges}
        covered_edges: set[str] = set()
        selected_strategies = []
        total_cost = 0.0
        remaining_budget = constraints.max_cost

        # 可用的策略
        remaining_strategies = list(available_strategies)

        while required_edge_ids - covered_edges and remaining_strategies and remaining_budget > 0:
            best_strategy = None
            best_coverage = 0
            best_efficiency = 0.0

            for strategy in remaining_strategies:
                # 计算该策略能覆盖多少未覆盖的边
                coverage = len(
                    set(strategy.activates_edges) & (required_edge_ids - covered_edges)
                )

                if coverage == 0:
                    continue

                # 成本效益
                efficiency = coverage / max(strategy.cost, 0.1)

                if efficiency > best_efficiency:
                    best_strategy = strategy
                    best_coverage = coverage
                    best_efficiency = efficiency

            if best_strategy is None:
                break

            # 选择该策略
            selected_strategies.append(best_strategy)
            covered_edges |= set(best_strategy.activates_edges)
            total_cost += best_strategy.cost
            remaining_budget -= best_strategy.cost

            # 移除已选策略
            remaining_strategies.remove(best_strategy)

        # 计算期望质量（基于选中策略的平均成功率）
        if selected_strategies:
            expected_quality = sum(s.success_rate for s in selected_strategies) / len(selected_strategies)
        else:
            expected_quality = 0.0

        # 计算覆盖率
        if required_edge_ids:
            coverage_ratio = len(covered_edges & required_edge_ids) / len(required_edge_ids)
        else:
            coverage_ratio = 1.0

        return StrategySelectionResult(
            selected_strategies=selected_strategies,
            covered_edges=covered_edges,
            total_cost=total_cost,
            expected_quality=expected_quality,
            coverage_ratio=coverage_ratio,
        )

    def register_strategy(self, strategy: StrategyProfile) -> None:
        """注册策略"""
        self.strategy_registry[strategy.strategy_id] = strategy

    def unregister_strategy(self, strategy_id: str) -> None:
        """注销策略"""
        if strategy_id in self.strategy_registry:
            del self.strategy_registry[strategy_id]


class AdaptiveStrategySelector(StrategySelector):
    """
    自适应策略选择器

    根据任务特征动态调整策略选择
    """

    def __init__(self, strategy_registry: dict[str, StrategyProfile] | None = None):
        super().__init__(strategy_registry)
        self._success_history: dict[str, list[float]] = {}

    def update_success_rate(
        self,
        strategy_id: str,
        success: bool,
        quality: float,
    ) -> None:
        """
        更新策略成功率

        Args:
            strategy_id: 策略 ID
            success: 是否成功
            quality: 质量
        """
        if strategy_id not in self._success_history:
            self._success_history[strategy_id] = []

        # 记录最近的成功率和质量
        score = 1.0 if success else 0.0
        self._success_history[strategy_id].append(score * quality)

        # 只保留最近 20 次
        if len(self._success_history[strategy_id]) > 20:
            self._success_history[strategy_id] = self._success_history[strategy_id][-20:]

    def select(
        self,
        required_edges: list[CausalEdge],
        constraints: PlanningConstraints,
        available_strategies: list[StrategyProfile] | None = None,
        task_features: dict[str, Any] | None = None,
    ) -> StrategySelectionResult:
        """
        选择最优策略组合（带自适应）

        Args:
            required_edges: 必需的因果边
            constraints: 规划约束
            available_strategies: 可用策略列表
            task_features: 任务特征
        """
        if available_strategies is None:
            available_strategies = list(self.strategy_registry.values())

        # 根据历史更新策略成功率
        for strategy in available_strategies:
            if strategy.strategy_id in self._success_history:
                history = self._success_history[strategy.strategy_id]
                if history:
                    strategy.success_rate = sum(history) / len(history)

        return super().select(required_edges, constraints, available_strategies)


class BeamSearchStrategySelector(StrategySelector):
    """
    Beam Search 策略选择器

    探索多条路径，选择最优组合
    """

    def __init__(self, strategy_registry: dict[str, StrategyProfile] | None = None, beam_width: int = 3):
        super().__init__(strategy_registry)
        self.beam_width = beam_width

    def select(
        self,
        required_edges: list[CausalEdge],
        constraints: PlanningConstraints,
        available_strategies: list[StrategyProfile] | None = None,
    ) -> StrategySelectionResult:
        """
        Beam Search 选择策略

        Args:
            required_edges: 必需的因果边
            constraints: 规划约束
            available_strategies: 可用策略列表
        """
        if not available_strategies:
            available_strategies = list(self.strategy_registry.values())

        required_edge_ids = {e.edge_id for e in required_edges}

        # Beam 状态：(covered_edges, strategies, cost, expected_quality)
        beam = [(set(), [], 0.0, 0.0)]

        max_iterations = 20  # 防止无限循环

        for _ in range(max_iterations):
            next_beam = []

            for covered, strategies, cost, quality in beam:
                if covered >= required_edge_ids:
                    # 已覆盖所有边，直接添加
                    next_beam.append((covered, strategies, cost, quality))
                    continue

                if cost >= constraints.max_cost:
                    continue

                # 尝试添加每个策略
                for strategy in available_strategies:
                    if strategy in strategies:
                        continue

                    new_covered = covered | set(strategy.activates_edges)
                    new_cost = cost + strategy.cost

                    if new_cost > constraints.max_cost:
                        continue

                    new_quality = (
                        (quality * len(strategies) + strategy.success_rate)
                        / (len(strategies) + 1)
                        if strategies
                        else strategy.success_rate
                    )

                    next_beam.append((new_covered, strategies + [strategy], new_cost, new_quality))

            # 排序并截断
            next_beam.sort(key=lambda x: (len(x[0] & required_edge_ids), -x[2]), reverse=True)
            beam = next_beam[:self.beam_width]

            # 如果所有 beam 状态都已覆盖所有边，停止
            if all(covered >= required_edge_ids for covered, _, _, _ in beam):
                break

        # 选择最优
        if beam:
            best = max(beam, key=lambda x: (len(x[0] & required_edge_ids), -x[2]))
            covered_edges = best[0]
            selected_strategies = best[1]
            total_cost = best[2]
            expected_quality = best[3]
        else:
            covered_edges = set()
            selected_strategies = []
            total_cost = 0.0
            expected_quality = 0.0

        coverage_ratio = (
            len(covered_edges & required_edge_ids) / len(required_edge_ids)
            if required_edge_ids
            else 1.0
        )

        return StrategySelectionResult(
            selected_strategies=selected_strategies,
            covered_edges=covered_edges,
            total_cost=total_cost,
            expected_quality=expected_quality,
            coverage_ratio=coverage_ratio,
        )
