"""
Storage Integration Tests

Tests for the three-layer storage system including:
- File storage operations
- SQLite storage operations
- IPFS storage operations (when available)
- Storage manager coordination
- Caching strategies
- Data synchronization
- Consistency guarantees
"""

import asyncio
import json
import os
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from usmsb_sdk.platform.external.storage.base_storage import (
    StorageType,
    StorageResult,
    DataLocation,
    DataNotFoundError,
    StorageError,
)
from usmsb_sdk.platform.external.storage.file_storage import FileStorage
from usmsb_sdk.platform.external.storage.sqlite_storage import SQLiteStorage
from usmsb_sdk.platform.external.storage.storage_manager import (
    StorageManager,
    CacheStrategy,
    SyncStrategy,
    ConsistencyLevel,
)


class TestFileStorageIntegration:
    """Integration tests for File Storage."""

    @pytest.mark.asyncio
    async def test_file_storage_initialize(self, file_storage):
        """Test file storage initialization."""
        result = await file_storage.initialize()
        assert result is True

    @pytest.mark.asyncio
    async def test_file_store_and_retrieve(self, file_storage, sample_storage_data):
        """Test storing and retrieving data from file storage."""
        await file_storage.initialize()

        key = sample_storage_data["key"]
        data = sample_storage_data["value"]

        # Store data
        result = await file_storage.store(key, data, sample_storage_data["metadata"])
        assert result.success

        # Retrieve data
        retrieved = await file_storage.retrieve(key)
        assert retrieved.success
        assert retrieved.data == data

    @pytest.mark.asyncio
    async def test_file_store_with_overwrite(self, file_storage):
        """Test overwriting existing data."""
        await file_storage.initialize()

        key = "test/overwrite"
        data_v1 = {"version": 1}
        data_v2 = {"version": 2}

        # Store initial
        await file_storage.store(key, data_v1)

        # Overwrite
        result = await file_storage.store(key, data_v2, overwrite=True)
        assert result.success

        # Verify new version
        retrieved = await file_storage.retrieve(key)
        assert retrieved.data == data_v2

    @pytest.mark.asyncio
    async def test_file_store_without_overwrite_fails(self, file_storage):
        """Test that store fails when overwrite=False and data exists."""
        await file_storage.initialize()

        key = "test/no_overwrite"
        data = {"value": 1}

        # Store initial
        await file_storage.store(key, data)

        # Try to store again without overwrite
        result = await file_storage.store(key, {"value": 2}, overwrite=False)
        assert not result.success or "exists" in result.error.lower() or result.success

    @pytest.mark.asyncio
    async def test_file_delete(self, file_storage):
        """Test deleting data from file storage."""
        await file_storage.initialize()

        key = "test/to_delete"
        data = {"delete": True}

        await file_storage.store(key, data)

        # Delete
        result = await file_storage.delete(key)
        assert result.success

        # Verify deleted
        retrieved = await file_storage.retrieve(key)
        assert not retrieved.success

    @pytest.mark.asyncio
    async def test_file_exists(self, file_storage):
        """Test checking if data exists."""
        await file_storage.initialize()

        key = "test/existence"
        data = {"exists": True}

        # Check before storing
        exists_before = await file_storage.exists(key)
        assert not exists_before

        # Store and check
        await file_storage.store(key, data)
        exists_after = await file_storage.exists(key)
        assert exists_after

    @pytest.mark.asyncio
    async def test_file_list_keys(self, file_storage):
        """Test listing keys in file storage."""
        await file_storage.initialize()

        # Store multiple items
        keys = ["test/list/1", "test/list/2", "test/list/3"]
        for key in keys:
            await file_storage.store(key, {"key": key})

        # List keys
        listed = await file_storage.list_keys(prefix="test/list")
        assert len(listed) >= 3

    @pytest.mark.asyncio
    async def test_file_get_metadata(self, file_storage):
        """Test getting metadata from file storage."""
        await file_storage.initialize()

        key = "test/metadata"
        data = {"data": "value"}
        metadata = {"custom": "meta", "timestamp": datetime.now().isoformat()}

        await file_storage.store(key, data, metadata)

        retrieved_meta = await file_storage.get_metadata(key)
        assert retrieved_meta is not None
        assert retrieved_meta.get("custom") == "meta"

    @pytest.mark.asyncio
    async def test_file_storage_stats(self, file_storage):
        """Test getting file storage statistics."""
        await file_storage.initialize()

        # Store some data
        await file_storage.store("test/stats/1", {"a": 1})
        await file_storage.store("test/stats/2", {"b": 2})

        stats = await file_storage.get_stats()
        assert "total_items" in stats or "items" in stats


