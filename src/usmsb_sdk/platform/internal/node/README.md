# Node Directory Architecture

This document describes the node-related directory structure and responsibilities
in the USMSB SDK.

## Directory Structure

```
usmsb_sdk/
├── node/                           # Core P2P networking layer (independent)
│   ├── __init__.py
│   └── decentralized_node.py       # P2PNode, DecentralizedPlatform, DistributedServiceRegistry
│
└── platform/
    ├── internal/                   # NEW: Internal platform components
    │   ├── __init__.py
    │   └── node/                   # Node management layer
    │       ├── __init__.py
    │       ├── config.py           # Node configuration classes
    │       ├── node_manager.py     # Node lifecycle management
    │       ├── node_discovery.py   # Peer discovery service
    │       ├── broadcast_service.py # Real-time broadcast via WebSocket
    │       ├── sync_service.py     # Data synchronization services
    │       └── config.yaml.example # Example configuration
    │
    └── external/
        └── node/                   # DEPRECATED: Use platform.internal.node
            └── __init__.py         # Backward compatibility with deprecation warning
```

## Component Responsibilities

### `usmsb_sdk.node` - Core P2P Layer

This is the **CORE** decentralized P2P networking layer that can run independently.

**Purpose:**
- Provides fundamental P2P networking capabilities
- Can operate as a standalone node without platform dependencies
- Implements the distributed service registry using gossip protocol

**Key Classes:**
- `P2PNode` - A fully decentralized P2P node
- `DecentralizedPlatform` - Main entry point for the AI Civilization Platform
- `DistributedServiceRegistry` - Gossip-based service discovery
- `NodeStatus`, `ServiceType` - Enums for node state
- `NodeIdentity`, `ServiceEndpoint` - Data classes for node info

**When to use:**
- When you need core P2P networking without platform features
- When building lightweight decentralized applications
- When you need the distributed service registry

### `usmsb_sdk.platform.internal.node` - Node Management Layer

This is the **PLATFORM-LEVEL** node management layer that provides higher-level
abstractions on top of the core P2P layer.

**Purpose:**
- Manages node lifecycle (start, stop, restart, status)
- Provides peer discovery with health monitoring
- Implements real-time broadcast communication
- Handles data synchronization across nodes

**Key Classes:**
- `NodeManager` - Node lifecycle and connection management
- `NodeDiscoveryService` - Peer discovery with health checks
- `NodeBroadcastService` - Real-time broadcast via WebSocket
- `SyncService` - Data sync (WebSocket, gRPC, IPFS)
- `NodeConfig`, `NetworkConfig`, `SyncConfig`, `SecurityConfig` - Configuration

**When to use:**
- When you need full platform node management features
- When building production-grade decentralized applications
- When you need health monitoring and automatic recovery
- When you need real-time broadcast or data synchronization

## Migration Guide

### Old Import (Deprecated)
```python
from usmsb_sdk.platform.external.node import NodeManager, NodeConfig
```

### New Import (Recommended)
```python
from usmsb_sdk.platform.internal.node import NodeManager, NodeConfig
```

The old import path will continue to work but will emit a `DeprecationWarning`.
Update your imports to use the new path to avoid future issues.

## Design Rationale

### Why separate `node/` and `platform/internal/node/`?

1. **Separation of Concerns**
   - `node/` contains the core P2P networking logic that is independent
   - `platform/internal/node/` contains platform-specific management features

2. **Reusability**
   - The core P2P layer can be used without the platform
   - The platform management layer can be swapped or extended

3. **Clear Boundaries**
   - `node/` = "What is a P2P node and how does it network?"
   - `platform/internal/node/` = "How do we manage nodes in the platform?"

### Why move from `external` to `internal`?

The `external` directory was originally intended for external-facing adapters.
The node management components are internal platform utilities, not external
adapters. The move clarifies the intended use and improves code organization.

## Summary

| Component | Path | Purpose |
|-----------|------|---------|
| Core P2P | `usmsb_sdk.node` | Independent P2P networking |
| Node Management | `usmsb_sdk.platform.internal.node` | Platform-level node operations |
| Legacy (deprecated) | `usmsb_sdk.platform.external.node` | Backward compatibility |
