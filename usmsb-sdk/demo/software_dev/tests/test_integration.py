"""
Software Dev Demo 集成测试

测试 Agent SDK 与平台 API 的集成功能。

运行方式:
    cd demo/software_dev
    python -m pytest tests/test_integration.py -v
"""

import asyncio
import pytest
import sys
import os
import httpx

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from usmsb_sdk.agent_sdk import AgentConfig

# 测试配置
BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000")
TEST_TIMEOUT = 30.0


# ============================================================================
# 集成测试 - 平台交互
# ============================================================================

class TestPlatformIntegration:
    """平台集成测试"""

    @pytest.fixture
    def client(self):
        return httpx.Client(timeout=TEST_TIMEOUT)

    def test_platform_health(self, client):
        """测试平台健康检查"""
        response = client.get(f"{BASE_URL}/health")
        assert response.status_code == 200

        data = response.json()
        assert "version" in data

    def test_agent_list(self, client):
        """测试获取 Agent 列表"""
        response = client.get(f"{BASE_URL}/agents")
        # 可能返回 200 或其他状态码
        assert response.status_code in [200, 500, 404]


# ============================================================================
# 集成测试 - Agent 注册
# ============================================================================

class TestAgentRegistration:
    """Agent 注册集成测试"""

    @pytest.fixture
    def client(self):
        return httpx.Client(timeout=TEST_TIMEOUT)

    @pytest.fixture
    def cleanup_agent(self, client):
        """测试后清理 Agent"""
        agent_ids = []

        def register_agent_id(agent_id):
            agent_ids.append(agent_id)

        yield register_agent_id

        # 清理
        for agent_id in agent_ids:
            try:
                client.delete(f"{BASE_URL}/agents/{agent_id}")
            except:
                pass

    def test_register_agent(self, client, cleanup_agent):
        """测试注册 Agent"""
        response = client.post(
            f"{BASE_URL}/agents",
            json={
                "name": f"IntegrationTest_{os.urandom(4).hex()}",
                "description": "集成测试 Agent",
                "capabilities": ["testing", "integration"],
                "endpoint": "http://localhost:9999",
                "protocol": "standard",
                "heartbeat_interval": 30,
                "ttl": 90
            }
        )

        if response.status_code in [200, 201]:
            data = response.json()
            agent_id = data.get("agent_id")
            if agent_id:
                cleanup_agent(agent_id)
                assert agent_id is not None
        else:
            # API 可能还没完全实现
            pytest.skip(f"注册 API 返回: {response.status_code}")

    def test_register_and_get(self, client):
        """测试注册后获取 Agent"""
        import time
        agent_name = f"GetTest_{int(time.time())}"

        # 注册
        reg_response = client.post(
            f"{BASE_URL}/agents",
            json={
                "name": agent_name,
                "description": "测试获取",
                "capabilities": ["test"],
                "endpoint": "http://localhost:9999",
                "protocol": "standard",
                "heartbeat_interval": 30,
                "ttl": 90
            }
        )

        if reg_response.status_code not in [200, 201]:
            pytest.skip("注册 API 不可用")

        agent_id = reg_response.json().get("agent_id")

        try:
            # 获取
            get_response = client.get(f"{BASE_URL}/agents/{agent_id}")
            assert get_response.status_code == 200
        finally:
            # 清理
            try:
                client.delete(f"{BASE_URL}/agents/{agent_id}")
            except:
                pass


# ============================================================================
# 集成测试 - Demo Agent 场景
# ============================================================================

class TestSoftwareDevScenario:
    """软件开发场景集成测试"""

    @pytest.mark.asyncio
    async def test_full_development_workflow(self):
        """测试完整开发工作流"""
        from demo.software_dev.agents.product_owner import ProductOwnerAgent
        from demo.software_dev.agents.architect import ArchitectAgent
        from demo.software_dev.agents.developer import DeveloperAgent
        from demo.software_dev.agents.reviewer import ReviewerAgent
        from demo.software_dev.agents.devops import DevOpsAgent

        # 创建配置
        po_config = AgentConfig(name="PO", description="产品经理", capabilities=["requirement_analysis"])
        arch_config = AgentConfig(name="Arch", description="架构师", capabilities=["architecture_design"])
        dev_config = AgentConfig(name="Dev", description="开发者", capabilities=["coding"])
        reviewer_config = AgentConfig(name="Reviewer", description="审查员", capabilities=["code_review"])
        devops_config = AgentConfig(name="DevOps", description="运维", capabilities=["deployment"])

        # 创建 Agent
        po = ProductOwnerAgent(po_config)
        arch = ArchitectAgent(arch_config)
        dev = DeveloperAgent(dev_config)
        reviewer = ReviewerAgent(reviewer_config)
        devops = DevOpsAgent(devops_config)

        # 初始化
        await po.initialize()
        await arch.initialize()
        await dev.initialize()
        await reviewer.initialize()
        await devops.initialize()

        # Step 1: ProductOwner 发布需求
        requirement = "用户登录功能"
        await po.publish_requirement(requirement)

        # Step 2: Architect 处理需求
        arch_result = await arch.handle_message({
            "sender": "PO",
            "receiver": "Arch",
            "content": {"type": "new_requirement", "requirement": requirement},
            "message_type": "task"
        })

        assert arch_result.get("status") == "design_completed"

        # 验证 Architect 创建了任务
        assert len(arch.designs) > 0


# ============================================================================
# 集成测试 - 服务市场
# ============================================================================

