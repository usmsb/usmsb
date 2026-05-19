"""
因果规划器验收测试

覆盖设计文档 10.3 节验收标准
"""

import pytest


class TestBackwardSearch:
    """逆向搜索测试"""

    def test_search_basic(self):
        """测试基本逆向搜索"""
        from usmsb_sdk.meta_agent.models.causal_graph import CausalGraph, CausalEdge
        from usmsb_sdk.meta_agent.evolution_v2.causal_planner.backward_search import BackwardSearch

        graph = CausalGraph(graph_id="test")
        graph.nodes = {"A", "B", "C"}
        graph.edges = [
            CausalEdge(edge_id="e1", source="A", target="B", strength=0.8),
            CausalEdge(edge_id="e2", source="B", target="C", strength=0.9),
        ]

        search = BackwardSearch(graph)
        required = search.search(target_nodes=["C"])

        assert isinstance(required, list)

    def test_cost_aware_search(self):
        """测试带成本的逆向搜索"""
        from usmsb_sdk.meta_agent.models.causal_graph import CausalGraph, CausalEdge
        from usmsb_sdk.meta_agent.evolution_v2.causal_planner.backward_search import CostAwareBackwardSearch

        graph = CausalGraph(graph_id="test")
        graph.nodes = {"A", "B", "C"}
        graph.edges = [
            CausalEdge(edge_id="e1", source="A", target="B", strength=0.8),
            CausalEdge(edge_id="e2", source="B", target="C", strength=0.9),
        ]

        search = CostAwareBackwardSearch(graph)
        result = search.search(target_nodes=["C"], max_cost=10)

        assert result is not None


class TestTaskAbstraction:
    """任务抽象测试"""

    def test_feature_extractor(self):
        """测试特征提取"""
        from usmsb_sdk.meta_agent.evolution_v2.causal_planner.task_abstraction import TaskFeatureExtractor

        extractor = TaskFeatureExtractor()
        features = extractor.extract("api data processing web service")

        assert isinstance(features, dict)


class TestStrategyProfile:
    """策略画像测试"""

    def test_profile_creation(self):
        """测试策略画像创建"""
        from usmsb_sdk.meta_agent.evolution_v2.causal_planner.strategy_selector import StrategyProfile

        profile = StrategyProfile(
            strategy_id="test",
            name="Test Strategy",
            activates_edges=["e1", "e2"],
            produces_nodes=["node1"],
            cost=1.0,
            success_rate=0.8,
            applicable_conditions=["cond1"],
        )

        assert profile.strategy_id == "test"
        assert profile.success_rate == 0.8
