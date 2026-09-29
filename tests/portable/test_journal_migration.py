"""Real SQLite migration, backup, fencing and host replay checks; no services."""

import hashlib
import importlib
import importlib.util
import json
import shutil
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from threading import Barrier, Event
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def api(tmp_path_factory):
    script = Path(__file__).resolve().parents[2] / "scripts/export_autonomy.py"
    spec = importlib.util.spec_from_file_location("export_migration_tests", script)
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    # Parent owns the export list. Exercise the real file in the portable package
    # even while that independent integration change is still being prepared.
    exporter.FILES["autonomy/migration.py"] = "src/usmsb_sdk/autonomy/migration.py"
    root = tmp_path_factory.mktemp("journal_migration")
    package = "portable_journal_migration"
    exporter.export(root / package)
    sys.path.insert(0, str(root))
    try:
        yield SimpleNamespace(
            journal=importlib.import_module(f"{package}.autonomy.journal"),
            migration=importlib.import_module(f"{package}.autonomy.migration"),
            profiles=importlib.import_module(f"{package}.autonomy.profiles"),
            ContractError=importlib.import_module(f"{package}.autonomy.contracts").ContractError,
        )
    finally:
        sys.path.remove(str(root))
        for name in tuple(sys.modules):
            if name == package or name.startswith(package + "."):
                del sys.modules[name]


def principals(api):
    grants = {
        actor: {"controller": f"controller:{actor}", "operations": sorted(api.journal.OPERATIONS)}
        for actor in ("requester", "provider", "reviewer")
    }
    grants["observer"] = {"controller": "controller:observer", "operations": []}
    grants["alias"] = {"controller": "controller:observer", "operations": []}
    return grants


def open_ledger(api, path, configuration=None, **changes):
    if configuration is None:
        return api.journal.CollaborationJournal(
            path, **{"host_id": "host:研究", "principals": principals(api), **changes}
        )
    config = deepcopy(configuration)
    config["profiles"] = [
        api.profiles.CollaborationProfile(**{**record, "media_types": tuple(record["media_types"])})
        for record in config["profiles"].values()
    ]
    return api.journal.CollaborationJournal(path, **config)


@pytest.fixture
def ledger(api, tmp_path):
    return open_ledger(api, tmp_path / "journal.sqlite")


def goal_payload(ident="goal"):
    return {
        "id": ident,
        "intent": {
            "title": "Local measurement",
            "description": "Record reproducible observations",
            "domain": "research",
            "success_criteria": "Agreed check passes",
        },
    }


def seed(ledger):
    ledger.apply("requester", "goal", "goal.create", goal_payload())
    proposal = {
        "id": "commitment",
        "goal_id": "goal",
        "goal_revision": 1,
        "provider_id": "provider",
        "description": "Publish observations",
        "terms": "No fee or execution grant",
        "criteria": [{"id": "check", "description": "Reproducible"}],
        "verifier_ids": ["reviewer"],
        "profile_id": "usmsb:open-collaboration",
    }
    terms = ledger.apply("requester", "propose", "commitment.propose", proposal)["result"]
    for actor in ("requester", "provider"):
        ledger.apply(
            actor,
            "accept:" + actor,
            "commitment.accept",
            {
                "commitment_id": "commitment",
                "terms_hash": terms["terms_hash"],
            },
        )
    ledger.apply(
        "provider",
        "submit",
        "artifact.submit",
        {
            "commitment_id": "commitment",
            "terms_hash": terms["terms_hash"],
            "artifact": {
                "id": "artifact",
                "media_type": "text/plain",
                "sha256": "a" * 64,
                "uri": "urn:local:artifact",
                "size_bytes": 1,
            },
        },
    )
    ledger.apply(
        "reviewer",
        "review",
        "review.record",
        {
            "id": "review",
            "artifact_id": "artifact",
            "artifact_sha256": "a" * 64,
            "terms_hash": terms["terms_hash"],
            "checks": [
                {
                    "criterion_id": "check",
                    "status": "pass",
                    "evidence_ids": ["evidence:1"],
                    "reason": "Attributed check",
                }
            ],
        },
    )
    ledger.apply(
        "requester",
        "revise",
        "goal.revise",
        {
            "goal_id": "goal",
            "base_revision": 1,
            "changes": {"title": "Revised intent"},
            "reason": "New observations",
            "evidence_ids": ["evidence:2"],
        },
    )
    return terms


def snapshot(path):
    with sqlite3.connect(path) as db:
        names = [
            row[0]
            for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        ]
        return {
            name: db.execute(
                'SELECT * FROM "' + name.replace('"', '""') + '" ORDER BY rowid'
            ).fetchall()
            for name in names
        }


