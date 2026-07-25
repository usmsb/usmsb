"""OpenAI adapter physical-call telemetry contract tests."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from typing import Any

import pytest

from usmsb_sdk.intelligence_adapters.base import (
    IntelligenceSourceConfig,
    IntelligenceSourceType,
)
from usmsb_sdk.intelligence_adapters.llm import openai_adapter as module
from usmsb_sdk.intelligence_adapters.llm.openai_adapter import OpenAIAdapter
from usmsb_sdk.llm_telemetry import (
    LLMBillingContext,
    LLMInvocationRecorder,
    LLMTraceContext,
    LLMUsage,
    llm_context_scope,
    platform_observation_context,
    resolve_llm_context,
)


class AsyncCreate:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class AsyncChunks:
    def __init__(self, chunks: list[Any]) -> None:
        self.chunks = chunks

    def __aiter__(self):
        return self

    async def __anext__(self) -> Any:
        if not self.chunks:
            raise StopAsyncIteration
        return self.chunks.pop(0)


class APITimeoutError(RuntimeError):
    """Named like the OpenAI retryable transport exception for the fake client."""


def usage(
    *,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int,
) -> Any:
    values = {"total_tokens": total_tokens}
    if prompt_tokens is not None:
        values["prompt_tokens"] = prompt_tokens
    if completion_tokens is not None:
        values["completion_tokens"] = completion_tokens
    return SimpleNamespace(**values)


def chat_response(content: str, *, response_id: str = "chat-1") -> Any:
    return SimpleNamespace(
        id=response_id,
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=usage(prompt_tokens=11, completion_tokens=4, total_tokens=15),
    )


def adapter_with_client(
    chat_outcomes: list[Any],
    *,
    embedding_outcomes: list[Any] | None = None,
) -> tuple[OpenAIAdapter, LLMInvocationRecorder, AsyncCreate, AsyncCreate]:
    recorder = LLMInvocationRecorder()
    adapter = OpenAIAdapter(
        IntelligenceSourceConfig(
            name="openai",
            type=IntelligenceSourceType.LLM,
            api_key="test-key",
            model="gpt-test",
            extra_params={"invocation_recorder": recorder},
        )
    )
    chat_create = AsyncCreate(chat_outcomes)
    embedding_create = AsyncCreate(embedding_outcomes or [])
    adapter._client = SimpleNamespace(
        chat=SimpleNamespace(completions=chat_create),
        embeddings=embedding_create,
    )
    return adapter, recorder, chat_create, embedding_create


def trace_and_billing() -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        {
            "trace_id": "trace-openai",
            "logical_call_id": "logical-openai",
            "source_service": "openai-test",
        },
        {
            "billing_task_id": "billing-openai",
            "task_scope_type": "agent_execution",
            "task_scope_id": "task-openai",
            "billing_user_id": "user-openai",
            "admission_status": "admitted",
        },
    )


def non_artifact_events(
    recorder: LLMInvocationRecorder,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Return lifecycle events without asynchronous artifact resolutions."""

    return [
        event
        for event in recorder.recent_events(limit=limit)
        if event["event_type"] != "llm.artifact.resolved"
    ]


