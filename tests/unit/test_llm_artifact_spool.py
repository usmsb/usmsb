"""Durable redacted artifact contract tests for provider telemetry."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import statistics
import threading
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest

from usmsb_sdk.llm_artifacts import (
    LLM_ARTIFACT_SPOOL_DIR_ENV,
    LLM_ARTIFACT_SPOOL_MAX_ARTIFACT_BYTES_ENV,
    LLM_ARTIFACT_SPOOL_REQUIRED_ENV,
    LLMArtifactSpool,
    LLMArtifactSpoolError,
    canonical_artifact_bytes,
    close_shared_llm_artifact_spools,
)
from usmsb_sdk.llm_telemetry import LLMInvocationRecorder


def _wait_until(predicate, *, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            raise AssertionError("timed out waiting for asynchronous artifact resolution")
        time.sleep(0.005)


@pytest.mark.asyncio
async def test_artifacts_survive_restart_and_are_redacted_and_hash_verified(
    tmp_path: Path,
) -> None:
    root = tmp_path / "llm-artifacts"
    recorder = LLMInvocationRecorder(
        artifact_spool_dir=str(root),
        capture_payloads=False,
    )
    request = {
        "messages": [{"role": "user", "content": "keep this prompt"}],
        "api_key": "request-secret",
        "headers": {"Authorization": "Bearer request-secret"},
    }
    response = {
        "content": "keep this answer",
        "access_token": "response-secret",
    }

    attempt_id = recorder.requested(
        provider="test-provider",
        model="test-model",
        operation="chat",
        request_payload=request,
    )
    recorder.completed(attempt_id, response_payload=response)

    requested, completed = [
        event
        for event in recorder.recent_events(limit=10)
        if event["event_type"].startswith("llm.provider.")
    ]
    assert requested["artifacts"]["request_provisional_id"]
    assert requested["artifacts"]["request_uri"] is None
    assert completed["artifacts"]["response_provisional_id"]
    assert "request_payload" not in requested
    assert "response_payload" not in completed
    assert "request-secret" not in json.dumps(requested)
    assert "response-secret" not in json.dumps(completed)
    assert recorder.recent_calls(limit=1)[0]["request_payload"] is None
    assert await recorder.flush_artifacts_async(timeout=5)
    detail = recorder.recent_calls(limit=1)[0]
    request_artifact = {
        "request_uri": detail["request_uri"],
        "request_sha256": detail["request_hash"],
    }
    response_artifact = {
        "response_uri": detail["response_uri"],
        "response_sha256": detail["response_hash"],
    }
    assert request_artifact["request_uri"].startswith("file://")
    assert response_artifact["response_uri"].startswith("file://")
    resolved = [
        event
        for event in recorder.recent_events(limit=10)
        if event["event_type"] == "llm.artifact.resolved"
    ]
    assert {event["artifacts"]["artifact_kind"] for event in resolved} == {
        "request",
        "response",
    }
    assert len({event["event_id"] for event in resolved}) == 2
    assert await recorder.close_artifacts_async(timeout=5)

    request_path = Path(unquote(urlparse(request_artifact["request_uri"]).path))
    response_path = Path(unquote(urlparse(response_artifact["response_uri"]).path))
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    for directory in request_path.parents:
        if directory == root.parent:
            break
        assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(request_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(response_path.stat().st_mode) == 0o600
    assert hashlib.sha256(request_path.read_bytes()).hexdigest() == request_artifact[
        "request_sha256"
    ]
    assert hashlib.sha256(response_path.read_bytes()).hexdigest() == response_artifact[
        "response_sha256"
    ]

    # A fresh reader simulates a process restart.  URI plus hash is sufficient
    # to recover and verify the full redacted artifact.
    restarted = LLMArtifactSpool(root)
    restored_request = restarted.read(
        uri=request_artifact["request_uri"],
        expected_sha256=request_artifact["request_sha256"],
    )
    restored_response = restarted.read(
        uri=response_artifact["response_uri"],
        expected_sha256=response_artifact["response_sha256"],
    )
    assert restored_request["messages"][0]["content"] == "keep this prompt"
    assert restored_request["api_key"] == "[REDACTED]"
    assert restored_request["headers"]["Authorization"] == "[REDACTED]"
    assert restored_response == {
        "content": "keep this answer",
        "access_token": "[REDACTED]",
    }
    assert await restarted.aclose(timeout=5)


def test_provider_hot_path_does_not_wait_for_artifact_disk_write(tmp_path: Path) -> None:
    spool = LLMArtifactSpool(tmp_path / "spool")
    recorder = LLMInvocationRecorder(artifact_spool=spool)
    write_started = threading.Event()
    allow_write = threading.Event()
    request_finished = threading.Event()
    original_write = spool._write_artifact

    def blocked_write(item):
        write_started.set()
        assert allow_write.wait(timeout=5)
        return original_write(item)

    spool._write_artifact = blocked_write  # type: ignore[method-assign]

    def provider_hot_path() -> None:
        recorder.requested(
            provider="test-provider",
            model="test-model",
            operation="chat",
            request_payload={"messages": [{"role": "user", "content": "hello"}]},
        )
        request_finished.set()

    caller = threading.Thread(target=provider_hot_path)
    caller.start()
    assert request_finished.wait(timeout=1), "requested() waited for filesystem I/O"
    assert write_started.wait(timeout=1)
    assert not allow_write.is_set()
    allow_write.set()
    caller.join(timeout=1)
    assert not caller.is_alive()
    assert spool.close(timeout=5)


@pytest.mark.parametrize("payload_size", [1024 * 1024, 5 * 1024 * 1024])
def test_provider_hot_path_p99_stays_below_three_ms_for_large_artifacts(
    tmp_path: Path,
    payload_size: int,
) -> None:
    spool = LLMArtifactSpool(
        tmp_path / f"spool-{payload_size}",
        max_pending_bytes=256 * 1024 * 1024,
        max_artifact_bytes=8 * 1024 * 1024,
    )
    recorder = LLMInvocationRecorder(artifact_spool=spool, capture_payloads=False)
    payload = {"content": "x" * payload_size}
    requested_ms: list[float] = []
    completed_ms: list[float] = []

    # Warm the Python call sites before measuring the provider contract.
    warmup = recorder.requested(
        provider="test-provider",
        model="test-model",
        operation="chat",
        request_payload={"content": "warmup"},
    )
    recorder.completed(warmup, response_payload={"content": "warmup"})
    for _ in range(20):
        started = time.perf_counter_ns()
        attempt_id = recorder.requested(
            provider="test-provider",
            model="test-model",
            operation="chat",
            request_payload=payload,
        )
        requested_ms.append((time.perf_counter_ns() - started) / 1_000_000)

        started = time.perf_counter_ns()
        recorder.completed(attempt_id, response_payload=payload)
        completed_ms.append((time.perf_counter_ns() - started) / 1_000_000)

    def p99(values: list[float]) -> float:
        ordered = sorted(values)
        return ordered[max(0, int(len(ordered) * 0.99) - 1)]

    assert p99(requested_ms) < 3.0, statistics.quantiles(requested_ms, n=10)
    assert p99(completed_ms) < 3.0, statistics.quantiles(completed_ms, n=10)
    assert spool.close(timeout=30)


def test_artifact_write_failure_is_observational_and_does_not_break_call(
    tmp_path: Path,
) -> None:
    spool = LLMArtifactSpool(tmp_path / "spool")
    recorder = LLMInvocationRecorder(artifact_spool=spool)

    def failed_write(_item):
        raise OSError("disk unavailable")

    spool._write_artifact = failed_write  # type: ignore[method-assign]
    attempt_id = recorder.requested(
        provider="test-provider",
        model="test-model",
        operation="chat",
        request_payload={"content": "request still executes"},
    )
    recorder.completed(attempt_id, response_payload={"content": "done"})

    assert recorder.recent_calls(limit=1)[0]["status"] == "completed"
    assert spool.flush(timeout=5) is False
    assert spool.diagnostics["write_failures"] == 2
    assert spool.close(timeout=5) is False
    assert spool.diagnostics["closed"] is True


@pytest.mark.asyncio
async def test_env_enables_spool_while_default_remains_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(LLM_ARTIFACT_SPOOL_DIR_ENV, raising=False)
    disabled = LLMInvocationRecorder()
    disabled_attempt = disabled.requested(
        provider="test-provider",
        model="test-model",
        operation="chat",
        request_payload={"content": "hash only"},
    )
    _wait_until(
        lambda: bool(disabled.recent_calls(limit=1)[0]["request_hash"]),
    )
    disabled_event = disabled.recent_events(limit=1)[0]
    assert disabled.artifact_spool_enabled is False
    assert disabled_event["event_type"] == "llm.artifact.resolved"
    assert disabled_event["artifacts"]["sha256"]
    assert disabled_event["artifacts"]["uri"] is None
    disabled.completed(disabled_attempt, response_payload={"content": "done"})

    root = tmp_path / "env-spool"
    monkeypatch.setenv(LLM_ARTIFACT_SPOOL_DIR_ENV, str(root))
    enabled = LLMInvocationRecorder()
    enabled.requested(
        provider="test-provider",
        model="test-model",
        operation="chat",
        request_payload={"content": "durable"},
    )
    assert await enabled.flush_artifacts_async(timeout=5)
    enabled_call = enabled.recent_calls(limit=1)[0]
    assert enabled.artifact_spool_enabled is True
    assert enabled_call["request_uri"].startswith(root.as_uri())
    assert await enabled.close_artifacts_async(timeout=5)
    assert close_shared_llm_artifact_spools(timeout=5)


def test_reader_rejects_uri_outside_root_and_hash_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "spool"
    spool = LLMArtifactSpool(root)
    reference = spool.enqueue_redacted({"content": "safe"})
    assert reference.uri is not None
    assert spool.flush(timeout=5)

    outside = tmp_path / f"{reference.sha256}.json"
    outside.write_text('{"content":"safe"}', encoding="utf-8")
    with pytest.raises(LLMArtifactSpoolError, match="canonical|escapes"):
        spool.read(uri=outside.as_uri(), expected_sha256=reference.sha256)
    with pytest.raises(LLMArtifactSpoolError, match="does not match"):
        spool.read(uri=reference.uri, expected_sha256="0" * 64)

    canonical = Path(unquote(urlparse(reference.uri).path))
    real_artifact = canonical.with_name(f"real-{canonical.name}")
    canonical.replace(real_artifact)
    canonical.symlink_to(real_artifact)
    with pytest.raises(LLMArtifactSpoolError, match="symbolic links"):
        spool.read(uri=reference.uri, expected_sha256=reference.sha256)

    assert spool.close(timeout=5)


def test_spool_root_must_be_absolute() -> None:
    with pytest.raises(LLMArtifactSpoolError, match="absolute"):
        LLMArtifactSpool(Path("relative-artifact-spool"))


def test_deduplicated_reference_refreshes_retention_mtime(tmp_path: Path) -> None:
    spool = LLMArtifactSpool(tmp_path / "spool")
    reference = spool.enqueue_redacted({"content": "reused"})
    assert reference.uri is not None
    assert spool.flush(timeout=5)
    path = Path(unquote(urlparse(reference.uri).path))
    old_timestamp = time.time() - 86_400
    path.touch()
    path.chmod(0o600)
    # Explicitly make the artifact look retention-expired before it is reused.
    os.utime(path, (old_timestamp, old_timestamp))
    assert path.stat().st_mtime <= old_timestamp + 1

    duplicate = spool.enqueue_redacted({"content": "reused"})
    assert duplicate == reference
    assert spool.flush(timeout=5)
    assert path.stat().st_mtime > old_timestamp + 1
    assert spool.diagnostics["deduplicated"] == 1
    assert spool.close(timeout=5)


def test_retention_prunes_old_relation_but_keeps_cas_referenced_by_new_trace(
    tmp_path: Path,
) -> None:
    spool = LLMArtifactSpool(
        tmp_path / "retention",
        retention_seconds=100,
        cleanup_interval_seconds=10_000,
    )
    payload = {"content": "shared by two traces"}
    first_id = "llm_artifact_" + "a" * 32
    second_id = "llm_artifact_" + "b" * 32
    spool.enqueue_payload(
        payload,
        provider_attempt_id="attempt-old",
        artifact_kind="request",
        redactor=lambda value: value,
        provisional_id=first_id,
    )
    spool.enqueue_payload(
        payload,
        provider_attempt_id="attempt-new",
        artifact_kind="request",
        redactor=lambda value: value,
        provisional_id=second_id,
    )
    assert spool.flush(timeout=5)
    digest = hashlib.sha256(canonical_artifact_bytes(payload)).hexdigest()
    cas_path = spool._path_for_digest(digest)
    first_relation = spool._relation_path(first_id)
    second_relation = spool._relation_path(second_id)
    now = time.time()
    old = now - 1_000
    first_value = json.loads(first_relation.read_text(encoding="utf-8"))
    first_value["resolved_at"] = old
    spool._atomic_write_json(first_relation, first_value)
    os.utime(first_relation, (old, old))
    os.utime(cas_path, (old, old))

    result = spool.prune_expired(now=now)

    assert result == {
        "relations_removed": 1,
        "artifacts_removed": 0,
        "artifact_bytes_removed": 0,
        "unsafe_relation_state": 0,
    }
    assert not first_relation.exists()
    assert second_relation.exists()
    assert cas_path.exists(), "a retention-window relation still references the digest"
    status = spool.storage_status(now=now)
    assert status["relations"]["items"] == 1
    assert status["artifacts"]["items"] == 1

    second_value = json.loads(second_relation.read_text(encoding="utf-8"))
    second_value["resolved_at"] = old
    spool._atomic_write_json(second_relation, second_value)
    os.utime(second_relation, (old, old))
    os.utime(cas_path, (old, old))
    result = spool.prune_expired(now=now)
    assert result["relations_removed"] == 1
    assert result["artifacts_removed"] == 1
    assert not second_relation.exists()
    assert not cas_path.exists()
    assert spool.close(timeout=5)


def test_pending_recovery_relation_prevents_cas_retention_deletion(
    tmp_path: Path,
) -> None:
    spool = LLMArtifactSpool(
        tmp_path / "pending-retention",
        retention_seconds=10,
        cleanup_interval_seconds=10_000,
    )
    payload = {"prompt": "still pending recovery"}
    reference = spool.enqueue_redacted(payload)
    assert spool.flush(timeout=5)
    assert reference.uri is not None
    cas_path = Path(unquote(urlparse(reference.uri).path))
    old = time.time() - 1_000
    os.utime(cas_path, (old, old))
    provisional_id = "llm_artifact_" + "c" * 32
    spool._atomic_write_json(
        spool._pending_path(provisional_id),
        {
            "schema": "usmsb.llm-artifact-pending.v1",
            "provisional_id": provisional_id,
            "provider_attempt_id": "attempt-pending",
            "artifact_kind": "request",
            "created_at": old,
            "payload": payload,
        },
    )

    result = spool.prune_expired(now=time.time())

    assert result["artifacts_removed"] == 0
    assert cas_path.exists()
    # Remove the synthetic recovery boundary before graceful close; it has
    # already proved that cleanup cannot invalidate a replayable pending item.
    spool._pending_path(provisional_id).unlink()
    assert spool.close(timeout=5)


def test_startup_and_periodic_retention_cleanup_are_executed(tmp_path: Path) -> None:
    root = tmp_path / "scheduled-retention"
    first = LLMArtifactSpool(
        root,
        retention_seconds=1,
        cleanup_interval_seconds=1,
    )
    expired = first.enqueue_redacted({"artifact": "startup-expired"})
    assert first.flush(timeout=5)
    assert expired.uri is not None
    expired_path = Path(unquote(urlparse(expired.uri).path))
    old = time.time() - 10
    os.utime(expired_path, (old, old))
    assert first.close(timeout=5)

    restarted = LLMArtifactSpool(
        root,
        retention_seconds=1,
        cleanup_interval_seconds=1,
    )
    assert restarted.flush(timeout=5)
    assert not expired_path.exists()
    assert restarted.diagnostics["artifacts_pruned"] >= 1
    assert restarted.diagnostics["last_cleanup_at"] > 0

    periodic = restarted.enqueue_redacted({"artifact": "periodic-expired"})
    assert restarted.flush(timeout=5)
    assert periodic.uri is not None
    periodic_path = Path(unquote(urlparse(periodic.uri).path))
    os.utime(periodic_path, (old, old))
    # Force the next resolved relation through the periodic branch without a
    # wall-clock sleep; production uses cleanup_interval_seconds.
    restarted._last_cleanup_monotonic = 0.0
    restarted.enqueue_payload(
        {"artifact": "periodic-trigger"},
        provider_attempt_id="attempt-periodic-trigger",
        artifact_kind="request",
        redactor=lambda value: value,
        provisional_id="llm_artifact_" + "d" * 32,
    )
    assert restarted.flush(timeout=5)
    assert not periodic_path.exists()
    assert restarted.diagnostics["artifacts_pruned"] >= 2
    assert restarted.close(timeout=5)


def test_byte_limits_drop_uri_without_blocking_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(LLM_ARTIFACT_SPOOL_DIR_ENV, str(tmp_path / "bounded"))
    monkeypatch.setenv(LLM_ARTIFACT_SPOOL_MAX_ARTIFACT_BYTES_ENV, "16")
    recorder = LLMInvocationRecorder()

    attempt_id = recorder.requested(
        provider="test-provider",
        model="test-model",
        operation="chat",
        request_payload={"content": "this payload is deliberately larger than sixteen bytes"},
    )
    recorder.completed(attempt_id, response_payload={"content": "done"})

    initial_requested = [
        event
        for event in recorder.recent_events(limit=10)
        if event["event_type"] == "llm.provider.requested"
    ][0]
    assert initial_requested["artifacts"]["request_provisional_id"]
    assert initial_requested["artifacts"]["request_uri"] is None
    assert recorder.recent_calls(limit=1)[0]["status"] == "completed"
    assert recorder.flush_artifacts(timeout=5) is False
    assert recorder.recent_calls(limit=1)[0]["request_artifact_status"] == (
        "artifact_too_large"
    )
    assert close_shared_llm_artifact_spools(timeout=5) is False


def test_shared_env_spool_uses_one_worker_and_required_config_fails_fast(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(LLM_ARTIFACT_SPOOL_DIR_ENV, str(tmp_path / "shared"))
    first = LLMInvocationRecorder()
    second = LLMInvocationRecorder()
    assert first.artifact_spool is second.artifact_spool
    assert first.close_artifacts(timeout=5)
    assert second.artifact_spool is not None
    assert second.artifact_spool.diagnostics["closed"] is False
    assert close_shared_llm_artifact_spools(timeout=5)

    monkeypatch.delenv(LLM_ARTIFACT_SPOOL_DIR_ENV, raising=False)
    monkeypatch.setenv(LLM_ARTIFACT_SPOOL_REQUIRED_ENV, "true")
    with pytest.raises(LLMArtifactSpoolError, match="required"):
        LLMInvocationRecorder()


def test_required_request_and_terminal_events_are_nonblocking_then_durable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(LLM_ARTIFACT_SPOOL_REQUIRED_ENV, "true")
    root = tmp_path / "required-boundary"
    spool = LLMArtifactSpool(root)
    recorder = LLMInvocationRecorder(artifact_spool=spool, capture_payloads=False)

    attempt_id = recorder.requested(
        provider="test-provider",
        model="test-model",
        operation="chat",
        request_payload={"prompt": "durable before provider", "api_key": "secret"},
    )

    # Provider admission transfers ownership only; the caller does not wait for
    # redaction, JSON, hashing or fsync. Graceful flush establishes durability.
    assert spool.diagnostics["inflight_provider_attempts"] == 1
    assert spool.flush(timeout=5)
    detail = recorder.recent_calls(limit=1)[0]
    request_relation_path = spool._relation_path(detail["request_provisional_id"])
    request_relation = json.loads(request_relation_path.read_text(encoding="utf-8"))
    requested_event = request_relation["invocation_event"]
    assert request_relation["status"] == "resolved"
    assert detail["request_artifact_status"] == "resolved"
    assert detail["request_uri"].startswith(root.as_uri())
    assert requested_event["event_type"] == "llm.provider.requested"
    assert requested_event["provider_attempt_id"] == attempt_id
    assert "secret" not in json.dumps(request_relation)

    recorder.completed(
        attempt_id,
        response_payload={"content": "terminal evidence", "access_token": "secret"},
        usage={"prompt_tokens": 30, "completion_tokens": 60, "total_tokens": 90},
    )
    assert spool.diagnostics["inflight_provider_attempts"] == 0
    assert spool.flush(timeout=5)
    detail = recorder.recent_calls(limit=1)[0]
    response_relation_path = spool._relation_path(detail["response_provisional_id"])
    response_relation = json.loads(response_relation_path.read_text(encoding="utf-8"))
    terminal_event = response_relation["invocation_event"]
    assert response_relation["status"] == "resolved"
    assert detail["response_artifact_status"] == "resolved"
    assert terminal_event["event_type"] == "llm.provider.completed"
    assert terminal_event["usage"]["total_tokens"] == 90
    assert "secret" not in json.dumps(response_relation)

    requested_event_id = requested_event["event_id"]
    terminal_event_id = terminal_event["event_id"]
    assert spool.close(timeout=5)

    # Restart replay recovers the exact stable events from their durable
    # artifact relations; downstream consumers can deduplicate by event_id.
    restarted_spool = LLMArtifactSpool(root)
    restarted_recorder = LLMInvocationRecorder(artifact_spool=restarted_spool)
    replayed = restarted_recorder.recent_events(limit=20)
    assert requested_event_id in {event["event_id"] for event in replayed}
    assert terminal_event_id in {event["event_id"] for event in replayed}
    assert restarted_spool.close(timeout=5)


def test_required_async_persistence_failure_blocks_next_provider_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(LLM_ARTIFACT_SPOOL_REQUIRED_ENV, "true")
    spool = LLMArtifactSpool(tmp_path / "required-failure")
    recorder = LLMInvocationRecorder(artifact_spool=spool)
    provider_calls = 0

    def fail_write(_path, _payload):
        raise OSError("disk unavailable")

    spool._atomic_write_json = fail_write  # type: ignore[method-assign]

    first_attempt = recorder.requested(
        provider="test-provider",
        model="test-model",
        operation="chat",
        request_payload={"prompt": "accepted before latent disk failure"},
    )
    provider_calls += 1
    recorder.failed(
        first_attempt,
        "provider finished before persistence failure became observable",
    )
    _wait_until(lambda: spool.diagnostics["write_failures"] > 0)

    def next_adapter_call() -> None:
        nonlocal provider_calls
        recorder.requested(
            provider="test-provider",
            model="test-model",
            operation="chat",
            request_payload={"prompt": "must never reach provider"},
        )
        provider_calls += 1

    with pytest.raises(LLMArtifactSpoolError, match="handoff rejected.*unhealthy"):
        next_adapter_call()

    assert provider_calls == 1
    assert [item["provider_attempt_id"] for item in recorder.recent_calls(limit=10)] == [
        first_attempt
    ]
    assert not any(
        event["event_type"] == "llm.provider.requested"
        for event in recorder.recent_events(limit=10)
    )
    assert spool.diagnostics["write_failures"] >= 1
    assert spool.close(timeout=5) is False


def test_payload_queue_pressure_is_bounded_without_memory_overflow(
    tmp_path: Path,
) -> None:
    spool = LLMArtifactSpool(tmp_path / "bounded-payload-queue", max_queue=1)
    # Consume the startup cleanup control item before deliberately saturating
    # the one-slot provider payload queue.
    assert spool.flush(timeout=5)
    redactor_started = threading.Event()
    release_redactor = threading.Event()

    def blocked_redactor(value):
        redactor_started.set()
        assert release_redactor.wait(timeout=5)
        return value

    first = spool.enqueue_payload(
        {"content": "first"},
        provider_attempt_id="attempt-first",
        artifact_kind="request",
        redactor=blocked_redactor,
        provisional_id="llm_artifact_" + "e" * 32,
    )
    assert first.enqueue_status == "provisional"
    assert redactor_started.wait(timeout=1)
    second = spool.enqueue_payload(
        {"content": "second"},
        provider_attempt_id="attempt-second",
        artifact_kind="request",
        redactor=lambda value: value,
        provisional_id="llm_artifact_" + "f" * 32,
    )
    third = spool.enqueue_payload(
        {"content": "third"},
        provider_attempt_id="attempt-third",
        artifact_kind="request",
        redactor=lambda value: value,
        provisional_id="llm_artifact_" + "0" * 32,
    )
    assert second.enqueue_status == "provisional"
    assert third.enqueue_status == "queue_full"
    assert spool.diagnostics["memory_spill_depth"] == 0
    assert spool.diagnostics["queue_overflows"] == 1
    release_redactor.set()
    assert spool.close(timeout=5)


def test_required_provider_inflight_and_terminal_spill_are_bounded_fifo(
    tmp_path: Path,
) -> None:
    spool = LLMArtifactSpool(tmp_path / "bounded-required-handoffs", max_queue=3)
    assert spool.flush(timeout=5)
    redactor_started = threading.Event()
    release_redactor = threading.Event()
    resolutions = []
    spool.add_resolution_callback(resolutions.append)

    def blocked_redactor(value):
        redactor_started.set()
        assert release_redactor.wait(timeout=5)
        return value

    for index in range(3):
        reference = spool.enqueue_payload(
            {"request": index},
            provider_attempt_id=f"attempt-{index}",
            artifact_kind="request",
            redactor=blocked_redactor if index == 0 else (lambda value: value),
            provider_phase="requested",
            require_healthy=True,
        )
        assert reference.enqueue_status == "provisional"
    assert redactor_started.wait(timeout=1)

    overflowed = spool.enqueue_payload(
        {"request": "must-wait"},
        provider_attempt_id="attempt-new",
        artifact_kind="request",
        redactor=lambda value: value,
        provider_phase="requested",
        require_healthy=True,
    )
    assert overflowed.enqueue_status == "queue_full"

    for index in range(3):
        terminal = spool.enqueue_payload(
            {"response": index},
            provider_attempt_id=f"attempt-{index}",
            artifact_kind="response",
            redactor=lambda value: value,
            provider_phase="terminal",
        )
        assert terminal.enqueue_status == "provisional"
    assert spool.diagnostics["inflight_provider_attempts"] == 0
    assert spool.diagnostics["memory_spill_depth"] == 2

    still_blocked = spool.enqueue_payload(
        {"request": "must-not-overtake-terminal-spill"},
        provider_attempt_id="attempt-after-terminal",
        artifact_kind="request",
        redactor=lambda value: value,
        provider_phase="requested",
        require_healthy=True,
    )
    assert still_blocked.enqueue_status == "queue_full"

    release_redactor.set()
    assert spool.flush(timeout=10)
    assert [
        (item.provider_attempt_id, item.artifact_kind)
        for item in resolutions
    ] == [
        ("attempt-0", "request"),
        ("attempt-1", "request"),
        ("attempt-2", "request"),
        ("attempt-0", "response"),
        ("attempt-1", "response"),
        ("attempt-2", "response"),
    ]
    assert spool.close(timeout=5)


def test_extended_credentials_and_signed_urls_are_redacted(tmp_path: Path) -> None:
    recorder = LLMInvocationRecorder(artifact_spool_dir=str(tmp_path / "spool"))
    attempt_id = recorder.requested(
        provider="test-provider",
        model="test-model",
        operation="chat",
        request_payload={
            "headers": {
                "X-API-Key": "x-api-secret",
                "Cookie": "session=cookie-secret",
            },
            "asset_url": (
                "https://example.test/image.png?X-Amz-Signature=url-secret&size=large"
            ),
            "prompt": "ordinary prompt remains intact",
        },
    )
    recorder.completed(attempt_id, response_payload={"content": "ok"})
    assert recorder.flush_artifacts(timeout=5)
    call = recorder.recent_calls(limit=1)[0]
    assert recorder.artifact_spool is not None
    restored = recorder.artifact_spool.read(
        uri=call["request_uri"],
        expected_sha256=call["request_hash"],
    )
    assert restored["headers"] == {
        "X-API-Key": "[REDACTED]",
        "Cookie": "[REDACTED]",
    }
    assert "url-secret" not in restored["asset_url"]
    assert "size=large" in restored["asset_url"]
    assert restored["prompt"] == "ordinary prompt remains intact"
    assert recorder.close_artifacts(timeout=5)


def test_recorder_reopens_owned_spool_after_stop_start(tmp_path: Path) -> None:
    root = tmp_path / "restartable"
    recorder = LLMInvocationRecorder(artifact_spool_dir=str(root))
    first_attempt = recorder.requested(
        provider="test-provider",
        model="test-model",
        operation="chat",
        request_payload={"content": "before stop"},
    )
    recorder.completed(first_attempt, response_payload={"content": "done"})
    assert recorder.close_artifacts(timeout=5)
    assert recorder.artifact_spool_enabled is False

    assert recorder.reopen_artifacts()
    assert recorder.artifact_spool_enabled is True
    second_attempt = recorder.requested(
        provider="test-provider",
        model="test-model",
        operation="chat",
        request_payload={"content": "after restart"},
    )
    recorder.completed(second_attempt, response_payload={"content": "done again"})
    assert recorder.flush_artifacts(timeout=5)
    second_call = recorder.recent_calls(limit=1)[0]
    assert second_call["request_uri"].startswith(root.as_uri())
    assert recorder.close_artifacts(timeout=5)


def test_pending_relation_is_recovered_after_process_restart(tmp_path: Path) -> None:
    root = tmp_path / "recoverable"
    crashed = LLMArtifactSpool(root)
    provisional_id = "llm_artifact_" + "1" * 32
    attempt_id = "attempt-after-crash"
    pending_path = crashed._pending_path(provisional_id)
    redacted = {"prompt": "recover me", "api_key": "[REDACTED]"}
    assert crashed.close(timeout=5)

    # This is the durable boundary a killed worker leaves behind after
    # redaction but before CAS/relation completion.
    crashed._atomic_write_json(
        pending_path,
        {
            "schema": "usmsb.llm-artifact-pending.v1",
            "provisional_id": provisional_id,
            "provider_attempt_id": attempt_id,
            "artifact_kind": "request",
            "created_at": time.time(),
            "payload": redacted,
        },
    )

    resolutions = []
    restarted = LLMArtifactSpool(root)
    restarted.add_resolution_callback(resolutions.append, replay_existing=True)
    assert restarted.flush(timeout=5)
    _wait_until(lambda: bool(resolutions))
    resolution = resolutions[-1]
    assert resolution.provisional_id == provisional_id
    assert resolution.provider_attempt_id == attempt_id
    assert resolution.status == "resolved"
    assert resolution.sha256 == hashlib.sha256(canonical_artifact_bytes(redacted)).hexdigest()
    assert restarted.read(uri=resolution.uri, expected_sha256=resolution.sha256) == redacted
    assert not pending_path.exists()
    assert (root / "relations" / f"{provisional_id}.json").exists()
    assert restarted.close(timeout=5)


def test_close_drains_queue_and_resolution_replay_is_idempotent(tmp_path: Path) -> None:
    root = tmp_path / "drain"
    spool = LLMArtifactSpool(root, max_queue=32)
    recorder = LLMInvocationRecorder(artifact_spool=spool, capture_payloads=False)
    for index in range(12):
        recorder.requested(
            provider="test-provider",
            model="test-model",
            operation="chat",
            request_payload={"index": index, "content": "x" * 1024},
        )
    assert spool.close(timeout=10)
    assert len(list((root / "relations").glob("*.json"))) == 12
    assert spool.diagnostics["memory_spill_depth"] == 0

    replay_spool = LLMArtifactSpool(root)
    replay_recorder = LLMInvocationRecorder(artifact_spool=replay_spool)
    first_ids = {
        event["event_id"]
        for event in replay_recorder.recent_events(limit=100)
        if event["event_type"] == "llm.artifact.resolved"
    }
    assert len(first_ids) == 12
    replay_spool.remove_resolution_callback(replay_recorder._on_artifact_resolved)
    replay_spool.add_resolution_callback(
        replay_recorder._on_artifact_resolved,
        replay_existing=True,
    )
    second_ids = {
        event["event_id"]
        for event in replay_recorder.recent_events(limit=100)
        if event["event_type"] == "llm.artifact.resolved"
    }
    assert second_ids == first_ids
    assert replay_spool.close(timeout=5)


def test_close_control_enqueue_failure_can_be_retried(tmp_path: Path) -> None:
    spool = LLMArtifactSpool(tmp_path / "spool")
    original_put = spool._put_control_item
    attempts = 0

    def fail_first_control_put(item, *, timeout):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return False
        return original_put(item, timeout=timeout)

    spool._put_control_item = fail_first_control_put  # type: ignore[method-assign]
    assert spool.close(timeout=0) is False
    assert spool.diagnostics["closed"] is False
    assert spool.close(timeout=5)
    assert spool.diagnostics["closed"] is True
