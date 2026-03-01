"""
软件开发协作 Demo - Agent SDK 核心功能演示

运行方式:
    cd demo/software_dev
    python run_demo.py

场景：模拟软件开发团队，5个AI Agent协作完成功能开发
"""

import asyncio
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo.shared import DemoAgent, DemoVisualizer
from demo.software_dev.agents import (
    ProductOwnerAgent,
    ArchitectAgent,
    DeveloperAgent,
    ReviewerAgent,
    DevOpsAgent,
)
from usmsb_sdk.agent_sdk import AgentConfig, CapabilityDefinition


# ============================================================================
# 团队角色配置
# ============================================================================

TEAM_CONFIG = [
    {
        "name": "ProductOwner",
        "role": "产品经理",
        "class": ProductOwnerAgent,
        "capabilities": ["requirement_analysis", "prioritization", "acceptance_testing"],
    },
    {
        "name": "Architect",
        "role": "架构师",
        "class": ArchitectAgent,
        "capabilities": ["architecture_design", "tech_selection", "api_design"],
    },
    {
        "name": "Developer",
        "role": "开发者",
        "class": DeveloperAgent,
        "capabilities": ["coding", "testing", "debugging"],
    },
    {
        "name": "Reviewer",
        "role": "代码审查",
        "class": ReviewerAgent,
        "capabilities": ["code_review", "security_audit"],
    },
    {
        "name": "DevOps",
        "role": "运维",
        "class": DevOpsAgent,
        "capabilities": ["ci_cd", "deployment", "monitoring"],
    },
]


# ============================================================================
# 演示流程
# ============================================================================

async def demo_agent_lifecycle(agents: dict, visualizer: DemoVisualizer):
    """演示：Agent 生命周期"""
    print("\n📋 Agent 生命周期演示")

    developer = agents["Developer"]

    # 启动
    await developer.start()
    print(f"  ✅ {developer.name} 已启动")

    # 暂停
    await developer.pause()
    print(f"  ⏸️ {developer.name} 已暂停")

    # 恢复
    await developer.resume()
    print(f"  ▶️ {developer.name} 已恢复")

    # 获取指标
    metrics = developer.metrics
    print(f"\n  📊 Agent 指标:")
    print(f"     - 消息接收: {metrics.get('messages_received', 0)}")
    print(f"     - 消息发送: {metrics.get('messages_sent', 0)}")
    print(f"     - 技能执行: {metrics.get('skills_executed', 0)}")

    # 停止
    await developer.stop()
    print(f"\n  ⏹️ {developer.name} 已停止")


async def demo_skills_and_capabilities(agents: dict, visualizer: DemoVisualizer):
    """演示：技能和能力"""
    print("\n🎯 技能与能力演示")

    developer = agents["Developer"]

    # 列出技能
    skills = developer.skills
    print(f"  📝 已注册技能 ({len(skills)} 个):")
    for skill in skills:
        print(f"     - {skill.name}: {skill.description}")

    # 列出能力
    capabilities = developer.capabilities
    print(f"\n  💪 已注册能力 ({len(capabilities)} 个):")
    for cap in capabilities:
        print(f"     - {cap.name}: {cap.description} (级别: {cap.level})")


async def demo_messaging(agents: dict, visualizer: DemoVisualizer):
    """演示：Agent 间通信"""
    print("\n💬 Agent 通信演示")

    developer = agents["Developer"]
    reviewer = agents["Reviewer"]

    # 启动 Developer 以便发送消息
    await developer.start()

    # 发送消息
    msg = await developer.send_message(
        receiver="Reviewer",
        content={"type": "code_submission", "task": "用户登录API"},
        message_type="task"
    )
    print(f"  ✅ 消息已发送给 Reviewer")

    # 消息历史
    history = developer.message_history
    print(f"  📬 消息历史 ({len(history)} 条)")

    await developer.stop()


async def demo_agent_info(agents: dict, visualizer: DemoVisualizer):
    """演示：Agent 信息"""
    print("\nℹ️ Agent 信息演示")

    for name, agent in agents.items():
        print(f"\n  [{name}]")
        print(f"    描述: {agent.config.description}")
        print(f"    状态: {agent.state.value if hasattr(agent.state, 'value') else agent.state}")
        print(f"    技能数: {len(agent.skills)}")
        print(f"    能力数: {len(agent.capabilities)}")


# ============================================================================
# 主函数
# ============================================================================

async def main():
    print("\n" + "=" * 50)
    print("  软件开发协作 Demo")
    print("  Agent SDK 核心功能演示")
    print("=" * 50)

    # 初始化可视化器
    visualizer = DemoVisualizer(scenario_name="software_dev", enable_html=False)

    # 创建 Agent 团队
    print("\n📦 创建开发团队...")
    created_agents = {}

    for cfg in TEAM_CONFIG:
        # 将字符串 capabilities 转换为 CapabilityDefinition 对象
        capabilities = [
            CapabilityDefinition(
                name=c,
                description=c.replace("_", " ").title(),
                category="development",
                level="advanced"
            )
            for c in cfg["capabilities"]
        ]
        config = AgentConfig(
            name=cfg["name"],
            description=f"{cfg['role']} AI Agent",
            capabilities=capabilities,
            heartbeat_interval=30,
            ttl=90,
        )

        agent = cfg["class"](config, visualizer=visualizer)
        await agent.initialize()
        created_agents[cfg["name"]] = agent
        print(f"  ✅ {cfg['name']} ({cfg['role']})")

    print(f"\n共 {len(created_agents)} 个 Agent")

    # 演示各项功能
    await demo_agent_info(created_agents, visualizer)
    await demo_agent_lifecycle(created_agents, visualizer)
    await demo_skills_and_capabilities(created_agents, visualizer)
    await demo_messaging(created_agents, visualizer)

    # 打印日志摘要
    visualizer.print_summary()

    print("\n✅ Demo 完成!\n")


if __name__ == "__main__":
    asyncio.run(main())
