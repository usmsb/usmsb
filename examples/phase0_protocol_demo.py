# -*- coding: utf-8 -*-
"""
Phase 0: Protocol Integration 示例

展示协议整合层的功能。

运行方式：
    python examples/phase0_protocol_demo.py
"""

import sys
sys.path.insert(0, 'src')

from usmsb_sdk.protocol import (
    MultiWallet,
    x402Router,
    Currency,
    AgentCard,
    AgentCardRegistry,
    A2AAdapter,
    A2AMessageType,
    MCPRegistry,
    MCPToolBuilder,
    MCPGateway,
    ToolCategory,
)


def demo_multi_wallet():
    """多币种钱包演示"""
    print("=" * 60)
    print("多币种钱包演示")
    print("=" * 60)
    
    wallet = MultiWallet(agent_id="agent_001")
    
    # 添加地址
    print("\n[添加地址]")
    wallet.add_address("0x1234567890abcdef", "USDC", "Main Wallet")
    wallet.add_address("vibe_token_address", "VIBE", "VIBE Rewards")
    print(f"  添加了 USDC 和 VIBE 地址")
    
    # 模拟余额
    print("\n[模拟余额]")
    wallet.update_balance("0x1234567890abcdef", "USDC", 1000.0)
    wallet.update_balance("vibe_token_address", "VIBE", 5000.0)
    print(f"  USDC 余额: {wallet.get_balance('0x1234567890abcdef', 'USDC'):.2f}")
    print(f"  VIBE 余额: {wallet.get_balance('vibe_token_address', 'VIBE'):.2f}")
    
    # 查询总资产
    print("\n[查询总资产]")
    wallet.set_vibe_usd_rate(0.01)
    total_usd = wallet.get_total_value_usd()
    print(f"  总资产 (USD): ${total_usd:.2f}")
    
    # 支付
    print("\n[发起支付]")
    success = wallet.pay(
        from_address="0x1234567890abcdef",
        to_address="0xabcdef1234567890",
        amount=100.0,
        currency="USDC"
    )
    print(f"  支付成功: {success}")
    print(f"  剩余 USDC: {wallet.get_balance('0x1234567890abcdef', 'USDC'):.2f}")


def demo_x402_router():
    """x402 支付路由演示"""
    print("\n" + "=" * 60)
    print("x402 支付路由演示")
    print("=" * 60)
    
    router = x402Router()
    
    # 创建支付请求
    print("\n[创建支付请求]")
    request = router.create_payment(
        from_address="0x123...",
        to_address="0x456...",
        amount=10.0,
        currency=Currency.USDC,
        memo="Service payment"
    )
    print(f"  支付 ID: {request.id[:20]}...")
    print(f"  金额: {request.amount} {request.currency.value}")
    
    # 处理支付
    print("\n[处理支付]")
    result = router.process_payment(request)
    print(f"  成功: {result.success}")
    if result.success:
        print(f"  交易哈希: {result.transaction_hash[:30]}...")
        print(f"  手续费: {result.fee_paid:.4f}")
        print(f"  实付: {result.amount_paid:.4f}")
    
    # 验证支付
    print("\n[验证支付]")
    verified = router.verify_payment(result.transaction_hash)
    print(f"  验证结果: {'通过' if verified else '失败'}")
    
    # 统计
    print("\n[支付统计]")
    stats = router.get_payment_stats()
    print(f"  总支付数: {stats['total_payments']}")
    print(f"  成功: {stats['completed']}")


def demo_a2a_card():
    """A2A Agent Card 演示"""
    print("\n" + "=" * 60)
    print("A2A Agent Card 演示")
    print("=" * 60)
    
    registry = AgentCardRegistry()
    
    # 创建 Agent Card
    print("\n[创建 Agent Card]")
    card1 = AgentCard(
        id="agent_coder",
        name="Coding Agent",
        description="专业的代码编写和重构 Agent",
        capabilities=["coding", "refactoring", "testing"],
        reputation=0.85,
        status="online",
        hourly_rate={"USDC": 50.0}
    )
    
    card2 = AgentCard(
        id="agent_researcher",
        name="Research Agent",
        description="专业的研究分析 Agent",
        capabilities=["research", "analysis", "writing"],
        reputation=0.90,
        status="online",
        hourly_rate={"USDC": 40.0}
    )
    
    # 注册
    print("\n[注册 Agent]")
    registry.register(card1)
    registry.register(card2)
    print(f"  注册了 2 个 Agent")
    
    # 发现 Agent
    print("\n[发现 Agent - 搜索 coding 能力]")
    agents = registry.discover(capabilities=["coding"], min_reputation=0.5)
    for agent in agents:
        print(f"  - {agent.name}: {agent.capabilities}")
    
    # 搜索
    print("\n[搜索 Agent - 'research']")
    results = registry.search("research")
    for agent in results:
        print(f"  - {agent.name}: {agent.description}")
    
    # 统计
    print("\n[统计信息]")
    stats = registry.get_statistics()
    print(f"  总 Agent: {stats['total_agents']}")


