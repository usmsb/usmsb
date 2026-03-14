"""
File Storage Implementation

Provides local file-based storage with JSON support, caching, and file locking.
"""

import hashlib
import json
import logging
import os
import sys
import tempfile
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Union

# Platform-specific file locking
if sys.platform == 'win32':
    HAS_FCNTL = False
else:
    try:
        import fcntl
        HAS_FCNTL = True
    except ImportError:
        HAS_FCNTL = False

from usmsb_sdk.platform.external.storage.base_storage import (
    DataExistsError,
    DataLocation,
    DataNotFoundError,
    StorageInterface,
    StorageResult,
    StorageType,
)

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cached item."""
    data: Any
    metadata: dict[str, Any]
    timestamp: datetime
    access_count: int = 0
    last_access: datetime = field(default_factory=datetime.utcnow)
    size_bytes: int = 0

    def touch(self) -> None:
        """Update access time and count."""
        self.last_access = datetime.utcnow()
        self.access_count += 1


class FileLockManager:
    """
    Manages file locks for concurrent access control.

    Supports both thread-level and process-level locking.
    """

    def __init__(self, lock_dir: Path | None = None):
        """
        Initialize the lock manager.

        Args:
            lock_dir: Directory for lock files. Defaults to temp directory.
        """
        self.lock_dir = lock_dir or Path(tempfile.gettempdir()) / "usmsb_locks"
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self._thread_locks: dict[str, threading.Lock] = {}
        self._process_locks: dict[str, tuple[Any, Path]] = {}
        self._lock = threading.Lock()

    def _get_lock_path(self, key: str) -> Path:
        """Get lock file path for a key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.lock_dir / f"{key_hash}.lock"

    def acquire_thread_lock(self, key: str, timeout: float = 10.0) -> bool:
        """
        Acquire a thread-level lock for the key.

        Args:
            key: The key to lock.
            timeout: Maximum time to wait for lock.

        Returns:
            True if lock acquired, False if timeout.
        """
        with self._lock:
            if key not in self._thread_locks:
                self._thread_locks[key] = threading.Lock()

            lock = self._thread_locks[key]

        return lock.acquire(timeout=timeout)

    def release_thread_lock(self, key: str) -> None:
        """Release thread-level lock for the key."""
        with self._lock:
            if key in self._thread_locks:
                try:
                    self._thread_locks[key].release()
                except RuntimeError:
                    pass  # Lock not held

    def acquire_process_lock(self, key: str, timeout: float = 10.0) -> bool:
        """
        Acquire a process-level lock for the key.

        Args:
            key: The key to lock.
            timeout: Maximum time to wait for lock.

        Returns:
            True if lock acquired, False if timeout.
        """
        lock_path = self._get_lock_path(key)
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with self._lock:
                    self._process_locks[key] = (fd, lock_path)
                return True
            except FileExistsError:
                # Check if lock is stale (older than 60 seconds)
                try:
                    stat = lock_path.stat()
                    if time.time() - stat.st_mtime > 60:
                        lock_path.unlink()
                        continue
                except FileNotFoundError:
                    pass
                time.sleep(0.1)

        return False

    def release_process_lock(self, key: str) -> None:
        """Release process-level lock for the key."""
        with self._lock:
            if key in self._process_locks:
                fd, lock_path = self._process_locks[key]
                try:
                    os.close(fd)
                    lock_path.unlink()
                except (OSError, FileNotFoundError):
                    pass
                del self._process_locks[key]

    def acquire(self, key: str, timeout: float = 10.0) -> bool:
        """
        Acquire both thread and process locks.

        Args:
            key: The key to lock.
            timeout: Maximum time to wait.

        Returns:
            True if both locks acquired.
        """
        if not self.acquire_thread_lock(key, timeout):
            return False
        if not self.acquire_process_lock(key, timeout):
            self.release_thread_lock(key)
            return False
        return True

    def release(self, key: str) -> None:
        """Release both thread and process locks."""
        self.release_process_lock(key)
        self.release_thread_lock(key)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Release all locks on context exit
        for key in list(self._thread_locks.keys()):
            self.release_thread_lock(key)
        for key in list(self._process_locks.keys()):
            self.release_process_lock(key)


