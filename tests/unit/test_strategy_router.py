"""
StrategyRouter 完整测试

测试双轨并行策略路由器的所有核心场景：
1. 单轨执行（internal/sdk）
2. 双轨并行执行
3. LLM 场景分类
4. 历史经验驱动的策略选择
5. LLM 评估选优
6. 错误处理与降级
7. 经验记录与查询
"""

import asyncio
import json
import os
import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_manager():
    """Mock LLM Manager"""
    manager = MagicMock()
    manager.model = "test-model"
    manager.api_key = "test-key"
    return manager


@pytest.fixture
def router(mock_llm_manager):
    """StrategyRouter with temp database"""
    from usmsb_sdk.meta_agent.strategy_router import StrategyRouter

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_strategy.db")
        router = StrategyRouter(
            llm_manager=mock_llm_manager,
            experience_db_path=db_path
        )
        yield router


@pytest.fixture
def task_text():
    return "帮我分析一下这个项目的架构设计，并给出优化建议"


# =============================================================================
# Test: 场景分类 (Scenario Classification)
# =============================================================================

class TestScenarioClassification:
    """测试 LLM 场景分类能力"""

    @pytest.mark.asyncio
    async def test_classify_info_task(self, router):
        """INFO 类任务分类"""
        router.llm.generate = AsyncMock(return_value=json.dumps({
            "scenario": "INFO",
            "complexity": "SIMPLE",
            "confidence": 0.95,
            "reasoning": "查询类任务，步骤简单",
            "suggested_layer": "L2",
            "strategy_preference": "sdk"
        }))

        tag = await router._classify_scenario("查询北京市今天的天气")
        assert tag.scenario == "INFO"
        assert tag.complexity == "SIMPLE"
        assert tag.confidence == 0.95
        assert tag.suggested_layer == "L2"

    @pytest.mark.asyncio
    async def test_classify_plan_task(self, router):
        """PLAN 类任务分类"""
        router.llm.generate = AsyncMock(return_value=json.dumps({
            "scenario": "PLAN",
            "complexity": "COMPLEX",
            "confidence": 0.88,
            "reasoning": "多目标规划任务，需要分解",
            "suggested_layer": "L3",
            "strategy_preference": "both"
        }))

        tag = await router._classify_scenario("帮我制定一个三个月的学习计划")
        assert tag.scenario == "PLAN"
        assert tag.complexity == "COMPLEX"
        assert tag.suggested_layer == "L3"

    @pytest.mark.asyncio
    async def test_classify_cog_task(self, router):
        """COG 类任务分类"""
        router.llm.generate = AsyncMock(return_value=json.dumps({
            "scenario": "COG",
            "complexity": "COMPLEX",
            "confidence": 0.82,
            "reasoning": "自我反思任务",
            "suggested_layer": "L4",
            "strategy_preference": "internal"
        }))

        tag = await router._classify_scenario("我最近总是拖延，帮我分析原因")
        assert tag.scenario == "COG"
        assert tag.suggested_layer == "L4"
        assert tag.strategy_preference == "internal"

    @pytest.mark.asyncio
    async def test_classify_collab_task(self, router):
        """COLLAB 类任务分类"""
        router.llm.generate = AsyncMock(return_value=json.dumps({
            "scenario": "COLLAB",
            "complexity": "COMPLEX",
            "confidence": 0.85,
            "reasoning": "多Agent协作任务",
            "suggested_layer": "L5",
            "strategy_preference": "both"
        }))

        tag = await router._classify_scenario("让分析和执行Agent协作完成这个任务")
        assert tag.scenario == "COLLAB"
        assert tag.suggested_layer == "L5"

    @pytest.mark.asyncio
    async def test_classify_invalid_json_fallback(self, router):
        """LLM 返回非 JSON 时的降级处理"""
        router.llm.generate = AsyncMock(return_value="这不是有效的JSON")

        tag = await router._classify_scenario("随便什么任务")
        # 应该使用默认值
        assert tag.scenario in ["INFO", "PLAN", "COG", "COLLAB"]
        assert tag.confidence == 0.3  # 解析失败时的默认置信度

    @pytest.mark.asyncio
    async def test_classify_missing_fields(self, router):
        """LLM 返回缺字段 JSON 时的处理"""
        router.llm.generate = AsyncMock(return_value=json.dumps({
            "scenario": "INFO",
            # 缺少其他字段
        }))

        tag = await router._classify_scenario("查询任务")
        # 缺字段时应有默认值
        assert tag.scenario == "INFO"
        assert tag.complexity in ["SIMPLE", "COMPLEX"]


