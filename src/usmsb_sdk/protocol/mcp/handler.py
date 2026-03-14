"""
MCP Protocol Handler

This module provides the handler for Model Context Protocol (MCP),
enabling communication with AI services following the MCP specification.
"""

import asyncio
import logging
import uuid
from typing import Any

from usmsb_sdk.protocol.base import (
    BaseProtocolHandler,
    ExternalAgentStatus,
    ProtocolConfig,
    SkillDefinition,
)
from usmsb_sdk.protocol.mcp.types import (
    MCPMessage,
    MCPPrompt,
    MCPResource,
    MCPServerInfo,
    MCPTool,
    MCPToolCall,
)

logger = logging.getLogger(__name__)


class MCPHandler(BaseProtocolHandler):
    """
    Handler for Model Context Protocol (MCP).

    This handler implements the MCP specification for communication
    with AI services.

    Features:
    - Tool discovery and execution
    - Resource access
    - Prompt management
    - JSON-RPC 2.0 protocol

    Note: This is a framework implementation. Full MCP support
    including stdio, WebSocket transports will be added later.
    """

    MCP_VERSION = "2024-11-05"

    def __init__(
        self,
        config: ProtocolConfig | None = None,
        client_name: str = "usmsb-sdk",
        client_version: str = "1.0.0",
    ):
        """
        Initialize the MCP handler.

        Args:
            config: Protocol configuration.
            client_name: Name of the MCP client.
            client_version: Version of the MCP client.
        """
        super().__init__(config)
        self._client_name = client_name
        self._client_version = client_version
        self._server_info: MCPServerInfo | None = None
        self._tools: list[MCPTool] = []
        self._resources: list[MCPResource] = []
        self._prompts: list[MCPPrompt] = []
        self._session_id: str | None = None
        self._initialized = False

        logger.info(f"MCPHandler initialized: {client_name} v{client_version}")

    # ========== Protocol-Specific Implementation ==========

    async def _do_connect(self, endpoint: str) -> bool:
        """
        Establish MCP connection to the endpoint.

        Args:
            endpoint: The MCP endpoint (URL or command for stdio).

        Returns:
            True if connection successful.
        """
        try:
            # Initialize MCP session
            success = await self._initialize_session()

            if success:
                logger.info(f"MCP connection established to {endpoint}")
                return True

            return False

        except Exception as e:
            logger.error(f"MCP connection error: {e}")
            return False

    async def _do_disconnect(self) -> None:
        """Close the MCP connection."""
        if self._initialized:
            # Send shutdown notification
            await self._send_notification("shutdown", {})
            self._initialized = False

        self._server_info = None
        self._tools.clear()
        self._resources.clear()
        self._prompts.clear()

        logger.info("MCP connection closed")

    async def _do_call_skill(
        self,
        skill_name: str,
        arguments: dict[str, Any],
        timeout: float,
    ) -> Any:
        """
        Execute a skill (MCP tool) via MCP protocol.

        Args:
            skill_name: Name of the tool to execute.
            arguments: Arguments for the tool.
            timeout: Timeout for execution.

        Returns:
            Result from the tool execution.
        """
        if not self._initialized:
            raise Exception("MCP session not initialized")

        # Create tool call
        tool_call = MCPToolCall(
            name=skill_name,
            arguments=arguments,
        )

        # Send tools/call request
        response = await self._send_request(
            "tools/call",
            {
                "name": tool_call.name,
                "arguments": tool_call.arguments,
            },
            timeout=timeout,
        )

        if "error" in response:
            raise Exception(response["error"].get("message", "Unknown error"))

        # Extract content from result
        result = response.get("result", {})
        content = result.get("content", [])

        # Convert content to simple format
        if content:
            text_content = [
                item.get("text", "")
                for item in content
                if item.get("type") == "text"
            ]
            if text_content:
                return {"output": "\n".join(text_content)}

        return result

    async def _do_discover_skills(self) -> list[SkillDefinition]:
        """
        Discover skills (MCP tools) from the server.

        Returns:
            List of discovered skills.
        """
        if not self._initialized:
            return []

        try:
            # Fetch tools list
            response = await self._send_request("tools/list", {})

            if "result" in response:
                tools_data = response["result"].get("tools", [])

                self._tools = [
                    MCPTool(
                        name=t.get("name", ""),
                        description=t.get("description", ""),
                        input_schema=t.get("inputSchema", {}),
                    )
                    for t in tools_data
                ]

                return [
                    SkillDefinition(
                        skill_id=f"mcp-tool-{tool.name}",
                        name=tool.name,
                        description=tool.description,
                        category="mcp-tool",
                        input_schema=tool.input_schema,
                    )
                    for tool in self._tools
                ]

            return []

        except Exception as e:
            logger.error(f"MCP tool discovery error: {e}")
            return []

    async def _do_check_status(self) -> ExternalAgentStatus:
        """
        Check the MCP server status.

        Returns:
            Current status of the MCP server.
        """
        if not self._initialized or not self._server_info:
            return ExternalAgentStatus.OFFLINE

        try:
            # Send ping to check connection
            response = await self._send_request("ping", {}, timeout=5.0)

            if "error" not in response:
                return ExternalAgentStatus.ONLINE

            return ExternalAgentStatus.ERROR

        except Exception:
            return ExternalAgentStatus.OFFLINE

    # ========== MCP-Specific Methods ==========

    async def _initialize_session(self) -> bool:
        """
        Initialize MCP session with handshake.

        Returns:
            True if initialization successful.
        """
        try:
            # Send initialize request
            response = await self._send_request(
                "initialize",
                {
                    "protocolVersion": self.MCP_VERSION,
                    "capabilities": {
                        "tools": {},
                        "resources": {},
                        "prompts": {},
                    },
                    "clientInfo": {
                        "name": self._client_name,
                        "version": self._client_version,
                    },
                },
                timeout=30.0,
            )

            if "result" in response:
                result = response["result"]
                server_info = result.get("serverInfo", {})

                self._server_info = MCPServerInfo(
                    name=server_info.get("name", "Unknown"),
                    version=server_info.get("version", "1.0.0"),
                    protocol_version=result.get("protocolVersion", self.MCP_VERSION),
                    capabilities=result.get("capabilities", {}),
                    instructions=result.get("instructions", ""),
                )

                # Send initialized notification
                await self._send_notification("notifications/initialized", {})

                self._initialized = True
                self._session_id = str(uuid.uuid4())

                logger.info(f"MCP session initialized: {self._server_info.name}")
                return True

            return False

        except Exception as e:
            logger.error(f"MCP session initialization error: {e}")
            return False

    async def _send_request(
        self,
        method: str,
        params: dict[str, Any],
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        """
        Send an MCP request.

        Args:
            method: MCP method name.
            params: Request parameters.
            timeout: Request timeout.

        Returns:
            Response dictionary.
        """
        request_id = str(uuid.uuid4())

        MCPMessage(
            id=request_id,
            method=method,
            params=params,
        )

        logger.debug(f"MCP request: {method} (id={request_id})")

        # In real implementation, send via transport (stdio, WebSocket, etc.)
        # Simulated response
        await asyncio.sleep(0.1)

        # Simulated responses based on method
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": self.MCP_VERSION,
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"subscribe": True, "listChanged": True},
                        "prompts": {"listChanged": True},
                    },
                    "serverInfo": {
                        "name": "MCP Server",
                        "version": "1.0.0",
                    },
                },
            }
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "example_tool",
                            "description": "An example MCP tool",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"},
                                },
                            },
                        }
                    ]
                },
            }
        elif method == "tools/call":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {"type": "text", "text": f"Executed tool: {params.get('name')}"}
                    ]
                },
            }
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}

        return {"jsonrpc": "2.0", "id": request_id, "result": {}}

    async def _send_notification(
        self,
        method: str,
        params: dict[str, Any],
    ) -> None:
        """
        Send an MCP notification.

        Args:
            method: Notification method name.
            params: Notification parameters.
        """
        MCPMessage(
            method=method,
            params=params,
        )

        logger.debug(f"MCP notification: {method}")

        # In real implementation, send via transport
        await asyncio.sleep(0.01)

    # ========== Resource Methods ==========

    async def list_resources(self) -> list[MCPResource]:
        """
        List available MCP resources.

        Returns:
            List of available resources.
        """
        if not self._initialized:
            return []

        try:
            response = await self._send_request("resources/list", {})

            if "result" in response:
                resources_data = response["result"].get("resources", [])

                self._resources = [
                    MCPResource(
                        uri=r.get("uri", ""),
                        name=r.get("name", ""),
                        description=r.get("description", ""),
                        resource_type=r.get("type", "text"),
                        mime_type=r.get("mimeType", "text/plain"),
                        metadata=r.get("metadata", {}),
                    )
                    for r in resources_data
                ]

                return self._resources

            return []

        except Exception as e:
            logger.error(f"MCP resource list error: {e}")
            return []

    async def read_resource(self, uri: str) -> Any:
        """
        Read an MCP resource.

        Args:
            uri: Resource URI.

        Returns:
            Resource content.
        """
        if not self._initialized:
            raise Exception("MCP session not initialized")

        response = await self._send_request(
            "resources/read",
            {"uri": uri},
        )

        if "error" in response:
            raise Exception(response["error"].get("message", "Unknown error"))

        return response.get("result", {})

    # ========== Prompt Methods ==========

    async def list_prompts(self) -> list[MCPPrompt]:
        """
        List available MCP prompts.

        Returns:
            List of available prompts.
        """
        if not self._initialized:
            return []

        try:
            response = await self._send_request("prompts/list", {})

            if "result" in response:
                prompts_data = response["result"].get("prompts", [])

                self._prompts = [
                    MCPPrompt(
                        name=p.get("name", ""),
                        description=p.get("description", ""),
                        arguments=p.get("arguments", []),
                    )
                    for p in prompts_data
                ]

                return self._prompts

            return []

        except Exception as e:
            logger.error(f"MCP prompt list error: {e}")
            return []

    async def get_prompt(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> Any:
        """
        Get an MCP prompt.

        Args:
            name: Prompt name.
            arguments: Prompt arguments.

        Returns:
            Prompt content.
        """
        if not self._initialized:
            raise Exception("MCP session not initialized")

        response = await self._send_request(
            "prompts/get",
            {"name": name, "arguments": arguments or {}},
        )

        if "error" in response:
            raise Exception(response["error"].get("message", "Unknown error"))

        return response.get("result", {})

    # ========== Utility Methods ==========

    def get_server_info(self) -> MCPServerInfo | None:
        """Get MCP server information."""
        return self._server_info

    def get_tools(self) -> list[MCPTool]:
        """Get list of available tools."""
        return self._tools

    def get_resources(self) -> list[MCPResource]:
        """Get list of available resources."""
        return self._resources

    def get_prompts(self) -> list[MCPPrompt]:
        """Get list of available prompts."""
        return self._prompts

    def is_initialized(self) -> bool:
        """Check if MCP session is initialized."""
        return self._initialized
