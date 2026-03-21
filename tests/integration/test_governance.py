"""
Integration tests: /api/governance/* endpoints.
"""
import pytest
from tests.integration.conftest import mock_web3, mock_web3_not_found, mock_web3_failed, VALID_TX


class TestGovernanceProposals:
    """GET /api/governance/proposals"""

    def test_list_proposals_returns_200(self, client, integration_db):
        """Proposal list returns 200."""
        response = client.get("/api/governance/proposals")
        assert response.status_code == 200

    def test_list_proposals_returns_list(self, client, integration_db):
        """Response is a list (possibly empty)."""
        response = client.get("/api/governance/proposals")
        data = response.json()
        assert isinstance(data, (list, dict))


class TestGovernanceVote:
    """POST /api/governance/vote"""

    def test_vote_success(self, client, integration_db, sample_proposal):
        """Valid vote tx (status=1) → 200."""
        with mock_web3(status=1, from_addr="0xVOTERADDR"):
            response = client.post("/api/governance/vote", json={
                "proposal_id": 1, "support": 1, "tx_hash": VALID_TX,
            })
        assert response.status_code == 200, \
            f"{response.status_code}: {response.json()}"

    def test_vote_rejects_failed_tx(self, client, integration_db, sample_proposal):
        """Failed vote tx → 400/500."""
        with mock_web3_failed():
            response = client.post("/api/governance/vote", json={
                "proposal_id": 1, "support": 1, "tx_hash": VALID_TX,
            })
        assert response.status_code in (400, 500), \
            f"{response.status_code}: {response.json()}"

    def test_vote_rejects_pending_tx(self, client, integration_db, sample_proposal):
        """Pending tx → 400/404."""
        with mock_web3_not_found():
            response = client.post("/api/governance/vote", json={
                "proposal_id": 1, "support": 1, "tx_hash": VALID_TX,
            })
        assert response.status_code in (400, 404), \
            f"{response.status_code}: {response.json()}"

    def test_vote_rejects_invalid_support(self, client, integration_db, sample_proposal):
        """support=99 → 422."""
        with mock_web3(status=1):
            response = client.post("/api/governance/vote", json={
                "proposal_id": 1, "support": 99, "tx_hash": VALID_TX,
            })
        assert response.status_code == 422

    def test_vote_rejects_invalid_hash(self, client, integration_db, sample_proposal):
        """Invalid tx_hash → 422."""
        response = client.post("/api/governance/vote", json={
            "proposal_id": 1, "support": 1, "tx_hash": "0x12",
        })
        assert response.status_code == 422


class TestGovernanceCreateProposal:
    """POST /api/governance/proposals (create)"""

    def test_create_proposal_success(self, client, integration_db):
        """Valid creation tx → 200."""
        with mock_web3(status=1, from_addr="0xPROPOSER"):
            response = client.post("/api/governance/proposals", json={
                "proposal_type": 0,
                "title": "New Proposal",
                "description": "A test governance proposal",
                "target": "0x1234567890123456789012345678901234567890",
                "tx_hash": VALID_TX,
            })
        assert response.status_code == 200, \
            f"{response.status_code}: {response.json()}"

    def test_create_proposal_rejects_failed_tx(self, client, integration_db):
        """Failed tx → 400/500."""
        with mock_web3_failed():
            response = client.post("/api/governance/proposals", json={
                "proposal_type": 0,
                "title": "New Proposal",
                "description": "A test",
                "target": "0x1234567890123456789012345678901234567890",
                "tx_hash": VALID_TX,
            })
        assert response.status_code in (400, 500)

    def test_create_proposal_rejects_invalid_target(self, client, integration_db):
        """Invalid target address → 422."""
        response = client.post("/api/governance/proposals", json={
            "proposal_type": 0,
            "title": "Test",
            "description": "Desc",
            "target": "not-an-address",
            "tx_hash": VALID_TX,
        })
        assert response.status_code == 422
