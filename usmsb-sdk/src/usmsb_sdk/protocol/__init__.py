"""
USMSB SDK Protocol Layer

This module provides unified protocol handlers for all communication patterns:

Supported Protocols:
- HTTP: RESTful API communication (server and client)
- WebSocket: Real-time bidirectional communication
- MCP: Model Context Protocol for AI services
- A2A: Agent-to-Agent protocol
- P2P: Peer-to-Peer decentralized communication
- gRPC: High-performance RPC framework

Usage:
    from usmsb_sdk.protocol import (
        BaseProtocolHandler,
        HTTPServer,
        HTTPClient,
        WebSocketServer,
        WebSocketClient,
        MCPAdapter,
        MCPHandler,
        A2AProtocolHandler,
        P2PProtocolHandler,
        gRPCProtocolHandler,
    )

    # Create HTTP client
    from usmsb_sdk.protocol.http import HTTPClient
    client = HTTPClient()
    await client.connect("https://api.example.com")
    response = await client.call_skill("example", {"arg": "value"})
"""

# Base types
from usmsb_sdk.protocol.base import (
    BaseProtocolHandler,
    ProtocolConfig,
    ProtocolMessage,
    ProtocolResponse,
    ConnectionInfo,
    ExternalAgentStatus,
    ExternalAgentResponse,
    SkillDefinition,
)

# HTTP Protocol
from usmsb_sdk.protocol.http import (
    HTTPServer,
    HTTPClient,
    HTTPEndpointConfig,
    HTTPAuthConfig,
    HTTPRequest,
    HTTPResponse,
)

# WebSocket Protocol
from usmsb_sdk.protocol.websocket import (
    WebSocketServer,
    WebSocketClient,
    WebSocketConfig,
    WebSocketMessage,
    WebSocketEvent,
)

# MCP Protocol
from usmsb_sdk.protocol.mcp import (
    MCPAdapter,
    MCPHandler,
    MCPConnection,
    MCPResource,
    MCPResourceType,
    MCPTool,
    MCPToolResult,
    MCPToolStatus,
    MCPPrompt,
    MCPSamplingRequest,
    MCPSamplingResponse,
    MCPServerInfo,
    MCPToolCall,
    MCPMessage,
)

# A2A Protocol
from usmsb_sdk.protocol.a2a import (
    A2AServer,
    A2AClient,
    A2AEnvelope,
    A2ASkillRequest,
    A2ASkillResponse,
    A2AAgentInfo,
)

# P2P Protocol
from usmsb_sdk.protocol.p2p import (
    P2PHandler,
    P2PNodeInfo,
    P2PMessage,
    P2PSkillRequest,
    P2PSkillResponse,
    P2PDHTEntry,
)

# gRPC Protocol
from usmsb_sdk.protocol.grpc import (
    gRPCHandler,
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
)


__all__ = [
    # Base
    "BaseProtocolHandler",
    "ProtocolConfig",
    "ProtocolMessage",
    "ProtocolResponse",
    "ConnectionInfo",
    "ExternalAgentStatus",
    "ExternalAgentResponse",
    "SkillDefinition",

    # HTTP
    "HTTPServer",
    "HTTPClient",
    "HTTPEndpointConfig",
    "HTTPAuthConfig",
    "HTTPRequest",
    "HTTPResponse",

    # WebSocket
    "WebSocketServer",
    "WebSocketClient",
    "WebSocketConfig",
    "WebSocketMessage",
    "WebSocketEvent",

    # MCP
    "MCPAdapter",
    "MCPHandler",
    "MCPConnection",
    "MCPResource",
    "MCPResourceType",
    "MCPTool",
    "MCPToolResult",
    "MCPToolStatus",
    "MCPPrompt",
    "MCPSamplingRequest",
    "MCPSamplingResponse",
    "MCPServerInfo",
    "MCPToolCall",
    "MCPMessage",

    # A2A
    "A2AServer",
    "A2AClient",
    "A2AEnvelope",
    "A2ASkillRequest",
    "A2ASkillResponse",
    "A2AAgentInfo",

    # P2P
    "P2PHandler",
    "P2PNodeInfo",
    "P2PMessage",
    "P2PSkillRequest",
    "P2PSkillResponse",
    "P2PDHTEntry",

    # gRPC
    "gRPCHandler",
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
]


from typing import Optional as _Optional

# Supported protocols
SUPPORTED_PROTOCOLS = ["http", "websocket", "mcp", "a2a", "p2p", "grpc"]


def create_protocol_handler(
    protocol: str,
    config: _Optional[ProtocolConfig] = None,
    **kwargs,
) -> BaseProtocolHandler:
    """
    Factory function to create protocol handlers.

    Args:
        protocol: Protocol type (http, websocket, mcp, a2a, p2p, grpc).
        config: Protocol configuration.
        **kwargs: Additional arguments for specific handlers.

    Returns:
        Protocol handler instance.

    Raises:
        ValueError: If protocol type is not supported.
    """
    protocol = protocol.lower()

    if protocol == "http":
        from usmsb_sdk.protocol.http import HTTPClient
        return HTTPClient(config=config, **kwargs)
    elif protocol == "websocket":
        from usmsb_sdk.protocol.websocket import WebSocketClient
        return WebSocketClient(config=config, **kwargs)
    elif protocol == "mcp":
        from usmsb_sdk.protocol.mcp import MCPHandler
        return MCPHandler(config=config, **kwargs)
    elif protocol == "a2a":
        from usmsb_sdk.protocol.a2a import A2AClient
        return A2AClient(config=config, **kwargs)
    elif protocol == "p2p":
        from usmsb_sdk.protocol.p2p import P2PHandler
        return P2PHandler(config=config, **kwargs)
    elif protocol == "grpc":
        from usmsb_sdk.protocol.grpc import gRPCHandler
        grpc_config = kwargs.pop("grpc_config", None)
        return gRPCHandler(config=config, grpc_config=grpc_config, **kwargs)
    else:
        raise ValueError(f"Unsupported protocol type: {protocol}")


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
    from usmsb_sdk.protocol.http import HTTPClient
    from usmsb_sdk.protocol.websocket import WebSocketClient
    from usmsb_sdk.protocol.mcp import MCPHandler
    from usmsb_sdk.protocol.a2a import A2AClient
    from usmsb_sdk.protocol.p2p import P2PHandler
    from usmsb_sdk.protocol.grpc import gRPCHandler

    protocol_map = {
        "http": HTTPClient,
        "websocket": WebSocketClient,
        "mcp": MCPHandler,
        "a2a": A2AClient,
        "p2p": P2PHandler,
        "grpc": gRPCHandler,
    }

    protocol = protocol.lower()
    if protocol not in protocol_map:
        raise ValueError(f"Unsupported protocol type: {protocol}")

    return protocol_map[protocol]
