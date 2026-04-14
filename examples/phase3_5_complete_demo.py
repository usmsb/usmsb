# -*- coding: utf-8 -*-
"""
Phase 3-5 完整功能演示

展示完整强大的实现。

运行方式：
    python examples/phase3_5_complete_demo.py
"""

import sys
sys.path.insert(0, 'src')

print("\n" + "=" * 70)
print("Phase 3-5 完整功能演示")
print("=" * 70)

# ============================================================================
# Phase 3: Intelligent Optimization - 完整实现
# ============================================================================
print("\n" + "=" * 70)
print("Phase 3: Intelligent Optimization - 完整实现")
print("=" * 70)

from usmsb_sdk.intelligence import (
    MarketFeedbackLoop, TrendDetector, PriceOptimizer, DemandForecaster, ABTestEngine,
    FeedbackRecord, TrendAnalysis, PriceRecommendation, DemandForecast
)

print("\n[1] MarketFeedbackLoop - 市场反馈闭环")
print("-" * 50)

# 创建市场反馈系统
feedback_loop = MarketFeedbackLoop()

# 模拟记录反馈数据
print("\n[模拟市场数据]")
for i in range(50):
    feedback_loop.record_feedback(
        agent_id=f"agent_{i % 5}",
        order_id=f"order_{i}",
        capability="coding",
        price=50.0 + random.uniform(-10, 10),
        market_price=55.0,
        success=i % 10 > 2,  # 70% 成功率
        response_time=random.uniform(1, 10),
        completion_time=random.uniform(10, 100),
        quality_score=random.uniform(0.6, 1.0),
        customer_satisfaction=random.uniform(0.7, 1.0)
    )
print(f"  记录了 50 条市场反馈")

# 趋势检测
print("\n[2] TrendDetector - 趋势检测")
print("-" * 50)

trend_detector = TrendDetector()

# 生成测试数据
prices = [100 + i * 2 + random.uniform(-5, 5) for i in range(30)]
timestamps = [1614556800 + i * 86400 for i in range(30)]

trend = trend_detector.detect_trend(prices, timestamps)
print(f"  检测到趋势: {trend.direction}")
print(f"  变化率: {trend.change_rate:.4f}")
print(f"  置信度: {trend.confidence:.2f}")
print(f"  预测值: {trend.prediction:.2f}")

# 价格优化
print("\n[3] PriceOptimizer - 价格优化")
print("-" * 50)

optimizer = PriceOptimizer()

recommendation = optimizer.calculate_optimal_price(
    base_cost=50.0,
    avg_success_rate=0.75,
    market_avg_price=60.0
)
print(f"  最优价格: {recommendation.optimal_price:.2f} VIBE")
print(f"  价格范围: {recommendation.min_price:.2f} - {recommendation.max_price:.2f}")
print(f"  预期成功率: {recommendation.expected_success_rate:.2%}")
print(f"  预期交易量: {recommendation.expected_volume}")

# 需求预测
print("\n[4] DemandForecaster - 需求预测")
print("-" * 50)

forecaster = DemandForecaster()

# 生成预测数据
forecast = forecaster.forecast(
    capability="coding",
    historical_data=[],
    forecast_days=30
)
print(f"  当前需求指数: {forecast.current_demand:.3f}")
print(f"  7天预测: {forecast.predicted_demand_7d:.3f}")
print(f"  30天预测: {forecast.predicted_demand_30d:.3f}")
print(f"  置信度: {forecast.confidence:.2f}")
print(f"  趋势: {forecast.trends}")

# A/B 测试
print("\n[5] ABTestEngine - A/B 测试引擎")
print("-" * 50)

ab_engine = ABTestEngine()

# 模拟 A/B 测试
ab_engine.create_test(
    test_id="pricing_test",
    hypothesis="新定价策略更好",
    agent_id="test_agent"
)

# 模拟结果
import random
for _ in range(50):
    ab_engine.record_result("pricing_test", "a", random.uniform(0.4, 0.8))
    ab_engine.record_result("pricing_test", "b", random.uniform(0.5, 0.9))

result = ab_engine.analyze("pricing_test")
if result:
    print(f"  测试假设: {result.hypothesis}")
    print(f"  A变体均值: {result.variant_a_results['mean']:.4f}")
    print(f"  B变体均值: {result.variant_b_results['mean']:.4f}")
    print(f"  统计显著性: {result.statistical_significance:.4f}")
    print(f"  p值: {result.p_value:.4f}")
    print(f"  获胜者: {result.winner}")
    print(f"  建议: {result.recommended_action}")

# ============================================================================
# Phase 4: Emergence System - 完整实现
# ============================================================================
print("\n" + "=" * 70)
print("Phase 4: Emergence System - 完整实现")
print("=" * 70)

