"""
EWC 惩罚计算

Elastic Weight Consolidation 实现

防止灾难性遗忘：学习新任务时保护对旧任务重要的参数
"""

from typing import Any

import numpy as np


class EWCPenalty:
    """
    EWC 惩罚项计算

    EWC 核心思想：
    学习新任务时，对那些对旧任务重要的参数施加惩罚
    防止这些参数被大幅修改

    公式：
    L_ewc = Σ_i F_i * (θ_i - θ_i*_old)²

    其中 F_i 是 Fisher 信息（参数重要程度）
    θ_i*_old 是旧任务优化后的参数值
    """

    def __init__(self, ewc_lambda: float = 5000):
        """
        初始化

        Args:
            ewc_lambda: EWC 惩罚系数，控制旧知识的保护强度
        """
        self.ewc_lambda = ewc_lambda

    def compute_penalty(
        self,
        new_weights: dict[str, np.ndarray],
        old_weights: dict[str, np.ndarray],
        fisher_information: dict[str, np.ndarray],
    ) -> float:
        """
        计算 EWC 惩罚项

        Args:
            new_weights: 新任务的权重
            old_weights: 旧任务的权重
            fisher_information: Fisher 信息矩阵

        Returns:
            惩罚项的值
        """
        penalty = 0.0

        for param_name in new_weights:
            if param_name not in old_weights:
                continue

            theta = new_weights[param_name]
            theta_old = old_weights[param_name]
            F = fisher_information.get(param_name, np.zeros_like(theta))

            # Σ F_i * (θ_i - θ_i*_old)²
            diff = theta - theta_old
            penalty += np.sum(F * (diff**2))

        return self.ewc_lambda * penalty

    def compute_gradients(
        self,
        new_weights: dict[str, np.ndarray],
        old_weights: dict[str, np.ndarray],
        fisher_information: dict[str, np.ndarray],
    ) -> dict[str, np.ndarray]:
        """
        计算 EWC 惩罚项的梯度

        ∂L_ewc / ∂θ_i = 2 * F_i * (θ_i - θ_i*_old)

        Args:
            new_weights: 新任务的权重
            old_weights: 旧任务的权重
            fisher_information: Fisher 信息矩阵

        Returns:
            梯度字典
        """
        gradients = {}

        for param_name in new_weights:
            if param_name not in old_weights:
                continue

            theta = new_weights[param_name]
            theta_old = old_weights[param_name]
            F = fisher_information.get(param_name, np.zeros_like(theta))

            # 梯度：2 * F_i * (θ_i - θ_i*_old)
            gradients[param_name] = 2 * self.ewc_lambda * F * (theta - theta_old)

        return gradients


class OnlineEWC:
    """
    在线 EWC

    增量更新 Fisher 信息，避免存储所有旧任务的权重
    """

    def __init__(self, ewc_lambda: float = 5000, decay: float = 0.9):
        """
        初始化

        Args:
            ewc_lambda: EWC 惩罚系数
            decay: 衰减因子，用于合并多个 Fisher 信息
        """
        self.ewc_lambda = ewc_lambda
        self.decay = decay

        # 累积的 Fisher 信息
        self.accumulated_fisher: dict[str, np.ndarray] = {}
        self.optimal_weights: dict[str, np.ndarray] = {}

    def update(
        self,
        new_fisher: dict[str, np.ndarray],
        new_weights: dict[str, np.ndarray],
    ) -> None:
        """
        更新累积的 Fisher 信息和最优权重

        使用指数加权平均合并新的 Fisher 信息

        Args:
            new_fisher: 新计算的 Fisher 信息
            new_weights: 新优化后的权重
        """
        for param_name, F_new in new_fisher.items():
            if param_name in self.accumulated_fisher:
                # 指数加权平均
                self.accumulated_fisher[param_name] = (
                    self.decay * self.accumulated_fisher[param_name] + (1 - self.decay) * F_new
                )
            else:
                self.accumulated_fisher[param_name] = F_new

            self.optimal_weights[param_name] = new_weights[param_name]

    def compute_penalty(
        self,
        current_weights: dict[str, np.ndarray],
    ) -> float:
        """
        计算惩罚项
        """
        penalty = 0.0

        for param_name in current_weights:
            if param_name not in self.optimal_weights:
                continue

            theta = current_weights[param_name]
            theta_old = self.optimal_weights[param_name]
            F = self.accumulated_fisher.get(param_name, np.zeros_like(theta))

            diff = theta - theta_old
            penalty += np.sum(F * (diff**2))

        return self.ewc_lambda * penalty

    def compute_gradients(
        self,
        current_weights: dict[str, np.ndarray],
    ) -> dict[str, np.ndarray]:
        """
        计算梯度
        """
        gradients = {}

        for param_name in current_weights:
            if param_name not in self.optimal_weights:
                continue

            theta = current_weights[param_name]
            theta_old = self.optimal_weights[param_name]
            F = self.accumulated_fisher.get(param_name, np.zeros_like(theta))

            gradients[param_name] = 2 * self.ewc_lambda * F * (theta - theta_old)

        return gradients


class EmpiricalFisher:
    """
    经验 Fisher 信息计算

    F ≈ (1/N) Σ (∂ log p(y|x,θ) / ∂θ)(∂ log p(y|x,θ) / ∂θ)^T

    使用梯度外积近似
    """

    def __init__(self):
        pass

    def compute(
        self,
        gradients: dict[str, np.ndarray],
        batch_size: int | None = None,
    ) -> dict[str, np.ndarray]:
        """
        计算经验 Fisher 信息

        Args:
            gradients: 梯度字典列表 or 单个梯度字典
            batch_size: 批次大小（用于归一化）

        Returns:
            Fisher 信息字典
        """
        if isinstance(gradients, dict):
            # 单个梯度，转换为列表
            gradients = [gradients]

        fisher: dict[str, np.ndarray] = {}
        n = len(gradients)

        for param_name in gradients[0].keys():
            # 收集所有梯度
            grads = np.array([g[param_name].flatten() for g in gradients])

            # 计算外积的平均
            # F = (1/N) * Σ g * g^T
            fisher[param_name] = np.mean(np.stack([g @ g.T for g in grads]), axis=0)

            # 对角近似
            fisher[param_name] = np.diag(np.diag(fisher[param_name]))

        return fisher

    def compute_from_loss_gradient(
        self,
        loss: float,
        weights: dict[str, np.ndarray],
        weight_grads: dict[str, np.ndarray],
    ) -> dict[str, np.ndarray]:
        """
        从损失梯度计算 Fisher 信息

        Args:
            loss: 损失值
            weights: 权重字典
            weight_grads: 权重梯度

        Returns:
            Fisher 信息字典
        """
        fisher = {}

        for param_name, grad in weight_grads.items():
            # 经验 Fisher：g * g^T
            fisher[param_name] = grad.flatten()[:, np.newaxis] @ grad.flatten()[np.newaxis, :]

            # 对角近似
            fisher[param_name] = np.diag(np.diag(fisher[param_name]))

        return fisher
