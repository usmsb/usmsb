"""Existing Harness ladder persisted and fed into the portable strategy.

Attestations here are synthetic resolver fixtures, not external evidence.
"""
import importlib
import importlib.util
from pathlib import Path
import sys
import pytest


@pytest.fixture(scope="module")
def modules(tmp_path_factory):
    script = Path(__file__).resolve().parents[2] / "scripts/export_autonomy.py"
    spec = importlib.util.spec_from_file_location("export_learning", script)
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    root = tmp_path_factory.mktemp("learning")
    exporter.export(root / "portable_learning")
    sys.path.insert(0, str(root))
    try:
        yield importlib.import_module("portable_learning.autonomy"), importlib.import_module("portable_learning.autonomy.learning")
    finally:
        sys.path.remove(str(root))


def setup(modules, tmp_path):
    a, l = modules
    refs = {f"outcome-{n}": {"ref": f"outcome-{n}", "unit_id": f"local-unit-{n}", "issuer": "producer", "kind": "execution", "content_hash": f"hash-{n}", "verified": True, "validity": "valid"} for n in (1, 2, 3)}
    refs["evaluation"] = {"ref": "evaluation", "issuer": "independent-checker", "kind": "evaluation", "content_hash": "evaluation-hash", "verified": True, "validity": "valid"}
    refs["correction"] = {"ref": "correction", "issuer": "source-owner", "kind": "correction", "content_hash": "correction-hash", "verified": True, "validity": "valid", "supersedes": ["outcome-1"]}
    store = a.SQLiteEvolutionStore(tmp_path / "private.sqlite")
    journal = l.ExperienceJournal(store, "learner", refs.__getitem__)
    journal.candidate({"lesson": "Check canonical source before reusing a method", "applicability": "This local protocol revision only", "evidence_refs": ["outcome-1"], "confidence": 0.3}, run_id="local-unit-1", experience_id="lesson-1")
    return a, l, refs, store, journal


def evidence(l, n, **changes):
    return l.PromotionEvidence(evaluation_ref="evaluation", observed_run_ids=tuple(f"local-unit-{i}" for i in range(1, n + 1)),
        outcome_refs=tuple(f"outcome-{i}" for i in range(1, n + 1)), independent_evidence_refs=("evaluation",), scope="This local protocol revision only", policy_version="growth-experience-policy.v1", **changes)


def test_existing_ladder_persists_with_original_transition_history(modules, tmp_path):
    a, l, refs, store, journal = setup(modules, tmp_path)
    probation = journal.transition("lesson-1", "probation", evidence(l, 1))
    assert probation["state"] == "probation"
    reopened = l.ExperienceJournal(a.SQLiteEvolutionStore(store.path), "learner", refs.__getitem__)
    validated = reopened.transition("lesson-1", "validated", evidence(l, 2))
    assert len(validated["metadata"]["transition_history"]) == 2
    assert reopened.transition("lesson-1", "validated", evidence(l, 2)) == validated
    with pytest.raises(ValueError):
        reopened.transition("lesson-1", "promoted_skill", evidence(l, 3))
    engine = a.EvolutionEngine(store, clock=lambda: 1000)
    engine.cycle(a.SubjectSnapshot("learner"), [])
    with store.transaction() as db:
        assert store.memory(db)["applicable_experiences"][0]["experience_id"] == "lesson-1"


