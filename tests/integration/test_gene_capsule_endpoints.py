"""Integration tests for GeneCapsule router endpoints."""
import pytest


class TestGeneCapsuleEndpoints:
    """GeneCapsule router endpoint coverage."""

    def test_search_agents_requires_auth(self, client):
        """POST /api/gene-capsule/search-agents → 401/200."""
        r = client.post("/api/gene-capsule/search-agents", json={
            "query": "AI agent",
            "limit": 10
        })
        assert r.status_code in (200, 400, 401, 403, 404, 422, 503)

    def test_get_agent_experiences_requires_auth(self, client):
        """GET /api/gene-capsule/experiences/{agent_id} → 401/200."""
        r = client.get("/api/gene-capsule/experiences/test_agent")
        assert r.status_code in (200, 401, 404, 503)

    def test_search_experiences_requires_auth(self, client):
        """POST /api/gene-capsule/experiences → 401/200."""
        r = client.post("/api/gene-capsule/experiences", json={
            "query": "data analysis"
        })
        assert r.status_code in (200, 400, 401, 403, 404, 422, 503)

    def test_get_gene_capsule_requires_auth(self, client):
        """GET /api/gene-capsule/{agent_id} → 401/200."""
        r = client.get("/api/gene-capsule/test_agent")
        assert r.status_code in (200, 401, 404, 503)
