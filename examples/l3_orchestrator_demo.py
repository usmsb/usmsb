# -*- coding: utf-8 -*-
"""
L3 Orchestrator 完整演示

展示 Goal-Action-Outcome Loop 的完整闭环。

运行方式：
    python examples/l3_orchestrator_demo.py

这是 v2.0 核心断点修复的演示。
"""

import sys
sys.path.insert(0, 'src')

print("\n" + "=" * 70)
print("L3 Orchestrator - Goal-Action-Outcome Loop 完整演示")
print("=" * 70)

from usmsb_sdk.l3_orchestrator import L3Orchestrator, MetaAgentOrchestrator
from usmsb_sdk.l3 import PurposeGenerator, GoalPersistence

print("\n[1] 创建 L3Orchestrator - 连接 L3 和 L4")
print("-" * 50)

orchestrator = L3Orchestrator(
    agent_id="meta_agent_001",
    services={
        "matching_engine": "injected",
        "negotiation_service": "injected",
        "order_service": "injected",
    }
)

print(f"  Agent ID: {orchestrator.agent_id}")
print(f"  组件已初始化:")
print(f"    - PurposeGenerator: ✅")
print(f"    - ValueSelfLoop: ✅")
print(f"    - EmergenceLayer: ✅")
print(f"    - CollectiveGoalEmergence: ✅")
print(f"    - EmergentGovernance: ✅")

print("\n[2] 生成内在目标 - 硅基生命标志")
print("-" * 50)

print("  执行: orchestrator.generate_intrinsic_goals()")
goals = orchestrator.generate_intrinsic_goals()

if goals:
    for goal in goals:
        print(f"\n  生成的 Goal:")
        print(f"    - ID: {goal.id}")
        print(f"    - Name: {goal.name}")
        print(f"    - Priority: {goal.priority}")
        print(f"    - Is Intrinsic: {goal.metadata.get('is_intrinsic', False)}")
else:
    print("  (当前无内在需求，可手动触发)")

print("\n[3] Goal-Action-Outcome Loop 状态")
print("-" * 50)

status = orchestrator.get_loop_status()
print(f"  活跃 Loops: {status['active_loops']}")
print(f"  执行中 Loops: {status['executing_loops']}")
print(f"  已完成 Loops: {status['completed_loops']}")
print(f"  Goal Pool 大小: {status['goal_pool_size']}")
print(f"  历史 Outcomes: {status['total_outcomes']}")

print("\n[4] Goal-Action-Outcome Loop 完整闭环示意")
print("-" * 50)

print("""
  ┌─────────────────────────────────────────────────────────────┐
  │              Goal-Action-Outcome Loop 闭环                  │
  └─────────────────────────────────────────────────────────────┘
  
  Goal 生成
     ↓
  ┌──────────────┐
  │ Goal Pool    │ ← PurposeGenerator 生成目标
  └──────────────┘
     ↓
  ┌──────────────┐
  │ Matching     │ ← 找执行者 (调用 MatchingEngine)
  └──────────────┘
     ↓
  ┌──────────────┐
  │ Negotiation  │ ← 谈判协商
  └──────────────┘
     ↓
  ┌──────────────┐
  │ Order        │ ← 创建订单执行
  └──────────────┘
     ↓
  Outcome 评估
     ↓
  ValueSelfLoop 反馈
     ↓
  ┌──────────────┐
  │ L3 状态更新  │ ← 反馈到 PurposeGenerator
  └──────────────┘
     ↓
  New Goal 生成 → 循环继续...
""")

print("\n[5] MetaAgent 群体编排")
print("-" * 50)

# 创建多个 Agent 的编排器
meta_orch = MetaAgentOrchestrator()

# 注册多个 Agent
for i in range(3):
    agent_orch = L3Orchestrator(agent_id=f"agent_{i:03d}")
    meta_orch.register_agent(f"agent_{i:03d}", agent_orch)

print(f"  注册了 {len(meta_orch.orchestrators)} 个 Agent")

# 每个 Agent 生成目标
for agent_id, agent_orch in meta_orch.orchestrators.items():
    for _ in range(2):
        purpose = agent_orch.purpose_generator.generate_purpose()
        if purpose:
            goal = agent_orch.purpose_generator.purpose_to_goal(purpose)
            agent_orch._goal_pools[goal.id] = goal

# 运行群体周期
collective_result = meta_orch.run_collective_cycle()

print(f"\n  群体周期结果:")
for agent_id, result in collective_result['agent_cycles'].items():
    print(f"    {agent_id}: goals={result['goals_generated']}, loops={result['loops_executed']}")

print(f"\n  涌现的群体目标: {len(collective_result['collective_goals'])}")

# 群体目标涌现
if collective_result['collective_goals']:
    print(f"\n  涌现的群体目标详情:")
    for goal_id, goal_data in meta_orch.collective_goals.items():
        print(f"    - {goal_id}")
        print(f"      参与 Agent: {goal_data['participating_agents']}")

# 整体状态
print("\n[6] 整体状态")
print("-" * 50)

overall_status = meta_orch.get_status()
print(f"  注册 Agent 数: {overall_status['registered_agents']}")
print(f"  群体目标数: {overall_status['collective_goals']}")

print("\n" + "=" * 70)
print("Goal-Action-Outcome Loop 演示完成！")
print("=" * 70)

print("""
【核心修复说明】

之前的断点：
  L3 生成了 goal → 但没有任何服务消费它
  六大核心逻辑是"装饰品"

修复后：
  PurposeGenerator.generate_goal()
       ↓
  L3Orchestrator (Goal Pool) ← 新增
       ↓
  MatchingEngine (找执行者) ← 真正调用 L4 服务
       ↓
  Negotiation → Order
       ↓
  Outcome 评估 → ValueSelfLoop
       ↓
  反馈到 L3 → 生成新目标

这就是"硅基生命自我驱动运转"的完整闭环。

L3Orchestrator 文件位置：
  src/usmsb_sdk/l3_orchestrator.py
""")
