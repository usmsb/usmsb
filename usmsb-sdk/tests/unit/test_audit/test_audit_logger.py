"""
Unit tests for AuditLogger
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import shutil

from usmsb_sdk.platform.external.meta_agent.audit import AuditLogger, AuditConfig


@pytest.fixture
def temp_log_dir():
    """Create a temporary directory for test logs"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def audit_config():
    """Create a default audit config for testing"""
    return AuditConfig(
        retention_days=90,
        archive_after_days=30,
        log_sensitive_content=False,
        hash_user_id=True,
    )


@pytest.fixture
def audit_logger(temp_log_dir, audit_config):
    """Create an AuditLogger instance for testing"""
    return AuditLogger(config=audit_config, log_dir=temp_log_dir)


class TestAuditConfig:
    """Tests for AuditConfig"""

    def test_default_config(self):
        """Test default configuration values"""
        config = AuditConfig()

        assert config.retention_days == 90
        assert config.archive_after_days == 30
        assert config.log_sensitive_content is False
        assert config.hash_user_id is True
        assert len(config.audit_events) == 15  # session_timeout is included

        # Check for specific event types
        assert "session_created" in config.audit_events
        assert "session_closed" in config.audit_events
        assert "session_timeout" in config.audit_events
        assert "wallet_connected" in config.audit_events
        assert "signature_verified" in config.audit_events
        assert "auth_failed" in config.audit_events
        assert "data_synced_to_ipfs" in config.audit_events
        assert "code_executed" in config.audit_events
        assert "browser_opened" in config.audit_events
        assert "file_uploaded" in config.audit_events
        assert "sandbox_violation" in config.audit_events
        assert "quota_exceeded" in config.audit_events
        assert "suspicious_activity" in config.audit_events

    def test_custom_config(self):
        """Test custom configuration"""
        custom_events = ["test_event_1", "test_event_2"]

        config = AuditConfig(
            retention_days=180,
            archive_after_days=60,
            log_sensitive_content=True,
            hash_user_id=False,
            audit_events=custom_events,
        )

        assert config.retention_days == 180
        assert config.archive_after_days == 60
        assert config.log_sensitive_content is True
        assert config.hash_user_id is False
        assert config.audit_events == custom_events


