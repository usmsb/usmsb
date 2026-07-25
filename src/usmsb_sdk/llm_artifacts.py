"""Non-blocking durable storage for redacted LLM request/response artifacts.

Provider transports hand ownership of an opaque payload reference to this
spool and immediately receive a provisional id.  A dedicated worker performs
redaction, JSON normalization, hashing and content-addressed filesystem I/O.
The worker first persists a redacted pending envelope, so a crash can replay the
relation between ``provider_attempt_id`` and the eventual content address.  The
handoff itself is deliberately *not* a durable acknowledgement: a hard process
or node failure after ``enqueue_payload`` and before the worker fsyncs that
envelope is the explicit enqueue-before-WAL crash window.  Graceful close waits
for in-flight Provider attempts to hand off their terminal evidence and drains
all accepted work; durable pending/relation files replay after restart.

``enqueue_redacted`` remains as a compatibility API for already-redacted
control-plane callers.  Provider hot paths must use ``enqueue_payload``.
"""

from __future__ import annotations

import asyncio
import atexit
import hashlib
import json
import logging
import os
import queue
import re
import stat
import tempfile
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
from uuid import uuid4

logger = logging.getLogger(__name__)

LLM_ARTIFACT_SPOOL_DIR_ENV = "USMSB_LLM_ARTIFACT_SPOOL_DIR"
LLM_ARTIFACT_SPOOL_MAX_QUEUE_ENV = "USMSB_LLM_ARTIFACT_SPOOL_MAX_QUEUE"
LLM_ARTIFACT_SPOOL_MAX_PENDING_BYTES_ENV = "USMSB_LLM_ARTIFACT_SPOOL_MAX_PENDING_BYTES"
LLM_ARTIFACT_SPOOL_MAX_ARTIFACT_BYTES_ENV = "USMSB_LLM_ARTIFACT_SPOOL_MAX_ARTIFACT_BYTES"
LLM_ARTIFACT_SPOOL_REQUIRED_ENV = "USMSB_LLM_ARTIFACT_SPOOL_REQUIRED"
LLM_ARTIFACT_SPOOL_RETENTION_SECONDS_ENV = "USMSB_LLM_ARTIFACT_SPOOL_RETENTION_SECONDS"
LLM_ARTIFACT_SPOOL_CLEANUP_INTERVAL_SECONDS_ENV = (
    "USMSB_LLM_ARTIFACT_SPOOL_CLEANUP_INTERVAL_SECONDS"
)
DEFAULT_LLM_ARTIFACT_SPOOL_MAX_QUEUE = 1024
DEFAULT_LLM_ARTIFACT_SPOOL_MAX_PENDING_BYTES = 256 * 1024 * 1024
DEFAULT_LLM_ARTIFACT_SPOOL_MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
DEFAULT_LLM_ARTIFACT_SPOOL_RETENTION_SECONDS = 14 * 24 * 60 * 60
DEFAULT_LLM_ARTIFACT_SPOOL_CLEANUP_INTERVAL_SECONDS = 60 * 60
# Debounce CPU-heavy JSON work until the Provider thread has had a quiet
# handoff window.  This prevents a previous artifact's encoder from holding the
# GIL while a burst of requested/completed hooks is still returning.
LLM_ARTIFACT_WORKER_HANDOFF_GRACE_SECONDS = 0.05

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class LLMArtifactSpoolError(RuntimeError):
    """Raised by control-plane reads/configuration, never by provider calls."""


@dataclass(frozen=True, slots=True)
class LLMArtifactReference:
    """Content address returned synchronously when an artifact is accepted."""

    sha256: str
    uri: str | None
    enqueue_status: str = "queued"


@dataclass(frozen=True, slots=True)
class LLMArtifactProvisionalReference:
    """O(1) reference returned before payload inspection begins."""

    provisional_id: str
    enqueue_status: str = "provisional"


