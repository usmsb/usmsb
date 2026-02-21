"""
MCP Protocol Adapters Module (Deprecated)

.. deprecated::
    This module is deprecated. Use usmsb_sdk.protocol.mcp instead.

    Migration guide:
        from usmsb_sdk.platform.protocols import MCPAdapter
        ->
        from usmsb_sdk.protocol import MCPAdapter
"""

import warnings

# Emit deprecation warning
warnings.warn(
    "platform.protocols is deprecated. Use usmsb_sdk.protocol instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location for backward compatibility
from usmsb_sdk.protocol.mcp import (
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

__all__ = [
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
]
