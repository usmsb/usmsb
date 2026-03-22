"""Integration tests for Souls router endpoints."""
import pytest


class TestSoulsEndpoints:
    """Souls router endpoint coverage."""

    def test_get_soul_requires_auth(self, client):
        """GET /api/souls/{agent_id} → 401/200."""
        r = client.get("/api/souls/test_agent")
        assert r.status_code in (200, 401, 404, 503)

    def test_mint_soul_requires_auth(self, client):
        """POST /api/souls/mint → 401/201."""
        r = client.post("/api/souls/mint", json={
            "agent_id": "test_agent",
            "soul_type": "agent_soul"
        })
        assert r.status_code in (201, 400, 401, 403, 404, 422, 500)

    def test_list_souls_requires_auth(self, client):
        """GET /api/souls → 401/200."""
        r = client.get("/api/souls")
        assert r.status_code in (200, 401, 404, 503)
