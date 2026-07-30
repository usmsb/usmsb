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
from usmsb_sdk.growth_economic_harness.models import (
    ActionIntent,
    ActionKind,
    ContextEntry,
    CycleResult,
    ExperienceRecord,
    HarnessCheckpoint,
    HarnessObjective,
    HarnessStepResult,
    ModelDecision,
    Observation,
    ToolDescriptor,
    WaitIntent,
)
from usmsb_sdk.growth_economic_harness.ports import (
    CognitiveModel,
    EmptyExperienceRepository,
    ExperienceRepository,
    GroupReasoner,
    GroupRequest,
    ModelTurnRequest,
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
        telemetry: TelemetrySink | None = None,
        config: HarnessConfig | None = None,
    ) -> None:
        self.model = model
        self.group_reasoner = group_reasoner
        self.context_loop = context_loop or ContextLoop()
        self.experience_loop = experience_loop or ExperienceLoop()
        self.experience_repository = experience_repository or EmptyExperienceRepository()
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
        checkpoint = self._accept_observation(checkpoint, observation)
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

        for internal_index in range(self.config.max_internal_decisions_per_step):
            checkpoint = self.context_loop.compact(checkpoint)
            decision = await self._decide(checkpoint, tool_catalog, experiences)
            checkpoint = self._record_decision(checkpoint, decision)
            draft = decision.action

            if draft.capability == "cognitive.deliberate":
                if self.group_reasoner is None or draft.team_plan is None:
                    raise HarnessDecisionError(
                        "model requested cognitive.deliberate but no GroupReasoner is configured",
                        checkpoint,
                    )
                group_result = await self.group_reasoner.deliberate(
                    GroupRequest(
                        run_id=checkpoint.run_id,
                        step_index=checkpoint.step_index,
                        objective=checkpoint.objective.model_dump(mode="json"),
                        team_plan=draft.team_plan,
                        context=[entry.model_dump(mode="json") for entry in checkpoint.context],
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
                result = self._cycle_result(draft.arguments, draft.rationale)
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
    ) -> ModelDecision:
        validation_error: str | None = None
        for attempt_index in range(self.config.max_structured_output_repairs + 1):
            request = ModelTurnRequest(
                run_id=checkpoint.run_id,
                step_index=checkpoint.step_index,
                objective=checkpoint.objective.model_dump(mode="json"),
                current_hypothesis=checkpoint.current_hypothesis,
                open_commitments=checkpoint.open_commitments,
                context=[entry.model_dump(mode="json") for entry in checkpoint.context],
                tools=tools,
                recalled_experiences=experiences,
                last_validation_error=validation_error,
            )
            completion = await self.model.complete(request)
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
                return decision
        raise HarnessDecisionError(
            f"model failed strict structured output after bounded repair: {validation_error}",
            checkpoint,
        )

    def _record_decision(
        self,
        checkpoint: HarnessCheckpoint,
        decision: ModelDecision,
    ) -> HarnessCheckpoint:
        candidates = list(checkpoint.experience_candidates)
        if decision.experience_candidate is not None:
            candidates.append(
                self.experience_loop.candidate_from(
                    decision.experience_candidate,
                    run_id=checkpoint.run_id,
                )
            )
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
        return checkpoint.model_copy(
            update={
                "current_hypothesis": (
                    decision.current_hypothesis or checkpoint.current_hypothesis
                ),
                "open_commitments": decision.open_commitments,
                "experience_candidates": candidates,
                "context": [*checkpoint.context, entry],
            }
        )

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
    def _cycle_result(arguments: dict[str, Any], rationale: str) -> CycleResult:
        summary = arguments.get("summary", rationale)
        evidence = arguments.get("success_evidence_refs", [])
        unresolved = arguments.get("unresolved", [])
        if not isinstance(summary, str):
            raise HarnessProtocolError("complete summary must be a string")
        if not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
            raise HarnessProtocolError("success_evidence_refs must be a list of strings")
        if not isinstance(unresolved, list) or not all(
            isinstance(item, str) for item in unresolved
        ):
            raise HarnessProtocolError("unresolved must be a list of strings")
        return CycleResult(
            summary=summary,
            success_evidence_refs=evidence,
            unresolved=unresolved,
        )

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
