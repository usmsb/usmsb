# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
# ToolAdapter - OpenHarness ToolRegistry Integration

"""
OpenHarness ToolAdapter for USMSB.

This adapter wraps the OpenHarness ToolRegistry to provide:
- 43+ built-in tools (file, shell, search, MCP)
- Tool discovery and capability matching
- Tool registration for USMSB custom tools
- Tool execution with permission checking
- Tool validation and schema generation

The adapter follows the Adapter Pattern to decouple USMSB from OH internals.

Usage:
    >>> adapter = ToolAdapter(registry=oh_registry, permission_checker=perm_checker)
    >>> result = await adapter.execute_tool("file_read", path="/tmp/test.txt")
    >>> tools = adapter.discover_tools(capability="file_operations")
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, TypeVar, Generic

from pydantic import BaseModel, ValidationError

try:
    from openharness.tools.tool import Tool as BaseTool
    from openharness.tools.read_file import ReadFileTool
    from openharness.tools.write_file import WriteFileTool
    from openharness.tools.search import SearchTool
    from openharness.tools.run_tests import RunTestsTool
    OPENHARNESS_AVAILABLE = True
except ImportError:
    OPENHARNESS_AVAILABLE = False
    # Stub for type hints when OH not installed
    BaseTool = None
    ReadFileTool = None
    WriteFileTool = None
    SearchTool = None
    RunTestsTool = None

from usmsb_sdk.adapters.openharness.exceptions import (
    ToolExecutionError,
    ConfigurationError,
    OpenHarnessNotAvailableError,
)

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass
class ToolMetadata:
    """Metadata for a tool registration."""
    name: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    category: str = "general"
    is_read_only: bool = False
    timeout_seconds: int = 300
    retryable: bool = True


@dataclass
class ToolExecutionResult:
    """Result of tool execution with USMSB-specific metadata."""
    output: str
    is_error: bool = False
    tool_name: str = ""
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolValidator:
    """
    Validates tool arguments against schema.
    
    This class provides argument validation before tool execution
    to provide better error messages and prevent invalid tool calls.
    """
    
    def __init__(self):
        self._validators: dict[str, Callable[[Any], bool]] = {}
    
    def register_validator(self, tool_name: str, validator: Callable[[Any], bool]) -> None:
        """Register a custom validator for a tool."""
        self._validators[tool_name] = validator
    
    def validate(self, tool_name: str, arguments: dict[str, Any], schema: dict) -> list[str]:
        """
        Validate arguments against schema.
        
        Returns:
            List of validation error messages. Empty list means valid.
        """
        errors = []
        
        # Check required fields
        required = schema.get("required", [])
        for field_name in required:
            if field_name not in arguments:
                errors.append(f"Missing required field: {field_name}")
        
        # Check field types
        properties = schema.get("properties", {})
        for field_name, field_value in arguments.items():
            if field_name in properties:
                expected_type = properties[field_name].get("type")
                if expected_type and not self._type_check(field_value, expected_type):
                    errors.append(
                        f"Field '{field_name}' has wrong type: "
                        f"expected {expected_type}, got {type(field_value).__name__}"
                    )
        
        # Custom validator
        if tool_name in self._validators:
            try:
                if not self._validators[tool_name](arguments):
                    errors.append(f"Custom validation failed for {tool_name}")
            except Exception as e:
                errors.append(f"Validator error: {e}")
        
        return errors
    
    def _type_check(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected JSON schema type."""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        expected = type_map.get(expected_type)
        if expected is None:
            return True  # Unknown type, skip check
        return isinstance(value, expected)


