"""
因果任务采样器

CausalMetaLearner 的组件

从历史数据中构造因果任务
每个任务包含支持集和查询集
"""

import random
from dataclasses import dataclass
from typing import Any

from ...models.task_record import TaskRecord


@dataclass
class CausalTask:
    """
    因果元学习任务

    用于 MAML 的内循环和外循环评估
    """
    domain: str
    support_set: list[TaskRecord]
    query_set: list[TaskRecord]
    causal_graph_gt: Any = None
    difficulty: float = 0.5


class CausalTaskSampler:
    """
    因果任务采样器

    从历史数据中构造因果任务
    每个任务代表一个"领域"
    支持集用于快速适应，查询集用于评估泛化
    """

    def __init__(
        self,
        support_size: int = 5,
        query_size: int = 10,
        min_task_size: int = 15,
    ):
        """
        初始化

        Args:
            support_size: 支持集大小
            query_size: 查询集大小
            min_task_size: 最小任务大小（support + query）
        """
        self.support_size = support_size
        self.query_size = query_size
        self.min_task_size = min_task_size

    def sample_tasks(
        self,
        all_records: list[TaskRecord],
        num_tasks: int | None = None,
    ) -> list[CausalTask]:
        """
        从所有记录中采样多个因果任务

        Args:
            all_records: 所有任务记录
            num_tasks: 要采样的任务数（默认自动）

        Returns:
            因果任务列表
        """
        # 按领域分组
        domain_groups = self._group_by_domain(all_records)

        tasks = []
        for domain, records in domain_groups.items():
            if len(records) < self.min_task_size:
                continue

            # 采样多个任务（每个领域可采样多个）
            n_samples = min(
                len(records) // self.min_task_size,
                num_tasks or 10
            )

            for _ in range(n_samples):
                task = self._sample_single_task(domain, records)
                if task:
                    tasks.append(task)

        # 如果指定了任务数，限制返回
        if num_tasks is not None and len(tasks) > num_tasks:
            tasks = random.sample(tasks, num_tasks)

        return tasks

    def _group_by_domain(
        self, records: list[TaskRecord]
    ) -> dict[str, list[TaskRecord]]:
        """
        按领域分组任务记录
        """
        groups: dict[str, list[TaskRecord]] = {}

        for record in records:
            domain = getattr(record, "domain", "general") or "general"
            if domain not in groups:
                groups[domain] = []
            groups[domain].append(record)

        return groups

    def _sample_single_task(
        self,
        domain: str,
        records: list[TaskRecord],
    ) -> CausalTask | None:
        """
        从领域记录中采样单个因果任务
        """
        if len(records) < self.min_task_size:
            return None

        # 随机打乱
        shuffled = records.copy()
        random.shuffle(shuffled)

        # 划分支持集和查询集
        total = self.support_size + self.query_size
        if len(shuffled) < total:
            return None

        support = shuffled[:self.support_size]
        query = shuffled[self.support_size:total]

        # 估计难度（基于效果方差）
        difficulty = self._estimate_difficulty(support + query)

        return CausalTask(
            domain=domain,
            support_set=support,
            query_set=query,
            difficulty=difficulty,
        )

    def _estimate_difficulty(self, records: list[TaskRecord]) -> float:
        """
        估计任务难度

        基于成功率方差和执行时间方差
        """
        if not records:
            return 0.5

        # 成功率
        success_rate = sum(1 for r in records if r.outcome.success) / len(records)

        # 执行时间方差（归一化）
        durations = [r.outcome.duration for r in records if r.outcome.duration > 0]
        if durations:
            duration_std = np.std(durations) / (np.mean(durations) + 1e-6)
        else:
            duration_std = 0

        # 难度 = 1 - 成功率 + 时间方差（归一化）
        difficulty = (1 - success_rate + min(duration_std, 1)) / 2

        return max(0.0, min(1.0, difficulty))

    def sample_task_by_domain(
        self,
        records: list[TaskRecord],
        domain: str,
    ) -> CausalTask | None:
        """
        采样指定领域的任务
        """
        domain_records = [r for r in records if getattr(r, "domain", "general") == domain]
        return self._sample_single_task(domain, domain_records)


import numpy as np  # 添加导入


class MetaBatchSampler:
    """
    元学习批次采样器

    用于 MAML 外循环，一次采样多个任务
    """

    def __init__(
        self,
        task_sampler: CausalTaskSampler,
        meta_batch_size: int = 5,
    ):
        """
        初始化

        Args:
            task_sampler: 因果任务采样器
            meta_batch_size: 每个元批次的任务数
        """
        self.task_sampler = task_sampler
        self.meta_batch_size = meta_batch_size

    def sample_meta_batch(
        self,
        all_records: list[TaskRecord],
    ) -> list[CausalTask]:
        """
        采样一个元批次

        Args:
            all_records: 所有记录

        Returns:
            元批次任务列表
        """
        return self.task_sampler.sample_tasks(
            all_records,
            num_tasks=self.meta_batch_size,
        )


class AdaptiveTaskSampler(CausalTaskSampler):
    """
    自适应任务采样器

    根据历史表现调整采样策略
    """

    def __init__(
        self,
        support_size: int = 5,
        query_size: int = 10,
        min_task_size: int = 15,
        difficulty_weight: float = 0.3,
    ):
        super().__init__(support_size, query_size, min_task_size)
        self.difficulty_weight = difficulty_weight

        # 跟踪每个领域的性能
        self.domain_performance: dict[str, dict[str, float]] = {}

    def update_domain_performance(
        self,
        domain: str,
        performance: float,
    ) -> None:
        """
        更新领域性能
        """
        if domain not in self.domain_performance:
            self.domain_performance[domain] = {}
            self.domain_performance[domain]["scores"] = []

        self.domain_performance[domain]["scores"].append(performance)

        # 计算平均性能
        scores = self.domain_performance[domain]["scores"]
        self.domain_performance[domain]["avg_performance"] = np.mean(scores[-10:])

    def sample_tasks_adaptive(
        self,
        all_records: list[TaskRecord],
        num_tasks: int = 10,
    ) -> list[CausalTask]:
        """
        自适应采样任务

        优先采样性能较差的领域（探索）
        """
        # 计算每个领域的采样权重
        domain_weights = self._compute_domain_weights()

        # 按权重采样领域
        tasks = []
        for _ in range(num_tasks):
            domain = self._sample_domain(domain_weights)
            domain_records = [
                r for r in all_records
                if getattr(r, "domain", "general") == domain
            ]

            task = self._sample_single_task(domain, domain_records)
            if task:
                tasks.append(task)

        return tasks

    def _compute_domain_weights(self) -> dict[str, float]:
        """
        计算每个领域的采样权重

        性能差的领域权重更高（需要更多学习）
        """
        weights = {}

        for domain, perf in self.domain_performance.items():
            avg_perf = perf.get("avg_performance", 0.5)
            # 性能越差，权重越高
            weights[domain] = 1 - avg_perf + self.difficulty_weight

        # 归一化
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return weights

    def _sample_domain(self, weights: dict[str, float]) -> str:
        """
        根据权重采样领域
        """
        domains = list(weights.keys())
        probs = list(weights.values())

        return np.random.choice(domains, p=probs)
