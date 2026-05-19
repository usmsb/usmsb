"""
反例驱动的自我修正

ReasoningEnhancer 的组件

主动找反例，触发重新推理
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class Counterexample:
    """反例"""
    content: str
    why_overturns: str
    original_handling: str


class CounterexampleDrivenCorrector:
    """
    反例驱动的自我修正器

    核心思想：
    1. 要求 LLM 主动质疑自己的结论
    2. 主动找反例
    3. 发现反例后触发重新推理
    """

    def __init__(self, llm_manager=None):
        """
        初始化

        Args:
            llm_manager: LLM 管理器
        """
        self.llm = llm_manager

    async def generate_counterexamples(
        self,
        reasoning_step: dict[str, Any],
    ) -> list[Counterexample]:
        """
        生成反例

        问 LLM：「这个结论有没有反例？」

        Args:
            reasoning_step: 推理步骤

        Returns:
            反例列表
        """
        if not self.llm:
            return []

        prompt = f"""
        推理步骤：{reasoning_step.get('reasoning', '')}

        问：有没有反例可以推翻这个推理？
        如果有，列出 3 个反例。
        每个反例说明：
        1. 反例内容
        2. 为什么这个反例能推翻原推理
        3. 原推理对这个反例的处理方式

        回答格式：
        反例1: [内容]
        原因1: [为什么能推翻]
        处理1: [原推理如何处理]

        反例2: ...
        """

        try:
            response = await self.llm.generate(prompt)
            return self._parse_counterexamples(response)
        except Exception:
            return []

    def _parse_counterexamples(self, text: str) -> list[Counterexample]:
        """解析反例"""
        counterexamples = []

        # 简化的解析逻辑
        lines = text.split("\n")
        current = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "反例" in line and ":" in line:
                if current:
                    counterexamples.append(Counterexample(**current))
                    current = {}
                current["content"] = line.split(":", 1)[1].strip()

            elif "原因" in line and ":" in line:
                current["why_overturns"] = line.split(":", 1)[1].strip()

            elif "处理" in line and ":" in line:
                current["original_handling"] = line.split(":", 1)[1].strip()

        if current:
            counterexamples.append(Counterexample(**current))

        return counterexamples

    async def trigger_correction(
        self,
        original_reasoning: dict[str, Any],
        counterexamples: list[Counterexample],
        regenerate_fn=None,
    ) -> dict[str, Any]:
        """
        触发修正

        发现反例后，要求 LLM 重新推理

        Args:
            original_reasoning: 原始推理
            counterexamples: 反例列表
            regenerate_fn: 重新生成函数

        Returns:
            修正后的推理
        """
        if not counterexamples or not regenerate_fn:
            return original_reasoning

        prompt = f"""
        原始推理：{original_reasoning.get('conclusion', '')}

        原始推理过程：
        {original_reasoning.get('trace', '')}

        反例：
        {self._format_counterexamples(counterexamples)}

        请重新推理：
        1. 承认或反驳这些反例
        2. 如果承认，修改结论或添加限制条件
        3. 如果反驳，说明为什么反例不成立
        4. 输出新的推理过程（使用相同的格式）
        """

        try:
            response = await regenerate_fn(prompt)
            return {"conclusion": response, "counterexamples": counterexamples}
        except Exception:
            return original_reasoning

    def _format_counterexamples(self, counterexamples: list[Counterexample]) -> str:
        """格式化反例"""
        lines = []
        for i, ce in enumerate(counterexamples, 1):
            lines.append(f"反例{i}: {ce.content}")
            lines.append(f"  为什么能推翻: {ce.why_overturns}")
            lines.append(f"  原处理: {ce.original_handling}")
        return "\n".join(lines)

    def is_reasonable_counterexample(
        self,
        counterexample: Counterexample,
        reasoning_step: dict[str, Any],
    ) -> bool:
        """
        检查反例是否合理

        Args:
            counterexample: 反例
            reasoning_step: 推理步骤

        Returns:
            是否合理
        """
        # 简化的合理性检查
        if not counterexample.content or len(counterexample.content) < 10:
            return False

        if not counterexample.why_overturns:
            return False

        # 反例内容应该与推理相关
        reasoning_text = reasoning_step.get("reasoning", "").lower()
        counterexample_text = counterexample.content.lower()

        # 检查是否有关键词重叠
        reasoning_words = set(reasoning_text.split())
        counterexample_words = set(counterexample_text.split())

        overlap = len(reasoning_words & counterexample_words)

        return overlap >= 2


class ReflectiveCorrector:
    """
    反思修正器

    不依赖外部反例，通过自我反思发现潜在问题
    """

    def __init__(self, llm_manager=None):
        self.llm = llm_manager

    async def reflect(
        self,
        reasoning: dict[str, Any],
    ) -> dict[str, Any]:
        """
        反思推理过程

        Args:
            reasoning: 推理

        Returns:
            反思结果
        """
        if not self.llm:
            return reasoning

        prompt = f"""
        推理：{reasoning.get('conclusion', '')}

        推理过程：
        {reasoning.get('trace', '')}

        请反思这个推理：
        1. 有什么可能的漏洞？
        2. 有什么被忽略的因素？
        3. 如果结论错了，可能的原因是什么？
        4. 如何加强这个推理？

        回答格式：
        漏洞: [列点]
        忽略因素: [列点]
        失败原因: [列点]
        加强方法: [列点]
        """

        try:
            response = await self.llm.generate(prompt)
            return {
                "original": reasoning,
                "reflection": self._parse_reflection(response),
            }
        except Exception:
            return reasoning

    def _parse_reflection(self, text: str) -> dict[str, list[str]]:
        """解析反思结果"""
        result = {
            "vulnerabilities": [],
            "ignored_factors": [],
            "failure_reasons": [],
            "strengthening_methods": [],
        }

        current_key = None
        lines = text.split("\n")

        key_map = {
            "漏洞": "vulnerabilities",
            "忽略因素": "ignored_factors",
            "失败原因": "failure_reasons",
            "加强方法": "strengthening_methods",
        }

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检查是否是键
            for key, attr in key_map.items():
                if key in line and ":" in line:
                    current_key = attr
                    content = line.split(":", 1)[1].strip()
                    if content:
                        result[attr].append(content)
                    break
            elif current_key and line.startswith("-"):
                result[current_key].append(line[1:].strip())
            elif current_key and line.startswith("*"):
                result[current_key].append(line[1:].strip())

        return result
