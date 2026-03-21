"""
Unit tests for Collaborations business logic.

Real Pydantic models: CollaborationCreateRequest.
Prefix: /collaborations
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.collaborations import CollaborationCreateRequest


class TestCollaborationCreateRequest:
    def test_valid_request(self):
        r = CollaborationCreateRequest(
            goal_description="Build a web app together",
            required_skills=["python", "frontend"],
            coordinator_agent_id="agent-001",
        )
        assert r.goal_description == "Build a web app together"
        assert r.required_skills == ["python", "frontend"]



    def test_collaboration_mode_default(self):
        r = CollaborationCreateRequest(goal_description="Test", required_skills=["x"], coordinator_agent_id="a")
        assert r.collaboration_mode == "hybrid"


class TestCollaborationsAuth:
    def test_create_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.collaborations import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/collaborations", json={
                "goal_description": "Test",
                "required_skills": ["python"],
                "coordinator_agent_id": "a",
            })
            assert r.status_code in (401, 403)
