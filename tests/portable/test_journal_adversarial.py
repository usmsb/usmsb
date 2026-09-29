"""Adversarial exported-core checks: real SQLite, synthetic host identities, no services."""

import importlib
import importlib.util
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from threading import Barrier, Event

import pytest


@pytest.fixture(scope="module")
def api(tmp_path_factory):
    script = Path(__file__).resolve().parents[2] / "scripts/export_autonomy.py"
    spec = importlib.util.spec_from_file_location("export_journal_adversarial", script)
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    root = tmp_path_factory.mktemp("journal_adversarial")
    package = "portable_journal_adversarial"
    exporter.export(root / package)
    sys.path.insert(0, str(root))
    try:
        yield importlib.import_module(f"{package}.autonomy")
    finally:
        sys.path.remove(str(root))
        for name in tuple(sys.modules):
            if name == package or name.startswith(f"{package}."):
                del sys.modules[name]


def principals():
    operations = [
        "goal.create",
        "goal.revise",
        "commitment.propose",
        "commitment.accept",
        "artifact.submit",
        "review.record",
        "adoption.record",
    ]
    actors = ("requester", "provider", "replacement", "reviewer", "reviewer-2", "outsider")
    grants = {
        actor: {"controller": f"controller:{actor}", "operations": list(operations)}
        for actor in actors
    }
    grants["observer"] = {"controller": "controller:observer", "operations": []}
    return grants


def profiles(api):
    return (
        api.OPEN_COLLABORATION_V1,
        api.PEER_COLLABORATION_V1,
        api.CollaborationProfile("test:self", review_mode="self"),
    )


def open_ledger(api, tmp_path, **changes):
    config = {"host_id": "test:host", "principals": principals(), "profiles": profiles(api)}
    config.update(changes)
    return api.CollaborationJournal(tmp_path / "journal.sqlite", **config)


@pytest.fixture
def ledger(api, tmp_path):
    return open_ledger(api, tmp_path)


def snapshot(tmp_path):
    """Include version/impact rows and allocated receipt sequences in rollback checks."""
    with sqlite3.connect(tmp_path / "journal.sqlite") as db:
        return {
            table: db.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall()
            for table in (
                "collaboration_records",
                "collaboration_commands",
                "collaboration_revision_impacts",
                "sqlite_sequence",
            )
        }


def goal_payload(goal_id="goal"):
    return {
        "id": goal_id,
        "intent": {
            "title": "Publish reproducible measurements",
            "description": "Independent local research",
            "domain": "research",
            "success_criteria": "Two agreed checks pass with evidence",
        },
    }


def create_goal(ledger, goal_id="goal", actor="requester"):
    return ledger.apply(actor, f"create:{goal_id}", "goal.create", goal_payload(goal_id))["result"]


def revision_payload(**changes):
    return {
        "goal_id": "goal",
        "base_revision": 1,
        "changes": {"title": "Revise research direction"},
        "reason": "New counterevidence",
        "evidence_ids": ["observation:new"],
        **changes,
    }


def proposal_payload(ident="commitment", **changes):
    return {
        "id": ident,
        "goal_id": "goal",
        "goal_revision": 1,
        "provider_id": "provider",
        "description": "Publish the original measurements",
        "terms": "No fee or data grant",
        "criteria": [
            {"id": "reproducible", "description": "Measurements are reproducible"},
            {"id": "complete", "description": "Include every agreed measurement"},
        ],
        "verifier_ids": ["reviewer"],
        "profile_id": "usmsb:open-collaboration",
        **changes,
    }


def propose(ledger, ident="commitment", **changes):
    return ledger.apply(
        "requester", f"propose:{ident}", "commitment.propose", proposal_payload(ident, **changes)
    )["result"]


def accept(ledger, commitment, actor, command_id=None):
    return ledger.apply(
        actor,
        command_id or f"accept:{commitment['id']}:{actor}",
        "commitment.accept",
        {"commitment_id": commitment["id"], "terms_hash": commitment["terms_hash"]},
    )


def activate(ledger, ident="commitment", **changes):
    commitment = propose(ledger, ident, **changes)
    for actor in commitment["required_parties"]:
        accept(ledger, commitment, actor)
    return ledger.get("commitment", ident)


def artifact_payload(commitment, ident="artifact", **changes):
    descriptor = {
        "id": ident,
        "media_type": "application/json",
        "sha256": "a" * 64,
        "uri": f"urn:artifact:{ident}",
        "size_bytes": 12,
        **changes,
    }
    return {
        "commitment_id": commitment["id"],
        "terms_hash": commitment["terms_hash"],
        "artifact": descriptor,
    }


def submit(ledger, commitment, ident="artifact", **changes):
    return ledger.apply(
        commitment["terms"]["provider_id"],
        f"submit:{ident}",
        "artifact.submit",
        artifact_payload(commitment, ident, **changes),
    )["result"]


