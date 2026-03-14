"""
External Platform Module.

Provides external adapters for agent communication, authentication, protocol handling,
node management, storage services, and platform launcher.

Note: The node management module has been moved to `usmsb_sdk.platform.internal.node`.
Imports from `usmsb_sdk.platform.external.node` will continue to work but will emit
a deprecation warning.
"""

# Protocol handlers
# Auth module
from usmsb_sdk.platform.external.auth import (
    MAX_SESSION_DURATION_HOURS,
    MINIMUM_STAKE_FOR_REGISTRATION,
    SESSION_DURATION_HOURS,
    STAKE_LOCK_PERIOD_DAYS,
    AgentRegistration,
    # Base types
    AuthContext,
    AuthCoordinator,
    BaseAuthResult,
    FullAuthResult,
    IAuthProvider,
    IStakeVerifier,
    IWalletAuthenticator,
    MockStakeVerifier,
    MockWalletAuthenticator,
    # Enums
    Permission,
    # Coordinator
    SessionInfo,
    # Stake verification
    StakeInfo,
    StakeTier,
    StakeVerificationResult,
    VerificationContext,
    WalletAuthResult,
    # Wallet authentication
    WalletBinding,
)
from usmsb_sdk.platform.external.external_agent_adapter import (
    A2AProtocolHandler as LegacyA2AProtocolHandler,
)

# External Agent Adapter (with legacy compatibility)
from usmsb_sdk.platform.external.external_agent_adapter import (
    ExternalAgentAdapter,
    ExternalAgentCall,
    ExternalAgentProfile,
    ExternalAgentProtocol,
    ExternalAgentResponse,
    ExternalAgentStatus,
    ProtocolHandler,
    SkillMatchLevel,
    create_agent_from_skill_md,
    create_skill_from_dict,
)
from usmsb_sdk.platform.external.external_agent_adapter import (
    HTTPProtocolHandler as LegacyHTTPProtocolHandler,
)
from usmsb_sdk.platform.external.external_agent_adapter import (
    SkillDefinition as AdapterSkillDefinition,
)

# Launcher module
from usmsb_sdk.platform.external.launcher import (
    ConfigWizard,
    HealthChecker,
    HealthReport,
    NodeInfo,
    PlatformLauncher,
    PlatformStatus,
    StatusMonitor,
    cli_main,
)

# Node management - imports from new location (will emit deprecation warning)
from usmsb_sdk.platform.external.node import (
    BroadcastMessage,
    BroadcastMessageType,
    ConnectionStatus,
    DataChunk,
    DiscoveredNode,
    HealthCheckResult,
    MessageAck,
    NetworkConfig,
    # Broadcast
    NodeBroadcastService,
    NodeCapabilities,
    # Config
    NodeConfig,
    NodeConnection,
    # Discovery
    NodeDiscoveryService,
    NodeHealthStatus,
    # Node Manager
    NodeManager,
    NodeState,
    SecurityConfig,
    SyncConfig,
    SyncMode,
    SyncResult,
    # Sync
    SyncService,
    SyncStatus,
)
from usmsb_sdk.platform.external.protocol import (
    GRPC_AVAILABLE,
    SUPPORTED_PROTOCOLS,
    A2AAgentInfo,
    A2AEnvelope,
    # A2A
    A2AProtocolHandler,
    A2ASkillRequest,
    A2ASkillResponse,
    # Base
    BaseProtocolHandler,
    ConnectionEndpoint,
    ConnectionInfo,
    ConnectionPool,
    HTTPAuthConfig,
    HTTPEndpointConfig,
    # HTTP
    HTTPProtocolHandler,
    HTTPRequest,
    HTTPResponse,
    HTTPSkillEndpoint,
    LoadBalancingStrategy,
    MCPMessage,
    MCPPrompt,
    # MCP
    MCPProtocolHandler,
    MCPResource,
    MCPServerInfo,
    MCPTool,
    MCPToolCall,
    MCPToolResult,
    P2PDHTEntry,
    P2PMessage,
    P2PNodeInfo,
    # P2P
    P2PProtocolHandler,
    P2PSkillRequest,
    P2PSkillResponse,
    ProtocolConfig,
    ProtocolMessage,
    ProtocolResponse,
    ProtoMessageBuilder,
    WebSocketConfig,
    WebSocketEvent,
    WebSocketMessage,
    # WebSocket
    WebSocketProtocolHandler,
    WebSocketSubscription,
    call_grpc_method,
    create_grpc_handler,
    # Factory
    create_protocol_handler,
    get_handler_class,
    gRPCConfig,
    gRPCError,
    gRPCErrorCode,
    gRPCMethod,
    # gRPC
    gRPCProtocolHandler,
    gRPCRequest,
    gRPCResponse,
    gRPCServiceDefinition,
)

# Storage module
from usmsb_sdk.platform.external.storage import (
    AgentRegistryManager,
    CacheStrategy,
    ConsistencyLevel,
    DataLocation,
    DataShardingManager,
    FileLockManager,
    # File Storage
    FileStorage,
    IPFSConnectionConfig,
    # IPFS Storage
    IPFSStorage,
    SessionStateManager,
    # SQLite Storage
    SQLiteStorage,
    StorageError,
    # Base
    StorageInterface,
    # Storage Manager
    StorageManager,
    StorageResult,
    StorageType,
    SyncStrategy,
    TransactionRecordManager,
    create_storage_manager,
)