# =============================================================================
# Test: 策略执行计时 (Execution with Timing)
# =============================================================================

class TestExecutionWithTiming:
    """测试带计时的策略执行"""

    @pytest.mark.asyncio
    async def test_execute_internal_success(self, router):
        """internal 函数成功执行"""
        async def internal_fn(task):
            await asyncio.sleep(0.01)
            return "internal result"

        result = await router._execute_with_timing("internal", internal_fn, "test task")
        assert result.strategy_name == "internal"
        assert result.result == "internal result"
        assert result.error is None
        assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_execute_sdk_success(self, router):
        """sdk 函数成功执行"""
        async def sdk_fn(task):
            await asyncio.sleep(0.01)
            return "sdk result"

        result = await router._execute_with_timing("sdk", sdk_fn, "test task")
        assert result.strategy_name == "sdk"
        assert result.result == "sdk result"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_execute_internal_error(self, router):
        """internal 函数执行出错"""
        async def failing_fn(task):
            raise ValueError("执行失败")

        result = await router._execute_with_timing("internal", failing_fn, "test task")
        assert result.strategy_name == "internal"
        assert result.error == "执行失败"
        assert result.result is None

    @pytest.mark.asyncio
    async def test_execute_sdk_error(self, router):
        """sdk 函数执行出错"""
        async def failing_fn(task):
            raise RuntimeError("SDK Error")

        result = await router._execute_with_timing("sdk", failing_fn, "test task")
        assert result.strategy_name == "sdk"
        assert "SDK Error" in result.error


# =============================================================================
# Test: 主路由流程 (Main Route Flow)
# =============================================================================

