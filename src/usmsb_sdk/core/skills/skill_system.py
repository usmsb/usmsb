"""
Agent Skills System

This module provides a comprehensive skill system for agents:
- Skill registration and discovery
- Skill execution with input/output validation
- Skill marketplace and sharing
- Skill composition and chaining
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class SkillCategory(StrEnum):
    """Categories of agent skills."""
    ANALYSIS = "analysis"
    GENERATION = "generation"
    TRANSFORMATION = "transformation"
    COMMUNICATION = "communication"
    REASONING = "reasoning"
    ACTION = "action"
    PERCEPTION = "perception"
    LEARNING = "learning"
    PLANNING = "planning"
    EVALUATION = "evaluation"


class SkillStatus(StrEnum):
    """Status of a skill."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    BETA = "beta"
    EXPERIMENTAL = "experimental"


@dataclass
class SkillParameter:
    """Definition of a skill parameter."""
    name: str
    type: str  # "string", "number", "boolean", "object", "array"
    description: str
    required: bool = True
    default: Any = None
    enum: list[str] | None = None
    min_value: float | None = None
    max_value: float | None = None
    pattern: str | None = None  # Regex pattern for string validation


@dataclass
class SkillOutput:
    """Definition of skill output."""
    name: str
    type: str
    description: str
    example: Any | None = None


@dataclass
class SkillMetadata:
    """Metadata for a skill."""
    name: str
    version: str
    description: str
    category: SkillCategory
    tags: list[str] = field(default_factory=list)
    author: str = "system"
    status: SkillStatus = SkillStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    usage_count: int = 0
    success_rate: float = 1.0
    avg_execution_time: float = 0.0
    cost: float = 0.0  # Cost per execution in platform tokens


