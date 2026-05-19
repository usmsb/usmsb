#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GoalOutcomeVerifier 测试脚本

测试目标达成验证系统的核心功能
"""

import asyncio
import json
import sys
sys.path.insert(0, 'src')

from usmsb_sdk.meta_agent.core.goal_outcome_verifier import (
    GoalOutcomeVerifier,
    VerificationCriterion,
    VerificationType,
    VerificationStatus,
    GapAnalysis,
    OutcomeVerification,
    VERIFICATION_CONFIG,
)


# Mock Agent for testing
class MockLLMManager:
    async def chat(self, prompt, system_prompt=None):
        # 模拟 LLM 返回验证标准
        if "生成" in prompt and "验证标准" in prompt:
            return json.dumps([
                {
                    "criterion": "代码包含快速排序函数定义",
                    "verification_type": "code_pattern",
                    "verification_method": "检查代码中是否有 def quicksort",
                    "params": {"pattern": "def quicksort|function quicksort"}
                },
                {
                    "criterion": "函数能对数组进行排序",
                    "verification_type": "test_execution",
                    "verification_method": "用 [3,1,2] 测试，检查返回 [1,2,3]",
                    "params": {"test_input": [3, 1, 2], "expected_output": [1, 2, 3]}
                },
                {
                    "criterion": "代码可执行无语法错误",
                    "verification_type": "code_pattern",
                    "verification_method": "检查代码能被 Python 解析",
                    "params": {"pattern": "def |class |import "}
                }
            ])
        # LLM 判断
        if "判断" in prompt:
            return json.dumps({"passed": True, "confidence": 0.9, "reason": "代码结构正确"})
        return json.dumps({"passed": True})


class MockAgent:
    def __init__(self):
        self.llm_manager = MockLLMManager()
    
    async def _execute_tool(self, tool_name, tool_args, user_session):
        return {"success": True, "result": "executed"}


async def test_criteria_generation():
    """测试验证标准生成"""
    print("\n" + "="*60)
    print("测试 1: 验证标准生成")
    print("="*60)
    
    agent = MockAgent()
    verifier = GoalOutcomeVerifier(agent)
    
    criteria = await verifier.generate_criteria(
        goal="写一个快速排序算法"
    )
    
    print(f"生成 {len(criteria)} 个验证标准:")
    for i, c in enumerate(criteria, 1):
        print(f"  {i}. [{c.verification_type.value}] {c.criterion}")
        print(f"     验证方法: {c.verification_method[:50]}...")
    
    assert len(criteria) > 0, "应该生成至少一个验证标准"
    print("\n✅ 测试通过")


async def test_code_pattern_verification():
    """测试代码模式验证"""
    print("\n" + "="*60)
    print("测试 2: 代码模式验证")
    print("="*60)
    
    agent = MockAgent()
    verifier = GoalOutcomeVerifier(agent)
    
    # 测试代码
    code = """
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
"""
    
    criterion = VerificationCriterion(
        criterion="代码包含快速排序函数",
        verification_type=VerificationType.CODE_PATTERN,
        verification_method="检查 def quicksort",
        params={"pattern": "def quicksort"}
    )
    
    result = await verifier._verify_code_pattern(
        criterion=criterion,
        execution_result=code,
        result=None
    )
    
    print(f"验证结果: {result.status.value if result else 'N/A'}")
    print(f"证据: {result.evidence if result else 'N/A'}")
    
    assert result.status == VerificationStatus.PASSED, "代码模式应该匹配"
    print("\n✅ 测试通过")


async def test_gap_analysis():
    """测试差距分析"""
    print("\n" + "="*60)
    print("测试 3: 差距分析")
    print("="*60)
    
    agent = MockAgent()
    verifier = GoalOutcomeVerifier(agent)
    
    # 模拟部分失败的验证结果
    verification = OutcomeVerification(
        goal="写一个快速排序算法",
        criteria=[],
        results=[
            type('Result', (), {
                'status': VerificationStatus.PASSED,
                'criterion': '代码包含 quicksort 函数'
            })(),
            type('Result', (), {
                'status': VerificationStatus.NEEDS_RETRY,
                'criterion': '测试用例全部通过',
                'error': '返回结果顺序不对'
            })(),
            type('Result', (), {
                'status': VerificationStatus.FAILED,
                'criterion': '时间复杂度正确',
                'error': 'O(n^2) 而非 O(n log n)'
            })(),
        ],
        gap_analysis=GapAnalysis(),
    )
    
    gap = verifier._analyze_gap(verification)
    
    print(f"缺失部分: {gap.missing_parts}")
    print(f"错误部分: {gap.incorrect_parts}")
    print(f"不完整部分: {gap.incomplete_parts}")
    print(f"建议: {gap.suggestions}")
    
    assert gap.has_gaps(), "应该有差距"
    print("\n✅ 测试通过")


async def test_correction_plan():
    """测试修正计划生成"""
    print("\n" + "="*60)
    print("测试 4: 修正计划生成")
    print("="*60)
    
    agent = MockAgent()
    verifier = GoalOutcomeVerifier(agent)
    
    # 创建有差距的验证结果
    verification = OutcomeVerification(
        goal="写一个快速排序算法",
        criteria=[],
        results=[],
        gap_analysis=GapAnalysis(
            incomplete_parts=["测试用例需要补充"],
            incorrect_parts=["时间复杂度不正确"],
            suggestions=["优化分区算法", "添加更多测试用例"]
        ),
    )
    verification.score = 0.66  # 66% 达成度
    
    correction = verifier._generate_correction_plan(
        goal=verification.goal,
        verification=verification,
        execution_result={},
        context={}
    )
    
    if correction:
        print(f"修正策略: {correction.strategy.value}")
        print(f"修正原因: {correction.reason}")
        print(f"变更数量: {len(correction.changes)}")
        print(f"新步骤数量: {len(correction.new_steps)}")
    else:
        print("无需修正")
    
    print("\n✅ 测试通过")


async def test_full_verification():
    """测试完整验证流程"""
    print("\n" + "="*60)
    print("测试 5: 完整验证流程")
    print("="*60)
    
    agent = MockAgent()
    verifier = GoalOutcomeVerifier(agent)
    
    # 生成验证标准
    criteria = await verifier.generate_criteria(
        goal="写一个快速排序算法"
    )
    
    # 模拟执行结果（代码）
    code = """
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)

