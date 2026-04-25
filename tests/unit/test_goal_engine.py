"""
GoalEngine 完整测试

测试 LLM 驱动的目标引擎所有场景：
1. 引擎生命周期（启动/停止）
2. 目标列表管理（添加/更新/查询）
3. LLM 驱动目标生成（L3Adapter）
4. Internal 策略模式
5. 目标状态机转换
6. 边界情况和错误处理
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm():
    """Mock LLM 客户端"""
    llm = MagicMock()
    llm.generate = AsyncMock(return_value="测试LLM响应")
    return llm


@pytest.fixture
def engine(mock_llm):
    """GoalEngine 实例"""
    from usmsb_sdk.meta_agent.goals.engine import GoalEngine
    return GoalEngine(llm_client=mock_llm, agent_id="test-agent")


# =============================================================================
# Test: 引擎生命周期 (Engine Lifecycle)
# =============================================================================

class TestGoalEngineLifecycle:
    """测试引擎启动和停止"""

    @pytest.mark.asyncio
    async def test_start_initializes_l3_adapter(self, engine):
        """启动时初始化 L3Adapter"""
        await engine.start()
        assert engine._l3_adapter is not None

    @pytest.mark.asyncio
    async def test_stop_does_not_crash(self, engine):
        """停止时不崩溃"""
        await engine.start()
        await engine.stop()  # 不应崩溃

    @pytest.mark.asyncio
    async def test_double_start(self, engine):
        """重复启动不崩溃"""
        await engine.start()
        await engine.start()  # 不应崩溃


# =============================================================================
# Test: 内部目标列表 (Internal Goals)
# =============================================================================

class TestInternalGoals:
    """测试内置目标列表"""

    def test_eternal_goals_exist(self, engine):
        """永恒目标默认存在"""
        assert len(engine.eternal_goals) == 4
        ids = [g["id"] for g in engine.eternal_goals]
        assert "platform_health" in ids
        assert "user_satisfaction" in ids
        assert "system_optimization" in ids
        assert "learning_evolution" in ids

    def test_eternal_goals_have_valid_status(self, engine):
        """永恒目标都有有效状态"""
        for goal in engine.eternal_goals:
            assert goal["status"] in ["in_progress", "completed", "pending", "failed"]

    @pytest.mark.asyncio
    async def test_add_goal(self, engine):
        """添加目标"""
        initial_count = len(engine.goals)
        await engine.add_goal({"id": "new-goal", "name": "新目标", "status": "pending"})
        assert len(engine.goals) == initial_count + 1
        assert engine.goals[-1]["id"] == "new-goal"

    @pytest.mark.asyncio
    async def test_add_multiple_goals(self, engine):
        """添加多个目标"""
        await engine.add_goal({"id": "goal-1", "name": "目标1", "status": "pending"})
        await engine.add_goal({"id": "goal-2", "name": "目标2", "status": "in_progress"})
        assert len(engine.goals) == 2

    @pytest.mark.asyncio
    async def test_update_goal_exists(self, engine):
        """更新存在的目标"""
        await engine.add_goal({"id": "update-test", "name": "测试更新", "status": "pending"})
        await engine.update_goal("update-test", "in_progress")
        updated = next(g for g in engine.goals if g["id"] == "update-test")
        assert updated["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_update_goal_not_exists(self, engine):
        """更新不存在的目标不崩溃"""
        await engine.update_goal("nonexistent-goal", "completed")
        # 不应崩溃，只是找不到

    @pytest.mark.asyncio
    async def test_update_eternal_goal(self, engine):
        """更新永恒目标"""
        await engine.update_goal("platform_health", "completed")
        updated = next(g for g in engine.eternal_goals if g["id"] == "platform_health")
        assert updated["status"] == "completed"


# =============================================================================
# Test: 目标状态检查 (Goal Checking)
# =============================================================================

class TestGoalChecking:
    """测试 check_goals 逻辑"""

    @pytest.mark.asyncio
    async def test_check_goals_returns_none_when_no_adapter(self, engine):
        """check_goals 在无 L3Adapter 时返回 None"""
        result = await engine.check_goals()
        # L3Adapter 不可用时返回 None
        assert result is None

    @pytest.mark.asyncio
    async def test_check_goals_does_not_raise(self, engine):
        """check_goals 不抛出异常"""
        await engine.add_goal({"id": "check-1", "name": "检查1", "status": "pending"})
        # 即使 L3Adapter 不可用，也不应崩溃
        try:
            await engine.check_goals()
        except Exception as e:
            pytest.fail(f"check_goals raised {e}")


# =============================================================================
# Test: 当前状态获取 (Current State)
# =============================================================================

class TestCurrentState:
    """测试 _get_current_state"""

    def test_current_state_contains_keys(self, engine):
        """当前状态包含必要字段"""
        state = engine._get_current_state()
        assert "active_goals" in state
        assert "eternal_goals" in state
        assert "agent_id" in state

    def test_current_state_eternal_goals_count(self, engine):
        """永恒目标计数正确"""
        state = engine._get_current_state()
        assert state["eternal_goals"] == 4
        assert state["active_goals"] == 0  # 初始无用户目标


# =============================================================================
# Test: LLM 适配器集成 (L3 Adapter Integration)
# =============================================================================

class TestL3AdapterIntegration:
    """测试 L3Adapter 集成"""

    @pytest.mark.asyncio
    async def test_l3_adapter_lazy_init(self, engine):
        """L3Adapter 延迟初始化"""
        assert engine._l3_adapter is None
        await engine.start()
        assert engine._l3_adapter is not None

    @pytest.mark.asyncio
    async def test_l3_adapter_cached(self, engine):
        """L3Adapter 只初始化一次"""
        await engine.start()
        first = engine._l3_adapter
        await engine.start()  # 再次启动
        assert engine._l3_adapter is first  # 同一实例


# =============================================================================
# Test: 边界情况 (Edge Cases)
# =============================================================================

class TestGoalEngineEdgeCases:
    """测试边界情况"""

    @pytest.mark.asyncio
    async def test_add_goal_with_minimal_fields(self, engine):
        """添加最少字段的目标"""
        await engine.add_goal({"id": "minimal"})
        assert engine.goals[-1]["id"] == "minimal"

    @pytest.mark.asyncio
    async def test_add_goal_with_extra_fields(self, engine):
        """添加带额外字段的目标"""
        await engine.add_goal({
            "id": "extra-fields",
            "name": "完整目标",
            "status": "in_progress",
            "priority": "high",
            "tags": ["test", "automation"],
            "created_at": "2024-01-01"
        })
        goal = engine.goals[-1]
        assert goal["priority"] == "high"
        assert goal["tags"] == ["test", "automation"]

    @pytest.mark.asyncio
    async def test_update_goal_same_status(self, engine):
        """更新为目标为同一状态"""
        await engine.add_goal({"id": "same-status", "name": "测试", "status": "pending"})
        await engine.update_goal("same-status", "pending")  # 不应崩溃
        assert True

    @pytest.mark.asyncio
    async def test_check_goals_empty_user_goals(self, engine):
        """无用户目标时 check_goals 仍不崩溃"""
        engine.goals.clear()
        # check_goals 在无 L3Adapter 时返回 None
        result = await engine.check_goals()
        assert result is None

    def test_get_current_state_no_crash(self, engine):
        """获取状态不崩溃"""
        state = engine._get_current_state()
        assert state["agent_id"] == "test-agent"
        assert "timestamp" in state or "active_goals" in state
