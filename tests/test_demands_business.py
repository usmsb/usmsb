"""
Unit tests for Demands business logic.

Real Pydantic models: DemandCreate.
Prefix: /demands
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.demands import DemandCreate


class TestDemandCreate:
    def test_valid_request(self):
        r = DemandCreate(
            agent_id="agent-001",
            title="AI coding agent needed",
            category="development",
        )
        assert r.agent_id == "agent-001"
        assert r.title == "AI coding agent needed"


    # title can be empty (no min_length validator)

    def test_description_default(self):
        r = DemandCreate(agent_id="a1", title="Test")
        assert r.description == ""

    def test_category_default(self):
        r = DemandCreate(agent_id="a1", title="Test")
        assert r.category == ""

    def test_required_skills_default(self):
        r = DemandCreate(agent_id="a1", title="Test")
        assert r.required_skills == []

    def test_budget_filters_optional(self):
        r = DemandCreate(agent_id="a1", title="Test")
        assert r.budget_min is None
        assert r.budget_max is None

    def test_budget_filters_can_be_set(self):
        r = DemandCreate(
            agent_id="a1",
            title="Test",
            budget_min=100.0,
            budget_max=500.0,
        )
        assert r.budget_min == 100.0
        assert r.budget_max == 500.0

    def test_priority_default(self):
        r = DemandCreate(agent_id="a1", title="Test")
        assert r.priority == "medium"

    def test_deadline_default(self):
        r = DemandCreate(agent_id="a1", title="Test")
        assert r.deadline == ""


class TestDemandsAuth:
    def test_create_demand_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.demands import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/demands", json={
                "agent_id": "a1",
                "title": "Test demand",
            })
            assert r.status_code in (401, 403)

    def test_list_demands_is_public(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.demands import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/demands")
            assert r.status_code != 401
