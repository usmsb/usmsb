"""Ports that keep cognition independent from OPC and tenant business models."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import Field

from usmsb_sdk.growth_economic_harness.models import (
    ExperienceRecord,
    HarnessCheckpoint,
    ModelCompletion,
    StrictModel,
    TeamPlan,
    ToolDescriptor,
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