def proposal(api, ledger, **changes):
    config = ledger.configuration()
    config["max_commands"] += 1
    return {
        "migration_id": "migration:1",
        "expected_config_hash": api.migration.configuration_hash(ledger.configuration()),
        "new_configuration": config,
        "reason": "Host-approved capacity growth",
        "evidence_ids": ["approval:host-case-1"],
        "verify_approval": lambda controller, request: True,
        "backup_path": Path(ledger._store.path).parent / "before.sqlite",
        **changes,
    }


def migrate(api, ledger, **changes):
    return api.migration.migrate_journal(ledger, **proposal(api, ledger, **changes))


def test_configuration_is_complete_detached_and_uses_real_scope_encoding(api, ledger):
    expected = ledger.configuration()
    mutable = ledger.configuration()
    mutable["principals"]["requester"]["operations"].clear()
    mutable["profiles"]["usmsb:open-collaboration"]["media_types"].append("text/plain")
    mutable["max_commands"] = 1
    assert ledger.configuration() == expected
    with sqlite3.connect(ledger._store.path) as db:
        binding = db.execute(
            "SELECT binding FROM evolution_scopes WHERE name=?", (api.journal.JOURNAL_SCOPE,)
        ).fetchone()[0]
    assert json.loads(binding) == expected
    assert (
        api.migration.configuration_hash(expected) == hashlib.sha256(binding.encode()).hexdigest()
    )
    assert api.journal.digest(expected) != api.migration.configuration_hash(expected)


@pytest.mark.parametrize("mode", ["DELETE", "WAL"])
def test_additive_migration_preserves_all_old_rows_backup_and_frozen_terms(api, ledger, mode):
    with sqlite3.connect(ledger._store.path) as db:
        assert db.execute("PRAGMA journal_mode=" + mode).fetchone()[0].upper() == mode
    # Hold a WAL reader open so the backup must include committed WAL content.
    reader = sqlite3.connect(ledger._store.path)
    try:
        reader.execute("SELECT count(*) FROM evolution_scopes").fetchone()
        old = ledger.configuration()
        original_terms = seed(ledger)
        original_receipts = ledger.events()
        before = snapshot(ledger._store.path)
        new = deepcopy(old)
        new["principals"]["new-actor"] = {
            "controller": "controller:new",
            "operations": ["goal.create"],
        }
        fresh_profile = api.profiles.CollaborationProfile("new:profile", review_mode="self")
        new["profiles"][fresh_profile.id] = fresh_profile.record()
        new["max_commands"] += 10
        approvals = []

        def approve(controller, request):
            approvals.append((controller, deepcopy(request)))
            assert request["old_config_hash"] == api.migration.configuration_hash(old)
            assert request["new_config_hash"] == api.migration.configuration_hash(new)
            assert request["reason"] == "Host-approved capacity growth"
            assert request["evidence_ids"] == ["approval:host-case-1"]
            return True

        event = migrate(api, ledger, new_configuration=new, verify_approval=approve)
        assert [controller for controller, _ in approvals] == sorted(
            {grant["controller"] for grant in old["principals"].values()}
        )
        assert "controller:new" not in event["approved_controllers"]
        backup = Path(event["backup"]["path"])
        assert hashlib.sha256(backup.read_bytes()).hexdigest() == event["backup"]["sha256"]
        assert snapshot(backup) == before
        after = snapshot(ledger._store.path)
        for table, rows in before.items():
            if table not in {"evolution_scopes", "sqlite_sequence"}:
                assert after[table] == rows
        assert dict(after["sqlite_sequence"])["collaboration_commands"] == 7
        assert api.migration.migration_events(ledger) == [event]
        reopened = open_ledger(api, ledger._store.path, new)
        assert reopened.configuration() == new
        assert reopened.get("commitment", "commitment")["terms"] == original_terms["terms"]
        assert (
            reopened.get("commitment", "commitment")["terms_hash"] == original_terms["terms_hash"]
        )
        assert (
            reopened.receipt("requester", "goal", "goal.create", goal_payload())
            == ledger.events()[0]
        )
        # New capabilities only apply to their new actor.
        reopened.apply("new-actor", "new-goal", "goal.create", goal_payload("new-goal"))
        with pytest.raises(api.ContractError, match="Capability denied"):
            reopened.apply("observer", "blocked", "goal.create", goal_payload("blocked"))
        # Restore into a different file, never overwrite the live ledger or backup.
        restored_path = backup.parent / "restored.sqlite"
        shutil.copyfile(backup, restored_path)
        restored = open_ledger(api, restored_path, old)
        assert snapshot(restored_path) == before
        assert restored.events() == original_receipts
        assert restored.goal_version("goal", 1) == ledger.goal_version("goal", 1)
        assert restored.revision_impacts("goal", 2) == ledger.revision_impacts("goal", 2)
        assert api.migration.migration_events(restored) == []
        with pytest.raises(api.ContractError, match="explicit migration"):
            open_ledger(api, restored_path, new)
    finally:
        reader.close()