class ToolAdapter:
    """
    OpenHarness ToolRegistry Adapter.
    
    This adapter wraps the OH ToolRegistry to provide a unified
    interface for USMSB's tool usage. It handles:
    - Tool registration (OH tools and USMSB custom tools)
    - Tool execution with permission checking
    - Tool discovery and capability matching
    - Execution result normalization
    
    Attributes:
        registry: The underlying OH ToolRegistry instance
        permission_checker: PermissionChecker for access control
        cwd: Current working directory for tool execution
        validator: ToolValidator for argument validation
        _usmsb_tools: Cache of USMSB custom tool wrappers
        
    Example:
        >>> from openharness.permissions.checker import PermissionChecker
        >>> from openharness.tools.base import ToolRegistry
        >>> registry = ToolRegistry()
        >>> checker = PermissionChecker(settings)
        >>> adapter = ToolAdapter(registry=registry, permission_checker=checker)
        >>> result = await adapter.execute_tool("file_read", path="/tmp/test.txt")
    """

    def __init__(
        self,
        registry: ToolRegistry | None = None,
        permission_checker: Any = None,
        cwd: str | Path = ".",
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize ToolAdapter.
        
        Args:
            registry: OpenHarness ToolRegistry instance. If None, creates a new one.
            permission_checker: OH PermissionChecker instance.
            cwd: Current working directory for relative paths.
            config: Additional configuration options.
        """
        if not OPENHARNESS_AVAILABLE:
            raise OpenHarnessNotAvailableError()
        
        self._registry = registry or ToolRegistry()
        self._permission_checker = permission_checker
        self._cwd = Path(cwd).resolve()
        self._config = config or {}
        self._validator = ToolValidator()
        self._usmsb_tools: dict[str, Callable] = {}
        self._tool_metadata: dict[str, ToolMetadata] = {}
        self._execution_count: dict[str, int] = {}
        self._execution_times: dict[str, list[float]] = {}
        
        log.info("ToolAdapter initialized with %d registered tools", len(self._registry.list_tools()))

    @property
    def registry(self) -> ToolRegistry:
        """Return the underlying tool registry."""
        return self._registry

    @property
    def tool_count(self) -> int:
        """Return the number of registered tools."""
        return len(self._registry.list_tools())

    @property
    def tool_names(self) -> list[str]:
        """Return list of all registered tool names."""
        return [tool.name for tool in self._registry.list_tools()]

    def register_tool(
        self,
        tool: BaseTool | Callable,
        metadata: ToolMetadata | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Register a tool with the adapter.
        
        This method supports both OH BaseTool instances and
        plain Python callables (wrapped as SimpleTool).
        
        Args:
            tool: OH BaseTool instance or Python callable
            metadata: Optional metadata for the tool
            **kwargs: Additional tool configuration
            
        Example:
            >>> def my_tool(arg1: str) -> str:
            ...     return f"Hello {arg1}"
            >>> adapter.register_tool(my_tool, metadata=ToolMetadata(
            ...     name="my_tool",
            ...     description="A custom tool"
            ... ))
        """
        if isinstance(tool, BaseTool):
            self._registry.register(tool)
            if metadata:
                self._tool_metadata[tool.name] = metadata
            log.debug("Registered OH tool: %s", tool.name)
        else:
            # Wrap Python callable as OH tool
            wrapped = self._wrap_callable(tool, **kwargs)
            tool_name = kwargs.get("name", getattr(tool, "__name__", "unknown"))
            self._usmsb_tools[tool_name] = tool
            self._registry.register(wrapped)
            if metadata:
                self._tool_metadata[tool_name] = metadata
            log.debug("Registered USMSB tool wrapper: %s", tool_name)

    def _wrap_callable(self, func: Callable, **kwargs: Any) -> BaseTool:
        """
        Wrap a Python callable as an OH BaseTool.
        
        Args:
            func: The callable to wrap
            **kwargs: Tool configuration (name, description, etc.)
            
        Returns:
            A BaseTool instance wrapping the callable
        """
        tool_name = kwargs.get("name", getattr(func, "__name__", "unknown"))
        description = kwargs.get("description", f"Wrapped tool: {func.__name__}")
        
        class SimpleTool(BaseTool):
            name: str = tool_name
            description: str = description
            input_model: type[BaseModel] = kwargs.get(
                "input_model",
                self._create_input_model(func, kwargs)
            )
            
            async def execute(self, arguments: BaseModel, context: ToolExecutionContext) -> ToolResult:
                try:
                    # Convert Pydantic model to dict, excluding None values
                    args = arguments.model_dump(exclude_none=True)
                    # Execute the wrapped function
                    if asyncio.iscoroutinefunction(func):
                        result = await func(**args)
                    else:
                        result = func(**args)
                    return ToolResult(output=str(result) if result is not None else "")
                except Exception as e:
                    return ToolResult(output=str(e), is_error=True)
            
            def is_read_only(self, arguments: BaseModel) -> bool:
                return kwargs.get("is_read_only", False)
        
        return SimpleTool()

    def _create_input_model(self, func: Callable, kwargs: dict) -> type[BaseModel]:
        """Create a Pydantic input model from function signature."""
        import inspect
        
        sig = inspect.signature(func)
        fields = {}
        annotations = sig.parameters
        
        for param_name, param in annotations.items():
            if param.annotation is inspect.Parameter.empty:
                field_type = str
            else:
                field_type = param.annotation
            
            default = ...  # Required by default
            if param.default is not inspect.Parameter.empty:
                default = param.default
            
            fields[param_name] = (field_type, default)
        
        return type("InputModel", (BaseModel,), fields)

    async def execute_tool(
        self,
        tool_name: str,
        check_permission: bool = True,
        **kwargs: Any,
    ) -> ToolExecutionResult:
        """
        Execute a tool by name with the given arguments.
        
        This method:
        1. Validates arguments against tool schema
        2. Checks permissions via PermissionChecker
        3. Executes the tool with timeout
        4. Returns normalized result
        
        Args:
            tool_name: Name of the tool to execute
            check_permission: Whether to check permissions before execution
            **kwargs: Tool arguments
            
        Returns:
            ToolExecutionResult with output and metadata
            
        Raises:
            ToolExecutionError: If tool execution fails
            PermissionDeniedError: If permission check fails
        """
        import time
        start_time = time.time()
        
        # Get tool from registry
        tool = self._registry.get(tool_name)
        if not tool:
            raise ToolExecutionError(
                tool_name=tool_name,
                message=f"Tool not found in registry. Available: {self.tool_names}",
            )
        
        # Validate arguments
        schema = tool.to_api_schema().get("input_schema", {})
        validation_errors = self._validator.validate(tool_name, kwargs, schema)
        if validation_errors:
            raise ToolExecutionError(
                tool_name=tool_name,
                message=f"Argument validation failed: {', '.join(validation_errors)}",
            )
        
        # Check permission
        if check_permission and self._permission_checker:
            decision = self._permission_checker.evaluate(
                tool_name=tool_name,
                is_read_only=tool.is_read_only,
                file_path=kwargs.get("path") or kwargs.get("file_path"),
                command=kwargs.get("command"),
            )
            if not decision.allowed:
                from usmsb_sdk.adapters.openharness.exceptions import PermissionDeniedError
                raise PermissionDeniedError(
                    tool_name=tool_name,
                    reason=decision.reason,
                    requires_confirmation=decision.requires_confirmation,
                )
        
        # Build execution context
        context = ToolExecutionContext(
            cwd=self._cwd,
            metadata={
                "tool_name": tool_name,
                "usmsb_adapter": True,
            },
        )
        
        # Build input model
        try:
            input_model = tool.input_model(**kwargs)
        except ValidationError as e:
            raise ToolExecutionError(
                tool_name=tool_name,
                message=f"Argument validation error: {e}",
            )
        
        # Execute with timeout
        timeout = self._tool_metadata.get(tool_name)
        timeout_seconds = timeout.timeout_seconds if timeout else 300
        
        try:
            if asyncio.iscoroutinefunction(tool.execute):
                result = await asyncio.wait_for(
                    tool.execute(input_model, context),
                    timeout=timeout_seconds,
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: tool.execute(input_model, context)
                    ),
                    timeout=timeout_seconds,
                )
        except asyncio.TimeoutError:
            raise ToolExecutionError(
                tool_name=tool_name,
                message=f"Tool execution timed out after {timeout_seconds}s",
            )
        except Exception as e:
            raise ToolExecutionError(
                tool_name=tool_name,
                message=f"Tool execution failed: {e}",
            )
        
        # Track execution stats
        execution_time = (time.time() - start_time) * 1000
        self._execution_count[tool_name] = self._execution_count.get(tool_name, 0) + 1
        self._execution_times.setdefault(tool_name, []).append(execution_time)
        
        return ToolExecutionResult(
            output=result.output,
            is_error=result.is_error,
            tool_name=tool_name,
            execution_time_ms=execution_time,
            metadata=result.metadata,
        )

    def discover_tools(
        self,
        capability: str | None = None,
        category: str | None = None,
        read_only: bool | None = None,
        pattern: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Discover tools matching given criteria.
        
        Args:
            capability: Filter by capability tag (e.g., "file_operations")
            category: Filter by category
            read_only: Filter by read-only flag
            pattern: Glob pattern to match tool names
            
        Returns:
            List of tool info dicts with name, description, capabilities
        """
        tools = []
        for tool in self._registry.list_tools():
            # Pattern filter
            if pattern and not fnmatch.fnmatch(tool.name, pattern):
                continue
            
            # Capability filter
            metadata = self._tool_metadata.get(tool.name)
            if capability and metadata:
                if capability not in metadata.capabilities:
                    continue
            
            # Category filter
            if category and metadata:
                if metadata.category != category:
                    continue
            
            # Read-only filter
            if read_only is not None and metadata:
                if metadata.is_read_only != read_only:
                    continue
            
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "capabilities": metadata.capabilities if metadata else [],
                "category": metadata.category if metadata else "general",
                "is_read_only": metadata.is_read_only if metadata else False,
                "schema": tool.to_api_schema(),
                "execution_count": self._execution_count.get(tool.name, 0),
                "avg_execution_time_ms": (
                    sum(self._execution_times.get(tool.name, [])) /
                    max(len(self._execution_times.get(tool.name, [])), 1)
                ),
            })
        
        return tools

    def get_tool_info(self, tool_name: str) -> dict[str, Any] | None:
        """
        Get detailed information about a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool info dict or None if not found
        """
        tool = self._registry.get(tool_name)
        if not tool:
            return None
        
        metadata = self._tool_metadata.get(tool_name)
        return {
            "name": tool.name,
            "description": tool.description,
            "capabilities": metadata.capabilities if metadata else [],
            "category": metadata.category if metadata else "general",
            "is_read_only": metadata.is_read_only if metadata else False,
            "schema": tool.to_api_schema(),
            "execution_count": self._execution_count.get(tool_name, 0),
            "avg_execution_time_ms": (
                sum(self._execution_times.get(tool_name, [])) /
                max(len(self._execution_times.get(tool_name, [])), 1)
            ),
        }

    def to_api_schema(self) -> list[dict[str, Any]]:
        """
        Export all tools in Anthropic-compatible API schema format.
        
        Returns:
            List of tool schemas for API calls
        """
        return self._registry.to_api_schema()

    def get_statistics(self) -> dict[str, Any]:
        """
        Get tool execution statistics.
        
        Returns:
            Dict with execution counts, times, and tool metrics
        """
        return {
            "total_tools": len(self._registry.list_tools()),
            "usmsb_custom_tools": len(self._usmsb_tools),
            "execution_counts": dict(self._execution_count),
            "execution_times": {
                name: {
                    "count": len(times),
                    "total_ms": sum(times),
                    "avg_ms": sum(times) / max(len(times), 1),
                    "min_ms": min(times) if times else 0,
                    "max_ms": max(times) if times else 0,
                }
                for name, times in self._execution_times.items()
            },
        }
