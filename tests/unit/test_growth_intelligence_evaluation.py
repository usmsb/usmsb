from __future__ import annotations

from usmsb_sdk.growth_economic_harness import (
    EvaluationGate,
    EvaluationRun,
    EvaluationVariant,
    IntelligenceEvaluationReport,
    IntelligenceGateEvaluator,
    IntelligenceScores,
    SealedEvaluationCase,
    canonical_hash,
)


def _case(case_id: str) -> SealedEvaluationCase:
    payload = {
        "schema_version": "growth-harness.evaluation-case.v1",
        "case_id": case_id,
        "objective": {"goal": "adapt to evidence"},
        "tool_catalog": [{"capability": "evidence.read"}],
        "observation_script_ref": f"artifact://cases/{case_id}/observations",
        "success_rubric_ref": f"artifact://cases/{case_id}/rubric",
        "unseen": True,
    }
    return SealedEvaluationCase(**payload, seal=canonical_hash(payload))


def _run(
    case: SealedEvaluationCase,
    variant: EvaluationVariant,
    score: float,
) -> EvaluationRun:
    return EvaluationRun(
        run_id=f"run-{case.case_id}-{variant.value}",
        case_id=case.case_id,
        case_seal=case.seal,
        variant=variant,
        model_provider="authorized-provider",
        model_name="real-evaluation-model",
        model_is_real=True,
        trace_artifact_ref=f"artifact://traces/{case.case_id}/{variant.value}",
        trace_artifact_hash=canonical_hash(
            {"case": case.case_id, "variant": variant.value, "kind": "trace"}
        ),
        execution_configuration_hash=canonical_hash(
            {"case": case.case_id, "variant": variant.value, "kind": "config"}
        ),
        judge_model_provider="independent-provider",
        judge_model_name="real-judge-model",
        judge_model_is_real=True,
        judge_artifact_ref=f"artifact://judgements/{case.case_id}/{variant.value}",
        judge_artifact_hash=canonical_hash(
            {"case": case.case_id, "variant": variant.value, "kind": "judgement"}
        ),
        scores=IntelligenceScores(
            goal_progress=score,
            observation_adaptation=score,
            evidence_discipline=score,
            recovery_quality=score,
            safety_and_authorization=score,
        ),
    )


def test_mock_or_incomplete_matrix_cannot_pass_intelligence_gate() -> None:
    case = _case("sealed-1")
    run = _run(case, EvaluationVariant.FULL_HARNESS, 0.9).model_copy(
        update={"model_is_real": False}
    )
    status, findings = IntelligenceGateEvaluator().evaluate(
        cases=[case],
        runs=[run],
        gate=EvaluationGate(minimum_unseen_cases=1),
    )
    assert status == "not_evaluated"
    assert findings


def test_mock_or_same_model_judge_cannot_pass_intelligence_gate() -> None:
    case = _case("sealed-judge")
    gate = EvaluationGate(minimum_unseen_cases=1)
    variants = list(gate.required_variants)
    mock_judge_runs = [
        _run(case, variant, 0.9 if variant == EvaluationVariant.FULL_HARNESS else 0.6)
        .model_copy(update={"judge_model_is_real": False})
        for variant in variants
    ]
    status, findings = IntelligenceGateEvaluator().evaluate(
        cases=[case],
        runs=mock_judge_runs,
        gate=gate,
    )
    assert status == "not_evaluated"
    assert findings

    same_model_runs = [
        _run(case, variant, 0.9 if variant == EvaluationVariant.FULL_HARNESS else 0.6)
        .model_copy(
            update={
                "judge_model_provider": "authorized-provider",
                "judge_model_name": "real-evaluation-model",
            }
        )
        for variant in variants
    ]
    status, findings = IntelligenceGateEvaluator().evaluate(
        cases=[case],
        runs=same_model_runs,
        gate=gate,
    )
    assert status == "not_evaluated"
    assert findings


def test_full_harness_must_beat_all_ablation_baselines() -> None:
    case = _case("sealed-2")
    runs = [
        _run(case, EvaluationVariant.FULL_HARNESS, 0.9),
        _run(case, EvaluationVariant.NO_EXPERIENCE, 0.65),
        _run(case, EvaluationVariant.NO_OBSERVATION_FEEDBACK, 0.6),
        _run(case, EvaluationVariant.SINGLE_AGENT, 0.7),
    ]
    status, findings = IntelligenceGateEvaluator().evaluate(
        cases=[case],
        runs=runs,
        gate=EvaluationGate(
            minimum_unseen_cases=1,
            minimum_full_score=0.8,
            minimum_baseline_delta=0.1,
        ),
    )
    assert status == "passed"
    assert findings == []


def test_report_cannot_self_declare_passed_against_run_evidence() -> None:
    case = _case("sealed-self-declaration")
    incomplete = [_run(case, EvaluationVariant.FULL_HARNESS, 0.99)]
    gate = EvaluationGate(minimum_unseen_cases=1)
    try:
        IntelligenceEvaluationReport.build(
            evaluation_id="eval-self-declaration",
            evaluator_ref="artifact://evaluators/authorized-1",
            gate=gate,
            runs=incomplete,
            status="passed",
            findings=[],
        )
    except ValueError as exc:
        assert "status does not match" in str(exc)
    else:
        raise AssertionError("incomplete evidence self-declared a passed gate")
