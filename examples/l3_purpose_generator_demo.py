# -*- coding: utf-8 -*-
"""
L3 PurposeGenerator 示例

展示如何使用 PurposeGenerator 生成自主目标。

运行方式：
    python examples/l3_purpose_generator_demo.py

关键概念：
- 工具：goal = user_input (外部赋予) → 不是硅基生命
- 硅基生命：goal = self.generate_goal() (自己生成)
"""

import sys
sys.path.insert(0, '/Users/gujun/vibecode/usmsb/src')

from usmsb_sdk.l3 import (
    PurposeGenerator,
    IntrinsicMotivationEngine,
    NeedDetector,
    GoalPersistence,
    AgentSelfState,
)


def demo_basic_usage():
    """基础用法演示"""
    print("=" * 60)
    print("L3 PurposeGenerator 基础用法演示")
    print("=" * 60)
    
    # 创建组件
    motivation = IntrinsicMotivationEngine()
    detector = NeedDetector()
    
    # 创建 PurposeGenerator
    generator = PurposeGenerator(
        agent_id="agent_001",
        intrinsic_motivation=motivation,
        need_detector=detector,
    )
    
    # 生成目标
    print("\n[1] 生成目标意图 (Purpose)...")
    purpose = generator.generate_purpose()
    
    if purpose:
        print(f"    生成的 Purpose:")
        print(f"    - ID: {purpose.id}")
        print(f"    - Name: {purpose.name}")
        print(f"    - Motivation: {purpose.motivation}")
        print(f"    - Confidence: {purpose.confidence:.2f}")
        
        # 转化为 Goal
        print("\n[2] 将 Purpose 转化为 Goal...")
        goal = generator.purpose_to_goal(purpose)
        
        print(f"    生成的 Goal:")
        print(f"    - ID: {goal.id}")
        print(f"    - Name: {goal.name}")
        print(f"    - Priority: {goal.priority}")
        print(f"    - Status: {goal.status}")
        print(f"    - Is Intrinsic: {goal.metadata.get('is_intrinsic', False)}")
    else:
        print("    没有检测到需求（可能所有动机都低于阈值）")
    
    return generator, purpose


def demo_with_persistence():
    """带持久化的演示"""
    print("\n" + "=" * 60)
    print("L3 GoalPersistence 持久化演示")
    print("=" * 60)
    
    # 创建带持久化的 PurposeGenerator
    persistence = GoalPersistence(agent_id="agent_001")
    
    generator = PurposeGenerator(
        agent_id="agent_001",
        goal_persistence=persistence,
    )
    
    # 生成目标
    print("\n[1] 生成目标...")
    purpose = generator.generate_purpose()
    if purpose:
        goal = generator.purpose_to_goal(purpose)
        print(f"    生成了 Goal: {goal.name} (ID: {goal.id})")
    
    # 模拟重启：创建一个新的 generator 实例
    print("\n[2] 模拟重启（创建新的 PurposeGenerator 实例）...")
    new_generator = PurposeGenerator(
        agent_id="agent_001",
        goal_persistence=persistence,
    )
    
    # 恢复目标
    print("\n[3] 从 Gene Capsule 恢复目标...")
    recovered_goals = new_generator.recover_goals_from_persistence()
    
    print(f"    恢复了 {len(recovered_goals)} 个未完成的目标:")
    for goal in recovered_goals:
        print(f"    - {goal.name} (Status: {goal.status}, Priority: {goal.priority})")
    
    return persistence


def demo_intrinsic_motivation():
    """内在动机引擎演示"""
    print("\n" + "=" * 60)
    print("L3 IntrinsicMotivationEngine 演示")
    print("=" * 60)
    
    engine = IntrinsicMotivationEngine()
    
    print("\n[1] 初始动机状态:")
    for mot_type, intensity in engine._motivation_states.items():
        print(f"    - {mot_type}: {intensity:.2f}")
    
    print("\n[2] 主导动机:")
    dominant = engine.get_dominant_motivation()
    print(f"    {dominant} (强度: {engine.get_motivation_state(dominant):.2f})")
    
    print("\n[3] 生成内在需求:")
    needs = engine.generate_needs()
    for need in needs:
        print(f"    - {need.type.value}: {need.description} (强度: {need.intensity:.2f})")
    
    print("\n[4] 满足需求后动机衰减:")
    if needs:
        engine.satisfy_need(needs[0], satisfaction=0.8)
        print(f"    {needs[0].type.value} 被满足后:")
        print(f"    - {needs[0].metadata.get('motivation')}: {engine.get_motivation_state(needs[0].metadata.get('motivation', '')):.2f}")


def demo_need_detector():
    """需求检测器演示"""
    print("\n" + "=" * 60)
    print("L3 NeedDetector 演示")
    print("=" * 60)
    
    detector = NeedDetector()
    
    # 创建自定义状态
    state = AgentSelfState(
        agent_id="agent_002",
        resources={"compute": 5.0, "memory": 5.0},  # 低资源
        capabilities=["basic_reasoning"],
        collaboration_count=0,  # 从未协作
        reputation=0.2,  # 低声誉
        success_rate=0.3,  # 低成功率
        isolation_level=0.8,  # 高孤独感
        efficiency=0.3,  # 低效率
    )
    
    print("\n[1] Agent 状态:")
    print(f"    - Resources: {state.resources}")
    print(f"    - Reputation: {state.reputation:.2f}")
    print(f"    - Isolation: {state.isolation_level:.2f}")
    print(f"    - Success Rate: {state.success_rate:.2f}")
    
    print("\n[2] 检测到的需求:")
    needs = detector.detect_needs("agent_002", state)
    for need in needs:
        print(f"    - [{need.type.value}] {need.description}")
        print(f"      强度: {need.intensity:.2f}, 来源: {need.source}")


def demo_tool_vs_silicon_life():
    """工具 vs 硅基生命 对比演示"""
    print("\n" + "=" * 60)
    print("工具 vs 硅基生命 对比演示")
    print("=" * 60)
    
    print("\n[工具] 外部赋予目标:")
    print("    # 外部用户输入")
    print("    goal = Goal(name='帮我写代码')  # goal = user_input")
    print("    # 关机后目标消失，开机后不记得")
    
    print("\n[硅基生命] 自我生成目标:")
    generator = PurposeGenerator(agent_id="agent_003")
    purpose = generator.generate_purpose()
    if purpose:
        goal = generator.purpose_to_goal(purpose)
        print(f"    purpose = generator.generate_purpose()")
        print(f"    goal = generator.purpose_to_goal(purpose)")
        print(f"    # goal.name = '{goal.name}'")
        print(f"    # 关机后目标持久化到 Gene Capsule")
        print(f"    # 重启后恢复，继续追求")
    
    print("\n[关键区别]")
    print("    工具: goal = user_input  → 依赖外部，是工具")
    print("    硅基生命: goal = self.generate_goal()  → 自我驱动，是生命")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("USMSB L3 PurposeGenerator 演示")
    print("=" * 60)
    print("\nL3 = 目的内生 Agent (Intrinsic Purpose Agent)")
    print("判断标准：它是否拥有自己生成的目标？")
    
    try:
        # 基础演示
        demo_basic_usage()
        
        # 持久化演示
        persistence = demo_with_persistence()
        
        # 内在动机演示
        demo_intrinsic_motivation()
        
        # 需求检测演示
        demo_need_detector()
        
        # 对比演示
        demo_tool_vs_silicon_life()
        
        print("\n" + "=" * 60)
        print("演示完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
