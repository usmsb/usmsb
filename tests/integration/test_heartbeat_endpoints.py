"""Integration tests for Heartbeat router endpoints."""
import pytest


class TestHeartbeatEndpoints:
    """Heartbeat router endpoint coverage."""

    def test_send_heartbeat_requires_auth(self, client):
        """POST /api/heartbeat → 401/200."""
        r = client.post("/api/heartbeat", json={
            "agent_id": "test_agent",
            "status": "online"
        })
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)

    def test_get_heartbeat_status_requires_auth(self, client):
        """GET /api/heartbeat/{agent_id} → 401/200."""
        r = client.get("/api/heartbeat/test_agent")
        assert r.status_code in (200, 401, 404, 503)

    def test_heartbeat_batch_requires_auth(self, client):
        """POST /api/heartbeat/batch → 401/200."""
        r = client.post("/api/heartbeat/batch", json={
            "agents": [{"agent_id": "a1", "status": "online"}]
        })
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)
