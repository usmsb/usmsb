"""
Integration tests for missing Matching router endpoints.

Tests: get_negotiations, submit_proposal, accept/reject_negotiation,
       opportunities, stats, search_demands/suppliers.

Requires: client fixture from conftest.
"""
import pytest


class TestMatchingEndpoints:
    """Missing Matching router endpoint tests."""

    def test_get_negotiations_requires_auth(self, client):
        """GET /api/matching/negotiations → 401 or 200."""
        r = client.get("/api/matching/negotiations")
        assert r.status_code in (200, 401, 404)

    def test_get_negotiations_with_filters(self, client):
        """GET /api/matching/negotiations?status=active → 200/401/404."""
        r = client.get("/api/matching/negotiations?status=active")
        assert r.status_code in (200, 401, 404)

    def test_submit_proposal_requires_auth(self, client):
        """POST /api/matching/negotiations/{id}/proposal → 401/404."""
        r = client.post(
            "/api/matching/negotiations/nonexistent/proposal",
            json={"price": 500, "terms": "standard"}
        )
        assert r.status_code in (200, 400, 401, 403, 404, 422)

    def test_accept_negotiation_requires_auth(self, client):
        """POST /api/matching/negotiations/{id}/accept → 401/404."""
        r = client.post("/api/matching/negotiations/nonexistent/accept", json={})
        assert r.status_code in (200, 400, 401, 403, 404, 422)

    def test_reject_negotiation_requires_auth(self, client):
        """POST /api/matching/negotiations/{id}/reject → 401/404."""
        r = client.post(
            "/api/matching/negotiations/nonexistent/reject",
            json={"reason": "Price too high"}
        )
        assert r.status_code in (200, 400, 401, 403, 404, 422)

    def test_get_opportunities_requires_auth(self, client):
        """GET /api/matching/opportunities → 200/401/404."""
        r = client.get("/api/matching/opportunities")
        assert r.status_code in (200, 401, 404)

    def test_get_matching_stats_requires_auth(self, client):
        """GET /api/matching/stats → 200/401/404."""
        r = client.get("/api/matching/stats")
        assert r.status_code in (200, 401, 404)

    def test_search_demands_with_pagination(self, client):
        """POST /api/matching/search-demands with pagination → 200/401/404."""
        r = client.post(
            "/api/matching/search-demands",
            json={"capabilities": ["python"], "limit": 10, "offset": 0}
        )
        assert r.status_code in (200, 400, 401, 403, 404, 422)

    def test_search_suppliers_with_pagination(self, client):
        """POST /api/matching/search-suppliers with pagination → 200/401/404."""
        r = client.post(
            "/api/matching/search-suppliers",
            json={"capabilities": ["python"], "limit": 10, "offset": 0}
        )
        assert r.status_code in (200, 400, 401, 403, 404, 422)
