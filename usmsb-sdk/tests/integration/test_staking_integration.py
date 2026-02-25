"""
Integration tests for staking API endpoints.

Tests cover:
- GET /auth/config - Staking configuration
- GET /auth/balance - User balance info
- POST /auth/stake - Staking tokens
- POST /auth/unstake - Request unstake
- POST /auth/unstake/cancel - Cancel unstake
- POST /auth/unstake/confirm - Confirm unstake
- POST /auth/profile - Profile creation (hourlyRate fix verification)

Note: These tests use a shared test database to ensure proper isolation.
"""
import pytest
import os
import sys
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Shared test database path for all tests in this module
_TEST_DB_PATH = None


def get_test_db_path(tmp_path_factory):
    """Get or create a shared test database path."""
    global _TEST_DB_PATH
    if _TEST_DB_PATH is None:
        _TEST_DB_PATH = str(tmp_path_factory.getbasetemp() / "staking_test.db")
    return _TEST_DB_PATH


@pytest.fixture(scope="module")
def test_app(tmp_path_factory):
    """Create a test app with a temporary database."""
    # Set environment variable before importing
    test_db_path = get_test_db_path(tmp_path_factory)

    # Set JWT_SECRET for testing
    os.environ["JWT_SECRET"] = "test-secret-key-for-integration-tests"
    os.environ["STAKE_REQUIRED"] = "true"

    # Patch the DATABASE_PATH before importing the database module
    with patch('usmsb_sdk.api.database.DATABASE_PATH', test_db_path):
        # Force reimport of database module
        import importlib
        if 'usmsb_sdk.api.database' in sys.modules:
            importlib.reload(sys.modules['usmsb_sdk.api.database'])

        from usmsb_sdk.api import database
        database.init_db()

        # Now import and create the app
        from usmsb_sdk.api.rest.main import app

        yield {
            'app': app,
            'database': database,
            'db_path': test_db_path
        }


@pytest.fixture
def client(test_app):
    """Create a test client."""
    from fastapi.testclient import TestClient
    return TestClient(test_app['app'])


@pytest.fixture
def db(test_app):
    """Get the test database module."""
    return test_app['database']


class TestStakingConfigAPI:
    """Integration tests for GET /auth/config endpoint."""

    def test_config_returns_stake_required_true_by_default(self, client):
        """Test that config returns stakeRequired=true by default."""
        # Set STAKE_REQUIRED=true for this test
        original = os.environ.get('STAKE_REQUIRED')
        os.environ['STAKE_REQUIRED'] = 'true'

        try:
            response = client.get("/auth/config")

            assert response.status_code == 200
            data = response.json()
            assert data['stakeRequired'] == True
            assert data['minStakeAmount'] == 100.0
            assert data['defaultBalance'] == 10000.0
            assert data['unstakingPeriodDays'] == 7
        finally:
            if original is not None:
                os.environ['STAKE_REQUIRED'] = original

    def test_config_returns_stake_required_false_when_disabled(self, client):
        """Test that config returns stakeRequired=false when disabled."""
        original = os.environ.get('STAKE_REQUIRED')
        os.environ['STAKE_REQUIRED'] = 'false'

        try:
            response = client.get("/auth/config")

            assert response.status_code == 200
            data = response.json()
            assert data['stakeRequired'] == False
        finally:
            if original is not None:
                os.environ['STAKE_REQUIRED'] = original
            else:
                os.environ['STAKE_REQUIRED'] = 'true'


