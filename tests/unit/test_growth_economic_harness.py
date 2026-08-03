from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest

from usmsb_sdk.growth_economic_harness import (
    ContextBudget,
    ContextEntry,
    ContextLoop,
    ExperienceDraft,
    ExperienceLoop,
    ExperiencePromotionPolicy,
    ExperienceState,
    ExperienceTransitionError,
    GroupContribution,
    GroupRequest,
    GroupResult,
    GrowthEconomicHarness,
    HarnessConfig,
    HarnessDecisionError,
    HarnessObjective,
    HarnessProtocolError,
    ModelCompletion,
    Observation,
    PromotionEvidence,
    SideEffectClass,
    ToolDescriptor,
)


def decision(
    kind: str,
    *,
    capability: str | None = None,
    arguments: dict[str, Any] | None = None,
    side_effect: str = "cognitive",
    rationale: str = "Use the latest observation to choose the next bounded action.",
    team_plan: dict[str, Any] | None = None,
    hypothesis: str | None = None,
    experience: dict[str, Any] | None = None,
) -> str:
    return json.dumps(
        {
            "action": {
                "kind": kind,
                "capability": capability,
                "arguments": arguments or {},
                "rationale": rationale,
                "expected_observation": "A complete, cited observation",
                "side_effect_class": side_effect,
                "team_plan": team_plan,
            },
            "current_hypothesis": hypothesis,
            "open_commitments": [],
            "experience_candidate": experience,
        }
    )


class ScriptedModel:
    def __init__(self, outputs: list[str] | Callable[[Any], str]) -> None:
        self.outputs = outputs
        self.requests = []

    async def complete(self, request):
        self.requests.append(request)
        if callable(self.outputs):
            output = self.outputs(request)
        else:
            output = self.outputs.pop(0)
        return ModelCompletion(raw_output=output, model="mechanics-fixture")


class RecordingTelemetry:
    def __init__(self) -> None:
        self.attempts = []
        self.events = []

    async def model_attempt(self, **payload):
        self.attempts.append(payload)

    async def event(self, name, payload):
        self.events.append((name, payload))


class ScriptedGroup:
    def __init__(self) -> None:
        self.requests: list[GroupRequest] = []

    async def deliberate(self, request: GroupRequest) -> GroupResult:
        self.requests.append(request)
        return GroupResult(
            contributions=[
                GroupContribution(
                    role=role.name,
                    proposal=f"{role.name} proposal",
                    objections=[role.challenge] if role.challenge else [],
                    confidence=0.6,
                    artifact_ref=f"artifact://{role.name}",
                )
                for role in request.team_plan.roles
            ],
            synthesis="The evidence is promising but needs an independent source.",
            conflicts=["Demand strength is disputed"],
            evidence_gaps=["independent source"],
            artifact_refs=["artifact://group/synthesis"],
        )


@pytest.fixture
def objective() -> HarnessObjective:
    return HarnessObjective(
        goal="Find a real unmet demand and choose the next evidence-producing action.",
        success_evidence=["independent demand evidence", "attributable downstream outcome"],
        stop_conditions=["evidence remains non-independent"],
    )


@pytest.fixture
def tools() -> list[ToolDescriptor]:
    return [
        ToolDescriptor(
            capability="market.scan",
            description="Observe public market evidence",
            side_effect_class=SideEffectClass.READ_ONLY,
        ),
        ToolDescriptor(
            capability="evidence.verify",
            description="Verify independence of cited evidence",
            side_effect_class=SideEffectClass.READ_ONLY,
        ),
    ]


@pytest.mark.asyncio
async def test_observation_changes_the_next_model_selected_action(objective, tools) -> None:
    def choose(request) -> str:
        has_low_quality = any(
            entry.get("metadata", {}).get("status") == "failed" for entry in request.context
        )
        return decision(
            "observe",
            capability="evidence.verify" if has_low_quality else "market.scan",
            side_effect="read_only",
            hypothesis="Public demand may exist but evidence independence is unresolved.",
        )

    model = ScriptedModel(choose)
    harness = GrowthEconomicHarness(model)
    first = await harness.step(objective=objective, tools=tools)
    assert first.action.capability == "market.scan"

    second = await harness.step(
        checkpoint=first.checkpoint,
        observation=Observation(
            action_id=first.action.action_id,
            status="failed",
            summary="The apparent demand sources are mirrors of one original post.",
            artifact_refs=["artifact://market/scan-1"],
        ),
        tools=tools,
    )
    assert second.action.capability == "evidence.verify"
    assert model.requests[1].context[-1]["metadata"]["status"] == "failed"


