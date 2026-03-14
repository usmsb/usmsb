"""
Storage Manager

Coordinates the three-layer storage system (File -> SQLite -> IPFS).
Provides unified interface with caching, synchronization, and consistency guarantees.
"""

import asyncio
import hashlib
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from usmsb_sdk.platform.external.storage.base_storage import (
    DataLocation,
    DataNotFoundError,
    StorageInterface,
    StorageResult,
    StorageType,
)
from usmsb_sdk.platform.external.storage.file_storage import FileStorage
from usmsb_sdk.platform.external.storage.ipfs_storage import IPFSConnectionConfig, IPFSStorage
from usmsb_sdk.platform.external.storage.sqlite_storage import SQLiteStorage

logger = logging.getLogger(__name__)


class CacheStrategy(Enum):
    """Cache strategy for data access."""
    NONE = "none"  # No caching
    WRITE_THROUGH = "write_through"  # Write to cache and storage simultaneously
    WRITE_BACK = "write_back"  # Write to cache first, then to storage
    READ_THROUGH = "read_through"  # Read from storage if not in cache
    CACHE_ASIDE = "cache_aside"  # Application manages cache explicitly


class SyncStrategy(Enum):
    """Synchronization strategy for multi-layer storage."""
    IMMEDIATE = "immediate"  # Sync immediately on write
    PERIODIC = "periodic"  # Sync periodically
    ON_DEMAND = "on_demand"  # Sync when requested
    HYBRID = "hybrid"  # Immediate for critical, periodic for others


class ConsistencyLevel(Enum):
    """Consistency level for storage operations."""
    EVENTUAL = "eventual"  # Eventually consistent
    STRONG = "strong"  # Strong consistency
    CAUSAL = "causal"  # Causal consistency
    READ_YOUR_WRITES = "read_your_writes"  # Read-your-writes consistency


@dataclass
class StorageLayer:
    """Represents a storage layer in the hierarchy."""
    storage: StorageInterface
    priority: int  # Lower = faster/closer
    enabled: bool = True
    read_enabled: bool = True
    write_enabled: bool = True


@dataclass
class SyncStatus:
    """Status of synchronization between layers."""
    key: str
    source_type: StorageType
    target_type: StorageType
    synced: bool
    last_sync: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DataIndex:
    """Index entry for tracking data across layers."""
    key: str
    primary_location: StorageType
    locations: dict[StorageType, DataLocation]
    checksum: str
    size: int
    created_at: datetime
    updated_at: datetime
    version: int
    sync_status: dict[tuple[StorageType, StorageType], SyncStatus]
    metadata: dict[str, Any] = field(default_factory=dict)


