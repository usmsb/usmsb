"""
Unit tests for Staking business logic.

Tests pure functions and endpoint behavior:
- calculate_apy, calculate_pending_rewards, get_stake_tier, get_tier_benefits
- deposit/withdraw/claim/info endpoints via TestClient with real DB via patched get_db_path
"""
import sys, os, time, sqlite3, tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from usmsb_sdk.api.rest.routers.staking import (
    calculate_apy, calculate_pending_rewards,
    BASE_APY, APY_BONUS_PER_TIER,
)
from usmsb_sdk.api.rest.api_key_manager import get_stake_tier, get_tier_benefits


# =============================================================================
# Pure Function Tests
# =============================================================================
class TestCalculateApy:
    def test_no_stake_zero_apy(self):
        assert calculate_apy(0) == 0.0
        assert calculate_apy(-100) == 0.0

    def test_bronze_base_apy(self):
        assert calculate_apy(100) == pytest.approx(BASE_APY)  # 5%

    def test_silver_6_percent(self):
        assert calculate_apy(1000) == pytest.approx(BASE_APY + APY_BONUS_PER_TIER)  # 6%

    def test_gold_7_percent(self):
        assert calculate_apy(5000) == pytest.approx(BASE_APY + 2 * APY_BONUS_PER_TIER)  # 7%

    def test_platinum_8_percent(self):
        assert calculate_apy(10000) == pytest.approx(BASE_APY + 3 * APY_BONUS_PER_TIER)  # 8%

    def test_large_caps_at_platinum(self):
        assert calculate_apy(1_000_000) == pytest.approx(BASE_APY + 3 * APY_BONUS_PER_TIER)


class TestCalculatePendingRewards:
    def test_zero_stake_zero(self):
        now = time.time()
        assert calculate_pending_rewards("a", 0, now) == 0.0

    def test_zero_elapsed_zero(self):
        now = time.time()
        assert calculate_pending_rewards("a", 10000, now) == 0.0

    def test_one_year_full_apy(self):
        now = time.time()
        one_year_ago = now - (365 * 24 * 3600)
        rewards = calculate_pending_rewards("a", 1000, one_year_ago)
        expected = 1000 * (BASE_APY + APY_BONUS_PER_TIER)
        assert rewards == pytest.approx(expected, rel=1e-3)

    def test_none_last_claim_uses_now(self):
        assert calculate_pending_rewards("a", 10000, None) == 0.0

    def test_rounding_6_decimals(self):
        now = time.time()
        three_months = now - (90 * 24 * 3600)
        rewards = calculate_pending_rewards("a", 7777, three_months)
        assert round(rewards, 6) == rewards
        assert rewards > 0


class TestStakeTiers:
    def test_none_tier(self):
        assert get_stake_tier(0) == "NONE"
        assert get_stake_tier(99) == "NONE"

    def test_bronze_tier(self):
        assert get_stake_tier(100) == "BRONZE"
        assert get_stake_tier(500) == "BRONZE"

    def test_silver_tier(self):
        assert get_stake_tier(1000) == "SILVER"
        assert get_stake_tier(3000) == "SILVER"

    def test_gold_tier(self):
        assert get_stake_tier(5000) == "GOLD"
        assert get_stake_tier(7500) == "GOLD"

    def test_platinum_tier(self):
        assert get_stake_tier(10000) == "PLATINUM"
        assert get_stake_tier(1_000_000) == "PLATINUM"

    def test_benefits_none(self):
        b = get_tier_benefits("NONE")
        assert b["max_agents"] == 0

    def test_benefits_bronze(self):
        b = get_tier_benefits("BRONZE")
        assert b["max_agents"] == 1
        assert b["discount"] == 0.0

    def test_benefits_platinum(self):
        b = get_tier_benefits("PLATINUM")
        assert b["max_agents"] == 50
        assert b["discount"] == 0.20


class TestApyTierBoundaries:
    def test_bronze_silver(self):
        assert get_stake_tier(999) == "BRONZE"
        assert get_stake_tier(1000) == "SILVER"
        assert calculate_apy(999) < calculate_apy(1000)

    def test_silver_gold(self):
        assert get_stake_tier(4999) == "SILVER"
        assert get_stake_tier(5000) == "GOLD"
        assert calculate_apy(4999) < calculate_apy(5000)

    def test_gold_platinum(self):
        assert get_stake_tier(9999) == "GOLD"
        assert get_stake_tier(10000) == "PLATINUM"
        assert calculate_apy(9999) < calculate_apy(10000)


# =============================================================================
# DB helpers: use file-based SQLite so get_db() connects to same DB
# =============================================================================
_TEST_DB_FD = None
_TEST_DB_PATH = None

