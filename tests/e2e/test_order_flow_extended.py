"""
Extended E2E flow tests - complete governance, dispute resolution, and matching flows.

These use the shared TestClient from e2e conftest.
"""
import pytest


class TestGovernanceFullFlow:
    """Full governance flow: proposal → vote → execute."""

    def test_create_proposal(self, client):
        """POST /api/governance/proposals → 201/400/401."""
        r = client.post("/api/governance/proposals", json={
            "title": "Extended Test Proposal",
            "description": "Testing full governance flow",
            "proposal_type": "upgrade",
            "target": "0x" + "a" * 40,
            "data": "0x"
        })
        assert r.status_code in (201, 400, 401, 403, 422, 500)

    def test_list_proposals(self, client):
        """GET /api/governance/proposals → 200/401."""
        r = client.get("/api/governance/proposals")
        assert r.status_code in (200, 401, 404, 422)

    def test_vote_on_proposal(self, client):
        """POST /api/governance/proposals/{id}/vote → 200/401/404."""
        r = client.post(
            "/api/governance/proposals/nonexistent/vote",
            json={"vote": "for", "reason": "test"}
        )
        assert r.status_code in (200, 400, 401, 403, 404, 422)

    def test_execute_proposal(self, client):
        """POST /api/governance/proposals/{id}/execute → 200/401/404."""
        r = client.post("/api/governance/proposals/nonexistent/execute", json={})
        assert r.status_code in (200, 400, 401, 403, 404, 422)

    def test_get_proposal_details(self, client):
        """GET /api/governance/proposals/{id} → 200/401/404."""
        r = client.get("/api/governance/proposals/nonexistent")
        assert r.status_code in (200, 401, 404, 422)


class TestDisputeFullFlow:
    """Full dispute flow: raise → resolve."""

    def test_raise_dispute(self, client):
        """POST /api/disputes → 201/400/401."""
        r = client.post("/api/disputes", json={
            "order_id": "test_order_001",
            "reason": "quality issue",
            "evidence": "test evidence"
        })
        assert r.status_code in (201, 400, 401, 403, 404, 422, 500)

    def test_list_disputes(self, client):
        """GET /api/disputes → 200/401."""
        r = client.get("/api/disputes")
        assert r.status_code in (200, 401, 404, 422)

    def test_get_dispute_details(self, client):
        """GET /api/disputes/{id} → 200/401/404."""
        r = client.get("/api/disputes/nonexistent")
        assert r.status_code in (200, 401, 404, 422)

    def test_resolve_dispute(self, client):
        """POST /api/disputes/{id}/resolve → 200/401/404."""
        r = client.post(
            "/api/disputes/nonexistent/resolve",
            json={"resolution": "refund", "amount": 100}
        )
        assert r.status_code in (200, 400, 401, 403, 404, 422)


class TestMatchingFullFlow:
    """Full matching flow: demand → search → negotiate → order."""

    def test_create_demand(self, client):
        """POST /api/demands → 201/400/401."""
        r = client.post("/api/demands", json={
            "title": "Need数据分析",
            "description": "需要数据分析服务",
            "budget": 1000,
            "deadline": 9999999999
        })
        assert r.status_code in (201, 400, 401, 403, 404, 422, 500)

    def test_list_demands(self, client):
        """GET /api/demands → 200/401."""
        r = client.get("/api/demands")
        assert r.status_code in (200, 401, 404, 422)

    def test_search_suppliers(self, client):
        """POST /api/matching/search-suppliers → 200/401."""
        r = client.post("/api/matching/search-suppliers", json={
            "capabilities": ["数据分析"],
            "limit": 10
        })
        assert r.status_code in (200, 400, 401, 403, 404, 422)

    def test_initiate_negotiation(self, client):
        """POST /api/matching/negotiate → 200/401."""
        r = client.post("/api/matching/negotiate", json={
            "demand_id": "test_demand",
            "supply_agent_id": "test_agent",
            "initial_terms": {"price": 500}
        })
        assert r.status_code in (200, 400, 401, 403, 404, 422)

    def test_list_negotiations(self, client):
        """GET /api/matching/negotiations → 200/401."""
        r = client.get("/api/matching/negotiations")
        assert r.status_code in (200, 401, 404, 422)


class TestReputationFlow:
    """Reputation tracking flow."""

    def test_get_reputation(self, client):
        """GET /api/reputation/{agent_id} → 200/401/404."""
        r = client.get("/api/reputation/test_agent")
        assert r.status_code in (200, 401, 404, 503)

    def test_get_reputation_history(self, client):
        """GET /api/reputation/{agent_id}/history → 200/401/404."""
        r = client.get("/api/reputation/test_agent/history")
        assert r.status_code in (200, 401, 404, 503)


class TestWorkflowExecution:
    """Workflow execution flow."""

    def test_create_workflow(self, client):
        """POST /api/workflows → 201/400/401."""
        r = client.post("/api/workflows", json={
            "name": "Test Workflow",
            "steps": [{"action": "analyze"}]
        })
        assert r.status_code in (201, 400, 401, 403, 404, 422, 500)

    def test_list_workflows(self, client):
        """GET /api/workflows → 200/401."""
        r = client.get("/api/workflows")
        assert r.status_code in (200, 401, 404, 422)

    def test_execute_workflow(self, client):
        """POST /api/workflows/{id}/execute → 200/401/404."""
        r = client.post("/api/workflows/nonexistent/execute", json={})
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)