class TestStakingBalanceAPI:
    """Integration tests for GET /auth/balance endpoint."""

    @pytest.fixture
    def auth_user(self, db):
        """Create a user with authentication."""
        import uuid

        user = db.create_user({
            'wallet_address': f'0xbalance{uuid.uuid4().hex[:24]}'
        })

        session_id = str(uuid.uuid4())
        access_token = hashlib.sha256(f"{session_id}:balance".encode()).hexdigest()
        db.create_session({
            'session_id': session_id,
            'address': user['wallet_address'],
            'did': user['did'],
            'access_token': access_token,
            'expires_at': (datetime.now() + timedelta(days=1)).timestamp(),
        })

        return {
            'user': user,
            'headers': {"Authorization": f"Bearer {access_token}"}
        }

    def test_balance_requires_authentication(self, client):
        """Test that balance endpoint requires authentication."""
        response = client.get("/auth/balance")
        assert response.status_code == 401

    def test_balance_returns_user_balance_info(self, client, auth_user):
        """Test that balance returns correct user balance info."""
        response = client.get(
            "/auth/balance",
            headers=auth_user['headers']
        )

        assert response.status_code == 200
        data = response.json()
        assert 'balance' in data
        assert 'stakedAmount' in data
        assert 'lockedAmount' in data
        assert 'totalBalance' in data
        assert 'stakeStatus' in data
        assert data['balance'] == 10000.0