class TestAuditLogger:
    """Tests for AuditLogger"""

    def test_logger_initialization(self, audit_logger, temp_log_dir):
        """Test AuditLogger initialization"""
        assert audit_logger.config is not None
        assert audit_logger.log_dir == Path(temp_log_dir)
        assert audit_logger.log_file == Path(temp_log_dir) / "audit.log"
        assert audit_logger.archive_dir == Path(temp_log_dir) / "archive"
        assert audit_logger._write_lock is not None

        # Check directories were created
        assert audit_logger.log_dir.exists()
        assert audit_logger.archive_dir.exists()

    @pytest.mark.asyncio
    async def test_log_event(self, audit_logger):
        """Test logging an event"""
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

        await audit_logger.log(
            event="session_created",
            wallet_address=wallet_address,
            details={"ip": "192.168.1.1"},
            result="success"
        )

        # Verify log was written
        assert audit_logger.log_file.exists()

        # Read and verify log
        with open(audit_logger.log_file, 'r') as f:
            line = f.readline()
            entry = json.loads(line)

            assert entry["event"] == "session_created"
            assert entry["result"] == "success"
            assert "user_hash" in entry
            assert entry["user_hash"] != wallet_address  # Should be hashed
            assert entry["details"] == {"ip": "192.168.1.1"}
            assert "timestamp" in entry
            assert "node_id" in entry

    @pytest.mark.asyncio
    async def test_log_multiple_events(self, audit_logger):
        """Test logging multiple events"""
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

        events = [
            ("session_created", {"ip": "192.168.1.1"}, "success"),
            ("wallet_connected", {}, "success"),
            ("code_executed", {"language": "python"}, "success"),
            ("auth_failed", {"attempt": 1}, "failed"),
        ]

        for event, details, result in events:
            await audit_logger.log(event, wallet_address, details, result)

        # Verify all events were logged
        logs = await audit_logger.query_logs(limit=100)
        assert len(logs) == 4

    @pytest.mark.asyncio
    async def test_log_ignored_event(self, audit_logger):
        """Test that events not in audit_events are ignored"""
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

        # This event is not in the default audit_events list
        await audit_logger.log(
            event="not_audited_event",
            wallet_address=wallet_address,
            details={}
        )

        # Verify log was not written
        logs = await audit_logger.query_logs(limit=100)
        assert len(logs) == 0

    def test_hash_user_id(self, audit_logger):
        """Test user ID hashing"""
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

        user_hash = audit_logger._hash_user_id(wallet_address)

        # Verify hash properties
        assert isinstance(user_hash, str)
        assert len(user_hash) == 16
        assert user_hash != wallet_address

        # Same input should produce same hash
        user_hash2 = audit_logger._hash_user_id(wallet_address)
        assert user_hash == user_hash2

        # Different input should produce different hash
        different_wallet = "0xabcdef1234567890abcdef1234567890abcdef12"
        different_hash = audit_logger._hash_user_id(different_wallet)
        assert user_hash != different_hash

    @pytest.mark.asyncio
    async def test_query_logs(self, audit_logger):
        """Test log query functionality"""
        wallet_address_1 = "0x1234567890abcdef1234567890abcdef12345678"
        wallet_address_2 = "0xabcdef1234567890abcdef1234567890abcdef12"

        # Log different events
        await audit_logger.log("session_created", wallet_address_1, {}, "success")
        await audit_logger.log("session_created", wallet_address_2, {}, "success")
        await audit_logger.log("wallet_connected", wallet_address_1, {}, "success")
        await audit_logger.log("code_executed", wallet_address_1, {"language": "python"}, "success")

        # Query all logs
        all_logs = await audit_logger.query_logs()
        assert len(all_logs) == 4

        # Query by event type
        session_logs = await audit_logger.query_logs(event="session_created")
        assert len(session_logs) == 2

        # Query by user hash
        user_hash = audit_logger._hash_user_id(wallet_address_1)
        user_logs = await audit_logger.query_logs(user_hash=user_hash)
        assert len(user_logs) == 3

        # Query with limit
        limited_logs = await audit_logger.query_logs(limit=2)
        assert len(limited_logs) == 2

    @pytest.mark.asyncio
    async def test_query_logs_with_time_filter(self, audit_logger):
        """Test log query with time filtering"""
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

        # Log an event
        await audit_logger.log("session_created", wallet_address, {}, "success")

        # Get current time (use timezone-aware datetime)
        now = datetime.now(timezone.utc)

        # Query with time range that includes our log
        start_time = (now - timedelta(hours=1)).timestamp()
        end_time = (now + timedelta(hours=1)).timestamp()

        logs = await audit_logger.query_logs(start_time=start_time, end_time=end_time)
        assert len(logs) == 1

        # Query with time range that excludes our log
        future_start = (now + timedelta(hours=2)).timestamp()
        future_end = (now + timedelta(hours=3)).timestamp()

        logs = await audit_logger.query_logs(start_time=future_start, end_time=future_end)
        assert len(logs) == 0

    @pytest.mark.asyncio
    async def test_query_user_activity(self, audit_logger):
        """Test querying user activity"""
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

        # Log some events
        await audit_logger.log("session_created", wallet_address, {}, "success")
        await audit_logger.log("wallet_connected", wallet_address, {}, "success")
        await audit_logger.log("code_executed", wallet_address, {"language": "python"}, "success")

        # Query user activity
        user_hash = audit_logger._hash_user_id(wallet_address)
        activity = await audit_logger.query_user_activity(user_hash=user_hash, hours=24)

        assert len(activity) == 3
        for entry in activity:
            assert entry["user_hash"] == user_hash

    @pytest.mark.asyncio
    async def test_get_security_events(self, audit_logger):
        """Test getting security events"""
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

        # Log various events
        await audit_logger.log("auth_failed", wallet_address, {"attempt": 1}, "failed")
        await audit_logger.log("sandbox_violation", wallet_address, {"type": "import"}, "blocked")
        await audit_logger.log("quota_exceeded", wallet_address, {"resource": "storage"}, "blocked")
        await audit_logger.log("suspicious_activity", wallet_address, {"reason": "rapid_requests"}, "blocked")
        await audit_logger.log("session_created", wallet_address, {}, "success")  # Not a security event

        # Get security events
        security_events = await audit_logger.get_security_events(hours=24)

        assert len(security_events) == 4
        event_types = {e["event"] for e in security_events}
        assert "auth_failed" in event_types
        assert "sandbox_violation" in event_types
        assert "quota_exceeded" in event_types
        assert "suspicious_activity" in event_types
        assert "session_created" not in event_types

    @pytest.mark.asyncio
    async def test_get_log_stats(self, audit_logger):
        """Test getting log statistics"""
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

        # Log some events
        await audit_logger.log("session_created", wallet_address, {}, "success")
        await audit_logger.log("wallet_connected", wallet_address, {}, "success")
        await audit_logger.log("code_executed", wallet_address, {"language": "python"}, "success")

        # Get stats
        stats = await audit_logger.get_log_stats()

        assert stats["total_entries"] == 3
        assert stats["events_count"]["session_created"] == 1
        assert stats["events_count"]["wallet_connected"] == 1
        assert stats["events_count"]["code_executed"] == 1
        assert stats["last_entry"] is not None
        assert stats["log_file_size"] > 0

    @pytest.mark.asyncio
    async def test_archive_old_logs(self, audit_logger):
        """Test archiving old logs"""
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

        # Create a config with short archive period
        audit_logger.config.archive_after_days = 0  # Archive immediately

        # Log some events
        await audit_logger.log("session_created", wallet_address, {}, "success")
        await audit_logger.log("wallet_connected", wallet_address, {}, "success")

        # Archive old logs
        archived_count = await audit_logger.archive_old_logs()

        # Verify logs were archived (archive_after_days=0 means all logs are "old")
        assert archived_count == 2

        # Check archive file exists
        archive_files = list(audit_logger.archive_dir.glob("audit_*.log"))
        assert len(archive_files) > 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_logs(self, audit_logger):
        """Test cleaning up expired logs"""
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

        # Create a config with short retention period
        audit_logger.config.retention_days = 0
        audit_logger.config.archive_after_days = 0

        # Log and archive
        await audit_logger.log("session_created", wallet_address, {}, "success")
        await audit_logger.archive_old_logs()

        # Get archive file
        archive_files = list(audit_logger.archive_dir.glob("audit_*.log"))
        assert len(archive_files) > 0

        # Clean up expired logs
        deleted_count = await audit_logger.cleanup_expired_logs()

        # Since retention_days=0, all archived files should be deleted
        assert deleted_count >= 1

    @pytest.mark.asyncio
    async def test_no_hash_user_id_config(self, temp_log_dir):
        """Test when hash_user_id is False"""
        config = AuditConfig(hash_user_id=False)
        audit_logger = AuditLogger(config=config, log_dir=temp_log_dir)

        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

        await audit_logger.log(
            event="session_created",
            wallet_address=wallet_address,
            details={},
            result="success"
        )

        # Read and verify log
        logs = await audit_logger.query_logs()
        assert len(logs) == 1
        assert logs[0]["user_hash"] == wallet_address  # Not hashed

    @pytest.mark.asyncio
    async def test_concurrent_logging(self, audit_logger):
        """Test concurrent logging with write lock"""
        wallet_address = "0x1234567890abcdef1234567890abcdef12345678"

        # Create multiple concurrent log tasks
        tasks = [
            audit_logger.log("code_executed", wallet_address, {"iteration": i}, "success")
            for i in range(100)
        ]

        # Execute concurrently
        await asyncio.gather(*tasks)

        # Verify all logs were written
        logs = await audit_logger.query_logs(limit=1000)
        assert len(logs) == 100

    @pytest.mark.asyncio
    async def test_empty_query(self, audit_logger):
        """Test querying when no logs exist"""
        logs = await audit_logger.query_logs()
        assert logs == []

        stats = await audit_logger.get_log_stats()
        assert stats["total_entries"] == 0
        assert stats["events_count"] == {}
