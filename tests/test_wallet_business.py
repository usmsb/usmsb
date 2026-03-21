"""
Unit tests for Wallet business logic.

Real Pydantic models: WalletBalanceResponse, TransactionHistoryResponse,
TransactionRecord.
Prefix: /wallet
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.wallet import (
    WalletBalanceResponse,
    TransactionHistoryResponse,
    TransactionRecord,
)


class TestWalletBalanceResponse:
    def test_valid_response(self):
        r = WalletBalanceResponse(
            agent_id="agent-001",
            balance=500.0,
            staked_amount=1000.0,
            locked_amount=200.0,
            pending_rewards=50.0,
            total_assets=1750.0,
            stake_tier="silver",
            tier_benefits={"discount": 0.05},
        )
        assert r.balance == 500.0
        assert r.stake_tier == "silver"
        assert r.success is True


class TestTransactionRecord:
    def test_valid_record(self):
        r = TransactionRecord(
            id="tx-001",
            transaction_type="transfer",
            amount=100.0,
            status="completed",
            counterparty_id="agent-002",
            created_at=1700000000.0,
        )
        assert r.id == "tx-001"
        assert r.amount == 100.0
        assert r.status == "completed"

    def test_optional_fields_default(self):
        r = TransactionRecord(
            id="tx-002",
            transaction_type="stake",
            amount=500.0,
            status="pending",
            created_at=1700000000.0,
        )
        assert r.counterparty_id is None
        assert r.completed_at is None


class TestWalletAuth:
    def test_balance_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.wallet import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/wallet/balance?agent_id=agent-001")
            assert r.status_code in (401, 403)

    def test_transactions_requires_auth(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.wallet import router
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client:
            r = client.get("/wallet/transactions/agent-001")
            assert r.status_code in (401, 403)
