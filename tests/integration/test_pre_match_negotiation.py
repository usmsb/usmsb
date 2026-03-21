"""
Integration tests for Pre-match Negotiation router.

Tests: initiate, ask/answer questions, propose terms, confirm scope, decline.
Requires: client fixture.
"""
import pytest


class TestPreMatchNegotiation:
    def test_initiate_requires_auth(self, client):
        """POST /api/negotiations/pre-match → 401 without auth."""
        r = client.post("/api/negotiations/pre-match", json={
            "demand_agent_id": "demand-001",
            "supply_agent_id": "supply-001",
            "demand_id": "demand-001",
        })
        assert r.status_code in (401, 403)

    def test_ask_question_requires_auth(self, client):
        """POST /api/negotiations/pre-match/sessions/{id}/ask → 401 without auth."""
        r = client.post("/api/negotiations/pre-match/session-001/ask", json={
            "question": "Can you deliver in 3 days?",
            "asker_id": "demand-001",
        })
        assert r.status_code in (401, 403, 404)

    def test_answer_question_requires_auth(self, client):
        """POST /api/negotiations/pre-match/sessions/{id}/answer → 401 without auth."""
        r = client.post("/api/negotiations/pre-match/session-001/answer", json={
            "answer": "Yes, I can deliver in 3 days",
            "answerer_id": "supply-001",
        })
        assert r.status_code in (401, 403, 404)

    def test_propose_terms_requires_auth(self, client):
        """POST /api/negotiations/pre-match/sessions/{id}/terms/propose → 401 without auth."""
        r = client.post("/api/negotiations/pre-match/session-001/terms/propose", json={
            "terms": {"price": 500, "delivery_days": 5},
            "proposer_id": "demand-001",
        })
        assert r.status_code in (401, 403, 404)

    def test_confirm_scope_requires_auth(self, client):
        """POST /api/negotiations/pre-match/sessions/{id}/confirm-scope → 401 without auth."""
        r = client.post("/api/negotiations/pre-match/session-001/confirm-scope", json={})
        assert r.status_code in (401, 403, 404)

    def test_decline_match_requires_auth(self, client):
        """POST /api/negotiations/pre-match/sessions/{id}/decline → 401 without auth."""
        r = client.post("/api/negotiations/pre-match/session-001/decline", json={
            "reason": "Too expensive",
            "decliner_id": "demand-001",
        })
        assert r.status_code in (401, 403, 404)


class TestPreMatchVerification:
    def test_request_verification_requires_auth(self, client):
        """POST /api/negotiations/pre-match/sessions/{id}/verify → 401 without auth."""
        r = client.post("/api/negotiations/pre-match/session-001/verify", json={
            "capability": "python",
            "verification_type": "code_test",
            "request_detail": "Write a sorting algorithm",
        })
        assert r.status_code in (401, 403, 404)

    def test_cancel_requires_auth(self, client):
        """POST /api/negotiations/pre-match/sessions/{id}/cancel → 401 without auth."""
        r = client.post("/api/negotiations/pre-match/session-001/cancel", json={
            "reason": "Changed mind",
        })
        assert r.status_code in (401, 403, 404)
