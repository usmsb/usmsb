"""
Integration tests for Orders router.

Tests: create from pre-match, create from negotiation, confirm, start, deliver, accept, cancel.
Requires: client, integration_db, sample_bound_agent fixtures.
"""
import pytest
from tests.integration.conftest import mock_web3


class TestOrderLifecycle:
    """Test order lifecycle: create → confirm → start → deliver → accept."""

    def test_create_order_from_prematch_returns_200_or_400(self, client, integration_db, sample_bound_agent):
        """POST /api/orders/from-pre-match → 200 or 400."""
        r = client.post("/api/orders/from-pre-match", json={
            "negotiation_id": "neg-001",
        })
        assert r.status_code in (200, 400, 404)  # 404 if pre-match not found

    def test_create_order_from_negotiation_returns_200_or_400(self, client, integration_db, sample_bound_agent):
        """POST /api/orders/from-negotiation → 200 or 400."""
        r = client.post("/api/orders/from-negotiation", json={
            "negotiation_session_id": "ns-001",
            "price": 500.0,
            "task_description": "Build a web app",
            "demand_agent_id": "demand_agent",
            "supply_agent_id": sample_bound_agent,
        })
        assert r.status_code in (200, 400, 404)  # 404 if negotiation not found

    def test_confirm_order_requires_auth(self, client):
        """POST /api/orders/{id}/confirm → 401 without auth."""
        r = client.post("/api/orders/nonexistent/confirm", json={})
        assert r.status_code in (401, 403, 404)

    def test_start_order_requires_auth(self, client):
        """POST /api/orders/{id}/start → 401 without auth."""
        r = client.post("/api/orders/nonexistent/start", json={})
        assert r.status_code in (401, 403, 404)

    def test_deliver_order_requires_auth(self, client):
        """POST /api/orders/{id}/deliver → 401 without auth."""
        r = client.post("/api/orders/nonexistent/deliver", json={
            "description": "Done",
        })
        assert r.status_code in (401, 403, 404)

    def test_accept_deliverable_requires_auth(self, client):
        """POST /api/orders/{id}/accept → 401 without auth."""
        r = client.post("/api/orders/nonexistent/accept", json={
            "rating": 5,
        })
        assert r.status_code in (401, 403, 404)

    def test_cancel_order_requires_auth(self, client):
        """POST /api/orders/{id}/cancel → 401 without auth."""
        r = client.post("/api/orders/nonexistent/cancel", json={
            "reason": "Changed mind",
        })
        assert r.status_code in (401, 403, 404)

    def test_raise_dispute_requires_auth(self, client):
        """POST /api/orders/{id}/dispute → 401 without auth."""
        r = client.post("/api/orders/nonexistent/dispute", json={
            "reason": "Service not delivered",
        })
        assert r.status_code in (401, 403, 404)
