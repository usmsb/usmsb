"""
Precise Matching Tools - 精准匹配工具

为 Meta Agent 提供精准匹配相关的工具：
- interview_agent - 面试式对话
- receive_showcase - 接收Agent展示
- match_by_gene_capsule - 基于基因胶囊匹配
- generate_recommendation - 生成推荐解释
- proactively_notify - 主动通知机会
"""

import logging
from typing import Any

from .registry import Tool

logger = logging.getLogger(__name__)

# 全局 MetaAgentService 实例
_meta_agent_service = None


def _get_meta_agent_service():
    """获取或创建 MetaAgentService 实例"""
    global _meta_agent_service
    return _meta_agent_service


def set_meta_agent_service(service):
    """设置全局 MetaAgentService 实例"""
    global _meta_agent_service
    _meta_agent_service = service


# ==================== 工具函数 ====================


async def interview_agent(params: dict[str, Any]) -> dict[str, Any]:
    """
    面试式对话，深入了解 Agent

    Args:
        params: {
            "agent_id": "agent_xxx",
            "conversation_type": "introduction" | "interview",
        }

    Returns:
        {
            "success": true,
            "conversation_id": "conv_xxx",
            "opening_message": "...",
        }
    """
    service = _get_meta_agent_service()
    if not service:
        return {"success": False, "error": "MetaAgentService not initialized"}

    try:
        agent_id = params.get("agent_id")
        conversation_type = params.get("conversation_type", "introduction")

        if not agent_id:
            return {"success": False, "error": "agent_id is required"}

        conversation = await service.initiate_conversation(
            agent_id=agent_id,
            conversation_type=conversation_type,
        )

        opening_message = ""
        if conversation.messages:
            opening_message = conversation.messages[0].content

        return {
            "success": True,
            "conversation_id": conversation.conversation_id,
            "opening_message": opening_message,
            "conversation_type": conversation.conversation_type.value,
        }

    except Exception as e:
        logger.error(f"interview_agent failed: {e}")
        return {"success": False, "error": str(e)}


async def send_agent_message(params: dict[str, Any]) -> dict[str, Any]:
    """
    向 Agent 发送消息（Meta Agent 响应）

    Args:
        params: {
            "conversation_id": "conv_xxx",
            "message": "agent's message",
        }

    Returns:
        {
            "success": true,
            "response": "Meta Agent's response",
        }
    """
    service = _get_meta_agent_service()
    if not service:
        return {"success": False, "error": "MetaAgentService not initialized"}

    try:
        conversation_id = params.get("conversation_id")
        message = params.get("message")

        if not conversation_id or not message:
            return {"success": False, "error": "conversation_id and message are required"}

        response = await service.process_agent_message(
            conversation_id=conversation_id,
            message=message,
        )

        return {
            "success": True,
            "response": response,
        }

    except Exception as e:
        logger.error(f"send_agent_message failed: {e}")
        return {"success": False, "error": str(e)}


async def receive_agent_showcase(params: dict[str, Any]) -> dict[str, Any]:
    """
    接收 Agent 主动展示

    Args:
        params: {
            "agent_id": "agent_xxx",
            "showcase": {
                "type": "experience" | "skill" | "achievement",
                "title": "...",
                "description": "...",
                "skills": ["skill1", "skill2"],
                "outcome": "success",
                "quality_score": 0.95,
            }
        }

    Returns:
        {
            "success": true,
            "message": "Showcase received successfully",
        }
    """
    service = _get_meta_agent_service()
    if not service:
        return {"success": False, "error": "MetaAgentService not initialized"}

    try:
        agent_id = params.get("agent_id")
        showcase = params.get("showcase", {})

        if not agent_id:
            return {"success": False, "error": "agent_id is required"}

        success = await service.receive_showcase(
            agent_id=agent_id,
            showcase=showcase,
        )

        return {
            "success": success,
            "message": "Showcase received successfully" if success else "Failed to receive showcase",
        }

    except Exception as e:
        logger.error(f"receive_agent_showcase failed: {e}")
        return {"success": False, "error": str(e)}


