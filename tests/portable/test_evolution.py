"""Portable engine invariants; synthetic inputs, real SQLite and concurrency."""
import importlib
import importlib.util
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import pytest


@pytest.fixture(scope="module")
def autonomy(tmp_path_factory):
    script = Path(__file__).resolve().parents[2] / "scripts/export_autonomy.py"
    spec = importlib.util.spec_from_file_location("export_evolution_tests", script)
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    root = tmp_path_factory.mktemp("portable_evolution")
    exporter.export(root / "portable_evolution")
    sys.path.insert(0, str(root))
    try:
        yield importlib.import_module("portable_evolution.autonomy")
    finally:
        sys.path.remove(str(root))


def obs(a, ident="o1", **changes):
    return a.EnvironmentObservation(id=ident, source_id="source1", source_version=ident,
        observed_at=1000, fetched_at=1001, validity="valid", payload={"latency": 90},
        evidence_ids=("source-artifact",), **changes)


def subject(a, **changes):
    return a.SubjectSnapshot(subject_id="actor-a", **changes)


def environment(ident="a1", oid="o1", status="gap"):
    return {"assessments": [{"id": ident, "concern_id": "c1", "actor_id": "actor-a",
        "observation_id": oid, "title": "Reduce observed latency", "status": status,
        "verification": "Measure source latency", "desired": 30, "actual": 90}]}


def engine(a, tmp_path, **kwargs):
    return a.EvolutionEngine(a.SQLiteEvolutionStore(tmp_path / "private.sqlite"),
                            clock=lambda: 1100, **kwargs)


def test_journal_restarts_and_recovers_exact_unacknowledged_decision(autonomy, tmp_path):
    a = autonomy
    e = engine(a, tmp_path)
    first = e.cycle(subject(a), [obs(a)], environment=environment())
    assert first["decision"] == "create_goal" and first["effect"] == "proposal_only"
    recovered = engine(a, tmp_path).cycle(subject(a), [obs(a, "o2")], environment=environment("a2", "o2"))
    assert recovered["id"] == first["id"] and recovered["replayed"]
    e.acknowledge("actor-a", first["id"], {"id": "world-goal-1"})
    unchanged = e.cycle(subject(a), [obs(a)], environment=environment())
    assert unchanged["decision"] == "wait"
    again = e.cycle(subject(a), [obs(a)], environment=environment())
    assert again["replayed"]
    changed = e.cycle(subject(a), [obs(a, "o2")], environment=environment("a2", "o2"))
    assert changed["decision"] == "reconsider"


def test_question_alone_and_missing_resources_do_not_invent_need(autonomy, tmp_path):
    a = autonomy
    result = engine(a, tmp_path).cycle(subject(a), [obs(a)])
    assert result["decision"] == "wait"
    assert subject(a).record()["resources"]["availability"] == "unknown"


@pytest.mark.parametrize("access,owner,authorized,expected", [
    ("private", "actor-b", (), []),
    ("authorized", "actor-b", (), []),
    ("authorized", "actor-b", ("actor-a",), ["o1"]),
    ("private", "actor-a", (), ["o1"]),
    ("public", "actor-b", (), ["o1"]),
])
def test_visible_state_obeys_access_and_does_not_leak_ids(autonomy, tmp_path, access, owner, authorized, expected):
    a = autonomy
    result = engine(a, tmp_path).cycle(subject(a), [obs(a, access=access, owner_id=owner, authorized_subjects=authorized)],
                                        environment=environment())
    assert result["observation_ids"] == expected
    assert (result["decision"] == "create_goal") == bool(expected)


@pytest.mark.parametrize("changes", [{"validity": "unknown"}, {"validity": "retracted"},
    {"observed_at": 9999}, {"expires_at": 1050}])
def test_unknown_future_expired_retracted_dont_generate_goal(autonomy, tmp_path, changes):
    a = autonomy
    item = obs(a).record()
    item.update(changes)
    assert engine(a, tmp_path).cycle(subject(a), [item], environment=environment())["decision"] == "wait"


def test_other_subject_assessment_is_not_our_goal(autonomy, tmp_path):
    a = autonomy
    env = environment()
    env["assessments"][0]["actor_id"] = "someone-else"
    assert engine(a, tmp_path).cycle(subject(a), [obs(a)], environment=env)["decision"] == "wait"


