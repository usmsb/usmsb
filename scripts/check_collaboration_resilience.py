"""Bounded, offline SQLite protocol experiments; never evidence of intelligent emergence.

Run with .venv/Scripts/python.exe -E -B scripts/check_collaboration_resilience.py.
Only a newly allocated temporary directory is used for databases and evidence.
"""

import argparse
import hashlib
import importlib
import json
import math
import os
import platform
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIMITS = {"goals": 64, "workers": 4, "rounds": 32, "goal_rounds": 256, "seconds": 120}
DEFAULTS = {"goals": 4, "workers": 2, "rounds": 3, "seconds": 45}
PHASES = (
    "export",
    "initialize",
    "replay",
    "cas",
    "fault_baseline",
    "kill_writer",
    "rollback_restart",
    "load",
    "revision_rounds",
    "restart",
    "backup_restore",
)
TABLES = (
    "evolution_binding",
    "evolution_decisions",
    "evolution_journal",
    "evolution_remote_state",
    "evolution_observations",
    "evolution_scopes",
    "collaboration_records",
    "collaboration_commands",
    "collaboration_revision_impacts",
    "sqlite_sequence",
)
PRINCIPALS = {
    "owner": {
        "controller": "fixture:owner",
        "operations": [
            "goal.create",
            "goal.revise",
            "commitment.propose",
            "commitment.accept",
        ],
    },
    "provider": {
        "controller": "fixture:provider",
        "operations": [
            "commitment.accept",
            "artifact.submit",
        ],
    },
    "reviewer": {"controller": "fixture:reviewer", "operations": ["review.record"]},
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def validate_config(config):
    if set(config) != set(DEFAULTS):
        raise ValueError("Expected goals, workers, rounds and seconds")
    for key, maximum in LIMITS.items():
        if key == "goal_rounds":
            continue
        minimum = 2 if key == "workers" else 5 if key == "seconds" else 1
        if type(config[key]) is not int or not minimum <= config[key] <= maximum:
            raise ValueError(f"{key} must be an integer in [{minimum}, {maximum}]")
    if config["goals"] * config["rounds"] > LIMITS["goal_rounds"]:
        raise ValueError(f"goals * rounds must not exceed {LIMITS['goal_rounds']}")
    return dict(config)


def write_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
    )
    temporary.replace(path)  # Readiness/result files become visible only when complete.


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def json_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def snapshot(path):
    """Logical contents, including scope binding and sequence allocation, not file bytes."""
    with closing(sqlite3.connect(path, timeout=1)) as db:
        contents = {}
        for table in TABLES:  # Trusted constant identifiers; no user SQL.
            rows = db.execute(f"SELECT * FROM {table}").fetchall()
            contents[table] = sorted(rows, key=lambda row: json.dumps(row))
        return {
            "sha256": json_digest(contents),
            "rows": {table: len(rows) for table, rows in contents.items()},
        }


def integrity(path):
    with closing(sqlite3.connect(path, timeout=1)) as db:
        result = [row[0] for row in db.execute("PRAGMA integrity_check")]
    require(result == ["ok"], f"Integrity failure: {result}")
    return result


def backup(source, destination):
    with closing(sqlite3.connect(source, timeout=1)) as src:
        with closing(sqlite3.connect(destination, timeout=1)) as dst:
            src.backup(dst)


def goal_payload(gid):
    return {
        "id": gid,
        "intent": {
            "title": f"Controlled goal {gid}",
            "description": "Synthetic local protocol load",
            "domain": "engineering",
            "success_criteria": "Version and consent invariants hold",
        },
    }


def revision_payload(gid, base, label):
    return {
        "goal_id": gid,
        "base_revision": base,
        "changes": {"title": label},
        "reason": "Scripted counterevidence, not autonomous learning",
        "evidence_ids": [f"fixture:{gid}:{base}"],
    }


def proposal(gid, revision, cid, supersedes=None):
    result = {
        "id": cid,
        "goal_id": gid,
        "goal_revision": revision,
        "provider_id": "provider",
        "description": "Controlled local protocol exercise",
        "terms": "Synthetic consent; no execution, payment or data grant",
        "criteria": [{"id": "invariants", "description": "Protocol checks pass"}],
        "verifier_ids": ["reviewer"],
        "profile_id": "usmsb:open-collaboration",
    }
    if supersedes is not None:
        result["supersedes"] = supersedes
    return result


