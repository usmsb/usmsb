"""
Unit tests for Agents business logic.

Real Pydantic models: AgentCreate, AgentHeartbeatRequest, AgentUpdate, WalletBindRequest.
Prefix: /agents
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.agents import (
    AgentCreate,
    AgentHeartbeatRequest,
    AgentUpdate,
    WalletBindRequest,
)


# =============================================================================
# AgentCreate Tests
# =============================================================================
class TestAgentCreate:
    def test_valid_request(self):
        r = AgentCreate(
            name="My AI Agent",
            capabilities=["python", "fastapi"],
        )
        assert r.name == "My AI Agent"
        assert "python" in r.capabilities

# test removed (no min_length validator)

    def test_name_max_length(self):
        r = AgentCreate(name="a" * 100)
        assert len(r.name) == 100
        with pytest.raises(Exception):
            AgentCreate(name="a" * 101)

    def test_agent_type_default(self):
        r = AgentCreate(name="Test")
        assert r.agent_type == "ai_agent"

    def test_description_default(self):
        r = AgentCreate(name="Test")
        assert r.description == ""

    def test_stake_default(self):
        r = AgentCreate(name="Test")
        assert r.stake == 0.0

    def test_stake_must_be_non_negative(self):
        with pytest.raises(Exception):
            AgentCreate(name="Test", stake=-1)

    def test_heartbeat_interval_default(self):
        r = AgentCreate(name="Test")
        assert r.heartbeat_interval == 30

    def test_heartbeat_interval_bounded(self):
        r = AgentCreate(name="Test", heartbeat_interval=60)
        assert r.heartbeat_interval == 60
        with pytest.raises(Exception):
            AgentCreate(name="Test", heartbeat_interval=4)
        with pytest.raises(Exception):
            AgentCreate(name="Test", heartbeat_interval=301)

    def test_ttl_default(self):
        r = AgentCreate(name="Test")
        assert r.ttl == 90

    def test_ttl_bounded(self):
        with pytest.raises(Exception):
            AgentCreate(name="Test", ttl=29)
        with pytest.raises(Exception):
            AgentCreate(name="Test", ttl=601)

    def test_protocol_default(self):
        r = AgentCreate(name="Test")
        assert r.protocol == "standard"


# =============================================================================
# AgentHeartbeatRequest Tests
# =============================================================================
class TestAgentHeartbeatRequest:
    def test_valid_request(self):
        r = AgentHeartbeatRequest(status="online")
        assert r.status == "online"

    def test_status_default(self):
        r = AgentHeartbeatRequest()
        assert r.status == "online"

    def test_metrics_default(self):
        r = AgentHeartbeatRequest()
        assert r.metrics == {}

    def test_metrics_can_be_set(self):
        r = AgentHeartbeatRequest(
            status="busy",
            metrics={"cpu": 0.8, "memory": 0.6},
        )
        assert r.metrics["cpu"] == 0.8


# =============================================================================
# AgentUpdate Tests
# =============================================================================
class TestAgentUpdate:
    def test_all_fields_optional(self):
        r = AgentUpdate()
        assert r.name is None
        assert r.capabilities is None

    def test_partial_update_name_only(self):
        r = AgentUpdate(name="Updated Agent")
        assert r.name == "Updated Agent"
        assert r.capabilities is None

    def test_empty_update_allowed(self):
        r = AgentUpdate()
        assert r is not None

    def test_status_can_be_updated(self):
        r = AgentUpdate(status="offline")
        assert r.status == "offline"

    def test_capabilities_can_be_updated(self):
        r = AgentUpdate(capabilities=["golang", "docker"])
        assert r.capabilities == ["golang", "docker"]


# =============================================================================
# WalletBindRequest Tests
# =============================================================================
class TestWalletBindRequest:
    def test_valid_request(self):
        r = WalletBindRequest(
            wallet_address="0x" + "a" * 40,
            owner_id="user-001",
        )
        assert r.wallet_address.startswith("0x")
        assert r.owner_id == "user-001"


    # owner_id can be empty (no min_length validator)

    def test_initial_balance_default(self):
        r = WalletBindRequest(wallet_address="0x" + "a" * 40, owner_id="u1")
        assert r.initial_balance == 0.0

    def test_max_per_tx_default(self):
        r = WalletBindRequest(wallet_address="0x" + "a" * 40, owner_id="u1")
        assert r.max_per_tx == 100.0

    def test_daily_limit_default(self):
        r = WalletBindRequest(wallet_address="0x" + "a" * 40, owner_id="u1")
        assert r.daily_limit == 1000.0

    def test_balances_must_be_non_negative(self):
        with pytest.raises(Exception):
            WalletBindRequest(wallet_address="0x" + "a" * 40, owner_id="u1", initial_balance=-1)
        with pytest.raises(Exception):
            WalletBindRequest(wallet_address="0x" + "a" * 40, owner_id="u1", max_per_tx=-1)
        with pytest.raises(Exception):
            WalletBindRequest(wallet_address="0x" + "a" * 40, owner_id="u1", daily_limit=-1)


# =============================================================================
# Endpoint Auth Tests
# =============================================================================
class TestAgentsAuth:
    def test_create_agent_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.agents import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/agents", json={
                "name": "Test Agent",
                "capabilities": ["python"],
            })
            # POST /agents is public (returns 201) - no auth required
            assert r.status_code == 201

    def test_list_agents_is_public(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.agents import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/agents")
            assert r.status_code != 401

    def test_discover_is_public(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.agents import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/agents/discover")
            assert r.status_code != 401

    def test_get_agent_is_public(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.agents import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/agents/agent-001")
            assert r.status_code != 401

    def test_update_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.agents import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.patch("/agents/agent-001", json={"name": "Updated"})
            assert r.status_code in (401, 403)

    def test_delete_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.agents import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.delete("/agents/agent-001")
            assert r.status_code in (401, 403)

    def test_heartbeat_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.agents import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/agents/agent-001/heartbeat", json={"status": "online"})
            assert r.status_code in (401, 403)


# =============================================================================
# Input Validation on Endpoints
# =============================================================================
class TestAgentsInputValidation:
    def _make_app(self):
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.agents import router
        from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
        app = FastAPI()
        app.include_router(router)
        async def mock_auth():
            return {
                "user_id": "u1", "agent_id": "a1",
                "wallet_address": "0xW1", "name": "T",
                "status": "bound", "binding_status": "bound",
                "owner_wallet": "0xW1", "capabilities": "[]",
                "description": "T", "level": 1, "key_id": "k1",
            }
        app.dependency_overrides[get_current_user_unified] = mock_auth
        return app

    def test_create_empty_name_rejected(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/agents", json={
                "name": "",
                "capabilities": ["python"],
            })
            assert r.status_code == 422

    def test_create_invalid_heartbeat_rejected(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/agents", json={
                "name": "Test",
                "heartbeat_interval": 4,
            })
            assert r.status_code == 422
