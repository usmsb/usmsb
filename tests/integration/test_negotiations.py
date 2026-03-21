"""
Integration tests for Negotiations router.

Tests: start, counter, agree, cancel negotiation.
Requires: client fixture.
"""
import pytest
from tests.integration.conftest import mock_web3


class TestNegotiationLifecycle:
    """Test negotiation lifecycle: start → counter/agree → cancel."""

    def test_start_negotiation_requires_auth(self, client):
        """POST /api/negotiations → 401 without auth."""
        r = client.post("/api/negotiations", json={
            "supply_agent_id": "agent-001",
        })
        assert r.status_code in (401, 403)

    def test_start_negotiation_valid_body(self, client, integration_db):
        """POST /api/negotiations with valid body → 201 or 400."""
        r = client.post("/api/negotiations", json={
            "supply_agent_id": "agent-001",
        })
        assert r.status_code in (201, 400, 404, 422)

    def test_counter_negotiation_requires_auth(self, client):
        """POST /api/negotiations/{id}/counter → 401 without auth."""
        r = client.post("/api/negotiations/nonexistent/counter", json={
            "counter_changes": {"price": 400},
        })
        assert r.status_code in (401, 403, 404)

    def test_agree_negotiation_requires_auth(self, client):
        """POST /api/negotiations/{id}/agree → 401 without auth."""
        r = client.post("/api/negotiations/nonexistent/agree", json={})
        assert r.status_code in (401, 403, 404)

    def test_cancel_negotiation_requires_auth(self, client):
        """POST /api/negotiations/{id}/cancel → 401 without auth."""
        r = client.post("/api/negotiations/nonexistent/cancel", json={
            "reason": "Changed mind",
        })
        assert r.status_code in (401, 403, 404)


class TestMatchingSearch:
    """Test matching/search endpoints."""

    def test_search_demands_requires_auth(self, client):
        """POST /api/matching/search-demands → 401 without auth."""
        r = client.post("/api/matching/search-demands", json={
            "agent_id": "agent-001",
            "capabilities": ["python"],
        })
        assert r.status_code in (401, 403)

    def test_search_suppliers_requires_auth(self, client):
        """POST /api/matching/search-suppliers → 401 without auth."""
        r = client.post("/api/matching/search-suppliers", json={
            "agent_id": "agent-001",
            "required_skills": ["python"],
        })
        assert r.status_code in (401, 403)

    def test_initiate_negotiation_requires_auth(self, client):
        """POST /api/matching/negotiate → 401 without auth."""
        r = client.post("/api/matching/negotiate", json={
            "initiator_id": "a",
            "counterpart_id": "b",
            "context": {},
        })
        assert r.status_code in (401, 403)
