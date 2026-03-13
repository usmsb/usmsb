"""
Base Storage Interface

Defines the unified storage interface that all storage backends must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union


class StorageType(Enum):
    """Enumeration of storage types."""
    FILE = "file"
    SQLITE = "sqlite"
    IPFS = "ipfs"


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class DataNotFoundError(StorageError):
    """Raised when data is not found."""
    pass


class DataExistsError(StorageError):
    """Raised when data already exists."""
    pass


class StorageConnectionError(StorageError):
    """Raised when connection to storage fails."""
    pass


class StorageOperationError(StorageError):
    """Raised when a storage operation fails."""
    pass


@dataclass
class DataLocation:
    """Represents the location of data in the storage system."""
    storage_type: StorageType
    key: str
    path: Optional[str] = None
    cid: Optional[str] = None  # IPFS Content ID
    version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "storage_type": self.storage_type.value,
            "key": self.key,
            "path": self.path,
            "cid": self.cid,
            "version": self.version,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataLocation":
        """Create from dictionary."""
        return cls(
            storage_type=StorageType(data["storage_type"]),
            key=data["key"],
            path=data.get("path"),
            cid=data.get("cid"),
            version=data.get("version"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class StorageResult:
    """Result of a storage operation."""
    success: bool
    data: Optional[Any] = None
    location: Optional[DataLocation] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "location": self.location.to_dict() if self.location else None,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


T = TypeVar("T")


class StorageInterface(ABC, Generic[T]):
    """
    Abstract base class for all storage backends.

    This interface defines the common operations that all storage
    implementations must support, ensuring consistency across
    different storage layers.
    """

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the storage backend.

        Returns:
            True if initialization was successful, False otherwise.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the storage backend and release resources."""
        pass

    @abstractmethod
    async def store(
        self,
        key: str,
        data: T,
        metadata: Optional[Dict[str, Any]] = None,
        overwrite: bool = False,
    ) -> StorageResult:
        """
        Store data with the given key.

        Args:
            key: Unique identifier for the data.
            data: The data to store.
            metadata: Optional metadata associated with the data.
            overwrite: If True, overwrite existing data; if False, raise error on conflict.

        Returns:
            StorageResult indicating success/failure and location of stored data.
        """
        pass

    @abstractmethod
    async def retrieve(self, key: str) -> StorageResult:
        """
        Retrieve data by key.

        Args:
            key: Unique identifier for the data.

        Returns:
            StorageResult containing the retrieved data or error.
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> StorageResult:
        """
        Delete data by key.

        Args:
            key: Unique identifier for the data.

        Returns:
            StorageResult indicating success/failure.
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if data exists for the given key.

        Args:
            key: Unique identifier for the data.

        Returns:
            True if data exists, False otherwise.
        """
        pass

    @abstractmethod
    async def list_keys(
        self,
        prefix: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[str]:
        """
        List all keys in storage.

        Args:
            prefix: Optional prefix to filter keys.
            limit: Maximum number of keys to return.
            offset: Number of keys to skip.

        Returns:
            List of keys matching the criteria.
        """
        pass

    @abstractmethod
    async def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a key without retrieving the full data.

        Args:
            key: Unique identifier for the data.

        Returns:
            Metadata dictionary or None if key not found.
        """
        pass

    @abstractmethod
    async def update_metadata(
        self,
        key: str,
        metadata: Dict[str, Any],
        merge: bool = True,
    ) -> StorageResult:
        """
        Update metadata for a key.

        Args:
            key: Unique identifier for the data.
            metadata: New metadata to set/merge.
            merge: If True, merge with existing metadata; if False, replace.

        Returns:
            StorageResult indicating success/failure.
        """
        pass

    @property
    @abstractmethod
    def storage_type(self) -> StorageType:
        """Return the type of this storage backend."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the storage backend is connected and ready."""
        pass

    # Optional methods with default implementations

    async def batch_store(
        self,
        items: Dict[str, T],
        metadata: Optional[Dict[str, Dict[str, Any]]] = None,
        overwrite: bool = False,
    ) -> Dict[str, StorageResult]:
        """
        Store multiple items in a batch.

        Args:
            items: Dictionary mapping keys to data.
            metadata: Optional dictionary mapping keys to their metadata.
            overwrite: If True, overwrite existing data.

        Returns:
            Dictionary mapping keys to their StorageResults.
        """
        results = {}
        metadata = metadata or {}
        for key, data in items.items():
            results[key] = await self.store(
                key,
                data,
                metadata.get(key),
                overwrite,
            )
        return results

    async def batch_retrieve(self, keys: List[str]) -> Dict[str, StorageResult]:
        """
        Retrieve multiple items in a batch.

        Args:
            keys: List of keys to retrieve.

        Returns:
            Dictionary mapping keys to their StorageResults.
        """
        results = {}
        for key in keys:
            results[key] = await self.retrieve(key)
        return results

    async def batch_delete(self, keys: List[str]) -> Dict[str, StorageResult]:
        """
        Delete multiple items in a batch.

        Args:
            keys: List of keys to delete.

        Returns:
            Dictionary mapping keys to their StorageResults.
        """
        results = {}
        for key in keys:
            results[key] = await self.delete(key)
        return results

    async def clear(self) -> StorageResult:
        """
        Clear all data from storage.

        Returns:
            StorageResult indicating success/failure.
        """
        return StorageResult(
            success=False,
            error="Clear operation not implemented for this storage type",
        )

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dictionary containing storage statistics.
        """
        return {
            "storage_type": self.storage_type.value,
            "connected": self.is_connected,
        }


class AsyncStorageInterface(StorageInterface[T]):
    """
    Extended interface for storage backends with async batch operations.
    """

    async def store_with_ttl(
        self,
        key: str,
        data: T,
        ttl_seconds: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StorageResult:
        """
        Store data with a time-to-live.

        Args:
            key: Unique identifier for the data.
            data: The data to store.
            ttl_seconds: Time-to-live in seconds.
            metadata: Optional metadata.

        Returns:
            StorageResult indicating success/failure.
        """
        raise NotImplementedError("TTL not supported by this storage backend")

    async def watch(
        self,
        key: str,
        callback: callable,
    ) -> str:
        """
        Watch a key for changes and call callback on change.

        Args:
            key: Key to watch.
            callback: Async function to call when data changes.

        Returns:
            Watch ID that can be used to unwatch.
        """
        raise NotImplementedError("Watch not supported by this storage backend")

    async def unwatch(self, watch_id: str) -> bool:
        """
        Stop watching a key.

        Args:
            watch_id: ID returned from watch().

        Returns:
            True if successfully unwatched.
        """
        raise NotImplementedError("Watch not supported by this storage backend")
