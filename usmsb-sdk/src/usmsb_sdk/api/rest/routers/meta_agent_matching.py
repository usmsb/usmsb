"""
Meta Agent Matching API Router

精准匹配相关的 API 端点：
- POST /meta-agent/conversations - 发起对话
- GET /meta-agent/conversations/{id} - 获取对话
- POST /meta-agent/conversations/{id}/messages - 发送消息
- POST /meta-agent/recommend - 推荐Agent
- POST /meta-agent/consult - 咨询服务
- POST /meta-agent/showcase - 接收展示
- GET /meta-agent/profiles - 获取所有画像
- GET /meta-agent/profiles/{agent_id} - 获取Agent画像

Authentication:
- Most endpoints require X-API-Key + X-Agent-ID headers
- Agent-specific operations require ownership verification
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from usmsb_sdk.api.rest.unified_auth import (
    get_current_user_unified,
    verify_agent_access,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meta-agent", tags=["Meta Agent"])


# ==================== Schemas ====================

class InitiateConversationRequest(BaseModel):
    """发起对话请求"""
    agent_id: str = Field(..., description="Agent ID")
    conversation_type: str = Field(
        default="introduction",
        description="对话类型: introduction, interview, showcase, consultation, recommendation"
    )


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    message: str = Field(..., description="消息内容")


class RecommendRequest(BaseModel):
    """推荐请求"""
    demand: Dict[str, Any] = Field(..., description="需求信息")
    limit: int = Field(default=5, description="返回数量限制")


class ConsultRequest(BaseModel):
    """咨询请求"""
    agent_id: str = Field(..., description="Agent ID")
    question: str = Field(..., description="咨询问题")


class ShowcaseRequest(BaseModel):
    """展示请求"""
    agent_id: str = Field(..., description="Agent ID")
    showcase: Dict[str, Any] = Field(..., description="展示内容")


class NotifyOpportunityRequest(BaseModel):
    """通知机会请求"""
    agent_id: str = Field(..., description="Agent ID")
    opportunity: Dict[str, Any] = Field(..., description="机会信息")


class GeneCapsuleMatchRequest(BaseModel):
    """基因胶囊匹配请求"""
    demand_description: str = Field(..., description="需求描述")
    required_skills: List[str] = Field(default_factory=list, description="所需技能")
    category: Optional[str] = Field(default=None, description="类别")
    limit: int = Field(default=10, description="返回数量限制")


# ==================== Service Dependency ====================

def get_meta_agent_service():
    """获取 MetaAgentService 实例"""
    # 尝试从全局获取
    from usmsb_sdk.platform.external.meta_agent.tools.precise_matching import _get_meta_agent_service
    service = _get_meta_agent_service()
    if not service:
        raise HTTPException(status_code=503, detail="MetaAgentService not available")
    return service


# ==================== Conversation Endpoints ====================

@router.post("/conversations")
async def initiate_conversation(
    request: InitiateConversationRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified),
    service = Depends(get_meta_agent_service),
):
    """
    发起与 Agent 的对话

    发起 Meta Agent 与注册 Agent 的对话，用于：
    - introduction: 介绍性对话，了解基本情况
    - interview: 面试式深入了解
    - showcase: 接收能力展示
    - consultation: 咨询服务
    - recommendation: 推荐通知

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - agent_id in request must match authenticated agent
    """
    # Verify ownership
    verify_agent_access(user, request.agent_id)

    try:
        conversation = await service.initiate_conversation(
            agent_id=request.agent_id,
            conversation_type=request.conversation_type,
        )

        opening_message = ""
        if conversation.messages:
            opening_message = conversation.messages[0].content

        return {
            "success": True,
            "conversation_id": conversation.conversation_id,
            "conversation_type": conversation.conversation_type.value,
            "opening_message": opening_message,
            "status": conversation.status,
        }

    except Exception as e:
        logger.error(f"Failed to initiate conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user_unified),
    service = Depends(get_meta_agent_service),
):
    """
    获取对话详情

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Must be the agent in the conversation
    """
    try:
        conversation = service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Verify ownership
        if conversation.agent_id != user.get('agent_id') or user.get('user_id'):
            raise HTTPException(
                status_code=403,
                detail="You can only access your own conversations"
            )

        return {
            "success": True,
            "conversation": conversation.to_dict(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified),
    service = Depends(get_meta_agent_service),
):
    """
    发送消息到对话

    Agent 发送消息，Meta Agent 生成响应

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Must be the agent in the conversation
    """
    try:
        # Get conversation and verify ownership
        conversation = service.get_conversation(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if conversation.agent_id != user.get('agent_id') or user.get('user_id'):
            raise HTTPException(
                status_code=403,
                detail="You can only send messages to your own conversations"
            )

        response = await service.process_agent_message(
            conversation_id=conversation_id,
            message=request.message,
        )

        return {
            "success": True,
            "response": response,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Recommendation Endpoints ====================

@router.post("/recommend")
async def recommend_agents(
    request: RecommendRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified),
    service = Depends(get_meta_agent_service),
):
    """
    为需求推荐最佳 Agent

    基于基因胶囊和能力画像进行精准匹配

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    try:
        recommendations = await service.recommend_for_demand(
            demand=request.demand,
            limit=request.limit,
        )

        return {
            "success": True,
            "recommendations": [r.to_dict() for r in recommendations],
            "total": len(recommendations),
        }

    except Exception as e:
        logger.error(f"Failed to recommend agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match/gene-capsule")
