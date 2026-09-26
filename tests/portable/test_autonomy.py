"""No optional SDK dependencies or model calls; use the supported export path."""
import importlib
import importlib.util
from pathlib import Path
import sys
import pytest


@pytest.fixture(scope="module")
def contracts(tmp_path_factory):
    script = Path(__file__).resolve().parents[2] / "scripts/export_autonomy.py"
    spec = importlib.util.spec_from_file_location("export_autonomy", script)
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    root = tmp_path_factory.mktemp("portable")
    exporter.export(root / "portable_usmsb")
    exporter.export(root / "portable_usmsb", check=True)
    sys.path.insert(0, str(root))
    yield importlib.import_module("portable_usmsb.autonomy")
    sys.path.remove(str(root))


def test_goal_reuses_existing_element(contracts):
    goal = contracts.goal_element(dict(id="g", title="open", description="real gap", status="active", owner_id="a"))
    assert goal.associated_agent_id == "a" and goal.status == "in_progress"


def test_feedback_can_revise_intent_without_rewriting_identity_or_obligations(contracts):
    revision = importlib.import_module("portable_usmsb.autonomy.goal_revision")
    source = dict(id="g", title="原目标", description="初始假设", domain="research", success_criteria="原判断")
    original = revision.goal_version(source)
    patch = revision.revision_patch({"description": "根据新证据修订的目标"})
    updated = revision.goal_version({**source, **patch, "revision": 2})
    assert original["revision"] == 1 and updated["revision"] == 2
    assert original["goal_id"] == updated["goal_id"]
    assert source["description"] == original["intent"]["description"] == "初始假设"
    for invalid in ({"owner_id": "another"}, {"status": "completed"}, {}, {"description": ""}):
        with pytest.raises(contracts.ContractError):
            revision.revision_patch(invalid)
    for invalid in (True, 0, -1, "2"):
        with pytest.raises(contracts.ContractError):
            revision.revision_basis(invalid)


def test_open_world_identity_is_namespaced_and_cannot_alias_another_ledger(contracts):
    node = "wishbud:ed25519:" + "A" * 43
    ref = contracts.world_reference(node, "storage_" + "a" * 20, "goal", "g1")
    assert ref != contracts.world_reference(node, "storage_" + "b" * 20, "goal", "g1")
    for record_id in ("../../foreign", "a/b", None, ""):
        with pytest.raises(contracts.ContractError):
            contracts.world_reference(node, "storage_" + "a" * 20, "goal", record_id)


def test_reference_feedback_policy_is_evidence_bound_and_finite(contracts):
    evidence = {"id": "a1", "observation_id": "o1", "status": "gap"}
    assert contracts.feedback_decision(evidence, {})["decision"] == "investigate"
    memory = {"assessment_id": "a1", "goal_id": "g1", "phase": "gap", "episodes": 1, "strategy": "learned-from-execution"}
    assert contracts.feedback_decision(evidence, memory)["decision"] == "wait"
    changed = {**evidence, "id": "a2", "status": "aligned"}
    assert contracts.feedback_decision(changed, memory)["decision"] == "assess_effect"
    result = contracts.feedback_decision(evidence, {**memory, "phase": "aligned", "assessment_id": "a2"})
    assert result["previous_strategy"] == "learned-from-execution" and not result["causal_claim"]
    assert contracts.feedback_decision(evidence, {"episodes": 12})["reason"] == "episode_budget"
    for state in ("unknown", "disabled"):
        assert contracts.feedback_decision({**evidence, "status": state}, {})["decision"] == "wait"


def test_specialization_preserves_units_unknown_fields_and_original(contracts):
    base = contracts.model_definition("timed object", "Object", [], {"duration": {"type": "number", "unit": "seconds", "required": True}})
    child = contracts.model_definition("film", "Object", [base], {"caption": {"type": "string"}})
    raw = {"duration": 1.5, "caption": "a", "future_extension": {"x": [1]}}
    parsed = contracts.model_properties(child, raw)
    parsed["future_extension"]["x"].append(2)
    assert raw["future_extension"]["x"] == [1]
    for fields in ({"duration": {"type": "number", "unit": "minutes", "required": True}}, {"duration": {"type": "string"}}):
        with pytest.raises(contracts.ContractError):
            contracts.model_definition("invalid", "Object", [base], fields)
    for props in ({}, {"duration": True}, {"duration": float("nan")}):
        with pytest.raises(contracts.ContractError):
            contracts.model_properties(child, props)


def test_relation_is_only_an_attributed_statement(contracts):
    relation = contracts.attributed_relation("a", {"kind": "goal", "id": "one"}, {"kind": "object", "id": "two"}, "supports", "my reason")
    assert relation["effect"] == "statement_only"
    with pytest.raises(contracts.ContractError):
        contracts.attributed_relation("a", relation["source"], relation["target"], "grants_access", "no authority")
    ref = contracts.object_reference({"id": "version2", "logical_id": "original", "content": "unchanged"})
    assert ref["object_id"] == "original" and ref["version_id"] == "version2"


def test_dependency_graph_rejects_cycles_and_missing_steps(contracts):
    for steps in ([dict(id="a", title="a", depends_on=["a"])],
                  [dict(id="a", title="a", depends_on=["b"])],
                  [dict(id="a", title="a"), dict(id="a", title="again")]):
        with pytest.raises(contracts.ContractError):
            contracts.plan_steps(steps)
    assert len(contracts.plan_steps([dict(id="a", title="a"), dict(id="b", title="b", depends_on=["a"])])) == 2


def test_every_criterion_needs_attributed_evidence(contracts):
    contract = contracts.goal_contract([dict(id="c", description="real validation", evidence_kind="execution")], ["peer"])
    with pytest.raises(contracts.ContractError):
        contracts.review_checks(contract, [dict(criterion_id="c", status="pass", reason="looks good")])
    assert contracts.review_checks(contract, [dict(criterion_id="c", status="unknown", reason="await provider")])[0]["status"] == "unknown"


def test_remote_acceptance_cannot_fake_success(contracts):
    assert contracts.remote_status(dict(state="accepted", run_ref="provider:123"))["state"] == "accepted"
    with pytest.raises(contracts.ContractError):
        contracts.remote_status(dict(state="completed", run_ref="provider:123"))


def test_malformed_json_is_a_contract_error(contracts):
    with pytest.raises(contracts.ContractError):
        contracts.goal_contract([dict(id="c", description="a", evidence_kind=[])], ["v"])
    with pytest.raises(contracts.ContractError):
        contracts.remote_status(dict(state=[], run_ref="r"))
    spec = contracts.goal_contract([dict(id="c", description="a")], ["v"])
    with pytest.raises(contracts.ContractError):
        contracts.review_checks(spec, [dict(criterion_id={}, status="unknown", reason="a")])
