"""
L4 Self-Conscious Agent 完整测试

测试 L4 层次（自我意识）的所有核心能力：
1. 自我反思 (self_reflect)
2. 元认知 (metacognize)
3. 心智理论 (infer_mind)
4. 情绪响应 (feel)
5. 自模型构建 (build_self_model)
6. 边界情况
"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def l4_agent():
    from usmsb_sdk.l4.l4_agent import L4SelfConsciousAgent
    return L4SelfConsciousAgent(
        agent_id="test-l4-agent",
        name="TestL4"
    )


# =============================================================================
# Test: 自我反思 (SelfReflection)
# =============================================================================

class TestSelfReflection:
    """测试自我反思能力"""

    @pytest.mark.asyncio
    async def test_self_reflect_returns_result(self, l4_agent):
        """自我反思返回结果"""
        result = await l4_agent.self_reflect()
        assert result is not None

    @pytest.mark.asyncio
    async def test_self_reflect_twice_increments_count(self, l4_agent):
        """多次反思计数增加"""
        await l4_agent.self_reflect()
        count_after = l4_agent.reflection_count
        await l4_agent.self_reflect()
        assert l4_agent.reflection_count > count_after

    @pytest.mark.asyncio
    async def test_self_reflect_updates_timestamp(self, l4_agent):
        """反思更新最后反思时间戳"""
        l4_agent.last_reflection = 0
        await l4_agent.self_reflect()
        assert l4_agent.last_reflection > 0


# =============================================================================
# Test: 元认知 (Metacognition)
# =============================================================================

class TestMetacognition:
    """测试元认知能力"""

    @pytest.mark.asyncio
    async def test_metacognize_returns_result(self, l4_agent):
        """元认知返回结果"""
        result = await l4_agent.metacognize("我正在分析这个问题")
        assert result is not None

    @pytest.mark.asyncio
    async def test_metacognize_contains_thought(self, l4_agent):
        """元认知包含输入的思考"""
        result = await l4_agent.metacognize("思考过程：先用简单方法")
        assert result.thought == "思考过程：先用简单方法"

    @pytest.mark.asyncio
    async def test_metacognize_empty_thought(self, l4_agent):
        """空思考过程的元认知"""
        result = await l4_agent.metacognize("")
        assert result.thought == ""

    @pytest.mark.asyncio
    async def test_metacognize_long_thought(self, l4_agent):
        """长思考过程的元认知"""
        long_thought = "分析过程" * 100
        result = await l4_agent.metacognize(long_thought)
        assert result.thought == long_thought


# =============================================================================
# Test: 心智理论 (Theory of Mind)
# =============================================================================

class TestTheoryOfMind:
    """测试心智理论 - 推断他人在做什么"""

    @pytest.mark.asyncio
    async def test_infer_mind_returns_result(self, l4_agent):
        """推断他人心理状态"""
        result = await l4_agent.infer_mind(
            other_agent_id="agent_002",
            history=[]
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_infer_mind_contains_agent_id(self, l4_agent):
        """推断结果包含他人 agent ID"""
        result = await l4_agent.infer_mind(
            other_agent_id="agent_xyz",
            history=[]
        )
        assert result.other_agent_id == "agent_xyz"

    @pytest.mark.asyncio
    async def test_infer_mind_with_history(self, l4_agent):
        """带历史的推断"""
        history = [
            {"action": "查询数据", "timestamp": 123456},
            {"action": "分析结果", "timestamp": 123457},
        ]
        result = await l4_agent.infer_mind(
            other_agent_id="agent_002",
            history=history
        )
        assert result.other_agent_id == "agent_002"

    @pytest.mark.asyncio
    async def test_infer_mind_empty_history(self, l4_agent):
        """空历史的推断"""
        result = await l4_agent.infer_mind(
            other_agent_id="new_agent",
            history=[]
        )
        assert result is not None


# =============================================================================
# Test: 情绪响应 (Emotional Response)
# =============================================================================

class TestEmotionalResponse:
    """测试情绪响应"""

    @pytest.mark.asyncio
    async def test_feel_returns_response(self, l4_agent):
        """feel() 返回情绪响应"""
        stimulus = {"type": "success", "description": "任务完成"}
        result = await l4_agent.feel(stimulus)
        assert result is not None

    @pytest.mark.asyncio
    async def test_feel_different_stimuli(self, l4_agent):
        """不同刺激产生不同情绪"""
        stimulus_success = {"type": "success", "description": "取得成绩"}
        stimulus_failure = {"type": "failure", "description": "遭遇挫折"}

        result_success = await l4_agent.feel(stimulus_success)
        result_failure = await l4_agent.feel(stimulus_failure)
        assert result_success is not None
        assert result_failure is not None

    @pytest.mark.asyncio
    async def test_feel_no_infinite_recursion(self, l4_agent):
        """feel() 不会导致无限递归"""
        try:
            result = await l4_agent.feel({"type": "test", "description": "递归测试"})
            assert result is not None
        except RecursionError:
            pytest.fail("feel() 导致无限递归!")

    @pytest.mark.asyncio
    async def test_feel_rapid_calls(self, l4_agent):
        """快速连续调用 feel()"""
        tasks = [
            l4_agent.feel({"type": "event1", "description": f"事件{i}"})
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_feel_minimal_stimulus(self, l4_agent):
        """最简刺激"""
        result = await l4_agent.feel({})
        assert result is not None


# =============================================================================
# Test: 自模型构建 (Self Model Building)
# =============================================================================

class TestSelfModel:
    """测试自模型构建"""

    @pytest.mark.asyncio
    async def test_build_self_model_returns_model(self, l4_agent):
        """构建自模型"""
        experience = [
            {"type": "success", "outcome": "很好", "lessons": ["继续保持"]}
        ]
        model = await l4_agent.build_self_model(experience)
        assert model is not None

    @pytest.mark.asyncio
    async def test_build_self_model_multiple_experiences(self, l4_agent):
        """多条经验构建自模型"""
        experience = [
            {"type": "success", "outcome": "项目完成", "lessons": ["计划重要"]},
            {"type": "failure", "outcome": "超时", "lessons": ["时间估计不足"]},
            {"type": "learning", "outcome": "掌握了新技术", "lessons": []},
        ]
        model = await l4_agent.build_self_model(experience)
        assert model is not None

    @pytest.mark.asyncio
    async def test_build_self_model_empty_experience(self, l4_agent):
        """空经验构建自模型"""
        model = await l4_agent.build_self_model([])
        assert model is not None

    @pytest.mark.asyncio
    async def test_build_self_model_partial_fields(self, l4_agent):
        """部分字段的经验"""
        experience = [
            {"type": "general"}
        ]
        model = await l4_agent.build_self_model(experience)
        assert model is not None


# =============================================================================
# Test: L4 Agent 初始化与元数据
# =============================================================================

class TestL4Initialization:
    """测试 L4 Agent 初始化"""

    def test_agent_has_correct_id(self, l4_agent):
        """Agent 有正确的 ID"""
        assert l4_agent.agent_id == "test-l4-agent"
        assert l4_agent.id == "test-l4-agent"  # 别名

    def test_agent_has_self_model(self, l4_agent):
        """Agent 有自模型组件"""
        assert l4_agent.self_model is not None

    def test_agent_has_metacognition(self, l4_agent):
        """Agent 有元认知组件"""
        assert l4_agent.metacognition is not None

    def test_agent_has_theory_of_mind(self, l4_agent):
        """Agent 有心智理论组件"""
        assert l4_agent.theory_of_mind is not None

    def test_agent_has_emotions(self, l4_agent):
        """Agent 有情感架构组件"""
        assert l4_agent.emotions is not None

    def test_agent_initial_reflection_count(self, l4_agent):
        """初始反思计数为 0"""
        assert l4_agent.reflection_count == 0

    def test_agent_with_parent_id(self):
        """带 parent_id 的 Agent"""
        from usmsb_sdk.l4.l4_agent import L4SelfConsciousAgent
        agent = L4SelfConsciousAgent(
            agent_id="child-agent",
            name="Child",
            parent_id="parent-agent"
        )
        assert agent.parent_id == "parent-agent"


# =============================================================================
# Test: SelfModel 内部组件
# =============================================================================

class TestSelfModelComponents:
    """测试 SelfModel 及其内部组件"""

    def test_self_model_has_identity(self, l4_agent):
        """自模型有身份信息"""
        identity = l4_agent.self_model.identity
        assert identity is not None

    def test_self_model_has_desires(self, l4_agent):
        """自模型有欲望引擎"""
        assert l4_agent.self_model.desires is not None

    def test_self_model_desires_get_dominant(self, l4_agent):
        """欲望引擎能获取主导欲望"""
        desire = l4_agent.self_model.desires.get_dominant_desire()
        # 可能为 None 如果没有欲望
        assert desire is None or hasattr(desire, 'target')

    def test_self_model_describe_self(self, l4_agent):
        """自模型能描述自己"""
        desc = l4_agent.self_model.describe_self()
        assert desc is not None


# =============================================================================
# Test: DesireEngine
# =============================================================================

class TestDesireEngine:
    """测试欲望引擎"""

    def test_desire_engine_creation(self):
        """创建 DesireEngine"""
        from usmsb_sdk.l4.self_model import DesireEngine
        engine = DesireEngine(agent_id="test-agent")
        assert engine is not None

    def test_desire_engine_has_satisfy_and_frustrate(self):
        """DesireEngine 有满足和受挫方法"""
        from usmsb_sdk.l4.self_model import DesireEngine
        engine = DesireEngine(agent_id="test-agent")
        assert hasattr(engine, 'satisfy')
        assert hasattr(engine, 'frustrate')
        assert hasattr(engine, 'get_dominant_desire')


# =============================================================================
# Test: 边界情况 (Edge Cases)
# =============================================================================

class TestL4EdgeCases:
    """测试 L4 Agent 边界情况"""

    @pytest.mark.asyncio
    async def test_concurrent_calls_unique_results(self, l4_agent):
        """并发调用各自产生结果"""
        tasks = [
            l4_agent.metacognize(f"思考过程{i}")
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_all_methods_available(self, l4_agent):
        """所有 L4 方法都可用"""
        # 自我反思
        reflect = await l4_agent.self_reflect()
        assert reflect is not None
        # 元认知
        meta = await l4_agent.metacognize("测试")
        assert meta is not None
        # 心智理论
        tom = await l4_agent.infer_mind("other", [])
        assert tom is not None
        # 情绪
        emotion = await l4_agent.feel({"type": "test"})
        assert emotion is not None
        # 自模型
        model = await l4_agent.build_self_model([])
        assert model is not None
