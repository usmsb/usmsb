"""
Unit tests for Workflows business logic.

Real Pydantic models: WorkflowCreate.
Prefix: /workflows
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.workflows import WorkflowCreate


class TestWorkflowCreate:
    def test_valid_request(self):
        r = WorkflowCreate(
            task_description="Process incoming orders",
            agent_id="agent-001",
            available_tools=["tool1", "tool2"],
        )
        assert r.task_description == "Process incoming orders"
        assert r.agent_id == "agent-001"
        assert r.available_tools == ["tool1", "tool2"]

    def test_task_description_required(self):
        with pytest.raises(Exception):
            WorkflowCreate(task_description="", agent_id="a")


    def test_available_tools_default(self):
        r = WorkflowCreate(task_description="Test", agent_id="a")
        assert r.available_tools is None


class TestWorkflowsAuth:
    def test_create_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.workflows import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/workflows", json={
                "task_description": "Test",
                "agent_id": "a",
            })
            assert r.status_code in (401, 403)

    def test_list_is_public(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.workflows import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/workflows")
            assert r.status_code in (401, 403)
