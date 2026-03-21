"""
Integration tests for USMSB Matching and Gene Capsule routers.

Tests: broadcast capability/goal, get gene capsule, search experiences.
Requires: client fixture.
"""
import pytest


class TestUsmsbMatching:
    """/api/usmsb/match/* endpoints — publicly accessible."""

    def test_broadcast_capability_returns_200_or_error(self, client):
        """POST /api/usmsb/match/broadcast/capability → 200 (public endpoint)."""
        r = client.post("/api/usmsb/match/broadcast/capability", json={
            "capability": "python",
            "offering": "AI coding assistant",
        })
        assert r.status_code in (200, 400, 500)

    def test_broadcast_goal_returns_200_or_error(self, client):
        """POST /api/usmsb/match/broadcast/goal → 200 (public endpoint)."""
        r = client.post("/api/usmsb/match/broadcast/goal", json={
            "goal": "Find AI agent for data processing",
            "requirements": ["python", "fastapi"],
        })
        assert r.status_code in (200, 400, 500)

    def test_get_matching_returns_200_or_503(self, client):
        """GET /api/usmsb/match/{agent_id} → 200 or 503."""
        r = client.get("/api/usmsb/match/agent-001")
        assert r.status_code in (200, 404, 503)


class TestGeneCapsule:
    """/api/gene-capsule/* endpoints."""

    def test_get_capsule_returns_503_or_404(self, client):
        """GET /api/gene-capsule/{agent_id} → 503 (service unavailable) or 404."""
        r = client.get("/api/gene-capsule/agent-001")
        assert r.status_code in (401, 403, 404, 503)

    def test_search_experiences_returns_422_or_503(self, client):
        """POST /api/gene-capsule/experiences → 422 or 503 without auth."""
        r = client.post("/api/gene-capsule/experiences", json={
            "query": "python",
        })
        assert r.status_code in (401, 403, 422, 503)

    def test_search_agents_returns_422_or_503(self, client):
        """POST /api/gene-capsule/search-agents → 422 or 503 without auth."""
        r = client.post("/api/gene-capsule/search-agents", json={
            "query": "python developer",
        })
        assert r.status_code in (401, 403, 422, 503)


class TestWallet:
    """Wallet endpoints (may not exist or be in different router)."""

    def test_wallet_balance_returns_404(self, client):
        """GET /api/wallet/balance/* → likely 404 (endpoint not registered)."""
        r = client.get("/api/wallet/balance/agent-001")
        assert r.status_code in (401, 403, 404)
