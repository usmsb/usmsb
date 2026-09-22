"""Portable collaboration choices from synthetic snapshots, not live execution."""
import importlib
import importlib.util
from pathlib import Path
import sys
import pytest


@pytest.fixture(scope="module")
def collaboration(tmp_path_factory):
    script = Path(__file__).resolve().parents[2] / "scripts/export_autonomy.py"
    spec = importlib.util.spec_from_file_location("export_collaboration_tests", script)
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    root = tmp_path_factory.mktemp("collaboration")
    exporter.export(root / "portable_collaboration")
    sys.path.insert(0, str(root))
    try:
        yield importlib.import_module("portable_collaboration.autonomy.collaboration")
    finally:
        sys.path.remove(str(root))


def config(**changes):
    return {"execution_scope": "owner_authorized_local_programs", "provider_ids": ["p1", "p2"], "requester_ids": [],
        "max_requests": 2, "max_accepts": 1, "accept_operations": [], "verify": [], "work": [{"concern_id": "c",
            "produce_operation": "unknown.vendor.operation", "verify_operation": "verify", "consume_operation": "consume",
            "candidate_format": "unknown.type.v7", "criterion": "Exact reproducibility", "input_object_ids": []}], **changes}


def context():
    return {"subject": {"subject_id": "me", "goals": [{"id": "g", "status": "active"}], "resources": {"availability": "unknown"}},
        "memory": {"concerns": {"c": {"goal_id": "g", "phase": "gap", "assessment_id": "a", "episodes": 1}}, "actions": [], "remotes": []},
        "observations": [{"id": "o", "effective_validity": "valid"}], "limits": {"max_episodes": 3}, "environment": {
            "goals": [{"id": "g", "status": "active", "owner_id": "me", "member_ids": ["me"]}], "executions": [], "objects": [],
            "assessments": [{"actor_id": "me", "concern_id": "c", "id": "a", "observation_id": "o", "status": "gap"}],
            "capabilities": [{"id": "cap-1", "owner_id": "p1", "operation": "unknown.vendor.operation", "runtime_online": True, "available_slots": 1, "remaining_today": 1},
                             {"id": "cap-2", "owner_id": "p2", "operation": "unknown.vendor.operation", "runtime_online": True, "available_slots": 1, "remaining_today": 1}]}}


def started(ctx, status):
    ctx["memory"]["actions"].append({"action_key": "work:g:produce:0", "receipt": {"id": "exec-1"}, "intent": {"operation": "request_execution",
        "parameters": {"capability_id": "cap-1", "observation_ids": ["o"]}}})
    ctx["environment"]["executions"] = [{"id": "exec-1", "status": status}]


def test_discovery_uses_available_authorized_offers_and_preserves_unknown_resources(collaboration):
    c = context()
    c["environment"]["capabilities"][0]["runtime_online"] = False
    c["environment"]["capabilities"].insert(0, {**c["environment"]["capabilities"][1], "id": "cap-0", "owner_id": "not-authorized"})
    result = collaboration.CollaborationPolicy(config()).decide(c)
    assert result["intent"]["parameters"]["capability_id"] == "cap-2"
    assert c["subject"]["resources"]["availability"] == "unknown"
    c["environment"]["capabilities"] = []
    assert collaboration.CollaborationPolicy(config()).decide(c)["intent"]["operation"] == "record_goal_gap"


@pytest.mark.parametrize("state", ["uncertain", "leased", "accepted", "requested", "closed_uncertain", "failed"])
def test_unknown_and_non_authorized_failure_never_replay(collaboration, state):
    c = context()
    started(c, state)
    assert collaboration.CollaborationPolicy(config()).decide(c)["decision"] == "wait"


@pytest.mark.parametrize("state", ["cancelled", "declined"])
def test_unstarted_termination_can_select_an_alternative(collaboration, state):
    c = context()
    started(c, state)
    result = collaboration.CollaborationPolicy(config()).decide(c)
    assert result["intent"]["parameters"]["capability_id"] == "cap-2"
    assert result["action_key"] == "work:g:produce:1"


def test_explicit_read_only_recovery_and_persistent_request_budget(collaboration):
    c, cfg = context(), config()
    started(c, "failed")
    cfg["work"][0]["allow_read_only_recovery"] = True
    policy = collaboration.CollaborationPolicy(cfg)
    assert policy.decide(c)["intent"]["parameters"]["capability_id"] == "cap-2"
    c["environment"]["assessments"][0]["observation_id"] = "new-source"
    c["observations"][0]["id"] = "new-source"
    assert policy.decide(c)["intent"]["parameters"]["capability_id"] == "cap-1"
    c["memory"]["actions"].append({"action_key": "another-request", "intent": {"operation": "request_execution"}})
    assert policy.decide(c)["reason"] == "persistent_request_execution_budget"


def test_a_policy_is_not_a_grant_to_run_models_or_modify_owner_budgets(collaboration):
    with pytest.raises(ValueError):
        collaboration.CollaborationPolicy(config(execution_scope="any_paid_provider"))
    assert collaboration.CollaborationPolicy(config()).version != collaboration.CollaborationPolicy(config(max_requests=3)).version
    assert "reflect_goal" not in collaboration.EFFECTS and "offer_resource" not in collaboration.EFFECTS
