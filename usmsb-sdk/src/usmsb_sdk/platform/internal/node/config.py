"""
Node Configuration Module

This module defines configuration classes for node management, including:
- Node identity and network configuration
- Synchronization settings
- Security parameters
- Node capabilities and resources
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib
import socket
import time
import uuid


class NodeRole(str, Enum):
    """Roles a node can assume in the network."""
    FULL_NODE = "full_node"           # Full participating node
    LIGHT_NODE = "light_node"         # Light client node
    BOOTSTRAP = "bootstrap"           # Bootstrap/seed node
    RELAY = "relay"                   # Relay node for message routing
    COORDINATOR = "coordinator"       # Coordination node
    OBSERVER = "observer"             # Observer-only node


class TransportProtocol(str, Enum):
    """Supported transport protocols."""
    WEBSOCKET = "websocket"
    GRPC = "grpc"
    HTTP = "http"
    TCP = "tcp"
    UDP = "udp"


@dataclass
class NetworkConfig:
    """Network configuration for a node."""
    address: str = "0.0.0.0"
    port: int = 8080
    external_address: Optional[str] = None
    external_port: Optional[int] = None
    bind_address: str = "0.0.0.0"
    max_connections: int = 100
    connection_timeout: float = 30.0
    idle_timeout: float = 300.0
    enable_upnp: bool = False
    enable_nat_traversal: bool = True
    protocols: List[TransportProtocol] = field(
        default_factory=lambda: [TransportProtocol.WEBSOCKET, TransportProtocol.TCP]
    )
    tls_enabled: bool = False
    tls_cert_path: Optional[str] = None
    tls_key_path: Optional[str] = None

    def get_external_address(self) -> str:
        """Get the external address for this node."""
        if self.external_address:
            return self.external_address
        return self._detect_external_ip()

    def get_external_port(self) -> int:
        """Get the external port for this node."""
        return self.external_port or self.port

    def get_connection_string(self, protocol: TransportProtocol = TransportProtocol.WEBSOCKET) -> str:
        """Get connection string for the specified protocol."""
        addr = self.get_external_address()
        port = self.get_external_port()

        if protocol == TransportProtocol.WEBSOCKET:
            scheme = "wss" if self.tls_enabled else "ws"
            return f"{scheme}://{addr}:{port}"
        elif protocol == TransportProtocol.GRPC:
            return f"{addr}:{port}"
        elif protocol == TransportProtocol.HTTP:
            scheme = "https" if self.tls_enabled else "http"
            return f"{scheme}://{addr}:{port}"
        else:
            return f"{addr}:{port}"

    def _detect_external_ip(self) -> str:
        """Detect external IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "address": self.address,
            "port": self.port,
            "external_address": self.external_address,
            "external_port": self.external_port,
            "bind_address": self.bind_address,
            "max_connections": self.max_connections,
            "connection_timeout": self.connection_timeout,
            "idle_timeout": self.idle_timeout,
            "enable_upnp": self.enable_upnp,
            "enable_nat_traversal": self.enable_nat_traversal,
            "protocols": [p.value for p in self.protocols],
            "tls_enabled": self.tls_enabled,
        }


@dataclass
class SyncConfig:
    """Synchronization configuration."""
    sync_interval: float = 30.0              # Interval for periodic sync (seconds)
    full_sync_interval: float = 3600.0       # Interval for full sync (seconds)
    incremental_sync_interval: float = 10.0  # Interval for incremental sync
    batch_size: int = 100                     # Number of items per batch
    max_retries: int = 3                      # Max retry attempts
    retry_delay: float = 1.0                  # Delay between retries
    enable_compression: bool = True           # Enable data compression
    compression_threshold: int = 1024         # Bytes threshold for compression
    checkpoint_interval: int = 1000           # Create checkpoint every N items
    enable_incremental: bool = True           # Enable incremental sync
    enable_grpc_batch: bool = True            # Enable gRPC for batch sync
    enable_ipfs_data: bool = False            # Enable IPFS for large data
    ipfs_gateway: Optional[str] = None        # IPFS gateway URL
    conflict_resolution: str = "last_write_wins"  # Conflict resolution strategy

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sync_interval": self.sync_interval,
            "full_sync_interval": self.full_sync_interval,
            "incremental_sync_interval": self.incremental_sync_interval,
            "batch_size": self.batch_size,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "enable_compression": self.enable_compression,
            "compression_threshold": self.compression_threshold,
            "checkpoint_interval": self.checkpoint_interval,
            "enable_incremental": self.enable_incremental,
            "enable_grpc_batch": self.enable_grpc_batch,
            "enable_ipfs_data": self.enable_ipfs_data,
            "ipfs_gateway": self.ipfs_gateway,
            "conflict_resolution": self.conflict_resolution,
        }


