# -*- coding: utf-8 -*-
"""
EmergenceLayer 示例

展示如何使用 EmergenceLayer 实现涌现智能。

运行方式：
    python examples/l3_emergence_layer_demo.py
"""

import sys
sys.path.insert(0, 'src')

from usmsb_sdk.l3 import EmergenceLayer, GossipMessageType


def demo_gossip_protocol():
    """Gossip 协议演示"""
    print("=" * 60)
    print("Gossip 协议演示")
    print("=" * 60)
    
    # 创建两个 Agent 的 Gossip 实例
    agent_a = EmergenceLayer(agent_id="agent_a", peers=["agent_b"])
    agent_b = EmergenceLayer(agent_id="agent_b", peers=["agent_a"])
    
    # Agent A 广播能力
    print("\n[Agent A 广播能力]")
    agent_a.update_capability(
        capabilities=["coding", "analysis"],
        reputation=0.8,
        resource_amount=100.0,
        current_goals=["explore"]
    )
    print("  能力已广播")
    
    # Agent B 广播能力
    print("\n[Agent B 广播能力]")
    agent_b.update_capability(
        capabilities=["design", "creative"],
        reputation=0.7,
        resource_amount=80.0,
        current_goals=["create"]
    )
    print("  能力已广播")
    
    # Agent A 搜索能力
    print("\n[Agent A 搜索 'analysis' 能力]")
    results = agent_a.search_for_collaborators(["analysis"])
    print(f"  找到 {len(results)} 个 Agent")
    for r in results:
        print(f"    - {r.agent_id}: {r.capabilities}")
    
    # Agent A 搜索 'design' 能力
    print("\n[Agent A 搜索 'design' 能力]")
    results = agent_a.search_for_collaborators(["design"])
    print(f"  找到 {len(results)} 个 Agent")
    for r in results:
        print(f"    - {r.agent_id}: {r.capabilities}")


def demo_team_formation():
    """团队形成演示"""
    print("\n" + "=" * 60)
    print("自组织团队形成演示")
    print("=" * 60)
    
    # 创建一个 Agent
    agent = EmergenceLayer(agent_id="coordinator", peers=[])
    
    # 发布任务
    print("\n[发布任务]")
    task_id = agent.publish_task(
        task="数据分析项目",
        required_capabilities=["analysis", "visualization"],
        max_members=3
    )
    print(f"  任务 ID: {task_id}")
    print(f"  开放任务: {len(agent.get_open_tasks())}")
    
    # 模拟其他 Agent 加入
    print("\n[其他 Agent 申请加入]")
    result = agent.team_formation.join_team(task_id, "analyst_001")
    print(f"  analyst_001 申请: {'成功' if result else '失败'}")
    result = agent.team_formation.join_team(task_id, "analyst_002")
    print(f"  analyst_002 申请: {'成功' if result else '失败'}")
    result = agent.team_formation.join_team(task_id, "analyst_003")
    print(f"  analyst_003 申请: {'成功' if result else '失败'}")
    
    team = agent.get_active_teams()[0] if agent.get_active_teams() else None
    if team:
        print(f"\n  团队已形成!")
        print(f"  成员: {team.member_ids}")
        print(f"  状态: {team.status}")
    else:
        print(f"\n  团队还未形成（等待更多成员）")


def demo_pattern_detection():
    """模式检测演示"""
    print("\n" + "=" * 60)
    print("模式检测演示")
    print("=" * 60)
    
    detector = EmergenceLayer(agent_id="detector", peers=[])
    
    # 记录多次交互
    print("\n[记录交互]")
    interactions = [
        ("a", "b", "collaboration", "success"),
        ("a", "c", "collaboration", "success"),
        ("a", "b", "collaboration", "success"),
        ("a", "b", "collaboration", "failure"),
        ("b", "c", "resource_sharing", "success"),
        ("b", "c", "resource_sharing", "success"),
        ("c", "d", "collaboration", "success"),
        ("d", "e", "collaboration", "success"),
        ("e", "a", "collaboration", "success"),
    ]
    
    for a, b, itype, outcome in interactions:
        detector.record_interaction(a, itype, outcome)
    
    print(f"  记录了 {len(interactions)} 次交互")
    
    # 检测模式
    print("\n[检测全局模式]")
    patterns = detector.detect_global_patterns()
    
    print(f"\n  总交互次数: {patterns['total_interactions']}")
    print(f"  中心节点: {patterns['hub_agents']}")
    print(f"  成功协作对: {patterns['successful_pairs']}")


def demo_emergence_integration():
    """完整涌现演示"""
    print("\n" + "=" * 60)
    print("完整涌现演示")
    print("=" * 60)
    
    # 创建多个 Agent
    agents = {}
    for name in ["alice", "bob", "charlie", "david"]:
        peers = [n for n in ["alice", "bob", "charlie", "david"] if n != name]
        agents[name] = EmergenceLayer(agent_id=name, peers=peers)
    
    # Alice 发布任务
    print("\n[Alice 发布复杂任务]")
    task_id = agents["alice"].publish_task(
        task="需要多领域专家的项目",
        required_capabilities=["coding", "design", "analysis"],
        max_members=4
    )
    print(f"  任务: {task_id}")
    
    # Bob 和 Charlie 广播能力
    print("\n[Bob 和 Charlie 广播能力]")
    agents["bob"].update_capability(
        capabilities=["coding", "analysis"],
        reputation=0.8,
        resource_amount=100.0,
        current_goals=["code"]
    )
    print("  Bob: coding, analysis")
    
    agents["charlie"].update_capability(
        capabilities=["design", "creative"],
        reputation=0.75,
        resource_amount=90.0,
        current_goals=["design"]
    )
    print("  Charlie: design, creative")
    
    # Bob 和 Charlie 报名
    print("\n[Bob 和 Charlie 响应任务]")
    agents["bob"].join_task(task_id)
    print("  Bob 申请加入")
    agents["charlie"].join_task(task_id)
    print("  Charlie 申请加入")
    
    # Alice 检测模式
    print("\n[Alice 检测全局模式]")
    patterns = agents["alice"].detect_global_patterns()
    print(f"  发现的中心 Agent: {patterns['hub_agents']}")
    print(f"  成功的协作对: {patterns['successful_pairs']}")
    
    # 记录协作
    print("\n[记录协作经验]")
    agents["alice"].record_interaction("bob", "collaboration", "success")
    agents["alice"].record_interaction("charlie", "collaboration", "success")
    agents["bob"].record_interaction("charlie", "collaboration", "success")
    print("  记录了 3 次成功协作")
    
    # 再次检测
    print("\n[Alice 再次检测模式]")
    patterns = agents["alice"].detect_global_patterns()
    print(f"  发现的中心 Agent: {patterns['hub_agents']}")
    print(f"  成功的协作对: {patterns['successful_pairs']}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("USMSB L3 EmergenceLayer 演示")
    print("=" * 60)
    print("\n核心概念：涌现智能")
    print("- Gossip 协议：状态传播、能力发现")
    print("- Team Formation：自组织团队形成")
    print("- Pattern Detection：模式检测")
    
    try:
        demo_gossip_protocol()
        demo_team_formation()
        demo_pattern_detection()
        demo_emergence_integration()
        
        print("\n" + "=" * 60)
        print("演示完成!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
