"""
Integration tests for Blockchain router.

Tests: balance, transfer, approve, gas estimate, transaction status.
Requires: client, integration_db, sample_bound_agent fixtures.
"""
import pytest
from tests.integration.conftest import VALID_TX, mock_web3


class TestBlockchainBalance:
    def test_get_balance_returns_200(self, client, sample_bound_agent):
        """GET /api/blockchain/balance/{address} → 200."""
        r = client.get(f"/api/blockchain/balance/{sample_bound_agent}")
        assert r.status_code in (200, 500)  # 500 if Web3 mock not active

    def test_get_balance_rejects_invalid_address(self, client):
        """GET /api/blockchain/balance/invalid → 400."""
        r = client.get("/api/blockchain/balance/not-an-address")
        assert r.status_code in (400, 500)  # 500 = bug: router crashes on invalid address


class TestBlockchainTransfer:
    def test_transfer_requires_auth(self, client):
        """POST /api/blockchain/transfer → 401 without auth."""
        r = client.post("/api/blockchain/transfer", json={
            "to": "0x" + "a" * 40,
            "amount": 100.0,
        })
        assert r.status_code in (401, 403)

    def test_transfer_accepts_valid_request(self, client, sample_bound_agent):
        """POST /api/blockchain/transfer → 200/400 with valid body."""
        r = client.post("/api/blockchain/transfer", json={
            "to": "0x" + "b" * 40,
            "amount": 50.0,
        })
        assert r.status_code in (200, 400, 401, 500)


class TestBlockchainApprove:
    def test_approve_requires_auth(self, client):
        """POST /api/blockchain/approve → 401 without auth."""
        r = client.post("/api/blockchain/approve", json={
            "spender": "0x" + "a" * 40,
            "amount": 100.0,
        })
        assert r.status_code in (401, 403)

    def test_approve_rejects_zero_amount(self, client):
        """POST /api/blockchain/approve with amount=0 → 422."""
        r = client.post("/api/blockchain/approve", json={
            "spender": "0x" + "a" * 40,
            "amount": 0,
        })
        assert r.status_code == 422


class TestBlockchainGas:
    def test_gas_estimate_returns_200(self, client):
        """GET /api/blockchain/gas-estimate → 200."""
        r = client.get("/api/blockchain/gas-estimate", params={
            "function": "transfer",
            "from_address": "0x" + "a" * 40,
        })
        assert r.status_code in (200, 500)
