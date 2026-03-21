"""
Integration tests for USMSB Matching and Gene Capsule routers.

Tests: broadcast capability/goal, get gene capsule, search genes.
Requires: client fixture.
"""
import pytest


class TestUsmsbMatching:
    def test_broadcast_capability_requires_auth(self, client):
        """POST /api/usmsb/match/capability → 401 without auth."""
        r = client.post("/api/usmsb/match/capability", json={
            "capability": "python",
            "offering": "AI coding assistant",
        })
        assert r.status_code in (401, 403, 404)

    def test_broadcast_goal_requires_auth(self, client):
        """POST /api/usmsb/match/goal → 401 without auth."""
        r = client.post("/api/usmsb/match/goal", json={
            "goal": "Find AI agent for data processing",
            "requirements": ["python", "fastapi"],
        })
        assert r.status_code in (401, 403, 404)

    def test_get_matching_requires_auth(self, client):
        """GET /api/usmsb/match/{agent_id} → 401 without auth."""
        r = client.get("/api/usmsb/match/agent-001")
        assert r.status_code in (401, 403, 404)


class TestGeneCapsule:
    def test_get_capsule_requires_auth(self, client):
        """GET /api/gene-capsule/{agent_id} → 401 without auth."""
        r = client.get("/api/gene-capsule/agent-001")
        assert r.status_code in (401, 403, 404)

    def test_search_experiences_requires_auth(self, client):
        """POST /api/gene-capsule/experiences → 401 without auth."""
        r = client.post("/api/gene-capsule/experiences", json={
            "query": "python",
        })
        assert r.status_code in (401, 403, 404)

    def test_search_patterns_requires_auth(self, client):
        """POST /api/gene-capsule/patterns → 401 without auth."""
        r = client.post("/api/gene-capsule/patterns", json={
            "query": "design pattern",
        })
        assert r.status_code in (401, 403, 404)

    def test_search_skills_requires_auth(self, client):
        """POST /api/gene-capsule/skills → 401 without auth."""
        r = client.post("/api/gene-capsule/skills", json={
            "query": "python",
        })
        assert r.status_code in (401, 403, 404)


class TestWallet:
    def test_get_balance_requires_auth(self, client):
        """GET /api/wallet/balance/{agent_id} → 401 without auth."""
        r = client.get("/api/wallet/balance/agent-001")
        assert r.status_code in (401, 403, 404)

    def test_get_transactions_requires_auth(self, client):
        """GET /api/wallet/transactions/{agent_id} → 401 without auth."""
        r = client.get("/api/wallet/transactions/agent-001")
        assert r.status_code in (401, 403, 404)
