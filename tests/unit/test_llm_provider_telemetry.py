"""Provider-attempt telemetry contract tests for MetaAgent LLM paths."""

from __future__ import annotations

import asyncio
import threading
import time
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
import requests

from usmsb_sdk.intelligence_adapters.base import (
    IntelligenceSourceConfig,
    IntelligenceSourceType,
)
from usmsb_sdk.intelligence_adapters.llm.minimax_adapter import MiniMaxAdapter
from usmsb_sdk.llm_telemetry import (
    LLMBillingContext,
    LLMInvocationRecorder,
    LLMTraceContext,
    LLMUsage,
)
from usmsb_sdk.meta_agent.agent import MetaAgent
from usmsb_sdk.meta_agent.llm.manager import LLMManager
from usmsb_sdk.meta_agent.llm_client import LLMClient


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")


class SequencedAsyncClient:
    def __init__(self, outcomes: list[Any]):
        self.outcomes = list(outcomes)
        self.call_count = 0

    async def post(self, *_args: Any, **_kwargs: Any) -> FakeResponse:
        self.call_count += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def minimax_payload(content: str, *, input_tokens: int, output_tokens: int) -> dict[str, Any]:
    return {
        "id": f"resp-{input_tokens}-{output_tokens}",
        "base_resp": {"status_code": 0, "status_msg": "success"},
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "prompt_tokens_details": {"cached_tokens": 3},
        },
    }


def make_context() -> LLMTraceContext:
    return LLMTraceContext(
        trace_id="trace-1",
        source_service="usmsb-test",
        agent_id="agent-1",
        billing=LLMBillingContext.from_value(
            {
                "schema": "opc.billing-context.v1",
                "billing_task_id": "billing-task-1",
                "task_scope_type": "agent_execution",
                "task_scope_id": "task-1",
                "principal_type": "user",
                "billing_user_id": "user-1",
                "actor_user_id": "actor-1",
                "owner_user_id": "owner-1",
                "pricing_policy_id": "llm.token.usage:test-v1",
                "admission_status": "admitted",
                "signature": "signed-envelope",
            }
        ),
    )


def make_adapter(recorder: LLMInvocationRecorder, outcomes: list[Any]) -> MiniMaxAdapter:
    config = IntelligenceSourceConfig(
        name="minimax",
        type=IntelligenceSourceType.LLM,
        api_key="test-key",
        model="MiniMax-M2.5",
        extra_params={"invocation_recorder": recorder},
    )
    adapter = MiniMaxAdapter(config)
    adapter._client = SequencedAsyncClient(outcomes)  # type: ignore[assignment]
    return adapter


def non_artifact_events(recorder: LLMInvocationRecorder) -> list[dict[str, Any]]:
    return [
        event
        for event in recorder.recent_events(limit=100)
        if event["event_type"] != "llm.artifact.resolved"
    ]