def test_observation_versions_cannot_overwrite_history(autonomy, tmp_path):
    a = autonomy
    e = engine(a, tmp_path)
    e.cycle(subject(a), [obs(a)])
    tampered = obs(a).record()
    tampered["payload"]["latency"] = 10
    with pytest.raises(a.ContractError, match="overwrite"):
        e.cycle(subject(a), [tampered])


def test_budget_survives_restart_and_cannot_be_silently_expanded(autonomy, tmp_path):
    a = autonomy
    first = engine(a, tmp_path, max_episodes=1).cycle(subject(a), [obs(a)], environment=environment())
    engine(a, tmp_path, max_episodes=1).acknowledge("actor-a", first["id"], {"id": "g1"})
    aligned = engine(a, tmp_path, max_episodes=1).cycle(subject(a), [obs(a, "o2")], environment=environment("a2", "o2", "aligned"))
    engine(a, tmp_path, max_episodes=1).acknowledge("actor-a", aligned["id"], {"id": "learning1"})
    again = engine(a, tmp_path, max_episodes=1).cycle(subject(a), [obs(a, "o3")], environment=environment("a3", "o3"))
    assert again["decision"] == "wait"
    with pytest.raises(a.ContractError, match="budget mismatch"):
        engine(a, tmp_path, max_episodes=2).cycle(subject(a), [obs(a)])


def test_private_identity_is_bound(autonomy, tmp_path):
    a = autonomy
    e = engine(a, tmp_path)
    e.cycle(subject(a), [obs(a)])
    with pytest.raises(a.ContractError, match="identity"):
        e.cycle(a.SubjectSnapshot(subject_id="actor-b"), [obs(a)])


def test_policy_cannot_forge_attribution_or_completion(autonomy, tmp_path):
    a = autonomy
    class Malicious:
        version = "invalid.v1"
        def decide(self, context):
            return {"decision": "wait", "reason": "x", "effect": "completed"}
    with pytest.raises(a.ContractError, match="replace"):
        engine(a, tmp_path, policy=Malicious()).cycle(subject(a), [obs(a)])


def test_concurrent_responses_propose_same_command_once(autonomy, tmp_path):
    a = autonomy
    def run(_):
        return engine(a, tmp_path).cycle(subject(a), [obs(a)], environment=environment())
    with ThreadPoolExecutor(max_workers=5) as workers:
        results = list(workers.map(run, range(10)))
    assert len({r["id"] for r in results}) == 1
    with engine(a, tmp_path).store.transaction() as db:
        assert db.execute("SELECT COUNT(*) FROM evolution_decisions").fetchone()[0] == 1


def test_remote_unknown_queries_same_reference_and_terminal_receipt_is_immutable(autonomy, tmp_path):
    a = autonomy
    e = engine(a, tmp_path)
    e.cycle(subject(a), [obs(a)])
    unknown = e.record_remote("actor-a", {"state": "unknown", "run_ref": "r1", "error": "lost response"})
    assert unknown["automatic_retry"] is False
    assert e.cycle(subject(a), [obs(a)])["reason"] == "reconcile_original_execution"
    completed = {"state": "completed", "run_ref": "r1",
        "output": {"title": "Complete original artifact", "content_type": "application/json", "content": '{"result":1}'}}
    e.record_remote("actor-a", completed)
    assert e.cycle(subject(a), [obs(a)])["reason"] == "no_new_actionable_evidence"
    with pytest.raises(a.ContractError, match="immutable"):
        e.record_remote("actor-a", {**completed, "output": {**completed["output"], "content": "{}"}})


def test_feedback_reaches_replaceable_policy_with_complete_input(autonomy, tmp_path):
    a = autonomy
    seen = []
    class Policy:
        version = "research-policy.v1"
        def decide(self, context):
            seen.append(context)
            return {"decision": "wait", "reason": "review_counterevidence" if context["memory"]["feedback"] else "observe"}
    e = engine(a, tmp_path, policy=Policy())
    e.cycle(subject(a), [obs(a)])
    e.feedback("actor-a", observation_id="o1", status="retracted", evidence_ids=["independent-check"])
    result = e.cycle(subject(a), [obs(a)])
    assert result["reason"] == "review_counterevidence"
    assert seen[-1]["memory"]["feedback"][0]["causal_claim"] is False
    with e.store.transaction() as db:
        ctx = db.execute("SELECT context FROM evolution_decisions WHERE input_hash=?", (result["input_hash"],)).fetchone()[0]
        assert "independent-check" in ctx and "latency" in ctx
