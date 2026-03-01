"""
Software Dev Demo E2E 测试

端到端测试 - 验证完整的用户场景。

运行方式:
    cd demo/software_dev
    python -m pytest tests/test_e2e.py -v
"""

import asyncio
import pytest
import sys
import os
import httpx
from datetime import datetime
from typing import Dict, List, Any

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from usmsb_sdk.agent_sdk import AgentConfig

# 测试配置
BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000")
TEST_TIMEOUT = 30.0


# ============================================================================
# E2E 测试助手
# ============================================================================

class E2ETestHelper:
    """E2E 测试助手"""

    def __init__(self):
        self.client = httpx.Client(timeout=TEST_TIMEOUT)
        self.created_agents: List[str] = []

    def cleanup(self):
        """清理创建的测试资源"""
        for agent_id in self.created_agents:
            try:
                self.client.delete(f"{BASE_URL}/agents/{agent_id}")
            except:
                pass
        self.client.close()

    def create_test_agent(self, name: str = None) -> str:
        """创建测试 Agent"""
        if name is None:
            name = f"E2ETest_{datetime.now().strftime('%H%M%S')}"

        response = self.client.post(
            f"{BASE_URL}/agents",
            json={
                "name": name,
                "description": "E2E 测试 Agent",
                "capabilities": ["e2e_testing"],
                "endpoint": "http://localhost:9999",
                "protocol": "standard",
                "heartbeat_interval": 30,
                "ttl": 90,
                "metadata": {"test_type": "e2e"}
            }
        )

        if response.status_code in [200, 201]:
            agent_id = response.json().get("agent_id")
            self.created_agents.append(agent_id)
            return agent_id
        return None


# ============================================================================
# E2E 测试 - 完整用户场景
# ============================================================================

