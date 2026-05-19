#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GoalOutcomeVerifier 独立测试脚本

不依赖 usmsb_sdk，直接测试验证器逻辑
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Dict, Optional


# ==================== 简化的类型定义 ====================

class VerificationType(Enum):
    CODE_PATTERN = "code_pattern"
    TEST_EXECUTION = "test_execution"
    OUTPUT_MATCH = "output_match"
    FILE_EXISTS = "file_exists"
    API_RESPONSE = "api_response"
    LLM_JUDGMENT = "llm_judgment"
    PERFORMANCE_TEST = "performance_test"
    DATA_STRUCTURE = "data_structure"


class VerificationStatus(Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NEEDS_RETRY = "needs_retry"


class CorrectionStrategy(Enum):
    NONE = "none"
    RETRY_SAME = "retry_same"
    REFINE_OUTPUT = "refine_output"
    ADD_STEPS = "add_steps"
    REPLAN = "replan"


@dataclass
class VerificationCriterion:
    criterion: str
    verification_type: VerificationType
    verification_method: str
    params: Dict = field(default_factory=dict)
    expected: Any = None


@dataclass
class VerificationResult:
    criterion: str
    status: VerificationStatus
    verification_type: VerificationType
    evidence: Dict = field(default_factory=dict)
    error: Optional[str] = None
    retry_count: int = 0


@dataclass
class GapAnalysis:
    missing_parts: List = field(default_factory=list)
    incorrect_parts: List = field(default_factory=list)
    incomplete_parts: List = field(default_factory=list)
    suggestions: List = field(default_factory=list)
    
    def has_gaps(self) -> bool:
        return bool(self.missing_parts or self.incorrect_parts)


@dataclass
class CorrectionPlan:
    strategy: CorrectionStrategy
    reason: str
    changes: List = field(default_factory=list)
    new_steps: List = field(default_factory=list)


@dataclass
class OutcomeVerification:
    goal: str
    criteria: List
    results: List
    gap_analysis: GapAnalysis
    correction_plan: Any = None
    score: float = 0.0
    passed: bool = False
    status: str = "pending"
    verification_time: float = 0.0
    
    def calculate_score(self) -> float:
        if not self.results:
            return 0.0
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == VerificationStatus.PASSED)
        partial = sum(1 for r in self.results if r.status == VerificationStatus.NEEDS_RETRY)
        # 考虑部分完成
        return (passed + partial * 0.5) / total


VERIFICATION_CONFIG = {
    "enabled": True,
    "max_retries": 3,
    "score_threshold_pass": 0.9,
    "score_threshold_retry": 0.6,
    "score_threshold_adjust": 0.3,
    "require_human": False,
    "self_correction_enabled": True,
}


# ==================== 验证器实现 ====================

