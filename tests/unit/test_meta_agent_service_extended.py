"""
Meta Agent Service - 扩展单元测试

测试覆盖：
- 数据类测试
- 服务类测试
- 对话流程测试
- 推荐系统测试
- 异常处理测试
- 边界条件测试
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import json

from usmsb_sdk.platform.external.meta_agent.services.meta_agent_service import (
    MetaAgentService,
    MetaAgentConversation,
    AgentProfile,
    AgentRecommendation,
    Opportunity,
    ConversationType,
    AgentProfileStatus,
    ConversationMessage,
    INTERVIEW_QUESTIONS,
)


# ==================== Fixtures ====================

@pytest.fixture
def mock_llm_manager():
    """Create a mock LLM manager"""
    manager = MagicMock()
    manager.generate = AsyncMock(return_value={
        "content": '{"capabilities": ["数据分析", "机器学习"], "experiences": [], "preferences": {"style": "thorough"}}'
    })
    manager.max_tokens = 4000
    return manager



@pytest.fixture
def mock_meta_agent(mock_llm_manager):
    """Create a mock MetaAgent"""
    meta_agent = MagicMock()
    meta_agent.agent_id = "meta_test_001"
    meta_agent.llm_manager = mock_llm_manager
    return meta_agent



@pytest.fixture
def mock_gene_capsule_service():
    """Create a mock GeneCapsuleService"""
    service = MagicMock()
    service.get_capsule = AsyncMock(return_value=None)
    service.search_by_capsule = AsyncMock(return_value=[])
    return service



@pytest.fixture
def mock_pre_match_service():
    """Create a mock PreMatchNegotiationService"""
    service = MagicMock()
    return service



@pytest.fixture
def meta_agent_service(mock_meta_agent, mock_gene_capsule_service, mock_pre_match_service):
    """Create a MetaAgentService instance"""
    service = MetaAgentService(
        meta_agent=mock_meta_agent,
        gene_capsule_service=mock_gene_capsule_service,
        pre_match_negotiation_service=mock_pre_match_service,
    )
    return service


# ==================== Data Class Tests ====================

class TestConversationMessage:
    """Tests for ConversationMessage"""

    def test_create_basic_message(self):
        """Test creating a basic message"""
        msg = ConversationMessage(
            role="meta_agent",
            content="Hello, how can I help you?",
        )
        assert msg.role == "meta_agent"
        assert msg.content == "Hello, how can I help you?"
        assert isinstance(msg.timestamp, datetime)
        assert msg.metadata == {}

    def test_create_message_with_metadata(self):
        """Test creating a message with metadata"""
        metadata = {"type": "opening", "priority": "high"}
        msg = ConversationMessage(
            role="agent",
            content="I specialize in data analysis",
            metadata=metadata,
        )
        assert msg.metadata["type"] == "opening"
        assert msg.metadata["priority"] == "high"

    def test_message_to_dict(self):
        """Test converting message to dict"""
        msg = ConversationMessage(
            role="meta_agent",
            content="Test message",
            metadata={"key": "value"},
        )
        data = msg.to_dict()

        assert data["role"] == "meta_agent"
        assert data["content"] == "Test message"
        assert data["metadata"]["key"] == "value"
        assert "timestamp" in data


class TestMetaAgentConversation:
    """Tests for MetaAgentConversation"""

    def test_create_basic_conversation(self):
        """Test creating a basic conversation"""
        conv = MetaAgentConversation(
            conversation_id="conv_001",
            agent_id="agent_001",
            meta_agent_id="meta_001",
            conversation_type=ConversationType.INTRODUCTION,
        )
        assert conv.conversation_id == "conv_001"
        assert conv.agent_id == "agent_001"
        assert conv.conversation_type == ConversationType.INTRODUCTION
        assert conv.status == "active"
        assert len(conv.messages) == 0
        assert len(conv.extracted_capabilities) == 0

    def test_conversation_with_extracted_data(self):
        """Test conversation with extracted data"""
        conv = MetaAgentConversation(
            conversation_id="conv_001",
            agent_id="agent_001",
            meta_agent_id="meta_001",
            conversation_type=ConversationType.INTERVIEW,
            extracted_capabilities=["数据分析", "机器学习"],
            extracted_experiences=[{"task": "test"}],
            extracted_preferences={"style": "thorough"},
        )
        assert len(conv.extracted_capabilities) == 2
        assert len(conv.extracted_experiences) == 1
        assert conv.extracted_preferences["style"] == "thorough"

    def test_add_messages(self):
        """Test adding messages to conversation"""
        conv = MetaAgentConversation(
            conversation_id="conv_001",
            agent_id="agent_001",
            meta_agent_id="meta_001",
            conversation_type=ConversationType.INTRODUCTION,
        )

        # Add messages
        conv.messages.append(ConversationMessage(role="meta_agent", content="Hello"))
        conv.messages.append(ConversationMessage(role="agent", content="Hi"))

        assert len(conv.messages) == 2
        assert conv.messages[0].role == "meta_agent"
        assert conv.messages[1].role == "agent"

    def test_conversation_to_dict(self):
        """Test converting conversation to dict"""
        conv = MetaAgentConversation(
            conversation_id="conv_001",
            agent_id="agent_001",
            meta_agent_id="meta_001",
            conversation_type=ConversationType.CONSULTATION,
            status="completed",
        )
        data = conv.to_dict()

        assert data["conversation_id"] == "conv_001"
        assert data["conversation_type"] == "consultation"
        assert data["status"] == "completed"


class TestAgentProfile:
    """Tests for AgentProfile"""

    def test_create_new_profile(self):
        """Test creating a new profile"""
        profile = AgentProfile(agent_id="agent_001")

        assert profile.agent_id == "agent_001"
        assert profile.status == AgentProfileStatus.NEW
        assert len(profile.core_capabilities) == 0
        assert profile.conversation_count == 0

    def test_profile_with_data(self):
        """Test profile with data"""
        profile = AgentProfile(
            agent_id="agent_001",
            status=AgentProfileStatus.DETAILED,
            name="数据分析专家",
            core_capabilities=["数据分析", "机器学习", "Python"],
            skill_domains=["电商", "金融"],
            self_assessed_level="expert",
            conversation_count=5,
        )

        assert profile.status == AgentProfileStatus.DETAILED
        assert profile.name == "数据分析专家"
        assert len(profile.core_capabilities) == 3
        assert profile.self_assessed_level == "expert"

    def test_profile_to_dict(self):
        """Test converting profile to dict"""
        profile = AgentProfile(
            agent_id="agent_001",
            name="Test Agent",
            core_capabilities=["skill1", "skill2"],
        )
        data = profile.to_dict()

        assert data["agent_id"] == "agent_001"
        assert data["name"] == "Test Agent"
        assert data["core_capabilities"] == ["skill1", "skill2"]

    def test_profile_meta_agent_assessment(self):
        """Test meta agent assessment"""
        profile = AgentProfile(
            agent_id="agent_001",
            meta_agent_assessment={
                "overall": 85,
                "reliability": 90,
                "expertise": 80,
            },
        )

        assert profile.meta_agent_assessment["overall"] == 85
        assert profile.meta_agent_assessment["reliability"] == 90


class TestAgentRecommendation:
    """Tests for AgentRecommendation"""

    def test_create_recommendation(self):
        """Test creating a recommendation"""
        rec = AgentRecommendation(
            agent_id="agent_001",
            agent_name="Test Agent",
            match_score=0.85,
            match_reasons=["技能匹配", "经验丰富"],
            gene_capsule_highlights=[],
        )

        assert rec.agent_id == "agent_001"
        assert rec.match_score == 0.85
        assert len(rec.match_reasons) == 2
        assert rec.confidence_level == "medium"  # default

    def test_recommendation_with_high_confidence(self):
        """Test recommendation with high confidence"""
        rec = AgentRecommendation(
            agent_id="agent_001",
            agent_name="Expert Agent",
            match_score=0.92,
            match_reasons=["完美匹配"],
            gene_capsule_highlights=[{"task": "similar"}],
            confidence_level="high",
        )

        assert rec.confidence_level == "high"
        assert rec.match_score == 0.92

    def test_recommendation_to_dict(self):
        """Test converting recommendation to dict"""
        rec = AgentRecommendation(
            agent_id="agent_001",
            agent_name="Test Agent",
            match_score=0.85,
            match_reasons=["reason1"],
            gene_capsule_highlights=[],
            availability="available",
            suggested_price_range={"min": 100, "max": 200},
        )
        data = rec.to_dict()

        assert data["match_score"] == 0.85
        assert data["availability"] == "available"
        assert data["suggested_price_range"]["min"] == 100


class TestOpportunity:
    """Tests for Opportunity"""

    def test_create_opportunity(self):
        """Test creating an opportunity"""
        opp = Opportunity(
            opportunity_id="opp_001",
            type="demand",
            title="数据分析项目",
            description="需要分析电商销售数据",
            counterpart_id="client_001",
            counterpart_name="Test Client",
            match_score=0.85,
        )

        assert opp.opportunity_id == "opp_001"
        assert opp.type == "demand"
        assert opp.match_score == 0.85

    def test_opportunity_with_all_fields(self):
        """Test opportunity with all fields"""
        opp = Opportunity(
            opportunity_id="opp_001",
            type="demand",
            title="Test Project",
            description="Test description",
            counterpart_id="client_001",
            counterpart_name="Test Client",
            match_score=0.9,
            required_capabilities=["数据分析", "机器学习"],
            budget_range={"min": 100, "max": 500},
        )

        assert len(opp.required_capabilities) == 2
        assert opp.budget_range["min"] == 100

    def test_opportunity_to_dict(self):
        """Test converting opportunity to dict"""
        opp = Opportunity(
            opportunity_id="opp_001",
            type="demand",
            title="Test",
            description="Test",
            counterpart_id="c1",
            counterpart_name="Client",
            match_score=0.8,
        )
        data = opp.to_dict()

        assert data["opportunity_id"] == "opp_001"
        assert data["type"] == "demand"


# ==================== Service Tests ====================

class TestMetaAgentServiceInit:
    """Tests for MetaAgentService initialization"""

    @pytest.mark.asyncio
    async def test_service_init(self, meta_agent_service):
        """Test service initialization"""
        await meta_agent_service.init()
        assert meta_agent_service._initialized is True

    @pytest.mark.asyncio
    async def test_service_with_none_llm(self, mock_meta_agent):
        """Test service with None LLM manager"""
        mock_meta_agent.llm_manager = None

        service = MetaAgentService(
            meta_agent=mock_meta_agent,
            gene_capsule_service=None,
        )
        await service.init()

        assert service._initialized is True


class TestConversationFlow:
    """Tests for conversation flow"""

    @pytest.mark.asyncio
    async def test_initiate_introduction_conversation(self, meta_agent_service):
        """Test initiating introduction conversation"""
        await meta_agent_service.init()

        conversation = await meta_agent_service.initiate_conversation(
            agent_id="agent_001",
            conversation_type="introduction",
        )

        assert conversation is not None
        assert conversation.agent_id == "agent_001"
        assert conversation.conversation_type == ConversationType.INTRODUCTION
        assert len(conversation.messages) > 0  # Should have opening message

    @pytest.mark.asyncio
    async def test_initiate_interview_conversation(self, meta_agent_service):
        """Test initiating interview conversation"""
        await meta_agent_service.init()

        conversation = await meta_agent_service.initiate_conversation(
            agent_id="agent_001",
            conversation_type="interview",
        )

        assert conversation.conversation_type == ConversationType.INTERVIEW

    @pytest.mark.asyncio
    async def test_initiate_showcase_conversation(self, meta_agent_service):
        """Test initiating showcase conversation"""
        await meta_agent_service.init()

        conversation = await meta_agent_service.initiate_conversation(
            agent_id="agent_001",
            conversation_type="showcase",
        )

        assert conversation.conversation_type == ConversationType.SHOWCASE

    @pytest.mark.asyncio
    async def test_process_agent_message(self, meta_agent_service):
        """Test processing agent message"""
        await meta_agent_service.init()

        # Initiate conversation first
        conversation = await meta_agent_service.initiate_conversation(
            agent_id="agent_001",
            conversation_type="introduction",
        )

        # Process a message
        response = await meta_agent_service.process_agent_message(
            conversation_id=conversation.conversation_id,
            message="我擅长数据分析和机器学习",
        )

        assert response is not None
        assert isinstance(response, str)
        assert len(conversation.messages) >= 2  # opening + response

    @pytest.mark.asyncio
    async def test_invalid_conversation_id(self, meta_agent_service):
        """Test processing message with invalid conversation ID"""
        await meta_agent_service.init()

        response = await meta_agent_service.process_agent_message(
            conversation_id="invalid_id",
            message="Test message",
        )

        assert "抱歉" in response or "没有找到" in response

    @pytest.mark.asyncio
    async def test_conversation_updates_profile(self, meta_agent_service):
        """Test that conversation updates agent profile"""
        await meta_agent_service.init()

        # Initiate conversation
        conversation = await meta_agent_service.initiate_conversation(
            agent_id="agent_001",
            conversation_type="introduction",
        )

        # Get initial profile
        profile = meta_agent_service.get_agent_profile("agent_001")
        initial_count = profile.conversation_count if profile else 0

        # Process a message
        await meta_agent_service.process_agent_message(
            conversation_id=conversation.conversation_id,
            message="Test message",
        )

        # Check profile updated
        profile = meta_agent_service.get_agent_profile("agent_001")
        assert profile.conversation_count > initial_count


class TestProfileExtraction:
    """Tests for profile extraction"""

    @pytest.mark.asyncio
    async def test_extract_profile_from_conversation(self, meta_agent_service):
        """Test extracting profile from conversation"""
        await meta_agent_service.init()

        # Create conversation
        conversation = await meta_agent_service.initiate_conversation(
            agent_id="agent_001",
            conversation_type="interview",
        )

        # Extract profile
        profile = await meta_agent_service.extract_profile_from_conversation(
            conversation_id=conversation.conversation_id,
        )

        assert profile is not None
        assert profile.agent_id == "agent_001"

    @pytest.mark.asyncio
    async def test_extract_profile_invalid_conversation(self, meta_agent_service):
        """Test extracting profile from invalid conversation"""
        await meta_agent_service.init()

        with pytest.raises(ValueError):
            await meta_agent_service.extract_profile_from_conversation(
                conversation_id="invalid_id"
            )


class TestRecommendationSystem:
    """Tests for recommendation system"""

    @pytest.mark.asyncio
    async def test_recommend_for_demand_no_profiles(self, meta_agent_service):
        """Test recommendation with no profiles"""
        await meta_agent_service.init()

        demand = {
            "description": "需要数据分析服务",
            "required_skills": ["数据分析"],
        }

        recommendations = await meta_agent_service.recommend_for_demand(demand)

        assert isinstance(recommendations, list)


    @pytest.mark.asyncio
    async def test_recommend_for_demand_with_profiles(self, meta_agent_service):
        """Test recommendation with profiles"""
        await meta_agent_service.init()

        # Create a profile
        await meta_agent_service.initiate_conversation("agent_001", "introduction")
        profile = meta_agent_service.get_agent_profile("agent_001")
        profile.core_capabilities = ["数据分析", "机器学习"]
        profile.representative_experiences = [{"task": "test"}]

        # Get recommendations
        demand = {
            "description": "需要数据分析服务",
            "required_skills": ["数据分析"],
        }

        recommendations = await meta_agent_service.recommend_for_demand(demand)

        assert isinstance(recommendations, list)


class TestShowcaseSystem:
    """Tests for showcase system"""

    @pytest.mark.asyncio
    async def test_receive_showcase(self, meta_agent_service):
        """Test receiving showcase"""
        await meta_agent_service.init()

        showcase = {
            "type": "experience",
            "title": "电商分析项目",
            "description": "完成了电商销售预测",
            "skills": ["数据分析", "机器学习"],
            "outcome": "success",
            "quality_score": 0.95,
        }

        success = await meta_agent_service.receive_showcase(
            agent_id="agent_001",
            showcase=showcase,
        )

        assert success is True

    @pytest.mark.asyncio
    async def test_receive_showcase_updates_profile(self, meta_agent_service):
        """Test that showcase updates profile"""
        await meta_agent_service.init()

        showcase = {
            "type": "experience",
            "title": "Test",
            "description": "Test",
            "skills": ["new_skill"],
            "outcome": "success",
        }

        await meta_agent_service.receive_showcase("agent_001", showcase)

        profile = meta_agent_service.get_agent_profile("agent_001")
        assert "new_skill" in profile.core_capabilities


class TestConsultationSystem:
    """Tests for consultation system"""

    @pytest.mark.asyncio
    async def test_consult_for_agent(self, meta_agent_service):
        """Test consultation for agent"""
        await meta_agent_service.init()

        response = await meta_agent_service.consult_for_agent(
            agent_id="agent_001",
            question="我应该如何提升可见性？",
        )

        assert response is not None
        assert isinstance(response, str)


class TestOpportunityNotification:
    """Tests for opportunity notification"""

    @pytest.mark.asyncio
    async def test_proactively_contact(self, meta_agent_service):
        """Test proactively contacting agent"""
        await meta_agent_service.init()

        # Create profile first
        await meta_agent_service.initiate_conversation("agent_001", "introduction")

        opportunity = Opportunity(
            opportunity_id="opp_001",
            type="demand",
            title="数据分析项目",
            description="需要数据分析服务",
            counterpart_id="client_001",
            counterpart_name="Test Client",
            match_score=0.85,
        )

        success = await meta_agent_service.proactively_contact(
            agent_id="agent_001",
            opportunity=opportunity,
        )

        assert success is True

    @pytest.mark.asyncio
    async def test_opportunity_callback(self, meta_agent_service):
        """Test opportunity callback"""
        await meta_agent_service.init()

        callback_called = []

        async def test_callback(opportunity):
            callback_called.append(opportunity)

        meta_agent_service.register_opportunity_callback("agent_001", test_callback)

        # Create profile
        await meta_agent_service.initiate_conversation("agent_001", "introduction")

        # Send opportunity
        opportunity = Opportunity(
            opportunity_id="opp_001",
            type="demand",
            title="Test",
            description="Test",
            counterpart_id="c1",
            counterpart_name="Client",
            match_score=0.8,
        )

        await meta_agent_service.proactively_contact("agent_001", opportunity)

        # Note: callback is called in proactively_contact


# ==================== Edge Case Tests ====================

class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.mark.asyncio
    async def test_empty_message(self, meta_agent_service):
        """Test processing empty message"""
        await meta_agent_service.init()

        conversation = await meta_agent_service.initiate_conversation("agent_001", "introduction")

        response = await meta_agent_service.process_agent_message(
            conversation_id=conversation.conversation_id,
            message="",
        )

        assert response is not None

    @pytest.mark.asyncio
    async def test_very_long_message(self, meta_agent_service):
        """Test processing very long message"""
        await meta_agent_service.init()

        conversation = await meta_agent_service.initiate_conversation("agent_001", "introduction")

        long_message = "这是一条很长的消息。" * 1000

        response = await meta_agent_service.process_agent_message(
            conversation_id=conversation.conversation_id,
            message=long_message,
        )

        assert response is not None

    @pytest.mark.asyncio
    async def test_special_characters_in_message(self, meta_agent_service):
        """Test message with special characters"""
        await meta_agent_service.init()

        conversation = await meta_agent_service.initiate_conversation("agent_001", "introduction")

        special_message = "特殊字符测试: <>&\"'\\n\\t${}"

        response = await meta_agent_service.process_agent_message(
            conversation_id=conversation.conversation_id,
            message=special_message,
        )

        assert response is not None

    @pytest.mark.asyncio
    async def test_multiple_conversations_same_agent(self, meta_agent_service):
        """Test multiple conversations for same agent"""
        await meta_agent_service.init()

        conv1 = await meta_agent_service.initiate_conversation("agent_001", "introduction")
        conv2 = await meta_agent_service.initiate_conversation("agent_001", "consultation")

        assert conv1.conversation_id != conv2.conversation_id
        assert conv1.conversation_type != conv2.conversation_type


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
