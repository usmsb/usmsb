"""
Protocol Handlers Package (Deprecated)

.. deprecated::
    This module is deprecated. Use usmsb_sdk.protocol instead.

    Migration guide:
        from usmsb_sdk.platform.external.protocol import HTTPProtocolHandler
        ->
        from usmsb_sdk.protocol import HTTPClient

        from usmsb_sdk.platform.external.protocol import WebSocketProtocolHandler
        ->
        from usmsb_sdk.protocol import WebSocketClient
"""

import warnings
from typing import Optional

# Emit deprecation warning
warnings.warn(
    "platform.external.protocol is deprecated. Use usmsb_sdk.protocol instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location for backward compatibility
from usmsb_sdk.protocol.a2a.client import (
    A2AAgentInfo,
    A2AEnvelope,
    A2ASkillRequest,
    A2ASkillResponse,
)
from usmsb_sdk.protocol.a2a.client import (
    A2AClient as A2AProtocolHandler,
)
from usmsb_sdk.protocol.base import (
    BaseProtocolHandler,
    ConnectionInfo,
    ProtocolConfig,
    ProtocolMessage,
    ProtocolResponse,
)
from usmsb_sdk.protocol.grpc.handler import (
    GRPC_AVAILABLE,
    ConnectionEndpoint,
    ConnectionPool,
    LoadBalancingStrategy,
    ProtoMessageBuilder,
    call_grpc_method,
    create_grpc_handler,
    gRPCConfig,
    gRPCError,
    gRPCErrorCode,
    gRPCMethod,
    gRPCRequest,
    gRPCResponse,
    gRPCServiceDefinition,
)
from usmsb_sdk.protocol.grpc.handler import (
    gRPCHandler as gRPCProtocolHandler,
)
from usmsb_sdk.protocol.http.client import (
    HTTPAuthConfig,
    HTTPEndpointConfig,
    HTTPRequest,
    HTTPResponse,
    HTTPSkillEndpoint,
)
from usmsb_sdk.protocol.http.client import (
    HTTPClient as HTTPProtocolHandler,
)
from usmsb_sdk.protocol.mcp.handler import (
    MCPHandler as MCPProtocolHandler,
)
from usmsb_sdk.protocol.mcp.handler import (
    MCPServerInfo,
)
from usmsb_sdk.protocol.mcp.types import (
    MCPMessage,
    MCPPrompt,
    MCPResource,
    MCPTool,
    MCPToolCall,
    MCPToolResult,
)
from usmsb_sdk.protocol.p2p.handler import (
    P2PDHTEntry,
    P2PMessage,
    P2PNodeInfo,
    P2PSkillRequest,
    P2PSkillResponse,
)
from usmsb_sdk.protocol.p2p.handler import (
    P2PHandler as P2PProtocolHandler,
)
from usmsb_sdk.protocol.websocket.client import (
    WebSocketClient as WebSocketProtocolHandler,
)
from usmsb_sdk.protocol.websocket.client import (
    WebSocketConfig,
    WebSocketEvent,
    WebSocketMessage,
    WebSocketSubscription,
)

__all__ = [
    # Base handler
    "BaseProtocolHandler",
    "ProtocolConfig",
    "ProtocolMessage",
    "ProtocolResponse",
    "ConnectionInfo",

    # A2A Protocol
    "A2AProtocolHandler",
    "A2AEnvelope",
    "A2ASkillRequest",
    "A2ASkillResponse",
    "A2AAgentInfo",

    # HTTP Protocol
    "HTTPProtocolHandler",
    "HTTPEndpointConfig",
    "HTTPAuthConfig",
    "HTTPRequest",
    "HTTPResponse",
    "HTTPSkillEndpoint",

    # MCP Protocol
    "MCPProtocolHandler",
    "MCPServerInfo",
    "MCPTool",
    "MCPResource",
    "MCPPrompt",
    "MCPToolCall",
    "MCPToolResult",
    "MCPMessage",

    # P2P Protocol
    "P2PProtocolHandler",
    "P2PNodeInfo",
    "P2PMessage",
    "P2PSkillRequest",
    "P2PSkillResponse",
    "P2PDHTEntry",

    # WebSocket Protocol
    "WebSocketProtocolHandler",
    "WebSocketConfig",
    "WebSocketMessage",
    "WebSocketEvent",
    "WebSocketSubscription",

    # gRPC Protocol
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
    "GRPC_AVAILABLE",
    "create_grpc_handler",
    "call_grpc_method",
]


# Protocol handler factory (backward compatibility)
def create_protocol_handler(
    protocol: str,
    config: ProtocolConfig | None = None,
    **kwargs,
) -> BaseProtocolHandler:
    """
    Factory function to create protocol handlers.

    Args:
        protocol: Protocol type (a2a, http, mcp, p2p, websocket, grpc).
        config: Protocol configuration.
        **kwargs: Additional arguments for specific handlers.

    Returns:
        Protocol handler instance.

    Raises:
        ValueError: If protocol type is not supported.
    """
    from usmsb_sdk.protocol import create_protocol_handler as _create

    return _create(protocol, config, **kwargs)


# Convenience function to get handler class
def get_handler_class(protocol: str) -> type:
    """
    Get the handler class for a protocol type.

    Args:
        protocol: Protocol type.

    Returns:
        Handler class.

    Raises:
        ValueError: If protocol type is not supported.
    """
    from usmsb_sdk.protocol import get_handler_class as _get_class

    return _get_class(protocol)


# List of supported protocols
SUPPORTED_PROTOCOLS = ["a2a", "http", "mcp", "p2p", "websocket", "grpc"]
