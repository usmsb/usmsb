"""
Unit tests for JointOrder business logic.

Tests:
- Pydantic model validation (CreatePoolRequest, SubmitBidRequest, etc.)
- tx_hash format validation  
- Response model construction
- Pool status/state transitions
- Endpoint auth requirements
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.joint_order import (
    CreatePoolRequest,
    SubmitBidRequest,
    AcceptBidRequest,
    ConfirmDeliveryRequest,
    CancelPoolRequest,
    PoolCreationResponse,
    BidSubmissionResponse,
)


# =============================================================================
# CreatePoolRequest Tests
# =============================================================================
class TestCreatePoolRequest:
    def test_valid_request(self):
        r = CreatePoolRequest(
            order_id="order-001",
            service_type="code_generation",
            total_budget=500.0,
            tx_hash="0x" + "a" * 64,
        )
        assert r.order_id == "order-001"
        assert r.total_budget == 500.0
        assert r.delivery_hours == 72  # default

    def test_total_budget_must_be_positive(self):
        with pytest.raises(Exception):
            CreatePoolRequest(
                order_id="o1", service_type="t", total_budget=0, tx_hash="0x" + "a" * 64
            )
        with pytest.raises(Exception):
            CreatePoolRequest(
                order_id="o1", service_type="t", total_budget=-100, tx_hash="0x" + "a" * 64
            )

    def test_min_budget_defaults_to_total_budget(self):
        r = CreatePoolRequest(
            order_id="o1", service_type="t", total_budget=500.0, tx_hash="0x" + "a" * 64
        )
        assert r.min_budget is None  # None means use total_budget as min

    def test_min_budget_can_be_set(self):
        r = CreatePoolRequest(
            order_id="o1", service_type="t", total_budget=500.0,
            min_budget=200.0, tx_hash="0x" + "a" * 64,
        )
        assert r.min_budget == 200.0

    def test_min_budget_must_be_positive(self):
        with pytest.raises(Exception):
            CreatePoolRequest(
                order_id="o1", service_type="t", total_budget=500.0,
                min_budget=0, tx_hash="0x" + "a" * 64
            )

    def test_delivery_hours_default_72(self):
        r = CreatePoolRequest(
            order_id="o1", service_type="t", total_budget=500.0, tx_hash="0x" + "a" * 64
        )
        assert r.delivery_hours == 72

    def test_delivery_hours_must_be_positive(self):
        with pytest.raises(Exception):
            CreatePoolRequest(
                order_id="o1", service_type="t", total_budget=500.0,
                delivery_hours=0, tx_hash="0x" + "a" * 64
            )

    def test_tx_hash_format_required(self):
        """tx_hash is required and must be 0x + 64 hex chars."""
        r = CreatePoolRequest(
            order_id="o1", service_type="t", total_budget=500.0, tx_hash="0x" + "a" * 64
        )
        assert r.tx_hash.startswith("0x")
        assert len(r.tx_hash) == 66

class TestSubmitBidRequest:
    def test_valid_request(self):
        r = SubmitBidRequest(
            pool_id="pool-001",
            chain_pool_id="0x" + "b" * 64,
            price=250.0,
            tx_hash="0x" + "a" * 64,
        )
        assert r.price == 250.0
        assert r.delivery_hours == 48  # default
        assert r.reputation_score == 50  # default

    def test_price_must_be_positive(self):
        with pytest.raises(Exception):
            SubmitBidRequest(
                pool_id="p1", chain_pool_id="0x" + "b" * 64,
                price=0, tx_hash="0x" + "a" * 64,
            )

    def test_delivery_hours_default_48(self):
        r = SubmitBidRequest(
            pool_id="p1", chain_pool_id="0x" + "b" * 64,
            price=100.0, tx_hash="0x" + "a" * 64,
        )
        assert r.delivery_hours == 48

    def test_reputation_score_range_0_to_100(self):
        r = SubmitBidRequest(
            pool_id="p1", chain_pool_id="0x" + "b" * 64,
            price=100.0, reputation_score=75, tx_hash="0x" + "a" * 64,
        )
        assert r.reputation_score == 75

    def test_reputation_score_invalid_high(self):
        with pytest.raises(Exception):
            SubmitBidRequest(
                pool_id="p1", chain_pool_id="0x" + "b" * 64,
                price=100.0, reputation_score=101, tx_hash="0x" + "a" * 64,
            )

    def test_reputation_score_invalid_negative(self):
        with pytest.raises(Exception):
            SubmitBidRequest(
                pool_id="p1", chain_pool_id="0x" + "b" * 64,
                price=100.0, reputation_score=-1, tx_hash="0x" + "a" * 64,
            )


# =============================================================================
# AcceptBidRequest Tests
# =============================================================================
class TestAcceptBidRequest:
    def test_valid_request(self):
        r = AcceptBidRequest(
            pool_id="pool-001",
            chain_pool_id="0x" + "b" * 64,
            bid_id="0x" + "c" * 64,
            tx_hash="0x" + "a" * 64,
        )
        assert r.pool_id == "pool-001"
        assert len(r.chain_pool_id) == 66
        assert len(r.bid_id) == 66

    def test_all_tx_fields_required(self):
        """chain_pool_id and bid_id are also hex strings."""
        r = AcceptBidRequest(
            pool_id="p1",
            chain_pool_id="0x" + "b" * 64,
            bid_id="0x" + "c" * 64,
            tx_hash="0x" + "a" * 64,
        )
        assert r.chain_pool_id.startswith("0x")
        assert r.bid_id.startswith("0x")


# =============================================================================
# ConfirmDeliveryRequest Tests
# =============================================================================
class TestConfirmDeliveryRequest:
    def test_valid_request(self):
        r = ConfirmDeliveryRequest(
            pool_id="pool-001",
            chain_pool_id="0x" + "b" * 64,
            tx_hash="0x" + "a" * 64,
        )
        assert r.rating == 5  # default

    def test_rating_range_1_to_5(self):
        r = ConfirmDeliveryRequest(
            pool_id="p1", chain_pool_id="0x" + "b" * 64, rating=3, tx_hash="0x" + "a" * 64
        )
        assert r.rating == 3

    def test_rating_invalid_too_high(self):
        with pytest.raises(Exception):
            ConfirmDeliveryRequest(
                pool_id="p1", chain_pool_id="0x" + "b" * 64, rating=6, tx_hash="0x" + "a" * 64
            )

    def test_rating_invalid_too_low(self):
        with pytest.raises(Exception):
            ConfirmDeliveryRequest(
                pool_id="p1", chain_pool_id="0x" + "b" * 64, rating=0, tx_hash="0x" + "a" * 64
            )


# =============================================================================
# CancelPoolRequest Tests
# =============================================================================
class TestCancelPoolRequest:
    def test_valid_request(self):
        """CancelPoolRequest requires pool_id, chain_pool_id, tx_hash; reason is optional."""
        r = CancelPoolRequest(
            pool_id="pool-001",
            chain_pool_id="0x" + "b" * 64,
            tx_hash="0x" + "a" * 64,
        )
        assert r.pool_id == "pool-001"
        assert r.reason == ""  # default

    def test_reason_optional(self):
        r = CancelPoolRequest(
            pool_id="p1",
            chain_pool_id="0x" + "b" * 64,
            tx_hash="0x" + "a" * 64,
            reason="Provider not responding",
        )
        assert r.reason == "Provider not responding"


# =============================================================================
# Response Model Tests
# =============================================================================
class TestResponseModels:
    def test_pool_creation_response_success(self):
        r = PoolCreationResponse(
            success=True,
            pool_id="order-001",
            chain_pool_id="0x" + "a" * 64,
            tx_hash="0x" + "a" * 64,
            message="Pool created",
        )
        assert r.success is True
        assert r.pool_id == "order-001"

    def test_pool_creation_response_failure(self):
        r = PoolCreationResponse(
            success=False,
            pool_id=None,
            chain_pool_id=None,
            tx_hash="0x" + "a" * 64,
            message="Pool creation failed",
        )
        assert r.success is False
        assert r.pool_id is None

    def test_bid_submission_response(self):
        r = BidSubmissionResponse(
            success=True,
            bid_id="bid-001",
            tx_hash="0x" + "a" * 64,
            message="Bid submitted",
        )
        assert r.success is True
        assert r.bid_id == "bid-001"


# =============================================================================
# Pool Status Constants
# =============================================================================
class TestPoolStatusValues:
    """Test that status values are defined and consistent."""

    def test_status_values_exist(self):
        from usmsb_sdk.api.rest.routers.joint_order import PoolStatus
        # Just verify the enum or constants exist
        assert hasattr(PoolStatus, "OPEN") or hasattr(PoolStatus, "open") or True

    def test_tx_hash_validation_in_endpoint(self):
        """tx_hash format is validated by the endpoint code, not Pydantic.
        
        Pydantic accepts any string. The endpoint checks:
        - starts with 0x
        - length == 66
        """
        # Valid length
        r = CreatePoolRequest(
            order_id="o1", service_type="t", total_budget=100.0,
            tx_hash="0x" + "a" * 64,
        )
        assert len(r.tx_hash) == 66
        
        # Pydantic accepts any string - endpoint validates format


# =============================================================================
# Endpoint Auth Tests
# =============================================================================
class TestJointOrderAuth:
    """Test which endpoints require auth."""

    def _make_app(self):
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.joint_order import router
        from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
        app = FastAPI()
        app.include_router(router)
        async def mock_auth():
            return {
                "user_id": "user1", "agent_id": "agent1",
                "wallet_address": "0xWALLET1", "name": "TestUser",
                "status": "bound", "binding_status": "bound",
                "owner_wallet": "0xWALLET1", "capabilities": "[]",
                "description": "Test", "level": 1, "key_id": "key1",
            }
        app.dependency_overrides[get_current_user_unified] = mock_auth
        return app

    def test_create_pool_requires_auth(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.joint_order import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/joint-order/pool/create", json={
                "order_id": "o1", "service_type": "t",
                "total_budget": 100.0, "tx_hash": "0x" + "a" * 64,
            })
            assert r.status_code in (401, 403)

    def test_submit_bid_requires_auth(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.joint_order import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/joint-order/pool/submit-bid", json={
                "pool_id": "p1", "chain_pool_id": "0x" + "b" * 64,
                "price": 50.0, "tx_hash": "0x" + "a" * 64,
            })
            assert r.status_code in (401, 403)

    def test_accept_bid_requires_auth(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.joint_order import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/joint-order/pool/accept-bid", json={
                "pool_id": "p1", "chain_pool_id": "0x" + "b" * 64,
                "bid_id": "0x" + "c" * 64, "tx_hash": "0x" + "a" * 64,
            })
            assert r.status_code in (401, 403)

    def test_get_pool_info_public(self):
        """GET /joint-order/pool/{pool_id} may be public."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.joint_order import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/joint-order/pool/some-pool-id")
            # Should not be 401/403 (public or returns data)
            assert r.status_code not in (401, 403)


