"""
USMSB Platform Extensions Module.

This module provides platform-level components including:

- blockchain: Blockchain adapters and digital currency management
- protocols: MCP protocol adapter
- external: External agent adapters, authentication, protocols, and storage
- internal: Internal platform components (node management)
- compute: Compute resource adapters and scheduling
- human: Human resource management and talent matching
- governance: Governance and community services
- registry: Model and dataset registries
- environment: Environment broadcast services
"""

from usmsb_sdk.platform.blockchain.adapter import (
    IBlockchainAdapter,
    EthereumAdapter,
    MockBlockchainAdapter,
    BlockchainNetwork,
    Transaction,
    TransactionStatus,
    WalletInfo,
    SmartContract,
)
from usmsb_sdk.platform.blockchain.digital_currency_manager import (
    DigitalCurrencyManager,
    CurrencyConfig,
    CurrencyBalance,
    CurrencyTransaction,
    CurrencyType,
    TransactionType,
)
from usmsb_sdk.platform.protocols.mcp_adapter import (
    MCPAdapter,
    MCPConnection,
    MCPResource,
    MCPResourceType,
    MCPTool,
    MCPToolResult,
    MCPToolStatus,
    MCPPrompt,
    MCPSamplingRequest,
    MCPSamplingResponse,
    MCPMessageType,
    create_standard_tools,
)
from usmsb_sdk.platform.external.external_agent_adapter import (
    ExternalAgentAdapter,
    ExternalAgentProfile,
    ExternalAgentProtocol,
    ExternalAgentStatus,
    ExternalAgentCall,
    ExternalAgentResponse,
    SkillDefinition,
    SkillMatchLevel,
    ProtocolHandler,
    A2AProtocolHandler,
    HTTPProtocolHandler,
    create_skill_from_dict,
    create_agent_from_skill_md,
)
from usmsb_sdk.platform.environment.broadcast_service import (
    EnvironmentBroadcastService,
    BroadcastMessage,
    BroadcastType,
    BroadcastPriority,
    BroadcastScope,
    Subscription,
    BroadcastStats,
)

# Import internal node management components
from usmsb_sdk.platform.internal import (
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
    BroadcastMessage as NodeBroadcastMessage,
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
    # Blockchain
    "IBlockchainAdapter",
    "EthereumAdapter",
    "MockBlockchainAdapter",
    "BlockchainNetwork",
    "Transaction",
    "TransactionStatus",
    "WalletInfo",
    "SmartContract",
    # Digital Currency
    "DigitalCurrencyManager",
    "CurrencyConfig",
    "CurrencyBalance",
    "CurrencyTransaction",
    "CurrencyType",
    "TransactionType",
    # MCP Protocol
    "MCPAdapter",
    "MCPConnection",
    "MCPResource",
    "MCPResourceType",
    "MCPTool",
    "MCPToolResult",
    "MCPToolStatus",
    "MCPPrompt",
    "MCPSamplingRequest",
    "MCPSamplingResponse",
    "MCPMessageType",
    "create_standard_tools",
    # External Agent
    "ExternalAgentAdapter",
    "ExternalAgentProfile",
    "ExternalAgentProtocol",
    "ExternalAgentStatus",
    "ExternalAgentCall",
    "ExternalAgentResponse",
    "SkillDefinition",
    "SkillMatchLevel",
    "ProtocolHandler",
    "A2AProtocolHandler",
    "HTTPProtocolHandler",
    "create_skill_from_dict",
    "create_agent_from_skill_md",
    # Environment Broadcast
    "EnvironmentBroadcastService",
    "BroadcastMessage",
    "BroadcastType",
    "BroadcastPriority",
    "BroadcastScope",
    "Subscription",
    "BroadcastStats",
    # Internal Node Management - Config
    "NodeConfig",
    "NetworkConfig",
    "SyncConfig",
    "SecurityConfig",
    "NodeCapabilities",
    # Internal Node Management - Manager
    "NodeManager",
    "NodeState",
    "NodeConnection",
    "ConnectionStatus",
    # Internal Node Management - Discovery
    "NodeDiscoveryService",
    "DiscoveredNode",
    "NodeHealthStatus",
    "HealthCheckResult",
    # Internal Node Management - Broadcast
    "NodeBroadcastService",
    "NodeBroadcastMessage",
    "BroadcastMessageType",
    "MessageAck",
    # Internal Node Management - Sync
    "SyncService",
    "SyncMode",
    "SyncStatus",
    "SyncResult",
    "DataChunk",
]