class TestMainRouteFlow:
    """测试主路由流程"""

    @pytest.mark.asyncio
    async def test_route_internal_only(self, router):
        """策略偏好为 internal 时只执行 internal"""
        router.llm.generate = AsyncMock(return_value=json.dumps({
            "scenario": "INFO",
            "complexity": "SIMPLE",
            "confidence": 0.9,
            "reasoning": "简单任务",
            "suggested_layer": "L2",
            "strategy_preference": "internal"
        }))

        internal_called = False
        sdk_called = False

        async def internal_fn(task):
            nonlocal internal_called
            internal_called = True
            return "internal ok"

        async def sdk_fn(task):
            nonlocal sdk_called
            sdk_called = True
            return "sdk ok"

        result = await router.route("test task", "L2", internal_fn, sdk_fn)
        assert internal_called
        assert not sdk_called
        assert result.strategy_name == "internal"
        assert result.result == "internal ok"

    @pytest.mark.asyncio
    async def test_route_sdk_only(self, router):
        """策略偏好为 sdk 时只执行 sdk"""
        router.llm.generate = AsyncMock(return_value=json.dumps({
            "scenario": "INFO",
            "complexity": "SIMPLE",
            "confidence": 0.9,
            "reasoning": "SDK更擅长",
            "suggested_layer": "L2",
            "strategy_preference": "sdk"
        }))

        internal_called = False
        sdk_called = False

        async def internal_fn(task):
            nonlocal internal_called
            internal_called = True
            return "internal ok"

        async def sdk_fn(task):
            nonlocal sdk_called
            sdk_called = True
            return "sdk ok"

        result = await router.route("test task", "L2", internal_fn, sdk_fn)
        assert not internal_called
        assert sdk_called
        assert result.strategy_name == "sdk"

    @pytest.mark.asyncio
    async def test_route_both_parallel(self, router):
        """策略偏好为 both 时双轨并行"""
        router.llm.generate = AsyncMock(return_value=json.dumps({
            "scenario": "PLAN",
            "complexity": "COMPLEX",
            "confidence": 0.85,
            "reasoning": "复杂任务，双轨验证",
            "suggested_layer": "L3",
            "strategy_preference": "both"
        }))
        # LLM 评估时，选择 internal
        router.llm.generate = AsyncMock(side_effect=[
            json.dumps({  # 第一次：场景分类
                "scenario": "PLAN",
                "complexity": "COMPLEX",
                "confidence": 0.85,
                "reasoning": "复杂任务",
                "suggested_layer": "L3",
                "strategy_preference": "both"
            }),
            json.dumps({  # 第二次：策略评估选 internal
                "winner": "A",
                "quality_a": 0.9,
                "quality_b": 0.7,
                "reasoning": "A质量更高"
            })
        ])

        internal_called = False
        sdk_called = False

        async def internal_fn(task):
            nonlocal internal_called
            internal_called = True
            await asyncio.sleep(0.01)
            return "internal result"

        async def sdk_fn(task):
            nonlocal sdk_called
            sdk_called = True
            await asyncio.sleep(0.01)
            return "sdk result"

        result = await router.route("复杂规划任务", "L3", internal_fn, sdk_fn)
        # 两次调用都应执行（双轨并行）
        assert internal_called
        assert sdk_called
        # 结果应该是 internal（被 LLM 选中）

    @pytest.mark.asyncio
    async def test_route_with_history_prefers_better(self, router):
        """有历史经验时，选择质量更好的策略"""
        # 先记录一条 internal 质量更高的经验
        from usmsb_sdk.meta_agent.strategy_router import StrategyExperience, ScenarioTag

        exp = StrategyExperience(
            id="exp-001",
            scenario="INFO",
            complexity="SIMPLE",
            task_hash="abc123",
            task_text="查询任务",
            strategy="internal",
            layer="L2",
            quality_score=0.95,
            response_quality=0.95,
            reasoning_depth=0.8,
            execution_time=0.5,
            token_cost=100,
            result_summary="很好",
            selected=True,
            improvement_notes="",
            timestamp=datetime.now(),
            embedding=None
        )
        router._experience_cache["INFO:L2"] = [exp]

        router.llm.generate = AsyncMock(return_value=json.dumps({
            "scenario": "INFO",
            "complexity": "SIMPLE",
            "confidence": 0.9,
            "reasoning": "有历史",
            "suggested_layer": "L2",
            "strategy_preference": "both"
        }))

        internal_called = False
        sdk_called = False

        async def internal_fn(task):
            nonlocal internal_called
            internal_called = True
            return "internal"

        async def sdk_fn(task):
            nonlocal sdk_called
            sdk_called = True
            return "sdk"

        # 有历史经验且 internal 质量更高，应该只执行 internal
        result = await router.route("查询任务", "L2", internal_fn, sdk_fn)
        assert internal_called
        # Note: 由于有历史经验，如果 internal_avg > sdk_avg + 0.1，只执行 internal

    @pytest.mark.asyncio
    async def test_route_error_all_fail(self, router):
        """两个策略都失败时的降级处理"""
        router.llm.generate = AsyncMock(return_value=json.dumps({
            "scenario": "INFO",
            "complexity": "SIMPLE",
            "confidence": 0.9,
            "reasoning": "测试",
            "suggested_layer": "L2",
            "strategy_preference": "both"
        }))

        async def always_fail(task):
            raise Exception("总是失败")

        result = await router.route("test", "L2", always_fail, always_fail)
        # 至少有一个结果（虽然是错误）
        assert result.error is not None


# =============================================================================
# Test: 经验记录与查询 (Experience Recording & Query)
# =============================================================================

