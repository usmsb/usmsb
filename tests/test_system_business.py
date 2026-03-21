"""
Unit tests for System business logic.

Real Pydantic models: HealthResponse.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.system import HealthResponse


class TestHealthResponse:
    def test_valid_response(self):
        r = HealthResponse(
            status="healthy",
            version="1.0.0",
            timestamp=1700000000.0,
            services={"db": "ok", "cache": "ok"},
        )
        assert r.status == "healthy"
        assert r.version == "1.0.0"

    def test_all_fields_required(self):
        with pytest.raises(Exception):
            HealthResponse(status="ok", version="1.0")


class TestSystemAuth:
    def test_health_is_public(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.system import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/health")
            assert r.status_code != 401

    def test_liveness_is_public(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.system import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/liveness")
            assert r.status_code != 401
