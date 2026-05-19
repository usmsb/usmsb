"""
结构化推理输出

ReasoningEnhancer 的组件

强制 CoT 格式，解析和验证推理步骤
"""

import re
from dataclasses import dataclass
from typing import Any


# 强制 CoT 的 prompt 模板
REASONING_TEMPLATE = """
你必须按以下格式输出推理过程：

## 推理步骤 1
**输入**: [这一步的输入]
**规则**: [使用的推理规则]
**输出**: [这一步的输出]
**置信度**: [0-1 之间，标注依据]
**自检**: [这一步有没有矛盾或不确定的地方？]

## 推理步骤 2
...

## 反例检查
**可能的反例**: [有没有能推翻结论的例子？]
**结论是否能承受这些反例**: [能/不能，原因]

## 最终结论
**结论**: [最终结论]
**置信度**: [整体置信度，0-1]
**风险**: [可能的风险点]
**如果结论错了，可能的原因**: [列点]
"""


@dataclass
class ReasoningStep:
    """推理步骤"""
    step_id: int
    inputs: list[str]
    rule: str
    output: str
    confidence: float
    self_check: str
    has_uncertainty: bool = False


@dataclass
class ReasoningTrace:
    """推理轨迹"""
    steps: list[ReasoningStep]
    counterexamples: list[str]
    final_conclusion: str
    overall_confidence: float
    risks: list[str]
    possible_failures: list[str]


class ReasoningParser:
    """
    解析 LLM 输出的推理步骤
    检查步骤间的逻辑一致性
    """

    def __init__(self):
        self.step_pattern = re.compile(
            r"## 推理步骤\s*(\d+)"
            r"(.*?)"
            r"(?=##\s*推理步骤\s*\d+|##\s*反例检查|##\s*最终结论|$)",
            re.DOTALL | re.IGNORECASE,
        )

        self.field_patterns = {
            "input": re.compile(r"\*\*输入\*\*:\s*(.+?)(?=\n\*\*|\n##|$)", re.DOTALL),
            "rule": re.compile(r"\*\*规则\*\*:\s*(.+?)(?=\n\*\*|\n##|$)", re.DOTALL),
            "output": re.compile(r"\*\*输出\*\*:\s*(.+?)(?=\n\*\*|\n##|$)", re.DOTALL),
            "confidence": re.compile(r"\*\*置信度\*\*:\s*([0-9.]+)", re.DOTALL),
            "self_check": re.compile(r"\*\*自检\*\*:\s*(.+?)(?=\n\*\*|\n##|$)", re.DOTALL),
        }

        self.counterexample_pattern = re.compile(
            r"##\s*反例检查.*?\*\*可能的反例\*\*:\s*(.+?)(?=\n\*\*|##\s*最终结论|$)",
            re.DOTALL | re.IGNORECASE,
        )

        self.conclusion_patterns = {
            "conclusion": re.compile(r"\*\*结论\*\*:\s*(.+?)(?=\n\*\*|$$)", re.DOTALL),
            "confidence": re.compile(r"\*\*置信度\*\*:\s*([0-9.]+)", re.DOTALL),
            "risks": re.compile(r"\*\*风险\*\*:\s*(.+?)(?=\n\*\*|$$)", re.DOTALL),
            "failures": re.compile(r"\*\*如果结论错了.*?\*\*:\s*(.+?)(?=\n\*\*|$$)", re.DOTALL),
        }

    def parse(self, llm_output: str) -> ReasoningTrace | None:
        """
        解析 LLM 输出

        Args:
            llm_output: LLM 原始输出

        Returns:
            ReasoningTrace 对象，如果解析失败返回 None
        """
        try:
            steps = self._parse_steps(llm_output)
            counterexamples = self._parse_counterexamples(llm_output)
            conclusion = self._parse_conclusion(llm_output)

            return ReasoningTrace(
                steps=steps,
                counterexamples=counterexamples,
                final_conclusion=conclusion["conclusion"],
                overall_confidence=conclusion["confidence"],
                risks=conclusion["risks"],
                possible_failures=conclusion["failures"],
            )
        except Exception:
            return None

    def _parse_steps(self, text: str) -> list[ReasoningStep]:
        """解析推理步骤"""
        steps = []

        matches = self.step_pattern.findall(text)

        for step_id, content in matches:
            step_id = int(step_id.strip())

            inputs = []
            rule = ""
            output = ""
            confidence = 0.5
            self_check = ""
            has_uncertainty = False

            # 解析各个字段
            input_match = self.field_patterns["input"].search(content)
            if input_match:
                inputs = [x.strip() for x in input_match.group(1).split("\n") if x.strip()]

            rule_match = self.field_patterns["rule"].search(content)
            if rule_match:
                rule = rule_match.group(1).strip()

            output_match = self.field_patterns["output"].search(content)
            if output_match:
                output = output_match.group(1).strip()

            confidence_match = self.field_patterns["confidence"].search(content)
            if confidence_match:
                confidence = float(confidence_match.group(1))

            self_check_match = self.field_patterns["self_check"].search(content)
            if self_check_match:
                self_check = self_check_match.group(1).strip()
                has_uncertainty = "不确定" in self_check or "矛盾" in self_check

            steps.append(ReasoningStep(
                step_id=step_id,
                inputs=inputs,
                rule=rule,
                output=output,
                confidence=confidence,
                self_check=self_check,
                has_uncertainty=has_uncertainty,
            ))

        return steps

    def _parse_counterexamples(self, text: str) -> list[str]:
        """解析反例"""
        match = self.counterexample_pattern.search(text)
        if not match:
            return []

        content = match.group(1)
        # 按行分割
        counterexamples = [
            x.strip() for x in content.split("\n")
            if x.strip() and not x.strip().startswith("**")
        ]

        return counterexamples

    def _parse_conclusion(self, text: str) -> dict[str, Any]:
        """解析最终结论"""
        # 找到最终结论部分
        conclusion_match = re.search(
            r"##\s*最终结论(.*?)$",
            text,
            re.DOTALL | re.IGNORECASE,
        )

        if not conclusion_match:
            return {
                "conclusion": "",
                "confidence": 0.5,
                "risks": [],
                "failures": [],
            }

        content = conclusion_match.group(1)

        result = {
            "conclusion": "",
            "confidence": 0.5,
            "risks": [],
            "failures": [],
        }

        conclusion_match = self.conclusion_patterns["conclusion"].search(content)
        if conclusion_match:
            result["conclusion"] = conclusion_match.group(1).strip()

        confidence_match = self.conclusion_patterns["confidence"].search(content)
        if confidence_match:
            result["confidence"] = float(confidence_match.group(1))

        risks_match = self.conclusion_patterns["risks"].search(content)
        if risks_match:
            risks_text = risks_match.group(1).strip()
            result["risks"] = [x.strip() for x in risks_text.split("\n") if x.strip()]

        failures_match = self.conclusion_patterns["failures"].search(content)
        if failures_match:
            failures_text = failures_match.group(1).strip()
            result["failures"] = [x.strip() for x in failures_text.split("\n") if x.strip()]

        return result