@pytest.mark.parametrize(
    "change",
    [
        "remove_actor",
        "controller",
        "revoke",
        "escalate",
        "host",
        "budget",
        "remove_profile",
        "version",
        "review_mode",
        "media_types",
        "max_criteria",
        "max_steps",
        "legacy",
        "noop",
    ],
)
def test_nonadditive_changes_fail_without_callback_backup_or_mutation(api, ledger, change):
    seed(ledger)
    before = snapshot(ledger._store.path)
    config = ledger.configuration()
    profile = config["profiles"]["usmsb:open-collaboration"]
    if change == "remove_actor":
        del config["principals"]["observer"]
    elif change == "controller":
        config["principals"]["requester"]["controller"] = "controller:other"
    elif change == "revoke":
        config["principals"]["requester"]["operations"].remove("goal.create")
    elif change == "escalate":
        config["principals"]["observer"]["operations"] = ["goal.create"]
    elif change == "host":
        config["host_id"] = "other:host"
    elif change == "budget":
        config["max_commands"] -= 1
    elif change == "remove_profile":
        config["profiles"] = {"replacement": {**profile, "id": "replacement"}}
    elif change in {"version", "max_criteria", "max_steps"}:
        profile[change] += 1
    elif change == "review_mode":
        profile[change] = "self"
    elif change == "media_types":
        profile[change] = ["text/plain"]
    elif change == "legacy":
        profile[change] = True
    called = []
    with pytest.raises(api.ContractError, match="separate governance case|additive configuration"):
        migrate(
            api, ledger, new_configuration=config, verify_approval=lambda *args: called.append(args)
        )
    assert not called
    assert snapshot(ledger._store.path) == before
    assert not (Path(ledger._store.path).parent / "before.sqlite").exists()


@pytest.mark.parametrize(
    "change",
    [
        "unknown_field",
        "unknown_grant",
        "unknown_operation",
        "profile_extra",
        "profile_id",
        "profile_boolean_version",
        "profile_missing_field",
        "budget_bool",
        "budget_upper",
        "budget_lower",
        "uncanonical_operations",
        "uncanonical_controller",
        "too_many_profiles",
    ],
)
def test_malformed_complete_config_is_rejected(api, ledger, change):
    config = proposal(api, ledger)["new_configuration"]
    actor = config["principals"]["requester"]
    profile = config["profiles"]["usmsb:open-collaboration"]
    if change == "unknown_field":
        config["execution"] = True
    elif change == "unknown_grant":
        actor["funds"] = 100
    elif change == "unknown_operation":
        actor["operations"].append("execution.run")
    elif change == "profile_extra":
        profile["execute"] = True
    elif change == "profile_id":
        profile["id"] = "different"
    elif change == "profile_boolean_version":
        profile["version"] = True
    elif change == "profile_missing_field":
        del profile["legacy"]
    elif change.startswith("budget"):
        config["max_commands"] = {"budget_bool": True, "budget_upper": 1000001, "budget_lower": 0}[
            change
        ]
    elif change == "uncanonical_operations":
        actor["operations"].reverse()
    elif change == "uncanonical_controller":
        actor["controller"] += " "
    elif change == "too_many_profiles":
        config["profiles"].update({str(i): {**profile, "id": str(i)} for i in range(32)})
    before = snapshot(ledger._store.path)
    with pytest.raises(api.ContractError):
        migrate(api, ledger, new_configuration=config)
    assert snapshot(ledger._store.path) == before


@pytest.mark.parametrize("answer", [False, None, 0, 1, "true", [], {"approved": True}])
def test_every_old_controller_must_return_strict_true(api, ledger, answer):
    calls = []

    def verify(controller, request):
        calls.append(controller)
        # Include a controller with no operation permissions in required consent.
        return answer if controller == "controller:observer" else True

    before = snapshot(ledger._store.path)
    with pytest.raises(api.ContractError, match="exact approval"):
        migrate(api, ledger, verify_approval=verify)
    assert calls == ["controller:observer"]
    assert snapshot(ledger._store.path) == before
    assert not (Path(ledger._store.path).parent / "before.sqlite").exists()


