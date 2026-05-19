"""
ReasoningEnhancer

推理增强器

整合结构化输出、多路径检查、反例修正

核心定位：
- 不是「增强 LLM 的推理能力」
- 而是「让推理过程更可见、更可控」
"""

import logging
from dataclasses import dataclass
from typing import Any

from .structured_output import (
    ReasoningParser,
    ReasoningTrace,
    ReasoningConsistencyChecker,
    REASONING_TEMPLATE,
)
from .multi_path_check import MultiPathConsistencyChecker, SelfConsistencyChecker
from .counterexample import CounterexampleDrivenCorrector


logger = logging.getLogger(__name__)


@dataclass
class ReasoningResult:
    """推理结果"""
    conclusion: str
    trace: ReasoningTrace
    confidence: float
    issues: list[str]
    used_multi_path: bool = False
    corrections_applied: int = 0


class ReasoningEnhancer:
    """
    推理增强器

    整合所有推理增强功能
    """

    def __init__(
        self,
        llm_manager=None,
        enable_multi_path: bool = True,
        enable_counterexample: bool = True,
        enable_consistency_check: bool = True,
        n_paths: int = 3,
        consistency_threshold: float = 0.6,
    ):
        """
        初始化

        Args:
            llm_manager: LLM 管理器
            enable_multi_path: 启用多路径检查
            enable_counterexample: 启用反例驱动修正
            enable_consistency_check: 启用一致性检查
            n_paths: 推理路径数量
            consistency_threshold: 一致性阈值
        """
        self.llm = llm_manager
        self.enable_multi_path = enable_multi_path
        self.enable_counterexample = enable_counterexample
        self.enable_consistency_check = enable_consistency_check

        # 组件
        self.parser = ReasoningParser()
        self.consistency_checker = ReasoningConsistencyChecker()
        self.multi_path_checker = MultiPathConsistencyChecker(
            llm_manager, n_paths, consistency_threshold
        )
        self.counterexample_corrector = CounterexampleDrivenCorrector(llm_manager)

        self.n_paths = n_paths
        self.consistency_threshold = consistency_threshold

    async def reason(
        self,
        task: Any,
        context: Any,
        generate_fn=None,
    ) -> ReasoningResult:
        """
        增强推理

        步骤：
        1. 生成结构化推理
        2. 解析推理步骤
        3. 检查步骤一致性
        4. 反例检查
        5. 多路径验证（仅对关键决策）
        6. 返回增强后的推理

        Args:
            task: 任务
            context: 上下文
            generate_fn: 生成推理的函数

        Returns:
            增强后的推理结果
        """
        corrections_applied = 0
        issues = []

        # 1. 生成结构化推理
        if generate_fn:
            response = await generate_fn(task, context, REASONING_TEMPLATE)
        else:
            response = await self._default_generate(task, context)

        # 2. 解析推理步骤
        trace = self.parser.parse(response)

        if trace is None:
            return ReasoningResult(
                conclusion=response[:200] if len(response) > 200 else response,
                trace=None,
                confidence=0.0,
                issues=["解析失败"],
                corrections_applied=0,
            )

        # 3. 检查步骤一致性
        if self.enable_consistency_check:
            consistency = self.consistency_checker.check_consistency(trace)
            issues.extend(consistency.issues)

            if not consistency.is_consistent:
                logger.warning(f"推理一致性检查发现问题: {consistency.issues}")

        # 4. 反例检查
        if self.enable_counterexample and trace.steps:
            counterexamples = await self._check_counterexamples(trace.steps[-1])
            if counterexamples:
                # 触发修正
                if generate_fn:
                    response = await self.counterexample_corrector.trigger_correction(
                        {"conclusion": trace.final_conclusion, "trace": response},
                        counterexamples,
                        generate_fn,
                    )
                    corrections_applied += 1
                    logger.info("应用了反例驱动修正")

        # 5. 多路径验证（仅对关键决策）
        used_multi_path = False
        if self.enable_multi_path and generate_fn:
            multi_result = await self.multi_path_checker.verify(
                task, context, generate_fn
            )

            used_multi_path = True

            if not multi_result.consistent:
                issues.append(f"多路径不一致: score={multi_result.score:.2f}")
                logger.warning(
                    f"推理分歧检测: score={multi_result.score:.2f}, "
                    f"divergent_steps={multi_result.divergent_steps}"
                )

            # 如果多路径验证给出一致结论，使用它
            if multi_result.consistent:
                trace.final_conclusion = multi_result.dominant_conclusion

        # 计算总体置信度
        confidence = trace.overall_confidence
        if issues:
            confidence = max(0.0, confidence - len(issues) * 0.1)

        return ReasoningResult(
            conclusion=trace.final_conclusion,
            trace=trace,
            confidence=confidence,
            issues=issues,
            used_multi_path=used_multi_path,
            corrections_applied=corrections_applied,
        )

    async def _check_counterexamples(self, step) -> list:
        """检查反例"""
        try:
            counterexamples = await self.counterexample_corrector.generate_counterexamples(
                {"reasoning": step.output}
            )

            # 过滤不合理的反例
            valid = []
            for ce in counterexamples:
                if self.counterexample_corrector.is_reasonable_counterexample(
                    ce, {"reasoning": step.output}
                ):
                    valid.append(ce)

            return valid
        except Exception as e:
            logger.error(f"反例检查失败: {e}")
            return []

    async def _default_generate(self, task: Any, context: Any) -> str:
        """默认生成函数"""
        if self.llm:
            prompt = f"""
            任务：{task}

            上下文：{context}

            {REASONING_TEMPLATE}
            """
            return await self.llm.generate(prompt)

        return "无法生成推理（没有 LLM 管理器）"

    def get_reasoning_prompt(self) -> str:
        """获取推理 prompt 模板"""
        return REASONING_TEMPLATE


class LightweightReasoningEnhancer:
    """
    轻量级推理增强器

    不依赖 LLM，仅做解析和验证
    """

    def __init__(
        self,
        enable_consistency_check: bool = True,
        consistency_threshold: float = 0.6,
    ):
        self.parser = ReasoningParser()
        self.consistency_checker = ReasoningConsistencyChecker()
        self.self_consistency = SelfConsistencyChecker(consistency_threshold)

    def enhance(self, llm_output: str) -> ReasoningResult:
        """
        增强推理（同步）

        Args:
            llm_output: LLM 输出

        Returns:
            增强后的推理结果
        """
        # 解析
        trace = self.parser.parse(llm_output)

        if trace is None:
            return ReasoningResult(
                conclusion=llm_output[:200] if len(llm_output) > 200 else llm_output,
                trace=None,
                confidence=0.0,
                issues=["解析失败"],
            )

        # 一致性检查
        issues = []
        if self.consistency_checker:
            consistency = self.consistency_checker.check_consistency(trace)
            issues.extend(consistency.issues)

        confidence = trace.overall_confidence
        if issues:
            confidence = max(0.0, confidence - len(issues) * 0.1)

        return ReasoningResult(
            conclusion=trace.final_conclusion,
            trace=trace,
            confidence=confidence,
            issues=issues,
        )

    def check_multi_trace_consistency(
        self,
        traces: list[ReasoningTrace],
    ):
        """
        检查多条推理的一致性

        Args:
            traces: 推理轨迹列表

        Returns:
            多路径检查结果
        """
        return self.self_consistency.check(traces)