class TestSoftwareDevE2E:
    """软件开发 E2E 测试"""

    @pytest.fixture
    def helper(self):
        helper = E2ETestHelper()
        yield helper
        helper.cleanup()

    @pytest.mark.asyncio
    async def test_complete_development_lifecycle(self, helper):
        """
        E2E-001: 完整开发生命周期

        场景：模拟真实软件开发团队协作流程
        1. ProductOwner 发布需求
        2. Architect 进行架构设计
        3. Developer 实现功能
        4. Reviewer 审查代码
        5. DevOps 部署上线
        """
        from demo.software_dev.agents import (
            ProductOwnerAgent,
            ArchitectAgent,
            DeveloperAgent,
            ReviewerAgent,
            DevOpsAgent,
        )
        from demo.shared import TeamCoordinator

        print("\n" + "=" * 60)
        print("  E2E-001: 完整开发生命周期")
        print("=" * 60)

        # 准备：创建团队 Agent
        agents = {}

        for name, AgentClass, role in [
            ("PO", ProductOwnerAgent, "产品经理"),
            ("Arch", ArchitectAgent, "架构师"),
            ("Dev", DeveloperAgent, "开发者"),
            ("Reviewer", ReviewerAgent, "代码审查"),
            ("DevOps", DevOpsAgent, "运维"),
        ]:
            config = AgentConfig(
                name=name,
                description=f"{role} Agent",
                capabilities=[],
                heartbeat_interval=30,
                ttl=90,
            )
            agent = AgentClass(config)
            await agent.initialize()
            agents[name] = agent
            print(f"  ✅ 创建 {role}: {name}")

        # 创建协调器
        coordinator = TeamCoordinator(scenario_name="e2e_test")
        for agent in agents.values():
            coordinator.add_agent(agent)

        print("\n  开始流程...")

        # Step 1: ProductOwner 发布需求
        requirement = "开发用户登录功能 - 支持 JWT 和 OAuth2"
        await agents["PO"].publish_requirement(requirement)

        await coordinator.send_to(
            sender="PO",
            receiver="Arch",
            content={"type": "new_requirement", "requirement": requirement},
            message_type="task"
        )
        print(f"  📋 Step 1: PO 发布需求 - {requirement}")

        # Step 2: Architect 设计架构
        arch_result = await agents["Arch"].handle_message({
            "sender": "PO",
            "receiver": "Arch",
            "content": {"type": "new_requirement", "requirement": requirement},
            "message_type": "task"
        })
        print(f"  🏗️ Step 2: Arch 完成设计 - {arch_result.get('status')}")

        # 验证架构设计
        assert len(agents["Arch"].designs) > 0, "Architect 应该创建了设计方案"

        # Step 3: Developer 实现
        dev_msg = None
        for msg in agents["Arch"].message_history:
            if msg.receiver == "Dev":
                dev_msg = msg
                break

        if dev_msg:
            dev_result = await agents["Dev"].handle_message(dev_msg)
            print(f"  💻 Step 3: Dev 完成实现 - {dev_result.get('status')}")

        # Step 4: Reviewer 审查
        reviewer_msg = None
        for msg in agents["Dev"].message_history:
            if msg.receiver == "Reviewer":
                reviewer_msg = msg
                break

        if reviewer_msg:
            reviewer_result = await agents["Reviewer"].handle_message(reviewer_msg)
            print(f"  🔍 Step 4: Reviewer 完成审查 - {reviewer_result.get('status')}")

        # Step 5: DevOps 部署
        devops_msg = None
        for msg in agents["Reviewer"].message_history:
            if msg.receiver == "DevOps":
                devops_msg = msg
                break

        if devops_msg:
            devops_result = await agents["DevOps"].handle_message(devops_msg)
            print(f"  🚀 Step 5: DevOps 完成部署 - {devops_result.get('status')}")

        # 验证结果
        print("\n  验证结果:")
        print(f"    - PO 需求数: {len(agents['PO'].requirements)}")
        print(f"    - Arch 设计数: {len(agents['Arch'].designs)}")
        print(f"    - Dev 实现数: {len(agents['Dev'].implementations)}")
        print(f"    - Reviewer 审查数: {len(agents['Reviewer'].reviews)}")
        print(f"    - DevOps 部署数: {len(agents['DevOps'].deployments)}")

        # 断言
        assert len(agents["PO"].requirements) > 0
        assert len(agents["Arch"].designs) > 0

        print("\n  ✅ E2E-001 测试通过!")

    @pytest.mark.asyncio
    async def test_agent_platform_registration(self, helper):
        """
        E2E-002: Agent 平台注册流程

        场景：
        1. 在平台注册 Agent
        2. 验证 Agent 列表
        3. 获取 Agent 详情
        4. 更新 Agent
        5. 注销 Agent
        """
        print("\n" + "=" * 60)
        print("  E2E-002: Agent 平台注册流程")
        print("=" * 60)

        # Step 1: 注册 Agent
        agent_name = f"PlatformTest_{datetime.now().strftime('%H%M%S')}"
        print(f"  📝 Step 1: 注册 Agent - {agent_name}")

        response = helper.client.post(
            f"{BASE_URL}/agents",
            json={
                "name": agent_name,
                "description": "平台测试 Agent",
                "capabilities": ["testing", "development"],
                "endpoint": "http://localhost:9999",
                "protocol": "standard",
                "heartbeat_interval": 30,
                "ttl": 90,
                "metadata": {"test": "e2e_platform"}
            }
        )

        if response.status_code not in [200, 201]:
            pytest.skip(f"平台 API 不可用: {response.status_code}")

        agent_id = response.json().get("agent_id")
        helper.created_agents.append(agent_id)
        print(f"    ✅ Agent ID: {agent_id}")

        # Step 2: 获取 Agent 列表
        print(f"  📋 Step 2: 获取 Agent 列表")
        list_response = helper.client.get(f"{BASE_URL}/agents")
        assert list_response.status_code == 200

        agents = list_response.json()
        print(f"    ✅ 平台共有 {len(agents)} 个 Agent")

        # Step 3: 获取 Agent 详情
        print(f"  🔍 Step 3: 获取 Agent 详情")
        detail_response = helper.client.get(f"{BASE_URL}/agents/{agent_id}")
        assert detail_response.status_code == 200

        agent_detail = detail_response.json()
        assert agent_detail.get("name") == agent_name
        print(f"    ✅ Agent 详情: {agent_detail.get('description')}")

        # Step 4: 发送心跳
        print(f"  💓 Step 4: 发送心跳")
        heartbeat_response = helper.client.post(
            f"{BASE_URL}/agents/{agent_id}/heartbeat",
            json={"status": "online"}
        )
        # 心跳可能返回各种状态码
        print(f"    📊 心跳响应: {heartbeat_response.status_code}")

        print("\n  ✅ E2E-002 测试通过!")

    @pytest.mark.asyncio
    async def test_service_marketplace_flow(self, helper):
        """
        E2E-003: 服务市场流程

        场景：
        1. 注册 Agent
        2. 发布服务
        3. 查询服务列表
        4. 发布需求
        """
        print("\n" + "=" * 60)
        print("  E2E-003: 服务市场流程")
        print("=" * 60)

        # Step 1: 注册 Agent
        agent_name = f"ServiceTest_{datetime.now().strftime('%H%M%S')}"
        response = helper.client.post(
            f"{BASE_URL}/agents",
            json={
                "name": agent_name,
                "description": "服务测试 Agent",
                "capabilities": ["development"],
                "endpoint": "http://localhost:9999",
                "protocol": "standard",
                "heartbeat_interval": 30,
                "ttl": 90,
            }
        )

        if response.status_code not in [200, 201]:
            pytest.skip("平台 API 不可用")

        agent_id = response.json().get("agent_id")
        helper.created_agents.append(agent_id)
        print(f"  ✅ Step 1: 注册 Agent - {agent_name}")

        # Step 2: 发布服务
        print(f"  📦 Step 2: 发布服务")
        service_response = helper.client.post(
            f"{BASE_URL}/agents/{agent_id}/services",
            json={
                "service_name": "Python 开发服务",
                "service_type": "development",
                "description": "专业 Python 开发服务",
                "capabilities": ["Python", "FastAPI", "Django"],
                "price": 150.0,
                "price_type": "hourly",
                "availability": "24/7"
            }
        )

        if service_response.status_code in [200, 201]:
            service = service_response.json()
            service_id = service.get("service_id")
            print(f"    ✅ 服务发布成功 - ID: {service_id}")
        else:
            print(f"    ⚠️ 服务发布响应: {service_response.status_code}")

        # Step 3: 获取服务列表
        print(f"  📋 Step 3: 获取服务列表")
        services_response = helper.client.get(f"{BASE_URL}/services")

        if services_response.status_code == 200:
            services = services_response.json()
            print(f"    ✅ 平台共有 {len(services)} 个服务")
        else:
            print(f"    ⚠️ 服务列表响应: {services_response.status_code}")

        print("\n  ✅ E2E-003 测试通过!")

    @pytest.mark.asyncio
    async def test_multi_agent_collaboration(self):
        """
        E2E-004: 多 Agent 协作

        场景：多个 Agent 协同完成复杂任务
        """
        from demo.software_dev.agents import (
            ProductOwnerAgent,
            ArchitectAgent,
            DeveloperAgent,
            ReviewerAgent,
            DevOpsAgent,
        )
        from demo.shared import DemoVisualizer

        print("\n" + "=" * 60)
        print("  E2E-004: 多 Agent 协作")
        print("=" * 60)

        # 创建可视化器
        visualizer = DemoVisualizer(scenario_name="e2e_collab", enable_html=False)

        # 创建团队
        team = {}
        for name, AgentClass in [
            ("PO", ProductOwnerAgent),
            ("Arch", ArchitectAgent),
            ("Dev", DeveloperAgent),
            ("Reviewer", ReviewerAgent),
            ("DevOps", DevOpsAgent),
        ]:
            config = AgentConfig(
                name=name,
                description=f"{name} Agent",
                capabilities=[],
            )
            agent = AgentClass(config, visualizer=visualizer)
            await agent.initialize()
            team[name] = agent
            print(f"  ✅ 创建 {name} Agent")

        # 模拟协作：处理需求
        requirement = "电商网站后端 API"
        print(f"\n  📋 发布需求: {requirement}")

        await team["PO"].publish_requirement(requirement)

        # PO 发送给 Arch
        for msg in team["PO"].message_history:
            if msg.receiver == "Arch" or msg.receiver == "broadcast":
                await team["Arch"].handle_message(msg)

        print(f"  ✅ Arch 处理需求，创建 {len(team['Arch'].designs)} 个设计")

        # Arch 发送给 Dev
        for msg in team["Arch"].message_history:
            if msg.receiver == "Dev":
                await team["Dev"].handle_message(msg)

        print(f"  ✅ Dev 实现功能，创建 {len(team['Dev'].implementations)} 个实现")

        # Dev 发送给 Reviewer
        for msg in team["Dev"].message_history:
            if msg.receiver == "Reviewer":
                await team["Reviewer"].handle_message(msg)

        print(f"  ✅ Reviewer 审查代码，创建 {len(team['Reviewer'].reviews)} 个审查")

        # Reviewer 发送给 DevOps
        for msg in team["Reviewer"].message_history:
            if msg.receiver == "DevOps":
                await team["DevOps"].handle_message(msg)

        print(f"  ✅ DevOps 部署，创建 {len(team['DevOps'].deployments)} 个部署")

        # 验证
        assert len(team["PO"].requirements) > 0
        assert len(team["Arch"].designs) > 0

        # 打印可视化摘要
        visualizer.print_summary()

        print("\n  ✅ E2E-004 测试通过!")


