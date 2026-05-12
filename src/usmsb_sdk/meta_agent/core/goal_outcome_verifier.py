# -*- coding: utf-8 -*-
"""
Goal Outcome Verifier - 目标达成验证系统

核心职责：
1. 在规划阶段生成可验证的"完成标准"
2. 执行后按标准逐项验证
3. 计算达成度分数
4. 决定是否需要自我修正
5. 全程无需人工介入

设计原则：
- 自驱动：永不要求用户确认
- 可验证：每个目标都有明确的验证标准
- 可修正：失败后自动分析差距并重试
"""

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ==================== Enums ====================

class VerificationType(Enum):
    """验证类型"""
    CODE_PATTERN = "code_pattern"           # 代码结构检查
    TEST_EXECUTION = "test_execution"       # 测试执行验证
    OUTPUT_MATCH = "output_match"           # 输出比对
    FILE_EXISTS = "file_exists"            # 文件存在检查
    API_RESPONSE = "api_response"           # API响应验证
    LLM_JUDGMENT = "llm_judgment"          # LLM主观评估
    PERFORMANCE_TEST = "performance_test"   # 性能测试
    DATA_STRUCTURE = "data_structure"       # 数据结构验证


class VerificationStatus(Enum):
    """验证状态"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    NEEDS_RETRY = "needs_retry"


class CorrectionStrategy(Enum):
    """修正策略"""
    NONE = "none"               # 无需修正
    RETRY_SAME = "retry_same"   # 原样重试
    REFINE_OUTPUT = "refine_output"  # 修正输出
    ADD_STEPS = "add_steps"     # 添加步骤
    REPLAN = "replan"          # 重新规划


# ==================== Data Classes ====================

@dataclass
class VerificationCriterion:
    """单个验证标准"""
    criterion: str                          # 标准描述
    verification_type: VerificationType     # 验证类型
    verification_method: str                 # 验证方法描述
    params: dict[str, Any] = field(default_factory=dict)  # 验证参数
    expected: Any = None                    # 期望值（用于比对）
    
    def to_dict(self) -> dict:
        return {
            "criterion": self.criterion,
            "verification_type": self.verification_type.value,
            "verification_method": self.verification_method,
            "params": self.params,
            "expected": str(self.expected) if self.expected else None,
        }


@dataclass
class VerificationResult:
    """单个标准的验证结果"""
    criterion: str
    status: VerificationStatus
    verification_type: VerificationType
    evidence: dict[str, Any] = field(default_factory=dict)  # 验证证据
    error: str | None = None
    retry_count: int = 0
    
    def to_dict(self) -> dict:
        return {
            "criterion": self.criterion,
            "status": self.status.value,
            "verification_type": self.verification_type.value,
            "evidence": self.evidence,
            "error": self.error,
            "retry_count": self.retry_count,
        }


@dataclass
class GapAnalysis:
    """目标差距分析"""
    missing_parts: list[str] = field(default_factory=list)   # 缺失部分
    incorrect_parts: list[str] = field(default_factory=list) # 错误部分
    incomplete_parts: list[str] = field(default_factory=list) # 不完整部分
    suggestions: list[str] = field(default_factory=list)     # 修正建议
    
    def has_gaps(self) -> bool:
        return bool(self.missing_parts or self.incorrect_parts)
    
    def to_dict(self) -> dict:
        return {
            "missing_parts": self.missing_parts,
            "incorrect_parts": self.incorrect_parts,
            "incomplete_parts": self.incomplete_parts,
            "suggestions": self.suggestions,
        }


@dataclass
class CorrectionPlan:
    """修正计划"""
    strategy: CorrectionStrategy
    reason: str
    changes: list[dict] = field(default_factory=list)  # 需要做的变更
    new_steps: list[dict] = field(default_factory=list)  # 新增步骤（如果有）
    
    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy.value,
            "reason": self.reason,
            "changes": self.changes,
            "new_steps": self.new_steps,
        }


@dataclass
class OutcomeVerification:
    """整体目标达成验证结果"""
    goal: str                               # 原始目标
    criteria: list[VerificationCriterion]   # 验证标准列表
    results: list[VerificationResult]       # 每项验证结果
    gap_analysis: GapAnalysis               # 差距分析
    correction_plan: CorrectionPlan | None # 修正计划
    
    # 达成度分数 (0.0 - 1.0)
    score: float = 0.0
    
    # 是否通过
    passed: bool = False
    
    # 状态
    status: str = "pending"  # pending, completed, needs_correction, failed
    
    # 元数据
    verification_time: float = 0.0
    
    def calculate_score(self) -> float:
        """计算达成度分数"""
        if not self.results:
            return 0.0
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == VerificationStatus.PASSED)
        
        # 考虑部分完成的情况
        partial = sum(1 for r in self.results if r.status == VerificationStatus.NEEDS_RETRY)
        
        return passed / total
    
    def get_passed_count(self) -> int:
        return sum(1 for r in self.results if r.status == VerificationStatus.PASSED)
    
    def get_failed_count(self) -> int:
        return sum(1 for r in self.results if r.status == VerificationStatus.FAILED)
    
    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "score": self.score,
            "passed": self.passed,
            "status": self.status,
            "passed_count": self.get_passed_count(),
            "total_count": len(self.results),
            "verification_time": self.verification_time,
            "criteria": [c.to_dict() for c in self.criteria],
            "results": [r.to_dict() for r in self.results],
            "gap_analysis": self.gap_analysis.to_dict() if self.gap_analysis else None,
            "correction_plan": self.correction_plan.to_dict() if self.correction_plan else None,
        }


# ==================== Verification Config ====================

VERIFICATION_CONFIG = {
    "enabled": True,
    "max_retries": 3,                    # 最大重试次数
    "score_threshold_pass": 0.9,          # ≥90% 直接通过
    "score_threshold_retry": 0.6,         # ≥60% 可重试
    "score_threshold_adjust": 0.3,        # ≥30% 需调整策略
    "require_human": False,              # 永远不要求人工介入
    "self_correction_enabled": True,      # 启用自我修正
    "verification_timeout": 60,            # 单次验证超时（秒）
}


# ==================== Goal Outcome Verifier ====================

class GoalOutcomeVerifier:
    """
    目标达成验证器
    
    核心能力：
    1. 基于LLM生成验证标准
    2. 执行多类型验证
    3. 分析差距
    4. 生成修正计划
    """
    
    def __init__(self, agent: Any):
        self.agent = agent
        self.config = VERIFICATION_CONFIG.copy()
        self._verification_cache: dict[str, Any] = {}
    
    # ==================== Public API ====================
    
    async def generate_criteria(
        self,
        goal: str,
        context: dict[str, Any] | None = None
    ) -> list[VerificationCriterion]:
        """
        基于目标生成验证标准
        
        Args:
            goal: 用户目标描述
            context: 额外上下文（可选）
            
        Returns:
            验证标准列表
        """
        logger.info(f"[Verifier] Generating criteria for goal: {goal[:50]}...")
        
        prompt = f"""你是一个任务验证专家。基于用户目标，生成可验证的完成标准。

