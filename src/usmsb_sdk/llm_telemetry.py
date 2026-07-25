"""Provider-attempt-level LLM telemetry primitives.

The SDK has several agent and tool loops.  Recording at the public ``chat``
boundary loses retries, JSON repairs and direct adapter calls, so this module
models one record per physical provider request.  It deliberately has no
database or network dependency: events are captured synchronously in a
bounded in-memory journal and callbacks are dispatched best-effort in the
background.
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import logging
import math
import re
import threading
from collections import OrderedDict, deque
from collections.abc import Callable, Iterator, Mapping
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import asdict, dataclass, field, is_dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

from usmsb_sdk.llm_artifacts import (
    LLMArtifactResolution,
    LLMArtifactSpool,
    LLMArtifactSpoolError,
    artifact_sha256,
    canonical_artifact_bytes,
    get_shared_llm_artifact_spool_from_env,
    llm_artifact_spool_required,
)

logger = logging.getLogger(__name__)

LLMEventCallback = Callable[[dict[str, Any]], Any]


class LLMProviderEventType(StrEnum):
    """Stable event names consumed by billing and trace projections."""

    REQUESTED = "llm.provider.requested"
    COMPLETED = "llm.provider.completed"
    FAILED = "llm.call.failed"
    ARTIFACT_RESOLVED = "llm.artifact.resolved"


class LLMProviderAttemptStatus(StrEnum):
    REQUESTED = "requested"
    COMPLETED = "completed"
    FAILED = "failed"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _as_non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        values = [_json_safe(item) for item in value]
        return sorted(values, key=lambda item: repr(item))
    if is_dataclass(value):
        return _json_safe(asdict(value))
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            return _json_safe(model_dump(mode="json"))
        except TypeError:
            return _json_safe(model_dump())
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            return _json_safe(to_dict())
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        public = {key: item for key, item in vars(value).items() if not str(key).startswith("_")}
        if public:
            return _json_safe(public)
    return str(value)


_SENSITIVE_KEY_PARTS = (
    "apikey",
    "authorization",
    "accesstoken",
    "refreshtoken",
    "sessiontoken",
    "securitytoken",
    "xapikey",
    "secret",
    "password",
    "privatekey",
    "cookie",
    "setcookie",
    "signature",
    "credential",
)


def _normalized_sensitive_key(value: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", str(value).lower())
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _redact_signed_url(value: str) -> str:
    """Redact credential-like query parameters without altering ordinary URLs."""

    if not value.lower().startswith(("http://", "https://")):
        return value
    try:
        parsed = urlsplit(value)
        if not parsed.query:
            return value
        redacted_query = [
            (key, "[REDACTED]" if _normalized_sensitive_key(key) else item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
        ]
        return urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                urlencode(redacted_query, doseq=True),
                parsed.fragment,
            )
        )
    except (TypeError, ValueError):
        return value


def redact_llm_payload(value: Any) -> Any:
    """Return a JSON-safe payload with credential-like values redacted."""

    safe = _json_safe(value)
    if isinstance(safe, dict):
        redacted: dict[str, Any] = {}
        for key, item in safe.items():
            if _normalized_sensitive_key(key):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_llm_payload(item)
        return redacted
    if isinstance(safe, list):
        return [redact_llm_payload(item) for item in safe]
    if isinstance(safe, str):
        return _redact_signed_url(safe)
    return safe


def _payload_hash(value: Any) -> str | None:
    if value is None:
        return None
    return artifact_sha256(redact_llm_payload(value))


def _bounded_text(value: Any, *, limit: int = 2048) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}…[truncated:{len(text) - limit}]"


def _first_present(mapping: Mapping[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        value = mapping.get(name)
        if value is not None:
            return value
    return None


@dataclass(frozen=True, slots=True)
class LLMBillingContext:
    """Opaque billing identity propagated by an embedding application."""

    schema: str = "opc.billing-context.v1"
    principal_id: str | None = None
    principal_type: str = "user"
    billing_user_id: str | None = None
    actor_user_id: str | None = None
    owner_user_id: str | None = None
    user_id: str | None = None
    task_id: str | None = None
    billing_task_id: str | None = None
    task_scope_type: str | None = None
    task_scope_id: str | None = None
    admission_id: str | None = None
    pricing_policy_id: str | None = None
    admission_status: str = "pending"
    trace_id: str | None = None
    issued_at: float | None = None
    expires_at: float | None = None
    nonce: str | None = None
    audience_agent_id: str | None = None
    a2a_execution_id: str | None = None
    signature_alg: str | None = None
    key_id: str | None = None
    signature: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    extra: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(
        cls,
        value: LLMBillingContext | Mapping[str, Any] | None,
    ) -> LLMBillingContext | None:
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        data = dict(value)
        billing_user_id = data.get("billing_user_id") or data.get("user_id")
        known_keys = {
            "schema",
            "principal_id",
            "principal_type",
            "billing_user_id",
            "actor_user_id",
            "owner_user_id",
            "user_id",
            "task_id",
            "root_task_id",
            "billing_task_id",
            "task_scope_type",
            "task_scope_id",
            "admission_id",
            "pricing_policy_id",
            "pricing_version",
            "admission_status",
            "trace_id",
            "issued_at",
            "expires_at",
            "nonce",
            "audience_agent_id",
            "a2a_execution_id",
            "signature_alg",
            "key_id",
            "signature",
            "metadata",
        }
        return cls(
            schema=str(data.get("schema") or "opc.billing-context.v1"),
            principal_id=(data.get("principal_id") or billing_user_id or data.get("owner_user_id")),
            principal_type=str(data.get("principal_type") or "user"),
            billing_user_id=billing_user_id,
            actor_user_id=data.get("actor_user_id"),
            owner_user_id=data.get("owner_user_id"),
            user_id=billing_user_id,
            task_id=data.get("task_id") or data.get("root_task_id"),
            billing_task_id=data.get("billing_task_id"),
            task_scope_type=data.get("task_scope_type"),
            task_scope_id=(
                data.get("task_scope_id") or data.get("task_id") or data.get("root_task_id")
            ),
            admission_id=data.get("admission_id"),
            pricing_policy_id=data.get("pricing_policy_id") or data.get("pricing_version"),
            admission_status=str(data.get("admission_status") or "pending"),
            trace_id=data.get("trace_id"),
            issued_at=data.get("issued_at"),
            expires_at=data.get("expires_at"),
            nonce=data.get("nonce"),
            audience_agent_id=data.get("audience_agent_id"),
            a2a_execution_id=data.get("a2a_execution_id"),
            signature_alg=data.get("signature_alg"),
            key_id=data.get("key_id"),
            signature=data.get("signature"),
            metadata=dict(data.get("metadata") or {}),
            extra={key: item for key, item in data.items() if key not in known_keys},
        )

    def merge(self, overlay: LLMBillingContext | None) -> LLMBillingContext:
        if overlay is None:
            return self
        return LLMBillingContext(
            schema=overlay.schema or self.schema,
            principal_id=overlay.principal_id or self.principal_id,
            principal_type=overlay.principal_type or self.principal_type,
            billing_user_id=overlay.billing_user_id or self.billing_user_id,
            actor_user_id=overlay.actor_user_id or self.actor_user_id,
            owner_user_id=overlay.owner_user_id or self.owner_user_id,
            user_id=overlay.user_id or self.user_id,
            task_id=overlay.task_id or self.task_id,
            billing_task_id=overlay.billing_task_id or self.billing_task_id,
            task_scope_type=overlay.task_scope_type or self.task_scope_type,
            task_scope_id=overlay.task_scope_id or self.task_scope_id,
            admission_id=overlay.admission_id or self.admission_id,
            pricing_policy_id=overlay.pricing_policy_id or self.pricing_policy_id,
            admission_status=overlay.admission_status or self.admission_status,
            trace_id=overlay.trace_id or self.trace_id,
            issued_at=overlay.issued_at or self.issued_at,
            expires_at=overlay.expires_at or self.expires_at,
            nonce=overlay.nonce or self.nonce,
            audience_agent_id=overlay.audience_agent_id or self.audience_agent_id,
            a2a_execution_id=overlay.a2a_execution_id or self.a2a_execution_id,
            signature_alg=overlay.signature_alg or self.signature_alg,
            key_id=overlay.key_id or self.key_id,
            signature=overlay.signature or self.signature,
            metadata={**dict(self.metadata), **dict(overlay.metadata)},
            extra={**dict(self.extra), **dict(overlay.extra)},
        )

    def to_dict(self, *, include_sensitive: bool = False) -> dict[str, Any]:
        result = {
            **redact_llm_payload(dict(self.extra)),
            "schema": self.schema,
            "principal_id": self.principal_id,
            "principal_type": self.principal_type,
            "billing_user_id": self.billing_user_id or self.user_id,
            "actor_user_id": self.actor_user_id,
            "owner_user_id": self.owner_user_id,
            "billing_task_id": self.billing_task_id,
            "task_scope_type": self.task_scope_type,
            "task_scope_id": self.task_scope_id or self.task_id,
            "admission_id": self.admission_id,
            "pricing_policy_id": self.pricing_policy_id,
            "admission_status": self.admission_status,
            "trace_id": self.trace_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "nonce": self.nonce,
            "audience_agent_id": self.audience_agent_id,
            "a2a_execution_id": self.a2a_execution_id,
            "signature_alg": self.signature_alg,
            "key_id": self.key_id,
            "metadata": redact_llm_payload(dict(self.metadata)),
        }
        if include_sensitive:
            result["signature"] = self.signature
        elif self.signature:
            result["signature_present"] = True
        return result


@dataclass(frozen=True, slots=True)
class LLMTraceContext:
    """Async-safe trace lineage shared by all calls in a task or agent run."""

    trace_id: str | None = None
    logical_call_id: str | None = None
    parent_logical_call_id: str | None = None
    session_id: str | None = None
    conversation_id: str | None = None
    agent_id: str | None = None
    source_service: str | None = None
    operation: str | None = None
    billing: LLMBillingContext | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(
        cls,
        value: LLMTraceContext | Mapping[str, Any] | None,
    ) -> LLMTraceContext | None:
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        data = dict(value)
        billing_value = data.get("billing") or data.get("billing_context")
        if billing_value is None and any(
            data.get(key)
            for key in (
                "user_id",
                "billing_user_id",
                "principal_id",
                "task_id",
                "task_scope_id",
                "billing_task_id",
            )
        ):
            billing_value = data
        return cls(
            trace_id=data.get("trace_id"),
            logical_call_id=data.get("logical_call_id") or data.get("call_id"),
            parent_logical_call_id=data.get("parent_logical_call_id"),
            session_id=data.get("session_id"),
            conversation_id=data.get("conversation_id"),
            agent_id=data.get("agent_id"),
            source_service=data.get("source_service"),
            operation=data.get("operation"),
            billing=LLMBillingContext.from_value(billing_value),
            metadata=dict(data.get("metadata") or {}),
        )

    def merge(self, overlay: LLMTraceContext | None) -> LLMTraceContext:
        if overlay is None:
            return self
        crosses_principal_boundary = bool(
            self.billing
            and overlay.billing
            and self.billing.principal_type != overlay.billing.principal_type
        )
        if crosses_principal_boundary:
            # Never let a default/ambient user identity bleed into an explicit
            # platform observation scope (or vice versa).  The trace/session
            # lineage is part of that same security boundary, so the explicit
            # overlay replaces the whole context instead of truthy-merging
            # absent session/conversation fields from the user scope.
            return overlay
        elif self.billing and overlay.billing:
            billing = self.billing.merge(overlay.billing)
        else:
            billing = overlay.billing or self.billing
        return LLMTraceContext(
            trace_id=overlay.trace_id or self.trace_id,
            logical_call_id=overlay.logical_call_id or self.logical_call_id,
            parent_logical_call_id=(overlay.parent_logical_call_id or self.parent_logical_call_id),
            session_id=overlay.session_id or self.session_id,
            conversation_id=overlay.conversation_id or self.conversation_id,
            agent_id=overlay.agent_id or self.agent_id,
            source_service=overlay.source_service or self.source_service,
            operation=overlay.operation or self.operation,
            billing=billing,
            metadata={**dict(self.metadata), **dict(overlay.metadata)},
        )

    def with_updates(self, **updates: Any) -> LLMTraceContext:
        metadata = updates.pop("metadata", None)
        billing = updates.pop("billing", None)
        updated = replace(
            self,
            **{key: value for key, value in updates.items() if value is not None},
        )
        if metadata is not None:
            updated = replace(updated, metadata={**dict(self.metadata), **dict(metadata)})
        if billing is not None:
            billing_context = LLMBillingContext.from_value(billing)
            merged_billing = (
                self.billing.merge(billing_context) if self.billing else billing_context
            )
            updated = replace(updated, billing=merged_billing)
        return updated

    def for_logical_call(
        self,
        *,
        operation: str,
        logical_call_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        force_new: bool = False,
    ) -> LLMTraceContext:
        call_id = logical_call_id
        if not call_id and not force_new:
            call_id = self.logical_call_id
        if not call_id:
            call_id = f"llm_call_{uuid4().hex}"
        return self.with_updates(
            trace_id=self.trace_id or f"llm_trace_{uuid4().hex}",
            logical_call_id=call_id,
            operation=operation,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        billing = self.billing.to_dict() if self.billing else None
        return {
            "trace_id": self.trace_id,
            "logical_call_id": self.logical_call_id,
            "parent_logical_call_id": self.parent_logical_call_id,
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "agent_id": self.agent_id,
            "source_service": self.source_service,
            "operation": self.operation,
            "billing_user_id": billing.get("billing_user_id") if billing else None,
            "actor_user_id": billing.get("actor_user_id") if billing else None,
            "owner_user_id": billing.get("owner_user_id") if billing else None,
            "principal_id": billing.get("principal_id") if billing else None,
            "task_scope_type": billing.get("task_scope_type") if billing else None,
            "task_scope_id": billing.get("task_scope_id") if billing else None,
            "billing_task_id": billing.get("billing_task_id") if billing else None,
            "billing_context": billing,
            "metadata": redact_llm_payload(dict(self.metadata)),
        }


_CURRENT_LLM_CONTEXT: ContextVar[LLMTraceContext | None] = ContextVar(
    "usmsb_current_llm_context",
    default=None,
)


def get_llm_context() -> LLMTraceContext | None:
    return _CURRENT_LLM_CONTEXT.get()


def resolve_llm_context(
    explicit: LLMTraceContext | Mapping[str, Any] | None = None,
    *,
    default: LLMTraceContext | Mapping[str, Any] | None = None,
) -> LLMTraceContext:
    result = LLMTraceContext.from_value(default) or LLMTraceContext()
    ambient = get_llm_context()
    if ambient:
        result = result.merge(ambient)
    overlay = LLMTraceContext.from_value(explicit)
    if overlay:
        result = result.merge(overlay)
    return result


def platform_observation_context(
    *,
    provider: str,
    operation: str,
    default: LLMTraceContext | Mapping[str, Any] | None = None,
) -> LLMTraceContext:
    """Create an uncharged task scope for SDK health/control-plane probes."""

    # Deliberately do not call ``resolve_llm_context`` here: it reads the
    # ambient ContextVar and could attach a user's trace/session/conversation
    # to an initialization or health probe.  Only runtime-instance identity is
    # safe to inherit from an explicit default.
    configured = LLMTraceContext.from_value(default) or LLMTraceContext()
    # OPC's llm_billing_tasks.id is String(36); keep the canonical UUID form.
    scope_id = str(uuid4())
    trace_id = f"llm_trace_{uuid4().hex}"
    configured_platform = (
        configured.billing
        if configured.billing and configured.billing.principal_type == "platform"
        else None
    )
    billing = LLMBillingContext(
        principal_id=(
            configured_platform.principal_id
            if configured_platform and configured_platform.principal_id
            else f"platform:{provider}"
        ),
        principal_type="platform",
        billing_task_id=scope_id,
        task_scope_type="logical_call",
        task_scope_id=scope_id,
        admission_status="bypassed_platform",
        pricing_policy_id="platform.observation",
        trace_id=trace_id,
        metadata={"provider": provider, "operation": operation},
    )
    return LLMTraceContext(
        trace_id=trace_id,
        logical_call_id=f"llm_call_{uuid4().hex}",
        agent_id=configured.agent_id,
        source_service=configured.source_service or "usmsb-sdk",
        operation=operation,
        billing=billing,
        metadata={
            key: value
            for key, value in dict(configured.metadata).items()
            if key in {"source_instance_id", "runtime_id", "deployment_id"}
        },
    )


def update_llm_context(**updates: Any) -> Token[LLMTraceContext | None]:
    """Update the current task context; callers may later reset the token."""

    current = get_llm_context() or LLMTraceContext()
    return _CURRENT_LLM_CONTEXT.set(current.with_updates(**updates))


@contextmanager
def llm_context_scope(
    context: LLMTraceContext | Mapping[str, Any] | None = None,
    *,
    default: LLMTraceContext | Mapping[str, Any] | None = None,
) -> Iterator[LLMTraceContext]:
    resolved = resolve_llm_context(context, default=default)
    token = _CURRENT_LLM_CONTEXT.set(resolved)
    try:
        yield resolved
    finally:
        _CURRENT_LLM_CONTEXT.reset(token)


@dataclass(frozen=True, slots=True)
class LLMUsage:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0
    source: str = "unavailable"
    raw: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_value(cls, value: Any, *, source: str = "provider_reported") -> LLMUsage:
        # Provider responses can contain multi-megabyte text/tool payloads.
        # Inspect only the small usage projection instead of JSON-normalizing
        # the entire response on the completion hot path.
        usage_field_names = {
            "input_tokens",
            "prompt_tokens",
            "promptTokens",
            "inputTokens",
            "promptTokenCount",
            "prompt_tokens_count",
            "output_tokens",
            "completion_tokens",
            "completionTokens",
            "outputTokens",
            "completionTokenCount",
            "completion_tokens_count",
            "total_tokens",
            "totalTokens",
            "totalTokenCount",
            "cached_input_tokens",
            "cache_read_input_tokens",
            "cached_tokens",
            "reasoning_tokens",
            "thinking_tokens",
            "prompt_tokens_details",
            "input_tokens_details",
            "completion_tokens_details",
            "output_tokens_details",
            "source",
        }
        if isinstance(value, Mapping):
            safe: Mapping[str, Any] = value
        else:
            candidate = getattr(value, "usage", None)
            if candidate is None:
                candidate = getattr(value, "usage_metadata", None)
            if candidate is None:
                # OpenHarness and several SDKs expose their usage object
                # directly (for example ``usage.input_tokens``), rather than
                # wrapping it in another ``usage`` attribute.  Read only the
                # known token fields so a response-like object cannot make the
                # completion hot path serialize its full generated payload.
                candidate = {
                    name: item
                    for name in usage_field_names
                    if (item := getattr(value, name, None)) is not None
                }
            safe_value = _json_safe(candidate) if candidate is not None else {}
            safe = safe_value if isinstance(safe_value, Mapping) else {}
        if isinstance(safe.get("usage"), Mapping):
            usage = dict(safe["usage"])
        elif isinstance(safe.get("usage_metadata"), Mapping):
            usage = dict(safe["usage_metadata"])
        elif any(key in safe for key in usage_field_names):
            usage = {key: safe[key] for key in usage_field_names if key in safe}
        else:
            usage = {}

        input_tokens = _as_non_negative_int(
            _first_present(
                usage,
                (
                    "input_tokens",
                    "prompt_tokens",
                    "promptTokens",
                    "inputTokens",
                    "promptTokenCount",
                    "prompt_tokens_count",
                ),
            )
        )
        output_tokens = _as_non_negative_int(
            _first_present(
                usage,
                (
                    "output_tokens",
                    "completion_tokens",
                    "completionTokens",
                    "outputTokens",
                    "completionTokenCount",
                    "completion_tokens_count",
                ),
            )
        )
        total_tokens = _as_non_negative_int(
            _first_present(usage, ("total_tokens", "totalTokens", "totalTokenCount"))
        )
        if not total_tokens:
            total_tokens = input_tokens + output_tokens

        input_details = usage.get("prompt_tokens_details") or usage.get("input_tokens_details")
        output_details = usage.get("completion_tokens_details") or usage.get(
            "output_tokens_details"
        )
        cached_input_tokens = _as_non_negative_int(
            _first_present(
                usage,
                (
                    "cached_input_tokens",
                    "cache_read_input_tokens",
                    "cached_tokens",
                ),
            )
        )
        if not cached_input_tokens and isinstance(input_details, Mapping):
            cached_input_tokens = _as_non_negative_int(
                _first_present(input_details, ("cached_tokens", "cache_read_tokens"))
            )
        reasoning_tokens = _as_non_negative_int(
            _first_present(usage, ("reasoning_tokens", "thinking_tokens"))
        )
        if not reasoning_tokens and isinstance(output_details, Mapping):
            reasoning_tokens = _as_non_negative_int(
                _first_present(output_details, ("reasoning_tokens", "thinking_tokens"))
            )

        has_provider_usage = bool(usage) and any(
            key in usage
            for key in (
                "input_tokens",
                "prompt_tokens",
                "promptTokens",
                "output_tokens",
                "completion_tokens",
                "completionTokens",
                "total_tokens",
                "totalTokens",
                "totalTokenCount",
            )
        )
        total_only_unallocated = bool(total_tokens) and not input_tokens and not output_tokens
        usage_source = str(
            usage.get("source")
            or (
                "total_only_unallocated"
                if total_only_unallocated
                else source if has_provider_usage else "unavailable"
            )
        )
        return cls(
            input_tokens=input_tokens,
            cached_input_tokens=cached_input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            total_tokens=total_tokens,
            source=usage_source,
            raw=redact_llm_payload(usage),
        )

    @classmethod
    def from_embedding(
        cls,
        value: Any,
        *,
        source: str = "provider_reported",
    ) -> LLMUsage:
        """Normalize embedding usage, whose tokens are all input tokens.

        Several OpenAI-compatible embedding providers only return
        ``total_tokens``.  Treating that value as an unclassified total makes
        input-token billing silently miss the entire embedding request.  An
        embedding has no generated-token side, so a total-only report is an
        unambiguous input-token count.
        """

        usage = cls.from_value(value, source=source)
        if usage.total_tokens and not usage.input_tokens and not usage.output_tokens:
            return replace(
                usage,
                input_tokens=usage.total_tokens,
                source=source,
            )
        return usage

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "output_tokens": self.output_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "total_tokens": self.total_tokens,
            "source": self.source,
            "raw": redact_llm_payload(dict(self.raw)),
        }


@dataclass(slots=True)
class LLMProviderCallDetail:
    provider_attempt_id: str
    event_id: str
    provider: str
    model: str
    operation: str
    status: str
    requested_at: datetime
    context: LLMTraceContext
    request_payload: Any = None
    request_provisional_id: str | None = None
    request_hash: str | None = None
    request_uri: str | None = None
    request_artifact_status: str = "not_applicable"
    completed_at: datetime | None = None
    duration_ms: float | None = None
    response_payload: Any = None
    response_provisional_id: str | None = None
    response_hash: str | None = None
    response_uri: str | None = None
    response_artifact_status: str = "not_applicable"
    response_id: str | None = None
    usage: LLMUsage = field(default_factory=LLMUsage)
    error_type: str | None = None
    error_message: str | None = None
    http_status: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_attempt_id": self.provider_attempt_id,
            "event_id": self.event_id,
            "provider": self.provider,
            "model": self.model,
            "operation": self.operation,
            "status": self.status,
            "requested_at": _iso(self.requested_at),
            "completed_at": _iso(self.completed_at),
            "duration_ms": self.duration_ms,
            "trace_context": self.context.to_dict(),
            "request_payload": self.request_payload,
            "request_provisional_id": self.request_provisional_id,
            "request_hash": self.request_hash,
            "request_uri": self.request_uri,
            "request_artifact_status": self.request_artifact_status,
            "response_payload": self.response_payload,
            "response_provisional_id": self.response_provisional_id,
            "response_hash": self.response_hash,
            "response_uri": self.response_uri,
            "response_artifact_status": self.response_artifact_status,
            "response_id": self.response_id,
            "usage": self.usage.to_dict(),
            "error_type": self.error_type,
            "error_message": self.error_message,
            "http_status": self.http_status,
            "metadata": redact_llm_payload(dict(self.metadata)),
        }


_CALLBACK_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="usmsb-llm-events")


class LLMInvocationRecorder:
    """Bounded provider-attempt journal with durable production evidence.

    Provider hooks only perform bounded scalar bookkeeping and an O(1)
    ownership handoff. Redaction, JSON normalization, hashing and filesystem
    durability run on the artifact worker. Required mode fails a new Provider
    request closed when that worker is known unhealthy or its bounded admission
    queue is full. The accepted enqueue-before-WAL crash window is explicit;
    graceful shutdown drains every admitted attempt and its terminal evidence.
    """

    def __init__(
        self,
        event_callback: LLMEventCallback | None = None,
        *,
        default_context: LLMTraceContext | Mapping[str, Any] | None = None,
        max_calls: int = 1000,
        max_events: int = 3000,
        capture_payloads: bool = True,
        artifact_spool: LLMArtifactSpool | None = None,
        artifact_spool_dir: str | None = None,
    ) -> None:
        self.default_context = LLMTraceContext.from_value(default_context)
        self.max_calls = max(1, int(max_calls))
        self.capture_payloads = bool(capture_payloads)
        self._calls: OrderedDict[str, LLMProviderCallDetail] = OrderedDict()
        self._events: deque[dict[str, Any]] = deque(maxlen=max(3, int(max_events)))
        self._callbacks: list[LLMEventCallback] = []
        if event_callback:
            self._callbacks.append(event_callback)
        self._lock = threading.RLock()
        self._owns_artifact_spool = False
        self._artifact_spool_dir = artifact_spool_dir
        self.artifact_spool = artifact_spool
        if artifact_spool is not None and artifact_spool_dir is not None:
            logger.warning(
                "Both artifact_spool and artifact_spool_dir were supplied; using the "
                "explicit artifact_spool instance"
            )
        if self.artifact_spool is None:
            try:
                if artifact_spool_dir is not None:
                    self.artifact_spool = LLMArtifactSpool(artifact_spool_dir)
                    self._owns_artifact_spool = True
                else:
                    self.artifact_spool = get_shared_llm_artifact_spool_from_env()
            except Exception:
                # Artifact persistence is observational.  Invalid/unavailable
                # storage must be visible in logs but must not prevent an LLM
                # request from executing.
                logger.warning(
                    "Could not initialize the durable LLM artifact spool; continuing "
                    "with hash-only telemetry",
                    exc_info=True,
                )
                self.artifact_spool = None
                if llm_artifact_spool_required():
                    raise
        if self.artifact_spool is not None:
            self.artifact_spool.add_resolution_callback(
                self._on_artifact_resolved,
                replay_existing=True,
            )

    def add_callback(self, callback: LLMEventCallback) -> None:
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def remove_callback(self, callback: LLMEventCallback) -> None:
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    @property
    def has_event_callbacks(self) -> bool:
        """Whether provider events have an outward non-blocking projection."""

        with self._lock:
            return bool(self._callbacks)

    def set_default_context(
        self,
        context: LLMTraceContext | Mapping[str, Any] | None,
    ) -> None:
        self.default_context = LLMTraceContext.from_value(context)

    def requested(
        self,
        *,
        provider: str,
        model: str,
        operation: str,
        request_payload: Any,
        context: LLMTraceContext | Mapping[str, Any] | None = None,
        provider_attempt_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> str:
        resolved = resolve_llm_context(context, default=self.default_context)
        if not resolved.logical_call_id:
            resolved = resolved.for_logical_call(operation=operation)
        else:
            resolved = resolved.with_updates(operation=operation)
        attempt_id = provider_attempt_id or f"llm_pa_{uuid4().hex}"
        now = _utc_now()
        request_provisional_id = (
            f"llm_artifact_{uuid4().hex}" if request_payload is not None else None
        )
        detail = LLMProviderCallDetail(
            provider_attempt_id=attempt_id,
            event_id=f"llm_evt_{uuid4().hex}",
            provider=provider,
            model=model,
            operation=operation,
            status=LLMProviderAttemptStatus.REQUESTED.value,
            requested_at=now,
            context=resolved,
            request_provisional_id=request_provisional_id,
            request_artifact_status=(
                "provisional" if request_provisional_id else "not_applicable"
            ),
            metadata=dict(metadata or {}),
        )
        with self._lock:
            self._calls[attempt_id] = detail
            self._calls.move_to_end(attempt_id)
            while len(self._calls) > self.max_calls:
                self._calls.popitem(last=False)
        if llm_artifact_spool_required():
            try:
                if request_provisional_id is None:
                    raise LLMArtifactSpoolError(
                        "required LLM artifact evidence needs a request payload"
                    )
                spool = self.artifact_spool
                if spool is None:
                    raise LLMArtifactSpoolError(
                        "required LLM artifact spool is unavailable"
                    )
                # Transfer the event and exact request by reference. The worker
                # later writes both under one stable relation id; no
                # payload-sized work or filesystem I/O happens here.
                requested_event = self._build_event_payload(
                    LLMProviderEventType.REQUESTED,
                    detail,
                )
                reference = spool.enqueue_payload(
                    request_payload,
                    provider_attempt_id=detail.provider_attempt_id,
                    artifact_kind="request",
                    redactor=redact_llm_payload,
                    provisional_id=request_provisional_id,
                    capture_payload=self.capture_payloads,
                    invocation_event=requested_event,
                    provider_phase="requested",
                    require_healthy=True,
                )
                if reference.enqueue_status != "provisional":
                    raise LLMArtifactSpoolError(
                        "required LLM artifact handoff rejected before Provider "
                        f"dispatch: {reference.enqueue_status}"
                    )
            except Exception as exc:
                # Nothing has crossed the Provider boundary yet.  Remove the
                # provisional in-memory attempt so a rejected admission cannot
                # later be mistaken for a physical Provider request.
                with self._lock:
                    if self._calls.get(attempt_id) is detail:
                        self._calls.pop(attempt_id, None)
                if isinstance(exc, LLMArtifactSpoolError):
                    raise
                raise LLMArtifactSpoolError(
                    "could not enqueue required LLM request evidence"
                ) from exc
        else:
            self._emit(LLMProviderEventType.REQUESTED, detail)
            if request_provisional_id:
                self._queue_artifact(
                    payload=request_payload,
                    detail=detail,
                    artifact_kind="request",
                    provisional_id=request_provisional_id,
                )
        return attempt_id

    def completed(
        self,
        provider_attempt_id: str,
        *,
        response_payload: Any,
        usage: LLMUsage | Mapping[str, Any] | Any | None = None,
        response_id: str | None = None,
        http_status: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        now = _utc_now()
        normalized_usage = self._normalize_usage_fast(
            usage if usage is not None else response_payload
        )
        resolved_response_id = response_id or extract_provider_response_id(response_payload)
        response_provisional_id = (
            f"llm_artifact_{uuid4().hex}"
            if response_payload is not None or llm_artifact_spool_required()
            else None
        )
        with self._lock:
            detail = self._calls.get(provider_attempt_id)
            if detail is None:
                logger.warning("Unknown LLM provider attempt completed: %s", provider_attempt_id)
                return
            detail.status = LLMProviderAttemptStatus.COMPLETED.value
            detail.completed_at = now
            detail.duration_ms = max(0.0, (now - detail.requested_at).total_seconds() * 1000)
            detail.response_provisional_id = response_provisional_id
            detail.response_artifact_status = (
                "provisional" if response_provisional_id else "not_applicable"
            )
            detail.response_id = resolved_response_id
            detail.usage = normalized_usage
            detail.http_status = http_status
            detail.metadata = {**dict(detail.metadata), **dict(metadata or {})}
        self._record_terminal_event_with_artifact(
            event_type=LLMProviderEventType.COMPLETED,
            detail=detail,
            response_payload=response_payload,
            response_provisional_id=response_provisional_id,
        )

    def failed(
        self,
        provider_attempt_id: str,
        error: BaseException | str,
        *,
        response_payload: Any = None,
        usage: LLMUsage | Mapping[str, Any] | Any | None = None,
        response_id: str | None = None,
        http_status: int | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        now = _utc_now()
        normalized_usage = self._normalize_usage_fast(
            usage if usage is not None else response_payload
        )
        resolved_response_id = response_id or extract_provider_response_id(response_payload)
        response_provisional_id = (
            f"llm_artifact_{uuid4().hex}"
            if response_payload is not None or llm_artifact_spool_required()
            else None
        )
        with self._lock:
            detail = self._calls.get(provider_attempt_id)
            if detail is None:
                logger.warning("Unknown LLM provider attempt failed: %s", provider_attempt_id)
                return
            detail.status = LLMProviderAttemptStatus.FAILED.value
            detail.completed_at = now
            detail.duration_ms = max(0.0, (now - detail.requested_at).total_seconds() * 1000)
            detail.response_provisional_id = response_provisional_id
            detail.response_artifact_status = (
                "provisional" if response_provisional_id else "not_applicable"
            )
            detail.response_id = resolved_response_id
            detail.usage = normalized_usage
            detail.error_type = (
                type(error).__name__ if isinstance(error, BaseException) else "Error"
            )
            detail.error_message = str(error)
            detail.http_status = http_status
            detail.metadata = {**dict(detail.metadata), **dict(metadata or {})}
        self._record_terminal_event_with_artifact(
            event_type=LLMProviderEventType.FAILED,
            detail=detail,
            response_payload=response_payload,
            response_provisional_id=response_provisional_id,
        )

    def get_call(self, provider_attempt_id: str) -> dict[str, Any] | None:
        with self._lock:
            detail = self._calls.get(provider_attempt_id)
            return detail.to_dict() if detail else None

    def recent_calls(
        self,
        *,
        limit: int = 100,
        status: str | None = None,
        task_id: str | None = None,
        billing_task_id: str | None = None,
        task_scope_type: str | None = None,
        task_scope_id: str | None = None,
        logical_call_id: str | None = None,
        trace_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        with self._lock:
            calls = [detail.to_dict() for detail in reversed(self._calls.values())]
        result: list[dict[str, Any]] = []
        for call in calls:
            trace_context = call.get("trace_context") or {}
            billing = trace_context.get("billing_context") or {}
            if status and call.get("status") != status:
                continue
            if task_id and task_id not in {
                billing.get("task_scope_id"),
                billing.get("billing_task_id"),
            }:
                continue
            if billing_task_id and billing.get("billing_task_id") != billing_task_id:
                continue
            if task_scope_type and billing.get("task_scope_type") != task_scope_type:
                continue
            if task_scope_id and billing.get("task_scope_id") != task_scope_id:
                continue
            if logical_call_id and trace_context.get("logical_call_id") != logical_call_id:
                continue
            if trace_id and trace_context.get("trace_id") != trace_id:
                continue
            result.append(call)
            if len(result) >= limit:
                break
        return result

    def recent_events(self, *, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            if limit <= 0:
                return []
            return list(self._events)[-limit:]

    def drain_events(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        with self._lock:
            count = len(self._events) if limit is None else min(max(0, limit), len(self._events))
            return [self._events.popleft() for _ in range(count)]

    def task_terminal(
        self,
        *,
        context: LLMTraceContext | Mapping[str, Any],
        status: str,
        error: BaseException | str | None = None,
    ) -> None:
        """Emit an explicit logical-task terminal event for a bounded SDK scope."""

        normalized_status = str(status).lower()
        if normalized_status not in {"completed", "failed", "cancelled"}:
            raise ValueError(f"Unsupported LLM task terminal status: {status}")
        resolved = resolve_llm_context(context, default=self.default_context)
        billing = resolved.billing.to_dict(include_sensitive=True) if resolved.billing else {}
        if billing and not billing.get("trace_id"):
            billing["trace_id"] = resolved.trace_id
        now = _utc_now()
        payload = {
            "schema": "opc.llm.invocation-event.v1",
            "schema_version": "1.0",
            "event_id": f"llm_evt_{uuid4().hex}",
            "event_type": f"llm.task.{normalized_status}",
            "occurred_at": now.timestamp(),
            "occurred_at_iso": _iso(now),
            "source_service": resolved.source_service or "usmsb-sdk",
            "source_instance_id": resolved.metadata.get("source_instance_id"),
            "provider_attempt_id": None,
            "logical_call_id": resolved.logical_call_id,
            "trace_id": resolved.trace_id,
            "billing": billing,
            "lineage": {
                "trace_id": resolved.trace_id or billing.get("trace_id"),
                "logical_call_id": resolved.logical_call_id,
                "parent_logical_call_id": resolved.parent_logical_call_id,
                "provider_attempt_id": None,
                "provider_response_id": None,
                "session_id": resolved.session_id,
                "conversation_id": resolved.conversation_id,
                "agent_id": resolved.agent_id,
            },
            "provider": {
                "name": None,
                "model": None,
                "status": normalized_status,
                "http_status": None,
                "latency_ms": None,
                "operation": resolved.operation,
            },
            "usage": LLMUsage().to_dict(),
            "artifacts": {
                "request_sha256": None,
                "response_sha256": None,
                "request_uri": None,
                "response_uri": None,
            },
            "result": {
                "operation": resolved.operation,
                "classification": normalized_status,
                "error_class": type(error).__name__ if isinstance(error, BaseException) else None,
                "error_message": _bounded_text(error),
            },
            "model": None,
            "operation": resolved.operation,
            "status": normalized_status,
        }
        self._publish(payload)

    @property
    def artifact_spool_enabled(self) -> bool:
        """Whether durable redacted payload artifacts are configured."""

        return bool(
            self.artifact_spool is not None
            and not self.artifact_spool.diagnostics["closed"]
        )

    def reopen_artifacts(self) -> bool:
        """Reacquire durable storage at application start after a prior shutdown."""

        if self.artifact_spool_enabled:
            return True
        try:
            if self._artifact_spool_dir is not None:
                self.artifact_spool = LLMArtifactSpool(self._artifact_spool_dir)
                self._owns_artifact_spool = True
            else:
                self.artifact_spool = get_shared_llm_artifact_spool_from_env()
                self._owns_artifact_spool = False
            if self.artifact_spool is not None:
                self.artifact_spool.add_resolution_callback(
                    self._on_artifact_resolved,
                    replay_existing=True,
                )
            return self.artifact_spool is not None or not llm_artifact_spool_required()
        except Exception:
            logger.warning("Could not reopen the durable LLM artifact spool", exc_info=True)
            self.artifact_spool = None
            if llm_artifact_spool_required():
                raise
            return False

    def flush_artifacts(self, timeout: float | None = None) -> bool:
        """Wait for queued artifact writes; safe to call during graceful shutdown."""

        if self.artifact_spool is None:
            return True
        return self.artifact_spool.flush(timeout=timeout)

    async def flush_artifacts_async(self, timeout: float | None = None) -> bool:
        """Event-loop-safe form of :meth:`flush_artifacts`."""

        if self.artifact_spool is None:
            return True
        return await self.artifact_spool.flush_async(timeout=timeout)

    def close_artifacts(self, timeout: float | None = None) -> bool:
        """Drain and close the recorder-owned spool.

        An explicitly injected shared spool remains owned by its caller and is
        only flushed here.  Recorders created from the environment or from
        ``artifact_spool_dir`` own and close their worker.
        """

        if self.artifact_spool is None:
            return True
        if not self._owns_artifact_spool:
            return self.artifact_spool.flush(timeout=timeout)
        spool = self.artifact_spool
        result = spool.close(timeout=timeout)
        spool.remove_resolution_callback(self._on_artifact_resolved)
        if bool(spool.diagnostics["closed"]):
            self.artifact_spool = None
            self._owns_artifact_spool = False
        return result

    async def close_artifacts_async(self, timeout: float | None = None) -> bool:
        """Event-loop-safe form of :meth:`close_artifacts`."""

        if self.artifact_spool is None:
            return True
        if not self._owns_artifact_spool:
            return await self.artifact_spool.flush_async(timeout=timeout)
        spool = self.artifact_spool
        result = await spool.aclose(timeout=timeout)
        spool.remove_resolution_callback(self._on_artifact_resolved)
        if bool(spool.diagnostics["closed"]):
            self.artifact_spool = None
            self._owns_artifact_spool = False
        return result

    def _queue_artifact(
        self,
        *,
        payload: Any,
        detail: LLMProviderCallDetail,
        artifact_kind: str,
        provisional_id: str,
    ) -> None:
        """Transfer artifact ownership without inspecting a potentially large payload."""

        spool = self.artifact_spool
        if spool is not None:
            reference = spool.enqueue_payload(
                payload,
                provider_attempt_id=detail.provider_attempt_id,
                artifact_kind=artifact_kind,
                redactor=redact_llm_payload,
                provisional_id=provisional_id,
                capture_payload=self.capture_payloads,
            )
            if reference.enqueue_status == "provisional":
                return
            resolution = LLMArtifactResolution(
                provisional_id=provisional_id,
                provider_attempt_id=detail.provider_attempt_id,
                artifact_kind=artifact_kind,
                sha256=None,
                uri=None,
                status=reference.enqueue_status,
                resolved_at=_utc_now().timestamp(),
            )
            self._on_artifact_resolved(resolution)
            return

        # SDK-only consumers may intentionally run without persistent storage.
        # Hashing/redaction still happens away from the Provider thread.
        _CALLBACK_EXECUTOR.submit(
            self._resolve_hash_only,
            payload,
            detail.provider_attempt_id,
            artifact_kind,
            provisional_id,
            self.capture_payloads,
        )

    def _record_terminal_event_with_artifact(
        self,
        *,
        event_type: LLMProviderEventType,
        detail: LLMProviderCallDetail,
        response_payload: Any,
        response_provisional_id: str | None,
    ) -> None:
        """Record one terminal event without corrupting a completed Provider call.

        In required mode the Provider response and terminal event are handed
        off together without waiting for redaction, serialization or disk.
        Queue pressure cannot drop an already-admitted terminal: the spool uses
        a FIFO no-eviction spill. A later persistence failure marks the spool
        unhealthy so the next request fails before Provider dispatch, while
        this Provider result remains authoritative.
        """

        if response_provisional_id and llm_artifact_spool_required():
            terminal_event = self._build_event_payload(event_type, detail)
            artifact_payload = response_payload
            if artifact_payload is None:
                # A network/provider failure can have no response body. Keep a
                # small explicit source artifact so the terminal event still
                # crosses the same replayable relation and releases the
                # accepted-attempt shutdown lease.
                artifact_payload = {
                    "schema": "usmsb.llm-missing-provider-response.v1",
                    "provider_attempt_id": detail.provider_attempt_id,
                    "status": detail.status,
                    "error_type": detail.error_type,
                    "reason": "provider_response_unavailable",
                }
            try:
                spool = self.artifact_spool
                if spool is None:
                    raise LLMArtifactSpoolError(
                        "required LLM artifact spool is unavailable"
                    )
                reference = spool.enqueue_payload(
                    artifact_payload,
                    provider_attempt_id=detail.provider_attempt_id,
                    artifact_kind="response",
                    redactor=redact_llm_payload,
                    provisional_id=response_provisional_id,
                    capture_payload=self.capture_payloads,
                    invocation_event=terminal_event,
                    provider_phase="terminal",
                )
                if reference.enqueue_status != "provisional":
                    raise LLMArtifactSpoolError(
                        "required terminal LLM artifact handoff rejected: "
                        f"{reference.enqueue_status}"
                    )
                return
            except Exception as exc:
                logger.error(
                    "Could not hand off required terminal LLM evidence for %s; "
                    "future Provider admissions will fail closed",
                    detail.provider_attempt_id,
                    exc_info=True,
                )
                with self._lock:
                    detail.response_artifact_status = "persist_failed"
                    detail.metadata = {
                        **dict(detail.metadata),
                        "artifact_persistence_error": type(exc).__name__,
                    }
                # The Provider has already returned.  Project the terminal fact
                # best-effort so callers do not lose their valid response.
                self._emit(event_type, detail)
                self._on_artifact_resolved(
                    LLMArtifactResolution(
                        provisional_id=response_provisional_id,
                        provider_attempt_id=detail.provider_attempt_id,
                        artifact_kind="response",
                        sha256=None,
                        uri=None,
                        status="persist_failed",
                        resolved_at=_utc_now().timestamp(),
                        error=f"{type(exc).__name__}: {exc}"[:1000],
                    )
                )
                return

        self._emit(event_type, detail)
        if response_provisional_id:
            self._queue_artifact(
                payload=response_payload,
                detail=detail,
                artifact_kind="response",
                provisional_id=response_provisional_id,
            )

    def _resolve_hash_only(
        self,
        payload: Any,
        provider_attempt_id: str,
        artifact_kind: str,
        provisional_id: str,
        capture_payload: bool,
    ) -> None:
        try:
            redacted = redact_llm_payload(payload)
            content = canonical_artifact_bytes(redacted)
            resolution = LLMArtifactResolution(
                provisional_id=provisional_id,
                provider_attempt_id=provider_attempt_id,
                artifact_kind=artifact_kind,
                sha256=hashlib.sha256(content).hexdigest(),
                uri=None,
                status="hash_only",
                resolved_at=_utc_now().timestamp(),
                captured_payload=(
                    redacted if capture_payload and len(content) <= 64 * 1024 else None
                ),
            )
        except Exception as exc:
            resolution = LLMArtifactResolution(
                provisional_id=provisional_id,
                provider_attempt_id=provider_attempt_id,
                artifact_kind=artifact_kind,
                sha256=None,
                uri=None,
                status="prepare_failed",
                resolved_at=_utc_now().timestamp(),
                error=f"{type(exc).__name__}: {exc}"[:1000],
            )
        self._on_artifact_resolved(resolution)

    def _on_artifact_resolved(self, resolution: LLMArtifactResolution) -> None:
        with self._lock:
            detail = self._calls.get(resolution.provider_attempt_id)
            if detail is not None:
                if resolution.artifact_kind == "request":
                    detail.request_hash = resolution.sha256
                    detail.request_uri = resolution.uri
                    detail.request_artifact_status = resolution.status
                    if resolution.captured_payload is not None:
                        detail.request_payload = resolution.captured_payload
                elif resolution.artifact_kind == "response":
                    detail.response_hash = resolution.sha256
                    detail.response_uri = resolution.uri
                    detail.response_artifact_status = resolution.status
                    if resolution.captured_payload is not None:
                        detail.response_payload = resolution.captured_payload
        if resolution.invocation_event is not None:
            # The event and exact artifact crossed the same local durable
            # boundary. Replaying a relation after a crash re-emits the stable
            # event_id; downstream accounting deduplicates it idempotently.
            self._publish(dict(resolution.invocation_event))
        self._publish_artifact_resolution(resolution)

    @staticmethod
    def _normalize_usage_fast(value: Any) -> LLMUsage:
        if isinstance(value, LLMUsage):
            return value
        if isinstance(value, Mapping):
            return LLMUsage.from_value(value)
        usage = getattr(value, "usage", None)
        if usage is None:
            usage = getattr(value, "usage_metadata", None)
        return LLMUsage.from_value(usage)

    def _publish_artifact_resolution(self, resolution: LLMArtifactResolution) -> None:
        payload = {
            "schema": "opc.llm.invocation-event.v1",
            "schema_version": "1.0",
            "event_id": (
                "llm_artifact_evt_"
                f"{resolution.provisional_id.removeprefix('llm_artifact_')}"
            ),
            "event_type": LLMProviderEventType.ARTIFACT_RESOLVED.value,
            "occurred_at": resolution.resolved_at,
            "occurred_at_iso": _iso(datetime.fromtimestamp(resolution.resolved_at, UTC)),
            "source_service": "usmsb-sdk-artifact-spool",
            "provider_attempt_id": resolution.provider_attempt_id,
            "logical_call_id": None,
            "trace_id": None,
            "billing": {},
            "lineage": {
                "provider_attempt_id": resolution.provider_attempt_id,
            },
            "provider": {},
            "usage": LLMUsage().to_dict(),
            "artifacts": {
                "artifact_kind": resolution.artifact_kind,
                "provisional_id": resolution.provisional_id,
                "sha256": resolution.sha256,
                "uri": resolution.uri,
                "status": resolution.status,
            },
            "result": {
                "classification": resolution.status,
                "error_message": _bounded_text(resolution.error),
            },
            "status": resolution.status,
        }
        self._publish(payload)

    def _build_event_payload(
        self,
        event_type: LLMProviderEventType,
        detail: LLMProviderCallDetail,
    ) -> dict[str, Any]:
        occurred = (
            detail.requested_at
            if event_type is LLMProviderEventType.REQUESTED
            else detail.completed_at or _utc_now()
        )
        billing = (
            detail.context.billing.to_dict(include_sensitive=True) if detail.context.billing else {}
        )
        if billing and not billing.get("trace_id"):
            billing["trace_id"] = detail.context.trace_id
        context_metadata = dict(detail.context.metadata)
        call_metadata = dict(detail.metadata)
        source_service = detail.context.source_service or "usmsb-sdk"
        response_id = detail.response_id
        payload = {
            "schema": "opc.llm.invocation-event.v1",
            "schema_version": "1.0",
            "event_id": (
                detail.event_id
                if event_type is LLMProviderEventType.REQUESTED
                else f"llm_evt_{uuid4().hex}"
            ),
            "event_type": event_type.value,
            "occurred_at": occurred.timestamp(),
            "occurred_at_iso": _iso(occurred),
            "source_service": source_service,
            "source_instance_id": context_metadata.get("source_instance_id"),
            "provider_attempt_id": detail.provider_attempt_id,
            "logical_call_id": detail.context.logical_call_id,
            "trace_id": detail.context.trace_id,
            "billing": billing,
            "lineage": {
                "trace_id": detail.context.trace_id or billing.get("trace_id"),
                "logical_call_id": detail.context.logical_call_id,
                "parent_logical_call_id": detail.context.parent_logical_call_id,
                "provider_attempt_id": detail.provider_attempt_id,
                "provider_response_id": response_id,
                "route_attempt": call_metadata.get("route_attempt")
                or call_metadata.get("transport_retry_index", 0) + 1,
                "parent_attempt_id": call_metadata.get("parent_attempt_id"),
                "repair_of_attempt_id": call_metadata.get("repair_of_attempt_id"),
                "provider_operation_key": call_metadata.get("provider_operation_key"),
                "session_id": detail.context.session_id,
                "conversation_id": detail.context.conversation_id,
                "agent_id": detail.context.agent_id,
            },
            "provider": {
                "name": detail.provider,
                "model": detail.model,
                "status": detail.status,
                "http_status": detail.http_status,
                "latency_ms": int(detail.duration_ms) if detail.duration_ms is not None else None,
                "operation": detail.operation,
            },
            "usage": detail.usage.to_dict(),
            "artifacts": {
                "request_provisional_id": detail.request_provisional_id,
                "response_provisional_id": detail.response_provisional_id,
                "request_sha256": detail.request_hash,
                "response_sha256": detail.response_hash,
                "request_uri": detail.request_uri or call_metadata.get("request_uri"),
                "response_uri": detail.response_uri or call_metadata.get("response_uri"),
                "request_status": detail.request_artifact_status,
                "response_status": detail.response_artifact_status,
            },
            "result": {
                "operation": detail.operation,
                "classification": detail.status,
                "error_class": detail.error_type,
                "error_message": _bounded_text(detail.error_message),
            },
            # Flat aliases keep older SDK callbacks source compatible.  OPC's
            # canonical projector reads the billing/lineage/provider objects.
            # Keep only small scalars here: full request/response artifacts
            # remain available from ``recent_calls`` and must not be duplicated
            # into every async event/callback payload.
            "model": detail.model,
            "operation": detail.operation,
            "status": detail.status,
        }
        return payload

    def _emit(self, event_type: LLMProviderEventType, detail: LLMProviderCallDetail) -> None:
        self._publish(self._build_event_payload(event_type, detail))

    def _publish(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self._events.append(payload)
            callbacks = tuple(self._callbacks)
        for callback in callbacks:
            self._dispatch_nowait(callback, payload)

    @staticmethod
    def _dispatch_nowait(callback: LLMEventCallback, payload: dict[str, Any]) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            _CALLBACK_EXECUTOR.submit(LLMInvocationRecorder._invoke_callback, callback, payload)
            return

        if inspect.iscoroutinefunction(callback):
            task = loop.create_task(LLMInvocationRecorder._invoke_async_callback(callback, payload))
            task.add_done_callback(LLMInvocationRecorder._consume_task_exception)
        else:
            # OPC's sink is a synchronous ``asyncio.Queue.put_nowait`` wrapper
            # and must execute on the owning event-loop thread.  ``call_soon``
            # still keeps it off the provider hot path; genuinely blocking
            # synchronous sinks should enqueue to their own worker.
            loop.call_soon(
                LLMInvocationRecorder._invoke_callback_on_loop,
                loop,
                callback,
                payload,
            )

    @staticmethod
    def _invoke_callback_on_loop(
        loop: asyncio.AbstractEventLoop,
        callback: LLMEventCallback,
        payload: dict[str, Any],
    ) -> None:
        """Invoke sync sinks and safely schedule async callable objects."""

        try:
            result = callback(payload)
            if inspect.isawaitable(result):
                task = loop.create_task(result)
                task.add_done_callback(LLMInvocationRecorder._consume_task_exception)
        except Exception:
            logger.exception("LLM event callback failed")

    @staticmethod
    async def _invoke_async_callback(
        callback: LLMEventCallback,
        payload: dict[str, Any],
    ) -> None:
        try:
            await callback(payload)
        except Exception:
            logger.exception("LLM event callback failed")

    @staticmethod
    def _invoke_callback(callback: LLMEventCallback, payload: dict[str, Any]) -> None:
        try:
            result = callback(payload)
            if inspect.isawaitable(result):
                asyncio.run(result)
        except Exception:
            logger.exception("LLM event callback failed")

    @staticmethod
    def _consume_task_exception(task: asyncio.Task[Any]) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            return
        except Exception:
            # _invoke_async_callback already logs callback exceptions.  This
            # guard covers cancellation and unexpected dispatcher failures.
            logger.debug("LLM event callback task ended with an error", exc_info=True)


def extract_provider_response_id(value: Any) -> str | None:
    if isinstance(value, Mapping):
        safe: Mapping[str, Any] = value
    else:
        for key in ("id", "request_id", "requestId", "response_id", "responseId"):
            candidate = getattr(value, key, None)
            if candidate:
                return str(candidate)
        base = getattr(value, "base_resp", None)
        safe = {"base_resp": base} if isinstance(base, Mapping) else {}
    for key in ("id", "request_id", "requestId", "response_id", "responseId"):
        candidate = safe.get(key)
        if candidate:
            return str(candidate)
    base_resp = safe.get("base_resp")
    if isinstance(base_resp, Mapping):
        for key in ("request_id", "trace_id"):
            candidate = base_resp.get(key)
            if candidate:
                return str(candidate)
    return None


__all__ = [
    "LLMBillingContext",
    "LLMEventCallback",
    "LLMInvocationRecorder",
    "LLMProviderAttemptStatus",
    "LLMProviderCallDetail",
    "LLMProviderEventType",
    "LLMTraceContext",
    "LLMUsage",
    "extract_provider_response_id",
    "get_llm_context",
    "llm_context_scope",
    "platform_observation_context",
    "redact_llm_payload",
    "resolve_llm_context",
    "update_llm_context",
]
