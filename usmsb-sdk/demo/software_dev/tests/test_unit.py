"""
Software Dev Demo 单元测试

测试 Agent SDK 核心功能在软件开发场景中的应用。

运行方式:
    cd demo/software_dev
    python -m pytest tests/test_unit.py -v
"""

import asyncio
import pytest
import sys
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from usmsb_sdk.agent_sdk import (
    BaseAgent,
    AgentConfig,
    CapabilityDefinition,
    SkillDefinition,
    SkillParameter,
    ServiceDefinition,
    DemandDefinition,
)


# ============================================================================
# 单元测试 - Agent 配置
# ============================================================================

class TestAgentConfig:
    """Agent 配置测试"""

    def test_create_agent_config(self):
        """测试创建 Agent 配置"""
        config = AgentConfig(
            name="TestDeveloper",
            description="测试开发者 Agent",
            capabilities=["coding", "testing"],
            heartbeat_interval=30,
            ttl=90,
        )

        assert config.name == "TestDeveloper"
        assert config.description == "测试开发者 Agent"
        assert len(config.capabilities) == 2
        assert config.heartbeat_interval == 30

    def test_capability_definition(self):
        """测试能力定义"""
        cap = CapabilityDefinition(
            name="coding",
            description="编程能力",
            category="development",
            level="expert"
        )

        assert cap.name == "coding"
        assert cap.category == "development"
        assert cap.level == "expert"

    def test_skill_definition(self):
        """测试技能定义"""
        skill = SkillDefinition(
            name="implement_feature",
            description="实现功能",
            parameters=[
                SkillParameter("task", "string", "任务描述"),
                SkillParameter("design", "object", "设计方案")
            ]
        )

        assert skill.name == "implement_feature"
        assert len(skill.parameters) == 2


# ============================================================================
# 单元测试 - Demo Agent
# ============================================================================

class TestDemoAgent:
    """Demo Agent 测试"""

    @pytest.fixture
    def config(self):
        return AgentConfig(
            name="TestDevAgent",
            description="测试开发 Agent",
            capabilities=["coding", "testing"],
        )

    @pytest.fixture
    def agent(self, config):
        from demo.software_dev.agents.developer import DeveloperAgent
        return DeveloperAgent(config)

    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """测试 Agent 初始化"""
        await agent.initialize()

        assert agent.name == "TestDevAgent"
        assert agent.scenario_name == "software_dev"

    @pytest.mark.asyncio
    async def test_agent_skills_setup(self, agent):
        """测试技能设置"""
        await agent.initialize()

        # Developer Agent 应该有这些技能
        skill_names = [s.name for s in agent.skills]
        assert "implement_feature" in skill_names
        assert "write_tests" in skill_names
        assert "fix_bug" in skill_names

    @pytest.mark.asyncio
    async def test_agent_capabilities_setup(self, agent):
        """测试能力设置"""
        await agent.initialize()

        # Developer Agent 应该有这些能力
        cap_names = [c.name for c in agent.capabilities]
        assert "coding" in cap_names
        assert "testing" in cap_names
        assert "debugging" in cap_names


# ============================================================================
# 单元测试 - Product Owner Agent
# ============================================================================

class TestProductOwnerAgent:
    """Product Owner Agent 测试"""

    @pytest.fixture
    def config(self):
        return AgentConfig(
            name="TestPOAgent",
            description="测试产品经理 Agent",
            capabilities=["requirement_analysis"],
        )

    @pytest.fixture
    def agent(self, config):
        from demo.software_dev.agents.product_owner import ProductOwnerAgent
        return ProductOwnerAgent(config)

    @pytest.mark.asyncio
    async def test_requirement_analysis(self, agent):
        """测试需求分析技能"""
        await agent.initialize()

        result = await agent._analyze_requirement({
            "requirement": "用户登录功能"
        })

        assert "user_stories" in result
        assert "tasks" in result
        assert len(result["tasks"]) > 0

    @pytest.mark.asyncio
    async def test_task_prioritization(self, agent):
        """测试任务优先级排序"""
        await agent.initialize()

        tasks = [
            {"id": "TASK-1", "priority": 1},
            {"id": "TASK-2", "priority": 3},
            {"id": "TASK-3", "priority": 2},
        ]

        result = await agent._prioritize_tasks({"tasks": tasks})

        # 验证按优先级排序
        sorted_tasks = result["sorted_tasks"]
        assert sorted_tasks[0]["id"] == "TASK-2"  # priority 3
        assert sorted_tasks[1]["id"] == "TASK-3"  # priority 2
        assert sorted_tasks[2]["id"] == "TASK-1"  # priority 1


# ============================================================================
# 单元测试 - Architect Agent
# ============================================================================

