"""
Unit tests for Blockchain business logic.

Tests:
- Pydantic model validation (TransferRequest, ApproveRequest, etc.)
- Response model construction
- Endpoint auth requirements (public vs protected)
- Input validation
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.blockchain import (
    TransferRequest,
    TransferResponse,
    ApproveRequest,
    ApproveResponse,
    TokenBalanceResponse,
    BlockchainStatusResponse,
    TransactionStatusResponse,
    GasEstimateResponse,
)


# =============================================================================
# TransferRequest Tests
# =============================================================================
class TestTransferRequest:
    def test_valid_request(self):
        r = TransferRequest(to="0x" + "a" * 40, amount=100.0)
        assert r.to.startswith("0x")
        assert r.amount == 100.0

    def test_amount_must_be_positive(self):
        with pytest.raises(Exception):
            TransferRequest(to="0x" + "a" * 40, amount=0)
        with pytest.raises(Exception):
            TransferRequest(to="0x" + "a" * 40, amount=-50)

    def test_amount_can_be_decimal(self):
        r = TransferRequest(to="0x" + "a" * 40, amount=0.5)
        assert r.amount == 0.5

    def test_to_address_format(self):
        r = TransferRequest(to="0x" + "b" * 40, amount=10.0)
        assert len(r.to) == 42


# =============================================================================
# ApproveRequest Tests
# =============================================================================
class TestApproveRequest:
    def test_valid_request(self):
        r = ApproveRequest(spender="0x" + "a" * 40, amount=500.0)
        assert r.spender.startswith("0x")
        assert r.amount == 500.0

    def test_zero_amount_revokes_approval(self):
        """amount=0 means revoke approval."""
        r = ApproveRequest(spender="0x" + "a" * 40, amount=0)
        assert r.amount == 0

    def test_amount_must_be_positive_or_zero(self):
        with pytest.raises(Exception):
            ApproveRequest(spender="0x" + "a" * 40, amount=-1)


# =============================================================================
# Response Models Tests
# =============================================================================
class TestBlockchainResponses:
    def test_transfer_response_success(self):
        r = TransferResponse(
            success=True,
            tx_hash="0x" + "a" * 64,
            from_address="0x" + "a" * 40,
            to_address="0x" + "b" * 40,
            amount_vibe=100.0,
            message="Transfer successful",
        )
        assert r.success is True
        assert r.amount_vibe == 100.0

    def test_transfer_response_failure(self):
        r = TransferResponse(
            success=False,
            tx_hash="0x" + "a" * 64,
            from_address="0x" + "a" * 40,
            to_address="0x" + "b" * 40,
            amount_vibe=0,
            message="Transfer failed",
        )
        assert r.success is False

    def test_approve_response(self):
        r = ApproveResponse(
            success=True,
            tx_hash="0x" + "a" * 64,
            owner="0x" + "a" * 40,
            spender="0x" + "b" * 40,
            amount_vibe=200.0,
            message="Approval granted",
        )
        assert r.success is True
        assert r.amount_vibe == 200.0

    def test_token_balance_response(self):
        r = TokenBalanceResponse(
            address="0x" + "a" * 40,
            balance_wei=1_000_000_000_000_000_000,
            balance_vibe=1.0,
        )
        assert r.balance_vibe == 1.0
        assert r.balance_wei == 10**18

    def test_blockchain_status_response(self):
        r = BlockchainStatusResponse(
            connected=True,
            chain_id=84532,
            network_name="Base Sepolia",
            block_number=12345678,
            token_address="0x" + "a" * 40,
            token_name="VibeToken",
            token_symbol="VIBE",
        )
        assert r.connected is True
        assert r.chain_id == 84532

    def test_transaction_status_response_pending(self):
        r = TransactionStatusResponse(
            task_id="task-001",
            status="pending",
            tx_hash="0x" + "a" * 64,
            from_address="0x" + "a" * 40,
            to_address="0x" + "b" * 40,
            amount_vibe=50.0,
            created_at=1700000000.0,
            updated_at=1700000000.0,
        )
        assert r.status == "pending"
        assert r.task_id == "task-001"

    def test_gas_estimate_response(self):
        r = GasEstimateResponse(
            function="transfer",
            gas_estimate=21000,
            gas_price_wei=1000000000,
            gas_price_gwei=1.0,
            estimated_cost_wei=21000000000000,
            estimated_cost_vibe=0.000021,
        )
        assert r.gas_estimate == 21000
        assert r.gas_price_gwei == 1.0


# =============================================================================
# Endpoint Auth Tests
# =============================================================================
class TestBlockchainAuth:
    """Test blockchain endpoints: public (no auth) vs protected (auth required)."""

    def _make_app(self):
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.blockchain import router
        from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
        app = FastAPI()
        app.include_router(router)
        async def mock_auth():
            return {
                "user_id": "user1", "agent_id": "agent1",
                "wallet_address": "0xWALLET1", "name": "TestUser",
                "status": "bound", "binding_status": "bound",
                "owner_wallet": "0xWALLET1", "capabilities": "[]",
                "description": "Test", "level": 1, "key_id": "key1",
            }
        app.dependency_overrides[get_current_user_unified] = mock_auth
        return app

    def test_get_status_public(self):
        """GET /blockchain/status is public."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.blockchain import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/blockchain/status")
            # Should NOT be 401/403
            assert r.status_code not in (401, 403)

    def test_transfer_requires_auth(self):
        """POST /blockchain/transfer requires auth."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.blockchain import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/blockchain/transfer", json={
                "to": "0x" + "a" * 40,
                "amount": 100.0,
            })
            assert r.status_code in (401, 403)

    def test_approve_requires_auth(self):
        """POST /blockchain/approve requires auth."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.blockchain import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.post("/blockchain/approve", json={
                "spender": "0x" + "a" * 40,
                "amount": 100.0,
            })
            assert r.status_code in (401, 403)

    def test_balance_requires_auth(self):
        """GET /blockchain/balance/{address} requires auth."""
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.blockchain import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/blockchain/balance/0x" + "a" * 40)
            assert r.status_code in (401, 403)

    def test_transfer_accepts_auth(self):
        """POST /blockchain/transfer with auth passes auth layer."""
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/blockchain/transfer", json={
                "to": "0x" + "a" * 40,
                "amount": 100.0,
            })
            # Should NOT be 401/403 (passed auth)
            assert r.status_code not in (401, 403)

    def test_approve_accepts_auth(self):
        """POST /blockchain/approve with auth passes auth layer."""
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/blockchain/approve", json={
                "spender": "0x" + "a" * 40,
                "amount": 100.0,
            })
            assert r.status_code not in (401, 403)


