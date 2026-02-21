"""
Meta Agent 测试
"""

import asyncio
import sys

sys.path.insert(0, "../../../../")

from usmsb_sdk.platform.external.meta_agent import MetaAgent, MetaAgentConfig


async def test_meta_agent():
    """测试 Meta Agent"""
    print("=== 测试 Meta Agent ===")

    config = MetaAgentConfig(name="TestMetaAgent", description="测试用 Meta Agent")

    agent = MetaAgent(config)
    print(f"Agent ID: {agent.agent_id}")
    print(f"Config: {agent.config.name}")

    print("\n=== 测试工具注册 ===")
    tools = agent.get_available_tools()
    print(f"已注册工具数量: {len(tools)}")
    for tool in tools[:5]:
        print(f"  - {tool['name']}: {tool['description']}")

    print("\n=== 测试执行工具 ===")
    result = await agent.execute_tool("health_check", {"target": "system"})
    print(f"health_check 结果: {result}")

    result = await agent.execute_tool("get_node_status", {})
    print(f"get_node_status 结果: {result}")

    print("\n=== 测试创建钱包 ===")
    result = await agent.execute_tool("create_wallet", {"chain": "ethereum"})
    print(f"create_wallet 结果: {result}")

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(test_meta_agent())
