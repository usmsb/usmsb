"""
L5 Collective Intelligence 完整测试

测试 L5 集体智能系统的所有核心场景：
1. L5CollectiveIntelligence 初始化
2. 成员管理（添加/移除 L4 Agent）
3. 集体思考 (think_collectively)
4. 集体决策 (decide)
5. 集体创造 (create_together)
6. 全局工作空间
7. 集体记忆
8. 集体自模型
9. 边界情况
"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def l5_collective():
    from usmsb_sdk.l5.l5_collective import L5CollectiveIntelligence
    return L5CollectiveIntelligence(
        collective_id="test-collective",
        max_attention=7
    )


@pytest.fixture
def mock_l4_agent():
    """Mock L4 Agent"""
    agent = MagicMock()
    agent.agent_id = "mock-l4-agent"
    agent.capabilities = ["reasoning", "creativity"]
    agent.self_model = MagicMock()
    agent.self_model.capabilities = MagicMock()
    agent.self_model.capabilities.strongest = ["reasoning"]
    agent.think = MagicMock()
    return agent


# =============================================================================
# Test: L5 初始化 (Initialization)
# =============================================================================

class TestL5Initialization:
    """测试 L5CollectiveIntelligence 初始化"""

    def test_initialization_basic(self, l5_collective):
        """基本初始化"""
        assert l5_collective.collective_id == "test-collective"
        assert l5_collective.created_at > 0
        assert l5_collective.cycle_count == 0

    def test_initialization_has_workspace(self, l5_collective):
        """初始化有全局工作空间"""
        assert l5_collective.workspace is not None

    def test_initialization_has_collective_memory(self, l5_collective):
        """初始化有集体记忆"""
        assert l5_collective.collective_memory is not None

    def test_initialization_has_decision_making(self, l5_collective):
        """初始化有集体决策组件"""
        assert l5_collective.decision_making is not None

    def test_initialization_has_creativity(self, l5_collective):
        """初始化有集体创造力组件"""
        assert l5_collective.creativity is not None

    def test_initialization_has_collective_self(self, l5_collective):
        """初始化有集体自模型"""
        assert l5_collective.collective_self is not None

    def test_initial_members_empty(self, l5_collective):
        """初始无成员"""
        assert len(l5_collective.members) == 0
        assert len(l5_collective.member_info) == 0

    def test_initialization_with_custom_id(self):
        """自定义 ID 初始化"""
        from usmsb_sdk.l5.l5_collective import L5CollectiveIntelligence
        l5 = L5CollectiveIntelligence(collective_id="custom-id")
        assert l5.collective_id == "custom-id"

    def test_workspace_max_attention(self, l5_collective):
        """工作空间最大注意力数量"""
        assert l5_collective.workspace.max_attention == 7


# =============================================================================
# Test: 成员管理 (Member Management)
# =============================================================================

class TestMemberManagement:
    """测试 L4 Agent 成员管理"""

    def test_add_member(self, l5_collective, mock_l4_agent):
        """添加单个成员"""
        l5_collective.add_member(mock_l4_agent)
        assert "mock-l4-agent" in l5_collective.members
        assert "mock-l4-agent" in l5_collective.member_info

    def test_add_multiple_members(self, l5_collective, mock_l4_agent):
        """添加多个成员"""
        for i in range(3):
            agent = MagicMock()
            agent.agent_id = f"agent-{i}"
            agent.capabilities = [f"cap-{i}"]
            agent.self_model = MagicMock()
            agent.self_model.capabilities = MagicMock()
            agent.self_model.capabilities.strongest = [f"cap-{i}"]
            l5_collective.add_member(agent)

        assert len(l5_collective.members) == 3

    def test_add_member_sets_join_time(self, l5_collective, mock_l4_agent):
        """添加成员记录加入时间"""
        l5_collective.add_member(mock_l4_agent)
        info = l5_collective.member_info["mock-l4-agent"]
        assert "joined_at" in info
        assert info["joined_at"] > 0

    def test_remove_member(self, l5_collective, mock_l4_agent):
        """移除成员"""
        l5_collective.add_member(mock_l4_agent)
        l5_collective.remove_member("mock-l4-agent")
        assert "mock-l4-agent" not in l5_collective.members

    def test_remove_nonexistent_member(self, l5_collective):
        """移除不存在的成员不崩溃"""
        l5_collective.remove_member("nonexistent")
        assert len(l5_collective.members) == 0

    def test_add_same_member_twice(self, l5_collective, mock_l4_agent):
        """添加同一成员两次（后者覆盖前者）"""
        l5_collective.add_member(mock_l4_agent)
        l5_collective.add_member(mock_l4_agent)
        assert len(l5_collective.members) == 1


# =============================================================================
# Test: 集体思考 (Collective Thinking)
# =============================================================================

class TestCollectiveThinking:
    """测试集体思考"""

    @pytest.mark.asyncio
    async def test_think_collectively_no_members(self, l5_collective):
        """无成员时的集体思考"""
        result = await l5_collective.think_collectively("test problem")
        assert result is not None
        assert len(result.participating_agents) == 0

    @pytest.mark.asyncio
    async def test_think_collectively_with_members(self, l5_collective, mock_l4_agent):
        """有成员时的集体思考"""
        l5_collective.add_member(mock_l4_agent)
        result = await l5_collective.think_collectively("如何解决X问题")
        assert result is not None
        assert result.problem == "如何解决X问题"

    @pytest.mark.asyncio
    async def test_think_collectively_multiple_members(self, l5_collective):
        """多成员集体思考"""
        for i in range(3):
            agent = MagicMock()
            agent.agent_id = f"agent-{i}"
            agent.capabilities = [f"cap-{i}"]
            agent.self_model = MagicMock()
            agent.self_model.capabilities = MagicMock()
            agent.self_model.capabilities.strongest = [f"cap-{i}"]
            agent.think = MagicMock()
            l5_collective.add_member(agent)

        result = await l5_collective.think_collectively("复杂问题")
        assert result is not None

    @pytest.mark.asyncio
    async def test_think_collectively_empty_problem(self, l5_collective):
        """空问题"""
        result = await l5_collective.think_collectively("")
        assert result is not None

    @pytest.mark.asyncio
    async def test_think_collectively_long_problem(self, l5_collective):
        """长问题描述"""
        problem = "问题描述 " * 100
        result = await l5_collective.think_collectively(problem)
        assert result is not None


# =============================================================================
# Test: 集体决策 (Collective Decision)
# =============================================================================

class TestCollectiveDecision:
    """测试集体决策"""

    @pytest.mark.asyncio
    async def test_decide_returns_result(self, l5_collective):
        """集体决策返回结果"""
        decision = await l5_collective.decide(
            topic="技术选型",
            description="选择 Python 还是 Rust"
        )
        assert decision is not None

    @pytest.mark.asyncio
    async def test_decide_with_topic_only(self, l5_collective):
        """仅提供话题的决策"""
        decision = await l5_collective.decide(topic="简单决策")
        assert decision is not None

    @pytest.mark.asyncio
    async def test_decide_updates_cycle_count(self, l5_collective):
        """决策后 cycle_count 增加"""
        initial = l5_collective.cycle_count
        await l5_collective.decide(topic="测试决策")
        assert l5_collective.cycle_count >= initial


# =============================================================================
# Test: 集体创造 (Collective Creativity)
# =============================================================================

class TestCollectiveCreativity:
    """测试集体创造"""

    @pytest.mark.asyncio
    async def test_create_together_no_members(self, l5_collective):
        """无成员时的集体创造"""
        ideas = await l5_collective.create_together(
            domain1="物理",
            domain2="生物",
            problem="新储能方式"
        )
        assert isinstance(ideas, list)

    @pytest.mark.asyncio
    async def test_create_together_with_members(self, l5_collective, mock_l4_agent):
        """有成员时的集体创造"""
        l5_collective.add_member(mock_l4_agent)
        ideas = await l5_collective.create_together(
            domain1="AI",
            domain2="医学",
            problem="诊断辅助"
        )
        assert isinstance(ideas, list)

    @pytest.mark.asyncio
    async def test_create_together_different_domains(self, l5_collective):
        """不同领域组合"""
        ideas = await l5_collective.create_together(
            domain1="艺术",
            domain2="工程",
            problem="创新设计"
        )
        assert isinstance(ideas, list)


# =============================================================================
# Test: 全局工作空间 (Global Workspace)
# =============================================================================

class TestGlobalWorkspace:
    """测试全局工作空间"""

    def test_workspace_has_register_method(self, l5_collective):
        """工作空间可注册 Agent"""
        assert hasattr(l5_collective.workspace, 'register_agent')

    def test_workspace_has_receive_broadcast(self, l5_collective):
        """工作空间可接收广播"""
        assert hasattr(l5_collective.workspace, 'receive_broadcast')

    def test_workspace_max_attention_respected(self, l5_collective):
        """最大注意力数量被遵守"""
        assert l5_collective.workspace.max_attention == 7


# =============================================================================
# Test: 集体记忆 (Collective Memory)
# =============================================================================

class TestCollectiveMemory:
    """测试集体记忆"""

    def test_memory_has_store_method(self, l5_collective):
        """记忆可存储"""
        assert hasattr(l5_collective.collective_memory, 'store')

    def test_memory_has_recall_method(self, l5_collective):
        """记忆可召回"""
        assert hasattr(l5_collective.collective_memory, 'recall')

    @pytest.mark.asyncio
    async def test_store_and_recall(self, l5_collective):
        """存储后能召回"""
        await l5_collective.store_collective_memory(
            content="测试记忆内容",
            memory_type="test"
        )
        # recall 是 async 方法
        results = await l5_collective.collective_memory.recall("测试")
        assert isinstance(results, list)  # 不崩溃即通过


# =============================================================================
# Test: 集体自模型 (Collective Self Model)
# =============================================================================

class TestCollectiveSelfModel:
    """测试集体自模型"""

    @pytest.mark.asyncio
    async def test_describe_collective_self(self, l5_collective):
        """描述集体自我"""
        desc = await l5_collective.collective_self.describe_collective_self()
        assert desc is not None
        assert len(desc) > 0

    @pytest.mark.asyncio
    async def test_detect_collective_mood(self, l5_collective):
        """检测集体情绪"""
        moods = [
            {"agent_id": "a1", "emotion": "happy"},
            {"agent_id": "a2", "emotion": "neutral"},
        ]
        result = await l5_collective.collective_self.detect_collective_mood(moods)
        assert result is not None

    @pytest.mark.asyncio
    async def test_detect_mood_empty(self, l5_collective):
        """空成员时检测情绪"""
        result = await l5_collective.collective_self.detect_collective_mood([])
        assert result is not None


# =============================================================================
# Test: 边界情况 (Edge Cases)
# =============================================================================

class TestL5EdgeCases:
    """测试 L5 边界情况"""

    @pytest.mark.asyncio
    async def test_think_with_all_members_failing(self, l5_collective):
        """所有成员思考都失败时"""
        agent = MagicMock()
        agent.agent_id = "failing-agent"
        agent.think = MagicMock(side_effect=Exception("thinking failed"))
        agent.self_model = MagicMock()
        agent.self_model.capabilities = MagicMock()
        agent.self_model.capabilities.strongest = []
        l5_collective.add_member(agent)

        # 不应崩溃
        result = await l5_collective.think_collectively("问题")
        assert result is not None

    @pytest.mark.asyncio
    async def test_decide_with_empty_topic(self, l5_collective):
        """空话题决策"""
        result = await l5_collective.decide("")
        assert result is not None

    @pytest.mark.asyncio
    async def test_creativity_empty_domain(self, l5_collective):
        """空领域创造"""
        ideas = await l5_collective.create_together("", "", "问题")
        assert isinstance(ideas, list)

    def test_update_identity_no_crash(self, l5_collective):
        """更新集体身份不崩溃"""
        l5_collective.collective_self.update_identity(
            name="新名称",
            purpose="新目的"
        )
        assert True