class StorageManager:
    """
    Manages the three-layer storage system.

    Layer hierarchy (from fastest to slowest):
    1. File Storage - Local JSON files with caching
    2. SQLite Storage - Persistent database
    3. IPFS Storage - Decentralized storage

    Features:
    - Unified storage interface
    - Automatic layer selection based on data requirements
    - Caching strategies
    - Synchronization between layers
    - Consistency guarantees
    """

    def __init__(
        self,
        file_storage: FileStorage | None = None,
        sqlite_storage: SQLiteStorage | None = None,
        ipfs_storage: IPFSStorage | None = None,
        cache_strategy: CacheStrategy = CacheStrategy.WRITE_THROUGH,
        sync_strategy: SyncStrategy = SyncStrategy.HYBRID,
        consistency_level: ConsistencyLevel = ConsistencyLevel.READ_YOUR_WRITES,
        sync_interval_seconds: int = 60,
    ):
        """
        Initialize storage manager.

        Args:
            file_storage: File storage instance.
            sqlite_storage: SQLite storage instance.
            ipfs_storage: IPFS storage instance.
            cache_strategy: Caching strategy to use.
            sync_strategy: Synchronization strategy.
            consistency_level: Consistency level.
            sync_interval_seconds: Interval for periodic sync.
        """
        self.layers: dict[StorageType, StorageLayer] = {}
        self.cache_strategy = cache_strategy
        self.sync_strategy = sync_strategy
        self.consistency_level = consistency_level
        self.sync_interval = timedelta(seconds=sync_interval_seconds)

        # Add layers
        if file_storage:
            self.layers[StorageType.FILE] = StorageLayer(
                storage=file_storage,
                priority=1,
            )
        if sqlite_storage:
            self.layers[StorageType.SQLITE] = StorageLayer(
                storage=sqlite_storage,
                priority=2,
            )
        if ipfs_storage:
            self.layers[StorageType.IPFS] = StorageLayer(
                storage=ipfs_storage,
                priority=3,
            )

        # Data index for tracking
        self._index: dict[str, DataIndex] = {}
        self._write_buffer: dict[str, tuple[Any, dict[str, Any]]] = {}

        # Sync task
        self._sync_task: asyncio.Task | None = None
        self._running = False

        # Event handlers
        self._on_sync_complete: Callable | None = None
        self._on_sync_error: Callable | None = None

    async def initialize(self) -> bool:
        """Initialize all storage layers."""
        results = []

        for storage_type, layer in self.layers.items():
            try:
                result = await layer.storage.initialize()
                results.append(result)
                logger.info(f"Initialized {storage_type.value} storage: {result}")
            except Exception as e:
                logger.error(f"Failed to initialize {storage_type.value} storage: {e}")
                results.append(False)

        # Start sync task if using periodic sync
        if self.sync_strategy == SyncStrategy.PERIODIC:
            self._running = True
            self._sync_task = asyncio.create_task(self._periodic_sync())

        return all(results)

    async def close(self) -> None:
        """Close all storage layers."""
        self._running = False

        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        # Flush write buffer
        await self._flush_write_buffer()

        for layer in self.layers.values():
            await layer.storage.close()

        logger.info("StorageManager closed")

    def _calculate_checksum(self, data: Any) -> str:
        """Calculate checksum for data."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def _get_layer_by_priority(self) -> list[StorageLayer]:
        """Get layers sorted by priority."""
        return sorted(
            [l for l in self.layers.values() if l.enabled],
            key=lambda l: l.priority,
        )

    def _select_write_layers(self, metadata: dict | None = None) -> list[StorageLayer]:
        """Select layers for writing based on data requirements."""
        layers = []

        for layer in self._get_layer_by_priority():
            if not layer.write_enabled:
                continue

            # Check metadata hints
            if metadata:
                # Skip IPFS for small, transient data
                if layer.storage.storage_type == StorageType.IPFS:
                    if metadata.get("transient", False):
                        continue
                    if metadata.get("size", 0) < 100:  # Small data
                        continue

            layers.append(layer)

        return layers

    def _select_read_layers(self, key: str) -> list[StorageLayer]:
        """Select layers for reading."""
        layers = []

        # Check index for known locations
        if key in self._index:
            index_entry = self._index[key]
            # Try primary location first
            if index_entry.primary_location in self.layers:
                layer = self.layers[index_entry.primary_location]
                if layer.read_enabled:
                    layers.append(layer)

        # Add remaining layers by priority
        for layer in self._get_layer_by_priority():
            if layer.read_enabled and layer not in layers:
                layers.append(layer)

        return layers

    async def store(
        self,
        key: str,
        data: Any,
        metadata: dict[str, Any] | None = None,
        overwrite: bool = False,
        target_layers: list[StorageType] | None = None,
    ) -> StorageResult:
        """
        Store data across storage layers.

        Args:
            key: Unique key for the data.
            data: Data to store.
            metadata: Optional metadata.
            overwrite: Whether to overwrite existing data.
            target_layers: Specific layers to store to (default: all).

        Returns:
            StorageResult with operation status.
        """
        try:
            metadata = metadata or {}
            checksum = self._calculate_checksum(data)

            # Select target layers
            if target_layers:
                layers = [
                    self.layers[t] for t in target_layers
                    if t in self.layers and self.layers[t].write_enabled
                ]
            else:
                layers = self._select_write_layers(metadata)

            if not layers:
                return StorageResult(
                    success=False,
                    error="No writable storage layers available",
                )

            # Handle cache strategy
            if self.cache_strategy == CacheStrategy.WRITE_BACK:
                # Buffer the write
                self._write_buffer[key] = (data, metadata)
                # Still write to first layer immediately
                layers = layers[:1]

            # Store to layers
            results = []
            primary_location = None
            locations = {}

            for layer in layers:
                try:
                    result = await layer.storage.store(
                        key,
                        data,
                        metadata,
                        overwrite,
                    )

                    if result.success:
                        results.append(True)
                        locations[layer.storage.storage_type] = result.location

                        if primary_location is None:
                            primary_location = layer.storage.storage_type

                        logger.debug(
                            f"Stored {key} to {layer.storage.storage_type.value}"
                        )
                    else:
                        results.append(False)
                        logger.warning(
                            f"Failed to store {key} to {layer.storage.storage_type.value}: "
                            f"{result.error}"
                        )
                except Exception as e:
                    results.append(False)
                    logger.error(
                        f"Error storing {key} to {layer.storage.storage_type.value}: {e}"
                    )

            if not any(results):
                return StorageResult(
                    success=False,
                    error="Failed to store data to any layer",
                )

            # Update index
            now = datetime.utcnow()
            if key in self._index:
                index_entry = self._index[key]
                index_entry.updated_at = now
                index_entry.version += 1
                index_entry.checksum = checksum
                index_entry.locations.update(locations)
                if primary_location:
                    index_entry.primary_location = primary_location
            else:
                index_entry = DataIndex(
                    key=key,
                    primary_location=primary_location or StorageType.FILE,
                    locations=locations,
                    checksum=checksum,
                    size=len(json.dumps(data, default=str)),
                    created_at=now,
                    updated_at=now,
                    version=1,
                    sync_status={},
                    metadata=metadata,
                )
                self._index[key] = index_entry

            # Handle sync strategy
            if self.sync_strategy == SyncStrategy.IMMEDIATE:
                await self._sync_key(key)

            return StorageResult(
                success=True,
                location=locations.get(primary_location),
                metadata={
                    "layers": [l.storage.storage_type.value for l in layers if results[layers.index(l)]],
                    "checksum": checksum,
                    **metadata,
                },
            )

        except Exception as e:
            logger.error(f"Error storing data for key {key}: {e}")
            return StorageResult(success=False, error=str(e))

    async def retrieve(
        self,
        key: str,
        preferred_layer: StorageType | None = None,
    ) -> StorageResult:
        """
        Retrieve data from storage layers.

        Args:
            key: Key to retrieve.
            preferred_layer: Preferred storage layer to read from.

        Returns:
            StorageResult with the data.
        """
        try:
            # Check write buffer first (for write-back strategy)
            if key in self._write_buffer:
                data, metadata = self._write_buffer[key]
                return StorageResult(
                    success=True,
                    data=data,
                    metadata=metadata,
                )

            # Select layers to try
            if preferred_layer and preferred_layer in self.layers:
                layers = [self.layers[preferred_layer]]
                # Add other layers as fallback
                for layer in self._get_layer_by_priority():
                    if layer not in layers and layer.read_enabled:
                        layers.append(layer)
            else:
                layers = self._select_read_layers(key)

            # Try each layer
            for layer in layers:
                if not layer.read_enabled:
                    continue

                try:
                    result = await layer.storage.retrieve(key)

                    if result.success:
                        # Verify checksum if in index
                        if key in self._index:
                            checksum = self._calculate_checksum(result.data)
                            if checksum != self._index[key].checksum:
                                logger.warning(
                                    f"Checksum mismatch for {key} in {layer.storage.storage_type.value}"
                                )
                                continue

                        # Promote to faster layer if needed
                        if self.cache_strategy in (
                            CacheStrategy.READ_THROUGH,
                            CacheStrategy.CACHE_ASIDE,
                        ):
                            await self._promote_data(key, result.data, layer)

                        return result

                except DataNotFoundError:
                    continue
                except Exception as e:
                    logger.warning(
                        f"Error retrieving {key} from {layer.storage.storage_type.value}: {e}"
                    )
                    continue

            return StorageResult(
                success=False,
                error=f"Data not found in any layer: {key}",
            )

        except Exception as e:
            logger.error(f"Error retrieving data for key {key}: {e}")
            return StorageResult(success=False, error=str(e))

    async def delete(
        self,
        key: str,
        all_layers: bool = True,
    ) -> StorageResult:
        """
        Delete data from storage layers.

        Args:
            key: Key to delete.
            all_layers: Whether to delete from all layers.

        Returns:
            StorageResult with operation status.
        """
        try:
            # Remove from write buffer
            if key in self._write_buffer:
                del self._write_buffer[key]

            # Remove from index
            if key in self._index:
                del self._index[key]

            results = []

            for layer in self.layers.values():
                if not all_layers and layer.priority > 1:
                    continue

                try:
                    result = await layer.storage.delete(key)
                    results.append((layer.storage.storage_type, result.success))
                except Exception as e:
                    logger.warning(
                        f"Error deleting {key} from {layer.storage.storage_type.value}: {e}"
                    )
                    results.append((layer.storage.storage_type, False))

            success_count = sum(1 for _, s in results if s)

            return StorageResult(
                success=success_count > 0,
                metadata={
                    "deleted_from": [t.value for t, s in results if s],
                    "failed_in": [t.value for t, s in results if not s],
                },
            )

        except Exception as e:
            logger.error(f"Error deleting data for key {key}: {e}")
            return StorageResult(success=False, error=str(e))

    async def exists(self, key: str) -> bool:
        """Check if data exists in any layer."""
        # Check write buffer
        if key in self._write_buffer:
            return True

        # Check index
        if key in self._index:
            return True

        # Check layers
        for layer in self.layers.values():
            if layer.read_enabled:
                if await layer.storage.exists(key):
                    return True

        return False

    async def get_metadata(self, key: str) -> dict[str, Any] | None:
        """Get metadata for a key."""
        if key in self._index:
            return self._index[key].metadata

        for layer in self.layers.values():
            if layer.read_enabled:
                metadata = await layer.storage.get_metadata(key)
                if metadata:
                    return metadata

        return None

    async def sync(
        self,
        key: str | None = None,
        source: StorageType | None = None,
        target: StorageType | None = None,
    ) -> dict[str, SyncStatus]:
        """
        Synchronize data between layers.

        Args:
            key: Specific key to sync (None for all).
            source: Source layer (None for auto-detect).
            target: Target layer (None for all deeper layers).

        Returns:
            Dictionary of sync statuses.
        """
        if key:
            keys = [key]
        else:
            keys = list(self._index.keys())

        statuses = {}

        for k in keys:
            status = await self._sync_key(k, source, target)
            statuses[k] = status

        return statuses

    async def _sync_key(
        self,
        key: str,
        source: StorageType | None = None,
        target: StorageType | None = None,
    ) -> SyncStatus:
        """Synchronize a single key between layers."""
        if key not in self._index:
            return SyncStatus(
                key=key,
                source_type=source or StorageType.FILE,
                target_type=target or StorageType.SQLITE,
                synced=False,
                error="Key not found in index",
            )

        index_entry = self._index[key]

        # Determine source layer
        if source:
            source_type = source
        else:
            source_type = index_entry.primary_location

        # Get source data
        if source_type not in self.layers:
            return SyncStatus(
                key=key,
                source_type=source_type,
                target_type=target or StorageType.SQLITE,
                synced=False,
                error="Source layer not available",
            )

        source_layer = self.layers[source_type]
        result = await source_layer.storage.retrieve(key)

        if not result.success:
            return SyncStatus(
                key=key,
                source_type=source_type,
                target_type=target or StorageType.SQLITE,
                synced=False,
                error=f"Failed to retrieve from source: {result.error}",
            )

        # Sync to target layers
        sorted_layers = self._get_layer_by_priority()
        source_priority = source_layer.priority

        for layer in sorted_layers:
            if layer.priority <= source_priority:
                continue  # Skip layers at or above source

            if target and layer.storage.storage_type != target:
                continue  # Skip if specific target specified

            try:
                sync_result = await layer.storage.store(
                    key,
                    result.data,
                    index_entry.metadata,
                    overwrite=True,
                )

                if sync_result.success:
                    index_entry.locations[layer.storage.storage_type] = sync_result.location
                    logger.debug(
                        f"Synced {key} from {source_type.value} to {layer.storage.storage_type.value}"
                    )
            except Exception as e:
                logger.warning(
                    f"Failed to sync {key} to {layer.storage.storage_type.value}: {e}"
                )

        return SyncStatus(
            key=key,
            source_type=source_type,
            target_type=target or StorageType.SQLITE,
            synced=True,
            last_sync=datetime.utcnow(),
        )

    async def _promote_data(
        self,
        key: str,
        data: Any,
        source_layer: StorageLayer,
    ) -> None:
        """Promote data to a faster layer."""
        if key not in self._index:
            return

        index_entry = self._index[key]

        # Find faster layers
        for layer in self._get_layer_by_priority():
            if layer.priority >= source_layer.priority:
                break  # No faster layers available

            if not layer.write_enabled:
                continue

            # Check if already exists
            if layer.storage.storage_type in index_entry.locations:
                continue

            try:
                result = await layer.storage.store(
                    key,
                    data,
                    index_entry.metadata,
                    overwrite=False,
                )

                if result.success:
                    index_entry.locations[layer.storage.storage_type] = result.location
                    logger.debug(
                        f"Promoted {key} to {layer.storage.storage_type.value}"
                    )
                    break
            except Exception as e:
                logger.warning(
                    f"Failed to promote {key} to {layer.storage.storage_type.value}: {e}"
                )

    async def _periodic_sync(self) -> None:
        """Periodic synchronization task."""
        while self._running:
            try:
                await asyncio.sleep(self.sync_interval.total_seconds())
                await self.sync()
                if self._on_sync_complete:
                    await self._on_sync_complete()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic sync error: {e}")
                if self._on_sync_error:
                    await self._on_sync_error(e)

    async def _flush_write_buffer(self) -> None:
        """Flush write buffer to deeper layers."""
        if not self._write_buffer:
            return

        logger.info(f"Flushing {len(self._write_buffer)} buffered writes")

        for key, (data, metadata) in list(self._write_buffer.items()):
            try:
                # Write to all layers
                layers = self._select_write_layers(metadata)

                for layer in layers[1:]:  # Skip first layer (already written)
                    try:
                        await layer.storage.store(key, data, metadata, overwrite=True)
                    except Exception as e:
                        logger.warning(
                            f"Failed to flush {key} to {layer.storage.storage_type.value}: {e}"
                        )

            except Exception as e:
                logger.error(f"Error flushing {key}: {e}")

        self._write_buffer.clear()

    def on_sync_complete(self, callback: Callable) -> None:
        """Set callback for sync completion."""
        self._on_sync_complete = callback

    def on_sync_error(self, callback: Callable) -> None:
        """Set callback for sync errors."""
        self._on_sync_error = callback

    # Convenience methods for layer-specific access

    @property
    def file_storage(self) -> FileStorage | None:
        """Get file storage layer."""
        layer = self.layers.get(StorageType.FILE)
        return layer.storage if layer else None

    @property
    def sqlite_storage(self) -> SQLiteStorage | None:
        """Get SQLite storage layer."""
        layer = self.layers.get(StorageType.SQLITE)
        return layer.storage if layer else None

    @property
    def ipfs_storage(self) -> IPFSStorage | None:
        """Get IPFS storage layer."""
        layer = self.layers.get(StorageType.IPFS)
        return layer.storage if layer else None

    async def store_to_file(
        self,
        key: str,
        data: Any,
        metadata: dict | None = None,
    ) -> StorageResult:
        """Store data only to file storage."""
        return await self.store(key, data, metadata, target_layers=[StorageType.FILE])

    async def store_to_sqlite(
        self,
        key: str,
        data: Any,
        metadata: dict | None = None,
    ) -> StorageResult:
        """Store data only to SQLite storage."""
        return await self.store(key, data, metadata, target_layers=[StorageType.SQLITE])

    async def store_to_ipfs(
        self,
        key: str,
        data: Any,
        metadata: dict | None = None,
    ) -> StorageResult:
        """Store data only to IPFS storage."""
        return await self.store(key, data, metadata, target_layers=[StorageType.IPFS])

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics for all storage layers."""
        stats = {
            "cache_strategy": self.cache_strategy.value,
            "sync_strategy": self.sync_strategy.value,
            "consistency_level": self.consistency_level.value,
            "indexed_keys": len(self._index),
            "buffered_writes": len(self._write_buffer),
            "layers": {},
        }

        for storage_type, layer in self.layers.items():
            try:
                layer_stats = await layer.storage.get_stats()
                stats["layers"][storage_type.value] = layer_stats
            except Exception as e:
                stats["layers"][storage_type.value] = {"error": str(e)}

        return stats

    async def list_keys(
        self,
        prefix: str | None = None,
        limit: int = 100,
    ) -> list[str]:
        """List all keys across layers."""
        keys = set(self._index.keys())

        for layer in self.layers.values():
            try:
                layer_keys = await layer.storage.list_keys(prefix=prefix, limit=limit)
                keys.update(layer_keys)
            except Exception as e:
                logger.warning(
                    f"Error listing keys from {layer.storage.storage_type.value}: {e}"
                )

        result = list(keys)
        if prefix:
            result = [k for k in result if k.startswith(prefix)]

        return result[:limit]

    async def get_data_locations(self, key: str) -> dict[StorageType, DataLocation]:
        """Get all locations where data is stored."""
        if key in self._index:
            return self._index[key].locations.copy()

        locations = {}
        for storage_type, layer in self.layers.items():
            if await layer.storage.exists(key):
                metadata = await layer.storage.get_metadata(key)
                locations[storage_type] = DataLocation(
                    storage_type=storage_type,
                    key=key,
                    metadata=metadata or {},
                )

        return locations

    async def ensure_consistency(
        self,
        key: str,
        level: ConsistencyLevel | None = None,
    ) -> bool:
        """
        Ensure data consistency across layers.

        Args:
            key: Key to check.
            level: Consistency level (default: manager's level).

        Returns:
            True if consistent.
        """
        level = level or self.consistency_level

        if key not in self._index:
            return False

        index_entry = self._index[key]
        primary_checksum = index_entry.checksum

        # Check each layer
        for storage_type, _location in index_entry.locations.items():
            layer = self.layers.get(storage_type)
            if not layer:
                continue

            result = await layer.storage.retrieve(key)
            if result.success:
                checksum = self._calculate_checksum(result.data)
                if checksum != primary_checksum:
                    if level == ConsistencyLevel.STRONG:
                        # Re-sync from primary
                        await self._sync_key(key)
                    return False

        return True

    async def migrate_data(
        self,
        key: str,
        from_layer: StorageType,
        to_layer: StorageType,
        delete_source: bool = False,
    ) -> StorageResult:
        """
        Migrate data between layers.

        Args:
            key: Key to migrate.
            from_layer: Source layer.
            to_layer: Target layer.
            delete_source: Whether to delete from source after migration.

        Returns:
            StorageResult with migration status.
        """
        if from_layer not in self.layers or to_layer not in self.layers:
            return StorageResult(
                success=False,
                error="Invalid layer specified",
            )

        source = self.layers[from_layer]
        target = self.layers[to_layer]

        # Read from source
        result = await source.storage.retrieve(key)
        if not result.success:
            return StorageResult(
                success=False,
                error=f"Failed to read from source: {result.error}",
            )

        # Write to target
        store_result = await target.storage.store(
            key,
            result.data,
            result.metadata,
            overwrite=True,
        )

        if not store_result.success:
            return store_result

        # Update index
        if key in self._index:
            self._index[key].locations[to_layer] = store_result.location
            if delete_source:
                del self._index[key].locations[from_layer]
            elif to_layer in self.layers and self.layers[to_layer].priority < source.priority:
                self._index[key].primary_location = to_layer

        # Delete from source if requested
        if delete_source:
            await source.storage.delete(key)

        return StorageResult(
            success=True,
            location=store_result.location,
            metadata={
                "migrated_from": from_layer.value,
                "migrated_to": to_layer.value,
            },
        )


