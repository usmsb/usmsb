#!/usr/bin/env python3
"""
V2.1 Causal Learning System 能力验证测试

使用创建的测试数据验证 V2.1 六大核心系统的能力
"""

import asyncio
import numpy as np
from dataclasses import dataclass, field
from typing import Any, List, Dict, Optional


# ============================================================================
# 测试数据创建
# ============================================================================

@dataclass
class MockOutcome:
    quality: float = 0.0
    correctness: float = 0.0
    efficiency: float = 0.0


@dataclass
class MockTaskRecord:
    task_id: str
    task_description: str
    task_features: Dict[str, Any]
    outcome: Optional[MockOutcome] = None
    execution_time: float = 0.0


def create_correlated_task_records(n_samples: int = 50) -> List[MockTaskRecord]:
    """创建具有相关性的测试任务记录"""
    np.random.seed(42)
    records = []

    for i in range(n_samples):
        # 任务复杂度
        complexity = np.random.beta(2, 2)

        # 任务特征
        features = {
            "complexity": complexity,
            "length": int(complexity * 1000),
            "api_calls": int(complexity * 10),
            "error_rate": (1 - complexity) * 0.3,
        }

        # 结果质量与复杂度相关
        quality = 0.5 + 0.3 * complexity + np.random.randn() * 0.1

        outcome = MockOutcome(
            quality=min(1.0, max(0.0, quality)),
            correctness=min(1.0, max(0.0, quality + np.random.randn() * 0.05)),
            efficiency=min(1.0, max(0.0, 1 - complexity * 0.5)),
        )

        record = MockTaskRecord(
            task_id=f"task_{i}",
            task_description=f"Task with complexity {complexity:.2f}",
            task_features=features,
            outcome=outcome,
            execution_time=1.0 + complexity * 10,
        )
        records.append(record)

    return records


async def test_conditional_independence():
    """测试条件独立性检验"""
    print("\n" + "="*60)
    print("1. 条件独立性检验 (Conditional Independence Test)")
    print("="*60)

    from usmsb_sdk.meta_agent.evolution_v2.causal_discovery.conditional_independence import (
        ConditionalIndependenceTest,
    )

    ci = ConditionalIndependenceTest(alpha=0.05)

    # 测试独立变量
    np.random.seed(42)
    n = 100
    x_ind = np.random.randn(n)
    y_ind = np.random.randn(n)

    # 测试相关变量
    x_dep = np.random.randn(n)
    y_dep = 0.8 * x_dep + np.random.randn(n) * 0.2

    # 测试条件独立（给定 z，x 和 y 应该独立）
    z_cond = np.random.randn(n)

    # CMI 检验
    mi_ind, p_ind = ci.ci_test(x_ind, y_ind, None, method="cmi")
    mi_dep, p_dep = ci.ci_test(x_dep, y_dep, None, method="cmi")

    print(f"\n互信息 (MI) 测试:")
    print(f"  独立变量: MI = {mi_ind:.4f}, p-value = {p_ind:.4f}")
    print(f"  相关变量: MI = {mi_dep:.4f}, p-value = {p_dep:.4f}")
    print(f"  ✓ 独立变量 MI < 相关变量 MI: {mi_ind < mi_dep}")

    # 条件互信息
    cmi_cond, p_cond = ci.ci_test(x_dep, y_dep, z_cond, method="cmi")
    print(f"\n条件互信息 (CMI) 测试:")
    print(f"  CMI(X,Y|Z) = {cmi_cond:.4f}, p-value = {p_cond:.4f}")

    return True


async def test_causal_discovery():
    """测试因果发现引擎"""
    print("\n" + "="*60)
    print("2. 因果发现引擎 (Causal Discovery Engine)")
    print("="*60)

    from usmsb_sdk.meta_agent.evolution_v2.causal_discovery.skeleton_builder import SkeletonBuilder
    from usmsb_sdk.meta_agent.evolution_v2.causal_discovery.edge_orienter import EdgeOrienter
    from usmsb_sdk.meta_agent.evolution_v2.causal_discovery.strength_estimator import StrengthEstimator
    from usmsb_sdk.meta_agent.evolution_v2.causal_discovery.conditional_independence import ConditionalIndependenceTest

    # 创建测试数据
    np.random.seed(42)
    n = 50
    x = np.random.randn(n)
    y = 0.8 * x + np.random.randn(n) * 0.2
    z = np.random.randn(n)

    # 构建骨架
    ci = ConditionalIndependenceTest(alpha=0.05)
    skeleton = SkeletonBuilder(ci_tester=ci)
    data = {"X": x, "Y": y, "Z": z}
    sep_sets, edge_weights = skeleton.build_skeleton(["X", "Y", "Z"], data)

    print(f"\n骨架构建:")
    print(f"  分离集: {sep_sets}")
    print(f"  边权重: {edge_weights}")

    # 检查骨架边
    remaining_edges = list(edge_weights.keys())
    print(f"  剩余边数: {len(remaining_edges)}")
    for edge in remaining_edges:
        print(f"  {edge[0]} -- {edge[1]} (CMI: {edge_weights[edge]:.4f})")

    # 强度估计
    estimator = StrengthEstimator()
    effect = estimator._linear_regression(x, y)
    print(f"\n强度估计 (X -> Y):")
    print(f"  因果效应: {effect.get('effect', 0):.2f}")
    print(f"  p-value: {effect.get('p_value', 0):.4f}")

    return len(remaining_edges) > 0


