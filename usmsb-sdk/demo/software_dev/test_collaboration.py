"""
协作功能演示脚本

展示Agent如何使用协作功能:
1. 创建协作会话
2. 加入协作
3. 提交贡献
4. 查看协作状态
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
from demo.shared import DemoAgent
from demo.software_dev.agents import (
    ProductOwnerAgent,
    ArchitectAgent,
    DeveloperAgent,
)


async def demo_collaboration():
    """演示协作功能"""

    print("\n" + "=" * 50)
    print("  协作功能演示")
    print("=" * 50)

    # 创建ProductOwner Agent
    capabilities = [
        CapabilityDefinition(
            name="requirement_analysis",
            description="需求分析",
            category="development",
            level="advanced"
        )
    ]

    protocols = {
        ProtocolType.HTTP: ProtocolConfig(
            protocol_type=ProtocolType.HTTP,
            enabled=False,  # 不启动HTTP服务器
        ),
    }

    config = AgentConfig(
        name="ProductOwner_Demo",
        description="产品经理演示",
        capabilities=capabilities,
        protocols=protocols,
        auto_register=False,
    )

    agent = ProductOwnerAgent(config, visualizer=None)

    # 启动Agent以初始化组件
    print("\n🔄 启动Agent...")
    await agent.start()
    print("  ✅ Agent已启动")

    print("\n📋 步骤1: 创建协作会话")

    # 创建协作会话
    session = await agent.start_collaboration(
        goal="开发一个电商平台",
        required_skills=["frontend", "backend", "database"],
        mode="parallel",
    )

    if session:
        print(f"  ✅ 协作会话创建成功: {session.session_id}")
        print(f"  📊 状态: {session.status}")
    else:
        print("  ❌ 创建失败")
        return

    print("\n👥 步骤2: 获取可用Agent")

    # 获取可用Agent
    agents = await agent.discover_by_capability("coding")
    print(f"  发现 {len(agents)} 个可用Agent")
    for a in agents[:3]:
        print(f"    - {a.name if hasattr(a, 'name') else a}")

    print("\n🎯 步骤3: 加入协作")

    # 加入协作
    join_result = await agent.join_collaboration(session.session_id)
    print(f"  ✅ 加入协作成功")

    print("\n📝 步骤4: 提交贡献")

    # 提交贡献
    contribution = await agent.contribute(
        session_id=session.session_id,
        output={
            "type": "requirement_document",
            "content": "电商平台需求规格说明书 v1.0",
            "sections": ["用户故事", "功能列表", "非功能需求"]
        }
    )
    print(f"  ✅ 贡献提交成功: {contribution}")

    print("\n📊 步骤5: 获取协作状态")

    # 获取协作列表
    sessions = await agent.list_collaborations()
    print(f"  总会话数: {len(sessions)}")
    for s in sessions:
        print(f"    - {s.session_id}: {s.status}")

    print("\n🛑 停止Agent...")
    await agent.stop()
    print("  ✅ Agent已停止")

    print("\n" + "=" * 50)
    print("  协作功能演示完成!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(demo_collaboration())
