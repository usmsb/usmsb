# -*- coding: utf-8 -*-
"""
USMSB L3 综合演示

展示所有 L3 模块的协同工作。

运行方式：
    python examples/l3_complete_demo.py
"""

import sys
sys.path.insert(0, 'src')

from usmsb_sdk.l3 import (
    # P0: Purpose Generation
    PurposeGenerator,
    IntrinsicMotivationEngine,
    NeedDetector,
    GoalPersistence,
    # P1: Value Self-Cycle
    ValueSelfLoop,
    ServiceType,
    # P2: Self-Replication
    SelfReplication,
    ReplicationType,
    # Phase 3: Emergence
    EmergenceLayer,
    # Collective Goal
    CollectiveGoalEmergence,
    # Negotiation
    DynamicNegotiationProtocol,
    # Governance
    EmergentGovernance,
    RuleType,
)


def demo_complete_silicon_life_cycle():
    """完整的硅基生命循环"""
    print("=" * 70)
    print("完整硅基生命循环演示")
    print("=" * 70)
    
    # 1. 创建 Agent
    print("\n[1] 创建 Agent (PurposeGenerator)")
    generator = PurposeGenerator(agent_id="agent_alpha")
    purpose = generator.generate_purpose()
    goal = generator.purpose_to_goal(purpose)
    print(f"    生成目标: {goal.name}")
    print(f"    优先级: {goal.priority}")
    
    # 2. 创建价值循环
    print("\n[2] 价值自循环 (ValueSelfLoop)")
    value_loop = ValueSelfLoop()
    result = value_loop.execute_complete_cycle(
        provider_id="agent_alpha",
        consumer_id="agent_beta",
        service_type=ServiceType.COMPUTATION,
        description="数据处理服务",
        difficulty=0.7,
        urgency=0.8
    )
    print(f"    获得 VIBE: {result['vibe_amount']:.2f}")
    print(f"    新余额: {result['new_balance']:.2f}")
    
    # 3. 自我复制
    print("\n[3] 自我复制 (SelfReplication)")
    replication = SelfReplication()
    replication.set_agent_state("agent_alpha", {
        "id": "agent_alpha",
        "value_created": 500.0,
        "collaboration_count": 30,
        "learning_progress": 0.7,
        "resource_efficiency": 0.7,
        "resource_amount": 200.0,
        "age_seconds": 7200,
        "capabilities": ["coding", "reasoning"],
        "goals": [],
    })
    
    can_replicate, reason = replication.can_replicate("agent_alpha")
    print(f"    可以复制: {can_replicate}")
    
    if can_replicate:
        child = replication.replicate("agent_alpha", ReplicationType.VARIANT)
        print(f"    子 Agent 创建: {child['id']}")
        print(f"    继承能力: {child['inherited_capabilities']}")
        print(f"    代数: {child['generation']}")


def demo_multi_agent_emergence():
    """多 Agent 涌现"""
    print("\n" + "=" * 70)
    print("多 Agent 涌现演示")
    print("=" * 70)
    
    # 创建多个 Agent
    agents = {}
    for name in ["alpha", "beta", "gamma"]:
        peers = [n for n in ["alpha", "beta", "gamma"] if n != name]
        agents[name] = EmergenceLayer(agent_id=name, peers=peers)
    
    # 广播能力
    print("\n[1] Agent 广播能力")
    agents["alpha"].update_capability(
        capabilities=["coding"],
        reputation=0.8,
        resource_amount=100.0,
        current_goals=["explore"]
    )
    agents["beta"].update_capability(
        capabilities=["analysis"],
        reputation=0.7,
        resource_amount=80.0,
        current_goals=["learn"]
    )
    agents["gamma"].update_capability(
        capabilities=["design"],
        reputation=0.75,
        resource_amount=90.0,
        current_goals=["create"]
    )
    print("    能力已广播")
    
    # 发布任务
    print("\n[2] 发布协作任务")
    task_id = agents["alpha"].publish_task(
        task="综合项目",
        required_capabilities=["coding", "design"],
        max_members=3
    )
    print(f"    任务 ID: {task_id}")
    
    # 搜索协作方
    print("\n[3] 搜索 'coding' 能力")
    results = agents["beta"].search_for_collaborators(["coding"])
    print(f"    找到: {len(results)} 个 Agent")


