"""
Node Management Layer

This module provides comprehensive node management capabilities for the
decentralized network, including:

- Node configuration and identity management
- Node lifecycle management (start, stop, status)
- Peer discovery and health monitoring
- Real-time broadcast communication via WebSocket
- Data synchronization services (WebSocket, gRPC, IPFS)

The layer integrates with the existing P2P node architecture and provides
higher-level abstractions for node operations.
"""

from .broadcast_service import (
    BroadcastMessage,
    BroadcastMessageType,
    MessageAck,
    NodeBroadcastService,
)
from .config import (
    NetworkConfig,
    NodeCapabilities,
    NodeConfig,
    SecurityConfig,
    SyncConfig,
)
from .node_discovery import (
    DiscoveredNode,
    HealthCheckResult,
    NodeDiscoveryService,
    NodeHealthStatus,
)
from .node_manager import (
    ConnectionStatus,
    NodeConnection,
    NodeManager,
    NodeState,
)
from .sync_service import (
    DataChunk,
    SyncMode,
    SyncResult,
    SyncService,
    SyncStatus,
)

__all__ = [
    # Config
    "NodeConfig",
    "NetworkConfig",
    "SyncConfig",
    "SecurityConfig",
    "NodeCapabilities",
    # Node Manager
    "NodeManager",
    "NodeState",
    "NodeConnection",
    "ConnectionStatus",
    # Node Discovery
    "NodeDiscoveryService",
    "DiscoveredNode",
    "NodeHealthStatus",
    "HealthCheckResult",
    # Broadcast Service
    "NodeBroadcastService",
    "BroadcastMessage",
    "BroadcastMessageType",
    "MessageAck",
    # Sync Service
    "SyncService",
    "SyncMode",
    "SyncStatus",
    "SyncResult",
    "DataChunk",
]