# Test
print(quicksort([3,1,2]))
"""
    
    execution_result = {"code": code, "output": "执行成功"}
    
    # 执行验证
    verification = await verifier.verify_outcome(
        goal="写一个快速排序算法",
        criteria=criteria,
        execution_result=execution_result,
        context={}
    )
    
    print(f"达成度分数: {verification.score:.1%}")
    print(f"通过: {verification.passed}")
    print(f"状态: {verification.status}")
    print(f"验证详情:")
    for r in verification.results:
        icon = "✅" if r.status == VerificationStatus.PASSED else "❌"
        print(f"  {icon} [{r.verification_type.value}] {r.criterion[:40]}...")
    
    if verification.gap_analysis and verification.gap_analysis.has_gaps():
        print(f"\n差距分析:")
        print(f"  缺失: {verification.gap_analysis.missing_parts}")
        print(f"  错误: {verification.gap_analysis.incorrect_parts}")
        print(f"  建议: {verification.gap_analysis.suggestions[:2]}")
    
    if verification.correction_plan:
        print(f"\n修正计划:")
        print(f"  策略: {verification.correction_plan.strategy.value}")
        print(f"  原因: {verification.correction_plan.reason}")
    
    print("\n✅ 测试通过")


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("GoalOutcomeVerifier 测试套件")
    print("="*60)
    
    print(f"\n配置: {json.dumps(VERIFICATION_CONFIG, indent=2)}")
    
    try:
        await test_criteria_generation()
        await test_code_pattern_verification()
        await test_gap_analysis()
        await test_correction_plan()
        await test_full_verification()
        
        print("\n" + "="*60)
        print("🎉 所有测试通过!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
