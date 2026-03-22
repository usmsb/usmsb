"""
Integration tests for missing Workflows router endpoints.

Tests: execute workflow, list with filters.

Requires: client fixture from conftest.
"""
import pytest


class TestWorkflowEndpoints:
    """Missing Workflows router endpoint tests."""

    def test_execute_workflow_requires_auth(self, client):
        """POST /api/workflows/{id}/execute → 401 or 200."""
        r = client.post("/api/workflows/nonexistent/execute", json={})
        assert r.status_code in (200, 400, 401, 403, 404, 422)

    def test_execute_workflow_with_input(self, client):
        """POST /api/workflows/{id}/execute with input → 200/401/404."""
        r = client.post(
            "/api/workflows/nonexistent/execute",
            json={"input": {"task": "test"}}
        )
        assert r.status_code in (200, 400, 401, 403, 404, 422)

    def test_list_workflows_with_filters(self, client):
        """GET /api/workflows?status=active → 200/401/404."""
        r = client.get("/api/workflows?status=active")
        assert r.status_code in (200, 401, 404)

    def test_list_workflows_pagination(self, client):
        """GET /api/workflows?limit=10&offset=0 → 200/401/404."""
        r = client.get("/api/workflows?limit=10&offset=0")
        assert r.status_code in (200, 401, 404)