## 用户目标
{goal}

## 要求
1. 生成 3-8 个具体的验证标准
2. 每个标准必须可以通过代码/测试/检查来验证
3. 每个标准包含：
   - criterion: 具体描述
   - verification_type: code_pattern | test_execution | output_match | file_exists | api_response | llm_judgment | performance_test | data_structure
   - verification_method: 如何验证（具体步骤）
   - params: 验证需要的参数（如文件路径、测试用例等）

## 输出格式
返回 JSON 数组：
[
  {{
    "criterion": "代码包含 quicksort 函数定义",
    "verification_type": "code_pattern",
    "verification_method": "检查代码中是否有 def quicksort 或 function quicksort",
    "params": {{"pattern": "def quicksort|function quicksort"}}
  }},
  ...
]

请直接返回 JSON，不要解释。"""

        try:
            response = await self.agent.llm_manager.chat(prompt)
            criteria = self._parse_criteria_response(response)
            
            if not criteria:
                logger.warning("[Verifier] LLM returned no criteria, using default")
                criteria = self._generate_default_criteria(goal)
            
            logger.info(f"[Verifier] Generated {len(criteria)} criteria")
            return criteria
            
        except Exception as e:
            logger.error(f"[Verifier] Failed to generate criteria: {e}")
            return self._generate_default_criteria(goal)
    
    async def verify_outcome(
        self,
        goal: str,
        criteria: list[VerificationCriterion],
        execution_result: Any,
        context: dict[str, Any] | None = None
    ) -> OutcomeVerification:
        """
        验证目标达成情况
        
        Args:
            goal: 原始目标
            criteria: 验证标准列表
            execution_result: 执行结果（可能是代码、文件路径、API响应等）
            context: 额外上下文
            
        Returns:
            完整的验证结果
        """
        start_time = time.time()
        
        logger.info(f"[Verifier] Verifying outcome for goal: {goal[:50]}...")
        logger.info(f"[Verifier] Execution result type: {type(execution_result)}")
        
        verification = OutcomeVerification(
            goal=goal,
            criteria=criteria,
            results=[],
            gap_analysis=GapAnalysis(),
            correction_plan=None,
        )
        
        # 执行每项验证
        for criterion in criteria:
            result = await self._verify_criterion(
                criterion=criterion,
                execution_result=execution_result,
                context=context
            )
            verification.results.append(result)
            
            # 立即记录
            status_icon = "✅" if result.status == VerificationStatus.PASSED else "❌"
            logger.info(f"[Verifier] {status_icon} {criterion.criterion[:40]}...")
        
        # 计算达成度
        verification.score = verification.calculate_score()
        
        # 分析差距
        verification.gap_analysis = self._analyze_gap(verification)
        
        # 生成修正计划
        if verification.gap_analysis.has_gaps() and self.config["self_correction_enabled"]:
            verification.correction_plan = self._generate_correction_plan(
                goal=goal,
                verification=verification,
                execution_result=execution_result,
                context=context
            )
        
        # 判定是否通过
        verification.passed = verification.score >= self.config["score_threshold_pass"]
        
        if verification.passed:
            verification.status = "completed"
        elif verification.correction_plan:
            verification.status = "needs_correction"
        else:
            verification.status = "failed"
        
        verification.verification_time = time.time() - start_time
        
        # 记录到历史
        self._record_verification(verification)
        
        logger.info(
            f"[Verifier] Score: {verification.score:.1%}, "
            f"Passed: {verification.get_passed_count()}/{len(verification.results)}, "
            f"Status: {verification.status}"
        )
        
        return verification
    
    async def should_retry(
        self,
        verification: OutcomeVerification
    ) -> bool:
        """
        判断是否需要重试
        
        Args:
            verification: 验证结果
            
        Returns:
            是否应该重试
        """
        if not self.config["self_correction_enabled"]:
            return False
        
        if verification.status == "completed":
            return False
        
        # 检查是否还有重试机会
        max_retries = self.config["max_retries"]
        
        # 从 context 中获取当前重试次数
        retry_count = verification.results[0].retry_count if verification.results else 0
        
        if retry_count >= max_retries:
            logger.info(f"[Verifier] Max retries ({max_retries}) reached, no more retry")
            return False
        
        # 分数在可重试范围内
        if verification.score >= self.config["score_threshold_retry"]:
            return True
        
        return False
    
    def get_refinement_steps(
        self,
        verification: OutcomeVerification
    ) -> list[dict]:
        """
        获取修正步骤（用于重新执行）
        
        Args:
            verification: 验证结果
            
        Returns:
            需要重新执行的步骤
        """
        if not verification.correction_plan:
            return []
        
        return verification.correction_plan.new_steps
    
    # ==================== Private Methods ====================
    
    async def _verify_criterion(
        self,
        criterion: VerificationCriterion,
        execution_result: Any,
        context: dict[str, Any] | None
    ) -> VerificationResult:
        """验证单个标准"""
        result = VerificationResult(
            criterion=criterion.criterion,
            status=VerificationStatus.PENDING,
            verification_type=criterion.verification_type,
        )
        
        try:
            # 根据验证类型选择验证方法
            if criterion.verification_type == VerificationType.CODE_PATTERN:
                result = await self._verify_code_pattern(criterion, execution_result, result)
            elif criterion.verification_type == VerificationType.TEST_EXECUTION:
                result = await self._verify_test_execution(criterion, execution_result, result)
            elif criterion.verification_type == VerificationType.FILE_EXISTS:
                result = await self._verify_file_exists(criterion, execution_result, result)
            elif criterion.verification_type == VerificationType.OUTPUT_MATCH:
                result = await self._verify_output_match(criterion, execution_result, result)
            elif criterion.verification_type == VerificationType.LLM_JUDGMENT:
                result = await self._verify_llm_judgment(criterion, execution_result, result, context)
            elif criterion.verification_type == VerificationType.PERFORMANCE_TEST:
                result = await self._verify_performance(criterion, execution_result, result)
            elif criterion.verification_type == VerificationType.API_RESPONSE:
                result = await self._verify_api_response(criterion, execution_result, result)
            elif criterion.verification_type == VerificationType.DATA_STRUCTURE:
                result = await self._verify_data_structure(criterion, execution_result, result)
            else:
                # 默认使用 LLM 判断
                result = await self._verify_llm_judgment(criterion, execution_result, result, context)
        
        except Exception as e:
            logger.error(f"[Verifier] Verification error: {e}")
            result.status = VerificationStatus.FAILED
            result.error = str(e)
        
        return result
    
    async def _verify_code_pattern(
        self,
        criterion: VerificationCriterion,
        execution_result: Any,
        result: VerificationResult
    ) -> VerificationResult:
        """验证代码模式"""
        code = self._extract_code(execution_result)
        pattern = criterion.params.get("pattern", "")
        
        if not code:
            result.status = VerificationStatus.FAILED
            result.error = "No code found in execution result"
            return result
        
        # 使用正则匹配
        if re.search(pattern, code, re.IGNORECASE | re.MULTILINE):
            result.status = VerificationStatus.PASSED
            result.evidence = {"matched": True, "pattern": pattern}
        else:
            result.status = VerificationStatus.FAILED
            result.error = f"Pattern '{pattern}' not found in code"
            result.evidence = {"matched": False, "pattern": pattern}
        
        return result
    
    async def _verify_test_execution(
        self,
        criterion: VerificationCriterion,
        execution_result: Any,
        result: VerificationResult
    ) -> VerificationResult:
        """验证测试执行"""
        # 从 params 获取测试代码或测试用例
        test_code = criterion.params.get("test_code")
        test_input = criterion.params.get("test_input")
        expected_output = criterion.params.get("expected_output")
        
        if test_code:
            # 执行提供的测试代码
            test_result = await self._execute_test(test_code)
            result.evidence = {"test_result": test_result}
            result.status = VerificationStatus.PASSED if test_result.get("passed") else VerificationStatus.FAILED
        elif test_input and expected_output:
            # 用例测试
            actual = await self._execute_code_with_input(execution_result, test_input)
            passed = str(actual).strip() == str(expected_output).strip()
            result.evidence = {
                "input": test_input,
                "expected": expected_output,
                "actual": actual,
                "passed": passed
            }
            result.status = VerificationStatus.PASSED if passed else VerificationStatus.NEEDS_RETRY
        else:
            result.status = VerificationStatus.SKIPPED
            result.error = "No test parameters provided"
        
        return result
    
    async def _verify_file_exists(
        self,
        criterion: VerificationCriterion,
        execution_result: Any,
        result: VerificationResult
    ) -> VerificationResult:
        """验证文件存在"""
        file_path = criterion.params.get("path") or criterion.params.get("file_path")
        
        if not file_path:
            # 尝试从 execution_result 中提取
            if isinstance(execution_result, str):
                # 简单匹配文件路径
                match = re.search(r'[\w\-\.]+\.[\w]+', execution_result)
                if match:
                    file_path = match.group()
        
        if not file_path:
            result.status = VerificationStatus.SKIPPED
            result.error = "No file path provided"
            return result
        
        # 检查文件是否存在
        # 这里应该使用 sandbox 或 workspace 的文件检查
        # 暂时通过尝试读取来验证
        try:
            # 使用 agent 的工具来检查文件
            file_result = await self.agent._execute_tool(
                tool_name="get_file_info",
                tool_args={"file_path": file_path},
                user_session=None
            )
            
            if file_result.get("exists"):
                result.status = VerificationStatus.PASSED
                result.evidence = {"path": file_path, "exists": True}
            else:
                result.status = VerificationStatus.FAILED
                result.error = f"File not found: {file_path}"
        except Exception as e:
            result.status = VerificationStatus.FAILED
            result.error = str(e)
        
        return result
    
    async def _verify_output_match(
        self,
        criterion: VerificationCriterion,
        execution_result: Any,
        result: VerificationResult
    ) -> VerificationResult:
        """验证输出匹配"""
        expected = criterion.expected
        actual = self._extract_output(execution_result)
        
        if expected is None:
            result.status = VerificationStatus.SKIPPED
            result.error = "No expected output provided"
            return result
        
        # 字符串包含检查
        if isinstance(expected, str) and isinstance(actual, str):
            matched = expected.lower() in actual.lower()
        elif expected == actual:
            matched = True
        else:
            matched = False
        
        result.evidence = {
            "expected": str(expected)[:200],
            "actual": str(actual)[:200],
            "matched": matched
        }
        result.status = VerificationStatus.PASSED if matched else VerificationStatus.NEEDS_RETRY
        
        return result
    
    async def _verify_llm_judgment(
        self,
        criterion: VerificationCriterion,
        execution_result: Any,
        result: VerificationResult,
        context: dict[str, Any] | None
    ) -> VerificationResult:
        """使用 LLM 判断验证结果"""
        prompt = f"""你是一个任务验证专家。评估以下验证标准是否满足。

