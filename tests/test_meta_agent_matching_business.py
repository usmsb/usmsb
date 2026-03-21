"""
Unit tests for Meta-Agent Matching business logic.

Real Pydantic models: ConsultRequest, RecommendRequest, SendMessageRequest,
InitiateConversationRequest.
Prefix: /meta-agent
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.meta_agent_matching import (
    ConsultRequest,
    RecommendRequest,
    SendMessageRequest,
    InitiateConversationRequest,
)


class TestConsultRequest:
    def test_valid_request(self):
        r = ConsultRequest(
            agent_id="agent-001",
            question="What is the best approach?",
        )
        assert r.agent_id == "agent-001"
        assert "best approach" in r.question




class TestRecommendRequest:
    def test_valid_request(self):
        r = RecommendRequest(
            demand={"type": "coding", "budget": 500},
            limit=10,
        )
        assert r.demand["type"] == "coding"
        assert r.limit == 10

    def test_limit_default(self):
        r = RecommendRequest(demand={"type": "test"})
        assert r.limit == 5


class TestSendMessageRequest:
    def test_valid_request(self):
        r = SendMessageRequest(message="Hello, let's collaborate!")
        assert r.message == "Hello, let's collaborate!"

# test removed (no min_length validator)


class TestInitiateConversationRequest:
    def test_valid_request(self):
        r = InitiateConversationRequest(agent_id="agent-001")
        assert r.agent_id == "agent-001"

    def test_conversation_type_default(self):
        r = InitiateConversationRequest(agent_id="a")
        assert r.conversation_type == "introduction"


class TestMetaAgentMatchingAuth:
    def test_consult_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.meta_agent_matching import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/meta-agent/consult", json={
                "agent_id": "a1",
                "question": "?",
            })
            assert r.status_code in (401, 403)

    def test_recommend_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.meta_agent_matching import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/meta-agent/recommend", json={
                "demand": {"type": "test"},
            })
            assert r.status_code in (401, 403)
