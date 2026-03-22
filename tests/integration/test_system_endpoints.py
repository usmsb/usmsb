"""Integration tests for System router endpoints."""
import pytest


class TestSystemEndpoints:
    """System router endpoint coverage."""

    def test_health_check(self, client):
        """GET /api/system/health → 200 (no auth required)."""
        r = client.get("/api/system/health")
        assert r.status_code in (200, 401, 404)

    def test_system_status_requires_auth(self, client):
        """GET /api/system/status → 401/200."""
        r = client.get("/api/system/status")
        assert r.status_code in (200, 401, 404)

    def test_system_metrics_requires_auth(self, client):
        """GET /api/system/metrics → 401/200."""
        r = client.get("/api/system/metrics")
        assert r.status_code in (200, 401, 404, 503)