@pytest.mark.asyncio
async def test_model_selects_dynamic_group_then_uses_its_conflict(objective, tools) -> None:
    team_plan = {
        "roles": [
            {
                "name": "market_scout",
                "purpose": "Find independent evidence",
                "capabilities": ["search"],
                "challenge": None,
            },
            {
                "name": "adversarial_critic",
                "purpose": "Try to falsify the demand hypothesis",
                "capabilities": ["critique"],
                "challenge": "Assume all apparent signals are mirrors",
            },
        ],
        "synthesis_question": "Is the demand evidence independent enough to continue?",
        "stop_when": "The main uncertainty has an explicit evidence gap",
    }
    model = ScriptedModel(
        [
            decision(
                "delegate",
                capability="cognitive.deliberate",
                team_plan=team_plan,
                hypothesis="The demand signal needs adversarial review.",
            ),
            decision(
                "observe",
                capability="evidence.verify",
                side_effect="read_only",
                rationale="The model-selected team found an independent-source gap.",
            ),
        ]
    )
    group = ScriptedGroup()
    telemetry = RecordingTelemetry()
    harness = GrowthEconomicHarness(model, group_reasoner=group, telemetry=telemetry)

    result = await harness.step(objective=objective, tools=tools)
    assert result.action.capability == "evidence.verify"
    assert [role.name for role in group.requests[0].team_plan.roles] == [
        "market_scout",
        "adversarial_critic",
    ]
    group_entries = [entry for entry in result.checkpoint.context if entry.kind == "group"]
    assert group_entries[0].metadata["evidence_gaps"] == ["independent source"]
    assert telemetry.events[0][0] == "growth.group.completed"


@pytest.mark.asyncio
async def test_strict_json_failure_is_bounded_repaired_and_traced(objective, tools) -> None:
    valid = decision(
        "observe", capability="market.scan", side_effect="read_only"
    )
    telemetry = RecordingTelemetry()
    model = ScriptedModel(['{"action": {}, "action": {}}', valid])
    harness = GrowthEconomicHarness(
        model,
        telemetry=telemetry,
        config=HarnessConfig(max_structured_output_repairs=1),
    )
    result = await harness.step(objective=objective, tools=tools)
    assert result.kind == "action"
    assert len(telemetry.attempts) == 2
    assert "duplicate JSON key" in telemetry.attempts[0]["validation_error"]
    assert model.requests[1].last_validation_error


@pytest.mark.asyncio
async def test_hallucinated_or_misclassified_tool_fails_closed(objective, tools) -> None:
    hallucinated = GrowthEconomicHarness(
        ScriptedModel([decision("observe", capability="invented.tool", side_effect="read_only")])
    )
    with pytest.raises(HarnessDecisionError, match="unavailable capability"):
        await hallucinated.step(objective=objective, tools=tools)

    misclassified = GrowthEconomicHarness(
        ScriptedModel([decision("observe", capability="market.scan", side_effect="financial")])
    )
    with pytest.raises(HarnessDecisionError, match="side_effect_class"):
        await misclassified.step(objective=objective, tools=tools)


@pytest.mark.asyncio
async def test_checkpoint_requires_matching_observation_before_resuming(objective, tools) -> None:
    harness = GrowthEconomicHarness(
        ScriptedModel([decision("observe", capability="market.scan", side_effect="read_only")])
    )
    first = await harness.step(objective=objective, tools=tools)
    with pytest.raises(HarnessProtocolError, match="awaits observation"):
        await harness.step(checkpoint=first.checkpoint, tools=tools)
    with pytest.raises(HarnessProtocolError, match="must equal pending action"):
        await harness.step(
            checkpoint=first.checkpoint,
            observation=Observation(
                action_id="wrong",
                status="succeeded",
                summary="Wrong receipt",
            ),
            tools=tools,
        )


def test_context_compaction_preserves_goal_commitments_and_artifact_refs(objective) -> None:
    loop = ContextLoop(
        ContextBudget(max_input_tokens=500, reserved_output_tokens=100, preserve_recent_entries=2)
    )
    harness = GrowthEconomicHarness(ScriptedModel([]), context_loop=loop)
    checkpoint = harness.create_checkpoint(objective).model_copy(
        update={
            "open_commitments": ["verify evidence independence"],
            "context": [
                ContextEntry(
                    kind="observation",
                    summary="x" * 1_000,
                    artifact_refs=[f"artifact://{index}"],
                )
                for index in range(8)
            ],
        }
    )
    compacted = loop.compact(checkpoint)
    assert compacted.objective == objective
    assert compacted.open_commitments == ["verify evidence independence"]
    assert compacted.context[0].kind == "compact"
    assert "artifact://0" in compacted.context[0].artifact_refs
    assert compacted.context[-1].artifact_refs == ["artifact://7"]


