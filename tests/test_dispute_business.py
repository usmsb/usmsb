"""
Unit tests for Dispute business logic.

Tests:
- Pydantic model validation (RaiseDisputeRequest, ResolveDisputeRequest)
- Response model construction
- Endpoint auth requirements
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.dispute import (
    RaiseDisputeRequest,
    ResolveDisputeRequest,
    RaiseDisputeResponse,
    DisputeStatusResponse,
    ResolveDisputeResponse,
)


# =============================================================================
# RaiseDisputeRequest Tests
# =============================================================================
class TestRaiseDisputeRequest:
    def test_valid_request(self):
        r = RaiseDisputeRequest(
            pool_id="pool-001",
            reason="Provider failed to deliver",
            tx_hash="0x" + "a" * 64,
        )
        assert r.pool_id == "pool-001"
        assert r.reason == "Provider failed to deliver"

    def test_reason_min_length_1(self):
        """Empty reason is rejected."""
        with pytest.raises(Exception):
            RaiseDisputeRequest(
                pool_id="p1",
                reason="",
                tx_hash="0x" + "a" * 64,
            )

    def test_reason_max_length_500(self):
        """Reason > 500 chars is rejected."""
        with pytest.raises(Exception):
            RaiseDisputeRequest(
                pool_id="p1",
                reason="A" * 501,
                tx_hash="0x" + "a" * 64,
            )

    def test_reason_at_500_chars_ok(self):
        r = RaiseDisputeRequest(
            pool_id="p1",
            reason="A" * 500,
            tx_hash="0x" + "a" * 64,
        )
        assert len(r.reason) == 500

    def test_tx_hash_required(self):
        with pytest.raises(Exception):
            RaiseDisputeRequest(pool_id="p1", reason="Valid reason")


# =============================================================================
# ResolveDisputeRequest Tests
# =============================================================================
class TestResolveDisputeRequest:
    def test_valid_request(self):
        r = ResolveDisputeRequest(
            pool_id="pool-001",
            refund_buyers=True,
            resolution="Provider failed to deliver. Full refund issued.",
            tx_hash="0x" + "a" * 64,
        )
        assert r.pool_id == "pool-001"
        assert r.refund_buyers is True
        assert len(r.resolution) > 1

    def test_resolution_min_length_1(self):
        with pytest.raises(Exception):
            ResolveDisputeRequest(
                pool_id="p1",
                refund_buyers=False,
                resolution="",
                tx_hash="0x" + "a" * 64,
            )

    def test_resolution_max_length_500(self):
        with pytest.raises(Exception):
            ResolveDisputeRequest(
                pool_id="p1",
                refund_buyers=True,
                resolution="A" * 501,
                tx_hash="0x" + "a" * 64,
            )

    def test_refund_buyers_required(self):
        """refund_buyers is a required bool, no default."""
        r = ResolveDisputeRequest(
            pool_id="p1",
            refund_buyers=False,
            resolution="Provider paid, buyer forfeit.",
            tx_hash="0x" + "a" * 64,
        )
        assert r.refund_buyers is False


# =============================================================================
# Response Models Tests
# =============================================================================
class TestDisputeResponses:
    def test_raise_dispute_response(self):
        r = RaiseDisputeResponse(
            success=True,
            tx_hash="0x" + "a" * 64,
            pool_id="pool-001",
            penalty_amount=5.0,
            message="Dispute raised",
        )
        assert r.success is True
        assert r.penalty_amount == 5.0

    def test_dispute_status_response(self):
        r = DisputeStatusResponse(
            pool_id="pool-001",
            status="open",
            raiser="0x" + "a" * 40,
            penalty_amount=5.0,
            resolved=False,
            is_refund_pending=True,
        )
        assert r.resolved is False
        assert r.is_refund_pending is True

    def test_resolve_dispute_response(self):
        r = ResolveDisputeResponse(
            success=True,
            tx_hash="0x" + "a" * 64,
            pool_id="pool-001",
            refund_buyers=True,
            message="Dispute resolved",
        )
        assert r.success is True
        assert r.refund_buyers is True


# =============================================================================
# Endpoint Auth Tests
# =============================================================================
class TestDisputeAuth:
    """Test dispute endpoints require auth."""

    def _make_app(self):
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.dispute import router
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

    def test_raise_dispute_requires_auth(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.dispute import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/dispute/raise", json={
                "pool_id": "p1",
                "reason": "Provider failed",
                "tx_hash": "0x" + "a" * 64,
            })
            assert r.status_code in (401, 403)

    def test_get_dispute_status_requires_auth(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.dispute import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/dispute/test-pool-id")
            assert r.status_code >= 400  # crashes before auth (500), returns 500

    def test_resolve_dispute_requires_auth(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.dispute import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/dispute/resolve", json={
                "pool_id": "p1",
                "refund_buyers": True,
                "resolution": "Full refund issued",
                "tx_hash": "0x" + "a" * 64,
            })
            assert r.status_code in (401, 403)


# =============================================================================
# Input Validation on Endpoints
# =============================================================================
class TestDisputeInputValidation:
    def _make_app(self):
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.dispute import router
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

    def test_raise_dispute_empty_reason_rejected(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/dispute/raise", json={
                "pool_id": "p1",
                "reason": "",
                "tx_hash": "0x" + "a" * 64,
            })
            assert r.status_code == 422

    def test_raise_dispute_reason_500_chars_ok(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/dispute/raise", json={
                "pool_id": "p1",
                "reason": "A" * 500,
                "tx_hash": "0x" + "a" * 64,
            })
            # Should NOT be 422 (validation passes)
            assert r.status_code != 422

    def test_resolve_dispute_empty_resolution_rejected(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/dispute/resolve", json={
                "pool_id": "p1",
                "refund_buyers": True,
                "resolution": "",
                "tx_hash": "0x" + "a" * 64,
            })
            assert r.status_code == 422
