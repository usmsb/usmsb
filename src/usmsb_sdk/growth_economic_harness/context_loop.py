"""Budgeted, reference-preserving Context Loop for long-running harness runs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from usmsb_sdk.growth_economic_harness.models import (
    ArtifactRecord,
    ContinuityState,
    ContextEntry,
    ExperienceRecord,
    HarnessCheckpoint,
    MemoryManifest,
    ToolDescriptor,
)
from usmsb_sdk.growth_economic_harness.ports import (
    ModelTurnRequest,
    enforce_cognitive_request_policy,
)


class ContextBudgetExceeded(RuntimeError):
    """The complete model request cannot fit without discarding canonical facts."""


def estimate_tokens(text: str) -> int:
    """Fail-safe tokenizer-independent upper bound used for admission."""

    if not text:
        return 0
    # A token cannot encode less than zero bytes. Treating every UTF-8 byte as
    # one token intentionally overestimates JSON punctuation, hashes and CJK
    # rather than risking an over-context provider call.
    return max(1, len(text.encode("utf-8")))


@dataclass(frozen=True)
class ContextBudget:
    max_input_tokens: int = 48_000
    reserved_output_tokens: int = 8_000
    model_envelope_reserve_tokens: int = 8_000
    preserve_recent_entries: int = 12
    max_resolved_artifact_bytes: int = 256_000

    def __post_init__(self) -> None:
        values = {
            "max_input_tokens": self.max_input_tokens,
            "reserved_output_tokens": self.reserved_output_tokens,
            "model_envelope_reserve_tokens": self.model_envelope_reserve_tokens,
            "preserve_recent_entries": self.preserve_recent_entries,
            "max_resolved_artifact_bytes": self.max_resolved_artifact_bytes,
        }
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values.values()):
            raise ValueError("context budget values must be integers")
        if self.max_input_tokens < 1 or self.reserved_output_tokens < 0:
            raise ValueError("context token limits are invalid")
        if self.reserved_output_tokens >= self.max_input_tokens:
            raise ValueError("reserved output must be smaller than the input limit")
        if (
            self.reserved_output_tokens + self.model_envelope_reserve_tokens
            >= self.max_input_tokens
        ):
            raise ValueError("output and model-envelope reserves exhaust the input limit")
        if self.preserve_recent_entries < 1 or self.max_resolved_artifact_bytes < 0:
            raise ValueError("context preservation limits are invalid")

    @property
    def usable_input_tokens(self) -> int:
        return (
            self.max_input_tokens
            - self.reserved_output_tokens
            - self.model_envelope_reserve_tokens
        )

    @property
    def physical_input_tokens(self) -> int:
        """Limit for the exact system + prompt + schema envelope."""

        return self.max_input_tokens - self.reserved_output_tokens


@dataclass(frozen=True)
class SemanticCompactionRequest:
    run_id: str
    step_index: int
    objective: dict[str, Any]
    entries: tuple[ContextEntry, ...]
    required_artifact_refs: tuple[str, ...]
    open_commitments: tuple[str, ...]
    failure_facts: tuple[dict[str, Any], ...]
    target_tokens: int
    authorization: dict[str, Any]

    def __post_init__(self) -> None:
        enforce_cognitive_request_policy(
            self.authorization,
            {
                "run_id": self.run_id,
                "objective": self.objective,
                "entries": [item.model_dump(mode="json") for item in self.entries],
                "open_commitments": list(self.open_commitments),
                "failure_facts": list(self.failure_facts),
            },
        )


class SemanticContextCompactor(Protocol):
    async def compact(self, request: SemanticCompactionRequest) -> ContextEntry:
        """Return one grounded semantic summary without executing external tools."""


@dataclass(frozen=True)
class PreparedModelTurn:
    checkpoint: HarnessCheckpoint
    request: ModelTurnRequest
    estimated_input_tokens: int
    usable_input_tokens: int


class ContextLoop:
    """Assemble and admit the *whole* model request.

    The legacy synchronous :meth:`compact` API remains available. Production
    callers should use :meth:`prepare_model_turn`, which budgets objective,
    continuity, tools, memories, candidate experiences and repair feedback as
    one request. Oversized facts fail closed instead of being silently cut.
    """

    def __init__(
        self,
        budget: ContextBudget | None = None,
        *,
        semantic_compactor: SemanticContextCompactor | None = None,
        model_turn_token_estimator: Callable[[ModelTurnRequest], int] | None = None,
    ) -> None:
        self.budget = budget or ContextBudget()
        self.semantic_compactor = semantic_compactor
        self.model_turn_token_estimator = model_turn_token_estimator

    def compact(self, checkpoint: HarnessCheckpoint) -> HarnessCheckpoint:
        """Compatibility entry point using deterministic reference-safe compaction."""

        candidate = self._deduplicate_checkpoint(checkpoint)
        if self._checkpoint_tokens(candidate) <= self._usable_tokens(candidate):
            return candidate
        compacted = self._compact_deterministically(candidate)
        if self._checkpoint_tokens(compacted) > self._usable_tokens(compacted):
            raise ContextBudgetExceeded(
                "checkpoint exceeds context budget after lossless deterministic compaction"
            )
        return compacted

    async def prepare_model_turn(
        self,
        checkpoint: HarnessCheckpoint,
        *,
        tools: list[ToolDescriptor],
        recalled_experiences: list[ExperienceRecord],
        resolved_artifacts: list[ArtifactRecord] | None = None,
        last_validation_error: str | None = None,
    ) -> PreparedModelTurn:
        """Build a deduplicated request and compact only when the whole turn needs it."""

        candidate = self._deduplicate_checkpoint(checkpoint)
        experiences = self._unique_experiences(recalled_experiences)
        current_candidates = {
            record.experience_id: record for record in candidate.experience_candidates
        }
        filtered_experiences: list[ExperienceRecord] = []
        for experience in experiences:
            current = current_candidates.get(experience.experience_id)
            if current is not None:
                # The durable repository is authoritative for transitions that
                # happened after this checkpoint was written.
                current_candidates[experience.experience_id] = experience
                continue
            filtered_experiences.append(experience)
        candidate = candidate.model_copy(
            update={"experience_candidates": list(current_candidates.values())}
        )
        experiences = filtered_experiences
        artifacts = self._unique_artifacts(resolved_artifacts or [])
        request = self._request(
            candidate,
            tools=tools,
            experiences=experiences,
            artifacts=artifacts,
            last_validation_error=last_validation_error,
        )
        usable = self._model_turn_limit(candidate)
        estimated = self._request_tokens(request)
        if estimated <= usable:
            return PreparedModelTurn(candidate, request, estimated, usable)

        previous_tokens = estimated
        for _ in range(6):
            candidate = await self._compact_for_request(candidate, target_tokens=usable)
            request = self._request(
                candidate,
                tools=tools,
                experiences=experiences,
                artifacts=artifacts,
                last_validation_error=last_validation_error,
            )
            estimated = self._request_tokens(request)
            if estimated <= usable:
                return PreparedModelTurn(candidate, request, estimated, usable)
            if (
                estimated >= previous_tokens
                or len(candidate.context) <= self.budget.preserve_recent_entries
            ):
                break
            previous_tokens = estimated
        raise ContextBudgetExceeded(
            "complete model request exceeds input budget after semantic compaction: "
            f"estimated={estimated}, usable={usable}; reduce tools, memories, artifacts, "
            "checkpoint metadata, or inject a stronger semantic compactor"
        )

    async def _compact_for_request(
        self,
        checkpoint: HarnessCheckpoint,
        *,
        target_tokens: int,
    ) -> HarnessCheckpoint:
        context = list(checkpoint.context)
        preserve = self.budget.preserve_recent_entries
        if len(context) <= preserve:
            return checkpoint

        older = context[:-preserve]
        recent = context[-preserve:]
        compaction_overhead = estimate_tokens(
            json.dumps(
                {
                    "objective": checkpoint.objective.model_dump(mode="json"),
                    "open_commitments": checkpoint.open_commitments,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        ) + 4_000
        chunks = self._compaction_chunks(
            older,
            target_tokens=target_tokens,
            overhead_tokens=compaction_overhead,
        )
        compact_entries: list[ContextEntry] = []
        for index, chunk in enumerate(chunks):
            request = SemanticCompactionRequest(
                run_id=checkpoint.run_id,
                step_index=checkpoint.step_index,
                objective=checkpoint.objective.model_dump(mode="json"),
                entries=tuple(chunk),
                required_artifact_refs=tuple(self._artifact_refs(chunk)),
                open_commitments=(
                    tuple(checkpoint.open_commitments) if index == 0 else ()
                ),
                failure_facts=tuple(self._failure_facts(chunk)),
                target_tokens=max(1, target_tokens // max(3, len(chunks) + 1)),
                authorization=dict(
                    checkpoint.metadata.get("cognitive_data_authorization", {})
                ),
            )
            if self.semantic_compactor is None:
                compact_entry = self._deterministic_entry(request)
            else:
                compact_entry = await self.semantic_compactor.compact(request)
                compact_entry = self._enforce_compaction_invariants(
                    compact_entry,
                    request,
                )
            compact_entries.append(compact_entry)

        return checkpoint.model_copy(
            update={
                "context": [*compact_entries, *recent],
                "compacted_entries": checkpoint.compacted_entries + len(older),
            }
        )

    def _compaction_chunks(
        self,
        entries: list[ContextEntry],
        *,
        target_tokens: int,
        overhead_tokens: int,
    ) -> list[list[ContextEntry]]:
        available = min(self.budget.usable_input_tokens, target_tokens) - overhead_tokens
        if available < 2_000:
            raise ContextBudgetExceeded(
                "objective and commitments leave no safe semantic-compaction input budget"
            )
        # Failure facts and artifact-reference guards repeat part of each entry.
        max_chunk_tokens = max(1_000, available // 2)
        chunks: list[list[ContextEntry]] = []
        current: list[ContextEntry] = []
        current_tokens = 0
        for entry in entries:
            entry_tokens = estimate_tokens(entry.model_dump_json())
            if entry_tokens > max_chunk_tokens:
                raise ContextBudgetExceeded(
                    "one context entry exceeds the semantic compactor input budget; "
                    "store its body as an artifact and keep a bounded evidence summary"
                )
            if current and current_tokens + entry_tokens > max_chunk_tokens:
                chunks.append(current)
                current = []
                current_tokens = 0
            current.append(entry)
            current_tokens += entry_tokens
        if current:
            chunks.append(current)
        return chunks

    def _compact_deterministically(self, checkpoint: HarnessCheckpoint) -> HarnessCheckpoint:
        context = list(checkpoint.context)
        preserve = self.budget.preserve_recent_entries
        if len(context) <= preserve:
            return checkpoint
        older = context[:-preserve]
        request = SemanticCompactionRequest(
            run_id=checkpoint.run_id,
            step_index=checkpoint.step_index,
            objective=checkpoint.objective.model_dump(mode="json"),
            entries=tuple(older),
            required_artifact_refs=tuple(self._artifact_refs(older)),
            open_commitments=tuple(checkpoint.open_commitments),
            failure_facts=tuple(self._failure_facts(older)),
            target_tokens=max(1, self._usable_tokens(checkpoint) // 3),
            authorization=dict(
                checkpoint.metadata.get("cognitive_data_authorization", {})
            ),
        )
        return checkpoint.model_copy(
            update={
                "context": [self._deterministic_entry(request), *context[-preserve:]],
                "compacted_entries": checkpoint.compacted_entries + len(older),
            }
        )

    @staticmethod
    def _deterministic_entry(request: SemanticCompactionRequest) -> ContextEntry:
        kind_counts: dict[str, int] = {}
        for entry in request.entries:
            kind_counts[entry.kind] = kind_counts.get(entry.kind, 0) + 1
        failure_summaries = [item["summary"] for item in request.failure_facts]
        summary_parts = [
            f"Compacted {len(request.entries)} earlier context entries.",
            "Canonical details remain in the referenced immutable artifacts.",
        ]
        if request.open_commitments:
            summary_parts.append("Open commitments: " + json.dumps(list(request.open_commitments)))
        if failure_summaries:
            summary_parts.append("Observed failures: " + json.dumps(failure_summaries))
        summary = " ".join(summary_parts)
        if len(summary) > 30_000:
            raise ContextBudgetExceeded(
                "commitments and failure facts exceed the compact-entry schema; "
                "inject a semantic compactor"
            )
        return ContextEntry(
            kind="compact",
            summary=summary,
            artifact_refs=list(request.required_artifact_refs),
            metadata={
                "kind_counts": kind_counts,
                "compacted_count": len(request.entries),
                "preserved_commitments": list(request.open_commitments),
                "preserved_failures": list(request.failure_facts),
                "semantic": False,
            },
        )

    @staticmethod
    def _enforce_compaction_invariants(
        compact_entry: ContextEntry,
        request: SemanticCompactionRequest,
    ) -> ContextEntry:
        if estimate_tokens(compact_entry.model_dump_json()) > request.target_tokens:
            raise ContextBudgetExceeded(
                "semantic compactor output exceeds its target token budget"
            )
        required = set(request.required_artifact_refs)
        unknown = sorted(set(compact_entry.artifact_refs) - required)
        if unknown:
            raise ContextBudgetExceeded(
                "semantic compactor invented artifact refs: " + repr(unknown)
            )
        artifact_refs = list(compact_entry.artifact_refs)
        for artifact_ref in request.required_artifact_refs:
            if artifact_ref not in artifact_refs:
                artifact_refs.append(artifact_ref)
        # Model-authored metadata is informational only. Remove fields that
        # resemble machine-readable provenance so they cannot be promoted to
        # trusted evidence by a later projector.
        safe_metadata = {
            key: value
            for key, value in compact_entry.metadata.items()
            if not any(
                marker in key.lower()
                for marker in ("artifact_ref", "evidence_ref", "source_ref")
            )
        }
        metadata = {
            **safe_metadata,
            "compacted_count": len(request.entries),
            "preserved_commitments": list(request.open_commitments),
            "preserved_failures": list(request.failure_facts),
            "required_artifact_refs": list(request.required_artifact_refs),
            "semantic": True,
        }
        grounded = compact_entry.model_copy(
            update={"kind": "compact", "artifact_refs": artifact_refs, "metadata": metadata}
        )
        if estimate_tokens(grounded.model_dump_json()) > request.target_tokens:
            raise ContextBudgetExceeded(
                "reference-preserving compactor output exceeds its target token budget"
            )
        return grounded

    @staticmethod
    def _request(
        checkpoint: HarnessCheckpoint,
        *,
        tools: list[ToolDescriptor],
        experiences: list[ExperienceRecord],
        artifacts: list[ArtifactRecord],
        last_validation_error: str | None,
    ) -> ModelTurnRequest:
        continuity = checkpoint.continuity
        return ModelTurnRequest(
            run_id=checkpoint.run_id,
            step_index=checkpoint.step_index,
            objective=checkpoint.objective.model_dump(mode="json"),
            current_hypothesis=checkpoint.current_hypothesis,
            open_commitments=list(dict.fromkeys(checkpoint.open_commitments)),
            context=[entry.model_dump(mode="json") for entry in checkpoint.context],
            tools=tools,
            recalled_experiences=experiences,
            checkpoint_metadata=ContextLoop._project_checkpoint_metadata(
                checkpoint.metadata
            ),
            wake_events=continuity.wake_events if continuity else [],
            cycle_handoff=continuity.cycle_handoff if continuity else None,
            memory_manifest=continuity.memory_manifest if continuity else None,
            budget_context=continuity.budget_context if continuity else None,
            current_experience_candidates=checkpoint.experience_candidates,
            plan_state=checkpoint.plan_state,
            resolved_artifacts=artifacts,
            last_validation_error=last_validation_error,
        )

    def _usable_tokens(self, checkpoint: HarnessCheckpoint) -> int:
        usable = self.budget.usable_input_tokens
        continuity_budget = (
            checkpoint.continuity.budget_context
            if checkpoint.continuity is not None
            else None
        )
        if continuity_budget is None:
            return usable
        reserved = (
            continuity_budget.reserved_output_tokens
            if continuity_budget.reserved_output_tokens is not None
            else self.budget.reserved_output_tokens
        )
        if continuity_budget.model_context_window is not None:
            usable = min(
                usable,
                max(
                    1,
                    continuity_budget.model_context_window
                    - reserved
                    - self.budget.model_envelope_reserve_tokens,
                ),
            )
        if continuity_budget.max_input_tokens is not None:
            usable = min(
                usable,
                max(
                    1,
                    continuity_budget.max_input_tokens
                    - self.budget.model_envelope_reserve_tokens,
                ),
            )
        return max(1, usable)

    @staticmethod
    def project_checkpoint_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        """Remove duplicate first-class payloads while preserving audit identity."""

        first_class = {
            "tool_catalog_snapshot",
            "tool_catalog",
            "tools",
            "objective",
            "context",
            "wake_events",
            "cycle_handoff",
            "memory_manifest",
            "budget_context",
            "recalled_experiences",
            "experience_candidates",
            "plan_state",
        }
        projected: dict[str, Any] = {}
        omitted: list[str] = []
        audit_projection: dict[str, Any] = {}
        audit_markers = ("hash", "ref", "version", "count", "id", "etag", "digest")
        for key, value in metadata.items():
            if key not in first_class:
                projected[key] = value
                continue
            omitted.append(key)
            if isinstance(value, dict):
                audit_values = {
                    child_key: child_value
                    for child_key, child_value in value.items()
                    if any(marker in child_key.lower() for marker in audit_markers)
                    and isinstance(child_value, (str, int, float, bool, type(None)))
                }
                if audit_values:
                    audit_projection[key] = audit_values
        if omitted:
            projected["first_class_metadata_omitted"] = sorted(omitted)
        if audit_projection:
            projected["first_class_metadata_audit"] = audit_projection
        return projected

    # Kept as an implementation alias for callers built during the V3 migration.
    _project_checkpoint_metadata = project_checkpoint_metadata

    def _request_tokens(self, request: ModelTurnRequest) -> int:
        if self.model_turn_token_estimator is not None:
            estimated = self.model_turn_token_estimator(request)
            if isinstance(estimated, bool) or not isinstance(estimated, int) or estimated < 1:
                raise ContextBudgetExceeded(
                    "model-turn token estimator returned an invalid value"
                )
            return estimated
        return estimate_tokens(request.model_dump_json())

    def _model_turn_limit(self, checkpoint: HarnessCheckpoint) -> int:
        """Physical input limit when the estimator includes system/schema envelope."""

        if self.model_turn_token_estimator is None:
            return self._usable_tokens(checkpoint)
        limit = self.budget.physical_input_tokens
        continuity_budget = (
            checkpoint.continuity.budget_context
            if checkpoint.continuity is not None
            else None
        )
        if continuity_budget is None:
            return limit
        reserved = (
            continuity_budget.reserved_output_tokens
            if continuity_budget.reserved_output_tokens is not None
            else self.budget.reserved_output_tokens
        )
        if continuity_budget.model_context_window is not None:
            limit = min(
                limit,
                max(1, continuity_budget.model_context_window - reserved),
            )
        if continuity_budget.max_input_tokens is not None:
            limit = min(limit, continuity_budget.max_input_tokens)
        return max(1, limit)

    @staticmethod
    def _checkpoint_tokens(checkpoint: HarnessCheckpoint) -> int:
        return estimate_tokens(checkpoint.model_dump_json())

    @staticmethod
    def _deduplicate_checkpoint(checkpoint: HarnessCheckpoint) -> HarnessCheckpoint:
        seen: set[str] = set()
        context: list[ContextEntry] = []
        for entry in checkpoint.context:
            canonical = json.dumps(
                entry.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            if digest not in seen:
                seen.add(digest)
                context.append(entry)
        candidates = ContextLoop._unique_experiences(checkpoint.experience_candidates)
        continuity = ContextLoop._deduplicate_continuity(checkpoint.continuity)
        return checkpoint.model_copy(
            update={
                "context": context,
                "experience_candidates": candidates,
                "open_commitments": list(dict.fromkeys(checkpoint.open_commitments)),
                "continuity": continuity,
            }
        )

    @staticmethod
    def _deduplicate_continuity(
        continuity: ContinuityState | None,
    ) -> ContinuityState | None:
        if continuity is None:
            return None
        consumed = list(dict.fromkeys(continuity.consumed_wake_event_ids))
        consumed_set = set(consumed)
        events: dict[str, Any] = {}
        for event in continuity.wake_events:
            if event.event_id in consumed_set:
                continue
            existing = events.get(event.event_id)
            if existing is not None and existing != event:
                raise ContextBudgetExceeded(
                    f"conflicting wake events for {event.event_id!r}"
                )
            events.setdefault(event.event_id, event)
        manifest = continuity.memory_manifest
        if manifest is not None:
            memories: dict[str, Any] = {}
            for memory in manifest.memories:
                existing = memories.get(memory.memory_id)
                if existing is not None and existing != memory:
                    raise ContextBudgetExceeded(
                        f"conflicting memories for {memory.memory_id!r}"
                    )
                memories.setdefault(memory.memory_id, memory)
            manifest = MemoryManifest(
                query=manifest.query,
                memories=list(memories.values()),
                generated_at=manifest.generated_at,
                metadata=manifest.metadata,
            )
        handoff = continuity.cycle_handoff
        if handoff is not None:
            handoff = handoff.model_copy(
                update={
                    "open_commitments": list(dict.fromkeys(handoff.open_commitments)),
                    "unresolved": list(dict.fromkeys(handoff.unresolved)),
                    "failed_approaches": list(dict.fromkeys(handoff.failed_approaches)),
                    "wake_conditions": list(dict.fromkeys(handoff.wake_conditions)),
                    "artifact_refs": list(dict.fromkeys(handoff.artifact_refs)),
                    "experience_refs": list(dict.fromkeys(handoff.experience_refs)),
                }
            )
        return continuity.model_copy(
            update={
                "wake_events": list(events.values()),
                "cycle_handoff": handoff,
                "memory_manifest": manifest,
                "consumed_wake_event_ids": consumed,
            }
        )

    @staticmethod
    def _unique_experiences(records: list[ExperienceRecord]) -> list[ExperienceRecord]:
        values: dict[str, ExperienceRecord] = {}
        for record in records:
            existing = values.get(record.experience_id)
            if existing is not None and existing != record:
                raise ContextBudgetExceeded(
                    f"conflicting experience projections for {record.experience_id!r}"
                )
            values.setdefault(record.experience_id, record)
        return list(values.values())

    def _unique_artifacts(self, records: list[ArtifactRecord]) -> list[ArtifactRecord]:
        values: dict[str, ArtifactRecord] = {}
        for record in records:
            existing = values.get(record.artifact_ref)
            if existing is not None and existing != record:
                raise ContextBudgetExceeded(
                    f"conflicting artifact projections for {record.artifact_ref!r}"
                )
            values.setdefault(record.artifact_ref, record)
        unique = list(values.values())
        total_bytes = 0
        for record in unique:
            content_bytes = (
                len(record.content.encode("utf-8")) if record.content is not None else 0
            )
            if record.content is not None and record.byte_size is not None:
                if record.byte_size != content_bytes:
                    raise ContextBudgetExceeded(
                        f"artifact {record.artifact_ref!r} byte_size does not match content"
                    )
            if record.content is not None and record.content_hash is not None:
                actual_hash = hashlib.sha256(record.content.encode("utf-8")).hexdigest()
                declared_hash = record.content_hash.removeprefix("sha256:")
                if declared_hash != actual_hash:
                    raise ContextBudgetExceeded(
                        f"artifact {record.artifact_ref!r} content_hash does not match content"
                    )
            declared_bytes = record.byte_size or 0
            total_bytes += max(content_bytes, declared_bytes)
        if total_bytes > self.budget.max_resolved_artifact_bytes:
            raise ContextBudgetExceeded(
                "resolved artifacts exceed byte budget: "
                f"received={total_bytes}, allowed={self.budget.max_resolved_artifact_bytes}"
            )
        return unique

    @staticmethod
    def _artifact_refs(entries: list[ContextEntry]) -> list[str]:
        refs: list[str] = []
        for entry in entries:
            for artifact_ref in entry.artifact_refs:
                if artifact_ref not in refs:
                    refs.append(artifact_ref)
        return refs

    @staticmethod
    def _failure_facts(entries: list[ContextEntry]) -> list[dict[str, Any]]:
        failures: list[dict[str, Any]] = []
        for entry in entries:
            status = entry.metadata.get("status")
            error = entry.metadata.get("error")
            if status not in {"failed", "rejected", "outcome_unknown"} and not error:
                continue
            failures.append(
                {
                    "summary": entry.summary,
                    "status": status,
                    "error": error,
                    "action_id": entry.metadata.get("action_id"),
                    "artifact_refs": entry.artifact_refs,
                }
            )
        return failures
