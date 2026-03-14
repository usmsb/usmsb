"""
Decentralized Node Architecture - Core P2P Layer

This module provides the CORE decentralized P2P node functionality that can
run independently. It implements the fundamental building blocks for a
distributed network.

Key Components:
===============
- P2PNode: A fully decentralized P2P node that can discover peers,
  register services, and participate in the network
- DistributedServiceRegistry: A gossip-based distributed service registry
  for service discovery across the network
- DecentralizedPlatform: The main entry point for the decentralized
  AI Civilization Platform

Architecture Note:
==================
This module provides the CORE P2P networking layer. For higher-level
node management operations (lifecycle, discovery, broadcast, sync),
see `usmsb_sdk.platform.internal.node` which provides additional
abstractions built on top of this core layer.

Module Responsibilities:
- usmsb_sdk.node: Core P2P networking (can run independently)
- usmsb_sdk.platform.internal.node: Platform-level node management
  (lifecycle, discovery, broadcast, sync services)

Usage:
======
    from usmsb_sdk.node import P2PNode, DecentralizedPlatform, DistributedServiceRegistry

    # Create and start a decentralized platform
    platform = DecentralizedPlatform({"port": 8080})
    await platform.start()

    # Or use the lower-level P2PNode directly
    node = P2PNode({"port": 8080})
    await node.start()
    services = await node.discover_services()
"""

from .decentralized_node import (
    DecentralizedPlatform,
    DistributedServiceRegistry,
    NodeIdentity,
    NodeStatus,
    P2PNode,
    ServiceEndpoint,
    ServiceRequest,
    ServiceResponse,
    ServiceType,
)

__all__ = [
    # Enums
    "NodeStatus",
    "ServiceType",
    # Data classes
    "NodeIdentity",
    "ServiceEndpoint",
    "ServiceRequest",
    "ServiceResponse",
    # Core classes
    "DistributedServiceRegistry",
    "P2PNode",
    "DecentralizedPlatform",
]
