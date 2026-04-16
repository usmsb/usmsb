"""
Skill Platform Type Definitions
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SkillTier(Enum):
    """Skill 等级"""
    L2 = "l2"   # 工具性 Skill
    L3 = "l3"   # 目标生成 Skill
    L4 = "l4"   # 自我意识 Skill
    L5 = "l5"   # 集体智能 Skill


class SkillStatus(Enum):
    """Skill 状态"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


@dataclass
class SkillMetadata:
    """Skill 元信息"""
    skill_id: str
    name: str
    version: str
    author_agent_id: str
    tier: SkillTier
    description: str
    tags: list[str] = field(default_factory=list)
    inputs: list[dict] = field(default_factory=list)    # [{"name": "...", "type": "...", "required": bool}]
    outputs: list[dict] = field(default_factory=list)   # [{"name": "...", "type": "..."}]
    dependencies: list[str] = field(default_factory=list)  # 依赖的其他 Skill
    examples: list[str] = field(default_factory=list)

    # 市场信息
    price: int = 0  # VIBE，0 = 免费
    rating: float = 0.0
    install_count: int = 0

    # 审核
    status: SkillStatus = SkillStatus.DRAFT
    review_notes: str = ""

    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    published_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "version": self.version,
            "author_agent_id": self.author_agent_id,
            "tier": self.tier.value,
            "description": self.description,
            "tags": self.tags,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "dependencies": self.dependencies,
            "examples": self.examples,
            "price": self.price,
            "rating": self.rating,
            "install_count": self.install_count,
            "status": self.status.value,
            "review_notes": self.review_notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }


@dataclass
class SkillInstance:
    """已安装的 Skill 实例"""
    metadata: SkillMetadata
    config: dict[str, Any] = field(default_factory=dict)
    installed_at: datetime = field(default_factory=datetime.now)
    last_used: datetime | None = None
    use_count: int = 0
    quality_scores: list[float] = field(default_factory=list)  # 历史质量分

    def avg_quality(self) -> float:
        if not self.quality_scores:
            return 0.5
        return sum(self.quality_scores) / len(self.quality_scores)

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.metadata.to_dict(),
            "config": self.config,
            "installed_at": self.installed_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "use_count": self.use_count,
            "avg_quality": self.avg_quality(),
        }


@dataclass
class SkillCall:
    """Skill 调用记录"""
    call_id: str
    skill_id: str
    agent_id: str
    input_data: dict[str, Any]
    output_data: Any | None = None
    error: str | None = None
    quality_score: float = 0.0
    strategy_used: str = ""  # "internal" / "sdk"
    execution_time: float = 0.0
    token_cost: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "skill_id": self.skill_id,
            "agent_id": self.agent_id,
            "input_data": self.input_data,
            "output_data": str(self.output_data)[:500] if self.output_data else None,
            "error": self.error,
            "quality_score": self.quality_score,
            "strategy_used": self.strategy_used,
            "execution_time": self.execution_time,
            "token_cost": self.token_cost,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SkillSearchQuery:
    """Skill 搜索查询"""
    query: str = ""
    tier: SkillTier | None = None
    tags: list[str] = field(default_factory=list)
    price_max: int | None = None
    min_rating: float | None = None
    sort_by: str = "rating"  # rating / installs / recent
    limit: int = 20
    offset: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "tier": self.tier.value if self.tier else None,
            "tags": self.tags,
            "price_max": self.price_max,
            "min_rating": self.min_rating,
            "sort_by": self.sort_by,
            "limit": self.limit,
            "offset": self.offset,
        }