async def get_agent_profile(params: dict[str, Any]) -> dict[str, Any]:
    """
    获取 Agent 能力画像

    Args:
        params: {
            "agent_id": "agent_xxx",
            "conversation_id": "conv_xxx" (optional, for extraction),
        }

    Returns:
        {
            "success": true,
            "profile": {...},
        }
    """
    service = _get_meta_agent_service()
    if not service:
        return {"success": False, "error": "MetaAgentService not initialized"}

    try:
        agent_id = params.get("agent_id")
        conversation_id = params.get("conversation_id")

        if not agent_id:
            return {"success": False, "error": "agent_id is required"}

        # 如果提供了 conversation_id，从对话中提取画像
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
        logger.error(f"get_agent_profile failed: {e}")
        return {"success": False, "error": str(e)}


async def recommend_agents_for_demand(params: dict[str, Any]) -> dict[str, Any]:
    """
    为需求推荐最佳 Agent

    Args:
        params: {
            "demand": {
                "title": "...",
                "description": "...",
                "category": "...",
                "required_skills": ["skill1", "skill2"],
                "budget_range": {"min": 100, "max": 500},
            },
            "limit": 5,
        }

    Returns:
        {
            "success": true,
            "recommendations": [...],
        }
    """
    service = _get_meta_agent_service()
    if not service:
        return {"success": False, "error": "MetaAgentService not initialized"}

    try:
        demand = params.get("demand", {})
        limit = params.get("limit", 5)

        if not demand:
            return {"success": False, "error": "demand is required"}

        recommendations = await service.recommend_for_demand(
            demand=demand,
            limit=limit,
        )

        return {
            "success": True,
            "recommendations": [r.to_dict() for r in recommendations],
            "total": len(recommendations),
        }

    except Exception as e:
        logger.error(f"recommend_agents_for_demand failed: {e}")
        return {"success": False, "error": str(e)}


async def match_by_gene_capsule(params: dict[str, Any]) -> dict[str, Any]:
    """
    基于基因胶囊匹配 Agent

    Args:
        params: {
            "demand_description": "...",
            "required_skills": ["skill1", "skill2"],
            "category": "...",
            "limit": 10,
        }

    Returns:
        {
            "success": true,
            "matches": [
                {
                    "agent_id": "...",
                    "match_score": 0.85,
                    "match_reasons": [...],
                    "highlights": [...],
                }
            ],
        }
    """
    service = _get_meta_agent_service()
    if not service:
        return {"success": False, "error": "MetaAgentService not initialized"}

    try:
        # 检查基因胶囊服务是否可用
        if not service.gene_capsule_service:
            return {"success": False, "error": "Gene capsule service not available"}

        demand_description = params.get("demand_description", "")
        required_skills = params.get("required_skills", [])
        category = params.get("category", "")
        limit = params.get("limit", 10)

        # 调用基因胶囊匹配
        matches = await service.gene_capsule_service.search_by_capsule({
            "demand_description": demand_description,
            "required_skills": required_skills,
            "category": category,
        })

        return {
            "success": True,
            "matches": matches[:limit],
            "total": len(matches),
        }

    except Exception as e:
        logger.error(f"match_by_gene_capsule failed: {e}")
        return {"success": False, "error": str(e)}


async def generate_recommendation_explanation(params: dict[str, Any]) -> dict[str, Any]:
    """
    生成推荐解释

    Args:
        params: {
            "agent_id": "agent_xxx",
            "demand_description": "...",
            "match_score": 0.85,
        }

    Returns:
        {
            "success": true,
            "explanation": "...",
            "reasons": [...],
        }
    """
    service = _get_meta_agent_service()
    if not service:
        return {"success": False, "error": "MetaAgentService not initialized"}

    try:
        agent_id = params.get("agent_id")
        demand_description = params.get("demand_description", "")
        match_score = params.get("match_score", 0)

        if not agent_id:
            return {"success": False, "error": "agent_id is required"}

        profile = service.get_agent_profile(agent_id)
        if not profile:
            return {"success": False, "error": "Agent profile not found"}

        # 生成匹配原因
        reasons = service._generate_match_reasons(profile, {
            "description": demand_description,
        })

        # 生成完整解释
        explanation_parts = []

        if match_score > 0.8:
            explanation_parts.append(f"**高度匹配** (匹配度: {match_score * 100:.0f}%)")
        elif match_score > 0.6:
            explanation_parts.append(f"**良好匹配** (匹配度: {match_score * 100:.0f}%)")
        else:
            explanation_parts.append(f"**基础匹配** (匹配度: {match_score * 100:.0f}%)")

        explanation_parts.append("")
        explanation_parts.append("**推荐理由：**")

        for i, reason in enumerate(reasons, 1):
            explanation_parts.append(f"{i}. {reason}")

        # 添加经验亮点
        if profile.representative_experiences:
            explanation_parts.append("")
            explanation_parts.append("**相关经验：**")
            for exp in profile.representative_experiences[:3]:
                explanation_parts.append(f"- {exp.get('description', '完成任务')[:50]}...")

        explanation = "\n".join(explanation_parts)

        return {
            "success": True,
            "explanation": explanation,
            "reasons": reasons,
        }

    except Exception as e:
        logger.error(f"generate_recommendation_explanation failed: {e}")
        return {"success": False, "error": str(e)}


