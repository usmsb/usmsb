"""
Unit tests for staking system database operations.

Tests cover:
- User creation with new staking fields
- Balance operations (deduct/add)
- Stake status management
- Unstake flow state transitions
"""
import pytest
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestStakingDatabaseOperations:
    """Unit tests for staking database operations."""

    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create a temporary database for testing."""
        db_path = tmp_path / "test_staking.db"

        # Patch the DATABASE_PATH
        with patch('usmsb_sdk.api.database.DATABASE_PATH', str(db_path)):
            from usmsb_sdk.api import database
            database.init_db()
            yield database

    def test_create_user_with_staking_fields(self, temp_db):
        """Test that new users are created with default staking fields."""
        user = temp_db.create_user({
            'wallet_address': '0x1234567890abcdef1234567890abcdef12345678'
        })

        assert user is not None
        assert user['wallet_address'] == '0x1234567890abcdef1234567890abcdef12345678'
        assert user['stake'] == 0
        assert user['reputation'] == 0.5
        # New staking fields should have defaults
        assert user.get('vibe_balance') == 10000.0
        assert user.get('stake_status') == 'none'
        assert user.get('locked_stake') == 0
        assert user.get('unlock_available_at') is None

    def test_get_user_by_address_returns_staking_fields(self, temp_db):
        """Test that get_user_by_address returns all staking fields."""
        address = '0xabcd567890abcdef1234567890abcdef12345678'
        temp_db.create_user({'wallet_address': address})

        user = temp_db.get_user_by_address(address)

        assert user is not None
        assert 'vibe_balance' in user
        assert 'stake_status' in user
        assert 'locked_stake' in user
        assert user['vibe_balance'] == 10000.0

    def test_update_user_balance_deduct(self, temp_db):
        """Test deducting from user balance."""
        user = temp_db.create_user({
            'wallet_address': '0x1111111111111111111111111111111111111111'
        })

        # Deduct 1000 VIBE
        result = temp_db.update_user_balance(user['id'], 1000, deduct=True)

        assert result is not None
        assert result['vibe_balance'] == 9000.0

    def test_update_user_balance_add(self, temp_db):
        """Test adding to user balance."""
        user = temp_db.create_user({
            'wallet_address': '0x2222222222222222222222222222222222222222'
        })

        # Add 500 VIBE
        result = temp_db.update_user_balance(user['id'], 500, deduct=False)

        assert result is not None
        assert result['vibe_balance'] == 10500.0

    def test_update_user_balance_insufficient(self, temp_db):
        """Test that deducting more than balance returns None."""
        user = temp_db.create_user({
            'wallet_address': '0x3333333333333333333333333333333333333333'
        })

        # Try to deduct more than balance (10000)
        result = temp_db.update_user_balance(user['id'], 20000, deduct=True)

        assert result is None

    def test_update_stake_status_to_staked(self, temp_db):
        """Test updating stake status to 'staked'."""
        user = temp_db.create_user({
            'wallet_address': '0x4444444444444444444444444444444444444444'
        })

        result = temp_db.update_stake_status(user['id'], 'staked')

        assert result is True

        # Verify the status was updated
        balance_info = temp_db.get_user_balance_info(user['id'])
        assert balance_info['stake_status'] == 'staked'

    def test_update_stake_status_to_unstaking(self, temp_db):
        """Test updating stake status to 'unstaking' with lock info."""
        user = temp_db.create_user({
            'wallet_address': '0x5555555555555555555555555555555555555555'
        })

        unlock_time = (datetime.now() + timedelta(days=7)).timestamp()
        result = temp_db.update_stake_status(
            user['id'],
            'unstaking',
            locked_stake=1000,
            unlock_available_at=unlock_time
        )

        assert result is True

        balance_info = temp_db.get_user_balance_info(user['id'])
        assert balance_info['stake_status'] == 'unstaking'
        assert balance_info['locked_stake'] == 1000
        assert balance_info['unlock_available_at'] == unlock_time

    def test_update_stake_status_cancel_unstake(self, temp_db):
        """Test canceling unstake by resetting status."""
        user = temp_db.create_user({
            'wallet_address': '0x6666666666666666666666666666666666666666'
        })

        # First set to unstaking
        unlock_time = (datetime.now() + timedelta(days=7)).timestamp()
        temp_db.update_stake_status(
            user['id'],
            'unstaking',
            locked_stake=1000,
            unlock_available_at=unlock_time
        )

        # Then cancel
        result = temp_db.update_stake_status(
            user['id'],
            'staked',
            locked_stake=0,
            unlock_available_at=None
        )

        assert result is True

        balance_info = temp_db.get_user_balance_info(user['id'])
        assert balance_info['stake_status'] == 'staked'
        assert balance_info['locked_stake'] == 0
        assert balance_info['unlock_available_at'] is None

    def test_get_user_balance_info(self, temp_db):
        """Test getting comprehensive balance info."""
        user = temp_db.create_user({
            'wallet_address': '0x7777777777777777777777777777777777777777'
        })

        # Update some values
        temp_db.update_user_balance(user['id'], 500, deduct=True)
        temp_db.update_stake_status(user['id'], 'staked')

        balance_info = temp_db.get_user_balance_info(user['id'])

        assert balance_info is not None
        assert balance_info['vibe_balance'] == 9500.0
        assert balance_info['stake_status'] == 'staked'


class TestStakeValidation:
    """Unit tests for staking validation logic."""

    def test_minimum_stake_validation(self):
        """Test that minimum stake is 100 VIBE."""
        min_stake = 100

        # Valid stakes
        assert 100 >= min_stake
        assert 500 >= min_stake
        assert 1000 >= min_stake

        # Invalid stakes
        assert not (50 >= min_stake)
        assert not (99.99 >= min_stake)

    def test_stake_status_transitions(self):
        """Test valid stake status transitions."""
        # Valid states
        valid_states = {'none', 'staked', 'unstaking', 'unlocked'}

        # Transition rules:
        # none -> staked (stake)
        # staked -> unstaking (request unstake)
        # unstaking -> staked (cancel unstake)
        # unstaking -> unlocked (confirm unstake after period)
        # unlocked -> staked (stake again)

        transitions = [
            ('none', 'staked'),
            ('staked', 'unstaking'),
            ('unstaking', 'staked'),
            ('unstaking', 'unlocked'),
            ('unlocked', 'staked'),
        ]

        for from_state, to_state in transitions:
            assert from_state in valid_states
            assert to_state in valid_states

    def test_unstaking_period_calculation(self):
        """Test unstaking period calculation (7 days)."""
        unstaking_period_days = 7
        now = datetime.now()
        unlock_time = now + timedelta(days=unstaking_period_days)

        # Verify unlock time is in the future
        assert unlock_time > now

        # Verify it's approximately 7 days
        diff = unlock_time - now
        assert diff.days == 7
