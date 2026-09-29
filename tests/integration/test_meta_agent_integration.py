"""Offline integration of MetaAgent, discovery, negotiations and notifications.

Use real services and SQLite; replace only external boundaries and the autonomous
loop. Unexpected network attempts fail even when production catches the error.
"""

import json
import socket
from functools import partial
from types import SimpleNamespace
from unittest.mock import AsyncMock, create_autospec

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(autouse=True)
async def offline_environment(monkeypatch, tmp_path):
    """Install after asyncio creates its own local wakeup sockets."""
    attempts = []

    def reject_network(*args, **kwargs):
        attempts.append((args, kwargs))
        raise AssertionError("Network access is forbidden in MetaAgent integration tests")

    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, reject_network)
    monkeypatch.setattr(socket, "getaddrinfo", reject_network)
    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local_hash")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.chdir(tmp_path)
    yield
    assert attempts == [], "A service attempted network access and swallowed the error"


@pytest.fixture
def integration_config(tmp_path):
    from usmsb_sdk.meta_agent.meta_agent_config import (
        DatabaseConfig,
        LLMConfig,
        MetaAgentConfig,
    )

    return MetaAgentConfig(
        database=DatabaseConfig(path=str(tmp_path / "meta_agent.db")),
        llm=LLMConfig(provider="minimax", api_key=None),
        data_dir=str(tmp_path / "data"),
        guardian_enabled=False,
        smart_recall_enabled=False,
        enable_cognitive_plugins=False,
    )


@pytest.fixture
def service_session_factory(tmp_path):
    """Use actual service schemas and separately owned sessions per test."""
    from usmsb_sdk.api.rest.gene_capsule_service import Base as CapsuleBase
    from usmsb_sdk.services.pre_match_negotiation import Base as NegotiationBase
    from usmsb_sdk.services.schema import Base as ServiceBase

    engine = create_engine(f"sqlite:///{(tmp_path / 'services.db').as_posix()}")
    for base in (ServiceBase, CapsuleBase, NegotiationBase):
        base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    sessions = []

    def create_session():
        session = factory()
        sessions.append(session)
        return session

    try:
        yield create_session
    finally:
        for session in sessions:
            session.close()
        engine.dispose()


@pytest.fixture
def offline_llm_adapter():
    """Keep the real LLMManager API and replace its provider boundary."""
    from usmsb_sdk.intelligence_adapters.llm.minimax_adapter import MiniMaxAdapter

    adapter = create_autospec(MiniMaxAdapter, instance=True)
    adapter.generate_text.return_value = json.dumps({
        "capabilities": ["数据分析"],
        "experiences": [],
        "preferences": {"format": "CSV"},
    })
    adapter.generate_with_system.return_value = "先确认数据质量，再选择分析方法。"
    return adapter


@pytest.fixture
async def meta_agent_instance(
    integration_config, service_session_factory, offline_llm_adapter, monkeypatch, tmp_path
):
    from usmsb_sdk.meta_agent.agent import MetaAgent
    from usmsb_sdk.meta_agent.llm.manager import LLMManager
    from usmsb_sdk.meta_agent.permission import audit_logger
    from usmsb_sdk.meta_agent.services import meta_agent_service as service_module
    from usmsb_sdk.meta_agent.tools import precise_matching
    from usmsb_sdk.services import schema

    async def initialize_offline_provider(manager):
        manager._adapter = offline_llm_adapter

    monkeypatch.setattr(LLMManager, "_init_minimax", initialize_offline_provider)
    monkeypatch.setattr(schema, "create_session", service_session_factory)
    monkeypatch.setattr(
        service_module, "MetaAgentService",
        partial(service_module.MetaAgentService, storage_path=str(tmp_path / "profiles")),
    )
    # Restore both process-global bindings when the test finishes.
    monkeypatch.setattr(precise_matching, "_meta_agent_service", None)
    monkeypatch.setattr(audit_logger, "_audit_logger", None)
    agent = MetaAgent(integration_config)
    monkeypatch.setattr(agent.wallet_manager, "init", AsyncMock())
    monkeypatch.setattr(agent, "_main_loop", AsyncMock())
    try:
        await agent._init_components()
        await agent._register_default_tools()
        # Matching is wired in runtime initialization, not _init_components.
        await agent._start_runtime()
        yield agent
    finally:
        await agent.stop()
        if agent.meta_agent_service is not None:
            await agent.meta_agent_service.shutdown()


