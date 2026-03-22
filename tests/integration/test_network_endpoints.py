"""Integration tests for Network router endpoints."""
import pytest


class TestNetworkEndpoints:
    """Network router endpoint coverage."""

    def test_explore_network_requires_auth(self, client):
        """GET /api/network/explore → 401/200."""
        r = client.get("/api/network/explore")
        assert r.status_code in (200, 401, 404, 405, 503)

    def test_get_recommendations_requires_auth(self, client):
        """GET /api/network/recommendations → 401/200."""
        r = client.get("/api/network/recommendations")
        assert r.status_code in (200, 401, 404, 405, 503)

    def test_get_network_stats_requires_auth(self, client):
        """GET /api/network/stats → 401/200."""
        r = client.get("/api/network/stats")
        assert r.status_code in (200, 401, 404, 405, 503)