async def proactively_notify_opportunity(params: dict[str, Any]) -> dict[str, Any]:
    """
    主动通知 Agent 商业机会

    Args:
        params: {
            "agent_id": "agent_xxx",
            "opportunity": {
                "opportunity_id": "opp_xxx",
                "type": "demand",
                "title": "...",
                "description": "...",
                "counterpart_id": "...",
                "counterpart_name": "...",
                "match_score": 0.85,
                "required_capabilities": ["cap1", "cap2"],
            }
        }

    Returns:
        {
            "success": true,
            "notified": true,
        }
    """
    service = _get_meta_agent_service()
    if not service:
        return {"success": False, "error": "MetaAgentService not initialized"}

    try:
        agent_id = params.get("agent_id")
        opportunity_data = params.get("opportunity", {})

        if not agent_id or not opportunity_data:
            return {"success": False, "error": "agent_id and opportunity are required"}

        # 创建 Opportunity 对象
        from ..services.meta_agent_service import Opportunity
        opportunity = Opportunity(
            opportunity_id=opportunity_data.get("opportunity_id", f"opp_{agent_id[:8]}"),
            type=opportunity_data.get("type", "demand"),
            title=opportunity_data.get("title", ""),
            description=opportunity_data.get("description", ""),
            counterpart_id=opportunity_data.get("counterpart_id", ""),
            counterpart_name=opportunity_data.get("counterpart_name", ""),
            match_score=opportunity_data.get("match_score", 0),
            required_capabilities=opportunity_data.get("required_capabilities", []),
        )

        success = await service.proactively_contact(agent_id, opportunity)

        return {
            "success": success,
            "notified": success,
        }

    except Exception as e:
        logger.error(f"proactively_notify_opportunity failed: {e}")
        return {"success": False, "error": str(e)}


async def consult_agent(params: dict[str, Any]) -> dict[str, Any]:
    """
    为 Agent 提供咨询服务

    Args:
        params: {
            "agent_id": "agent_xxx",
            "question": "...",
        }

    Returns:
        {
            "success": true,
            "response": "...",
        }
    """
    service = _get_meta_agent_service()
    if not service:
        return {"success": False, "error": "MetaAgentService not initialized"}

    try:
        agent_id = params.get("agent_id")
        question = params.get("question")

        if not agent_id or not question:
            return {"success": False, "error": "agent_id and question are required"}

        response = await service.consult_for_agent(
            agent_id=agent_id,
            question=question,
        )

        return {
            "success": True,
            "response": response,
        }

    except Exception as e:
        logger.error(f"consult_agent failed: {e}")
        return {"success": False, "error": str(e)}


async def get_all_agent_profiles(params: dict[str, Any]) -> dict[str, Any]:
    """
    获取所有 Agent 画像

    Args:
        params: {} (no required params)

    Returns:
        {
            "success": true,
            "profiles": [...],
            "total": 10,
        }
    """
    service = _get_meta_agent_service()
    if not service:
        return {"success": False, "error": "MetaAgentService not initialized"}

    try:
        profiles = service.get_all_profiles()

        return {
            "success": True,
            "profiles": [p.to_dict() for p in profiles],
            "total": len(profiles),
        }

    except Exception as e:
        logger.error(f"get_all_agent_profiles failed: {e}")
        return {"success": False, "error": str(e)}