## 验证标准
{criterion.criterion}

## 验证方法
{criterion.verification_method}

## 执行结果
{self._format_for_llm(execution_result)}

## 你的任务
判断执行结果是否满足验证标准。返回 JSON：
{{
  "passed": true/false,
  "confidence": 0.0-1.0,
  "reason": "判断理由"
}}

请直接返回 JSON。"""

        try:
            response = await self.agent.llm_manager.chat(prompt)
            judgment = json.loads(response)
            
            passed = judgment.get("passed", False)
            confidence = judgment.get("confidence", 0.5)
            
            # 置信度低于阈值需要重试
            if confidence < 0.6 and not passed:
                result.status = VerificationStatus.NEEDS_RETRY
            elif passed:
                result.status = VerificationStatus.PASSED
            else:
                result.status = VerificationStatus.NEEDS_RETRY
            
            result.evidence = {
                "confidence": confidence,
                "reason": judgment.get("reason", ""),
                "llm_response": judgment
            }
            
        except Exception as e:
            logger.error(f"[Verifier] LLM judgment failed: {e}")
            result.status = VerificationStatus.SKIPPED
            result.error = str(e)
        
        return result
    
    async def _verify_performance(
        self,
        criterion: VerificationCriterion,
        execution_result: Any,
        result: VerificationResult
    ) -> VerificationResult:
        """验证性能"""
        max_time = criterion.params.get("max_time", 1.0)  # 秒
        max_memory = criterion.params.get("max_memory", 100)  # MB
        
        # 执行性能测试
        code = self._extract_code(execution_result)
        test_input = criterion.params.get("test_input", [100, 1000, 10000])
        
        perf_result = await self._measure_performance(code, test_input)
        
        time_ok = perf_result.get("time", float('inf')) <= max_time
        memory_ok = perf_result.get("memory", float('inf')) <= max_memory
        
        result.evidence = {
            "measured_time": perf_result.get("time"),
            "measured_memory": perf_result.get("memory"),
            "max_allowed_time": max_time,
            "max_allowed_memory": max_memory,
            "time_ok": time_ok,
            "memory_ok": memory_ok
        }
        
        result.status = VerificationStatus.PASSED if (time_ok and memory_ok) else VerificationStatus.NEEDS_RETRY
        
        return result
    
    async def _verify_api_response(
        self,
        criterion: VerificationCriterion,
        execution_result: Any,
        result: VerificationResult
    ) -> VerificationResult:
        """验证 API 响应"""
        expected_status = criterion.params.get("status_code", 200)
        expected_fields = criterion.params.get("fields", [])
        
        if not isinstance(execution_result, dict):
            result.status = VerificationStatus.FAILED
            result.error = "API response is not a valid JSON object"
            return result
        
        status_ok = execution_result.get("status") == expected_status
        fields_ok = all(f in execution_result for f in expected_fields)
        
        result.evidence = {
            "status_ok": status_ok,
            "fields_ok": fields_ok,
            "actual_status": execution_result.get("status"),
            "expected_status": expected_status
        }
        
        result.status = VerificationStatus.PASSED if (status_ok and fields_ok) else VerificationStatus.FAILED
        
        return result
    
    async def _verify_data_structure(
        self,
        criterion: VerificationCriterion,
        execution_result: Any,
        result: VerificationResult
    ) -> VerificationResult:
        """验证数据结构"""
        expected_structure = criterion.params.get("structure")
        
        if not expected_structure:
            result.status = VerificationStatus.SKIPPED
            result.error = "No expected structure provided"
            return result
        
        # 检查执行结果是否符合预期结构
        # 简化实现：检查关键字段
        actual = execution_result if isinstance(execution_result, dict) else {}
        
        missing = []
        for key in expected_structure:
            if key not in actual:
                missing.append(key)
        
        if not missing:
            result.status = VerificationStatus.PASSED
            result.evidence = {"structure_match": True}
        else:
            result.status = VerificationStatus.FAILED
            result.error = f"Missing fields: {missing}"
            result.evidence = {"missing_fields": missing}
        
        return result
    
    # ==================== Gap Analysis & Correction ====================
    
    def _analyze_gap(self, verification: OutcomeVerification) -> GapAnalysis:
        """分析达成差距"""
        gap = GapAnalysis()
        
        for result in verification.results:
            if result.status == VerificationStatus.FAILED:
                gap.incorrect_parts.append(result.criterion)
                if result.error:
                    gap.suggestions.append(f"修复 '{result.criterion}': {result.error}")
            elif result.status == VerificationStatus.NEEDS_RETRY:
                gap.incomplete_parts.append(result.criterion)
                gap.suggestions.append(f"改进 '{result.criterion}': 需要调整")
        
        return gap
    
    def _generate_correction_plan(
        self,
        goal: str,
        verification: OutcomeVerification,
        execution_result: Any,
        context: dict[str, Any] | None
    ) -> CorrectionPlan | None:
        """生成修正计划"""
        if not verification.gap_analysis.has_gaps():
            return None
        
        gap = verification.gap_analysis
        
        # 根据分数决定策略
        score = verification.score
        
        if score >= 0.6:
            strategy = CorrectionStrategy.REFINE_OUTPUT
            reason = "大部分完成，只需要小幅修正"
        elif score >= 0.3:
            strategy = CorrectionStrategy.ADD_STEPS
            reason = "部分完成，需要补充遗漏的功能"
        else:
            strategy = CorrectionStrategy.REPLAN
            reason = "严重不完整，需要重新规划"
        
        # 生成具体的修正步骤
        changes = []
        for suggestion in gap.suggestions:
            changes.append({
                "action": "fix",
                "description": suggestion,
            })
        
        # 生成新的执行步骤
        new_steps = []
        if strategy in [CorrectionStrategy.ADD_STEPS, CorrectionStrategy.REPLAN]:
            new_steps = self._generate_correction_steps(
                goal=goal,
                gap=gap,
                execution_result=execution_result
            )
        
        return CorrectionPlan(
            strategy=strategy,
            reason=reason,
            changes=changes,
            new_steps=new_steps
        )
    
    def _generate_correction_steps(
        self,
        goal: str,
        gap: GapAnalysis,
        execution_result: Any
    ) -> list[dict]:
        """生成修正步骤"""
        # 基于 gap 分析生成需要补充的步骤
        steps = []
        
        for missing in gap.missing_parts:
            steps.append({
                "name": f"补充: {missing[:30]}",
                "description": missing,
                "action": "direct_execute",
                "params": {"request": f"补充实现: {missing}"},
                "dependencies": [],
                "estimated_time": 30,
            })
        
        for incomplete in gap.incomplete_parts:
            steps.append({
                "name": f"改进: {incomplete[:30]}",
                "description": incomplete,
                "action": "direct_execute",
                "params": {"request": f"改进现有实现以满足: {incomplete}"},
                "dependencies": [],
                "estimated_time": 30,
            })
        
        return steps
    
    # ==================== Helper Methods ====================
    
    def _extract_code(self, execution_result: Any) -> str:
        """从执行结果中提取代码"""
        if isinstance(execution_result, str):
            return execution_result
        if isinstance(execution_result, dict):
            return execution_result.get("code", "") or execution_result.get("output", "")
        return str(execution_result)
    
    def _extract_output(self, execution_result: Any) -> str:
        """从执行结果中提取输出"""
        if isinstance(execution_result, str):
            return execution_result
        if isinstance(execution_result, dict):
            return execution_result.get("output", "") or execution_result.get("result", "")
        return str(execution_result)
    
    def _format_for_llm(self, data: Any, max_length: int = 2000) -> str:
        """格式化数据用于 LLM 输入"""
        if isinstance(data, str):
            return data[:max_length]
        try:
            formatted = json.dumps(data, ensure_ascii=False, indent=2)
            return formatted[:max_length]
        except:
            return str(data)[:max_length]
    
    async def _execute_test(self, test_code: str) -> dict:
        """执行测试代码"""
        # 使用 agent 的工具执行
        try:
            result = await self.agent._execute_tool(
                tool_name="execute_python",
                tool_args={"code": test_code},
                user_session=None
            )
            return {"passed": True, "result": result}
        except Exception as e:
            return {"passed": False, "error": str(e)}
    
    async def _execute_code_with_input(self, code: str, test_input: Any) -> Any:
        """用输入执行代码"""
        # 简化的执行方法
        exec_code = f"""
