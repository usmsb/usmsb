"""
Gene Capsule API Endpoints

API routes for gene capsule management including:
- Experience gene management
- Skill gene management
- Pattern gene management
- LLM desensitization
- Experience matching and discovery
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from usmsb_sdk.api.rest.schemas.gene_capsule import (
    AddExperienceRequest,
    UpdateVisibilityRequest,
    DesensitizeTextRequest,
    FindMatchingExperiencesRequest,
    SkillRecommendationsRequest,
    ExportShowcaseRequest,
    SearchAgentsByExperienceRequest,
    RequestVerificationRequest,
    GeneCapsuleResponse,
    ExperienceGeneResponse,
    SkillGeneResponse,
    PatternGeneResponse,
    DesensitizeTextResponse,
    MatchingExperienceResponse,
    ValueScoresResponse,
    ShowcaseResponse,
    AgentExperienceSearchResult,
    VerificationStatusResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gene-capsule", tags=["Gene Capsule"])

# Global reference to services (set by main.py)
_gene_capsule_service = None
_desensitization_service = None
_matching_service = None
_verification_service = None
_value_evaluator = None


def set_gene_capsule_services(
    capsule_service=None,
    desensitization_service=None,
    matching_service=None,
    verification_service=None,
    value_evaluator=None,
):
    """Set the gene capsule service instances."""
    global _gene_capsule_service, _desensitization_service, _matching_service
    global _verification_service, _value_evaluator
    _gene_capsule_service = capsule_service
    _desensitization_service = desensitization_service
    _matching_service = matching_service
    _verification_service = verification_service
    _value_evaluator = value_evaluator


# ==================== Gene Capsule Management ====================

@router.get("/{agent_id}", response_model=GeneCapsuleResponse)
async def get_gene_capsule(agent_id: str):
    """
    Get an agent's gene capsule containing experiences, skills, and patterns.
    """
    if not _gene_capsule_service:
        raise HTTPException(status_code=503, detail="Gene capsule service not available")

    try:
        capsule = await _gene_capsule_service.get_capsule(agent_id)
        if not capsule:
            # Create a new empty capsule
            capsule = await _gene_capsule_service.create_capsule(agent_id)

        return _convert_capsule_to_response(capsule)
    except Exception as e:
        logger.error(f"Error getting gene capsule for {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiences", response_model=ExperienceGeneResponse)
async def add_experience(request: AddExperienceRequest):
    """
    Add a new experience gene to an agent's capsule.

    Optionally auto-desensitizes sensitive information using LLM.
    """
    if not _gene_capsule_service:
        raise HTTPException(status_code=503, detail="Gene capsule service not available")

    try:
        experience_data = request.experience

        # Auto-desensitize if requested
        if request.auto_desensitize and _desensitization_service:
            experience_data = await _desensitize_service.desensitize_experience(experience_data)

        experience = await _gene_capsule_service.add_experience(
            agent_id=request.agent_id,
            experience_data=experience_data,
        )

        return _convert_experience_to_response(experience)
    except Exception as e:
        logger.error(f"Error adding experience: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/experiences/{experience_id}/visibility", response_model=Dict[str, Any])
async def update_experience_visibility(
    experience_id: str,
    request: UpdateVisibilityRequest,
):
    """
    Update the visibility level of an experience gene.

    Visibility levels:
    - public: Visible to everyone
    - semi_public: Visible to verified agents only
    - private: Only visible in negotiations with permission
    - hidden: Not visible externally
    """
    if not _gene_capsule_service:
        raise HTTPException(status_code=503, detail="Gene capsule service not available")

    try:
        result = await _gene_capsule_service.update_visibility(
            experience_id=experience_id,
            agent_id=request.agent_id,
            share_level=request.share_level,
        )

        if not result:
            raise HTTPException(status_code=404, detail="Experience not found")

        return {"success": True, "experience_id": experience_id, "share_level": request.share_level}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating visibility: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/desensitize", response_model=DesensitizeTextResponse)
async def desensitize_text(request: DesensitizeTextRequest):
    """
    Desensitize text using LLM-based recursive processing.

    Identifies and replaces:
    - Personal names
    - Company names
    - Email addresses
    - Phone numbers
    - IP addresses
    - API keys
    - Other sensitive patterns

    Multiple rounds ensure thorough desensitization.
    """
    if not _desensitization_service:
        raise HTTPException(status_code=503, detail="Desensitization service not available")

    try:
        result = await _desensitization_service.desensitize_text(
            text=request.text,
            context=request.context,
            recursion_depth=request.recursion_depth,
        )

        return DesensitizeTextResponse(
            original_text=request.text,
            desensitized_text=result["desensitized_text"],
            detected_entities=result.get("detected_entities", []),
            rounds_completed=result.get("rounds_completed", 0),
            confidence=result.get("confidence", 0.0),
        )
    except Exception as e:
        logger.error(f"Error desensitizing text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Matching & Discovery ====================

@router.post("/match", response_model=List[MatchingExperienceResponse])
async def find_matching_experiences(request: FindMatchingExperiencesRequest):
    """
    Find experiences from an agent's capsule that match a given task.

    Returns experiences with:
    - Relevance scores
    - Matching skills and techniques
    - Reasoning for the match
    """
    if not _matching_service:
        raise HTTPException(status_code=503, detail="Matching service not available")

    try:
        matches = await _matching_service.find_matching_experiences(
            agent_id=request.agent_id,
            task_description=request.task_description,
            required_skills=request.required_skills or [],
            min_relevance=request.min_relevance,
            limit=request.limit,
        )

        return [
            MatchingExperienceResponse(
                experience=_convert_experience_to_response(m["experience"]),
                relevance_score=m["relevance_score"],
                matching_skills=m.get("matching_skills", []),
                matching_techniques=m.get("matching_techniques", []),
                reasoning=m.get("reasoning"),
            )
            for m in matches
        ]
    except Exception as e:
        logger.error(f"Error finding matching experiences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/skill-recommendations", response_model=Dict[str, Any])
async def get_skill_recommendations(request: SkillRecommendationsRequest):
    """
    Get skill recommendations based on an agent's gene capsule analysis.

    Analyzes past experiences to suggest skills that would be useful for the task.
    """
    if not _gene_capsule_service:
        raise HTTPException(status_code=503, detail="Gene capsule service not available")

    try:
        recommendations = await _gene_capsule_service.get_skill_recommendations(
            agent_id=request.agent_id,
            task_description=request.task_description,
        )

        return recommendations
    except Exception as e:
        logger.error(f"Error getting skill recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search-agents", response_model=List[AgentExperienceSearchResult])
async def search_agents_by_experience(request: SearchAgentsByExperienceRequest):
    """
    Search for agents with relevant experience genes.

    This is a powerful discovery method that finds agents based on
    their proven experience, not just claimed capabilities.

    Factors considered:
    - Experience relevance to task
    - Skill proficiency levels
    - Experience verification status
    - Past success rates
    """
    if not _matching_service:
        raise HTTPException(status_code=503, detail="Matching service not available")

    try:
        results = await _matching_service.search_agents_by_experience(
            task_description=request.task_description,
            required_skills=request.required_skills or [],
            min_relevance=request.min_experience_relevance,
            limit=request.limit,
        )

        return [
            AgentExperienceSearchResult(
                agent_id=r["agent_id"],
                agent_name=r.get("agent_name"),
                overall_relevance=r["overall_relevance"],
                matched_experiences=[
                    MatchingExperienceResponse(
                        experience=_convert_experience_to_response(e["experience"]),
                        relevance_score=e["relevance_score"],
                        matching_skills=e.get("matching_skills", []),
                        matching_techniques=e.get("matching_techniques", []),
                        reasoning=e.get("reasoning"),
                    )
                    for e in r.get("matched_experiences", [])
                ],
                verified_experiences_count=r.get("verified_experiences_count", 0),
                total_experience_value=r.get("total_experience_value", 0.0),
            )
            for r in results
        ]
    except Exception as e:
        logger.error(f"Error searching agents by experience: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Showcase & Export ====================

@router.post("/showcase", response_model=ShowcaseResponse)
async def export_showcase(request: ExportShowcaseRequest):
    """
    Export a showcase of experiences for negotiation or portfolio display.

    Selects and formats the best experiences to present to potential clients.
    """
    if not _gene_capsule_service:
        raise HTTPException(status_code=503, detail="Gene capsule service not available")

    try:
        showcase = await _gene_capsule_service.export_showcase(
            agent_id=request.agent_id,
            experience_ids=request.experience_ids,
            for_negotiation=request.for_negotiation,
        )

        return ShowcaseResponse(
            agent_id=request.agent_id,
            showcase_id=showcase["showcase_id"],
            experiences=[_convert_experience_to_response(e) for e in showcase.get("experiences", [])],
            skills=[_convert_skill_to_response(s) for s in showcase.get("skills", [])],
            patterns=[_convert_pattern_to_response(p) for p in showcase.get("patterns", [])],
            generated_at=datetime.now(),
            summary=showcase.get("summary"),
        )
    except Exception as e:
        logger.error(f"Error exporting showcase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Verification ====================

@router.post("/experiences/{experience_id}/verify")
async def request_verification(experience_id: str, request: RequestVerificationRequest):
    """
    Request platform verification for an experience.

    Verification checks:
    - Transaction records
    - Execution traces
    - Client feedback authenticity
    - Timestamp consistency
    """
    if not _verification_service:
        raise HTTPException(status_code=503, detail="Verification service not available")

    try:
        result = await _verification_service.request_verification(
            experience_id=experience_id,
            agent_id=request.agent_id,
        )

        return result
    except Exception as e:
        logger.error(f"Error requesting verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiences/{experience_id}/verification", response_model=VerificationStatusResponse)
async def get_verification_status(experience_id: str):
    """
    Get the verification status for an experience.
    """
    if not _verification_service:
        raise HTTPException(status_code=503, detail="Verification service not available")

    try:
        status = await _verification_service.get_verification_status(experience_id)

        if not status:
            raise HTTPException(status_code=404, detail="Experience not found")

        return VerificationStatusResponse(
            experience_id=experience_id,
            status=status.get("status", "unverified"),
            verification_methods=status.get("verification_methods", []),
            verification_score=status.get("verification_score", 0.0),
            verified_at=status.get("verified_at"),
            details=status.get("details"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting verification status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Value Scores ====================

@router.get("/{agent_id}/value-scores", response_model=List[ValueScoresResponse])
async def get_experience_value_scores(agent_id: str):
    """
    Get experience value scores for all experiences in the capsule.

    Value scores include:
    - Scarcity: Uniqueness of the experience
    - Difficulty: Task difficulty level
    - Impact: Business/user impact
    - Recency: Time relevance
    - Demonstration: Evidence quality
    """
    if not _value_evaluator:
        raise HTTPException(status_code=503, detail="Value evaluator not available")

    try:
        scores = await _value_evaluator.evaluate_capsule(agent_id)

        return [
            ValueScoresResponse(
                experience_id=s["experience_id"],
                scarcity_score=s.get("scarcity_score", 0.0),
                difficulty_score=s.get("difficulty_score", 0.0),
                impact_score=s.get("impact_score", 0.0),
                recency_score=s.get("recency_score", 0.0),
                demonstration_score=s.get("demonstration_score", 0.0),
                overall_value=s.get("overall_value", 0.0),
            )
            for s in scores
        ]
    except Exception as e:
        logger.error(f"Error getting value scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Patterns ====================

@router.get("/{agent_id}/patterns", response_model=List[PatternGeneResponse])
async def get_pattern_library(agent_id: str):
    """
    Get all extracted patterns from an agent's gene capsule.

    Pattern types include:
    - problem_solving_patterns
    - collaboration_patterns
    - optimization_patterns
    """
    if not _gene_capsule_service:
        raise HTTPException(status_code=503, detail="Gene capsule service not available")

    try:
        patterns = await _gene_capsule_service.get_patterns(agent_id)

        return [_convert_pattern_to_response(p) for p in patterns]
    except Exception as e:
        logger.error(f"Error getting patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Sync ====================

@router.post("/{agent_id}/sync")
async def sync_capsule_version(agent_id: str):
    """
    Sync local capsule with platform version.

    Returns the latest capsule data and version information.
    """
    if not _gene_capsule_service:
        raise HTTPException(status_code=503, detail="Gene capsule service not available")

    try:
        result = await _gene_capsule_service.sync_capsule(agent_id)

        return result
    except Exception as e:
        logger.error(f"Error syncing capsule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Helper Functions ====================

def _convert_capsule_to_response(capsule: Dict[str, Any]) -> GeneCapsuleResponse:
    """Convert capsule dict to response model."""
    return GeneCapsuleResponse(
        capsule_id=capsule.get("capsule_id", ""),
        agent_id=capsule.get("agent_id", ""),
        version=capsule.get("version", "1.0.0"),
        total_tasks=capsule.get("total_tasks", 0),
        success_rate=capsule.get("success_rate", 0.0),
        avg_satisfaction=capsule.get("avg_satisfaction", 0.0),
        verification_status=capsule.get("verification_status", "pending"),
        experiences=[_convert_experience_to_response(e) for e in capsule.get("experiences", [])],
        skills=[_convert_skill_to_response(s) for s in capsule.get("skills", [])],
        patterns=[_convert_pattern_to_response(p) for p in capsule.get("patterns", [])],
        created_at=capsule.get("created_at"),
        last_updated=capsule.get("last_updated"),
    )


def _convert_experience_to_response(exp: Dict[str, Any]) -> ExperienceGeneResponse:
    """Convert experience dict to response model."""
    return ExperienceGeneResponse(
        gene_id=exp.get("gene_id", ""),
        task_type=exp.get("task_type", ""),
        task_category=exp.get("task_category"),
        task_description=exp.get("task_description"),
        techniques_used=_safe_json_loads(exp.get("techniques_used", [])),
        tools_used=_safe_json_loads(exp.get("tools_used", [])),
        outcome=exp.get("outcome"),
        quality_score=exp.get("quality_score", 0.0),
        completion_time=exp.get("completion_time", 0.0),
        client_rating=exp.get("client_rating"),
        client_review=exp.get("client_review"),
        lessons_learned=_safe_json_loads(exp.get("lessons_learned", [])),
        verified=exp.get("verified", False),
        verification_status=exp.get("verification_status", "unverified"),
        verification_score=exp.get("verification_score", 0.0),
        share_level=exp.get("share_level", "semi_public"),
        value_score=exp.get("value_score"),
        created_at=exp.get("created_at"),
    )


def _convert_skill_to_response(skill: Dict[str, Any]) -> SkillGeneResponse:
    """Convert skill dict to response model."""
    return SkillGeneResponse(
        skill_id=skill.get("skill_id", ""),
        skill_name=skill.get("skill_name", ""),
        category=skill.get("category"),
        proficiency_level=skill.get("proficiency_level", "basic"),
        times_used=skill.get("times_used", 0),
        success_count=skill.get("success_count", 0),
        avg_quality_score=skill.get("avg_quality_score", 0.0),
        verified_at=skill.get("verified_at"),
    )


def _convert_pattern_to_response(pattern: Dict[str, Any]) -> PatternGeneResponse:
    """Convert pattern dict to response model."""
    return PatternGeneResponse(
        pattern_id=pattern.get("pattern_id", ""),
        pattern_name=pattern.get("pattern_name", ""),
        pattern_type=pattern.get("pattern_type"),
        trigger_conditions=_safe_json_loads(pattern.get("trigger_conditions", [])),
        approach=pattern.get("approach"),
        success_rate=pattern.get("success_rate", 0.0),
        usage_count=pattern.get("usage_count", 0),
    )


def _safe_json_loads(value: Any, default: Any = None) -> Any:
    """Safely parse JSON string or return value."""
    if value is None:
        return default if default is not None else []
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default if default is not None else []
    return value