def _get_test_db_path():
    global _TEST_DB_FD, _TEST_DB_PATH
    if _TEST_DB_PATH is None:
        _TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(suffix=".db")
        os.close(_TEST_DB_FD)
    return _TEST_DB_PATH

def _setup_test_db():
    """Create test DB schema."""
    db_path = _get_test_db_path()
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE agent_wallets (
            id, agent_id, owner_id, wallet_address, agent_address,
            vibe_balance REAL DEFAULT 0, staked_amount REAL DEFAULT 0,
            stake_status TEXT DEFAULT 'none', locked_stake REAL DEFAULT 0,
            unlock_available_at REAL, max_per_tx REAL DEFAULT 10000,
            daily_limit REAL DEFAULT 100000, daily_spent REAL DEFAULT 0,
            last_reset_time REAL, registry_registered INTEGER DEFAULT 0,
            created_at REAL, updated_at REAL
        )
    """)
    conn.execute("ALTER TABLE agent_wallets ADD COLUMN agent_private_key TEXT")
    conn.execute("""
        CREATE TABLE staking_rewards (
            id, agent_id, pending_rewards REAL DEFAULT 0,
            total_claimed REAL DEFAULT 0, last_claim_at REAL,
            last_update_at REAL, created_at REAL
        )
    """)
    conn.commit()
    conn.close()

def _insert_wallet(agent_id, vibe_balance, staked_amount, stake_status="active", locked_stake=0.0):
    db_path = _get_test_db_path()
    conn = sqlite3.connect(db_path)
    now = time.time()
    conn.execute("""
        INSERT INTO agent_wallets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (f"w_{agent_id}", agent_id, "owner1", "0xWALLET1", "0xAGENT1",
          vibe_balance, staked_amount, stake_status, locked_stake,
          None, 10000.0, 100000.0, 0.0, now, 1, now, now, "0xPK"))
    conn.commit()
    conn.close()

def _insert_rewards(agent_id, pending, total_claimed, last_claim_at=None):
    """Insert staking rewards record. last_claim_at=None means never claimed (pending=0)."""
    db_path = _get_test_db_path()
    conn = sqlite3.connect(db_path)
    now = time.time()
    conn.execute("""
        INSERT INTO staking_rewards VALUES (?,?,?,?,?,?,?)
    """, (f"sr_{agent_id}", agent_id, pending, total_claimed, last_claim_at, now, now))
    conn.commit()
    conn.close()


MOCK_USER = {
    "user_id": "agent1", "agent_id": "agent1",
    "wallet_address": "0xWALLET1", "name": "TestAgent",
    "status": "bound", "binding_status": "bound",
    "owner_wallet": "0xWALLET1", "capabilities": "[]",
    "description": "Test agent", "level": 1, "key_id": "key1", "staked_amount": 5000.0, "stake_status": "active", "staked_amount": 5000.0, "stake_status": "active",
}


# =============================================================================
# Endpoint Tests: use patched get_db_path to direct get_db() to test file
# =============================================================================
class TestDepositEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        # Reset the module-level cached path so each test gets fresh DB
        global _TEST_DB_FD, _TEST_DB_PATH
        _TEST_DB_FD = None
        _TEST_DB_PATH = None
        _setup_test_db()

    def _do(self, path, json_data, agent_id="agent1"):
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.staking import router
        from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
        from fastapi import FastAPI

        user = dict(MOCK_USER)
        user["agent_id"] = agent_id

        app = FastAPI()
        app.include_router(router)

        async def mock_auth():
            return user

        app.dependency_overrides[get_current_user_unified] = mock_auth

        with patch('usmsb_sdk.api.database.get_db_path', return_value=_get_test_db_path()):
            with TestClient(app) as client:
                return client.post(path, json=json_data)

    def test_insufficient_balance_returns_400(self):
        _insert_wallet("agent1", vibe_balance=50.0, staked_amount=0)
        r = self._do("/staking/deposit", {"amount": 100.0})
        assert r.status_code == 400
        assert "VIBE" in r.json()["detail"]["message"]

    def test_sufficient_balance_returns_200(self):
        _insert_wallet("agent1", vibe_balance=5000.0, staked_amount=1000.0)
        r = self._do("/staking/deposit", {"amount": 1000.0})
        assert r.status_code == 200
        assert r.json()["staked_amount"] == 2000.0

    def test_negative_amount_returns_422(self):
        r = self._do("/staking/deposit", {"amount": -50.0})
        assert r.status_code == 422

    def test_zero_amount_returns_422(self):
        r = self._do("/staking/deposit", {"amount": 0.0})
        assert r.status_code == 422

    def test_wallet_not_found_returns_404(self):
        # No wallet inserted
        r = self._do("/staking/deposit", {"amount": 100.0})
        assert r.status_code == 404


class TestWithdrawEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        # Reset the module-level cached path so each test gets fresh DB
        global _TEST_DB_FD, _TEST_DB_PATH
        _TEST_DB_FD = None
        _TEST_DB_PATH = None
        _setup_test_db()

    def _do(self, path, json_data):
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.staking import router
        from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        async def mock_auth():
            return MOCK_USER

        app.dependency_overrides[get_current_user_unified] = mock_auth

        with patch('usmsb_sdk.api.database.get_db_path', return_value=_get_test_db_path()):
            with TestClient(app) as client:
                return client.post(path, json=json_data)

    def test_insufficient_available_stake_returns_400(self):
        _insert_wallet("agent1", vibe_balance=1000.0, staked_amount=500.0, locked_stake=400.0)
        r = self._do("/staking/withdraw", {"amount": 200.0})
        assert r.status_code == 400
        assert "available" in r.json()["detail"]["message"]

    def test_sufficient_available_returns_200(self):
        _insert_wallet("agent1", vibe_balance=1000.0, staked_amount=5000.0, locked_stake=0.0)
        r = self._do("/staking/withdraw", {"amount": 1000.0})
        assert r.status_code == 200
        assert r.json()["staked_amount"] == 4000.0

    def test_wallet_not_found_returns_404(self):
        r = self._do("/staking/withdraw", {"amount": 100.0})
        assert r.status_code == 404

    def test_negative_amount_returns_422(self):
        r = self._do("/staking/withdraw", {"amount": -10.0})
        assert r.status_code == 422


class TestGetStakingInfoEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        # Reset the module-level cached path so each test gets fresh DB
        global _TEST_DB_FD, _TEST_DB_PATH
        _TEST_DB_FD = None
        _TEST_DB_PATH = None
        _setup_test_db()

    def _do_get(self, path):
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.staking import router
        from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        async def mock_auth():
            return MOCK_USER

        app.dependency_overrides[get_current_user_unified] = mock_auth

        with patch('usmsb_sdk.api.database.get_db_path', return_value=_get_test_db_path()):
            with TestClient(app) as client:
                return client.get(path)

    def test_bound_agent_returns_stake_info(self):
        _insert_wallet("agent1", vibe_balance=1000.0, staked_amount=5000.0)
        r = self._do_get("/staking/info")
        assert r.status_code == 200
        assert r.json()["staked_amount"] == 5000.0
        assert r.json()["stake_tier"] == "GOLD"

    def test_no_wallet_returns_defaults(self):
        # No wallet in DB
        r = self._do_get("/staking/info")
        assert r.status_code == 200
        assert r.json()["staked_amount"] == 0
        assert r.json()["stake_tier"] == "NONE"


class TestClaimEndpoint:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        # Reset the module-level cached path so each test gets fresh DB
        global _TEST_DB_FD, _TEST_DB_PATH
        _TEST_DB_FD = None
        _TEST_DB_PATH = None
        _setup_test_db()

    def _do_claim(self):
        from fastapi.testclient import TestClient
        from usmsb_sdk.api.rest.routers.staking import router
        from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)

        async def mock_auth():
            return MOCK_USER

        app.dependency_overrides[get_current_user_unified] = mock_auth

        with patch('usmsb_sdk.api.database.get_db_path', return_value=_get_test_db_path()):
            with TestClient(app) as client:
                return client.post("/staking/claim")

    def test_zero_pending_returns_zero_claimed(self):
        _insert_wallet("agent1", vibe_balance=1000.0, staked_amount=5000.0)
        _insert_rewards("agent1", pending=0.0, total_claimed=100.0, last_claim_at=None)
        r = self._do_claim()
        assert r.status_code == 200
        assert r.json()["claimed_amount"] == 0.0
        assert "No pending" in r.json()["message"]

    def test_positive_pending_increases_balance(self):
        _insert_wallet("agent1", vibe_balance=1000.0, staked_amount=5000.0)
        _insert_rewards("agent1", pending=75.5, total_claimed=200.0, last_claim_at=time.time() - 86400)
        r = self._do_claim()
        assert r.status_code == 200
        assert r.json()["claimed_amount"] > 0
        assert r.json()["new_balance"] == 1000.0 + r.json()["claimed_amount"]

    def test_wallet_not_found_returns_404(self):
        # No wallet
        r = self._do_claim()
        assert r.status_code == 404
