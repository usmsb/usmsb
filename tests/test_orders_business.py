"""
Unit tests for Orders business logic.

Real Pydantic models: CreateOrderFromPreMatchRequest,
CreateOrderFromNegotiationRequest, SubmitDeliverableRequest,
AcceptDeliverableRequest, RaiseDisputeRequest, CancelOrderRequest.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.orders import (
    CreateOrderFromPreMatchRequest,
    CreateOrderFromNegotiationRequest,
    SubmitDeliverableRequest,
    AcceptDeliverableRequest,
    RaiseDisputeRequest,
    CancelOrderRequest,
    MAX_ORDER_PRICE,
)


class TestCreateOrderFromPreMatchRequest:
    def test_valid_request(self):
        r = CreateOrderFromPreMatchRequest(negotiation_id="neg-001")
        assert r.negotiation_id == "neg-001"

    def test_task_description_optional(self):
        r = CreateOrderFromPreMatchRequest(negotiation_id="n1")
        assert r.task_description is None


class TestCreateOrderFromNegotiationRequest:
    def test_valid_request(self):
        r = CreateOrderFromNegotiationRequest(
            negotiation_session_id="ns-001",
            price=500.0,
            task_description="Build a web app",
            demand_agent_id="buyer-001",
            supply_agent_id="seller-001",
        )
        assert r.price == 500.0

    def test_price_le_max_order_price(self):
        """Price must be <= MAX_ORDER_PRICE (1_000_000)."""
        r = CreateOrderFromNegotiationRequest(
            negotiation_session_id="ns-001",
            price=1_000_000.0,
            task_description="Big project",
            demand_agent_id="a",
            supply_agent_id="b",
        )
        assert r.price <= MAX_ORDER_PRICE

    def test_payment_terms_default(self):
        r = CreateOrderFromNegotiationRequest(
            negotiation_session_id="n1",
            price=100,
            task_description="t",
            demand_agent_id="a",
            supply_agent_id="b",
        )
        assert r.payment_terms == "escrow"

    def test_milestones_default(self):
        r = CreateOrderFromNegotiationRequest(
            negotiation_session_id="n1",
            price=100,
            task_description="t",
            demand_agent_id="a",
            supply_agent_id="b",
        )
        assert r.milestones == []


class TestSubmitDeliverableRequest:
    def test_valid_request(self):
        r = SubmitDeliverableRequest(
            description="Completed web app",
            artifact_type="zip",
            url_or_content="https://example.com/output.zip",
        )
        assert r.description == "Completed web app"

    def test_artifact_type_default(self):
        r = SubmitDeliverableRequest(description="Done")
        assert r.artifact_type == "text"


class TestAcceptDeliverableRequest:
    def test_valid_rating_1_to_5(self):
        for rating in range(1, 6):
            r = AcceptDeliverableRequest(rating=rating)
            assert r.rating == rating

    def test_rating_0_invalid(self):
        with pytest.raises(Exception):
            AcceptDeliverableRequest(rating=0)

    def test_rating_6_invalid(self):
        with pytest.raises(Exception):
            AcceptDeliverableRequest(rating=6)


class TestMaxOrderPrice:
    def test_max_order_price(self):
        assert MAX_ORDER_PRICE == 1_000_000.0


class TestOrdersAuth:
    def test_create_from_prematch_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.orders import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/orders/from-pre-match", json={
                "negotiation_id": "n1",
            })
            assert r.status_code in (401, 403)

    def test_create_from_negotiation_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.orders import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/orders/from-negotiation", json={
                "negotiation_session_id": "ns1",
                "price": 100,
                "task_description": "t",
                "demand_agent_id": "a",
                "supply_agent_id": "b",
            })
            assert r.status_code in (401, 403)

    def test_confirm_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.orders import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/orders/o1/confirm", json={})
            assert r.status_code in (401, 403)
