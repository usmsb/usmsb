"""
Unit tests for USMSB Matching business logic.

Real Pydantic models: BroadcastCapabilityRequest, BroadcastGoalRequest.
Prefix: /usmsb/match
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.usmsb_matching import (
    BroadcastCapabilityRequest,
    BroadcastGoalRequest,
)


class TestBroadcastCapabilityRequest:
    def test_valid_request(self):
        r = BroadcastCapabilityRequest(
            capability="python",
            offering="AI coding assistant",
        )
        assert r.capability == "python"
        assert r.offering == "AI coding assistant"

    def test_capability_can_be_empty(self):
        """No min_length validator on capability field."""
        r = BroadcastCapabilityRequest(capability="", offering="x")
        assert r.capability == ""

    def test_offering_can_be_empty(self):
        """No min_length validator on offering field."""
        r = BroadcastCapabilityRequest(capability="x", offering="")
        assert r.offering == ""


class TestBroadcastGoalRequest:
    def test_valid_request(self):
        r = BroadcastGoalRequest(
            goal="Find AI agent for data processing",
            requirements=["python", "fastapi"],
        )
        assert r.goal == "Find AI agent for data processing"
        assert r.requirements == ["python", "fastapi"]

    def test_goal_can_be_empty(self):
        """No min_length validator on goal field."""
        r = BroadcastGoalRequest(goal="", requirements=[])
        assert r.goal == ""

    def test_requirements_default(self):
        r = BroadcastGoalRequest(goal="Test goal")
        assert r.requirements == []


class TestUsmsbMatchingAuth:
    def test_broadcast_capability_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.usmsb_matching import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/usmsb/match/broadcast/capability", json={
                "capability": "python",
                "offering": "AI agent",
            })
            assert r.status_code in (401, 403)

    def test_broadcast_goal_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.usmsb_matching import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/usmsb/match/broadcast/goal", json={
                "goal": "Find agent",
                "requirements": ["python"],
            })
            assert r.status_code in (401, 403)
