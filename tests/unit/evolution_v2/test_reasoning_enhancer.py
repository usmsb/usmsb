"""
推理增强层验收测试

覆盖设计文档 10.5 节验收标准
"""

import pytest

from usmsb_sdk.meta_agent.evolution_v2.reasoning_enhancer.structured_output import (
    ReasoningParser,
    REASONING_TEMPLATE,
)
from usmsb_sdk.meta_agent.evolution_v2.reasoning_enhancer.counterexample import (
    CounterexampleDrivenCorrector,
    Counterexample,
    ReflectiveCorrector,
)


class TestReasoningParser:
    """推理解析器测试"""

    @pytest.fixture
    def parser(self):
        return ReasoningParser()

    def test_parse_valid_reasoning(self, parser):
        """测试解析有效推理输出"""
        reasoning_text = """
## 推理步骤 1
**输入**: 这个问题是要计算 2+2
**规则**: 加法规则
**输出**: 4
**置信度**: 0.95
**自检**: 没有矛盾
"""
        trace = parser.parse(reasoning_text)
        assert trace is not None

    def test_parse_empty_reasoning(self, parser):
        """测试解析空推理"""
        trace = parser.parse("")
        assert trace is not None


class TestCounterexampleDrivenCorrector:
    """反例驱动修正器测试"""

    @pytest.fixture
    def corrector(self):
        return CounterexampleDrivenCorrector(llm_manager=None)

    def test_is_reasonable_counterexample(self, corrector):
        """测试反例合理性检查"""
        counterexample = Counterexample(
            content="这个结论在 x=0 时不成立",
            why_overturns="代入会得到负数平方根",
            original_handling="没有考虑边界情况",
        )
        reasoning_step = {"reasoning": "任何数的平方都是非负数"}

        is_reasonable = corrector.is_reasonable_counterexample(counterexample, reasoning_step)
        assert isinstance(is_reasonable, bool)

    def test_is_reasonable_empty_content(self, corrector):
        """测试空内容反例"""
        counterexample = Counterexample(
            content="short",
            why_overturns="reason",
            original_handling="handling",
        )
        reasoning_step = {"reasoning": "some reasoning"}

        is_reasonable = corrector.is_reasonable_counterexample(counterexample, reasoning_step)
        assert is_reasonable is False

    def test_generate_counterexamples_no_llm(self, corrector):
        """测试无 LLM 时返回空列表"""
        import asyncio
        reasoning_step = {"reasoning": "test reasoning"}
        result = asyncio.run(corrector.generate_counterexamples(reasoning_step))
        assert result == []


class TestReflectiveCorrector:
    """反思修正器测试"""

    @pytest.fixture
    def corrector(self):
        return ReflectiveCorrector(llm_manager=None)

    def test_reflect_no_llm(self, corrector):
        """测试无 LLM 时返回原始推理"""
        import asyncio
        reasoning = {"conclusion": "test conclusion", "trace": "test trace"}
        result = asyncio.run(corrector.reflect(reasoning))
        assert result == reasoning

    def test_parse_reflection(self, corrector):
        """测试反思结果解析"""
        text = """
漏洞: 可能忽略边界情况
忽略因素: 时间限制
失败原因: 假设不成立
加强方法: 添加边界检查
"""
        result = corrector._parse_reflection(text)
        assert "vulnerabilities" in result
        assert "ignored_factors" in result
