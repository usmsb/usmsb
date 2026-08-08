"""Ports that keep cognition independent from OPC and tenant business models."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import Field

from usmsb_sdk.growth_economic_harness.models import (
    ArtifactRecord,
    BudgetContext,
    CycleHandoff,
    EpisodeOutcome,
    ExperienceEpisode,
    ExperienceRecord,
    ExperienceState,
    HarnessCheckpoint,
    MemoryManifest,
    ModelCompletion,
    PlanState,
    SkillManifest,
    StrictModel,
    TeamPlan,
    ToolDescriptor,
    WakeEvent,
)


class ModelTurnRequest(StrictModel):
    run_id: str
    step_index: int
    objective: dict[str, Any]
    current_hypothesis: str | None = None
    open_commitments: list[str] = Field(default_factory=list)
    context: list[dict[str, Any]] = Field(default_factory=list)
    tools: list[ToolDescriptor] = Field(default_factory=list)
    recalled_experiences: list[ExperienceRecord] = Field(default_factory=list)
    checkpoint_metadata: dict[str, Any] = Field(default_factory=dict)
    wake_events: list[WakeEvent] = Field(default_factory=list)
    cycle_handoff: CycleHandoff | None = None
    memory_manifest: MemoryManifest | None = None
    budget_context: BudgetContext | None = None
    current_experience_candidates: list[ExperienceRecord] = Field(default_factory=list)
    plan_state: PlanState | None = None
    resolved_artifacts: list[ArtifactRecord] = Field(default_factory=list)
    last_validation_error: str | None = None


class CognitiveModel(Protocol):
    async def complete(self, request: ModelTurnRequest) -> ModelCompletion:
        """Return one strict action decision as raw JSON."""


class GroupRequest(StrictModel):
    run_id: str
    step_index: int
    objective: dict[str, Any]
    team_plan: TeamPlan
    context: list[dict[str, Any]] = Field(default_factory=list)
    checkpoint_metadata: dict[str, Any] = Field(default_factory=dict)
    wake_events: list[WakeEvent] = Field(default_factory=list)
    cycle_handoff: CycleHandoff | None = None
    memory_manifest: MemoryManifest | None = None
    budget_context: BudgetContext | None = None
    current_experience_candidates: list[ExperienceRecord] = Field(default_factory=list)
    plan_state: PlanState | None = None
    recalled_experiences: list[ExperienceRecord] = Field(default_factory=list)
    resolved_artifacts: list[ArtifactRecord] = Field(default_factory=list)


class GroupContribution(StrictModel):
    role: str
    proposal: str
    evidence_refs: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    artifact_ref: str | None = None


class GroupResult(StrictModel):
    contributions: list[GroupContribution] = Field(min_length=1)
    synthesis: str
    conflicts: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)


class GroupReasoner(Protocol):
    async def deliberate(self, request: GroupRequest) -> GroupResult:
        """Run the exact team selected by the model; roles are not hard-coded."""


class ExperienceRepository(Protocol):
    async def recall(self, checkpoint: HarnessCheckpoint, *, limit: int) -> list[ExperienceRecord]:
        """Return tenant-scoped, applicable experiences."""

    async def persist_candidate(
        self,
        record: ExperienceRecord,
        *,
        checkpoint: HarnessCheckpoint,
    ) -> None:
        """Idempotently persist a model-proposed candidate and its provenance."""

    async def persist_episode(self, episode: ExperienceEpisode) -> None:
        """Persist an attributable action/observation/outcome episode."""

    async def outcomes(
        self,
        experience_id: str,
        *,
        limit: int,
    ) -> list[EpisodeOutcome]:
        """Return independently attributable outcomes used for evaluation."""

    async def transition(
        self,
        record: ExperienceRecord,
        *,
        target: ExperienceState,
        evidence: dict[str, Any],
    ) -> ExperienceRecord:
        """Persist an evidence-gated, compare-and-set state transition."""

    async def persist_skill(self, skill: SkillManifest) -> None:
        """Persist a declarative promoted skill; never executable model code."""


class ContextRepository(Protocol):
    async def recall_manifest(
        self,
        checkpoint: HarnessCheckpoint,
        *,
        query: str,
        limit: int,
    ) -> MemoryManifest | None:
        """Return goal-relevant working, episodic, semantic and skill memory."""


class ArtifactRepository(Protocol):
    async def read(
        self,
        artifact_refs: list[str],
        *,
        max_total_bytes: int,
    ) -> list[ArtifactRecord]:
        """Resolve only authorized immutable artifacts within a hard byte budget."""


class CheckpointRepository(Protocol):
    async def load(self, run_id: str) -> HarnessCheckpoint | None:
        """Load one tenant-scoped checkpoint."""

    async def save(
        self,
        checkpoint: HarnessCheckpoint,
        *,
        expected_step_index: int | None,
    ) -> None:
        """Durably compare-and-set a checkpoint without executing its action."""


class TelemetrySink(Protocol):
    async def model_attempt(
        self,
        *,
        run_id: str,
        step_index: int,
        attempt_index: int,
        completion: ModelCompletion,
        validation_error: str | None,
    ) -> None: ...

    async def event(self, name: str, payload: dict[str, Any]) -> None: ...


class NullTelemetry:
    async def model_attempt(self, **_: Any) -> None:
        return None

    async def event(self, name: str, payload: dict[str, Any]) -> None:
        del name, payload
        return None


class EmptyExperienceRepository:
    async def recall(self, checkpoint: HarnessCheckpoint, *, limit: int) -> list[ExperienceRecord]:
        del checkpoint, limit
        return []

    async def persist_candidate(
        self,
        record: ExperienceRecord,
        *,
        checkpoint: HarnessCheckpoint,
    ) -> None:
        del record, checkpoint

    async def persist_episode(self, episode: ExperienceEpisode) -> None:
        del episode

    async def outcomes(
        self,
        experience_id: str,
        *,
        limit: int,
    ) -> list[EpisodeOutcome]:
        del experience_id, limit
        return []

    async def transition(
        self,
        record: ExperienceRecord,
        *,
        target: ExperienceState,
        evidence: dict[str, Any],
    ) -> ExperienceRecord:
        del target, evidence
        return record

    async def persist_skill(self, skill: SkillManifest) -> None:
        del skill


class EmptyContextRepository:
    async def recall_manifest(
        self,
        checkpoint: HarnessCheckpoint,
        *,
        query: str,
        limit: int,
    ) -> MemoryManifest | None:
        del checkpoint, query, limit
        return None


class EmptyArtifactRepository:
    async def read(
        self,
        artifact_refs: list[str],
        *,
        max_total_bytes: int,
    ) -> list[ArtifactRecord]:
        del artifact_refs, max_total_bytes
        return []


class EmptyCheckpointRepository:
    async def load(self, run_id: str) -> HarnessCheckpoint | None:
        del run_id
        return None

    async def save(
        self,
        checkpoint: HarnessCheckpoint,
        *,
        expected_step_index: int | None,
    ) -> None:
        del checkpoint, expected_step_index