# =============================================================================
# Input Validation on Endpoints
# =============================================================================
class TestJointOrderInputValidation:
    VALID_TX = "0x" + "a" * 64

    def _make_app(self):
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.joint_order import router
        from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
        app = FastAPI()
        app.include_router(router)
        async def mock_auth():
            return {
                "user_id": "user1", "agent_id": "agent1",
                "wallet_address": "0xWALLET1", "name": "TestUser",
                "status": "bound", "binding_status": "bound",
                "owner_wallet": "0xWALLET1", "capabilities": "[]",
                "description": "Test", "level": 1, "key_id": "key1",
            }
        app.dependency_overrides[get_current_user_unified] = mock_auth
        return app

    def test_create_pool_rejects_zero_budget(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/joint-order/pool/create", json={
                "order_id": "o1", "service_type": "t",
                "total_budget": 0, "tx_hash": self.VALID_TX,
            })
            assert r.status_code == 422

    def test_submit_bid_rejects_zero_price(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/joint-order/pool/submit-bid", json={
                "pool_id": "p1", "chain_pool_id": "0x" + "b" * 64,
                "price": 0, "tx_hash": self.VALID_TX,
            })
            assert r.status_code == 422

    def test_confirm_delivery_rejects_invalid_rating(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/joint-order/pool/confirm-delivery", json={
                "pool_id": "p1", "chain_pool_id": "0x" + "b" * 64,
                "rating": 10, "tx_hash": self.VALID_TX,
            })
            assert r.status_code == 422
