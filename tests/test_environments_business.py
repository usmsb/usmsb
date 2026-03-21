"""
Unit tests for Environments business logic.

Real Pydantic models: EnvironmentCreate.
Prefix: /environments
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.environments import EnvironmentCreate


class TestEnvironmentCreate:
    def test_valid_request(self):
        r = EnvironmentCreate(name="Test Env", type="sandbox")
        assert r.name == "Test Env"
        assert r.type == "sandbox"

    def test_name_required(self):
        with pytest.raises(Exception):
            EnvironmentCreate(name="")

    def test_type_default(self):
        r = EnvironmentCreate(name="Test")
        assert r.type == "social"

    def test_state_default(self):
        r = EnvironmentCreate(name="Test")
        assert r.state == {}


class TestEnvironmentsAuth:
    def test_create_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.environments import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/environments", json={"name": "Test"})
            assert r.status_code in (401, 403)

    def test_list_is_public(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.environments import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/environments")
            assert r.status_code != 401