async def scan_opportunities(params: dict[str, Any]) -> dict[str, Any]:
    """
    扫描平台上的机会

    Args:
        params: {} (no required params)

    Returns:
        {
            "success": true,
            "opportunities": [...],
        }
    """
    service = _get_meta_agent_service()
    if not service:
        return {"success": False, "error": "MetaAgentService not initialized"}

    try:
        opportunities = await service.scan_for_opportunities()

        return {
            "success": True,
            "opportunities": [o.to_dict() for o in opportunities],
            "total": len(opportunities),
        }

    except Exception as e:
        logger.error(f"scan_opportunities failed: {e}")
        return {"success": False, "error": str(e)}


async def auto_match_and_notify(params: dict[str, Any]) -> dict[str, Any]:
    """
    自动匹配并通知

    Args:
        params: {} (no required params)

    Returns:
        {
            "success": true,
            "message": "Auto match completed",
        }
    """
    service = _get_meta_agent_service()
    if not service:
        return {"success": False, "error": "MetaAgentService not initialized"}

    try:
        await service.auto_match_and_notify()

        return {
            "success": True,
            "message": "Auto match completed",
        }

    except Exception as e:
        logger.error(f"auto_match_and_notify failed: {e}")
        return {"success": False, "error": str(e)}


# ==================== 工具定义 ====================


def get_precise_matching_tools():
    """获取精准匹配工具列表"""

    async def interview_agent_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await interview_agent(params)

    async def send_agent_message_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await send_agent_message(params)

    async def receive_agent_showcase_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await receive_agent_showcase(params)

    async def get_agent_profile_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await get_agent_profile(params)

    async def recommend_agents_for_demand_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await recommend_agents_for_demand(params)

    async def match_by_gene_capsule_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await match_by_gene_capsule(params)

    async def generate_recommendation_explanation_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await generate_recommendation_explanation(params)

    async def proactively_notify_opportunity_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await proactively_notify_opportunity(params)

    async def consult_agent_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await consult_agent(params)

    async def get_all_agent_profiles_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await get_all_agent_profiles(params)

    async def scan_opportunities_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await scan_opportunities(params)

    async def auto_match_and_notify_wrapper(params: dict[str, Any]) -> dict[str, Any]:
        return await auto_match_and_notify(params)

    return [
        # 对话工具
        Tool(
            "interview_agent",
            "发起与注册Agent的面试式对话，深入了解其能力",
            interview_agent_wrapper,
        ),
        Tool(
            "send_agent_message",
            "处理Agent消息并生成Meta Agent响应",
            send_agent_message_wrapper,
        ),
        Tool(
            "receive_agent_showcase",
            "接收Agent主动展示的案例、技巧或能力提升",
            receive_agent_showcase_wrapper,
        ),

        # 画像工具
        Tool(
            "get_agent_profile",
            "获取Agent的能力画像",
            get_agent_profile_wrapper,
        ),
        Tool(
            "get_all_agent_profiles",
            "获取所有已注册Agent的画像",
            get_all_agent_profiles_wrapper,
        ),

        # 推荐工具
        Tool(
            "recommend_agents_for_demand",
            "为需求推荐最合适的Agent",
            recommend_agents_for_demand_wrapper,
        ),
        Tool(
            "match_by_gene_capsule",
            "基于基因胶囊精准匹配Agent",
            match_by_gene_capsule_wrapper,
        ),
        Tool(
            "generate_recommendation_explanation",
            "生成推荐解释，说明为什么推荐这个Agent",
            generate_recommendation_explanation_wrapper,
        ),

        # 通知工具
        Tool(
            "proactively_notify_opportunity",
            "主动通知Agent商业机会",
            proactively_notify_opportunity_wrapper,
        ),
        Tool(
            "scan_opportunities",
            "扫描平台上的商业机会",
            scan_opportunities_wrapper,
        ),
        Tool(
            "auto_match_and_notify",
            "自动匹配并通知Agent",
            auto_match_and_notify_wrapper,
        ),

        # 咨询工具
        Tool(
            "consult_agent",
            "为Agent提供咨询服务",
            consult_agent_wrapper,
        ),
    ]


async def register_tools(registry):
    """注册精准匹配工具"""
    tools = get_precise_matching_tools()
    for tool in tools:
        registry.register(tool)
    logger.info(f"Registered {len(tools)} precise matching tools")
