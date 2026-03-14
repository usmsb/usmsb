"""
MCP (Model Context Protocol) Adapter

.. deprecated::
    This module has been moved to `usmsb_sdk.protocol.mcp.adapter`.
    Please update your imports to use the new location.
    This module will be removed in a future version.

    Old import:
        from usmsb_sdk.platform.protocols.mcp_adapter import MCPAdapter

    New import:
        from usmsb_sdk.protocol.mcp import MCPAdapter, MCPConnection
        from usmsb_sdk.protocol.mcp.types import (
            MCPResource, MCPTool, MCPPrompt, MCPToolResult,
            MCPSamplingRequest, MCPSamplingResponse,
            MCPMessageType, MCPResourceType, MCPToolStatus,
        )
"""

import warnings

# Issue deprecation warning when this module is imported
warnings.warn(
    "platform.protocols.mcp_adapter is deprecated. "
    "Use usmsb_sdk.protocol.mcp instead. "
    "This module will be removed in a future version.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location for backward compatibility
from usmsb_sdk.protocol.mcp.adapter import (
    MCPAdapter,
    MCPConnection,
    create_standard_tools,
)
from usmsb_sdk.protocol.mcp.types import (
    MCPMessageType,
    MCPPrompt,
    MCPResource,
    MCPResourceType,
    MCPSamplingRequest,
    MCPSamplingResponse,
    MCPTool,
    MCPToolResult,
    MCPToolStatus,
)

__all__ = [
    # Connection
    "MCPConnection",
    # Adapter
    "MCPAdapter",
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
    # Utilities
    "create_standard_tools",
]
