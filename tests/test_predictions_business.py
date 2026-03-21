"""
Unit tests for Predictions business logic.

Real Pydantic model: PredictionRequest.
Prefix: /predict
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.predictions import PredictionRequest


class TestPredictionRequest:
    def test_valid_request(self):
        r = PredictionRequest(
            agent_id="agent-001",
            environment_id="env-001",
            goal_name="data_processing",
        )
        assert r.agent_id == "agent-001"
        assert r.environment_id == "env-001"

    def test_environment_id_optional(self):
        r = PredictionRequest(agent_id="a1")
        assert r.environment_id is None

    def test_goal_name_optional(self):
        r = PredictionRequest(agent_id="a1")
        assert r.goal_name is None

    def test_context_optional(self):
        r = PredictionRequest(agent_id="a1")
        assert r.context is None

    def test_context_can_be_set(self):
        r = PredictionRequest(
            agent_id="a1",
            context={"urgency": "high"},
        )
        assert r.context["urgency"] == "high"


class TestPredictionsAuth:
    """Predictions router prefix is /predict."""

    def test_behavior_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.predictions import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/predict/behavior", json={
                "agent_id": "a1",
            })
            assert r.status_code in (401, 403)

    def test_behavior_endpoint_exists(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.predictions import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/predict/behavior", json={"agent_id": "a1"})
            # Should not be 404
            assert r.status_code != 404
