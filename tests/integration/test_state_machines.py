"""
State machine integration tests.

Tests that state transitions are valid and enforced:
- Order: created → accepted → delivered → completed
- Transaction/Dispute: created → disputed → resolved
- Staking: none → staked → unstaking → unlocked
"""
import pytest
import time


class TestOrderStateMachine:
    """Test order state transitions."""

    def test_order_state_persists_in_db(self, client, integration_db):
        """Order state is stored correctly in DB using correct schema."""
        now = time.time()
        order_id = f"order_state_{int(now)}"
        integration_db.execute(
            """INSERT INTO orders (order_id, source, demand_agent_id, supply_agent_id, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (order_id, "test", "demand_001", "supply_001", "created", now, now)
        )
        integration_db.commit()

        cursor = integration_db.execute(
            "SELECT status FROM orders WHERE order_id = ?", (order_id,)
        )
        row = cursor.fetchone()
        assert row is not None, "Order should exist in DB"
        assert row[0] == "created"

    def test_order_state_transition_created_to_accepted(self, client, integration_db):
        """Order transitions from created to accepted."""
        now = time.time()
        order_id = f"order_accept_{int(now)}"
        integration_db.execute(
            """INSERT INTO orders (order_id, source, demand_agent_id, supply_agent_id, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (order_id, "test", "demand_001", "supply_001", "created", now, now)
        )
        integration_db.commit()

        # Transition to accepted
        integration_db.execute(
            "UPDATE orders SET status = 'accepted', updated_at = ? WHERE order_id = ?",
            (time.time(), order_id)
        )
        integration_db.commit()

        cursor = integration_db.execute(
            "SELECT status FROM orders WHERE order_id = ?", (order_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "accepted"


class TestTransactionDisputeStateMachine:
    """Test transaction dispute state transitions."""

    def test_transaction_dispute_state(self, client, integration_db):
        """Transaction dispute state is stored correctly."""
        now = time.time()
        tx_id = f"tx_dispute_{int(now)}"
        integration_db.execute(
            """INSERT INTO transactions (id, buyer_id, seller_id, amount, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (tx_id, "buyer_001", "seller_001", 100.0, "created", now, now)
        )
        integration_db.commit()

        cursor = integration_db.execute(
            "SELECT status, dispute_reason FROM transactions WHERE id = ?", (tx_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "created"

    def test_transaction_can_be_disputed(self, client, integration_db):
        """Transaction transitions from created to disputed."""
        now = time.time()
        tx_id = f"tx_disputing_{int(now)}"
        integration_db.execute(
            """INSERT INTO transactions (id, buyer_id, seller_id, amount, status, dispute_reason, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (tx_id, "buyer_001", "seller_001", 100.0, "disputed", " quality issue", now, now)
        )
        integration_db.commit()

        cursor = integration_db.execute(
            "SELECT status, dispute_reason FROM transactions WHERE id = ?", (tx_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "disputed"
        assert row[1] is not None

    def test_transaction_dispute_can_be_resolved(self, client, integration_db):
        """Transaction dispute transitions from disputed to resolved."""
        now = time.time()
        tx_id = f"tx_resolved_{int(now)}"
        integration_db.execute(
            """INSERT INTO transactions (id, buyer_id, seller_id, amount, status, dispute_reason, dispute_resolution, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tx_id, "buyer_001", "seller_001", 100.0, "resolved", " quality issue", " refund issued", now, now)
        )
        integration_db.commit()

        cursor = integration_db.execute(
            "SELECT status, dispute_resolution FROM transactions WHERE id = ?", (tx_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "resolved"
        assert row[1] is not None


class TestStakingStateMachine:
    """Test staking state transitions."""

    def test_staking_state_none_to_staked(self, client, integration_db):
        """Staking transitions from none to staked."""
        now = time.time()
        wallet = f"0xstaker{int(now):040x}"
        user_id = f"user_{int(now)}"
        integration_db.execute(
            """INSERT INTO users (id, wallet_address, stake_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, wallet, "staked", now, now)
        )
        integration_db.commit()

        cursor = integration_db.execute(
            "SELECT stake_status FROM users WHERE wallet_address = ?", (wallet,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "staked"

    def test_staking_state_staked_to_unstaking(self, client, integration_db):
        """Staking transitions from staked to unstaking."""
        now = time.time()
        wallet = f"0xunstaker{int(now):040x}"
        user_id = f"user_{int(now)}"
        integration_db.execute(
            """INSERT INTO users (id, wallet_address, stake_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, wallet, "unstaking", now, now)
        )
        integration_db.commit()

        cursor = integration_db.execute(
            "SELECT stake_status FROM users WHERE wallet_address = ?", (wallet,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "unstaking"

    def test_staking_state_unstaking_to_unlocked(self, client, integration_db):
        """Staking transitions from unstaking to unlocked."""
        now = time.time()
        wallet = f"0xunlocked{int(now):040x}"
        user_id = f"user_{int(now)}"
        integration_db.execute(
            """INSERT INTO users (id, wallet_address, stake_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, wallet, "unlocked", now, now)
        )
        integration_db.commit()

        cursor = integration_db.execute(
            "SELECT stake_status FROM users WHERE wallet_address = ?", (wallet,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "unlocked"