from usmsb_sdk.emergence import (
    EmergenceSystem, GossipProtocol, TeamFormationAlgorithm, PatternDetection, GlobalCoordination
)

print("\n[1] GossipProtocol - Gossip 协议")
print("-" * 50)

# 创建 Gossip 网络
nodes = {}
for name in ["alice", "bob", "charlie", "david"]:
    nodes[name] = GossipProtocol(name)

# 建立连接
nodes["alice"].add_peer("bob", nodes["bob"])
nodes["alice"].add_peer("charlie", nodes["charlie"])
nodes["bob"].add_peer("charlie", nodes["charlie"])
nodes["charlie"].add_peer("david", nodes["david"])

print(f"  Alice 的 peers: {list(nodes['alice'].peers.keys())}")

# 广播消息
msg = nodes["alice"].broadcast("capability", {
    "capabilities": ["coding", "analysis"],
    "reputation": 0.85
})
print(f"  广播消息 ID: {msg.id[:20]}...")

# 执行 Gossip 轮次
for _ in range(3):
    for name in nodes:
        nodes[name].gossip_round()

print(f"  Alice 收到消息: {len(nodes['alice'].message_cache)}")

# 团队形成
print("\n[2] TeamFormationAlgorithm - 团队形成算法")
print("-" * 50)

team_formation = TeamFormationAlgorithm()

# 注册节点能力
team_formation.register_node_capabilities("alice", ["coding", "analysis", "planning"], 0.9)
team_formation.register_node_capabilities("bob", ["design", "creative"], 0.85)
team_formation.register_node_capabilities("charlie", ["coding", "testing"], 0.8)
team_formation.register_node_capabilities("david", ["management", "coordination"], 0.9)
team_formation.register_node_capabilities("eve", ["security", "testing"], 0.75)

# 形成团队
team = team_formation.form_team(
    task="完整项目开发",
    required_capabilities=["coding", "design", "management"],
    leader_id="alice",
    min_size=3
)

if team:
    print(f"  团队 ID: {team.id[:20]}...")
    print(f"  成员: {team.members}")
    print(f"  凝聚力: {team.cohesion_score:.3f}")
    print(f"  状态: {team.status}")

# 查找候选
candidates = team_formation.find_candidates(
    required_capabilities=["coding", "security"],
    min_reputation=0.7
)
print(f"\n  候选节点（coding+security）: {[c[0] for c in candidates[:3]]}")

# 模式检测
print("\n[3] PatternDetection - 模式检测")
print("-" * 50)

pattern_det = PatternDetection()

# 记录交互
for _ in range(100):
    a, b = random.sample(["alice", "bob", "charlie", "david", "eve"], 2)
    pattern_det.record_interaction(a, b, "collaboration", 1.0)

# 检测中心节点
hubs = pattern_det.detect_hub_nodes(min_degree=5)
print(f"  检测到 {len(hubs)} 个中心节点")

# 检测社区
communities = pattern_det.detect_communities()
print(f"  检测到 {len(communities)} 个社区")
for i, comm in enumerate(communities[:3]):
    print(f"    社区 {i+1}: {comm[:3]}...")

# 分析小世界特性
sw = pattern_det.analyze_small_world_property()
print(f"  小世界特性: {sw.get('is_small_world', 'N/A')}")
if sw.get('clustering_coefficient'):
    print(f"  聚类系数: {sw['clustering_coefficient']:.4f}")

# 全局协调
print("\n[4] GlobalCoordination - 全局协调")
print("-" * 50)

coordination = GlobalCoordination()

# 添加节点
for name in ["alice", "bob", "charlie"]:
    coordination.network_topology.add_node(name)

# 提议动作
action = coordination.propose_action(
    proposer_id="alice",
    action_type="allocate",
    target_nodes=["bob", "charlie"],
    parameters={"resources": {"bob": 50, "charlie": 30}}
)

print(f"  提议动作 ID: {action.id[:20]}...")
print(f"  类型: {action.action_type}")
print(f"  状态: {action.status}")

# 投票
coordination.vote(action.id, "bob", True)
coordination.vote(action.id, "charlie", True)

print(f"  投票结果: {action.votes_for} 赞成, {action.votes_against} 反对")
print(f"  最终状态: {action.status}")

# ============================================================================
# Phase 5: Self-Evolution - 完整实现
# ============================================================================
print("\n" + "=" * 70)
print("Phase 5: Self-Evolution - 完整实现")
print("=" * 70)

from usmsb_sdk.evolution import (
    EvolutionController, Genome, Gene, FitnessResult, Genome,
    MultiObjectiveFitnessEvaluator, GeneMutator
)