@dataclass(frozen=True, slots=True)
class LLMArtifactResolution:
    """Durable result of resolving one provisional provider artifact."""

    provisional_id: str
    provider_attempt_id: str
    artifact_kind: str
    sha256: str | None
    uri: str | None
    status: str
    resolved_at: float
    error: str | None = None
    captured_payload: Any = None
    # Ownership is transferred together with the payload. Do not copy a
    # potentially nested event on the Provider thread; the storage worker
    # normalizes it before crossing the durable boundary.
    invocation_event: Mapping[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": "usmsb.llm-artifact-relation.v1",
            "provisional_id": self.provisional_id,
            "provider_attempt_id": self.provider_attempt_id,
            "artifact_kind": self.artifact_kind,
            "sha256": self.sha256,
            "uri": self.uri,
            "status": self.status,
            "resolved_at": self.resolved_at,
            "error": self.error,
        }
        if self.invocation_event is not None:
            payload["invocation_event"] = dict(self.invocation_event)
        return payload

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> LLMArtifactResolution:
        return cls(
            provisional_id=str(value.get("provisional_id") or ""),
            provider_attempt_id=str(value.get("provider_attempt_id") or ""),
            artifact_kind=str(value.get("artifact_kind") or ""),
            sha256=str(value.get("sha256") or "") or None,
            uri=str(value.get("uri") or "") or None,
            status=str(value.get("status") or "resolved"),
            resolved_at=float(value.get("resolved_at") or time.time()),
            error=str(value.get("error") or "") or None,
            invocation_event=(
                dict(value.get("invocation_event") or {})
                if isinstance(value.get("invocation_event"), Mapping)
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class _WriteArtifact:
    sha256: str
    content: bytes


@dataclass(frozen=True, slots=True)
class _ResolveArtifact:
    provisional_id: str
    provider_attempt_id: str
    artifact_kind: str
    payload: Any
    redactor: Callable[[Any], Any]
    capture_payload: bool = False
    invocation_event: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class _RecoverArtifact:
    path: Path


@dataclass(frozen=True, slots=True)
class _PruneExpired:
    now: float


@dataclass(frozen=True, slots=True)
class _Barrier:
    completed: threading.Event


@dataclass(frozen=True, slots=True)
class _Stop:
    completed: threading.Event


_QueueItem = (
    _WriteArtifact
    | _ResolveArtifact
    | _RecoverArtifact
    | _PruneExpired
    | _Barrier
    | _Stop
)


def canonical_artifact_bytes(redacted_payload: Any) -> bytes:
    """Serialize an already-redacted JSON-safe artifact deterministically."""

    return json.dumps(
        redacted_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def artifact_sha256(redacted_payload: Any) -> str:
    """Return the content address for an already-redacted payload."""

    return hashlib.sha256(canonical_artifact_bytes(redacted_payload)).hexdigest()


class LLMArtifactSpool:
    """Bounded, asynchronous, content-addressed local artifact spool.

    The spool is disabled by default at the recorder layer.  An embedding
    application such as OPC enables it with ``USMSB_LLM_ARTIFACT_SPOOL_DIR`` or
    passes an explicit absolute directory.  ``enqueue_redacted`` never waits for
    disk I/O.  ``flush``/``close`` are lifecycle operations and may wait; async
    variants move that wait off the caller's event loop.
    """

    def __init__(
        self,
        root: str | os.PathLike[str],
        *,
        max_queue: int = DEFAULT_LLM_ARTIFACT_SPOOL_MAX_QUEUE,
        max_pending_bytes: int = DEFAULT_LLM_ARTIFACT_SPOOL_MAX_PENDING_BYTES,
        max_artifact_bytes: int = DEFAULT_LLM_ARTIFACT_SPOOL_MAX_ARTIFACT_BYTES,
        retention_seconds: int = DEFAULT_LLM_ARTIFACT_SPOOL_RETENTION_SECONDS,
        cleanup_interval_seconds: int = (
            DEFAULT_LLM_ARTIFACT_SPOOL_CLEANUP_INTERVAL_SECONDS
        ),
    ) -> None:
        requested_root = Path(root)
        if not requested_root.is_absolute():
            raise LLMArtifactSpoolError("LLM artifact spool root must be an absolute path")
        if requested_root == Path(requested_root.anchor):
            raise LLMArtifactSpoolError("filesystem root cannot be used as an artifact spool")

        requested_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.root = requested_root.resolve(strict=True)
        if self.root == Path(self.root.anchor):
            raise LLMArtifactSpoolError("filesystem root cannot be used as an artifact spool")
        self._secure_directory(self.root)

        self.max_queue = max(1, int(max_queue))
        self.max_pending_bytes = max(1, int(max_pending_bytes))
        self.max_artifact_bytes = max(1, int(max_artifact_bytes))
        if self.max_artifact_bytes > self.max_pending_bytes:
            self.max_artifact_bytes = self.max_pending_bytes
        self.retention_seconds = max(1, int(retention_seconds))
        self.cleanup_interval_seconds = max(1, int(cleanup_interval_seconds))
        self._queue: queue.Queue[_QueueItem] = queue.Queue(maxsize=self.max_queue)
        self._state_lock = threading.RLock()
        self._storage_lock = threading.RLock()
        self._accepting = True
        self._closed = threading.Event()
        self._stop_event: threading.Event | None = None
        self._write_failures = 0
        self._queue_overflows = 0
        self._pending_byte_overflows = 0
        self._oversized_artifacts = 0
        self._pending_bytes = 0
        self._writes_completed = 0
        self._deduplicated = 0
        self._relations_completed = 0
        self._relations_replayed = 0
        self._last_cleanup_at = 0.0
        self._last_cleanup_monotonic = 0.0
        self._relations_pruned = 0
        self._artifacts_pruned = 0
        self._artifact_bytes_pruned = 0
        self._resolution_callbacks: list[Callable[[LLMArtifactResolution], Any]] = []
        # Startup/control items and terminal evidence which already crossed a
        # Provider boundary spill here when the fast queue is full.  There is no
        # maxlen and therefore no silent eviction of older accepted evidence.
        # New Provider requests still fail fast under pressure; only a bounded
        # set of already-admitted in-flight attempts may add terminal payloads.
        self._overflow: deque[_QueueItem] = deque()
        self._inflight_provider_attempts: set[str] = set()
        self._last_payload_enqueue_at = 0.0
        self._prepare_artifact_parent(self.root / "pending")
        self._prepare_artifact_parent(self.root / "relations")
        recovered = sorted((self.root / "pending").glob("*.json"))
        self._worker = threading.Thread(
            target=self._run,
            name="usmsb-llm-artifact-spool",
            daemon=True,
        )
        self._worker.start()
        for path in recovered:
            self._enqueue_work_item(_RecoverArtifact(path=path))
        # Cleanup is serialized behind pending recovery on the storage worker;
        # construction and Provider calls never wait for a filesystem scan.
        self._enqueue_work_item(_PruneExpired(now=time.time()))

    @classmethod
    def from_env(cls) -> LLMArtifactSpool | None:
        """Build an enabled spool from environment, or ``None`` when disabled."""

        config = _spool_config_from_env()
        if config is None:
            return None
        return cls(**config)

    @property
    def diagnostics(self) -> dict[str, Any]:
        """Return small operational counters without touching the filesystem."""

        with self._state_lock:
            return {
                "enabled": True,
                "root": str(self.root),
                "accepting": self._accepting,
                "closed": self._closed.is_set(),
                "queued": self._queue.qsize(),
                "pending_bytes": self._pending_bytes,
                "write_failures": self._write_failures,
                "queue_overflows": self._queue_overflows,
                "pending_byte_overflows": self._pending_byte_overflows,
                "oversized_artifacts": self._oversized_artifacts,
                "writes_completed": self._writes_completed,
                "deduplicated": self._deduplicated,
                "relations_completed": self._relations_completed,
                "relations_replayed": self._relations_replayed,
                "memory_spill_depth": len(self._overflow),
                "inflight_provider_attempts": len(self._inflight_provider_attempts),
                "retention_seconds": self.retention_seconds,
                "cleanup_interval_seconds": self.cleanup_interval_seconds,
                "last_cleanup_at": self._last_cleanup_at,
                "relations_pruned": self._relations_pruned,
                "artifacts_pruned": self._artifacts_pruned,
                "artifact_bytes_pruned": self._artifact_bytes_pruned,
            }

    def storage_status(self, *, now: float | None = None) -> dict[str, Any]:
        """Return exact capacity/age gauges for operational readiness.

        This is a control-plane operation and may scan the spool.  Provider
        paths use :attr:`diagnostics`, which remains in-memory and O(1).
        Unknown files and symlinks are reported nowhere and are never treated
        as managed artifacts by either this method or retention cleanup.
        """

        current = time.time() if now is None else float(now)

        def summarize(paths: list[Path]) -> dict[str, int | float]:
            items = 0
            bytes_used = 0
            oldest_age = 0.0
            for path in paths:
                if path.is_symlink():
                    continue
                try:
                    file_stat = path.stat()
                except OSError:
                    continue
                if not stat.S_ISREG(file_stat.st_mode):
                    continue
                items += 1
                bytes_used += max(0, int(file_stat.st_size))
                oldest_age = max(oldest_age, max(0.0, current - file_stat.st_mtime))
            return {
                "items": items,
                "bytes": bytes_used,
                "oldest_age_seconds": oldest_age,
            }

        with self._storage_lock:
            pending = [
                path
                for path in (self.root / "pending").glob("llm_artifact_*.json")
                if re.fullmatch(r"llm_artifact_[0-9a-f]{32}", path.stem)
            ]
            relations = [
                path
                for path in (self.root / "relations").glob("llm_artifact_*.json")
                if re.fullmatch(r"llm_artifact_[0-9a-f]{32}", path.stem)
            ]
            artifacts = list(self._iter_canonical_artifact_paths())
            return {
                "pending": summarize(pending),
                "relations": summarize(relations),
                "artifacts": summarize(artifacts),
                "limits": {
                    "max_queue": self.max_queue,
                    "max_pending_bytes": self.max_pending_bytes,
                    "max_artifact_bytes": self.max_artifact_bytes,
                    "retention_seconds": self.retention_seconds,
                },
            }

    def prune_expired(self, *, now: float | None = None) -> dict[str, int]:
        """Safely remove expired relations and unreferenced CAS bodies.

        A flush establishes a boundary before the scan.  The storage lock then
        serializes cleanup with writes.  Pending recovery envelopes are never
        deleted and their content hashes protect any matching CAS body.
        """

        if threading.current_thread() is not self._worker:
            self.flush(timeout=30.0)
        return self._prune_expired_storage(
            now=time.time() if now is None else float(now)
        )

    def add_resolution_callback(
        self,
        callback: Callable[[LLMArtifactResolution], Any],
        *,
        replay_existing: bool = True,
    ) -> None:
        """Subscribe to stable resolutions and optionally replay durable history."""

        with self._state_lock:
            if callback not in self._resolution_callbacks:
                self._resolution_callbacks.append(callback)
        if not replay_existing:
            return
        replay: list[LLMArtifactResolution] = []
        with self._storage_lock:
            relation_paths = sorted((self.root / "relations").glob("*.json"))
            for path in relation_paths:
                try:
                    replay.append(
                        LLMArtifactResolution.from_dict(
                            json.loads(self._read_file_nofollow(path).decode("utf-8"))
                        )
                    )
                except Exception:
                    logger.warning(
                        "Could not read LLM artifact relation %s", path, exc_info=True
                    )
        for resolution in replay:
            try:
                callback(resolution)
                with self._state_lock:
                    self._relations_replayed += 1
            except Exception:
                logger.warning(
                    "Could not replay LLM artifact relation %s",
                    resolution.provisional_id,
                    exc_info=True,
                )

    def remove_resolution_callback(
        self,
        callback: Callable[[LLMArtifactResolution], Any],
    ) -> None:
        with self._state_lock:
            if callback in self._resolution_callbacks:
                self._resolution_callbacks.remove(callback)

    def enqueue_payload(
        self,
        payload: Any,
        *,
        provider_attempt_id: str,
        artifact_kind: str,
        redactor: Callable[[Any], Any],
        provisional_id: str | None = None,
        capture_payload: bool = False,
        invocation_event: Mapping[str, Any] | None = None,
        provider_phase: str | None = None,
        require_healthy: bool = False,
    ) -> LLMArtifactProvisionalReference:
        """Transfer a payload reference to the worker without inspecting it.

        The caller must not mutate the payload after this method returns.  This
        ownership-transfer contract is what keeps arbitrarily large Provider
        envelopes off the request/completion hot path.
        """

        if artifact_kind not in {"request", "response"}:
            raise ValueError("artifact_kind must be request or response")
        normalized_phase = str(provider_phase or "").strip().lower() or None
        if normalized_phase not in {None, "requested", "terminal"}:
            raise ValueError("provider_phase must be requested, terminal or None")
        resolved_id = provisional_id or f"llm_artifact_{uuid4().hex}"
        item = _ResolveArtifact(
            provisional_id=resolved_id,
            provider_attempt_id=str(provider_attempt_id),
            artifact_kind=artifact_kind,
            payload=payload,
            redactor=redactor,
            capture_payload=bool(capture_payload),
            invocation_event=invocation_event,
        )
        attempt_id = str(provider_attempt_id)
        with self._state_lock:
            terminal_for_accepted_attempt = bool(
                normalized_phase == "terminal"
                and attempt_id in self._inflight_provider_attempts
            )
            if not self._accepting and not terminal_for_accepted_attempt:
                return LLMArtifactProvisionalReference(resolved_id, "closed")
            if normalized_phase == "terminal" and not terminal_for_accepted_attempt:
                return LLMArtifactProvisionalReference(resolved_id, "unknown_attempt")
            if require_healthy and any(
                (
                    not self._worker.is_alive(),
                    self._closed.is_set(),
                    self._write_failures,
                    self._pending_byte_overflows,
                    self._oversized_artifacts,
                )
            ):
                return LLMArtifactProvisionalReference(resolved_id, "unhealthy")
            if normalized_phase == "requested" and (
                self._overflow
                or len(self._inflight_provider_attempts) >= self.max_queue
            ):
                # Bound the no-eviction terminal spill by the number of
                # admitted Provider attempts and let older spill work drain
                # before accepting newer paid work.
                self._queue_overflows += 1
                return LLMArtifactProvisionalReference(resolved_id, "queue_full")
            self._last_payload_enqueue_at = time.monotonic()
            if normalized_phase == "terminal" and self._overflow:
                # Once spill exists it is the FIFO tail. Do not let a later
                # terminal leapfrog it through a newly-freed bounded slot.
                self._queue_overflows += 1
                self._overflow.append(item)
            else:
                try:
                    self._queue.put_nowait(item)
                except queue.Full:
                    self._queue_overflows += 1
                    if normalized_phase != "terminal":
                        return LLMArtifactProvisionalReference(resolved_id, "queue_full")
                    # A Provider has already returned. Keep exact FIFO ownership
                    # rather than dropping the new or an older event. The number
                    # of such payloads is bounded by admitted attempts.
                    self._overflow.append(item)
            if normalized_phase == "requested":
                self._inflight_provider_attempts.add(attempt_id)
            elif normalized_phase == "terminal":
                self._inflight_provider_attempts.discard(attempt_id)
        return LLMArtifactProvisionalReference(resolved_id)

    def persist_payload_durable(
        self,
        payload: Any,
        *,
        provider_attempt_id: str,
        artifact_kind: str,
        redactor: Callable[[Any], Any],
        provisional_id: str | None = None,
        capture_payload: bool = False,
        invocation_event: Mapping[str, Any] | None = None,
    ) -> LLMArtifactResolution:
        """Synchronously persist a control-plane payload.

        Provider adapters must use :meth:`enqueue_payload`; this compatibility
        API is reserved for lifecycle/control-plane callers that explicitly
        request a durable acknowledgement and are not on a Provider hot path.
        """

        if artifact_kind not in {"request", "response"}:
            raise ValueError("artifact_kind must be request or response")
        resolved_id = provisional_id or f"llm_artifact_{uuid4().hex}"
        with self._state_lock:
            if not self._accepting or self._closed.is_set():
                raise LLMArtifactSpoolError("LLM artifact spool is not accepting evidence")
            if not self._worker.is_alive():
                raise LLMArtifactSpoolError("LLM artifact spool worker is unavailable")
            if self._write_failures or self._pending_byte_overflows:
                raise LLMArtifactSpoolError("LLM artifact spool is unhealthy")
        try:
            redacted = redactor(payload)
            content = canonical_artifact_bytes(redacted)
            if len(content) > self.max_artifact_bytes:
                with self._state_lock:
                    self._oversized_artifacts += 1
                raise LLMArtifactSpoolError(
                    f"redacted LLM artifact exceeds {self.max_artifact_bytes} bytes"
                )
            pending_path = self._pending_path(resolved_id)
            envelope: dict[str, Any] = {
                "schema": "usmsb.llm-artifact-pending.v1",
                "provisional_id": resolved_id,
                "provider_attempt_id": str(provider_attempt_id),
                "artifact_kind": artifact_kind,
                "created_at": time.time(),
                "payload": redacted,
            }
            if invocation_event is not None:
                envelope["invocation_event"] = dict(invocation_event)
            with self._storage_lock:
                self._atomic_write_json(pending_path, envelope)
                resolution = self._finish_pending_relation(
                    pending_path,
                    captured_payload=(
                        redacted
                        if capture_payload and len(content) <= 64 * 1024
                        else None
                    ),
                )
        except Exception:
            with self._state_lock:
                self._write_failures += 1
            raise
        self._notify_resolution(resolution)
        return resolution

    def enqueue_redacted(self, redacted_payload: Any) -> LLMArtifactReference:
        """Queue an already-redacted payload without performing filesystem I/O."""

        content = canonical_artifact_bytes(redacted_payload)
        digest = hashlib.sha256(content).hexdigest()
        path = self._path_for_digest(digest)
        reference = LLMArtifactReference(sha256=digest, uri=path.as_uri())
        with self._state_lock:
            if not self._accepting:
                logger.warning("LLM artifact spool is closed; artifact %s was not queued", digest)
                return LLMArtifactReference(sha256=digest, uri=None, enqueue_status="closed")
            if len(content) > self.max_artifact_bytes:
                self._oversized_artifacts += 1
                logger.warning(
                    "Redacted LLM artifact %s is %s bytes, above the configured %s-byte "
                    "limit; it was not persisted",
                    digest,
                    len(content),
                    self.max_artifact_bytes,
                )
                return LLMArtifactReference(
                    sha256=digest,
                    uri=None,
                    enqueue_status="artifact_too_large",
                )
            if self._pending_bytes + len(content) > self.max_pending_bytes:
                self._pending_byte_overflows += 1
                logger.warning(
                    "LLM artifact pending-byte budget is exhausted; artifact %s was not persisted",
                    digest,
                )
                return LLMArtifactReference(
                    sha256=digest,
                    uri=None,
                    enqueue_status="pending_bytes_full",
                )
            self._pending_bytes += len(content)
            try:
                self._queue.put_nowait(_WriteArtifact(sha256=digest, content=content))
            except queue.Full:
                self._pending_bytes -= len(content)
                self._queue_overflows += 1
                logger.warning(
                    "LLM artifact spool queue is full; artifact %s was not persisted",
                    digest,
                )
                return LLMArtifactReference(
                    sha256=digest,
                    uri=None,
                    enqueue_status="queue_full",
                )
        return reference

    def flush(self, timeout: float | None = None) -> bool:
        """Wait until all artifacts queued before this call have been processed."""

        deadline = self._deadline(timeout)
        with self._state_lock:
            if self._closed.is_set():
                return self._is_healthy()
            closing = not self._accepting
            if not self._worker.is_alive():
                return False
            barrier = _Barrier(completed=threading.Event())
        if closing:
            closed = self._closed.wait(timeout=self._remaining_timeout(deadline))
            return closed and self._is_healthy()
        if not self._wait_overflow_empty(deadline):
            return False
        if not self._put_control_item(barrier, timeout=self._remaining_timeout(deadline)):
            return False
        flushed = barrier.completed.wait(timeout=self._remaining_timeout(deadline))
        return flushed and self._is_healthy()

    async def flush_async(self, timeout: float | None = None) -> bool:
        """Async event-loop-safe form of :meth:`flush`."""

        return await asyncio.to_thread(self.flush, timeout)

    def close(self, timeout: float | None = None) -> bool:
        """Stop new admissions, await terminal handoffs and drain accepted work."""

        deadline = self._deadline(timeout)
        with self._state_lock:
            if self._closed.is_set():
                return self._is_healthy()
            should_enqueue = self._stop_event is None
            if should_enqueue:
                self._accepting = False
                self._stop_event = threading.Event()
            stop_event = self._stop_event
        assert stop_event is not None
        if should_enqueue and not self._wait_inflight_empty(deadline):
            with self._state_lock:
                if self._stop_event is stop_event:
                    self._stop_event = None
                    self._accepting = True
            return False
        if should_enqueue and not self._wait_overflow_empty(deadline):
            with self._state_lock:
                if self._stop_event is stop_event:
                    self._stop_event = None
                    self._accepting = True
            return False
        if should_enqueue and not self._put_control_item(
            _Stop(completed=stop_event),
            timeout=self._remaining_timeout(deadline),
        ):
            with self._state_lock:
                if self._stop_event is stop_event:
                    self._stop_event = None
            return False
        if not stop_event.wait(timeout=self._remaining_timeout(deadline)):
            return False
        self._worker.join(timeout=self._remaining_timeout(deadline))
        return self._closed.is_set() and self._is_healthy()

    async def aclose(self, timeout: float | None = None) -> bool:
        """Async event-loop-safe form of :meth:`close`."""

        return await asyncio.to_thread(self.close, timeout)

    def read(self, *, uri: str, expected_sha256: str | None = None) -> Any:
        """Load and verify a redacted artifact after a flush or process restart."""

        path, digest = self._validated_uri_path(uri, expected_sha256=expected_sha256)
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(path, flags)
        except OSError as error:
            raise LLMArtifactSpoolError(f"cannot open LLM artifact {uri!r}") from error
        try:
            file_stat = os.fstat(descriptor)
            if not stat.S_ISREG(file_stat.st_mode):
                raise LLMArtifactSpoolError("artifact URI must reference a regular file")
            if file_stat.st_size > self.max_artifact_bytes:
                raise LLMArtifactSpoolError(
                    "artifact file exceeds the configured safe read limit"
                )
            with os.fdopen(descriptor, "rb") as stream:
                content = stream.read()
            descriptor = -1
        except Exception:
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            raise
        actual = hashlib.sha256(content).hexdigest()
        if actual != digest:
            raise LLMArtifactSpoolError(
                f"LLM artifact hash mismatch: expected {digest}, observed {actual}"
            )
        try:
            return json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise LLMArtifactSpoolError("LLM artifact is not canonical UTF-8 JSON") from error

    def read_by_hash(self, sha256: str) -> Any:
        """Load a local artifact by its validated SHA-256 content address."""

        path = self._path_for_digest(sha256)
        return self.read(uri=path.as_uri(), expected_sha256=sha256)

    def _run(self) -> None:
        try:
            while True:
                item = self._queue.get()
                try:
                    if isinstance(item, _WriteArtifact):
                        try:
                            deduplicated = self._write_artifact(item)
                            with self._state_lock:
                                if deduplicated:
                                    self._deduplicated += 1
                                else:
                                    self._writes_completed += 1
                        except Exception:
                            with self._state_lock:
                                self._write_failures += 1
                            logger.warning(
                                "Failed to persist redacted LLM artifact %s",
                                item.sha256,
                                exc_info=True,
                            )
                        finally:
                            with self._state_lock:
                                self._pending_bytes = max(
                                    0,
                                    self._pending_bytes - len(item.content),
                                )
                    elif isinstance(item, _ResolveArtifact):
                        self._resolve_payload(item)
                    elif isinstance(item, _RecoverArtifact):
                        self._recover_pending(item.path)
                    elif isinstance(item, _PruneExpired):
                        self._prune_expired_storage(now=item.now)
                    elif isinstance(item, _Barrier):
                        item.completed.set()
                    elif isinstance(item, _Stop):
                        item.completed.set()
                        return
                    if isinstance(item, (_ResolveArtifact, _RecoverArtifact)):
                        self._maybe_prune_expired()
                finally:
                    self._queue.task_done()
                    self._promote_overflow()
        finally:
            self._closed.set()

    def _resolve_payload(self, item: _ResolveArtifact) -> None:
        pending_path = self._pending_path(item.provisional_id)
        relation = {
            "schema": "usmsb.llm-artifact-pending.v1",
            "provisional_id": item.provisional_id,
            "provider_attempt_id": item.provider_attempt_id,
            "artifact_kind": item.artifact_kind,
            "created_at": time.time(),
        }
        if item.invocation_event is not None:
            relation["invocation_event"] = dict(item.invocation_event)
        try:
            self._wait_for_provider_handoff()
            redacted = item.redactor(item.payload)
            content = canonical_artifact_bytes(redacted)
            digest = hashlib.sha256(content).hexdigest()
            if len(content) > self.max_artifact_bytes:
                with self._state_lock:
                    self._oversized_artifacts += 1
                self._complete_resolution(
                    LLMArtifactResolution(
                        provisional_id=item.provisional_id,
                        provider_attempt_id=item.provider_attempt_id,
                        artifact_kind=item.artifact_kind,
                        sha256=digest,
                        uri=None,
                        status="artifact_too_large",
                        resolved_at=time.time(),
                    )
                )
                return

            # The pending envelope contains only redacted data.  It is the
            # durable recovery boundary between payload normalization and CAS.
            self._atomic_write_json(
                pending_path,
                {**relation, "payload": redacted},
            )
            resolution = self._finish_pending_relation(
                pending_path,
                captured_payload=(
                    redacted if item.capture_payload and len(content) <= 64 * 1024 else None
                ),
            )
            self._notify_resolution(resolution)
        except Exception as exc:
            with self._state_lock:
                self._write_failures += 1
            logger.warning(
                "Failed to resolve provisional LLM artifact %s",
                item.provisional_id,
                exc_info=True,
            )
            if pending_path.exists():
                # Redaction already crossed the durable boundary.  Preserve
                # that envelope for restart replay; emitting a transient
                # failure under the stable provisional event id would make a
                # later successful resolution look like a duplicate.
                return
            self._complete_resolution(
                LLMArtifactResolution(
                    provisional_id=item.provisional_id,
                    provider_attempt_id=item.provider_attempt_id,
                    artifact_kind=item.artifact_kind,
                    sha256=None,
                    uri=None,
                    status="prepare_failed",
                    resolved_at=time.time(),
                    error=f"{type(exc).__name__}: {exc}"[:1000],
                )
            )

    def _recover_pending(self, path: Path) -> None:
        try:
            resolution = self._finish_pending_relation(path)
            self._notify_resolution(resolution)
        except Exception:
            with self._state_lock:
                self._write_failures += 1
            logger.warning("Failed to replay pending LLM artifact %s", path, exc_info=True)

    def _wait_for_provider_handoff(self) -> None:
        """Wait on the worker only until a burst of Provider hooks is quiet."""

        while True:
            with self._state_lock:
                quiet_for = time.monotonic() - self._last_payload_enqueue_at
            remaining = LLM_ARTIFACT_WORKER_HANDOFF_GRACE_SECONDS - quiet_for
            if remaining <= 0:
                return
            time.sleep(remaining)

    def _finish_pending_relation(
        self,
        pending_path: Path,
        *,
        captured_payload: Any = None,
    ) -> LLMArtifactResolution:
        envelope = json.loads(self._read_file_nofollow(pending_path).decode("utf-8"))
        payload = envelope["payload"]
        content = canonical_artifact_bytes(payload)
        digest = hashlib.sha256(content).hexdigest()
        artifact = _WriteArtifact(sha256=digest, content=content)
        deduplicated = self._write_artifact(artifact)
        with self._state_lock:
            if deduplicated:
                self._deduplicated += 1
            else:
                self._writes_completed += 1
        resolution = LLMArtifactResolution(
            provisional_id=str(envelope["provisional_id"]),
            provider_attempt_id=str(envelope["provider_attempt_id"]),
            artifact_kind=str(envelope["artifact_kind"]),
            sha256=digest,
            uri=self._path_for_digest(digest).as_uri(),
            status="resolved",
            resolved_at=time.time(),
            captured_payload=captured_payload,
            invocation_event=(
                dict(envelope.get("invocation_event") or {})
                if isinstance(envelope.get("invocation_event"), Mapping)
                else None
            ),
        )
        self._atomic_write_json(
            self._relation_path(resolution.provisional_id),
            resolution.to_dict(),
        )
        try:
            pending_path.unlink(missing_ok=True)
            self._fsync_directory(pending_path.parent)
        except OSError:
            logger.debug("Could not remove resolved pending artifact %s", pending_path)
        with self._state_lock:
            self._relations_completed += 1
        return resolution

    def _complete_resolution(self, resolution: LLMArtifactResolution) -> None:
        try:
            self._atomic_write_json(
                self._relation_path(resolution.provisional_id),
                resolution.to_dict(),
            )
            with self._state_lock:
                self._relations_completed += 1
        except Exception:
            with self._state_lock:
                self._write_failures += 1
            logger.warning(
                "Could not persist terminal LLM artifact relation %s",
                resolution.provisional_id,
                exc_info=True,
            )
        finally:
            self._notify_resolution(resolution)

    def _notify_resolution(self, resolution: LLMArtifactResolution) -> None:
        with self._state_lock:
            callbacks = tuple(self._resolution_callbacks)
        for callback in callbacks:
            try:
                callback(resolution)
            except Exception:
                logger.warning(
                    "LLM artifact resolution callback failed for %s",
                    resolution.provisional_id,
                    exc_info=True,
                )

    def _atomic_write_json(self, path: Path, payload: Mapping[str, Any]) -> None:
        self._prepare_artifact_parent(path.parent)
        encoded = canonical_artifact_bytes(payload)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            os.chmod(path, 0o600)
            self._fsync_directory(path.parent)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            temporary.unlink(missing_ok=True)

    def _pending_path(self, provisional_id: str) -> Path:
        return self.root / "pending" / f"{self._safe_provisional_id(provisional_id)}.json"

    def _relation_path(self, provisional_id: str) -> Path:
        return self.root / "relations" / f"{self._safe_provisional_id(provisional_id)}.json"

    @staticmethod
    def _safe_provisional_id(provisional_id: str) -> str:
        value = str(provisional_id)
        if not re.fullmatch(r"llm_artifact_[0-9a-f]{32}", value):
            raise LLMArtifactSpoolError("invalid provisional artifact id")
        return value

    def _write_artifact(self, item: _WriteArtifact) -> bool:
        with self._storage_lock:
            return self._write_artifact_locked(item)

    def _write_artifact_locked(self, item: _WriteArtifact) -> bool:
        if hashlib.sha256(item.content).hexdigest() != item.sha256:
            raise LLMArtifactSpoolError("artifact content does not match its SHA-256 address")

        lexical_path = self._path_for_digest(item.sha256)
        self._prepare_artifact_parent(lexical_path.parent)
        resolved_parent = lexical_path.parent.resolve(strict=True)
        self._require_inside_root(resolved_parent)
        self._secure_directory(resolved_parent)
        target = resolved_parent / lexical_path.name

        if target.is_symlink():
            raise LLMArtifactSpoolError("artifact target cannot be a symbolic link")
        if target.exists():
            current = self._read_file_nofollow(target)
            if hashlib.sha256(current).hexdigest() == item.sha256:
                os.chmod(target, 0o600)
                # Retention is based on last reference time, not first creation.
                # Refreshing mtime prevents a frequently reused content-addressed
                # artifact from being deleted while new trace rows still point to it.
                os.utime(target, None, follow_symlinks=False)
                self._fsync_directory(resolved_parent)
                return True

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{item.sha256}.",
            suffix=".tmp",
            dir=resolved_parent,
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            stream = os.fdopen(descriptor, "wb")
            descriptor = -1
            with stream:
                stream.write(item.content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            os.chmod(target, 0o600)
            self._fsync_directory(resolved_parent)
            return False
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                logger.debug("Could not remove temporary LLM artifact %s", temporary)

    def _iter_canonical_artifact_paths(self):
        content_root = self.root / "sha256"
        if not content_root.is_dir() or content_root.is_symlink():
            return
        for candidate in content_root.glob("*/*/*.json"):
            digest = candidate.stem
            try:
                relative = candidate.relative_to(content_root)
            except ValueError:
                continue
            if (
                len(relative.parts) != 3
                or not _SHA256_RE.fullmatch(digest)
                or relative.parts[0] != digest[:2]
                or relative.parts[1] != digest[2:4]
                or candidate.is_symlink()
                or candidate.parent.is_symlink()
                or candidate.parent.parent.is_symlink()
            ):
                continue
            try:
                if candidate.is_file():
                    yield candidate
            except OSError:
                continue

    def _maybe_prune_expired(self) -> None:
        if (
            time.monotonic() - self._last_cleanup_monotonic
            < self.cleanup_interval_seconds
        ):
            return
        try:
            self._prune_expired_storage(now=time.time())
        except Exception:
            logger.warning("Could not prune expired LLM artifacts", exc_info=True)

    def _prune_expired_storage(self, *, now: float) -> dict[str, int]:
        cutoff = float(now) - self.retention_seconds
        relations_to_remove: list[Path] = []
        active_digests: set[str] = set()
        pending_digests: set[str] = set()
        unsafe_relation_state = False
        relation_root = self.root / "relations"
        pending_root = self.root / "pending"

        with self._storage_lock:
            for path in sorted(relation_root.glob("llm_artifact_*.json")):
                if (
                    not re.fullmatch(r"llm_artifact_[0-9a-f]{32}", path.stem)
                    or path.is_symlink()
                ):
                    unsafe_relation_state = True
                    continue
                try:
                    file_stat = path.stat()
                    value = json.loads(self._read_file_nofollow(path).decode("utf-8"))
                    if (
                        not stat.S_ISREG(file_stat.st_mode)
                        or value.get("schema") != "usmsb.llm-artifact-relation.v1"
                        or str(value.get("provisional_id") or "") != path.stem
                    ):
                        raise ValueError("invalid relation envelope")
                    digest = str(value.get("sha256") or "")
                    if digest and not _SHA256_RE.fullmatch(digest):
                        raise ValueError("invalid relation digest")
                    lease = max(
                        float(value.get("resolved_at") or 0.0),
                        float(file_stat.st_mtime),
                    )
                    if lease >= cutoff:
                        if digest:
                            active_digests.add(digest)
                    else:
                        relations_to_remove.append(path)
                except Exception:
                    unsafe_relation_state = True
                    logger.warning(
                        "Preserving malformed LLM artifact relation %s", path
                    )

            for path in sorted(pending_root.glob("llm_artifact_*.json")):
                if (
                    not re.fullmatch(r"llm_artifact_[0-9a-f]{32}", path.stem)
                    or path.is_symlink()
                ):
                    unsafe_relation_state = True
                    continue
                try:
                    value = json.loads(self._read_file_nofollow(path).decode("utf-8"))
                    if (
                        value.get("schema") != "usmsb.llm-artifact-pending.v1"
                        or str(value.get("provisional_id") or "") != path.stem
                    ):
                        raise ValueError("invalid pending envelope")
                    pending_digests.add(artifact_sha256(value["payload"]))
                except Exception:
                    unsafe_relation_state = True
                    logger.warning(
                        "Preserving malformed pending LLM artifact %s", path
                    )

            relations_removed = 0
            artifacts_removed = 0
            bytes_removed = 0
            # If any managed relation cannot be understood, fail closed for the
            # entire cleanup pass: it may be the only remaining reference to a
            # content address.
            if not unsafe_relation_state:
                for path in relations_to_remove:
                    try:
                        path.unlink()
                        relations_removed += 1
                    except OSError:
                        logger.warning(
                            "Could not remove expired LLM artifact relation %s", path
                        )
                for path in list(self._iter_canonical_artifact_paths()):
                    digest = path.stem
                    try:
                        file_stat = path.stat()
                        if (
                            file_stat.st_mtime >= cutoff
                            or digest in active_digests
                            or digest in pending_digests
                        ):
                            continue
                        size = max(0, int(file_stat.st_size))
                        path.unlink()
                        artifacts_removed += 1
                        bytes_removed += size
                    except OSError:
                        logger.warning(
                            "Could not remove expired LLM artifact %s", path
                        )
                content_root = self.root / "sha256"
                for pattern in ("*/*", "*"):
                    for directory in sorted(content_root.glob(pattern), reverse=True):
                        if directory.is_symlink() or not directory.is_dir():
                            continue
                        try:
                            directory.rmdir()
                        except OSError:
                            pass
                self._fsync_directory(relation_root)

            with self._state_lock:
                self._last_cleanup_at = float(now)
                self._last_cleanup_monotonic = time.monotonic()
                self._relations_pruned += relations_removed
                self._artifacts_pruned += artifacts_removed
                self._artifact_bytes_pruned += bytes_removed
            return {
                "relations_removed": relations_removed,
                "artifacts_removed": artifacts_removed,
                "artifact_bytes_removed": bytes_removed,
                "unsafe_relation_state": int(unsafe_relation_state),
            }

    def _validated_uri_path(
        self,
        uri: str,
        *,
        expected_sha256: str | None,
    ) -> tuple[Path, str]:
        parsed = urlparse(str(uri))
        if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}:
            raise LLMArtifactSpoolError("only local file:// artifact URIs are supported")
        if parsed.query or parsed.fragment:
            raise LLMArtifactSpoolError("artifact URI must not contain query or fragment data")
        supplied_path = Path(unquote(parsed.path))
        if not supplied_path.is_absolute():
            raise LLMArtifactSpoolError("artifact URI path must be absolute")

        filename = supplied_path.name
        if not filename.endswith(".json"):
            raise LLMArtifactSpoolError("artifact URI must reference a JSON content address")
        digest = filename[:-5]
        self._validate_digest(digest)
        if expected_sha256 is not None:
            self._validate_digest(expected_sha256)
            if digest != expected_sha256:
                raise LLMArtifactSpoolError("artifact URI does not match expected SHA-256")

        expected_path = self._path_for_digest(digest)
        if supplied_path != expected_path:
            raise LLMArtifactSpoolError("artifact URI is not in the canonical spool location")
        self._reject_symlink_components(supplied_path)
        if supplied_path.is_symlink():
            raise LLMArtifactSpoolError("artifact URI must not reference a symbolic link")
        try:
            resolved = supplied_path.resolve(strict=True)
        except OSError as error:
            raise LLMArtifactSpoolError(f"LLM artifact does not exist: {uri!r}") from error
        self._require_inside_root(resolved)
        if resolved != expected_path.resolve(strict=True):
            raise LLMArtifactSpoolError("artifact URI is not in the canonical spool location")
        if resolved.is_symlink() or not resolved.is_file():
            raise LLMArtifactSpoolError("artifact URI must reference a regular non-symlink file")
        return resolved, digest

    def _path_for_digest(self, digest: str) -> Path:
        self._validate_digest(digest)
        return self.root / "sha256" / digest[:2] / digest[2:4] / f"{digest}.json"

    @staticmethod
    def _validate_digest(digest: str) -> None:
        if not _SHA256_RE.fullmatch(str(digest)):
            raise LLMArtifactSpoolError("invalid SHA-256 content address")

    def _require_inside_root(self, path: Path) -> None:
        try:
            path.relative_to(self.root)
        except ValueError as error:
            raise LLMArtifactSpoolError(
                "artifact path escapes the configured spool root"
            ) from error

    def _prepare_artifact_parent(self, parent: Path) -> None:
        """Create every content-address directory with private permissions."""

        try:
            relative_parts = parent.relative_to(self.root).parts
        except ValueError as error:
            raise LLMArtifactSpoolError("artifact parent escapes the spool root") from error
        current = self.root
        for part in relative_parts:
            current = current / part
            if current.is_symlink():
                raise LLMArtifactSpoolError(
                    "symbolic links are not allowed in the artifact spool layout"
                )
            current.mkdir(mode=0o700, exist_ok=True)
            resolved = current.resolve(strict=True)
            self._require_inside_root(resolved)
            self._secure_directory(resolved)

    def _reject_symlink_components(self, path: Path) -> None:
        try:
            relative_parts = path.relative_to(self.root).parts
        except ValueError as error:
            raise LLMArtifactSpoolError("artifact path escapes the spool root") from error
        current = self.root
        for part in relative_parts:
            current = current / part
            if current.is_symlink():
                raise LLMArtifactSpoolError(
                    "symbolic links are not allowed in the artifact spool layout"
                )

    @staticmethod
    def _secure_directory(path: Path) -> None:
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode != 0o700:
            os.chmod(path, 0o700)

    @staticmethod
    def _read_file_nofollow(path: Path) -> bytes:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            return stream.read()

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        try:
            descriptor = os.open(path, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError:
            # Some filesystems do not support directory fsync.  The artifact was
            # already atomically replaced and fsynced; report only at debug level.
            logger.debug("Directory fsync is unavailable for %s", path, exc_info=True)

    def _put_control_item(self, item: _QueueItem, *, timeout: float | None) -> bool:
        try:
            if timeout is None:
                self._queue.put(item)
            else:
                self._queue.put(item, timeout=max(0.0, timeout))
            return True
        except queue.Full:
            return False

    def _enqueue_work_item(self, item: _QueueItem) -> None:
        """Retain bounded-size startup recovery work outside the fast queue.

        Provider requests never use this path.  Terminal Provider evidence may
        use the same no-eviction spill through :meth:`enqueue_payload` after a
        request has already been admitted.
        """

        try:
            self._queue.put_nowait(item)
        except queue.Full:
            with self._state_lock:
                self._overflow.append(item)
                self._queue_overflows += 1

    def _promote_overflow(self) -> None:
        with self._state_lock:
            if not self._overflow:
                return
            item = self._overflow[0]
            try:
                self._queue.put_nowait(item)
            except queue.Full:
                return
            self._overflow.popleft()

    def _wait_overflow_empty(self, deadline: float | None) -> bool:
        while True:
            with self._state_lock:
                if not self._overflow:
                    return True
            remaining = self._remaining_timeout(deadline)
            if remaining is not None and remaining <= 0:
                return False
            time.sleep(min(0.005, remaining) if remaining is not None else 0.005)

    def _wait_inflight_empty(self, deadline: float | None) -> bool:
        """Wait for every accepted request to transfer terminal ownership."""

        while True:
            with self._state_lock:
                if not self._inflight_provider_attempts:
                    return True
            remaining = self._remaining_timeout(deadline)
            if remaining is not None and remaining <= 0:
                return False
            time.sleep(min(0.005, remaining) if remaining is not None else 0.005)

    def _is_healthy(self) -> bool:
        with self._state_lock:
            return not any(
                (
                    self._write_failures,
                    self._pending_byte_overflows,
                    self._oversized_artifacts,
                )
            )

    @staticmethod
    def _deadline(timeout: float | None) -> float | None:
        return None if timeout is None else time.monotonic() + max(0.0, timeout)

    @staticmethod
    def _remaining_timeout(deadline: float | None) -> float | None:
        return None if deadline is None else max(0.0, deadline - time.monotonic())


def llm_artifact_spool_required() -> bool:
    """Whether an embedding application requires valid startup configuration."""

    return str(os.environ.get(LLM_ARTIFACT_SPOOL_REQUIRED_ENV, "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _positive_env_int(name: str, default: int) -> int:
    raw = str(os.environ.get(name, default)).strip()
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        logger.warning("Invalid %s=%r; using %s", name, raw, default)
        return default


def _spool_config_from_env() -> dict[str, Any] | None:
    configured = str(os.environ.get(LLM_ARTIFACT_SPOOL_DIR_ENV, "")).strip()
    if not configured:
        if llm_artifact_spool_required():
            raise LLMArtifactSpoolError(
                f"{LLM_ARTIFACT_SPOOL_DIR_ENV} is required when "
                f"{LLM_ARTIFACT_SPOOL_REQUIRED_ENV}=true"
            )
        return None
    return {
        "root": configured,
        "max_queue": _positive_env_int(
            LLM_ARTIFACT_SPOOL_MAX_QUEUE_ENV,
            DEFAULT_LLM_ARTIFACT_SPOOL_MAX_QUEUE,
        ),
        "max_pending_bytes": _positive_env_int(
            LLM_ARTIFACT_SPOOL_MAX_PENDING_BYTES_ENV,
            DEFAULT_LLM_ARTIFACT_SPOOL_MAX_PENDING_BYTES,
        ),
        "max_artifact_bytes": _positive_env_int(
            LLM_ARTIFACT_SPOOL_MAX_ARTIFACT_BYTES_ENV,
            DEFAULT_LLM_ARTIFACT_SPOOL_MAX_ARTIFACT_BYTES,
        ),
        "retention_seconds": _positive_env_int(
            LLM_ARTIFACT_SPOOL_RETENTION_SECONDS_ENV,
            DEFAULT_LLM_ARTIFACT_SPOOL_RETENTION_SECONDS,
        ),
        "cleanup_interval_seconds": _positive_env_int(
            LLM_ARTIFACT_SPOOL_CLEANUP_INTERVAL_SECONDS_ENV,
            DEFAULT_LLM_ARTIFACT_SPOOL_CLEANUP_INTERVAL_SECONDS,
        ),
    }


_SHARED_SPOOL_LOCK = threading.RLock()
_SHARED_SPOOLS: dict[tuple[str, int, int, int, int, int], LLMArtifactSpool] = {}


def get_shared_llm_artifact_spool_from_env() -> LLMArtifactSpool | None:
    """Return one process-wide spool per resolved environment configuration."""

    config = _spool_config_from_env()
    if config is None:
        return None
    root = Path(config["root"])
    root_key = str(root.resolve(strict=False))
    key = (
        root_key,
        int(config["max_queue"]),
        int(config["max_pending_bytes"]),
        int(config["max_artifact_bytes"]),
        int(config["retention_seconds"]),
        int(config["cleanup_interval_seconds"]),
    )
    with _SHARED_SPOOL_LOCK:
        existing = _SHARED_SPOOLS.get(key)
        if existing is not None and not bool(existing.diagnostics["closed"]):
            return existing
        spool = LLMArtifactSpool(**config)
        _SHARED_SPOOLS[key] = spool
        return spool


def close_shared_llm_artifact_spools(timeout: float | None = 10.0) -> bool:
    """Drain all process-wide environment spools during application shutdown."""

    deadline = None if timeout is None else time.monotonic() + max(0.0, timeout)
    with _SHARED_SPOOL_LOCK:
        entries = list(_SHARED_SPOOLS.items())
    succeeded = True
    for key, spool in entries:
        remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
        if not spool.close(timeout=remaining):
            succeeded = False
        if bool(spool.diagnostics["closed"]):
            with _SHARED_SPOOL_LOCK:
                if _SHARED_SPOOLS.get(key) is spool:
                    _SHARED_SPOOLS.pop(key, None)
    return succeeded


async def close_shared_llm_artifact_spools_async(timeout: float | None = 10.0) -> bool:
    """Event-loop-safe process shutdown hook for shared artifact spools."""

    return await asyncio.to_thread(close_shared_llm_artifact_spools, timeout)


def _close_shared_spools_at_exit() -> None:
    close_shared_llm_artifact_spools(timeout=5.0)


atexit.register(_close_shared_spools_at_exit)


__all__ = [
    "DEFAULT_LLM_ARTIFACT_SPOOL_MAX_ARTIFACT_BYTES",
    "DEFAULT_LLM_ARTIFACT_SPOOL_MAX_PENDING_BYTES",
    "DEFAULT_LLM_ARTIFACT_SPOOL_MAX_QUEUE",
    "DEFAULT_LLM_ARTIFACT_SPOOL_RETENTION_SECONDS",
    "DEFAULT_LLM_ARTIFACT_SPOOL_CLEANUP_INTERVAL_SECONDS",
    "LLM_ARTIFACT_SPOOL_DIR_ENV",
    "LLM_ARTIFACT_SPOOL_MAX_ARTIFACT_BYTES_ENV",
    "LLM_ARTIFACT_SPOOL_MAX_PENDING_BYTES_ENV",
    "LLM_ARTIFACT_SPOOL_MAX_QUEUE_ENV",
    "LLM_ARTIFACT_SPOOL_REQUIRED_ENV",
    "LLM_ARTIFACT_SPOOL_RETENTION_SECONDS_ENV",
    "LLM_ARTIFACT_SPOOL_CLEANUP_INTERVAL_SECONDS_ENV",
    "LLMArtifactReference",
    "LLMArtifactProvisionalReference",
    "LLMArtifactResolution",
    "LLMArtifactSpool",
    "LLMArtifactSpoolError",
    "artifact_sha256",
    "canonical_artifact_bytes",
    "close_shared_llm_artifact_spools",
    "close_shared_llm_artifact_spools_async",
    "get_shared_llm_artifact_spool_from_env",
    "llm_artifact_spool_required",
]
