"""Neutral profiles and a real cross-process, cross-language protocol path."""

import importlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def core(tmp_path_factory):
    spec = importlib.util.spec_from_file_location(
        "open_core_exporter", ROOT / "scripts/export_autonomy.py"
    )
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    folder = tmp_path_factory.mktemp("open_core")
    exporter.export(folder / "usmsb_core")
    sys.path.insert(0, str(folder))
    yield importlib.import_module("usmsb_core.autonomy"), folder
    sys.path.remove(str(folder))


def test_profiles_are_explicit_and_legacy_is_unchanged(core):
    api, _ = core
    criteria = [{"id": "c", "description": "Check a measurement"}]
    legacy = api.goal_contract(criteria, ["reviewer"])
    assert legacy["schema"] == "usmsb.goal-contract.v1"
    assert set(legacy) == {"schema", "criteria", "verifier_ids", "independent_review"}
    peer = api.goal_contract(criteria, ["recipient"], profile=api.PEER_COLLABORATION_V1)
    assert peer["schema"] == "usmsb.goal-contract.v2" and not peer["independent_review"]
    assert peer["review_mode"] == "peer"
    reference = api.world_reference(
        "research:lab", "dataset/a", "observation", "測定/1", profile=api.OPEN_COLLABORATION_V1
    )
    assert reference.startswith("usmsb-ref:") and "dataset%2Fa" in reference
    assert (
        api.entity_reference("independent-host", "lab", "Information", "sample")["authority"]
        == "independent-host"
    )
    with pytest.raises(api.ContractError):
        api.world_reference("research:lab", "dataset/a", "observation", "sample")
    for profile in ({"id": "untrusted"}, "open", 1):
        with pytest.raises(api.ContractError):
            api.goal_contract(criteria, ["reviewer"], profile=profile)
    for options in (
        {"review_mode": []},
        {"id": " spaced "},
        {"version": True},
        {"media_types": ["*"]},
    ):
        with pytest.raises(api.ContractError):
            api.CollaborationProfile(**{"id": "local:policy", **options})


def test_binary_artifact_contract_and_limits(core):
    api, _ = core
    artifact = api.artifact_reference("data", "image/png", "a" * 64, "urn:sha256:" + "a" * 64, 128)
    value = {
        "state": "completed",
        "run_ref": "other-agent:operation-1",
        "output": {"artifacts": [artifact]},
    }
    assert api.remote_status(value, profile=api.OPEN_COLLABORATION_V1) == value
    with pytest.raises(api.ContractError):
        api.remote_status(value)
    for sha, size, uri in (
        ("f" * 63, 1, "urn:x"),
        ("f" * 64, True, "urn:x"),
        ("f" * 64, 1, "relative/path"),
    ):
        with pytest.raises(api.ContractError):
            api.artifact_reference("x", "application/pdf", sha, uri, size)
    small = api.CollaborationProfile("local:small", max_criteria=1, max_steps=1)
    with pytest.raises(api.ContractError):
        api.goal_contract(
            [{"id": "a", "description": "a"}, {"id": "b", "description": "b"}], ["v"], profile=small
        )
    with pytest.raises(api.ContractError):
        api.plan_steps([{"id": "a", "title": "a"}, {"id": "b", "title": "b"}], profile=small)


def test_cas_and_replay_across_instances(core, tmp_path):
    api, _ = core
    config = {
        "host_id": "host",
        "principals": {
            "owner": {"controller": "operator", "operations": ["goal.create", "goal.revise"]}
        },
    }
    a = api.CollaborationJournal(tmp_path / "ledger.db", **config)
    intent = {
        "title": "Initial",
        "description": "A research intent",
        "domain": "research",
        "success_criteria": "Observe results",
    }
    first = a.apply("owner", "create", "goal.create", {"id": "g", "intent": intent})
    b = api.CollaborationJournal(tmp_path / "ledger.db", **config)
    assert b.apply("owner", "create", "goal.create", {"id": "g", "intent": intent}) == first

    def revise(pair):
        ledger, title = pair
        try:
            return ledger.apply(
                "owner",
                title,
                "goal.revise",
                {
                    "goal_id": "g",
                    "base_revision": 1,
                    "changes": {"title": title},
                    "reason": "new evidence",
                    "evidence_ids": ["observation:1"],
                },
            )
        except api.ContractError:
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(revise, [(a, "one"), (b, "two")]))
    assert sum(r is not None for r in results) == 1
    assert a.goal_version("g", 1)["intent"]["title"] == "Initial"
    assert a.get("goal", "g")["revision"] == 2
    assert len(a.events()) == 2


def test_external_javascript_client_survives_host_restart(core, tmp_path):
    _, folder = core
    node = shutil.which("node")
    if node is None:
        pytest.fail("Node.js is required for the open collaboration conformance gate")
    # Remove machine-specific Python overrides but provide ONLY exported core.
    env = {k: v for k, v in os.environ.items() if k.upper() not in {"PYTHONHOME", "PYTHONPATH"}}
    env["PYTHONPATH"] = str(folder)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    reports = []
    for _ in range(2):
        host = subprocess.Popen(
            [
                sys.executable,
                "-S",
                str(ROOT / "examples/open_collaboration/host.py"),
                "--db",
                str(tmp_path / "ledger.db"),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                startup = executor.submit(host.stdout.readline)
                try:
                    line = startup.result(timeout=15)
                except TimeoutError:
                    host.kill()
                    raise
            assert line, host.stderr.read()
            url = json.loads(line)["url"]
            result = subprocess.run(
                [node, str(ROOT / "examples/open_collaboration/client.mjs"), url],
                capture_output=True,
                text=True,
                timeout=40,
            )
            assert result.returncode == 0, result.stderr
            reports.append(json.loads(result.stdout))
        finally:
            host.terminate()
            host.communicate(timeout=10)
    assert reports[0] == reports[1]
    assert reports[0]["adopted_goal_revision"] == 2
    assert reports[0]["model_calls"] == reports[0]["payments"] == 0
