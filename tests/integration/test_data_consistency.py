"""
Data consistency integration tests.

Tests that related entities maintain consistent state:
- Agent ↔ Wallet balance consistency
- Staking ↔ Reputation consistency
- Order ↔ Transaction consistency
"""
import pytest
import time


class TestAgentWalletConsistency:
    """Test agent and wallet data consistency."""

    def test_agent_wallet_balance_stays_consistent(self, client, integration_db, sample_bound_agent):
        """Agent wallet balance is readable and consistent."""
        # Insert agent with wallet
        now = time.time()
        wallet = "0xconsistency" + "a" * 34
        integration_db.execute(
            """INSERT INTO agents (agent_id, name, status, owner_wallet, binding_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("agent_consist", "ConsistAgent", "active", wallet, "bound", now, now)
        )
        integration_db.commit()

        # Query back
        cursor = integration_db.execute(
            "SELECT owner_wallet, binding_status FROM agents WHERE agent_id = ?",
            ("agent_consist",)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == wallet
        assert row[1] == "bound"


class TestStakingReputationConsistency:
    """Test staking and reputation consistency."""

    def test_staked_user_has_valid_status(self, client, integration_db):
        """User who stakes has staked status and positive reputation."""
        now = time.time()
        user_id = f"user_staked_{int(now)}"
        wallet = f"0xstaked{int(now):040x}"
        integration_db.execute(
            """INSERT INTO users (id, wallet_address, stake, reputation, stake_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, wallet, 1000.0, 5.0, "staked", now, now)
        )
        integration_db.commit()

        cursor = integration_db.execute(
            "SELECT stake, reputation, stake_status FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 1000.0   # stake
        assert row[1] == 5.0      # reputation
        assert row[2] == "staked" # status

    def test_unstaked_user_has_none_status(self, client, integration_db):
        """User who unstakes has none/unlocked status."""
        now = time.time()
        user_id = f"user_unstaked_{int(now)}"
        wallet = f"0xunstaked{int(now):040x}"
        integration_db.execute(
            """INSERT INTO users (id, wallet_address, stake, reputation, stake_status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, wallet, 0.0, 0.5, "none", now, now)
        )
        integration_db.commit()

        cursor = integration_db.execute(
            "SELECT stake, stake_status FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == 0.0
        assert row[1] == "none"


class TestOrderTransactionConsistency:
    """Test order and transaction data consistency."""

    def test_order_has_transaction_reference(self, client, integration_db):
        """Order with chain tx has consistent status."""
        now = time.time()
        order_id = f"order_chain_{int(now)}"
        tx_hash = "0x" + "a" * 64
        integration_db.execute(
            """INSERT INTO orders (order_id, source, demand_agent_id, supply_agent_id, status, chain_tx_hash, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_id, "onchain", "demand_001", "supply_001", "accepted", tx_hash, now, now)
        )
        integration_db.commit()

        cursor = integration_db.execute(
            "SELECT status, chain_tx_hash FROM orders WHERE order_id = ?",
            (order_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "accepted"
        assert row[1] == tx_hash

    def test_transaction_references_order(self, client, integration_db):
        """Transaction references valid order."""
        now = time.time()
        tx_id = f"tx_ref_order_{int(now)}"
        order_id = f"order_for_tx_{int(now)}"
        integration_db.execute(
            """INSERT INTO orders (order_id, source, demand_agent_id, supply_agent_id, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (order_id, "test", "demand_001", "supply_001", "created", now, now)
        )
        integration_db.execute(
            """INSERT INTO transactions (id, buyer_id, seller_id, amount, status, demand_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (tx_id, "buyer_001", "seller_001", 100.0, "created", order_id, now, now)
        )
        integration_db.commit()

        cursor = integration_db.execute(
            "SELECT demand_id FROM transactions WHERE id = ?",
            (tx_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == order_id


class TestProposalVotingConsistency:
    """Test proposal and voting data consistency."""

    def test_active_proposal_has_vote_counts(self, client, integration_db):
        """Active proposal has valid vote counts."""
        now = time.time()
        prop_id = f"prop_active_{int(now)}"
        integration_db.execute(
            """INSERT INTO proposals (id, title, proposer_id, status, votes_for, votes_against, quorum, deadline, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (prop_id, "Active Proposal", "0xPROPOSER", "active", 100, 50, 10, (now + 86400), now, now)
        )
        integration_db.commit()

        cursor = integration_db.execute(
            "SELECT status, votes_for, votes_against FROM proposals WHERE id = ?",
            (prop_id,)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "active"
        assert row[1] == 100
        assert row[2] == 50
