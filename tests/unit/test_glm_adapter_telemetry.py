"""GLM adapter physical HTTP-boundary telemetry tests."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import pytest

from usmsb_sdk.intelligence_adapters.base import (
    IntelligenceSourceConfig,
    IntelligenceSourceType,
)
from usmsb_sdk.intelligence_adapters.llm.glm_adapter import GLMAdapter
from usmsb_sdk.llm_telemetry import LLMInvocationRecorder


class FakeResponse:
    def __init__(
        self,
        payload: dict[str, Any] | None = None,
        *,
        status_code: int = 200,
        lines: list[str] | None = None,
    ) -> None:
        self.payload = payload or {}
        self.status_code = status_code
        self.text = json.dumps(self.payload)
        self.lines = list(lines or [])

    def json(self) -> dict[str, Any]:
        return self.payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            error = RuntimeError(f"HTTP {self.status_code}")
            error.status_code = self.status_code  # type: ignore[attr-defined]
            raise error

    async def aiter_lines(self):
        for line in self.lines:
            yield line


class StreamContext:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    async def __aenter__(self) -> FakeResponse:
        return self.response

    async def __aexit__(self, *_args: Any) -> None:
        return None


class FakeClient:
    def __init__(
        self,
        post_outcomes: list[Any],
        stream_outcomes: list[FakeResponse] | None = None,
    ) -> None:
        self.post_outcomes = list(post_outcomes)
        self.stream_outcomes = list(stream_outcomes or [])

    async def post(self, *_args: Any, **_kwargs: Any) -> FakeResponse:
        outcome = self.post_outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def stream(self, *_args: Any, **_kwargs: Any) -> StreamContext:
        return StreamContext(self.stream_outcomes.pop(0))


def chat_payload(content: str, *, response_id: str) -> dict[str, Any]:
    return {
        "id": response_id,
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 3, "total_tokens": 11},
    }


def make_adapter(
    post_outcomes: list[Any],
    *,
    stream_outcomes: list[FakeResponse] | None = None,
) -> tuple[GLMAdapter, LLMInvocationRecorder]:
    recorder = LLMInvocationRecorder()
    adapter = GLMAdapter(
        IntelligenceSourceConfig(
            name="glm",
            type=IntelligenceSourceType.LLM,
            api_key="test-key",
            model="glm-test",
            extra_params={"invocation_recorder": recorder},
        )
    )
    adapter._client = FakeClient(post_outcomes, stream_outcomes)  # type: ignore[assignment]
    return adapter, recorder


def call_context() -> dict[str, Any]:
    return {
        "trace_id": "glm-trace",
        "logical_call_id": "glm-logical",
        "billing": {
            "billing_task_id": "glm-billing",
            "task_scope_type": "agent_execution",
            "task_scope_id": "glm-task",
            "billing_user_id": "glm-user",
            "admission_status": "admitted",
        },
    }


def non_artifact_events(
    recorder: LLMInvocationRecorder,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
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
    deadline = time.monotonic() + timeout
    while True:
        call = recorder.recent_calls(limit=1)[0]
        if call["response_payload"] is not None:
            return call
        if time.monotonic() >= deadline:
            raise AssertionError("timed out waiting for asynchronous response artifact")
        await asyncio.sleep(0.005)


@pytest.mark.asyncio
async def test_every_non_streaming_glm_provider_boundary_is_recorded() -> None:
    adapter, recorder = make_adapter(
        [
            FakeResponse(chat_payload("ok", response_id="health")),
            FakeResponse(chat_payload("plain", response_id="generate")),
            FakeResponse(chat_payload("system", response_id="system")),
            FakeResponse(chat_payload('{"intent":"ask"}', response_id="intent")),
            FakeResponse(chat_payload('{"score":1}', response_id="evaluate")),
            FakeResponse(
                {
                    "id": "embedding",
                    "data": [{"embedding": [0.1, 0.2]}],
                    "usage": {"total_tokens": 12},
                }
            ),
            FakeResponse(
                {
                    "id": "function",
                    "choices": [
                        {"message": {"content": None, "tool_calls": [{"id": "tool-1"}]}}
                    ],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
                }
            ),
        ]
    )
    common = {"trace_context": call_context()}

    assert await adapter.is_available() is True
    health_events = non_artifact_events(recorder)
    assert [event["event_type"] for event in health_events] == [
        "llm.provider.requested",
        "llm.provider.completed",
        "llm.task.completed",
    ]
    assert health_events[0]["billing"]["principal_type"] == "platform"
    assert health_events[0]["billing"]["task_scope_type"] == "logical_call"
    assert health_events[0]["billing"]["admission_status"] == "bypassed_platform"
    assert await adapter.generate_text("hello", **common) == "plain"
    assert await adapter.generate_with_system("system", "hello", **common) == "system"
    assert (await adapter.understand_intent("hello", **common))["intent"] == "ask"
    assert (await adapter.evaluate("item", "criteria", **common))["score"] == 1
    assert await adapter.embed("hello", **common) == [0.1, 0.2]
    assert (await adapter.function_call("hello", [], **common))["tool_calls"] == [
        {"id": "tool-1"}
    ]

    calls = list(reversed(recorder.recent_calls(limit=20)))
    assert [call["operation"] for call in calls] == [
        "health_check.chat",
        "generate_text",
        "generate_with_system",
        "understand_intent",
        "evaluate",
        "embeddings.query",
        "function_call",
    ]
    assert all(call["status"] == "completed" for call in calls)
    assert calls[5]["usage"]["input_tokens"] == 12
    assert all(
        call["trace_context"]["billing_context"]["billing_task_id"] == "glm-billing"
        for call in calls[1:]
    )


@pytest.mark.asyncio
async def test_glm_stream_aggregates_final_usage_and_emits_one_terminal() -> None:
    lines = [
        'data: {"id":"glm-stream","choices":[{"delta":{"content":"你"}}]}',
        'data: {"id":"glm-stream","choices":[{"delta":{"content":"好"}}]}',
        'data: {"id":"glm-stream","choices":[],"usage":'
        '{"prompt_tokens":6,"completion_tokens":2,"total_tokens":8}}',
        "data: [DONE]",
    ]
    adapter, recorder = make_adapter([], stream_outcomes=[FakeResponse(lines=lines)])

    chunks = [
        chunk
        async for chunk in adapter.generate_stream(
            "hello",
            trace_context=call_context(),
        )
    ]

    assert chunks == ["你", "好"]
    assert [event["event_type"] for event in non_artifact_events(recorder)] == [
        "llm.provider.requested",
        "llm.provider.completed",
    ]
    call = await wait_for_response_payload(recorder)
    assert call["response_payload"]["content"] == "你好"
    assert call["usage"]["input_tokens"] == 6
    assert call["usage"]["output_tokens"] == 2


@pytest.mark.asyncio
async def test_glm_http_failure_has_exactly_one_failed_terminal() -> None:
    adapter, recorder = make_adapter([FakeResponse({"error": "busy"}, status_code=503)])

    with pytest.raises(RuntimeError, match="HTTP 503"):
        await adapter.generate_text("hello")

    assert [event["event_type"] for event in non_artifact_events(recorder)] == [
        "llm.provider.requested",
        "llm.call.failed",
    ]
    assert recorder.recent_calls(limit=1)[0]["http_status"] == 503
