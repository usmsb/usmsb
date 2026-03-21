"""
Unit tests for Heartbeat business logic.

Real Pydantic models: HeartbeatRequest, HeartbeatResponse.
Prefix: /heartbeat
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.heartbeat import HeartbeatRequest, HeartbeatResponse


class TestHeartbeatRequest:
    def test_valid_request(self):
        r = HeartbeatRequest(status="online")
        assert r.status == "online"

    def test_status_default(self):
        r = HeartbeatRequest()
        assert r.status == "online"

    def test_metadata_default(self):
        r = HeartbeatRequest()
        assert r.metadata is None


class TestHeartbeatResponse:
    def test_valid_response(self):
        r = HeartbeatResponse(
            agent_id="agent-001",
            status="online",
            ttl_remaining=60,
            last_heartbeat=1700000000.0,
            is_alive=True,
            message="OK",
        )
        assert r.agent_id == "agent-001"
        assert r.is_alive is True
        assert r.success is True


class TestHeartbeatAuth:
    def test_send_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.heartbeat import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/heartbeat", json={"status": "online"})
            assert r.status_code in (401, 403)

    def test_status_is_public(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.heartbeat import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/heartbeat/status/agent-001")
            assert r.status_code != 401
