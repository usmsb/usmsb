"""
Gene Capsule Platform Services

Platform-side services for gene capsule management including:
- Gene Capsule Storage Service
- LLM Recursive Desensitization Service
- Auto Verification Service
- Value Evaluation Service
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship
from pydantic import BaseModel

logger = logging.getLogger(__name__)

Base = declarative_base()


# ==================== Database Models ====================

class GeneCapsuleDB(Base):
    """Database model for gene capsules"""
    __tablename__ = "gene_capsules"

    capsule_id = Column(String(64), primary_key=True)
    agent_id = Column(String(64), unique=True, nullable=False)
    version = Column(String(32), default="1.0.0")

    # Statistics
    total_tasks = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    avg_satisfaction = Column(Float, default=0.0)

    # Status
    verification_status = Column(String(32), default="pending")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Relationships
    experiences = relationship("ExperienceGeneDB", back_populates="capsule", cascade="all, delete-orphan")
    skills = relationship("SkillGeneDB", back_populates="capsule", cascade="all, delete-orphan")
    patterns = relationship("PatternGeneDB", back_populates="capsule", cascade="all, delete-orphan")
    versions = relationship("CapsuleVersionDB", back_populates="capsule", cascade="all, delete-orphan")


class ExperienceGeneDB(Base):
    """Database model for experience genes"""
    __tablename__ = "experience_genes"

    gene_id = Column(String(64), primary_key=True)
    capsule_id = Column(String(64), ForeignKey("gene_capsules.capsule_id"), nullable=False)

    # Task info
    task_type = Column(String(128), nullable=False)
    task_category = Column(String(128))
    task_description = Column(Text)
    task_keywords = Column(Text)  # JSON list

    # Result
    outcome = Column(String(32))
    quality_score = Column(Float, default=0.0)
    completion_time = Column(Float, default=0.0)

    # Client feedback
    client_rating = Column(Integer)
    client_review = Column(Text)
    would_recommend = Column(Boolean)

    # Methods
    techniques_used = Column(Text)  # JSON list
    tools_used = Column(Text)  # JSON list
    approach_description = Column(Text)
    lessons_learned = Column(Text)  # JSON list
    best_practices = Column(Text)  # JSON list

    # Verification
    verified = Column(Boolean, default=False)
    verification_status = Column(String(32), default="unverified")
    verification_methods = Column(Text)  # JSON list
    verification_score = Column(Float, default=0.0)
    verification_timestamp = Column(DateTime)

    # Visibility
    share_level = Column(String(32), default="semi_public")
    visible_to_verified_only = Column(Boolean, default=False)

    # Value
    value_score = Column(Float)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    task_completed_at = Column(DateTime)

    # Relationship
    capsule = relationship("GeneCapsuleDB", back_populates="experiences")


class SkillGeneDB(Base):
    """Database model for skill genes"""
    __tablename__ = "skill_genes"

    skill_id = Column(String(64), primary_key=True)
    capsule_id = Column(String(64), ForeignKey("gene_capsules.capsule_id"), nullable=False)

    skill_name = Column(String(128), nullable=False)
    category = Column(String(128))
    proficiency_level = Column(String(32), default="basic")

    # Statistics
    times_used = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    avg_quality_score = Column(Float, default=0.0)

    # Relations
    related_experience_ids = Column(Text)  # JSON list
    certifications = Column(Text)  # JSON list
    verified_at = Column(DateTime)

    # Relationship
    capsule = relationship("GeneCapsuleDB", back_populates="skills")


class PatternGeneDB(Base):
    """Database model for pattern genes"""
    __tablename__ = "pattern_genes"

    pattern_id = Column(String(64), primary_key=True)
    capsule_id = Column(String(64), ForeignKey("gene_capsules.capsule_id"), nullable=False)

    pattern_name = Column(String(256), nullable=False)
    pattern_type = Column(String(64))

    # Pattern definition
    trigger_conditions = Column(Text)  # JSON list
    approach = Column(Text)
    expected_outcome = Column(Text)

    # Stats
    times_applied = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)

    # Examples
    example_experience_ids = Column(Text)  # JSON list
    confidence = Column(Float, default=0.0)

    # Relationship
    capsule = relationship("GeneCapsuleDB", back_populates="patterns")


class CapsuleVersionDB(Base):
    """Database model for capsule version history"""
    __tablename__ = "capsule_versions"

    version_id = Column(String(64), primary_key=True)
    capsule_id = Column(String(64), ForeignKey("gene_capsules.capsule_id"), nullable=False)
    version_number = Column(Integer, nullable=False)

    # Snapshot (JSON)
    snapshot = Column(Text)

    # Change info
    change_type = Column(String(32))
    change_description = Column(Text)
    changed_fields = Column(Text)  # JSON list

    # Trigger
    trigger = Column(String(64))
    trigger_reference = Column(String(128))

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    capsule = relationship("GeneCapsuleDB", back_populates="versions")


# ==================== Pydantic Models for API ====================

class ExperienceGeneCreate(BaseModel):
    """Request model for creating experience gene"""
    task_type: str
    task_category: str
    task_description: str
    task_keywords: List[str] = []

    outcome: str
    quality_score: float
    completion_time: float

    client_rating: Optional[int] = None
    client_review: Optional[str] = None
    would_recommend: Optional[bool] = None

    techniques_used: List[str] = []
    tools_used: List[str] = []
    approach_description: str = ""
    lessons_learned: List[str] = []
    best_practices: List[str] = []

    share_level: str = "semi_public"
    visible_to_verified_only: bool = False


class ExperienceGeneUpdate(BaseModel):
    """Request model for updating experience gene"""
    share_level: Optional[str] = None
    visible_to_verified_only: Optional[bool] = None


class GeneCapsuleResponse(BaseModel):
    """Response model for gene capsule"""
    capsule_id: str
    agent_id: str
    version: str
    total_tasks: int
    success_rate: float
    avg_satisfaction: float
    verification_status: str
    created_at: datetime
    last_updated: datetime


# ==================== Services ====================

class GeneCapsuleStorageService:
    """
    Storage service for gene capsules

    Handles CRUD operations for capsules, experiences, skills, patterns
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    # ==================== Capsule Operations ====================

    async def get_or_create_capsule(self, agent_id: str) -> GeneCapsuleDB:
        """Get existing capsule or create new one"""
        capsule = self.db.query(GeneCapsuleDB).filter(
            GeneCapsuleDB.agent_id == agent_id
        ).first()

        if not capsule:
            capsule = GeneCapsuleDB(
                capsule_id=f"capsule-{uuid4().hex[:12]}",
                agent_id=agent_id,
            )
            self.db.add(capsule)
            self.db.commit()
            logger.info(f"Created new capsule for agent: {agent_id}")

        return capsule

    async def get_capsule(self, agent_id: str) -> Optional[GeneCapsuleDB]:
        """Get capsule by agent ID"""
        return self.db.query(GeneCapsuleDB).filter(
            GeneCapsuleDB.agent_id == agent_id
        ).first()

    async def get_capsule_by_id(self, capsule_id: str) -> Optional[GeneCapsuleDB]:
        """Get capsule by ID"""
        return self.db.query(GeneCapsuleDB).filter(
            GeneCapsuleDB.capsule_id == capsule_id
        ).first()

    async def update_capsule_stats(self, capsule_id: str):
        """Update capsule statistics"""
        capsule = self.db.query(GeneCapsuleDB).filter(
            GeneCapsuleDB.capsule_id == capsule_id
        ).first()

        if not capsule:
            return

        # Calculate stats from experiences
        experiences = capsule.experiences
        capsule.total_tasks = len(experiences)

        if experiences:
            successes = sum(1 for e in experiences if e.outcome == "success")
            capsule.success_rate = successes / len(experiences)

            ratings = [e.client_rating for e in experiences if e.client_rating]
            if ratings:
                capsule.avg_satisfaction = sum(ratings) / len(ratings)

        capsule.last_updated = datetime.utcnow()
        self.db.commit()

    # ==================== Experience Operations ====================

    async def add_experience(
        self,
        capsule_id: str,
        experience_data: ExperienceGeneCreate,
    ) -> ExperienceGeneDB:
        """Add new experience to capsule"""
        experience = ExperienceGeneDB(
            gene_id=f"exp-{uuid4().hex[:12]}",
            capsule_id=capsule_id,
            task_type=experience_data.task_type,
            task_category=experience_data.task_category,
            task_description=experience_data.task_description,
            task_keywords=json.dumps(experience_data.task_keywords),
            outcome=experience_data.outcome,
            quality_score=experience_data.quality_score,
            completion_time=experience_data.completion_time,
            client_rating=experience_data.client_rating,
            client_review=experience_data.client_review,
            would_recommend=experience_data.would_recommend,
            techniques_used=json.dumps(experience_data.techniques_used),
            tools_used=json.dumps(experience_data.tools_used),
            approach_description=experience_data.approach_description,
            lessons_learned=json.dumps(experience_data.lessons_learned),
            best_practices=json.dumps(experience_data.best_practices),
            share_level=experience_data.share_level,
            visible_to_verified_only=experience_data.visible_to_verified_only,
            task_completed_at=datetime.utcnow(),
        )

        self.db.add(experience)
        self.db.commit()

        # Update capsule stats
        await self.update_capsule_stats(capsule_id)

        # Create version
        await self.create_version(capsule_id, "addition", f"Added experience: {experience.gene_id}")

        logger.info(f"Added experience {experience.gene_id} to capsule {capsule_id}")
        return experience

    async def get_experience(self, experience_id: str) -> Optional[ExperienceGeneDB]:
        """Get experience by ID"""
        return self.db.query(ExperienceGeneDB).filter(
            ExperienceGeneDB.gene_id == experience_id
        ).first()

    async def update_experience_visibility(
        self,
        experience_id: str,
        share_level: str,
        visible_to_verified_only: bool,
    ) -> Optional[ExperienceGeneDB]:
        """Update experience visibility"""
        experience = await self.get_experience(experience_id)
        if not experience:
            return None

        experience.share_level = share_level
        experience.visible_to_verified_only = visible_to_verified_only
        self.db.commit()

        return experience

    async def get_public_experiences(
        self,
        capsule_id: str,
        limit: int = 10,
    ) -> List[ExperienceGeneDB]:
        """Get publicly visible experiences"""
        return self.db.query(ExperienceGeneDB).filter(
            ExperienceGeneDB.capsule_id == capsule_id,
            ExperienceGeneDB.share_level.in_(["public", "semi_public"]),
            ExperienceGeneDB.outcome == "success",
        ).order_by(
            ExperienceGeneDB.quality_score.desc()
        ).limit(limit).all()

    # ==================== Skill Operations ====================

    async def get_or_create_skill(
        self,
        capsule_id: str,
        skill_name: str,
        category: str,
    ) -> SkillGeneDB:
        """Get or create skill gene"""
        skill = self.db.query(SkillGeneDB).filter(
            SkillGeneDB.capsule_id == capsule_id,
            SkillGeneDB.skill_name == skill_name,
        ).first()

        if not skill:
            skill = SkillGeneDB(
                skill_id=f"skill-{uuid4().hex[:8]}",
                capsule_id=capsule_id,
                skill_name=skill_name,
                category=category,
            )
            self.db.add(skill)
            self.db.commit()

        return skill

    async def update_skill_stats(
        self,
        skill_id: str,
        success: bool,
        quality_score: float,
        experience_id: str,
    ):
        """Incrementally update skill statistics"""
        skill = self.db.query(SkillGeneDB).filter(
            SkillGeneDB.skill_id == skill_id
        ).first()

        if not skill:
            return

        skill.times_used += 1
        if success:
            skill.success_count += 1
            exp_ids = json.loads(skill.related_experience_ids or "[]")
            exp_ids.append(experience_id)
            skill.related_experience_ids = json.dumps(exp_ids)

        # Update average incrementally
        n = skill.times_used
        old_avg = skill.avg_quality_score
        skill.avg_quality_score = (old_avg * (n - 1) + quality_score) / n

        self.db.commit()

    # ==================== Pattern Operations ====================

    async def add_pattern(
        self,
        capsule_id: str,
        pattern_name: str,
        pattern_type: str,
        trigger_conditions: List[str],
        approach: str,
        experience_ids: List[str],
    ) -> PatternGeneDB:
        """Add new pattern to capsule"""
        pattern = PatternGeneDB(
            pattern_id=f"pattern-{uuid4().hex[:8]}",
            capsule_id=capsule_id,
            pattern_name=pattern_name,
            pattern_type=pattern_type,
            trigger_conditions=json.dumps(trigger_conditions),
            approach=approach,
            expected_outcome="success",
            times_applied=len(experience_ids),
            success_rate=1.0,
            example_experience_ids=json.dumps(experience_ids),
            confidence=min(1.0, len(experience_ids) / 5),
        )

        self.db.add(pattern)
        self.db.commit()

        return pattern

    # ==================== Version Operations ====================

    async def create_version(
        self,
        capsule_id: str,
        change_type: str,
        description: str,
        trigger: str = "agent_request",
        reference: Optional[str] = None,
    ) -> CapsuleVersionDB:
        """Create a new version snapshot"""
        # Get latest version number
        latest = self.db.query(CapsuleVersionDB).filter(
            CapsuleVersionDB.capsule_id == capsule_id
        ).order_by(CapsuleVersionDB.version_number.desc()).first()

        version_number = (latest.version_number + 1) if latest else 1

        # Get capsule for snapshot
        capsule = await self.get_capsule_by_id(capsule_id)
        snapshot = self._serialize_capsule(capsule) if capsule else "{}"

        version = CapsuleVersionDB(
            version_id=f"ver-{uuid4().hex[:8]}",
            capsule_id=capsule_id,
            version_number=version_number,
            snapshot=snapshot,
            change_type=change_type,
            change_description=description,
            trigger=trigger,
            trigger_reference=reference,
        )

        self.db.add(version)
        self.db.commit()

        return version

    def _serialize_capsule(self, capsule: GeneCapsuleDB) -> str:
        """Serialize capsule to JSON for snapshot"""
        data = {
            "capsule_id": capsule.capsule_id,
            "agent_id": capsule.agent_id,
            "version": capsule.version,
            "total_tasks": capsule.total_tasks,
            "success_rate": capsule.success_rate,
            "avg_satisfaction": capsule.avg_satisfaction,
            "experiences": [
                {
                    "gene_id": e.gene_id,
                    "task_type": e.task_type,
                }
                for e in capsule.experiences
            ],
            "skills": [
                {
                    "skill_id": s.skill_id,
                    "skill_name": s.skill_name,
                }
                for s in capsule.skills
            ],
        }
        return json.dumps(data)