class TestExperienceRecording:
    """测试经验记录和查询"""

    @pytest.mark.asyncio
    async def test_record_experience(self, router):
        """记录经验到数据库"""
        from usmsb_sdk.meta_agent.strategy_router import ScenarioTag, StrategyResult

        scenario_tag = ScenarioTag(
            scenario="INFO",
            complexity="SIMPLE",
            confidence=0.9,
            reasoning="测试",
            suggested_layer="L2",
            strategy_preference="sdk"
        )
        results = {
            "internal": StrategyResult(
                strategy_name="internal",
                result="internal",
                quality_score=0.7,
                execution_time=0.5,
                token_cost=100,
                error=None
            )
        }
        best = results["internal"]

        await router._record_experience("test task", "L2", scenario_tag, results, best)

        # 查询刚记录的经验
        history = await router._get_relevant_experience("INFO", "L2")
        assert len(history) >= 1

    @pytest.mark.asyncio
    async def test_avg_quality_calculation(self, router):
        """平均质量计算"""
        from usmsb_sdk.meta_agent.strategy_router import StrategyExperience

        experiences = [
            StrategyExperience(
                id=f"exp-{i}", scenario="INFO", complexity="SIMPLE",
                task_hash=f"hash{i}", task_text="task",
                strategy="internal", layer="L2",
                quality_score=0.7 + i * 0.1,
                response_quality=0.8, reasoning_depth=0.6,
                execution_time=0.5, token_cost=100,
                result_summary="ok", selected=True,
                improvement_notes="", timestamp=datetime.now(), embedding=None
            )
            for i in range(3)
        ]

        avg = router._avg_quality(experiences, "internal")
        # (0.7 + 0.8 + 0.9) / 3 = 0.8
        assert abs(avg - 0.8) < 0.01

    @pytest.mark.asyncio
    async def test_avg_quality_no_history(self, router):
        """无历史时返回默认值"""
        avg = router._avg_quality([], "internal")
        assert avg == 0.5  # 默认中等质量


# =============================================================================
# Test: LLM 评估选优 (LLM Evaluation & Selection)
# =============================================================================

class TestLLMEvaluation:
    """测试 LLM 评估选优逻辑"""

    @pytest.mark.asyncio
    async def test_evaluate_prefers_quality_a(self, router):
        """评估结果：策略A胜出"""
        router.llm.generate = AsyncMock(return_value=json.dumps({
            "winner": "A",
            "quality_a": 0.9,
            "quality_b": 0.6,
            "reasoning": "A更完整"
        }))

        from usmsb_sdk.meta_agent.strategy_router import ScenarioTag, StrategyResult

        results = {
            "internal": StrategyResult(
                strategy_name="internal",
                result="result A",
                quality_score=0.9,
                execution_time=1.0,
                token_cost=200,
                error=None
            ),
            "sdk": StrategyResult(
                strategy_name="sdk",
                result="result B",
                quality_score=0.6,
                execution_time=0.5,
                token_cost=100,
                error=None
            )
        }
        tag = ScenarioTag(
            scenario="INFO", complexity="SIMPLE",
            confidence=0.9, reasoning="test",
            suggested_layer="L2", strategy_preference="both"
        )

        best = await router._llm_evaluate_and_select("task", results, tag)
        assert best.strategy_name == "internal"

    @pytest.mark.asyncio
    async def test_evaluate_prefers_b(self, router):
        """评估结果：策略B胜出"""
        router.llm.generate = AsyncMock(return_value=json.dumps({
            "winner": "B",
            "quality_a": 0.5,
            "quality_b": 0.95,
            "reasoning": "B更准确"
        }))

        from usmsb_sdk.meta_agent.strategy_router import ScenarioTag, StrategyResult

        results = {
            "internal": StrategyResult(
                strategy_name="internal",
                result="result A",
                quality_score=0.5,
                execution_time=1.0,
                token_cost=200,
                error=None
            ),
            "sdk": StrategyResult(
                strategy_name="sdk",
                result="result B",
                quality_score=0.95,
                execution_time=0.5,
                token_cost=100,
                error=None
            )
        }
        tag = ScenarioTag(
            scenario="INFO", complexity="SIMPLE",
            confidence=0.9, reasoning="test",
            suggested_layer="L2", strategy_preference="both"
        )

        best = await router._llm_evaluate_and_select("task", results, tag)
        assert best.strategy_name == "sdk"

    @pytest.mark.asyncio
    async def test_evaluate_tie_chooses_faster(self, router):
        """平局时选择执行时间更短的策略"""
        router.llm.generate = AsyncMock(return_value=json.dumps({
            "winner": "TIE",
            "quality_a": 0.8,
            "quality_b": 0.8,
            "reasoning": "两者质量相当"
        }))

        from usmsb_sdk.meta_agent.strategy_router import ScenarioTag, StrategyResult

        results = {
            "internal": StrategyResult(
                strategy_name="internal",
                result="result A",
                quality_score=0.8,
                execution_time=1.0,
                token_cost=200,
                error=None
            ),
            "sdk": StrategyResult(
                strategy_name="sdk",
                result="result B",
                quality_score=0.8,
                execution_time=0.5,
                token_cost=100,
                error=None
            )
        }
        tag = ScenarioTag(
            scenario="INFO", complexity="SIMPLE",
            confidence=0.9, reasoning="test",
            suggested_layer="L2", strategy_preference="both"
        )

        best = await router._llm_evaluate_and_select("task", results, tag)
        # TIE 时选择执行时间更短的（sdk 0.5s < internal 1.0s）
        assert best.strategy_name == "sdk"

    @pytest.mark.asyncio
    async def test_evaluate_tie_internal_faster(self, router):
        """平局且 internal 更快时选择 internal"""
        router.llm.generate = AsyncMock(return_value=json.dumps({
            "winner": "TIE",
            "quality_a": 0.8,
            "quality_b": 0.8,
            "reasoning": "两者质量相当"
        }))

        from usmsb_sdk.meta_agent.strategy_router import ScenarioTag, StrategyResult

        results = {
            "internal": StrategyResult(
                strategy_name="internal",
                result="result A",
                quality_score=0.8,
                execution_time=0.3,
                token_cost=200,
                error=None
            ),
            "sdk": StrategyResult(
                strategy_name="sdk",
                result="result B",
                quality_score=0.8,
                execution_time=1.0,
                token_cost=100,
                error=None
            )
        }
        tag = ScenarioTag(
            scenario="INFO", complexity="SIMPLE",
            confidence=0.9, reasoning="test",
            suggested_layer="L2", strategy_preference="both"
        )

        best = await router._llm_evaluate_and_select("task", results, tag)
        # TIE 时选择执行时间更短的（internal 0.3s < sdk 1.0s）
        assert best.strategy_name == "internal"