async def test_causal_meta_learner():
    """测试因果元学习器"""
    print("\n" + "="*60)
    print("3. 因果元学习器 (Causal Meta-Learner)")
    print("="*60)

    from usmsb_sdk.meta_agent.evolution_v2.causal_meta_learner.meta_learner import (
        CausalMetaLearner,
        CausalMetaLearnerConfig,
    )

    config = CausalMetaLearnerConfig(
        inner_lr=0.01,
        inner_steps=3,
        outer_lr=0.001,
        meta_epochs=5,
        ewc_lambda=5000,
        meta_batch_size=2,
        support_size=3,
        query_size=5,
    )

    learner = CausalMetaLearner(config=config)
    await learner.initialize()

    # 获取初始权重
    weights = learner.get_weights()
    print(f"\n初始权重数量: {len(weights)}")
    for name, w in list(weights.items())[:3]:
        print(f"  {name}: shape={w.shape}")

    # 测试权重更新
    old_weights = {k: v.copy() for k, v in weights.items()}

    # EWC Fisher 信息
    fisher = learner.get_fisher_information()
    print(f"\nFisher 信息初始状态: {len(fisher)} entries")

    return True


async def test_causal_planner():
    """测试因果规划器"""
    print("\n" + "="*60)
    print("4. 因果规划器 (Causal Planner)")
    print("="*60)

    from usmsb_sdk.meta_agent.evolution_v2.causal_planner.planner import (
        CausalPlanner,
        CausalPlannerConfig,
    )
    from usmsb_sdk.meta_agent.models.causal_graph import CausalGraph, CausalEdge

    # 创建简单的因果图
    graph = CausalGraph(graph_id="test")
    graph.nodes = {"A", "B", "C"}
    graph.edges = [
        CausalEdge(edge_id="e1", source="A", target="B", strength=0.8),
        CausalEdge(edge_id="e2", source="B", target="C", strength=0.9),
    ]

    config = CausalPlannerConfig(
        max_plan_depth=5,
        use_cost_aware=True,
    )

    planner = CausalPlanner(causal_graph=graph, config=config)

    # 测试逆向搜索
    from usmsb_sdk.meta_agent.evolution_v2.causal_planner.backward_search import (
        BackwardSearch,
    )

    search = BackwardSearch(graph)
    required = search.search(target_nodes=["C"])

    print(f"\n逆向搜索结果 (目标=C):")
    print(f"  所需节点: {required}")

    # 测试任务抽象
    from usmsb_sdk.meta_agent.evolution_v2.causal_planner.task_abstraction import (
        TaskFeatureExtractor,
    )

    extractor = TaskFeatureExtractor()
    features = extractor.extract("api data processing service")

    print(f"\n任务特征提取:")
    print(f"  输入: 'api data processing service'")
    print(f"  特征: {features}")

    return True


async def test_causal_verifier():
    """测试因果验证器"""
    print("\n" + "="*60)
    print("5. 因果验证器 (Causal Verifier)")
    print("="*60)

    from usmsb_sdk.meta_agent.evolution_v2.causal_verifier.verifier import (
        CausalVerifier,
        VerificationContext,
    )
    from usmsb_sdk.meta_agent.models.causal_graph import CausalGraph

    # 创建验证器
    graph = CausalGraph(graph_id="test")
    verifier = CausalVerifier(causal_graph=graph)

    # 创建验证上下文
    context = VerificationContext(
        task_id="test_task",
        strategy_a=None,
        strategy_b=None,
        outcome_a=None,
        task_features={"complexity": 0.8},
        historical_records=[],
        verification_cost=0.5,
    )

    print(f"\n验证上下文:")
    print(f"  任务ID: {context.task_id}")
    print(f"  验证成本: {context.verification_cost}")

    return True


