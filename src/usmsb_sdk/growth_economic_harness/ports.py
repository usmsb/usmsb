"""Ports that keep cognition independent from OPC and tenant business models."""

from __future__ import annotations

import re
from typing import Any, Protocol

from pydantic import Field, StrictInt, model_validator

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


_SENSITIVE_COGNITIVE_PATTERNS = (
    re.compile(r"(?i)(?<![\w.+-])[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}(?![\w.-])"),
    re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\d)\d{17}[\dXx](?!\w)"),
    re.compile(r"(?i)(?:微信|wechat|wxid)\s*[:：=]\s*[A-Za-z][A-Za-z0-9_-]{5,}"),
    re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*\S+"),
)
_FORBIDDEN_COGNITIVE_KEYS = {
    "fullname",
    "personalname",
    "customername",
    "phone",
    "mobile",
    "email",
    "address",
    "visitorid",
    "subjectref",
    "prospectid",
    "customerid",
    "conversationid",
    "assessmentid",
    "orderid",
    "paymentid",
    "bankcard",
    "trackingnumber",
    "openid",
    "unionid",
    "wechatid",
    "password",
    "cookie",
    "credential",
    "accesstoken",
    "refreshtoken",
    "secret",
}


def enforce_cognitive_request_policy(
    authorization: dict[str, Any],
    payload: Any,
) -> None:
    """Require explicit host authorization and rescan every string value."""

    classifications = {
        str(item).strip().lower()
        for item in authorization.get("classifications", [])
        if isinstance(item, str)
    }
    destinations = {
        str(item).strip().lower()
        for item in authorization.get("destinations", [])
        if isinstance(item, str)
    }
    if (
        authorization.get("allowed") is not True
        or not classifications
        or not classifications.issubset({"non_personal", "tenant_authorized"})
        or not {"opc_conductor", "llm", "agent"}.issubset(destinations)
        or not str(authorization.get("authorization_ref") or "").strip()
        or authorization.get("pii_field_count") != 0
        or authorization.get("contains_customer_transcript") is not False
        or authorization.get("contains_payment_data") is not False
        or authorization.get("contains_logistics_data") is not False
        or authorization.get("contains_credentials") is not False
    ):
        raise ValueError("cognitive request is missing an authorized data boundary")

    def inspect(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                normalized = "".join(
                    character
                    for character in str(key).casefold()
                    if character.isalnum()
                )
                if normalized in _FORBIDDEN_COGNITIVE_KEYS:
                    raise ValueError(
                        "cognitive request contains a forbidden sensitive field"
                    )
                inspect(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                inspect(item)
        elif isinstance(value, str) and any(
            pattern.search(value) for pattern in _SENSITIVE_COGNITIVE_PATTERNS
        ):
            raise ValueError("cognitive request failed sensitive-data inspection")

    inspect(payload)


class ModelTurnRequest(StrictModel):
    run_id: str = Field(min_length=1, max_length=200)
    step_index: StrictInt = Field(ge=0)
    objective: dict[str, Any]
    current_hypothesis: str | None = None
    open_commitments: list[str] = Field(default_factory=list, max_length=50)
    context: list[dict[str, Any]] = Field(default_factory=list, max_length=1_000)
    tools: list[ToolDescriptor] = Field(default_factory=list, max_length=500)
    recalled_experiences: list[ExperienceRecord] = Field(default_factory=list, max_length=1_000)
    checkpoint_metadata: dict[str, Any] = Field(default_factory=dict)
    wake_events: list[WakeEvent] = Field(default_factory=list, max_length=500)
    cycle_handoff: CycleHandoff | None = None
    memory_manifest: MemoryManifest | None = None
    budget_context: BudgetContext | None = None
    current_experience_candidates: list[ExperienceRecord] = Field(default_factory=list, max_length=200)
    plan_state: PlanState | None = None
    resolved_artifacts: list[ArtifactRecord] = Field(default_factory=list, max_length=1_000)
    last_validation_error: str | None = Field(default=None, max_length=10_000)

    @model_validator(mode="after")
    def require_authorized_cognitive_envelope(self) -> "ModelTurnRequest":
        enforce_cognitive_request_policy(
            self.checkpoint_metadata.get("cognitive_data_authorization", {}),
            self.model_dump(mode="json", exclude={"checkpoint_metadata"}),
        )
        return self


class CognitiveModel(Protocol):
    async def complete(self, request: ModelTurnRequest) -> ModelCompletion:
        """Return one strict action decision as raw JSON."""


class GroupRequest(StrictModel):
    run_id: str = Field(min_length=1, max_length=200)
    step_index: StrictInt = Field(ge=0)
    objective: dict[str, Any]
    team_plan: TeamPlan
    context: list[dict[str, Any]] = Field(default_factory=list, max_length=1_000)
    checkpoint_metadata: dict[str, Any] = Field(default_factory=dict)
    wake_events: list[WakeEvent] = Field(default_factory=list, max_length=500)
    cycle_handoff: CycleHandoff | None = None
    memory_manifest: MemoryManifest | None = None
    budget_context: BudgetContext | None = None
    current_experience_candidates: list[ExperienceRecord] = Field(default_factory=list, max_length=200)
    plan_state: PlanState | None = None
    recalled_experiences: list[ExperienceRecord] = Field(default_factory=list, max_length=1_000)
    resolved_artifacts: list[ArtifactRecord] = Field(default_factory=list, max_length=1_000)

    @model_validator(mode="after")
    def require_authorized_cognitive_envelope(self) -> "GroupRequest":
        enforce_cognitive_request_policy(
            self.checkpoint_metadata.get("cognitive_data_authorization", {}),
            self.model_dump(mode="json", exclude={"checkpoint_metadata"}),
        )
        return self


class GroupContribution(StrictModel):
    role: str = Field(min_length=1, max_length=100)
    proposal: str = Field(min_length=1, max_length=30_000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=300)
    objections: list[str] = Field(default_factory=list, max_length=100)
    confidence: float = Field(ge=0, le=1)
    artifact_ref: str | None = Field(default=None, max_length=1_000)
    host_verified_artifact_refs: list[str] = Field(default_factory=list, max_length=300)

    @model_validator(mode="before")
    @classmethod
    def require_exact_confidence(cls, value: Any) -> Any:
        if not isinstance(value, dict) or "confidence" not in value:
            return value
        confidence = value["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError("confidence must be a JSON number")
        return value


class GroupResult(StrictModel):
    contributions: list[GroupContribution] = Field(min_length=1, max_length=12)
    synthesis: str = Field(min_length=1, max_length=30_000)
    conflicts: list[str] = Field(default_factory=list, max_length=100)
    evidence_gaps: list[str] = Field(default_factory=list, max_length=100)
    artifact_refs: list[str] = Field(default_factory=list, max_length=300)
    host_verified_artifact_refs: list[str] = Field(default_factory=list, max_length=300)


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
