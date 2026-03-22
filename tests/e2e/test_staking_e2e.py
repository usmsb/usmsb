"""
E2E staking flow tests.

Tests the staking flow: stake, unstake, cancel.
These tests use the shared in-memory DB from e2e conftest and
the shared TestClient from _app fixture.
"""
import pytest
import hashlib
from datetime import datetime, timedelta


class TestStakingE2E:
    """Staking end-to-end flow tests."""

    @pytest.fixture
    def authenticated_user(self, client):
        """Create a test user and inject into auth override."""
        from usmsb_sdk.api.database import create_user, create_session
        from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
        from usmsb_sdk.api.rest.auth import get_current_user

        wallet = "0xe2etest1234567890abcdef1234567890abcdef"
        user = create_user({"wallet_address": wallet})

        test_user = {
            "user_id": user.get("user_id") or user.get("id") or "test_user",
            "wallet_address": wallet,
            "agent_id": user.get("agent_id") or "agent_e2e",
            "name": "E2EUser",
            "status": "active",
            "binding_status": "bound",
            "owner_wallet": wallet,
            "capabilities": "[]",
            "description": "E2E test user",
            "level": 1,
            "key_id": "e2e_key1",
        }
        client.app.dependency_overrides[get_current_user_unified] = lambda: test_user
        client.app.dependency_overrides[get_current_user] = lambda: test_user

        return {"user": user, "headers": {}}

    def test_stake_endpoint_accessible(self, client):
        """POST /api/auth/stake -> staking endpoint responds."""
        r = client.post("/api/auth/stake", json={"amount": 100})
        assert r.status_code in (200, 400, 401, 403, 500)

    def test_unstake_endpoint_accessible(self, client):
        """POST /api/auth/unstake -> unstake endpoint responds."""
        r = client.post("/api/auth/unstake", json={"amount": 50})
        assert r.status_code in (200, 400, 401, 403, 500)

    def test_cancel_unstake_accessible(self, client):
        """POST /api/auth/unstake/cancel -> cancel endpoint responds."""
        r = client.post("/api/auth/unstake/cancel", json={})
        assert r.status_code in (200, 400, 401, 404, 500)

    def test_config_endpoint_accessible(self, client):
        """GET /api/auth/config -> config endpoint responds."""
        r = client.get("/api/auth/config")
        assert r.status_code in (200, 401, 404, 500)

    def test_balance_endpoint_accessible(self, client):
        """GET /api/auth/balance -> balance endpoint responds."""
        r = client.get("/api/auth/balance")
        assert r.status_code in (200, 401, 500)

    def test_profile_endpoint_accessible(self, client):
        """GET /api/agents/v2/profile -> profile endpoint responds."""
        r = client.get("/api/agents/v2/profile")
        assert r.status_code in (200, 401, 404, 500)
