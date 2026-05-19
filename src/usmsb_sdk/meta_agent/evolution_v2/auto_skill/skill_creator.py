"""
Skill 创建器

AutoSkillEngine 的组件

创建 Prompt Skill 和 Code Skill
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class SkillCreationResult:
    """Skill 创建结果"""
    skill_id: str
    skill_type: str  # "prompt" | "code"
    path: str
    quality_score: float


class SkillCreator:
    """
    Skill 创建器

    两种创建模式：
    1. Prompt Skill: 从 LLM 生成的 prompt 模板创建
    2. Code Skill: 从 LLM 生成的代码创建
    """

    def __init__(
        self,
        llm_manager=None,
        skills_base_dir: str = "skills",
    ):
        """
        初始化

        Args:
            llm_manager: LLM 管理器
            skills_base_dir: Skill 基础目录
        """
        self.llm = llm_manager
        self.skills_base_dir = Path(skills_base_dir)

    async def create_prompt_skill(
        self,
        name: str,
        description: str,
        prompt_template: str,
        trigger_conditions: list[str],
        examples: list[dict[str, Any]],
    ) -> SkillCreationResult:
        """
        创建 Prompt Skill

        Args:
            name: Skill 名称
            description: 描述
            prompt_template: Prompt 模板
            trigger_conditions: 触发条件
            examples: 示例

        Returns:
            创建结果
        """
        skill_id = self._generate_skill_id(name)

        # 创建目录
        skill_dir = self.skills_base_dir / "prompts" / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)

        # 写 SKILL.md
        content = self._render_prompt_skill_md(
            name=name,
            description=description,
            trigger_conditions=trigger_conditions,
            prompt_template=prompt_template,
            examples=examples,
        )

        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(content)

        # 写 metadata.yaml
        metadata = self._render_metadata(
            skill_id=skill_id,
            name=name,
            skill_type="prompt",
            description=description,
        )

        import yaml
        metadata_file = skill_dir / "metadata.yaml"
        metadata_file.write_text(yaml.dump(metadata))

        # 评估质量
        quality_score = await self._estimate_prompt_quality(prompt_template)

        return SkillCreationResult(
            skill_id=skill_id,
            skill_type="prompt",
            path=str(skill_dir),
            quality_score=quality_score,
        )

    async def create_code_skill(
        self,
        name: str,
        description: str,
        code: str,
        tests: str,
        dependencies: list[str],
        trigger_conditions: list[str],
    ) -> SkillCreationResult:
        """
        创建 Code Skill

        Args:
            name: Skill 名称
            description: 描述
            code: 代码
            tests: 测试代码
            dependencies: 依赖
            trigger_conditions: 触发条件

        Returns:
            创建结果
        """
        skill_id = self._generate_skill_id(name)

        # 创建目录
        skill_dir = self.skills_base_dir / "code" / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)

        # 写 skill.yaml
        metadata = self._render_metadata(
            skill_id=skill_id,
            name=name,
            skill_type="code",
            description=description,
            dependencies=dependencies,
        )

        import yaml
        metadata_file = skill_dir / "skill.yaml"
        metadata_file.write_text(yaml.dump(metadata))

        # 写 main.py
        main_file = skill_dir / "main.py"
        main_file.write_text(code)

        # 写 test_skill.py
        test_file = skill_dir / "test_skill.py"
        test_file.write_text(tests)

        # 写 requirements.txt
        if dependencies:
            req_file = skill_dir / "requirements.txt"
            req_file.write_text("\n".join(dependencies))

        # 评估质量
        quality_score = await self._estimate_code_quality(code, tests)

        return SkillCreationResult(
            skill_id=skill_id,
            skill_type="code",
            path=str(skill_dir),
            quality_score=quality_score,
        )

    def _generate_skill_id(self, name: str) -> str:
        """生成 Skill ID"""
        # 简单的 ID 生成
        clean_name = "".join(c if c.isalnum() else "_" for c in name.lower())
        return f"{clean_name}_{uuid.uuid4().hex[:8]}"

    def _render_prompt_skill_md(
        self,
        name: str,
        description: str,
        trigger_conditions: list[str],
        prompt_template: str,
        examples: list[dict[str, Any]],
    ) -> str:
        """渲染 Prompt Skill Markdown"""
        lines = [
            "---",
            f"name: {name}",
            f"description: {description}",
            f"trigger: {', '.join(trigger_conditions)}",
            f"version: 1.0.0",
            f"created_at: {datetime.now().isoformat()}",
            "---",
            "",
            "# Prompt Template",
            "",
            prompt_template,
            "",
            "# Examples",
            "",
        ]

        for i, example in enumerate(examples, 1):
            lines.append(f"## Example {i}")
            lines.append(f"**Input**: {example.get('input', '')}")
            lines.append(f"**Output**: {example.get('output', '')}")
            lines.append("")

        return "\n".join(lines)

    def _render_metadata(
        self,
        skill_id: str,
        name: str,
        skill_type: str,
        description: str,
        **kwargs,
    ) -> dict[str, Any]:
        """渲染 metadata"""
        metadata = {
            "skill_id": skill_id,
            "name": name,
            "type": skill_type,
            "description": description,
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "source": "auto_generated",
        }

        metadata.update(kwargs)

        return metadata

    async def _estimate_prompt_quality(self, prompt_template: str) -> float:
        """评估 Prompt 质量"""
        if not self.llm:
            return 0.5

        # 简化的质量评估
        score = 0.5

        # 检查是否有占位符
        if "{" in prompt_template and "}" in prompt_template:
            score += 0.1

        # 检查是否有格式说明
        if "格式" in prompt_template or "format" in prompt_template.lower():
            score += 0.1

        # 检查是否有示例
        if "example" in prompt_template.lower():
            score += 0.1

        return min(score, 1.0)

    async def _estimate_code_quality(self, code: str, tests: str) -> float:
        """评估代码质量"""
        score = 0.5

        # 检查是否有测试
        if tests and len(tests) > 50:
            score += 0.2

        # 检查代码长度
        if len(code) > 100:
            score += 0.1

        # 检查是否有错误处理
        if "try" in code or "except" in code:
            score += 0.1

        return min(score, 1.0)


class LLMAssistedSkillCreator(SkillCreator):
    """
    LLM 辅助的 Skill 创建器

    使用 LLM 生成 Skill 内容和代码
    """

    async def create_from_analysis(
        self,
        analysis: dict[str, Any],
    ) -> SkillCreationResult:
        """
        从分析结果创建 Skill

        Args:
            analysis: LLM 分析结果，包含：
                - name: 名称
                - description: 描述
                - skill_type: 类型 (prompt/code)
                - implementation: 实现内容
                - examples: 示例
                - dependencies: 依赖（如果是 code）

        Returns:
            创建结果
        """
        skill_type = analysis.get("skill_type", "prompt")

        if skill_type == "prompt":
            return await self.create_prompt_skill(
                name=analysis["name"],
                description=analysis["description"],
                prompt_template=analysis["implementation"],
                trigger_conditions=analysis.get("triggers", []),
                examples=analysis.get("examples", []),
            )
        else:
            return await self.create_code_skill(
                name=analysis["name"],
                description=analysis["description"],
                code=analysis["implementation"],
                tests=analysis.get("tests", ""),
                dependencies=analysis.get("dependencies", []),
                trigger_conditions=analysis.get("triggers", []),
            )

    async def analyze_and_create(
        self,
        gap_description: str,
    ) -> SkillCreationResult:
        """
        分析缺口并创建 Skill

        Args:
            gap_description: 缺口描述

        Returns:
            创建结果
        """
        if not self.llm:
            raise ValueError("LLM manager required for analyze_and_create")

        # LLM 分析缺口，设计 Skill
        prompt = f"""
        分析以下能力缺口，设计一个 Skill 来解决它。

        缺口：{gap_description}

        请设计：
        1. Skill 的名称和描述
        2. Skill 类型（prompt 或 code）
        3. 实现方案（对于 Code Skill：代码；对于 Prompt Skill：prompt 模板）
        4. 触发条件
        5. 测试用例（至少 3 个）
        6. 依赖（如果是 Code Skill）

        输出格式（JSON）：
        {{
            "name": "Skill名称",
            "description": "描述",
            "skill_type": "prompt或code",
            "implementation": "实现内容",
            "triggers": ["触发条件1", "触发条件2"],
            "examples": [
                {{"input": "示例输入", "output": "示例输出"}}
            ],
            "tests": "测试代码（如果是code skill）",
            "dependencies": ["依赖1", "依赖2"]
        }}
        """

        try:
            response = await self.llm.analyze(prompt)
            import json
            analysis = json.loads(response)
            return await self.create_from_analysis(analysis)
        except Exception as e:
            raise ValueError(f"Failed to analyze gap: {e}")