@pytest.mark.parametrize(
    "changed", ["old_config_hash", "new_config_hash", "reason", "evidence_ids"]
)
def test_approval_for_any_other_request_is_not_accepted(api, ledger, changed):
    args = proposal(api, ledger)
    signed = {
        "old_config_hash": args["expected_config_hash"],
        "new_config_hash": api.migration.configuration_hash(args["new_configuration"]),
        "reason": args["reason"],
        "evidence_ids": args["evidence_ids"],
    }
    signed[changed] = ["other:evidence"] if changed == "evidence_ids" else "other"
    args["verify_approval"] = lambda controller, request: all(
        request[k] == v for k, v in signed.items()
    )
    before = snapshot(ledger._store.path)
    with pytest.raises(api.ContractError, match="exact approval"):
        api.migration.migrate_journal(ledger, **args)
    assert snapshot(ledger._store.path) == before


def test_callback_exception_and_missing_verifier_fail_closed(api, ledger):
    before = snapshot(ledger._store.path)

    def crash(*args):
        raise RuntimeError("Host approval service unavailable")

    for verifier, error in ((None, api.ContractError), (crash, RuntimeError)):
        with pytest.raises(error):
            migrate(api, ledger, verify_approval=verifier)
        assert snapshot(ledger._store.path) == before


def test_callback_mutation_cannot_rewrite_approved_config_reason_or_evidence(api, ledger):
    args = proposal(api, ledger)
    original = deepcopy(args["new_configuration"])
    seen = []

    def verify(controller, request):
        seen.append(deepcopy(request))
        request["reason"] = "Changed by callback"
        request["evidence_ids"].clear()
        request["required_controllers"].clear()
        args["new_configuration"]["principals"]["requester"]["controller"] = "rewritten"
        args["evidence_ids"].clear()
        return True

    args["verify_approval"] = verify
    event = api.migration.migrate_journal(ledger, **args)
    assert len(seen) == 4 and all(request == seen[0] for request in seen)
    assert event["reason"] == "Host-approved capacity growth"
    assert event["evidence_ids"] == ["approval:host-case-1"]
    assert event["new_configuration"] == original
    assert open_ledger(api, ledger._store.path, original).configuration() == original


@pytest.mark.parametrize(
    "field,value",
    [
        ("reason", ""),
        ("reason", " reason "),
        ("evidence_ids", []),
        ("evidence_ids", ["a", "a"]),
        ("evidence_ids", [" a"]),
        ("migration_id", ""),
        ("migration_id", " case "),
        ("expected_config_hash", "0" * 64),
    ],
)
def test_invalid_request_does_not_modify_ledger(api, ledger, field, value):
    before = snapshot(ledger._store.path)
    with pytest.raises(api.ContractError):
        migrate(api, ledger, **{field: value})
    assert snapshot(ledger._store.path) == before


@pytest.mark.parametrize("existing", [b"", b"precious backup bytes"])
def test_backup_never_overwrites_even_empty_existing_file(api, ledger, existing):
    path = Path(ledger._store.path).parent / "before.sqlite"
    path.write_bytes(existing)
    before = snapshot(ledger._store.path)
    with pytest.raises(FileExistsError):
        migrate(api, ledger, backup_path=path)
    assert path.read_bytes() == existing
    assert snapshot(ledger._store.path) == before


@pytest.mark.parametrize("suffix", ["", "-wal", "-shm", "-journal"])
def test_backup_rejects_live_database_and_its_sidecars(api, ledger, suffix):
    before = snapshot(ledger._store.path)
    with pytest.raises(api.ContractError, match="journal or sidecar"):
        migrate(api, ledger, backup_path=ledger._store.path + suffix)
    assert snapshot(ledger._store.path) == before


@pytest.mark.parametrize("kind", ["sidecar", "hardlink", "directory", "missing_parent"])
def test_unsafe_backup_destination_cannot_change_ledger(api, ledger, kind):
    path = Path(ledger._store.path).parent / "before.sqlite"
    if kind == "sidecar":
        Path(str(path) + "-wal").write_bytes(b"existing sidecar")
    elif kind == "hardlink":
        path.hardlink_to(ledger._store.path)
    elif kind == "directory":
        path.mkdir()
    else:
        path = path / "missing" / "backup.sqlite"
    before = snapshot(ledger._store.path)
    with pytest.raises((api.ContractError, OSError)):
        migrate(api, ledger, backup_path=path)
    assert snapshot(ledger._store.path) == before
    if kind == "sidecar":
        assert Path(str(path) + "-wal").read_bytes() == b"existing sidecar"


