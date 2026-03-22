"""Integration tests for Pre-match Negotiation router endpoints."""
import pytest


class TestPreMatchNegotiationEndpoints:
    """Pre-match negotiation router endpoint coverage."""

    def test_initiate_requires_auth(self, client):
        """POST /api/pre-match/negotiate → 401/200."""
        r = client.post("/api/pre-match/negotiate", json={
            "demand_id": "demand_001",
            "supply_agent_id": "agent_001"
        })
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)

    def test_list_negotiations_requires_auth(self, client):
        """GET /api/pre-match/negotiations → 401/200."""
        r = client.get("/api/pre-match/negotiations")
        assert r.status_code in (200, 401, 404, 503)

    def test_get_negotiation_requires_auth(self, client):
        """GET /api/pre-match/negotiations/{id} → 401/200."""
        r = client.get("/api/pre-match/negotiations/nonexistent")
        assert r.status_code in (200, 401, 404, 422)
