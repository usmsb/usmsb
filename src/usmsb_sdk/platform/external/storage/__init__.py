"""
Storage Module

Three-layer storage system for USMSB SDK:
- File Storage: Local JSON files with caching
- SQLite Storage: Persistent database for structured data
- IPFS Storage: Decentralized storage for distributed data
"""

from usmsb_sdk.platform.external.storage.base_storage import (
    DataLocation,
    StorageError,
    StorageInterface,
    StorageResult,
    StorageType,
)
from usmsb_sdk.platform.external.storage.file_storage import (
    FileLockManager,
    FileStorage,
)
from usmsb_sdk.platform.external.storage.ipfs_storage import (
    DataShardingManager,
    IPFSConnectionConfig,
    IPFSStorage,
)
from usmsb_sdk.platform.external.storage.sqlite_storage import (
    AgentRegistryManager,
    SessionStateManager,
    SQLiteStorage,
    TransactionRecordManager,
)
from usmsb_sdk.platform.external.storage.storage_manager import (
    CacheStrategy,
    ConsistencyLevel,
    StorageManager,
    SyncStrategy,
    create_storage_manager,
)

__all__ = [
    # Base
    "StorageInterface",
    "StorageType",
    "StorageResult",
    "StorageError",
    "DataLocation",
    # File Storage
    "FileStorage",
    "FileLockManager",
    # SQLite Storage
    "SQLiteStorage",
    "SessionStateManager",
    "TransactionRecordManager",
    "AgentRegistryManager",
    # IPFS Storage
    "IPFSStorage",
    "DataShardingManager",
    "IPFSConnectionConfig",
    # Storage Manager
    "StorageManager",
    "CacheStrategy",
    "SyncStrategy",
    "ConsistencyLevel",
    "create_storage_manager",
]