def wait_for_call_artifacts(
    recorder: LLMInvocationRecorder,
    attempt_id: str,
    *,
    timeout: float = 5.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while True:
        call = recorder.get_call(attempt_id)
        if call and call["request_hash"] and (
            call["response_provisional_id"] is None or call["response_hash"]
        ):
            return call
        if time.monotonic() >= deadline:
            raise AssertionError("timed out waiting for artifact resolution")
        time.sleep(0.005)


def test_usage_normalizes_provider_token_dialects() -> None:
    usage = LLMUsage.from_value(
        {
            "usage": {
                "prompt_tokens": 40,
                "completion_tokens": 12,
                "total_tokens": 52,
                "prompt_tokens_details": {"cached_tokens": 7},
                "completion_tokens_details": {"reasoning_tokens": 4},
            }
        }
    )

    assert usage.input_tokens == 40
    assert usage.output_tokens == 12
    assert usage.cached_input_tokens == 7
    assert usage.reasoning_tokens == 4
    assert usage.total_tokens == 52
    assert usage.source == "provider_reported"


def test_total_only_chat_usage_remains_unallocated_and_not_settleable() -> None:
    usage = LLMUsage.from_value({"usage": {"total_tokens": 52}})

    assert usage.input_tokens == 0
    assert usage.output_tokens == 0
    assert usage.total_tokens == 52
    assert usage.source == "total_only_unallocated"


def test_events_match_opc_invocation_contract_without_call_detail_guessing() -> None:
    recorder = LLMInvocationRecorder()
    attempt_id = recorder.requested(
        provider="minimax",
        model="MiniMax-M2.5",
        operation="chat_with_tools",
        request_payload={"messages": [{"role": "user", "content": "hello"}]},
        context=make_context().for_logical_call(operation="chat_with_tools"),
    )
    recorder.completed(
        attempt_id,
        response_payload=minimax_payload("ok", input_tokens=31, output_tokens=9),
    )

    requested, completed = non_artifact_events(recorder)
    for event in (requested, completed):
        assert event["schema"] == "opc.llm.invocation-event.v1"
        assert isinstance(event["occurred_at"], float)
        assert event["source_service"] == "usmsb-test"
        assert event["billing"]["billing_user_id"] == "user-1"
        assert event["billing"]["task_scope_type"] == "agent_execution"
        assert event["billing"]["task_scope_id"] == "task-1"
        assert event["billing"]["pricing_policy_id"] == "llm.token.usage:test-v1"
        assert event["billing"]["admission_status"] == "admitted"
        assert event["lineage"]["provider_attempt_id"] == attempt_id
        assert event["provider"]["name"] == "minimax"
        assert event["provider"]["model"] == "MiniMax-M2.5"

    assert requested["event_type"] == "llm.provider.requested"
    assert completed["event_type"] == "llm.provider.completed"
    assert completed["usage"]["input_tokens"] == 31
    assert completed["usage"]["output_tokens"] == 9
    for event in (requested, completed):
        assert "call_detail" not in event
        assert "request_payload" not in event["result"]
        assert "response_payload" not in event["result"]
        assert event["artifacts"]["request_provisional_id"]
    assert completed["artifacts"]["response_provisional_id"]
    # The bounded diagnostic journal may retain redacted artifacts; the
    # callback/event hot path must not duplicate those potentially huge values.
    diagnostic = wait_for_call_artifacts(recorder, attempt_id)
    assert diagnostic["request_payload"]
    assert diagnostic["response_payload"]
    assert recorder.recent_calls(task_id="task-1")[0]["provider_attempt_id"] == attempt_id
    assert (
        recorder.recent_calls(billing_task_id="billing-task-1")[0]["provider_attempt_id"]
        == attempt_id
    )
    assert recorder.recent_calls(limit=0) == []


@pytest.mark.asyncio
async def test_sync_emit_nowait_callback_runs_on_event_loop_thread() -> None:
    callback_thread_ids: list[tuple[str, int]] = []

    def callback(event: dict[str, Any]) -> None:
        callback_thread_ids.append((event["event_type"], threading.get_ident()))

    loop_thread_id = threading.get_ident()
    recorder = LLMInvocationRecorder(event_callback=callback)
    attempt_id = recorder.requested(
        provider="minimax",
        model="model",
        operation="chat",
        request_payload={},
        context=make_context(),
    )
    recorder.completed(attempt_id, response_payload={})
    await asyncio.sleep(0)

    provider_callback_threads = [
        thread_id
        for event_type, thread_id in callback_thread_ids
        if event_type != "llm.artifact.resolved"
    ]
    assert provider_callback_threads == [loop_thread_id, loop_thread_id]


@pytest.mark.asyncio
async def test_async_callable_object_callback_is_scheduled_on_current_loop() -> None:
    callback_thread_ids: list[tuple[str, int]] = []

    class AsyncSink:
        async def __call__(self, event: dict[str, Any]) -> None:
            callback_thread_ids.append((event["event_type"], threading.get_ident()))

    loop_thread_id = threading.get_ident()
    recorder = LLMInvocationRecorder(event_callback=AsyncSink())
    attempt_id = recorder.requested(
        provider="minimax",
        model="model",
        operation="chat",
        request_payload={},
        context=make_context(),
    )
    recorder.completed(attempt_id, response_payload={})
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    provider_callback_threads = [
        thread_id
        for event_type, thread_id in callback_thread_ids
        if event_type != "llm.artifact.resolved"
    ]
    assert provider_callback_threads == [loop_thread_id, loop_thread_id]


@pytest.mark.asyncio
async def test_minimax_paid_generation_network_failure_is_single_shot() -> None:
    recorder = LLMInvocationRecorder(default_context=make_context())
    adapter = make_adapter(
        recorder,
        [
            httpx.ConnectError("temporary disconnect"),
            FakeResponse(minimax_payload("done", input_tokens=20, output_tokens=5)),
        ],
    )
    client = adapter._client

    with pytest.raises(httpx.ConnectError, match="temporary disconnect"):
        await adapter.generate_text("hello", trace_context=make_context())

    assert isinstance(client, SequencedAsyncClient)
    assert client.call_count == 1
    assert len(client.outcomes) == 1
    calls = list(reversed(recorder.recent_calls(limit=10)))
    assert [item["status"] for item in calls] == ["failed"]
    assert calls[0]["metadata"]["retry_policy"] == "single_shot"
    assert [event["event_type"] for event in non_artifact_events(recorder)] == [
        "llm.provider.requested",
        "llm.call.failed",
    ]


@pytest.mark.asyncio
async def test_minimax_generate_with_system_does_not_add_an_outer_retry() -> None:
    recorder = LLMInvocationRecorder(default_context=make_context())
    adapter = make_adapter(
        recorder,
        [
            httpx.ReadTimeout("ambiguous timeout"),
            FakeResponse(minimax_payload("must-not-run", input_tokens=20, output_tokens=5)),
        ],
    )
    client = adapter._client

    with pytest.raises(httpx.ReadTimeout, match="ambiguous timeout"):
        await adapter.generate_with_system(
            "system",
            "hello",
            trace_context=make_context(),
        )

    assert isinstance(client, SequencedAsyncClient)
    assert client.call_count == 1
    assert len(client.outcomes) == 1
    assert [item["status"] for item in recorder.recent_calls(limit=10)] == ["failed"]


@pytest.mark.asyncio
async def test_minimax_health_check_uses_platform_scope_and_emits_task_terminal() -> None:
    recorder = LLMInvocationRecorder(default_context=make_context())
    adapter = make_adapter(
        recorder,
        [FakeResponse(minimax_payload("ok", input_tokens=2, output_tokens=1))],
    )

    assert await adapter.health_check() is True

    events = non_artifact_events(recorder)
    assert [event["event_type"] for event in events] == [
        "llm.provider.requested",
        "llm.provider.completed",
        "llm.task.completed",
    ]
    logical_call_ids = {event["logical_call_id"] for event in events}
    assert len(logical_call_ids) == 1
    for event in events:
        assert event["billing"]["principal_type"] == "platform"
        assert event["billing"]["billing_user_id"] is None
        assert event["billing"]["admission_status"] == "bypassed_platform"
        assert event["billing"]["pricing_policy_id"] == "platform.observation"
        assert len(event["billing"]["billing_task_id"]) == 36
        assert event["operation"] == "health_check.chat"


@pytest.mark.asyncio
async def test_minimax_failed_health_check_is_single_shot_and_task_terminal() -> None:
    recorder = LLMInvocationRecorder(default_context=make_context())
    adapter = make_adapter(recorder, [httpx.ConnectError("health unavailable")])
    client = adapter._client

    assert await adapter.health_check() is False

    assert isinstance(client, SequencedAsyncClient)
    assert client.call_count == 1
    events = non_artifact_events(recorder)
    assert [event["event_type"] for event in events] == [
        "llm.provider.requested",
        "llm.call.failed",
        "llm.task.failed",
    ]
    assert {event["billing"]["principal_type"] for event in events} == {"platform"}
    assert {event["logical_call_id"] for event in events} == {events[0]["logical_call_id"]}


@pytest.mark.asyncio
async def test_minimax_embedding_total_only_usage_is_billed_as_input_tokens() -> None:
    recorder = LLMInvocationRecorder(default_context=make_context())
    adapter = make_adapter(recorder, [])
    adapter._embedding_client = SequencedAsyncClient(  # type: ignore[assignment]
        [
            FakeResponse(
                {
                    "vectors": [[0.1, 0.2]],
                    "base_resp": {"status_code": 0, "status_msg": "success"},
                    "usage": {"total_tokens": 17},
                }
            )
        ]
    )

    assert await adapter.embed("hello", trace_context=make_context()) == [0.1, 0.2]

    call = recorder.recent_calls(limit=1)[0]
    assert call["operation"] == "embeddings.query"
    assert call["status"] == "completed"
    assert call["usage"]["input_tokens"] == 17
    assert call["usage"]["output_tokens"] == 0
    assert call["usage"]["total_tokens"] == 17
    assert call["usage"]["source"] == "provider_reported"


@pytest.mark.asyncio
async def test_minimax_embedding_http_200_provider_error_is_failed_not_completed() -> None:
    recorder = LLMInvocationRecorder(default_context=make_context())
    adapter = make_adapter(recorder, [])
    embedding_client = SequencedAsyncClient(
        [
            FakeResponse(
                {
                    "vectors": [[0.1, 0.2]],
                    "base_resp": {"status_code": 1004, "status_msg": "invalid request"},
                    "usage": {"total_tokens": 11},
                }
            )
        ]
    )
    adapter._embedding_client = embedding_client  # type: ignore[assignment]

    with pytest.raises(RuntimeError, match="invalid request"):
        await adapter.embed("hello", trace_context=make_context())

    assert embedding_client.call_count == 1
    call = recorder.recent_calls(limit=1)[0]
    assert call["status"] == "failed"
    assert call["usage"]["input_tokens"] == 11
    assert [event["event_type"] for event in non_artifact_events(recorder)] == [
        "llm.provider.requested",
        "llm.call.failed",
    ]


@pytest.mark.asyncio
async def test_minimax_embedding_invalid_vector_is_failed_not_completed() -> None:
    recorder = LLMInvocationRecorder(default_context=make_context())
    adapter = make_adapter(recorder, [])
    adapter._embedding_client = SequencedAsyncClient(  # type: ignore[assignment]
        [
            FakeResponse(
                {
                    "vectors": [[0.1, "not-a-number"]],
                    "base_resp": {"status_code": 0, "status_msg": "success"},
                    "usage": {"total_tokens": 7},
                }
            )
        ]
    )

    with pytest.raises(ValueError, match="expected number"):
        await adapter.embed("hello", trace_context=make_context())

    call = recorder.recent_calls(limit=1)[0]
    assert call["status"] == "failed"
    assert call["usage"]["input_tokens"] == 7


@pytest.mark.asyncio
async def test_minimax_embedding_network_failure_is_single_shot() -> None:
    recorder = LLMInvocationRecorder(default_context=make_context())
    adapter = make_adapter(recorder, [])
    embedding_client = SequencedAsyncClient(
        [
            httpx.ConnectError("ambiguous embedding disconnect"),
            FakeResponse(
                {
                    "vectors": [[0.1, 0.2]],
                    "base_resp": {"status_code": 0, "status_msg": "success"},
                }
            ),
        ]
    )
    adapter._embedding_client = embedding_client  # type: ignore[assignment]

    with pytest.raises(httpx.ConnectError, match="ambiguous embedding disconnect"):
        await adapter.embed("hello", trace_context=make_context())

    assert embedding_client.call_count == 1
    assert len(embedding_client.outcomes) == 1
    assert [call["status"] for call in recorder.recent_calls(limit=10)] == ["failed"]


@pytest.mark.asyncio
async def test_minimax_batch_embedding_validates_body_count_and_indexes_before_completed() -> None:
    recorder = LLMInvocationRecorder(default_context=make_context())
    adapter = make_adapter(recorder, [])
    adapter._embedding_client = SequencedAsyncClient(  # type: ignore[assignment]
        [
            FakeResponse(
                {
                    "data": [{"index": 0, "embedding": [0.1, 0.2]}],
                    "base_resp": {"status_code": 0, "status_msg": "success"},
                    "usage": {"total_tokens": 13},
                }
            )
        ]
    )

    with pytest.raises(ValueError, match="indexes do not match input texts"):
        await adapter.embed_batch(["one", "two"], trace_context=make_context())

    call = recorder.recent_calls(limit=1)[0]
    assert call["status"] == "failed"
    assert call["usage"]["input_tokens"] == 13


@pytest.mark.asyncio
async def test_minimax_total_only_chat_usage_is_not_mislabeled_provider_reported() -> None:
    recorder = LLMInvocationRecorder(default_context=make_context())
    adapter = make_adapter(
        recorder,
        [
            FakeResponse(
                {
                    "id": "total-only-chat",
                    "base_resp": {"status_code": 0, "status_msg": "success"},
                    "choices": [{"message": {"content": "done"}}],
                    "usage": {"total_tokens": 21},
                }
            )
        ],
    )

    assert await adapter.generate_text("hello", trace_context=make_context()) == "done"

    usage = recorder.recent_calls(limit=1)[0]["usage"]
    assert usage["input_tokens"] == 0
    assert usage["output_tokens"] == 0
    assert usage["total_tokens"] == 21
    assert usage["source"] == "total_only_unallocated"


@pytest.mark.asyncio
async def test_json_repair_is_a_separate_physical_call_under_one_logical_call() -> None:
    manager_config = SimpleNamespace(
        provider="minimax",
        model="MiniMax-M2.5",
        api_key="test-key",
        base_url="https://example.invalid/v1",
        temperature=0.0,
        max_tokens=1024,
    )
    manager = LLMManager(manager_config, default_context=make_context())
    manager._adapter = make_adapter(
        manager.invocation_recorder,
        [
            FakeResponse(minimax_payload("not-json", input_tokens=10, output_tokens=2)),
            FakeResponse(minimax_payload('{"title":"ok"}', input_tokens=30, output_tokens=5)),
        ],
    )

    result = await manager.generate_json(
        system_prompt="JSON only",
        user_prompt="make object",
        schema={"type": "object", "required": ["title"]},
        retries=1,
        trace_context=make_context(),
        return_metadata=True,
    )

    assert result["data"] == {"title": "ok"}
    calls = list(reversed(manager.get_llm_call_details(limit=10)))
    assert len(calls) == 2
    assert len({item["provider_attempt_id"] for item in calls}) == 2
    assert len({item["trace_context"]["logical_call_id"] for item in calls}) == 1
    assert [item["operation"] for item in calls] == [
        "generate_json",
        "generate_json.repair",
    ]


@pytest.mark.asyncio
async def test_agent_loop_chat_result_contains_calls_events_and_usage() -> None:
    manager_config = SimpleNamespace(
        provider="minimax",
        model="MiniMax-M2.5",
        api_key="test-key",
        base_url="https://example.invalid/v1",
        temperature=0.0,
        max_tokens=1024,
    )
    manager = LLMManager(manager_config, default_context=make_context())
    manager._adapter = make_adapter(
        manager.invocation_recorder,
        [FakeResponse(minimax_payload("hello", input_tokens=12, output_tokens=4))],
    )
    agent = object.__new__(MetaAgent)
    agent.llm_manager = manager

    with manager.trace_scope(make_context()):
        result = await agent._chat_with_llm(
            [{"role": "user", "content": "hello"}],
            tools=[],
            skills=[],
        )

    assert result.content == "hello"
    assert len(result.llm_calls) == 1
    assert [event["event_type"] for event in result.llm_events] == [
        "llm.provider.requested",
        "llm.provider.completed",
    ]
    assert result.llm_usage == {
        "physical_calls": 1,
        "completed_calls": 1,
        "failed_calls": 0,
        "input_tokens": 12,
        "cached_input_tokens": 3,
        "output_tokens": 4,
        "total_tokens": 16,
    }


def test_legacy_minimax_provider_failure_does_not_fallback_to_another_paid_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = [
        FakeResponse({"error": "busy"}, status_code=503),
        FakeResponse(
            {
                "id": "openai-response",
                "choices": [{"message": {"content": "fallback-ok"}}],
                "usage": {"prompt_tokens": 6, "completion_tokens": 2, "total_tokens": 8},
            }
        ),
    ]

    call_count = 0

    def fake_post(*_args: Any, **_kwargs: Any) -> FakeResponse:
        nonlocal call_count
        call_count += 1
        return responses.pop(0)

    monkeypatch.setattr("usmsb_sdk.meta_agent.llm_client.requests.post", fake_post)
    client = LLMClient(api_key="openai-key", default_context=make_context())
    client.minimax_key = "minimax-key"

    result = client.complete(
        "你好",
        model="MiniMax",
        trace_context=make_context(),
    )

    assert result == "[MiniMax Error: status=503]"
    assert call_count == 1
    assert len(responses) == 1
    failed_call = client.get_llm_call_details(limit=1)[0]
    wait_for_call_artifacts(
        client.invocation_recorder,
        failed_call["provider_attempt_id"],
    )
    calls = list(reversed(client.get_llm_call_details(limit=10)))
    assert [(item["provider"], item["status"]) for item in calls] == [
        ("minimax", "failed"),
    ]
    assert calls[0]["response_payload"] == {"error": "busy"}
    assert [
        event["event_type"] for event in non_artifact_events(client.invocation_recorder)
    ] == [
        "llm.provider.requested",
        "llm.call.failed",
    ]
