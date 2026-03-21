"""
Unit tests for Reputation business logic.

Real Pydantic models: ReputationEvent, ReputationResponse.
Prefix: /reputation
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.reputation import (
    ReputationEvent,
    ReputationResponse,
)


class TestReputationEvent:
    def test_valid_event(self):
        r = ReputationEvent(
            timestamp=1700000000.0,
            event_type="transaction_completed",
            change=5.0,
            reason="Good service delivery",
        )
        assert r.event_type == "transaction_completed"
        assert r.change == 5.0

    def test_negative_change_allowed(self):
        r = ReputationEvent(
            timestamp=1700000000.0,
            event_type="dispute_lost",
            change=-10.0,
            reason="Customer complaint",
        )
        assert r.change == -10.0


class TestReputationResponse:
    def test_valid_response(self):
        r = ReputationResponse(
            agent_id="agent-001",
            score=85.5,
            tier="gold",
            total_transactions=50,
            successful_transactions=48,
            success_rate=0.96,
            avg_rating=4.8,
            total_ratings=48,
        )
        assert r.tier == "gold"
        assert r.success is True


class TestReputationAuth:
    """Reputation router has GET-only endpoints."""

    def test_get_reputation_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.reputation import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/reputation?agent_id=agent-001")
            assert r.status_code in (401, 403)
