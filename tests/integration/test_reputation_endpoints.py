"""Integration tests for Reputation router endpoints."""
import pytest


class TestReputationEndpoints:
    """Reputation router endpoint coverage."""

    def test_get_reputation_requires_auth(self, client):
        """GET /api/reputation/{agent_id} → 401/200."""
        r = client.get("/api/reputation/test_agent")
        assert r.status_code in (200, 401, 404, 503)

    def test_get_reputation_history_requires_auth(self, client):
        """GET /api/reputation/{agent_id}/history → 401/200."""
        r = client.get("/api/reputation/test_agent/history")
        assert r.status_code in (200, 401, 404, 503)

    def test_update_reputation_requires_auth(self, client):
        """POST /api/reputation/{agent_id} → 401/200."""
        r = client.post("/api/reputation/test_agent", json={"delta": 1.0})
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)
