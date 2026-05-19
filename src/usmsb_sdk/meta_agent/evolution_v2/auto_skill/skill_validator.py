"""
Skill 验证器

AutoSkillEngine 的组件

验证 Skill 的功能正确性、质量和冲突
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    """检查结果"""
    passed: bool
    needs_improvement: bool = False
    issues: list[str] = None
    score: float = 0.0


@dataclass
class ValidationResult:
    """验证结果"""
    skill_id: str
    passed: bool
    checks: list[tuple[str, CheckResult]]
    quality_score: float
    issues: list[str]


class SkillValidator:
    """
    Skill 验证器

    验证维度：
    1. 功能正确性：测试用例通过
    2. 因果效应：skill 是否真的激活了对应因果边
    3. 质量评分：prompt 质量、代码质量
    4. 冲突检测：是否与现有 skill 冲突
    """

    def __init__(
        self,
        causal_graph=None,
        llm_manager=None,
        skill_registry=None,
    ):
        """
        初始化

        Args:
            causal_graph: 因果图
            llm_manager: LLM 管理器
            skill_registry: Skill 注册表（用于冲突检测）
        """
        self.graph = causal_graph
        self.llm = llm_manager
        self.registry = skill_registry or {}

    async def validate(
        self,
        skill: Any,
        test_cases: list[dict[str, Any]],
    ) -> ValidationResult:
        """
        验证 Skill

        Args:
            skill: Skill 对象
            test_cases: 测试用例

        Returns:
            验证结果
        """
        checks = []

        # 1. 功能正确性
        functional_result = await self._check_functional(skill, test_cases)
        checks.append(("functional", functional_result))

        # 2. 质量评分
        quality_result = await self._check_quality(skill)
        checks.append(("quality", quality_result))

        # 3. 冲突检测
        conflict_result = await self._check_conflicts(skill)
        checks.append(("conflict", conflict_result))

        # 4. 因果效应
        if self.graph:
            causal_result = await self._check_causal_effect(skill)
            checks.append(("causal_effect", causal_result))

        # 汇总结果
        all_passed = all(r.passed for _, r in checks)
        needs_improvement = any(r.needs_improvement for _, r in checks)

        issues = []
        for name, result in checks:
            if result.issues:
                issues.extend([f"[{name}] {i}" for i in result.issues])

        quality_score = sum(r.score for _, r in checks) / len(checks) if checks else 0.0

        return ValidationResult(
            skill_id=getattr(skill, "skill_id", "unknown"),
            passed=all_passed and not needs_improvement,
            checks=checks,
            quality_score=quality_score,
            issues=issues,
        )

    async def _check_functional(
        self,
        skill: Any,
        test_cases: list[dict[str, Any]],
    ) -> CheckResult:
        """
        功能正确性检查

        Args:
            skill: Skill
            test_cases: 测试用例

        Returns:
            检查结果
        """
        if not test_cases:
            return CheckResult(passed=False, issues=["没有测试用例"], score=0.0)

        passed = 0
        failed = 0

        for tc in test_cases:
            input_data = tc.get("input")
            expected_output = tc.get("output")

            # 执行 skill（简化版）
            try:
                actual_output = await self._execute_skill(skill, input_data)

                if expected_output:
                    if self._outputs_match(actual_output, expected_output):
                        passed += 1
                    else:
                        failed += 1
                else:
                    passed += 1  # 没有预期输出，只检查执行不报错
            except Exception:
                failed += 1

        total = passed + failed
        pass_rate = passed / total if total > 0 else 0

        return CheckResult(
            passed=pass_rate >= 0.8,
            needs_improvement=pass_rate < 0.8,
            issues=[f"通过率 {pass_rate:.1%}"] if pass_rate < 0.8 else [],
            score=pass_rate,
        )

    async def _execute_skill(self, skill: Any, input_data: Any) -> Any:
        """执行 Skill"""
        skill_type = getattr(skill, "skill_type", "prompt")
        skill_path = getattr(skill, "path", None)

        if skill_type == "code" and skill_path:
            # 真实执行 code skill
            test_file = Path(skill_path) / "test_skill.py"
            if test_file.exists():
                try:
                    result = subprocess.run(
                        ["python", str(test_file)],
                        capture_output=True, text=True, timeout=30,
                        input=str(input_data)
                    )
                    return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
                except subprocess.TimeoutExpired:
                    return "Error: Execution timeout"
                except Exception as e:
                    return f"Error: {e}"
        # Prompt skill 或无路径的 code skill
        if self.llm:
            return await self.llm.generate(str(input_data))
        return str(input_data)

    def _outputs_match(self, actual: Any, expected: Any) -> bool:
        """检查输出是否匹配"""
        if isinstance(expected, str):
            return expected.lower() in str(actual).lower()
        return actual == expected

    async def _check_quality(self, skill: Any) -> CheckResult:
        """质量检查"""
        issues = []
        score = 0.5

        # 检查描述
        description = getattr(skill, "description", "")
        if len(description) < 10:
            issues.append("描述太短")
        else:
            score += 0.1

        # 检查名称
        name = getattr(skill, "name", "")
        if name and len(name) >= 3:
            score += 0.1

        # 检查版本
        version = getattr(skill, "version", "")
        if version:
            score += 0.1

        # 检查触发条件
        triggers = getattr(skill, "trigger_conditions", [])
        if len(triggers) >= 2:
            score += 0.1

        # 检查示例
        examples = getattr(skill, "examples", [])
        if len(examples) >= 2:
            score += 0.1

        return CheckResult(
            passed=len(issues) == 0,
            needs_improvement=score < 0.6,
            issues=issues,
            score=min(score, 1.0),
        )

    async def _check_conflicts(self, skill: Any) -> CheckResult:
        """冲突检查 - 检测 skill 之间是否冲突"""
        conflicts = []
        skill_triggers = set(getattr(skill, "trigger_conditions", []) or [])
        skill_desc = getattr(skill, "description", "").lower()
        skill_id = getattr(skill, "skill_id", None)

        # 与注册表中的 skill 检测冲突
        for existing_id, existing_info in self.registry.items():
            if existing_id == skill_id:
                continue

            existing_triggers = set(existing_info.get("trigger_conditions", []) or [])
            existing_desc = existing_info.get("description", "").lower()

            # 检查触发条件重叠
            overlap = skill_triggers & existing_triggers
            if overlap:
                conflicts.append(f"触发条件重叠: {overlap}")

            # 检查描述语义冲突
            if self._has_semantic_conflict(skill_desc, existing_desc):
                conflicts.append(f"与 {existing_id} 描述语义冲突")

        return CheckResult(
            passed=len(conflicts) == 0,
            score=1.0 - len(conflicts) * 0.2,
            issues=conflicts,
        )

    def _has_semantic_conflict(self, desc1: str, desc2: str) -> bool:
        """检测描述是否存在语义冲突"""
        conflict_pairs = [
            ("always", "never"), ("require", "skip"), ("must", "must_not"),
            ("enable", "disable"), ("allow", "forbid"),
        ]
        for pos, neg in conflict_pairs:
            if (pos in desc1 and neg in desc2) or (neg in desc1 and pos in desc2):
                return True
        return False

    async def _check_causal_effect(self, skill: Any) -> CheckResult:
        """因果效应检查"""
        if not self.graph:
            return CheckResult(passed=True, score=0.5)

        # 检查 skill 是否激活了因果边
        activates_edges = getattr(skill, "activates_edges", [])

        if not activates_edges:
            return CheckResult(
                passed=True,
                needs_improvement=True,
                issues=["没有关联因果边"],
                score=0.3,
            )

        # 检查激活的边是否在因果图中
        valid_edges = []
        for edge_id in activates_edges:
            for edge in self.graph.edges:
                if edge.edge_id == edge_id:
                    valid_edges.append(edge_id)
                    break

        if not valid_edges:
            return CheckResult(
                passed=False,
                issues=["激活的因果边都不在因果图中"],
                score=0.0,
            )

        coverage = len(valid_edges) / len(activates_edges)

        return CheckResult(
            passed=coverage >= 0.5,
            needs_improvement=coverage < 0.8,
            issues=[f"因果边覆盖率 {coverage:.1%}"] if coverage < 0.8 else [],
            score=coverage,
        )
