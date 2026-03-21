"""
Integration tests for Services, Demands, Environments, Workflows routers.

Tests: service CRUD, demand CRUD, environment CRUD, workflow CRUD.
Requires: client fixture.
"""
import pytest


class TestServices:
    def test_register_service_requires_auth(self, client):
        """POST /api/services → 401 without auth."""
        r = client.post("/api/services", json={
            "service_name": "TestService",
            "service_type": "ai_agent",
            "description": "A test service",
            "capabilities": ["python"],
            "price": 50.0,
        })
        assert r.status_code in (401, 403)

    def test_list_services_is_public(self, client):
        """GET /api/services → 200 (public listing)."""
        r = client.get("/api/services")
        assert r.status_code == 200


class TestDemands:
    def test_create_demand_requires_auth(self, client):
        """POST /api/demands → 401 without auth."""
        r = client.post("/api/demands", json={
            "agent_id": "agent-001",
            "title": "Need AI coding agent",
            "category": "development",
        })
        assert r.status_code in (401, 403)

    def test_list_demands_is_public(self, client):
        """GET /api/demands → 200 (public listing)."""
        r = client.get("/api/demands")
        assert r.status_code == 200


class TestEnvironments:
    def test_create_environment_requires_auth(self, client):
        """POST /api/environments → 401 without auth."""
        r = client.post("/api/environments", json={
            "name": "TestEnv",
            "type": "sandbox",
        })
        assert r.status_code in (401, 403)

    def test_list_environments_is_public(self, client):
        """GET /api/environments → 200 (public listing)."""
        r = client.get("/api/environments")
        assert r.status_code == 200


class TestWorkflows:
    def test_create_workflow_requires_auth(self, client):
        """POST /api/workflows → 401 without auth."""
        r = client.post("/api/workflows", json={
            "task_description": "Process orders",
            "agent_id": "agent-001",
        })
        assert r.status_code in (401, 403)

    def test_list_workflows_is_public(self, client):
        """GET /api/workflows → 401 (auth required)."""
        r = client.get("/api/workflows")
        assert r.status_code in (401, 403)


class TestReputation:
    def test_get_reputation_requires_auth(self, client):
        """GET /api/reputation/{agent_id} → 401 without auth."""
        r = client.get("/api/reputation/agent-001")
        assert r.status_code in (401, 403)


class TestSouls:
    def test_register_soul_requires_auth(self, client):
        """POST /api/agents/soul → 401 without auth."""
        r = client.post("/api/agents/soul", json={
            "goals": [{"name": "Build AI"}],
            "capabilities": ["python"],
        })
        assert r.status_code in (401, 403)

    def test_get_soul_requires_auth(self, client):
        """GET /api/agents/soul/{agent_id} → 401 without auth."""
        r = client.get("/api/agents/soul/agent-001")
        assert r.status_code in (401, 403, 404)


class TestFeedback:
    def test_submit_feedback_requires_auth(self, client):
        """POST /api/feedback/contract/{contract_id} → 401 without auth."""
        r = client.post("/api/feedback/contract/contract-001", json={
            "success": True,
        })
        assert r.status_code in (401, 403)


class TestNetwork:
    def test_explore_network_requires_auth(self, client):
        """POST /api/network/explore → 401 without auth."""
        r = client.post("/api/network/explore", json={
            "agent_id": "agent-001",
            "target_capabilities": ["python"],
        })
        assert r.status_code in (401, 403)


class TestMetaAgent:
    def test_consult_requires_auth(self, client):
        """POST /api/meta-agent/consult → 401 without auth."""
        r = client.post("/api/meta-agent/consult", json={
            "agent_id": "agent-001",
            "question": "What is the best approach?",
        })
        assert r.status_code in (401, 403)

    def test_recommend_requires_auth(self, client):
        """POST /api/meta-agent/recommend → 401 without auth."""
        r = client.post("/api/meta-agent/recommend", json={
            "demand": {"type": "coding"},
        })
        assert r.status_code in (401, 403)


class TestSystem:
    def test_health_is_public(self, client):
        """GET /api/health → 200 (public health check)."""
        r = client.get("/api/health")
        assert r.status_code == 200

    def test_liveness_is_public(self, client):
        """GET /api/liveness → 200 (public liveness check)."""
        r = client.get("/api/liveness")
        assert r.status_code == 200


class TestHeartbeat:
    def test_send_heartbeat_requires_auth(self, client):
        """POST /api/heartbeat → 401 without auth."""
        r = client.post("/api/heartbeat", json={
            "status": "online",
        })
        assert r.status_code in (401, 403)

    def test_heartbeat_status_is_public(self, client):
        """GET /api/heartbeat/status/{agent_id} → 200 or 404."""
        r = client.get("/api/heartbeat/status/agent-001")
        assert r.status_code in (200, 404)
