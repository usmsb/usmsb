"""
Meta Agent 集成测试

测试模块之间的协作：
- MetaAgentService + GeneCapsuleService 集成
- MetaAgentService + PreMatchNegotiationService 集成
- Meta Agent 工具与平台集成
- 完整的匹配流程测试
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import json
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==================== Fixtures ====================

@pytest.fixture
def integration_config():
    """Integration test configuration"""
    return {
        "db_path": ":memory:",
        "llm_enabled": False,  # 禁用 LLM 以加快测试
    }



@pytest.fixture
async def meta_agent_instance(integration_config):
    """Create a real MetaAgent instance for integration testing"""
    from usmsb_sdk.platform.external.meta_agent.agent import MetaAgent
    from usmsb_sdk.platform.external.meta_agent.config import MetaAgentConfig

    config = MetaAgentConfig(
        database={"path": ":memory:"},
        llm={"enabled": False},
    )
    agent = MetaAgent(config)
    # 不调用 start()，只初始化基本组件
    await agent._init_components()
    await agent._register_default_tools()
    yield agent

    # Cleanup
    await agent.stop()


@pytest.fixture
async def gene_capsule_service(integration_config):
    """Create a real GeneCapsuleService instance"""
    from usmsb_sdk.api.rest.gene_capsule_service import GeneCapsuleService

    service = GeneCapsuleService()
    return service


# ==================== Integration: MetaAgent + GeneCapsule ====================

class TestMetaAgentGeneCapsuleIntegration:
    """Test integration between MetaAgent and GeneCapsule"""

    @pytest.mark.asyncio
    async def test_meta_agent_service_initialization(self, meta_agent_instance):
        """Test that MetaAgentService is initialized in MetaAgent"""
        assert meta_agent_instance.meta_agent_service is not None

    @pytest.mark.asyncio
    async def test_meta_agent_has_precise_matching_tools(self, meta_agent_instance):
        """Test that MetaAgent has precise matching tools registered"""
        tools = meta_agent_instance.tool_registry.list_tools()
        tool_names = [t["name"] for t in tools]

        # 检查关键工具是否存在
        assert "interview_agent" in tool_names
        assert "recommend_agents_for_demand" in tool_names
        assert "match_by_gene_capsule" in tool_names

    @pytest.mark.asyncio
    async def test_interview_creates_profile(self, meta_agent_instance):
        """Test that interview creates agent profile"""
        service = meta_agent_instance.meta_agent_service
        await service.init()

        # 发起对话
        conversation = await service.initiate_conversation(
            agent_id="integration_agent_001",
            conversation_type="introduction",
        )

        # 发送消息
        await service.process_agent_message(
            conversation_id=conversation.conversation_id,
            message="我是一名数据分析专家",
        )

        # 检查画像是否创建
        profile = service.get_agent_profile("integration_agent_001")
        assert profile is not None
        assert profile.conversation_count >= 1


# ==================== Integration: Discovery + Matching ====================

class TestDiscoveryMatchingIntegration:
    """Test integration between Discovery and Matching"""

    @pytest.mark.asyncio
    async def test_enhanced_discovery_multi_dimensional_search(self):
        """Test multi-dimensional search in discovery"""
        from usmsb_sdk.agent_sdk.discovery import (
            EnhancedDiscoveryManager,
            DiscoveryFilter,
            SearchCriteria,
            MatchDimension,
        )

        discovery = EnhancedDiscoveryManager()

        # 创建搜索条件
        criteria = SearchCriteria(
            capabilities=["数据分析"],
            min_reputation=0.5,
            max_price=1000,
        )

        # 执行搜索（在没有实际数据库的情况下）
        # 这里只测试对象创建和参数处理
        assert criteria.capabilities == ["数据分析"]
        assert criteria.min_reputation == 0.5

    @pytest.mark.asyncio
    async def test_discovery_filter_creation(self):
        """Test discovery filter creation"""
        from usmsb_sdk.agent_sdk.discovery import DiscoveryFilter

        filter = DiscoveryFilter(
            capabilities=["python", "ml"],
            min_price=100,
            max_price=500,
            min_reputation=0.8,
            availability="available",
        )

        assert filter.capabilities == ["python", "ml"]
        assert filter.min_price == 100
        assert filter.max_price == 500
        assert filter.availability == "available"


# ==================== Integration: PreMatch + Negotiation ====================

class TestPreMatchNegotiationIntegration:
    """Test integration between PreMatchNegotiation and Negotiation"""

    @pytest.mark.asyncio
    async def test_pre_match_negotiation_flow(self):
        """Test complete pre-match negotiation flow"""
        from usmsb_sdk.services.pre_match_negotiation import (
            PreMatchNegotiationService,
            ClarificationQA,
            VerificationType,
        )

        service = PreMatchNegotiationService()

        # 发起洽谈
        negotiation = await service.initiate(
            demand_agent_id="demand_001",
            supply_agent_id="supply_001",
            demand_id="demand_req_001",
        )

        assert negotiation is not None
        assert negotiation.status.value == "initiated"

        # 提问
        qa = await service.ask_question(
            negotiation_id=negotiation.negotiation_id,
            question="您需要什么样的数据格式？",
            asker_id="demand_001",
        )

        assert qa is not None
        assert qa.question == "您需要什么样的数据格式？"

        # 回答
        answered = await service.answer_question(
            negotiation_id=negotiation.negotiation_id,
            question_id=qa.question_id,
            answer="需要 CSV 或 JSON 格式",
        )

        assert answered.answer == "需要 CSV 或 JSON 格式"

    @pytest.mark.asyncio
    async def test_verification_request_flow(self):
        """Test capability verification flow"""
        from usmsb_sdk.services.pre_match_negotiation import (
            PreMatchNegotiationService,
            VerificationType,
        )

        service = PreMatchNegotiationService()

        # 发起洽谈
        negotiation = await service.initiate(
            demand_agent_id="demand_002",
            supply_agent_id="supply_002",
            demand_id="demand_req_002",
        )

        # 请求验证
        request = await service.request_verification(
            negotiation_id=negotiation.negotiation_id,
            capability="数据分析",
            verification_type=VerificationType.GENE_CAPSULE,
            request_detail="请展示相关的数据分析经验",
        )

        assert request is not None
        assert request.verification_type == VerificationType.GENE_CAPSULE

        # 提交验证
        result = await service.submit_verification(
            negotiation_id=negotiation.negotiation_id,
            request_id=request.request_id,
            response="我有3年数据分析经验，完成过20+项目",
        )

        assert result.status == "submitted"


# ==================== Integration: GeneCapsule + Discovery ====================

class TestGeneCapsuleDiscoveryIntegration:
    """Test integration between GeneCapsule and Discovery"""

    @pytest.mark.asyncio
    async def test_gene_capsule_experience_discovery(self):
        """Test discovering agents by gene capsule experience"""
        from usmsb_sdk.agent_sdk.discovery import EnhancedDiscoveryManager
        from usmsb_sdk.agent_sdk.gene_capsule import GeneCapsuleManager

        discovery = EnhancedDiscoveryManager()

        # 测试按经验发现的方法存在
        assert hasattr(discovery, 'discover_by_experience')
        assert hasattr(discovery, 'get_recommendations_from_history')


# ==================== Integration: WebSocket Notifications ====================

class TestWebSocketNotificationIntegration:
    """Test WebSocket notification integration"""

    @pytest.mark.asyncio
    async def test_negotiation_notification_manager(self):
        """Test negotiation notification manager"""
        from usmsb_sdk.services.negotiation_notifications import (
            NegotiationNotificationManager,
            NotificationType,
        )

        manager = NegotiationNotificationManager()

        # 测试通知类型
        assert NotificationType.QUESTION_ASKED.value == "question_asked"
        assert NotificationType.VERIFICATION_REQUESTED.value == "verification_requested"
        assert NotificationType.MATCH_CONFIRMED.value == "match_confirmed"

    @pytest.mark.asyncio
    async def test_notification_subscriber_management(self):
        """Test notification subscriber management"""
        from usmsb_sdk.services.negotiation_notifications import NegotiationNotificationManager

        manager = NegotiationNotificationManager()

        # 添加订阅者
        await manager.subscribe("agent_001", "negotiation_001")

        # 检查订阅
        subscribers = manager.get_subscribers("negotiation_001")
        assert "agent_001" in subscribers

        # 取消订阅
        await manager.unsubscribe("agent_001", "negotiation_001")
        subscribers = manager.get_subscribers("negotiation_001")
        assert "agent_001" not in subscribers


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