class Skill(ABC):
    """
    Abstract base class for agent skills.

    Skills are reusable capabilities that agents can execute.
    Each skill has defined inputs, outputs, and execution logic.
    """

    def __init__(self, metadata: SkillMetadata):
        self.metadata = metadata
        self.parameters: dict[str, SkillParameter] = {}
        self.outputs: dict[str, SkillOutput] = {}
        self._execution_count = 0
        self._total_execution_time = 0.0

    @abstractmethod
    async def execute(
        self,
        inputs: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute the skill with given inputs.

        Args:
            inputs: Input parameters matching skill definition
            context: Optional execution context

        Returns:
            Dictionary of outputs matching skill definition
        """
        pass

    def validate_inputs(self, inputs: dict[str, Any]) -> list[str]:
        """
        Validate input parameters.

        Returns:
            List of validation errors, empty if valid
        """
        errors = []

        for param_name, param_def in self.parameters.items():
            if param_def.required and param_name not in inputs:
                errors.append(f"Missing required parameter: {param_name}")
                continue

            if param_name in inputs:
                value = inputs[param_name]
                error = self._validate_single_param(param_name, param_def, value)
                if error:
                    errors.append(error)

        return errors

    def _validate_single_param(self, name: str, param: SkillParameter, value: Any) -> str | None:
        """Validate a single parameter value."""
        if value is None:
            if param.required:
                return f"Parameter {name} cannot be null"
            return None

        # Type validation
        type_validators = {
            "string": lambda v: isinstance(v, str),
            "number": lambda v: isinstance(v, (int, float)),
            "integer": lambda v: isinstance(v, int),
            "boolean": lambda v: isinstance(v, bool),
            "object": lambda v: isinstance(v, dict),
            "array": lambda v: isinstance(v, list),
        }

        validator = type_validators.get(param.type)
        if validator and not validator(value):
            return f"Parameter {name} must be of type {param.type}"

        # Enum validation
        if param.enum and value not in param.enum:
            return f"Parameter {name} must be one of: {param.enum}"

        # Range validation for numbers
        if param.type in ("number", "integer"):
            if param.min_value is not None and value < param.min_value:
                return f"Parameter {name} must be >= {param.min_value}"
            if param.max_value is not None and value > param.max_value:
                return f"Parameter {name} must be <= {param.max_value}"

        # Pattern validation for strings
        if param.type == "string" and param.pattern:
            import re
            if not re.match(param.pattern, value):
                return f"Parameter {name} does not match pattern: {param.pattern}"

        return None

    def get_schema(self) -> dict[str, Any]:
        """Get JSON schema for the skill."""
        return {
            "name": self.metadata.name,
            "version": self.metadata.version,
            "description": self.metadata.description,
            "category": self.metadata.category.value,
            "parameters": {
                name: {
                    "type": param.type,
                    "description": param.description,
                    "required": param.required,
                    **({"default": param.default} if param.default is not None else {}),
                    **({"enum": param.enum} if param.enum else {}),
                }
                for name, param in self.parameters.items()
            },
            "outputs": {
                name: {
                    "type": output.type,
                    "description": output.description,
                }
                for name, output in self.outputs.items()
            },
        }


class SkillRegistry:
    """
    Registry for managing skills.

    Provides skill registration, discovery, and execution capabilities.
    """

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._skill_by_category: dict[SkillCategory, list[str]] = {
            cat: [] for cat in SkillCategory
        }
        self._skill_handlers: dict[str, Callable] = {}

    def register(self, skill: Skill) -> None:
        """Register a skill."""
        skill_id = f"{skill.metadata.category.value}:{skill.metadata.name}"
        self._skills[skill_id] = skill
        self._skill_by_category[skill.metadata.category].append(skill_id)
        logger.info(f"Registered skill: {skill_id}")

    def unregister(self, skill_id: str) -> bool:
        """Unregister a skill."""
        if skill_id in self._skills:
            skill = self._skills[skill_id]
            del self._skills[skill_id]
            if skill_id in self._skill_by_category[skill.metadata.category]:
                self._skill_by_category[skill.metadata.category].remove(skill_id)
            logger.info(f"Unregistered skill: {skill_id}")
            return True
        return False

    def get(self, skill_id: str) -> Skill | None:
        """Get a skill by ID."""
        return self._skills.get(skill_id)

    def list_skills(
        self,
        category: SkillCategory | None = None,
        tags: list[str] | None = None,
        status: SkillStatus | None = None,
    ) -> list[Skill]:
        """List skills with optional filters."""
        if category:
            skill_ids = self._skill_by_category.get(category, [])
            skills = [self._skills[sid] for sid in skill_ids if sid in self._skills]
        else:
            skills = list(self._skills.values())

        # Apply filters
        if tags:
            skills = [s for s in skills if any(tag in s.metadata.tags for tag in tags)]

        if status:
            skills = [s for s in skills if s.metadata.status == status]

        return skills

    def search(self, query: str) -> list[Skill]:
        """Search skills by name, description, or tags."""
        query_lower = query.lower()
        results = []

        for skill in self._skills.values():
            if (
                query_lower in skill.metadata.name.lower()
                or query_lower in skill.metadata.description.lower()
                or any(query_lower in tag.lower() for tag in skill.metadata.tags)
            ):
                results.append(skill)

        return results

    async def execute(
        self,
        skill_id: str,
        inputs: dict[str, Any],
        context: dict[str, Any] | None = None,
        validate: bool = True,
    ) -> dict[str, Any]:
        """
        Execute a skill.

        Args:
            skill_id: ID of the skill to execute
            inputs: Input parameters
            context: Optional execution context
            validate: Whether to validate inputs before execution

        Returns:
            Skill execution result
        """
        skill = self.get(skill_id)
        if not skill:
            raise ValueError(f"Skill not found: {skill_id}")

        # Validate inputs
        if validate:
            errors = skill.validate_inputs(inputs)
            if errors:
                raise ValueError(f"Input validation failed: {errors}")

        # Execute with timing
        start_time = time.time()
        try:
            result = await skill.execute(inputs, context)

            # Update metrics
            execution_time = time.time() - start_time
            skill._execution_count += 1
            skill._total_execution_time += execution_time
            skill.metadata.usage_count += 1
            skill.metadata.avg_execution_time = (
                skill._total_execution_time / skill._execution_count
            )

            return {
                "success": True,
                "outputs": result,
                "execution_time": execution_time,
                "skill_id": skill_id,
            }

        except Exception as e:
            logger.error(f"Skill execution failed: {skill_id} - {e}")
            return {
                "success": False,
                "error": str(e),
                "skill_id": skill_id,
            }


# ============== Built-in Skills ==============

class TextAnalysisSkill(Skill):
    """Skill for analyzing text content."""

    def __init__(self):
        super().__init__(SkillMetadata(
            name="text_analysis",
            version="1.0.0",
            description="Analyze text for sentiment, entities, and key phrases",
            category=SkillCategory.ANALYSIS,
            tags=["nlp", "text", "analysis"],
        ))

        self.parameters = {
            "text": SkillParameter(
                name="text",
                type="string",
                description="Text to analyze",
                required=True,
            ),
            "analysis_type": SkillParameter(
                name="analysis_type",
                type="string",
                description="Type of analysis to perform",
                required=False,
                default="all",
                enum=["sentiment", "entities", "keywords", "all"],
            ),
        }

        self.outputs = {
            "sentiment": SkillOutput(
                name="sentiment",
                type="object",
                description="Sentiment analysis result",
            ),
            "entities": SkillOutput(
                name="entities",
                type="array",
                description="Extracted entities",
            ),
            "keywords": SkillOutput(
                name="keywords",
                type="array",
                description="Key phrases extracted",
            ),
        }

    async def execute(
        self,
        inputs: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute text analysis."""
        # In a real implementation, this would call an NLP service
        inputs["text"]
        analysis_type = inputs.get("analysis_type", "all")

        result = {}

        if analysis_type in ("sentiment", "all"):
            result["sentiment"] = {
                "label": "neutral",
                "score": 0.7,
                "confidence": 0.85,
            }

        if analysis_type in ("entities", "all"):
            result["entities"] = [
                {"text": "example", "type": "ORG", "confidence": 0.9},
            ]

        if analysis_type in ("keywords", "all"):
            result["keywords"] = ["analysis", "text", "example"]

        return result


class DataTransformationSkill(Skill):
    """Skill for transforming data between formats."""

    def __init__(self):
        super().__init__(SkillMetadata(
            name="data_transformation",
            version="1.0.0",
            description="Transform data between different formats",
            category=SkillCategory.TRANSFORMATION,
            tags=["data", "transform", "format"],
        ))

        self.parameters = {
            "data": SkillParameter(
                name="data",
                type="object",
                description="Data to transform",
                required=True,
            ),
            "source_format": SkillParameter(
                name="source_format",
                type="string",
                description="Source data format",
                required=True,
                enum=["json", "xml", "csv", "yaml"],
            ),
            "target_format": SkillParameter(
                name="target_format",
                type="string",
                description="Target data format",
                required=True,
                enum=["json", "xml", "csv", "yaml"],
            ),
        }

        self.outputs = {
            "result": SkillOutput(
                name="result",
                type="string",
                description="Transformed data as string",
            ),
        }

    async def execute(
        self,
        inputs: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute data transformation."""
        data = inputs["data"]
        source_format = inputs["source_format"]
        target_format = inputs["target_format"]

        # Simple JSON to other formats for demonstration
        if source_format == "json" and target_format == "yaml":
            import yaml
            result = yaml.dump(data, default_flow_style=False)
        elif source_format == "json" and target_format == "csv":
            # Flatten and convert to CSV
            import csv
            import io
            output = io.StringIO()
            if isinstance(data, list) and data:
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            result = output.getvalue()
        else:
            result = json.dumps(data, indent=2)

        return {"result": result}


class WebSearchSkill(Skill):
    """Skill for performing web searches."""

    def __init__(self):
        super().__init__(SkillMetadata(
            name="web_search",
            version="1.0.0",
            description="Search the web for information",
            category=SkillCategory.PERCEPTION,
            tags=["web", "search", "information"],
            cost=0.01,  # Small cost per search
        ))

        self.parameters = {
            "query": SkillParameter(
                name="query",
                type="string",
                description="Search query",
                required=True,
            ),
            "max_results": SkillParameter(
                name="max_results",
                type="integer",
                description="Maximum number of results",
                required=False,
                default=5,
                min_value=1,
                max_value=20,
            ),
        }

        self.outputs = {
            "results": SkillOutput(
                name="results",
                type="array",
                description="Search results",
            ),
        }

    async def execute(
        self,
        inputs: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute web search."""
        query = inputs["query"]
        max_results = inputs.get("max_results", 5)

        # In a real implementation, this would call a search API
        # For now, return mock results
        results = [
            {
                "title": f"Result {i+1} for: {query}",
                "url": f"https://example.com/result/{i+1}",
                "snippet": f"This is a snippet for result {i+1}...",
            }
            for i in range(max_results)
        ]

        return {"results": results}


class CodeExecutionSkill(Skill):
    """Skill for executing code in a sandboxed environment."""

    def __init__(self):
        super().__init__(SkillMetadata(
            name="code_execution",
            version="1.0.0",
            description="Execute code in a sandboxed environment",
            category=SkillCategory.ACTION,
            tags=["code", "execution", "python"],
            status=SkillStatus.BETA,
        ))

        self.parameters = {
            "code": SkillParameter(
                name="code",
                type="string",
                description="Python code to execute",
                required=True,
            ),
            "timeout": SkillParameter(
                name="timeout",
                type="integer",
                description="Execution timeout in seconds",
                required=False,
                default=30,
                min_value=1,
                max_value=300,
            ),
        }

        self.outputs = {
            "output": SkillOutput(
                name="output",
                type="string",
                description="Standard output from execution",
            ),
            "error": SkillOutput(
                name="error",
                type="string",
                description="Error output if any",
            ),
        }

    async def execute(
        self,
        inputs: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute code in sandbox."""
        code = inputs["code"]
        timeout = inputs.get("timeout", 30)

        # WARNING: In production, use a proper sandboxed execution environment
        # This is a simplified example
        import os
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            result = subprocess.run(
                ['python', temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "output": result.stdout,
                "error": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"output": "", "error": f"Execution timed out after {timeout} seconds"}
        finally:
            os.unlink(temp_file)


# Global skill registry instance
skill_registry = SkillRegistry()

# Register built-in skills
skill_registry.register(TextAnalysisSkill())
skill_registry.register(DataTransformationSkill())
skill_registry.register(WebSearchSkill())
skill_registry.register(CodeExecutionSkill())
