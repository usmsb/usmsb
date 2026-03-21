"""
Unit tests for Contracts business logic.

Real Pydantic models: AddRiskRequest, DeclineRequest, DeliveryConfirm.
Prefix: /contracts
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.contracts import (
    AddRiskRequest,
    DeclineRequest,
    DeliveryConfirm,
)


class TestAddRiskRequest:
    def test_valid_request(self):
        r = AddRiskRequest(
            risk_type="delay",
            probability=0.3,
            impact=0.7,
        )
        assert r.risk_type == "delay"
        assert r.probability == 0.3
        assert r.impact == 0.7

    def test_probability_bounded_0_to_1(self):
        with pytest.raises(Exception):
            AddRiskRequest(risk_type="r", probability=-0.1, impact=0.5)
        with pytest.raises(Exception):
            AddRiskRequest(risk_type="r", probability=1.1, impact=0.5)

    def test_impact_bounded_0_to_1(self):
        with pytest.raises(Exception):
            AddRiskRequest(risk_type="r", probability=0.5, impact=-0.1)
        with pytest.raises(Exception):
            AddRiskRequest(risk_type="r", probability=0.5, impact=1.1)

    def test_mitigation_default(self):
        r = AddRiskRequest(risk_type="r", probability=0.3, impact=0.3)
        assert r.mitigation == ""


class TestDeclineRequest:
    def test_reason_default(self):
        r = DeclineRequest()
        assert r.reason == ""

    def test_reason_can_be_set(self):
        r = DeclineRequest(reason="Terms not acceptable")
        assert r.reason == "Terms not acceptable"


class TestDeliveryConfirm:
    def test_quality_approved_required(self):
        r = DeliveryConfirm(quality_approved=True)
        assert r.quality_approved is True

    def test_quality_feedback_default(self):
        r = DeliveryConfirm(quality_approved=False)
        assert r.quality_feedback is None


class TestContractsAuth:
    def test_create_project_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.contracts import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/contracts/project", json={
                "project_name": "Test",
            })
            assert r.status_code in (401, 403)

    def test_decline_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.contracts import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/contracts/c1/decline", json={})
            assert r.status_code in (401, 403)
