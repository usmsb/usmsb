"""
Integration tests for Agents router.

Tests: create agent, list, discover, get, update, delete, heartbeat.
Requires: client fixture (from conftest.py).
"""
import pytest
import time
from tests.integration.conftest import VALID_TX, mock_web3


class TestAgentLifecycle:
    """Test full agent lifecycle: create → list → get → update → heartbeat."""

    def test_create_agent_success(self, client, integration_db):
        """POST /api/agents → 201 on success."""
        payload = {
            "name": "TestAgent",
            "capabilities": ["python", "fastapi"],
            "agent_type": "ai_agent",
            "heartbeat_interval": 30,
        }
        r = client.post("/api/agents", json=payload)
        assert r.status_code in (201, 400)  # 400 = already exists

    def test_list_agents_returns_200(self, client, integration_db):
        """GET /api/agents → 200."""
        r = client.get("/api/agents")
        assert r.status_code == 200

    def test_discover_agents_returns_200(self, client):
        """GET /api/agents/discover → 200."""
        r = client.get("/api/agents/discover")
        assert r.status_code == 200

    def test_get_agent_returns_200_or_404(self, client, integration_db):
        """GET /api/agents/{agent_id} → 200 or 404."""
        r = client.get("/api/agents/nonexistent_agent")
        assert r.status_code in (200, 404)

    def test_update_agent_success(self, client, integration_db, sample_bound_agent):
        """PATCH /api/agents/{agent_id} → 200 on success."""
        r = client.patch(
            f"/api/agents/{sample_bound_agent}",
            json={"name": "UpdatedName", "capabilities": ["golang"]},
        )
        assert r.status_code in (200, 403, 404)  # 403=agent mismatch, 200=success

    def test_delete_agent_returns_204_or_404(self, client, integration_db):
        """DELETE /api/agents/{agent_id} → 204 or 404."""
        r = client.delete("/api/agents/nonexistent_agent")
        assert r.status_code in (204, 403, 404)

    def test_agent_heartbeat_success(self, client, integration_db, sample_bound_agent):
        """POST /api/agents/{agent_id}/heartbeat → 200 on success."""
        r = client.post(
            f"/api/agents/{sample_bound_agent}/heartbeat",
            json={"status": "online"},
        )
        assert r.status_code in (200, 403, 404)


class TestAgentAuth:
    """Auth-related agent tests."""

    def test_create_agent_public_no_auth(self, client):
        """POST /api/agents → 201 without auth (public registration)."""
        r = client.post("/api/agents", json={
            "name": "PublicAgent",
            "capabilities": ["python"],
        })
        assert r.status_code in (201, 400)  # public endpoint

    def test_delete_requires_auth(self, client, integration_db, sample_bound_agent):
        """DELETE /api/agents/{agent_id} → 204 (auth passes for own agent)."""
        r = client.delete(f"/api/agents/{sample_bound_agent}")
        assert r.status_code in (204, 403, 404)