class TestArchitectAgent:
    """Architect Agent 测试"""

    @pytest.fixture
    def config(self):
        return AgentConfig(
            name="TestArchAgent",
            description="测试架构师 Agent",
            capabilities=["architecture_design"],
        )

    @pytest.fixture
    def agent(self, config):
        from demo.software_dev.agents.architect import ArchitectAgent
        return ArchitectAgent(config)

    @pytest.mark.asyncio
    async def test_architecture_design(self, agent):
        """测试架构设计"""
        await agent.initialize()

        result = await agent._design_architecture({
            "requirement": "电商系统"
        })

        assert "architecture" in result
        assert "modules" in result
        assert len(result["modules"]) > 0

    @pytest.mark.asyncio
    async def test_tech_stack_selection(self, agent):
        """测试技术选型"""
        await agent.initialize()

        result = await agent._select_tech_stack({
            "requirements": "Web 应用"
        })

        assert "framework" in result
        assert "database" in result


# ============================================================================
# 单元测试 - Reviewer Agent
# ============================================================================

class TestReviewerAgent:
    """Reviewer Agent 测试"""

    @pytest.fixture
    def config(self):
        return AgentConfig(
            name="TestReviewerAgent",
            description="测试审查 Agent",
            capabilities=["code_review"],
        )

    @pytest.fixture
    def agent(self, config):
        from demo.software_dev.agents.reviewer import ReviewerAgent
        return ReviewerAgent(config)

    @pytest.mark.asyncio
    async def test_code_review(self, agent):
        """测试代码审查"""
        await agent.initialize()

        code = """
def login(user, password):
    # TODO: implement
    print(user, password)
"""

        result = await agent._review_code({
            "code": code,
            "task": {"id": "TASK-001", "title": "用户登录"}
        })

        assert "score" in result
        assert "issues" in result
        assert "suggestions" in result

    @pytest.mark.asyncio
    async def test_security_check(self, agent):
        """测试安全检查"""
        await agent.initialize()

        # 测试密码明文问题
        code_with_password = """
def login(user, password):
    db.execute(f"SELECT * FROM users WHERE password = '{password}'")
"""

        concerns = await agent._check_security({"code": code_with_password})
        assert len(concerns) > 0


# ============================================================================
# 单元测试 - DevOps Agent
# ============================================================================

class TestDevOpsAgent:
    """DevOps Agent 测试"""

    @pytest.fixture
    def config(self):
        return AgentConfig(
            name="TestDevOpsAgent",
            description="测试运维 Agent",
            capabilities=["deployment"],
        )

    @pytest.fixture
    def agent(self, config):
        from demo.software_dev.agents.devops import DevOpsAgent
        return DevOpsAgent(config)

    @pytest.mark.asyncio
    async def test_deployment(self, agent):
        """测试部署功能"""
        await agent.initialize()

        result = await agent._deploy({
            "environment": "staging",
            "version": "1.0.0"
        })

        assert result["status"] == "success"
        assert result["environment"] == "staging"
        assert result["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_health_check(self, agent):
        """测试健康检查"""
        await agent.initialize()

        result = await agent._check_health({"service": "api"})

        assert "status" in result
        assert result["status"] == "healthy"
        assert "checks" in result


# ============================================================================
# 单元测试 - Team Coordinator
# ============================================================================

class TestTeamCoordinator:
    """团队协调器测试"""

    @pytest.fixture
    def coordinator(self):
        from demo.shared.base_demo_agent import TeamCoordinator
        return TeamCoordinator(scenario_name="test")

    @pytest.fixture
    def agent(self):
        from demo.software_dev.agents.developer import DeveloperAgent
        config = AgentConfig(name="Dev1", description="Test")
        return DeveloperAgent(config)

    @pytest.mark.asyncio
    async def test_add_agent(self, coordinator, agent):
        """测试添加 Agent"""
        coordinator.add_agent(agent)
        assert "Dev1" in coordinator.agents

    @pytest.mark.asyncio
    async def test_send_message(self, coordinator, agent):
        """测试发送消息"""
        coordinator.add_agent(agent)
        await coordinator.start()

        await coordinator.send_to(
            sender="Dev1",
            receiver="Dev1",
            content={"type": "test"},
            message_type="text"
        )

        await coordinator.stop()


# ============================================================================
# 单元测试 - Demo Visualizer
# ============================================================================

class TestDemoVisualizer:
    """Demo 可视化器测试"""

    @pytest.fixture
    def visualizer(self):
        from demo.shared.visualizer import DemoVisualizer
        return DemoVisualizer(scenario_name="test", enable_html=False)

    def test_log_event(self, visualizer):
        """测试事件记录"""
        visualizer.log_event("agent_join", {"name": "TestAgent"})

        assert len(visualizer.events) == 1
        assert visualizer.events[0]["type"] == "agent_join"

    def test_update_agent_state(self, visualizer):
        """测试更新 Agent 状态"""
        visualizer.update_agent_state("TestAgent", {"status": "ready"})

        assert "TestAgent" in visualizer.agent_states

    def test_print_summary(self, visualizer):
        """测试打印摘要"""
        visualizer.log_event("start", {})
        visualizer.update_agent_state("Agent1", {"status": "running"})

        # 不应该抛出异常
        visualizer.print_summary()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
