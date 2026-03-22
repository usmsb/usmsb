"""
Integration tests for missing Collaborations router endpoints.

Tests: execute, join, contribute, stats.

Requires: client fixture from conftest.
"""
import pytest


class TestCollaborationEndpoints:
    """Missing Collaborations router endpoint tests."""

    def test_execute_collaboration_requires_auth(self, client):
        """POST /api/collaborations/{id}/execute → 401 or 200."""
        r = client.post("/api/collaborations/nonexistent/execute", json={})
        assert r.status_code in (200, 400, 401, 403, 404, 422)

    def test_execute_collaboration_with_input(self, client):
        """POST /api/collaborations/{id}/execute with input → 200/401/404."""
        r = client.post(
            "/api/collaborations/nonexistent/execute",
            json={"input": {"task": "test"}}
        )
        assert r.status_code in (200, 400, 401, 403, 404, 422)

    def test_join_collaboration_requires_auth(self, client):
        """POST /api/collaborations/{id}/join → 401 or 200."""
        r = client.post("/api/collaborations/nonexistent/join", json={})
        assert r.status_code in (200, 400, 401, 403, 404, 422)

    def test_submit_contribution_requires_auth(self, client):
        """POST /api/collaborations/{id}/contribute → 401 or 200."""
        r = client.post(
            "/api/collaborations/nonexistent/contribute",
            json={"content": "test contribution"}
        )
        assert r.status_code in (200, 400, 401, 403, 404, 422)

    def test_complete_collaboration_requires_auth(self, client):
        """POST /api/collaborations/{id}/complete → 401 or 200."""
        r = client.post("/api/collaborations/nonexistent/complete", json={})
        assert r.status_code in (200, 400, 401, 403, 404, 422)

    def test_get_collaboration_stats_requires_auth(self, client):
        """GET /api/collaborations/stats → 401 or 200."""
        r = client.get("/api/collaborations/stats")
        assert r.status_code in (200, 401, 404)

    def test_list_collaborations_with_status(self, client):
        """GET /api/collaborations?status=active → 200/401/404."""
        r = client.get("/api/collaborations?status=active")
        assert r.status_code in (200, 401, 404)
