"""
USMSB Protocol Integration Layer

Phase 0 模块：
- MultiWallet: 多币种钱包
- x402Router: 机器间微支付
- A2ACard: Agent 能力描述卡
- A2AAdapter: Agent 间通信
- MCPRegistry: 工具注册
- MCPGateway: MCP 网关
"""

from .multi_wallet import MultiWallet, WalletAddress, WalletBalance
from .x402_router import (
    x402Router,
    PaymentRequest,
    PaymentResult,
    PaymentStatus,
    Currency,
)
from .a2a_card import (
    AgentCard,
    AgentCardRegistry,
    Skill,
    AgentCapability,
)
from .a2a_adapter import (
    A2AAdapter,
    A2AMessage,
    A2AMessageType,
    DelegatedTask,
    TaskStatus,
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
    # A2A Card
    "AgentCard",
    "AgentCardRegistry",
    "Skill",
    "AgentCapability",
    # A2A Adapter
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
]
