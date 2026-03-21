"""
Unit tests for Learning business logic.

No Pydantic request models - endpoints use function parameters directly.
Prefix: /learning
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestLearningAuth:
    """Learning endpoints all require auth."""

    def test_analyze_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.learning import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/learning/analyze", json={})
            assert r.status_code in (401, 403)

    def test_insights_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.learning import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/learning/insights")
            assert r.status_code in (401, 403)

    def test_strategy_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.learning import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/learning/strategy")
            assert r.status_code in (401, 403)

    def test_market_insight_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.learning import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/learning/market")
            assert r.status_code in (401, 403)


class TestLearningEndpointRegistration:
    """All expected learning endpoints are registered."""

    def test_analyze_endpoint_exists(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.learning import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/learning/analyze", json={})
            # Should not be 404
            assert r.status_code != 404

    def test_insights_endpoint_exists(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.learning import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/learning/insights")
            assert r.status_code != 404
