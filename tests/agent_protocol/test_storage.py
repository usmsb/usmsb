"""
Tests for Storage Layer

Unit tests for FileStorage, SQLiteStorage, IPFSStorage, and StorageManager.
"""

import asyncio
import os
import tempfile
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Import storage modules
from usmsb_sdk.platform.external.storage import (
    StorageInterface,
    StorageType,
    StorageResult,
    StorageError,
    DataLocation,
    FileStorage,
    SQLiteStorage,
    IPFSStorage,
    StorageManager,
    CacheStrategy,
    SyncStrategy,
    ConsistencyLevel,
    create_storage_manager,
)


class TestFileStorage:
    """Tests for FileStorage"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def file_storage(self, temp_dir):
        """Create a file storage instance"""
        return FileStorage(base_path=temp_dir)

    def test_creation(self, file_storage):
        """Test file storage creation"""
        assert file_storage is not None

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, file_storage):
        """Test storing and retrieving data"""
        key = "test/key.json"
        data = {"name": "test", "value": 123}

        # Store data
        result = await file_storage.store(key, data)
        assert result.success

        # Retrieve data
        retrieved = await file_storage.retrieve(key)
        assert retrieved.success
        assert retrieved.data == data

    @pytest.mark.asyncio
    async def test_delete(self, file_storage):
        """Test deleting data"""
        key = "test/delete.json"
        data = {"to_delete": True}

        # Store then delete
        await file_storage.store(key, data)
        result = await file_storage.delete(key)
        assert result.success

        # Verify deleted
        retrieved = await file_storage.retrieve(key)
        assert not retrieved.success


class TestSQLiteStorage:
    """Tests for SQLiteStorage"""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def sqlite_storage(self, temp_db):
        """Create a SQLite storage instance"""
        return SQLiteStorage(db_path=temp_db)

    def test_creation(self, sqlite_storage):
        """Test SQLite storage creation"""
        assert sqlite_storage is not None

    @pytest.mark.asyncio
    async def test_store_agent(self, sqlite_storage):
        """Test storing agent data"""
        agent_data = {
            "agent_id": "test-agent-001",
            "name": "TestAgent",
            "description": "Test",
            "status": "online",
        }
        result = await sqlite_storage.store_agent(agent_data)
        assert result.success

    @pytest.mark.asyncio
    async def test_retrieve_agent(self, sqlite_storage):
        """Test retrieving agent data"""
        agent_data = {
            "agent_id": "test-agent-002",
            "name": "TestAgent2",
        }
        await sqlite_storage.store_agent(agent_data)

        retrieved = await sqlite_storage.retrieve_agent("test-agent-002")
        assert retrieved.success
        assert retrieved.data["name"] == "TestAgent2"


class TestIPFSStorage:
    """Tests for IPFSStorage"""

    @pytest.fixture
    def ipfs_storage(self):
        """Create an IPFS storage instance"""
        # Use mock configuration for testing
        return IPFSStorage(
            gateway="https://ipfs.io",
            api_host=None,  # Disable actual IPFS connection for tests
        )

    def test_creation(self, ipfs_storage):
        """Test IPFS storage creation"""
        assert ipfs_storage is not None

    @pytest.mark.skip(reason="Requires IPFS connection")
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self, ipfs_storage):
        """Test storing and retrieving data from IPFS"""
        data = {"test": "ipfs_data"}
        result = await ipfs_storage.store(data)
        assert result.success
        assert result.cid is not None

        retrieved = await ipfs_storage.retrieve(result.cid)
        assert retrieved.success
        assert retrieved.data == data


class TestStorageManager:
    """Tests for StorageManager"""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def storage_manager(self, temp_dir):
        """Create a storage manager instance"""
        db_path = os.path.join(temp_dir, "test.db")
        return StorageManager(
            file_storage_path=temp_dir,
            sqlite_db_path=db_path,
            ipfs_enabled=False,  # Disable IPFS for tests
        )

    def test_creation(self, storage_manager):
        """Test storage manager creation"""
        assert storage_manager is not None

    @pytest.mark.asyncio
    async def test_store_with_cache(self, storage_manager):
        """Test storing data with caching"""
        key = "test/cached_data"
        data = {"cached": True}

        result = await storage_manager.store(
            key,
            data,
            cache_strategy=CacheStrategy.WRITE_THROUGH,
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_retrieve_from_cache(self, storage_manager):
        """Test retrieving data from cache"""
        key = "test/cache_retrieve"
        data = {"for_cache": True}

        # Store first
        await storage_manager.store(key, data)

        # Retrieve (should come from fastest layer)
        result = await storage_manager.retrieve(key)
        assert result.success
        assert result.data == data


class TestCreateStorageManager:
    """Tests for create_storage_manager factory function"""

    def test_create_default(self):
        """Test creating storage manager with defaults"""
        manager = create_storage_manager()
        assert manager is not None

    def test_create_with_config(self):
        """Test creating storage manager with configuration"""
        manager = create_storage_manager(
            file_storage_path="./data/files",
            sqlite_db_path="./data/test.db",
            ipfs_enabled=False,
        )
        assert manager is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