def test_counterevidence_propagates_to_dependents_and_changes_next_strategy(modules, tmp_path):
    a, l, refs, store, journal = setup(modules, tmp_path)
    journal.transition("lesson-1", "probation", evidence(l, 1))
    journal.transition("lesson-1", "validated", evidence(l, 2))
    journal.candidate({"lesson": "A derived method", "applicability": "Same local revision", "evidence_refs": ["outcome-2"], "confidence": 0.2}, run_id="local-unit-2", experience_id="lesson-2", depends_on=["lesson-1"])
    engine = a.EvolutionEngine(store, clock=lambda: 1000)
    assert engine.cycle(a.SubjectSnapshot("learner"), [])["decision"] == "wait"
    event = journal.invalidate("outcome-1", correction_ref="correction", reason="Source reports a counterexample")
    assert event["impacted_experience_ids"] == ["lesson-1", "lesson-2"]
    decision = engine.cycle(a.SubjectSnapshot("learner"), [])
    assert decision["reason"] == "experience_evidence_invalidated"
    assert decision["experience_ids"] == ["lesson-1", "lesson-2"]
    engine.acknowledge("learner", decision["id"], {"id": "attributed-world-learning"})
    assert engine.cycle(a.SubjectSnapshot("learner"), [])["decision"] == "wait"
    with store.transaction() as db:
        memory = store.memory(db)
        assert not memory["applicable_experiences"]
        assert {r["state"] for r in memory["experiences"]} == {"deprecated"}
    with pytest.raises(ValueError, match="new evidence-grounded candidate"):
        journal.transition("lesson-1", "probation", evidence(l, 1))
    assert journal.invalidate("outcome-1", correction_ref="correction", reason="Source reports a counterexample") == event


def test_invalid_or_unrelated_correction_does_not_change_records(modules, tmp_path):
    _, _, refs, store, journal = setup(modules, tmp_path)
    with pytest.raises(ValueError):
        journal.invalidate("outcome-2", correction_ref="correction", reason="Not a matching source")
    refs["correction"]["verified"] = False
    with pytest.raises(ValueError):
        journal.invalidate("outcome-1", correction_ref="correction", reason="Unverified")
    with store.transaction() as db:
        assert db.execute("SELECT COUNT(*) FROM learning_invalidations").fetchone()[0] == 0


def test_observation_counts_and_independence_cannot_be_fabricated(modules, tmp_path):
    _, l, refs, _, journal = setup(modules, tmp_path)
    with pytest.raises(ValueError, match="observation units"):
        journal.transition("lesson-1", "probation", l.PromotionEvidence(evaluation_ref="evaluation", observed_run_ids=("invented",), outcome_refs=("outcome-1",), policy_version="growth-experience-policy.v1"))
    refs["evaluation"]["issuer"] = "producer"
    with pytest.raises(ValueError, match="different evaluator"):
        journal.transition("lesson-1", "probation", evidence(l, 1))
    refs["evaluation"]["issuer"] = "independent-checker"
    refs["outcome-1"]["validity"] = "retracted"
    with pytest.raises(ValueError, match="currently verified"):
        journal.transition("lesson-1", "probation", evidence(l, 1))


def test_license_revocation_is_durable_and_does_not_claim_information_recall(modules, tmp_path):
    _, _, refs, store, journal = setup(modules, tmp_path)
    refs["correction"]["kind"] = "license_revocation"
    event = journal.invalidate("outcome-1", correction_ref="correction", reason="Owner withdrawal", license_revoked=True)
    assert event["published_information_recalled"] is False
    with store.transaction() as db:
        assert store.memory(db)["experiences"][0]["state"] == "revoked"


def test_promoted_skill_requires_resolved_counterfactual_and_attested_gate(modules, tmp_path):
    _, l, refs, _, journal = setup(modules, tmp_path)
    journal.transition("lesson-1", "probation", evidence(l, 1))
    journal.transition("lesson-1", "validated", evidence(l, 2))
    refs["cf"] = {**refs["evaluation"], "ref": "cf", "kind": "counterfactual"}
    with pytest.raises(ValueError, match="K gate"):
        journal.transition("lesson-1", "promoted_skill", evidence(l, 3, k_threshold_passed=True, counterfactual_ref="cf"))
    refs["evaluation"]["gates"] = {"k_threshold_passed": True}
    assert journal.transition("lesson-1", "promoted_skill", evidence(l, 3, k_threshold_passed=True, counterfactual_ref="cf"))["state"] == "promoted_skill"
