"""Strict contracts for the domain-neutral Growth Economic Harness."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator


class StrictModel(BaseModel):
    """Forbid projection drift at every process boundary."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _require_json_number(value: Any, *, field: str) -> Any:
    if not isinstance(value, dict) or field not in value:
        return value
    number = value[field]
    if isinstance(number, bool) or not isinstance(number, (int, float)):
        raise ValueError(f"{field} must be a JSON number")
    return value


class ActionKind(str, Enum):
    OBSERVE = "observe"
    DELEGATE = "delegate"
    PROPOSE_ACTION = "propose_action"
    REVISE = "revise"
    REFLECT = "reflect"
    WAIT = "wait"
    COMPLETE = "complete"
    REQUEST_GATE = "request_gate"


class SideEffectClass(str, Enum):
    COGNITIVE = "cognitive"
    READ_ONLY = "read_only"
    LOCAL_REVERSIBLE = "local_reversible"
    EXTERNAL_REVERSIBLE = "external_reversible"
    CUSTOMER_CONTACT = "customer_contact"
    PUBLIC_PUBLISH = "public_publish"
    PAID_MEDIA = "paid_media"
    FINANCIAL = "financial"
    IRREVERSIBLE_OR_HIGH_RISK = "irreversible_or_high_risk"


class ExperienceState(str, Enum):
    RAW_EPISODE = "raw_episode"
    CANDIDATE = "candidate"
    PROBATION = "probation"
    VALIDATED = "validated"
    PROMOTED_SKILL = "promoted_skill"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"


class ToolDescriptor(StrictModel):
    capability: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=2_000)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    side_effect_class: SideEffectClass
    provider_ref: str | None = Field(default=None, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TeamRole(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    purpose: str = Field(min_length=1, max_length=1_000)
    capabilities: list[str] = Field(default_factory=list, max_length=20)
    challenge: str | None = Field(default=None, max_length=1_000)


class TeamPlan(StrictModel):
    roles: list[TeamRole] = Field(min_length=1, max_length=12)
    synthesis_question: str = Field(min_length=1, max_length=2_000)
    stop_when: str | None = Field(default=None, max_length=1_000)


class ExperienceDraft(StrictModel):
    lesson: str = Field(min_length=1, max_length=4_000)
    applicability: str = Field(min_length=1, max_length=2_000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=100)
    counter_evidence_refs: list[str] = Field(default_factory=list, max_length=100)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="before")
    @classmethod
    def require_exact_confidence(cls, value: Any) -> Any:
        return _require_json_number(value, field="confidence")


class ActionDraft(StrictModel):
    kind: ActionKind
    capability: str | None = Field(default=None, max_length=160)
    arguments: dict[str, Any] = Field(default_factory=dict)
    rationale: str = Field(min_length=1, max_length=4_000)
    expected_observation: str | None = Field(default=None, max_length=2_000)
    side_effect_class: SideEffectClass = SideEffectClass.COGNITIVE
    team_plan: TeamPlan | None = None

    @model_validator(mode="after")
    def validate_kind_contract(self) -> "ActionDraft":
        external = {
            ActionKind.OBSERVE,
            ActionKind.DELEGATE,
            ActionKind.PROPOSE_ACTION,
        }
        if self.kind in external and not self.capability:
            raise ValueError(f"{self.kind.value} requires capability")
        if self.capability == "cognitive.deliberate" and self.team_plan is None:
            raise ValueError("cognitive.deliberate requires a model-selected team_plan")
        return self


class ModelDecision(StrictModel):
    """One model-selected bounded action; not a precomputed workflow stage."""

    action: ActionDraft
    current_hypothesis: str | None = Field(default=None, max_length=4_000)
    open_commitments: list[str] = Field(default_factory=list, max_length=50)
    experience_candidate: ExperienceDraft | None = None


class ModelCompletion(StrictModel):
    raw_output: str = Field(max_length=1_000_000)
    provider: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=200)
    attempt_id: str | None = Field(default=None, max_length=200)
    input_tokens: StrictInt = Field(default=0, ge=0)
    output_tokens: StrictInt = Field(default=0, ge=0)
    cost: float = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def require_exact_cost(cls, value: Any) -> Any:
        return _require_json_number(value, field="cost")


