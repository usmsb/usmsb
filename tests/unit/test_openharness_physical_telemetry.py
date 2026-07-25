"""Fail-closed tests for OpenHarness provider send-boundary telemetry."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from usmsb_sdk.llm_telemetry import (
    LLMInvocationRecorder,
    LLMTraceContext,
    llm_context_scope,
)
from usmsb_sdk.openharness_telemetry import (
    OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT,
    OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT_ATTR,
    OpenHarnessPhysicalTelemetryClient,
    OpenHarnessTelemetryContractError,
    install_openharness_physical_telemetry,
)


def make_context() -> LLMTraceContext:
    return LLMTraceContext(
        trace_id="trace-openharness",
        source_service="usmsb-test",
        agent_id="agent-openharness",
    )


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


@dataclass
class FakeRequest:
    model: str
    messages: list[dict[str, str]]


@dataclass
class FakeTextEvent:
    text: str


@dataclass
class FakeRetryEvent:
    message: str
    attempt: int
    max_attempts: int
    delay_seconds: float


@dataclass
class FakeCompleteEvent:
    message: dict[str, str]
    usage: Any
    stop_reason: str = "end_turn"


class AuditedRetryThenSuccessClient:
    physical_call_count = 0

    async def stream_message(self, _request: FakeRequest) -> AsyncIterator[Any]:
        self.physical_call_count += 1
        yield FakeTextEvent("partial")
        yield FakeRetryEvent("temporary upstream failure", 1, 2, 0.0)
        self.physical_call_count += 1
        yield FakeTextEvent("done")
        yield FakeCompleteEvent(
            message={"role": "assistant", "content": "done"},
            usage=SimpleNamespace(input_tokens=8, output_tokens=2, total_tokens=10),
        )


setattr(
    AuditedRetryThenSuccessClient,
    OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT_ATTR,
    OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT,
)


class FakeEngine:
    def __init__(self, api_client: Any):
        self.api_client = api_client
        self.set_calls = 0

    def set_api_client(self, api_client: Any) -> None:
        self.set_calls += 1
        self.api_client = api_client


@pytest.mark.asyncio
async def test_openharness_wrapper_blocks_retry_before_second_physical_attempt() -> None:
    recorder = LLMInvocationRecorder(default_context=make_context())
    delegate = AuditedRetryThenSuccessClient()
    engine = FakeEngine(delegate)
    wrapper = install_openharness_physical_telemetry(
        engine,
        invocation_recorder=recorder,
        provider="minimax",
    )

    root_context = make_context().for_logical_call(operation="openharness.query")
    with llm_context_scope(root_context):
        with pytest.raises(OpenHarnessTelemetryContractError, match="single-shot"):
            _ = [
                event
                async for event in wrapper.stream_message(
                    FakeRequest(
                        model="minimax-m1",
                        messages=[{"role": "user", "content": "hi"}],
                    )
                )
            ]

    assert engine.set_calls == 1
    assert engine.api_client is wrapper
    assert delegate.physical_call_count == 1
    calls = list(reversed(recorder.recent_calls(limit=10)))
    assert [call["status"] for call in calls] == ["failed"]
    assert len({call["provider_attempt_id"] for call in calls}) == 1
    assert len({call["trace_context"]["logical_call_id"] for call in calls}) == 1
    assert calls[0]["trace_context"]["parent_logical_call_id"] == root_context.logical_call_id
    assert [event["event_type"] for event in non_artifact_events(recorder)] == [
        "llm.provider.requested",
        "llm.call.failed",
    ]


@pytest.mark.asyncio
async def test_openharness_wrapper_records_one_successful_physical_attempt() -> None:
    class AuditedSuccessClient:
        physical_call_count = 0

        async def stream_message(self, _request: FakeRequest) -> AsyncIterator[Any]:
            self.physical_call_count += 1
            yield FakeTextEvent("done")
            yield FakeCompleteEvent(
                message={"role": "assistant", "content": "done"},
                usage=SimpleNamespace(input_tokens=8, output_tokens=2, total_tokens=10),
            )

    setattr(
        AuditedSuccessClient,
        OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT_ATTR,
        OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT,
    )
    recorder = LLMInvocationRecorder(default_context=make_context())
    delegate = AuditedSuccessClient()
    wrapper = OpenHarnessPhysicalTelemetryClient(
        delegate,
        invocation_recorder=recorder,
        provider="minimax",
    )

    events = [
        event
        async for event in wrapper.stream_message(
            FakeRequest(model="minimax-m1", messages=[])
        )
    ]

    assert delegate.physical_call_count == 1
    assert len(events) == 2
    calls = recorder.recent_calls(limit=10)
    assert len(calls) == 1
    assert calls[0]["status"] == "completed"
    assert calls[0]["usage"]["input_tokens"] == 8
    assert calls[0]["usage"]["output_tokens"] == 2
    assert [event["event_type"] for event in non_artifact_events(recorder)] == [
        "llm.provider.requested",
        "llm.provider.completed",
    ]


def test_openharness_unverified_client_is_rejected_before_provider_send() -> None:
    class UnverifiedClient:
        call_count = 0

        async def stream_message(self, _request: FakeRequest) -> AsyncIterator[Any]:
            self.call_count += 1
            yield FakeCompleteEvent(message={}, usage={})

    recorder = LLMInvocationRecorder(default_context=make_context())
    delegate = UnverifiedClient()
    engine = FakeEngine(delegate)

    with pytest.raises(OpenHarnessTelemetryContractError, match="hidden SDK retries disabled"):
        install_openharness_physical_telemetry(
            engine,
            invocation_recorder=recorder,
            provider="minimax",
        )

    assert engine.set_calls == 0
    assert engine.api_client is delegate
    assert delegate.call_count == 0
    assert recorder.recent_calls(limit=10) == []


@pytest.mark.asyncio
async def test_openharness_stream_without_terminal_event_fails_closed() -> None:
    class IncompleteClient:
        async def stream_message(self, _request: FakeRequest) -> AsyncIterator[Any]:
            yield FakeTextEvent("partial")

    setattr(
        IncompleteClient,
        OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT_ATTR,
        OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT,
    )
    recorder = LLMInvocationRecorder(default_context=make_context())
    wrapper = OpenHarnessPhysicalTelemetryClient(
        IncompleteClient(),
        invocation_recorder=recorder,
        provider="minimax",
    )

    with pytest.raises(OpenHarnessTelemetryContractError, match="without a terminal"):
        _ = [
            event
            async for event in wrapper.stream_message(FakeRequest(model="minimax-m1", messages=[]))
        ]

    assert [call["status"] for call in recorder.recent_calls(limit=10)] == ["failed"]
    assert [event["event_type"] for event in non_artifact_events(recorder)] == [
        "llm.provider.requested",
        "llm.call.failed",
    ]
