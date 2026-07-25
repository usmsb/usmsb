"""Fail-closed physical-attempt telemetry for OpenHarness API clients.

OpenHarness's ``QueryEngine`` is an agent-loop boundary, not a provider network
boundary.  One engine query can contain several model turns and each API client
may retry internally.  Projecting engine events as provider calls therefore
creates incomplete or even fictitious billing records.

This module wraps the public ``SupportsStreamingMessages.stream_message`` send
boundary. It only accepts clients which explicitly declare that a proposed
retry is surfaced *before* the next physical send and that no SDK layer performs
hidden retries. The wrapper aborts at that retry event, so a failed paid
creation request is never replayed. Unknown clients fail closed before the
engine can send a paid request.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from usmsb_sdk.llm_telemetry import (
    LLMInvocationRecorder,
    LLMTraceContext,
    LLMUsage,
    resolve_llm_context,
)

OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT = (
    "openharness.retry-event-before-next-send.no-hidden-sdk-retry.v1"
)
"""Capability value an audited OpenHarness API client must declare."""

OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT_ATTR = "__usmsb_openharness_physical_attempt_contract__"


class OpenHarnessTelemetryContractError(RuntimeError):
    """Raised before billing-sensitive execution when attempt evidence is unsafe."""


def supports_openharness_physical_attempt_telemetry(client: Any) -> bool:
    """Return whether ``client`` makes every physical attempt observable.

    This is intentionally an explicit capability contract. Class names or
    package versions are not trusted: provider SDKs commonly retry internally,
    and a wrapper above that SDK cannot stop those extra HTTP requests. The
    declared retry event must be yielded before another physical send so this
    wrapper can fail closed instead of resuming it.
    """

    if isinstance(client, OpenHarnessPhysicalTelemetryClient):
        return True
    return (
        getattr(client, OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT_ATTR, None)
        == OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT
    )


class OpenHarnessPhysicalTelemetryClient:
    """Record one provider attempt for every audited OpenHarness send attempt."""

    __usmsb_llm_physical_telemetry__ = "opc.llm.invocation-event.v1"

    def __init__(
        self,
        delegate: Any,
        *,
        invocation_recorder: LLMInvocationRecorder,
        provider: str,
        operation: str = "openharness.stream_message",
    ) -> None:
        if not supports_openharness_physical_attempt_telemetry(delegate):
            raise OpenHarnessTelemetryContractError(
                "OpenHarness API client does not guarantee a retry event before the "
                "next physical send with hidden SDK retries disabled; refusing paid "
                "LLM execution because single-shot transport cannot be proven"
            )
        self._delegate = delegate
        self.invocation_recorder = invocation_recorder
        self.provider = str(provider)
        self.operation = operation

    def __getattr__(self, name: str) -> Any:
        """Preserve non-streaming lifecycle/configuration APIs on the delegate."""

        return getattr(self._delegate, name)

    @staticmethod
    def _is_retry_event(event: Any) -> bool:
        return all(
            hasattr(event, name) for name in ("attempt", "max_attempts", "delay_seconds", "message")
        )

    @staticmethod
    def _is_complete_event(event: Any) -> bool:
        return hasattr(event, "message") and hasattr(event, "usage")

    @staticmethod
    def _event_text(event: Any) -> str | None:
        value = getattr(event, "text", None)
        return value if isinstance(value, str) and value else None

    def _logical_call_context(self) -> LLMTraceContext:
        root = resolve_llm_context(default=self.invocation_recorder.default_context)
        parent_call_id = root.logical_call_id
        if parent_call_id:
            root = root.with_updates(parent_logical_call_id=parent_call_id)
        return root.for_logical_call(operation=self.operation, force_new=True)

    async def stream_message(self, request: Any) -> AsyncIterator[Any]:
        """Yield delegate events while recording each physical provider attempt."""

        model = str(getattr(request, "model", "") or "unknown")
        call_context = self._logical_call_context()
        attempt_id: str | None = None
        content_parts: list[str] = []
        terminal_completed = False

        def start_attempt() -> str:
            return self.invocation_recorder.requested(
                provider=self.provider,
                model=model,
                operation=self.operation,
                request_payload=request,
                context=call_context,
                metadata={
                    "transport_retry_index": 0,
                    "retry_policy": "single_shot",
                    "attempt_evidence": OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT,
                },
            )

        attempt_id = start_attempt()
        try:
            async for event in self._delegate.stream_message(request):
                if terminal_completed:
                    raise OpenHarnessTelemetryContractError(
                        "OpenHarness client emitted events after its terminal provider event"
                    )

                text = self._event_text(event)
                if text:
                    content_parts.append(text)

                if self._is_retry_event(event):
                    if attempt_id is None:
                        raise OpenHarnessTelemetryContractError(
                            "OpenHarness retry event has no active physical attempt"
                        )
                    retry_error = OpenHarnessTelemetryContractError(
                        "OpenHarness provider requested an automatic retry; paid LLM "
                        "creation is single-shot and the next physical send was blocked"
                    )
                    self.invocation_recorder.failed(
                        attempt_id,
                        retry_error,
                        response_payload={
                            "partial_content": "".join(content_parts),
                            "attempt": getattr(event, "attempt", None),
                            "max_attempts": getattr(event, "max_attempts", None),
                            "delay_seconds": getattr(event, "delay_seconds", None),
                        },
                        metadata={
                            "transport_retry_index": 0,
                            "retry_policy": "single_shot",
                            "attempt_evidence": OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT,
                        },
                    )
                    attempt_id = None
                    # Do not yield or request another delegate event. Under the
                    # capability contract, the delegate is paused before its
                    # next physical send, so raising here prevents the replay.
                    raise retry_error

                if self._is_complete_event(event):
                    if attempt_id is None:
                        raise OpenHarnessTelemetryContractError(
                            "OpenHarness completion event has no active physical attempt"
                        )
                    usage = LLMUsage.from_value(getattr(event, "usage", None))
                    self.invocation_recorder.completed(
                        attempt_id,
                        response_payload={
                            "message": getattr(event, "message", None),
                            "usage": getattr(event, "usage", None),
                            "stop_reason": getattr(event, "stop_reason", None),
                            "content": "".join(content_parts),
                        },
                        usage=usage,
                        metadata={
                            "transport_retry_index": 0,
                            "retry_policy": "single_shot",
                            "attempt_evidence": OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT,
                        },
                    )
                    attempt_id = None
                    terminal_completed = True

                yield event

            if not terminal_completed:
                error = OpenHarnessTelemetryContractError(
                    "OpenHarness stream ended without a terminal provider completion event"
                )
                if attempt_id is not None:
                    self.invocation_recorder.failed(
                        attempt_id,
                        error,
                        response_payload={"partial_content": "".join(content_parts)},
                        metadata={
                            "transport_retry_index": 0,
                            "retry_policy": "single_shot",
                            "attempt_evidence": OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT,
                        },
                    )
                    attempt_id = None
                raise error
        except BaseException as error:
            if attempt_id is not None:
                self.invocation_recorder.failed(
                    attempt_id,
                    error,
                    response_payload={"partial_content": "".join(content_parts)},
                    metadata={
                        "transport_retry_index": 0,
                        "retry_policy": "single_shot",
                        "attempt_evidence": OPENHARNESS_PHYSICAL_ATTEMPT_CONTRACT,
                    },
                )
            raise


def install_openharness_physical_telemetry(
    engine: Any,
    *,
    invocation_recorder: LLMInvocationRecorder,
    provider: str,
) -> OpenHarnessPhysicalTelemetryClient:
    """Install the audited send-boundary wrapper or reject before execution."""

    client = getattr(engine, "api_client", None)
    if client is None:
        raise OpenHarnessTelemetryContractError(
            "OpenHarness QueryEngine does not expose its provider API client"
        )
    if isinstance(client, OpenHarnessPhysicalTelemetryClient):
        if client.invocation_recorder is not invocation_recorder:
            raise OpenHarnessTelemetryContractError(
                "OpenHarness API client is tracked by a different invocation recorder"
            )
        return client

    setter = getattr(engine, "set_api_client", None)
    if not callable(setter):
        raise OpenHarnessTelemetryContractError(
            "OpenHarness QueryEngine cannot install telemetry at the provider send boundary"
        )

    wrapped = OpenHarnessPhysicalTelemetryClient(
        client,
        invocation_recorder=invocation_recorder,
        provider=provider,
    )
    setter(wrapped)
    if getattr(engine, "api_client", None) is not wrapped:
        raise OpenHarnessTelemetryContractError(
            "OpenHarness QueryEngine did not retain the provider telemetry wrapper"
        )
    return wrapped
