# -*- coding: utf-8 -*-
"""
ValueSelfLoop 示例

展示如何使用 ValueSelfLoop 实现价值自循环。

运行方式：
    python examples/l3_value_self_loop_demo.py

关键概念：
- 价值循环：服务 → 价值 → VIBE → 新目标 → 新服务
- 不需要外部注入，Agent 通过服务交换维持运转
"""

import sys
sys.path.insert(0, 'src')

from usmsb_sdk.l3 import (
    ValueSelfLoop,
    VIBEToken,
    ServiceType,
    ValueStatus,
)


def demo_basic_service_cycle():
    """基础服务循环演示"""
    print("=" * 60)
    print("基础服务循环演示")
    print("=" * 60)
    
    # 创建 ValueSelfLoop
    value_loop = ValueSelfLoop()
    
    # 1. 提供服务
    print("\n[1] Agent_001 为 Agent_002 提供服务")
    service = value_loop.provide_service(
        provider_id="agent_001",
        consumer_id="agent_002",
        service_type=ServiceType.COMPUTATION,
        description="数据处理服务",
        difficulty=0.7,
        urgency=0.8
    )
    print(f"    服务创建: {service.id}")
    print(f"    状态: {service.status.value}")
    
    # 2. 完成服务
    print("\n[2] 服务完成，生成价值记录")
    value_record = value_loop.complete_service(service.id, quality_score=0.8)
    print(f"    基础价值: {value_record.raw_value:.2f}")
    print(f"    稀缺性加成: {value_record.scarcity_bonus:.2f}")
    print(f"    最终价值: {value_record.final_value:.2f}")
    print(f"    状态: {value_record.status.value}")
    
    # 3. 确认服务
    print("\n[3] Agent_002 确认服务")
    value_record = value_loop.verify_service(service.id, quality_score=0.85)
    print(f"    最终价值（更新后）: {value_record.final_value:.2f}")
    print(f"    状态: {value_record.status.value}")
    
    # 4. 转换为 VIBE
    print("\n[4] 价值转换为 VIBE Token")
    vibe_resource = value_loop.convert_to_vibe(value_record.id)
    print(f"    转换数量: {vibe_resource.quantity:.4f} VIBE")
    
    # 5. 检查余额
    print("\n[5] Agent_001 的 VIBE 余额")
    balance = value_loop.get_agent_vibe_balance("agent_001")
    print(f"    余额: {balance:.4f} VIBE")


def demo_complete_circular_flow():
    """完整价值循环演示"""
    print("\n" + "=" * 60)
    print("完整价值循环演示")
    print("=" * 60)
    
    value_loop = ValueSelfLoop()
    
    print("\n[完整循环] Agent_A → Agent_B → Agent_A")
    
    result = value_loop.execute_complete_cycle(
        provider_id="agent_a",
        consumer_id="agent_b",
        service_type=ServiceType.DATA_PROCESSING,
        description="批量数据处理",
        difficulty=0.6,
        urgency=0.7,
        quality_score=0.85
    )
    
    print(f"\n    服务ID: {result['service_id'][:20]}...")
    print(f"    VIBE 获得: {result['vibe_amount']:.4f}")
    print(f"    新余额: {result['new_balance']:.4f}")
    print(f"    触发新目标: {'是' if result['new_goal'] else '否'}")
    
    if result['new_goal']:
        print(f"    目标名称: {result['new_goal']['name']}")


