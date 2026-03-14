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
    BlockchainNetwork,
    EthereumAdapter,
    IBlockchainAdapter,
    MockBlockchainAdapter,
    SmartContract,
    Transaction,
    TransactionStatus,
    WalletInfo,
)
from usmsb_sdk.platform.blockchain.digital_currency_manager import (
    CurrencyBalance,
    CurrencyConfig,
    CurrencyTransaction,
    CurrencyType,
    DigitalCurrencyManager,
    TransactionType,
)
from usmsb_sdk.platform.environment.broadcast_service import (
    BroadcastMessage,
    BroadcastPriority,
    BroadcastScope,
    BroadcastStats,
    BroadcastType,
    EnvironmentBroadcastService,
    Subscription,
)
from usmsb_sdk.platform.external.external_agent_adapter import (
    A2AProtocolHandler,
    ExternalAgentAdapter,
    ExternalAgentCall,
    ExternalAgentProfile,
    ExternalAgentProtocol,
    ExternalAgentResponse,
    ExternalAgentStatus,
    HTTPProtocolHandler,
    ProtocolHandler,
    SkillDefinition,
    SkillMatchLevel,
    create_agent_from_skill_md,
    create_skill_from_dict,
)
from usmsb_sdk.platform.internal import (
    BroadcastMessage as NodeBroadcastMessage,
)

# Import internal node management components
from usmsb_sdk.platform.internal import (
    BroadcastMessageType,
    ConnectionStatus,
    DataChunk,
    DiscoveredNode,
    HealthCheckResult,
    MessageAck,
    NetworkConfig,
    # Broadcast Service
    NodeBroadcastService,
    NodeCapabilities,
    # Config
    NodeConfig,
    NodeConnection,
    # Node Discovery
    NodeDiscoveryService,
    NodeHealthStatus,
    # Node Manager
    NodeManager,
    NodeState,
    SecurityConfig,
    SyncConfig,
    SyncMode,
    SyncResult,
    # Sync Service
    SyncService,
    SyncStatus,
)
from usmsb_sdk.platform.protocols.mcp_adapter import (
    MCPAdapter,
    MCPConnection,
    MCPMessageType,
    MCPPrompt,
    MCPResource,
    MCPResourceType,
    MCPSamplingRequest,
    MCPSamplingResponse,
    MCPTool,
    MCPToolResult,
    MCPToolStatus,
    create_standard_tools,
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
