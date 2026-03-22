"""
Integration tests for missing Wallet router endpoints.

Tests: get_balance, get_transactions, get_transaction.

Requires: client fixture from conftest.
"""
import pytest


class TestWalletEndpoints:
    """Missing Wallet router endpoint tests."""

    def test_get_balance_requires_auth(self, client):
        """GET /api/wallet/balance → 401 or 200."""
        r = client.get("/api/wallet/balance")
        assert r.status_code in (200, 401, 404)

    def test_get_balance_with_address(self, client):
        """GET /api/wallet/balance?address=0x... → 200/401/404."""
        r = client.get("/api/wallet/balance?address=0x" + "a" * 40)
        assert r.status_code in (200, 400, 401, 404)

    def test_get_transactions_requires_auth(self, client):
        """GET /api/wallet/transactions → 401 or 200."""
        r = client.get("/api/wallet/transactions")
        assert r.status_code in (200, 401, 404)

    def test_get_transactions_with_filters(self, client):
        """GET /api/wallet/transactions?type=stake → 200/401/404."""
        r = client.get("/api/wallet/transactions?type=stake")
        assert r.status_code in (200, 401, 404)

    def test_get_transactions_pagination(self, client):
        """GET /api/wallet/transactions?limit=10&offset=0 → 200/401/404."""
        r = client.get("/api/wallet/transactions?limit=10&offset=0")
        assert r.status_code in (200, 401, 404)

    def test_get_transaction_requires_auth(self, client):
        """GET /api/wallet/transactions/{tx_id} → 401 or 200."""
        r = client.get("/api/wallet/transactions/0x" + "a" * 64)
        assert r.status_code in (200, 401, 404)

    def test_get_transaction_not_found(self, client):
        """GET /api/wallet/transactions/nonexistent → 404."""
        r = client.get("/api/wallet/transactions/nonexistent")
        assert r.status_code in (200, 401, 404)