@pytest.fixture
def pre_match_service(service_session_factory):
    from usmsb_sdk.services.pre_match_negotiation import PreMatchNegotiationService

    return PreMatchNegotiationService(db_session=service_session_factory())


@pytest.fixture
async def discovery_manager(monkeypatch):
    from usmsb_sdk.agent_sdk.agent_config import AgentConfig
    from usmsb_sdk.agent_sdk.communication import CommunicationManager
    from usmsb_sdk.agent_sdk.discovery import AgentInfo, EnhancedDiscoveryManager

    config = AgentConfig(
        name="OfflineDiscovery", description="Offline integration", agent_id="discovery_001"
    )
    communication = CommunicationManager(config.agent_id, config, AsyncMock())
    manager = EnhancedDiscoveryManager(config.agent_id, config, communication)
    await manager.initialize()
    candidates = [
        AgentInfo(
            agent_id="analysis_expert", name="Analyst", description="数据分析",
            capabilities=[{"name": "数据分析", "level": "expert"}],
            rating=4.8, is_online=True, metadata={"price": 300},
        ),
        AgentInfo(
            agent_id="expensive_analyst", name="Expensive analyst", description="数据分析",
            capabilities=[{"name": "数据分析", "level": "expert"}],
            rating=4.8, is_online=True, metadata={"price": 2000},
        ),
        AgentInfo(
            agent_id="unrelated", name="Designer", description="设计",
            capabilities=[{"name": "设计"}], rating=4.9, is_online=True,
        ),
    ]
    # Only replace transport discovery: filtering, ranking and scoring stay real.
    monkeypatch.setattr(manager, "_discover_platform", AsyncMock(return_value=candidates))
    await manager._update_cache(candidates)
    try:
        yield manager
    finally:
        await manager.close()


class TestMetaAgentGeneCapsuleIntegration:
    @pytest.mark.asyncio
    async def test_meta_agent_service_initialization(self, meta_agent_instance):
        from usmsb_sdk.api.rest.gene_capsule_service import GeneCapsuleStorageService
        from usmsb_sdk.meta_agent.tools import precise_matching

        service = meta_agent_instance.meta_agent_service
        assert service is not None
        assert service._initialized is True
        assert service.meta_agent is meta_agent_instance
        assert isinstance(service.gene_capsule_service, GeneCapsuleStorageService)
        assert precise_matching._get_meta_agent_service() is service
        assert meta_agent_instance.llm_manager.config.api_key is None

    @pytest.mark.asyncio
    async def test_meta_agent_has_precise_matching_tools(self, meta_agent_instance):
        tool_names = {tool["name"] for tool in meta_agent_instance.tool_registry.list_tools()}
        assert {
            "interview_agent", "recommend_agents_for_demand", "match_by_gene_capsule"
        } <= tool_names
        result = await meta_agent_instance.tool_registry.execute(
            "interview_agent", agent_id="tool_agent_001", conversation_type="interview"
        )
        assert result["success"] is True
        conversation = meta_agent_instance.meta_agent_service.get_conversation(
            result["conversation_id"]
        )
        assert conversation.agent_id == "tool_agent_001"
        assert result["opening_message"] == conversation.messages[0].content

    @pytest.mark.asyncio
    async def test_interview_creates_profile(self, meta_agent_instance, offline_llm_adapter):
        service = meta_agent_instance.meta_agent_service
        conversation = await service.initiate_conversation(
            agent_id="integration_agent_001", conversation_type="introduction"
        )
        response = await service.process_agent_message(
            conversation_id=conversation.conversation_id, message="我是一名数据分析专家"
        )
        profile = service.get_agent_profile("integration_agent_001")
        assert profile is not None
        assert profile.conversation_count == 1
        assert profile.core_capabilities == ["数据分析"]
        assert profile.preferences == {"format": "CSV"}
        assert conversation.extracted_capabilities == ["数据分析"]
        assert [message.role for message in conversation.messages] == [
            "meta_agent", "agent", "meta_agent"
        ]
        assert response == conversation.messages[-1].content
        offline_llm_adapter.generate_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_profile_analysis_uses_llm_manager_contract(
        self, meta_agent_instance, offline_llm_adapter
    ):
        service = meta_agent_instance.meta_agent_service
        conversation = await service.initiate_conversation("analysis_agent")
        offline_llm_adapter.generate_text.return_value = json.dumps({
            "core_capabilities": ["统计分析"],
            "skill_domains": ["数据科学"],
            "self_assessed_level": "expert",
            "work_style": {"delivery": "thorough"},
            "meta_agent_assessment": {"overall": 85},
        })
        profile = await service.extract_profile_from_conversation(conversation.conversation_id)
        assert profile.core_capabilities == ["统计分析"]
        assert profile.skill_domains == ["数据科学"]
        assert profile.meta_agent_assessment == {"overall": 85}
        offline_llm_adapter.generate_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_consultation_uses_llm_manager_contract(
        self, meta_agent_instance, offline_llm_adapter
    ):
        response = await meta_agent_instance.meta_agent_service.consult_for_agent(
            "consult_agent", "如何分析数据？"
        )
        assert response == "先确认数据质量，再选择分析方法。"
        offline_llm_adapter.generate_with_system.assert_awaited_once()
        assert offline_llm_adapter.generate_with_system.await_args.kwargs["user_prompt"] == (
            "如何分析数据？"
        )