def demo_multiple_agents():
    """多 Agent 循环演示"""
    print("\n" + "=" * 60)
    print("多 Agent 价值循环演示")
    print("=" * 60)
    
    value_loop = ValueSelfLoop()
    
    agents = ["agent_x", "agent_y", "agent_z"]
    
    print("\n[场景] 3 个 Agent 相互提供服务")
    
    # Agent X → Agent Y
    print("\n  Agent_X → Agent_Y (计算服务)")
    result1 = value_loop.execute_complete_cycle(
        provider_id="agent_x",
        consumer_id="agent_y",
        service_type=ServiceType.COMPUTATION,
        description="复杂计算",
        difficulty=0.8,
        urgency=0.9
    )
    print(f"    VIBE: {result1['vibe_amount']:.4f}")
    
    # Agent Y → Agent Z
    print("\n  Agent_Y → Agent_Z (知识查询)")
    result2 = value_loop.execute_complete_cycle(
        provider_id="agent_y",
        consumer_id="agent_z",
        service_type=ServiceType.KNOWLEDGE_QUERY,
        description="市场分析",
        difficulty=0.5,
        urgency=0.6
    )
    print(f"    VIBE: {result2['vibe_amount']:.4f}")
    
    # Agent Z → Agent X
    print("\n  Agent_Z → Agent_X (协调服务)")
    result3 = value_loop.execute_complete_cycle(
        provider_id="agent_z",
        consumer_id="agent_x",
        service_type=ServiceType.COORDINATION,
        description="资源协调",
        difficulty=0.6,
        urgency=0.5
    )
    print(f"    VIBE: {result3['vibe_amount']:.4f}")
    
    # 统计
    print("\n[循环统计]")
    for agent_id in agents:
        stats = value_loop.get_circular_flow_stats(agent_id)
        print(f"\n  {agent_id}:")
        print(f"    服务次数: {stats.total_services}")
        print(f"    创造价值: {stats.total_value_created:.4f}")
        print(f"    VIBE 余额: {value_loop.get_agent_vibe_balance(agent_id):.4f}")


def demo_value_self_sufficiency():
    """价值自足演示"""
    print("\n" + "=" * 60)
    print("价值自足演示（连续循环，无外部注入）")
    print("=" * 60)
    
    value_loop = ValueSelfLoop()
    
    print("\n[场景] Agent_1 连续为 Agent_2 提供 5 次服务")
    print("（模拟价值内循环，不需要外部资金注入）\n")
    
    total_vibe = 0.0
    
    for i in range(5):
        result = value_loop.execute_complete_cycle(
            provider_id="agent_1",
            consumer_id="agent_2",
            service_type=ServiceType.DATA_PROCESSING,
            description=f"第 {i+1} 次数据处理",
            difficulty=0.5 + (i * 0.05),  # 难度递增
            urgency=0.6
        )
        total_vibe += result['vibe_amount']
        
        print(f"  第 {i+1} 次服务:")
        print(f"    获得 VIBE: {result['vibe_amount']:.4f}")
        print(f"    累计 VIBE: {total_vibe:.4f}")
        print(f"    当前余额: {result['new_balance']:.4f}")
        
        # 检查资源是否充足，触发新目标
        if result['new_goal']:
            print(f"    ⚡ 触发新目标: {result['new_goal']['name']}")
    
    print(f"\n[结果]")
    print(f"  5 次服务累计获得: {total_vibe:.4f} VIBE")
    print(f"  Agent_1 最终余额: {value_loop.get_agent_vibe_balance('agent_1'):.4f} VIBE")


def demo_scarcity_bonus():
    """稀缺性加成演示"""
    print("\n" + "=" * 60)
    print("稀缺性加成演示")
    print("=" * 60)
    
    value_loop = ValueSelfLoop()
    
    print("\n[场景] 不同服务类型的稀缺性加成")
    
    service_types = [
        (ServiceType.MEDIATION, "调解服务"),
        (ServiceType.COORDINATION, "协调服务"),
        (ServiceType.CREATION, "创造服务"),
        (ServiceType.COMPUTATION, "计算服务"),
        (ServiceType.RESOURCE_SHARING, "资源共享"),
    ]
    
    for service_type, name in service_types:
        result = value_loop.execute_complete_cycle(
            provider_id="provider_1",
            consumer_id="consumer_1",
            service_type=service_type,
            description=f"{name}测试",
            difficulty=0.5,
            urgency=0.5
        )
        
        # 获取价值记录
        value_record = value_loop.value_ledger.get_value_record(result['value_record_id'])
        
        print(f"\n  {name}:")
        print(f"    基础价值: {value_record.raw_value:.2f}")
        print(f"    稀缺性加成: ×{value_record.scarcity_bonus:.2f}")
        print(f"    最终价值: {value_record.final_value:.2f}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("USMSB L3 ValueSelfLoop 演示")
    print("=" * 60)
    print("\n核心概念：价值自循环")
    print("- Agent 通过服务交换创造价值")
    print("- 价值转换为 VIBE Token")
    print("- VIBE 支持新目标生成")
    print("- 新目标驱动新服务 → 循环继续")
    
    try:
        demo_basic_service_cycle()
        demo_complete_circular_flow()
        demo_multiple_agents()
        demo_value_self_sufficiency()
        demo_scarcity_bonus()
        
        print("\n" + "=" * 60)
        print("演示完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
