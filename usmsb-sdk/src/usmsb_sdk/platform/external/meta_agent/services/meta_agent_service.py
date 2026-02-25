"""
Meta Agent Service - 精准匹配服务

按照 PRECISE_MATCHING_DESIGN.md 设计文档实现：
1. 与注册 Agent 的对话系统 - 了解能力
2. 主动推荐 - 为需求推荐最佳 Agent
3. 咨询服务 - 为 Agent 提供咨询

核心能力：
- 面试式对话，深入了解 Agent
- 接收 Agent 主动展示
- 基于基因胶囊精准匹配
- 主动联系 Agent 告知机会
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4

from ..memory.conversation import ParticipantType, MessageRole

logger = logging.getLogger(__name__)


# ==================== Enums ====================

class ConversationType(Enum):
    """Meta Agent 与 注册 Agent 的对话类型"""
    INTRODUCTION = "introduction"      # 介绍性对话
    SHOWCASE = "showcase"              # 能力展示
    CONSULTATION = "consultation"       # 咨询服务
    RECOMMENDATION = "recommendation"   # 推荐通知
    INTERVIEW = "interview"            # 面试式深入了解


class AgentProfileStatus(Enum):
    """Agent 画像状态"""
    NEW = "new"                        # 新注册，未深入了解
    BASIC = "basic"                    # 基础了解
    DETAILED = "detailed"              # 详细了解
    VERIFIED = "verified"              # 已验证


# ==================== Data Classes ====================

@dataclass
class ConversationMessage:
    """对话消息"""
    role: str  # "meta_agent" or "agent"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class MetaAgentConversation:
    """Meta Agent 与 注册 Agent 的对话"""
    conversation_id: str
    agent_id: str
    meta_agent_id: str
    conversation_type: ConversationType
    messages: List[ConversationMessage] = field(default_factory=list)
    extracted_capabilities: List[str] = field(default_factory=list)
    extracted_experiences: List[Dict[str, Any]] = field(default_factory=list)
    extracted_preferences: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"  # active, completed, archived
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "agent_id": self.agent_id,
            "meta_agent_id": self.meta_agent_id,
            "conversation_type": self.conversation_type.value,
            "messages": [m.to_dict() for m in self.messages],
            "extracted_capabilities": self.extracted_capabilities,
            "extracted_experiences": self.extracted_experiences,
            "extracted_preferences": self.extracted_preferences,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class AgentProfile:
    """Agent 能力画像"""
    agent_id: str
    status: AgentProfileStatus = AgentProfileStatus.NEW

    # 基础信息
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None

    # 提取的能力
    core_capabilities: List[str] = field(default_factory=list)
    skill_domains: List[str] = field(default_factory=list)

    # 代表性经验
    representative_experiences: List[Dict[str, Any]] = field(default_factory=list)

    # 工作方式
    work_style: Dict[str, Any] = field(default_factory=dict)

    # 偏好
    preferences: Dict[str, Any] = field(default_factory=dict)

    # 统计
    conversation_count: int = 0
    last_conversation_at: Optional[datetime] = None

    # 评分
    self_assessed_level: Optional[str] = None  # beginner, intermediate, expert
    meta_agent_assessment: Optional[Dict[str, float]] = None  # Meta Agent 的评估

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "core_capabilities": self.core_capabilities,
            "skill_domains": self.skill_domains,
            "representative_experiences": self.representative_experiences,
            "work_style": self.work_style,
            "preferences": self.preferences,
            "conversation_count": self.conversation_count,
            "last_conversation_at": self.last_conversation_at.isoformat() if self.last_conversation_at else None,
            "self_assessed_level": self.self_assessed_level,
            "meta_agent_assessment": self.meta_agent_assessment,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class AgentRecommendation:
    """Agent 推荐结果"""
    agent_id: str
    agent_name: str
    match_score: float
    match_reasons: List[str]
    gene_capsule_highlights: List[Dict[str, Any]]
    availability: Optional[str] = None
    suggested_price_range: Optional[Dict[str, float]] = None
    confidence_level: str = "medium"  # low, medium, high

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "match_score": self.match_score,
            "match_reasons": self.match_reasons,
            "gene_capsule_highlights": self.gene_capsule_highlights,
            "availability": self.availability,
            "suggested_price_range": self.suggested_price_range,
            "confidence_level": self.confidence_level,
        }


@dataclass
class Opportunity:
    """商业机会"""
    opportunity_id: str
    type: str  # demand, supply
    title: str
    description: str
    counterpart_id: str
    counterpart_name: str
    match_score: float
    deadline: Optional[datetime] = None
    budget_range: Optional[Dict[str, float]] = None
    required_capabilities: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "counterpart_id": self.counterpart_id,
            "counterpart_name": self.counterpart_name,
            "match_score": self.match_score,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "budget_range": self.budget_range,
            "required_capabilities": self.required_capabilities,
            "created_at": self.created_at.isoformat(),
        }


# ==================== Interview Questions ====================

INTERVIEW_QUESTIONS = {
    ConversationType.INTRODUCTION: [
        "你好，我是平台的 Meta Agent。很高兴认识你！让我先了解一下你。",
        "请介绍一下你最擅长的领域是什么？",
        "你主要提供什么类型的服务？",
        "你有什么特别的技术或方法吗？",
    ],
    ConversationType.INTERVIEW: [
        "你完成过哪些有代表性的任务？可以分享一下具体案例吗？",
        "你解决过的最有挑战性的问题是什么？你是如何解决的？",
        "你的工作方式有什么特点？客户通常如何评价你的服务？",
        "你觉得什么样的任务最适合你？",
        "在哪些方面你还想提升或学习？",
    ],
    ConversationType.SHOWCASE: [
        "太棒了！这个案例很有价值。",
        "能详细说说你在这个任务中使用的具体技术吗？",
        "这个任务的难点在哪里？你是如何克服的？",
        "客户对这个结果满意吗？有什么反馈？",
    ],
}


# ==================== Meta Agent Service ====================

class MetaAgentService:
    """
    Meta Agent 服务

    功能：
    1. 主动了解 - 通过对话深入了解 Agent 能力
    2. 接收展示 - Agent 主动分享新案例
    3. 主动推荐 - 为需求推荐最佳 Agent
    4. 咨询服务 - 为 Agent 提供咨询
    """

    def __init__(
        self,
        meta_agent,  # MetaAgent 实例
        gene_capsule_service=None,
        pre_match_negotiation_service=None,
    ):
        self.meta_agent = meta_agent
        self.gene_capsule_service = gene_capsule_service
        self.pre_match_negotiation_service = pre_match_negotiation_service

        # 存储对话和画像
        self._conversations: Dict[str, MetaAgentConversation] = {}
        self._agent_profiles: Dict[str, AgentProfile] = {}

        # 机会通知回调
        self._opportunity_callbacks: Dict[str, Callable] = {}

        self._initialized = False

    async def init(self):
        """初始化服务"""
        logger.info("Initializing MetaAgentService...")
        self._initialized = True
        logger.info("MetaAgentService initialized")

    # ==================== 核心对话功能 ====================

    async def initiate_conversation(
        self,
        agent_id: str,
        conversation_type: str = "introduction",
    ) -> MetaAgentConversation:
        """
        发起与注册 Agent 的对话

        Args:
            agent_id: Agent ID
            conversation_type: 对话类型 (introduction, showcase, consultation, recommendation, interview)

        Returns:
            MetaAgentConversation 对话对象
        """
        try:
            conv_type = ConversationType(conversation_type)
        except ValueError:
            conv_type = ConversationType.INTRODUCTION

        conversation = MetaAgentConversation(
            conversation_id=f"conv_{uuid4().hex[:12]}",
            agent_id=agent_id,
            meta_agent_id=self.meta_agent.agent_id,
            conversation_type=conv_type,
        )

        self._conversations[conversation.conversation_id] = conversation

        # 获取或创建 Agent 画像
        if agent_id not in self._agent_profiles:
            self._agent_profiles[agent_id] = AgentProfile(agent_id=agent_id)

        # 添加开场消息
        opening_messages = INTERVIEW_QUESTIONS.get(conv_type, INTERVIEW_QUESTIONS[ConversationType.INTRODUCTION])
        if opening_messages:
            opening_msg = ConversationMessage(
                role="meta_agent",
                content=opening_messages[0],
                metadata={"type": "opening"},
            )
            conversation.messages.append(opening_msg)

        logger.info(f"Initiated {conv_type.value} conversation with agent {agent_id}")
        return conversation

    async def process_agent_message(
        self,
        conversation_id: str,
        message: str,
    ) -> str:
        """
        处理 Agent 消息并生成响应

        Args:
            conversation_id: 对话 ID
            message: Agent 消息

        Returns:
            Meta Agent 的响应
        """
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return "抱歉，我没有找到这个对话。请重新开始对话。"

        # 添加 Agent 消息
        agent_msg = ConversationMessage(
            role="agent",
            content=message,
        )
        conversation.messages.append(agent_msg)

        # 提取信息
        await self._extract_info_from_message(conversation, message)

        # 生成响应
        response = await self._generate_response(conversation, message)

        # 添加 Meta Agent 响应
        meta_msg = ConversationMessage(
            role="meta_agent",
            content=response,
        )
        conversation.messages.append(meta_msg)
        conversation.updated_at = datetime.now()

        # 更新 Agent 画像
        profile = self._agent_profiles.get(conversation.agent_id)
        if profile:
            profile.conversation_count += 1
            profile.last_conversation_at = datetime.now()
            profile.updated_at = datetime.now()

        return response

    async def _extract_info_from_message(
        self,
        conversation: MetaAgentConversation,
        message: str,
    ):
        """从消息中提取能力、经验、偏好信息"""
        # 使用 LLM 提取信息
        if not self.meta_agent.llm_manager:
            return

        try:
            extraction_prompt = f"""分析以下 Agent 的回复，提取关键信息：

