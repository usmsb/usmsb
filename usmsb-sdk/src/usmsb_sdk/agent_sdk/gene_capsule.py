"""
Gene Capsule Module

Implements the Gene Capsule system for storing and managing agent experiences,
skills, and patterns. This is the core of the precise matching system.

Key Concepts:
- Gene Capsule: Agent's "experience DNA" containing real task experiences
- Experience Gene: Single task case with techniques, results, and lessons
- Skill Gene: Verified skill with usage statistics
- Pattern Gene: Problem-solving patterns extracted from experiences
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4

from usmsb_sdk.agent_sdk.platform_client import PlatformClient, APIResponse


logger = logging.getLogger(__name__)


# ==================== Enums ====================

class ShareLevel(Enum):
    """Sharing level for experiences"""
    PUBLIC = "public"              # Fully visible
    SEMI_PUBLIC = "semi_public"    # Visible on match, details hidden
    PRIVATE = "private"            # Only Meta Agent can see (for matching)
    HIDDEN = "hidden"              # Not participating in matching


class VerificationStatus(Enum):
    """Verification status of experience"""
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


class ProficiencyLevel(Enum):
    """Skill proficiency levels"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"


class PatternType(Enum):
    """Types of problem-solving patterns"""
    PROBLEM_SOLVING = "problem_solving"
    OPTIMIZATION = "optimization"
    AUTOMATION = "automation"
    INTEGRATION = "integration"
    ANALYSIS = "analysis"
    CREATIVE = "creative"


# ==================== Data Classes ====================

@dataclass
class ChangeRecord:
    """Record of a desensitization change"""
    original: str
    replaced_with: str
    reason: str


@dataclass
class DesensitizationResult:
    """Result of LLM desensitization"""
    original: str
    desensitized: str
    changes: List[ChangeRecord]
    iterations: int
    final_risk_level: str


@dataclass
class ExperienceGene:
    """
    Experience Gene - A single task case

    This is the core unit that proves "I have done this before"
    """
    gene_id: str
    task_type: str
    task_category: str

    # Task description (desensitized)
    task_description: str
    task_keywords: List[str]

    # Execution result
    outcome: str  # success, partial, failed
    quality_score: float  # 0-1
    completion_time: float  # seconds

    # Client feedback
    client_rating: Optional[int]  # 1-5
    client_review: Optional[str]  # desensitized
    would_recommend: Optional[bool]

    # Techniques and methods
    techniques_used: List[str]
    tools_used: List[str]
    approach_description: str

    # Shareable experience
    lessons_learned: List[str]
    best_practices: List[str]

    # Verification
    verified: bool
    verification_status: str
    verification_methods: List[str] = field(default_factory=list)
    verification_timestamp: Optional[datetime] = None

    # Visibility
    share_level: str = ShareLevel.SEMI_PUBLIC.value
    visible_to_verified_only: bool = False

    # Value score (computed)
    value_score: Optional[float] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    task_completed_at: Optional[datetime] = None

    # Original data (for internal use, not exposed)
    _original_description: str = ""
    _desensitization_result: Optional[DesensitizationResult] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "gene_id": self.gene_id,
            "task_type": self.task_type,
            "task_category": self.task_category,
            "task_description": self.task_description,
            "task_keywords": self.task_keywords,
            "outcome": self.outcome,
            "quality_score": self.quality_score,
            "completion_time": self.completion_time,
            "client_rating": self.client_rating,
            "client_review": self.client_review,
            "would_recommend": self.would_recommend,
            "techniques_used": self.techniques_used,
            "tools_used": self.tools_used,
            "approach_description": self.approach_description,
            "lessons_learned": self.lessons_learned,
            "best_practices": self.best_practices,
            "verified": self.verified,
            "verification_status": self.verification_status,
            "verification_methods": self.verification_methods,
            "verification_timestamp": self.verification_timestamp.isoformat() if self.verification_timestamp else None,
            "share_level": self.share_level,
            "visible_to_verified_only": self.visible_to_verified_only,
            "value_score": self.value_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "task_completed_at": self.task_completed_at.isoformat() if self.task_completed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperienceGene":
        """Create from dictionary"""
        verification_ts = None
        if data.get("verification_timestamp"):
            if isinstance(data["verification_timestamp"], str):
                verification_ts = datetime.fromisoformat(data["verification_timestamp"])
            else:
                verification_ts = data["verification_timestamp"]

        created_at = datetime.now()
        if data.get("created_at"):
            if isinstance(data["created_at"], str):
                created_at = datetime.fromisoformat(data["created_at"])
            else:
                created_at = data["created_at"]

        task_completed_at = None
        if data.get("task_completed_at"):
            if isinstance(data["task_completed_at"], str):
                task_completed_at = datetime.fromisoformat(data["task_completed_at"])
            else:
                task_completed_at = data["task_completed_at"]

        return cls(
            gene_id=data.get("gene_id", ""),
            task_type=data.get("task_type", ""),
            task_category=data.get("task_category", ""),
            task_description=data.get("task_description", ""),
            task_keywords=data.get("task_keywords", []),
            outcome=data.get("outcome", "success"),
            quality_score=data.get("quality_score", 0.0),
            completion_time=data.get("completion_time", 0.0),
            client_rating=data.get("client_rating"),
            client_review=data.get("client_review"),
            would_recommend=data.get("would_recommend"),
            techniques_used=data.get("techniques_used", []),
            tools_used=data.get("tools_used", []),
            approach_description=data.get("approach_description", ""),
            lessons_learned=data.get("lessons_learned", []),
            best_practices=data.get("best_practices", []),
            verified=data.get("verified", False),
            verification_status=data.get("verification_status", "unverified"),
            verification_methods=data.get("verification_methods", []),
            verification_timestamp=verification_ts,
            share_level=data.get("share_level", ShareLevel.SEMI_PUBLIC.value),
            visible_to_verified_only=data.get("visible_to_verified_only", False),
            value_score=data.get("value_score"),
            created_at=created_at,
            task_completed_at=task_completed_at,
        )


