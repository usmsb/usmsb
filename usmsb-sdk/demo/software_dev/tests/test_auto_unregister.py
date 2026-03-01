"""
Unit Tests for Auto-Unregister Mechanism

Tests the automatic unregistration of AI agents without wallet binding
after extended periods of inactivity.
"""

import pytest
import time
from datetime import datetime
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from usmsb_sdk.api.database import (
    init_db,
    create_agent,
    get_agent,
    delete_agent,
    check_and_mark_offline_agents,
    auto_unregister_inactive_agents,
    has_wallet_binding,
    get_agent_wallet,
    AUTO_UNREGISTER_GRACE_PERIOD,
    AUTO_UNREGISTER_CHECK_INTERVAL,
)


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Use a temporary database for each test."""
    test_db_path = str(tmp_path / "test_agents.db")

    # Patch get_db_path before importing/using database functions
    with patch('usmsb_sdk.api.database.get_db_path', return_value=test_db_path):
        # Also need to patch DATABASE_PATH to ensure consistency
        with patch('usmsb_sdk.api.database.DATABASE_PATH', test_db_path):
            init_db()
            yield
            # Cleanup: close any open connections
            import sqlite3
            try:
                conn = sqlite3.connect(test_db_path)
                conn.close()
            except:
                pass


class TestWalletBinding:
    """Test wallet binding detection."""

    def test_has_wallet_binding_no_wallet(self):
        """Test that agent without wallet returns False."""
        # Create agent without wallet
        agent_data = {
            'agent_id': 'test_no_wallet',
            'name': 'Test Agent No Wallet',
            'agent_type': 'ai_agent',
            'status': 'online',
            'last_heartbeat': time.time(),
        }
        create_agent(agent_data)

        # Should not have wallet binding
        assert has_wallet_binding('test_no_wallet') is False

    def test_has_wallet_binding_with_wallet(self):
        """Test that agent with wallet returns True."""
        # Create agent with wallet
        agent_data = {
            'agent_id': 'test_with_wallet',
            'name': 'Test Agent With Wallet',
            'agent_type': 'ai_agent',
            'status': 'online',
            'last_heartbeat': time.time(),
        }
        create_agent(agent_data)

        # Create wallet binding via SQL
        from usmsb_sdk.api.database import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO agent_wallets (id, agent_id, owner_id, wallet_address, agent_address)
                VALUES (?, ?, ?, ?, ?)
            ''', ('wallet_1', 'test_with_wallet', 'owner_1', '0x123abc', '0x456def'))
            conn.commit()

        # Should have wallet binding
        assert has_wallet_binding('test_with_wallet') is True

    def test_has_wallet_binding_empty_wallet_address(self):
        """Test that agent with empty wallet address returns False."""
        # Create agent with empty wallet
        agent_data = {
            'agent_id': 'test_empty_wallet',
            'name': 'Test Agent Empty Wallet',
            'agent_type': 'ai_agent',
            'status': 'online',
            'last_heartbeat': time.time(),
        }
        create_agent(agent_data)

        # Create wallet binding with empty address
        from usmsb_sdk.api.database import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO agent_wallets (id, agent_id, owner_id, wallet_address, agent_address)
                VALUES (?, ?, ?, ?, ?)
            ''', ('wallet_2', 'test_empty_wallet', 'owner_2', '', '0x456def'))
            conn.commit()

        # Should not have wallet binding (empty address)
        assert has_wallet_binding('test_empty_wallet') is False


class TestHeartbeatMonitor:
    """Test heartbeat monitoring and offline marking."""

    def test_mark_online_agent_offline_after_ttl(self):
        """Test that online agents are marked offline after TTL expires."""
        # Create agent with expired TTL
        expired_heartbeat = time.time() - 200  # 200 seconds ago
        agent_data = {
            'agent_id': 'test_expired_ttl',
            'name': 'Test Expired TTL',
            'agent_type': 'ai_agent',
            'status': 'online',
            'last_heartbeat': expired_heartbeat,
            'ttl': 90,  # 90 seconds TTL
        }
        create_agent(agent_data)

        # Run heartbeat check
        offline_count = check_and_mark_offline_agents()

        # Should have marked one agent offline
        assert offline_count == 1

        # Verify agent is now offline
        agent = get_agent('test_expired_ttl')
        assert agent['status'] == 'offline'

    def test_keep_online_agent_within_ttl(self):
        """Test that online agents within TTL stay online."""
        # Create agent with recent heartbeat
        agent_data = {
            'agent_id': 'test_active_agent',
            'name': 'Test Active Agent',
            'agent_type': 'ai_agent',
            'status': 'online',
            'last_heartbeat': time.time() - 30,  # 30 seconds ago
            'ttl': 90,  # 90 seconds TTL
        }
        create_agent(agent_data)

        # Run heartbeat check
        offline_count = check_and_mark_offline_agents()

        # Should not have marked any agents offline
        assert offline_count == 0

        # Verify agent is still online
        agent = get_agent('test_active_agent')
        assert agent['status'] == 'online'


class TestAutoUnregister:
    """Test automatic unregistration of inactive agents."""

    def test_auto_unregister_agent_without_wallet(self):
        """Test that AI agents without wallet are unregistered after grace period."""
        # Create offline agent beyond grace period
        expired_heartbeat = time.time() - AUTO_UNREGISTER_GRACE_PERIOD - 3600
        agent_data = {
            'agent_id': 'test_unregister_no_wallet',
            'name': 'Test Unregister No Wallet',
            'agent_type': 'ai_agent',
            'status': 'offline',
            'last_heartbeat': expired_heartbeat,
            'ttl': 90,
        }
        create_agent(agent_data)

        # Run auto-unregister with short grace period for testing
        result = auto_unregister_inactive_agents(grace_period_seconds=60)

        # Should have unregistered one agent
        assert result['unregistered'] == 1

        # Verify agent is deleted
        agent = get_agent('test_unregister_no_wallet')
        assert agent is None

    def test_keep_agent_with_wallet(self):
        """Test that AI agents with wallet binding are kept even when offline."""
        # Create offline agent beyond grace period with wallet
        expired_heartbeat = time.time() - AUTO_UNREGISTER_GRACE_PERIOD - 3600
        agent_data = {
            'agent_id': 'test_keep_with_wallet',
            'name': 'Test Keep With Wallet',
            'agent_type': 'ai_agent',
            'status': 'offline',
            'last_heartbeat': expired_heartbeat,
            'ttl': 90,
        }
        create_agent(agent_data)

        # Create wallet binding
        from usmsb_sdk.api.database import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO agent_wallets (id, agent_id, owner_id, wallet_address, agent_address)
                VALUES (?, ?, ?, ?, ?)
            ''', ('wallet_3', 'test_keep_with_wallet', 'owner_3', '0x789abc', '0xabc123'))
            conn.commit()

        # Run auto-unregister with short grace period
        result = auto_unregister_inactive_agents(grace_period_seconds=60)

        # Should have kept one agent
        assert result['kept'] == 1

        # Verify agent still exists
        agent = get_agent('test_keep_with_wallet')
        assert agent is not None
        assert agent['status'] == 'offline'

    def test_skip_human_agent(self):
        """Test that human agents are never auto-unregistered."""
        # Create offline human agent
        expired_heartbeat = time.time() - AUTO_UNREGISTER_GRACE_PERIOD - 3600
        agent_data = {
            'agent_id': 'test_human_agent',
            'name': 'Test Human Agent',
            'agent_type': 'human_agent',
            'status': 'offline',
            'last_heartbeat': expired_heartbeat,
            'ttl': 90,
        }
        create_agent(agent_data)

        # Run auto-unregister with short grace period
        result = auto_unregister_inactive_agents(grace_period_seconds=60)

        # Should have skipped one agent
        assert result['skipped'] >= 1

        # Verify agent still exists
        agent = get_agent('test_human_agent')
        assert agent is not None

    def test_skip_system_agent(self):
        """Test that system agents are never auto-unregistered."""
        # Create offline system agent
        expired_heartbeat = time.time() - AUTO_UNREGISTER_GRACE_PERIOD - 3600
        agent_data = {
            'agent_id': 'test_system_agent',
            'name': 'Test System Agent',
            'agent_type': 'system_agent',
            'status': 'offline',
            'last_heartbeat': expired_heartbeat,
            'ttl': 90,
        }
        create_agent(agent_data)

        # Run auto-unregister with short grace period
        result = auto_unregister_inactive_agents(grace_period_seconds=60)

        # Should have skipped one agent
        assert result['skipped'] >= 1

        # Verify agent still exists
        agent = get_agent('test_system_agent')
        assert agent is not None


class TestConfiguration:
    """Test configuration parameters."""

    def test_default_grace_period(self):
        """Test default grace period is 24 hours."""
        assert AUTO_UNREGISTER_GRACE_PERIOD == 24 * 60 * 60  # 86400 seconds

    def test_default_check_interval(self):
        """Test default check interval is 1 hour."""
        assert AUTO_UNREGISTER_CHECK_INTERVAL == 60 * 60  # 3600 seconds

    def test_custom_grace_period(self):
        """Test using custom grace period."""
        # Create offline agent
        agent_data = {
            'agent_id': 'test_custom_grace',
            'name': 'Test Custom Grace',
            'agent_type': 'ai_agent',
            'status': 'offline',
            'last_heartbeat': time.time() - 3600,  # 1 hour ago
            'ttl': 90,
        }
        create_agent(agent_data)

        # Run with 30-minute grace period
        result = auto_unregister_inactive_agents(grace_period_seconds=1800)

        # Should have unregistered one agent
        assert result['unregistered'] == 1


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_agent_exactly_at_grace_period(self):
        """Test agent exactly at grace period boundary."""
        # Create agent slightly within grace period (to account for test execution time)
        # Using 3595 seconds instead of exactly 3600 to ensure it's within the boundary
        expired_heartbeat = time.time() - 3595  # Just within 1 hour
        agent_data = {
            'agent_id': 'test_exact_boundary',
            'name': 'Test Exact Boundary',
            'agent_type': 'ai_agent',
            'status': 'offline',
            'last_heartbeat': expired_heartbeat,
            'ttl': 90,
        }
        create_agent(agent_data)

        # Run with 1-hour grace period (3600 seconds)
        result = auto_unregister_inactive_agents(grace_period_seconds=3600)

        # Agent slightly within boundary should NOT be unregistered
        # (last_heartbeat is 3595 seconds ago, threshold is 3600 seconds, so 3595 < (now - 3600) is False)
        assert result['unregistered'] == 0

    def test_multiple_agents_mixed_conditions(self):
        """Test handling multiple agents with different conditions."""
        now = time.time()

        # Agent 1: Should be unregistered (no wallet, beyond grace)
        create_agent({
            'agent_id': 'multi_1',
            'name': 'Multi 1',
            'agent_type': 'ai_agent',
            'status': 'offline',
            'last_heartbeat': now - 7200,
            'ttl': 90,
        })

        # Agent 2: Should be kept (has wallet, beyond grace)
        create_agent({
            'agent_id': 'multi_2',
            'name': 'Multi 2',
            'agent_type': 'ai_agent',
            'status': 'offline',
            'last_heartbeat': now - 7200,
            'ttl': 90,
        })
        from usmsb_sdk.api.database import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO agent_wallets (id, agent_id, owner_id, wallet_address, agent_address)
                VALUES (?, ?, ?, ?, ?)
            ''', ('wallet_multi_2', 'multi_2', 'owner_multi', '0x111', '0x222'))
            conn.commit()

        # Agent 3: Should be skipped (human agent)
        create_agent({
            'agent_id': 'multi_3',
            'name': 'Multi 3',
            'agent_type': 'human_agent',
            'status': 'offline',
            'last_heartbeat': now - 7200,
            'ttl': 90,
        })

        # Agent 4: Should not be touched (still within grace period)
        create_agent({
            'agent_id': 'multi_4',
            'name': 'Multi 4',
            'agent_type': 'ai_agent',
            'status': 'offline',
            'last_heartbeat': now - 1800,  # 30 minutes ago
            'ttl': 90,
        })

        # Run auto-unregister with 1-hour grace period
        result = auto_unregister_inactive_agents(grace_period_seconds=3600)

        # Verify results
        assert result['unregistered'] == 1  # multi_1
        assert result['kept'] == 1  # multi_2
        assert result['skipped'] >= 1  # multi_3

        # Verify agent states
        assert get_agent('multi_1') is None  # Unregistered
        assert get_agent('multi_2') is not None  # Kept
        assert get_agent('multi_3') is not None  # Skipped
        assert get_agent('multi_4') is not None  # Not touched


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