def checks(status="pass"):
    return [
        {
            "criterion_id": criterion,
            "status": status,
            "evidence_ids": [f"evidence:{criterion}"],
            "reason": "Attributed local verification",
        }
        for criterion in ("reproducible", "complete")
    ]


def review_payload(commitment, artifact, ident="review", **changes):
    return {
        "id": ident,
        "artifact_id": artifact["id"],
        "artifact_sha256": artifact["descriptor"]["sha256"],
        "terms_hash": commitment["terms_hash"],
        "checks": checks(),
        **changes,
    }


def review(ledger, commitment, artifact, actor="reviewer", **changes):
    ident = changes.pop("ident", f"review:{artifact['id']}:{actor}")
    return ledger.apply(
        actor, ident, "review.record", review_payload(commitment, artifact, ident, **changes)
    )


def adoption_payload(commitment, artifact, **changes):
    return {
        "id": "adoption",
        "artifact_id": artifact["id"],
        "artifact_sha256": artifact["descriptor"]["sha256"],
        "terms_hash": commitment["terms_hash"],
        "evidence_ids": ["usage:local"],
        "statement": "Recipient reports local use, without a causal claim",
        **changes,
    }


def test_goal_revision_preserves_existing_obligations_and_old_acceptance(api, ledger, tmp_path):
    original_goal = create_goal(ledger)
    original_version = ledger.goal_version("goal", 1)
    commitment = activate(ledger)
    artifact = submit(ledger, commitment)
    review_receipt = review(ledger, commitment, artifact)
    pending = propose(ledger, "pending")
    revised = ledger.apply("requester", "revise", "goal.revise", revision_payload())["result"]
    assert revised["obligations_changed"] is False
    assert revised["affected_commitment_ids"] == ["commitment", "pending"]
    assert ledger.get("commitment", "commitment") == commitment
    assert ledger.get("commitment", "pending") == pending
    assert ledger.goal_version("goal", 1) == original_version == original_goal["version"]
    assert ledger.get("review", review_receipt["result"]["id"]) == review_receipt["result"]
    adopted = ledger.apply(
        "requester", "adopt-old", "adoption.record", adoption_payload(commitment, artifact)
    )["result"]
    assert adopted["goal_revision"] == 1
    assert adopted["matches_current_goal_revision"] is False
    assert ledger.get("goal", "goal") == revised["goal"]
    assert open_ledger(api, tmp_path).goal_version("goal", 1) == original_version


@pytest.mark.parametrize(
    "field,value",
    [
        ("owner_id", "outsider"),
        ("id", "stolen"),
        ("revision", 99),
        ("obligations", []),
        ("status", "achieved"),
    ],
)
def test_intent_patch_cannot_rewrite_identity_or_obligations(api, ledger, tmp_path, field, value):
    create_goal(ledger)
    activate(ledger)
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        ledger.apply(
            "requester", "bad-patch", "goal.revise", revision_payload(changes={field: value})
        )
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("actor", ["provider", "outsider", "observer", "unregistered"])
def test_authenticated_actor_cannot_revise_another_owners_goal(api, ledger, tmp_path, actor):
    create_goal(ledger)
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        ledger.apply(actor, "spoof-owner", "goal.revise", revision_payload())
    assert snapshot(tmp_path) == before


def test_business_payload_cannot_supply_authenticated_actor(api, ledger, tmp_path):
    create_goal(ledger)
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        ledger.apply(
            "outsider", "spoof-payload", "goal.revise", revision_payload(actor="requester")
        )
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("base", [1, 0, -1, True, "2", 3])
def test_stale_or_invalid_goal_cas_cannot_append_history(api, ledger, tmp_path, base):
    create_goal(ledger)
    ledger.apply("requester", "revision-2", "goal.revise", revision_payload())
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        ledger.apply("requester", "stale", "goal.revise", revision_payload(base_revision=base))
    assert snapshot(tmp_path) == before
    with pytest.raises(api.ContractError):
        ledger.goal_version("goal", 3)


@pytest.mark.parametrize(
    "mode,shared_party",
    [("independent", "provider"), ("independent", "requester"), ("peer", "provider")],
)
def test_distinct_actor_strings_do_not_prove_controller_independence(
    api, tmp_path, mode, shared_party
):
    grants = principals()
    grants["reviewer"]["controller"] = grants[shared_party]["controller"]
    ledger = open_ledger(api, tmp_path, principals=grants)
    create_goal(ledger)
    profile_id = "usmsb:peer-collaboration" if mode == "peer" else "usmsb:open-collaboration"
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError, match="controller"):
        propose(ledger, profile_id=profile_id)
    assert snapshot(tmp_path) == before


