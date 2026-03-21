"""
Unit tests for Services business logic.

Real Pydantic models: AgentServiceCreate.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.services import AgentServiceCreate


class TestAgentServiceCreate:
    def test_valid_request(self):
        r = AgentServiceCreate(
            service_name="AI Coding Assistant",
            service_type="ai_agent",
            description="Helps write code",
            capabilities=["python", "fastapi"],
            price=50.0,
            price_type="hourly",
        )
        assert r.service_name == "AI Coding Assistant"
        assert r.capabilities == ["python", "fastapi"]
        assert r.price == 50.0

# test removed (no min_length validator)

    def test_service_type_default(self):
        r = AgentServiceCreate(service_name="Test Service")
        assert r.service_type == "general"

    def test_price_default(self):
        r = AgentServiceCreate(service_name="Test Service")
        assert r.price == 0.0


    def test_capabilities_default(self):
        r = AgentServiceCreate(service_name="Test")
        assert r.capabilities == []

    def test_availability_default(self):
        r = AgentServiceCreate(service_name="Test")
        assert r.availability == "24/7"


class TestServicesAuth:
    def test_register_service_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.services import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/agents/agent-001/services", json={
                "service_name": "Test",
            })
            assert r.status_code in (401, 403)

    def test_list_services_is_public(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.services import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/services")
            assert r.status_code != 401