@dataclass
class ConsistencyResult:
    """一致性检查结果"""
    is_consistent: bool
    confidence: float
    issues: list[str]


class ReasoningConsistencyChecker:
    """
    检查推理步骤的一致性
    """

    def check_consistency(self, trace: ReasoningTrace) -> ConsistencyResult:
        """
        检查推理步骤的一致性

        Args:
            trace: 推理轨迹

        Returns:
            一致性检查结果
        """
        issues = []

        # 1. 步骤间依赖检查
        for i, step in enumerate(trace.steps):
            for inp in step.inputs:
                if not self._has_produced(inp, trace.steps[:i]):
                    issues.append(
                        f"步骤 {step.step_id} 依赖 「{inp}」，但之前没有产生"
                    )

        # 2. 置信度合理性检查
        for step in trace.steps:
            if step.confidence > 0.9 and step.has_uncertainty:
                issues.append(
                    f"步骤 {step.step_id} 声称高置信度，但有明显不确定性"
                )

        # 3. 结论与步骤一致性检查
        if trace.steps:
            last_step = trace.steps[-1]
            if last_step.output and trace.final_conclusion:
                # 简化的检查：结论应该与最后一步输出相关
                if last_step.output not in trace.final_conclusion:
                    # 可能是一致性问题，但不一定
                    pass

        # 计算总体置信度
        if trace.steps:
            avg_confidence = sum(s.confidence for s in trace.steps) / len(trace.steps)
            # 根据问题数量降低置信度
            penalty = min(len(issues) * 0.1, 0.5)
            overall_confidence = max(0.0, avg_confidence - penalty)
        else:
            overall_confidence = 0.0

        return ConsistencyResult(
            is_consistent=len(issues) == 0,
            confidence=overall_confidence,
            issues=issues,
        )

    def _has_produced(self, item: str, previous_steps: list[ReasoningStep]) -> bool:
        """检查之前的步骤是否产生了指定项"""
        for step in previous_steps:
            if item in step.output:
                return True
        return False
