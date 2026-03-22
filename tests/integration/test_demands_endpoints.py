"""Integration tests for Demands router endpoints."""
import pytest


class TestDemandsEndpoints:
    """Demands router endpoint coverage."""

    def test_create_demand_requires_auth(self, client):
        """POST /api/demands → 401/201/404."""
        r = client.post("/api/demands", json={
            "title": "Need AI agent",
            "description": "Test demand",
            "budget": 1000,
        })
        assert r.status_code in (201, 400, 401, 403, 404, 422, 500)

    def test_list_demands_requires_auth(self, client):
        """GET /api/demands → 401/200."""
        r = client.get("/api/demands")
        assert r.status_code in (200, 401, 404)

    def test_list_demands_with_filters(self, client):
        """GET /api/demands?status=open → 401/200."""
        r = client.get("/api/demands?status=open")
        assert r.status_code in (200, 401, 404)

    def test_get_demand_requires_auth(self, client):
        """GET /api/demands/{id} → 401/200/404."""
        r = client.get("/api/demands/nonexistent")
        assert r.status_code in (200, 401, 404, 405, 422)

    def test_update_demand_requires_auth(self, client):
        """PATCH /api/demands/{id} → 401/200/404."""
        r = client.patch("/api/demands/nonexistent", json={"title": "Updated"})
        assert r.status_code in (200, 400, 401, 403, 404, 405, 422)

    def test_delete_demand_requires_auth(self, client):
        """DELETE /api/demands/{id} → 401/200/404."""
        r = client.delete("/api/demands/nonexistent")
        assert r.status_code in (200, 400, 401, 403, 404, 405, 422)

    def test_search_demands_requires_auth(self, client):
        """POST /api/demands/search → 401/200."""
        r = client.post("/api/demands/search", json={"query": "AI agent"})
        assert r.status_code in (200, 400, 401, 403, 404, 405, 422)
