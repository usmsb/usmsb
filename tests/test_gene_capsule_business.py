"""
Unit tests for Gene Capsule business logic.

Prefix: /gene-capsule
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestGeneCapsuleAuth:
    def test_get_capsule_endpoint_exists(self):
        """GET /gene-capsule/{agent_id} exists (returns 503 service unavailable)."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.gene_capsule import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/gene-capsule/agent-001")
            # 503 = service unavailable (route exists but service not initialized)
            # 404 = not found (wrong path)
            assert r.status_code != 404, "Endpoint should exist"

    def test_search_requires_auth(self):
        """POST /gene-capsule/experiences requires auth."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.gene_capsule import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/gene-capsule/experiences", json={"query": "python"})
            assert r.status_code in (401, 403)
