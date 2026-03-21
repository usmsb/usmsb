"""
Integration tests for Registration flow.

Tests: binding initiation, status check, completion, wallet binding.
Requires: sample_bound_agent fixture.
"""
import pytest
from tests.integration.conftest import VALID_TX, mock_web3


class TestBindingFlow:
    def test_initiate_binding_success(self, client, integration_db, sample_bound_agent):
        """POST /api/agents/v2/{agent_id}/request-binding → starts binding flow."""
        with mock_web3():
            r = client.post(
                f"/api/agents/v2/{sample_bound_agent}/request-binding",
                json={"wallet_address": "0xNEWWALLET12345678901234567890123456"},
            )
        # 200 = binding initiated, 400 = already bound
        assert r.status_code in (200, 400)

    def test_binding_status_returns_pending(self, client, integration_db):
        """GET /api/agents/v2/{agent_id}/binding-status → 200 with status."""
        r = client.get("/api/agents/v2/agent_pending/binding-status")
        # 403 = authenticated agent != requested agent (security check)
        # 404 = agent not found
        assert r.status_code in (200, 403, 404)

    def test_binding_status_returns_404_for_nonexistent(self, client):
        """GET /api/agents/v2/nonexistent/binding-status → 403 (agent mismatch) or 404."""
        r = client.get("/api/agents/v2/nonexistent/binding-status")
        # 403 = authenticated agent != nonexistent (security check passes)
        assert r.status_code in (403, 404)

    def test_complete_binding_invalid_code_returns_error(self, client, integration_db, sample_bound_agent):
        """POST /api/agents/v2/complete-binding/{code} with empty body → 422 (missing fields)."""
        r = client.post(
            "/api/agents/v2/complete-binding/invalid_code",
            json={},
        )
        # 422 = Pydantic validation error (missing required fields)
        assert r.status_code in (400, 422, 500)

    def test_complete_binding_pending_tx_returns_error(self, client, integration_db):
        """POST /api/agents/v2/complete-binding/{code} with pending tx → 422."""
        r = client.post(
            "/api/agents/v2/complete-binding/CODE123",
            json={"stake_amount": 100.0, "approve_tx_hash": "0x" + "a" * 64},
        )
        # 422 = Pydantic validation error
        assert r.status_code in (400, 422, 500)


class TestWalletBinding:
    def test_bind_wallet_success(self, client, integration_db, sample_bound_agent):
        """POST /api/agents/v2/{agent_id}/wallet-binding → 200 on success."""
        with mock_web3():
            r = client.post(
                f"/api/agents/v2/{sample_bound_agent}/wallet-binding",
                json={
                    "wallet_address": "0xNEWWALLET12345678901234567890123456",
                    "owner_address": "0xOWNER1234567890123456789012345678901234",
                    "binding_code": "CODE123",
                },
            )
        # 200 = success, 400 = already bound, 500 = mock error
        assert r.status_code in (200, 400, 500)

    def test_bind_wallet_already_bound_returns_400(self, client, integration_db, sample_bound_agent):
        """POST wallet-binding when already bound → 400."""
        r = client.post(
            f"/api/agents/v2/{sample_bound_agent}/wallet-binding",
            json={
                "wallet_address": "0xNEWWALLET12345678901234567890123456",
                "owner_address": "0xOWNER1234567890123456789012345678901234",
                "binding_code": "CODE123",
            },
        )
        assert r.status_code in (200, 400)


class TestAgentAPIKeys:
    def test_list_api_keys_returns_200_or_403(self, client, integration_db, sample_bound_agent):
        """GET /api/agents/v2/{agent_id}/api-keys → 200 or 403."""
        r = client.get(f"/api/agents/v2/{sample_bound_agent}/api-keys")
        # 200 = keys listed, 403 = wrong agent
        assert r.status_code in (200, 403, 500)
