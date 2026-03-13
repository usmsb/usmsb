"""
Meta Agent Service Unit Tests

Tests for MetaAgentService and related functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from usmsb_sdk.platform.external.meta_agent.services.meta_agent_service import (
    MetaAgentService,
    MetaAgentConversation,
    AgentProfile,
    AgentRecommendation,
    Opportunity,
    ConversationType,
    AgentProfileStatus,
    ConversationMessage,
)


# ==================== Fixtures ====================

@pytest.fixture
def mock_meta_agent():
    """Create a mock MetaAgent"""
    meta_agent = MagicMock()
    meta_agent.agent_id = "meta_test_001"
    meta_agent.llm_manager = MagicMock()
    meta_agent.llm_manager.generate = AsyncMock(return_value={
        "content": '{"capabilities": ["数据分析"], "experiences": [], "preferences": {}}'
    })
    return meta_agent


@pytest.fixture
def mock_gene_capsule_service():
    """Create a mock GeneCapsuleService"""
    service = MagicMock()
    service.get_capsule = AsyncMock(return_value=None)
    service.search_by_capsule = AsyncMock(return_value=[])
    return service


@pytest.fixture
def meta_agent_service(mock_meta_agent, mock_gene_capsule_service):
    """Create a MetaAgentService instance"""
    service = MetaAgentService(
        meta_agent=mock_meta_agent,
        gene_capsule_service=mock_gene_capsule_service,
    )
    return service


# ==================== Data Class Tests ====================

class TestConversationMessage:
    """Tests for ConversationMessage"""

    def test_create_message(self):
        """Test creating a conversation message"""
        msg = ConversationMessage(
            role="meta_agent",
            content="Hello",
        )
        assert msg.role == "meta_agent"
        assert msg.content == "Hello"
        assert isinstance(msg.timestamp, datetime)

    def test_message_to_dict(self):
        """Test converting message to dict"""
        msg = ConversationMessage(
            role="agent",
            content="Test message",
            metadata={"type": "test"},
        )
        data = msg.to_dict()
        assert data["role"] == "agent"
        assert data["content"] == "Test message"
        assert data["metadata"]["type"] == "test"
        assert "timestamp" in data


class TestMetaAgentConversation:
    """Tests for MetaAgentConversation"""

    def test_create_conversation(self):
        """Test creating a conversation"""
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

    def test_add_message(self):
        """Test adding messages to conversation"""
        conv = MetaAgentConversation(
            conversation_id="conv_001",
            agent_id="agent_001",
            meta_agent_id="meta_001",
            conversation_type=ConversationType.INTRODUCTION,
        )
        msg = ConversationMessage(role="meta_agent", content="Hello")
        conv.messages.append(msg)
        assert len(conv.messages) == 1

    def test_conversation_to_dict(self):
        """Test converting conversation to dict"""
        conv = MetaAgentConversation(
            conversation_id="conv_001",
            agent_id="agent_001",
            meta_agent_id="meta_001",
            conversation_type=ConversationType.INTERVIEW,
            extracted_capabilities=["数据分析", "机器学习"],
        )
        data = conv.to_dict()
        assert data["conversation_id"] == "conv_001"
        assert data["conversation_type"] == "interview"
        assert data["extracted_capabilities"] == ["数据分析", "机器学习"]


class TestAgentProfile:
    """Tests for AgentProfile"""

    def test_create_profile(self):
        """Test creating an agent profile"""
        profile = AgentProfile(
            agent_id="agent_001",
        )
        assert profile.agent_id == "agent_001"
        assert profile.status == AgentProfileStatus.NEW
        assert len(profile.core_capabilities) == 0

    def test_profile_to_dict(self):
        """Test converting profile to dict"""
        profile = AgentProfile(
            agent_id="agent_001",
            status=AgentProfileStatus.DETAILED,
            name="数据分析专家",
            core_capabilities=["数据分析", "机器学习"],
            conversation_count=5,
        )
        data = profile.to_dict()
        assert data["agent_id"] == "agent_001"
        assert data["status"] == "detailed"
        assert data["name"] == "数据分析专家"
        assert data["core_capabilities"] == ["数据分析", "机器学习"]
        assert data["conversation_count"] == 5


class TestAgentRecommendation:
    """Tests for AgentRecommendation"""

    def test_create_recommendation(self):
        """Test creating a recommendation"""
        rec = AgentRecommendation(
            agent_id="agent_001",
            agent_name="Test Agent",
            match_score=0.85,
            match_reasons=["技能匹配"],
            gene_capsule_highlights=[],
        )
        assert rec.agent_id == "agent_001"
        assert rec.match_score == 0.85
        assert rec.confidence_level == "medium"

    def test_recommendation_to_dict(self):
        """Test converting recommendation to dict"""
        rec = AgentRecommendation(
            agent_id="agent_001",
            agent_name="Test Agent",
            match_score=0.92,
            match_reasons=["技能覆盖", "经验丰富"],
            gene_capsule_highlights=[{"task": "test"}],
            confidence_level="high",
        )
        data = rec.to_dict()
        assert data["match_score"] == 0.92
        assert data["confidence_level"] == "high"
        assert len(data["match_reasons"]) == 2


class TestOpportunity:
    """Tests for Opportunity"""

    def test_create_opportunity(self):
        """Test creating an opportunity"""
        opp = Opportunity(
            opportunity_id="opp_001",
            type="demand",
            title="数据分析项目",
            description="需要数据分析服务",
            counterpart_id="client_001",
            counterpart_name="Test Client",
            match_score=0.85,
        )
        assert opp.opportunity_id == "opp_001"
        assert opp.type == "demand"
        assert opp.match_score == 0.85

    def test_opportunity_to_dict(self):
        """Test converting opportunity to dict"""
        opp = Opportunity(
            opportunity_id="opp_001",
            type="demand",
            title="Test Project",
            description="Test description",
            counterpart_id="client_001",
            counterpart_name="Test Client",
            match_score=0.9,
            required_capabilities=["数据分析"],
        )
        data = opp.to_dict()
        assert data["opportunity_id"] == "opp_001"
        assert data["required_capabilities"] == ["数据分析"]


# ==================== Service Tests ====================

class TestMetaAgentService:
    """Tests for MetaAgentService"""

    @pytest.mark.asyncio
    async def test_init(self, meta_agent_service):
        """Test service initialization"""
        await meta_agent_service.init()
        assert meta_agent_service._initialized is True

    @pytest.mark.asyncio
    async def test_initiate_conversation(self, meta_agent_service):
        """Test initiating a conversation"""
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
        """Test initiating an interview conversation"""
        await meta_agent_service.init()

        conversation = await meta_agent_service.initiate_conversation(
            agent_id="agent_001",
            conversation_type="interview",
        )

        assert conversation.conversation_type == ConversationType.INTERVIEW

    @pytest.mark.asyncio
    async def test_process_agent_message(self, meta_agent_service):
        """Test processing agent message"""
        await meta_agent_service.init()

        # First initiate a conversation
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
        assert len(conversation.messages) >= 3  # opening + agent + response

    @pytest.mark.asyncio
    async def test_get_agent_profile(self, meta_agent_service):
        """Test getting agent profile"""
        await meta_agent_service.init()

        # Create a profile through conversation
        await meta_agent_service.initiate_conversation(
            agent_id="agent_001",
            conversation_type="introduction",
        )

        profile = meta_agent_service.get_agent_profile("agent_001")
        assert profile is not None
        assert profile.agent_id == "agent_001"

    @pytest.mark.asyncio
    async def test_get_all_profiles(self, meta_agent_service):
        """Test getting all profiles"""
        await meta_agent_service.init()

        # Create multiple profiles
        await meta_agent_service.initiate_conversation("agent_001", "introduction")
        await meta_agent_service.initiate_conversation("agent_002", "introduction")

        profiles = meta_agent_service.get_all_profiles()
        assert len(profiles) == 2

    @pytest.mark.asyncio
    async def test_recommend_for_demand(self, meta_agent_service):
        """Test recommending agents for demand"""
        await meta_agent_service.init()

        # Create some profiles
        await meta_agent_service.initiate_conversation("agent_001", "introduction")

        # Get the profile and add capabilities
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

    @pytest.mark.asyncio
    async def test_receive_showcase(self, meta_agent_service):
        """Test receiving agent showcase"""
        await meta_agent_service.init()

        showcase = {
            "type": "experience",
            "title": "电商分析项目",
            "description": "完成了一个电商数据分析项目",
            "skills": ["数据分析", "电商"],
            "outcome": "success",
            "quality_score": 0.95,
        }

        success = await meta_agent_service.receive_showcase(
            agent_id="agent_001",
            showcase=showcase,
        )

        assert success is True

        # Check that experience was added
        profile = meta_agent_service.get_agent_profile("agent_001")
        assert len(profile.core_capabilities) > 0 or len(profile.representative_experiences) > 0

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
    async def test_consult_for_agent(self, meta_agent_service):
        """Test consulting for agent"""
        await meta_agent_service.init()

        response = await meta_agent_service.consult_for_agent(
            agent_id="agent_001",
            question="我应该如何提升我的可见性？",
        )

        assert response is not None
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_extract_profile_from_conversation(self, meta_agent_service):
        """Test extracting profile from conversation"""
        await meta_agent_service.init()

        # Create conversation
        conversation = await meta_agent_service.initiate_conversation(
            agent_id="agent_001",
            conversation_type="interview",
        )

        # Add some messages
        await meta_agent_service.process_agent_message(
            conversation_id=conversation.conversation_id,
            message="我擅长数据分析和机器学习",
        )

        # Extract profile
        profile = await meta_agent_service.extract_profile_from_conversation(
            conversation_id=conversation.conversation_id,
        )

        assert profile is not None
        assert profile.agent_id == "agent_001"


# ==================== Integration Tests ====================

class TestMetaAgentServiceIntegration:
    """Integration tests for MetaAgentService"""

    @pytest.mark.asyncio
    async def test_full_interview_flow(self, meta_agent_service):
        """Test full interview flow"""
        await meta_agent_service.init()

        # 1. Initiate conversation
        conversation = await meta_agent_service.initiate_conversation(
            agent_id="agent_001",
            conversation_type="introduction",
        )
        assert conversation is not None

        # 2. Agent responds
        response = await meta_agent_service.process_agent_message(
            conversation_id=conversation.conversation_id,
            message="我是一名数据分析专家，擅长机器学习和数据可视化",
        )
        assert response is not None

        # 3. Get profile
        profile = meta_agent_service.get_agent_profile("agent_001")
        assert profile is not None
        assert profile.conversation_count >= 1

    @pytest.mark.asyncio
    async def test_showcase_and_recommend_flow(self, meta_agent_service):
        """Test showcase and recommendation flow"""
        await meta_agent_service.init()

        # 1. Agent shares showcase
        await meta_agent_service.receive_showcase(
            agent_id="agent_001",
            showcase={
                "type": "experience",
                "title": "电商销售预测",
                "description": "完成了电商销售预测项目，准确率92%",
                "skills": ["数据分析", "机器学习", "电商"],
                "outcome": "success",
                "quality_score": 0.95,
            },
        )

        # 2. Get recommendations for similar demand
        demand = {
            "description": "需要电商数据分析",
            "required_skills": ["数据分析", "电商"],
        }
        recommendations = await meta_agent_service.recommend_for_demand(demand)

        # Should have some recommendations
        assert isinstance(recommendations, list)


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
