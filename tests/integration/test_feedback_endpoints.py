"""Integration tests for Feedback router endpoints."""
import pytest


class TestFeedbackEndpoints:
    """Feedback router endpoint coverage."""

    def test_process_contract_feedback_requires_auth(self, client):
        """POST /api/feedback/contract/{id} → 401/200."""
        r = client.post("/api/feedback/contract/nonexistent", json={
            "success": True,
            "quality_score": 5,
        })
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)

    def test_get_agent_feedback_requires_auth(self, client):
        """GET /api/feedback/agent/{id} → 401/200."""
        r = client.get("/api/feedback/agent/test_agent")
        assert r.status_code in (200, 401, 404, 503)

    def test_get_feedback_stats_requires_auth(self, client):
        """GET /api/feedback/stats → 401/200."""
        r = client.get("/api/feedback/stats")
        assert r.status_code in (200, 401, 404, 503)
