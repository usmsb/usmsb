"""Explicit additive governance migration for a host's collaboration SQLite file.

Only trusted host code may call this module. It supplies authenticated controller
approval verification and a private backup location. No identity enrollment,
execution, payment, automatic recovery, or authority to modify old obligations.
"""

import hashlib
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from .contracts import _check, _ids, _text
from .evolution import _json, clone, fingerprint
from .journal import JOURNAL_SCOPE, CollaborationJournal, _installed_configuration, fields
from .profiles import CollaborationProfile


def _configuration(value):
    """Accept a complete effective configuration, never normalize changes silently."""
    value = clone(value)
    fields(value, ("host_id", "principals", "profiles", "max_commands"))
    _check(type(value["profiles"]) is dict, "Expected complete profile mapping")
    profiles = []
    for key, record in value["profiles"].items():
        fields(
            record,
            ("id", "version", "review_mode", "media_types", "max_criteria", "max_steps", "legacy"),
        )
        _check(key == record["id"], "Profile key/id mismatch")
        _check(type(record["media_types"]) is list, "Expected profile media types list")
        profiles.append(
            CollaborationProfile(**{**record, "media_types": tuple(record["media_types"])})
        )
    installed, _ = _installed_configuration(
        value["host_id"], value["principals"], profiles, value["max_commands"]
    )
    _check(_json(installed) == _json(value), "Supply exact canonical effective configuration")
    return installed


def configuration_hash(configuration):
    """SHA256 of validated effective configuration in bind_scope's JSON encoding.

    This intentionally differs from journal.digest for non-ASCII identifiers.
    Pass journal.configuration(), or a complete additive proposal derived from it.
    """
    return fingerprint(_configuration(configuration))


def _additive(old, new):
    separate = "; requires a separate governance case, not an additive migration"
    _check(old["host_id"] == new["host_id"], "Host identity is immutable" + separate)
    for actor, grant in old["principals"].items():
        _check(
            actor in new["principals"] and new["principals"][actor] == grant,
            "Existing actor/controller/capabilities are immutable" + separate,
        )
    for key, profile in old["profiles"].items():
        _check(
            key in new["profiles"] and new["profiles"][key] == profile,
            "Existing profile ID and its complete configuration are immutable" + separate,
        )
    _check(new["max_commands"] >= old["max_commands"], "Cannot reduce command budget" + separate)
    _check(_json(old) != _json(new), "Migration must make an additive configuration change")


def _has_audit(db):
    return (
        db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='collaboration_migrations'"
        ).fetchone()
        is not None
    )