@dataclass
class SecurityConfig:
    """Security configuration for a node."""
    private_key: Optional[str] = None
    public_key: Optional[str] = None
    enable_encryption: bool = True
    enable_authentication: bool = True
    auth_token_expiry: float = 3600.0       # Token expiry in seconds
    max_auth_attempts: int = 5               # Max failed auth attempts
    auth_lockout_duration: float = 300.0    # Lockout duration in seconds
    trusted_peers: List[str] = field(default_factory=list)
    banned_peers: List[str] = field(default_factory=list)
    rate_limit_requests: int = 100           # Max requests per minute
    rate_limit_window: float = 60.0          # Rate limit window in seconds
    enable_whitelist: bool = False
    whitelist: List[str] = field(default_factory=list)

    def generate_keys(self) -> None:
        """Generate cryptographic keys for the node."""
        seed = f"{time.time()}{uuid.uuid4()}"
        self.private_key = hashlib.sha256(f"{seed}_private".encode()).hexdigest()
        self.public_key = hashlib.sha256(f"{seed}_public".encode()).hexdigest()

    def is_peer_trusted(self, peer_id: str) -> bool:
        """Check if a peer is trusted."""
        if peer_id in self.banned_peers:
            return False
        if self.enable_whitelist:
            return peer_id in self.whitelist
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without sensitive data)."""
        return {
            "enable_encryption": self.enable_encryption,
            "enable_authentication": self.enable_authentication,
            "auth_token_expiry": self.auth_token_expiry,
            "max_auth_attempts": self.max_auth_attempts,
            "auth_lockout_duration": self.auth_lockout_duration,
            "trusted_peers": self.trusted_peers,
            "banned_peers_count": len(self.banned_peers),
            "rate_limit_requests": self.rate_limit_requests,
            "rate_limit_window": self.rate_limit_window,
            "enable_whitelist": self.enable_whitelist,
        }


@dataclass
class NodeCapabilities:
    """Capabilities and resources of a node."""
    cpu_cores: int = 4
    memory_gb: float = 8.0
    storage_gb: float = 100.0
    bandwidth_mbps: float = 100.0
    gpu_available: bool = False
    gpu_memory_gb: float = 0.0
    services: List[str] = field(default_factory=list)
    supported_protocols: List[str] = field(
        default_factory=lambda: ["websocket", "grpc", "http"]
    )
    max_concurrent_tasks: int = 10
    max_storage_objects: int = 10000
    features: Dict[str, bool] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize default features."""
        if not self.features:
            self.features = {
                "llm_inference": False,
                "agent_hosting": False,
                "compute": True,
                "storage": True,
                "blockchain": False,
                "oracle": False,
                "coordination": True,
            }

    def has_feature(self, feature: str) -> bool:
        """Check if a feature is available."""
        return self.features.get(feature, False)

    def get_load_factor(self) -> float:
        """Calculate current load factor (placeholder)."""
        # In a real implementation, this would calculate actual load
        return 0.0

    def can_accept_task(self) -> bool:
        """Check if node can accept new tasks."""
        return self.get_load_factor() < 0.9

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cpu_cores": self.cpu_cores,
            "memory_gb": self.memory_gb,
            "storage_gb": self.storage_gb,
            "bandwidth_mbps": self.bandwidth_mbps,
            "gpu_available": self.gpu_available,
            "gpu_memory_gb": self.gpu_memory_gb,
            "services": self.services,
            "supported_protocols": self.supported_protocols,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "max_storage_objects": self.max_storage_objects,
            "features": self.features,
        }