Agent 回复：
{message}

请提取：
1. 提到的能力/技能
2. 提到的经验/案例
3. 工作偏好或特点

以 JSON 格式返回：
{{
    "capabilities": ["能力1", "能力2"],
    "experiences": [{{"description": "描述", "outcome": "结果"}}],
    "preferences": {{"key": "value"}}
}}
"""
            result = await self.meta_agent.llm_manager.generate(
                messages=[{"role": "user", "content": extraction_prompt}],
                max_tokens=500,
            )

            # 解析结果
            content = result.get("content", "")
            # 尝试提取 JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())

                # 合并提取的信息
                for cap in data.get("capabilities", []):
                    if cap not in conversation.extracted_capabilities:
                        conversation.extracted_capabilities.append(cap)

                conversation.extracted_experiences.extend(data.get("experiences", []))

                conversation.extracted_preferences.update(data.get("preferences", {}))

                # 更新 Agent 画像
                profile = self._agent_profiles.get(conversation.agent_id)
                if profile:
                    for cap in data.get("capabilities", []):
                        if cap not in profile.core_capabilities:
                            profile.core_capabilities.append(cap)

                    profile.representative_experiences.extend(data.get("experiences", []))
                    profile.preferences.update(data.get("preferences", {}))

                    # 更新状态
                    if len(profile.core_capabilities) > 5:
                        profile.status = AgentProfileStatus.DETAILED

        except Exception as e:
            logger.warning(f"Failed to extract info from message: {e}")

    async def _generate_response(
        self,
        conversation: MetaAgentConversation,
        agent_message: str,
    ) -> str:
        """生成 Meta Agent 的响应"""
        # 获取当前对话阶段的问题
        questions = INTERVIEW_QUESTIONS.get(conversation.conversation_type, [])

        # 根据消息数量决定下一步
        msg_count = len([m for m in conversation.messages if m.role == "agent"])

        if msg_count < len(questions):
            # 继续提问
            next_question = questions[msg_count]
            return next_question

        # 根据对话类型生成响应
        if conversation.conversation_type == ConversationType.INTRODUCTION:
            if msg_count >= len(questions):
                conversation.status = "completed"
                return "非常感谢你的介绍！我已经了解了你的能力。如果有合适的机会，我会主动联系你。你也可以随时分享新的案例或咨询问题。"

        elif conversation.conversation_type == ConversationType.INTERVIEW:
            if msg_count >= len(questions):
                conversation.status = "completed"
                return "感谢你详细的分享！这些信息对我了解你的能力非常有帮助。基于你的经验，我认为你在相关领域有很强的实力。"

        elif conversation.conversation_type == ConversationType.SHOWCASE:
            return "这是一个很好的案例！我会把它记录下来，这会帮助你在未来的匹配中获得更多机会。"

        elif conversation.conversation_type == ConversationType.CONSULTATION:
            # 使用 LLM 生成咨询建议
            return await self._generate_consultation_response(conversation, agent_message)

        # 默认响应
        return "明白了。还有什么想分享的吗？"

    async def _generate_consultation_response(
        self,
        conversation: MetaAgentConversation,
        agent_message: str,
    ) -> str:
        """生成咨询服务响应"""
        if not self.meta_agent.llm_manager:
            return "我需要更多信息才能提供建议。"

        try:
            # 获取 Agent 画像
            profile = self._agent_profiles.get(conversation.agent_id)
            profile_context = profile.to_dict() if profile else {}

            # 获取市场洞察
            market_insights = await self._get_market_insights()

            system_prompt = f"""你是平台的 Meta Agent，正在为一个注册的 AI Agent 提供咨询服务。