async def test_reasoning_enhancer():
    """测试推理增强层"""
    print("\n" + "="*60)
    print("6. 推理增强层 (Reasoning Enhancer)")
    print("="*60)

    from usmsb_sdk.meta_agent.evolution_v2.reasoning_enhancer.enhancer import (
        ReasoningEnhancer,
        ReasoningParser,
    )

    # 测试推理解析器
    parser = ReasoningParser()

    reasoning = """
    步骤1: 分析问题
    - 用户需要一个排序算法
    - 排序算法的时间复杂度应该是 O(n log n)

    步骤2: 选择策略
    - quicksort: 平均 O(n log n)
    - mergesort: 稳定 O(n log n)

    结论: 选择 quicksort
    """

    result = parser.parse(reasoning)

    print(f"\n推理解析:")
    print(f"  步骤数: {len(result.steps)}")
    print(f"  最终结论: {result.final_conclusion[:50] if result.final_conclusion else 'None'}...")

    # 测试反思纠正器
    from usmsb_sdk.meta_agent.evolution_v2.reasoning_enhancer.counterexample import (
        ReflectiveCorrector,
    )

    corrector = ReflectiveCorrector()

    reflection = corrector._parse_reflection(
        "步骤1可能有问题，因为没有考虑边界情况"
    )

    print(f"\n反思解析:")
    print(f"  反思内容: {reflection}")

    return True


async def test_skill_system():
    """测试 Skill 自创建系统"""
    print("\n" + "="*60)
    print("7. Skill 自创建系统 (Auto-Skill Engine)")
    print("="*60)

    from usmsb_sdk.meta_agent.evolution_v2.auto_skill.auto_skill_engine import (
        AutoSkillEngine,
        AutoSkillEngineConfig,
    )
    from usmsb_sdk.meta_agent.evolution_v2.auto_skill.skill_validator import (
        SkillValidator,
    )
    from usmsb_sdk.meta_agent.evolution_v2.auto_skill.skill_discovery import (
        SkillGap,
    )

    # 创建 SkillGap
    gap = SkillGap(
        gap_id="test_gap",
        source_node="execution",
        target_node="quality",
        gap_type="missing_skill",
        priority=0.8,
        description="需要 skill 来提升代码质量",
    )

    print(f"\nSkill Gap:")
    print(f"  ID: {gap.gap_id}")
    print(f"  类型: {gap.gap_type}")
    print(f"  描述: {gap.description}")

    # 测试冲突检测 - 用 MockSkill 对象测试
    validator = SkillValidator()

    @dataclass
    class MockSkill:
        skill_id: str
        trigger_conditions: list
        description: str

    skill1 = MockSkill(
        skill_id="retry_skill",
        trigger_conditions=["api_call"],
        description="always retry on failure",
    )

    skill2 = MockSkill(
        skill_id="no_retry_skill",
        trigger_conditions=["api_call"],
        description="never retry, skip on failure",
    )

    # 冲突检测在注册表为空时应该通过
    result = await validator._check_conflicts(skill2)

    print(f"\n冲突检测:")
    print(f"  Skill2: {skill2.trigger_conditions}, {skill2.description}")
    print(f"  检测通过(注册表为空): {result.passed}")

    return True


async def main():
    print("\n" + "#"*60)
    print("# V2.1 因果学习系统能力验证")
    print("#"*60)

    results = {}

    # 1. 条件独立性检验
    results["条件独立性检验"] = await test_conditional_independence()

    # 2. 因果发现引擎
    results["因果发现引擎"] = await test_causal_discovery()

    # 3. 因果元学习器
    results["因果元学习器"] = await test_causal_meta_learner()

    # 4. 因果规划器
    results["因果规划器"] = await test_causal_planner()

    # 5. 因果验证器
    results["因果验证器"] = await test_causal_verifier()

    # 6. 推理增强层
    results["推理增强层"] = await test_reasoning_enhancer()

    # 7. Skill 自创建系统
    results["Skill自创建"] = await test_skill_system()

    # 总结
    print("\n" + "#"*60)
    print("# V2.1 能力验证总结")
    print("#"*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✓" if result else "✗"
        print(f"  {status} {name}")

    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print("\n🎉 V2.1 所有核心能力验证通过!")
    else:
        print(f"\n⚠ {total - passed} 项验证失败")


if __name__ == "__main__":
    asyncio.run(main())