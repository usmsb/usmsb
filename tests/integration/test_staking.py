"""
Integration tests: /api/staking/* endpoints.
"""
import pytest
from tests.integration.conftest import mock_web3, mock_web3_not_found, mock_web3_failed, VALID_TX


class TestStakingStakeEndpoint:
    """POST /api/staking/stake"""

    def test_stake_success_status_1(self, client, integration_db, sample_bound_agent):
        """status=1 on chain → 200 OK."""
        with mock_web3(status=1, from_addr="0xBOUNDWALLET"):
            response = client.post("/api/staking/stake", json={
                "amount": "1000", "lock_period": 2, "tx_hash": VALID_TX,
            })
        assert response.status_code == 200, \
            f"{response.status_code}: {response.json()}"

    def test_stake_rejects_failed_tx(self, client, integration_db, sample_bound_agent):
        """status=0 on chain → 400/500 error."""
        with mock_web3_failed():
            response = client.post("/api/staking/stake", json={
                "amount": "100", "lock_period": 1, "tx_hash": VALID_TX,
            })
        assert response.status_code in (400, 500), \
            f"Expected 400/500 for failed tx, got {response.status_code}: {response.json()}"

    def test_stake_rejects_pending_tx(self, client, integration_db, sample_bound_agent):
        """Tx not yet mined (receipt=None) → 400/404."""
        with mock_web3_not_found():
            response = client.post("/api/staking/stake", json={
                "amount": "100", "lock_period": 1, "tx_hash": VALID_TX,
            })
        assert response.status_code in (400, 404), \
            f"Expected 400/404 for pending tx, got {response.status_code}"

    def test_stake_rejects_invalid_hash_too_short(self, client, integration_db, sample_bound_agent):
        """tx_hash too short → 422."""
        response = client.post("/api/staking/stake", json={
            "amount": "100", "lock_period": 1, "tx_hash": "0x12",
        })
        assert response.status_code in (400, 422)  # endpoint catches validation errors

    def test_stake_rejects_hash_no_0x(self, client, integration_db, sample_bound_agent):
        """tx_hash without 0x prefix → 422."""
        response = client.post("/api/staking/stake", json={
            "amount": "100", "lock_period": 1, "tx_hash": "a" * 64,
        })
        assert response.status_code in (400, 422)  # endpoint catches validation errors

    def test_stake_rejects_zero_amount(self, client, integration_db, sample_bound_agent):
        """amount=0 → 422."""
        response = client.post("/api/staking/stake", json={
            "amount": "0", "lock_period": 1, "tx_hash": VALID_TX,
        })
        assert response.status_code in (400, 422)  # endpoint catches validation errors

    def test_stake_rejects_negative_amount(self, client, integration_db, sample_bound_agent):
        """Negative amount → 422."""
        response = client.post("/api/staking/stake", json={
            "amount": "-100", "lock_period": 1, "tx_hash": VALID_TX,
        })
        assert response.status_code in (400, 422)  # endpoint catches validation errors

    def test_stake_rejects_missing_lock_period(self, client, integration_db, sample_bound_agent):
        """Missing lock_period → 422."""
        response = client.post("/api/staking/stake", json={
            "amount": "100", "tx_hash": VALID_TX,
        })
        assert response.status_code in (400, 422)  # endpoint catches validation errors


class TestStakingUnstakeEndpoint:
    """POST /api/staking/unstake"""

    def test_unstake_success(self, client, integration_db, sample_bound_agent):
        """Valid unstake tx → 200."""
        with mock_web3(status=1):
            response = client.post("/api/staking/unstake", json={"tx_hash": VALID_TX})
        assert response.status_code == 200, \
            f"{response.status_code}: {response.json()}"

    def test_unstake_rejects_failed_tx(self, client, integration_db, sample_bound_agent):
        """Failed tx → 400/500."""
        with mock_web3_failed():
            response = client.post("/api/staking/unstake", json={"tx_hash": VALID_TX})
        assert response.status_code in (400, 500)

    def test_unstake_rejects_pending_tx(self, client, integration_db, sample_bound_agent):
        """Pending tx → 400/404."""
        with mock_web3_not_found():
            response = client.post("/api/staking/unstake", json={"tx_hash": VALID_TX})
        assert response.status_code in (400, 404)


class TestStakingClaimEndpoint:
    """POST /api/staking/claim"""

    def test_claim_success(self, client, integration_db, sample_bound_agent):
        """Valid claim tx → 200."""
        with mock_web3(status=1):
            response = client.post("/api/staking/claim", json={"tx_hash": VALID_TX})
        assert response.status_code == 200, \
            f"{response.status_code}: {response.json()}"

    def test_claim_rejects_failed_tx(self, client, integration_db, sample_bound_agent):
        """Failed claim tx → 400/500."""
        with mock_web3_failed():
            response = client.post("/api/staking/claim", json={"tx_hash": VALID_TX})
        assert response.status_code in (400, 500)


class TestStakingInfoEndpoint:
    """GET /api/staking/info"""

    def test_staking_info_returns_200(self, client, integration_db, sample_bound_agent):
        """Returns staking info for authenticated user."""
        response = client.get("/api/staking/info")
        assert response.status_code == 200
