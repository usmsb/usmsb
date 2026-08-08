"""Budgeted, reference-preserving Context Loop for long-running harness runs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Protocol

from usmsb_sdk.growth_economic_harness.models import (
    ArtifactRecord,
    ContextEntry,
    ExperienceRecord,
    HarnessCheckpoint,
    ToolDescriptor,
)
from usmsb_sdk.growth_economic_harness.ports import ModelTurnRequest


class ContextBudgetExceeded(RuntimeError):
    """The complete model request cannot fit without discarding canonical facts."""


def estimate_tokens(text: str) -> int:
    """Conservative dependency-free estimate used for admission and compaction."""

    if not text:
        return 0
    ascii_count = sum(1 for char in text if ord(char) < 128)
    non_ascii_count = len(text) - ascii_count
    return max(1, (ascii_count + 3) // 4 + non_ascii_count)


@dataclass(frozen=True)
class ContextBudget:
    max_input_tokens: int = 48_000
    reserved_output_tokens: int = 8_000
    preserve_recent_entries: int = 12
    max_resolved_artifact_bytes: int = 256_000

    def __post_init__(self) -> None:
        values = {
            "max_input_tokens": self.max_input_tokens,
            "reserved_output_tokens": self.reserved_output_tokens,
            "preserve_recent_entries": self.preserve_recent_entries,
            "max_resolved_artifact_bytes": self.max_resolved_artifact_bytes,
        }
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values.values()):
            raise ValueError("context budget values must be integers")
        if self.max_input_tokens < 1 or self.reserved_output_tokens < 0:
            raise ValueError("context token limits are invalid")
        if self.reserved_output_tokens >= self.max_input_tokens:
            raise ValueError("reserved output must be smaller than the input limit")
        if self.preserve_recent_entries < 1 or self.max_resolved_artifact_bytes < 0:
            raise ValueError("context preservation limits are invalid")

    @property
    def usable_input_tokens(self) -> int:
        return self.max_input_tokens - self.reserved_output_tokens


@dataclass(frozen=True)
class SemanticCompactionRequest:
    run_id: str
    objective: dict[str, Any]
    entries: tuple[ContextEntry, ...]
    required_artifact_refs: tuple[str, ...]
    open_commitments: tuple[str, ...]
    failure_facts: tuple[dict[str, Any], ...]
    target_tokens: int


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
    ) -> None:
        self.budget = budget or ContextBudget()
        self.semantic_compactor = semantic_compactor

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
        artifacts = self._unique_artifacts(resolved_artifacts or [])
        request = self._request(
            candidate,
            tools=tools,
            experiences=experiences,
            artifacts=artifacts,
            last_validation_error=last_validation_error,
        )
        usable = self._usable_tokens(candidate)
        estimated = self._request_tokens(request)
        if estimated <= usable:
            return PreparedModelTurn(candidate, request, estimated, usable)

        candidate = await self._compact_for_request(candidate, target_tokens=usable)
        request = self._request(
            candidate,
            tools=tools,
            experiences=experiences,
            artifacts=artifacts,
            last_validation_error=last_validation_error,
        )
        estimated = self._request_tokens(request)
        if estimated > usable:
            raise ContextBudgetExceeded(
                "complete model request exceeds input budget after semantic compaction: "
                f"estimated={estimated}, usable={usable}; reduce tools, memories, artifacts, "
                "checkpoint metadata, or inject a stronger semantic compactor"
            )
        return PreparedModelTurn(candidate, request, estimated, usable)

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
        artifact_refs = self._artifact_refs(older)
        failures = self._failure_facts(older)
        request = SemanticCompactionRequest(
            run_id=checkpoint.run_id,
            objective=checkpoint.objective.model_dump(mode="json"),
            entries=tuple(older),
            required_artifact_refs=tuple(artifact_refs),
            open_commitments=tuple(checkpoint.open_commitments),
            failure_facts=tuple(failures),
            target_tokens=max(1, target_tokens // 3),
        )
        if self.semantic_compactor is None:
            compact_entry = self._deterministic_entry(request)
        else:
            compact_entry = await self.semantic_compactor.compact(request)
            compact_entry = self._enforce_compaction_invariants(compact_entry, request)

        return checkpoint.model_copy(
            update={
                "context": [compact_entry, *recent],
                "compacted_entries": checkpoint.compacted_entries + len(older),
            }
        )

    def _compact_deterministically(self, checkpoint: HarnessCheckpoint) -> HarnessCheckpoint:
        context = list(checkpoint.context)
        preserve = self.budget.preserve_recent_entries
        if len(context) <= preserve:
            return checkpoint
        older = context[:-preserve]
        request = SemanticCompactionRequest(
            run_id=checkpoint.run_id,
            objective=checkpoint.objective.model_dump(mode="json"),
            entries=tuple(older),
            required_artifact_refs=tuple(self._artifact_refs(older)),
            open_commitments=tuple(checkpoint.open_commitments),
            failure_facts=tuple(self._failure_facts(older)),
            target_tokens=max(1, self._usable_tokens(checkpoint) // 3),
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
        artifact_refs = list(compact_entry.artifact_refs)
        for artifact_ref in request.required_artifact_refs:
            if artifact_ref not in artifact_refs:
                artifact_refs.append(artifact_ref)
        metadata = {
            **compact_entry.metadata,
            "compacted_count": len(request.entries),
            "preserved_commitments": list(request.open_commitments),
            "preserved_failures": list(request.failure_facts),
            "semantic": True,
        }
        return compact_entry.model_copy(
            update={"kind": "compact", "artifact_refs": artifact_refs, "metadata": metadata}
        )

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
            checkpoint_metadata=checkpoint.metadata,
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
            usable = min(usable, max(1, continuity_budget.model_context_window - reserved))
        if continuity_budget.max_input_tokens is not None:
            usable = min(usable, continuity_budget.max_input_tokens)
        return max(1, usable)

    @staticmethod
    def _request_tokens(request: ModelTurnRequest) -> int:
        return estimate_tokens(request.model_dump_json())

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
        return checkpoint.model_copy(
            update={
                "context": context,
                "experience_candidates": candidates,
                "open_commitments": list(dict.fromkeys(checkpoint.open_commitments)),
            }
        )

    @staticmethod
    def _unique_experiences(records: list[ExperienceRecord]) -> list[ExperienceRecord]:
        values: dict[str, ExperienceRecord] = {}
        for record in records:
            values.setdefault(record.experience_id, record)
        return list(values.values())

    def _unique_artifacts(self, records: list[ArtifactRecord]) -> list[ArtifactRecord]:
        values: dict[str, ArtifactRecord] = {}
        for record in records:
            values.setdefault(record.artifact_ref, record)
        unique = list(values.values())
        total_bytes = 0
        for record in unique:
            content_bytes = (
                len(record.content.encode("utf-8")) if record.content is not None else 0
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
