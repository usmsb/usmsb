"""
Node Management Layer

.. deprecated::
    This module has been moved to `usmsb_sdk.platform.internal.node`.
    Please update your imports to use the new location.
    This module will be removed in a future version.

    Old import:
        from usmsb_sdk.platform.external.node import NodeManager

    New import:
        from usmsb_sdk.platform.internal.node import NodeManager

This module provides comprehensive node management capabilities for the
decentralized network, including:

- Node configuration and identity management
- Node lifecycle management (start, stop, status)
- Peer discovery and health monitoring
- Real-time broadcast communication via WebSocket
- Data synchronization services (WebSocket, gRPC, IPFS)
"""

import warnings

# Issue deprecation warning when this module is imported
warnings.warn(
    "usmsb_sdk.platform.external.node has been moved to "
    "usmsb_sdk.platform.internal.node. Please update your imports. "
    "This module will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location for backward compatibility
from usmsb_sdk.platform.internal.node import (
    # Config
    NodeConfig,
    NetworkConfig,
    SyncConfig,
    SecurityConfig,
    NodeCapabilities,
    # Node Manager
    NodeManager,
    NodeState,
    NodeConnection,
    ConnectionStatus,
    # Node Discovery
    NodeDiscoveryService,
    DiscoveredNode,
    NodeHealthStatus,
    HealthCheckResult,
    # Broadcast Service
    NodeBroadcastService,
    BroadcastMessage,
    BroadcastMessageType,
    MessageAck,
    # Sync Service
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
