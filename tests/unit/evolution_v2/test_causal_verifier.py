"""
因果验证器验收测试

覆盖设计文档 10.4 节验收标准
"""

import pytest


class TestCausalVerifier:
    """因果验证器测试"""

    def test_verifier_creation(self):
        """测试验证器创建"""
        from usmsb_sdk.meta_agent.evolution_v2.causal_verifier.verifier import CausalVerifier
        verifier = CausalVerifier(causal_graph=None)
        assert verifier is not None


class TestVerificationContext:
    """验证上下文测试"""

    def test_context_creation(self):
        """测试验证上下文创建"""
        from usmsb_sdk.meta_agent.evolution_v2.causal_verifier.verifier import VerificationContext

        context = VerificationContext(
            task_id="test_task",
            strategy_a=None,
            strategy_b=None,
            outcome_a=None,
            task_features={},
            historical_records=[],
            verification_cost=0.5,
        )

        assert context.task_id == "test_task"
        assert context.verification_cost == 0.5
