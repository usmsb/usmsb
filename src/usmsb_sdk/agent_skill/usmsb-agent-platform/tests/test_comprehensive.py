"""
Comprehensive tests for USMSB Agent Platform Skill.

Tests all modules: types, registration, platform APIs.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from usmsb_agent_platform import (
    ActionType,
    PlatformResult,
    StakeTier,
)
from usmsb_agent_platform.intent_parser import IntentParser
from usmsb_agent_platform.stake_checker import StakeChecker
from usmsb_agent_platform.registration import (
    generate_agent_id,
    generate_api_key,
    generate_binding_code,
    hash_api_key,
    RegistrationClient,
    RegistrationResult,
    BindingRequestResult,
    BindingStatus,
    APIKeyInfo,
)
from usmsb_agent_platform.types import (
    Intent,
    PlatformResult,
    StakeInfo,
    WalletInfo,
    ReputationInfo,
    RewardInfo,
    ExperienceGene,
    HeartbeatStatus,
    ErrorCode,
    RetryConfig,
    StakeRequirement,
)
from usmsb_agent_platform.platform import (
    PlatformClient,
    CollaborationAPI,
    MarketplaceAPI,
    DiscoveryAPI,
    NegotiationAPI,
    WorkflowAPI,
    LearningAPI,
    GeneCapsuleAPI,
    PreMatchNegotiationAPI,
    MetaAgentAPI,
    StakingAPI,
    ReputationAPI,
    WalletAPI,
    HeartbeatAPI,
    OrderAPI,
    AgentPlatform,
)


# ==================== Types Tests ====================

class TestActionTypes:
    """Test all ActionType enum values."""

    def test_collaboration_actions(self):
        assert ActionType.COLLABORATION_CREATE.category == "collaboration"
        assert ActionType.COLLABORATION_CREATE.action == "create"
        assert ActionType.COLLABORATION_CREATE.requires_stake is True
        assert ActionType.COLLABORATION_JOIN.requires_stake is False
        assert ActionType.COLLABORATION_CONTRIBUTE.requires_stake is True
        assert ActionType.COLLABORATION_LIST.requires_stake is False

    def test_marketplace_actions(self):
        assert ActionType.MARKETPLACE_PUBLISH_SERVICE.requires_stake is True
        assert ActionType.MARKETPLACE_FIND_WORK.requires_stake is False
        assert ActionType.MARKETPLACE_FIND_WORKERS.requires_stake is False
        assert ActionType.MARKETPLACE_PUBLISH_DEMAND.requires_stake is False
        assert ActionType.MARKETPLACE_HIRE.requires_stake is False

    def test_discovery_actions(self):
        assert ActionType.DISCOVERY_BY_CAPABILITY.requires_stake is False
        assert ActionType.DISCOVERY_BY_SKILL.requires_stake is False
        assert ActionType.DISCOVERY_RECOMMEND.requires_stake is False

    def test_negotiation_actions(self):
        assert ActionType.NEGOTIATION_INITIATE.requires_stake is False
        assert ActionType.NEGOTIATION_ACCEPT.requires_stake is True
        assert ActionType.NEGOTIATION_REJECT.requires_stake is False
        assert ActionType.NEGOTIATION_PROPOSE.requires_stake is False

    def test_workflow_actions(self):
        assert ActionType.WORKFLOW_CREATE.requires_stake is False
        assert ActionType.WORKFLOW_EXECUTE.requires_stake is True
        assert ActionType.WORKFLOW_LIST.requires_stake is False

    def test_learning_actions(self):
        assert ActionType.LEARNING_ANALYZE.requires_stake is False
        assert ActionType.LEARNING_INSIGHTS.requires_stake is False
        assert ActionType.LEARNING_STRATEGY.requires_stake is False
        assert ActionType.LEARNING_MARKET.requires_stake is False

    def test_gene_capsule_actions(self):
        assert ActionType.GENE_ADD_EXPERIENCE.requires_stake is True
        assert ActionType.GENE_UPDATE_VISIBILITY.requires_stake is False
        assert ActionType.GENE_MATCH.requires_stake is False
        assert ActionType.GENE_SHOWCASE.requires_stake is False
        assert ActionType.GENE_GET_CAPSULE.requires_stake is False
        assert ActionType.GENE_VERIFY_EXPERIENCE.requires_stake is False
        assert ActionType.GENE_DESENSITIZE.requires_stake is False

    def test_prematch_actions(self):
        assert ActionType.PREMATCH_INITIATE.requires_stake is False
        assert ActionType.PREMATCH_ASK_QUESTION.requires_stake is False
        assert ActionType.PREMATCH_ANSWER_QUESTION.requires_stake is False
        assert ActionType.PREMATCH_REQUEST_VERIFICATION.requires_stake is False
        assert ActionType.PREMATCH_CONFIRM_SCOPE.requires_stake is False
        assert ActionType.PREMATCH_PROPOSE_TERMS.requires_stake is False
        assert ActionType.PREMATCH_AGREE_TERMS.requires_stake is False
        assert ActionType.PREMATCH_CONFIRM.requires_stake is True
        assert ActionType.PREMATCH_DECLINE.requires_stake is False
        assert ActionType.PREMATCH_CANCEL.requires_stake is False

    def test_meta_agent_actions(self):
        assert ActionType.META_INITIATE_CONVERSATION.requires_stake is False
        assert ActionType.META_CONSULT.requires_stake is False
        assert ActionType.META_GET_PROFILE.requires_stake is False

    def test_staking_actions(self):
        assert ActionType.STAKE_DEPOSIT.requires_stake is False
        assert ActionType.STAKE_WITHDRAW.requires_stake is False


class TestStakeTierValues:
    """Test StakeTier enum values."""

    def test_stake_tier_values(self):
        assert StakeTier.NONE.value == 0
        assert StakeTier.BRONZE.value == 100
        assert StakeTier.SILVER.value == 1000
        assert StakeTier.GOLD.value == 5000
        assert StakeTier.PLATINUM.value == 10000

    def test_stake_tier_from_value(self):
        assert StakeTier(0) == StakeTier.NONE
        assert StakeTier(100) == StakeTier.BRONZE
        assert StakeTier(1000) == StakeTier.SILVER
        assert StakeTier(5000) == StakeTier.GOLD
        assert StakeTier(10000) == StakeTier.PLATINUM


# ==================== Intent Parser Tests ====================

class TestIntentParserBasic:
    """Test Intent Parser with valid inputs."""

    def setup_method(self):
        self.parser = IntentParser()

    def test_parse_collaboration_create(self):
        intent = self.parser.parse("创建协作，目标是开发电商网站")
        assert intent.action == ActionType.COLLABORATION_CREATE
        assert intent.action.requires_stake

    def test_parse_collaboration_join(self):
        intent = self.parser.parse("加入协作 collab-abc123")
        assert intent.action == ActionType.COLLABORATION_JOIN
        assert not intent.action.requires_stake

    def test_parse_marketplace_publish_service(self):
        intent = self.parser.parse("发布服务，Python开发，500 VIBE")
        assert intent.action == ActionType.MARKETPLACE_PUBLISH_SERVICE
        assert intent.action.requires_stake
        assert intent.parameters.get("price") == 500

    def test_parse_find_work(self):
        intent = self.parser.parse("找工作")
        assert intent.action == ActionType.MARKETPLACE_FIND_WORK

    def test_parse_negotiation_initiate(self):
        intent = self.parser.parse("initiate negotiation with agent_456")
        assert intent.action == ActionType.NEGOTIATION_INITIATE

    def test_parse_negotiation_accept(self):
        intent = self.parser.parse("accept negotiation")
        assert intent.action == ActionType.NEGOTIATION_ACCEPT


# ==================== Registration Tests ====================

class TestRegistrationFunctions:
    """Test registration module functions."""

    def test_generate_agent_id_format(self):
        agent_id = generate_agent_id()
        assert isinstance(agent_id, str)
        assert len(agent_id) > 0

    def test_generate_api_key_format(self):
        api_key = generate_api_key("test_agent")
        assert isinstance(api_key, str)
        assert len(api_key) > 20
        assert api_key.startswith("usmsb_")

    def test_generate_api_key_with_timestamp(self):
        api_key1 = generate_api_key("test_agent", timestamp=1000)
        api_key2 = generate_api_key("test_agent", timestamp=2000)
        assert api_key1 != api_key2

    def test_generate_binding_code(self):
        code, expires_at = generate_binding_code()
        assert isinstance(code, str)
        assert len(code) > 0
        assert isinstance(expires_at, int)
        assert expires_at > 0

    def test_hash_api_key(self):
        api_key = "usmsb_test_key_12345"
        hashed = hash_api_key(api_key)
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != api_key


class TestRegistrationResult:
    """Test RegistrationResult class."""

    def test_registration_result_success(self):
        result = RegistrationResult(
            success=True,
            agent_id="agent_123",
            api_key="usmsb_key",
            message="Registration successful"
        )
        assert result.success is True
        assert result.agent_id == "agent_123"
        d = result.to_dict()
        assert d["success"] is True

    def test_registration_result_failure(self):
        result = RegistrationResult(
            success=False,
            agent_id="",
            api_key="",
            message="Registration failed"
        )
        assert result.success is False


class TestBindingRequestResult:
    """Test BindingRequestResult class."""

    def test_binding_request_result(self):
        result = BindingRequestResult(
            success=True,
            binding_code="ABC123",
            expires_at=9999999999
        )
        assert result.success is True
        assert result.binding_code == "ABC123"


# ==================== Platform APIs Tests ====================

class TestPlatformClient:
    """Test PlatformClient class."""

    def test_platform_client_init(self):
        client = PlatformClient(
            base_url="http://localhost:8000",
            api_key="test_key",
            agent_id="agent_123"
        )
        assert client.base_url == "http://localhost:8000"
        assert client.api_key == "test_key"
        assert client.agent_id == "agent_123"

    def test_platform_client_has_api_handlers(self):
        client = PlatformClient(
            base_url="http://localhost:8000",
            api_key="test_key",
            agent_id="agent_123"
        )
        assert hasattr(client, 'collaboration')
        assert hasattr(client, 'marketplace')
        assert hasattr(client, 'discovery')
        assert hasattr(client, 'negotiation')
        assert hasattr(client, 'workflow')
        assert hasattr(client, 'learning')
        assert hasattr(client, 'gene_capsule')
        assert hasattr(client, 'prematch')
        assert hasattr(client, 'staking')
        assert hasattr(client, 'reputation')
        assert hasattr(client, 'wallet')
        assert hasattr(client, 'heartbeat')
        assert hasattr(client, 'order')


class TestCollaborationAPI:
    """Test CollaborationAPI class."""

    @pytest.mark.asyncio
    async def test_collaboration_api_create(self):
        client = PlatformClient(
            base_url="http://localhost:8000",
            api_key="test_key",
            agent_id="agent_123"
        )
        api = CollaborationAPI(client)

        with patch.object(client, '_request_with_retry', return_value={"session_id": "collab_123"}):
            result = await api.create(goal="Build website")
            assert result["session_id"] == "collab_123"

        await client.close()

    @pytest.mark.asyncio
    async def test_collaboration_api_join(self):
        client = PlatformClient(
            base_url="http://localhost:8000",
            api_key="test_key",
            agent_id="agent_123"
        )
        api = CollaborationAPI(client)

        with patch.object(client, '_request_with_retry', return_value={"status": "joined"}):
            result = await api.join(collab_id="collab_123")
            assert result["status"] == "joined"

        await client.close()


class TestMarketplaceAPI:
    """Test MarketplaceAPI class."""

    @pytest.mark.asyncio
    async def test_publish_service(self):
        client = PlatformClient(
            base_url="http://localhost:8000",
            api_key="test_key",
            agent_id="agent_123"
        )
        api = MarketplaceAPI(client)

        with patch.object(client, '_request_with_retry', return_value={"service_id": "svc_123"}):
            result = await api.publish_service(
                service_name="Python Dev",
                price=500,
                skills=["python", "django"]
            )
            assert result["service_id"] == "svc_123"

        await client.close()


class TestDiscoveryAPI:
    """Test DiscoveryAPI class."""

    @pytest.mark.asyncio
    async def test_by_capability(self):
        client = PlatformClient(
            base_url="http://localhost:8000",
            api_key="test_key",
            agent_id="agent_123"
        )
        api = DiscoveryAPI(client)

        with patch.object(client, '_request_with_retry', return_value={"agents": []}):
            result = await api.by_capability(capability="web development")
            assert "agents" in result

        await client.close()


class TestNegotiationAPI:
    """Test NegotiationAPI class."""

    @pytest.mark.asyncio
    async def test_initiate(self):
        client = PlatformClient(
            base_url="http://localhost:8000",
            api_key="test_key",
            agent_id="agent_123"
        )
        api = NegotiationAPI(client)

        with patch.object(client, '_request_with_retry', return_value={"negotiation_id": "neg_123"}):
            result = await api.initiate(target_agent="agent_456")
            assert result["negotiation_id"] == "neg_123"

        await client.close()


class TestWorkflowAPI:
    """Test WorkflowAPI class."""

    @pytest.mark.asyncio
    async def test_create(self):
        client = PlatformClient(
            base_url="http://localhost:8000",
            api_key="test_key",
            agent_id="agent_123"
        )
        api = WorkflowAPI(client)

        with patch.object(client, '_request_with_retry', return_value={"workflow_id": "wf_123"}):
            result = await api.create(name="Data Pipeline", steps=["extract", "load"])
            assert result["workflow_id"] == "wf_123"

        await client.close()


class TestGeneCapsuleAPI:
    """Test GeneCapsuleAPI class."""

    @pytest.mark.asyncio
    async def test_add_experience(self):
        client = PlatformClient(
            base_url="http://localhost:8000",
            api_key="test_key",
            agent_id="agent_123"
        )
        api = GeneCapsuleAPI(client)

        with patch.object(client, '_request_with_retry', return_value={"gene_id": "gene_123"}):
            result = await api.add_experience(
                task_type="数据分析",
                outcome="success",
                quality_score=0.9
            )
            assert result["gene_id"] == "gene_123"

        await client.close()


class TestPreMatchNegotiationAPI:
    """Test PreMatchNegotiationAPI class."""

    @pytest.mark.asyncio
    async def test_initiate(self):
        client = PlatformClient(
            base_url="http://localhost:8000",
            api_key="test_key",
            agent_id="agent_123"
        )
        api = PreMatchNegotiationAPI(client)

        with patch.object(client, '_request_with_retry', return_value={"negotiation_id": "pre_123"}):
            result = await api.initiate(counterparty="agent_789")
            assert result["negotiation_id"] == "pre_123"

        await client.close()


class TestMetaAgentAPI:
    """Test MetaAgentAPI class."""

    def test_meta_agent_api_exists(self):
        client = PlatformClient(
            base_url="http://localhost:8000",
            api_key="test_key",
            agent_id="agent_123"
        )
        api = MetaAgentAPI(client)
        # Just verify the API object exists and has the client reference
        assert api.client is not None


class TestStakingAPI:
    """Test StakingAPI class."""

    @pytest.mark.asyncio
    async def test_deposit(self):
        client = PlatformClient(
            base_url="http://localhost:8000",
            api_key="test_key",
            agent_id="agent_123"
        )
        api = StakingAPI(client)

        with patch.object(client, '_request_with_retry', return_value={"status": "deposited"}):
            result = await api.deposit(amount=1000)
            assert result["status"] == "deposited"

        await client.close()


class TestOrderAPI:
    """Test OrderAPI class."""

    @pytest.mark.asyncio
    async def test_create(self):
        client = PlatformClient(
            base_url="http://localhost:8000",
            api_key="test_key",
            agent_id="agent_123"
        )
        api = OrderAPI(client)

        with patch.object(client, '_request_with_retry', return_value={"order_id": "order_123"}):
            result = await api.create(
                title="Test Order",
                description="Test description",
                price=100
            )
            assert result["order_id"] == "order_123"

        await client.close()


# ==================== Stake Checker Tests ====================

class TestStakeChecker:
    """Test StakeChecker class."""

    def setup_method(self):
        self.checker = StakeChecker()

    def test_get_tier(self):
        assert self.checker.get_tier(0) == StakeTier.NONE
        assert self.checker.get_tier(100) == StakeTier.BRONZE
        assert self.checker.get_tier(1000) == StakeTier.SILVER
        assert self.checker.get_tier(5000) == StakeTier.GOLD
        assert self.checker.get_tier(10000) == StakeTier.PLATINUM

    def test_get_discount(self):
        assert self.checker.get_discount(StakeTier.NONE) == 0
        assert self.checker.get_discount(StakeTier.SILVER) == 5
        assert self.checker.get_discount(StakeTier.GOLD) == 10
        assert self.checker.get_discount(StakeTier.PLATINUM) == 20


# ==================== Data Types Tests ====================

class TestRetryConfig:
    """Test RetryConfig."""

    def test_retry_config_defaults(self):
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.retry_delay == 1.0

    def test_retry_config_custom(self):
        config = RetryConfig(max_retries=5, retry_delay=2.0)
        assert config.max_retries == 5
        assert config.retry_delay == 2.0


class TestErrorCode:
    """Test ErrorCode enum."""

    def test_error_codes_exist(self):
        # ErrorCode is an Enum-like class with error codes
        assert ErrorCode is not None


# ==================== AgentPlatform Tests ====================

class TestAgentPlatform:
    """Test AgentPlatform main class."""

    def test_agent_platform_init(self):
        platform = AgentPlatform(
            base_url="http://localhost:8000",
            api_key="test_key",
            agent_id="agent_123"
        )
        assert platform.base_url == "http://localhost:8000"
        assert platform.base_url == "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_agent_platform_close(self):
        platform = AgentPlatform(
            base_url="http://localhost:8000",
            api_key="test_key",
            agent_id="agent_123"
        )
        # Should not raise
        await platform.close()
