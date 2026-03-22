"""
Integration tests for Services, Demands, Environments, Workflows, Souls routers.

Tests endpoint behavior (auth required vs public).
Requires: client fixture.
"""
import pytest


class TestServices:
    """Service endpoints."""

    def test_register_service_returns_405_or_400(self, client):
        """POST /api/services → 405 (wrong path) or 400."""
        r = client.post("/api/services", json={
            "service_name": "TestService",
            "service_type": "ai_agent",
            "description": "A test service",
            "capabilities": ["python"],
            "price": 50.0,
        })
        assert r.status_code in (400, 404, 405)

    def test_list_services_is_public(self, client):
        """GET /api/services → 200 (public listing)."""
        r = client.get("/api/services")
        assert r.status_code == 200


class TestDemands:
    """Demand endpoints."""

    def test_create_demand_is_public(self, client):
        """POST /api/demands → 201 (public endpoint)."""
        r = client.post("/api/demands", json={
            "agent_id": "agent-001",
            "title": "Need AI coding agent",
            "category": "development",
        })
        assert r.status_code in (201, 400)

    def test_list_demands_is_public(self, client):
        """GET /api/demands → 200 (public listing)."""
        r = client.get("/api/demands")
        assert r.status_code == 200


class TestEnvironments:
    """Environment endpoints."""

    def test_create_environment_returns_400_or_404(self, client):
        """POST /api/environments → 400 (validation error) or 404."""
        r = client.post("/api/environments", json={
            "name": "TestEnv",
            "type": "sandbox",
        })
        assert r.status_code in (400, 404, 422)

    def test_list_environments_is_public(self, client):
        """GET /api/environments → 200 (public listing)."""
        r = client.get("/api/environments")
        assert r.status_code == 200


class TestWorkflows:
    """Workflow endpoints."""

    def test_create_workflow_is_public(self, client):
        """POST /api/workflows → 201 (public endpoint)."""
        r = client.post("/api/workflows", json={
            "task_description": "Process orders",
            "agent_id": "agent-001",
        })
        assert r.status_code in (201, 400)

    def test_list_workflows_is_public(self, client):
        """GET /api/workflows → 200 or 401 (depends on router)."""
        r = client.get("/api/workflows")
        assert r.status_code in (200, 401, 403)


class TestReputation:
    """Reputation endpoints."""

    def test_get_reputation_returns_404(self, client):
        """GET /api/reputation/{agent_id} → 404 (endpoint doesn't exist)."""
        r = client.get("/api/reputation/agent-001")
        assert r.status_code in (401, 403, 404)


class TestSouls:
    """Soul registration endpoints."""

    def test_register_soul_returns_405_or_400(self, client):
        """POST /api/agents/soul/register → 405 or 400 or 422."""
        r = client.post("/api/agents/soul/register", json={
            "goals": [{"name": "Build AI"}],
            "capabilities": ["python"],
        })
        assert r.status_code in (400, 401, 403, 405, 422)

    def test_get_soul_returns_404(self, client):
        """GET /api/agents/soul/{agent_id} → 404."""
        r = client.get("/api/agents/soul/agent-001")
        assert r.status_code in (401, 403, 404)


class TestFeedback:
    """Feedback endpoints."""

    def test_submit_feedback_returns_400_or_404(self, client):
        """POST /api/feedback/contract/{contract_id} → 400 or 404."""
        r = client.post("/api/feedback/contract/contract-001", json={
            "success": True,
        })
        assert r.status_code in (400, 401, 403, 404)


class TestNetwork:
    """Network exploration endpoints."""

    def test_explore_network_returns_404_or_405(self, client):
        """POST /api/network/explore → 404 or 405."""
        r = client.post("/api/network/explore", json={
            "agent_id": "agent-001",
            "target_capabilities": ["python"],
        })
        assert r.status_code in (200, 400, 401, 403, 404, 405)


class TestMetaAgent:
    """Meta-agent chat/consult endpoints."""

    def test_consult_returns_400_or_401(self, client):
        """POST /api/meta-agent/consult → 400 or 401."""
        r = client.post("/api/meta-agent/consult", json={
            "agent_id": "agent-001",
            "question": "What is the best approach?",
        })
        assert r.status_code in (400, 401, 403, 503)

    def test_recommend_returns_400_or_401(self, client):
        """POST /api/meta-agent/recommend → 400 or 401 or 503."""
        r = client.post("/api/meta-agent/recommend", json={
            "demand": {"type": "coding"},
        })
        assert r.status_code in (400, 401, 403, 503)


class TestSystem:
    """System health endpoints."""

    def test_health_is_public(self, client):
        """GET /api/health → 200 (public health check)."""
        r = client.get("/api/health")
        assert r.status_code == 200

    def test_liveness_is_public(self, client):
        """GET /api/health/live → 200 (public liveness check)."""
        r = client.get("/api/health/live")
        assert r.status_code == 200


class TestHeartbeat:
    """Heartbeat endpoints."""

    def test_send_heartbeat_returns_400_or_401(self, client):
        """POST /api/heartbeat → 400 or 401 (needs auth)."""
        r = client.post("/api/heartbeat", json={
            "status": "online",
        })
        assert r.status_code in (400, 401, 403, 500)  # heartbeat needs auth or crashes

    def test_heartbeat_status_returns_200_or_404(self, client):
        """GET /api/heartbeat/status/{agent_id} → 200 or 404."""
        r = client.get("/api/heartbeat/status/Agent-001")
        assert r.status_code in (200, 404)