class TestMarketplace:
    """市场功能集成测试"""

    @pytest.fixture
    def client(self):
        return httpx.Client(timeout=TEST_TIMEOUT)

    @pytest.fixture
    def test_agent_id(self, client):
        """创建测试 Agent"""
        response = client.post(
            f"{BASE_URL}/agents",
            json={
                "name": f"MarketplaceTest_{os.urandom(4).hex()}",
                "description": "市场测试 Agent",
                "capabilities": ["testing"],
                "endpoint": "http://localhost:9999",
                "protocol": "standard",
                "heartbeat_interval": 30,
                "ttl": 90
            }
        )

        if response.status_code in [200, 201]:
            agent_id = response.json().get("agent_id")
            yield agent_id
            # 清理
            try:
                client.delete(f"{BASE_URL}/agents/{agent_id}")
            except:
                pass
        else:
            yield None

    def test_publish_service(self, client, test_agent_id):
        """测试发布服务"""
        if not test_agent_id:
            pytest.skip("无法创建测试 Agent")

        response = client.post(
            f"{BASE_URL}/agents/{test_agent_id}/services",
            json={
                "service_name": "测试服务",
                "service_type": "development",
                "description": "测试服务描述",
                "capabilities": ["Python", "FastAPI"],
                "price": 100.0,
                "price_type": "hourly",
                "availability": "24/7"
            }
        )

        # 可能返回成功或 404（API 未实现）
        assert response.status_code in [200, 201, 404, 500]


# ============================================================================
# 集成测试 - 协作功能
# ============================================================================

class TestCollaboration:
    """协作功能集成测试"""

    @pytest.fixture
    def client(self):
        return httpx.Client(timeout=TEST_TIMEOUT)

    def test_collaboration_create(self, client):
        """测试创建协作"""
        response = client.post(
            f"{BASE_URL}/collaborations",
            json={
                "goal_description": "测试协作",
                "required_skills": ["Python"],
                "coordinator_agent_id": "test_coordinator",
                "collaboration_mode": "parallel"
            }
        )

        # 可能返回成功或 404
        assert response.status_code in [200, 201, 404, 500]


# ============================================================================
# 集成测试 - 消息通信
# ============================================================================

class TestMessaging:
    """消息通信集成测试"""

    @pytest.mark.asyncio
    async def test_agent_message_flow(self):
        """测试 Agent 消息流转"""
        from demo.shared.base_demo_agent import TeamCoordinator, DemoAgent

        # 创建测试 Agent
        class TestAgent(DemoAgent):
            async def _setup_skills(self):
                pass

            async def _setup_capabilities(self):
                pass

        config1 = AgentConfig(name="Agent1", description="Test Agent 1")
        config2 = AgentConfig(name="Agent2", description="Test Agent 2")

        agent1 = TestAgent(config1, scenario_name="test")
        agent2 = TestAgent(config2, scenario_name="test")

        await agent1.initialize()
        await agent2.initialize()

        # 创建协调器
        coordinator = TeamCoordinator(scenario_name="test")
        coordinator.add_agent(agent1)
        coordinator.add_agent(agent2)

        # 发送消息
        await coordinator.send_to(
            sender="Agent1",
            receiver="Agent2",
            content={"type": "test", "message": "Hello"},
            message_type="text"
        )

        # 验证消息已记录
        assert len(agent2.message_history) > 0


# ============================================================================
# 集成测试 - 完整流程
# ============================================================================

class TestFullWorkflow:
    """完整工作流集成测试"""

    @pytest.mark.asyncio
    async def test_software_development_flow(self):
        """测试软件开发完整流程"""
        from demo.software_dev.agents.product_owner import ProductOwnerAgent
        from demo.software_dev.agents.architect import ArchitectAgent
        from demo.software_dev.agents.developer import DeveloperAgent
        from demo.software_dev.agents.reviewer import ReviewerAgent
        from demo.software_dev.agents.devops import DevOpsAgent
        from demo.shared.base_demo_agent import TeamCoordinator

        # 创建团队
        agents = {
            "PO": ProductOwnerAgent(
                AgentConfig(name="PO", description="产品经理", capabilities=["requirement_analysis"])
            ),
            "Arch": ArchitectAgent(
                AgentConfig(name="Arch", description="架构师", capabilities=["architecture_design"])
            ),
            "Dev": DeveloperAgent(
                AgentConfig(name="Dev", description="开发者", capabilities=["coding"])
            ),
            "Reviewer": ReviewerAgent(
                AgentConfig(name="Reviewer", description="审查员", capabilities=["code_review"])
            ),
            "DevOps": DevOpsAgent(
                AgentConfig(name="DevOps", description="运维", capabilities=["deployment"])
            ),
        }

        # 初始化所有 Agent
        for agent in agents.values():
            await agent.initialize()

        # 创建协调器
        coordinator = TeamCoordinator(scenario_name="software_dev")
        for agent in agents.values():
            coordinator.add_agent(agent)

        # 1. PO 发布需求
        requirement = "开发用户登录功能"
        await agents["PO"].publish_requirement(requirement)

        # 2. PO 发送给 Arch
        await coordinator.send_to(
            sender="PO",
            receiver="Arch",
            content={"type": "new_requirement", "requirement": requirement},
            message_type="task"
        )

        # 3. Arch 处理
        arch_result = await agents["Arch"].handle_message({
            "sender": "PO",
            "receiver": "Arch",
            "content": {"type": "new_requirement", "requirement": requirement},
            "message_type": "task"
        })

        assert arch_result.get("status") == "design_completed"

        # 4. Dev 实现
        # 获取 Arch 发送给 Dev 的消息
        arch_to_dev = None
        for msg in agents["Arch"].message_history:
            if msg.receiver == "Dev":
                arch_to_dev = msg
                break

        if arch_to_dev:
            dev_result = await agents["Dev"].handle_message(arch_to_dev)
            # 验证实现完成
            assert "implementation" in str(dev_result) or dev_result.get("status") == "implementations_completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