class HarnessObjective(StrictModel):
    goal: str = Field(min_length=1, max_length=20_000)
    success_evidence: list[str] = Field(min_length=1, max_length=50)
    stop_conditions: list[str] = Field(default_factory=list, max_length=50)
    business_context_ref: str | None = Field(default=None, max_length=1_000)
    policy_context: dict[str, Any] = Field(default_factory=dict)
    initial_facts: dict[str, Any] = Field(default_factory=dict)


class Observation(StrictModel):
    action_id: str = Field(min_length=1, max_length=200)
    status: Literal["succeeded", "failed", "rejected", "outcome_unknown"]
    summary: str = Field(min_length=1, max_length=20_000)
    artifact_refs: list[str] = Field(default_factory=list, max_length=200)
    facts: dict[str, Any] = Field(default_factory=dict)
    error: str | None = Field(default=None, max_length=10_000)
    cost: float = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def require_exact_cost(cls, value: Any) -> Any:
        return _require_json_number(value, field="cost")


class ContextEntry(StrictModel):
    kind: Literal["decision", "observation", "group", "reflection", "revision", "compact"]
    summary: str = Field(min_length=1, max_length=30_000)
    artifact_refs: list[str] = Field(default_factory=list, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperienceRecord(StrictModel):
    experience_id: str = Field(min_length=1, max_length=200)
    state: ExperienceState
    lesson: str = Field(min_length=1, max_length=4_000)
    applicability: str = Field(min_length=1, max_length=2_000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=100)
    counter_evidence_refs: list[str] = Field(default_factory=list, max_length=100)
    confidence: float = Field(ge=0, le=1)
    source_run_id: str = Field(min_length=1, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def require_exact_confidence(cls, value: Any) -> Any:
        return _require_json_number(value, field="confidence")


class ActionIntent(StrictModel):
    action_id: str = Field(min_length=1, max_length=200)
    kind: ActionKind
    capability: str = Field(min_length=1, max_length=160)
    arguments: dict[str, Any] = Field(default_factory=dict)
    rationale: str = Field(min_length=1, max_length=4_000)
    expected_observation: str | None = Field(default=None, max_length=2_000)
    side_effect_class: SideEffectClass
    idempotency_key: str = Field(min_length=1, max_length=300)
    team_plan: TeamPlan | None = None


class HarnessCheckpoint(StrictModel):
    schema_version: Literal["growth-harness.checkpoint.v1"] = "growth-harness.checkpoint.v1"
    run_id: str = Field(min_length=1, max_length=200)
    objective: HarnessObjective
    step_index: StrictInt = Field(default=0, ge=0)
    status: Literal["running", "awaiting_observation", "waiting", "completed", "failed"] = (
        "running"
    )
    current_hypothesis: str | None = Field(default=None, max_length=4_000)
    open_commitments: list[str] = Field(default_factory=list, max_length=50)
    selected_team: TeamPlan | None = None
    context: list[ContextEntry] = Field(default_factory=list, max_length=1_000)
    experience_candidates: list[ExperienceRecord] = Field(default_factory=list, max_length=200)
    pending_action: ActionIntent | None = None
    compacted_entries: StrictInt = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WaitIntent(StrictModel):
    reason: str = Field(min_length=1, max_length=4_000)
    wake_conditions: list[str] = Field(default_factory=list, max_length=50)
    wake_after_seconds: StrictInt | None = Field(default=None, ge=1, le=2_592_000)
    requires_gate: StrictBool = False


class CycleResult(StrictModel):
    summary: str = Field(min_length=1, max_length=20_000)
    success_evidence_refs: list[str] = Field(default_factory=list, max_length=200)
    unresolved: list[str] = Field(default_factory=list, max_length=100)


class HarnessStepResult(StrictModel):
    kind: Literal["action", "wait", "complete"]
    checkpoint: HarnessCheckpoint
    action: ActionIntent | None = None
    wait: WaitIntent | None = None
    result: CycleResult | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "HarnessStepResult":
        payloads = {
            "action": self.action,
            "wait": self.wait,
            "complete": self.result,
        }
        if payloads[self.kind] is None:
            raise ValueError(f"{self.kind} result requires its matching payload")
        if sum(value is not None for value in payloads.values()) != 1:
            raise ValueError("step result must contain exactly one terminal payload")
        return self
