"""
Sync Service Module

This module implements data synchronization services:
- WebSocket-based incremental sync
- gRPC-based batch sync (framework)
- IPFS-based data sync (framework)
- Conflict resolution
- Checkpointing and recovery
"""

import asyncio
import gzip
import hashlib
import json
import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class SyncMode(StrEnum):
    """Synchronization modes."""
    INCREMENTAL = "incremental"  # WebSocket-based incremental sync
    BATCH = "batch"              # gRPC-based batch sync
    FULL = "full"                # Full state sync
    SNAPSHOT = "snapshot"        # Snapshot-based sync
    IPFS = "ipfs"                # IPFS-based data sync


class SyncStatus(StrEnum):
    """Status of a sync operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class SyncDirection(StrEnum):
    """Direction of sync."""
    PUSH = "push"       # Push local changes to remote
    PULL = "pull"       # Pull remote changes to local
    BIDIRECTIONAL = "bidirectional"  # Both directions


class ConflictResolution(StrEnum):
    """Conflict resolution strategies."""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    SOURCE_PRIORITY = "source_priority"
    MERGE = "merge"
    CUSTOM = "custom"


@dataclass
class DataChunk:
    """A chunk of data for synchronization."""
    chunk_id: str
    sequence_num: int
    data: bytes
    checksum: str
    is_compressed: bool = False
    is_last: bool = False
    total_chunks: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "sequence_num": self.sequence_num,
            "data": self.data.decode('base64') if isinstance(self.data, bytes) else self.data,
            "checksum": self.checksum,
            "is_compressed": self.is_compressed,
            "is_last": self.is_last,
            "total_chunks": self.total_chunks,
            "metadata": self.metadata,
        }

    def compute_checksum(self) -> str:
        """Compute checksum of data."""
        return hashlib.sha256(self.data).hexdigest()[:16]

    def verify(self) -> bool:
        """Verify chunk integrity."""
        return self.compute_checksum() == self.checksum

    @classmethod
    def create(
        cls,
        data: bytes,
        sequence_num: int,
        chunk_size: int = 65536,
        compress: bool = True,
    ) -> Iterator["DataChunk"]:
        """Create chunks from data."""
        chunk_id = str(uuid.uuid4())

        if compress:
            data = gzip.compress(data)

        total_chunks = (len(data) + chunk_size - 1) // chunk_size

        for i in range(total_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, len(data))
            chunk_data = data[start:end]

            yield cls(
                chunk_id=chunk_id,
                sequence_num=sequence_num + i,
                data=chunk_data,
                checksum=hashlib.sha256(chunk_data).hexdigest()[:16],
                is_compressed=compress,
                is_last=(i == total_chunks - 1),
                total_chunks=total_chunks,
            )


@dataclass
class SyncOperation:
    """Represents a sync operation."""
    operation_id: str
    mode: SyncMode
    direction: SyncDirection
    source_node: str
    target_node: str
    data_type: str
    status: SyncStatus = SyncStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    total_items: int = 0
    synced_items: int = 0
    failed_items: int = 0
    bytes_transferred: int = 0
    error_message: str | None = None
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def start(self) -> None:
        """Mark operation as started."""
        self.status = SyncStatus.IN_PROGRESS
        self.started_at = time.time()

    def complete(self, success: bool = True) -> None:
        """Mark operation as completed."""
        self.status = SyncStatus.COMPLETED if success else SyncStatus.FAILED
        self.completed_at = time.time()

    def get_progress(self) -> float:
        """Get progress percentage."""
        if self.total_items == 0:
            return 0.0
        return (self.synced_items / self.total_items) * 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "mode": self.mode.value,
            "direction": self.direction.value,
            "source_node": self.source_node,
            "target_node": self.target_node,
            "data_type": self.data_type,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_items": self.total_items,
            "synced_items": self.synced_items,
            "failed_items": self.failed_items,
            "bytes_transferred": self.bytes_transferred,
            "error_message": self.error_message,
            "progress": self.get_progress(),
            "checkpoints": self.checkpoints,
            "metadata": self.metadata,
        }


@dataclass
class SyncResult:
    """Result of a sync operation."""
    operation_id: str
    success: bool
    synced_count: int
    failed_count: int
    conflicts_count: int
    bytes_transferred: int
    duration_seconds: float
    errors: list[str] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "success": self.success,
            "synced_count": self.synced_count,
            "failed_count": self.failed_count,
            "conflicts_count": self.conflicts_count,
            "bytes_transferred": self.bytes_transferred,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
            "conflicts": self.conflicts,
            "metadata": self.metadata,
        }


@dataclass
class ConflictInfo:
    """Information about a sync conflict."""
    key: str
    local_value: Any
    remote_value: Any
    local_timestamp: float
    remote_timestamp: float
    local_node: str
    remote_node: str
    resolution: str | None = None
    resolved_value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "local_value": self.local_value,
            "remote_value": self.remote_value,
            "local_timestamp": self.local_timestamp,
            "remote_timestamp": self.remote_timestamp,
            "local_node": self.local_node,
            "remote_node": self.remote_node,
            "resolution": self.resolution,
            "resolved_value": self.resolved_value,
        }


@dataclass
class Checkpoint:
    """A sync checkpoint for recovery."""
    checkpoint_id: str
    operation_id: str
    sequence_num: int
    timestamp: float = field(default_factory=time.time)
    synced_items: int = 0
    state: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "operation_id": self.operation_id,
            "sequence_num": self.sequence_num,
            "timestamp": self.timestamp,
            "synced_items": self.synced_items,
            "state": self.state,
            "metadata": self.metadata,
        }


@dataclass
class SyncStats:
    """Statistics for the sync service."""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_items_synced: int = 0
    total_bytes_transferred: int = 0
    total_conflicts: int = 0
    resolved_conflicts: int = 0
    avg_sync_time: float = 0.0
    active_operations: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "total_items_synced": self.total_items_synced,
            "total_bytes_transferred": self.total_bytes_transferred,
            "total_conflicts": self.total_conflicts,
            "resolved_conflicts": self.resolved_conflicts,
            "avg_sync_time": self.avg_sync_time,
            "active_operations": self.active_operations,
        }


class SyncService:
    """
    Data Synchronization Service.

    This service provides synchronization capabilities:
    - WebSocket-based incremental sync
    - gRPC-based batch sync (framework)
    - IPFS-based data sync (framework)
    - Conflict detection and resolution
    - Checkpointing for recovery

    Usage:
        sync = SyncService(node_id="node_123")
        await sync.start()

        # Sync with a peer
        result = await sync.sync_with_peer(
            peer_id="node_456",
            data_type="agents",
            mode=SyncMode.INCREMENTAL
        )

        # Register data provider
        sync.register_data_provider("agents", get_agents, apply_changes)

        await sync.stop()
    """

    DEFAULT_SYNC_INTERVAL = 30.0
    DEFAULT_BATCH_SIZE = 100
    DEFAULT_CHUNK_SIZE = 65536
    DEFAULT_TIMEOUT = 300.0
    MAX_RETRIES = 3

    def __init__(
        self,
        node_id: str,
        sync_interval: float = DEFAULT_SYNC_INTERVAL,
        batch_size: int = DEFAULT_BATCH_SIZE,
        conflict_resolution: ConflictResolution = ConflictResolution.LAST_WRITE_WINS,
        enable_compression: bool = True,
        enable_checkpoints: bool = True,
        checkpoint_interval: int = 100,
    ):
        """
        Initialize the Sync Service.

        Args:
            node_id: ID of this node
            sync_interval: Interval for periodic sync
            batch_size: Number of items per batch
            conflict_resolution: Default conflict resolution strategy
            enable_compression: Enable data compression
            enable_checkpoints: Enable checkpointing
            checkpoint_interval: Items between checkpoints
        """
        self.node_id = node_id
        self.sync_interval = sync_interval
        self.batch_size = batch_size
        self.conflict_resolution = conflict_resolution
        self.enable_compression = enable_compression
        self.enable_checkpoints = enable_checkpoints
        self.checkpoint_interval = checkpoint_interval

        # Data providers and appliers
        self._data_providers: dict[str, Callable] = {}
        self._data_appliers: dict[str, Callable] = {}
        self._conflict_resolvers: dict[str, Callable] = {}

        # Sync state
        self._sync_states: dict[str, dict[str, Any]] = defaultdict(dict)
        self._last_sync_times: dict[str, float] = {}

        # Operations
        self._operations: dict[str, SyncOperation] = {}
        self._active_operations: dict[str, asyncio.Task] = {}

        # Checkpoints
        self._checkpoints: dict[str, list[Checkpoint]] = defaultdict(list)

        # Statistics
        self._stats = SyncStats()

        # State
        self._running = False
        self._tasks: set[asyncio.Task] = set()

        # Broadcast service (set externally)
        self._broadcast_service: Any | None = None

        # gRPC client/server (for batch sync)
        self._grpc_server: Any | None = None
        self._grpc_clients: dict[str, Any] = {}

        # IPFS client (for IPFS sync)
        self._ipfs_client: Any | None = None

    # ==================== Lifecycle ====================

    async def start(self) -> bool:
        """Start the sync service."""
        if self._running:
            return True

        self._running = True
        logger.info("Sync service starting")

        # Start periodic sync task
        task = asyncio.create_task(self._periodic_sync_loop())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

        # Start checkpoint cleanup task
        if self.enable_checkpoints:
            task = asyncio.create_task(self._checkpoint_cleanup_loop())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

        # Initialize gRPC if available
        await self._init_grpc()

        # Initialize IPFS if available
        await self._init_ipfs()

        logger.info("Sync service started")
        return True

    async def stop(self) -> None:
        """Stop the sync service."""
        self._running = False

        # Cancel active operations
        for _op_id, task in list(self._active_operations.items()):
            task.cancel()

        # Wait for tasks
        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Shutdown gRPC
        if self._grpc_server:
            await self._shutdown_grpc()

        logger.info("Sync service stopped")

    # ==================== Data Provider Registration ====================

    def register_data_provider(
        self,
        data_type: str,
        provider: Callable[[float | None, int | None], Iterator[dict[str, Any]]],
        applier: Callable[[list[dict[str, Any]]], int],
        conflict_resolver: Callable[[ConflictInfo], Any] | None = None,
    ) -> None:
        """
        Register a data provider for a data type.

        Args:
            data_type: Type of data (e.g., "agents", "transactions")
            provider: Function that yields data items (since_timestamp, limit)
            applier: Function that applies changes (returns count applied)
            conflict_resolver: Optional custom conflict resolver
        """
        self._data_providers[data_type] = provider
        self._data_appliers[data_type] = applier
        if conflict_resolver:
            self._conflict_resolvers[data_type] = conflict_resolver

        logger.debug(f"Registered data provider for: {data_type}")

    def unregister_data_provider(self, data_type: str) -> None:
        """Unregister a data provider."""
        self._data_providers.pop(data_type, None)
        self._data_appliers.pop(data_type, None)
        self._conflict_resolvers.pop(data_type, None)

    # ==================== Synchronization ====================

    async def sync_with_peer(
        self,
        peer_id: str,
        data_type: str,
        mode: SyncMode = SyncMode.INCREMENTAL,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL,
        since: float | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> SyncResult:
        """
        Synchronize data with a peer.

        Args:
            peer_id: ID of peer to sync with
            data_type: Type of data to sync
            mode: Sync mode
            direction: Sync direction
            since: Sync changes since timestamp
            timeout: Operation timeout

        Returns:
            SyncResult with sync details
        """
        if data_type not in self._data_providers:
            raise ValueError(f"No data provider registered for: {data_type}")

        operation = SyncOperation(
            operation_id=str(uuid.uuid4()),
            mode=mode,
            direction=direction,
            source_node=self.node_id,
            target_node=peer_id,
            data_type=data_type,
        )

        self._operations[operation.operation_id] = operation
        self._stats.total_operations += 1
        self._stats.active_operations += 1

        operation.start()
        start_time = time.time()

        try:
            if mode == SyncMode.INCREMENTAL:
                result = await self._incremental_sync(operation, since, timeout)
            elif mode == SyncMode.BATCH:
                result = await self._batch_sync(operation, timeout)
            elif mode == SyncMode.FULL:
                result = await self._full_sync(operation, timeout)
            elif mode == SyncMode.IPFS:
                result = await self._ipfs_sync(operation, timeout)
            else:
                raise ValueError(f"Unsupported sync mode: {mode}")

            operation.complete(success=result.success)
            self._stats.successful_operations += 1
            self._stats.total_items_synced += result.synced_count
            self._stats.total_bytes_transferred += result.bytes_transferred

            # Update last sync time
            self._last_sync_times[f"{peer_id}:{data_type}"] = time.time()

            return result

        except asyncio.CancelledError:
            operation.status = SyncStatus.CANCELLED
            raise
        except Exception as e:
            operation.status = SyncStatus.FAILED
            operation.error_message = str(e)
            self._stats.failed_operations += 1
            logger.error(f"Sync operation failed: {e}")

            return SyncResult(
                operation_id=operation.operation_id,
                success=False,
                synced_count=operation.synced_items,
                failed_count=operation.failed_items,
                conflicts_count=0,
                bytes_transferred=operation.bytes_transferred,
                duration_seconds=time.time() - start_time,
                errors=[str(e)],
            )
        finally:
            self._stats.active_operations -= 1

    async def _incremental_sync(
        self,
        operation: SyncOperation,
        since: float | None,
        timeout: float,
    ) -> SyncResult:
        """Perform incremental sync via WebSocket."""
        start_time = time.time()
        conflicts = []
        errors = []
        bytes_transferred = 0

        # Get local changes since timestamp
        provider = self._data_providers[operation.data_type]
        local_changes = list(provider(since, self.batch_size))
        operation.total_items = len(local_changes)

        # Send changes to peer (if push or bidirectional)
        if operation.direction in [SyncDirection.PUSH, SyncDirection.BIDIRECTIONAL]:
            try:
                sent_bytes = await self._send_changes(
                    operation.target_node,
                    operation.data_type,
                    local_changes,
                )
                bytes_transferred += sent_bytes
                operation.synced_items += len(local_changes)
            except Exception as e:
                errors.append(f"Failed to send changes: {e}")
                operation.failed_items += len(local_changes)

        # Receive changes from peer (if pull or bidirectional)
        if operation.direction in [SyncDirection.PULL, SyncDirection.BIDIRECTIONAL]:
            try:
                remote_changes, received_bytes = await self._receive_changes(
                    operation.target_node,
                    operation.data_type,
                    since,
                )
                bytes_transferred += received_bytes

                # Apply remote changes
                applier = self._data_appliers[operation.data_type]
                for batch in self._batch(remote_changes, self.batch_size):
                    # Check for conflicts
                    batch_conflicts = await self._detect_conflicts(batch, local_changes)

                    for conflict in batch_conflicts:
                        conflicts.append(conflict)
                        resolved = await self._resolve_conflict(conflict, operation.data_type)
                        batch.append({"key": conflict.key, "value": resolved})

                    applied = applier(batch)
                    operation.synced_items += applied

                    # Create checkpoint
                    if self.enable_checkpoints:
                        await self._create_checkpoint(operation, len(batch))

            except Exception as e:
                errors.append(f"Failed to receive changes: {e}")

        return SyncResult(
            operation_id=operation.operation_id,
            success=len(errors) == 0,
            synced_count=operation.synced_items,
            failed_count=operation.failed_items,
            conflicts_count=len(conflicts),
            bytes_transferred=bytes_transferred,
            duration_seconds=time.time() - start_time,
            errors=errors,
            conflicts=[c.to_dict() for c in conflicts],
        )

    async def _batch_sync(
        self,
        operation: SyncOperation,
        timeout: float,
    ) -> SyncResult:
        """Perform batch sync via gRPC (framework)."""
        start_time = time.time()

        # Framework for gRPC batch sync
        if self._grpc_server is None:
            logger.warning("gRPC not initialized, falling back to incremental sync")
            return await self._incremental_sync(operation, None, timeout)

        # gRPC batch sync implementation would go here
        # For now, return a placeholder result
        logger.info(f"gRPC batch sync initiated for {operation.data_type}")

        return SyncResult(
            operation_id=operation.operation_id,
            success=False,
            synced_count=0,
            failed_count=0,
            conflicts_count=0,
            bytes_transferred=0,
            duration_seconds=time.time() - start_time,
            errors=["gRPC batch sync not fully implemented"],
        )

    async def _full_sync(
        self,
        operation: SyncOperation,
        timeout: float,
    ) -> SyncResult:
        """Perform full state sync."""
        time.time()

        # Full sync is essentially incremental sync with since=None
        result = await self._incremental_sync(operation, None, timeout)

        # Update sync state
        self._sync_states[f"{operation.target_node}:{operation.data_type}"] = {
            "last_full_sync": time.time(),
            "items_synced": result.synced_count,
        }

        return result

    async def _ipfs_sync(
        self,
        operation: SyncOperation,
        timeout: float,
    ) -> SyncResult:
        """Perform IPFS-based data sync (framework)."""
        start_time = time.time()

        # Framework for IPFS sync
        if self._ipfs_client is None:
            logger.warning("IPFS not initialized, falling back to incremental sync")
            return await self._incremental_sync(operation, None, timeout)

        # IPFS sync implementation would go here
        # 1. Pin data to IPFS
        # 2. Share CID with peer
        # 3. Peer retrieves data from IPFS
        logger.info(f"IPFS sync initiated for {operation.data_type}")

        return SyncResult(
            operation_id=operation.operation_id,
            success=False,
            synced_count=0,
            failed_count=0,
            conflicts_count=0,
            bytes_transferred=0,
            duration_seconds=time.time() - start_time,
            errors=["IPFS sync not fully implemented"],
        )

    # ==================== Helper Methods ====================

    def _batch(self, items: list[Any], size: int) -> Iterator[list[Any]]:
        """Batch items into chunks."""
        for i in range(0, len(items), size):
            yield items[i:i + size]

    async def _send_changes(
        self,
        peer_id: str,
        data_type: str,
        changes: list[dict[str, Any]],
    ) -> int:
        """Send changes to a peer."""
        if not self._broadcast_service:
            raise RuntimeError("Broadcast service not set")

        # Serialize changes
        data = json.dumps({
            "type": "sync_changes",
            "data_type": data_type,
            "changes": changes,
            "timestamp": time.time(),
        }).encode()

        # Compress if enabled
        if self.enable_compression and len(data) > 1024:
            data = gzip.compress(data)

        # Send via broadcast service
        await self._broadcast_service.send_to_node(
            peer_id,
            self._broadcast_service.BroadcastMessageType.DATA_SYNC if hasattr(
                self._broadcast_service, 'BroadcastMessageType'
            ) else "data_sync",
            {"data_type": data_type, "changes": changes},
        )

        return len(data)

    async def _receive_changes(
        self,
        peer_id: str,
        data_type: str,
        since: float | None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Receive changes from a peer."""
        # This would normally request and wait for changes from the peer
        # For now, return empty list
        # In production, this would use the broadcast service to request
        # and receive changes from the peer

        # Placeholder implementation
        return [], 0

    async def _detect_conflicts(
        self,
        remote_changes: list[dict[str, Any]],
        local_changes: list[dict[str, Any]],
    ) -> list[ConflictInfo]:
        """Detect conflicts between local and remote changes."""
        conflicts = []
        local_by_key = {c.get("key"): c for c in local_changes if "key" in c}

        for remote in remote_changes:
            key = remote.get("key")
            if key and key in local_by_key:
                local = local_by_key[key]

                # Check if values differ
                if local.get("value") != remote.get("value"):
                    conflicts.append(ConflictInfo(
                        key=key,
                        local_value=local.get("value"),
                        remote_value=remote.get("value"),
                        local_timestamp=local.get("timestamp", 0),
                        remote_timestamp=remote.get("timestamp", 0),
                        local_node=local.get("node_id", self.node_id),
                        remote_node=remote.get("node_id", ""),
                    ))

        return conflicts

    async def _resolve_conflict(
        self,
        conflict: ConflictInfo,
        data_type: str,
    ) -> Any:
        """Resolve a sync conflict."""
        # Check for custom resolver
        if data_type in self._conflict_resolvers:
            return self._conflict_resolvers[data_type](conflict)

        # Default resolution strategies
        if self.conflict_resolution == ConflictResolution.LAST_WRITE_WINS:
            if conflict.remote_timestamp > conflict.local_timestamp:
                return conflict.remote_value
            return conflict.local_value

        elif self.conflict_resolution == ConflictResolution.FIRST_WRITE_WINS:
            if conflict.remote_timestamp < conflict.local_timestamp:
                return conflict.remote_value
            return conflict.local_value

        elif self.conflict_resolution == ConflictResolution.SOURCE_PRIORITY:
            # Prefer local changes
            return conflict.local_value

        elif self.conflict_resolution == ConflictResolution.MERGE:
            # Simple merge for dict values
            if isinstance(conflict.local_value, dict) and isinstance(conflict.remote_value, dict):
                return {**conflict.remote_value, **conflict.local_value}
            return conflict.local_value

        # Default: last write wins
        return conflict.remote_value if conflict.remote_timestamp > conflict.local_timestamp else conflict.local_value

    # ==================== Checkpointing ====================

    async def _create_checkpoint(
        self,
        operation: SyncOperation,
        items_synced: int,
    ) -> Checkpoint:
        """Create a sync checkpoint."""
        checkpoint = Checkpoint(
            checkpoint_id=str(uuid.uuid4()),
            operation_id=operation.operation_id,
            sequence_num=len(operation.checkpoints),
            synced_items=items_synced,
        )

        operation.checkpoints.append(checkpoint.to_dict())
        self._checkpoints[operation.operation_id].append(checkpoint)

        return checkpoint

    async def recover_from_checkpoint(
        self,
        operation_id: str,
    ) -> SyncOperation | None:
        """Recover a sync operation from checkpoint."""
        if operation_id not in self._checkpoints:
            return None

        checkpoints = self._checkpoints[operation_id]
        if not checkpoints:
            return None

        last_checkpoint = checkpoints[-1]
        operation = self._operations.get(operation_id)

        if operation:
            operation.synced_items = last_checkpoint.synced_items
            operation.status = SyncStatus.PENDING
            logger.info(f"Recovered operation {operation_id} from checkpoint")

        return operation

    # ==================== Background Tasks ====================

    async def _periodic_sync_loop(self) -> None:
        """Periodically sync with configured peers."""
        while self._running:
            try:
                await asyncio.sleep(self.sync_interval)
                # Periodic sync would happen here
                # This would check for peers and sync based on configuration
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic sync loop: {e}")

    async def _checkpoint_cleanup_loop(self) -> None:
        """Clean up old checkpoints."""
        while self._running:
            try:
                await asyncio.sleep(3600.0)  # Every hour

                # Remove old checkpoints (keep last 10 per operation)
                for op_id in list(self._checkpoints.keys()):
                    if len(self._checkpoints[op_id]) > 10:
                        self._checkpoints[op_id] = self._checkpoints[op_id][-10:]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in checkpoint cleanup: {e}")

    # ==================== gRPC Framework ====================

    async def _init_grpc(self) -> None:
        """Initialize gRPC server/client (framework)."""
        try:
            # Check if grpc is available
            import grpc
            logger.debug("gRPC library available")

            # gRPC server would be started here
            # self._grpc_server = ...

        except ImportError:
            logger.debug("gRPC library not available")

    async def _shutdown_grpc(self) -> None:
        """Shutdown gRPC server."""
        if self._grpc_server:
            # Graceful shutdown would happen here
            pass

    # ==================== IPFS Framework ====================

    async def _init_ipfs(self) -> None:
        """Initialize IPFS client (framework)."""
        try:
            # Check if ipfshttpclient is available
            import ipfshttpclient
            logger.debug("IPFS library available")

            # IPFS client would be initialized here
            # self._ipfs_client = ipfshttpclient.connect()

        except ImportError:
            logger.debug("IPFS library not available")

    # ==================== Integration ====================

    def set_broadcast_service(self, service: Any) -> None:
        """Set the broadcast service for communication."""
        self._broadcast_service = service

    def handle_sync_message(self, message: dict[str, Any]) -> None:
        """Handle incoming sync message."""
        msg_type = message.get("type")

        if msg_type == "sync_changes":
            asyncio.create_task(self._handle_sync_changes(message))
        elif msg_type == "sync_request":
            asyncio.create_task(self._handle_sync_request(message))

    async def _handle_sync_changes(self, message: dict[str, Any]) -> None:
        """Handle incoming sync changes."""
        data_type = message.get("data_type")
        changes = message.get("changes", [])

        if data_type not in self._data_appliers:
            return

        applier = self._data_appliers[data_type]
        try:
            applied = applier(changes)
            logger.debug(f"Applied {applied} {data_type} changes")
        except Exception as e:
            logger.error(f"Failed to apply {data_type} changes: {e}")

    async def _handle_sync_request(self, message: dict[str, Any]) -> None:
        """Handle incoming sync request."""
        data_type = message.get("data_type")
        since = message.get("since")
        requester = message.get("requester")

        if data_type not in self._data_providers:
            return

        provider = self._data_providers[data_type]
        changes = list(provider(since, self.batch_size * 10))

        if self._broadcast_service and requester:
            await self._send_changes(requester, data_type, changes)

    # ==================== Status and Info ====================

    def get_stats(self) -> SyncStats:
        """Get sync statistics."""
        return self._stats

    def get_operation(self, operation_id: str) -> SyncOperation | None:
        """Get an operation by ID."""
        return self._operations.get(operation_id)

    def get_active_operations(self) -> list[SyncOperation]:
        """Get list of active operations."""
        return [
            op for op in self._operations.values()
            if op.status == SyncStatus.IN_PROGRESS
        ]

    def get_sync_state(self, peer_id: str, data_type: str) -> dict[str, Any]:
        """Get sync state for a peer/data type."""
        return self._sync_states.get(f"{peer_id}:{data_type}", {})

    def get_last_sync_time(self, peer_id: str, data_type: str) -> float | None:
        """Get last sync time for a peer/data type."""
        return self._last_sync_times.get(f"{peer_id}:{data_type}")