# =============================================================================
# Input Validation on Endpoints
# =============================================================================
class TestBlockchainInputValidation:
    """Test endpoint-level input validation."""

    def _make_app(self):
        from fastapi import FastAPI
        from usmsb_sdk.api.rest.routers.blockchain import router
        from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
        app = FastAPI()
        app.include_router(router)
        async def mock_auth():
            return {
                "user_id": "user1", "agent_id": "agent1",
                "wallet_address": "0xWALLET1", "name": "TestUser",
                "status": "bound", "binding_status": "bound",
                "owner_wallet": "0xWALLET1", "capabilities": "[]",
                "description": "Test", "level": 1, "key_id": "key1",
            }
        app.dependency_overrides[get_current_user_unified] = mock_auth
        return app

    def test_transfer_rejects_zero_amount(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/blockchain/transfer", json={
                "to": "0x" + "a" * 40,
                "amount": 0,
            })
            assert r.status_code == 422

    def test_transfer_rejects_negative_amount(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/blockchain/transfer", json={
                "to": "0x" + "a" * 40,
                "amount": -10,
            })
            assert r.status_code == 422

    def test_approve_rejects_zero_amount_valid(self):
        """amount=0 is valid (revoke approval)."""
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/blockchain/approve", json={
                "spender": "0x" + "a" * 40,
                "amount": 0,
            })
            # Should NOT be 422 (valid)
            assert r.status_code != 422

    def test_transfer_rejects_missing_amount(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/blockchain/transfer", json={
                "to": "0x" + "a" * 40,
            })
            assert r.status_code == 422

    def test_approve_rejects_missing_spender(self):
        from fastapi.testclient import TestClient
        app = self._make_app()
        with TestClient(app) as client:
            r = client.post("/blockchain/approve", json={
                "amount": 100.0,
            })
            assert r.status_code == 422


# =============================================================================
# Transaction Tracking Logic
# =============================================================================
class TestTransactionTracking:
    """Test in-memory transaction tracking functions."""

    def test_task_id_format(self):
        """_create_task_id returns unique string."""
        from usmsb_sdk.api.rest.routers.blockchain import _create_task_id
        id1 = _create_task_id()
        id2 = _create_task_id()
        assert id1 != id2
        assert isinstance(id1, str)
        assert len(id1) > 0

    def test_store_transaction_returns_dict(self):
        """_store_transaction stores and returns tx info."""
        from usmsb_sdk.api.rest.routers.blockchain import _store_transaction
        task_id = _store_transaction(
            task_id="test-001",
            tx_hash="0x" + "a" * 64,
            from_address="0x" + "a" * 40,
            to_address="0x" + "b" * 40,
            amount=50.0,
        )
        assert task_id["task_id"] == "test-001"
        assert task_id["tx_hash"] == "0x" + "a" * 64
        assert task_id["amount_vibe"] == 50.0
        assert task_id["status"] == "pending"

    def test_update_transaction_receipt(self):
        """_update_transaction_receipt updates status based on receipt."""
        from usmsb_sdk.api.rest.routers.blockchain import (
            _store_transaction, _update_transaction_receipt, _tx_store
        )
        # Store a tx
        _store_transaction(
            task_id="test-002",
            tx_hash="0x" + "a" * 64,
            from_address="0x" + "a" * 40,
            to_address="0x" + "b" * 40,
            amount=25.0,
        )
        # Update with successful receipt
        receipt = {"status": 1, "blockNumber": 12345, "transactionHash": "0x" + "a" * 64}
        _update_transaction_receipt("test-002", receipt)
        info = _tx_store["test-002"]
        assert info["status"] == "confirmed"
        assert info["block_number"] == 12345

    def test_update_transaction_receipt_failed(self):
        """status=0 → confirmed_failed."""
        from usmsb_sdk.api.rest.routers.blockchain import (
            _store_transaction, _update_transaction_receipt, _tx_store
        )
        _store_transaction(
            task_id="test-003",
            tx_hash="0x" + "a" * 64,
            from_address="0x" + "a" * 40,
            to_address=None,
            amount=None,
        )
        receipt = {"status": 0, "blockNumber": 12345, "transactionHash": "0x" + "a" * 64}
        _update_transaction_receipt("test-003", receipt)
        info = _tx_store["test-003"]
        assert info["status"] == "confirmed_failed"

    def test_update_nonexistent_task_noop(self):
        """Updating non-existent task does not raise."""
        from usmsb_sdk.api.rest.routers.blockchain import _update_transaction_receipt
        receipt = {"status": 1, "blockNumber": 12345}
        # Should not raise
        _update_transaction_receipt("nonexistent-task", receipt)
