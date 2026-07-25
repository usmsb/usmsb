"""Fail-closed telemetry contract for the standalone inference worker.

The distributed inference runtime is packaged and deployed independently from
the main SDK process.  It must therefore receive an explicitly configured SDK
``LLMInvocationRecorder`` instead of silently creating an unobservable local
provider path.  The recorder is injected by a factory so the hosting process
can attach its normal non-blocking OPC event callback.
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Mapping
from typing import Any

from usmsb_sdk.llm_telemetry import (
    LLMInvocationRecorder,
    LLMTraceContext,
    resolve_llm_context,
)

DIST_INFERENCE_PHYSICAL_ATTEMPT_CONTRACT = (
    "usmsb-dist-inference.vllm.single-shot.physical-attempt-telemetry.v1"
)
DIST_INFERENCE_TELEMETRY_FACTORY_ENV = "USMSB_DIST_LLM_TELEMETRY_FACTORY"


class DistInferenceTelemetryContractError(RuntimeError):
    """Raised before a real vLLM call when telemetry cannot be guaranteed."""


def require_invocation_recorder(value: Any) -> LLMInvocationRecorder:
    """Require the canonical SDK recorder; duck-typed/no-op sinks are rejected."""

    if not isinstance(value, LLMInvocationRecorder):
        raise DistInferenceTelemetryContractError(
            "real vLLM inference requires an injected usmsb-sdk "
            "LLMInvocationRecorder; provider execution was blocked"
        )
    if not value.has_event_callbacks:
        raise DistInferenceTelemetryContractError(
            "distributed inference requires an LLMInvocationRecorder with at "
            "least one non-blocking event callback; an in-memory-only trace "
            "would be an unobservable provider bypass"
        )
    return value


def resolve_required_trace_context(
    recorder: LLMInvocationRecorder,
    value: LLMTraceContext | Mapping[str, Any] | None,
) -> LLMTraceContext:
    """Resolve and validate the chargeable lineage before a provider call."""

    resolved = resolve_llm_context(value, default=recorder.default_context)
    billing = resolved.billing
    missing: list[str] = []
    if not resolved.trace_id:
        missing.append("trace_id")
    if not resolved.logical_call_id:
        missing.append("logical_call_id")
    if not resolved.source_service:
        missing.append("source_service")
    if billing is None:
        missing.append("billing_context")
    else:
        if not billing.principal_id:
            missing.append("billing.principal_id")
        if not (billing.task_scope_id or billing.billing_task_id):
            missing.append("billing.task_scope_id")
        if billing.admission_status not in {"admitted", "bypassed_platform"}:
            missing.append("billing.admission_status")
    if missing:
        raise DistInferenceTelemetryContractError(
            "real vLLM inference is missing required telemetry context: "
            + ", ".join(missing)
        )
    return resolved.with_updates(operation="vllm.generate")


def load_invocation_recorder_from_factory(
    factory_path: str | None = None,
) -> LLMInvocationRecorder:
    """Load the host-owned recorder factory used by the standalone node.

    The factory path uses ``package.module:callable`` syntax.  No default or
    no-op recorder is installed: a production node without this integration
    must fail before it can expose a real inference boundary.
    """

    configured = str(
        factory_path
        if factory_path is not None
        else os.environ.get(DIST_INFERENCE_TELEMETRY_FACTORY_ENV, "")
    ).strip()
    if not configured or ":" not in configured:
        raise DistInferenceTelemetryContractError(
            f"{DIST_INFERENCE_TELEMETRY_FACTORY_ENV} must name a recorder factory "
            "as package.module:callable before real vLLM inference is enabled"
        )
    module_name, attribute_name = configured.rsplit(":", 1)
    try:
        module = importlib.import_module(module_name)
        factory = getattr(module, attribute_name)
    except (ImportError, AttributeError) as exc:
        raise DistInferenceTelemetryContractError(
            f"cannot load distributed inference telemetry factory {configured!r}"
        ) from exc
    if not callable(factory):
        raise DistInferenceTelemetryContractError(
            f"distributed inference telemetry factory {configured!r} is not callable"
        )
    try:
        recorder = factory()
    except Exception as exc:
        raise DistInferenceTelemetryContractError(
            f"distributed inference telemetry factory {configured!r} failed"
        ) from exc
    return require_invocation_recorder(recorder)


__all__ = [
    "DIST_INFERENCE_PHYSICAL_ATTEMPT_CONTRACT",
    "DIST_INFERENCE_TELEMETRY_FACTORY_ENV",
    "DistInferenceTelemetryContractError",
    "load_invocation_recorder_from_factory",
    "require_invocation_recorder",
    "resolve_required_trace_context",
]
