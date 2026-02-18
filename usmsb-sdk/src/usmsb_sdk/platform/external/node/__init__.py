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

from .config import (
    NodeConfig,
    NetworkConfig,
    SyncConfig,
    SecurityConfig,
    NodeCapabilities,
)
from .node_manager import (
    NodeManager,
    NodeState,
    NodeConnection,
    ConnectionStatus,
)
from .node_discovery import (
    NodeDiscoveryService,
    DiscoveredNode,
    NodeHealthStatus,
    HealthCheckResult,
)
from .broadcast_service import (
    NodeBroadcastService,
    BroadcastMessage,
    BroadcastMessageType,
    MessageAck,
)
from .sync_service import (
    SyncService,
    SyncMode,
    SyncStatus,
    SyncResult,
    DataChunk,
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
