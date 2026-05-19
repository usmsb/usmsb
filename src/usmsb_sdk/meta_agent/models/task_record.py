"""
TaskRecord 数据模型

v2.1 因果学习系统的核心数据结构
用于记录每次任务执行的经验，供因果发现和元学习使用

包含：
- TaskRecord: 单次任务执行记录
- TaskFeatures: 任务特征（因）
- Outcome: 执行效果（果）
- Strategy: 策略
- StrategyFeatures: 策略特征
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class InputSize(Enum):
    """输入大小"""
    SMALL = "small"       # < 1KB
    MEDIUM = "medium"     # 1KB - 100KB
    LARGE = "large"       # 100KB - 10MB
    XLARGE = "xlarge"     # > 10MB


class InputType(Enum):
    """输入类型"""
    CODE = "code"
    TEXT = "text"
    DATA = "data"
    MIXED = "mixed"
    STRUCTURED = "structured"  # JSON, XML, etc.


class DomainArea(Enum):
    """领域区域"""
    CODE_DEVELOPMENT = "code_development"
    DATA_ANALYSIS = "data_analysis"
    DOCUMENT_PROCESSING = "document_processing"
    API_INTEGRATION = "api_integration"
    DATABASE_OPERATION = "database_operation"
    SYSTEM_ADMINISTRATION = "system_administration"
    RESEARCH = "research"
    GENERAL = "general"


@dataclass
class TaskFeatures:
    """
    任务特征（因）

    描述任务本身的属性，用于因果发现
    """
    # 输入特征
    input_size: InputSize = InputSize.MEDIUM
    input_type: InputType = InputType.MIXED
    input_complexity: float = 0.5  # 0.0 ~ 1.0

    # 领域特征
    has_api: bool = False
    has_database: bool = False
    is_real_time: bool = False
    domain_area: DomainArea = DomainArea.GENERAL

    # 约束特征
    time_limit: float | None = None  # 秒
    memory_limit: float | None = None  # MB
    cost_budget: float | None = None

    # 质量要求
    accuracy_required: float = 0.7  # 0.0 ~ 1.0
    creativity_required: float = 0.3  # 0.0 ~ 1.0
    safety_required: float = 0.5  # 0.0 ~ 1.0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "input_size": self.input_size.value,
            "input_type": self.input_type.value,
            "input_complexity": self.input_complexity,
            "has_api": self.has_api,
            "has_database": self.has_database,
            "is_real_time": self.is_real_time,
            "domain_area": self.domain_area.value,
            "time_limit": self.time_limit,
            "memory_limit": self.memory_limit,
            "cost_budget": self.cost_budget,
            "accuracy_required": self.accuracy_required,
            "creativity_required": self.creativity_required,
            "safety_required": self.safety_required,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskFeatures":
        """从字典创建"""
        return cls(
            input_size=InputSize(data.get("input_size", "medium")),
            input_type=InputType(data.get("input_type", "mixed")),
            input_complexity=data.get("input_complexity", 0.5),
            has_api=data.get("has_api", False),
            has_database=data.get("has_database", False),
            is_real_time=data.get("is_real_time", False),
            domain_area=DomainArea(data.get("domain_area", "general")),
            time_limit=data.get("time_limit"),
            memory_limit=data.get("memory_limit"),
            cost_budget=data.get("cost_budget"),
            accuracy_required=data.get("accuracy_required", 0.7),
            creativity_required=data.get("creativity_required", 0.3),
            safety_required=data.get("safety_required", 0.5),
        )


@dataclass
class Outcome:
    """
    任务执行效果（果）

    描述任务执行的结果，用于因果发现
    """
    success: bool
    quality: float = 0.0  # 0.0 ~ 1.0
    duration: float = 0.0  # 秒
    resource_cost: float = 0.0  # 资源消耗
    error_type: str | None = None  # 错误类型（如果失败）
    partial_success: float = 0.0  # 部分成功度 0.0 ~ 1.0

    # 额外指标
    llm_calls: int = 0  # LLM 调用次数
    tool_calls: int = 0  # 工具调用次数
    retry_count: int = 0  # 重试次数

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "quality": self.quality,
            "duration": self.duration,
            "resource_cost": self.resource_cost,
            "error_type": self.error_type,
            "partial_success": self.partial_success,
            "llm_calls": self.llm_calls,
            "tool_calls": self.tool_calls,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Outcome":
        """从字典创建"""
        return cls(
            success=data.get("success", False),
            quality=data.get("quality", 0.0),
            duration=data.get("duration", 0.0),
            resource_cost=data.get("resource_cost", 0.0),
            error_type=data.get("error_type"),
            partial_success=data.get("partial_success", 0.0),
            llm_calls=data.get("llm_calls", 0),
            tool_calls=data.get("tool_calls", 0),
            retry_count=data.get("retry_count", 0),
        )


@dataclass
class StrategyFeatures:
    """
    策略特征

    描述策略的属性，用于因果发现
    """
    # 规划特征
    decomposition_depth: int = 1  # 分解深度
    parallel_threshold: float = 0.5  # 并行阈值

    # 执行特征
    tool_count: int = 1  # 工具数量
    llm_call_budget: int = 5  # LLM 调用预算
    retry_enabled: bool = True

    # 验证特征
    verify_always: bool = False
    verify_on_failure: bool = True
    verify_sample_rate: float = 0.1  # 验证采样率

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "decomposition_depth": self.decomposition_depth,
            "parallel_threshold": self.parallel_threshold,
            "tool_count": self.tool_count,
            "llm_call_budget": self.llm_call_budget,
            "retry_enabled": self.retry_enabled,
            "verify_always": self.verify_always,
            "verify_on_failure": self.verify_on_failure,
            "verify_sample_rate": self.verify_sample_rate,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StrategyFeatures":
        """从字典创建"""
        return cls(
            decomposition_depth=data.get("decomposition_depth", 1),
            parallel_threshold=data.get("parallel_threshold", 0.5),
            tool_count=data.get("tool_count", 1),
            llm_call_budget=data.get("llm_call_budget", 5),
            retry_enabled=data.get("retry_enabled", True),
            verify_always=data.get("verify_always", False),
            verify_on_failure=data.get("verify_on_failure", True),
            verify_sample_rate=data.get("verify_sample_rate", 0.1),
        )


@dataclass
class Strategy:
    """
    策略

    描述任务执行所使用的策略
    """
    name: str
    features: StrategyFeatures = field(default_factory=StrategyFeatures)
    applicable_conditions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "features": self.features.to_dict(),
            "applicable_conditions": self.applicable_conditions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Strategy":
        """从字典创建"""
        return cls(
            name=data.get("name", "default"),
            features=StrategyFeatures.from_dict(data.get("features", {})),
            applicable_conditions=data.get("applicable_conditions", []),
        )


@dataclass
class TaskRecord:
    """
    单次任务执行记录

    用于因果发现和元学习的核心数据结构
    记录：任务特征（因）→ 策略（中介）→ 效果（果）
    """
    task_id: str
    task_type: str  # 任务类型标识
    features: TaskFeatures  # 任务特征（因）
    strategy: Strategy  # 使用的策略
    parameters: dict[str, Any]  # 执行参数
    outcome: Outcome  # 执行效果（果）
    timestamp: float  # Unix 时间戳
    domain: str = "general"  # 领域标识

    # 额外元数据
    conversation_id: str | None = None
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "features": self.features.to_dict(),
            "strategy": self.strategy.to_dict(),
            "parameters": self.parameters,
            "outcome": self.outcome.to_dict(),
            "timestamp": self.timestamp,
            "domain": self.domain,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskRecord":
        """从字典创建"""
        return cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            features=TaskFeatures.from_dict(data["features"]),
            strategy=Strategy.from_dict(data["strategy"]),
            parameters=data.get("parameters", {}),
            outcome=Outcome.from_dict(data["outcome"]),
            timestamp=data["timestamp"],
            domain=data.get("domain", "general"),
            conversation_id=data.get("conversation_id"),
            user_id=data.get("user_id"),
            metadata=data.get("metadata", {}),
        )


# 特征类别定义（用于因果发现）
FEATURE_CATEGORIES = {
    "input": ["input_size", "input_type", "input_complexity"],
    "domain": ["has_api", "has_database", "is_real_time", "domain_area"],
    "constraints": ["time_limit", "memory_limit", "cost_budget"],
    "quality": ["accuracy_required", "creativity_required", "safety_required"],
}

STRATEGY_FEATURES = {
    "planning": ["decomposition_depth", "parallel_threshold"],
    "execution": ["tool_count", "llm_call_budget", "retry_enabled"],
    "verification": ["verify_always", "verify_on_failure", "verify_sample_rate"],
}

OUTCOME_FEATURES = {
    "performance": ["success", "quality", "duration", "resource_cost"],
    "reliability": ["error_type", "partial_success"],
}