def test_one_outcome_cannot_be_promoted_directly_to_skill() -> None:
    loop = ExperienceLoop()
    candidate = loop.candidate_from(
        ExperienceDraft(
            lesson="Mirrored sources should trigger independent verification.",
            applicability="Demand research with repeated citations.",
            evidence_refs=["artifact://one-run"],
            confidence=0.7,
        ),
        run_id="run-1",
    )
    assert candidate.state == ExperienceState.CANDIDATE
    evidence = PromotionEvidence(evaluation_ref="eval-1", policy_version="policy-1")
    with pytest.raises(ExperienceTransitionError):
        loop.transition(candidate, ExperienceState.PROMOTED_SKILL, evidence)


def test_experience_promotion_is_attributable_audited_and_reversible() -> None:
    policy = ExperiencePromotionPolicy(
        version="policy-1",
        promotion_requires_approval=True,
    )
    loop = ExperienceLoop(policy)
    candidate = loop.candidate_from(
        ExperienceDraft(
            lesson="A verified counterexample should revise the next hypothesis.",
            applicability="Evidence-led autonomous programs.",
            evidence_refs=["artifact://episode/1"],
            confidence=0.8,
        ),
        run_id="run-1",
    )
    probation = loop.transition(
        candidate,
        ExperienceState.PROBATION,
        PromotionEvidence(
            evaluation_ref="eval-1",
            policy_version="policy-1",
            observed_run_ids=("run-1",),
        ),
    )
    validated = loop.transition(
        probation,
        ExperienceState.VALIDATED,
        PromotionEvidence(
            evaluation_ref="eval-2",
            policy_version="policy-1",
            observed_run_ids=("run-1", "run-2"),
            outcome_refs=("artifact://outcome/1", "artifact://outcome/2"),
            repeated_outcomes=2,
            independent_evidence_refs=("artifact://independent/1",),
            scope="evidence-led programs",
            counter_evidence_resolved=True,
        ),
    )
    promoted = loop.transition(
        validated,
        ExperienceState.PROMOTED_SKILL,
        PromotionEvidence(
            evaluation_ref="eval-3",
            policy_version="policy-1",
            observed_run_ids=("run-1", "run-2", "run-3"),
            outcome_refs=(
                "artifact://outcome/1",
                "artifact://outcome/2",
                "artifact://outcome/3",
            ),
            repeated_outcomes=3,
            independent_evidence_refs=("artifact://independent/1",),
            counterfactual_ref="artifact://counterfactual/1",
            scope="evidence-led programs",
            k_threshold_passed=True,
            counter_evidence_resolved=True,
            approved_by="service-principal:experience-governor",
        ),
    )
    revoked = loop.transition(
        promoted,
        ExperienceState.REVOKED,
        PromotionEvidence(
            evaluation_ref="eval-revoke-1",
            policy_version="policy-1",
        ),
    )
    assert revoked.state == ExperienceState.REVOKED
    assert [item["to"] for item in revoked.metadata["transition_history"]] == [
        "probation",
        "validated",
        "promoted_skill",
        "revoked",
    ]


def test_legacy_repeated_count_cannot_fake_validation_runs() -> None:
    loop = ExperienceLoop(ExperiencePromotionPolicy(version="policy-1"))
    candidate = loop.candidate_from(
        ExperienceDraft(
            lesson="Repeated counters are not attributable outcomes.",
            applicability="Legacy imports.",
            evidence_refs=["artifact://legacy/1"],
            confidence=0.5,
        ),
        run_id="legacy-source",
    )
    with pytest.raises(ExperienceTransitionError):
        loop.transition(
            candidate,
            ExperienceState.VALIDATED,
            PromotionEvidence(
                evaluation_ref="eval-legacy",
                policy_version="policy-1",
                repeated_outcomes=99,
                independent_evidence_refs=("artifact://legacy/evidence",),
                outcome_refs=("artifact://legacy/outcome",),
                scope="legacy",
            ),
        )


@pytest.mark.asyncio
async def test_model_selected_wait_exposes_a_durable_wake_deadline(objective) -> None:
    harness = GrowthEconomicHarness(
        ScriptedModel(
            [
                decision(
                    "wait",
                    arguments={
                        "wake_conditions": ["new_market_signal"],
                        "wake_after_seconds": 900,
                    },
                    rationale="Wait for an independent market observation.",
                )
            ]
        )
    )
    result = await harness.step(objective=objective)
    assert result.kind == "wait"
    assert result.wait.wake_conditions == ["new_market_signal"]
    assert result.wait.wake_after_seconds == 900