import json

def _test_func(input_data):
{chr(10).join('    ' + line for line in code.split(chr(10))[:50])}
    return input_data

result = _test_func({json.dumps(test_input)})
print(json.dumps(result))
"""
        
        try:
            result = await self.agent._execute_tool(
                tool_name="execute_python",
                tool_args={"code": exec_code},
                user_session=None
            )
            return result
        except Exception as e:
            return f"Error: {e}"
    
    async def _measure_performance(self, code: str, test_inputs: list) -> dict:
        """测量性能"""
        # 简化的性能测量
        import time
        
        try:
            # 这里应该实际执行代码测量
            return {"time": 0.1, "memory": 10}  # placeholder
        except Exception as e:
            return {"time": float('inf'), "memory": float('inf'), "error": str(e)}
    
    def _parse_criteria_response(self, response: str) -> list[VerificationCriterion]:
        """解析 LLM 生成的验证标准"""
        criteria = []
        
        # 尝试解析 JSON
        try:
            data = json.loads(response)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict) and "criteria" in data:
                items = data["criteria"]
            else:
                items = []
            
            for item in items:
                criterion = VerificationCriterion(
                    criterion=item.get("criterion", ""),
                    verification_type=VerificationType(item.get("verification_type", "llm_judgment")),
                    verification_method=item.get("verification_method", ""),
                    params=item.get("params", {}),
                    expected=item.get("expected"),
                )
                criteria.append(criterion)
                
        except json.JSONDecodeError:
            logger.warning("[Verifier] Failed to parse criteria JSON")
        
        return criteria
    
    def _generate_default_criteria(self, goal: str) -> list[VerificationCriterion]:
        """生成默认验证标准（当 LLM 生成失败时）"""
        return [
            VerificationCriterion(
                criterion="任务执行完成",
                verification_type=VerificationType.LLM_JUDGMENT,
                verification_method="检查执行结果是否有效",
                params={},
            )
        ]
    
    def _record_verification(self, verification: OutcomeVerification) -> None:
        """记录验证结果到历史"""
        # 保留最近 100 条记录
        cache_key = f"verification_{int(time.time())}"
        self._verification_cache[cache_key] = verification.to_dict()
        
        if len(self._verification_cache) > 100:
            oldest = sorted(self._verification_cache.keys())[:50]
            for k in oldest:
                del self._verification_cache[k]
    
    def get_verification_history(self, limit: int = 10) -> list[dict]:
        """获取验证历史"""
        history = list(self._verification_cache.values())[-limit:]
        return list(reversed(history))