async def wait_for_response_payload(
    recorder: LLMInvocationRecorder,
    *,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Wait for the observational artifact worker to update diagnostics."""

    deadline = time.monotonic() + timeout
    while True:
        call = recorder.recent_calls(limit=1)[0]
        if call["response_payload"] is not None:
            return call
        if time.monotonic() >= deadline:
            raise AssertionError("timed out waiting for asynchronous response artifact")
        await asyncio.sleep(0.005)


def test_platform_probe_context_cannot_inherit_user_billing_identity() -> None:
    user_context = LLMTraceContext(
        trace_id="user-trace",
        logical_call_id="user-call",
        session_id="user-session",
        conversation_id="user-conversation",
        billing=LLMBillingContext(
            principal_id="user-1",
            principal_type="user",
            billing_user_id="user-1",
            billing_task_id="user-task",
            task_scope_type="conversation_turn",
            task_scope_id="turn-1",
            admission_status="admitted",
        ),
    )
    with llm_context_scope(user_context):
        platform_context = platform_observation_context(
            provider="openai",
            operation="health_check.models.list",
            default=user_context,
        )
    resolved_again = resolve_llm_context(platform_context, default=user_context)

    assert resolved_again.billing is not None
    assert resolved_again.billing.principal_type == "platform"
    assert resolved_again.billing.billing_user_id is None
    assert resolved_again.billing.billing_task_id != "user-task"
    assert len(resolved_again.billing.billing_task_id or "") == 36
    assert platform_context.trace_id != "user-trace"
    assert platform_context.logical_call_id != "user-call"
    assert platform_context.session_id is None
    assert platform_context.conversation_id is None
    assert resolved_again.trace_id == platform_context.trace_id
    assert resolved_again.session_id is None
    assert resolved_again.conversation_id is None


@pytest.mark.asyncio
async def test_openai_sdk_hidden_retries_are_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class Models:
        async def list(self) -> list[Any]:
            return []

    class Client:
        models = Models()

    def client_factory(**kwargs: Any) -> Client:
        captured.update(kwargs)
        return Client()

    monkeypatch.setattr(module, "OPENAI_AVAILABLE", True)
    monkeypatch.setattr(module, "AsyncOpenAI", client_factory)
    adapter = OpenAIAdapter(
        IntelligenceSourceConfig(
            name="openai",
            type=IntelligenceSourceType.LLM,
            api_key="test-key",
            model="gpt-test",
            max_retries=4,
        )
    )

    assert await adapter.initialize() is True
    assert captured["max_retries"] == 0
    events = non_artifact_events(adapter.invocation_recorder)
    assert [event["event_type"] for event in events] == [
        "llm.provider.requested",
        "llm.provider.completed",
        "llm.task.completed",
    ]
    billing = events[0]["billing"]
    assert billing["principal_type"] == "platform"
    assert billing["task_scope_type"] == "logical_call"
    assert billing["admission_status"] == "bypassed_platform"
    assert events[-1]["billing"]["billing_task_id"] == billing["billing_task_id"]
    health_call = adapter.invocation_recorder.recent_calls(limit=1)[0]
    assert health_call["usage"]["total_tokens"] == 0
    assert health_call["usage"]["source"] == "provider_reported"


@pytest.mark.asyncio
async def test_all_non_streaming_openai_boundaries_emit_one_requested_and_terminal() -> None:
    trace_context, billing_context = trace_and_billing()
    adapter, recorder, _chat_create, _embedding_create = adapter_with_client(
        [
            chat_response("plain", response_id="generate"),
            chat_response("system", response_id="system"),
            chat_response(
                '{"intent":"ask","entities":[],"sentiment":"neutral",'
                '"urgency":"low","confidence":1}',
                response_id="intent",
            ),
            chat_response(
                '{"score":1,"reasoning":"ok","strengths":[],"weaknesses":[],'
                '"suggestions":[]}',
                response_id="evaluate",
            ),
        ],
        embedding_outcomes=[
            SimpleNamespace(
                id="embedding",
                data=[SimpleNamespace(embedding=[0.1, 0.2])],
                # OpenAI-compatible providers often expose only this field.
                usage=usage(total_tokens=9),
            )
        ],
    )

    common = {"trace_context": trace_context, "billing_context": billing_context}
    assert await adapter.generate_text("hello", **common) == "plain"
    assert await adapter.generate_with_system("system", "hello", **common) == "system"
    assert (await adapter.understand_intent("hello", **common))["intent"] == "ask"
    assert (await adapter.evaluate("item", "criteria", **common))["score"] == 1
    assert await adapter.embed("hello", **common) == [0.1, 0.2]

    calls = list(reversed(recorder.recent_calls(limit=10)))
    assert [call["operation"] for call in calls] == [
        "generate_text",
        "generate_with_system",
        "understand_intent",
        "evaluate",
        "embeddings.query",
    ]
    assert all(call["status"] == "completed" for call in calls)
    assert all(call["trace_context"]["trace_id"] == "trace-openai" for call in calls)
    assert all(
        call["trace_context"]["billing_context"]["billing_task_id"]
        == "billing-openai"
        for call in calls
    )
    assert calls[-1]["usage"]["input_tokens"] == 9
    assert calls[-1]["usage"]["output_tokens"] == 0
    assert [event["event_type"] for event in non_artifact_events(recorder)] == [
        event
        for _ in range(5)
        for event in ("llm.provider.requested", "llm.provider.completed")
    ]


@pytest.mark.asyncio
async def test_openai_failure_emits_exactly_one_failed_terminal() -> None:
    adapter, recorder, _chat_create, _embedding_create = adapter_with_client(
        [RuntimeError("provider unavailable")]
    )

    with pytest.raises(RuntimeError, match="provider unavailable"):
        await adapter.generate_text("hello")

    assert [event["event_type"] for event in non_artifact_events(recorder)] == [
        "llm.provider.requested",
        "llm.call.failed",
    ]
    call = recorder.recent_calls(limit=1)[0]
    assert call["status"] == "failed"
    assert call["error_message"] == "provider unavailable"


@pytest.mark.asyncio
async def test_openai_paid_creation_timeout_is_not_retried() -> None:
    adapter, recorder, chat_create, _embedding_create = adapter_with_client(
        [APITimeoutError("timeout"), chat_response("recovered")]
    )

    with pytest.raises(APITimeoutError, match="timeout"):
        await adapter.generate_text("hello")

    calls = list(reversed(recorder.recent_calls(limit=10)))
    assert [call["status"] for call in calls] == ["failed"]
    assert len(chat_create.calls) == 1
    assert [event["event_type"] for event in non_artifact_events(recorder)] == [
        "llm.provider.requested",
        "llm.call.failed",
    ]


@pytest.mark.asyncio
async def test_openai_embedding_timeout_is_not_retried() -> None:
    adapter, recorder, _chat_create, embedding_create = adapter_with_client(
        [],
        embedding_outcomes=[
            APITimeoutError("embedding timeout"),
            SimpleNamespace(data=[SimpleNamespace(embedding=[1.0])], usage=usage(total_tokens=1)),
        ],
    )

    with pytest.raises(APITimeoutError, match="embedding timeout"):
        await adapter.embed("hello")

    assert len(embedding_create.calls) == 1
    assert [event["event_type"] for event in non_artifact_events(recorder)] == [
        "llm.provider.requested",
        "llm.call.failed",
    ]


@pytest.mark.asyncio
async def test_openai_stream_creation_timeout_is_not_retried() -> None:
    adapter, recorder, chat_create, _embedding_create = adapter_with_client(
        [APITimeoutError("stream timeout"), AsyncChunks([])]
    )

    with pytest.raises(APITimeoutError, match="stream timeout"):
        _ = [chunk async for chunk in adapter.generate_stream("hello")]

    assert len(chat_create.calls) == 1
    assert [event["event_type"] for event in non_artifact_events(recorder)] == [
        "llm.provider.requested",
        "llm.call.failed",
    ]


@pytest.mark.asyncio
async def test_openai_stream_aggregates_response_and_usage_with_one_terminal() -> None:
    stream = AsyncChunks(
        [
            SimpleNamespace(
                id="stream-1",
                choices=[SimpleNamespace(delta=SimpleNamespace(content="你"))],
                usage=None,
            ),
            SimpleNamespace(
                id="stream-1",
                choices=[SimpleNamespace(delta=SimpleNamespace(content="好"))],
                usage=None,
            ),
            SimpleNamespace(
                id="stream-1",
                choices=[],
                usage=usage(prompt_tokens=7, completion_tokens=2, total_tokens=9),
            ),
        ]
    )
    adapter, recorder, chat_create, _embedding_create = adapter_with_client([stream])
    trace_context, billing_context = trace_and_billing()

    chunks = [
        chunk
        async for chunk in adapter.generate_stream(
            "hello",
            trace_context=trace_context,
            billing_context=billing_context,
        )
    ]

    assert chunks == ["你", "好"]
    assert chat_create.calls[0]["stream_options"] == {"include_usage": True}
    assert [event["event_type"] for event in non_artifact_events(recorder)] == [
        "llm.provider.requested",
        "llm.provider.completed",
    ]
    call = await wait_for_response_payload(recorder)
    assert call["response_payload"]["content"] == "你好"
    assert call["usage"]["input_tokens"] == 7
    assert call["usage"]["output_tokens"] == 2
    assert call["usage"]["total_tokens"] == 9


@pytest.mark.asyncio
async def test_openai_partially_consumed_stream_has_one_failed_terminal() -> None:
    stream = AsyncChunks(
        [
            SimpleNamespace(
                id="stream-partial",
                choices=[SimpleNamespace(delta=SimpleNamespace(content="partial"))],
                usage=None,
            ),
            SimpleNamespace(
                id="stream-partial",
                choices=[SimpleNamespace(delta=SimpleNamespace(content="unread"))],
                usage=None,
            ),
        ]
    )
    adapter, recorder, _chat_create, _embedding_create = adapter_with_client([stream])
    generator = adapter.generate_stream("hello")

    assert await anext(generator) == "partial"
    await generator.aclose()

    assert [event["event_type"] for event in non_artifact_events(recorder)] == [
        "llm.provider.requested",
        "llm.call.failed",
    ]
    call = await wait_for_response_payload(recorder)
    assert call["status"] == "failed"
    assert call["response_payload"]["content"] == "partial"


def test_total_only_embedding_usage_is_normalized_to_input() -> None:
    normalized = LLMUsage.from_embedding({"usage": {"total_tokens": 13}})

    assert normalized.input_tokens == 13
    assert normalized.output_tokens == 0
    assert normalized.total_tokens == 13
    assert normalized.source == "provider_reported"
