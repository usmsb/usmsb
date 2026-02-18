"""
Storage Module

Three-layer storage system for USMSB SDK:
- File Storage: Local JSON files with caching
- SQLite Storage: Persistent database for structured data
- IPFS Storage: Decentralized storage for distributed data
"""

from usmsb_sdk.platform.external.storage.base_storage import (
    StorageInterface,
    StorageType,
    StorageResult,
    StorageError,
    DataLocation,
)
from usmsb_sdk.platform.external.storage.file_storage import (
    FileStorage,
    FileLockManager,
)
from usmsb_sdk.platform.external.storage.sqlite_storage import (
    SQLiteStorage,
    SessionStateManager,
    TransactionRecordManager,
    AgentRegistryManager,
)
from usmsb_sdk.platform.external.storage.ipfs_storage import (
    IPFSStorage,
    DataShardingManager,
    IPFSConnectionConfig,
)
from usmsb_sdk.platform.external.storage.storage_manager import (
    StorageManager,
    CacheStrategy,
    SyncStrategy,
    ConsistencyLevel,
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
]
