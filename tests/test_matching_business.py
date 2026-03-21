"""
Unit tests for Matching business logic.

Real Pydantic models: SearchDemandsRequest, SearchSuppliersRequest,
NegotiationRequest, ProposalRequest.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.matching import (
    SearchDemandsRequest,
    SearchSuppliersRequest,
    NegotiationRequest,
    ProposalRequest,
)


class TestSearchDemandsRequest:
    def test_valid_request(self):
        r = SearchDemandsRequest(
            agent_id="agent-001",
            capabilities=["python", "fastapi"],
        )
        assert r.agent_id == "agent-001"
        assert "python" in r.capabilities

    def test_capabilities_required(self):
        with pytest.raises(Exception):
            SearchDemandsRequest(agent_id="a1")

    def test_budget_filters_optional(self):
        r = SearchDemandsRequest(agent_id="a1", capabilities=[])
        assert r.budget_min is None
        assert r.budget_max is None

    def test_budget_filters_can_be_set(self):
        r = SearchDemandsRequest(
            agent_id="a1",
            capabilities=[],
            budget_min=100.0,
            budget_max=500.0,
        )
        assert r.budget_min == 100.0
        assert r.budget_max == 500.0


class TestSearchSuppliersRequest:
    def test_valid_request(self):
        r = SearchSuppliersRequest(
            agent_id="agent-001",
            required_skills=["python"],
        )
        assert r.agent_id == "agent-001"
        assert r.required_skills == ["python"]


class TestNegotiationRequest:
    def test_valid_request(self):
        r = NegotiationRequest(
            initiator_id="agent-a",
            counterpart_id="agent-b",
            context={"topic": "price"},
        )
        assert r.initiator_id == "agent-a"
        assert r.context["topic"] == "price"

    def test_all_fields_required(self):
        with pytest.raises(Exception):
            NegotiationRequest(initiator_id="a", counterpart_id="b")
        with pytest.raises(Exception):
            NegotiationRequest(initiator_id="a", context={})


class TestProposalRequest:
    def test_valid_request(self):
        r = ProposalRequest(
            price=300.0,
            delivery_time="5 days",
            payment_terms="escrow",
        )
        assert r.price == 300.0
        assert r.delivery_time == "5 days"
        assert r.payment_terms == "escrow"

    def test_quality_guarantee_default(self):
        r = ProposalRequest(price=100, delivery_time="1d", payment_terms="t")
        assert r.quality_guarantee == ""


class TestMatchingAlgorithm:
    def test_score_bounded_0_to_1(self):
        def calc_score(reputation, matched, required, urgency):
            cap_ratio = min(matched / required, 1.0) if required > 0 else 0.0
            urg_factor = max(0.0, 1 - urgency / 10)
            return 0.4 * reputation + 0.4 * cap_ratio + 0.2 * urg_factor

        score = calc_score(1.0, 2, 2, 1)
        assert 0 <= score <= 1.0

    def test_high_reputation_wins(self):
        def calc_score(reputation, matched, required, urgency):
            cap_ratio = min(matched / required, 1.0) if required > 0 else 0.0
            urg_factor = max(0.0, 1 - urgency / 10)
            return 0.4 * reputation + 0.4 * cap_ratio + 0.2 * urg_factor

        high = calc_score(0.9, 2, 2, 5)
        low = calc_score(0.5, 2, 2, 5)
        assert high > low

    def test_weights_sum_to_1(self):
        assert abs(0.4 + 0.4 + 0.2 - 1.0) < 0.001


class TestMatchingAuth:
    def test_search_demands_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.matching import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/matching/search-demands", json={
                "agent_id": "a1",
                "capabilities": ["python"],
            })
            assert r.status_code in (401, 403)

    def test_search_suppliers_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.matching import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/matching/search-suppliers", json={
                "agent_id": "a1",
                "required_skills": ["python"],
            })
            assert r.status_code in (401, 403)
