"""
MCP Protocol Adapter

This module provides the MCP adapter for integrating external AI services
using the Model Context Protocol.
"""

import asyncio
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Union

from usmsb_sdk.protocol.mcp.types import (
    MCPMessageType,
    MCPResourceType,
    MCPToolStatus,
    MCPResource,
    MCPTool,
    MCPPrompt,
    MCPToolResult,
    MCPSamplingRequest,
    MCPSamplingResponse,
)


logger = logging.getLogger(__name__)


class MCPConnection:
    """Manages MCP protocol connection."""

    def __init__(self, server_url: str, api_key: Optional[str] = None):
        self.server_url = server_url
        self.api_key = api_key
        self.session_id: Optional[str] = None
        self.connected = False
        self._message_id = 0
        self._pending_requests: Dict[str, asyncio.Future] = {}

    async def connect(self) -> bool:
        """Establish connection to MCP server."""
        try:
            # In real implementation, this would establish WebSocket or HTTP connection
            self.session_id = str(uuid.uuid4())
            self.connected = True
            logger.info(f"MCP connection established: {self.session_id}")
            return True
        except Exception as e:
            logger.error(f"MCP connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        self.connected = False
        self.session_id = None
        logger.info("MCP connection closed")

    async def send_request(
        self,
        method: str,
        params: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Send a request to MCP server."""
        if not self.connected:
            raise RuntimeError("Not connected to MCP server")

        self._message_id += 1
        request_id = str(self._message_id)

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        # In real implementation, send over transport
        logger.debug(f"MCP Request: {method}")
        return {"result": {}, "id": request_id}

    async def send_notification(
        self,
        method: str,
        params: Dict[str, Any],
    ) -> None:
        """Send a notification to MCP server."""
        if not self.connected:
            raise RuntimeError("Not connected to MCP server")

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        logger.debug(f"MCP Notification: {method}")


class MCPAdapter:
    """
    MCP Protocol Adapter for External AI Services.

    This adapter implements the Model Context Protocol for:
    - Resource management (data sources)
    - Tool management (function calling)
    - Prompt management (templates)
    - Sampling (LLM requests)

    It integrates with USMSB agents for seamless external service access.
    """

    def __init__(
        self,
        server_url: str = "http://localhost:8080/mcp",
        api_key: Optional[str] = None,
    ):
        """
        Initialize MCP Adapter.

        Args:
            server_url: URL of the MCP server
            api_key: Optional API key for authentication
        """
        self.connection = MCPConnection(server_url, api_key)

        # Registered resources, tools, prompts
        self._resources: Dict[str, MCPResource] = {}
        self._tools: Dict[str, MCPTool] = {}
        self._prompts: Dict[str, MCPPrompt] = {}

        # Tool handlers
        self._tool_handlers: Dict[str, Callable] = {}

        # Resource handlers
        self._resource_handlers: Dict[str, Callable] = {}

        # Context store
        self._context: Dict[str, Any] = {}

        # Callbacks
        self.on_resource_accessed: Optional[Callable[[MCPResource], None]] = None
        self.on_tool_executed: Optional[Callable[[MCPTool, MCPToolResult], None]] = None

    async def start(self) -> bool:
        """Start the MCP adapter."""
        connected = await self.connection.connect()
        if connected:
            await self._initialize_capabilities()
        return connected

    async def stop(self) -> None:
        """Stop the MCP adapter."""
        await self.connection.disconnect()

    async def _initialize_capabilities(self) -> None:
        """Initialize MCP capabilities with server."""
        # Register local capabilities
        await self.connection.send_notification(
            "capabilities/register",
            {
                "resources": [r.to_dict() for r in self._resources.values()],
                "tools": [t.to_dict() for t in self._tools.values()],
                "prompts": [p.to_dict() for p in self._prompts.values()],
            }
        )
        logger.info("MCP capabilities initialized")

    # ========== Resource Management ==========

    def register_resource(
        self,
        uri: str,
        name: str,
        description: str,
        resource_type: MCPResourceType,
        handler: Callable,
        mime_type: str = "text/plain",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MCPResource:
        """
        Register a resource.

        Args:
            uri: Unique resource identifier
            name: Human-readable name
            description: Resource description
            resource_type: Type of resource
            handler: Async function to read resource
            mime_type: MIME type of resource content
            metadata: Additional metadata

        Returns:
            The registered resource
        """
        resource = MCPResource(
            uri=uri,
            name=name,
            description=description,
            resource_type=resource_type,
            mime_type=mime_type,
            metadata=metadata or {},
        )

        self._resources[uri] = resource
        self._resource_handlers[uri] = handler

        logger.info(f"Registered MCP resource: {uri}")
        return resource

    async def list_resources(self) -> List[MCPResource]:
        """List all available resources."""
        return list(self._resources.values())

    async def read_resource(
        self,
        uri: str,
        encoding: str = "utf-8",
    ) -> Union[str, bytes, Dict[str, Any]]:
        """
        Read a resource.

        Args:
            uri: Resource URI
            encoding: Text encoding

        Returns:
            Resource content
        """
        if uri not in self._resources:
            raise ValueError(f"Resource not found: {uri}")

        resource = self._resources[uri]
        handler = self._resource_handlers.get(uri)

        if handler:
            content = await handler(resource)
        else:
            content = f"Resource content for {uri}"

        if self.on_resource_accessed:
            self.on_resource_accessed(resource)

        return content

    # ========== Tool Management ==========

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable,
        output_schema: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MCPTool:
        """
        Register a tool.

        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON Schema for input
            handler: Async function to execute tool
            output_schema: Optional JSON Schema for output
            metadata: Additional metadata

        Returns:
            The registered tool
        """
        tool = MCPTool(
            name=name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            metadata=metadata or {},
        )

        self._tools[name] = tool
        self._tool_handlers[name] = handler

        logger.info(f"Registered MCP tool: {name}")
        return tool

    async def list_tools(self) -> List[MCPTool]:
        """List all available tools."""
        return list(self._tools.values())

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        timeout: float = 60.0,
    ) -> MCPToolResult:
        """
        Execute a tool.

        Args:
            name: Tool name
            arguments: Tool arguments
            timeout: Execution timeout

        Returns:
            Tool execution result
        """
        if name not in self._tools:
            return MCPToolResult(
                tool_name=name,
                status=MCPToolStatus.FAILED,
                error=f"Tool not found: {name}",
            )

        tool = self._tools[name]
        handler = self._tool_handlers.get(name)

        start_time = time.time()

        try:
            if handler:
                # Execute with timeout
                output = await asyncio.wait_for(
                    handler(arguments),
                    timeout=timeout
                )
            else:
                output = {"result": "Tool executed (no handler)"}

            result = MCPToolResult(
                tool_name=name,
                status=MCPToolStatus.COMPLETED,
                output=output,
                execution_time=time.time() - start_time,
            )

        except asyncio.TimeoutError:
            result = MCPToolResult(
                tool_name=name,
                status=MCPToolStatus.TIMEOUT,
                error=f"Tool execution timed out after {timeout}s",
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            result = MCPToolResult(
                tool_name=name,
                status=MCPToolStatus.FAILED,
                error=str(e),
                execution_time=time.time() - start_time,
            )

        if self.on_tool_executed:
            self.on_tool_executed(tool, result)

        return result

    # ========== Prompt Management ==========

    def register_prompt(
        self,
        name: str,
        description: str,
        template: str,
        arguments: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MCPPrompt:
        """
        Register a prompt template.

        Args:
            name: Prompt name
            description: Prompt description
            template: Prompt template string
            arguments: List of argument definitions
            metadata: Additional metadata

        Returns:
            The registered prompt
        """
        prompt = MCPPrompt(
            name=name,
            description=description,
            arguments=arguments or [],
            template=template,
            metadata=metadata or {},
        )

        self._prompts[name] = prompt
        logger.info(f"Registered MCP prompt: {name}")
        return prompt

    async def list_prompts(self) -> List[MCPPrompt]:
        """List all available prompts."""
        return list(self._prompts.values())

    async def get_prompt(
        self,
        name: str,
        arguments: Dict[str, Any],
    ) -> str:
        """
        Get a prompt with arguments applied.

        Args:
            name: Prompt name
            arguments: Arguments to fill in template

        Returns:
            Rendered prompt string
        """
        if name not in self._prompts:
            raise ValueError(f"Prompt not found: {name}")

        prompt = self._prompts[name]

        # Simple template rendering
        result = prompt.template
        for key, value in arguments.items():
            result = result.replace(f"{{{key}}}", str(value))

        return result

    # ========== Sampling (LLM Requests) ==========

    async def create_sampling_request(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
    ) -> MCPSamplingRequest:
        """
        Create a sampling request.

        Args:
            messages: List of message objects
            model: Model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop_sequences: Stop sequences

        Returns:
            Sampling request object
        """
        return MCPSamplingRequest(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            stop_sequences=stop_sequences or [],
        )

    async def sample(
        self,
        request: MCPSamplingRequest,
    ) -> MCPSamplingResponse:
        """
        Execute a sampling request.

        Args:
            request: The sampling request

        Returns:
            Sampling response
        """
        # In real implementation, send to MCP server or local LLM
        response = await self.connection.send_request(
            "sampling/create",
            request.to_dict(),
        )

        return MCPSamplingResponse(
            content=response.get("result", {}).get("content", ""),
            model=request.model or "unknown",
            stop_reason="end",
            usage=response.get("result", {}).get("usage", {}),
        )

    # ========== Context Management ==========

    def set_context(self, key: str, value: Any) -> None:
        """Set a context value."""
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value."""
        return self._context.get(key, default)

    def clear_context(self) -> None:
        """Clear all context values."""
        self._context.clear()

    async def export_context(self) -> Dict[str, Any]:
        """Export current context."""
        return {
            "context": self._context.copy(),
            "resources": [r.to_dict() for r in self._resources.values()],
            "tools": [t.to_dict() for t in self._tools.values()],
            "prompts": [p.to_dict() for p in self._prompts.values()],
        }

    async def import_context(self, data: Dict[str, Any]) -> None:
        """Import context data."""
        self._context.update(data.get("context", {}))

    # ========== Utility Methods ==========

    def get_statistics(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        return {
            "connected": self.connection.connected,
            "session_id": self.connection.session_id,
            "resources_count": len(self._resources),
            "tools_count": len(self._tools),
            "prompts_count": len(self._prompts),
            "context_size": len(self._context),
        }

    # ========== Agent Integration ==========

    async def expose_agent_capabilities(
        self,
        agent_id: str,
        capabilities: Dict[str, Any],
    ) -> List[MCPTool]:
        """
        Expose agent capabilities as MCP tools.

        This allows external services to call agent methods via MCP.

        Args:
            agent_id: Agent identifier
            capabilities: Agent capabilities dict

        Returns:
            List of created tools
        """
        tools = []

        for skill_name, skill_info in capabilities.get("skills", {}).items():
            tool = self.register_tool(
                name=f"agent_{agent_id}_{skill_name}",
                description=skill_info.get("description", f"Agent {agent_id} skill: {skill_name}"),
                input_schema=skill_info.get("input_schema", {"type": "object"}),
                handler=lambda args, sn=skill_name: self._handle_agent_call(
                    agent_id, sn, args
                ),
                output_schema=skill_info.get("output_schema"),
                metadata={"agent_id": agent_id, "skill": skill_name},
            )
            tools.append(tool)

        return tools

    async def _handle_agent_call(
        self,
        agent_id: str,
        skill_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle a call to an agent skill."""
        # In real implementation, route to agent communication
        return {
            "agent_id": agent_id,
            "skill": skill_name,
            "arguments": arguments,
            "result": "Agent call processed",
        }


# ========== Standard MCP Tools ==========

def create_standard_tools() -> List[Dict[str, Any]]:
    """Create standard MCP tool definitions."""
    return [
        {
            "name": "read_file",
            "description": "Read content from a file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "encoding": {"type": "string", "default": "utf-8"},
                },
                "required": ["path"],
            },
        },
        {
            "name": "write_file",
            "description": "Write content to a file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "Content to write"},
                },
                "required": ["path", "content"],
            },
        },
        {
            "name": "execute_command",
            "description": "Execute a shell command",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"},
                    "timeout": {"type": "number", "default": 30},
                },
                "required": ["command"],
            },
        },
        {
            "name": "http_request",
            "description": "Make an HTTP request",
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Request URL"},
                    "method": {"type": "string", "default": "GET"},
                    "headers": {"type": "object"},
                    "body": {"type": "string"},
                },
                "required": ["url"],
            },
        },
    ]