@dataclass
class SkillGene:
    """
    Skill Gene - A verified skill with statistics
    """
    skill_id: str
    skill_name: str
    category: str

    # Proficiency
    proficiency_level: str

    # Statistics (incremental)
    times_used: int = 0
    success_count: int = 0
    avg_quality_score: float = 0.0

    # Related experiences
    related_experience_ids: List[str] = field(default_factory=list)

    # Certifications
    certifications: List[str] = field(default_factory=list)
    verified_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "category": self.category,
            "proficiency_level": self.proficiency_level,
            "times_used": self.times_used,
            "success_count": self.success_count,
            "avg_quality_score": self.avg_quality_score,
            "related_experience_ids": self.related_experience_ids,
            "certifications": self.certifications,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillGene":
        verified_at = None
        if data.get("verified_at"):
            if isinstance(data["verified_at"], str):
                verified_at = datetime.fromisoformat(data["verified_at"])
            else:
                verified_at = data["verified_at"]

        return cls(
            skill_id=data.get("skill_id", ""),
            skill_name=data.get("skill_name", ""),
            category=data.get("category", ""),
            proficiency_level=data.get("proficiency_level", "basic"),
            times_used=data.get("times_used", 0),
            success_count=data.get("success_count", 0),
            avg_quality_score=data.get("avg_quality_score", 0.0),
            related_experience_ids=data.get("related_experience_ids", []),
            certifications=data.get("certifications", []),
            verified_at=verified_at,
        )

    @property
    def success_rate(self) -> float:
        if self.times_used == 0:
            return 0.0
        return self.success_count / self.times_used


@dataclass
class PatternGene:
    """
    Pattern Gene - A problem-solving pattern extracted from experiences
    """
    pattern_id: str
    pattern_name: str
    pattern_type: str

    # Pattern definition
    trigger_conditions: List[str]  # When to apply this pattern
    approach: str                   # How to apply
    expected_outcome: str           # What to expect

    # Usage statistics
    times_applied: int = 0
    success_rate: float = 0.0

    # Supporting examples
    example_experience_ids: List[str] = field(default_factory=list)

    # Confidence
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "pattern_name": self.pattern_name,
            "pattern_type": self.pattern_type,
            "trigger_conditions": self.trigger_conditions,
            "approach": self.approach,
            "expected_outcome": self.expected_outcome,
            "times_applied": self.times_applied,
            "success_rate": self.success_rate,
            "example_experience_ids": self.example_experience_ids,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatternGene":
        return cls(
            pattern_id=data.get("pattern_id", ""),
            pattern_name=data.get("pattern_name", ""),
            pattern_type=data.get("pattern_type", "problem_solving"),
            trigger_conditions=data.get("trigger_conditions", []),
            approach=data.get("approach", ""),
            expected_outcome=data.get("expected_outcome", ""),
            times_applied=data.get("times_applied", 0),
            success_rate=data.get("success_rate", 0.0),
            example_experience_ids=data.get("example_experience_ids", []),
            confidence=data.get("confidence", 0.0),
        )


