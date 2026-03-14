"""
MCP (Model Context Protocol) Module

This module provides MCP protocol implementations for AI service integration.

The MCP protocol includes:
- Resources: Data sources that can be read
- Tools: Functions that can be called
- Prompts: Templates for interactions
- Sampling: LLM sampling requests

Usage:
    # MCP Adapter (resource/tool management)
    from usmsb_sdk.protocol.mcp import MCPAdapter
    adapter = MCPAdapter("http://localhost:8080/mcp")
    await adapter.start()
    await adapter.register_tool("my_tool", "A tool", schema, handler)

    # MCP Handler (client communication)
    from usmsb_sdk.protocol.mcp import MCPHandler
    handler = MCPHandler()
    await handler.connect("http://localhost:8080/mcp")
    result = await handler.call_skill("my_tool", {"arg": "value"})
"""

from usmsb_sdk.protocol.mcp.adapter import (
    MCPAdapter,
    MCPConnection,
    create_standard_tools,
)
from usmsb_sdk.protocol.mcp.handler import MCPHandler
from usmsb_sdk.protocol.mcp.types import (
    MCPMessage,
    MCPMessageType,
    MCPPrompt,
    MCPResource,
    MCPResourceType,
    MCPSamplingRequest,
    MCPSamplingResponse,
    MCPServerInfo,
    MCPTool,
    MCPToolCall,
    MCPToolResult,
    MCPToolStatus,
)

__all__ = [
    # Types
    "MCPMessageType",
    "MCPResourceType",
    "MCPToolStatus",
    "MCPResource",
    "MCPTool",
    "MCPPrompt",
    "MCPToolResult",
    "MCPSamplingRequest",
    "MCPSamplingResponse",
    "MCPServerInfo",
    "MCPToolCall",
    "MCPMessage",

    # Adapter
    "MCPAdapter",
    "MCPConnection",
    "create_standard_tools",

    # Handler
    "MCPHandler",
]
