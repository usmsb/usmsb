# -*- coding: utf-8 -*-
"""
USMSB v2.0 Complete Demo

运行方式：
    python examples/usmsb_v2_complete_demo.py
"""

import sys
sys.path.insert(0, 'src')

print("\n" + "=" * 70)
print("USMSB v2.0 完整演示")
print("=" * 70)

# Phase 0: Protocol
print("\n[Phase 0: Protocol Integration]")
from usmsb_sdk.protocol import (
    MultiWallet, AgentCard, AgentCardRegistry, A2AAdapter,
    MCPRegistry, MCPGateway, ToolCategory, x402Router, Currency
)
print("  ✅ MultiWallet, A2A, MCP, x402")

# Phase 1: Core Services
print("\n[Phase 1: Core Services]")
from usmsb_sdk.core_services import (
    AgentRegistry, AgentProfile, AgentStatus, AgentType,
    GeneCapsuleManager, MatchingEngine, Task,
    NegotiationHub, NegotiationTerm, OrderManager, ReputationService
)
print("  ✅ AgentRegistry, GeneCapsule, Matching, Negotiation, Order, Reputation")

# Phase 2: Economic
print("\n[Phase 2: Economic Incentive]")
from usmsb_sdk.economic import TokenEconomy, StakingPool, LayerSettlement, SettlementLayer
print("  ✅ TokenEconomy, StakingPool, LayerSettlement")

# Phase 3: Intelligence
print("\n[Phase 3: Intelligent Optimization]")
from usmsb_sdk.intelligence import IntelligentOptimizer, MarketFeedbackLoop, DemandPredictor
print("  ✅ MarketFeedback, DemandPredictor, PriceSuggestion")

# Phase 4: Emergence
print("\n[Phase 4: Emergence System]")
from usmsb_sdk.emergence import EmergenceSystem, GossipNode, TeamFormation
print("  ✅ Gossip, TeamFormation, EmergenceMonitor")

# Phase 5: Evolution
print("\n[Phase 5: Self-Evolution]")
from usmsb_sdk.evolution import EvolutionController, FitnessEvaluator, PerformanceTracker
print("  ✅ FitnessEvaluator, PerformanceTracker, EvolutionController")

# L3 Modules
print("\n[L3: Silicon-Based Life]")
from usmsb_sdk.l3 import (
    PurposeGenerator, IntrinsicMotivationEngine, NeedDetector,
    ValueSelfLoop, ServiceType, SelfReplication, ReplicationType,
    EmergenceLayer, CollectiveGoalEmergence, DynamicNegotiationProtocol, EmergentGovernance
)
print("  ✅ PurposeGenerator, ValueSelfLoop, SelfReplication, Emergence")

# Demo: Complete Flow
print("\n" + "=" * 70)
print("完整流程演示")
print("=" * 70)

# 1. 创建 Agent
print("\n[1] Agent 注册")
registry = AgentRegistry()
agent = AgentProfile(
    id="agent_alpha",
    name="Alpha Agent",
    description="主 Agent",
    capabilities=["reasoning", "coding", "analysis"],
    reputation=0.85
)
registry.register(agent)
print(f"  Agent 创建: {agent.name}")

# 2. 目标生成
print("\n[2] 目标生成 (PurposeGenerator)")
pg = PurposeGenerator(agent_id="agent_alpha")
purpose = pg.generate_purpose()
goal = pg.purpose_to_goal(purpose)
print(f"  目标: {goal.name}, 优先级: {goal.priority}")

# 3. 价值循环
print("\n[3] 价值自循环 (ValueSelfLoop)")
vl = ValueSelfLoop()
result = vl.execute_complete_cycle(
    provider_id="agent_alpha",
    consumer_id="agent_beta",
    service_type=ServiceType.COMPUTATION,
    description="计算任务",
    difficulty=0.7,
    urgency=0.8
)
print(f"  获得 VIBE: {result['vibe_amount']:.2f}")

# 4. 智能优化
print("\n[4] 智能优化 (IntelligentOptimizer)")
opt = IntelligentOptimizer()
suggestion = opt.get_price_suggestion("agent_alpha", 50.0, 60.0, 0.85)
print(f"  建议价格: {suggestion.suggested_price:.2f} VIBE")

# 5. 涌现
print("\n[5] 涌现系统 (EmergenceSystem)")
emergence = EmergenceSystem()
team = emergence.team_formation.form_team("agent_alpha", ["agent_beta", "agent_gamma"], "数据分析")
print(f"  团队形成: {len(team['members'])} 个成员")

# 6. 自我进化
print("\n[6] 自我进化 (EvolutionController)")
evo = EvolutionController()
state = {
    "capabilities": ["reasoning", "coding"],
    "value_created": 800.0,
    "task_success": 0.9,
    "efficiency": 0.75
}
result = evo.evolve_agent("agent_alpha", state)
print(f"  适应度: {result['fitness'].fitness_score:.3f}")

print("\n" + "=" * 70)
print("USMSB v2.0 演示完成！")
print("=" * 70)
print("\n模块清单:")
print("  Phase 0: Protocol Integration (MCP + A2A + x402)")
print("  Phase 1: Core Services (Agent + GeneCapsule + Matching + Negotiation + Order + Reputation)")
print("  Phase 2: Economic Incentive (Token + Staking + Settlement)")
print("  Phase 3: Intelligent Optimization (MarketFeedback + DemandPrediction + PriceSuggestion)")
print("  Phase 4: Emergence System (Gossip + TeamFormation + PatternDetection)")
print("  Phase 5: Self-Evolution (FitnessEvaluator + PerformanceTracker + GeneMutator)")
print("  L3 Core: PurposeGenerator + ValueSelfLoop + SelfReplication + EmergenceLayer")