def test_distinct_controllers_can_review_but_unappointed_actor_cannot(api, ledger, tmp_path):
    create_goal(ledger)
    commitment = activate(ledger)
    artifact = submit(ledger, commitment)
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        review(ledger, commitment, artifact, actor="outsider")
    assert snapshot(tmp_path) == before
    assert review(ledger, commitment, artifact)["result"]["passed"] is True


@pytest.mark.parametrize(
    "field,value",
    [("profile_id", "uninstalled:profile"), ("profile_version", 999), ("review_mode", "self")],
)
def test_client_cannot_select_uninstalled_rules_or_silently_weaken_profile(
    api, ledger, tmp_path, field, value
):
    create_goal(ledger)
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        propose(ledger, **{field: value})
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("conflict", ["actor", "payload", "operation"])
def test_command_id_is_bound_to_actor_operation_and_payload_after_restart(
    api, ledger, tmp_path, conflict
):
    payload = goal_payload()
    original = ledger.apply("requester", "shared-command", "goal.create", payload)
    reopened = open_ledger(api, tmp_path)
    before = snapshot(tmp_path)
    actor, operation, changed = "requester", "goal.create", deepcopy(payload)
    if conflict == "actor":
        actor = "outsider"
    elif conflict == "operation":
        operation, changed = "goal.revise", revision_payload()
    else:
        changed["intent"]["title"] = "Different input under the same id"
    with pytest.raises(api.ContractError, match="conflict"):
        reopened.apply(actor, "shared-command", operation, changed)
    assert snapshot(tmp_path) == before
    assert reopened.apply("requester", "shared-command", "goal.create", payload) == original


@pytest.mark.parametrize(
    "operation", ["commitment.accept", "artifact.submit", "review.record", "adoption.record"]
)
def test_every_effect_rejects_a_different_frozen_terms_hash(api, ledger, tmp_path, operation):
    create_goal(ledger)
    commitment = activate(ledger)
    artifact = submit(ledger, commitment)
    review(ledger, commitment, artifact)
    if operation == "commitment.accept":
        commitment = propose(ledger, "pending")
        actor, payload = "provider", {"commitment_id": commitment["id"]}
    elif operation == "artifact.submit":
        actor, payload = "provider", artifact_payload(commitment, "other-artifact")
    elif operation == "review.record":
        fresh = submit(ledger, commitment, "unreviewed")
        actor, payload = "reviewer", review_payload(commitment, fresh, "other-review")
    else:
        actor, payload = "requester", adoption_payload(commitment, artifact)
    payload["terms_hash"] = "0" * 64
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError, match="hash mismatch"):
        ledger.apply(actor, "hash-mismatch", operation, payload)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "operation,actor", [("review.record", "reviewer"), ("adoption.record", "requester")]
)
def test_review_and_adoption_cannot_relabel_artifact_bytes(api, ledger, tmp_path, operation, actor):
    create_goal(ledger)
    commitment = activate(ledger)
    artifact = submit(ledger, commitment)
    if operation == "adoption.record":
        review(ledger, commitment, artifact)
        payload = adoption_payload(commitment, artifact)
    else:
        payload = review_payload(commitment, artifact)
    payload["artifact_sha256"] = "b" * 64
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError, match="hash mismatch"):
        ledger.apply(actor, "wrong-bytes", operation, payload)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("consent", [[], ["requester"], ["provider"]])
def test_proposal_or_one_sided_consent_does_not_authorize_delivery(api, ledger, tmp_path, consent):
    create_goal(ledger)
    commitment = propose(ledger)
    for actor in consent:
        accept(ledger, commitment, actor)
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        submit(ledger, commitment)
    assert snapshot(tmp_path) == before
    assert ledger.get("commitment", commitment["id"])["status"] == "proposed"


def test_consent_and_delivery_cannot_be_supplied_by_an_unagreed_party(api, ledger, tmp_path):
    create_goal(ledger)
    commitment = propose(ledger)
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        accept(ledger, commitment, "outsider")
    assert snapshot(tmp_path) == before
    accept(ledger, commitment, "requester")
    accept(ledger, commitment, "provider")
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        ledger.apply(
            "replacement", "wrong-provider", "artifact.submit", artifact_payload(commitment)
        )
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("verdict", ["missing", "fail", "unknown", "partial"])
def test_adoption_requires_every_agreed_review_to_pass(api, ledger, tmp_path, verdict):
    create_goal(ledger)
    commitment = activate(ledger, verifier_ids=["reviewer", "reviewer-2"])
    artifact = submit(ledger, commitment)
    if verdict != "missing":
        review(ledger, commitment, artifact)
    if verdict in {"fail", "unknown"}:
        review(ledger, commitment, artifact, actor="reviewer-2", checks=checks(verdict))
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        ledger.apply(
            "requester",
            "premature-adopt",
            "adoption.record",
            adoption_payload(commitment, artifact),
        )
    assert snapshot(tmp_path) == before
    assert ledger.get("commitment", commitment["id"])["status"] == "active"


