"""
External Platform Module.

Provides external adapters for agent communication, authentication, protocol handling,
node management, storage services, and platform launcher.

Note: The node management module has been moved to `usmsb_sdk.platform.internal.node`.
Imports from `usmsb_sdk.platform.external.node` will continue to work but will emit
a deprecation warning.
"""

# Protocol handlers
from usmsb_sdk.platform.external.protocol import (
    # Base
    BaseProtocolHandler,
    ProtocolConfig,
    ProtocolMessage,
    ProtocolResponse,
    ConnectionInfo,
    # A2A
    A2AProtocolHandler,
    A2AEnvelope,
    A2ASkillRequest,
    A2ASkillResponse,
    A2AAgentInfo,
    # HTTP
    HTTPProtocolHandler,
    HTTPEndpointConfig,
    HTTPAuthConfig,
    HTTPRequest,
    HTTPResponse,
    HTTPSkillEndpoint,
    # MCP
    MCPProtocolHandler,
    MCPServerInfo,
    MCPTool,
    MCPResource,
    MCPPrompt,
    MCPToolCall,
    MCPToolResult,
    MCPMessage,
    # P2P
    P2PProtocolHandler,
    P2PNodeInfo,
    P2PMessage,
    P2PSkillRequest,
    P2PSkillResponse,
    P2PDHTEntry,
    # WebSocket
    WebSocketProtocolHandler,
    WebSocketConfig,
    WebSocketMessage,
    WebSocketEvent,
    WebSocketSubscription,
    # gRPC
    gRPCProtocolHandler,
    gRPCConfig,
    gRPCMethod,
    gRPCRequest,
    gRPCResponse,
    gRPCServiceDefinition,
    gRPCError,
    gRPCErrorCode,
    LoadBalancingStrategy,
    ConnectionPool,
    ConnectionEndpoint,
    ProtoMessageBuilder,
    create_grpc_handler,
    call_grpc_method,
    GRPC_AVAILABLE,
    # Factory
    create_protocol_handler,
    get_handler_class,
    SUPPORTED_PROTOCOLS,
)

# Node management - imports from new location (will emit deprecation warning)
from usmsb_sdk.platform.external.node import (
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
    # Discovery
    NodeDiscoveryService,
    DiscoveredNode,
    NodeHealthStatus,
    HealthCheckResult,
    # Broadcast
    NodeBroadcastService,
    BroadcastMessage,
    BroadcastMessageType,
    MessageAck,
    # Sync
    SyncService,
    SyncMode,
    SyncStatus,
    SyncResult,
    DataChunk,
)

# Storage module
from usmsb_sdk.platform.external.storage import (
    # Base
    StorageInterface,
    StorageType,
    StorageResult,
    StorageError,
    DataLocation,
    # File Storage
    FileStorage,
    FileLockManager,
    # SQLite Storage
    SQLiteStorage,
    SessionStateManager,
    TransactionRecordManager,
    AgentRegistryManager,
    # IPFS Storage
    IPFSStorage,
    DataShardingManager,
    IPFSConnectionConfig,
    # Storage Manager
    StorageManager,
    CacheStrategy,
    SyncStrategy,
    ConsistencyLevel,
    create_storage_manager,
)

# Auth module
from usmsb_sdk.platform.external.auth import (
    # Enums
    Permission,
    StakeTier,
    # Base types
    AuthContext,
    BaseAuthResult,
    WalletAuthResult,
    StakeVerificationResult,
    FullAuthResult,
    IAuthProvider,
    # Wallet authentication
    WalletBinding,
    IWalletAuthenticator,
    MockWalletAuthenticator,
    # Stake verification
    StakeInfo,
    AgentRegistration,
    IStakeVerifier,
    MockStakeVerifier,
    MINIMUM_STAKE_FOR_REGISTRATION,
    STAKE_LOCK_PERIOD_DAYS,
    # Coordinator
    SessionInfo,
    VerificationContext,
    AuthCoordinator,
    SESSION_DURATION_HOURS,
    MAX_SESSION_DURATION_HOURS,
)

# Launcher module
from usmsb_sdk.platform.external.launcher import (
    PlatformLauncher,
    PlatformStatus,
    NodeInfo,
    ConfigWizard,
    HealthChecker,
    HealthReport,
    StatusMonitor,
    cli_main,
)

# External Agent Adapter (with legacy compatibility)
from usmsb_sdk.platform.external.external_agent_adapter import (
    ExternalAgentAdapter,
    ExternalAgentProfile,
    ExternalAgentProtocol,
    ExternalAgentStatus,
    ExternalAgentCall,
    ExternalAgentResponse,
    SkillDefinition as AdapterSkillDefinition,
    SkillMatchLevel,
    ProtocolHandler,
    A2AProtocolHandler as LegacyA2AProtocolHandler,
    HTTPProtocolHandler as LegacyHTTPProtocolHandler,
    create_skill_from_dict,
    create_agent_from_skill_md,
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