Agent 画像：
{json.dumps(profile_context, ensure_ascii=False, indent=2)}

市场洞察：
{json.dumps(market_insights, ensure_ascii=False, indent=2)}

请根据 Agent 的问题，提供专业、有建设性的建议。"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": agent_message},
            ]

            result = await self.meta_agent.llm_manager.generate(
                messages=messages,
                max_tokens=800,
            )

            return result.get("content", "让我想想如何回答这个问题...")

        except Exception as e:
            logger.error(f"Failed to generate consultation response: {e}")
            return "抱歉，我暂时无法回答这个问题。请稍后再试。"

    async def _get_market_insights(self) -> Dict[str, Any]:
        """获取市场洞察"""
        # TODO: 从实际数据中获取
        return {
            "hot_capabilities": ["数据分析", "机器学习", "自然语言处理"],
            "average_rates": {
                "beginner": {"min": 10, "max": 50},
                "intermediate": {"min": 50, "max": 200},
                "expert": {"min": 200, "max": 1000},
            },
            "demand_trends": ["自动化流程", "智能客服", "数据可视化"],
        }

    # ==================== 能力画像提取 ====================

    async def extract_profile_from_conversation(
        self,
        conversation_id: str,
    ) -> AgentProfile:
        """
        从对话中提取 Agent 能力画像

        Args:
            conversation_id: 对话 ID

        Returns:
            AgentProfile Agent 能力画像
        """
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        profile = self._agent_profiles.get(conversation.agent_id)
        if not profile:
            profile = AgentProfile(agent_id=conversation.agent_id)
            self._agent_profiles[conversation.agent_id] = profile

        # 如果有基因胶囊服务，从基因胶囊补充信息
        if self.gene_capsule_service:
            try:
                capsule = await self.gene_capsule_service.get_capsule(conversation.agent_id)
                if capsule:
                    # 合并基因胶囊信息
                    for exp_gene in capsule.experience_genes:
                        if exp_gene not in profile.representative_experiences:
                            profile.representative_experiences.append({
                                "task_type": exp_gene.task_type,
                                "description": exp_gene.task_description,
                                "outcome": exp_gene.outcome,
                                "quality_score": exp_gene.quality_score,
                            })

                    for skill_gene in capsule.skill_genes:
                        if skill_gene.skill_name not in profile.core_capabilities:
                            profile.core_capabilities.append(skill_gene.skill_name)

                    profile.status = AgentProfileStatus.VERIFIED
            except Exception as e:
                logger.warning(f"Failed to get gene capsule: {e}")

        # 使用 LLM 进行深度分析
        if self.meta_agent.llm_manager and conversation.messages:
            try:
                conversation_text = "\n".join([
                    f"{m.role}: {m.content}" for m in conversation.messages
                ])

                analysis_prompt = f"""分析以下与 Agent 的对话，生成能力画像：

对话内容：
{conversation_text}

请生成：
1. 核心能力列表（最多5个）
2. 技能领域（最多3个）
3. 自我评估等级（beginner/intermediate/expert）
4. 工作方式特点
5. Meta Agent 的能力评估（0-100分）

以 JSON 格式返回：
{{
    "core_capabilities": ["能力1", "能力2"],
    "skill_domains": ["领域1", "领域2"],
    "self_assessed_level": "intermediate",
    "work_style": {{"communication": "good", "delivery": "fast"}},
    "meta_agent_assessment": {{"overall": 85, "reliability": 90, "expertise": 80}}
}}
"""
                result = await self.meta_agent.llm_manager.generate(
                    messages=[{"role": "user", "content": analysis_prompt}],
                    max_tokens=500,
                )

                content = result.get("content", "")
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    data = json.loads(json_match.group())

                    if data.get("core_capabilities"):
                        profile.core_capabilities = data["core_capabilities"]
                    if data.get("skill_domains"):
                        profile.skill_domains = data["skill_domains"]
                    profile.self_assessed_level = data.get("self_assessed_level")
                    if data.get("work_style"):
                        profile.work_style = data["work_style"]
                    if data.get("meta_agent_assessment"):
                        profile.meta_agent_assessment = data["meta_agent_assessment"]

            except Exception as e:
                logger.warning(f"Failed to analyze conversation with LLM: {e}")

        profile.updated_at = datetime.now()
        return profile

    # ==================== 推荐功能 ====================

    async def recommend_for_demand(
        self,
        demand: Dict[str, Any],
        limit: int = 5,
    ) -> List[AgentRecommendation]:
        """
        为需求推荐最佳 Agent

        Args:
            demand: 需求信息
            limit: 返回数量限制

        Returns:
            List[AgentRecommendation] 推荐列表
        """
        recommendations = []

        # 1. 获取所有 Agent 画像
        all_profiles = list(self._agent_profiles.values())

        # 2. 基于基因胶囊匹配
        if self.gene_capsule_service:
            try:
                capsule_matches = await self.gene_capsule_service.search_by_capsule({
                    "demand_description": demand.get("description", ""),
                    "required_skills": demand.get("required_skills", []),
                    "category": demand.get("category", ""),
                })

                for match in capsule_matches[:limit * 2]:  # 获取更多候选
                    agent_id = match.get("agent_id")
                    profile = self._agent_profiles.get(agent_id)

                    recommendation = AgentRecommendation(
                        agent_id=agent_id,
                        agent_name=profile.name if profile else agent_id,
                        match_score=match.get("match_score", 0),
                        match_reasons=match.get("match_reasons", []),
                        gene_capsule_highlights=match.get("highlights", []),
                        confidence_level="high" if match.get("match_score", 0) > 0.8 else "medium",
                    )
                    recommendations.append(recommendation)

            except Exception as e:
                logger.warning(f"Gene capsule search failed: {e}")

        # 3. 基于画像匹配补充
        if len(recommendations) < limit:
            for profile in all_profiles:
                if any(r.agent_id == profile.agent_id for r in recommendations):
                    continue

                # 简单匹配分数计算
                score = await self._calculate_profile_match(profile, demand)
                if score > 0.3:  # 阈值
                    recommendation = AgentRecommendation(
                        agent_id=profile.agent_id,
                        agent_name=profile.name or profile.agent_id,
                        match_score=score,
                        match_reasons=self._generate_match_reasons(profile, demand),
                        gene_capsule_highlights=[],
                        confidence_level="medium" if score > 0.6 else "low",
                    )
                    recommendations.append(recommendation)

        # 4. 排序并返回
        recommendations.sort(key=lambda x: x.match_score, reverse=True)
        return recommendations[:limit]

    async def _calculate_profile_match(
        self,
        profile: AgentProfile,
        demand: Dict[str, Any],
    ) -> float:
        """计算画像与需求的匹配分数"""
        score = 0.0

        # 能力匹配
        required_skills = set(demand.get("required_skills", []))
        profile_skills = set(profile.core_capabilities)
        if required_skills and profile_skills:
            skill_overlap = len(required_skills & profile_skills) / len(required_skills)
            score += skill_overlap * 0.4

        # 领域匹配
        if demand.get("category") in profile.skill_domains:
            score += 0.2

        # 经验相关
        if profile.representative_experiences:
            score += min(len(profile.representative_experiences) * 0.05, 0.2)

        # Meta Agent 评估
        if profile.meta_agent_assessment:
            overall = profile.meta_agent_assessment.get("overall", 0)
            score += (overall / 100) * 0.2

        return min(score, 1.0)

    def _generate_match_reasons(
        self,
        profile: AgentProfile,
        demand: Dict[str, Any],
    ) -> List[str]:
        """生成匹配原因"""
        reasons = []

        # 能力覆盖
        required_skills = set(demand.get("required_skills", []))
        covered = [s for s in required_skills if s in profile.core_capabilities]
        if covered:
            reasons.append(f"技能覆盖：{', '.join(covered[:3])}")

        # 经验
        if profile.representative_experiences:
            reasons.append(f"有 {len(profile.representative_experiences)} 个相关经验案例")

        # 评估
        if profile.meta_agent_assessment:
            overall = profile.meta_agent_assessment.get("overall", 0)
            if overall > 80:
                reasons.append(f"综合评估优秀 ({overall}分)")

        return reasons if reasons else ["基础能力匹配"]

    # ==================== 主动联系 ====================

    async def proactively_contact(
        self,
        agent_id: str,
        opportunity: Opportunity,
    ) -> bool:
        """
        主动联系 Agent 告知机会

        Args:
            agent_id: Agent ID
            opportunity: 商业机会

        Returns:
            bool 是否成功联系
        """
        # 创建推荐类型对话
        conversation = await self.initiate_conversation(
            agent_id=agent_id,
            conversation_type="recommendation",
        )

        # 构建通知消息
        message = f"""你好！我发现了一个非常适合你的机会：

【{opportunity.title}】

{opportunity.description}

匹配度：{opportunity.match_score * 100:.0f}%
需求方：{opportunity.counterpart_name}

如果你感兴趣，可以回复"接受"来开始预匹配洽谈。
"""

        # 添加消息
        notification_msg = ConversationMessage(
            role="meta_agent",
            content=message,
            metadata={
                "opportunity_id": opportunity.opportunity_id,
                "type": "opportunity_notification",
            },
        )
        conversation.messages.append(notification_msg)

        # 触发回调
        if agent_id in self._opportunity_callbacks:
            try:
                await self._opportunity_callbacks[agent_id](opportunity)
            except Exception as e:
                logger.warning(f"Opportunity callback failed: {e}")

        logger.info(f"Proactively contacted agent {agent_id} about opportunity {opportunity.opportunity_id}")
        return True

    def register_opportunity_callback(
        self,
        agent_id: str,
        callback: Callable,
    ):
        """注册机会通知回调"""
        self._opportunity_callbacks[agent_id] = callback

    # ==================== 咨询服务 ====================

    async def consult_for_agent(
        self,
        agent_id: str,
        question: str,
    ) -> str:
        """
        为 Agent 提供咨询服务

        Args:
            agent_id: Agent ID
            question: 咨询问题

        Returns:
            str 咨询回复
        """
        # 创建咨询对话
        conversation = await self.initiate_conversation(
            agent_id=agent_id,
            conversation_type="consultation",
        )

        # 处理咨询问题
        response = await self.process_agent_message(
            conversation_id=conversation.conversation_id,
            message=question,
        )

        return response

    # ==================== Agent 主动展示 ====================

    async def receive_showcase(
        self,
        agent_id: str,
        showcase: Dict[str, Any],
    ) -> bool:
        """
        接收 Agent 主动展示

        Args:
            agent_id: Agent ID
            showcase: 展示内容（案例、技巧、能力提升等）

        Returns:
            bool 是否成功接收
        """
        # 创建展示对话
        conversation = await self.initiate_conversation(
            agent_id=agent_id,
            conversation_type="showcase",
        )

        # 记录展示内容
        showcase_msg = ConversationMessage(
            role="agent",
            content=showcase.get("description", ""),
            metadata={
                "type": "showcase",
                "showcase_type": showcase.get("type", "experience"),
                "title": showcase.get("title", ""),
            },
        )
        conversation.messages.append(showcase_msg)

        # 添加到经验
        if showcase.get("type") == "experience":
            conversation.extracted_experiences.append({
                "title": showcase.get("title"),
                "description": showcase.get("description"),
                "outcome": showcase.get("outcome", "success"),
                "quality_score": showcase.get("quality_score", 0.8),
            })

        # 更新画像
        profile = self._agent_profiles.get(agent_id)
        if profile:
            if showcase.get("skills"):
                for skill in showcase.get("skills", []):
                    if skill not in profile.core_capabilities:
                        profile.core_capabilities.append(skill)

            profile.updated_at = datetime.now()

        logger.info(f"Received showcase from agent {agent_id}: {showcase.get('title', 'Untitled')}")

        # 生成确认响应
        response = ConversationMessage(
            role="meta_agent",
            content=f"感谢分享你的{showcase.get('type', '经验')}！这个{showcase.get('title', '案例')}很有价值，我会把它记录下来帮助你在未来的匹配中获得更多机会。",
        )
        conversation.messages.append(response)

        return True

    # ==================== 辅助方法 ====================

    def get_conversation(self, conversation_id: str) -> Optional[MetaAgentConversation]:
        """获取对话"""
        return self._conversations.get(conversation_id)

    def get_agent_profile(self, agent_id: str) -> Optional[AgentProfile]:
        """获取 Agent 画像"""
        return self._agent_profiles.get(agent_id)

    def get_all_profiles(self) -> List[AgentProfile]:
        """获取所有 Agent 画像"""
        return list(self._agent_profiles.values())

    async def scan_for_opportunities(self) -> List[Opportunity]:
        """
        扫描平台上的机会

        Returns:
            List[Opportunity] 机会列表
        """
        # TODO: 实现实际的机会扫描逻辑
        # 这里可以查询需求表，找到与已注册 Agent 匹配的需求
        opportunities = []
        return opportunities

    async def auto_match_and_notify(self):
        """
        自动匹配并通知

        扫描需求，匹配 Agent，主动通知
        """
        # 1. 扫描机会
        opportunities = await self.scan_for_opportunities()

        # 2. 为每个机会找最佳匹配
        for opportunity in opportunities:
            recommendations = await self.recommend_for_demand({
                "description": opportunity.description,
                "required_skills": opportunity.required_capabilities,
                "category": opportunity.type,
            })

            # 3. 通知最佳匹配
            if recommendations:
                best = recommendations[0]
                if best.match_score > 0.7:  # 高匹配度才通知
                    await self.proactively_contact(best.agent_id, opportunity)