@dataclass
class ExperienceValueScore:
    """Value score for an experience"""
    overall_score: float  # 0-100

    # Dimension scores
    scarcity_score: float      # How rare is this capability
    difficulty_score: float    # Task complexity
    impact_score: float        # Value created for client
    recency_score: float       # How recent
    demonstration_score: float # How well it demonstrates capability


@dataclass
class GeneCapsule:
    """
    Gene Capsule - Agent's experience DNA

    Contains all verified experiences, skills, and patterns
    """
    capsule_id: str
    agent_id: str
    version: str

    # Core genes
    experience_genes: List[ExperienceGene] = field(default_factory=list)
    skill_genes: List[SkillGene] = field(default_factory=list)
    pattern_genes: List[PatternGene] = field(default_factory=list)

    # Statistics
    total_tasks: int = 0
    success_rate: float = 0.0
    avg_satisfaction: float = 0.0

    # Verification status
    verification_status: str = "pending"

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capsule_id": self.capsule_id,
            "agent_id": self.agent_id,
            "version": self.version,
            "experience_genes": [e.to_dict() for e in self.experience_genes],
            "skill_genes": [s.to_dict() for s in self.skill_genes],
            "pattern_genes": [p.to_dict() for p in self.pattern_genes],
            "total_tasks": self.total_tasks,
            "success_rate": self.success_rate,
            "avg_satisfaction": self.avg_satisfaction,
            "verification_status": self.verification_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeneCapsule":
        created_at = datetime.now()
        if data.get("created_at"):
            if isinstance(data["created_at"], str):
                created_at = datetime.fromisoformat(data["created_at"])
            else:
                created_at = data["created_at"]

        last_updated = datetime.now()
        if data.get("last_updated"):
            if isinstance(data["last_updated"], str):
                last_updated = datetime.fromisoformat(data["last_updated"])
            else:
                last_updated = data["last_updated"]

        return cls(
            capsule_id=data.get("capsule_id", ""),
            agent_id=data.get("agent_id", ""),
            version=data.get("version", "1.0.0"),
            experience_genes=[ExperienceGene.from_dict(e) for e in data.get("experience_genes", [])],
            skill_genes=[SkillGene.from_dict(s) for s in data.get("skill_genes", [])],
            pattern_genes=[PatternGene.from_dict(p) for p in data.get("pattern_genes", [])],
            total_tasks=data.get("total_tasks", 0),
            success_rate=data.get("success_rate", 0.0),
            avg_satisfaction=data.get("avg_satisfaction", 0.0),
            verification_status=data.get("verification_status", "pending"),
            created_at=created_at,
            last_updated=last_updated,
        )

    def get_public_experiences(self) -> List[ExperienceGene]:
        """Get experiences that can be publicly shown"""
        return [
            e for e in self.experience_genes
            if e.share_level in [ShareLevel.PUBLIC.value, ShareLevel.SEMI_PUBLIC.value]
        ]

    def find_similar_experiences(
        self,
        task_type: str,
        keywords: List[str],
    ) -> List[ExperienceGene]:
        """Find experiences similar to given criteria"""
        matching = []
        for exp in self.experience_genes:
            if exp.outcome != "success":
                continue

            score = 0.0

            # Type match
            if exp.task_type == task_type:
                score += 0.5

            # Keyword match
            exp_keywords = set(k.lower() for k in exp.task_keywords)
            query_keywords = set(k.lower() for k in keywords)
            if exp_keywords and query_keywords:
                overlap = len(exp_keywords & query_keywords) / len(query_keywords)
                score += 0.5 * overlap

            if score > 0:
                matching.append((score, exp))

        matching.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in matching]


# ==================== Gene Capsule Manager ====================

