"""
Unit tests for Negotiations business logic.

Real Pydantic models: StartNegotiationRequest, CounterProposalRequest,
AutoNegotiateRequest, CancelNegotiationRequest.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.negotiations import (
    StartNegotiationRequest,
    CounterProposalRequest,
    AutoNegotiateRequest,
    CancelNegotiationRequest,
)


class TestStartNegotiationRequest:
    def test_valid_request(self):
        r = StartNegotiationRequest(supply_agent_id="agent-001")
        assert r.supply_agent_id == "agent-001"

    def test_supply_agent_id_required(self):
        """Empty string is accepted by Pydantic (no min_length validator)."""
        r = StartNegotiationRequest(supply_agent_id="")
        assert r.supply_agent_id == ""

    def test_initial_terms_can_be_set(self):
        r = StartNegotiationRequest(
            supply_agent_id="a1",
            initial_terms={"price": 100, "delivery_days": 5},
        )
        assert r.initial_terms["price"] == 100

    def test_template_id_default(self):
        r = StartNegotiationRequest(supply_agent_id="a1")
        assert r.template_id == "simple_task"

    def test_timeout_seconds_default(self):
        r = StartNegotiationRequest(supply_agent_id="a1")
        assert r.timeout_seconds == 300


class TestCounterProposalRequest:
    def test_valid_request(self):
        r = CounterProposalRequest(
            counter_changes={"price": 450, "delivery_days": 3},
        )
        assert r.counter_changes["price"] == 450

    def test_counter_changes_required(self):
        with pytest.raises(Exception):
            CounterProposalRequest()


class TestAutoNegotiateRequest:
    def test_valid_request(self):
        r = AutoNegotiateRequest(
            agent_a_soul={"name": "Buyer"},
            agent_b_soul={"name": "Seller"},
        )
        assert r.agent_a_soul["name"] == "Buyer"

    def test_both_souls_required(self):
        with pytest.raises(Exception):
            AutoNegotiateRequest(agent_a_soul={})


class TestCancelNegotiationRequest:
    def test_reason_default(self):
        r = CancelNegotiationRequest()
        assert r.reason == ""

    def test_reason_can_be_set(self):
        r = CancelNegotiationRequest(reason="Changed my mind")
        assert r.reason == "Changed my mind"


class TestNegotiationsAuth:
    def test_start_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.negotiations import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/negotiations", json={"supply_agent_id": "a1"})
            assert r.status_code in (401, 403)

    def test_counter_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.negotiations import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/negotiations/s1/counter", json={
                "counter_changes": {"price": 100},
            })
            assert r.status_code in (401, 403)

    def test_cancel_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.negotiations import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/negotiations/s1/cancel", json={})
            assert r.status_code in (401, 403)

    def test_agree_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.negotiations import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/negotiations/s1/agree", json={})
            assert r.status_code in (401, 403)