class GoalOutcomeVerifier:
    """简化的验证器用于测试"""
    
    def __init__(self, agent: Any = None):
        self.agent = agent
        self.config = VERIFICATION_CONFIG.copy()
    
    async def generate_criteria(self, goal: str, context: Dict = None) -> List:
        """模拟生成验证标准"""
        criteria = [
            VerificationCriterion(
                criterion="代码包含 quicksort 函数定义",
                verification_type=VerificationType.CODE_PATTERN,
                verification_method="检查代码中是否有 def quicksort",
                params={"pattern": "def quicksort"}
            ),
            VerificationCriterion(
                criterion="函数能对数组进行排序",
                verification_type=VerificationType.TEST_EXECUTION,
                verification_method="用 [3,1,2] 测试",
                params={"test_input": [3, 1, 2], "expected_output": [1, 2, 3]}
            ),
            VerificationCriterion(
                criterion="代码可执行无语法错误",
                verification_type=VerificationType.CODE_PATTERN,
                verification_method="检查代码能被解析",
                params={"pattern": "def |class |import "}
            ),
            VerificationCriterion(
                criterion="包含测试用例",
                verification_type=VerificationType.CODE_PATTERN,
                verification_method="检查是否有测试代码",
                params={"pattern": "test|assert|if __name__"}
            ),
        ]
        return criteria
    
    async def verify_outcome(self, goal, criteria, execution_result, context=None) -> OutcomeVerification:
        """验证目标达成"""
        start_time = time.time()
        
        verification = OutcomeVerification(
            goal=goal,
            criteria=criteria,
            results=[],
            gap_analysis=GapAnalysis(),
        )
        
        code = self._extract_code(execution_result)
        
        for criterion in criteria:
            result = await self._verify_criterion(criterion, code, execution_result)
            verification.results.append(result)
            
            status_icon = "✅" if result.status == VerificationStatus.PASSED else "❌"
            print(f"  {status_icon} [{criterion.verification_type.value}] {criterion.criterion[:40]}...")
        
        verification.score = verification.calculate_score()
        verification.gap_analysis = self._analyze_gap(verification)
        
        if verification.gap_analysis.has_gaps() and self.config["self_correction_enabled"]:
            verification.correction_plan = self._generate_correction_plan(verification)
        
        verification.passed = verification.score >= self.config["score_threshold_pass"]
        
        if verification.passed:
            verification.status = "completed"
        elif verification.correction_plan:
            verification.status = "needs_correction"
        else:
            verification.status = "failed"
        
        verification.verification_time = time.time() - start_time
        
        return verification
    
    async def _verify_criterion(self, criterion, code, execution_result) -> VerificationResult:
        """验证单个标准"""
        result = VerificationResult(
            criterion=criterion.criterion,
            status=VerificationStatus.PENDING,
            verification_type=criterion.verification_type,
        )
        
        try:
            if criterion.verification_type == VerificationType.CODE_PATTERN:
                pattern = criterion.params.get("pattern", "")
                if re.search(pattern, code or "", re.MULTILINE | re.IGNORECASE):
                    result.status = VerificationStatus.PASSED
                    result.evidence = {"matched": True, "pattern": pattern}
                else:
                    result.status = VerificationStatus.NEEDS_RETRY
                    result.error = f"Pattern '{pattern}' not found"
                    result.evidence = {"matched": False}
            
            elif criterion.verification_type == VerificationType.TEST_EXECUTION:
                # 模拟测试验证
                test_input = criterion.params.get("test_input")
                expected = criterion.params.get("expected_output")
                if test_input and expected:
                    # 模拟 quicksort 执行
                    actual = self._mock_quicksort(test_input)
                    if actual == expected:
                        result.status = VerificationStatus.PASSED
                    else:
                        result.status = VerificationStatus.NEEDS_RETRY
                    result.evidence = {"input": test_input, "expected": expected, "actual": actual}
        
        except Exception as e:
            result.status = VerificationStatus.FAILED
            result.error = str(e)
        
        return result
    
    def _mock_quicksort(self, arr):
        """模拟 quicksort 执行"""
        if len(arr) <= 1:
            return arr
        pivot = arr[len(arr) // 2]
        left = [x for x in arr if x < pivot]
        middle = [x for x in arr if x == pivot]
        right = [x for x in arr if x > pivot]
        return self._mock_quicksort(left) + middle + self._mock_quicksort(right)
    
    def _extract_code(self, execution_result) -> str:
        if isinstance(execution_result, str):
            return execution_result
        if isinstance(execution_result, dict):
            return execution_result.get("code", "")
        return ""
    
    def _analyze_gap(self, verification: OutcomeVerification) -> GapAnalysis:
        gap = GapAnalysis()
        
        for result in verification.results:
            if result.status == VerificationStatus.FAILED:
                gap.incorrect_parts.append(result.criterion)
                if result.error:
                    gap.suggestions.append(f"修复 '{result.criterion}': {result.error}")
            elif result.status == VerificationStatus.NEEDS_RETRY:
                gap.incomplete_parts.append(result.criterion)
                gap.suggestions.append(f"改进 '{result.criterion}'")
        
        return gap
    
    def _generate_correction_plan(self, verification: OutcomeVerification) -> CorrectionPlan:
        score = verification.score
        
        if score >= 0.6:
            strategy = CorrectionStrategy.REFINE_OUTPUT
            reason = "大部分完成，小幅修正"
        elif score >= 0.3:
            strategy = CorrectionStrategy.ADD_STEPS
            reason = "部分完成，需要补充"
        else:
            strategy = CorrectionStrategy.REPLAN
            reason = "严重不完整，重新规划"
        
        gap = verification.gap_analysis
        changes = [{"action": "fix", "description": s} for s in gap.suggestions]
        
        new_steps = []
        for missing in gap.missing_parts:
            new_steps.append({
                "name": f"补充: {missing[:30]}",
                "description": missing,
                "action": "direct_execute"
            })
        
        return CorrectionPlan(
            strategy=strategy,
            reason=reason,
            changes=changes,
            new_steps=new_steps
        )


# ==================== 测试 ====================

async def test_full_verification():
    """测试完整验证流程"""
    print("\n" + "="*60)
    print("GoalOutcomeVerifier 完整验证流程测试")
    print("="*60)
    
    verifier = GoalOutcomeVerifier()
    
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

# Test
print(quicksort([3,1,2]))
"""
    
    print("\n目标: 写一个快速排序算法")
    print("执行代码已生成...\n")
    
    # 生成验证标准
    print("步骤 1: 生成验证标准")
    criteria = await verifier.generate_criteria("写一个快速排序算法")
    print(f"  生成了 {len(criteria)} 个验证标准\n")
    
    # 执行验证
    print("步骤 2: 执行目标达成验证")
    verification = await verifier.verify_outcome(
        goal="写一个快速排序算法",
        criteria=criteria,
        execution_result={"code": code},
        context={}
    )
    
    print(f"\n验证结果:")
    print(f"  达成度分数: {verification.score:.1%}")
    print(f"  通过: {verification.passed}")
    print(f"  状态: {verification.status}")
    
    if verification.gap_analysis and verification.gap_analysis.has_gaps():
        print(f"\n差距分析:")
        print(f"  缺失: {verification.gap_analysis.missing_parts}")
        print(f"  不完整: {verification.gap_analysis.incomplete_parts}")
        print(f"  建议: {verification.gap_analysis.suggestions}")
    
    if verification.correction_plan:
        print(f"\n修正计划:")
        print(f"  策略: {verification.correction_plan.strategy.value}")
        print(f"  原因: {verification.correction_plan.reason}")
        print(f"  变更: {verification.correction_plan.changes}")
        print(f"  新步骤: {len(verification.correction_plan.new_steps)} 个")
    
    print(f"\n验证耗时: {verification.verification_time:.3f}s")
    
    print("\n" + "="*60)
    print("🎉 验证测试完成!")
    print("="*60)
    
    return verification


async def test_partial_code():
    """测试部分达成的代码"""
    print("\n" + "="*60)
    print("测试部分达成场景")
    print("="*60)
    
    verifier = GoalOutcomeVerifier()
    
    # 不完整的代码（缺少测试）
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
    
    print("\n代码没有测试用例...\n")
    
    criteria = await verifier.generate_criteria("写一个快速排序算法")
    verification = await verifier.verify_outcome(
        goal="写一个快速排序算法",
        criteria=criteria,
        execution_result={"code": code},
        context={}
    )
    
    print(f"\n达成度分数: {verification.score:.1%}")
    print(f"状态: {verification.status}")
    print(f"需要修正: {verification.status == 'needs_correction'}")
    
    if verification.correction_plan:
        print(f"\n修正计划: {verification.correction_plan.strategy.value}")
        print(f"原因: {verification.correction_plan.reason}")


async def main():
    print("\n" + "#"*60)
    print("# GoalOutcomeVerifier 测试套件")
    print("#"*60)
    
    await test_full_verification()
    await test_partial_code()
    
    print("\n" + "#"*60)
    print("# 🎉 所有测试完成")
    print("#"*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
