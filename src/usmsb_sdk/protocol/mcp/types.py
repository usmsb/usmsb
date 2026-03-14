"""
MCP Protocol Types

This module defines the types used in the Model Context Protocol.
"""

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class MCPMessageType(StrEnum):
    """MCP message types."""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"


class MCPResourceType(StrEnum):
    """Types of MCP resources."""
    TEXT = "text"
    BINARY = "binary"
    JSON = "json"
    FILE = "file"
    DATABASE = "database"
    API = "api"


class MCPToolStatus(StrEnum):
    """Status of tool execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class MCPResource:
    """An MCP resource that can be accessed."""
    uri: str
    name: str
    description: str
    resource_type: MCPResourceType
    mime_type: str = "text/plain"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "type": self.resource_type.value,
            "mimeType": self.mime_type,
            "metadata": self.metadata,
        }


@dataclass
class MCPTool:
    """An MCP tool that can be invoked."""
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema,
            "metadata": self.metadata,
        }


@dataclass
class MCPPrompt:
    """An MCP prompt template."""
    name: str
    description: str
    arguments: list[dict[str, Any]] = field(default_factory=list)
    template: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments,
            "template": self.template,
            "metadata": self.metadata,
        }


@dataclass
class MCPToolResult:
    """Result of a tool execution."""
    tool_name: str
    status: MCPToolStatus
    output: Any = None
    error: str | None = None
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "toolName": self.tool_name,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "executionTime": self.execution_time,
            "metadata": self.metadata,
        }


@dataclass
class MCPSamplingRequest:
    """Request for LLM sampling."""
    messages: list[dict[str, Any]]
    model: str | None = None
    max_tokens: int = 1000
    temperature: float = 0.7
    stop_sequences: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "messages": self.messages,
            "model": self.model,
            "maxTokens": self.max_tokens,
            "temperature": self.temperature,
            "stopSequences": self.stop_sequences,
            "metadata": self.metadata,
        }


@dataclass
class MCPSamplingResponse:
    """Response from LLM sampling."""
    content: str
    model: str
    stop_reason: str = "end"
    usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "stopReason": self.stop_reason,
            "usage": self.usage,
            "metadata": self.metadata,
        }


@dataclass
class MCPServerInfo:
    """Information about an MCP server."""
    name: str
    version: str
    protocol_version: str
    capabilities: dict[str, Any] = field(default_factory=dict)
    instructions: str = ""


@dataclass
class MCPToolCall:
    """MCP tool call request."""
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class MCPMessage:
    """MCP protocol message."""
    jsonrpc: str = "2.0"
    id: str | None = None
    method: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    result: Any | None = None
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            data["id"] = self.id
        if self.method is not None:
            data["method"] = self.method
        if self.params:
            data["params"] = self.params
        if self.result is not None:
            data["result"] = self.result
        if self.error is not None:
            data["error"] = self.error
        return data
