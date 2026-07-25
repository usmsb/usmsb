"""Provider-boundary contract tests for distributed vLLM inference."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from usmsb_sdk.llm_telemetry import LLMInvocationRecorder

from node_executor import vllm_engine as vllm_module
from node_executor.vllm_engine import VLLMEngine
from shared.llm_telemetry_contract import (
    DIST_INFERENCE_PHYSICAL_ATTEMPT_CONTRACT,
    DistInferenceTelemetryContractError,
    load_invocation_recorder_from_factory,
)
from shared.types import InferenceRequest


def _context() -> dict:
    return InferenceRequest.create(
        model_name="Qwen/Qwen2.5-7B-Instruct",
        messages=[{"role": "user", "content": "hello"}],
        user_id="user-telemetry",
    ).llm_context


def _recorder() -> LLMInvocationRecorder:
    return LLMInvocationRecorder(event_callback=lambda _event: None)


def _provider_events(recorder: LLMInvocationRecorder) -> list[dict]:
    """Ignore the independent artifact-resolution event stream."""

    return [
        event
        for event in recorder.recent_events(limit=100)
        if event["event_type"] != "llm.artifact.resolved"
    ]


class FakeSamplingParams:
    def __init__(self, **values):
        self.values = values


class FakeVLLM:
    def __init__(self, *, error: BaseException | None = None):
        self.error = error
        self.call_count = 0

    def generate(self, prompts, sampling_params):
        self.call_count += 1
        if self.error is not None:
            raise self.error
        return [
            SimpleNamespace(
                request_id="vllm-request-1",
                prompt_token_ids=[1, 2, 3],
                outputs=[
                    SimpleNamespace(
                        text="world",
                        token_ids=[4, 5],
                        finish_reason="stop",
                    )
                ],
            )
        ]


def _real_engine(monkeypatch, recorder=None, *, error=None):
    monkeypatch.setattr(vllm_module, "VLLM_AVAILABLE", True)
    monkeypatch.setattr(vllm_module, "SamplingParams", FakeSamplingParams)
    engine = VLLMEngine(invocation_recorder=recorder)
    engine.loaded_model_name = "Qwen/Qwen2.5-7B-Instruct"
    engine.llm = FakeVLLM(error=error)
    return engine


def test_vllm_success_records_one_physical_attempt(monkeypatch) -> None:
    recorder = _recorder()
    engine = _real_engine(monkeypatch, recorder)

    result = engine.generate(
        [{"role": "user", "content": "hello"}],
        telemetry_context=_context(),
    )

    assert result["content"] == "world"
    assert result["usage"] == {
        "prompt_tokens": 3,
        "completion_tokens": 2,
        "total_tokens": 5,
    }
    assert engine.llm.call_count == 1
    calls = recorder.recent_calls(limit=10)
    assert len(calls) == 1
    assert calls[0]["provider"] == "vllm"
    assert calls[0]["status"] == "completed"
    assert calls[0]["usage"]["input_tokens"] == 3
    assert calls[0]["usage"]["output_tokens"] == 2
    billing_context = calls[0]["trace_context"]["billing_context"]
    assert billing_context["billing_user_id"] == "user-telemetry"
    assert calls[0]["metadata"]["retry_policy"] == "single_shot"
    assert (
        calls[0]["metadata"]["attempt_evidence"]
        == DIST_INFERENCE_PHYSICAL_ATTEMPT_CONTRACT
    )
    assert [event["event_type"] for event in _provider_events(recorder)] == [
        "llm.provider.requested",
        "llm.provider.completed",
    ]


def test_vllm_failure_is_recorded_once_and_not_retried(monkeypatch) -> None:
    recorder = _recorder()
    engine = _real_engine(monkeypatch, recorder, error=RuntimeError("gpu failed"))

    with pytest.raises(RuntimeError, match="gpu failed"):
        engine.generate(
            [{"role": "user", "content": "hello"}],
            telemetry_context=_context(),
        )

    assert engine.llm.call_count == 1
    calls = recorder.recent_calls(limit=10)
    assert len(calls) == 1
    assert calls[0]["status"] == "failed"
    assert [event["event_type"] for event in _provider_events(recorder)] == [
        "llm.provider.requested",
        "llm.call.failed",
    ]


@pytest.mark.parametrize(
    ("recorder", "context", "message"),
    [
        (None, _context(), "requires an injected"),
        (_recorder(), None, "missing required telemetry context"),
    ],
)
def test_vllm_fails_closed_before_send_without_contract(
    monkeypatch, recorder, context, message
) -> None:
    engine = _real_engine(monkeypatch, recorder)

    with pytest.raises(DistInferenceTelemetryContractError, match=message):
        engine.generate(
            [{"role": "user", "content": "hello"}],
            telemetry_context=context,
        )

    assert engine.llm.call_count == 0


def test_standalone_factory_is_required(monkeypatch) -> None:
    monkeypatch.delenv("USMSB_DIST_LLM_TELEMETRY_FACTORY", raising=False)
    with pytest.raises(
        DistInferenceTelemetryContractError,
        match="must name a recorder factory",
    ):
        load_invocation_recorder_from_factory()


def test_standalone_factory_must_return_canonical_recorder(monkeypatch) -> None:
    monkeypatch.setattr(
        "shared.llm_telemetry_contract.importlib.import_module",
        lambda _name: SimpleNamespace(build=lambda: object()),
    )
    with pytest.raises(
        DistInferenceTelemetryContractError,
        match="requires an injected",
    ):
        load_invocation_recorder_from_factory("fake_module:build")


def test_standalone_factory_rejects_in_memory_only_recorder(monkeypatch) -> None:
    monkeypatch.setattr(
        "shared.llm_telemetry_contract.importlib.import_module",
        lambda _name: SimpleNamespace(build=LLMInvocationRecorder),
    )
    with pytest.raises(
        DistInferenceTelemetryContractError,
        match="in-memory-only trace",
    ):
        load_invocation_recorder_from_factory("fake_module:build")


def test_standalone_factory_accepts_recorder_with_callback(monkeypatch) -> None:
    recorder = _recorder()
    monkeypatch.setattr(
        "shared.llm_telemetry_contract.importlib.import_module",
        lambda _name: SimpleNamespace(build=lambda: recorder),
    )

    assert load_invocation_recorder_from_factory("fake_module:build") is recorder


def test_source_has_one_unlooped_vllm_physical_boundary() -> None:
    """Static guard against future hidden replay/bypass paths."""

    source_path = Path(vllm_module.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    physical_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "generate"
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "llm"
    ]
    assert len(physical_calls) == 1
    physical_call = physical_calls[0]
    ancestor = parents.get(physical_call)
    while ancestor is not None:
        assert not isinstance(ancestor, (ast.For, ast.AsyncFor, ast.While))
        ancestor = parents.get(ancestor)

    requested_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "requested"
    ]
    assert len(requested_calls) == 1
    assert requested_calls[0].lineno < physical_call.lineno

    guard_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", None) == "require_invocation_recorder"
    ]
    assert len(guard_calls) == 1
    assert guard_calls[0].lineno < requested_calls[0].lineno
