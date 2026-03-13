"""
Unit Tests for Creative Economy Platform Services

Tests for:
- JointOrderService
- AssetFractionalizationService
- ZKCredentialService
"""

import asyncio
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from usmsb_sdk.services.joint_order_service import (
    JointOrderService,
    Demand,
    OrderPool,
    Bid,
    PoolStatus,
)
from usmsb_sdk.services.asset_fractionalization_service import (
    AssetFractionalizationService,
    AssetInfo,
    AssetStatus,
)
from usmsb_sdk.services.zk_credential_service import (
    ZKCredentialService,
    Credential,
    CredentialType,
    CredentialStatus,
    ZKProof,
    PrivateInputs,
)


class TestJointOrderService:
    """Tests for JointOrderService."""

    @pytest.fixture
    async def service(self):
        """Create service instance."""
        service = JointOrderService()
        await service.start()
        yield service
        await service.stop()

    @pytest.mark.asyncio
    async def test_create_demand(self, service):
        """Test demand creation."""
        demand = await service.create_demand(
            user_id="user-001",
            service_type="web_development",
            budget=1000.0,
            requirements={"language": "Python", "framework": "FastAPI"},
        )

        assert demand.demand_id is not None
        assert demand.user_id == "user-001"
        assert demand.service_type == "web_development"
        assert demand.budget == 1000.0
        assert demand.status == "active"

    @pytest.mark.asyncio
    async def test_create_pool(self, service):
        """Test pool creation."""
        pool = await service.create_pool(
            creator_id="user-001",
            service_type="web_development",
            min_budget=500.0,
        )

        assert pool.pool_id is not None
        assert pool.service_type == "web_development"
        assert pool.status == PoolStatus.CREATED

    @pytest.mark.asyncio
    async def test_join_pool(self, service):
        """Test joining a pool."""
        pool = await service.create_pool(
            creator_id="user-001",
            service_type="web_development",
            min_budget=100.0,
        )

        demand = await service.create_demand(
            user_id="user-002",
            service_type="web_development",
            budget=200.0,
            requirements={"test": "value"},
        )

        result = await service.join_pool(pool.pool_id, demand)
        assert result is True
        assert pool.participant_count == 1
        assert pool.total_budget == 200.0

    @pytest.mark.asyncio
    async def test_submit_bid(self, service):
        """Test bid submission."""
        pool = await service.create_pool(
            creator_id="user-001",
            service_type="web_development",
            min_budget=100.0,
        )

        demand = await service.create_demand(
            user_id="user-002",
            service_type="web_development",
            budget=200.0,
            requirements={},
        )

        await service.join_pool(pool.pool_id, demand)

        bid = await service.submit_bid(
            pool_id=pool.pool_id,
            provider_id="provider-001",
            price=180.0,
            delivery_time_hours=48,
            proposal="I will deliver in 2 days",
        )

        assert bid is not None
        assert bid.price == 180.0
        assert bid.is_winner is False

    @pytest.mark.asyncio
    async def test_award_pool(self, service):
        """Test pool awarding."""
        pool = await service.create_pool(
            creator_id="user-001",
            service_type="web_development",
            min_budget=100.0,
        )

        demand = await service.create_demand(
            user_id="user-002",
            service_type="web_development",
            budget=200.0,
            requirements={},
        )

        await service.join_pool(pool.pool_id, demand)

        await service.submit_bid(
            pool_id=pool.pool_id,
            provider_id="provider-001",
            price=180.0,
            delivery_time_hours=48,
            proposal="Proposal 1",
        )

        winning_bid = await service.award_pool(pool.pool_id)

        assert winning_bid is not None
        assert winning_bid.is_winner is True
        assert pool.status == PoolStatus.AWARDED

    @pytest.mark.asyncio
    async def test_aggregate_demands(self, service):
        """Test demand aggregation."""
        demand1 = await service.create_demand(
            user_id="user-001",
            service_type="design",
            budget=50.0,
            requirements={"type": "logo"},
        )

        pool, is_new = await service.aggregate_demands(demand1)

        assert is_new is True
        assert pool is not None

        demand2 = await service.create_demand(
            user_id="user-002",
            service_type="design",
            budget=40.0,
            requirements={"type": "logo"},
        )

        pool2, is_new2 = await service.aggregate_demands(demand2)

        assert is_new2 is False
        assert pool2.pool_id == pool.pool_id