async def create_storage_manager(
    base_path: str | Path,
    database_name: str = "usmsb_storage.db",
    ipfs_config: IPFSConnectionConfig | None = None,
    cache_strategy: CacheStrategy = CacheStrategy.WRITE_THROUGH,
    sync_strategy: SyncStrategy = SyncStrategy.HYBRID,
) -> StorageManager:
    """
    Factory function to create and initialize a storage manager.

    Args:
        base_path: Base directory for file storage.
        database_name: SQLite database filename.
        ipfs_config: IPFS configuration.
        cache_strategy: Caching strategy.
        sync_strategy: Synchronization strategy.

    Returns:
        Initialized StorageManager instance.
    """
    base_path = Path(base_path)

    # Create storage instances
    file_storage = FileStorage(
        base_path=base_path / "files",
        cache_enabled=True,
    )

    sqlite_storage = SQLiteStorage(
        database_path=base_path / database_name,
    )

    ipfs_storage = IPFSStorage(
        config=ipfs_config or IPFSConnectionConfig.default(),
    )

    # Create manager
    manager = StorageManager(
        file_storage=file_storage,
        sqlite_storage=sqlite_storage,
        ipfs_storage=ipfs_storage,
        cache_strategy=cache_strategy,
        sync_strategy=sync_strategy,
    )

    # Initialize
    await manager.initialize()

    return manager