def demo_collective_goal_emergence():
    """集体目标涌现"""
    print("\n" + "=" * 70)
    print("集体目标涌现演示")
    print("=" * 70)
    
    emergence = CollectiveGoalEmergence()
    
    # 多个 Agent 提交相似目标
    print("\n[1] Agent 提交目标")
    for i in range(3):
        emergence.submit_goal(
            agent_id=f"agent_{i}",
            goal_type="exploration",
            description="探索新领域",
            priority=70,
            effort_required=20.0,
            expected_value=30.0
        )
    print("    提交了 3 个相似目标")
    
    # 聚合目标
    print("\n[2] 聚合目标并形成共识")
    collective_goals = emergence.aggregate_and_form_consensus(min_similar_goals=2)
    print(f"    形成 {len(collective_goals)} 个集体目标")
    
    for cg in collective_goals:
        print(f"    - {cg.name}: {cg.consensus_state.value}")
        print(f"      参与者: {cg.participating_agents}")
        print(f"      优先级: {cg.priority}")


def demo_negotiation():
    """动态协商"""
    print("\n" + "=" * 70)
    print("动态协商演示")
    print("=" * 70)
    
    protocol = DynamicNegotiationProtocol()
    
    # 发起资源交换协商
    print("\n[1] 发起资源交换协商")
    result = protocol.negotiate_resource_exchange(
        initiator_id="agent_1",
        respondent_id="agent_2",
        resources_offered={"compute": 50},
        resources_requested={"storage": 100}
    )
    print(f"    协商成功: {result.success}")
    if result.success:
        print(f"    交换价值: {result.value_exchanged:.2f}")
    
    # 发起能力共享协商
    print("\n[2] 发起能力共享协商")
    result = protocol.negotiate_capability_sharing(
        initiator_id="agent_3",
        respondent_id="agent_4",
        capabilities_to_share=["reasoning", "planning"]
    )
    print(f"    协商成功: {result.success}")


def demo_emergent_governance():
    """涌现治理"""
    print("\n" + "=" * 70)
    print("涌现治理演示")
    print("=" * 70)
    
    governance = EmergentGovernance()
    
    # 注册 Agent
    print("\n[1] 注册 Agent")
    for i in range(5):
        governance.register_agent(f"agent_{i}")
    print(f"    注册了 {len(governance._registered_agents)} 个 Agent")
    
    # 提案规则
    print("\n[2] 提案新规则")
    rule_id = governance.propose_rule(
        proposer_id="agent_0",
        rule_type=RuleType.RESOURCE_ALLOCATION,
        name="资源分配上限",
        description="限制单次资源请求不超过 100",
        content={"max_resource_request": 100}
    )
    print(f"    规则 ID: {rule_id[:16]}...")
    
    # 投票
    print("\n[3] Agent 投票")
    governance.vote(rule_id, "agent_1", True)
    governance.vote(rule_id, "agent_2", True)
    governance.vote(rule_id, "agent_3", False)
    print("    agent_1: 赞成")
    print("    agent_2: 赞成")
    print("    agent_3: 反对")
    
    # 检查是否通过
    print("\n[4] 检查投票结果")
    passed = governance.check_approval(rule_id)
    print(f"    规则通过: {passed}")
    
    # 检查违规
    print("\n[5] 检查规则违规")
    governance.check_violation(rule_id, "agent_4")
    violation_count = governance.get_violation_count(rule_id)
    print(f"    违规次数: {violation_count}")
    
    # 获取活跃规则
    print("\n[6] 活跃规则")
    active_rules = governance.get_active_rules()
    print(f"    活跃规则数: {len(active_rules)}")


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("USMSB L3 完整演示")
    print("=" * 70)
    print("\n涵盖模块:")
    print("- P0: PurposeGenerator, IntrinsicMotivation, NeedDetector, GoalPersistence")
    print("- P1: ValueSelfLoop")
    print("- P2: SelfReplication")
    print("- Phase 3: EmergenceLayer, CollectiveGoalEmergence")
    print("- Phase 4: DynamicNegotiation, EmergentGovernance")
    
    try:
        demo_complete_silicon_life_cycle()
        demo_multi_agent_emergence()
        demo_collective_goal_emergence()
        demo_negotiation()
        demo_emergent_governance()
        
        print("\n" + "=" * 70)
        print("演示完成!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
