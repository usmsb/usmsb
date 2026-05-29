"""
条件独立性检验

CausalDiscoveryEngine 的核心组件

提供三种检验方法：
1. 条件互信息 (CMI) - 连续变量
2. 卡方检验 - 离散变量
3. G-test - 离散变量（更准确）

支持混合变量处理
"""

import math
from typing import Any

import numpy as np

# scipy import with fallback for compatibility issues
try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except Exception:
    SCIPY_AVAILABLE = False
    stats = None


def _gammainc_series(a: float, x: float, max_iter: int = 100, tol: float = 1e-10) -> float:
    """Series expansion for regularized incomplete gamma function P(a, x)"""
    # P(a, x) = (x^a * e^(-x) / gamma(a)) * sum_{n=0}^∞ x^n / (a*(a+1)*...*(a+n))
    if x == 0:
        return 0.0
    lg = math.lgamma(a)
    term = 1.0 / a
    total = term
    for n in range(1, max_iter):
        term *= x / (a + n)
        total += term
        if abs(term) < tol * abs(total):
            break
    return total * math.exp(-x + a * math.log(x) - lg)


def _gammainc_cf(a: float, x: float, max_iter: int = 100, tol: float = 1e-10) -> float:
    """Continued fraction for regularized incomplete gamma function Q(a, x) = 1 - P(a, x)"""
    # Uses the Gauss continued fraction
    from math import inf
    b = x + 1.0 - a
    c = 1.0 / 1e-30  # Avoid division by zero
    d = 1.0 / b
    h = d
    for i in range(1, max_iter):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < 1e-30:
            d = 1e-30
        c = b + an / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < tol:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def _gammainc(a: float, x: float) -> float:
    """Regularized incomplete gamma function P(a, x)"""
    if x < 0 or a <= 0:
        return 0.0
    if x == 0:
        return 0.0
    # Use series for small x, continued fraction for large x
    if x < a + 1:
        return _gammainc_series(a, x)
    else:
        return 1.0 - _gammainc_cf(a, x)


def _chi2_cdf_fallback(x: float, df: int) -> float:
    """Pure Python fallback chi2 CDF using math.gamma"""
    if x <= 0:
        return 0.0
    if df <= 0:
        return 1.0
    a = df / 2.0
    y = x / 2.0
    return _gammainc(a, y)


if not SCIPY_AVAILABLE:
    # Create a minimal stats-like object for fallback

    def _chi2_contingency_fallback(contingency: np.ndarray) -> tuple:
        """Fallback chi2 contingency test"""
        # Calculate chi2 statistic manually
        n_rows, n_cols = contingency.shape
        row_totals = contingency.sum(axis=1, keepdims=True)
        col_totals = contingency.sum(axis=0, keepdims=True)
        n_total = contingency.sum()

        if n_total == 0:
            return 0.0, 1.0, 0, np.zeros_like(contingency)

        expected = (row_totals * col_totals) / n_total

        chi2 = 0.0
        for i in range(n_rows):
            for j in range(n_cols):
                if expected[i, j] > 0:
                    chi2 += (contingency[i, j] - expected[i, j]) ** 2 / expected[i, j]

        df = (n_rows - 1) * (n_cols - 1)
        p_value = 1 - _chi2_cdf_fallback(chi2, max(df, 1))

        return chi2, p_value, df, expected

    class _Chi2:
        @staticmethod
        def cdf(x, df):
            return _chi2_cdf_fallback(x, df)

    class _Chi2Contingency:
        @staticmethod
        def chi2_contingency(contingency):
            return _chi2_contingency_fallback(contingency)

    stats = type('stats', (), {
        'chi2': _Chi2(),
    })()
    stats.chi2_contingency = lambda contingency: _chi2_contingency_fallback(contingency)


