"""Real subprocess/SQLite evidence, plus bounded failure and timeout handling."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check_collaboration_resilience.py"


@pytest.fixture(scope="module")
def harness():
    spec = importlib.util.spec_from_file_location("collaboration_resilience_tests", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def report():
    result = subprocess.run(
        [
            sys.executable,
            "-E",
            "-B",
            str(SCRIPT),
            "--goals",
            "3",
            "--workers",
            "3",
            "--rounds",
            "2",
            "--seconds",
            "30",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=40,
    )
    evidence = json.loads(result.stdout)
    assert result.returncode == 0, (evidence.get("error"), evidence["phases"], result.stderr)
    assert evidence["status"] == "passed"
    assert json.loads(Path(evidence["report_path"]).read_text(encoding="utf-8")) == evidence
    return evidence


def phase(report, name):
    return next(item for item in report["phases"] if item["phase"] == name)


def evidence(report, name):
    return phase(report, name)["workers"][0]["evidence"]


def test_independent_processes_replay_one_receipt_and_one_cas_winner(report):
    replay, cas = phase(report, "replay"), phase(report, "cas")
    for group in (replay, cas):
        assert group["barrier_released"] is True
        assert len({w["pid"] for w in group["workers"]}) == 3
        assert len(group["barrier_participants"]) == 3
        assert all(w["sqlite_connection_open"] for w in group["barrier_participants"])
        assert {w["pid"] for w in group["barrier_participants"]} == {
            w["pid"] for w in group["workers"]
        }
        assert len({w["sqlite_database"] for w in group["barrier_participants"]}) == 1
        assert all(code == 0 for code in group["child_exit_codes"].values())
    receipts = [w["evidence"]["receipt"] for w in replay["workers"]]
    assert all(r == receipts[0] for r in receipts)
    assert receipts[0]["sequence"] == 1
    assert replay["metrics"]["success"] == 3
    assert replay["metrics"]["unique_successful_command_ids"] == 1
    starts = [s["started_monotonic"] for w in replay["workers"] for s in w["samples"]]
    finishes = [s["finished_monotonic"] for w in replay["workers"] for s in w["samples"]]
    assert max(starts) < min(finishes)  # All calls are in flight before any can commit.
    assert cas["metrics"]["success"] == 1
    assert cas["metrics"]["expected_rejection"] == 2
    assert cas["metrics"]["unexpected_failure"] == 0
    winner = evidence(report, "fault_baseline")["cas_winner"]
    assert winner["sequence"] == 2
    assert winner["result"]["goal"]["revision"] == 2


def test_actual_uncommitted_writer_is_killed_and_all_state_rolls_back(report):
    fault = phase(report, "kill_writer")
    point = fault["fault_point"]
    assert fault["killed_exit_code"] != 0
    assert fault["killed_pid"] == point["pid"]
    assert point["in_transaction"] is True
    assert point["rollback_journal_bytes"] > 512
    assert point["uncommitted_receipt"]["sequence"] == 6
    baseline = evidence(report, "fault_baseline")["baseline"]
    recovery = evidence(report, "rollback_restart")
    assert recovery["after_recovery"] == baseline
    assert baseline["rows"]["collaboration_commands"] == 5
    assert recovery["integrity_check"] == ["ok"]
    assert recovery["retry_committed_once"] is True
    assert recovery["retry_receipt"]["sequence"] == 6
    directory = Path(report["evidence_directory"])
    assert not (directory / "kill_writer-0.result.json").exists()
    assert not (directory / "kill_writer-0.samples.jsonl").exists()


def test_n_goals_controlled_revisions_and_history_survive_new_process(report):
    load = phase(report, "load")
    assert sorted(g for w in load["workers"] for g in w["evidence"]["created_goals"]) == [
        "load:0",
        "load:1",
        "load:2",
    ]
    rounds = phase(report, "revision_rounds")
    assert sum(w["evidence"]["completed_goal_rounds"] for w in rounds["workers"]) == 6
    assert rounds["metrics"]["expected_rejection"] == 6
    assert rounds["metrics"]["success"] == 30
    restart = evidence(report, "restart")
    assert restart["history_verified"] is True
    assert restart["event_count"] == 48  # 6 fault setup/retry + 3 * (6 setup + 4 * 2 rounds).
    assert restart["snapshot"]["rows"]["collaboration_revision_impacts"] == 19
    assert phase(report, "restart")["workers"][0]["pid"] not in {
        worker["pid"] for worker in rounds["workers"]
    }


def test_backup_recovers_exact_checkpoint_not_post_backup_tail(report):
    restored = evidence(report, "backup_restore")
    assert restored["checkpoint"] == evidence(report, "restart")["snapshot"]
    assert restored["checkpoint_sequence"] == 48
    assert restored["source_tail_sequence"] == restored["restored_write_sequence"] == 49
    assert restored["excluded_post_backup_commands"] == ["backup:tail"]
    assert restored["restored_replay_unchanged"] is True
    assert all(result == ["ok"] for result in restored["integrity_checks"].values())


def test_report_has_reproducibility_inputs_honest_metrics_and_claim_boundaries(report):
    assert report["summary"] == {
        "passed_phases": 11,
        "failed_phases": 0,
        "skipped_phases": 0,
        "incomplete_workers": 0,
        "expected_killed_writers": 1,
    }
    assert report["claims"] == {
        "protocol_stress_only": True,
        "long_term_emergence_completed": False,
        "autonomous_intelligence_demonstrated": False,
        "external_services_used": False,
    }
    manifest = report["source_manifest"]
    assert len(manifest["sha256"]["autonomy/journal.py"]) == 64
    assert len(manifest["content_digest"]) == 64
    assert len(report["harness_sha256"]) == 64
    assert {"python", "sqlite", "platform", "cpu_count"} <= report["environment"].keys()
    assert 0 < report["wall_seconds"] < 35
    directory = Path(report["evidence_directory"])
    assert directory.parent == Path(tempfile.gettempdir()).resolve()
    assert directory.name.startswith("usmsb-collaboration-resilience-")
    metrics = report["metrics"]
    assert metrics["success"] == 61
    assert metrics["expected_rejection"] == 8
    assert metrics["unexpected_failure"] == 0
    assert metrics["completed_apply_attempts"] == 69
    assert metrics["unique_successful_command_ids"] == 50  # Includes two recovery probes.
    latency = metrics["latency_ms"]
    assert latency["count"] == 69
    assert (
        0 <= latency["min"] <= latency["p50"] <= latency["p95"] <= latency["p99"] <= latency["max"]
    )
    assert metrics["sample_window_seconds"] > 0
    assert metrics["successful_apply_calls_per_second"] == pytest.approx(
        61 / metrics["sample_window_seconds"],
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"goals": 0},
        {"goals": 65},
        {"workers": 1},
        {"workers": 5},
        {"rounds": 0},
        {"rounds": 33},
        {"goals": 64, "rounds": 5},
        {"seconds": 4},
        {"seconds": 121},
        {"goals": True},
        {"workers": 2.0},
    ],
)
def test_unsafe_parameters_rejected_before_files_or_processes(harness, monkeypatch, changes):
    def forbidden(*args, **kwargs):
        pytest.fail("Unsafe request allocated an experiment directory")

    monkeypatch.setattr(harness.tempfile, "mkdtemp", forbidden)
    with pytest.raises(ValueError):
        harness.run_experiments({**harness.DEFAULTS, **changes})


def test_invalid_cli_returns_nonzero_without_claiming_success():
    result = subprocess.run(
        [sys.executable, "-E", "-B", str(SCRIPT), "--workers", "99"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert not result.stdout
    assert "workers must be an integer" in result.stderr


def test_worker_failure_is_reported_and_later_phases_are_skipped(harness, monkeypatch):
    original = harness.Supervisor.run

    def fail_exported_copy(self, name, *args, **kwargs):
        result = original(self, name, *args, **kwargs)
        if name == "export":
            # Fault injection touches only this run's disposable exported package.
            module = self.root / "resilience_core/autonomy/journal.py"
            with module.open("a", encoding="utf-8") as stream:
                stream.write("\nraise RuntimeError('injected local test regression')\n")
        return result

    monkeypatch.setattr(harness.Supervisor, "run", fail_exported_copy)
    result = harness.run_experiments({**harness.DEFAULTS, "goals": 1, "rounds": 1})
    assert result["status"] == "failed"
    assert result["summary"]["failed_phases"] == 1
    assert result["summary"]["skipped_phases"] == 9
    failed = phase(result, "initialize")
    assert failed["workers"][0]["status"] == "failed"
    assert "injected local test regression" in failed["workers"][0]["error"]["message"]
    assert result["metrics"]["success"] == 0
    assert Path(result["report_path"]).exists()


def test_global_deadline_kills_workers_and_preserves_completed_samples(harness, monkeypatch):
    original = harness.Supervisor.run

    def block_after_one_command(self, name, *args, **kwargs):
        if name == "load":
            # This is a test-local fault in the frozen export, not a production edit.
            module = self.root / "resilience_core/autonomy/journal.py"
            with module.open("a", encoding="utf-8") as stream:
                stream.write(
                    "\n_original_apply = CollaborationJournal.apply\n"
                    "def _blocked_apply(self, actor, command_id, operation, payload):\n"
                    "    if operation == 'commitment.propose':\n"
                    "        __import__('time').sleep(60)\n"
                    "    return _original_apply(self, actor, command_id, operation, payload)\n"
                    "CollaborationJournal.apply = _blocked_apply\n"
                )
            self.deadline = time.monotonic() + 1.5
        return original(self, name, *args, **kwargs)

    monkeypatch.setattr(harness.Supervisor, "run", block_after_one_command)
    started = time.monotonic()
    result = harness.run_experiments({**harness.DEFAULTS, "goals": 2, "rounds": 1})
    assert time.monotonic() - started < 15
    assert result["status"] == "failed"
    blocked = phase(result, "load")
    assert blocked["error"]["type"] == "TimeoutError"
    assert blocked["metrics"]["success"] == 2
    assert result["summary"]["incomplete_workers"] == 2
    assert result["summary"]["skipped_phases"] == 3
    assert all(code is not None and code != 0 for code in blocked["child_exit_codes"].values())
    assert not blocked.get("cleanup_errors")
    assert all(w["status"] == "incomplete" for w in blocked["workers"])
    # Reopening and writing verifies that killed children left no SQLite writer lock behind.
    directory = Path(result["evidence_directory"])
    with harness.closing(harness.sqlite3.connect(directory / "journal.sqlite", timeout=1)) as db:
        db.execute("BEGIN IMMEDIATE")
        db.rollback()
