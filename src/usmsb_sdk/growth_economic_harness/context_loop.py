"""Reference-preserving Context Loop for long-running harness checkpoints."""

from __future__ import annotations

from dataclasses import dataclass

from usmsb_sdk.growth_economic_harness.models import ContextEntry, HarnessCheckpoint


def estimate_tokens(text: str) -> int:
    """Conservative dependency-free estimate used only for admission/compaction."""

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

    @property
    def usable_input_tokens(self) -> int:
        return max(1, self.max_input_tokens - self.reserved_output_tokens)


class ContextLoop:
    """Compact old projections while preserving objective, state and artifact refs.

    This is mechanical context hygiene, not business reasoning.  A model-backed
    compactor may replace it later through the same checkpoint contract.
    """

    def __init__(self, budget: ContextBudget | None = None) -> None:
        self.budget = budget or ContextBudget()

    def compact(self, checkpoint: HarnessCheckpoint) -> HarnessCheckpoint:
        serialized = checkpoint.model_dump_json()
        if estimate_tokens(serialized) <= self.budget.usable_input_tokens:
            return checkpoint

        context = list(checkpoint.context)
        preserve = self.budget.preserve_recent_entries
        if len(context) <= preserve:
            return checkpoint

        older = context[:-preserve]
        recent = context[-preserve:]
        artifact_refs: list[str] = []
        kind_counts: dict[str, int] = {}
        for entry in older:
            kind_counts[entry.kind] = kind_counts.get(entry.kind, 0) + 1
            for artifact_ref in entry.artifact_refs:
                if artifact_ref not in artifact_refs:
                    artifact_refs.append(artifact_ref)

        compact_entry = ContextEntry(
            kind="compact",
            summary=(
                f"Compacted {len(older)} earlier context entries. "
                "Full artifacts remain canonical and are referenced separately."
            ),
            artifact_refs=artifact_refs,
            metadata={"kind_counts": kind_counts, "compacted_count": len(older)},
        )
        return checkpoint.model_copy(
            update={
                "context": [compact_entry, *recent],
                "compacted_entries": checkpoint.compacted_entries + len(older),
            }
        )

