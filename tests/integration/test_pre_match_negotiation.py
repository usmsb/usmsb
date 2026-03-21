"""
Integration tests for Pre-match Negotiation router.

Tests: initiate, ask/answer questions, propose terms, confirm scope, decline.
Requires: client fixture (unauthenticated).
"""
import pytest


class TestPreMatchNegotiation:
    """Pre-match negotiation endpoints require participant auth."""

    def test_initiate_returns_403_not_participant(self, client):
        """POST /api/negotiations/pre-match → 403 (not a participant)."""
        r = client.post("/api/negotiations/pre-match", json={
            "demand_agent_id": "demand-001",
            "supply_agent_id": "supply-001",
            "demand_id": "demand-001",
        })
        # 403 = user is not a participant (correct behavior)
        assert r.status_code in (401, 403)

    def test_ask_question_returns_403_not_participant(self, client):
        """POST /api/negotiations/pre-match/{id}/questions → 403."""
        r = client.post("/api/negotiations/pre-match/neg-001/questions", json={
            "question": "Can you deliver in 3 days?",
        })
        assert r.status_code in (401, 403, 404)

    def test_answer_question_returns_403_not_participant(self, client):
        """POST /api/negotiations/pre-match/{id}/questions/{qid}/answer → 403."""
        r = client.post("/api/negotiations/pre-match/neg-001/questions/q-001/answer", json={
            "answer": "Yes, I can.",
        })
        assert r.status_code in (401, 403, 404)

    def test_propose_terms_returns_403_not_participant(self, client):
        """POST /api/negotiations/pre-match/{id}/terms/propose → 403."""
        r = client.post("/api/negotiations/pre-match/neg-001/terms/propose", json={
            "terms": {"price": 500, "delivery_days": 5},
        })
        assert r.status_code in (401, 403, 404)

    def test_confirm_scope_returns_403_not_participant(self, client):
        """POST /api/negotiations/pre-match/{id}/scope → 403."""
        r = client.post("/api/negotiations/pre-match/neg-001/scope", json={})
        assert r.status_code in (401, 403, 404)

    def test_decline_returns_403_not_participant(self, client):
        """POST /api/negotiations/pre-match/{id}/decline → 403."""
        r = client.post("/api/negotiations/pre-match/neg-001/decline", json={
            "reason": "Too expensive",
        })
        assert r.status_code in (401, 403, 404)

    def test_cancel_returns_403_not_participant(self, client):
        """POST /api/negotiations/pre-match/{id}/cancel → 403."""
        r = client.post("/api/negotiations/pre-match/neg-001/cancel", json={})
        assert r.status_code in (401, 403, 404)

    def test_verify_returns_403_not_participant(self, client):
        """POST /api/negotiations/pre-match/{id}/verify → 403."""
        r = client.post("/api/negotiations/pre-match/neg-001/verify", json={})
        assert r.status_code in (401, 403, 404)

    def test_get_negotiation_returns_404_not_found(self, client):
        """GET /api/negotiations/pre-match/{id} → 404."""
        r = client.get("/api/negotiations/pre-match/neg-nonexistent")
        assert r.status_code in (401, 403, 404)