@dataclass
class NodeConfig:
    """
    Complete configuration for a node.

    This class aggregates all configuration aspects for node management,
    including identity, network, sync, security, and capabilities.
    """
    # Node identity
    node_id: str = ""
    node_name: str = ""
    role: NodeRole = NodeRole.FULL_NODE
    version: str = "1.0.0"

    # Configuration sections
    network: NetworkConfig = field(default_factory=NetworkConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    capabilities: NodeCapabilities = field(default_factory=NodeCapabilities)

    # Seed nodes for discovery
    seed_nodes: List[str] = field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)

    # Feature flags
    enable_discovery: bool = True
    enable_broadcast: bool = True
    enable_sync: bool = True
    enable_metrics: bool = True
    debug_mode: bool = False

    def __post_init__(self):
        """Generate node ID and keys if not provided."""
        if not self.node_id:
            self.node_id = self._generate_node_id()
        if not self.node_name:
            self.node_name = f"node-{self.node_id[:8]}"
        if not self.security.private_key:
            self.security.generate_keys()

    def _generate_node_id(self) -> str:
        """Generate a unique node ID."""
        seed = f"{time.time()}{uuid.uuid4()}{self.network.address}{self.network.port}"
        return "node_" + hashlib.sha256(seed.encode()).hexdigest()[:16]

    def get_identity_dict(self) -> Dict[str, Any]:
        """Get identity information."""
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "role": self.role.value,
            "version": self.version,
            "public_key": self.security.public_key,
            "address": self.network.get_external_address(),
            "port": self.network.get_external_port(),
        }

    def add_seed_node(self, address: str, port: Optional[int] = None) -> None:
        """Add a seed node."""
        if port:
            seed = f"{address}:{port}"
        else:
            seed = address
        if seed not in self.seed_nodes:
            self.seed_nodes.append(seed)
            self.last_updated = time.time()

    def remove_seed_node(self, address: str) -> None:
        """Remove a seed node."""
        self.seed_nodes = [
            s for s in self.seed_nodes
            if not s.startswith(address)
        ]
        self.last_updated = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "role": self.role.value,
            "version": self.version,
            "network": self.network.to_dict(),
            "sync": self.sync.to_dict(),
            "security": self.security.to_dict(),
            "capabilities": self.capabilities.to_dict(),
            "seed_nodes": self.seed_nodes,
            "metadata": self.metadata,
            "tags": self.tags,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "enable_discovery": self.enable_discovery,
            "enable_broadcast": self.enable_broadcast,
            "enable_sync": self.enable_sync,
            "enable_metrics": self.enable_metrics,
            "debug_mode": self.debug_mode,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NodeConfig":
        """Create config from dictionary."""
        network_data = data.get("network", {})
        sync_data = data.get("sync", {})
        security_data = data.get("security", {})
        capabilities_data = data.get("capabilities", {})

        config = cls(
            node_id=data.get("node_id", ""),
            node_name=data.get("node_name", ""),
            role=NodeRole(data.get("role", "full_node")),
            version=data.get("version", "1.0.0"),
            network=NetworkConfig(
                address=network_data.get("address", "0.0.0.0"),
                port=network_data.get("port", 8080),
                external_address=network_data.get("external_address"),
                external_port=network_data.get("external_port"),
                max_connections=network_data.get("max_connections", 100),
                connection_timeout=network_data.get("connection_timeout", 30.0),
            ),
            sync=SyncConfig(
                sync_interval=sync_data.get("sync_interval", 30.0),
                batch_size=sync_data.get("batch_size", 100),
            ),
            security=SecurityConfig(
                enable_encryption=security_data.get("enable_encryption", True),
                enable_authentication=security_data.get("enable_authentication", True),
            ),
            capabilities=NodeCapabilities(
                cpu_cores=capabilities_data.get("cpu_cores", 4),
                memory_gb=capabilities_data.get("memory_gb", 8.0),
            ),
            seed_nodes=data.get("seed_nodes", []),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            enable_discovery=data.get("enable_discovery", True),
            enable_broadcast=data.get("enable_broadcast", True),
            enable_sync=data.get("enable_sync", True),
        )
        return config

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "NodeConfig":
        """Create config from JSON string."""
        import json
        return cls.from_dict(json.loads(json_str))