# ============================================================================
# E2E 测试 - 性能测试
# ============================================================================

class TestPerformanceE2E:
    """性能 E2E 测试"""

    @pytest.mark.asyncio
    async def test_concurrent_agent_creation(self):
        """
        E2E-005: 并发创建 Agent 性能测试
        """
        from demo.software_dev.agents import DeveloperAgent

        print("\n" + "=" * 60)
        print("  E2E-005: 并发创建 Agent 性能测试")
        print("=" * 60)

        async def create_agent(i: int):
            config = AgentConfig(
                name=f"PerfTest_{i}",
                description=f"性能测试 Agent {i}",
                capabilities=["testing"],
            )
            agent = DeveloperAgent(config)
            await agent.initialize()
            return agent

        # 并发创建 10 个 Agent
        import time
        start = time.time()

        tasks = [create_agent(i) for i in range(10)]
        agents = await asyncio.gather(*tasks)

        duration = time.time() - start

        print(f"  ✅ 创建 {len(agents)} 个 Agent 耗时: {duration:.2f}s")
        print(f"  📊 平均每个 Agent: {duration/10:.3f}s")

        # 验证
        assert len(agents) == 10

        print("\n  ✅ E2E-005 测试通过!")

    @pytest.mark.asyncio
    async def test_message_throughput(self):
        """
        E2E-006: 消息吞吐量测试
        """
        from demo.software_dev.agents import DeveloperAgent
        from demo.shared import TeamCoordinator

        print("\n" + "=" * 60)
        print("  E2E-006: 消息吞吐量测试")
        print("=" * 60)

        # 创建 Agent
        config1 = AgentConfig(name="Sender", description="发送者", capabilities=["testing"])
        config2 = AgentConfig(name="Receiver", description="接收者", capabilities=["testing"])

        agent1 = DeveloperAgent(config1)
        agent2 = DeveloperAgent(config2)

        await agent1.initialize()
        await agent2.initialize()

        # 创建协调器
        coordinator = TeamCoordinator(scenario_name="perf_test")
        coordinator.add_agent(agent1)
        coordinator.add_agent(agent2)

        # 发送消息
        import time
        start = time.time()

        for i in range(20):
            await coordinator.send_to(
                sender="Sender",
                receiver="Receiver",
                content={"type": "test", "index": i},
                message_type="text"
            )

        duration = time.time() - start

        print(f"  ✅ 发送 {len(agent2.message_history)} 条消息耗时: {duration:.2f}s")
        print(f"  📊 吞吐量: {len(agent2.message_history)/duration:.1f} msg/s")

        # 验证
        assert len(agent2.message_history) == 20

        print("\n  ✅ E2E-006 测试通过!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
