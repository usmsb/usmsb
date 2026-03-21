"""
Unit tests for Registration business logic.

Tests:
- Pydantic models: SelfRegistrationRequest, CompleteBindingRequest, AgentRegistrationRequest
- check_agent_or_owner_access function
- Binding status endpoint
- Complete binding validation
"""
import sys, time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.registration import (
    check_agent_or_owner_access,
)
from usmsb_sdk.api.rest.routers.staking import MIN_STAKE_AMOUNT


# =============================================================================
# check_agent_or_owner_access Tests
# =============================================================================
class TestCheckAgentOrOwnerAccess:
    def test_owner_can_access_own_agent(self):
        from fastapi import HTTPException
        user = {
            "user_id": "user1",
            "wallet_address": "0xAAA",
            "owner_wallet": "0xAAA",
            "agent_id": "agent1",
            "status": "bound",
        }
        check_agent_or_owner_access(user, "agent1")  # no raise

    def test_cannot_access_other_agent(self):
        from fastapi import HTTPException
        user = {
            "user_id": "user1",
            "wallet_address": "0xAAA",
            "owner_wallet": "0xAAA",
            "agent_id": "agent1",
            "status": "bound",
        }
        with pytest.raises(HTTPException) as exc:
            check_agent_or_owner_access(user, "other_agent")
        assert exc.value.status_code == 403

    def test_no_wallet_raises_403(self):
        from fastapi import HTTPException
        user = {"user_id": "user1"}
        with pytest.raises(HTTPException) as exc:
            check_agent_or_owner_access(user, "agent1")
        assert exc.value.status_code == 403


# =============================================================================
# CompleteBindingRequest Tests
# =============================================================================
class TestCompleteBindingRequest:
    """CompleteBindingRequest requires stake_amount, approve_tx_hash, stake_tx_hash."""

    def _make_req(self, **kwargs):
        defaults = {
            "stake_amount": 1000.0,
            "approve_tx_hash": "0x" + "a" * 64,
            "stake_tx_hash": "0x" + "b" * 64,
        }
        defaults.update(kwargs)
        from usmsb_sdk.api.rest.routers.registration import CompleteBindingRequest
        return CompleteBindingRequest(**defaults)

    def test_valid_request(self):
        r = self._make_req()
        assert r.stake_amount == 1000.0
        assert len(r.approve_tx_hash) == 66
        assert len(r.stake_tx_hash) == 66

    def test_approve_tx_hash_required(self):
        from usmsb_sdk.api.rest.routers.registration import CompleteBindingRequest
        with pytest.raises(Exception):
            CompleteBindingRequest(
                stake_amount=1000.0,
                stake_tx_hash="0x" + "b" * 64,
            )

    def test_stake_tx_hash_required(self):
        from usmsb_sdk.api.rest.routers.registration import CompleteBindingRequest
        with pytest.raises(Exception):
            CompleteBindingRequest(
                stake_amount=1000.0,
                approve_tx_hash="0x" + "a" * 64,
            )


