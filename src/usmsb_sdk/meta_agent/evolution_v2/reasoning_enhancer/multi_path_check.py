"""
多路径一致性检查

ReasoningEnhancer 的组件

基于 Self-Consistency 思想
用多条推理路径的一致性来验证
"""

from collections import Counter
from dataclasses import dataclass
from typing import Any

from .structured_output import ReasoningTrace, ReasoningStep


@dataclass
class MultiPathResult:
    """多路径检查结果"""
    consistent: bool
    score: float  # 一致性分数
    dominant_conclusion: str
    divergent_steps: list[str]
    paths: list[dict[str, Any]]


class MultiPathConsistencyChecker:
    """
    多路径一致性检查器

    Self-Consistency 完整实现

    1. 生成 N 条不同推理路径
    2. 统计结论分布
    3. 一致性分数 = 最常见结论数 / 总路径数
    4. 如果一致性 < 阈值，分析分歧原因
    """

    def __init__(
        self,
        llm_manager=None,
        n_paths: int = 3,
        consistency_threshold: float = 0.6,
    ):
        """
        初始化

        Args:
            llm_manager: LLM 管理器
            n_paths: 推理路径数量（成本考虑，默认 3）
            consistency_threshold: 一致性阈值
        """
        self.llm = llm_manager
        self.n_paths = n_paths
        self.consistency_threshold = consistency_threshold

    async def verify(
        self,
        task: Any,
        context: Any,
        generate_path_fn,  # 生成单条路径的函数
    ) -> MultiPathResult:
        """
        验证推理一致性

        Args:
            task: 任务
            context: 上下文
            generate_path_fn: 生成单条路径的异步函数

        Returns:
            多路径检查结果
        """
        # 生成多条路径
        paths = []
        for _ in range(self.n_paths):
            path = await generate_path_fn(task, context)
            if path:
                paths.append(path)

        if not paths:
            return MultiPathResult(
                consistent=False,
                score=0.0,
                dominant_conclusion="",
                divergent_steps=[],
                paths=[],
            )

        # 提取结论
        conclusions = [p.get("conclusion", "") for p in paths]
        conclusion_counts = Counter(conclusions)

        # 统计结论分布
        most_common = conclusion_counts.most_common(1)[0]
        consistency_score = most_common[1] / len(paths)

        dominant_conclusion = most_common[0]

        # 分析分歧
        divergent_steps = []
        if consistency_score < self.consistency_threshold:
            divergent_steps = self._analyze_divergence(paths)

        return MultiPathResult(
            consistent=consistency_score >= self.consistency_threshold,
            score=consistency_score,
            dominant_conclusion=dominant_conclusion,
            divergent_steps=divergent_steps,
            paths=paths,
        )

    def _analyze_divergence(
        self,
        paths: list[dict[str, Any]],
    ) -> list[str]:
        """
        分析分歧原因

        Args:
            paths: 推理路径列表

        Returns:
            分歧描述列表
        """
        divergent_steps = []

        # 找出分歧最大的几步推理
        for i in range(len(paths[0].get("steps", []))):
            step_confidences = []
            step_outputs = []

            for path in paths:
                steps = path.get("steps", [])
                if i < len(steps):
                    step_confidences.append(steps[i].get("confidence", 0.5))
                    step_outputs.append(steps[i].get("output", ""))

            # 检查置信度方差
            if len(step_confidences) > 1:
                import numpy as np
                confidence_std = np.std(step_confidences)

                if confidence_std > 0.2:
                    divergent_steps.append(
                        f"步骤 {i+1} 置信度差异大: std={confidence_std:.3f}"
                    )

            # 检查输出差异
            if len(set(step_outputs)) > 1:
                divergent_steps.append(
                    f"步骤 {i+1} 输出不一致"
                )

        return divergent_steps

    def select_dominant_path(
        self,
        paths: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        选择主导路径

        选择置信度最高的路径

        Args:
            paths: 推理路径列表

        Returns:
            主导路径
        """
        if not paths:
            return {}

        # 计算每条路径的平均置信度
        path_scores = []
        for path in paths:
            steps = path.get("steps", [])
            if steps:
                avg_confidence = sum(s.get("confidence", 0.5) for s in steps) / len(steps)
            else:
                avg_confidence = 0.5
            path_scores.append((avg_confidence, path))

        # 选择置信度最高的
        path_scores.sort(key=lambda x: x[0], reverse=True)
        return path_scores[0][1]


class SelfConsistencyChecker:
    """
    Self-Consistency 检查器

    简化版本，不依赖 LLM 生成多路径
    直接分析已有推理
    """

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold

    def check(
        self,
        reasoning_traces: list[ReasoningTrace],
    ) -> MultiPathResult:
        """
        检查一致性

        Args:
            reasoning_traces: 推理轨迹列表

        Returns:
            多路径检查结果
        """
        if not reasoning_traces:
            return MultiPathResult(
                consistent=False,
                score=0.0,
                dominant_conclusion="",
                divergent_steps=[],
                paths=[],
            )

        # 提取结论
        conclusions = [t.final_conclusion for t in reasoning_traces]
        conclusion_counts = Counter(conclusions)

        most_common = conclusion_counts.most_common(1)[0]
        consistency_score = most_common[1] / len(reasoning_traces)

        # 分析分歧步骤
        divergent_steps = self._analyze_divergence(reasoning_traces)

        return MultiPathResult(
            consistent=consistency_score >= self.threshold,
            score=consistency_score,
            dominant_conclusion=most_common[0],
            divergent_steps=divergent_steps,
            paths=[],
        )

    def _analyze_divergence(
        self,
        traces: list[ReasoningTrace],
    ) -> list[str]:
        """分析分歧"""
        divergent_steps = []

        if not traces or not traces[0].steps:
            return divergent_steps

        max_steps = max(len(t.steps) for t in traces)

        for i in range(max_steps):
            # 获取所有轨迹在这一步的置信度
            confidences = []
            for trace in traces:
                if i < len(trace.steps):
                    confidences.append(trace.steps[i].confidence)

            if len(confidences) > 1:
                import numpy as np
                std = np.std(confidences)

                if std > 0.2:
                    divergent_steps.append(
                        f"步骤 {i+1} 置信度不一致: std={std:.3f}"
                    )

        return divergent_steps