def demo_a2a_adapter():
    """A2A 通信适配器演示"""
    print("\n" + "=" * 60)
    print("A2A 通信适配器演示")
    print("=" * 60)
    
    # 创建两个 Agent 的适配器
    adapter_alice = A2AAdapter(agent_id="alice")
    adapter_bob = A2AAdapter(agent_id="bob")
    
    # 发送消息
    print("\n[Alice 发送消息给 Bob]")
    msg = adapter_alice.send_message(
        to_agent="bob",
        message_type=A2AMessageType.QUERY,
        subject="Task Request",
        payload={"task": "分析数据"}
    )
    print(f"  消息 ID: {msg.id[:20]}...")
    print(f"  发送给: {msg.to_agent}")
    
    # Bob 接收消息（模拟传递）
    print("\n[Bob 接收消息]")
    adapter_bob.deliver_message(msg)
    received = adapter_bob.receive_message()
    if received:
        print(f"  收到消息: {received.subject}")
        print(f"  内容: {received.payload}")
    
    # 委托任务
    print("\n[Alice 委托任务给 Bob]")
    task = adapter_alice.delegate_task(
        to_agent="bob",
        description="数据分析任务",
        input_data={"dataset": "sales_2024.csv"},
        reward=5.0,
        currency="USDC"
    )
    print(f"  任务 ID: {task.id[:20]}...")
    print(f"  描述: {task.description}")
    print(f"  报酬: {task.reward} {task.currency}")


def demo_mcp_registry():
    """MCP 工具注册演示"""
    print("\n" + "=" * 60)
    print("MCP 工具注册演示")
    print("=" * 60)
    
    registry = MCPRegistry()
    
    # 创建工具
    print("\n[创建 MCP 工具]")
    search_tool = (MCPToolBuilder()
        .name("web_search")
        .description("Search the internet for information")
        .category(ToolCategory.SEARCH)
        .provider("usmsb")
        .input_prop("query", "string", "Search query")
        .input_prop("limit", "integer", "Result limit")
        .input_required("query")
        .output_prop("results", "array", "Search results")
        .cost(0.01)
        .capabilities("research", "information_gathering")
        .tags("search", "web", "research")
        .build())
    
    calc_tool = (MCPToolBuilder()
        .name("calculator")
        .description("Perform calculations")
        .category(ToolCategory.COMPUTATION)
        .provider("usmsb")
        .input_prop("expression", "string", "Math expression")
        .input_required("expression")
        .output_prop("result", "number", "Calculation result")
        .cost(0.001)
        .tags("math", "calculation")
        .build())
    
    # 注册
    print("\n[注册工具]")
    registry.register(search_tool)
    registry.register(calc_tool)
    print(f"  注册了 {len(registry.get_all_tools())} 个工具")
    
    # 发现工具
    print("\n[发现工具 - 'search' 关键词]")
    tools = registry.discover(query="search")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")
    
    # 按类别
    print("\n[发现工具 - SEARCH 类别]")
    tools = registry.get_by_category(ToolCategory.SEARCH)
    for tool in tools:
        print(f"  - {tool.name}")
    
    # 统计
    print("\n[统计信息]")
    stats = registry.get_statistics()
    print(f"  总工具: {stats['total_tools']}")
    print(f"  平均成本: {stats['average_cost']:.4f}")


def demo_mcp_gateway():
    """MCP 网关演示"""
    print("\n" + "=" * 60)
    print("MCP 网关演示")
    print("=" * 60)
    
    gateway = MCPGateway()
    
    # 注册工具
    print("\n[注册工具到网关]")
    
    def web_search_handler(query: str, limit: int = 10):
        """模拟搜索处理函数"""
        return {"results": [f"Result {i} for {query}" for i in range(limit)]}
    
    def calculator_handler(expression: str):
        """模拟计算处理函数"""
        try:
            result = eval(expression)
            return {"result": result}
        except Exception as e:
            return {"error": str(e)}
    
    # 构建并注册
    search_tool = (MCPToolBuilder()
        .name("web_search")
        .description("Search the internet")
        .category(ToolCategory.SEARCH)
        .input_prop("query", "string", "Search query")
        .input_prop("limit", "integer", "Result limit")
        .input_required("query")
        .output_prop("results", "array", "Results")
        .build())
    
    gateway.register_tool(search_tool, web_search_handler)
    
    calc_tool = (MCPToolBuilder()
        .name("calculator")
        .description("Calculate math")
        .category(ToolCategory.COMPUTATION)
        .input_prop("expression", "string", "Expression")
        .input_required("expression")
        .output_prop("result", "number", "Result")
        .build())
    
    gateway.register_tool(calc_tool, calculator_handler)
    
    print(f"  注册了 {len(gateway.registry.get_all_tools())} 个工具")
    
    # 调用工具
    print("\n[调用 web_search]")
    try:
        result = gateway.call_tool(
            tool_name="web_search",
            params={"query": "AI news", "limit": 5},
            agent_id="test_agent"
        )
        print(f"  结果: {result}")
    except Exception as e:
        print(f"  错误: {e}")
    
    print("\n[调用 calculator]")
    try:
        result = gateway.call_tool(
            tool_name="calculator",
            params={"expression": "2 + 2"},
            agent_id="test_agent"
        )
        print(f"  2 + 2 = {result['result']}")
    except Exception as e:
        print(f"  错误: {e}")
    
    # 统计
    print("\n[调用统计]")
    stats = gateway.get_statistics()
    print(f"  总调用: {stats['total_calls']}")
    print(f"  成功率: {stats['success_rate']:.2%}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("USMSB Phase 0: Protocol Integration 演示")
    print("=" * 60)
    print("\n涵盖模块:")
    print("- MultiWallet: 多币种钱包")
    print("- x402Router: 机器间微支付")
    print("- A2ACard: Agent 能力描述卡")
    print("- A2AAdapter: Agent 间通信")
    print("- MCPRegistry: 工具注册")
    print("- MCPGateway: MCP 网关")
    
    try:
        demo_multi_wallet()
        demo_x402_router()
        demo_a2a_card()
        demo_a2a_adapter()
        demo_mcp_registry()
        demo_mcp_gateway()
        
        print("\n" + "=" * 60)
        print("演示完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