class LLMDesensitizationService:
    """
    LLM-based recursive desensitization service

    Uses LLM to identify, replace, and verify desensitization
    """

    def __init__(self, llm_adapter=None):
        self.llm = llm_adapter
        self.max_iterations = 3

    async def desensitize(
        self,
        text: str,
        strictness: str = "high",
    ) -> Dict[str, Any]:
        """
        Perform recursive desensitization

        Args:
            text: Text to desensitize
            strictness: low, medium, high

        Returns:
            Dict with desensitized text, changes, and risk level
        """
        if not self.llm:
            # Fallback to basic desensitization
            return {
                "original": text,
                "desensitized": self._basic_desensitize(text),
                "changes": [],
                "iterations": 1,
                "final_risk_level": "medium",
            }

        iteration = 0
        current_text = text
        all_changes = []
        context = {}

        while iteration < self.max_iterations:
            iteration += 1

            # Step 1: Identify sensitive information
            sensitive_items = await self._identify_sensitive(current_text, context)
            if not sensitive_items:
                break

            # Step 2: Apply desensitization
            current_text, changes = await self._apply_desensitization(
                current_text,
                sensitive_items,
                strictness,
            )
            all_changes.extend(changes)

            # Step 3: Check remaining risk
            risk_check = await self._check_risk(current_text, context)
            if risk_check["risk_level"] == "none":
                break

            context["previous_findings"] = risk_check.get("potential_leaks", [])

        return {
            "original": text,
            "desensitized": current_text,
            "changes": all_changes,
            "iterations": iteration,
            "final_risk_level": risk_check.get("risk_level", "low") if 'risk_check' in dir() else "none",
        }

    async def _identify_sensitive(
        self,
        text: str,
        context: Dict,
    ) -> List[Dict]:
        """Use LLM to identify sensitive information"""
        prompt = f"""
分析以下文本，识别所有可能泄露客户隐私的信息。

文本：
{text}

请识别以下类型的敏感信息：
1. 公司名称/品牌名称
2. 人名/职位
3. 具体金额/数值
4. 具体日期/时间
5. 内部项目名/代号
6. 具体业务指标
7. 联系方式
8. 地址/位置
9. 技术细节（可能暴露业务逻辑）

返回JSON格式：
{{
    "sensitive_items": [
        {{
            "text": "敏感文本",
            "type": "类型",
            "risk_level": "high/medium/low",
            "reason": "原因"
        }}
    ]
}}
"""
        try:
            response = await self.llm.generate(prompt)
            # Parse JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                return data.get("sensitive_items", [])
        except Exception as e:
            logger.error(f"LLM identification failed: {e}")

        return []

    async def _apply_desensitization(
        self,
        text: str,
        sensitive_items: List[Dict],
        strictness: str,
    ) -> Tuple[str, List[Dict]]:
        """Use LLM to generate desensitized version"""
        prompt = f"""
对以下文本进行脱敏处理。

原文：
{text}

需要脱敏的项目：
{json.dumps(sensitive_items, ensure_ascii=False, indent=2)}

脱敏原则：
1. 保留信息的业务价值
2. 移除所有可识别客户身份的信息
3. 用泛化描述替换具体信息
4. 保留技术术语和方法论

严格程度：{strictness}

返回JSON格式：
{{
    "desensitized_text": "脱敏后的文本",
    "changes": [
        {{
            "original": "原文",
            "replaced_with": "替换后",
            "reason": "替换原因"
        }}
    ]
}}
"""
        try:
            response = await self.llm.generate(prompt)
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                return data["desensitized_text"], data.get("changes", [])
        except Exception as e:
            logger.error(f"LLM desensitization failed: {e}")

        # Fallback
        return self._basic_desensitize(text), []

    async def _check_risk(
        self,
        text: str,
        context: Dict,
    ) -> Dict[str, Any]:
        """Use LLM to check for remaining risks"""
        prompt = f"""
检查以下已脱敏文本是否还存在隐私泄露风险。

文本：
{text}

请检查：
1. 是否还有未识别的敏感信息？
2. 脱敏后的描述是否可以通过上下文推断出原信息？
3. 多个脱敏信息的组合是否可能重新识别身份？

返回JSON格式：
{{
    "risk_level": "none/low/medium/high",
    "potential_leaks": [
        {{
            "text": "可能有风险的文本",
            "reason": "风险原因"
        }}
    ]
}}
"""
        try:
            response = await self.llm.generate(prompt)
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"LLM risk check failed: {e}")

        return {"risk_level": "low", "potential_leaks": []}

    def _basic_desensitize(self, text: str) -> str:
        """Basic rule-based desensitization as fallback"""
        # Company names
        text = re.sub(
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|Corp|LLC|Ltd|Group|Company|集团|公司)\b',
            '某企业',
            text
        )

        # Emails
        text = re.sub(r'\b[\w.-]+@[\w.-]+\.\w+\b', '[邮箱已脱敏]', text)

        # Phone numbers
        text = re.sub(r'\b\d{11}\b', '[电话已脱敏]', text)
        text = re.sub(r'\b\d{3,4}[-\s]?\d{7,8}\b', '[电话已脱敏]', text)

        # Money amounts
        text = re.sub(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(元|万元|百万|千万|亿)', lambda m: '大量资金', text)

        return text


class ExperienceValueEvaluator:
    """
    Evaluates the value of experiences for matching

    Dimensions:
    - Scarcity: How rare is this capability
    - Difficulty: Task complexity
    - Impact: Value created for client
    - Recency: How recent
    - Demonstration: How well it shows capability
    """

    WEIGHTS = {
        "scarcity": 0.25,
        "difficulty": 0.20,
        "impact": 0.25,
        "recency": 0.15,
        "demonstration": 0.15,
    }

    def __init__(self, db_session: Session):
        self.db = db_session

    async def evaluate(
        self,
        experience: ExperienceGeneDB,
        market_context: Optional[Dict] = None,
    ) -> float:
        """
        Calculate overall value score for an experience

        Returns score 0-100
        """
        scores = {}

        # 1. Scarcity score
        scores["scarcity"] = await self._evaluate_scarcity(
            experience.task_type,
            market_context,
        )

        # 2. Difficulty score
        scores["difficulty"] = self._evaluate_difficulty(experience)

        # 3. Impact score
        scores["impact"] = self._evaluate_impact(experience)

        # 4. Recency score
        scores["recency"] = self._evaluate_recency(experience)

        # 5. Demonstration score
        scores["demonstration"] = self._evaluate_demonstration(experience)

        # Calculate weighted average
        overall = sum(
            scores[dim] * self.WEIGHTS[dim]
            for dim in self.WEIGHTS
        )

        # Store score
        experience.value_score = overall
        self.db.commit()

        return overall

    async def _evaluate_scarcity(
        self,
        task_type: str,
        market_context: Optional[Dict],
    ) -> float:
        """Evaluate how rare this capability is"""
        if not market_context:
            return 50.0

        # Count agents with this capability
        capable_count = market_context.get("capability_counts", {}).get(task_type, 0)
        total_agents = market_context.get("total_agents", 1)

        if total_agents == 0:
            return 50.0

        # Higher score for lower availability
        ratio = capable_count / total_agents
        return min(100, max(0, 100 * (1 - ratio)))

    def _evaluate_difficulty(self, experience: ExperienceGeneDB) -> float:
        """Evaluate task difficulty"""
        score = 0.0

        # Check techniques
        advanced_keywords = [
            "机器学习", "深度学习", "神经网络", "强化学习",
            "分布式", "高并发", "实时处理", "大规模",
            "优化", "预测", "建模", "分析",
        ]

        techniques = json.loads(experience.techniques_used or "[]")
        for tech in techniques:
            for keyword in advanced_keywords:
                if keyword in tech:
                    score += 15
                    break

        # Completion time
        if experience.completion_time > 7200:  # > 2 hours
            score += 20
        elif experience.completion_time > 3600:  # > 1 hour
            score += 10

        # Approach complexity
        if experience.approach_description and len(experience.approach_description) > 200:
            score += 15

        return min(100, score)

    def _evaluate_impact(self, experience: ExperienceGeneDB) -> float:
        """Evaluate impact of the work"""
        score = 50.0  # Base score

        # Quality score
        score += experience.quality_score * 20

        # Client rating
        if experience.client_rating:
            score += (experience.client_rating - 3) * 10

        # Would recommend
        if experience.would_recommend:
            score += 15

        return min(100, max(0, score))

    def _evaluate_recency(self, experience: ExperienceGeneDB) -> float:
        """Evaluate recency of experience"""
        if not experience.task_completed_at:
            return 50.0

        days_ago = (datetime.utcnow() - experience.task_completed_at).days

        if days_ago <= 7:
            return 100
        elif days_ago <= 30:
            return 80
        elif days_ago <= 90:
            return 60
        elif days_ago <= 180:
            return 40
        else:
            return 20

    def _evaluate_demonstration(self, experience: ExperienceGeneDB) -> float:
        """Evaluate how well it demonstrates capability"""
        score = 0.0

        # Approach description
        if experience.approach_description:
            if len(experience.approach_description) > 100:
                score += 30
            elif len(experience.approach_description) > 50:
                score += 20

        # Lessons learned
        lessons = json.loads(experience.lessons_learned or "[]")
        if lessons:
            score += min(30, len(lessons) * 10)

        # Verified
        if experience.verified:
            score += 40

        return min(100, score)


class AutoVerificationService:
    """
    Automatic verification of experiences

    Verifies experiences based on:
    - Transaction records
    - Execution traces
    - Client feedback
    - Time consistency
    """

    VERIFICATION_WEIGHTS = {
        "transaction_record": 0.4,
        "execution_trace": 0.3,
        "client_feedback": 0.2,
        "time_consistency": 0.1,
    }

    def __init__(self, db_session: Session):
        self.db = db_session

    async def verify_experience(
        self,
        experience: ExperienceGeneDB,
    ) -> Dict[str, Any]:
        """
        Verify an experience automatically

        Returns verification result with score and methods
        """
        verification_methods = []
        total_score = 0.0

        # 1. Check transaction record
        tx_result = await self._verify_transaction(experience)
        if tx_result["verified"]:
            verification_methods.append("transaction_record")
            total_score += self.VERIFICATION_WEIGHTS["transaction_record"]

        # 2. Check execution traces
        trace_result = await self._verify_execution_trace(experience)
        if trace_result["verified"]:
            verification_methods.append("execution_trace")
            total_score += self.VERIFICATION_WEIGHTS["execution_trace"]

        # 3. Check client feedback
        feedback_result = self._verify_client_feedback(experience)
        if feedback_result["verified"]:
            verification_methods.append("client_feedback")
            total_score += self.VERIFICATION_WEIGHTS["client_feedback"]

        # 4. Check time consistency
        time_result = self._verify_time_consistency(experience)
        if time_result["verified"]:
            verification_methods.append("time_consistency")
            total_score += self.VERIFICATION_WEIGHTS["time_consistency"]

        # Determine verification status
        is_verified = total_score >= 0.6

        # Update experience
        experience.verified = is_verified
        experience.verification_status = "verified" if is_verified else "unverified"
        experience.verification_methods = json.dumps(verification_methods)
        experience.verification_score = total_score
        experience.verification_timestamp = datetime.utcnow()

        self.db.commit()

        return {
            "experience_id": experience.gene_id,
            "verified": is_verified,
            "score": total_score,
            "methods": verification_methods,
        }

    async def _verify_transaction(self, experience: ExperienceGeneDB) -> Dict:
        """Verify via transaction records"""
        # TODO: Query transaction records
        # For now, assume verified if there's a capsule reference
        if experience.capsule_id:
            return {"verified": True, "source": "platform_record"}
        return {"verified": False}

    async def _verify_execution_trace(self, experience: ExperienceGeneDB) -> Dict:
        """Verify via execution traces"""
        # TODO: Query execution logs
        # Check if techniques used match actual execution
        return {"verified": False}

    def _verify_client_feedback(self, experience: ExperienceGeneDB) -> Dict:
        """Verify via client feedback"""
        if experience.client_rating and experience.client_rating >= 4:
            return {"verified": True, "source": "client_rating"}
        return {"verified": False}

    def _verify_time_consistency(self, experience: ExperienceGeneDB) -> Dict:
        """Verify time consistency"""
        if not experience.task_completed_at:
            return {"verified": False}

        # Check if completion time is reasonable
        if experience.completion_time > 0:
            return {"verified": True}

        return {"verified": False}


class GeneCapsuleMatchingService:
    """
    Matching service using gene capsules

    Finds best matching agents based on gene capsule analysis
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.value_evaluator = ExperienceValueEvaluator(db_session)

    async def find_matching_agents(
        self,
        task_type: str,
        keywords: List[str],
        min_rating: Optional[float] = None,
        verified_only: bool = False,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Find agents with matching gene capsules

        Returns list of agents with match scores
        """
        # Get all capsules with public experiences
        query = self.db.query(GeneCapsuleDB).join(ExperienceGeneDB).filter(
            ExperienceGeneDB.share_level.in_(["public", "semi_public"]),
            ExperienceGeneDB.outcome == "success",
        )

        capsules = query.distinct().all()

        results = []
        for capsule in capsules:
            match_result = await self._calculate_match_score(
                capsule,
                task_type,
                keywords,
                min_rating,
                verified_only,
            )

            if match_result["score"] > 0:
                results.append(match_result)

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)

        return results[:limit]

    async def _calculate_match_score(
        self,
        capsule: GeneCapsuleDB,
        task_type: str,
        keywords: List[str],
        min_rating: Optional[float],
        verified_only: bool,
    ) -> Dict:
        """Calculate match score for a capsule"""
        # Filter relevant experiences
        relevant_experiences = []
        for exp in capsule.experiences:
            if exp.outcome != "success":
                continue

            if exp.share_level == "hidden":
                continue

            if verified_only and not exp.verified:
                continue

            # Check task type match
            if exp.task_type == task_type:
                relevant_experiences.append(exp)
                continue

            # Check keyword match
            exp_keywords = set(json.loads(exp.task_keywords or "[]"))
            query_keywords = set(keywords)

            if exp_keywords & query_keywords:
                relevant_experiences.append(exp)

        if not relevant_experiences:
            return {
                "capsule_id": capsule.capsule_id,
                "agent_id": capsule.agent_id,
                "score": 0.0,
                "matching_experiences": [],
            }

        # Calculate scores
        type_match = len([e for e in relevant_experiences if e.task_type == task_type]) / max(len(relevant_experiences), 1)

        # Quality and verification
        avg_quality = sum(e.quality_score for e in relevant_experiences) / len(relevant_experiences)
        verified_count = sum(1 for e in relevant_experiences if e.verified)
        verification_ratio = verified_count / len(relevant_experiences)

        # Calculate overall score
        score = (
            type_match * 0.4 +
            avg_quality * 0.3 +
            verification_ratio * 0.2 +
            min(len(relevant_experiences) / 10, 1.0) * 0.1
        ) * 100

        return {
            "capsule_id": capsule.capsule_id,
            "agent_id": capsule.agent_id,
            "score": round(score, 1),
            "matching_experiences": [
                {
                    "gene_id": e.gene_id,
                    "task_type": e.task_type,
                    "description": e.task_description[:100] if e.task_description else "",
                    "quality_score": e.quality_score,
                    "verified": e.verified,
                    "value_score": e.value_score,
                }
                for e in sorted(relevant_experiences, key=lambda x: x.quality_score, reverse=True)[:3]
            ],
            "statistics": {
                "total_matches": len(relevant_experiences),
                "type_match_rate": round(type_match * 100, 1),
                "avg_quality": round(avg_quality * 100, 1),
                "verification_rate": round(verification_ratio * 100, 1),
            },
        }
