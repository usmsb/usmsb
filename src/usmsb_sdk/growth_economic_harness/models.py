"""Strict contracts for the domain-neutral Growth Economic Harness."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator


class StrictModel(BaseModel):
    """Forbid projection drift at every process boundary."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    def validated_copy(self, *, update: dict[str, Any]) -> "StrictModel":
        """Copy through full Pydantic validation.

        ``model_copy(update=...)`` deliberately skips validation and is unsafe
        at a durable-host boundary: a long-running loop could otherwise emit a
        checkpoint that it cannot load after restart.  State transitions use
        this helper so list bounds and cross-field invariants are rechecked.
        """

        payload = self.model_dump(mode="python")
        payload.update(update)
        return type(self).model_validate(payload)


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


class PlanNodeStatus(str, Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class WakeEvent(StrictModel):
    event_id: str = Field(min_length=1, max_length=200)
    condition: str = Field(min_length=1, max_length=1_000)
    facts: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: list[str] = Field(default_factory=list, max_length=200)
    observed_at: str | None = Field(default=None, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CycleHandoff(StrictModel):
    from_cycle_id: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=12_000)
    open_commitments: list[str] = Field(default_factory=list, max_length=50)
    unresolved_questions: list[str] = Field(default_factory=list, max_length=100)
    artifact_refs: list[str] = Field(default_factory=list, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryReference(StrictModel):
    memory_id: str = Field(min_length=1, max_length=500)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    state: str = Field(min_length=1, max_length=100)
    source_run_id: str | None = Field(default=None, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryManifest(StrictModel):
    query: str = Field(min_length=1, max_length=4_000)
    memories: list[MemoryReference] = Field(default_factory=list, max_length=200)
    generated_at: str = Field(min_length=1, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BudgetContext(StrictModel):
    max_input_tokens: StrictInt | None = Field(default=None, ge=1)
    reserved_output_tokens: StrictInt | None = Field(default=None, ge=0)
    model_context_window: StrictInt | None = Field(default=None, ge=1)
    remaining_cost: float | None = Field(default=None, ge=0)
    spent_cost: float = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def require_exact_numbers(cls, value: Any) -> Any:
        value = _require_json_number(value, field="spent_cost")
        if isinstance(value, dict) and value.get("remaining_cost") is not None:
            value = _require_json_number(value, field="remaining_cost")
        return value

    @model_validator(mode="after")
    def validate_limits(self) -> "BudgetContext":
        if (
            self.max_input_tokens is not None
            and self.reserved_output_tokens is not None
            and self.reserved_output_tokens >= self.max_input_tokens
        ):
            raise ValueError("reserved_output_tokens must be below max_input_tokens")
        if (
            self.model_context_window is not None
            and self.reserved_output_tokens is not None
            and self.reserved_output_tokens >= self.model_context_window
        ):
            raise ValueError("reserved_output_tokens must be below model_context_window")
        return self


class ContinuityState(StrictModel):
    wake_events: list[WakeEvent] = Field(default_factory=list, max_length=500)
    cycle_handoff: CycleHandoff | None = None
    memory_manifest: MemoryManifest | None = None
    budget_context: BudgetContext | None = None
    consumed_wake_event_ids: list[str] = Field(default_factory=list, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_wake_identity(self) -> "ContinuityState":
        active = [item.event_id for item in self.wake_events]
        consumed = self.consumed_wake_event_ids
        if len(active) != len(set(active)):
            raise ValueError("active wake event ids must be unique")
        if len(consumed) != len(set(consumed)):
            raise ValueError("consumed wake event ids must be unique")
        overlap = set(active) & set(consumed)
        if overlap:
            raise ValueError(f"active and consumed wake events overlap: {sorted(overlap)}")
        return self


class PlanNode(StrictModel):
    node_id: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1, max_length=4_000)
    status: PlanNodeStatus = PlanNodeStatus.PROPOSED
    success_evidence: list[str] = Field(default_factory=list, max_length=50)
    depends_on: list[str] = Field(default_factory=list, max_length=50)
    hypothesis: str | None = Field(default=None, max_length=4_000)
    stop_conditions: list[str] = Field(default_factory=list, max_length=50)
    status_basis: str | None = Field(default=None, max_length=4_000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_terminal_evidence(self) -> "PlanNode":
        if self.status == PlanNodeStatus.COMPLETED and not self.success_evidence:
            raise ValueError("completed plan node requires success evidence")
        if self.status in {PlanNodeStatus.BLOCKED, PlanNodeStatus.ABANDONED} and not self.status_basis:
            raise ValueError(f"{self.status.value} plan node requires status_basis")
        return self


class PlanState(StrictModel):
    plan_id: str = Field(min_length=1, max_length=200)
    revision: StrictInt = Field(default=0, ge=0)
    nodes: list[PlanNode] = Field(default_factory=list, max_length=500)
    focus_node_ids: list[str] = Field(default_factory=list, max_length=50)
    assumptions: list[str] = Field(default_factory=list, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_graph(self) -> "PlanState":
        node_ids = [item.node_id for item in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("plan node ids must be unique")
        known = set(node_ids)
        if any(item not in known for item in self.focus_node_ids):
            raise ValueError("focus nodes must reference known plan nodes")
        graph = {item.node_id: set(item.depends_on) for item in self.nodes}
        for node_id, dependencies in graph.items():
            if node_id in dependencies or not dependencies.issubset(known):
                raise ValueError("plan dependencies must reference other known nodes")
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("plan dependencies must be acyclic")
            if node_id in visited:
                return
            visiting.add(node_id)
            for dependency in graph[node_id]:
                visit(dependency)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in graph:
            visit(node_id)
        return self


class PlanDelta(StrictModel):
    expected_revision: StrictInt | None = Field(default=None, ge=0)
    rationale: str = Field(min_length=1, max_length=4_000)
    upsert_nodes: list[PlanNode] = Field(default_factory=list, max_length=100)
    remove_node_ids: list[str] = Field(default_factory=list, max_length=100)
    focus_node_ids: list[str] | None = Field(default=None, max_length=50)
    assumptions: list[str] | None = Field(default=None, max_length=100)
    metadata_updates: dict[str, Any] = Field(default_factory=dict)


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

    @model_validator(mode="after")
    def validate_roles(self) -> "TeamPlan":
        names = [item.name for item in self.roles]
        if len(names) != len(set(names)):
            raise ValueError("team role names must be unique")
        return self


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
        if self.capability == "cognitive.deliberate":
            if self.team_plan is None:
                raise ValueError("cognitive.deliberate requires a model-selected team_plan")
            if self.kind != ActionKind.DELEGATE:
                raise ValueError("cognitive.deliberate must use delegate")
            if self.side_effect_class != SideEffectClass.COGNITIVE:
                raise ValueError("cognitive.deliberate must be cognitive")
        elif self.team_plan is not None:
            raise ValueError("team_plan is valid only for cognitive.deliberate")
        if self.kind not in external:
            if self.capability is not None:
                raise ValueError(f"{self.kind.value} must not select an external capability")
            if self.side_effect_class != SideEffectClass.COGNITIVE:
                raise ValueError(f"{self.kind.value} must be cognitive")
        return self


class CommitmentResolution(StrictModel):
    commitment: str = Field(min_length=1, max_length=4_000)
    resolution_summary: str = Field(min_length=1, max_length=4_000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=100)
    observation_action_id: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def require_source(self) -> "CommitmentResolution":
        if not self.evidence_refs and self.observation_action_id is None:
            raise ValueError("commitment resolution requires evidence or observation")
        return self


class ModelDecision(StrictModel):
    """One model-selected bounded action; not a precomputed workflow stage."""

    action: ActionDraft
    current_hypothesis: str | None = Field(default=None, max_length=4_000)
    open_commitments: list[str] = Field(default_factory=list, max_length=50)
    commitments_to_add: list[str] = Field(default_factory=list, max_length=50)
    resolved_commitments: list[CommitmentResolution] = Field(default_factory=list, max_length=50)
    consumed_wake_event_ids: list[str] = Field(default_factory=list, max_length=500)
    experience_candidate: ExperienceDraft | None = None
    plan_delta: PlanDelta | None = None


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


class CognitiveCallRecord(StrictModel):
    call_id: str = Field(min_length=1, max_length=300)
    purpose: Literal["cognitive", "role", "specialist", "synthesis", "compaction"]
    run_id: str = Field(min_length=1, max_length=200)
    step_index: StrictInt = Field(ge=0)
    role: str | None = Field(default=None, max_length=100)
    parent_call_id: str | None = Field(default=None, max_length=300)
    status: Literal["succeeded", "failed"]
    provider: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=200)
    attempt_id: str | None = Field(default=None, max_length=200)
    input_tokens: StrictInt = Field(default=0, ge=0)
    output_tokens: StrictInt = Field(default=0, ge=0)
    cost: float = Field(default=0, ge=0)
    duration_ms: StrictInt = Field(default=0, ge=0)
    trace_ref: str | None = Field(default=None, max_length=1_000)
    governor_reservation_id: str | None = Field(default=None, max_length=500)
    host_verified_artifact_refs: list[str] = Field(default_factory=list, max_length=300)
    error: str | None = Field(default=None, max_length=10_000)
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


class ArtifactRecord(StrictModel):
    artifact_ref: str = Field(min_length=1, max_length=1_000)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_type: str = Field(min_length=1, max_length=200)
    content: Any
    metadata: dict[str, Any] = Field(default_factory=dict)


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


class EpisodeOutcome(StrictModel):
    outcome_ref: str = Field(min_length=1, max_length=1_000)
    status: str = Field(min_length=1, max_length=100)
    metric: str | None = Field(default=None, max_length=200)
    value: float | None = None
    evidence_refs: list[str] = Field(default_factory=list, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def require_exact_value(cls, value: Any) -> Any:
        if isinstance(value, dict) and value.get("value") is not None:
            return _require_json_number(value, field="value")
        return value


class ExperienceEpisode(StrictModel):
    episode_id: str = Field(min_length=1, max_length=300)
    run_id: str = Field(min_length=1, max_length=200)
    plan_node_id: str | None = Field(default=None, max_length=200)
    hypothesis: str | None = Field(default=None, max_length=4_000)
    team_plan: TeamPlan | None = None
    action: ActionIntent | None = None
    observation: Observation | None = None
    outcomes: list[EpisodeOutcome] = Field(default_factory=list, max_length=500)
    evidence_refs: list[str] = Field(default_factory=list, max_length=300)
    counter_evidence_refs: list[str] = Field(default_factory=list, max_length=300)
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    continuity: ContinuityState | None = None
    plan_state: PlanState | None = None

    @model_validator(mode="after")
    def validate_state_machine(self) -> "HarnessCheckpoint":
        if self.status == "awaiting_observation" and self.pending_action is None:
            raise ValueError("awaiting_observation requires pending_action")
        if self.status != "awaiting_observation" and self.pending_action is not None:
            raise ValueError(f"{self.status} checkpoint cannot retain pending_action")
        return self


class WaitIntent(StrictModel):
    reason: str = Field(min_length=1, max_length=4_000)
    wake_conditions: list[str] = Field(default_factory=list, max_length=50)
    wake_after_seconds: StrictInt | None = Field(default=None, ge=1, le=2_592_000)
    requires_gate: StrictBool = False


class CycleResult(StrictModel):
    outcome_status: Literal["success", "stopped", "failed"] = "success"
    summary: str = Field(min_length=1, max_length=20_000)
    success_evidence_refs: list[str] = Field(default_factory=list, max_length=200)
    unresolved: list[str] = Field(default_factory=list, max_length=100)
    stop_reason: str | None = Field(default=None, max_length=4_000)
    cycle_handoff: CycleHandoff | None = None


class HarnessMutationBatch(StrictModel):
    experience_candidates: list[ExperienceRecord] = Field(default_factory=list, max_length=200)
    episodes: list[ExperienceEpisode] = Field(default_factory=list, max_length=200)
    cycle_handoff: CycleHandoff | None = None
    cognitive_calls: list[CognitiveCallRecord] = Field(default_factory=list, max_length=1_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HarnessStepResult(StrictModel):
    kind: Literal["action", "wait", "complete"]
    checkpoint: HarnessCheckpoint
    action: ActionIntent | None = None
    wait: WaitIntent | None = None
    result: CycleResult | None = None
    mutations: HarnessMutationBatch = Field(default_factory=HarnessMutationBatch)

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