class LRUCache:
    """
    Thread-safe LRU cache implementation.
    """

    def __init__(self, max_size: int = 1000, max_bytes: int = 100 * 1024 * 1024):
        """
        Initialize LRU cache.

        Args:
            max_size: Maximum number of items.
            max_bytes: Maximum total size in bytes.
        """
        self.max_size = max_size
        self.max_bytes = max_bytes
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._current_bytes = 0
        self._lock = threading.RLock()

    def _estimate_size(self, data: Any) -> int:
        """Estimate size of data in bytes."""
        try:
            return len(json.dumps(data))
        except (TypeError, ValueError):
            return 0

    def get(self, key: str) -> CacheEntry | None:
        """Get item from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                entry.touch()
                self._cache[key] = entry
                return entry
            return None

    def put(self, key: str, data: Any, metadata: dict[str, Any]) -> None:
        """Put item in cache."""
        with self._lock:
            size = self._estimate_size(data)

            # Remove if already exists
            if key in self._cache:
                old_entry = self._cache.pop(key)
                self._current_bytes -= old_entry.size_bytes

            # Evict items if necessary
            while (
                len(self._cache) >= self.max_size or
                (self._current_bytes + size) > self.max_bytes
            ):
                if not self._cache:
                    break
                oldest_key, oldest_entry = self._cache.popitem(last=False)
                self._current_bytes -= oldest_entry.size_bytes

            # Add new entry
            entry = CacheEntry(
                data=data,
                metadata=metadata,
                timestamp=datetime.utcnow(),
                size_bytes=size,
            )
            self._cache[key] = entry
            self._current_bytes += size

    def remove(self, key: str) -> bool:
        """Remove item from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                self._current_bytes -= entry.size_bytes
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._current_bytes = 0

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                "item_count": len(self._cache),
                "current_bytes": self._current_bytes,
                "max_size": self.max_size,
                "max_bytes": self.max_bytes,
                "utilization_percent": (self._current_bytes / self.max_bytes) * 100 if self.max_bytes > 0 else 0,
            }


