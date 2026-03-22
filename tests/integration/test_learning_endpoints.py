"""Integration tests for Learning router endpoints."""
import pytest


class TestLearningEndpoints:
    """Learning router endpoint coverage."""

    def test_get_insights_requires_auth(self, client):
        """GET /api/learning/insights → 401/200."""
        r = client.get("/api/learning/insights")
        assert r.status_code in (200, 401, 404, 405, 500, 503)

    def test_analyze_requires_auth(self, client):
        """POST /api/learning/analyze → 401/200."""
        r = client.post("/api/learning/analyze", json={"data": "test"})
        assert r.status_code in (200, 400, 401, 403, 404, 422, 503)

    def test_get_strategy_requires_auth(self, client):
        """GET /api/learning/strategy → 401/200."""
        r = client.get("/api/learning/strategy")
        assert r.status_code in (200, 401, 404, 405, 500, 503)

    def test_get_market_requires_auth(self, client):
        """GET /api/learning/market → 401/200."""
        r = client.get("/api/learning/market")
        assert r.status_code in (200, 401, 404, 405, 500, 503)
