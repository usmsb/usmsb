# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
# QueryAdapter - OpenHarness QueryEngine Integration

"""
OpenHarness QueryAdapter for USMSB.

This adapter wraps the OpenHarness QueryEngine to provide:
- LLM query execution with streaming
- Tool-aware model loop
- Cost tracking and budgeting
- System prompt management
- Context window management

The adapter integrates USMSB's L3 (Goal Layer) with OH's
query engine for LLM-based reasoning.

Usage:
    >>> adapter = QueryAdapter(engine=oh_engine)
    >>> async for event in adapter.query("What is the capital of France?"):
    ...     print(event)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

try:
    from openharness.engine.query_engine import QueryEngine
    from openharness.engine.messages import ConversationMessage, TextBlock, ToolResultBlock
    from openharness.engine.stream_events import (
        AssistantTextDelta,
        AssistantTurnComplete,
        CompactProgressEvent,
        ErrorEvent,
        StatusEvent,
        StreamEvent as OHStreamEvent,
        ToolExecutionCompleted,
        ToolExecutionStarted,
    )
    from openharness.api.client import (
        ApiMessageRequest,
        ApiStreamEvent,
        ApiTextDeltaEvent,
        ApiMessageCompleteEvent,
        ApiRetryEvent,
        SupportsStreamingMessages,
    )
    from openharness.api.usage import UsageSnapshot
    OPENHARNESS_AVAILABLE = True
except ImportError:
    OPENHARNESS_AVAILABLE = False
    QueryEngine = None
    ConversationMessage = None
    StreamEvent = None

from usmsb_sdk.adapters.openharness.config import LLMConfig
from usmsb_sdk.adapters.openharness.exceptions import (
    QueryError,
    OpenHarnessNotAvailableError,
)
from usmsb_sdk.llm_telemetry import (
    LLMEventCallback,
    LLMInvocationRecorder,
    LLMTraceContext,
    llm_context_scope,
    resolve_llm_context,
)
from usmsb_sdk.openharness_telemetry import (
    OpenHarnessPhysicalTelemetryClient,
    OpenHarnessTelemetryContractError,
    install_openharness_physical_telemetry,
)

log = logging.getLogger(__name__)


@dataclass
class CostSummary:
    """
    Summary of LLM costs.
    
    Attributes:
        total_tokens: Total tokens used
        prompt_tokens: Tokens in prompts
        completion_tokens: Tokens in completions
        total_cost: Estimated cost in USD
        model: Model used
    """
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_tokens": self.total_tokens,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_cost": self.total_cost,
            "model": self.model,
        }


@dataclass
class QueryResult:
    """
    Result of a query execution.
    
    Attributes:
        message: Final assistant message
        usage: Token usage snapshot
        stop_reason: Why generation stopped
        tool_calls: List of tool calls made during query
        total_turns: Number of agent turns
    """
    message: str
    usage: CostSummary | None = None
    stop_reason: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    total_turns: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamEvent:
    """
    A streaming event from query execution.
    
    Event types:
    - text: Incremental text delta
    - tool_call: Tool call started
    - tool_result: Tool call completed
    - turn_complete: Agent turn finished
    - message_complete: Query finished
    - retry: Retry attempt
    """
    event_type: str
    data: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


class QueryAdapter:
    """
    OpenHarness QueryEngine Adapter.
    
    This adapter wraps OH's QueryEngine to provide:
    - Async streaming query execution
    - Tool integration with permission checking
    - Cost tracking
    - Context management
    - System prompt injection
    
    The adapter is used by USMSB's Goal Layer to execute
    LLM queries with tool access.
    
    Example:
        >>> from openharness.engine.query_engine import QueryEngine
        >>> from openharness.tools.base import ToolRegistry
        >>> 
        >>> engine = QueryEngine(
        ...     api_client=client,
        ...     tool_registry=registry,
        ...     permission_checker=checker,
        ...     model="minimax-m1",
        ...     system_prompt="You are a helpful assistant.",
        ... )
        >>> 
        >>> adapter = QueryAdapter(engine=engine)
        >>> 
        >>> # Streaming query
        >>> async for event in adapter.query("What is 2+2?"):
        ...     print(event.data, end="")
        >>> 
        >>> # Non-streaming query
        >>> result = await adapter.query_complete("What is 2+2?")
        >>> print(result.message)
    """

    def __init__(
        self,
        engine: QueryEngine | None = None,
        config: LLMConfig | None = None,
        cwd: str | Path = ".",
        invocation_recorder: LLMInvocationRecorder | None = None,
        llm_event_callback: LLMEventCallback | None = None,
        default_context: LLMTraceContext | dict[str, Any] | None = None,
    ):
        """
        Initialize QueryAdapter.
        
        Args:
            engine: OH QueryEngine instance
            config: LLM configuration
            cwd: Current working directory
        """
        if not OPENHARNESS_AVAILABLE:
            raise OpenHarnessNotAvailableError()
        
        self._engine = engine
        self._config = config or LLMConfig()
        self._cwd = Path(cwd).resolve()
        self.invocation_recorder = invocation_recorder or LLMInvocationRecorder(
            event_callback=llm_event_callback,
            default_context=default_context,
        )
        if invocation_recorder and llm_event_callback:
            self.invocation_recorder.add_callback(llm_event_callback)
        if invocation_recorder and default_context is not None:
            self.invocation_recorder.set_default_context(default_context)
        self._physical_telemetry_client: OpenHarnessPhysicalTelemetryClient | None = None
        
        # Cost tracking
        self._total_usage: UsageSnapshot | None = None
        self._query_count: int = 0
        self._turn_count: int = 0
        
        # Message history (for non-streaming convenience)
        self._message_history: list[ConversationMessage] = []

        if self._engine is not None:
            self._ensure_physical_telemetry()
        
        log.info("QueryAdapter initialized with model: %s", self._config.model)

    def _ensure_physical_telemetry(self) -> OpenHarnessPhysicalTelemetryClient:
        """Install verified provider-boundary telemetry or reject before sending."""

        if self._engine is None:
            raise QueryError(message="QueryEngine not initialized", model=self._config.model)
        try:
            self._physical_telemetry_client = install_openharness_physical_telemetry(
                self._engine,
                invocation_recorder=self.invocation_recorder,
                provider=str(getattr(self._config.provider, "value", self._config.provider)),
            )
        except OpenHarnessTelemetryContractError as error:
            raise QueryError(
                message=str(error),
                model=self._config.model,
                details={
                    "telemetry_status": "fail_closed",
                    "billing_eligible": False,
                    "provider_request_sent": False,
                },
            ) from error
        return self._physical_telemetry_client

    def _root_context(
        self,
        *,
        operation: str,
        trace_context: LLMTraceContext | dict[str, Any] | None,
        billing_context: dict[str, Any] | None,
    ) -> LLMTraceContext:
        root = resolve_llm_context(
            trace_context,
            default=self.invocation_recorder.default_context,
        )
        if billing_context:
            root = root.with_updates(billing=billing_context)
        return root.for_logical_call(operation=operation)

    @property
    def engine(self) -> QueryEngine:
        """Return the underlying query engine."""
        if self._engine is None:
            raise QueryError(
                message="QueryEngine not initialized. Pass engine to constructor or set via set_engine().",
            )
        return self._engine

    @property
    def model(self) -> str:
        """Return current model."""
        return self._config.model

    @property
    def total_usage(self) -> CostSummary:
        """Return total cost summary."""
        if self._total_usage:
            return CostSummary(
                total_tokens=self._total_usage.total_tokens,
                prompt_tokens=self._total_usage.input_tokens,
                completion_tokens=self._total_usage.output_tokens,
                total_cost=self._estimate_cost(self._total_usage),
                model=self._config.model,
            )
        return CostSummary(model=self._config.model)

    async def set_engine(self, engine: QueryEngine) -> None:
        """
        Set or update the query engine.
        
        Args:
            engine: OH QueryEngine instance
        """
        self._engine = engine
        self._ensure_physical_telemetry()

    def set_model(self, model: str) -> None:
        """
        Change the LLM model.
        
        Args:
            model: New model identifier
        """
        self._config.model = model
        if self._engine:
            self._engine.set_model(model)
        log.info("Model changed to: %s", model)

    def set_system_prompt(self, prompt: str) -> None:
        """
        Update the system prompt.
        
        Args:
            prompt: New system prompt
        """
        if self._engine:
            self._engine.set_system_prompt(prompt)
        log.debug("System prompt updated")

    def set_max_turns(self, max_turns: int | None) -> None:
        """
        Set maximum agent turns per query.
        
        Args:
            max_turns: Max turns, or None for unlimited
        """
        if self._engine:
            self._engine.set_max_turns(max_turns)
        log.debug("Max turns set to: %s", max_turns)

    async def query(
        self,
        prompt: str,
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        stream: bool = True,
        max_turns: int | None = None,
        message_history: list[ConversationMessage] | None = None,
        trace_context: LLMTraceContext | dict[str, Any] | None = None,
        billing_context: dict[str, Any] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """
        Execute a query with optional streaming.
        
        This method:
        1. Builds conversation message
        2. Injects system prompt if provided
        3. Submits to QueryEngine
        4. Yields streaming events
        
        Args:
            prompt: User prompt
            system_prompt: Override system prompt
            tools: Additional tools to make available
            stream: Whether to yield streaming events
            max_turns: Override max turns
            message_history: Previous messages for context
            
        Yields:
            StreamEvent objects
            
        Raises:
            QueryError: If query execution fails
        """
        if self._engine is None:
            raise QueryError(message="QueryEngine not initialized")

        # Re-check before every execution in case another component replaced the
        # engine's API client after initialization.  Unsupported clients are
        # rejected before ``submit_message`` can send a paid provider request.
        self._ensure_physical_telemetry()
        original_max_turns = self._engine.max_turns

        try:
            # Build message
            user_message = ConversationMessage.from_user_text(prompt)
            
            # A supplied history is canonical for this invocation.  Merely
            # assigning it to a local variable (the former behaviour) silently
            # discarded restored context after a process restart.
            if message_history is not None:
                self._message_history = list(message_history)
                self._engine.load_messages(self._message_history)
            
            # Inject system prompt if different from engine's
            if system_prompt:
                self._engine.set_system_prompt(system_prompt)
            
            # Override max turns if provided
            if max_turns is not None:
                self._engine.set_max_turns(max_turns)
            
            # Track state
            current_turn = 0
            final_message = None
            tool_calls = []
            
            root_context = self._root_context(
                operation="openharness.query",
                trace_context=trace_context,
                billing_context=billing_context,
            )
            with llm_context_scope(root_context):
                async for event in self._engine.submit_message(user_message):
                    stream_event = self._convert_event(
                        event,
                        current_turn=current_turn,
                    )

                    if stream_event:
                        # Track turn completion
                        if stream_event.event_type in {"turn_complete", "message_complete"}:
                            current_turn += 1

                        # Track final message
                        if stream_event.event_type == "message_complete":
                            final_message = stream_event.data

                        # Track tool calls
                        if stream_event.event_type == "tool_call":
                            tool_calls.append(stream_event.data)

                        yield stream_event
            
            # Update state
            self._query_count += 1
            self._turn_count += current_turn
            
            if self._engine.total_usage:
                self._total_usage = self._engine.total_usage
            
            # Add to message history
            self._message_history.append(user_message)
            if final_message:
                self._message_history.append(final_message)
            
        except QueryError:
            raise
        except Exception as e:
            raise QueryError(
                message=f"Query execution failed: {e}",
                model=self._config.model,
            )
        finally:
            # A failed provider/tool turn must not leak a one-call override into
            # the next resumed loop.
            if max_turns is not None:
                self._engine.set_max_turns(original_max_turns)

    async def query_complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        max_turns: int | None = None,
        trace_context: LLMTraceContext | dict[str, Any] | None = None,
        billing_context: dict[str, Any] | None = None,
    ) -> QueryResult:
        """
        Execute a query and return complete result.
        
        This is a convenience method that collects all streaming
        events and returns the final result.
        
        Args:
            prompt: User prompt
            system_prompt: Override system prompt
            tools: Additional tools
            max_turns: Max turns
            
        Returns:
            QueryResult with final message and metadata
        """
        message_parts = []
        tool_calls = []
        total_turns = 0
        final_message = None
        usage = None
        stop_reason = None
        
        async for event in self.query(
            prompt=prompt,
            system_prompt=system_prompt,
            tools=tools,
            max_turns=max_turns,
            trace_context=trace_context,
            billing_context=billing_context,
        ):
            if event.event_type == "text":
                message_parts.append(event.data)
            elif event.event_type == "tool_call":
                tool_calls.append(event.data)
            elif event.event_type == "turn_complete":
                total_turns += 1
            elif event.event_type == "message_complete":
                final_message = event.data
                usage = event.metadata.get("usage")
                stop_reason = event.metadata.get("stop_reason")
                total_turns += 1
        
        return QueryResult(
            message="".join(message_parts),
            usage=usage,
            stop_reason=stop_reason,
            tool_calls=tool_calls,
            total_turns=total_turns,
        )

    def _convert_event(
        self,
        event: Any,
        current_turn: int,
    ) -> StreamEvent | None:
        """Convert OH stream event to USMSB StreamEvent."""
        if isinstance(event, AssistantTextDelta):
            return StreamEvent(
                event_type="text",
                data=event.text,
            )

        if isinstance(event, AssistantTurnComplete):
            msg = event.message
            return StreamEvent(
                event_type="message_complete",
                data=msg,
                metadata={
                    "usage": self._to_cost_summary(event.usage),
                    "turn": current_turn + 1,
                    "stop_reason": event.stop_reason,
                },
            )

        if isinstance(event, ToolExecutionStarted):
            return StreamEvent(
                event_type="tool_call",
                data={"tool_name": event.tool_name, "tool_input": event.tool_input},
            )

        if isinstance(event, ToolExecutionCompleted):
            return StreamEvent(
                event_type="tool_result",
                data={
                    "tool_name": event.tool_name,
                    "output": event.output,
                    "is_error": event.is_error,
                },
            )

        if isinstance(event, CompactProgressEvent):
            return StreamEvent(
                event_type="compact",
                data={
                    "phase": event.phase,
                    "trigger": event.trigger,
                    "checkpoint": event.checkpoint,
                    "message": event.message,
                },
                metadata=event.metadata or {},
            )

        if isinstance(event, StatusEvent):
            return StreamEvent(event_type="status", data=event.message)

        if isinstance(event, ErrorEvent):
            return StreamEvent(
                event_type="error",
                data=event.message,
                metadata={"recoverable": event.recoverable},
            )

        return None

    def _to_cost_summary(self, usage: UsageSnapshot | None) -> CostSummary | None:
        """Convert OH UsageSnapshot to CostSummary."""
        if not usage:
            return None
        
        return CostSummary(
            total_tokens=usage.total_tokens,
            prompt_tokens=usage.input_tokens,
            completion_tokens=usage.output_tokens,
            total_cost=self._estimate_cost(usage),
            model=self._config.model,
        )

    def _estimate_cost(self, usage: UsageSnapshot) -> float:
        """
        Estimate cost in USD based on token usage.
        
        Pricing is approximate and varies by provider.
        """
        # Approximate pricing (USD per 1M tokens)
        pricing = {
            "minimax-m1": {"prompt": 0.5, "completion": 1.5},
            "gpt-4o": {"prompt": 5.0, "completion": 15.0},
            "gpt-4o-mini": {"prompt": 0.15, "completion": 0.6},
            "claude-3-5-sonnet": {"prompt": 3.0, "completion": 15.0},
            "claude-3-5-haiku": {"prompt": 0.8, "completion": 4.0},
        }
        
        rates = pricing.get(self._config.model, {"prompt": 1.0, "completion": 3.0})
        
        prompt_cost = (usage.input_tokens / 1_000_000) * rates["prompt"]
        completion_cost = (usage.output_tokens / 1_000_000) * rates["completion"]
        
        return prompt_cost + completion_cost

    def get_message_history(self) -> list[ConversationMessage]:
        """Get current message history."""
        return list(self._message_history)

    def load_message_history(self, messages: list[ConversationMessage]) -> None:
        """Load message history into the adapter."""
        self._message_history = list(messages)
        if self._engine:
            self._engine.load_messages(self._message_history)

    def clear_message_history(self) -> None:
        """Clear message history."""
        self._message_history.clear()
        if self._engine:
            self._engine.clear()

    def has_pending_continuation(self) -> bool:
        """Check if there's a pending continuation."""
        if self._engine:
            return self._engine.has_pending_continuation()
        return False

    async def continue_pending(
        self,
        max_turns: int | None = None,
        trace_context: LLMTraceContext | dict[str, Any] | None = None,
        billing_context: dict[str, Any] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """
        Continue an interrupted tool loop.
        
        Args:
            max_turns: Override max turns
            
        Yields:
            StreamEvent objects
        """
        if self._engine is None:
            raise QueryError(message="QueryEngine not initialized")

        self._ensure_physical_telemetry()
        
        current_turn = self._turn_count
        
        root_context = self._root_context(
            operation="openharness.continue_pending",
            trace_context=trace_context,
            billing_context=billing_context,
        )
        with llm_context_scope(root_context):
            async for event in self._engine.continue_pending(max_turns=max_turns):
                stream_event = self._convert_event(event, current_turn=current_turn)
                if stream_event:
                    yield stream_event

    def get_llm_call_details(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """Return physical provider attempts captured by this adapter."""

        return self.invocation_recorder.recent_calls(limit=limit)

    def get_llm_events(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """Return provider-attempt lifecycle events captured by this adapter."""

        return self.invocation_recorder.recent_events(limit=limit)

    def get_statistics(self) -> dict[str, Any]:
        """Get query statistics."""
        return {
            "query_count": self._query_count,
            "total_turns": self._turn_count,
            "avg_turns_per_query": (
                self._turn_count / self._query_count if self._query_count > 0 else 0
            ),
            "current_model": self._config.model,
            "message_history_size": len(self._message_history),
            "total_usage": self.total_usage.to_dict() if self.total_usage else {},
        }
