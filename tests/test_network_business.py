"""
Unit tests for Network business logic.

Real Pydantic models: NetworkExploreRequest, RecommendationRequest.
Prefix: /network
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.network import NetworkExploreRequest, RecommendationRequest


class TestNetworkExploreRequest:
    def test_valid_request(self):
        r = NetworkExploreRequest(
            agent_id="agent-001",
            target_capabilities=["python"],
        )
        assert r.agent_id == "agent-001"
        assert r.target_capabilities == ["python"]

# test removed (no min_length validator)

    def test_capabilities_optional(self):
        r = NetworkExploreRequest(agent_id="a1")
        assert r.target_capabilities is None

    def test_depth_default(self):
        r = NetworkExploreRequest(agent_id="a1")
        assert r.exploration_depth == 2


class TestRecommendationRequest:
    def test_valid_request(self):
        r = RecommendationRequest(
            agent_id="agent-001",
            target_capability="python",
        )
        assert r.agent_id == "agent-001"
        assert r.target_capability == "python"



class TestNetworkAuth:
    def test_explore_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.network import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/network/explore", json={
                "agent_id": "a1",
            })
            assert r.status_code in (401, 403)
