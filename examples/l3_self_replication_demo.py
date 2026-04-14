# -*- coding: utf-8 -*-
"""
SelfReplication 示例

展示如何使用 SelfReplication 实现 Agent 自我复制。

运行方式：
    python examples/l3_self_replication_demo.py
"""

import sys
sys.path.insert(0, 'src')

from usmsb_sdk.l3 import (
    SelfReplication,
    ReplicationType,
    ReplicationTrigger,
    FitnessCalculator,
)


def demo_fitness_calculation():
    """适应度计算演示"""
    print("=" * 60)
    print("适应度计算演示")
    print("=" * 60)
    
    calculator = FitnessCalculator()
    
    # 不同状态的适应度
    test_cases = [
        {
            "name": "高绩效 Agent",
            "value_created": 800.0,
            "collaboration_count": 50,
            "learning_progress": 0.9,
            "resource_efficiency": 0.85,
        },
        {
            "name": "中等 Agent",
            "value_created": 300.0,
            "collaboration_count": 20,
            "learning_progress": 0.5,
            "resource_efficiency": 0.5,
        },
        {
            "name": "低绩效 Agent",
            "value_created": 50.0,
            "collaboration_count": 5,
            "learning_progress": 0.2,
            "resource_efficiency": 0.3,
        },
    ]
    
    print("\n适应度 = 0.3×价值 + 0.2×协作 + 0.3×学习 + 0.2×效率\n")
    
    for case in test_cases:
        fitness = calculator.calculate_from_agent_state(case)
        print(f"  {case['name']}:")
        print(f"    价值创造: {case['value_created']:.0f}")
        print(f"    协作次数: {case['collaboration_count']}")
        print(f"    学习进度: {case['learning_progress']:.2f}")
        print(f"    资源效率: {case['resource_efficiency']:.2f}")
        print(f"    适应度: {fitness:.3f}")
        print()


def demo_replication_conditions():
    """复制条件演示"""
    print("=" * 60)
    print("复制条件演示")
    print("=" * 60)
    
    replication = SelfReplication()
    
    # 设置 Agent 状态
    replication.set_agent_state("agent_001", {
        "id": "agent_001",
        "value_created": 800.0,
        "collaboration_count": 50,
        "learning_progress": 0.9,
        "resource_efficiency": 0.85,
        "resource_amount": 150.0,
        "age_seconds": 7200,  # 2小时
        "capabilities": ["reasoning", "coding", "analysis"],
        "goals": [{"name": "explore", "priority": 70}],
    })
    
    print("\n[Agent_001 状态]")
    print(f"  适应度: {replication.calculate_fitness('agent_001'):.3f}")
    print(f"  资源: 150.0")
    print(f"  年龄: 2小时")
    
    can_replicate, reason = replication.can_replicate("agent_001")
    print(f"\n  可以复制: {can_replicate}")
    print(f"  原因: {reason}")


def demo_replication_execution():
    """复制执行演示"""
    print("\n" + "=" * 60)
    print("复制执行演示")
    print("=" * 60)
    
    # 创建 SelfReplication
    replication = SelfReplication()
    
    # 设置父 Agent 状态
    replication.set_agent_state("parent_agent", {
        "id": "parent_agent",
        "value_created": 800.0,
        "collaboration_count": 50,
        "learning_progress": 0.9,
        "resource_efficiency": 0.85,
        "resource_amount": 200.0,
        "age_seconds": 7200,
        "capabilities": ["reasoning", "coding", "analysis", "planning"],
        "goals": [
            {"name": "explore", "priority": 70},
            {"name": "learn", "priority": 60},
        ],
    })
    
    print("\n[父 Agent 状态]")
    print(f"  适应度: {replication.calculate_fitness('parent_agent'):.3f}")
    print(f"  资源: 200.0")
    print(f"  能力: reasoning, coding, analysis, planning")
    print(f"  目标: explore(70), learn(60)")
    
    # 执行复制
    print("\n[执行复制...]")
    result = replication.replicate("parent_agent", ReplicationType.VARIANT)
    
    if result:
        print(f"\n  子 Agent 创建成功!")
        print(f"  子 Agent ID: {result['id']}")
        print(f"  继承能力: {result['inherited_capabilities']}")
        print(f"  变异应用: {result['mutation_applied']}")
        print(f"  适应度: {result['fitness']:.3f}")
        print(f"  资源消耗: {result['resource_cost']:.1f}")
        print(f"  代数: {result['generation']}")
    else:
        print("  复制失败!")