def event_list(journal):
    result, cursor = [], 0
    for _ in range(100):
        page = journal.events(after=cursor, limit=100)
        if not page:
            return result
        require(page[0]["sequence"] > cursor, "Event cursor did not advance")
        result.extend(page)
        cursor = page[-1]["sequence"]
    raise AssertionError("Event pagination exceeded bounded ledger size")


def impact_ids(journal, gid, revision):
    result, cursor, pages = [], None, 0
    for _ in range(8):
        page = journal.revision_impacts(gid, revision, after=cursor, limit=2)
        result.extend(page["commitment_ids"])
        pages += 1
        if page["next_after"] is None:
            return result, pages
        require(page["next_after"] != cursor, "Impact cursor did not advance")
        cursor = page["next_after"]
    raise AssertionError("Impact pagination did not terminate")


class Worker:
    def __init__(self, spec):
        self.spec = spec
        self.root = Path(spec["directory"])
        self.path = self.root / "journal.sqlite"
        self.samples = []
        self.evidence = {}
        sys.path.insert(0, str(self.root))
        self.api = importlib.import_module("resilience_core.autonomy")
        self.journal = self.open(self.path)

    def open(self, path):
        return self.api.CollaborationJournal(
            path,
            host_id="local-resilience-fixture",
            principals=PRINCIPALS,
            max_commands=10000,
        )

    def wait_at_gate(self, connection=None):
        ready = {
            "pid": os.getpid(),
            "journal_initialized": True,
            "sqlite_connection_open": connection is not None,
        }
        if connection is not None:
            ready["sqlite_database"] = connection.execute("PRAGMA database_list").fetchone()[2]
        write_json(Path(self.spec["ready"]), ready)
        while not Path(self.spec["gate"]).exists():
            if time.monotonic() >= self.spec["deadline"]:
                raise TimeoutError("Start barrier timed out")
            time.sleep(0.005)

    def gate_first_connection(self):
        # One-shot, child-local connection instrumentation. The original store still
        # opens a real connection and executes its own BEGIN IMMEDIATE/commit/rollback.
        original_connect = sqlite3.connect

        def connect(*args, **kwargs):
            sqlite3.connect = original_connect
            db = original_connect(*args, **kwargs)
            try:
                self.wait_at_gate(db)
                return db
            except BaseException:
                db.close()
                raise

        sqlite3.connect = connect

    def apply(self, cid, operation, payload, actor="owner", expected_error=None, journal=None):
        start = time.monotonic()
        sample = {
            "command_id": cid,
            "operation": operation,
            "pid": os.getpid(),
            "started_monotonic": start,
            "outcome": "unexpected_failure",
        }
        try:
            receipt = (journal or self.journal).apply(actor, cid, operation, payload)
            require(expected_error is None, f"Expected rejection for {cid}")
            sample["outcome"] = "success"
            sample["sequence"] = receipt["sequence"]
            return receipt
        except self.api.ContractError as exc:
            sample["error"] = str(exc)
            if expected_error is None or str(exc) != expected_error:
                raise
            sample["outcome"] = "expected_rejection"
            return None
        finally:
            sample["finished_monotonic"] = time.monotonic()
            sample["latency_ms"] = (sample["finished_monotonic"] - start) * 1000
            self.samples.append(sample)
            # Keep completed samples even if this worker later blocks and is terminated.
            with Path(self.spec["samples"]).open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(sample, allow_nan=False) + "\n")

    def consent(self, contract, actor):
        return self.apply(
            f"accept:{contract['id']}:{actor}",
            "commitment.accept",
            {"commitment_id": contract["id"], "terms_hash": contract["terms_hash"]},
            actor=actor,
        )["result"]

    def propose(self, gid, revision, cid, supersedes=None):
        return self.apply(
            f"propose:{cid}", "commitment.propose", proposal(gid, revision, cid, supersedes)
        )["result"]

    def initialize(self):
        require(not event_list(self.journal), "Experiment did not start with an empty ledger")
        with closing(sqlite3.connect(self.path)) as db:
            self.evidence = {
                name: db.execute(f"PRAGMA {name}").fetchone()[0]
                for name in ("journal_mode", "synchronous", "page_size")
            }

    def replay(self):
        self.evidence["receipt"] = self.apply(
            "shared:create", "goal.create", goal_payload("shared")
        )

    def cas(self):
        label = f"CAS contender {self.spec['index']}"
        try:
            self.evidence["receipt"] = self.apply(
                f"cas:{self.spec['index']}",
                "goal.revise",
                revision_payload("shared", 1, label),
            )
        except self.api.ContractError as exc:
            if str(exc) != "Stale goal revision":
                raise
            self.samples[-1]["outcome"] = "expected_rejection"
            self.evidence["rejection"] = str(exc)

    def fault_baseline(self):
        events = event_list(self.journal)
        require(len(events) == 2, "Replay/CAS produced duplicate or missing events")
        require(events[0]["command_id"] == "shared:create", "Unexpected replay event")
        require(self.journal.get("goal", "shared")["revision"] == 2, "CAS revision mismatch")
        require(
            self.journal.goal_version("shared", 1)["intent"] == goal_payload("shared")["intent"],
            "CAS mutated the original version",
        )
        require(
            self.journal.get("goal", "shared") == events[1]["result"]["goal"],
            "CAS winning receipt does not match stored goal",
        )
        contract = self.propose("shared", 2, "fault:contract")
        self.consent(contract, "owner")
        self.consent(contract, "provider")
        self.evidence = {
            "baseline": snapshot(self.path),
            "cas_winner": events[1],
            "frozen_contract": self.journal.get("commitment", "fault:contract"),
        }

    def kill_writer(self):
        # Test-local instrumentation around the *real* transaction. apply() has written
        # records, impact rows AND its receipt when yield resumes, but commit is pending.
        original = self.journal._store.transaction

        @contextmanager
        def stop_before_commit():
            with original() as db:
                db.execute("PRAGMA cache_size=1")
                db.execute("PRAGMA cache_spill=ON")
                yield db
                require(db.in_transaction, "Fault hook ran outside a transaction")
                command = db.execute(
                    "SELECT receipt FROM collaboration_commands WHERE id='fault:revise'",
                ).fetchone()
                require(command is not None, "Fault injected before the receipt write")
                tentative = json.loads(command[0])
                require(tentative["result"]["goal"]["revision"] == 3, "Wrong tentative revision")
                require(
                    tentative["result"]["affected_commitment_count"] == 1,
                    "Tentative revision did not write its impact snapshot",
                )
                journal_bytes = Path(str(self.path) + "-journal").stat().st_size
                require(journal_bytes > 512, "Rollback journal was not written")
                write_json(
                    Path(self.spec["ready"]),
                    {
                        "pid": os.getpid(),
                        "uncommitted_receipt": tentative,
                        "in_transaction": db.in_transaction,
                        "rollback_journal_bytes": journal_bytes,
                        "hook": "after journal records/impacts/receipt writes; before store commit",
                    },
                )
                while time.monotonic() < self.spec["deadline"]:
                    time.sleep(0.01)
                raise TimeoutError("Writer was not killed at the confirmed fault point")

        self.journal._store.transaction = stop_before_commit
        self.apply("fault:revise", "goal.revise", revision_payload("shared", 2, "Killed revision"))
        raise AssertionError("Uncommitted writer unexpectedly returned")

    def rollback_restart(self):
        before = snapshot(self.path)
        require(before == self.spec["baseline"], "Killed transaction left partial durable state")
        require(
            self.journal.get("commitment", "fault:contract") == self.spec["frozen_contract"],
            "Killed transaction altered frozen contract",
        )
        self.evidence = {"after_recovery": before, "integrity_check": integrity(self.path)}
        payload = revision_payload("shared", 2, "Killed revision")
        receipt = self.apply("fault:revise", "goal.revise", payload)
        require(
            self.apply("fault:revise", "goal.revise", payload) == receipt,
            "Retry after restart was not idempotent",
        )
        require(len(event_list(self.journal)) == 6, "Retry committed an incorrect number of events")
        require(
            impact_ids(self.journal, "shared", 3)[0] == ["fault:contract"],
            "Retry lost the revision impact",
        )
        self.evidence.update(retry_receipt=receipt, retry_committed_once=True)

    def assigned_goals(self):
        config = self.spec["config"]
        return [f"load:{i}" for i in range(self.spec["index"], config["goals"], config["workers"])]

    def load(self):
        for gid in self.assigned_goals():
            self.apply(f"create:{gid}", "goal.create", goal_payload(gid))
            contract = self.propose(gid, 1, f"{gid}:contract:1")
            self.consent(contract, "owner")
            self.consent(contract, "provider")
            for i in range(2):
                self.propose(gid, 1, f"{gid}:pending:{i}")
        self.evidence["created_goals"] = self.assigned_goals()

    def revision_rounds(self):
        completed = 0
        for gid in self.assigned_goals():
            pending = [self.journal.get("commitment", f"{gid}:pending:{i}") for i in range(2)]
            for base in range(1, self.spec["config"]["rounds"] + 1):
                old = self.journal.get("commitment", f"{gid}:contract:{base}")
                version = self.journal.goal_version(gid, base)
                payload = revision_payload(gid, base, f"Controlled revision {base + 1}")
                cid = f"revise:{gid}:{base + 1}"
                receipt = self.apply(cid, "goal.revise", payload)
                require(
                    self.apply(cid, "goal.revise", payload) == receipt, "Revision replay changed"
                )
                self.apply(
                    cid + ":stale", "goal.revise", payload, expected_error="Stale goal revision"
                )
                require(
                    self.journal.goal_version(gid, base) == version, "Historical version changed"
                )
                require(
                    self.journal.get("commitment", old["id"]) == old,
                    "Intent revision rewrote an existing obligation",
                )
                expected_ids = sorted([old["id"], *(item["id"] for item in pending)])
                require(
                    impact_ids(self.journal, gid, base + 1) == (expected_ids, 2),
                    "Paginated revision impact mismatch",
                )
                result = receipt["result"]
                require(
                    result["affected_commitment_count"] == 3
                    and result["affected_commitment_ids"] == expected_ids
                    and result["obligations_changed"] is False,
                    "Incorrect revision receipt",
                )
                replacement = self.propose(gid, base + 1, f"{gid}:contract:{base + 1}", old["id"])
                half = self.consent(replacement, "owner")
                require(
                    half["status"] == "proposed"
                    and self.journal.get("commitment", old["id"]) == old,
                    "Contract replaced without provider consent",
                )
                active = self.consent(replacement, "provider")
                prior = self.journal.get("commitment", old["id"])
                require(
                    active["status"] == "active"
                    and prior["status"] == "superseded"
                    and prior["superseded_by"] == replacement["id"],
                    "Replacement not atomic",
                )
                require(
                    prior["terms"] == old["terms"] and prior["terms_hash"] == old["terms_hash"],
                    "Replacement rewrote frozen terms",
                )
                require(
                    impact_ids(self.journal, gid, base + 1) == (expected_ids, 2),
                    "Historical impact changed with live commitment state",
                )
                require(
                    [self.journal.get("commitment", item["id"]) for item in pending] == pending,
                    "Pending obligations changed without consent",
                )
                completed += 1
        self.evidence = {"completed_goal_rounds": completed, "autonomous_intelligence": False}

    def restart(self):
        config = self.spec["config"]
        expected_events = 6 + config["goals"] * (6 + 4 * config["rounds"])
        events = event_list(self.journal)
        require(len(events) == expected_events, "Restart event count differs from committed work")
        require(
            [item["sequence"] for item in events] == list(range(1, expected_events + 1)),
            "Unexpected sequence allocation or missing receipt",
        )
        require(
            len({item["command_id"] for item in events}) == expected_events, "Duplicate commands"
        )
        for i in range(config["goals"]):
            gid = f"load:{i}"
            require(
                self.journal.get("goal", gid)["revision"] == config["rounds"] + 1,
                "Lost final goal revision",
            )
            for revision in range(1, config["rounds"] + 2):
                version = self.journal.goal_version(gid, revision)
                expected = goal_payload(gid)["intent"]
                if revision > 1:
                    expected["title"] = f"Controlled revision {revision}"
                    ids = sorted(
                        [f"{gid}:contract:{revision - 1}", f"{gid}:pending:0", f"{gid}:pending:1"]
                    )
                    require(
                        impact_ids(self.journal, gid, revision) == (ids, 2),
                        "Restart lost a historical impact page",
                    )
                require(version["intent"] == expected, "Restart changed historical intent")
                contract = self.journal.get("commitment", f"{gid}:contract:{revision}")
                status = "active" if revision == config["rounds"] + 1 else "superseded"
                require(
                    contract["status"] == status and contract["terms"]["goal_revision"] == revision,
                    "Restart lost the consent/replacement chain",
                )
        before = snapshot(self.path)
        require(
            self.apply("shared:create", "goal.create", goal_payload("shared")) == events[0],
            "Restart changed the original receipt",
        )
        require(snapshot(self.path) == before, "Restart replay changed durable state")
        self.evidence = {
            "snapshot": before,
            "event_count": len(events),
            "integrity_check": integrity(self.path),
            "history_verified": True,
        }

    def backup_restore(self):
        checkpoint = snapshot(self.path)
        checkpoint_events = event_list(self.journal)
        checkpoint_path, restored_path = (
            self.root / "checkpoint.sqlite",
            self.root / "restored.sqlite",
        )
        backup(self.path, checkpoint_path)
        require(snapshot(checkpoint_path) == checkpoint, "SQLite backup lost committed state")
        # Deliberate committed tail makes the recovery point observable.
        tail = self.apply("backup:tail", "goal.create", goal_payload("backup:tail"))
        backup(checkpoint_path, restored_path)
        restored = self.open(restored_path)
        require(snapshot(restored_path) == checkpoint, "Restored state differs from checkpoint")
        try:
            restored.get("goal", "backup:tail")
        except self.api.ContractError as exc:
            require(str(exc) == "Record not found", "Unexpected restore lookup failure")
        else:
            raise AssertionError("Restore contains an event committed after the backup")
        require(event_list(restored) == checkpoint_events, "Restore changed historical receipts")
        require(
            self.apply("shared:create", "goal.create", goal_payload("shared"), journal=restored)
            == checkpoint_events[0],
            "Restore changed the idempotency receipt",
        )
        require(snapshot(restored_path) == checkpoint, "Restore replay changed checkpoint state")
        probe = self.apply(
            "restore:probe", "goal.create", goal_payload("restore:probe"), journal=restored
        )
        require(
            probe["sequence"] == tail["sequence"], "Restored sequence did not resume at checkpoint"
        )
        require(snapshot(checkpoint_path) == checkpoint, "Recovery probe mutated the backup")
        require(event_list(self.journal)[-1] == tail, "Restored writes changed source ledger")
        self.evidence = {
            "checkpoint": checkpoint,
            "checkpoint_sequence": checkpoint_events[-1]["sequence"],
            "source_tail_sequence": tail["sequence"],
            "restored_write_sequence": probe["sequence"],
            "excluded_post_backup_commands": ["backup:tail"],
            "restored_replay_unchanged": True,
            "integrity_checks": {
                p.name: integrity(p) for p in (self.path, checkpoint_path, restored_path)
            },
            "boundary": "Quiescent SQLite backup; the deliberate post-backup tail is not recovered",
        }