def test_backup_failure_keeps_original_binding_and_no_audit(api, ledger, monkeypatch):
    before = snapshot(ledger._store.path)

    def fail(*args):
        raise OSError("Storage unavailable")

    monkeypatch.setattr(api.migration, "_backup", fail)
    with pytest.raises(OSError):
        migrate(api, ledger)
    assert snapshot(ledger._store.path) == before
    assert api.migration.migration_events(ledger) == []


def test_backup_fsync_failure_aborts_and_retains_exclusive_backup(api, ledger, monkeypatch):
    seed(ledger)
    before = snapshot(ledger._store.path)

    def fail(fd):
        raise OSError("Backup fsync failed")

    with monkeypatch.context() as patch:
        patch.setattr(api.migration.os, "fsync", fail)
        with pytest.raises(OSError, match="fsync failed"):
            migrate(api, ledger)
    backup = Path(ledger._store.path).parent / "before.sqlite"
    assert snapshot(ledger._store.path) == before
    assert snapshot(backup) == before
    saved = backup.read_bytes()
    with pytest.raises(FileExistsError):
        migrate(api, ledger)
    assert backup.read_bytes() == saved


@pytest.mark.parametrize(
    "controller",
    [
        "controller:observer",
        "controller:provider",
        "controller:requester",
        "controller:reviewer",
    ],
)
def test_denial_by_any_old_controller_including_the_last_aborts(api, ledger, controller):
    calls = []

    def verify(ident, request):
        calls.append(ident)
        return ident != controller

    before = snapshot(ledger._store.path)
    with pytest.raises(api.ContractError, match="exact approval"):
        migrate(api, ledger, verify_approval=verify)
    assert calls[-1] == controller
    assert snapshot(ledger._store.path) == before
    assert not (Path(ledger._store.path).parent / "before.sqlite").exists()


@pytest.mark.parametrize("addition", ["actor", "profile"])
def test_each_additive_change_can_stand_alone_without_budget_growth(api, ledger, addition):
    seed(ledger)
    config = ledger.configuration()
    if addition == "actor":
        # A new actor may share a controller; this does not create independence.
        config["principals"]["provider-alias"] = {
            "controller": "controller:provider",
            "operations": ["review.record"],
        }
    else:
        profile = api.profiles.CollaborationProfile("profile:second", version=2)
        config["profiles"][profile.id] = profile.record()
    event = migrate(api, ledger, new_configuration=config)
    current = open_ledger(api, ledger._store.path, config)
    assert current.configuration()["max_commands"] == event["old_configuration"]["max_commands"]
    if addition == "actor":
        with pytest.raises(api.ContractError, match="distinct controller"):
            current.apply(
                "requester",
                "sybil",
                "commitment.propose",
                {
                    "id": "sybil",
                    "goal_id": "goal",
                    "goal_revision": 2,
                    "provider_id": "provider",
                    "description": "Attempt self verification",
                    "terms": "No grant",
                    "criteria": [{"id": "c", "description": "Check"}],
                    "verifier_ids": ["provider-alias"],
                    "profile_id": "usmsb:open-collaboration",
                },
            )
    # An old active obligation remains usable under its original profile and terms.
    commitment = current.get("commitment", "commitment")
    adoption = current.apply(
        "requester",
        "adopt",
        "adoption.record",
        {
            "id": "adoption",
            "artifact_id": "artifact",
            "artifact_sha256": "a" * 64,
            "terms_hash": commitment["terms_hash"],
            "evidence_ids": ["use:1"],
            "statement": "Recipient reports use",
        },
    )
    assert adoption["result"]["goal_revision"] == 1
    assert current.get("commitment", "commitment")["terms"] == commitment["terms"]


def test_large_installed_configuration_uses_scope_limits_not_command_json_limits(api, tmp_path):
    grants = principals(api)
    grants.update(
        {
            f"observer:{index}": {"controller": "controller:observer", "operations": []}
            for index in range(1025)
        }
    )
    ledger = open_ledger(api, tmp_path / "journal.sqlite", principals=grants)
    before = ledger.configuration()
    event = migrate(api, ledger)
    assert event["old_config_hash"] == api.migration.configuration_hash(before)
    current = open_ledger(api, ledger._store.path, event["new_configuration"])
    assert current.configuration()["principals"] == before["principals"]


def test_cas_failure_keeps_backup_but_rolls_back_binding_and_audit(api, ledger):
    with sqlite3.connect(ledger._store.path) as db:
        db.execute(
            "CREATE TRIGGER reject_cas BEFORE UPDATE ON evolution_scopes "
            "BEGIN SELECT RAISE(IGNORE); END"
        )
    before = snapshot(ledger._store.path)
    with pytest.raises(api.ContractError, match="CAS failed"):
        migrate(api, ledger)
    assert snapshot(ledger._store.path) == before
    assert snapshot(Path(ledger._store.path).parent / "before.sqlite") == before