class TestStakingFlow:
    """Integration tests for the complete staking flow."""

    @pytest.fixture
    def auth_user(self, db):
        """Create a user with authentication for staking tests."""
        import uuid

        user = db.create_user({
            'wallet_address': f'0xstake{uuid.uuid4().hex[:24]}'
        })

        session_id = str(uuid.uuid4())
        access_token = hashlib.sha256(f"{session_id}:stake".encode()).hexdigest()
        db.create_session({
            'session_id': session_id,
            'address': user['wallet_address'],
            'did': user['did'],
            'access_token': access_token,
            'expires_at': (datetime.now() + timedelta(days=1)).timestamp(),
        })

        return {
            'user': user,
            'headers': {"Authorization": f"Bearer {access_token}"}
        }

    def test_stake_minimum_validation(self, client, auth_user):
        """Test that staking below minimum returns error."""
        # Try to stake 50 VIBE (below minimum of 100)
        response = client.post(
            "/auth/stake",
            json={"amount": 50},
            headers=auth_user['headers']
        )

        # Should fail validation
        assert response.status_code == 400

    def test_stake_insufficient_balance(self, client, auth_user):
        """Test that staking more than balance returns error."""
        # Try to stake 20000 VIBE (more than default balance of 10000)
        response = client.post(
            "/auth/stake",
            json={"amount": 20000},
            headers=auth_user['headers']
        )

        assert response.status_code == 400
        assert "Insufficient" in response.json()['detail']

    def test_stake_success(self, client, auth_user, db):
        """Test successful staking."""
        # Stake 500 VIBE
        response = client.post(
            "/auth/stake",
            json={"amount": 500},
            headers=auth_user['headers']
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        assert data['newStake'] == 500
        assert 'transactionHash' in data

        # Verify balance was deducted
        balance_response = client.get("/auth/balance", headers=auth_user['headers'])
        balance_data = balance_response.json()
        assert balance_data['balance'] == 9500.0  # 10000 - 500
        assert balance_data['stakeStatus'] == 'staked'


class TestUnstakeFlow:
    """Integration tests for unstake flow."""

    @pytest.fixture
    def staked_user(self, db):
        """Create a user with existing stake."""
        import uuid

        user = db.create_user({
            'wallet_address': f'0xunstake{uuid.uuid4().hex[:24]}'
        })

        # Add stake
        db.update_user_stake(user['id'], 1000)
        db.update_stake_status(user['id'], 'staked')
        db.update_user_balance(user['id'], 1000, deduct=True)

        session_id = str(uuid.uuid4())
        access_token = hashlib.sha256(f"{session_id}:unstake".encode()).hexdigest()
        db.create_session({
            'session_id': session_id,
            'address': user['wallet_address'],
            'did': user['did'],
            'access_token': access_token,
            'expires_at': (datetime.now() + timedelta(days=1)).timestamp(),
        })

        return {
            'user': user,
            'headers': {"Authorization": f"Bearer {access_token}"}
        }

    @pytest.fixture
    def non_staked_user(self, db):
        """Create a user without stake."""
        import uuid

        user = db.create_user({
            'wallet_address': f'0xnostake{uuid.uuid4().hex[:24]}'
        })

        session_id = str(uuid.uuid4())
        access_token = hashlib.sha256(f"{session_id}:nostake".encode()).hexdigest()
        db.create_session({
            'session_id': session_id,
            'address': user['wallet_address'],
            'did': user['did'],
            'access_token': access_token,
            'expires_at': (datetime.now() + timedelta(days=1)).timestamp(),
        })

        return {
            'user': user,
            'headers': {"Authorization": f"Bearer {access_token}"}
        }

    def test_unstake_requires_staked_status(self, client, non_staked_user):
        """Test that unstake requires user to be in 'staked' status."""
        response = client.post(
            "/auth/unstake",
            json={},
            headers=non_staked_user['headers']
        )

        assert response.status_code == 400
        assert "No active stake" in response.json()['detail']

    def test_unstake_success(self, client, staked_user):
        """Test successful unstake request."""
        response = client.post(
            "/auth/unstake",
            json={},
            headers=staked_user['headers']
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        assert data['lockedAmount'] == 1000
        assert 'unlockAvailableAt' in data

        # Verify status changed to unstaking
        balance_response = client.get("/auth/balance", headers=staked_user['headers'])
        balance_data = balance_response.json()
        assert balance_data['stakeStatus'] == 'unstaking'

    def test_cancel_unstake(self, client, staked_user):
        """Test canceling an unstake request."""
        # First request unstake
        client.post("/auth/unstake", json={}, headers=staked_user['headers'])

        # Then cancel it
        response = client.post("/auth/unstake/cancel", headers=staked_user['headers'])

        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True

        # Verify status restored to staked
        balance_response = client.get("/auth/balance", headers=staked_user['headers'])
        balance_data = balance_response.json()
        assert balance_data['stakeStatus'] == 'staked'
        assert balance_data['lockedAmount'] == 0

    def test_confirm_unstake_too_early(self, client, staked_user):
        """Test that confirming unstake before unlock period fails."""
        # First request unstake
        client.post("/auth/unstake", json={}, headers=staked_user['headers'])

        # Try to confirm immediately (should fail)
        response = client.post("/auth/unstake/confirm", headers=staked_user['headers'])

        assert response.status_code == 400
        assert "not completed" in response.json()['detail'].lower()


class TestProfileHourlyRateFix:
    """Integration tests to verify the hourlyRate bug fix."""

    @pytest.fixture
    def auth_user(self, db):
        """Create a user with authentication."""
        import uuid

        user = db.create_user({
            'wallet_address': f'0xprofile{uuid.uuid4().hex[:24]}'
        })

        session_id = str(uuid.uuid4())
        access_token = hashlib.sha256(f"{session_id}:profile".encode()).hexdigest()
        db.create_session({
            'session_id': session_id,
            'address': user['wallet_address'],
            'did': user['did'],
            'access_token': access_token,
            'expires_at': (datetime.now() + timedelta(days=1)).timestamp(),
        })

        return {
            'user': user,
            'headers': {"Authorization": f"Bearer {access_token}"}
        }

    def test_profile_with_hourly_rate_camelCase(self, client, auth_user):
        """Test that profile creation works with hourlyRate in camelCase."""
        # Profile request with hourlyRate in camelCase (as frontend sends)
        response = client.post(
            "/auth/profile",
            json={
                "name": "Test User",
                "bio": "Test bio",
                "skills": ["python", "testing"],
                "hourlyRate": 100,  # camelCase as frontend sends
                "availability": "full-time",
                "role": "supplier"
            },
            headers=auth_user['headers']
        )

        # Should not return 500 error
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        assert 'agentId' in data