class TestDiscoveryMatchingIntegration:
    @pytest.mark.asyncio
    async def test_enhanced_discovery_multi_dimensional_search(self, discovery_manager):
        from usmsb_sdk.agent_sdk.discovery import MatchDimension, SearchCriteria

        criteria = SearchCriteria(
            required_capabilities=["数据分析"], min_rating=4.0,
            budget_min=100, budget_max=500, require_online=True,
        )
        results = await discovery_manager.multi_dimensional_search(criteria)
        assert [result.agent.agent_id for result in results] == [
            "analysis_expert", "expensive_analyst"
        ]
        assert results[0].overall_score > results[1].overall_score
        price_scores = [
            next(
                score for score in result.dimension_scores
                if score.dimension == MatchDimension.PRICE
            )
            for result in results
        ]
        assert price_scores[0].details["within_budget"] is True
        assert price_scores[1].details["within_budget"] is False
        assert criteria.to_dict()["budget_max"] == 500

    @pytest.mark.asyncio
    async def test_discovery_filter_creation(self, discovery_manager):
        from usmsb_sdk.agent_sdk.discovery import DiscoveryFilter, DiscoveryScope

        criteria = DiscoveryFilter(
            capabilities=["数据分析"], min_rating=4.0, online_only=True,
            scope=DiscoveryScope.LOCAL, exclude_ids={"expensive_analyst"},
        )
        restored = DiscoveryFilter.from_dict(criteria.to_dict())
        assert restored == criteria
        results = await discovery_manager.discover(restored)
        assert [agent.agent_id for agent in results] == ["analysis_expert"]
        discovery_manager._discover_platform.assert_not_awaited()


class TestPreMatchNegotiationIntegration:
    @pytest.mark.asyncio
    async def test_pre_match_negotiation_flow(self, pre_match_service, service_session_factory):
        from usmsb_sdk.services.pre_match_negotiation import PreMatchNegotiationService

        service = pre_match_service
        negotiation = await service.initiate("demand_001", "supply_001", "demand_req_001")
        negotiation_id = negotiation["negotiation_id"]
        assert negotiation["status"] == "initiated"
        assert negotiation["supply_consent"] is None
        with pytest.raises(PermissionError, match="must consent"):
            await service.ask_question(negotiation_id, "您需要什么样的数据格式？", "demand_001")
        consent = await service.confirm_consent(negotiation_id, "supply_001")
        assert consent["supply_consent"] is True
        qa = await service.ask_question(negotiation_id, "您需要什么样的数据格式？", "demand_001")
        assert qa.question == "您需要什么样的数据格式？"
        answered = await service.answer_question(
            negotiation_id, qa.question_id, "需要 CSV 或 JSON 格式", answerer_id="supply_001"
        )
        assert answered.answer == "需要 CSV 或 JSON 格式"
        assert answered.answerer_id == "supply_001"
        reader = PreMatchNegotiationService(service_session_factory())
        stored = await reader.get_negotiation(negotiation_id)
        assert stored["status"] == "in_progress"
        assert stored["clarification_qa"][0]["answer"] == answered.answer
        assert stored["clarification_qa"][0]["answerer_id"] == "supply_001"

    @pytest.mark.asyncio
    async def test_verification_request_flow(self, pre_match_service, service_session_factory):
        from usmsb_sdk.services.pre_match_negotiation import (
            PreMatchNegotiationService,
            VerificationType,
        )

        service = pre_match_service
        negotiation = await service.initiate("demand_002", "supply_002", "demand_req_002")
        negotiation_id = negotiation["negotiation_id"]
        await service.confirm_consent(negotiation_id, "supply_002")
        request = await service.request_capability_verification(
            negotiation_id=negotiation_id, capability="数据分析",
            verification_type=VerificationType.GENE_CAPSULE,
            request_detail="请展示相关的数据分析经验",
        )
        assert request.verification_type == VerificationType.GENE_CAPSULE
        assert request.status == "pending"
        result = await service.respond_to_verification(
            negotiation_id, request.request_id,
            response="我有3年数据分析经验，完成过20+项目", attachments=["local-evidence-001"],
        )
        assert result.status == "submitted"
        reader = PreMatchNegotiationService(service_session_factory())
        stored = await reader.get_negotiation(negotiation_id)
        verification = stored["capability_verification"]["requests"][0]
        assert verification["request_id"] == request.request_id
        assert verification["status"] == "submitted"
        assert verification["response"] == result.response
        assert verification["response_attachments"] == ["local-evidence-001"]