@pytest.mark.parametrize("failure", ["ABORT, 'audit unavailable'", "IGNORE"])
def test_audit_failure_rolls_back_cas_and_retains_pre_migration_backup(api, ledger, failure):
    first = migrate(api, ledger)
    current = open_ledger(api, ledger._store.path, first["new_configuration"])
    with sqlite3.connect(ledger._store.path) as db:
        db.execute(
            "CREATE TRIGGER reject_audit BEFORE INSERT ON collaboration_migrations "
            f"BEGIN SELECT RAISE({failure}); END"
        )
    before = snapshot(ledger._store.path)
    backup = Path(ledger._store.path).parent / "second.sqlite"
    with pytest.raises((sqlite3.IntegrityError, api.ContractError), match="audit"):
        migrate(api, current, migration_id="migration:2", backup_path=backup)
    assert snapshot(ledger._store.path) == before
    assert snapshot(backup) == before
    assert current.configuration() == first["new_configuration"]
    assert api.migration.migration_events(current) == [first]


def test_competing_migrations_have_one_cas_winner_and_one_backup(api, ledger):
    path = Path(ledger._store.path)
    other = open_ledger(api, path)
    barrier = Barrier(2, timeout=10)
    args = [
        proposal(
            api,
            journal,
            migration_id=f"migration:{i}",
            backup_path=path.parent / f"backup-{i}.sqlite",
        )
        for i, journal in enumerate((ledger, other))
    ]
    args[1]["new_configuration"]["max_commands"] += 1

    def run(i):
        barrier.wait()
        try:
            return api.migration.migrate_journal((ledger, other)[i], **args[i])
        except api.ContractError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(run, range(2)))
    successes = [value for value in outcomes if isinstance(value, dict)]
    assert len(successes) == 1
    assert sum((path.parent / f"backup-{i}.sqlite").exists() for i in range(2)) == 1
    assert api.migration.migration_events(ledger) == successes
    assert (
        open_ledger(api, path, successes[0]["new_configuration"]).configuration()
        == successes[0]["new_configuration"]
    )


def test_old_instances_replay_queries_and_old_constructor_are_fenced(api, ledger):
    ledger.apply("requester", "goal", "goal.create", goal_payload())
    other = open_ledger(api, ledger._store.path)
    old = ledger.configuration()
    event = migrate(api, ledger)
    before = snapshot(ledger._store.path)
    for instance in (ledger, other):
        with pytest.raises(api.ContractError, match="fence"):
            instance.apply("requester", "later", "goal.create", goal_payload("later"))
        with pytest.raises(api.ContractError, match="fence"):
            instance.apply("requester", "goal", "goal.create", goal_payload())
        with pytest.raises(api.ContractError, match="fence"):
            instance.receipt("requester", "goal", "goal.create", goal_payload())
        with pytest.raises(api.ContractError, match="fence"):
            instance.configuration()
    with pytest.raises(api.ContractError, match="explicit migration"):
        open_ledger(api, ledger._store.path, old)
    assert snapshot(ledger._store.path) == before
    fresh = open_ledger(api, ledger._store.path, event["new_configuration"])
    assert fresh.receipt("requester", "goal", "goal.create", goal_payload()) == ledger.events()[0]