__all__ = [
    # Protocol - Base
    "BaseProtocolHandler",
    "ProtocolConfig",
    "ProtocolMessage",
    "ProtocolResponse",
    "ConnectionInfo",
    # Protocol - A2A
    "A2AProtocolHandler",
    "A2AEnvelope",
    "A2ASkillRequest",
    "A2ASkillResponse",
    "A2AAgentInfo",
    # Protocol - HTTP
    "HTTPProtocolHandler",
    "HTTPEndpointConfig",
    "HTTPAuthConfig",
    "HTTPRequest",
    "HTTPResponse",
    "HTTPSkillEndpoint",
    # Protocol - MCP
    "MCPProtocolHandler",
    "MCPServerInfo",
    "MCPTool",
    "MCPResource",
    "MCPPrompt",
    "MCPToolCall",
    "MCPToolResult",
    "MCPMessage",
    # Protocol - P2P
    "P2PProtocolHandler",
    "P2PNodeInfo",
    "P2PMessage",
    "P2PSkillRequest",
    "P2PSkillResponse",
    "P2PDHTEntry",
    # Protocol - WebSocket
    "WebSocketProtocolHandler",
    "WebSocketConfig",
    "WebSocketMessage",
    "WebSocketEvent",
    "WebSocketSubscription",
    # Protocol - gRPC
    "gRPCProtocolHandler",
    "gRPCConfig",
    "gRPCMethod",
    "gRPCRequest",
    "gRPCResponse",
    "gRPCServiceDefinition",
    "gRPCError",
    "gRPCErrorCode",
    "LoadBalancingStrategy",
    "ConnectionPool",
    "ConnectionEndpoint",
    "ProtoMessageBuilder",
    "create_grpc_handler",
    "call_grpc_method",
    "GRPC_AVAILABLE",
    # Protocol - Factory
    "create_protocol_handler",
    "get_handler_class",
    "SUPPORTED_PROTOCOLS",
    # Node - Config
    "NodeConfig",
    "NetworkConfig",
    "SyncConfig",
    "SecurityConfig",
    "NodeCapabilities",
    # Node - Manager
    "NodeManager",
    "NodeState",
    "NodeConnection",
    "ConnectionStatus",
    # Node - Discovery
    "NodeDiscoveryService",
    "DiscoveredNode",
    "NodeHealthStatus",
    "HealthCheckResult",
    # Node - Broadcast
    "NodeBroadcastService",
    "BroadcastMessage",
    "BroadcastMessageType",
    "MessageAck",
    # Node - Sync
    "SyncService",
    "SyncMode",
    "SyncStatus",
    "SyncResult",
    "DataChunk",
    # Storage - Base
    "StorageInterface",
    "StorageType",
    "StorageResult",
    "StorageError",
    "DataLocation",
    # Storage - File
    "FileStorage",
    "FileLockManager",
    # Storage - SQLite
    "SQLiteStorage",
    "SessionStateManager",
    "TransactionRecordManager",
    "AgentRegistryManager",
    # Storage - IPFS
    "IPFSStorage",
    "DataShardingManager",
    "IPFSConnectionConfig",
    # Storage - Manager
    "StorageManager",
    "CacheStrategy",
    "SyncStrategy",
    "ConsistencyLevel",
    "create_storage_manager",
    # Auth - Enums
    "Permission",
    "StakeTier",
    # Auth - Base types
    "AuthContext",
    "BaseAuthResult",
    "WalletAuthResult",
    "StakeVerificationResult",
    "FullAuthResult",
    "IAuthProvider",
    # Auth - Wallet authentication
    "WalletBinding",
    "IWalletAuthenticator",
    "MockWalletAuthenticator",
    # Auth - Stake verification
    "StakeInfo",
    "AgentRegistration",
    "IStakeVerifier",
    "MockStakeVerifier",
    "MINIMUM_STAKE_FOR_REGISTRATION",
    "STAKE_LOCK_PERIOD_DAYS",
    # Auth - Coordinator
    "SessionInfo",
    "VerificationContext",
    "AuthCoordinator",
    "SESSION_DURATION_HOURS",
    "MAX_SESSION_DURATION_HOURS",
    # Launcher
    "PlatformLauncher",
    "PlatformStatus",
    "NodeInfo",
    "ConfigWizard",
    "HealthChecker",
    "HealthReport",
    "StatusMonitor",
    "cli_main",
    # External Agent Adapter
    "ExternalAgentAdapter",
    "ExternalAgentProfile",
    "ExternalAgentProtocol",
    "ExternalAgentStatus",
    "ExternalAgentCall",
    "ExternalAgentResponse",
    "AdapterSkillDefinition",
    "SkillMatchLevel",
    "ProtocolHandler",
    "LegacyA2AProtocolHandler",
    "LegacyHTTPProtocolHandler",
    "create_skill_from_dict",
    "create_agent_from_skill_md",
]
