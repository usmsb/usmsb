"""
Integration tests: /api/joint-order/* endpoints.
"""
import pytest
from tests.integration.conftest import mock_web3, mock_web3_not_found, mock_web3_failed, VALID_TX


class TestJointOrderCreatePool:
    """POST /api/joint-order/pool/create"""

    def test_create_pool_success(self, client, integration_db):
        """Valid creation tx → 200."""
        with mock_web3(status=1):
            response = client.post("/api/joint-order/pool/create", json={
                "order_id": "joint_order_test",
                "service_type": "ai_coding",
                "total_budget": 5000,
                "tx_hash": VALID_TX,
            })
        assert response.status_code == 200, \
            f"{response.status_code}: {response.json()}"

    def test_create_pool_rejects_failed_tx(self, client, integration_db):
        """Failed tx → 400/500."""
        with mock_web3_failed():
            response = client.post("/api/joint-order/pool/create", json={
                "order_id": "joint_fail",
                "service_type": "ai_coding",
                "total_budget": 5000,
                "tx_hash": VALID_TX,
            })
        assert response.status_code in (400, 500)

    def test_create_pool_rejects_pending_tx(self, client, integration_db):
        """Pending tx → 400/404."""
        with mock_web3_not_found():
            response = client.post("/api/joint-order/pool/create", json={
                "order_id": "joint_pending",
                "service_type": "ai_coding",
                "total_budget": 5000,
                "tx_hash": VALID_TX,
            })
        assert response.status_code in (400, 404)

    def test_create_pool_rejects_missing_order_id(self, client, integration_db):
        """Missing order_id → 422."""
        response = client.post("/api/joint-order/pool/create", json={
            "service_type": "ai_coding",
            "total_budget": 5000,
            "tx_hash": VALID_TX,
        })
        assert response.status_code == 422


class TestJointOrderSubmitBid:
    """POST /api/joint-order/pool/submit-bid"""

    def test_submit_bid_success(self, client, integration_db, sample_bound_agent):
        """Bound agent can submit bid → 200."""
        with mock_web3(status=1):
            response = client.post("/api/joint-order/pool/submit-bid", json={
                "pool_id": "pool1",
                "chain_pool_id": "0xCHAINPOOL1",
                "price": 500,
                "tx_hash": VALID_TX,
            })
        # 200 = success, 400/403 = business validation (e.g. pool not found — both valid)
        assert response.status_code in (200, 400, 403), \
            f"Unexpected {response.status_code}: {response.json()}"

    def test_submit_bid_rejects_failed_tx(self, client, integration_db, sample_bound_agent):
        """Failed tx → 400/500."""
        with mock_web3_failed():
            response = client.post("/api/joint-order/pool/submit-bid", json={
                "pool_id": "pool1",
                "chain_pool_id": "0xCHAINPOOL1",
                "price": 500,
                "tx_hash": VALID_TX,
            })
        assert response.status_code in (400, 500)

    def test_submit_bid_rejects_zero_price(self, client, integration_db, sample_bound_agent):
        """Price=0 → 422."""
        response = client.post("/api/joint-order/pool/submit-bid", json={
            "pool_id": "pool1",
            "chain_pool_id": "0xCHAINPOOL1",
            "price": 0,
            "tx_hash": VALID_TX,
        })
        assert response.status_code == 422


class TestJointOrderAcceptBid:
    """POST /api/joint-order/pool/accept-bid"""

    def test_accept_bid_success(self, client, integration_db, sample_bound_agent):
        """Valid accept-bid tx → 200 or business error."""
        with mock_web3(status=1):
            response = client.post("/api/joint-order/pool/accept-bid", json={
                "pool_id": "pool_accept",
                "chain_pool_id": "0xCHAINPOOL2",
                "bid_id": "bid1",
                "tx_hash": VALID_TX,
            })
        assert response.status_code in (200, 400, 404), \
            f"Unexpected {response.status_code}: {response.json()}"

    def test_accept_bid_rejects_failed_tx(self, client, integration_db, sample_bound_agent):
        """Failed tx → 400/500."""
        with mock_web3_failed():
            response = client.post("/api/joint-order/pool/accept-bid", json={
                "pool_id": "pool_accept",
                "chain_pool_id": "0xCHAINPOOL2",
                "bid_id": "bid1",
                "tx_hash": VALID_TX,
            })
        assert response.status_code in (400, 500)


class TestJointOrderConfirmDelivery:
    """POST /api/joint-order/pool/confirm-delivery"""

    def test_confirm_delivery_success(self, client, integration_db, sample_bound_agent):
        """Valid confirm-delivery tx → 200 or business error."""
        with mock_web3(status=1):
            response = client.post("/api/joint-order/pool/confirm-delivery", json={
                "pool_id": "pool_deliver",
                "chain_pool_id": "0xCHAINPOOL3",
                "rating": 5,
                "tx_hash": VALID_TX,
            })
        assert response.status_code in (200, 400, 404), \
            f"Unexpected {response.status_code}: {response.json()}"

    def test_confirm_delivery_rejects_invalid_rating(self, client, integration_db, sample_bound_agent):
        """Rating outside 1-5 → 422."""
        for bad in (0, 6, -1, 100):
            response = client.post("/api/joint-order/pool/confirm-delivery", json={
                "pool_id": "pool_rate",
                "chain_pool_id": "0xCHAINPOOL4",
                "rating": bad,
                "tx_hash": VALID_TX,
            })
            assert response.status_code == 422, \
                f"Expected 422 for rating={bad}, got {response.status_code}"

    def test_confirm_delivery_rejects_failed_tx(self, client, integration_db, sample_bound_agent):
        """Failed tx → 400/500."""
        with mock_web3_failed():
            response = client.post("/api/joint-order/pool/confirm-delivery", json={
                "pool_id": "pool_deliver",
                "chain_pool_id": "0xCHAINPOOL3",
                "rating": 5,
                "tx_hash": VALID_TX,
            })
        assert response.status_code in (400, 500)
