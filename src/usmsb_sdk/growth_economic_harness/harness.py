"""Model-led, resumable Growth Economic Harness.

The harness contains no sales funnel or channel workflow.  It asks the model
for one bounded next action, runs only pure cognitive group work internally,
and yields every external capability to its durable host.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from usmsb_sdk.growth_economic_harness.context_loop import ContextLoop
from usmsb_sdk.growth_economic_harness.experience_loop import ExperienceLoop
from usmsb_sdk.growth_economic_harness.json_schema import (
    JsonSchemaValidationError,
    validate_json_schema,
)
from usmsb_sdk.growth_economic_harness.models import (
    ActionIntent,
    ActionKind,
    ArtifactRecord,
    ContextEntry,
    ContinuityState,
    CycleHandoff,
    CycleResult,
    ExperienceEpisode,
    ExperienceRecord,
    HarnessCheckpoint,
    HarnessObjective,
    HarnessStepResult,
    ModelDecision,
    Observation,
    PlanDelta,
    PlanState,
    ToolDescriptor,
    WaitIntent,
)
from usmsb_sdk.growth_economic_harness.ports import (
    ArtifactRepository,
    CheckpointRepository,
    CognitiveModel,
    ContextRepository,
    EmptyArtifactRepository,
    EmptyCheckpointRepository,
    EmptyContextRepository,
    EmptyExperienceRepository,
    ExperienceRepository,
    GroupReasoner,
    GroupRequest,
    NullTelemetry,
    TelemetrySink,
)
from usmsb_sdk.growth_economic_harness.structured_output import (
    StructuredOutputError,
    decode_model_decision,
)


class HarnessProtocolError(ValueError):
    pass


class HarnessDecisionError(RuntimeError):
    def __init__(self, message: str, checkpoint: HarnessCheckpoint) -> None:
        super().__init__(message)
        self.checkpoint = checkpoint


@dataclass(frozen=True)
class HarnessConfig:
    max_internal_decisions_per_step: int = 6
    max_structured_output_repairs: int = 2
    max_model_output_bytes: int = 256_000
    experience_recall_limit: int = 20
    context_recall_limit: int = 50

    def __post_init__(self) -> None:
        bounds = {
            "max_internal_decisions_per_step": (self.max_internal_decisions_per_step, 1, 100),
            "max_structured_output_repairs": (self.max_structured_output_repairs, 0, 10),
            "max_model_output_bytes": (self.max_model_output_bytes, 1_024, 1_048_576),
            "experience_recall_limit": (self.experience_recall_limit, 0, 1_000),
            "context_recall_limit": (self.context_recall_limit, 0, 1_000),
        }
        for name, (value, minimum, maximum) in bounds.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not minimum <= value <= maximum
            ):
                raise ValueError(f"{name} must be an integer from {minimum} to {maximum}")


class GrowthEconomicHarness:
    """A cognitive state machine whose transition function is the model."""

    def __init__(
        self,
        model: CognitiveModel,
        *,
        group_reasoner: GroupReasoner | None = None,
        context_loop: ContextLoop | None = None,
        experience_loop: ExperienceLoop | None = None,
        experience_repository: ExperienceRepository | None = None,
        context_repository: ContextRepository | None = None,
        artifact_repository: ArtifactRepository | None = None,
        checkpoint_repository: CheckpointRepository | None = None,
        telemetry: TelemetrySink | None = None,
        config: HarnessConfig | None = None,
    ) -> None:
        self.model = model
        self.group_reasoner = group_reasoner
        self.context_loop = context_loop or ContextLoop()
        self.experience_loop = experience_loop or ExperienceLoop()
        self.experience_repository = experience_repository or EmptyExperienceRepository()
        self.context_repository = context_repository or EmptyContextRepository()
        self.artifact_repository = artifact_repository or EmptyArtifactRepository()
        self.checkpoint_repository = checkpoint_repository or EmptyCheckpointRepository()
        self.telemetry = telemetry or NullTelemetry()
        self.config = config or HarnessConfig()

    def create_checkpoint(
        self,
        objective: HarnessObjective,
        *,
        run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> HarnessCheckpoint:
        return HarnessCheckpoint(
            run_id=run_id or f"growth_{uuid4().hex}",
            objective=objective,
            metadata=metadata or {},
        )

    async def step(
        self,
        *,
        checkpoint: HarnessCheckpoint | None = None,
        objective: HarnessObjective | None = None,
        observation: Observation | None = None,
        tools: Iterable[ToolDescriptor] = (),
        recalled_experiences: list[ExperienceRecord] | None = None,
    ) -> HarnessStepResult:
        """Advance cognition until an external action, wait, or completion yields."""

        if checkpoint is None:
            if objective is None:
                raise HarnessProtocolError("objective is required for a new harness run")
            checkpoint = self.create_checkpoint(objective)
        elif objective is not None and objective != checkpoint.objective:
            raise HarnessProtocolError("objective cannot be replaced while resuming a checkpoint")

        if checkpoint.status == "completed":
            raise HarnessProtocolError("completed checkpoint cannot be resumed")
        await self._persist_observation_episode(checkpoint, observation)
        checkpoint = self._accept_observation(checkpoint, observation)
        checkpoint = await self._refresh_context(checkpoint)
        tool_catalog = list(tools)
        self._validate_tool_catalog(tool_catalog)
        experiences = (
            recalled_experiences
            if recalled_experiences is not None
            else await self.experience_repository.recall(
                checkpoint,
                limit=self.config.experience_recall_limit,
            )
        )
        resolved_artifacts = await self._resolve_relevant_artifacts(checkpoint)

        for internal_index in range(self.config.max_internal_decisions_per_step):
            decision, checkpoint = await self._decide(
                checkpoint,
                tool_catalog,
                experiences,
                resolved_artifacts,
            )
            checkpoint = await self._record_decision(checkpoint, decision)
            draft = decision.action

            if draft.capability == "cognitive.deliberate":
                if self.group_reasoner is None or draft.team_plan is None:
                    raise HarnessDecisionError(
                        "model requested cognitive.deliberate but no GroupReasoner is configured",
                        checkpoint,
                    )
                continuity = checkpoint.continuity
                group_result = await self.group_reasoner.deliberate(
                    GroupRequest(
                        run_id=checkpoint.run_id,
                        step_index=checkpoint.step_index,
                        objective=checkpoint.objective.model_dump(mode="json"),
                        team_plan=draft.team_plan,
                        context=[entry.model_dump(mode="json") for entry in checkpoint.context],
                        checkpoint_metadata=checkpoint.metadata,
                        wake_events=continuity.wake_events if continuity else [],
                        cycle_handoff=continuity.cycle_handoff if continuity else None,
                        memory_manifest=continuity.memory_manifest if continuity else None,
                        budget_context=continuity.budget_context if continuity else None,
                        current_experience_candidates=checkpoint.experience_candidates,
                        plan_state=checkpoint.plan_state,
                        recalled_experiences=experiences,
                        resolved_artifacts=resolved_artifacts,
                    )
                )
                checkpoint = checkpoint.model_copy(
                    update={
                        "selected_team": draft.team_plan,
                        "context": [
                            *checkpoint.context,
                            ContextEntry(
                                kind="group",
                                summary=group_result.synthesis,
                                artifact_refs=group_result.artifact_refs,
                                metadata={
                                    "roles": [role.name for role in draft.team_plan.roles],
                                    "conflicts": group_result.conflicts,
                                    "evidence_gaps": group_result.evidence_gaps,
                                    "contributions": [
                                        item.model_dump(mode="json")
                                        for item in group_result.contributions
                                    ],
                                },
                            ),
                        ],
                    }
                )
                await self.telemetry.event(
                    "growth.group.completed",
                    {
                        "run_id": checkpoint.run_id,
                        "step_index": checkpoint.step_index,
                        "roles": [role.name for role in draft.team_plan.roles],
                        "internal_index": internal_index,
                    },
                )
                continue

            if draft.kind == ActionKind.REVISE:
                if not decision.current_hypothesis:
                    raise HarnessDecisionError(
                        "revise requires current_hypothesis",
                        checkpoint,
                    )
                checkpoint = checkpoint.model_copy(
                    update={
                        "context": [
                            *checkpoint.context,
                            ContextEntry(
                                kind="revision",
                                summary=decision.current_hypothesis,
                                metadata={"rationale": draft.rationale},
                            ),
                        ]
                    }
                )
                continue

            if draft.kind == ActionKind.REFLECT:
                if decision.experience_candidate is None:
                    raise HarnessDecisionError(
                        "reflect requires experience_candidate",
                        checkpoint,
                    )
                candidate = checkpoint.experience_candidates[-1]
                checkpoint = checkpoint.model_copy(
                    update={
                        "context": [
                            *checkpoint.context,
                            ContextEntry(
                                kind="reflection",
                                summary=candidate.lesson,
                                artifact_refs=candidate.evidence_refs,
                                metadata={
                                    "experience_id": candidate.experience_id,
                                    "applicability": candidate.applicability,
                                    "counter_evidence_refs": candidate.counter_evidence_refs,
                                    "confidence": candidate.confidence,
                                },
                            ),
                        ]
                    }
                )
                continue

            if draft.kind in {ActionKind.WAIT, ActionKind.REQUEST_GATE}:
                wake_conditions = draft.arguments.get("wake_conditions", [])
                if not isinstance(wake_conditions, list) or not all(
                    isinstance(item, str) for item in wake_conditions
                ):
                    raise HarnessDecisionError(
                        "wake_conditions must be a list of strings",
                        checkpoint,
                    )
                wake_after_seconds = draft.arguments.get("wake_after_seconds")
                if (
                    wake_after_seconds is not None
                    and (
                        isinstance(wake_after_seconds, bool)
                        or not isinstance(wake_after_seconds, int)
                        or not 1 <= wake_after_seconds <= 2_592_000
                    )
                ):
                    raise HarnessDecisionError(
                        "wake_after_seconds must be an integer from 1 to 2592000",
                        checkpoint,
                    )
                waiting = checkpoint.model_copy(update={"status": "waiting"})
                return HarnessStepResult(
                    kind="wait",
                    checkpoint=waiting,
                    wait=WaitIntent(
                        reason=draft.rationale,
                        wake_conditions=wake_conditions,
                        wake_after_seconds=wake_after_seconds,
                        requires_gate=draft.kind == ActionKind.REQUEST_GATE,
                    ),
                )

            if draft.kind == ActionKind.COMPLETE:
                result = self._cycle_result(checkpoint, draft.arguments, draft.rationale)
                completed = checkpoint.model_copy(update={"status": "completed"})
                return HarnessStepResult(kind="complete", checkpoint=completed, result=result)

            intent = self._external_intent(checkpoint, decision, tool_catalog)
            awaiting = checkpoint.model_copy(
                update={
                    "step_index": checkpoint.step_index + 1,
                    "status": "awaiting_observation",
                    "pending_action": intent,
                }
            )
            return HarnessStepResult(kind="action", checkpoint=awaiting, action=intent)

        waiting = checkpoint.model_copy(update={"status": "waiting"})
        return HarnessStepResult(
            kind="wait",
            checkpoint=waiting,
            wait=WaitIntent(
                reason="bounded internal cognition limit reached; persist and resume",
                wake_conditions=["resume_same_cycle"],
            ),
        )

    async def _refresh_context(self, checkpoint: HarnessCheckpoint) -> HarnessCheckpoint:
        recall = getattr(self.context_repository, "recall_manifest", None)
        if not callable(recall) or self.config.context_recall_limit == 0:
            return checkpoint
        query_parts = [checkpoint.objective.goal]
        if checkpoint.current_hypothesis:
            query_parts.append(checkpoint.current_hypothesis)
        if checkpoint.plan_state is not None:
            focused = set(checkpoint.plan_state.focus_node_ids)
            query_parts.extend(
                node.goal
                for node in checkpoint.plan_state.nodes
                if not focused or node.node_id in focused
            )
        manifest = await recall(
            checkpoint,
            query="\n".join(query_parts),
            limit=self.config.context_recall_limit,
        )
        if manifest is None:
            return checkpoint
        continuity = checkpoint.continuity or ContinuityState()
        return checkpoint.model_copy(
            update={"continuity": continuity.model_copy(update={"memory_manifest": manifest})}
        )

    async def _resolve_relevant_artifacts(
        self,
        checkpoint: HarnessCheckpoint,
    ) -> list[ArtifactRecord]:
        read = getattr(self.artifact_repository, "read", None)
        if not callable(read):
            return []
        refs: list[str] = []

        def add(values: Iterable[str]) -> None:
            for value in values:
                if value not in refs:
                    refs.append(value)

        for entry in checkpoint.context:
            add(entry.artifact_refs)
        for candidate in checkpoint.experience_candidates:
            add(candidate.evidence_refs)
            add(candidate.counter_evidence_refs)
        continuity = checkpoint.continuity
        if continuity is not None:
            for event in continuity.wake_events:
                add(event.artifact_refs)
            if continuity.cycle_handoff is not None:
                add(continuity.cycle_handoff.artifact_refs)
            if continuity.memory_manifest is not None:
                for memory in continuity.memory_manifest.memories:
                    add(memory.artifact_refs)
        if not refs:
            return []
        records = await read(
            refs,
            max_total_bytes=self.context_loop.budget.max_resolved_artifact_bytes,
        )
        seen: set[str] = set()
        total_bytes = 0
        for record in records:
            if record.artifact_ref not in refs:
                raise HarnessProtocolError(
                    f"artifact repository returned unrequested ref {record.artifact_ref!r}"
                )
            if record.artifact_ref in seen:
                raise HarnessProtocolError(
                    f"artifact repository returned duplicate ref {record.artifact_ref!r}"
                )
            seen.add(record.artifact_ref)
            if record.content is not None:
                total_bytes += len(record.content.encode("utf-8"))
        if total_bytes > self.context_loop.budget.max_resolved_artifact_bytes:
            raise HarnessProtocolError("artifact repository exceeded the requested byte budget")
        return records

    async def _persist_observation_episode(
        self,
        checkpoint: HarnessCheckpoint,
        observation: Observation | None,
    ) -> None:
        pending = checkpoint.pending_action
        if pending is None or observation is None or pending.action_id != observation.action_id:
            return
        persist = getattr(self.experience_repository, "persist_episode", None)
        if not callable(persist):
            return
        canonical = json.dumps(
            {
                "run_id": checkpoint.run_id,
                "action_id": pending.action_id,
                "observation": observation.model_dump(mode="json"),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        evidence_refs = list(dict.fromkeys(observation.artifact_refs))
        episode = ExperienceEpisode(
            episode_id=f"episode_{digest[:32]}",
            run_id=checkpoint.run_id,
            plan_node_id=(
                checkpoint.plan_state.focus_node_ids[0]
                if checkpoint.plan_state and checkpoint.plan_state.focus_node_ids
                else None
            ),
            hypothesis=checkpoint.current_hypothesis,
            team_plan=checkpoint.selected_team,
            action=pending,
            observation=observation,
            evidence_refs=evidence_refs,
            metadata={
                "step_index": checkpoint.step_index,
                "observation_status": observation.status,
                "observation_cost": observation.cost,
            },
        )
        await persist(episode)

    def _accept_observation(
        self,
        checkpoint: HarnessCheckpoint,
        observation: Observation | None,
    ) -> HarnessCheckpoint:
        pending = checkpoint.pending_action
        if pending is not None and observation is None:
            raise HarnessProtocolError(
                f"checkpoint awaits observation for action {pending.action_id}"
            )
        if pending is None and observation is not None:
            raise HarnessProtocolError("observation supplied but checkpoint has no pending action")
        if pending is None:
            return checkpoint.model_copy(update={"status": "running"})
        if observation is None or observation.action_id != pending.action_id:
            raise HarnessProtocolError(
                f"observation action_id must equal pending action {pending.action_id}"
            )
        entry = ContextEntry(
            kind="observation",
            summary=observation.summary,
            artifact_refs=observation.artifact_refs,
            metadata={
                "action_id": observation.action_id,
                "capability": pending.capability,
                "status": observation.status,
                "facts": observation.facts,
                "error": observation.error,
                "cost": observation.cost,
                "observation_metadata": observation.metadata,
            },
        )
        return checkpoint.model_copy(
            update={
                "status": "running",
                "pending_action": None,
                "context": [*checkpoint.context, entry],
            }
        )

    async def _decide(
        self,
        checkpoint: HarnessCheckpoint,
        tools: list[ToolDescriptor],
        experiences: list[ExperienceRecord],
        resolved_artifacts: list[ArtifactRecord],
    ) -> tuple[ModelDecision, HarnessCheckpoint]:
        validation_error: str | None = None
        for attempt_index in range(self.config.max_structured_output_repairs + 1):
            prepared = await self.context_loop.prepare_model_turn(
                checkpoint,
                tools=tools,
                recalled_experiences=experiences,
                resolved_artifacts=resolved_artifacts,
                last_validation_error=validation_error,
            )
            checkpoint = prepared.checkpoint
            completion = await self.model.complete(prepared.request)
            try:
                decision = decode_model_decision(
                    completion.raw_output,
                    max_bytes=self.config.max_model_output_bytes,
                )
                validation_error = None
            except StructuredOutputError as error:
                validation_error = str(error)
                decision = None
            await self.telemetry.model_attempt(
                run_id=checkpoint.run_id,
                step_index=checkpoint.step_index,
                attempt_index=attempt_index,
                completion=completion,
                validation_error=validation_error,
            )
            if decision is not None:
                return decision, checkpoint
        raise HarnessDecisionError(
            f"model failed strict structured output after bounded repair: {validation_error}",
            checkpoint,
        )

    async def _record_decision(
        self,
        checkpoint: HarnessCheckpoint,
        decision: ModelDecision,
    ) -> HarnessCheckpoint:
        candidates = list(checkpoint.experience_candidates)
        new_candidate: ExperienceRecord | None = None
        if decision.experience_candidate is not None:
            candidate_payload = json.dumps(
                decision.experience_candidate.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            candidate_digest = hashlib.sha256(
                f"{checkpoint.run_id}:{checkpoint.step_index}:{candidate_payload}".encode("utf-8")
            ).hexdigest()
            new_candidate = self.experience_loop.candidate_from(
                decision.experience_candidate,
                run_id=checkpoint.run_id,
                experience_id=f"exp_{candidate_digest[:32]}",
            )
            if all(
                item.experience_id != new_candidate.experience_id
                for item in candidates
            ):
                candidates.append(new_candidate)
        entry = ContextEntry(
            kind="decision",
            summary=decision.action.rationale,
            metadata={
                "kind": decision.action.kind.value,
                "capability": decision.action.capability,
                "expected_observation": decision.action.expected_observation,
                "side_effect_class": decision.action.side_effect_class.value,
            },
        )
        updated = checkpoint.model_copy(
            update={
                "current_hypothesis": (
                    decision.current_hypothesis or checkpoint.current_hypothesis
                ),
                "open_commitments": decision.open_commitments,
                "experience_candidates": candidates,
                "context": [*checkpoint.context, entry],
            }
        )
        if decision.plan_delta is not None:
            updated = updated.model_copy(
                update={"plan_state": self._apply_plan_delta(updated, decision.plan_delta)}
            )
        if new_candidate is not None:
            persist = getattr(self.experience_repository, "persist_candidate", None)
            if callable(persist):
                await persist(new_candidate, checkpoint=updated)
        return updated

    @staticmethod
    def _apply_plan_delta(
        checkpoint: HarnessCheckpoint,
        delta: PlanDelta,
    ) -> PlanState:
        current = checkpoint.plan_state or PlanState(plan_id=f"plan_{checkpoint.run_id}")
        if delta.expected_revision is not None and delta.expected_revision != current.revision:
            raise HarnessDecisionError(
                "model plan_delta expected a stale plan revision: "
                f"expected={delta.expected_revision}, current={current.revision}",
                checkpoint,
            )
        nodes = {node.node_id: node for node in current.nodes}
        for node_id in delta.remove_node_ids:
            nodes.pop(node_id, None)
        for node in delta.upsert_nodes:
            nodes[node.node_id] = node
        focus = delta.focus_node_ids
        if focus is None:
            focus = [node_id for node_id in current.focus_node_ids if node_id in nodes]
        assumptions = delta.assumptions if delta.assumptions is not None else current.assumptions
        try:
            return PlanState(
                plan_id=current.plan_id,
                revision=current.revision + 1,
                nodes=list(nodes.values()),
                focus_node_ids=focus,
                assumptions=assumptions,
                metadata={**current.metadata, **delta.metadata_updates},
            )
        except ValueError as error:
            raise HarnessDecisionError(f"invalid model plan_delta: {error}", checkpoint) from error

    def _external_intent(
        self,
        checkpoint: HarnessCheckpoint,
        decision: ModelDecision,
        tools: list[ToolDescriptor],
    ) -> ActionIntent:
        draft = decision.action
        descriptor = next(
            (tool for tool in tools if tool.capability == draft.capability),
            None,
        )
        if descriptor is None:
            raise HarnessDecisionError(
                f"model selected unavailable capability {draft.capability!r}",
                checkpoint,
            )
        if draft.side_effect_class != descriptor.side_effect_class:
            raise HarnessDecisionError(
                "model side_effect_class does not match tool catalog: "
                f"{draft.side_effect_class.value}!={descriptor.side_effect_class.value}",
                checkpoint,
            )
        try:
            validate_json_schema(draft.arguments, descriptor.input_schema)
        except JsonSchemaValidationError as error:
            raise HarnessDecisionError(
                f"model arguments failed {descriptor.capability!r} input_schema: {error}",
                checkpoint,
            ) from error
        canonical = json.dumps(
            {
                "run_id": checkpoint.run_id,
                "step_index": checkpoint.step_index,
                "kind": draft.kind.value,
                "capability": draft.capability,
                "arguments": draft.arguments,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return ActionIntent(
            action_id=f"act_{digest[:24]}",
            kind=draft.kind,
            capability=draft.capability or "",
            arguments=draft.arguments,
            rationale=draft.rationale,
            expected_observation=draft.expected_observation,
            side_effect_class=draft.side_effect_class,
            idempotency_key=f"growth:{checkpoint.run_id}:{checkpoint.step_index}:{digest}",
            team_plan=draft.team_plan,
        )

    @staticmethod
    def _cycle_result(
        checkpoint: HarnessCheckpoint,
        arguments: dict[str, Any],
        rationale: str,
    ) -> CycleResult:
        summary = arguments.get("summary", rationale)
        evidence = arguments.get("success_evidence_refs", [])
        unresolved = arguments.get("unresolved", [])
        wake_conditions = arguments.get("wake_conditions", [])
        if not isinstance(summary, str):
            raise HarnessProtocolError("complete summary must be a string")
        if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
            raise HarnessProtocolError("success_evidence_refs must be a list of strings")
        if not isinstance(unresolved, list) or not all(
            isinstance(item, str) for item in unresolved
        ):
            raise HarnessProtocolError("unresolved must be a list of strings")
        if not isinstance(wake_conditions, list) or not all(
            isinstance(item, str) for item in wake_conditions
        ):
            raise HarnessProtocolError("wake_conditions must be a list of strings")
        known_evidence = GrowthEconomicHarness._known_evidence_refs(checkpoint)
        unknown = sorted(set(evidence) - known_evidence)
        if unknown:
            raise HarnessDecisionError(
                f"complete cited unknown success evidence refs: {unknown}",
                checkpoint,
            )
        failed_approaches = [
            entry.summary
            for entry in checkpoint.context
            if entry.metadata.get("status")
            in {"failed", "rejected", "outcome_unknown"}
            or entry.metadata.get("error")
        ]
        artifact_refs = sorted(known_evidence)
        canonical = json.dumps(
            {
                "run_id": checkpoint.run_id,
                "summary": summary,
                "unresolved": unresolved,
                "artifact_refs": artifact_refs,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        handoff = CycleHandoff(
            handoff_id=f"handoff_{digest[:32]}",
            previous_run_id=checkpoint.run_id,
            summary=summary,
            current_hypothesis=checkpoint.current_hypothesis,
            open_commitments=checkpoint.open_commitments,
            unresolved=unresolved,
            failed_approaches=failed_approaches,
            wake_conditions=wake_conditions,
            artifact_refs=artifact_refs,
            experience_refs=[
                item.experience_id for item in checkpoint.experience_candidates
            ],
            metadata={
                "plan_id": checkpoint.plan_state.plan_id if checkpoint.plan_state else None,
                "plan_revision": (
                    checkpoint.plan_state.revision if checkpoint.plan_state else None
                ),
                "step_index": checkpoint.step_index,
            },
        )
        return CycleResult(
            summary=summary,
            success_evidence_refs=evidence,
            unresolved=unresolved,
            cycle_handoff=handoff,
        )

    @staticmethod
    def _known_evidence_refs(checkpoint: HarnessCheckpoint) -> set[str]:
        refs: set[str] = set()
        for entry in checkpoint.context:
            refs.update(entry.artifact_refs)
        for candidate in checkpoint.experience_candidates:
            refs.update(candidate.evidence_refs)
            refs.update(candidate.counter_evidence_refs)
        continuity = checkpoint.continuity
        if continuity is not None:
            for event in continuity.wake_events:
                refs.update(event.artifact_refs)
            if continuity.cycle_handoff is not None:
                refs.update(continuity.cycle_handoff.artifact_refs)
            if continuity.memory_manifest is not None:
                for memory in continuity.memory_manifest.memories:
                    refs.update(memory.artifact_refs)
        return refs

    @staticmethod
    def _validate_tool_catalog(tools: list[ToolDescriptor]) -> None:
        seen: set[str] = set()
        for tool in tools:
            if tool.capability == "cognitive.deliberate":
                raise HarnessProtocolError(
                    "cognitive.deliberate is an internal capability and cannot be host-provided"
                )
            if tool.capability in seen:
                raise HarnessProtocolError(f"duplicate capability: {tool.capability}")
            seen.add(tool.capability)