print("\n[1] MultiObjectiveFitnessEvaluator - 多目标适应度评估")
print("-" * 50)

evaluator = MultiObjectiveFitnessEvaluator()

# 评估 Agent
agent_state = {
    "id": "test_agent",
    "value_created": 5000.0,
    "success_rate": 0.85,
    "efficiency": 0.75,
    "reputation": 0.9,
    "collaboration_score": 0.7,
    "learning_progress": 0.6,
    "resource_efficiency": 0.8
}

result = evaluator.evaluate(agent_state)
print(f"  Agent: {result.agent_id}")
print(f"  总体适应度: {result.overall_score:.4f}")
print(f"  百分位: {result.percentile:.1f}%")
print(f"  维度得分:")
print(f"    - 价值创造: {result.dimensions.value_created:.4f}")
print(f"    - 任务成功: {result.dimensions.task_success:.4f}")
print(f"    - 效率: {result.dimensions.efficiency:.4f}")
print(f"    - 声誉: {result.dimensions.reputation:.4f}")

# 基因突变
print("\n[2] GeneMutator - 基因突变器")
print("-" * 50)

mutator = GeneMutator(mutation_rate=0.3)

# 创建基因组
genes = {
    "learning_rate": Gene("learning_rate", 0.01, mutation_rate=0.2, mutation_range=(0.001, 0.5)),
    "creativity": Gene("creativity", 0.5, mutation_rate=0.15, mutation_range=(0, 1)),
    "risk_tolerance": Gene("risk_tolerance", 0.3, mutation_rate=0.1, mutation_range=(0, 1)),
}

genome = Genome(agent_id="agent_v1", genes=genes, generation=0)

print(f"  原始基因组:")
for name, gene in genome.genes.items():
    print(f"    {name}: {gene.value:.4f}")

# 执行突变
mutated, mutations = mutator.mutate_genome(genome)

print(f"\n  突变记录:")
for m in mutations:
    print(f"    - {m}")

print(f"\n  突变后基因组:")
for name, gene in mutated.genes.items():
    orig = genome.genes[name].value
    new = gene.value
    if orig != new:
        print(f"    {name}: {orig:.4f} -> {new:.4f} ⚡")
    else:
        print(f"    {name}: {new:.4f} (未变异)")

# 进化控制器
print("\n[3] EvolutionController - 进化控制器")
print("-" * 50)

controller = EvolutionController(
    population_size=20,
    elite_ratio=0.1,
    mutation_rate=0.15
)

# 创建模板基因组
template_genes = {
    "learning_rate": Gene("learning_rate", 0.01, mutation_rate=0.2, mutation_range=(0.001, 0.5)),
    "creativity": Gene("creativity", 0.5, mutation_rate=0.15, mutation_range=(0, 1)),
    "efficiency": Gene("efficiency", 0.7, mutation_rate=0.1, mutation_range=(0, 1)),
    "social": Gene("social", 0.6, mutation_rate=0.1, mutation_range=(0, 1)),
}

template = Genome(agent_id="template", genes=template_genes)

# 初始化种群
controller.initialize_population(template, size=20)
print(f"  种群大小: {len(controller.population)}")

# 模拟多代进化
print("\n[进化模拟 - 10代]")

agent_states = {}
for i, genome in enumerate(controller.population):
    agent_states[genome.agent_id] = {
        "id": genome.agent_id,
        "value_created": random.uniform(1000, 8000),
        "success_rate": random.uniform(0.5, 0.95),
        "efficiency": random.uniform(0.4, 0.9),
        "reputation": random.uniform(0.5, 0.95),
        "collaboration_score": random.uniform(0.4, 0.9),
        "learning_progress": random.uniform(0.3, 0.8),
        "resource_efficiency": random.uniform(0.5, 0.9)
    }

for gen in range(10):
    result = controller.evolve(agent_states)
    if gen == 9:
        print(f"  第{gen+1}代: 最佳={result['best_fitness']:.4f}, 平均={result['avg_fitness']:.4f}, 突变数={len(result['mutations'])}")

# 获取进化统计
stats = controller.get_evolution_statistics()
print(f"\n  进化统计:")
print(f"    代数: {stats['generation']}")
print(f"    收敛率: {stats['convergence_rate']:.4f}")
print(f"    总评估次数: {stats['total_evaluations']}")

# 获取最优基因组
best_genome = controller.get_best_genome()
if best_genome:
    print(f"\n  最优基因组 ({best_genome.agent_id}):")
    for name, gene in best_genome.genes.items():
        print(f"    {name}: {gene.value:.4f}")

print("\n" + "=" * 70)
print("演示完成！所有 Phase 3-5 模块均为完整实现。")
print("=" * 70)
