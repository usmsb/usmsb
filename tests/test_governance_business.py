"""
Unit tests for Governance business logic.

Pure unit tests:
- Pydantic model validation
- Auth requirement checks
- db_log_governance_event behavior

Note: Web3-dependent tests (proposal creation, voting) require
BlockchainConfig.from_env which doesn't exist as a classmethod.
These should be integration tests.
"""
import sys, os, time, json, sqlite3, tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.governance import (
    CreateProposalRequest, CastVoteRequest,
)
from usmsb_sdk.api.database import db_log_governance_event


# =============================================================================
# Pydantic Model: CreateProposalRequest
# =============================================================================
class TestCreateProposalRequest:
    def test_valid_request(self):
        r = CreateProposalRequest(
            proposal_type=0, title="Test Proposal",
            description="Test description",
            target="0x" + "0" * 40,
            data="0x", tx_hash="0x" + "a" * 64,
        )
        assert r.proposal_type == 0
        assert r.title == "Test Proposal"
        assert len(r.tx_hash) == 66

    def test_proposal_type_0_to_5_valid(self):
        for t in range(6):
            r = CreateProposalRequest(
                proposal_type=t, title="T", description="D",
                target="0x" + "0" * 40, data="0x",
                tx_hash="0x" + "a" * 64,
            )
            assert r.proposal_type == t

    def test_proposal_type_6_invalid(self):
        with pytest.raises(Exception):
            CreateProposalRequest(proposal_type=6, title="T", description="D",
                target="0x" + "0" * 40, data="0x", tx_hash="0x" + "a" * 64)

    def test_empty_title_invalid(self):
        with pytest.raises(Exception):
            CreateProposalRequest(proposal_type=0, title="", description="D",
                target="0x" + "0" * 40, data="0x", tx_hash="0x" + "a" * 64)

    def test_title_200_chars_ok(self):
        r = CreateProposalRequest(proposal_type=0, title="A" * 200, description="D",
            target="0x" + "0" * 40, data="0x", tx_hash="0x" + "a" * 64)
        assert len(r.title) == 200

    def test_title_201_chars_invalid(self):
        with pytest.raises(Exception):
            CreateProposalRequest(proposal_type=0, title="A" * 201, description="D",
                target="0x" + "0" * 40, data="0x", tx_hash="0x" + "a" * 64)

    def test_empty_description_invalid(self):
        with pytest.raises(Exception):
            CreateProposalRequest(proposal_type=0, title="T", description="",
                target="0x" + "0" * 40, data="0x", tx_hash="0x" + "a" * 64)

    def test_default_data_0x(self):
        r = CreateProposalRequest(proposal_type=0, title="T", description="D",
            target="0x" + "0" * 40, tx_hash="0x" + "a" * 64)
        assert r.data == "0x"


# =============================================================================
# Pydantic Model: CastVoteRequest
# =============================================================================
class TestCastVoteRequest:
    def test_valid_for(self):
        r = CastVoteRequest(proposal_id=1, support=1, tx_hash="0x" + "a" * 64)
        assert r.support == 1

    def test_valid_against(self):
        r = CastVoteRequest(proposal_id=1, support=0, tx_hash="0x" + "a" * 64)
        assert r.support == 0

    def test_valid_abstain(self):
        r = CastVoteRequest(proposal_id=1, support=2, tx_hash="0x" + "a" * 64)
        assert r.support == 2

    def test_support_3_invalid(self):
        with pytest.raises(Exception):
            CastVoteRequest(proposal_id=1, support=3, tx_hash="0x" + "a" * 64)

    def test_support_negative_invalid(self):
        with pytest.raises(Exception):
            CastVoteRequest(proposal_id=1, support=-1, tx_hash="0x" + "a" * 64)


# =============================================================================
# Endpoint Auth Requirements
# =============================================================================
class TestGovernanceAuth:
    """Test which endpoints require auth."""

    def _make_app(self):
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.governance import router
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

    def test_create_proposal_requires_auth(self):
        """POST /governance/proposals requires auth."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.governance import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/governance/proposals", json={
                "proposal_type": 0, "title": "T", "description": "D",
                "target": "0x" + "0" * 40, "data": "0x",
                "tx_hash": "0x" + "a" * 64,
            })
            assert r.status_code in (401, 403)

    def test_vote_requires_auth(self):
        """POST /governance/vote requires auth."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.governance import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/governance/vote", json={
                "proposal_id": 1, "support": 1,
                "tx_hash": "0x" + "a" * 64,
            })
            assert r.status_code in (401, 403)

    def test_list_proposals_no_auth(self):
        """GET /governance/proposals is public (no auth required)."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.governance import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/governance/proposals")
            # Public endpoint - should not return 401/403
            assert r.status_code != 401
            assert r.status_code != 403

    def test_create_proposal_accepts_auth(self):
        """POST /governance/proposals with auth succeeds (gets past auth, may fail on Web3)."""
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/governance/proposals", json={
                "proposal_type": 0, "title": "T", "description": "D",
                "target": "0x" + "0" * 40, "data": "0x",
                "tx_hash": "0x" + "a" * 64,
            })
            # Should NOT be 401/403 (auth passed)
            assert r.status_code not in (401, 403)

    def test_vote_accepts_auth(self):
        """POST /governance/vote with auth succeeds (gets past auth)."""
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/governance/vote", json={
                "proposal_id": 1, "support": 1,
                "tx_hash": "0x" + "a" * 64,
            })
            assert r.status_code not in (401, 403)


# =============================================================================
# Endpoint Input Validation
# =============================================================================
class TestGovernanceInputValidation:
    VALID_TX = "0x" + "a" * 64

    def _make_app(self):
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.governance import router
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

    def test_invalid_support_rejected(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/governance/vote", json={
                "proposal_id": 1, "support": 99, "tx_hash": self.VALID_TX,
            })
            assert r.status_code == 422

    def test_empty_title_rejected(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/governance/proposals", json={
                "proposal_type": 0, "title": "", "description": "D",
                "target": "0x" + "0" * 40, "data": "0x",
                "tx_hash": self.VALID_TX,
            })
            assert r.status_code == 422

    def test_proposal_type_all_valid_values(self):
        """All 6 proposal types (0-5) are valid input."""
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            for t in range(6):
                r = client.post("/governance/proposals", json={
                    "proposal_type": t, "title": f"P{t}",
                    "description": "D", "target": "0x" + "0" * 40,
                    "data": "0x", "tx_hash": self.VALID_TX,
                })
                # Pydantic validation passes for 0-5
                if r.status_code == 422:
                    pytest.fail(f"proposal_type={t} incorrectly rejected by Pydantic")


# =============================================================================
# db_log_governance_event Tests
# =============================================================================


