"""
因果强度估计器

PC Algorithm 的最后一步

估计每条因果边的因果效应大小和置信度
"""

from typing import Any

import numpy as np


class StrengthEstimator:
    """
    因果强度估计器

    估计每条因果边的：
    1. 因果效应大小（strength）：-1.0 ~ 1.0
       - 正值：X 增加导致 Y 增加
       - 负值：X 增加导致 Y 减少
       - 绝对值越大，因果效应越强

    2. 置信度（confidence）：0.0 ~ 1.0
       - 基于样本量和边的稳定性
    """

    def __init__(
        self,
        min_causal_strength: float = 0.1,
        min_confidence: float = 0.5,
    ):
        """
        初始化

        Args:
            min_causal_strength: 最小因果强度阈值
            min_confidence: 最小置信度阈值
        """
        self.min_causal_strength = min_causal_strength
        self.min_confidence = min_confidence

    def estimate_strengths(
        self,
        variables: list[str],
        data: dict[str, np.ndarray],
        directed_edges: list[tuple[str, str]],
        sep_sets: dict[tuple[str, str], frozenset[str]],
    ) -> dict[tuple[str, str], dict[str, float]]:
        """
        估计所有因果边的强度

        Args:
            variables: 变量名列表
            data: 变量名 -> 数据数组 的字典
            directed_edges: 已定向边列表 [(from, to), ...]
            sep_sets: separator sets

        Returns:
            {
                (from, to): {
                    "strength": float,
                    "confidence": float,
                    "n_samples": int,
                    "method": str,
                }
            }
        """
        results = {}

        for x, y in directed_edges:
            # 获取 x 和 y 的数据
            x_data = data[x]
            y_data = data[y]

            # 获取 separator set
            sep = sep_sets.get((x, y), frozenset())
            sep_data = {z: data[z] for z in sep} if sep else {}

            # 估计因果效应
            strength_result = self._estimate_causal_effect(
                x_data, y_data, sep_data
            )

            # 计算置信度
            confidence = self._estimate_confidence(
                x_data, y_data, sep_data, strength_result["effect"]
            )

            results[(x, y)] = {
                "strength": strength_result["effect"],
                "confidence": confidence,
                "n_samples": len(x_data),
                "method": strength_result["method"],
                "p_value": strength_result.get("p_value", 1.0),
            }

        return results

    def _estimate_causal_effect(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        z_data: dict[str, np.ndarray],
    ) -> dict[str, Any]:
        """
        估计因果效应

        使用 backdoor adjustment 或简单线性回归

        P(Y | do(X)) = Σ_z P(Y | X, Z=z) * P(Z=z)

        Args:
            x_data: X 的数据
            y_data: Y 的数据
            z_data: 条件集 Z 的数据

        Returns:
            {
                "effect": float,  # 因果效应
                "method": str,
                "p_value": float (如果有)
            }
        """
        n = len(x_data)

        if not z_data:
            # 无条件集，使用简单线性回归
            return self._linear_regression(x_data, y_data)

        # 有条件集，使用 backdoor adjustment
        # 首先检查数据量是否足够
        if n < 30:
            # 样本太少，使用简单回归
            return self._linear_regression(x_data, y_data)

        return self._backdoor_adjustment(x_data, y_data, z_data)

    def _linear_regression(
        self, x_data: np.ndarray, y_data: np.ndarray
    ) -> dict[str, Any]:
        """
        简单线性回归估计因果效应

        Y = α + β * X + ε

        β 就是因果效应的估计
        """
        n = len(x_data)

        # 标准化
        x_mean = np.mean(x_data)
        y_mean = np.mean(y_data)
        x_std = np.std(x_data)
        y_std = np.std(y_data)

        if x_std == 0 or y_std == 0:
            return {"effect": 0.0, "method": "linear_regression", "p_value": 1.0}

        # 计算相关系数
        x_norm = (x_data - x_mean) / x_std
        y_norm = (y_data - y_mean) / y_std

        correlation = np.mean(x_norm * y_norm)

        # 使用 Pearl 的方法：因果效应 = correlation * (std_y / std_x)
        # 但这里我们直接用标准化后的系数
        effect = correlation

        # 计算 p-value（使用 t-test）
        t_stat = correlation * np.sqrt(n - 2) / np.sqrt(1 - correlation**2)
        from scipy import stats
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))

        return {
            "effect": effect,
            "method": "linear_regression",
            "p_value": p_value,
        }

    def _backdoor_adjustment(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        z_data: dict[str, np.ndarray],
    ) -> dict[str, Any]:
        """
        使用 backdoor adjustment 估计因果效应

        P(Y | do(X)) = Σ_z P(Y | X, Z=z) * P(Z=z)

        对于连续变量，使用回归方法：
        E[Y | do(X)] = α + β * X + Σ γ_z * Z

        其中 β 是因果效应
        """
        from scipy import stats

        n = len(x_data)

        # 构建回归矩阵
        # Y = α + β * X + Σ γ_z * Z + ε
        k = len(z_data)
        X_mat = np.column_stack([np.ones(n), x_data] + [z_data[z] for z in z_data])

        try:
            # 最小二乘估计
            coeffs, residuals, rank, s = np.linalg.lstsq(X_mat, y_data, rcond=None)

            beta = coeffs[1]  # X 的系数

            # 计算 R² 用于置信度
            y_pred = X_mat @ coeffs
            ss_res = np.sum((y_data - y_pred) ** 2)
            ss_tot = np.sum((y_data - np.mean(y_data)) ** 2)
            r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

            # 调整效应方向
            # 如果 X 和 Y 负相关，效应为负
            x_y_corr = np.corrcoef(x_data, y_data)[0, 1]
            if x_y_corr < 0:
                beta = -beta

            return {
                "effect": beta,
                "method": "backdoor_adjustment",
                "r_squared": r_squared,
            }

        except Exception:
            # 回退到简单回归
            return self._linear_regression(x_data, y_data)

    def _estimate_confidence(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        z_data: dict[str, np.ndarray],
        effect: float,
    ) -> float:
        """
        估计因果效应的置信度

        置信度取决于：
        1. 样本量
        2. 效应的稳定性
        3. 与其他估计的一致性
        """
        n = len(x_data)

        # 样本量因子（越大越好）
        if n < 30:
            sample_factor = 0.5
        elif n < 100:
            sample_factor = 0.7
        elif n < 300:
            sample_factor = 0.85
        else:
            sample_factor = 1.0

        # 效应大小因子（绝对值越大越可靠）
        effect_magnitude = min(abs(effect), 1.0)
        magnitude_factor = 0.5 + 0.5 * effect_magnitude

        # 条件集大小因子（条件集越大，置信度越低）
        if not z_data:
            cond_factor = 1.0
        else:
            cond_factor = max(0.5, 1.0 - 0.1 * len(z_data))

        # 综合置信度
        confidence = sample_factor * magnitude_factor * cond_factor

        # 归一化到 [0.5, 1.0] 范围
        confidence = 0.5 + 0.5 * confidence

        return min(max(confidence, 0.0), 1.0)

    def filter_edges(
        self,
        edge_strengths: dict[tuple[str, str], dict[str, float]],
    ) -> list[tuple[str, str]]:
        """
        过滤低强度边

        Args:
            edge_strengths: 边强度字典

        Returns:
            保留的边列表
        """
        filtered = []

        for edge, info in edge_strengths.items():
            strength = info["strength"]
            confidence = info["confidence"]

            # 检查阈值
            if abs(strength) < self.min_causal_strength:
                continue
            if confidence < self.min_confidence:
                continue

            filtered.append(edge)

        return filtered


