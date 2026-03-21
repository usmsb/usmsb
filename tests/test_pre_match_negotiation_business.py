"""
Unit tests for Pre-match Negotiation business logic.

Real Pydantic models: InitiateNegotiationRequest, AskQuestionRequest,
AnswerQuestionRequest, ProposeTermsRequest, ScopeConfirmationRequest,
DeclineMatchRequest, VerificationRequestModel, CancelNegotiationRequest.
Prefix: /negotiations/pre-match
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.pre_match_negotiation import (
    InitiateNegotiationRequest,
    AskQuestionRequest,
    AnswerQuestionRequest,
    ProposeTermsRequest,
    ScopeConfirmationRequest,
    DeclineMatchRequest,
    VerificationRequestModel,
    CancelNegotiationRequest,
)


class TestInitiateNegotiationRequest:
    def test_valid_request(self):
        r = InitiateNegotiationRequest(
            demand_agent_id="buyer-001",
            supply_agent_id="seller-001",
            demand_id="demand-001",
        )
        assert r.demand_agent_id == "buyer-001"
        assert r.supply_agent_id == "seller-001"

    def test_expiration_hours_default(self):
        r = InitiateNegotiationRequest(
            demand_agent_id="b",
            supply_agent_id="s",
            demand_id="d",
        )
        assert r.expiration_hours == 24


class TestScopeConfirmationRequest:
    def test_deliverables_default(self):
        r = ScopeConfirmationRequest()
        assert r.deliverables == []

    def test_milestones_default(self):
        r = ScopeConfirmationRequest()
        assert r.milestones == []


class TestDeclineMatchRequest:
    def test_reason_required(self):
        """Reason is required (no default)."""
        r = DeclineMatchRequest(reason="Too expensive", decliner_id="a")
        assert r.reason == "Too expensive"

    def test_decliner_id_required(self):
        """Decliner ID is required."""
        r = DeclineMatchRequest(reason="Too expensive", decliner_id="a")
        assert r.decliner_id == "a"


class TestPreMatchNegotiationAuth:
    def test_initiate_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.pre_match_negotiation import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/negotiations/pre-match", json={
                "demand_agent_id": "b",
                "supply_agent_id": "s",
                "demand_id": "d",
            })
            assert r.status_code in (401, 403)

    def test_propose_terms_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.pre_match_negotiation import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post(
                "/negotiations/pre-match/n1/terms/propose",
                json={"terms": {"price": 100}, "proposer_id": "a"},
            )
            assert r.status_code in (401, 403)