class ConditionalIndependenceTest:
    """
    条件独立性检验

    完整实现：
    1. 条件互信息 (CMI) - 连续变量
    2. 卡方检验 - 离散变量
    3. G-test - 离散变量
    4. 混合变量处理
    """

    def __init__(self, alpha: float = 0.05):
        """
        初始化

        Args:
            alpha: 显著性水平，p-value > alpha 认为条件独立
        """
        self.alpha = alpha

    def ci_test(
        self,
        x: np.ndarray,
        y: np.ndarray,
        z: np.ndarray | None = None,
        method: str = "cmi",
    ) -> tuple[float, float]:
        """
        执行条件独立性检验

        Args:
            x: 变量 X 的数据
            y: 变量 Y 的数据
            z: 条件集 Z（可选）
            method: 检验方法
                - "cmi": 条件互信息（连续变量）
                - "chi2": 卡方检验（离散变量）
                - "g": G-test（离散变量）

        Returns:
            (test_statistic, p_value)
            - test_statistic: 检验统计量（CMI 值或 chi2/G 值）
            - p_value: p 值
        """
        if method == "cmi":
            return self._cmi_test(x, y, z)
        elif method == "chi2":
            return self._chi2_test(x, y, z)
        elif method == "g":
            return self._g_test(x, y, z)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _cmi_test(
        self,
        x: np.ndarray,
        y: np.ndarray,
        z: np.ndarray | None = None,
    ) -> tuple[float, float]:
        """
        条件互信息 (CMI) 检验

        CMI(X, Y | Z) = Σ Σ Σ p(x,y,z) log [ p(x,y|z) / (p(x|z) * p(y|z)) ]

        对于连续变量，使用核密度估计或分箱估计

        Args:
            x: 变量 X
            y: 变量 Y
            z: 条件集 Z

        Returns:
            (cmi_value, p_value)
        """
        n = len(x)

        if z is None or len(z) == 0:
            # 无条件检验：使用互信息
            cmi = self._mutual_information(x, y)
            # 转换为一个近似 p-value（使用卡方分布近似）
            # 自由度估计为 1
            p_value = 1 - stats.chi2.cdf(2 * n * cmi, df=1)
            return cmi, max(p_value, 0.0)

        # 条件互信息
        cmi = self._conditional_mutual_information(x, y, z)

        # 使用渐近分布估计 p-value
        # CMI 的渐近分布约为 (1/2) * chi2
        df = self._estimate_df_cmi(x, y, z)
        p_value = 1 - stats.chi2.cdf(2 * n * cmi, df=max(df, 1))

        return cmi, max(p_value, 0.0)

    def _mutual_information(self, x: np.ndarray, y: np.ndarray, n_bins: int = 10) -> float:
        """
        计算互信息（使用分箱估计）

        MI(X, Y) = Σ Σ p(x,y) log [ p(x,y) / (p(x) * p(y)) ]
        """
        # 离散化
        x_disc = self._discretize(x, n_bins)
        y_disc = self._discretize(y, n_bins)

        # 计算联合分布和边缘分布
        pxy, px, py = self._compute_joint_marginal(x_disc, y_disc, n_bins)

        # 计算互信息
        mi = 0.0
        for i in range(n_bins):
            for j in range(n_bins):
                if pxy[i, j] > 0 and px[i] > 0 and py[j] > 0:
                    mi += pxy[i, j] * math.log(pxy[i, j] / (px[i] * py[j]))

        return max(mi, 0.0)

    def _conditional_mutual_information(
        self,
        x: np.ndarray,
        y: np.ndarray,
        z: np.ndarray,
        n_bins: int = 5,
    ) -> float:
        """
        计算条件互信息（使用分箱估计）

        CMI(X, Y | Z) = Σ_z p(z) * CMI(X, Y | Z=z)

        其中 CMI(X, Y | Z=z) = Σ_x Σ_y p(x,y|z) log [ p(x,y|z) / (p(x|z) * p(y|z)) ]
        """
        n = len(x)
        cmi = 0.0

        # 对 z 离散化
        z_disc = self._discretize(z, n_bins)

        # 对每个 z 值计算条件互信息
        for z_val in range(n_bins):
            mask = z_disc == z_val
            count = np.sum(mask)

            if count < 2:
                continue

            p_z = count / n

            # 计算条件分布
            x_z = x[mask]
            y_z = y[mask]

            # 对 x, y 离散化（在 z 层内）
            x_z_disc = self._discretize(x_z, n_bins)
            y_z_disc = self._discretize(y_z, n_bins)

            # 联合和边缘分布
            pxy_z, px_z, py_z = self._compute_joint_marginal(x_z_disc, y_z_disc, n_bins)

            # 计算该层内的条件互信息
            cmi_z = 0.0
            for i in range(n_bins):
                for j in range(n_bins):
                    if pxy_z[i, j] > 0 and px_z[i] > 0 and py_z[j] > 0:
                        cmi_z += pxy_z[i, j] * math.log(pxy_z[i, j] / (px_z[i] * py_z[j]))

            cmi += p_z * cmi_z

        return max(cmi, 0.0)

    def _chi2_test(
        self,
        x: np.ndarray,
        y: np.ndarray,
        z: np.ndarray | None = None,
        n_bins: int = 5,
    ) -> tuple[float, float]:
        """
        卡方检验（用于离散变量）

        检验 X 和 Y 在给定 Z 的条件下是否条件独立

        Args:
            x: 变量 X（离散）
            y: 变量 Y（离散）
            z: 条件集 Z（可选）
            n_bins: 分箱数

        Returns:
            (chi2_value, p_value)
        """
        # 离散化
        x_disc = self._discretize(x, n_bins)
        y_disc = self._discretize(y, n_bins)

        if z is None or len(z) == 0:
            # 无条件检验：创建列联表
            contingency = self._create_contingency_table(x_disc, y_disc, n_bins)
            chi2, p_value, _, _ = stats.chi2_contingency(contingency)
            return chi2, p_value

        # 条件检验：分层卡方检验
        z_disc = self._discretize(z, n_bins)
        total_chi2 = 0.0
        total_df = 0

        for z_val in range(n_bins):
            mask = z_disc == z_val
            count = np.sum(mask)

            if count < 2:
                continue

            # 该层的列联表
            contingency = self._create_contingency_table(
                x_disc[mask], y_disc[mask], n_bins
            )

            if contingency.size > 0:
                chi2, p, df, _ = stats.chi2_contingency(contingency)
                total_chi2 += chi2
                total_df += max(df, 1)

        # 合并 p-value（使用 meta-analysis 方法）
        if total_df > 0:
            p_value = 1 - stats.chi2.cdf(total_chi2, df=total_df)
        else:
            p_value = 1.0

        return total_chi2, max(p_value, 0.0)

    def _g_test(
        self,
        x: np.ndarray,
        y: np.ndarray,
        z: np.ndarray | None = None,
        n_bins: int = 5,
    ) -> tuple[float, float]:
        """
        G-test（似然比检验，用于离散变量）

        比卡方检验更准确，尤其对于小样本

        Args:
            x: 变量 X（离散）
            y: 变量 Y（离散）
            z: 条件集 Z（可选）
            n_bins: 分箱数

        Returns:
            (g_value, p_value)
        """
        x_disc = self._discretize(x, n_bins)
        y_disc = self._discretize(y, n_bins)

        if z is None or len(z) == 0:
            contingency = self._create_contingency_table(x_disc, y_disc, n_bins)
            g, p_value, _, _ = self._g_test_contingency(contingency)
            return g, p_value

        # 条件检验
        z_disc = self._discretize(z, n_bins)
        total_g = 0.0
        total_df = 0

        for z_val in range(n_bins):
            mask = z_disc == z_val
            count = np.sum(mask)

            if count < 2:
                continue

            contingency = self._create_contingency_table(
                x_disc[mask], y_disc[mask], n_bins
            )

            if contingency.size > 0:
                g, _, df, _ = self._g_test_contingency(contingency)
                total_g += g
                total_df += max(df, 1)

        if total_df > 0:
            p_value = 1 - stats.chi2.cdf(total_g, df=total_df)
        else:
            p_value = 1.0

        return total_g, max(p_value, 0.0)

    def _g_test_contingency(
        self, contingency: np.ndarray
    ) -> tuple[float, float, int, np.ndarray]:
        """
        对列联表执行 G-test

        G = 2 * Σ [ O * log(O / E) ]

        其中 O 是观察值，E 是期望值
        """
        # 计算期望值
        row_totals = contingency.sum(axis=1, keepdims=True)
        col_totals = contingency.sum(axis=0, keepdims=True)
        n = contingency.sum()

        if n == 0:
            return 0.0, 1.0, 0, np.zeros_like(contingency)

        expected = (row_totals * col_totals) / n

        # 计算 G 统计量
        g = 0.0
        for i in range(contingency.shape[0]):
            for j in range(contingency.shape[1]):
                if contingency[i, j] > 0 and expected[i, j] > 0:
                    g += 2 * contingency[i, j] * math.log(
                        contingency[i, j] / expected[i, j]
                    )

        # 自由度
        df = (contingency.shape[0] - 1) * (contingency.shape[1] - 1)

        # p-value
        p_value = 1 - stats.chi2.cdf(g, df=max(df, 1))

        return g, p_value, df, expected

    def _discretize(self, x: np.ndarray, n_bins: int) -> np.ndarray:
        """
        将连续变量离散化（分箱）

        Args:
            x: 连续变量
            n_bins: 分箱数

        Returns:
            离散化后的数组
        """
        # 使用分位数分箱，保持每个箱大约有相同数量的样本
        try:
            quantiles = np.percentile(x, np.linspace(0, 100, n_bins + 1))
            # 处理重复的分位数
            quantiles = np.unique(quantiles)
            if len(quantiles) < 2:
                quantiles = np.array([x.min() - 1, x.max() + 1])
            bins = np.digitize(x, quantiles[1:-1], right=True)
            return bins
        except Exception:
            # 降级为均匀分箱
            bins = np.zeros(len(x), dtype=int)
            step = (x.max() - x.min()) / n_bins
            for i in range(n_bins):
                mask = (x >= x.min() + i * step) & (x < x.min() + (i + 1) * step)
                bins[mask] = i
            # 最后一个箱子包含最大值
            bins[x == x.max()] = n_bins - 1
            return bins

    def _create_contingency_table(
        self, x: np.ndarray, y: np.ndarray, n_bins: int
    ) -> np.ndarray:
        """
        创建列联表

        Returns:
            contingency[i, j] = count of (x=i, y=j)
        """
        contingency = np.zeros((n_bins, n_bins), dtype=float)
        for i in range(len(x)):
            xi = min(int(x[i]), n_bins - 1)
            yi = min(int(y[i]), n_bins - 1)
            contingency[xi, yi] += 1
        return contingency

    def _compute_joint_marginal(
        self, x: np.ndarray, y: np.ndarray, n_bins: int
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        计算联合分布和边缘分布

        Returns:
            (pxy, px, py)
        """
        n = len(x)
        pxy = np.zeros((n_bins, n_bins))
        px = np.zeros(n_bins)
        py = np.zeros(n_bins)

        for i in range(len(x)):
            xi = min(int(x[i]), n_bins - 1)
            yi = min(int(y[i]), n_bins - 1)
            pxy[xi, yi] += 1
            px[xi] += 1
            py[yi] += 1

        pxy /= n
        px /= n
        py /= n

        return pxy, px, py

    def _estimate_df_cmi(
        self, x: np.ndarray, y: np.ndarray, z: np.ndarray
    ) -> int:
        """
        估计 CMI 检验的自由度

        这是一个近似估计
        """
        n_bins = 5
        z_unique = len(np.unique(z))
        x_unique = min(len(np.unique(x)), n_bins)
        y_unique = min(len(np.unique(y)), n_bins)

        # 自由度约为 (|Z| - 1) * (|X| - 1) * (|Y| - 1)
        df = (z_unique - 1) * (x_unique - 1) * (y_unique - 1)

        return max(df, 1)

    def is_independent(self, x: np.ndarray, y: np.ndarray, z: np.ndarray | None = None) -> bool:
        """
        判断 X 和 Y 是否条件独立

        Args:
            x: 变量 X
            y: 变量 Y
            z: 条件集 Z

        Returns:
            True 如果条件独立（p_value > alpha）
        """
        _, p_value = self.ci_test(x, y, z, method="cmi")
        return p_value > self.alpha


class CITestResult:
    """条件独立性检验结果"""

    def __init__(
        self,
        variable_x: str,
        variable_y: str,
        conditioning_set: tuple[str, ...],
        test_statistic: float,
        p_value: float,
        sample_size: int,
        is_independent: bool,
    ):
        self.variable_x = variable_x
        self.variable_y = variable_y
        self.conditioning_set = conditioning_set
        self.test_statistic = test_statistic
        self.p_value = p_value
        self.sample_size = sample_size
        self.is_independent = is_independent

    def to_dict(self) -> dict[str, Any]:
        return {
            "variable_x": self.variable_x,
            "variable_y": self.variable_y,
            "conditioning_set": list(self.conditioning_set),
            "test_statistic": self.test_statistic,
            "p_value": self.p_value,
            "sample_size": self.sample_size,
            "is_independent": self.is_independent,
        }
