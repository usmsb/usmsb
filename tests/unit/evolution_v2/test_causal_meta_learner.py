"""
因果元学习器验收测试

覆盖设计文档 10.2 节验收标准
"""

import numpy as np
import pytest

from usmsb_sdk.meta_agent.evolution_v2.causal_meta_learner.meta_learner import (
    CausalMetaLearner,
    CausalMetaLearnerConfig,
    MetaLearningResult,
)


class TestCausalMetaLearner:
    """因果元学习器验收测试"""

    @pytest.fixture
    def config(self):
        return CausalMetaLearnerConfig(
            inner_lr=0.01,
            inner_steps=3,
            outer_lr=0.001,
            meta_epochs=5,
            ewc_lambda=5000,
            meta_batch_size=2,
            support_size=3,
            query_size=5,
        )

    @pytest.fixture
    def learner(self, config):
        return CausalMetaLearner(config=config)

    @pytest.mark.asyncio
    async def test_initialize(self, learner):
        """测试异步初始化"""
        await learner.initialize()

    def test_initial_weights_shape(self, learner):
        """测试初始权重形状"""
        weights = learner.get_weights()
        assert len(weights) > 0
        for name, w in weights.items():
            assert isinstance(w, np.ndarray)

    def test_fisher_information_initial(self, learner):
        """测试 Fisher 信息初始状态"""
        fisher = learner.get_fisher_information()
        assert fisher == {}

    def test_get_and_set_weights(self, learner):
        """测试权重获取和设置"""
        weights = learner.get_weights()
        learner.set_weights(weights)
        new_weights = learner.get_weights()
        assert len(new_weights) == len(weights)


class TestEWCPenalty:
    """EWC 惩罚计算测试"""

    def test_ewc_penalty_basic(self):
        """测试 EWC 惩罚基本计算"""
        from usmsb_sdk.meta_agent.evolution_v2.causal_meta_learner.ewc_penalty import EWCPenalty

        ewc = EWCPenalty(ewc_lambda=5000)
        new_weights = {"W_0": np.random.randn(10, 5)}
        old_weights = {"W_0": np.random.randn(10, 5)}
        fisher = {"W_0": np.random.rand(10, 5) * 0.1}

        penalty = ewc.compute_penalty(new_weights, old_weights, fisher)
        assert isinstance(penalty, float)
        assert penalty >= 0

    def test_online_ewc(self):
        """测试在线 EWC"""
        from usmsb_sdk.meta_agent.evolution_v2.causal_meta_learner.ewc_penalty import OnlineEWC

        online_ewc = OnlineEWC(ewc_lambda=5000, decay=0.9)
        weights = {"W_0": np.random.randn(10, 5)}
        fisher = {"W_0": np.random.rand(10, 5) * 0.1}

        online_ewc.update(fisher, weights)
        penalty = online_ewc.compute_penalty(weights)
        assert isinstance(penalty, float)


class TestCausalTaskSampler:
    """因果任务采样器测试"""

    def test_sampler_creation(self):
        """测试采样器创建"""
        from usmsb_sdk.meta_agent.evolution_v2.causal_meta_learner.task_sampler import CausalTaskSampler

        sampler = CausalTaskSampler(support_size=3, query_size=5)
        assert sampler.support_size == 3
        assert sampler.query_size == 5