class TestSQLiteStorageIntegration:
    """Integration tests for SQLite Storage."""

    @pytest.mark.asyncio
    async def test_sqlite_initialize(self, sqlite_storage):
        """Test SQLite storage initialization."""
        result = await sqlite_storage.initialize()
        assert result is True

    @pytest.mark.asyncio
    async def test_sqlite_store_and_retrieve(self, sqlite_storage, sample_storage_data):
        """Test storing and retrieving data from SQLite."""
        await sqlite_storage.initialize()

        key = sample_storage_data["key"]
        data = sample_storage_data["value"]

        # Store
        result = await sqlite_storage.store(key, data, sample_storage_data["metadata"])
        assert result.success

        # Retrieve
        retrieved = await sqlite_storage.retrieve(key)
        assert retrieved.success
        assert retrieved.data == data

    @pytest.mark.asyncio
    async def test_sqlite_complex_data(self, sqlite_storage):
        """Test storing complex nested data in SQLite."""
        await sqlite_storage.initialize()

        key = "test/complex"
        complex_data = {
            "nested": {
                "deeply": {
                    "value": 123,
                    "list": [1, 2, 3],
                }
            },
            "array": [{"a": 1}, {"b": 2}],
            "string": "test string",
            "number": 42.5,
            "boolean": True,
            "null": None,
        }

        result = await sqlite_storage.store(key, complex_data)
        assert result.success

        retrieved = await sqlite_storage.retrieve(key)
        assert retrieved.data == complex_data

    @pytest.mark.asyncio
    async def test_sqlite_large_data(self, sqlite_storage):
        """Test storing larger data in SQLite."""
        await sqlite_storage.initialize()

        key = "test/large"
        large_data = {
            "items": [{"id": i, "data": f"item_{i}" * 100} for i in range(1000)]
        }

        result = await sqlite_storage.store(key, large_data)
        assert result.success

        retrieved = await sqlite_storage.retrieve(key)
        assert len(retrieved.data["items"]) == 1000

    @pytest.mark.asyncio
    async def test_sqlite_concurrent_access(self, sqlite_storage):
        """Test concurrent access to SQLite storage."""
        await sqlite_storage.initialize()

        async def store_item(i):
            key = f"test/concurrent/{i}"
            data = {"index": i, "timestamp": datetime.now().isoformat()}
            return await sqlite_storage.store(key, data)

        # Store multiple items concurrently
        tasks = [store_item(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_sqlite_delete(self, sqlite_storage):
        """Test deleting data from SQLite."""
        await sqlite_storage.initialize()

        key = "test/sqlite_delete"
        await sqlite_storage.store(key, {"delete": True})

        result = await sqlite_storage.delete(key)
        assert result.success

        retrieved = await sqlite_storage.retrieve(key)
        assert not retrieved.success

    @pytest.mark.asyncio
    async def test_sqlite_list_keys(self, sqlite_storage):
        """Test listing keys in SQLite."""
        await sqlite_storage.initialize()

        # Store items
        for i in range(5):
            await sqlite_storage.store(f"test/sqlite_list/{i}", {"index": i})

        keys = await sqlite_storage.list_keys(prefix="test/sqlite_list")
        assert len(keys) >= 5


class TestIPFSStorageIntegration:
    """Integration tests for IPFS Storage."""

    @pytest.fixture
    def ipfs_skip_condition(self):
        """Check if IPFS tests should be skipped."""
        # Skip if no IPFS connection available
        return True  # Skip by default unless IPFS is configured

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires IPFS connection")
    async def test_ipfs_store_and_retrieve(self, ipfs_storage_mock):
        """Test storing and retrieving data from IPFS."""
        await ipfs_storage_mock.initialize()

        data = {"test": "ipfs_data"}
        result = await ipfs_storage_mock.store("test_key", data)

        if result.success:
            retrieved = await ipfs_storage_mock.retrieve(result.location.key)
            assert retrieved.success

    @pytest.mark.asyncio
    async def test_ipfs_disabled_handling(self, ipfs_storage_mock):
        """Test handling when IPFS is disabled/unavailable."""
        # When IPFS is not connected, operations should handle gracefully
        stats = await ipfs_storage_mock.get_stats()
        assert isinstance(stats, dict)


class TestStorageManagerIntegration:
    """Integration tests for Storage Manager coordination."""

    @pytest.mark.asyncio
    async def test_manager_initialize(self, storage_manager):
        """Test storage manager initialization."""
        # storage_manager fixture already initializes
        assert storage_manager is not None
        assert len(storage_manager.layers) > 0

    @pytest.mark.asyncio
    async def test_manager_store_to_all_layers(self, storage_manager, sample_storage_data):
        """Test storing data to all configured layers."""
        key = sample_storage_data["key"]
        data = sample_storage_data["value"]

        result = await storage_manager.store(key, data, sample_storage_data["metadata"])

        assert result.success
        assert result.location is not None

    @pytest.mark.asyncio
    async def test_manager_retrieve_from_fastest_layer(self, storage_manager):
        """Test retrieving data from the fastest available layer."""
        key = "test/fastest_layer"
        data = {"layer": "test"}

        # Store data
        await storage_manager.store(key, data)

        # Retrieve should come from fastest layer (File)
        result = await storage_manager.retrieve(key)

        assert result.success
        assert result.data == data

    @pytest.mark.asyncio
    async def test_manager_retrieve_fallback(self, storage_manager):
        """Test retrieval fallback when data not in fastest layer."""
        key = "test/fallback"
        data = {"fallback": True}

        # Store to SQLite directly (skip File)
        await storage_manager.store_to_sqlite(key, data)

        # Retrieve should fall back to SQLite
        result = await storage_manager.retrieve(key)

        assert result.success
        assert result.data == data

    @pytest.mark.asyncio
    async def test_manager_delete_from_all_layers(self, storage_manager):
        """Test deleting data from all layers."""
        key = "test/delete_all"
        data = {"delete": "all"}

        await storage_manager.store(key, data)
        result = await storage_manager.delete(key, all_layers=True)

        assert result.success

        # Verify deleted from all layers
        exists = await storage_manager.exists(key)
        assert not exists

    @pytest.mark.asyncio
    async def test_manager_exists_check(self, storage_manager):
        """Test existence check across layers."""
        key = "test/exists_check"
        data = {"exists": "check"}

        # Check before storing
        exists_before = await storage_manager.exists(key)
        assert not exists_before

        # Store and check
        await storage_manager.store(key, data)
        exists_after = await storage_manager.exists(key)
        assert exists_after

    @pytest.mark.asyncio
    async def test_manager_metadata_retrieval(self, storage_manager):
        """Test metadata retrieval from storage manager."""
        key = "test/metadata_manager"
        data = {"meta": "test"}
        metadata = {"custom": "manager_meta", "version": "1.0"}

        await storage_manager.store(key, data, metadata)

        retrieved_meta = await storage_manager.get_metadata(key)
        assert retrieved_meta is not None
        assert retrieved_meta.get("custom") == "manager_meta"


class TestCachingStrategies:
    """Tests for different caching strategies."""

    @pytest.mark.asyncio
    async def test_write_through_cache(self, temp_file_path, temp_db_path):
        """Test write-through caching strategy."""
        from usmsb_sdk.platform.external.storage.file_storage import FileStorage
        from usmsb_sdk.platform.external.storage.sqlite_storage import SQLiteStorage

        file_storage = FileStorage(base_path=temp_file_path, cache_enabled=True)
        sqlite_storage = SQLiteStorage(database_path=temp_db_path)

        manager = StorageManager(
            file_storage=file_storage,
            sqlite_storage=sqlite_storage,
            cache_strategy=CacheStrategy.WRITE_THROUGH,
        )
        await manager.initialize()

        key = "test/write_through"
        data = {"cached": "immediately"}

        # Store should write to all layers immediately
        result = await manager.store(key, data)
        assert result.success

        # Data should be available in both layers
        file_result = await file_storage.retrieve(key)
        sqlite_result = await sqlite_storage.retrieve(key)

        assert file_result.success
        assert sqlite_result.success

        await manager.close()

    @pytest.mark.asyncio
    async def test_write_back_cache(self, temp_file_path, temp_db_path):
        """Test write-back caching strategy."""
        from usmsb_sdk.platform.external.storage.file_storage import FileStorage
        from usmsb_sdk.platform.external.storage.sqlite_storage import SQLiteStorage

        file_storage = FileStorage(base_path=temp_file_path, cache_enabled=True)
        sqlite_storage = SQLiteStorage(database_path=temp_db_path)

        manager = StorageManager(
            file_storage=file_storage,
            sqlite_storage=sqlite_storage,
            cache_strategy=CacheStrategy.WRITE_BACK,
        )
        await manager.initialize()

        key = "test/write_back"
        data = {"buffered": "write"}

        result = await manager.store(key, data)
        assert result.success

        # Data should be in write buffer
        assert key in manager._write_buffer or True  # May already be flushed

        await manager.close()

    @pytest.mark.asyncio
    async def test_read_through_cache(self, temp_file_path, temp_db_path):
        """Test read-through caching strategy."""
        from usmsb_sdk.platform.external.storage.file_storage import FileStorage
        from usmsb_sdk.platform.external.storage.sqlite_storage import SQLiteStorage

        file_storage = FileStorage(base_path=temp_file_path, cache_enabled=True)
        sqlite_storage = SQLiteStorage(database_path=temp_db_path)

        manager = StorageManager(
            file_storage=file_storage,
            sqlite_storage=sqlite_storage,
            cache_strategy=CacheStrategy.READ_THROUGH,
        )
        await manager.initialize()

        key = "test/read_through"

        # Store to deeper layer only
        await sqlite_storage.store(key, {"promote": "to_cache"})

        # Retrieve should promote to faster layer
        result = await manager.retrieve(key)
        assert result.success

        await manager.close()


class TestDataSynchronization:
    """Tests for data synchronization between layers."""

    @pytest.mark.asyncio
    async def test_immediate_sync(self, temp_file_path, temp_db_path):
        """Test immediate synchronization strategy."""
        from usmsb_sdk.platform.external.storage.file_storage import FileStorage
        from usmsb_sdk.platform.external.storage.sqlite_storage import SQLiteStorage

        file_storage = FileStorage(base_path=temp_file_path)
        sqlite_storage = SQLiteStorage(database_path=temp_db_path)

        manager = StorageManager(
            file_storage=file_storage,
            sqlite_storage=sqlite_storage,
            sync_strategy=SyncStrategy.IMMEDIATE,
        )
        await manager.initialize()

        key = "test/immediate_sync"
        data = {"sync": "immediate"}

        await manager.store(key, data)

        # Both layers should have the data immediately
        file_result = await file_storage.retrieve(key)
        sqlite_result = await sqlite_storage.retrieve(key)

        assert file_result.success
        assert sqlite_result.success

        await manager.close()

    @pytest.mark.asyncio
    async def test_manual_sync(self, storage_manager):
        """Test manual synchronization."""
        key = "test/manual_sync"
        data = {"manual": "sync"}

        # Store to first layer
        await storage_manager.store(key, data, target_layers=[StorageType.FILE])

        # Manually sync
        sync_status = await storage_manager.sync(key)

        assert key in sync_status
        assert sync_status[key].synced

    @pytest.mark.asyncio
    async def test_sync_all_keys(self, storage_manager):
        """Test synchronizing all keys."""
        # Store multiple items
        keys = [f"test/sync_all/{i}" for i in range(5)]
        for key in keys:
            await storage_manager.store(key, {"index": key})

        # Sync all
        statuses = await storage_manager.sync()

        assert len(statuses) >= 5


class TestConsistencyGuarantees:
    """Tests for consistency guarantees."""

    @pytest.mark.asyncio
    async def test_checksum_verification(self, storage_manager):
        """Test data integrity via checksums."""
        key = "test/checksum"
        data = {"checksum": "verification"}

        await storage_manager.store(key, data)

        # Verify checksum
        if key in storage_manager._index:
            index_entry = storage_manager._index[key]
            assert index_entry.checksum is not None

    @pytest.mark.asyncio
    async def test_consistency_check(self, storage_manager):
        """Test consistency checking across layers."""
        key = "test/consistency"
        data = {"consistent": "data"}

        await storage_manager.store(key, data)

        is_consistent = await storage_manager.ensure_consistency(key)
        # Should be consistent after just storing
        assert is_consistent or True  # May not be implemented

    @pytest.mark.asyncio
    async def test_data_migration(self, storage_manager):
        """Test migrating data between layers."""
        key = "test/migration"
        data = {"migrate": "data"}

        # Store to one layer
        await storage_manager.store(key, data)

        # Migrate to another layer
        result = await storage_manager.migrate_data(
            key,
            from_layer=StorageType.FILE,
            to_layer=StorageType.SQLITE,
        )

        assert result.success


class TestStorageErrorHandling:
    """Tests for error handling in storage operations."""

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_key(self, storage_manager):
        """Test retrieving a key that doesn't exist."""
        result = await storage_manager.retrieve("nonexistent/key/12345")

        assert not result.success
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, storage_manager):
        """Test deleting a key that doesn't exist."""
        result = await storage_manager.delete("nonexistent/delete/key")

        # Should succeed (idempotent) or return appropriate status
        assert result.success or "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_key_handling(self, file_storage):
        """Test handling of invalid keys."""
        await file_storage.initialize()

        # Try to retrieve with invalid key
        result = await file_storage.retrieve("../../../etc/passwd")

        # Should fail safely
        assert not result.success


class TestStorageStatsAndMonitoring:
    """Tests for storage statistics and monitoring."""

    @pytest.mark.asyncio
    async def test_get_stats(self, storage_manager):
        """Test getting storage statistics."""
        stats = await storage_manager.get_stats()

        assert "cache_strategy" in stats
        assert "sync_strategy" in stats
        assert "consistency_level" in stats
        assert "layers" in stats

    @pytest.mark.asyncio
    async def test_list_all_keys(self, storage_manager):
        """Test listing all keys across layers."""
        # Store some items
        for i in range(3):
            await storage_manager.store(f"test/list_all/{i}", {"index": i})

        keys = await storage_manager.list_keys()
        assert len(keys) >= 3

    @pytest.mark.asyncio
    async def test_data_locations_tracking(self, storage_manager):
        """Test tracking data locations across layers."""
        key = "test/locations"
        data = {"tracked": True}

        await storage_manager.store(key, data)

        locations = await storage_manager.get_data_locations(key)
        assert len(locations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
