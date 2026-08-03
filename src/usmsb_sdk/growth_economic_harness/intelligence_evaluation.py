"""Sealed, baseline-controlled evaluation for Harness intelligence.

This module does not contain a scripted answer.  An authorized evaluator runs
the same unseen case through different cognitive configurations, judges the
canonical traces, and produces an immutable report.  Mechanical mocks may
exercise the protocol but cannot mark a report as production evidence.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Literal, Protocol

from pydantic import Field, StrictBool, StrictInt, model_validator

from usmsb_sdk.growth_economic_harness.models import StrictModel


def _require_json_numbers(value: Any, *, fields: tuple[str, ...]) -> Any:
    if not isinstance(value, dict):
        return value
    for field in fields:
        if field not in value:
            continue
        number = value[field]
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise ValueError(f"{field} must be a JSON number")
    return value


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


class EvaluationVariant(str, Enum):
    FULL_HARNESS = "full_harness"
    NO_EXPERIENCE = "no_experience"
    NO_OBSERVATION_FEEDBACK = "no_observation_feedback"
    SINGLE_AGENT = "single_agent"


class SealedEvaluationCase(StrictModel):
    schema_version: Literal["growth-harness.evaluation-case.v1"] = (
        "growth-harness.evaluation-case.v1"
    )
    case_id: str = Field(min_length=1, max_length=160)
    objective: dict[str, Any]
    tool_catalog: list[dict[str, Any]] = Field(min_length=1, max_length=100)
    observation_script_ref: str = Field(min_length=1, max_length=1_000)
    success_rubric_ref: str = Field(min_length=1, max_length=1_000)
    seal: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    unseen: StrictBool = True

    def seal_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"seal"})

    def verify_seal(self) -> None:
        if canonical_hash(self.seal_payload()) != self.seal:
            raise ValueError("evaluation case seal does not match canonical content")


class IntelligenceScores(StrictModel):
    goal_progress: float = Field(ge=0, le=1)
    observation_adaptation: float = Field(ge=0, le=1)
    evidence_discipline: float = Field(ge=0, le=1)
    recovery_quality: float = Field(ge=0, le=1)
    safety_and_authorization: float = Field(ge=0, le=1)

    @model_validator(mode="before")
    @classmethod
    def require_exact_scores(cls, value: Any) -> Any:
        return _require_json_numbers(
            value,
            fields=(
                "goal_progress",
                "observation_adaptation",
                "evidence_discipline",
                "recovery_quality",
                "safety_and_authorization",
            ),
        )

    @property
    def mean(self) -> float:
        values = tuple(self.model_dump().values())
        return sum(values) / len(values)


class EvaluationRun(StrictModel):
    schema_version: Literal["growth-harness.evaluation-run.v1"] = (
        "growth-harness.evaluation-run.v1"
    )
    run_id: str = Field(min_length=1, max_length=200)
    case_id: str = Field(min_length=1, max_length=160)
    case_seal: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    variant: EvaluationVariant
    model_provider: str = Field(min_length=1, max_length=100)
    model_name: str = Field(min_length=1, max_length=200)
    model_is_real: StrictBool
    trace_artifact_ref: str = Field(min_length=1, max_length=1_000)
    trace_artifact_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    execution_configuration_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    judge_model_provider: str = Field(min_length=1, max_length=100)
    judge_model_name: str = Field(min_length=1, max_length=200)
    judge_model_is_real: StrictBool
    judge_artifact_ref: str = Field(min_length=1, max_length=1_000)
    judge_artifact_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    action_artifact_refs: list[str] = Field(default_factory=list, max_length=500)
    scores: IntelligenceScores
    hard_failures: list[str] = Field(default_factory=list, max_length=100)
    total_cost: float = Field(default=0, ge=0)
    total_latency_seconds: float = Field(default=0, ge=0)

    @model_validator(mode="before")
    @classmethod
    def require_exact_metrics(cls, value: Any) -> Any:
        return _require_json_numbers(
            value,
            fields=("total_cost", "total_latency_seconds"),
        )


class EvaluationGate(StrictModel):
    minimum_unseen_cases: StrictInt = Field(default=5, ge=1, le=10_000)
    minimum_full_score: float = Field(default=0.72, ge=0, le=1)
    minimum_baseline_delta: float = Field(default=0.08, ge=0, le=1)
    maximum_hard_failures: StrictInt = Field(default=0, ge=0)
    required_variants: list[EvaluationVariant] = Field(
        default_factory=lambda: [
            EvaluationVariant.FULL_HARNESS,
            EvaluationVariant.NO_EXPERIENCE,
            EvaluationVariant.NO_OBSERVATION_FEEDBACK,
            EvaluationVariant.SINGLE_AGENT,
        ]
    )

    @model_validator(mode="after")
    def validate_variant_matrix(self) -> "EvaluationGate":
        if EvaluationVariant.FULL_HARNESS not in self.required_variants:
            raise ValueError("intelligence gate must include the full Harness")
        if len(self.required_variants) != len(set(self.required_variants)):
            raise ValueError("intelligence gate variants must be unique")
        if len(self.required_variants) < 2:
            raise ValueError("intelligence gate requires at least one ablation baseline")
        return self

    @model_validator(mode="before")
    @classmethod
    def require_exact_thresholds(cls, value: Any) -> Any:
        return _require_json_numbers(
            value,
            fields=("minimum_full_score", "minimum_baseline_delta"),
        )


def _evaluate_report_runs(
    gate: EvaluationGate,
    runs: list[EvaluationRun],
) -> tuple[Literal["passed", "failed", "not_evaluated"], list[str]]:
    structural: list[str] = []
    indexed: dict[tuple[str, EvaluationVariant], EvaluationRun] = {}
    seals_by_case: dict[str, set[str]] = {}
    for run in runs:
        seals_by_case.setdefault(run.case_id, set()).add(run.case_seal)
        if not run.model_is_real:
            structural.append(f"run {run.run_id} used a mechanical/mock model")
            continue
        if not run.judge_model_is_real:
            structural.append(f"run {run.run_id} used a mechanical/mock judge")
            continue
        if (
            run.model_provider == run.judge_model_provider
            and run.model_name == run.judge_model_name
        ):
            structural.append(f"run {run.run_id} was not independently judged")
            continue
        key = (run.case_id, run.variant)
        if key in indexed:
            structural.append(f"duplicate run for {run.case_id}/{run.variant.value}")
            continue
        indexed[key] = run
    for case_id, seals in seals_by_case.items():
        if len(seals) != 1:
            structural.append(f"case {case_id} has inconsistent seals")
    case_ids = sorted(seals_by_case)
    if len(case_ids) < gate.minimum_unseen_cases:
        structural.append("insufficient sealed unseen cases")
    for case_id in case_ids:
        missing = [
            variant.value
            for variant in gate.required_variants
            if (case_id, variant) not in indexed
        ]
        if missing:
            structural.append(f"case {case_id} missing variants: {','.join(missing)}")
    if structural:
        return "not_evaluated", structural

    failures: list[str] = []
    hard_failures = sum(len(run.hard_failures) for run in indexed.values())
    if hard_failures > gate.maximum_hard_failures:
        failures.append(f"hard failure count {hard_failures} exceeds gate")
    for case_id in case_ids:
        full = indexed[(case_id, EvaluationVariant.FULL_HARNESS)].scores.mean
        baselines = [
            indexed[(case_id, variant)].scores.mean
            for variant in gate.required_variants
            if variant != EvaluationVariant.FULL_HARNESS
        ]
        if full < gate.minimum_full_score:
            failures.append(f"case {case_id} full-harness score below gate")
        if not baselines or full - max(baselines) < gate.minimum_baseline_delta:
            failures.append(f"case {case_id} lacks required baseline improvement")
    return ("failed", failures) if failures else ("passed", [])


class IntelligenceEvaluationReport(StrictModel):
    schema_version: Literal["growth-harness.intelligence-report.v1"] = (
        "growth-harness.intelligence-report.v1"
    )
    evaluation_id: str = Field(min_length=1, max_length=200)
    evaluator_ref: str = Field(min_length=1, max_length=1_000)
    gate: EvaluationGate
    runs: list[EvaluationRun] = Field(min_length=1, max_length=100_000)
    status: Literal["passed", "failed", "not_evaluated"]
    findings: list[str] = Field(default_factory=list, max_length=1_000)
    report_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def verify_report_hash(self) -> "IntelligenceEvaluationReport":
        payload = self.model_dump(mode="json", exclude={"report_hash"})
        if canonical_hash(payload) != self.report_hash:
            raise ValueError("intelligence report hash does not match canonical content")
        expected_status, expected_findings = _evaluate_report_runs(self.gate, self.runs)
        if self.status != expected_status:
            raise ValueError("intelligence report status does not match its run evidence")
        if self.status == "passed" and self.findings:
            raise ValueError("a passed intelligence report cannot contain findings")
        if not set(expected_findings).issubset(set(self.findings)):
            raise ValueError("intelligence report omitted computed gate findings")
        return self

    @classmethod
    def build(
        cls,
        *,
        evaluation_id: str,
        evaluator_ref: str,
        gate: EvaluationGate,
        runs: list[EvaluationRun],
        status: Literal["passed", "failed", "not_evaluated"],
        findings: list[str],
    ) -> "IntelligenceEvaluationReport":
        expected_status, expected_findings = _evaluate_report_runs(gate, runs)
        if status != expected_status:
            raise ValueError("requested report status does not match run evidence")
        merged_findings = list(dict.fromkeys([*expected_findings, *findings]))
        if status == "passed" and merged_findings:
            raise ValueError("a passed intelligence report cannot contain findings")
        payload = {
            "schema_version": "growth-harness.intelligence-report.v1",
            "evaluation_id": evaluation_id,
            "evaluator_ref": evaluator_ref,
            "gate": gate.model_dump(mode="json"),
            "runs": [run.model_dump(mode="json") for run in runs],
            "status": status,
            "findings": merged_findings,
        }
        return cls.model_validate({**payload, "report_hash": canonical_hash(payload)})


class EvaluationJudge(Protocol):
    async def judge(
        self,
        *,
        case: SealedEvaluationCase,
        variant: EvaluationVariant,
        trace_artifact_ref: str,
    ) -> "JudgedEvaluationVariant":
        """Judge a canonical full trace; projections are not the source of truth."""


class ExecutedEvaluationVariant(StrictModel):
    model_provider: str = Field(min_length=1, max_length=100)
    model_name: str = Field(min_length=1, max_length=200)
    model_is_real: StrictBool
    trace_artifact_ref: str = Field(min_length=1, max_length=1_000)
    trace_artifact_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    execution_configuration_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    action_artifact_refs: list[str] = Field(default_factory=list, max_length=500)
    hard_failures: list[str] = Field(default_factory=list, max_length=100)
    total_cost: float = Field(default=0, ge=0)
    total_latency_seconds: float = Field(default=0, ge=0)

    @model_validator(mode="before")
    @classmethod
    def require_exact_metrics(cls, value: Any) -> Any:
        return _require_json_numbers(
            value,
            fields=("total_cost", "total_latency_seconds"),
        )


class JudgedEvaluationVariant(StrictModel):
    scores: IntelligenceScores
    model_provider: str = Field(min_length=1, max_length=100)
    model_name: str = Field(min_length=1, max_length=200)
    model_is_real: StrictBool
    artifact_ref: str = Field(min_length=1, max_length=1_000)
    artifact_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class EvaluationExecutor(Protocol):
    async def execute(
        self,
        *,
        case: SealedEvaluationCase,
        variant: EvaluationVariant,
    ) -> ExecutedEvaluationVariant:
        """Execute the actual Harness variant and persist its canonical trace."""


class IntelligenceGateEvaluator:
    """Aggregate completed runs without silently manufacturing missing evidence."""

    def evaluate(
        self,
        *,
        cases: list[SealedEvaluationCase],
        runs: list[EvaluationRun],
        gate: EvaluationGate | None = None,
    ) -> tuple[Literal["passed", "failed", "not_evaluated"], list[str]]:
        active_gate = gate or EvaluationGate()
        findings: list[str] = []
        for case in cases:
            case.verify_seal()
        unseen = {case.case_id: case for case in cases if case.unseen}
        if len(unseen) < active_gate.minimum_unseen_cases:
            return "not_evaluated", ["insufficient sealed unseen cases"]

        indexed: dict[tuple[str, EvaluationVariant], EvaluationRun] = {}
        for run in runs:
            case = unseen.get(run.case_id)
            if case is None or run.case_seal != case.seal:
                findings.append(f"run {run.run_id} is not bound to an unseen sealed case")
                continue
            if not run.model_is_real:
                findings.append(f"run {run.run_id} used a mechanical/mock model")
                continue
            if not run.judge_model_is_real:
                findings.append(f"run {run.run_id} used a mechanical/mock judge")
                continue
            if (
                run.model_provider == run.judge_model_provider
                and run.model_name == run.judge_model_name
            ):
                findings.append(f"run {run.run_id} was not independently judged")
                continue
            key = (run.case_id, run.variant)
            if key in indexed:
                findings.append(f"duplicate run for {run.case_id}/{run.variant.value}")
                continue
            indexed[key] = run

        for case_id in unseen:
            missing = [
                variant.value
                for variant in active_gate.required_variants
                if (case_id, variant) not in indexed
            ]
            if missing:
                findings.append(f"case {case_id} missing variants: {','.join(missing)}")
        if findings:
            return "not_evaluated", findings

        hard_failures = sum(len(run.hard_failures) for run in indexed.values())
        if hard_failures > active_gate.maximum_hard_failures:
            findings.append(f"hard failure count {hard_failures} exceeds gate")

        for case_id in unseen:
            full = indexed[(case_id, EvaluationVariant.FULL_HARNESS)].scores.mean
            baselines = [
                indexed[(case_id, variant)].scores.mean
                for variant in active_gate.required_variants
                if variant != EvaluationVariant.FULL_HARNESS
            ]
            if full < active_gate.minimum_full_score:
                findings.append(f"case {case_id} full-harness score below gate")
            if full - max(baselines) < active_gate.minimum_baseline_delta:
                findings.append(f"case {case_id} lacks required baseline improvement")
        return ("failed", findings) if findings else ("passed", [])


class IntelligenceSuiteRunner:
    """Run the sealed full/ablation matrix and derive, never declare, its gate."""

    async def run(
        self,
        *,
        evaluation_id: str,
        evaluator_ref: str,
        cases: list[SealedEvaluationCase],
        executor: EvaluationExecutor,
        judge: EvaluationJudge,
        gate: EvaluationGate | None = None,
    ) -> IntelligenceEvaluationReport:
        active_gate = gate or EvaluationGate()
        runs: list[EvaluationRun] = []
        for case in cases:
            case.verify_seal()
            for variant in active_gate.required_variants:
                executed = await executor.execute(case=case, variant=variant)
                judged = await judge.judge(
                    case=case,
                    variant=variant,
                    trace_artifact_ref=executed.trace_artifact_ref,
                )
                run_id = "evalrun_" + hashlib.sha256(
                    (
                        f"{evaluation_id}:{case.case_id}:{case.seal}:{variant.value}:"
                        f"{executed.trace_artifact_hash}:{judged.artifact_hash}"
                    ).encode("utf-8")
                ).hexdigest()[:40]
                runs.append(
                    EvaluationRun(
                        run_id=run_id,
                        case_id=case.case_id,
                        case_seal=case.seal,
                        variant=variant,
                        model_provider=executed.model_provider,
                        model_name=executed.model_name,
                        model_is_real=executed.model_is_real,
                        trace_artifact_ref=executed.trace_artifact_ref,
                        trace_artifact_hash=executed.trace_artifact_hash,
                        execution_configuration_hash=(
                            executed.execution_configuration_hash
                        ),
                        judge_model_provider=judged.model_provider,
                        judge_model_name=judged.model_name,
                        judge_model_is_real=judged.model_is_real,
                        judge_artifact_ref=judged.artifact_ref,
                        judge_artifact_hash=judged.artifact_hash,
                        action_artifact_refs=executed.action_artifact_refs,
                        scores=judged.scores,
                        hard_failures=executed.hard_failures,
                        total_cost=executed.total_cost,
                        total_latency_seconds=executed.total_latency_seconds,
                    )
                )
        status, findings = IntelligenceGateEvaluator().evaluate(
            cases=cases,
            runs=runs,
            gate=active_gate,
        )
        return IntelligenceEvaluationReport.build(
            evaluation_id=evaluation_id,
            evaluator_ref=evaluator_ref,
            gate=active_gate,
            runs=runs,
            status=status,
            findings=findings,
        )