def _backup(source_path, destination_path, expected_binding):
    """Run before ANY transaction writes, while a separate connection holds IMMEDIATE.

    A read-only connection sees the last committed snapshot; IMMEDIATE excludes
    other writers in WAL and rollback-journal modes. Backing up the writing
    connection itself can hang. The caller must own the backup directory; this
    does not defend against a hostile filesystem administrator replacing files.
    Failures may leave the exclusively created file for host inspection; never
    delete, reuse, or overwrite that file automatically.
    """
    source_path = Path(source_path).resolve(strict=True)
    destination = Path(os.path.abspath(destination_path))
    forbidden = {Path(str(source_path) + suffix) for suffix in ("", "-wal", "-shm", "-journal")}
    _check(destination.resolve() not in forbidden, "Backup must not be the journal or sidecar")
    for suffix in ("-wal", "-shm", "-journal"):
        _check(not os.path.lexists(str(destination) + suffix), "Backup sidecar already exists")
    # O_EXCL rejects even empty files, hard links and dangling symlinks.
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
    try:
        with closing(sqlite3.connect(source_path.as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(destination.as_uri() + "?mode=rw", uri=True)) as backup:
                source.backup(backup)
                _check(
                    backup.execute("PRAGMA integrity_check").fetchall() == [("ok",)],
                    "Backup integrity check failed",
                )
                _check(
                    backup.execute(
                        "SELECT binding FROM evolution_scopes WHERE name=?", (JOURNAL_SCOPE,)
                    ).fetchone()
                    == (expected_binding,),
                    "Backup configuration mismatch",
                )
        os.fsync(fd)
        with destination.open("rb") as saved:
            backup_hash = hashlib.file_digest(saved, "sha256").hexdigest()
    finally:
        os.close(fd)
    return {"path": str(destination), "sha256": backup_hash}


def migrate_journal(
    journal,
    *,
    migration_id,
    expected_config_hash,
    new_configuration,
    reason,
    evidence_ids,
    verify_approval,
    backup_path,
):
    """CAS an explicitly approved additive config, returning its immutable audit event.

    ``new_configuration`` has exactly the shape of journal.configuration(). The
    caller supplies configuration_hash(old_configuration) as expected_config_hash.
    For EVERY distinct old controller, verify_approval(controller, request) must
    authenticate approval of that exact request and return the singleton True.
    Request fields: schema, scope, host_id, migration_id, old_config_hash,
    new_config_hash, reason, evidence_ids, required_controllers. Every callback
    receives its own detached request. It must not reenter journal operations;
    it runs under the write lock and must complete promptly. A callback exception
    aborts the migration, as does False/None/1 or any other non-True result.

    Backup is mandatory, consistent, fsynced and exclusively created before CAS.
    Binding and audit append commit together. Existing rows/receipts/terms remain
    untouched, and old instances of THIS implementation become fenced.
    Stop pre-a2 binaries before migration: they lack the per-command fence;
    application checks cannot constrain arbitrary older software or raw SQL.
    Open a fresh CollaborationJournal with the approved config to resume writes.
    Reusing migration IDs and stale/no-op requests fails; no automatic retry.
    On failure an already-created backup is retained; use a fresh path to retry.
    """
    _check(isinstance(journal, CollaborationJournal), "Require a host collaboration journal")
    _check(callable(verify_approval), "Require trusted host approval callback")
    _check(_text(migration_id, 180) == migration_id, "Migration id must be canonical")
    _check(_text(reason) == reason, "Reason must be canonical")
    refs = _ids(evidence_ids)
    _check(refs and refs == evidence_ids, "Require canonical migration evidence references")
    old = json.loads(journal._binding)
    new = _configuration(new_configuration)
    old_hash, new_hash = configuration_hash(old), configuration_hash(new)
    _check(expected_config_hash == old_hash, "Expected configuration hash mismatch (CAS)")
    _additive(old, new)
    controllers = sorted({grant["controller"] for grant in old["principals"].values()})
    request = {
        "schema": "usmsb.collaboration-migration-approval.v1",
        "scope": JOURNAL_SCOPE,
        "host_id": old["host_id"],
        "migration_id": migration_id,
        "old_config_hash": old_hash,
        "new_config_hash": new_hash,
        "reason": reason,
        "evidence_ids": refs,
        "required_controllers": controllers,
    }
    with journal._store.transaction() as db:
        journal._check_scope(db)
        _check(
            not _has_audit(db)
            or db.execute(
                "SELECT 1 FROM collaboration_migrations WHERE id=?", (migration_id,)
            ).fetchone()
            is None,
            "Migration id already exists; requires a new governance case",
        )
        for controller in controllers:
            _check(
                verify_approval(controller, clone(request)) is True,
                "Missing exact approval from an old controller",
            )
        backup = _backup(journal._store.path, backup_path, journal._binding)
        new_binding = _json(new)
        cursor = db.execute(
            "UPDATE evolution_scopes SET binding=? WHERE name=? AND binding=?",
            (new_binding, JOURNAL_SCOPE, journal._binding),
        )
        _check(
            cursor.rowcount == 1, "Configuration CAS failed; retry requires a new governance case"
        )
        db.execute(
            "CREATE TABLE IF NOT EXISTS collaboration_migrations ("
            "sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
            "id TEXT UNIQUE NOT NULL, event TEXT NOT NULL)"
        )
        event = {
            **request,
            "schema": "usmsb.collaboration-migration.v1",
            "approved_controllers": controllers,
            "old_configuration": old,
            "new_configuration": new,
            "backup": backup,
        }
        cursor = db.execute(
            "INSERT INTO collaboration_migrations(id,event) VALUES (?,?)",
            (migration_id, _json(event)),
        )
        _check(cursor.rowcount == 1, "Migration audit append failed")
        return {"sequence": cursor.lastrowid, **event}


def migration_events(journal, *, after=0, limit=100):
    """Host-only detached audit pages, readable even from a fenced instance.

    Migration sequences are independent of command receipt sequences/budgets.
    The host must protect audit visibility and backup contents/paths.
    """
    _check(isinstance(journal, CollaborationJournal), "Require a host collaboration journal")
    _check(
        type(after) is int and after >= 0 and type(limit) is int and 1 <= limit <= 1000,
        "Invalid migration event cursor",
    )
    with journal._store.transaction() as db:
        if not _has_audit(db):
            return []
        return [
            {"sequence": sequence, **json.loads(event)}
            for sequence, event in db.execute(
                "SELECT sequence,event FROM collaboration_migrations "
                "WHERE sequence>? ORDER BY sequence LIMIT ?",
                (after, limit),
            )
        ]
