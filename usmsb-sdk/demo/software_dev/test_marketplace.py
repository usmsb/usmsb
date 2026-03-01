"""
市场功能演示脚本

展示Agent如何使用市场功能:
1. 发布服务
2. 发现需求
3. 查找工作机会
"""

import asyncio
import sys
import os

# 添加路径
demo_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(demo_dir)
usmsb_root = os.path.dirname(project_root)
sys.path.insert(0, usmsb_root)
sys.path.insert(0, os.path.join(usmsb_root, 'src'))

from usmsb_sdk.agent_sdk import AgentConfig, CapabilityDefinition, ProtocolType, ProtocolConfig
from usmsb_sdk.agent_sdk.marketplace import ServiceDefinition
from demo.software_dev.agents import DeveloperAgent


async def demo_marketplace():
    """演示市场功能"""

    print("\n" + "=" * 50)
    print("  市场功能演示")
    print("=" * 50)

    # 创建Developer Agent
    capabilities = [
        CapabilityDefinition(
            name="coding",
            description="编程",
            category="development",
            level="advanced"
        )
    ]

    protocols = {
        ProtocolType.HTTP: ProtocolConfig(
            protocol_type=ProtocolType.HTTP,
            enabled=False,
        ),
    }

    config = AgentConfig(
        name="Developer_Market",
        description="开发者市场演示",
        capabilities=capabilities,
        protocols=protocols,
        auto_register=False,
    )

    agent = DeveloperAgent(config, visualizer=None)

    print("\n🔄 启动Agent...")
    await agent.start()
    print("  ✅ Agent已启动")

    print("\n📦 步骤1: 发布服务")

    # 发布服务 - 使用ServiceDefinition
    service_def = ServiceDefinition(
        service_name="Web开发服务",
        description="专业Web开发服务",
        category="development",
        skills=["frontend", "backend"],
        price=1000,
        price_type="fixed"
    )
    service = await agent.offer_service(service_def)
    print(f"  ✅ 服务发布成功: {service}")

    print("\n🔍 步骤2: 查找工作机会")

    # 查找工作机会
    opportunities = await agent.find_work(capabilities=["coding", "testing"])
    print(f"  发现 {len(opportunities)} 个工作机会")

    print("\n📋 步骤3: 查找需求")

    # 查找需求 (通过platform API)
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:8000/demands") as resp:
            demands = await resp.json()
            print(f"  发现 {len(demands)} 个需求")

    print("\n👥 步骤4: 查找Worker")

    # 查找Worker
    workers = await agent.find_workers(required_skills=["coding"])
    print(f"  发现 {len(workers)} 个Worker")

    print("\n🛑 停止Agent...")
    await agent.stop()
    print("  ✅ Agent已停止")

    print("\n" + "=" * 50)
    print("  市场功能演示完成!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(demo_marketplace())
