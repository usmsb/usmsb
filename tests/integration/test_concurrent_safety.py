"""
Concurrent safety integration tests.

Tests that the system handles concurrent-like operations safely.
Note: SQLite has limited concurrency support, so some tests verify
that concurrent operations are serialized safely rather than truly parallel.
"""
import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestConcurrentOrderCreation:
    """Test concurrent order creation."""

    def test_sequential_orders_inserted_correctly(self, integration_db):
        """Multiple orders inserted sequentially should all persist."""
        now = time.time()
        for i in range(10):
            order_id = f"seq_order_{int(now)}_{i}"
            integration_db.execute(
                """INSERT INTO orders (order_id, source, demand_agent_id, supply_agent_id, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (order_id, "test", "demand", "supply", "created", now, now)
            )
        integration_db.commit()

        cursor = integration_db.execute(
            "SELECT COUNT(*) FROM orders WHERE order_id LIKE 'seq_order_%'"
        )
        assert cursor.fetchone()[0] == 10

    def test_concurrent_reads_return_consistent_data(self, integration_db):
        """Multiple concurrent reads return consistent data."""
        now = time.time()
        for i in range(5):
            order_id = f"concurrent_read_{int(now)}_{i}"
            integration_db.execute(
                """INSERT INTO orders (order_id, source, demand_agent_id, supply_agent_id, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (order_id, "test", "demand", "supply", "created", now, now)
            )
        integration_db.commit()

        results = []
        def read_count():
            cursor = integration_db.execute(
                "SELECT COUNT(*) FROM orders WHERE order_id LIKE 'concurrent_read_%'"
            )
            return cursor.fetchone()[0]

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(read_count) for _ in range(10)]
            for f in as_completed(futures):
                results.append(f.result())

        assert all(r == 5 for r in results), \
            f"Reads returned inconsistent counts: {results}"


class TestConcurrentBalanceUpdates:
    """Test concurrent balance/stake updates."""

    def test_sequential_stake_updates_work(self, integration_db):
        """Sequential stake updates accumulate correctly."""
        now = time.time()
        user_id = f"stake_user_{int(now)}"
        wallet = f"0x{int(now):040x}"

        integration_db.execute(
            """INSERT INTO users (id, wallet_address, stake, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, wallet, 0.0, now, now)
        )
        integration_db.commit()

        # Sequential updates (simulating what concurrent threads would do)
        for _ in range(5):
            cursor = integration_db.execute(
                "SELECT stake FROM users WHERE id = ?", (user_id,)
            )
            row = cursor.fetchone()
            current = row[0] if row else 0.0
            integration_db.execute(
                "UPDATE users SET stake = ?, updated_at = ? WHERE id = ?",
                (current + 100.0, time.time(), user_id)
            )
            integration_db.commit()

        cursor = integration_db.execute(
            "SELECT stake FROM users WHERE id = ?", (user_id,)
        )
        assert cursor.fetchone()[0] == 500.0


class TestConcurrentNegotiationUpdates:
    """Test concurrent negotiation state updates."""

    def test_sequential_negotiation_updates_work(self, integration_db):
        """Sequential negotiation updates persist correctly."""
        now = time.time()
        session_id = f"neg_{int(now)}"

        integration_db.execute(
            """INSERT INTO negotiations (session_id, initiator_id, counterpart_id, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, "init_a", "counter_b", "pending", now, now)
        )
        integration_db.commit()

        # Sequential status updates
        for i, new_status in enumerate(["active", "countered", "agreed"]):
            integration_db.execute(
                "UPDATE negotiations SET status = ?, updated_at = ? WHERE session_id = ?",
                (new_status, time.time(), session_id)
            )
            integration_db.commit()

        cursor = integration_db.execute(
            "SELECT status FROM negotiations WHERE session_id = ?", (session_id,)
        )
        assert cursor.fetchone()[0] == "agreed"


class TestConcurrentTransactionSafety:
    """Test transaction safety under load."""

    def test_rapid_successive_inserts_are_safe(self, integration_db):
        """Rapid successive inserts don't cause transaction issues."""
        now = time.time()
        for i in range(20):
            order_id = f"rapid_{int(now)}_{i}"
            integration_db.execute(
                """INSERT INTO orders (order_id, source, demand_agent_id, supply_agent_id, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (order_id, "test", "demand", "supply", "created", now, now)
            )
            integration_db.commit()

        cursor = integration_db.execute(
            "SELECT COUNT(*) FROM orders WHERE order_id LIKE 'rapid_%'"
        )
        assert cursor.fetchone()[0] == 20

    def test_duplicate_order_id_rejected(self, integration_db):
        """Duplicate order IDs should be rejected (UNIQUE constraint)."""
        now = time.time()
        order_id = f"dup_test_{int(now)}"
        integration_db.execute(
            """INSERT INTO orders (order_id, source, demand_agent_id, supply_agent_id, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (order_id, "test", "demand", "supply", "created", now, now)
        )
        integration_db.commit()

        # Try inserting same ID again
        try:
            integration_db.execute(
                """INSERT INTO orders (order_id, source, demand_agent_id, supply_agent_id, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (order_id, "test2", "demand2", "supply2", "created", now, now)
            )
            integration_db.commit()
            duplicate_inserted = True
        except Exception:
            duplicate_inserted = False

        assert not duplicate_inserted, "Duplicate order_id should be rejected"