def test_apply_waiting_before_transaction_cannot_bypass_migration_fence(api, ledger, monkeypatch):
    entered, release = Event(), Event()
    original = api.journal.digest

    def pause(value):
        result = original(value)
        if value.get("operation") == "goal.create":
            entered.set()
            assert release.wait(10)
        return result

    monkeypatch.setattr(api.journal, "digest", pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(ledger.apply, "requester", "waiting", "goal.create", goal_payload())
        try:
            assert entered.wait(10)
            migrate(api, ledger)
        finally:
            release.set()
        with pytest.raises(api.ContractError, match="fence"):
            pending.result(timeout=10)
    assert ledger.events() == []


def test_separate_preexisting_python_process_is_fenced_after_migration(api, ledger):
    ledger.apply("requester", "goal", "goal.create", goal_payload())
    old = ledger.configuration()
    code = """
import importlib, json, sys
sys.path.insert(0, sys.argv[1])
journal = importlib.import_module(sys.argv[2] + '.journal')
profiles = importlib.import_module(sys.argv[2] + '.profiles')
config = json.loads(sys.argv[4])
config['profiles'] = [profiles.CollaborationProfile(
    **{**record, 'media_types': tuple(record['media_types'])})
    for record in config['profiles'].values()]
ledger = journal.CollaborationJournal(sys.argv[3], **config)
payload = json.loads(sys.argv[5])
print('ready', flush=True)
sys.stdin.readline()
errors = []
for action in (
    lambda: ledger.apply('requester', 'child-new', 'goal.create', {**payload, 'id': 'child'}),
    lambda: ledger.apply('requester', 'goal', 'goal.create', payload),
    lambda: ledger.receipt('requester', 'goal', 'goal.create', payload),
    ledger.configuration,
):
    try:
        action()
        errors.append('NOT FENCED')
    except journal.ContractError as exc:
        errors.append(str(exc))
print(json.dumps(errors), flush=True)
"""
    command = [
        sys.executable,
        "-E",
        "-B",
        "-c",
        code,
        str(Path(api.journal.__file__).parents[2]),
        api.journal.__package__,
        ledger._store.path,
        json.dumps(old),
        json.dumps(goal_payload()),
    ]
    with subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    ) as child:
        with ThreadPoolExecutor(max_workers=1) as pool:
            try:
                assert pool.submit(child.stdout.readline).result(timeout=10) == "ready\n"
                migrate(api, ledger)
                before = snapshot(ledger._store.path)
                output, errors = child.communicate("continue\n", timeout=10)
                assert child.returncode == 0, errors
                results = json.loads(output)
                assert len(results) == 4 and all("fence" in error for error in results)
                assert snapshot(ledger._store.path) == before
            finally:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=10)


def test_writer_committed_before_migration_is_in_backup(api, ledger, monkeypatch):
    entered, release = Event(), Event()
    transaction = ledger._store.transaction

    @contextmanager
    def pause():
        with transaction() as db:
            entered.set()
            assert release.wait(10)
            yield db

    other = open_ledger(api, ledger._store.path)
    args = proposal(api, other)
    monkeypatch.setattr(ledger._store, "transaction", pause)
    with ThreadPoolExecutor(max_workers=2) as pool:
        writer = pool.submit(ledger.apply, "requester", "goal", "goal.create", goal_payload())
        try:
            assert entered.wait(10)
            migration = pool.submit(api.migration.migrate_journal, other, **args)
        finally:
            release.set()
        receipt = writer.result(timeout=10)
        event = migration.result(timeout=10)
    restored = open_ledger(api, event["backup"]["path"], event["old_configuration"])
    assert restored.events() == [receipt]


def test_migration_holds_writer_lock_through_approval_backup_and_cas(api, ledger):
    entered, release, trying = Event(), Event(), Event()
    other = open_ledger(api, ledger._store.path)

    def approve(controller, request):
        entered.set()
        assert release.wait(10)
        return True

    def old_writer():
        trying.set()
        return other.apply("requester", "stale", "goal.create", goal_payload())

    args = proposal(api, ledger, verify_approval=approve)
    with ThreadPoolExecutor(max_workers=2) as pool:
        migration = pool.submit(api.migration.migrate_journal, ledger, **args)
        try:
            assert entered.wait(10)
            writer = pool.submit(old_writer)
            assert trying.wait(10)
        finally:
            release.set()
        migration.result(timeout=10)
        with pytest.raises(api.ContractError, match="fence"):
            writer.result(timeout=10)
    assert ledger.events() == []


def test_audit_is_append_only_paginated_detached_and_ids_cannot_be_reused(api, ledger):
    assert api.migration.migration_events(ledger) == []
    first = migrate(api, ledger)
    current = open_ledger(api, ledger._store.path, first["new_configuration"])
    before = snapshot(ledger._store.path)
    with pytest.raises(api.ContractError, match="Migration id already exists"):
        migrate(api, current)
    assert snapshot(ledger._store.path) == before
    second = migrate(
        api,
        current,
        migration_id="migration:2",
        backup_path=Path(ledger._store.path).parent / "second.sqlite",
    )
    assert second["old_config_hash"] == first["new_config_hash"]
    assert (first["sequence"], second["sequence"]) == (1, 2)
    assert api.migration.migration_events(ledger, limit=1) == [first]
    assert api.migration.migration_events(ledger, after=1) == [second]
    assert api.migration.migration_events(ledger, after=2) == []
    page = api.migration.migration_events(ledger)
    page[0]["new_configuration"]["principals"].clear()
    page[1]["evidence_ids"].clear()
    first["reason"] = "Mutated detached return"
    actual = api.migration.migration_events(ledger)
    assert actual[0]["reason"] == "Host-approved capacity growth"
    assert actual[0]["new_configuration"]["principals"]
    assert actual[1]["evidence_ids"] == ["approval:host-case-1"]
    assert ledger.events() == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"after": -1},
        {"after": True},
        {"after": "1"},
        {"limit": 0},
        {"limit": 1001},
        {"limit": True},
    ],
)
def test_bad_audit_cursor_is_rejected(api, ledger, kwargs):
    with pytest.raises(api.ContractError):
        api.migration.migration_events(ledger, **kwargs)


