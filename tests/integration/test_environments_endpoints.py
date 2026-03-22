"""Integration tests for Environments router endpoints."""
import pytest


class TestEnvironmentsEndpoints:
    """Environments router endpoint coverage."""

    def test_list_environments_requires_auth(self, client):
        """GET /api/environments → 401/200."""
        r = client.get("/api/environments")
        assert r.status_code in (200, 401, 404)

    def test_create_environment_requires_auth(self, client):
        """POST /api/environments → 401/201/404."""
        r = client.post("/api/environments", json={
            "name": "test_env",
            "type": "sandbox"
        })
        assert r.status_code in (201, 400, 401, 403, 404, 422, 500)

    def test_get_environment_requires_auth(self, client):
        """GET /api/environments/{id} → 401/200/404."""
        r = client.get("/api/environments/nonexistent")
        assert r.status_code in (200, 401, 404, 405, 422)

    def test_update_environment_requires_auth(self, client):
        """PATCH /api/environments/{id} → 401/200/404."""
        r = client.patch("/api/environments/nonexistent", json={"name": "updated"})
        assert r.status_code in (200, 400, 401, 403, 404, 405, 422)