# =============================================================================
# Binding Status Endpoint Tests
# =============================================================================
class TestBindingStatusEndpoint:
    MOCK_USER = {
        "user_id": "user1", "agent_id": "agent1",
        "wallet_address": "0xWALLET1", "name": "TestUser",
        "status": "bound", "binding_status": "bound",
        "owner_wallet": "0xWALLET1", "capabilities": "[]",
        "description": "Test", "level": 1, "key_id": "key1",
        "stake_tier": "BRONZE", "staked_amount": 100.0,
    }

    def _make_app(self):
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.registration import router
        from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
        app = FastAPI()
        app.include_router(router)
        async def mock_auth():
            return self.MOCK_USER
        app.dependency_overrides[get_current_user_unified] = mock_auth
        return app

    def test_auth_access_own_agent_returns_200(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with patch('usmsb_sdk.api.rest.routers.registration.db_get_binding_request_by_agent') as mock_db:
            mock_db.return_value = None
            with TestClient(app) as client:
                r = client.get("/agents/v2/agent1/binding-status")
                assert r.status_code == 200
                assert r.json()["bound"] is True

    def test_no_pending_request_returns_null(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with patch('usmsb_sdk.api.rest.routers.registration.db_get_binding_request_by_agent') as mock_db:
            mock_db.return_value = None
            with TestClient(app) as client:
                r = client.get("/agents/v2/agent1/binding-status")
                assert r.status_code == 200
                assert r.json()["pending_request"] is None

    def test_pending_request_included_when_pending(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        mock_pending = {
            "binding_code": "ABC123",
            "binding_url": "https://example.com/bind/ABC123",
            "expires_at": time.time() + 3600,
            "status": "pending",
        }
        with patch('usmsb_sdk.api.rest.routers.registration.db_get_binding_request_by_agent') as mock_db:
            mock_db.return_value = mock_pending
            with TestClient(app) as client:
                r = client.get("/agents/v2/agent1/binding-status")
                assert r.status_code == 200
                assert r.json()["pending_request"]["binding_code"] == "ABC123"

    def test_access_other_agent_returns_403(self):
        """User cannot query binding status for a different agent."""
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.get("/agents/v2/other_agent/binding-status")
            assert r.status_code == 403


# =============================================================================
# Complete Binding Endpoint Tests
# =============================================================================
class TestCompleteBindingEndpoint:
    MOCK_USER = {
        "user_id": "user1", "agent_id": "agent1",
        "wallet_address": "0xWALLET1", "name": "TestUser",
        "status": "bound", "binding_status": "bound",
        "owner_wallet": "0xWALLET1", "capabilities": "[]",
        "description": "Test", "level": 1, "key_id": "key1",
    }

    def _make_app(self):
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.registration import router
        from usmsb_sdk.api.rest.auth import get_current_user
        app = FastAPI()
        app.include_router(router)
        async def mock_auth():
            return self.MOCK_USER
        app.dependency_overrides[get_current_user] = mock_auth
        return app

    def test_invalid_binding_code_returns_404(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with patch('usmsb_sdk.api.rest.routers.registration.db_get_binding_request_by_code') as mock_db:
            mock_db.return_value = None
            with TestClient(app) as client:
                r = client.post(
                    "/agents/v2/complete-binding/invalidcode",
                    json={
                        "stake_amount": 1000.0,
                        "approve_tx_hash": "0x" + "a" * 64,
                        "stake_tx_hash": "0x" + "b" * 64,
                    }
                )
                assert r.status_code == 404

    def test_expired_binding_returns_400(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        expired_binding = {
            "binding_code": "EXPIRED",
            "agent_id": "agent1",
            "status": "pending",
            "expires_at": time.time() - 3600,
        }
        with patch('usmsb_sdk.api.rest.routers.registration.db_get_binding_request_by_code') as mock_db:
            mock_db.return_value = expired_binding
            with TestClient(app) as client:
                r = client.post(
                    "/agents/v2/complete-binding/EXPIRED",
                    json={
                        "stake_amount": 1000.0,
                        "approve_tx_hash": "0x" + "a" * 64,
                        "stake_tx_hash": "0x" + "b" * 64,
                    }
                )
                assert r.status_code == 400
                assert "expired" in r.json()["detail"]["error"].lower()

    def test_already_completed_returns_400(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        completed_binding = {
            "binding_code": "DONE",
            "agent_id": "agent1",
            "status": "completed",
            "expires_at": time.time() + 3600,
        }
        with patch('usmsb_sdk.api.rest.routers.registration.db_get_binding_request_by_code') as mock_db:
            mock_db.return_value = completed_binding
            with TestClient(app) as client:
                r = client.post(
                    "/agents/v2/complete-binding/DONE",
                    json={
                        "stake_amount": 1000.0,
                        "approve_tx_hash": "0x" + "a" * 64,
                        "stake_tx_hash": "0x" + "b" * 64,
                    }
                )
                assert r.status_code == 400
                assert "already" in r.json()["detail"]["error"].lower()