def worker_main(job_path):
    spec = read_json(job_path)
    directory = Path(spec["directory"]).resolve()
    require(
        directory == job_path.resolve().parent
        and directory.parent == Path(tempfile.gettempdir()).resolve()
        and directory.name.startswith("usmsb-collaboration-resilience-"),
        "Worker jobs must belong to a dedicated local experiment directory",
    )
    require(spec["phase"] in PHASES, "Unknown experiment phase")
    for key in ("process", "ready", "samples", "result"):
        require(Path(spec[key]).resolve().parent == directory, "Worker evidence escaped directory")
    if spec.get("gate"):
        require(Path(spec["gate"]).resolve().parent == directory, "Worker gate escaped directory")
    validate_config(spec["config"])
    write_json(Path(spec["process"]), {"pid": os.getpid()})
    worker = None
    result = {"status": "failed", "pid": os.getpid(), "samples": []}
    try:
        if spec["phase"] == "export":
            sys.path.insert(0, str(ROOT / "scripts"))
            exporter = importlib.import_module("export_autonomy")
            result["evidence"] = {
                "manifest": exporter.export(Path(spec["directory"]) / "resilience_core")
            }
        else:
            worker = Worker(spec)
            if spec.get("gate"):
                if spec["phase"] in {"replay", "cas"}:
                    worker.gate_first_connection()
                else:
                    worker.wait_at_gate()
            getattr(worker, spec["phase"])()
            result["evidence"] = worker.evidence
        result["status"] = "passed"
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if worker is not None:
            result["samples"] = worker.samples
        write_json(Path(spec["result"]), result)
    return 0 if result["status"] == "passed" else 1


