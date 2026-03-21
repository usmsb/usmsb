"""
Integration tests: /api/identity/* endpoints.
"""
import pytest
from tests.integration.conftest import mock_web3, mock_web3_not_found, mock_web3_failed, VALID_TX


class TestIdentityMintSBT:
    """POST /api/identity/mint-sbt"""

    def test_mint_sbt_success(self, client, integration_db, sample_bound_agent):
        """Valid SBT minting tx → 200."""
        with mock_web3(status=1, from_addr="0xBOUNDAGENT"):
            response = client.post("/api/identity/mint-sbt", json={
                "agent_address": "0xBOUNDAGENT12345678901234567890123456789",
                "name": "TestSoul",
                "tx_hash": VALID_TX,
            })
        assert response.status_code == 200, \
            f"{response.status_code}: {response.json()}"

    def test_mint_sbt_rejects_failed_tx(self, client, integration_db, sample_bound_agent):
        """Failed tx → 400/500."""
        with mock_web3_failed():
            response = client.post("/api/identity/mint-sbt", json={
                "agent_address": "0xBOUNDAGENT12345678901234567890123456789",
                "name": "TestSoul",
                "tx_hash": VALID_TX,
            })
        assert response.status_code in (400, 500)

    def test_mint_sbt_rejects_pending_tx(self, client, integration_db, sample_bound_agent):
        """Pending tx → 400/404."""
        with mock_web3_not_found():
            response = client.post("/api/identity/mint-sbt", json={
                "agent_address": "0xBOUNDAGENT12345678901234567890123456789",
                "name": "TestSoul",
                "tx_hash": VALID_TX,
            })
        assert response.status_code in (400, 404)

    def test_mint_sbt_rejects_invalid_address(self, client, integration_db, sample_bound_agent):
        """Non-address agent_address → 422."""
        response = client.post("/api/identity/mint-sbt", json={
            "agent_address": "not-an-address",
            "name": "TestSoul",
            "tx_hash": VALID_TX,
        })
        assert response.status_code == 422

    def test_mint_sbt_requires_name(self, client, integration_db, sample_bound_agent):
        """Missing name → 422."""
        response = client.post("/api/identity/mint-sbt", json={
            "agent_address": "0xBOUNDAGENT12345678901234567890123456789",
            "tx_hash": VALID_TX,
        })
        assert response.status_code == 422
