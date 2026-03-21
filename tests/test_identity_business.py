"""
Unit tests for Identity business logic.

Tests:
- MintSBTRequest Pydantic model validation
- Identity type enum values
- SBTQueryResponse structure
- Endpoint auth requirements
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.identity import (
    MintSBTRequest,
    MintSBTResponse,
    SBTQueryResponse,
)


# =============================================================================
# MintSBTRequest Tests
# =============================================================================
class TestMintSBTRequest:
    def test_valid_request_ai_agent(self):
        r = MintSBTRequest(
            name="TestAgent",
            agent_address="0x" + "a" * 40,
            identity_type=0,
            tx_hash="0x" + "b" * 64,
        )
        assert r.identity_type == 0
        assert r.agent_address.startswith("0x")

    def test_identity_type_range_0_to_3(self):
        for t in range(4):
            r = MintSBTRequest(
                name="TestAgent",
                agent_address="0x" + "a" * 40,
                identity_type=t,
                tx_hash="0x" + "b" * 64,
            )
            assert r.identity_type == t

    def test_identity_type_4_invalid(self):
        with pytest.raises(Exception):
            MintSBTRequest(
                name="Test",
                agent_address="0x" + "a" * 40,
                identity_type=4,
                tx_hash="0x" + "b" * 64,
            )

    def test_identity_type_negative_invalid(self):
        with pytest.raises(Exception):
            MintSBTRequest(
                name="Test",
                agent_address="0x" + "a" * 40,
                identity_type=-1,
                tx_hash="0x" + "b" * 64,
            )

    def test_agent_address_format(self):
        """agent_address must be 0x + 40 hex chars."""
        r = MintSBTRequest(
            name="TestAgent",
            agent_address="0x" + "c" * 40,
            identity_type=0,
            tx_hash="0x" + "b" * 64,
        )
        assert len(r.agent_address) == 42
        assert r.agent_address.startswith("0x")

    def test_tx_hash_required(self):
        with pytest.raises(Exception):
            MintSBTRequest(
                name="Test",
                agent_address="0x" + "a" * 40,
                identity_type=0,
            )

    def test_default_identity_type(self):
        """identity_type defaults to 0 (AI_AGENT)."""
        r = MintSBTRequest(
            name="TestAgent",
            agent_address="0x" + "a" * 40,
            tx_hash="0x" + "b" * 64,
        )
        assert r.identity_type == 0


# =============================================================================
# MintSBTResponse Tests
# =============================================================================
class TestMintSBTResponse:
    def test_success_response(self):
        r = MintSBTResponse(
            success=True,
            token_id=42,
            tx_hash="0x" + "a" * 64,
            agent_address="0x" + "b" * 40,
            identity_type="AI_AGENT",
            message="SBT minted",
        )
        assert r.success is True
        assert r.token_id == 42

    def test_failure_response(self):
        r = MintSBTResponse(
            success=False,
            token_id=0,
            tx_hash="0x" + "a" * 64,
            agent_address="0x" + "b" * 40,
            identity_type="AI_AGENT",
            message="Failed",
        )
        assert r.success is False


# =============================================================================
# SBTQueryResponse Tests
# =============================================================================
class TestSBTQueryResponse:
    def test_registered_response(self):
        r = SBTQueryResponse(
            address="0x" + "a" * 40,
            is_registered=True,
            token_id=1,
            identity_type="AI_AGENT",
            name="TestAgent",
            metadata="{}",
            registration_time=1700000000,
        )
        assert r.is_registered is True
        assert r.token_id == 1

    def test_unregistered_response(self):
        r = SBTQueryResponse(
            address="0x" + "a" * 40,
            is_registered=False,
            token_id=None,
            identity_type=None,
            name=None,
            metadata=None,
            registration_time=None,
        )
        assert r.is_registered is False
        assert r.token_id is None


# =============================================================================
# Endpoint Auth Tests
# =============================================================================
class TestIdentityAuth:
    """Test identity endpoints require auth."""

    def _make_app(self):
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.identity import router
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

    def test_mint_sbt_requires_auth(self):
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.identity import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/identity/mint-sbt", json={
                "agent_address": "0x" + "a" * 40,
                "identity_type": 0,
                "name": "TestAgent",
                "tx_hash": "0x" + "b" * 64,
            })
            assert r.status_code in (401, 403)

    def test_mint_sbt_accepts_auth(self):
        """With auth, endpoint gets past auth layer."""
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/identity/mint-sbt", json={
                "agent_address": "0x" + "a" * 40,
                "identity_type": 0,
                "name": "TestAgent",
                "tx_hash": "0x" + "b" * 64,
            })
            # Should NOT be 401/403 (passed auth)
            assert r.status_code not in (401, 403)

    def test_get_sbt_public(self):
        """GET /identity/{address}/sbt may be public."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.identity import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/identity/0x" + "a" * 40 + "/sbt")
            assert r.status_code not in (401, 403)


# =============================================================================
# Input Validation on Endpoints
# =============================================================================
class TestIdentityInputValidation:
    def _make_app(self):
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.identity import router
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

    def test_mint_sbt_rejects_invalid_identity_type(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/identity/mint-sbt", json={
                "agent_address": "0x" + "a" * 40,
                "identity_type": 99,
                "tx_hash": "0x" + "b" * 64,
            })
            assert r.status_code == 422

    def test_all_identity_types_accepted(self):
        """All 4 identity types (0-3) are valid input via TestClient."""
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            for t in range(4):
                r = client.post("/identity/mint-sbt", json={
                    "name": "Agent",
                    "agent_address": "0x" + "a" * 40,
                    "identity_type": t,
                    "tx_hash": "0x" + "b" * 64,
                })
                # Should NOT be 422 (Pydantic accepts 0-3)
                if r.status_code == 422:
                    pytest.fail(f"identity_type={t} incorrectly rejected")