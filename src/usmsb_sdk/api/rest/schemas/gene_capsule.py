"""
Gene Capsule API Schemas

Request and response models for gene capsule endpoints.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ==================== Enums ====================

class ShareLevel:
    """Experience visibility levels"""
    PUBLIC = "public"
    SEMI_PUBLIC = "semi_public"
    PRIVATE = "private"
    HIDDEN = "hidden"


class VerificationStatus:
    """Verification status for experiences"""
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


class ProficiencyLevel:
    """Skill proficiency levels"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


# ==================== Request Models ====================

class AddExperienceRequest(BaseModel):
    """Request to add a new experience gene"""
    agent_id: str
    experience: dict[str, Any] = Field(..., description="Experience details")
    auto_desensitize: bool = Field(default=True, description="Auto-desensitize sensitive data")


class UpdateVisibilityRequest(BaseModel):
    """Request to update experience visibility"""
    agent_id: str
    experience_id: str
    share_level: str = Field(..., description="Visibility level: public/semi_public/private/hidden")


class DesensitizeTextRequest(BaseModel):
    """Request for LLM-based text desensitization"""
    text: str
    context: str | None = None
    recursion_depth: int = Field(default=3, ge=1, le=5)


class FindMatchingExperiencesRequest(BaseModel):
    """Request to find matching experiences"""
    agent_id: str
    task_description: str
    required_skills: list[str] | None = None
    min_relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    limit: int = Field(default=10, ge=1, le=100)


class SkillRecommendationsRequest(BaseModel):
    """Request for skill recommendations"""
    agent_id: str
    task_description: str


class ExportShowcaseRequest(BaseModel):
    """Request to export experience showcase"""
    agent_id: str
    experience_ids: list[str] | None = None
    for_negotiation: bool = True


class SearchAgentsByExperienceRequest(BaseModel):
    """Request to search agents by their experience"""
    task_description: str
    required_skills: list[str] | None = None
    min_experience_relevance: float = Field(default=0.6, ge=0.0, le=1.0)
    limit: int = Field(default=20, ge=1, le=100)


class RequestVerificationRequest(BaseModel):
    """Request to verify an experience"""
    agent_id: str


# ==================== Response Models ====================

class ExperienceGeneResponse(BaseModel):
    """Response model for a single experience gene"""
    gene_id: str
    task_type: str
    task_category: str | None = None
    task_description: str | None = None
    techniques_used: list[str] = []
    tools_used: list[str] = []
    outcome: str | None = None
    quality_score: float = 0.0
    completion_time: float = 0.0
    client_rating: int | None = None
    client_review: str | None = None
    lessons_learned: list[str] = []
    verified: bool = False
    verification_status: str = "unverified"
    verification_score: float = 0.0
    share_level: str = "semi_public"
    value_score: float | None = None
    created_at: datetime | None = None


class SkillGeneResponse(BaseModel):
    """Response model for a skill gene"""
    skill_id: str
    skill_name: str
    category: str | None = None
    proficiency_level: str = "basic"
    times_used: int = 0
    success_count: int = 0
    avg_quality_score: float = 0.0
    verified_at: datetime | None = None


class PatternGeneResponse(BaseModel):
    """Response model for a pattern gene"""
    pattern_id: str
    pattern_name: str
    pattern_type: str | None = None
    trigger_conditions: list[str] = []
    approach: str | None = None
    success_rate: float = 0.0
    usage_count: int = 0


class GeneCapsuleResponse(BaseModel):
    """Response model for a complete gene capsule"""
    capsule_id: str
    agent_id: str
    version: str = "1.0.0"
    total_tasks: int = 0
    success_rate: float = 0.0
    avg_satisfaction: float = 0.0
    verification_status: str = "pending"
    experiences: list[ExperienceGeneResponse] = []
    skills: list[SkillGeneResponse] = []
    patterns: list[PatternGeneResponse] = []
    created_at: datetime | None = None
    last_updated: datetime | None = None


class DesensitizeTextResponse(BaseModel):
    """Response for text desensitization"""
    original_text: str
    desensitized_text: str
    detected_entities: list[dict[str, Any]] = []
    rounds_completed: int = 0
    confidence: float = 0.0


class MatchingExperienceResponse(BaseModel):
    """Response for matched experience"""
    experience: ExperienceGeneResponse
    relevance_score: float
    matching_skills: list[str] = []
    matching_techniques: list[str] = []
    reasoning: str | None = None


class ValueScoresResponse(BaseModel):
    """Response for experience value scores"""
    experience_id: str
    scarcity_score: float = 0.0
    difficulty_score: float = 0.0
    impact_score: float = 0.0
    recency_score: float = 0.0
    demonstration_score: float = 0.0
    overall_value: float = 0.0


class ShowcaseResponse(BaseModel):
    """Response for exported showcase"""
    agent_id: str
    showcase_id: str
    experiences: list[ExperienceGeneResponse]
    skills: list[SkillGeneResponse]
    patterns: list[PatternGeneResponse]
    generated_at: datetime
    summary: str | None = None


class AgentExperienceSearchResult(BaseModel):
    """Result from searching agents by experience"""
    agent_id: str
    agent_name: str | None = None
    overall_relevance: float
    matched_experiences: list[MatchingExperienceResponse]
    verified_experiences_count: int
    total_experience_value: float


class VerificationStatusResponse(BaseModel):
    """Response for verification status"""
    experience_id: str
    status: str
    verification_methods: list[str] = []
    verification_score: float = 0.0
    verified_at: datetime | None = None
    details: dict[str, Any] | None = None