class RobustStrengthEstimator(StrengthEstimator):
    """
    鲁棒的因果强度估计器

    使用多种方法估计，选择最可靠的
    """

    def __init__(
        self,
        min_causal_strength: float = 0.1,
        min_confidence: float = 0.5,
    ):
        super().__init__(min_causal_strength, min_confidence)

    def estimate_strengths_robust(
        self,
        variables: list[str],
        data: dict[str, np.ndarray],
        directed_edges: list[tuple[str, str]],
        sep_sets: dict[tuple[str, str], frozenset[str]],
    ) -> dict[tuple[str, str], dict[str, Any]]:
        """
        鲁棒估计因果强度

        使用多种方法并综合结果
        """
        results = {}

        for x, y in directed_edges:
            x_data = data[x]
            y_data = data[y]
            sep = sep_sets.get((x, y), frozenset())
            sep_data = {z: data[z] for z in sep} if sep else {}

            # 方法1：线性回归
            result1 = self._linear_regression(x_data, y_data)

            # 方法2：如果有条件集，backdoor adjustment
            result2 = None
            if sep_data:
                result2 = self._backdoor_adjustment(x_data, y_data, sep_data)

            # 综合结果
            effects = [result1["effect"]]
            if result2:
                effects.append(result2["effect"])

            # 使用中位数（更鲁棒）
            effect = np.median(effects)

            # 置信度：使用结果的一致性
            if len(effects) > 1:
                effect_std = np.std(effects)
                consistency = max(0, 1 - effect_std)
            else:
                consistency = 1.0

            confidence = self._estimate_confidence(
                x_data, y_data, sep_data, effect
            )
            confidence *= consistency

            results[(x, y)] = {
                "strength": effect,
                "confidence": confidence,
                "n_samples": len(x_data),
                "method": "robust_ensemble",
                "individual_estimates": effects,
            }

        return results