class TestGeneCapsuleDiscoveryIntegration:
    @pytest.mark.asyncio
    async def test_gene_capsule_experience_discovery(self, discovery_manager):
        from usmsb_sdk.agent_sdk.platform_client import PlatformClient

        client = create_autospec(PlatformClient, instance=True)
        experience = {
            "agent_id": "analysis_expert", "overall_relevance": 0.9,
            "verified_experiences_count": 1,
            "matched_experiences": [
                {"experience": {"outcome": "success", "client_rating": 5}}
            ],
        }
        client.search_agents_by_experience.return_value = SimpleNamespace(
            success=True, data=[experience], error=None
        )
        discovery_manager.platform_client = client
        matches = await discovery_manager.discover_by_experience("数据分析", min_relevance=0.7)
        assert [match.agent.agent_id for match in matches] == ["analysis_expert"]
        assert matches[0].gene_capsule_match == experience
        client.search_agents_by_experience.assert_awaited_once_with(
            task_description="数据分析", min_experience_relevance=0.7, limit=20
        )
        recommendations = await discovery_manager.get_recommendations_from_history("数据分析")
        assert [match.agent.agent_id for match in recommendations] == ["analysis_expert"]
        assert recommendations[0].overall_score == pytest.approx(1.0)


class TestWebSocketNotificationIntegration:
    @pytest.mark.asyncio
    async def test_negotiation_notification_manager(self):
        from usmsb_sdk.services.negotiation_notifications import (
            NegotiationNotificationManager,
            NotificationType,
        )

        manager = NegotiationNotificationManager()
        assert NotificationType.QUESTION_ASKED.value == "question_asked"
        assert NotificationType.VERIFICATION_REQUESTED.value == "verification_requested"
        assert NotificationType.MATCH_CONFIRMED.value == "match_confirmed"
        sent = await manager.send_notification(
            NotificationType.MATCH_CONFIRMED, "negotiation_001", "agent_001"
        )
        assert sent is not None
        pending = await manager.get_pending_notifications("agent_001")
        assert [item["notification_id"] for item in pending] == [sent.notification_id]

    @pytest.mark.asyncio
    async def test_notification_subscriber_management(self):
        from usmsb_sdk.services.negotiation_notifications import (
            NegotiationNotificationManager,
            NotificationType,
        )

        manager = NegotiationNotificationManager()
        await manager.subscribe("agent_001", [NotificationType.QUESTION_ASKED])
        assert manager.is_subscribed("agent_001", NotificationType.QUESTION_ASKED)
        assert not manager.is_subscribed("agent_001", NotificationType.MATCH_CONFIRMED)
        sent = await manager.send_notification(
            NotificationType.QUESTION_ASKED, "negotiation_001", "agent_001"
        )
        assert sent is not None
        await manager.unsubscribe("agent_001", [NotificationType.QUESTION_ASKED])
        assert not manager.is_subscribed("agent_001", NotificationType.QUESTION_ASKED)
        assert await manager.send_notification(
            NotificationType.QUESTION_ASKED, "negotiation_001", "agent_001"
        ) is None
        pending = await manager.get_pending_notifications("agent_001")
        assert len(pending) == 1
        assert pending[0]["notification_id"] == sent.notification_id