class TestAssetFractionalizationService:
    """Tests for AssetFractionalizationService."""

    @pytest.fixture
    async def service(self):
        """Create service instance."""
        service = AssetFractionalizationService()
        await service.start()
        yield service
        await service.stop()

    @pytest.mark.asyncio
    async def test_deposit_nft(self, service):
        """Test NFT deposit."""
        asset = await service.deposit_nft(
            nft_contract="0xnft123",
            token_id=1,
            owner="user-001",
            total_shares=1000,
            share_price=10.0,
        )

        assert asset.asset_id is not None
        assert asset.total_shares == 1000
        assert asset.status == AssetStatus.CREATED

    @pytest.mark.asyncio
    async def test_fragment_asset(self, service):
        """Test asset fragmentation."""
        asset = await service.deposit_nft(
            nft_contract="0xnft123",
            token_id=1,
            owner="user-001",
            total_shares=1000,
            share_price=10.0,
        )

        result = await service.fragment_asset(asset.asset_id)
        assert result is True
        assert asset.status == AssetStatus.FRAGMENTED

    @pytest.mark.asyncio
    async def test_purchase_shares(self, service):
        """Test share purchase."""
        asset = await service.deposit_nft(
            nft_contract="0xnft123",
            token_id=1,
            owner="user-001",
            total_shares=1000,
            share_price=10.0,
        )

        await service.fragment_asset(asset.asset_id)

        result = await service.purchase_shares(
            asset_id=asset.asset_id,
            buyer="user-002",
            amount=100,
        )

        assert result is True
        assert asset.shares_sold == 200  # 100 creator + 100 buyer

    @pytest.mark.asyncio
    async def test_distribute_earnings(self, service):
        """Test earnings distribution."""
        asset = await service.deposit_nft(
            nft_contract="0xnft123",
            token_id=1,
            owner="user-001",
            total_shares=1000,
            share_price=10.0,
        )

        await service.fragment_asset(asset.asset_id)
        await service.purchase_shares(asset.asset_id, "user-002", 100)

        result = await service.distribute_earnings(
            asset_id=asset.asset_id,
            amount=1000.0,
        )

        assert result is True
        assert asset.distributed_earnings == 1000.0

    @pytest.mark.asyncio
    async def test_claim_earnings(self, service):
        """Test earnings claiming."""
        asset = await service.deposit_nft(
            nft_contract="0xnft123",
            token_id=1,
            owner="user-001",
            total_shares=1000,
            share_price=10.0,
        )

        await service.fragment_asset(asset.asset_id)
        await service.purchase_shares(asset.asset_id, "user-002", 100)
        await service.distribute_earnings(asset.asset_id, 1000.0)

        earnings = await service.claim_earnings(
            asset_id=asset.asset_id,
            holder="user-002",
        )

        assert earnings > 0


class TestZKCredentialService:
    """Tests for ZKCredentialService."""

    @pytest.fixture
    async def service(self):
        """Create service instance."""
        service = ZKCredentialService()
        await service.start()
        yield service
        await service.stop()

    @pytest.mark.asyncio
    async def test_generate_proof(self, service):
        """Test proof generation."""
        private_inputs = PrivateInputs(
            reputation=0.85,
            stake=10000.0,
            no_slash=True,
            secret=12345,
        )

        proof = await service.generate_proof(
            credential_type=CredentialType.SERVICE_PROVIDER,
            private_inputs=private_inputs,
            thresholds={"reputation": 0.7, "stake": 5000},
        )

        assert proof is not None
        assert proof.a is not None
        assert len(proof.public_inputs) == 4

    @pytest.mark.asyncio
    async def test_issue_credential(self, service):
        """Test credential issuance."""
        private_inputs = PrivateInputs(
            reputation=0.85,
            stake=10000.0,
            no_slash=True,
            secret=12345,
        )

        proof = await service.generate_proof(
            credential_type=CredentialType.SERVICE_PROVIDER,
            private_inputs=private_inputs,
            thresholds={},
        )

        credential = await service.issue_credential(
            holder="user-001",
            credential_type=CredentialType.SERVICE_PROVIDER,
            valid_duration=30 * 86400,
            proof=proof,
            score=0.85,
        )

        assert credential is not None
        assert credential.holder == "user-001"
        assert credential.status == CredentialStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_verify_credential(self, service):
        """Test credential verification."""
        private_inputs = PrivateInputs(
            reputation=0.85,
            stake=10000.0,
            no_slash=True,
            secret=12345,
        )

        proof = await service.generate_proof(
            credential_type=CredentialType.SERVICE_PROVIDER,
            private_inputs=private_inputs,
            thresholds={},
        )

        credential = await service.issue_credential(
            holder="user-001",
            credential_type=CredentialType.SERVICE_PROVIDER,
            valid_duration=30 * 86400,
            proof=proof,
            score=0.85,
        )

        is_valid = await service.verify_credential(
            credential_id=credential.credential_id,
            proof=proof,
        )

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_revoke_credential(self, service):
        """Test credential revocation."""
        private_inputs = PrivateInputs(
            reputation=0.85,
            stake=10000.0,
            no_slash=True,
            secret=12345,
        )

        proof = await service.generate_proof(
            credential_type=CredentialType.SERVICE_PROVIDER,
            private_inputs=private_inputs,
            thresholds={},
        )

        credential = await service.issue_credential(
            holder="user-001",
            credential_type=CredentialType.SERVICE_PROVIDER,
            valid_duration=30 * 86400,
            proof=proof,
            score=0.85,
        )

        result = await service.revoke_credential(
            credential_id=credential.credential_id,
            reason="Policy violation",
        )

        assert result is True
        assert credential.status == CredentialStatus.REVOKED

    @pytest.mark.asyncio
    async def test_has_credential_type(self, service):
        """Test checking credential type."""
        private_inputs = PrivateInputs(
            reputation=0.85,
            stake=10000.0,
            no_slash=True,
            secret=12345,
        )

        proof = await service.generate_proof(
            credential_type=CredentialType.SERVICE_PROVIDER,
            private_inputs=private_inputs,
            thresholds={},
        )

        await service.issue_credential(
            holder="user-001",
            credential_type=CredentialType.SERVICE_PROVIDER,
            valid_duration=30 * 86400,
            proof=proof,
            score=0.85,
        )

        has_cred = service.has_credential_type(
            holder="user-001",
            credential_type=CredentialType.SERVICE_PROVIDER,
        )

        assert has_cred is True

        has_other = service.has_credential_type(
            holder="user-001",
            credential_type=CredentialType.GOVERNANCE,
        )

        assert has_other is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