@pytest.mark.parametrize(
    "bad_checks",
    [
        checks()[:1],
        [checks()[0], checks()[0]],
        [{**item, "evidence_ids": []} for item in checks()],
        [{**item, "status": "approved"} for item in checks()],
    ],
)
def test_review_cannot_skip_duplicate_or_pass_criteria_without_evidence(
    api, ledger, tmp_path, bad_checks
):
    create_goal(ledger)
    commitment = activate(ledger)
    artifact = submit(ledger, commitment)
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        review(ledger, commitment, artifact, checks=deepcopy(bad_checks))
    assert snapshot(tmp_path) == before


def test_failed_review_cannot_be_replaced_and_new_artifact_cannot_inherit_it(api, ledger, tmp_path):
    create_goal(ledger)
    commitment = activate(ledger)
    artifact = submit(ledger, commitment)
    failed = review(ledger, commitment, artifact, checks=checks("fail"))
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        review(ledger, commitment, artifact, ident="rewrite-review")
    assert snapshot(tmp_path) == before
    newer = submit(ledger, commitment, "artifact-v2", sha256="b" * 64)
    with pytest.raises(api.ContractError):
        ledger.apply(
            "requester", "reuse-review", "adoption.record", adoption_payload(commitment, newer)
        )
    assert ledger.get("artifact", newer["id"])["reviews"] == {}
    assert ledger.get("review", failed["result"]["id"]) == failed["result"]


@pytest.mark.parametrize("changes,actor", [({"evidence_ids": []}, "requester"), ({}, "outsider")])
def test_adoption_needs_recipient_authority_and_evidence(api, ledger, tmp_path, changes, actor):
    create_goal(ledger)
    commitment = activate(ledger)
    artifact = submit(ledger, commitment)
    review(ledger, commitment, artifact)
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        ledger.apply(
            actor,
            "invalid-adoption",
            "adoption.record",
            adoption_payload(commitment, artifact, **changes),
        )
    assert snapshot(tmp_path) == before


def test_amendment_needs_affected_old_provider_and_cannot_transplant_old_evidence(
    api, ledger, tmp_path
):
    create_goal(ledger)
    original = activate(ledger)
    artifact = submit(ledger, original)
    old_review = review(ledger, original, artifact)
    amendment = propose(
        ledger,
        "amendment",
        supersedes="commitment",
        provider_id="replacement",
        profile_id="test:self",
        verifier_ids=["replacement"],
    )
    assert set(amendment["required_parties"]) == {"requester", "provider", "replacement"}
    accept(ledger, amendment, "requester")
    accept(ledger, amendment, "replacement")
    assert ledger.get("commitment", "commitment") == original
    assert ledger.get("commitment", "amendment")["status"] == "proposed"
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        submit(ledger, amendment, "early-amended-artifact")
    assert snapshot(tmp_path) == before
    accept(ledger, amendment, "provider")
    old = ledger.get("commitment", "commitment")
    assert old["status"] == "superseded" and old["superseded_by"] == "amendment"
    assert old["terms"] == original["terms"] and old["terms_hash"] == original["terms_hash"]
    assert ledger.get("review", old_review["result"]["id"]) == old_review["result"]
    with pytest.raises(api.ContractError):
        ledger.apply(
            "requester",
            "old-evidence-new-terms",
            "adoption.record",
            adoption_payload(amendment, artifact),
        )
    new_artifact = submit(ledger, amendment, "amended-artifact")
    with pytest.raises(api.ContractError):
        ledger.apply(
            "requester",
            "inherit-old-pass",
            "adoption.record",
            adoption_payload(amendment, new_artifact),
        )


@pytest.mark.parametrize("supersedes", [" commitment", "commitment ", "\tcommitment\n"])
def test_amendment_reference_alias_cannot_leave_original_obligation_active(
    api, ledger, tmp_path, supersedes
):
    """Normalization must be identical for looking up and replacing the old row."""
    create_goal(ledger)
    original = activate(ledger)
    before = snapshot(tmp_path)
    try:
        amendment = propose(ledger, "amendment", supersedes=supersedes)
    except api.ContractError:
        # Rejecting an ambiguous spelling before writing is also safe.
        assert snapshot(tmp_path) == before
        return
    for actor in amendment["required_parties"]:
        accept(ledger, amendment, actor)
    assert ledger.get("commitment", "amendment")["status"] == "active"
    old = ledger.get("commitment", original["id"])
    assert old["status"] == "superseded", "Amendment activated without replacing the original row"
    assert old["superseded_by"] == "amendment"
    with sqlite3.connect(tmp_path / "journal.sqlite") as db:
        keys = db.execute("SELECT id FROM collaboration_records WHERE kind='commitment'").fetchall()
    assert sorted(keys) == [("amendment",), ("commitment",)]


