"""
Gene Capsule API Schemas

Request and response models for gene capsule endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
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
    experience: Dict[str, Any] = Field(..., description="Experience details")
    auto_desensitize: bool = Field(default=True, description="Auto-desensitize sensitive data")


class UpdateVisibilityRequest(BaseModel):
    """Request to update experience visibility"""
    agent_id: str
    experience_id: str
    share_level: str = Field(..., description="Visibility level: public/semi_public/private/hidden")


class DesensitizeTextRequest(BaseModel):
    """Request for LLM-based text desensitization"""
    text: str
    context: Optional[str] = None
    recursion_depth: int = Field(default=3, ge=1, le=5)


class FindMatchingExperiencesRequest(BaseModel):
    """Request to find matching experiences"""
    agent_id: str
    task_description: str
    required_skills: Optional[List[str]] = None
    min_relevance: float = Field(default=0.5, ge=0.0, le=1.0)
    limit: int = Field(default=10, ge=1, le=100)


class SkillRecommendationsRequest(BaseModel):
    """Request for skill recommendations"""
    agent_id: str
    task_description: str


class ExportShowcaseRequest(BaseModel):
    """Request to export experience showcase"""
    agent_id: str
    experience_ids: Optional[List[str]] = None
    for_negotiation: bool = True


class SearchAgentsByExperienceRequest(BaseModel):
    """Request to search agents by their experience"""
    task_description: str
    required_skills: Optional[List[str]] = None
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
    task_category: Optional[str] = None
    task_description: Optional[str] = None
    techniques_used: List[str] = []
    tools_used: List[str] = []
    outcome: Optional[str] = None
    quality_score: float = 0.0
    completion_time: float = 0.0
    client_rating: Optional[int] = None
    client_review: Optional[str] = None
    lessons_learned: List[str] = []
    verified: bool = False
    verification_status: str = "unverified"
    verification_score: float = 0.0
    share_level: str = "semi_public"
    value_score: Optional[float] = None
    created_at: Optional[datetime] = None


class SkillGeneResponse(BaseModel):
    """Response model for a skill gene"""
    skill_id: str
    skill_name: str
    category: Optional[str] = None
    proficiency_level: str = "basic"
    times_used: int = 0
    success_count: int = 0
    avg_quality_score: float = 0.0
    verified_at: Optional[datetime] = None


class PatternGeneResponse(BaseModel):
    """Response model for a pattern gene"""
    pattern_id: str
    pattern_name: str
    pattern_type: Optional[str] = None
    trigger_conditions: List[str] = []
    approach: Optional[str] = None
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
    experiences: List[ExperienceGeneResponse] = []
    skills: List[SkillGeneResponse] = []
    patterns: List[PatternGeneResponse] = []
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None


class DesensitizeTextResponse(BaseModel):
    """Response for text desensitization"""
    original_text: str
    desensitized_text: str
    detected_entities: List[Dict[str, Any]] = []
    rounds_completed: int = 0
    confidence: float = 0.0


class MatchingExperienceResponse(BaseModel):
    """Response for matched experience"""
    experience: ExperienceGeneResponse
    relevance_score: float
    matching_skills: List[str] = []
    matching_techniques: List[str] = []
    reasoning: Optional[str] = None


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
    experiences: List[ExperienceGeneResponse]
    skills: List[SkillGeneResponse]
    patterns: List[PatternGeneResponse]
    generated_at: datetime
    summary: Optional[str] = None


class AgentExperienceSearchResult(BaseModel):
    """Result from searching agents by experience"""
    agent_id: str
    agent_name: Optional[str] = None
    overall_relevance: float
    matched_experiences: List[MatchingExperienceResponse]
    verified_experiences_count: int
    total_experience_value: float


class VerificationStatusResponse(BaseModel):
    """Response for verification status"""
    experience_id: str
    status: str
    verification_methods: List[str] = []
    verification_score: float = 0.0
    verified_at: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None