def test_budget_increase_keeps_command_count_and_exact_replay_does_not_spend(api, tmp_path):
    ledger = open_ledger(api, tmp_path / "journal.sqlite", max_commands=1)
    original = ledger.apply("requester", "goal", "goal.create", goal_payload())
    assert ledger.receipt("requester", "goal", "goal.create", goal_payload()) == original
    with pytest.raises(api.ContractError, match="budget exhausted"):
        ledger.apply("requester", "second", "goal.create", goal_payload("second"))
    event = migrate(api, ledger)
    current = open_ledger(api, ledger._store.path, event["new_configuration"])
    assert current.apply("requester", "goal", "goal.create", goal_payload()) == original
    assert (
        current.apply("requester", "second", "goal.create", goal_payload("second"))["sequence"] == 2
    )
    with pytest.raises(api.ContractError, match="budget exhausted"):
        current.apply("requester", "third", "goal.create", goal_payload("third"))
    assert len(current.events()) == 2


def test_receipt_missing_lookup_does_not_create_records_or_validate_current_evidence(
    api, ledger, monkeypatch
):
    original = ledger.apply("requester", "goal", "goal.create", goal_payload())
    before = snapshot(ledger._store.path)

    def must_not_run(*args):
        pytest.fail("Replay lookup must not execute the handler or recheck expired evidence")

    monkeypatch.setattr(ledger, "_goal_create", must_not_run)
    assert (
        ledger.receipt("requester", "missing", "goal.create", {"invalid_for_new_goal": True})
        is None
    )
    assert ledger.receipt("requester", "goal", "goal.create", goal_payload()) == original
    result = ledger.receipt("requester", "goal", "goal.create", goal_payload())
    result["result"]["version"]["intent"]["title"] = "tampered"
    assert ledger.receipt("requester", "goal", "goal.create", goal_payload()) == original
    assert snapshot(ledger._store.path) == before


@pytest.mark.parametrize("change", ["actor", "operation", "payload", "unknown", "denied"])
def test_receipt_never_discloses_another_actor_or_conflicting_input(api, ledger, change):
    ledger.apply("requester", "goal", "goal.create", goal_payload())
    actor, operation, payload = "requester", "goal.create", goal_payload()
    if change == "actor":
        actor = "provider"
    elif change == "operation":
        operation = "goal.revise"
    elif change == "payload":
        payload["id"] = "different"
    elif change == "unknown":
        actor = "attacker"
    else:
        actor = "observer"
    before = snapshot(ledger._store.path)
    with pytest.raises(
        api.ContractError, match="conflict|Unknown authenticated actor|Capability denied"
    ):
        ledger.receipt(actor, "goal", operation, payload)
    assert snapshot(ledger._store.path) == before


def test_missing_receipt_still_requires_authentication_and_capability(api, ledger):
    for actor in ("unknown", "observer"):
        with pytest.raises(api.ContractError):
            ledger.receipt(actor, "missing", "goal.create", goal_payload())


def test_receipt_replays_original_success_after_goal_and_commitment_state_changes(api, ledger):
    seed(ledger)
    saved = ledger.events()[0]
    assert ledger.get("goal", "goal")["revision"] == 2
    assert ledger.receipt("requester", "goal", "goal.create", goal_payload()) == saved
    assert saved["result"]["revision"] == 1
    reopened = open_ledger(api, ledger._store.path)
    assert reopened.receipt("requester", "goal", "goal.create", goal_payload()) == saved


def test_missing_or_replaced_scope_is_fenced_before_existing_receipt_lookup(api, ledger):
    ledger.apply("requester", "goal", "goal.create", goal_payload())
    with sqlite3.connect(ledger._store.path) as db:
        db.execute("DELETE FROM evolution_scopes WHERE name=?", (api.journal.JOURNAL_SCOPE,))
    before = snapshot(ledger._store.path)
    with pytest.raises(api.ContractError, match="fence"):
        ledger.apply("requester", "goal", "goal.create", goal_payload())
    with pytest.raises(api.ContractError, match="fence"):
        ledger.receipt("requester", "goal", "goal.create", goal_payload())
    assert snapshot(ledger._store.path) == before