def test_completed_commitment_cannot_be_reopened_by_an_amendment(api, ledger, tmp_path):
    create_goal(ledger)
    commitment = activate(ledger)
    artifact = submit(ledger, commitment)
    review(ledger, commitment, artifact)
    ledger.apply("requester", "adopt", "adoption.record", adoption_payload(commitment, artifact))
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        propose(ledger, "reopen", supersedes="commitment")
    assert snapshot(tmp_path) == before


def test_final_amendment_consent_rolls_back_if_old_work_was_adopted(api, ledger, tmp_path):
    create_goal(ledger)
    commitment = activate(ledger)
    artifact = submit(ledger, commitment)
    review(ledger, commitment, artifact)
    amendment = propose(ledger, "amendment", supersedes="commitment")
    accept(ledger, amendment, "requester")
    ledger.apply("requester", "adopt", "adoption.record", adoption_payload(commitment, artifact))
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        accept(ledger, amendment, "provider")
    assert snapshot(tmp_path) == before
    assert ledger.get("commitment", "amendment")["accepted_by"] == ["requester"]


@pytest.mark.parametrize(
    "change",
    [
        "host",
        "controller",
        "capability",
        "add_actor",
        "remove_actor",
        "profile_version",
        "review_mode",
        "media_types",
        "limit",
        "budget",
    ],
)
def test_restart_cannot_silently_change_bound_authority_or_profiles(api, ledger, tmp_path, change):
    receipt = ledger.apply("requester", "create:goal", "goal.create", goal_payload())
    grants, installed, config = principals(), list(profiles(api)), {}
    if change == "host":
        config["host_id"] = "other:host"
    elif change == "controller":
        grants["reviewer"]["controller"] = grants["provider"]["controller"]
    elif change == "capability":
        grants["observer"]["operations"] = ["commitment.accept"]
    elif change == "add_actor":
        grants["new-actor"] = deepcopy(grants["provider"])
    elif change == "remove_actor":
        del grants["outsider"]
    elif change == "profile_version":
        installed[0] = replace(installed[0], version=2)
    elif change == "review_mode":
        installed[0] = replace(installed[0], review_mode="self")
    elif change == "media_types":
        installed[0] = replace(installed[0], media_types=("text/plain",))
    elif change == "limit":
        installed[0] = replace(installed[0], max_criteria=17)
    else:
        config["max_commands"] = 100001
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError, match="migration"):
        open_ledger(api, tmp_path, principals=grants, profiles=installed, **config)
    assert snapshot(tmp_path) == before
    assert (
        open_ledger(api, tmp_path).apply("requester", "create:goal", "goal.create", goal_payload())
        == receipt
    )


def test_mutating_supplied_grants_or_returned_records_cannot_expand_authority(api, tmp_path):
    grants = principals()
    ledger = open_ledger(api, tmp_path, principals=grants)
    create_goal(ledger)
    grants["observer"]["operations"].append("goal.revise")
    grants["observer"]["controller"] = grants["requester"]["controller"]
    detached = ledger.get("goal", "goal")
    detached["owner_id"] = "observer"
    detached["version"]["intent"]["title"] = "Mutated detached result"
    before = snapshot(tmp_path)
    with pytest.raises(api.ContractError):
        ledger.apply("observer", "expanded-grant", "goal.revise", revision_payload())
    assert snapshot(tmp_path) == before
    assert ledger.get("goal", "goal")["owner_id"] == "requester"


def test_failure_after_version_write_rolls_back_history_projection_and_command(
    api, ledger, tmp_path, monkeypatch
):
    create_goal(ledger)
    before = snapshot(tmp_path)
    write = ledger._write

    def fail_after_write(db, kind, record_id, record, **kwargs):
        write(db, kind, record_id, record, **kwargs)
        if kind == "goal":
            raise RuntimeError("Injected projection failure after version and goal writes")

    with monkeypatch.context() as patch:
        patch.setattr(ledger, "_write", fail_after_write)
        with pytest.raises(RuntimeError, match="Injected"):
            ledger.apply("requester", "retry-revision", "goal.revise", revision_payload())
    assert snapshot(tmp_path) == before
    reopened = open_ledger(api, tmp_path)
    with pytest.raises(api.ContractError):
        reopened.goal_version("goal", 2)
    result = reopened.apply("requester", "retry-revision", "goal.revise", revision_payload())
    assert result["sequence"] == 2
    assert result["result"]["goal"]["revision"] == 2