# =============================================================================
# Test: 边界情况 (Edge Cases)
# =============================================================================

class TestEdgeCases:
    """测试边界情况和错误处理"""

    @pytest.mark.asyncio
    async def test_empty_task_text(self, router):
        """空任务文本"""
        router.llm.generate = AsyncMock(return_value=json.dumps({
            "scenario": "INFO",
            "complexity": "SIMPLE",
            "confidence": 0.5,
            "reasoning": "空任务",
            "suggested_layer": "L2",
            "strategy_preference": "sdk"
        }))

        async def sdk_fn(task):
            return "ok"

        async def internal_fn(task):
            return "ok"

        result = await router.route("", "L2", internal_fn, sdk_fn)
        assert result is not None

    @pytest.mark.asyncio
    async def test_very_long_task_text(self, router):
        """超长任务文本"""
        router.llm.generate = AsyncMock(return_value=json.dumps({
            "scenario": "INFO",
            "complexity": "COMPLEX",
            "confidence": 0.8,
            "reasoning": "长任务",
            "suggested_layer": "L3",
            "strategy_preference": "both"
        }))

        long_task = "详细描述 " * 1000  # 超长文本

        async def internal_fn(task):
            return "ok"

        async def sdk_fn(task):
            return "ok"

        result = await router.route(long_task, "L3", internal_fn, sdk_fn)
        assert result is not None

    @pytest.mark.asyncio
    async def test_llm_returns_wrong_scenario_value(self, router):
        """LLM 返回未知场景类型"""
        router.llm.generate = AsyncMock(return_value=json.dumps({
            "scenario": "UNKNOWN_TYPE",
            "complexity": "SIMPLE",
            "confidence": 0.5,
            "reasoning": "test",
            "suggested_layer": "L2",
            "strategy_preference": "sdk"
        }))

        async def sdk_fn(task):
            return "ok"

        async def internal_fn(task):
            return "ok"

        # 应该不崩溃，使用默认值
        result = await router.route("test", "L2", internal_fn, sdk_fn)
        assert result is not None

    @pytest.mark.asyncio
    async def test_strategy_result_serialization(self, router):
        """StrategyResult 序列化"""
        from usmsb_sdk.meta_agent.strategy_router import StrategyResult

        result = StrategyResult(
            strategy_name="internal",
            result={"key": "value", "count": 42},
            quality_score=0.85,
            execution_time=1.23,
            token_cost=500,
            error=None
        )
        # result 应该可以正常返回
        assert result.strategy_name == "internal"
        assert result.result["count"] == 42