def demo_mutation_effects():
    """变异效果演示"""
    print("\n" + "=" * 60)
    print("变异效果演示（多次复制）")
    print("=" * 60)
    
    replication = SelfReplication()
    
    # 设置初始 Agent
    replication.set_agent_state("ancestor", {
        "id": "ancestor",
        "value_created": 500.0,
        "collaboration_count": 30,
        "learning_progress": 0.6,
        "resource_efficiency": 0.6,
        "resource_amount": 500.0,
        "age_seconds": 7200,
        "capabilities": ["reasoning", "coding"],
        "goals": [{"name": "work", "priority": 50}],
    })
    
    print("\n[初始 Agent]")
    print(f"  学习进度: 0.600")
    print(f"  目标优先级: 50")
    
    # 执行 5 次复制，观察变异
    print("\n[连续 5 次复制]")
    current_id = "ancestor"
    
    for i in range(5):
        # 更新父状态
        parent_state = replication.get_agent_state(current_id)
        parent_state["value_created"] += 100
        replication.set_agent_state(current_id, parent_state)
        
        result = replication.replicate(current_id, ReplicationType.VARIANT)
        if result:
            child_state = replication.get_agent_state(result['id'])
            print(f"\n  第 {i+1} 代:")
            print(f"    学习进度: {child_state.get('learning_progress', 0):.3f}")
            goals = child_state.get('goals', [])
            if goals:
                print(f"    目标优先级: {goals[0].get('priority', 0)}")
            else:
                print(f"    目标优先级: N/A")
            if result['mutation_applied']:
                print(f"    变异: {result['mutation_applied']}")
            current_id = result['id']


def demo_population_growth():
    """种群增长演示"""
    print("\n" + "=" * 60)
    print("种群增长演示")
    print("=" * 60)
    
    replication = SelfReplication()
    
    # 设置初始 Agent
    replication.set_agent_state("gen0", {
        "id": "gen0",
        "value_created": 500.0,
        "collaboration_count": 30,
        "learning_progress": 0.6,
        "resource_efficiency": 0.6,
        "resource_amount": 1000.0,  # 更多资源
        "age_seconds": 7200,
        "capabilities": ["reasoning"],
        "goals": [],
    })
    
    print("\n[开始繁殖...]")
    
    to_replicate = ["gen0"]
    generation_counts = {0: 1}
    
    for generation in range(3):
        new_agents = []
        for agent_id in to_replicate:
            # 给予更多资源
            state = replication.get_agent_state(agent_id)
            state["resource_amount"] = 300.0
            replication.set_agent_state(agent_id, state)
            
            # 尝试复制
            result = replication.replicate(agent_id, ReplicationType.VARIANT)
            if result:
                new_agents.append(result['id'])
        
        generation_counts[generation + 1] = len(new_agents)
        to_replicate = new_agents
        
        if new_agents:
            print(f"  第 {generation+1} 代: {len(new_agents)} 个子 Agent")
    
    stats = replication.get_population_stats()
    print(f"\n[种群统计]")
    print(f"  总 Agent 数: {stats['total_agents']}")
    print(f"  最大种群: {stats['max_population']}")
    print(f"  总复制次数: {stats['total_replications']}")
    print(f"  各代分布: {stats['generations']}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("USMSB L3 SelfReplication 演示")
    print("=" * 60)
    print("\n核心概念：硅基生命的自我复制")
    print("- 高适应度 Agent 可以复制自身")
    print("- 子 Agent 继承 80% 能力")
    print("- 10% 变异率（可能增强或减弱）")
    print("- 复制消耗资源")
    
    try:
        demo_fitness_calculation()
        demo_replication_conditions()
        demo_replication_execution()
        demo_mutation_effects()
        demo_population_growth()
        
        print("\n" + "=" * 60)
        print("演示完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
