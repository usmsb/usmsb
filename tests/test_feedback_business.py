"""
Unit tests for Feedback business logic.

Real Pydantic models: ContractFeedbackRequest.
Prefix: /feedback
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.feedback import ContractFeedbackRequest


class TestContractFeedbackRequest:
    def test_valid_request(self):
        r = ContractFeedbackRequest(success=True)
        assert r.success is True

    def test_quality_score_default(self):
        r = ContractFeedbackRequest(success=True)
        assert r.quality_score == 0.8

    def test_quality_score_bounded(self):
        with pytest.raises(Exception):
            ContractFeedbackRequest(success=True, quality_score=-0.1)
        with pytest.raises(Exception):
            ContractFeedbackRequest(success=True, quality_score=1.1)

    def test_delivery_data_default(self):
        r = ContractFeedbackRequest(success=True)
        assert r.delivery_data == {}

    def test_issues_default(self):
        r = ContractFeedbackRequest(success=True)
        assert r.issues == []


class TestFeedbackAuth:
    def test_process_feedback_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.feedback import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/feedback/contract/c1", json={"success": True})
            assert r.status_code in (401, 403)
