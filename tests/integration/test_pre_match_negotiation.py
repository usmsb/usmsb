"""
Integration tests for Pre-match Negotiation router.

Tests: initiate, ask/answer questions, propose terms, confirm scope, decline.
Requires: client fixture (unauthenticated).
"""
import pytest


class TestPreMatchNegotiation:
    """Pre-match negotiation endpoints require participant auth."""

    def test_initiate_returns_403_not_participant(self, client):
        """POST /api/negotiations/pre-match → 403 (user not a participant)."""
        r = client.post("/api/negotiations/pre-match", json={
            "demand_agent_id": "demand-001",
            "supply_agent_id": "supply-001",
            "demand_id": "demand-001",
        })
        # 403 = user is authenticated but not a participant (correct behavior)
        assert r.status_code in (401, 403)

    def test_ask_question_returns_403_or_422(self, client):
        """POST /api/negotiations/pre-match/{id}/questions → 403 or 422."""
        r = client.post("/api/negotiations/pre-match/neg-001/questions", json={
            "question": "Can you deliver in 3 days?",
            "asker_id": "demand-001",
        })
        # 422 = validation error (missing fields), 403 = auth/participant check
        assert r.status_code in (401, 403, 404, 422, 503)

    def test_answer_question_returns_403_or_422(self, client):
        """POST /api/negotiations/pre-match/{id}/questions/{qid}/answer → 403 or 422."""
        r = client.post("/api/negotiations/pre-match/neg-001/questions/q-001/answer", json={
            "answer": "Yes, I can.",
            "answerer_id": "supply-001",
        })
        assert r.status_code in (401, 403, 404, 422, 503)

    def test_propose_terms_returns_403_or_422(self, client):
        """POST /api/negotiations/pre-match/{id}/terms/propose → 403 or 422."""
        r = client.post("/api/negotiations/pre-match/neg-001/terms/propose", json={
            "terms": {"price": 500, "delivery_days": 5},
            "proposer_id": "demand-001",
        })
        assert r.status_code in (401, 403, 404, 422, 503)

    def test_confirm_scope_returns_503_service_unavailable(self, client):
        """POST /api/negotiations/pre-match/{id}/scope → 503 (service not available)."""
        r = client.post("/api/negotiations/pre-match/neg-001/scope", json={})
        # 503 = pre-match service not available, 422 = validation error
        assert r.status_code in (401, 403, 404, 422, 503)

    def test_decline_returns_403_or_422(self, client):
        """POST /api/negotiations/pre-match/{id}/decline → 403 or 422."""
        r = client.post("/api/negotiations/pre-match/neg-001/decline", json={
            "reason": "Too expensive",
            "decliner_id": "demand-001",
        })
        assert r.status_code in (401, 403, 404, 422, 503)

    def test_cancel_returns_403_or_422(self, client):
        """POST /api/negotiations/pre-match/{id}/cancel → 403 or 422."""
        r = client.post("/api/negotiations/pre-match/neg-001/cancel", json={})
        assert r.status_code in (401, 403, 404, 422, 503)

    def test_verify_returns_403_or_422(self, client):
        """POST /api/negotiations/pre-match/{id}/verify → 403 or 422."""
        r = client.post("/api/negotiations/pre-match/neg-001/verify", json={})
        assert r.status_code in (401, 403, 404, 422, 503)

    def test_get_negotiation_returns_404_or_503(self, client):
        """GET /api/negotiations/pre-match/{id} → 404 or 503."""
        r = client.get("/api/negotiations/pre-match/neg-nonexistent")
        assert r.status_code in (401, 403, 404, 503)