class FileStorage(StorageInterface[Union[dict, list, str, int, float, bool]]):
    """
    File-based storage implementation with JSON support, caching, and locking.

    Features:
    - JSON file read/write
    - LRU caching
    - File locking for concurrent access
    - Automatic expiration of cached items
    """

    def __init__(
        self,
        base_path: str | Path,
        cache_enabled: bool = True,
        cache_max_size: int = 1000,
        cache_max_bytes: int = 100 * 1024 * 1024,
        cache_ttl_seconds: int = 3600,
        use_locking: bool = True,
    ):
        """
        Initialize file storage.

        Args:
            base_path: Base directory for storage files.
            cache_enabled: Enable/disable caching.
            cache_max_size: Maximum number of cached items.
            cache_max_bytes: Maximum cache size in bytes.
            cache_ttl_seconds: Time-to-live for cached items.
            use_locking: Enable/disable file locking.
        """
        self.base_path = Path(base_path)
        self.cache_enabled = cache_enabled
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.use_locking = use_locking

        # Initialize components
        self._cache = LRUCache(cache_max_size, cache_max_bytes) if cache_enabled else None
        self._lock_manager = FileLockManager() if use_locking else None
        self._initialized = False
        self._connected = False

    async def initialize(self) -> bool:
        """Initialize the storage backend."""
        try:
            # Create base directory if it doesn't exist
            self.base_path.mkdir(parents=True, exist_ok=True)

            # Create subdirectories
            (self.base_path / "data").mkdir(exist_ok=True)
            (self.base_path / "metadata").mkdir(exist_ok=True)
            (self.base_path / "cache").mkdir(exist_ok=True)

            self._initialized = True
            self._connected = True
            logger.info(f"FileStorage initialized at {self.base_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize FileStorage: {e}")
            return False

    async def close(self) -> None:
        """Close the storage backend."""
        if self._cache:
            self._cache.clear()
        self._connected = False
        logger.info("FileStorage closed")

    @property
    def storage_type(self) -> StorageType:
        return StorageType.FILE

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _get_data_path(self, key: str) -> Path:
        """Get path for data file."""
        safe_key = self._sanitize_key(key)
        return self.base_path / "data" / f"{safe_key}.json"

    def _get_metadata_path(self, key: str) -> Path:
        """Get path for metadata file."""
        safe_key = self._sanitize_key(key)
        return self.base_path / "metadata" / f"{safe_key}.meta.json"

    def _sanitize_key(self, key: str) -> str:
        """Sanitize key for use as filename."""
        # Replace problematic characters
        safe_key = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
        # Hash if too long
        if len(safe_key) > 200:
            key_hash = hashlib.md5(key.encode()).hexdigest()
            safe_key = f"{safe_key[:50]}_{key_hash}"
        return safe_key

    def _is_cache_valid(self, entry: CacheEntry) -> bool:
        """Check if cache entry is still valid."""
        return datetime.utcnow() - entry.timestamp < self.cache_ttl

    async def store(
        self,
        key: str,
        data: dict | list | str | int | float | bool,
        metadata: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> StorageResult:
        """Store data to file."""
        try:
            data_path = self._get_data_path(key)
            meta_path = self._get_metadata_path(key)

            # Check if exists
            if data_path.exists() and not overwrite:
                raise DataExistsError(f"Data already exists for key: {key}")

            # Acquire lock if enabled
            if self._lock_manager:
                if not self._lock_manager.acquire(key):
                    return StorageResult(
                        success=False,
                        error=f"Failed to acquire lock for key: {key}",
                    )

            try:
                # Prepare metadata
                full_metadata = {
                    "key": key,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "content_type": "application/json",
                    **(metadata or {}),
                }

                # Write data
                with open(data_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)

                # Write metadata
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(full_metadata, f, indent=2, ensure_ascii=False, default=str)

                # Update cache
                if self._cache:
                    self._cache.put(key, data, full_metadata)

                location = DataLocation(
                    storage_type=StorageType.FILE,
                    key=key,
                    path=str(data_path),
                    metadata=full_metadata,
                )

                return StorageResult(
                    success=True,
                    location=location,
                    metadata=full_metadata,
                )

            finally:
                if self._lock_manager:
                    self._lock_manager.release(key)

        except DataExistsError as e:
            return StorageResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error storing data for key {key}: {e}")
            return StorageResult(success=False, error=str(e))

    async def retrieve(self, key: str) -> StorageResult:
        """Retrieve data from file."""
        try:
            # Check cache first
            if self._cache:
                cached = self._cache.get(key)
                if cached and self._is_cache_valid(cached):
                    location = DataLocation(
                        storage_type=StorageType.FILE,
                        key=key,
                        path=str(self._get_data_path(key)),
                        metadata=cached.metadata,
                    )
                    return StorageResult(
                        success=True,
                        data=cached.data,
                        location=location,
                        metadata={"cache_hit": True, **cached.metadata},
                    )

            data_path = self._get_data_path(key)
            meta_path = self._get_metadata_path(key)

            if not data_path.exists():
                raise DataNotFoundError(f"Data not found for key: {key}")

            # Acquire lock if enabled
            if self._lock_manager:
                if not self._lock_manager.acquire(key):
                    return StorageResult(
                        success=False,
                        error=f"Failed to acquire lock for key: {key}",
                    )

            try:
                # Read data
                with open(data_path, encoding="utf-8") as f:
                    data = json.load(f)

                # Read metadata
                metadata = {}
                if meta_path.exists():
                    with open(meta_path, encoding="utf-8") as f:
                        metadata = json.load(f)

                # Update cache
                if self._cache:
                    self._cache.put(key, data, metadata)

                location = DataLocation(
                    storage_type=StorageType.FILE,
                    key=key,
                    path=str(data_path),
                    metadata=metadata,
                )

                return StorageResult(
                    success=True,
                    data=data,
                    location=location,
                    metadata={"cache_hit": False, **metadata},
                )

            finally:
                if self._lock_manager:
                    self._lock_manager.release(key)

        except DataNotFoundError as e:
            return StorageResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error retrieving data for key {key}: {e}")
            return StorageResult(success=False, error=str(e))

    async def delete(self, key: str) -> StorageResult:
        """Delete data file."""
        try:
            data_path = self._get_data_path(key)
            meta_path = self._get_metadata_path(key)

            if not data_path.exists():
                raise DataNotFoundError(f"Data not found for key: {key}")

            # Acquire lock if enabled
            if self._lock_manager:
                if not self._lock_manager.acquire(key):
                    return StorageResult(
                        success=False,
                        error=f"Failed to acquire lock for key: {key}",
                    )

            try:
                # Delete files
                if data_path.exists():
                    data_path.unlink()
                if meta_path.exists():
                    meta_path.unlink()

                # Remove from cache
                if self._cache:
                    self._cache.remove(key)

                return StorageResult(
                    success=True,
                    metadata={"deleted_key": key},
                )

            finally:
                if self._lock_manager:
                    self._lock_manager.release(key)

        except DataNotFoundError as e:
            return StorageResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error deleting data for key {key}: {e}")
            return StorageResult(success=False, error=str(e))

    async def exists(self, key: str) -> bool:
        """Check if data exists."""
        return self._get_data_path(key).exists()

    async def list_keys(
        self,
        prefix: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[str]:
        """List all keys."""
        data_dir = self.base_path / "data"
        keys = []

        for path in data_dir.glob("*.json"):
            # Reverse sanitize to get original key (approximate)
            key = path.stem
            if prefix is None or key.startswith(prefix):
                keys.append(key)

        # Sort and paginate
        keys.sort()
        return keys[offset:offset + limit]

    async def get_metadata(self, key: str) -> dict[str, Any] | None:
        """Get metadata without retrieving data."""
        meta_path = self._get_metadata_path(key)

        if not meta_path.exists():
            return None

        try:
            with open(meta_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading metadata for key {key}: {e}")
            return None

    async def update_metadata(
        self,
        key: str,
        metadata: dict[str, Any],
        merge: bool = True,
    ) -> StorageResult:
        """Update metadata for a key."""
        try:
            meta_path = self._get_metadata_path(key)

            if not meta_path.exists():
                raise DataNotFoundError(f"Metadata not found for key: {key}")

            # Acquire lock if enabled
            if self._lock_manager:
                if not self._lock_manager.acquire(key):
                    return StorageResult(
                        success=False,
                        error=f"Failed to acquire lock for key: {key}",
                    )

            try:
                # Read existing metadata
                with open(meta_path, encoding="utf-8") as f:
                    existing = json.load(f)

                # Merge or replace
                if merge:
                    existing.update(metadata)
                    existing["updated_at"] = datetime.utcnow().isoformat()
                    final_metadata = existing
                else:
                    final_metadata = {
                        "key": key,
                        "updated_at": datetime.utcnow().isoformat(),
                        **metadata,
                    }

                # Write updated metadata
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(final_metadata, f, indent=2, ensure_ascii=False, default=str)

                return StorageResult(
                    success=True,
                    metadata=final_metadata,
                )

            finally:
                if self._lock_manager:
                    self._lock_manager.release(key)

        except DataNotFoundError as e:
            return StorageResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error updating metadata for key {key}: {e}")
            return StorageResult(success=False, error=str(e))

    async def clear(self) -> StorageResult:
        """Clear all data from storage."""
        try:
            data_dir = self.base_path / "data"
            meta_dir = self.base_path / "metadata"

            # Delete all files
            for path in data_dir.glob("*.json"):
                path.unlink()
            for path in meta_dir.glob("*.json"):
                path.unlink()

            # Clear cache
            if self._cache:
                self._cache.clear()

            return StorageResult(success=True)
        except Exception as e:
            logger.error(f"Error clearing storage: {e}")
            return StorageResult(success=False, error=str(e))

    async def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        data_dir = self.base_path / "data"
        self.base_path / "metadata"

        file_count = len(list(data_dir.glob("*.json")))
        total_size = sum(f.stat().st_size for f in data_dir.glob("*.json"))

        stats = {
            "storage_type": self.storage_type.value,
            "connected": self.is_connected,
            "base_path": str(self.base_path),
            "file_count": file_count,
            "total_size_bytes": total_size,
            "cache_enabled": self.cache_enabled,
        }

        if self._cache:
            stats["cache_stats"] = self._cache.get_stats()

        return stats