def test_receipt_persistence_failure_rolls_back_successful_handler_and_allows_retry(
    api, ledger, tmp_path
):
    create_goal(ledger)
    commitment = activate(ledger)
    previous_sequence = ledger.events()[-1]["sequence"]
    with sqlite3.connect(tmp_path / "journal.sqlite") as db:
        db.execute(
            "CREATE TRIGGER reject_receipt BEFORE UPDATE OF receipt ON collaboration_commands "
            "BEGIN SELECT RAISE(ABORT, 'injected receipt persistence failure'); END"
        )
    before = snapshot(tmp_path)
    try:
        with pytest.raises(sqlite3.IntegrityError, match="injected receipt"):
            ledger.apply("requester", "retry-revision", "goal.revise", revision_payload())
        assert snapshot(tmp_path) == before
    finally:
        with sqlite3.connect(tmp_path / "journal.sqlite") as db:
            db.execute("DROP TRIGGER reject_receipt")
    reopened = open_ledger(api, tmp_path)
    with pytest.raises(api.ContractError):
        reopened.revision_impacts("goal", 2)
    result = reopened.apply("requester", "retry-revision", "goal.revise", revision_payload())
    assert result["sequence"] == previous_sequence + 1
    assert result["result"]["goal"]["revision"] == 2
    assert reopened.revision_impacts("goal", 2) == {
        "commitment_ids": [commitment["id"]],
        "next_after": None,
    }


def test_amendment_activation_failure_rolls_back_both_commitments(
    api, ledger, tmp_path, monkeypatch
):
    create_goal(ledger)
    activate(ledger)
    amendment = propose(ledger, "amendment", supersedes="commitment")
    accept(ledger, amendment, "requester")
    before = snapshot(tmp_path)
    write = ledger._write

    def fail_after_write(db, kind, record_id, record, **kwargs):
        write(db, kind, record_id, record, **kwargs)
        if kind == "commitment" and record_id == "amendment":
            raise RuntimeError("Injected final amendment write failure")

    with monkeypatch.context() as patch:
        patch.setattr(ledger, "_write", fail_after_write)
        with pytest.raises(RuntimeError, match="Injected"):
            accept(ledger, amendment, "provider")
    assert snapshot(tmp_path) == before
    reopened = open_ledger(api, tmp_path)
    accept(reopened, amendment, "provider")
    assert reopened.get("commitment", "commitment")["status"] == "superseded"
    assert reopened.get("commitment", "amendment")["status"] == "active"


def test_concurrent_goal_cas_has_one_winner_across_separate_journal_instances(
    api, ledger, tmp_path
):
    create_goal(ledger)
    journals = [open_ledger(api, tmp_path) for _ in range(2)]
    barrier = Barrier(2, timeout=10)

    def run(index):
        barrier.wait()
        try:
            return journals[index].apply(
                "requester",
                f"racing-revision:{index}",
                "goal.revise",
                revision_payload(changes={"title": f"direction:{index}"}),
            )
        except api.ContractError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(run, range(2)))
    assert sum(isinstance(outcome, dict) for outcome in outcomes) == 1
    assert sum(isinstance(outcome, api.ContractError) for outcome in outcomes) == 1
    assert len(ledger.events()) == 2
    assert ledger.get("goal", "goal")["revision"] == 2
    with pytest.raises(api.ContractError):
        ledger.goal_version("goal", 3)


@pytest.mark.parametrize("conflicting", [False, True])
def test_concurrent_command_replay_or_collision_never_creates_two_events(
    api, ledger, tmp_path, conflicting
):
    journals = [open_ledger(api, tmp_path) for _ in range(2)]
    barrier = Barrier(2, timeout=10)

    def run(index):
        barrier.wait()
        payload = goal_payload(f"goal-{index}" if conflicting else "goal")
        try:
            return journals[index].apply("requester", "racing-command", "goal.create", payload)
        except api.ContractError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(run, range(2)))
    successes = [outcome for outcome in outcomes if isinstance(outcome, dict)]
    if conflicting:
        assert len(successes) == 1
        assert sum(isinstance(outcome, api.ContractError) for outcome in outcomes) == 1
    else:
        assert len(successes) == 2 and successes[0] == successes[1]
    assert ledger.events() == [successes[0]]
    with sqlite3.connect(tmp_path / "journal.sqlite") as db:
        assert db.execute(
            "SELECT COUNT(*) FROM collaboration_records WHERE kind='goal'"
        ).fetchone() == (1,)


def test_competing_amendments_cannot_both_supersede_the_same_obligation(api, ledger, tmp_path):
    create_goal(ledger)
    activate(ledger)
    amendments = [propose(ledger, f"amendment-{i}", supersedes="commitment") for i in range(2)]
    for amendment in amendments:
        accept(ledger, amendment, "requester")
    journals = [open_ledger(api, tmp_path) for _ in range(2)]
    barrier = Barrier(2, timeout=10)

    def run(index):
        barrier.wait()
        try:
            return accept(journals[index], amendments[index], "provider")
        except api.ContractError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(run, range(2)))
    successes = [outcome for outcome in outcomes if isinstance(outcome, dict)]
    assert len(successes) == 1
    winner = successes[0]["result"]["id"]
    assert ledger.get("commitment", "commitment")["superseded_by"] == winner
    loser = next(amendment["id"] for amendment in amendments if amendment["id"] != winner)
    assert ledger.get("commitment", loser)["status"] == "proposed"
    assert ledger.get("commitment", loser)["accepted_by"] == ["requester"]