def metrics(samples):
    values = sorted(sample["latency_ms"] for sample in samples)
    window = (
        (
            max(s["finished_monotonic"] for s in samples)
            - min(s["started_monotonic"] for s in samples)
        )
        if samples
        else 0.0
    )
    outcomes = {
        key: sum(s["outcome"] == key for s in samples)
        for key in ("success", "expected_rejection", "unexpected_failure")
    }
    return {
        "completed_apply_attempts": len(samples),
        **outcomes,
        "unique_successful_command_ids": len(
            {s["command_id"] for s in samples if s["outcome"] == "success"}
        ),
        "sample_window_seconds": window,
        "successful_apply_calls_per_second": outcomes["success"] / window if window else None,
        "attempts_per_second": len(samples) / window if window else None,
        "latency_ms": {
            "count": len(values),
            "min": values[0] if values else None,
            "p50": values[math.ceil(len(values) * 0.50) - 1] if values else None,
            "p95": values[math.ceil(len(values) * 0.95) - 1] if values else None,
            "p99": values[math.ceil(len(values) * 0.99) - 1] if values else None,
            "max": values[-1] if values else None,
        },
    }


class Supervisor:
    """Only children touch SQLite; one wall budget can stop blocked SQLite calls too."""

    def __init__(self, directory, config, deadline):
        self.root, self.config, self.deadline = directory, config, deadline
        self.phases = []

    @staticmethod
    def kill(process, spec):
        # Windows venv launchers may have a different PID from the real interpreter.
        # Target the PID reported by our worker, then reap its owned launcher too.
        process_file = Path(spec["process"])
        actual_pid = read_json(process_file)["pid"] if process_file.exists() else process.pid
        if process.poll() is None:
            if actual_pid != process.pid:
                try:
                    os.kill(actual_pid, signal.SIGTERM if os.name == "nt" else signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if process.poll() is None:
                process.kill()
        return actual_pid

    def run(self, phase, count=1, **extra):
        start = time.monotonic()
        record = {"phase": phase, "status": "failed", "workers": []}
        self.phases.append(record)
        children = []
        gate = self.root / f"{phase}.go" if count > 1 else None
        try:
            for index in range(count):
                if time.monotonic() >= self.deadline:
                    raise TimeoutError("Experiment wall-time budget exhausted")
                stem = self.root / f"{phase}-{index}"
                spec = {
                    "phase": phase,
                    "index": index,
                    "directory": str(self.root),
                    "config": self.config,
                    "deadline": self.deadline,
                    "ready": str(stem.with_suffix(".ready.json")),
                    "process": str(stem.with_suffix(".process.json")),
                    "samples": str(stem.with_suffix(".samples.jsonl")),
                    "result": str(stem.with_suffix(".result.json")),
                    "gate": str(gate) if gate else None,
                    **extra,
                }
                job_path = stem.with_suffix(".job.json")
                write_json(job_path, spec)
                with stem.with_suffix(".stderr.log").open("w", encoding="utf-8") as error_log:
                    process = subprocess.Popen(
                        [
                            sys.executable,
                            "-E",
                            "-B",
                            "-S",
                            str(Path(__file__).resolve()),
                            "--_worker",
                            str(job_path),
                        ],
                        cwd=self.root,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=error_log,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
                children.append((process, spec))
            while True:
                if time.monotonic() >= self.deadline:
                    raise TimeoutError("Experiment wall-time budget exhausted")
                if (
                    gate
                    and not gate.exists()
                    and all(Path(s["ready"]).exists() for _, s in children)
                ):
                    record["barrier_participants"] = [
                        read_json(Path(s["ready"])) for _, s in children
                    ]
                    gate.touch()
                    record["barrier_released"] = True
                if phase == "kill_writer" and Path(children[0][1]["ready"]).exists():
                    process, spec = children[0]
                    fault = read_json(Path(spec["ready"]))
                    require(process.poll() is None, "Writer exited before the parent could kill it")
                    killed_pid = self.kill(process, spec)  # No Python rollback/finally runs.
                    process.wait(timeout=3)
                    require(process.returncode != 0, "Killed writer exited successfully")
                    require(killed_pid == fault["pid"], "Did not target the actual SQLite writer")
                    record.update(
                        status="passed",
                        expected_terminations=1,
                        fault_point=fault,
                        killed_pid=killed_pid,
                        launcher_pid=process.pid,
                        killed_exit_code=process.returncode,
                    )
                    break
                if all(p.poll() is not None for p, _ in children):
                    break
                if any(p.poll() not in (None, 0) for p, _ in children):
                    raise RuntimeError(f"{phase} worker exited unexpectedly")
                time.sleep(0.01)
            if phase != "kill_writer":
                results = [read_json(Path(s["result"])) for _, s in children]
                record["workers"] = results
                require(
                    all(
                        p.returncode == 0 and r["status"] == "passed"
                        for (p, _), r in zip(children, results, strict=True)
                    ),
                    f"{phase} worker failure: {[r.get('error') for r in results]}",
                )
                if phase == "replay":
                    receipts = [r["evidence"]["receipt"] for r in results]
                    require(
                        all(receipt == receipts[0] for receipt in receipts),
                        "Concurrent receipts differ",
                    )
                if phase == "cas":
                    require(
                        sum("receipt" in r["evidence"] for r in results) == 1,
                        "CAS must have exactly one successful writer",
                    )
                    require(
                        sum("rejection" in r["evidence"] for r in results) == count - 1,
                        "CAS losers must specifically reject stale revisions",
                    )
                record["status"] = "passed"
        except Exception as exc:
            record["error"] = {"type": type(exc).__name__, "message": str(exc)}
            raise
        finally:
            for process, spec in children:
                if process.poll() is None:
                    self.kill(process, spec)
            cleanup_deadline = time.monotonic() + 5
            for process, _ in children:
                try:
                    process.wait(timeout=max(0.01, cleanup_deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    record.setdefault("cleanup_errors", []).append(process.pid)
                    record["status"] = "failed"
            if not record["workers"] and phase != "kill_writer":
                for process, spec in children:
                    result_path = Path(spec["result"])
                    if result_path.exists():
                        record["workers"].append(read_json(result_path))
                    else:
                        sample_path = Path(spec["samples"])
                        recovered = []
                        if sample_path.exists():
                            for line in sample_path.read_text(encoding="utf-8").splitlines():
                                try:
                                    recovered.append(json.loads(line))
                                except json.JSONDecodeError:
                                    break  # A kill may interrupt the final telemetry write.
                        record["workers"].append(
                            {
                                "pid": process.pid,
                                "status": "incomplete",
                                "samples": recovered,
                                "exit_code": process.returncode,
                            }
                        )
            record["child_exit_codes"] = {str(p.pid): p.returncode for p, _ in children}
            record["wall_seconds"] = time.monotonic() - start
            record["metrics"] = metrics([s for w in record["workers"] for s in w["samples"]])
        return record


def run_experiments(config):
    config = validate_config(config)  # Reject unsafe sizes before allocating files or processes.
    started, started_utc = time.monotonic(), datetime.now(UTC).isoformat()
    temporary_parent = Path(tempfile.gettempdir()).resolve()
    if str(temporary_parent).startswith(("\\\\", "//")):
        raise ValueError("A local temporary directory is required, not a network share")
    directory = Path(
        tempfile.mkdtemp(prefix="usmsb-collaboration-resilience-", dir=temporary_parent)
    )
    supervisor = Supervisor(directory, config, started + config["seconds"])
    report = {
        "schema": "usmsb.collaboration-resilience.v1",
        "status": "failed",
        "config": config,
        "hard_limits": LIMITS,
        "started_at_utc": started_utc,
        "evidence_directory": str(directory),
        "report_path": str(directory / "report.json"),
        "environment": {
            "python": sys.version,
            "sqlite": sqlite3.sqlite_version,
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
        },
        "harness_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "claims": {
            "protocol_stress_only": True,
            "long_term_emergence_completed": False,
            "autonomous_intelligence_demonstrated": False,
            "external_services_used": False,
        },
        "measurement_boundary": {
            "latency": "Completed apply() calls, including SQLite lock wait and receipt handling",
            "percentiles": "Nearest rank; all completed outcomes; raw per-worker samples retained",
            "throughput": (
                "Successful apply calls include replays, not unique commits or external work"
            ),
            "sample_window": (
                "First apply start to last completion; includes intervening gaps/checks"
            ),
            "incomplete": (
                "Killed/timed-out calls have no completed latency; never counted as success"
            ),
            "telemetry": (
                "Observed completed calls; JSONL flush follows timing; "
                "interrupted flush may lose a sample"
            ),
            "runtime": (
                "One global worker budget; cleanup may add up to 5 seconds plus OS scheduling"
            ),
            "concurrency_gate": (
                "Replay/CAS apply latency includes an injected barrier after real connection open; "
                "use load/revision_rounds metrics for uninstrumented apply latency"
            ),
            "scope": "One local host/filesystem; fixture actors controlled by one operator",
            "backup": "Quiescent checkpoint with explicit post-backup tail; no zero-RPO claim",
            "fault": "One process kill before commit; not host power loss or storage corruption",
        },
    }
    try:
        exported = supervisor.run("export")
        report["source_manifest"] = exported["workers"][0]["evidence"]["manifest"]
        supervisor.run("initialize")
        supervisor.run("replay", config["workers"])
        supervisor.run("cas", config["workers"])
        baseline = supervisor.run("fault_baseline")["workers"][0]["evidence"]
        supervisor.run("kill_writer")
        supervisor.run(
            "rollback_restart",
            baseline=baseline["baseline"],
            frozen_contract=baseline["frozen_contract"],
        )
        supervisor.run("load", config["workers"])
        supervisor.run("revision_rounds", config["workers"])
        supervisor.run("restart")
        supervisor.run("backup_restore")
        report["status"] = "passed"
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    completed = {phase["phase"] for phase in supervisor.phases}
    report["phases"] = supervisor.phases + [
        {"phase": phase, "status": "skipped"} for phase in PHASES if phase not in completed
    ]
    if any(phase["status"] != "passed" for phase in report["phases"]):
        report["status"] = "failed"
    samples = [s for phase in supervisor.phases for w in phase["workers"] for s in w["samples"]]
    report["metrics"] = metrics(samples)
    report["summary"] = {
        "passed_phases": sum(p["status"] == "passed" for p in report["phases"]),
        "failed_phases": sum(p["status"] == "failed" for p in report["phases"]),
        "skipped_phases": sum(p["status"] == "skipped" for p in report["phases"]),
        "incomplete_workers": sum(
            w["status"] == "incomplete" for p in supervisor.phases for w in p["workers"]
        ),
        "expected_killed_writers": sum(
            p.get("expected_terminations", 0) for p in supervisor.phases
        ),
    }
    report["finished_at_utc"] = datetime.now(UTC).isoformat()
    report["wall_seconds"] = time.monotonic() - started
    write_json(directory / "report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key, default in DEFAULTS.items():
        parser.add_argument(f"--{key}", type=int, default=default)
    parser.add_argument("--_worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args._worker:
        return worker_main(args._worker)
    try:
        report = run_experiments({key: getattr(args, key) for key in DEFAULTS})
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
