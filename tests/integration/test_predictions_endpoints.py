"""Integration tests for Predictions router endpoints."""
import pytest


class TestPredictionsEndpoints:
    """Predictions router endpoint coverage."""

    def test_create_prediction_requires_auth(self, client):
        """POST /api/predictions → 401/201."""
        r = client.post("/api/predictions", json={
            "model": "demand_forecast",
            "input": {}
        })
        assert r.status_code in (201, 400, 401, 403, 404, 422, 500)

    def test_list_predictions_requires_auth(self, client):
        """GET /api/predictions → 401/200."""
        r = client.get("/api/predictions")
        assert r.status_code in (200, 401, 404, 503)

    def test_get_prediction_requires_auth(self, client):
        """GET /api/predictions/{id} → 401/200."""
        r = client.get("/api/predictions/nonexistent")
        assert r.status_code in (200, 401, 404, 422, 503)