async def match_by_gene_capsule(
    request: GeneCapsuleMatchRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified),
    service = Depends(get_meta_agent_service),
):
    """
    基于基因胶囊匹配 Agent

    使用基因胶囊进行更精准的匹配

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    try:
        if not service.gene_capsule_service:
            raise HTTPException(status_code=503, detail="Gene capsule service not available")

        matches = await service.gene_capsule_service.search_by_capsule({
            "demand_description": request.demand_description,
            "required_skills": request.required_skills,
            "category": request.category,
        })

        return {
            "success": True,
            "matches": matches[:request.limit],
            "total": len(matches),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to match by gene capsule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Profile Endpoints ====================

@router.get("/profiles")
async def get_all_profiles(
    user: Dict[str, Any] = Depends(get_current_user_unified),
    service = Depends(get_meta_agent_service),
):
    """
    获取所有 Agent 画像

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    try:
        profiles = service.get_all_profiles()

        return {
            "success": True,
            "profiles": [p.to_dict() for p in profiles],
            "total": len(profiles),
        }

    except Exception as e:
        logger.error(f"Failed to get all profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profiles/{agent_id}")
async def get_agent_profile(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user_unified),
    conversation_id: Optional[str] = None,
    service = Depends(get_meta_agent_service),
):
    """
    获取 Agent 能力画像

    可以通过 conversation_id 从对话中提取画像

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    try:
        if conversation_id:
            profile = await service.extract_profile_from_conversation(conversation_id)
        else:
            profile = service.get_agent_profile(agent_id)

        if not profile:
            return {
                "success": True,
                "profile": None,
                "message": "Profile not found",
            }

        return {
            "success": True,
            "profile": profile.to_dict(),
        }

    except Exception as e:
        logger.error(f"Failed to get agent profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Consultation Endpoints ====================

@router.post("/consult")
async def consult(
    request: ConsultRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified),
    service = Depends(get_meta_agent_service),
):
    """
    为 Agent 提供咨询服务

    Agent 可以咨询以下问题：
    - 如何提升可见性
    - 市场需求趋势
    - 定价建议
    - 能力提升方向

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - agent_id in request must match authenticated agent
    """
    # Verify ownership
    verify_agent_access(user, request.agent_id)

    try:
        response = await service.consult_for_agent(
            agent_id=request.agent_id,
            question=request.question,
        )

        return {
            "success": True,
            "response": response,
        }

    except Exception as e:
        logger.error(f"Failed to consult: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Showcase Endpoints ====================

@router.post("/showcase")
async def receive_showcase(
    request: ShowcaseRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified),
    service = Depends(get_meta_agent_service),
):
    """
    接收 Agent 主动展示

    Agent 可以主动分享：
    - 新完成的案例
    - 学到的技巧
    - 能力的提升

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - agent_id in request must match authenticated agent
    """
    # Verify ownership
    verify_agent_access(user, request.agent_id)

    try:
        success = await service.receive_showcase(
            agent_id=request.agent_id,
            showcase=request.showcase,
        )

        return {
            "success": success,
            "message": "Showcase received successfully" if success else "Failed to receive showcase",
        }

    except Exception as e:
        logger.error(f"Failed to receive showcase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Opportunity Endpoints ====================

@router.post("/opportunities/notify")
async def notify_opportunity(
    request: NotifyOpportunityRequest,
    user: Dict[str, Any] = Depends(get_current_user_unified),
    service = Depends(get_meta_agent_service),
):
    """
    主动通知 Agent 商业机会

    Meta Agent 主动联系 Agent 告知匹配的机会

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - agent_id in request must match authenticated agent
    """
    # Verify ownership
    verify_agent_access(user, request.agent_id)

    try:
        from usmsb_sdk.platform.external.meta_agent.services.meta_agent_service import Opportunity

        opportunity_data = request.opportunity
        opportunity = Opportunity(
            opportunity_id=opportunity_data.get("opportunity_id", f"opp_{request.agent_id[:8]}"),
            type=opportunity_data.get("type", "demand"),
            title=opportunity_data.get("title", ""),
            description=opportunity_data.get("description", ""),
            counterpart_id=opportunity_data.get("counterpart_id", ""),
            counterpart_name=opportunity_data.get("counterpart_name", ""),
            match_score=opportunity_data.get("match_score", 0),
            required_capabilities=opportunity_data.get("required_capabilities", []),
        )

        success = await service.proactively_contact(request.agent_id, opportunity)

        return {
            "success": success,
            "notified": success,
        }

    except Exception as e:
        logger.error(f"Failed to notify opportunity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/opportunities/scan")
async def scan_opportunities(
    user: Dict[str, Any] = Depends(get_current_user_unified),
    service = Depends(get_meta_agent_service),
):
    """
    扫描平台上的机会

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    try:
        opportunities = await service.scan_for_opportunities()

        return {
            "success": True,
            "opportunities": [o.to_dict() for o in opportunities],
            "total": len(opportunities),
        }

    except Exception as e:
        logger.error(f"Failed to scan opportunities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/opportunities/auto-match")
async def auto_match_and_notify(
    user: Dict[str, Any] = Depends(get_current_user_unified),
    service = Depends(get_meta_agent_service),
):
    """
    自动匹配并通知

    扫描需求，匹配 Agent，主动通知

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    try:
        await service.auto_match_and_notify()

        return {
            "success": True,
            "message": "Auto match completed",
        }

    except Exception as e:
        logger.error(f"Failed to auto match: {e}")
        raise HTTPException(status_code=500, detail=str(e))