def test_command_fingerprint_and_applied_payload_share_one_immutable_snapshot(
    api, ledger, monkeypatch
):
    """A caller mutating its dict while apply waits must not rewrite hashed intent."""
    module = importlib.import_module(f"{api.__name__}.journal")
    original_digest = module.digest
    fingerprinted, continue_apply = Event(), Event()
    original = goal_payload()
    submitted = deepcopy(original)

    def paused_digest(value):
        result = original_digest(value)
        if type(value) is dict and value.get("operation") == "goal.create":
            fingerprinted.set()
            assert continue_apply.wait(10), "Test did not release fingerprint barrier"
        return result

    with monkeypatch.context() as patch:
        patch.setattr(module, "digest", paused_digest)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(
                ledger.apply, "requester", "mutable-input", "goal.create", submitted
            )
            try:
                assert fingerprinted.wait(10), "Command did not reach fingerprint barrier"
                submitted["intent"]["title"] = "Changed after command input was fingerprinted"
            finally:
                continue_apply.set()
            try:
                receipt = future.result(timeout=10)
            except api.ContractError:
                assert ledger.events() == []
                return
    assert receipt["result"]["version"]["intent"] == original["intent"], (
        "Persisted goal differs from the input authenticated by the receipt hash"
    )
    assert ledger.apply("requester", "mutable-input", "goal.create", original) == receipt


@pytest.mark.parametrize("entrypoint", ["remote_status", "artifact.submit"])
def test_unknown_artifact_schema_is_rejected_at_every_ingestion_entrypoint(
    api, ledger, tmp_path, entrypoint
):
    """A valid digest does not make an unsupported descriptor version compatible."""
    artifact = api.artifact_reference("future", "application/json", "a" * 64, "urn:future", 12)
    artifact["schema"] = "usmsb.artifact-reference.v999"
    if entrypoint == "remote_status":
        value = {"state": "completed", "run_ref": "external:1", "output": {"artifacts": [artifact]}}
        with pytest.raises(api.ContractError):
            api.remote_status(value, profile=api.OPEN_COLLABORATION_V1)
    else:
        create_goal(ledger)
        commitment = activate(ledger)
        before = snapshot(tmp_path)
        with pytest.raises(api.ContractError):
            ledger.apply(
                "provider",
                "future-schema",
                "artifact.submit",
                {
                    "commitment_id": commitment["id"],
                    "terms_hash": commitment["terms_hash"],
                    "artifact": artifact,
                },
            )
        assert snapshot(tmp_path) == before


def test_remote_status_returns_the_validated_snapshot_despite_concurrent_mutation(api, monkeypatch):
    """Validating fields and later copying a caller-owned descriptor is a race."""
    module = importlib.import_module(f"{api.__name__}.profiles")
    validate = module.artifact_reference
    validated, continue_validation = Event(), Event()
    artifact = api.artifact_reference(
        "candidate", "application/json", "a" * 64, "urn:candidate", 12
    )
    original = deepcopy(artifact)
    value = {"state": "completed", "run_ref": "external:1", "output": {"artifacts": [artifact]}}

    def paused_validation(*args, **kwargs):
        result = validate(*args, **kwargs)
        validated.set()
        assert continue_validation.wait(10), "Test did not release descriptor validation"
        return result

    with monkeypatch.context() as patch:
        patch.setattr(module, "artifact_reference", paused_validation)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(api.remote_status, value, profile=api.OPEN_COLLABORATION_V1)
            try:
                assert validated.wait(10), "Remote descriptor did not reach validation barrier"
                artifact["sha256"] = "not-a-digest"
            finally:
                continue_validation.set()
            try:
                result = future.result(timeout=10)
            except api.ContractError:
                return  # Detecting mutation and failing closed is also safe.
    assert result["output"]["artifacts"] == [original], (
        "remote_status returned bytes metadata that its validator never accepted"
    )


