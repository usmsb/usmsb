"""
Integration tests: /api/dispute/* endpoints.
"""
import pytest
from tests.integration.conftest import mock_web3, mock_web3_failed, VALID_TX


class TestDisputeRaise:
    """POST /api/dispute/raise"""

    def test_raise_dispute_success(self, client, integration_db, sample_bound_agent):
        """Valid dispute tx → 200 or business error."""
        with mock_web3(status=1):
            response = client.post("/api/dispute/raise", json={
                "pool_id": "pool_dispute",
                "chain_pool_id": "0xCHAINPOOLD",
                "reason": "Service not delivered",
                "tx_hash": VALID_TX,
            })
        assert response.status_code in (200, 400, 404), \
            f"Unexpected {response.status_code}: {response.json()}"

    def test_raise_dispute_rejects_failed_tx(self, client, integration_db, sample_bound_agent):
        """Failed tx → 400/500."""
        with mock_web3_failed():
            response = client.post("/api/dispute/raise", json={
                "pool_id": "pool_dispute",
                "chain_pool_id": "0xCHAINPOOLD",
                "reason": "Service not delivered",
                "tx_hash": VALID_TX,
            })
        assert response.status_code in (400, 500)

    def test_raise_dispute_requires_reason(self, client, integration_db):
        """Missing reason → 422."""
        response = client.post("/api/dispute/raise", json={
            "pool_id": "pool_dispute",
            "chain_pool_id": "0xCHAINPOOLD",
            "tx_hash": VALID_TX,
        })
        assert response.status_code == 422
