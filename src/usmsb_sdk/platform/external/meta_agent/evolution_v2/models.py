"""
自主进化系统 - 数据模型

定义自我进化AGI系统的核心数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class EvolutionPhase(StrEnum):
    """进化阶段"""

    EXPLORATION = "exploration"
    ACQUISITION = "acquisition"
    CONSOLIDATION = "consolidation"
    OPTIMIZATION = "optimization"
    MASTERY = "mastery"


class KnowledgeState(StrEnum):
    """知识状态"""

    EPISODIC = "episodic"
    WORKING = "working"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    CRYSTALLIZED = "crystallized"


class CapabilityLevel(StrEnum):
    """能力等级"""

    NOVICE = "novice"
    COMPETENT = "competent"
    PROFICIENT = "proficient"
    EXPERT = "expert"
    MASTER = "master"


class LearningType(StrEnum):
    """学习类型"""

    SUPERVISED = "supervised"
    UNSUPERVISED = "unsupervised"
    REINFORCEMENT = "reinforcement"
    SELF_SUPERVISED = "self_supervised"
    META = "meta"
    TRANSFER = "transfer"


class GoalPriority(StrEnum):
    """目标优先级"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    EXPLORATORY = "exploratory"


@dataclass
class KnowledgeUnit:
    """知识单元 - 最小知识存储单位"""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    content: str = ""
    state: KnowledgeState = KnowledgeState.EPISODIC
    confidence: float = 0.5
    access_count: int = 0
    success_rate: float = 0.0
    source: str = "unknown"
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    last_accessed: float = field(default_factory=lambda: datetime.now().timestamp())
    associations: list[str] = field(default_factory=list)
    embeddings: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def consolidate_score(self) -> float:
        """计算固化得分 - 基于访问频率、成功率、时间衰减"""
        time_decay = 1.0 - min(0.5, (datetime.now().timestamp() - self.last_accessed) / 86400 / 30)
        frequency_score = min(1.0, self.access_count / 10)
        return (
            time_decay * 0.3
            + frequency_score * 0.3
            + self.success_rate * 0.2
            + self.confidence * 0.2
        )


@dataclass
class Capability:
    """能力 - 可执行的技能或知识应用"""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    description: str = ""
    level: CapabilityLevel = CapabilityLevel.NOVICE
    score: float = 0.0
    experience_points: int = 0
    prerequisite_ids: list[str] = field(default_factory=list)
    derived_capability_ids: list[str] = field(default_factory=list)
    performance_history: list[float] = field(default_factory=list)
    last_improvement: float = 0.0
    practice_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    strategies: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    def add_experience(self, success: bool, performance: float):
        self.experience_points += 1
        self.performance_history.append(performance)
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        self._update_level()

    def _update_level(self):
        exp = self.experience_points
        rate = self.success_rate
        if exp < 10 or rate < 0.3:
            self.level = CapabilityLevel.NOVICE
            self.score = min(0.2, rate)
        elif exp < 50 or rate < 0.5:
            self.level = CapabilityLevel.COMPETENT
            self.score = 0.2 + min(0.2, rate * 0.4)
        elif exp < 200 or rate < 0.7:
            self.level = CapabilityLevel.PROFICIENT
            self.score = 0.4 + min(0.2, rate * 0.4)
        elif exp < 500 or rate < 0.85:
            self.level = CapabilityLevel.EXPERT
            self.score = 0.6 + min(0.2, rate * 0.4)
        else:
            self.level = CapabilityLevel.MASTER
            self.score = 0.8 + min(0.2, rate * 0.4)


@dataclass
class LearningGoal:
    """学习目标 - 自主生成的学习任务"""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    title: str = ""
    description: str = ""
    priority: GoalPriority = GoalPriority.MEDIUM
    progress: float = 0.0
    target_capability: str | None = None
    related_knowledge: list[str] = field(default_factory=list)
    sub_goals: list[str] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    deadline: float | None = None
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    started_at: float | None = None
    completed_at: float | None = None
    attempts: int = 0
    max_attempts: int = 5
    learning_type: LearningType = LearningType.SELF_SUPERVISED
    expected_outcomes: list[str] = field(default_factory=list)
    success_criteria: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExplorationResult:
    """探索结果 - 好奇心驱动的探索产出"""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    domain: str = ""
    discoveries: list[str] = field(default_factory=list)
    novelty_score: float = 0.0
    usefulness_score: float = 0.0
    potential_goals: list[str] = field(default_factory=list)
    knowledge_gained: list[str] = field(default_factory=list)
    questions_raised: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class MetaLearningRecord:
    """元学习记录 - 学习如何学习的记录"""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    learning_strategy: str = ""
    context_description: str = ""
    efficiency_score: float = 0.0
    retention_rate: float = 0.0
    transfer_success: float = 0.0
    time_to_mastery: float = 0.0
    optimal_conditions: dict[str, Any] = field(default_factory=dict)
    lessons_learned: list[str] = field(default_factory=list)
    recommended_approaches: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class SelfReflection:
    """自我反思 - 系统自我评估"""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    type: str = "performance"
    observations: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    improvement_areas: list[str] = field(default_factory=list)
    action_items: list[dict[str, Any]] = field(default_factory=list)
    confidence_level: float = 0.0
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class CapabilityTransfer:
    """能力迁移记录 - 将能力从一领域迁移到另一领域"""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    source_capability: str = ""
    target_domain: str = ""
    adaptation_required: float = 0.0
    transfer_success: float = 0.0
    knowledge_extracted: list[str] = field(default_factory=list)
    new_capability_id: str | None = None
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class EvolutionState:
    """进化状态 - 系统整体进化状态"""

    generation: int = 1
    phase: EvolutionPhase = EvolutionPhase.EXPLORATION
    total_knowledge: int = 0
    total_capabilities: int = 0
    active_goals: int = 0
    learning_efficiency: float = 0.5
    adaptation_rate: float = 0.5
    curiosity_index: float = 0.5
    self_awareness_score: float = 0.0
    last_evolution: float = field(default_factory=lambda: datetime.now().timestamp())
    evolution_history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PerformanceMetric:
    """性能指标"""

    name: str
    value: float = 0.0
    target: float = 1.0
    trend: float = 0.0
    history: list[float] = field(default_factory=list)
    last_updated: float = field(default_factory=lambda: datetime.now().timestamp())

    def update(self, new_value: float):
        self.history.append(new_value)
        if len(self.history) > 100:
            self.history = self.history[-100:]
        if len(self.history) >= 2:
            self.trend = self.history[-1] - self.history[-2]
        self.value = new_value
        self.last_updated = datetime.now().timestamp()