class GeneCapsuleManager:
    """
    Manager for Gene Capsule operations in Agent SDK

    Features:
    - Initialize and load gene capsule
    - Add new experiences (with desensitization)
    - Incremental updates
    - Sync with platform
    """

    # Proficiency evolution thresholds
    PROFICIENCY_THRESHOLDS = {
        "basic": {"times": 5, "success_rate": 0.6, "quality": 0.6},
        "intermediate": {"times": 15, "success_rate": 0.7, "quality": 0.7},
        "advanced": {"times": 30, "success_rate": 0.8, "quality": 0.8},
        "expert": {"times": 50, "success_rate": 0.9, "quality": 0.9},
    }

    def __init__(
        self,
        agent_id: str,
        platform_client: PlatformClient,
        logger: Optional[logging.Logger] = None,
    ):
        self.agent_id = agent_id
        self.platform = platform_client
        self.logger = logger or logging.getLogger(__name__)

        self._capsule: Optional[GeneCapsule] = None
        self._pending_experiences: List[ExperienceGene] = []
        self._lock = asyncio.Lock()

    @property
    def capsule(self) -> Optional[GeneCapsule]:
        return self._capsule

    @property
    def is_initialized(self) -> bool:
        return self._capsule is not None

    # ==================== Initialization ====================

    async def initialize(self) -> GeneCapsule:
        """
        Initialize gene capsule

        Creates a new capsule or loads existing one from platform
        """
        async with self._lock:
            # Try to load existing capsule
            response = await self.platform._request(
                "GET",
                f"/agents/{self.agent_id}/gene-capsule",
            )

            if response.success and response.data:
                self._capsule = GeneCapsule.from_dict(response.data)
                self.logger.info(f"Loaded gene capsule: {self._capsule.capsule_id}")
            else:
                # Create new capsule
                self._capsule = GeneCapsule(
                    capsule_id=f"capsule-{uuid4().hex[:12]}",
                    agent_id=self.agent_id,
                    version="1.0.0",
                )
                self.logger.info(f"Created new gene capsule: {self._capsule.capsule_id}")

            return self._capsule

    # ==================== Experience Management ====================

    async def add_experience(
        self,
        task_type: str,
        task_category: str,
        task_description: str,
        outcome: str,
        quality_score: float,
        completion_time: float,
        techniques_used: List[str],
        tools_used: Optional[List[str]] = None,
        approach_description: str = "",
        lessons_learned: Optional[List[str]] = None,
        client_rating: Optional[int] = None,
        client_review: Optional[str] = None,
        would_recommend: Optional[bool] = None,
        share_level: str = ShareLevel.SEMI_PUBLIC.value,
        auto_desensitize: bool = True,
    ) -> ExperienceGene:
        """
        Add a new experience gene

        Args:
            task_type: Type of task
            task_category: Category (e.g., data_analysis, nlp)
            task_description: Description (will be desensitized)
            outcome: success, partial, failed
            quality_score: 0-1
            completion_time: seconds
            techniques_used: Techniques applied
            tools_used: Tools used
            approach_description: Method description
            lessons_learned: What was learned
            client_rating: Client rating 1-5
            client_review: Client review (will be desensitized)
            would_recommend: Would client recommend
            share_level: PUBLIC, SEMI_PUBLIC, PRIVATE, HIDDEN
            auto_desensitize: Whether to auto-desensitize

        Returns:
            Created ExperienceGene
        """
        if not self._capsule:
            raise RuntimeError("Gene capsule not initialized")

        # Generate gene ID
        gene_id = f"exp-{uuid4().hex[:12]}"

        # Extract keywords
        keywords = self._extract_keywords(task_description)

        # Desensitize if needed
        if auto_desensitize:
            task_description = await self._desensitize_text(task_description)
            if client_review:
                client_review = await self._desensitize_text(client_review)

        # Create experience gene
        experience = ExperienceGene(
            gene_id=gene_id,
            task_type=task_type,
            task_category=task_category,
            task_description=task_description,
            task_keywords=keywords,
            outcome=outcome,
            quality_score=quality_score,
            completion_time=completion_time,
            client_rating=client_rating,
            client_review=client_review,
            would_recommend=would_recommend,
            techniques_used=techniques_used,
            tools_used=tools_used or [],
            approach_description=approach_description,
            lessons_learned=lessons_learned or [],
            best_practices=[],
            verified=False,
            verification_status="pending",
            share_level=share_level,
            task_completed_at=datetime.now(),
        )

        # Add to capsule
        async with self._lock:
            self._capsule.experience_genes.append(experience)

            # Update skill genes incrementally
            await self._update_skill_genes_incremental(experience)

            # Update statistics
            self._update_statistics()

            # Check for new patterns
            new_patterns = await self._detect_patterns()
            self._capsule.pattern_genes.extend(new_patterns)

            self._capsule.last_updated = datetime.now()

        # Sync with platform
        await self._sync_experience(experience)

        self.logger.info(f"Added experience gene: {gene_id}")
        return experience

    async def _desensitize_text(self, text: str) -> str:
        """
        Desensitize text using platform service

        The platform will use LLM recursive desensitization
        """
        response = await self.platform._request(
            "POST",
            "/gene-capsule/desensitize",
            data={"text": text},
        )

        if response.success and response.data:
            return response.data.get("desensitized", text)

        # Fallback: basic local desensitization
        return self._basic_desensitize(text)

    def _basic_desensitize(self, text: str) -> str:
        """Basic local desensitization as fallback"""
        import re

        # Remove potential company names (capitalized words followed by company suffix)
        text = re.sub(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|Corp|LLC|Ltd|Group|Company)\b', '某企业', text)

        # Remove email addresses
        text = re.sub(r'\b[\w.-]+@[\w.-]+\.\w+\b', '[邮箱已脱敏]', text)

        # Remove phone numbers
        text = re.sub(r'\b\d{11}\b', '[电话已脱敏]', text)
        text = re.sub(r'\b\d{3,4}[-\s]?\d{7,8}\b', '[电话已脱敏]', text)

        return text

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        import re

        # Simple keyword extraction
        stop_words = {
            "的", "是", "在", "了", "和", "与", "或", "等", "及",
            "这", "那", "有", "为", "对", "以", "到", "从",
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
        }

        # Extract words
        words = re.findall(r'\b[\u4e00-\u9fa5]{2,}\b|[a-zA-Z]{3,}\b', text.lower())
        keywords = [w for w in words if w not in stop_words]

        return list(set(keywords))[:10]  # Top 10 unique keywords

    async def _update_skill_genes_incremental(self, experience: ExperienceGene):
        """
        Incremental update of skill genes

        Updates statistics without recalculating everything
        """
        for technique in experience.techniques_used:
            # Find or create skill gene
            skill_gene = None
            for sg in self._capsule.skill_genes:
                if sg.skill_name.lower() == technique.lower():
                    skill_gene = sg
                    break

            if not skill_gene:
                skill_gene = SkillGene(
                    skill_id=f"skill-{uuid4().hex[:8]}",
                    skill_name=technique,
                    category=experience.task_category,
                    proficiency_level="basic",
                )
                self._capsule.skill_genes.append(skill_gene)

            # Incremental update
            skill_gene.times_used += 1
            if experience.outcome == "success":
                skill_gene.success_count += 1
                skill_gene.related_experience_ids.append(experience.gene_id)

            # Update average quality score incrementally
            n = skill_gene.times_used
            old_avg = skill_gene.avg_quality_score
            skill_gene.avg_quality_score = (old_avg * (n - 1) + experience.quality_score) / n

            # Check for proficiency evolution
            self._check_skill_evolution(skill_gene)

    def _check_skill_evolution(self, skill: SkillGene):
        """Check if skill should evolve to next level"""
        evolution_path = {
            "basic": "intermediate",
            "intermediate": "advanced",
            "advanced": "expert",
            "expert": "master",
        }

        current_level = skill.proficiency_level
        if current_level not in self.PROFICIENCY_THRESHOLDS:
            return

        threshold = self.PROFICIENCY_THRESHOLDS[current_level]
        success_rate = skill.success_rate if skill.times_used > 0 else 0

        if (
            skill.times_used >= threshold["times"] and
            success_rate >= threshold["success_rate"] and
            skill.avg_quality_score >= threshold["quality"]
        ):
            new_level = evolution_path.get(current_level)
            if new_level:
                skill.proficiency_level = new_level
                self.logger.info(f"Skill evolved: {skill.skill_name} -> {new_level}")

    def _update_statistics(self):
        """Update capsule statistics"""
        experiences = self._capsule.experience_genes

        self._capsule.total_tasks = len(experiences)

        if experiences:
            successes = sum(1 for e in experiences if e.outcome == "success")
            self._capsule.success_rate = successes / len(experiences)

            ratings = [e.client_rating for e in experiences if e.client_rating]
            if ratings:
                self._capsule.avg_satisfaction = sum(ratings) / len(ratings)

    async def _detect_patterns(self) -> List[PatternGene]:
        """
        Detect new patterns from experiences

        When similar approaches are used 3+ times, form a pattern
        """
        # Group experiences by similar approach
        approach_groups: Dict[str, List[ExperienceGene]] = {}

        for exp in self._capsule.experience_genes:
            if exp.outcome != "success":
                continue

            # Use task_type + first technique as grouping key
            key = f"{exp.task_type}:{exp.techniques_used[0] if exp.techniques_used else 'general'}"

            if key not in approach_groups:
                approach_groups[key] = []
            approach_groups[key].append(exp)

        # Create patterns for groups with 3+ similar experiences
        new_patterns = []
        for key, exps in approach_groups.items():
            if len(exps) < 3:
                continue

            # Check if pattern already exists
            existing = any(
                p.pattern_name == key for p in self._capsule.pattern_genes
            )
            if existing:
                continue

            # Create new pattern
            pattern = PatternGene(
                pattern_id=f"pattern-{uuid4().hex[:8]}",
                pattern_name=key,
                pattern_type="problem_solving",
                trigger_conditions=[exps[0].task_type],
                approach=exps[0].approach_description[:200] if exps[0].approach_description else "",
                expected_outcome="success",
                times_applied=len(exps),
                success_rate=1.0,  # All were successes
                example_experience_ids=[e.gene_id for e in exps[:3]],
                confidence=min(1.0, len(exps) / 5),
            )
            new_patterns.append(pattern)
            self.logger.info(f"Detected new pattern: {key}")

        return new_patterns

    # ==================== Sync with Platform ====================

    async def _sync_experience(self, experience: ExperienceGene):
        """Sync new experience with platform"""
        response = await self.platform._request(
            "POST",
            f"/agents/{self.agent_id}/gene-capsule/experiences",
            data=experience.to_dict(),
        )

        if response.success:
            self.logger.debug(f"Synced experience: {experience.gene_id}")
        else:
            self.logger.warning(f"Failed to sync experience: {response.error}")

    async def sync_capsule(self) -> bool:
        """Full sync of gene capsule with platform"""
        if not self._capsule:
            return False

        response = await self.platform._request(
            "PATCH",
            f"/agents/{self.agent_id}/gene-capsule",
            data=self._capsule.to_dict(),
        )

        if response.success:
            self.logger.info("Gene capsule synced with platform")
            return True
        else:
            self.logger.error(f"Failed to sync capsule: {response.error}")
            return False

    # ==================== Visibility Control ====================

    async def set_experience_visibility(
        self,
        experience_id: str,
        share_level: str,
        visible_to_verified_only: bool = False,
    ) -> bool:
        """Set visibility of an experience"""
        if not self._capsule:
            return False

        for exp in self._capsule.experience_genes:
            if exp.gene_id == experience_id:
                exp.share_level = share_level
                exp.visible_to_verified_only = visible_to_verified_only

                # Sync change
                await self.platform._request(
                    "PATCH",
                    f"/agents/{self.agent_id}/gene-capsule/experiences/{experience_id}",
                    data={"share_level": share_level, "visible_to_verified_only": visible_to_verified_only},
                )

                return True

        return False

    async def hide_experience(self, experience_id: str) -> bool:
        """Hide an experience from matching"""
        return await self.set_experience_visibility(
            experience_id,
            ShareLevel.HIDDEN.value,
        )

    # ==================== Queries ====================

    def get_capsule_summary(self) -> Dict[str, Any]:
        """Get summary of gene capsule for display"""
        if not self._capsule:
            return {}

        # Count by category
        categories: Dict[str, int] = {}
        for exp in self._capsule.experience_genes:
            cat = exp.task_category or "other"
            categories[cat] = categories.get(cat, 0) + 1

        # Top skills
        top_skills = sorted(
            self._capsule.skill_genes,
            key=lambda s: (s.times_used, s.success_rate),
            reverse=True,
        )[:5]

        # Recent successful experiences
        recent_success = [
            e for e in self._capsule.experience_genes
            if e.outcome == "success" and e.share_level != ShareLevel.HIDDEN.value
        ]
        recent_success.sort(key=lambda x: x.created_at, reverse=True)

        return {
            "capsule_id": self._capsule.capsule_id,
            "version": self._capsule.version,
            "total_tasks": self._capsule.total_tasks,
            "success_rate": round(self._capsule.success_rate * 100, 1),
            "avg_satisfaction": round(self._capsule.avg_satisfaction, 1),
            "categories": categories,
            "top_skills": [
                {
                    "name": s.skill_name,
                    "level": s.proficiency_level,
                    "times_used": s.times_used,
                }
                for s in top_skills
            ],
            "recent_experiences": [
                {
                    "gene_id": e.gene_id,
                    "task_type": e.task_type,
                    "description": e.task_description[:100],
                    "rating": e.client_rating,
                }
                for e in recent_success[:3]
            ],
            "patterns_count": len(self._capsule.pattern_genes),
            "last_updated": self._capsule.last_updated.isoformat() if self._capsule.last_updated else None,
        }

    def find_relevant_experiences(
        self,
        task_type: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        min_rating: Optional[int] = None,
        verified_only: bool = False,
        limit: int = 5,
    ) -> List[ExperienceGene]:
        """Find experiences matching criteria"""
        if not self._capsule:
            return []

        matching = []
        for exp in self._capsule.experience_genes:
            # Skip hidden
            if exp.share_level == ShareLevel.HIDDEN.value:
                continue

            # Filter by outcome
            if exp.outcome != "success":
                continue

            # Filter by type
            if task_type and exp.task_type != task_type:
                continue

            # Filter by rating
            if min_rating and (not exp.client_rating or exp.client_rating < min_rating):
                continue

            # Filter by verification
            if verified_only and not exp.verified:
                continue

            # Score by keyword match
            score = 0.0
            if keywords:
                exp_keywords = set(k.lower() for k in exp.task_keywords)
                query_keywords = set(k.lower() for k in keywords)
                if exp_keywords & query_keywords:
                    score = len(exp_keywords & query_keywords) / len(query_keywords)
            else:
                score = 1.0

            if score > 0:
                matching.append((score, exp))

        matching.sort(key=lambda x: (x[0], x[1].quality_score), reverse=True)
        return [e for _, e in matching[:limit]]

    def export_showcase(self) -> Dict[str, Any]:
        """
        Export showcase material for display

        Returns curated, public-safe information for marketing
        """
        if not self._capsule:
            return {}

        # Get public experiences
        public_exps = [
            e for e in self._capsule.experience_genes
            if e.share_level in [ShareLevel.PUBLIC.value, ShareLevel.SEMI_PUBLIC.value]
            and e.outcome == "success"
        ]

        # Sort by value
        public_exps.sort(key=lambda x: (
            x.verified,
            x.quality_score,
            x.client_rating or 0,
        ), reverse=True)

        return {
            "agent_id": self.agent_id,
            "statistics": {
                "total_tasks": self._capsule.total_tasks,
                "success_rate": round(self._capsule.success_rate * 100, 1),
                "avg_rating": round(self._capsule.avg_satisfaction, 1),
            },
            "top_experiences": [
                {
                    "task_type": e.task_type,
                    "description": e.task_description,
                    "techniques": e.techniques_used[:3],
                    "rating": e.client_rating,
                    "verified": e.verified,
                }
                for e in public_exps[:5]
            ],
            "skills": [
                {
                    "name": s.skill_name,
                    "level": s.proficiency_level,
                    "times_used": s.times_used,
                }
                for s in sorted(
                    self._capsule.skill_genes,
                    key=lambda x: x.times_used,
                    reverse=True,
                )[:10]
            ],
            "patterns": [
                {
                    "name": p.pattern_name,
                    "type": p.pattern_type,
                    "success_rate": p.success_rate,
                }
                for p in self._capsule.pattern_genes[:3]
            ],
        }
