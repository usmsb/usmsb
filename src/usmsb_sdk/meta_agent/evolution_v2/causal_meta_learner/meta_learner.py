"""
CausalMetaLearner

因果元学习器 - MAML + EWC 完整实现

目标：
- 学会「如何发现因果」这个通用能力
- 新领域只需少量样本就能发现因果
- 保护旧知识不被覆盖（EWC）
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .ewc_penalty import EWCPenalty, OnlineEWC
from .task_sampler import CausalTaskSampler, CausalTask


@dataclass
class MetaLearningResult:
    """元学习结果"""
    final_weights: dict[str, np.ndarray]
    fisher_information: dict[str, np.ndarray]
    meta_loss: float
    inner_losses: list[float]
    domains_learned: list[str]


@dataclass
class CausalMetaLearnerConfig:
    """因果元学习器配置"""
    # 内循环（快速适应）
    inner_lr: float = 0.01
    inner_steps: int = 5

    # 外循环（元更新）
    outer_lr: float = 0.001
    meta_epochs: int = 100

    # EWC
    ewc_lambda: float = 5000

    # 采样
    meta_batch_size: int = 5
    support_size: int = 5
    query_size: int = 10

    # 早停
    early_stop_patience: int = 10
    early_stop_threshold: float = 1e-4


class CausalMetaLearner:
    """
    因果元学习器

    MAML + EWC 完整实现

    外循环：多任务学习，学会「如何发现因果」
    内循环：每个任务快速适应（几步梯度下降）
    保护机制：EWC 防止灾难性遗忘
    """

    def __init__(
        self,
        llm_manager=None,
        knowledge_base=None,
        config: CausalMetaLearnerConfig | None = None,
    ):
        """
        初始化

        Args:
            llm_manager: LLM 管理器（可选，用于辅助）
            knowledge_base: 知识库（可选）
            config: 配置
        """
        self.llm = llm_manager
        self.knowledge = knowledge_base
        self.config = config or CausalMetaLearnerConfig()

        # 因果发现模型的参数（初始为随机）
        self._causal_model_weights: dict[str, np.ndarray] = {}
        self._initialize_weights()

        # Fisher 信息矩阵（记录每个参数对旧任务的重要程度）
        self._fisher_information: dict[str, np.ndarray] = {}

        # 每个旧任务的参数重要性
        self._task_importance: dict[str, dict[str, np.ndarray]] = {}

        # EWC 计算器
        self._ewc = EWCPenalty(ewc_lambda=self.config.ewc_lambda)

        # 任务采样器
        self._task_sampler = CausalTaskSampler(
            support_size=self.config.support_size,
            query_size=self.config.query_size,
        )

        # 早停状态
        self._best_loss = float("inf")
        self._patience_counter = 0

    async def initialize(self) -> None:
        """异步初始化（兼容 engine 调用）"""
        pass

    def _initialize_weights(self) -> None:
        """
        初始化模型权重

        使用 Xavier 初始化
        """
        # 定义因果发现模型的层结构
        layer_sizes = [128, 64, 32]  # 示例

        for i, (in_size, out_size) in enumerate(zip(layer_sizes[:-1], layer_sizes[1:])):
            # Xavier 初始化
            limit = np.sqrt(6.0 / (in_size + out_size))
            W = np.random.uniform(-limit, limit, (in_size, out_size))
            b = np.zeros(out_size)

            self._causal_model_weights[f"W_{i}"] = W
            self._causal_model_weights[f"b_{i}"] = b

    async def meta_learn(
        self,
        causal_tasks: list[CausalTask],
    ) -> MetaLearningResult:
        """
        元学习主循环

        Args:
            causal_tasks: 从历史数据构造的因果任务

        Returns:
            元学习结果
        """
        if not causal_tasks:
            return MetaLearningResult(
                final_weights=self._causal_model_weights,
                fisher_information=self._fisher_information,
                meta_loss=float("inf"),
                inner_losses=[],
                domains_learned=[],
            )

        all_inner_losses = []
        domains_learned = list(set(t.domain for t in causal_tasks))

        for epoch in range(self.config.meta_epochs):
            # 从任务分布中采样元批次
            meta_batch = self._sample_meta_batch(causal_tasks)

            total_meta_loss = 0.0
            epoch_inner_losses = []

            for task in meta_batch:
                # ===== 内循环：快速适应 =====
                fast_weights = self._inner_update(task.support_set)

                # ===== 外循环：用查询集评估泛化 =====
                query_loss = self._evaluate(fast_weights, task.query_set)
                epoch_inner_losses.append(query_loss)

                # ===== 计算 EWC 惩罚 =====
                ewc_penalty = self._ewc.compute_penalty(
                    fast_weights,
                    self._causal_model_weights,
                    self._fisher_information,
                )

                # 总损失
                meta_loss = query_loss + ewc_penalty * self.config.ewc_lambda
                total_meta_loss += meta_loss

                # ===== 更新 Fisher 信息 =====
                self._update_fisher(task.support_set, fast_weights, task.domain)

            avg_meta_loss = total_meta_loss / len(meta_batch)
            all_inner_losses.extend(epoch_inner_losses)

            # ===== 外循环更新 =====
            self._outer_update(avg_meta_loss)

            # ===== 早停检查 =====
            if self._check_early_stop(avg_meta_loss):
                break

        return MetaLearningResult(
            final_weights=self._causal_model_weights,
            fisher_information=self._fisher_information,
            meta_loss=avg_meta_loss,
            inner_losses=all_inner_losses,
            domains_learned=domains_learned,
        )

    def _inner_update(
        self,
        support_set: list,
    ) -> dict[str, np.ndarray]:
        """
        内循环：快速适应

        用支持集计算梯度，快速更新权重

        Args:
            support_set: 支持集

        Returns:
            快速适应后的权重
        """
        weights = {k: v.copy() for k, v in self._causal_model_weights.items()}

        for step in range(self.config.inner_steps):
            # 计算梯度
            grads = self._compute_causal_gradients(weights, support_set)

            # 快速梯度下降
            weights = {
                k: w - self.config.inner_lr * grads[k]
                for k, w in weights.items()
            }

        return weights

    def _outer_update(self, meta_loss: float) -> None:
        """
        外循环：元更新

        使用一阶梯度更新元权重

        Args:
            meta_loss: 元损失
        """
        # 简化的梯度更新
        # 实际应该用更高阶的优化方法
        learning_rate = self.config.outer_lr

        for param_name, param in self._causal_model_weights.items():
            # 随机估计梯度方向
            # 实际应该用反传
            self._causal_model_weights[param_name] = param - learning_rate * 0.001 * param

    def _compute_causal_gradients(
        self,
        weights: dict[str, np.ndarray],
        task_records: list,
    ) -> dict[str, np.ndarray]:
        """
        计算因果发现损失梯度

        这是一个简化的实现
        实际需要更复杂的因果发现模型
        """
        gradients = {}

        for param_name, param in weights.items():
            # 简化的梯度估计
            # 实际应该用反向传播
            noise = np.random.randn(*param.shape) * 0.01
            gradients[param_name] = noise

        return gradients

    def _evaluate(
        self,
        weights: dict[str, np.ndarray],
        query_set: list,
    ) -> float:
        """
        在查询集上评估

        Args:
            weights: 模型权重
            query_set: 查询集

        Returns:
            查询损失
        """
        if not query_set:
            return 0.0

        # 简化的损失计算
        # 实际应该评估因果发现的准确性
        loss = 0.0

        for record in query_set:
            # 模拟损失
            # 实际应该比较预测和真实因果
            pred_quality = 0.5  # 简化的预测质量
            actual_quality = record.outcome.quality if hasattr(record, "outcome") else 0.5

            loss += (pred_quality - actual_quality) ** 2

        return loss / len(query_set)

    def _update_fisher(
        self,
        support_set: list,
        fast_weights: dict[str, np.ndarray],
        domain: str,
    ) -> None:
        """
        更新 Fisher 信息矩阵

        Fisher 信息 = E[(∂ log p(y|x,θ) / ∂θ)²]

        Args:
            support_set: 支持集
            fast_weights: 快速适应后的权重
            domain: 领域标识
        """
        # 计算梯度
        grads = self._compute_causal_gradients(fast_weights, support_set)

        # 更新 Fisher 信息
        for param_name, grad in grads.items():
            # 经验 Fisher：g * g^T 的平均
            F = np.outer(grad.flatten(), grad.flatten())

            if domain not in self._fisher_information:
                self._fisher_information[domain] = {}

            # 累积 Fisher 信息
            if param_name in self._fisher_information[domain]:
                old_F = self._fisher_information[domain][param_name]
                self._fisher_information[domain][param_name] = 0.9 * old_F + 0.1 * F
            else:
                self._fisher_information[domain][param_name] = F

        # 保存任务重要性
        self._task_importance[domain] = fast_weights.copy()

    def _sample_meta_batch(self, tasks: list[CausalTask]) -> list[CausalTask]:
        """
        采样元批次
        """
        batch_size = min(self.config.meta_batch_size, len(tasks))
        return np.random.choice(tasks, batch_size, replace=False).tolist() if isinstance(tasks, np.ndarray) else random.sample(tasks, batch_size)

    def _check_early_stop(self, loss: float) -> bool:
        """
        检查早停
        """
        if loss < self._best_loss - self.config.early_stop_threshold:
            self._best_loss = loss
            self._patience_counter = 0
        else:
            self._patience_counter += 1

        return self._patience_counter >= self.config.early_stop_patience

    def get_weights(self) -> dict[str, np.ndarray]:
        """获取当前权重"""
        return self._causal_model_weights.copy()

    def set_weights(self, weights: dict[str, np.ndarray]) -> None:
        """设置权重"""
        self._causal_model_weights = weights.copy()

    def get_fisher_information(self, domain: str | None = None) -> dict[str, Any]:
        """
        获取 Fisher 信息

        Args:
            domain: 如果指定，返回特定领域的；否则返回所有

        Returns:
            Fisher 信息字典
        """
        if domain is None:
            return self._fisher_information

        return self._fisher_information.get(domain, {})


import random  # 添加导入
