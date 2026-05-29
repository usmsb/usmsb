"""
USMSB Protocol Integration Layer

Phase 0 模块：
- MultiWallet: 多币种钱包
- x402Router: 机器间微支付
- A2ACard: Agent 能力描述卡
- A2AAdapter: Agent 间通信
- MCPRegistry: 工具注册
- MCPGateway: MCP 网关

新类型系统（Phase 1）：
- protocol/types/ - 统一类型定义
  - types/google_a2a/ - Google A2A 类型（对齐官方 Spec 1.0）
  - types/custom_a2a/ - Custom A2A 类型（USMSB 私有协议）
  - types/envelope.py - 统一 A2AEnvelope
"""

# Phase 0 modules (kept for backward compatibility)
from .multi_wallet import MultiWallet, WalletAddress, WalletBalance
from .x402_router import (
    x402Router,
    PaymentRequest,
    PaymentResult,
    PaymentStatus,
    Currency,
)
from .a2a_card import (
    AgentCard as AgentCard,
    AgentCardRegistry,
    Skill,
    AgentCapability,
)
from .a2a_adapter import (
    A2AAdapter as A2AAdapter,
    A2AMessage as A2AMessage,
    A2AMessageType as A2AMessageType,
    DelegatedTask as DelegatedTask,
    TaskStatus as TaskStatus,
)
from .mcp_registry import (
    MCPRegistry,
    MCPTool,
    ToolCategory,
    MCPToolBuilder,
    ToolSchema,
)
from .mcp_gateway import (
    MCPGateway,
    ToolCall,
    CallStatus,
    MCPCallError,
)

# New type system - import from types/
from usmsb_sdk.protocol.types import (
    # Envelope
    A2AEnvelope,
    # Google A2A
    TaskState,
    Role,
    MessageType,
    Part,
    Message,
    TaskStatus,
    Artifact,
    Task,
    SendMessageConfiguration,
    TaskPushNotificationConfig,
    AuthenticationInfo,
    AgentCapabilities,
    AgentExtension,
    AgentProvider,
    AgentInterface,
    AgentSkill,
    AgentCard as GoogleAgentCard,
    SendMessageRequest,
    GetTaskRequest,
    CancelTaskRequest,
    ListTasksRequest,
    SubscribeToTaskRequest,
    # Custom A2A
    CustomTaskStatus,
    CustomMessageType,
    CustomPart,
    CustomMessage,
    CustomTask,
    CustomAgentCard,
)

# Handlers
from usmsb_sdk.protocol.google_a2a import GoogleA2AHandler
from usmsb_sdk.protocol.custom_a2a import CustomA2AHandler

__all__ = [
    # MultiWallet
    "MultiWallet",
    "WalletAddress",
    "WalletBalance",
    # x402 Router
    "x402Router",
    "PaymentRequest",
    "PaymentResult",
    "PaymentStatus",
    "Currency",
    # A2A Card (backward compat - re-exported from old module)
    "AgentCard",
    "AgentCardRegistry",
    "Skill",
    "AgentCapability",
    # A2A Adapter (backward compat - re-exported from old module)
    "A2AAdapter",
    "A2AMessage",
    "A2AMessageType",
    "DelegatedTask",
    "TaskStatus",
    # MCP Registry
    "MCPRegistry",
    "MCPTool",
    "ToolCategory",
    "MCPToolBuilder",
    "ToolSchema",
    # MCP Gateway
    "MCPGateway",
    "ToolCall",
    "CallStatus",
    "MCPCallError",
    # New types - A2A Envelope
    "A2AEnvelope",
    # New types - Google A2A
    "TaskState",
    "Role",
    "MessageType",
    "Part",
    "Message",
    "TaskStatus",
    "Artifact",
    "Task",
    "SendMessageConfiguration",
    "TaskPushNotificationConfig",
    "AuthenticationInfo",
    "AgentCapabilities",
    "AgentExtension",
    "AgentProvider",
    "AgentInterface",
    "AgentSkill",
    "GoogleAgentCard",
    "SendMessageRequest",
    "GetTaskRequest",
    "CancelTaskRequest",
    "ListTasksRequest",
    "SubscribeToTaskRequest",
    # New types - Custom A2A
    "CustomTaskStatus",
    "CustomMessageType",
    "CustomPart",
    "CustomMessage",
    "CustomTask",
    "CustomAgentCard",
    # Handlers
    "GoogleA2AHandler",
    "CustomA2AHandler",
]