@pytest.mark.parametrize("count,id_width", [(1025, 12), (800, 180)])
def test_legal_pending_commitment_fanout_cannot_permanently_block_owner_revision(
    api, ledger, tmp_path, count, id_width
):
    """Large impact snapshots are complete, restartable and independent of live state."""
    create_goal(ledger)
    original_version = ledger.goal_version("goal", 1)
    accepted_ids = []
    for index in range(count):
        commitment = ledger.apply(
            "requester",
            f"propose-many:{index}",
            "commitment.propose",
            proposal_payload(f"pending:{index}".ljust(id_width, "x")),
        )["result"]
        accepted_ids.append(commitment["id"])
    expected_ids = sorted(accepted_ids)
    assert len(expected_ids) == count
    receipt = ledger.apply("requester", "revise-many", "goal.revise", revision_payload())
    result = receipt["result"]
    assert result["goal"]["revision"] == 2
    assert result["obligations_changed"] is False
    assert result["affected_commitment_count"] == count
    assert result["affected_commitment_ids"] == expected_ids[:32]
    assert result["affected_next_after"] == expected_ids[31]
    assert ledger.goal_version("goal", 1) == original_version
    for ident in (accepted_ids[0], accepted_ids[-1]):
        commitment = ledger.get("commitment", ident)
        assert commitment["status"] == "proposed"
        assert commitment["terms"]["goal_revision"] == 1

    first_page = ledger.revision_impacts("goal", 2)
    assert first_page == {
        "commitment_ids": result["affected_commitment_ids"],
        "next_after": result["affected_next_after"],
    }

    def read_pages(journal, revision, expected, limit=32):
        cursor, pages, all_ids = None, [], []
        # A bounded loop exposes repeating cursors without hanging the test.
        for start in range(0, len(expected), limit):
            page = journal.revision_impacts("goal", revision, after=cursor, limit=limit)
            chunk = expected[start : start + limit]
            assert page["commitment_ids"] == chunk
            assert page["next_after"] == (chunk[-1] if start + limit < len(expected) else None)
            all_ids.extend(page["commitment_ids"])
            pages.append(page)
            cursor = page["next_after"]
        assert all_ids == expected and len(set(all_ids)) == len(expected)
        assert cursor is None
        assert journal.revision_impacts("goal", revision, after=expected[-1], limit=limit) == {
            "commitment_ids": [],
            "next_after": None,
        }
        return pages

    # Resume directly from the receipt cursor in a separate instance with a new page size.
    reopened = open_ledger(api, tmp_path)
    assert reopened.revision_impacts("goal", 2, after=result["affected_next_after"], limit=17) == {
        "commitment_ids": expected_ids[32:49],
        "next_after": expected_ids[48],
    }
    saved_pages = read_pages(reopened, 2, expected_ids)
    assert saved_pages[0] == first_page
    assert reopened.apply("requester", "revise-many", "goal.revise", revision_payload()) == receipt
    assert reopened.revision_impacts("goal", 1) == {"commitment_ids": [], "next_after": None}

    detached = reopened.revision_impacts("goal", 2)
    detached["commitment_ids"].clear()
    detached["next_after"] = "tampered-cursor"
    assert reopened.revision_impacts("goal", 2) == first_page

    # Change live membership of the impact set: finish an old commitment and add a new one.
    old = reopened.get("commitment", expected_ids[0])
    for actor in old["required_parties"]:
        accept(reopened, old, actor, command_id=f"finish-saved:{actor}")
    artifact = submit(reopened, old, "saved-impact-artifact")
    review(reopened, old, artifact)
    reopened.apply("requester", "adopt-saved", "adoption.record", adoption_payload(old, artifact))
    later = propose(reopened, "added-after-revision", goal_revision=2)
    next_revision = reopened.apply(
        "requester", "revise-again", "goal.revise", revision_payload(base_revision=2)
    )["result"]
    next_ids = sorted((set(expected_ids) - {old["id"]}) | {later["id"]})
    assert next_revision["affected_commitment_count"] == len(next_ids)
    assert next_revision["affected_commitment_ids"] == next_ids[:32]

    # The same revision number for a different goal must not leak into these pages.
    create_goal(reopened, "other-goal")
    foreign = propose(reopened, "foreign-pending", goal_id="other-goal")
    reopened.apply(
        "requester", "revise-other", "goal.revise", revision_payload(goal_id="other-goal")
    )

    restarted = open_ledger(api, tmp_path)
    before_reads = snapshot(tmp_path)
    assert read_pages(restarted, 2, expected_ids) == saved_pages
    read_pages(restarted, 2, expected_ids, limit=17)
    read_pages(restarted, 3, next_ids)
    assert restarted.revision_impacts("other-goal", 2) == {
        "commitment_ids": [foreign["id"]],
        "next_after": None,
    }
    assert restarted.apply("requester", "revise-many", "goal.revise", revision_payload()) == receipt
    for invalid_limit in (0, 33, True):
        with pytest.raises(api.ContractError):
            restarted.revision_impacts("goal", 2, limit=invalid_limit)
    with pytest.raises(api.ContractError):
        restarted.revision_impacts("goal", 999)
    assert snapshot(tmp_path) == before_reads
