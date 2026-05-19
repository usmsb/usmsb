"""
Skill 自创建系统验收测试

覆盖设计文档 10.6 节验收标准
"""

import asyncio
import pytest
from dataclasses import dataclass

from usmsb_sdk.meta_agent.evolution_v2.auto_skill.skill_creator import (
    SkillCreator,
    SkillCreationResult,
)
from usmsb_sdk.meta_agent.evolution_v2.auto_skill.skill_validator import (
    SkillValidator,
    CheckResult,
)
from usmsb_sdk.meta_agent.evolution_v2.auto_skill.skill_discovery import SkillGap
from usmsb_sdk.meta_agent.evolution_v2.auto_skill.skill_curator import SkillCurator


class MockSkill:
    """模拟 Skill 对象"""
    def __init__(
        self,
        skill_id: str = "test_skill",
        name: str = "Test Skill",
        description: str = "A test skill",
        skill_type: str = "prompt",
        path: str = "/tmp/test_skill",
        trigger_conditions: list = None,
        examples: list = None,
    ):
        self.skill_id = skill_id
        self.name = name
        self.description = description
        self.skill_type = skill_type
        self.path = path
        self.trigger_conditions = trigger_conditions or ["test_trigger"]
        self.examples = examples or [{"input": "test", "output": "result"}]


class TestSkillCreator:
    """Skill 创建器测试"""

    @pytest.fixture
    def creator(self):
        return SkillCreator()

    @pytest.mark.asyncio
    async def test_create_prompt_skill(self, creator, tmp_path):
        """测试创建 Prompt Skill"""
        result = await creator.create_prompt_skill(
            name="Test Prompt Skill",
            description="A test prompt skill",
            prompt_template="Solve {input} using {method}",
            trigger_conditions=["math", "calculation"],
            examples=[{"input": "2+2", "output": "4"}],
        )

        assert isinstance(result, SkillCreationResult)
        assert result.skill_type == "prompt"
        assert result.quality_score >= 0.0

    @pytest.mark.asyncio
    async def test_create_code_skill(self, creator, tmp_path):
        """测试创建 Code Skill"""
        result = await creator.create_code_skill(
            name="Test Code Skill",
            description="A test code skill",
            code="def main():\n    return 'hello'",
            tests="def test_main():\n    assert main() == 'hello'",
            dependencies=[],
            trigger_conditions=["code", "python"],
        )

        assert isinstance(result, SkillCreationResult)
        assert result.skill_type == "code"
        assert result.quality_score >= 0.0

    def test_generate_skill_id(self, creator):
        """测试 Skill ID 生成"""
        skill_id = creator._generate_skill_id("My Test Skill")
        assert isinstance(skill_id, str)


class TestSkillValidator:
    """Skill 验证器测试"""

    @pytest.fixture
    def validator(self):
        return SkillValidator()

    @pytest.mark.asyncio
    async def test_validate_prompt_skill(self, validator):
        """测试验证 Prompt Skill"""
        skill = MockSkill(skill_type="prompt")
        test_cases = [{"input": "test", "output": "result"}]

        result = await validator.validate(skill, test_cases)

        assert result is not None
        assert hasattr(result, "passed")
        assert hasattr(result, "quality_score")

    @pytest.mark.asyncio
    async def test_validate_no_test_cases(self, validator):
        """测试无测试用例验证"""
        skill = MockSkill()
        result = await validator.validate(skill, [])
        assert result is not None
        assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_check_conflicts_no_registry(self, validator):
        """测试无注册表时冲突检测"""
        skill = MockSkill()
        result = await validator._check_conflicts(skill)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_check_conflicts_with_overlap(self, validator):
        """测试触发条件重叠检测"""
        validator.registry = {
            "existing_skill": {
                "skill_id": "existing_skill",
                "description": "Always retry on failure",
                "trigger_conditions": ["api_call"],
            }
        }
        conflicting_skill = MockSkill(
            skill_id="new_skill",
            description="Never retry on failure",
            trigger_conditions=["api_call"],
        )
        result = await validator._check_conflicts(conflicting_skill)
        assert result.passed is False

    def test_has_semantic_conflict(self, validator):
        """测试语义冲突检测"""
        assert validator._has_semantic_conflict("always retry", "never retry") is True
        assert validator._has_semantic_conflict("retry once", "retry twice") is False


class TestSkillDiscovery:
    """Skill 缺口发现测试"""

    def test_skill_gap_creation(self):
        """测试 SkillGap 创建"""
        gap = SkillGap(
            gap_id="test_gap",
            source_node="input",
            target_node="output",
            gap_type="missing_capability",
            priority=0.8,
            description="Test gap",
        )
        assert gap.gap_id == "test_gap"
        assert gap.priority == 0.8


class TestSkillCurator:
    """Skill Curator 测试"""

    @pytest.fixture
    def curator(self):
        return SkillCurator(skill_registry={}, causal_graph=None)

    def test_curator_creation(self, curator):
        """测试 Curator 创建"""
        assert curator is not None


class MockLLM:
    """模拟 LLM"""
    async def generate(self, prompt):
        return "mocked response"


class TestAutoSkillEngine:
    """AutoSkillEngine 集成测试"""

    @pytest.mark.asyncio
    async def test_trigger_manual(self):
        """测试手动触发"""
        from usmsb_sdk.meta_agent.evolution_v2.auto_skill.auto_skill_engine import AutoSkillEngine, AutoSkillEngineConfig

        engine = AutoSkillEngine(llm_manager=MockLLM(), config=AutoSkillEngineConfig())
        result = await engine.trigger_manual("Test gap description")
        assert result is None or isinstance(result, str)
