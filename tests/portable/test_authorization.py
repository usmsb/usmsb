"""Synthetic confidential source; actual SQLite, computation and races."""
import importlib
import importlib.util
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor
import pytest


@pytest.fixture(scope="module")
def auth(tmp_path_factory):
    script = Path(__file__).resolve().parents[2] / "scripts/export_autonomy.py"
    spec = importlib.util.spec_from_file_location("export_authorization", script)
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    root = tmp_path_factory.mktemp("authorization")
    exporter.export(root / "portable_authorization")
    sys.path.insert(0, str(root))
    try:
        yield importlib.import_module("portable_authorization.autonomy.authorization")
    finally:
        sys.path.remove(str(root))


def vault(auth, tmp_path, **changes):
    v = auth.PrivateDataVault(tmp_path / "private.sqlite", "rights-owner", {"summary": lambda data, args: {"count": len(data["values"]), "sum": sum(data["values"]), "original": data}}, clock=lambda: 1000, **changes)
    v.add("rights-owner", data_id="data-v1", original={"private-name": "SECRET", "values": [1, 2, 3]}, title="Authorized numeric summary", rights="Test owner permits only aggregates")
    return v


def grant(v, **changes):
    return v.grant(changes.pop("actor", "rights-owner"), **{
        "grant_id": "root", "data_id": "data-v1", "grantee": "researcher", "purposes": ["research"],
        "operations": ["summary"], "disclosures": ["count", "sum"], "max_calls": 4, "max_units": 4,
        "not_before": 900, "expires_at": 1100, **changes})


def execute(v, **changes):
    return v.execute(changes.pop("actor", "researcher"), **{"grant_id": "root", "request_id": "req-1", "operation": "summary", "purpose": "research", "disclosures": ["count"], "arguments": {}, "units": 1, **changes})


def test_private_original_only_seen_by_owner_installed_program(auth, tmp_path):
    v = vault(auth, tmp_path)
    grant(v)
    public = v.metadata("data-v1")
    assert "SECRET" not in str(public) and "values" not in public
    with pytest.raises(ValueError):
        execute(v, actor="stranger")
    with pytest.raises(ValueError):
        execute(v, disclosures=["original"])
    result = execute(v)
    assert result["state"] == "completed" and result["output"] == {"count": 3}
    assert result["elapsed_ms"] >= 0 and "SECRET" not in str(result)
    assert execute(v) == result
    with pytest.raises(ValueError):
        execute(v, arguments={"changed": True})
    with pytest.raises(ValueError):
        v.add("stranger", data_id="data-v2", original={}, title="Not mine", rights="none")


@pytest.mark.parametrize("changes", [
    {"purposes": ["marketing"]}, {"operations": ["upload"]}, {"disclosures": ["original"]},
    {"max_calls": 5}, {"max_units": 5}, {"expires_at": 1101}, {"not_before": 899}, {"data_id": "other-data"},
])
def test_delegation_never_expands_authority(auth, tmp_path, changes):
    v = vault(auth, tmp_path)
    grant(v)
    with pytest.raises(ValueError):
        grant(v, actor="researcher", grant_id="child", grantee="reviewer", parent_id="root", **changes)


def test_suballocations_prevent_double_commitment_and_root_use(auth, tmp_path):
    v = vault(auth, tmp_path)
    grant(v)
    grant(v, actor="researcher", grant_id="child", grantee="reviewer", parent_id="root", max_calls=3, max_units=3)
    execute(v)
    with pytest.raises(ValueError, match="exhausted"):
        execute(v, request_id="req-2")
    with pytest.raises(ValueError, match="remaining allocation"):
        grant(v, actor="researcher", grant_id="child-2", grantee="new-reviewer", parent_id="root", max_calls=1, max_units=1)
    assert execute(v, actor="reviewer", grant_id="child", request_id="child-work")["state"] == "completed"
    reopened = vault(auth, tmp_path)
    assert execute(reopened) == execute(v)
    with pytest.raises(ValueError):
        execute(reopened, request_id="req-new")


def test_parent_revocation_denies_descendants_and_replay_without_claiming_recall(auth, tmp_path):
    v = vault(auth, tmp_path)
    grant(v)
    grant(v, actor="researcher", grant_id="child", grantee="reviewer", parent_id="root", max_calls=1, max_units=1)
    result = execute(v, actor="reviewer", grant_id="child")
    assert result["output"] == {"count": 3}
    revoked = v.revoke("rights-owner", "root", "Owner withdrew the license")
    assert revoked["already_disclosed"] == "cannot_be_recalled"
    with pytest.raises(ValueError):
        execute(v, actor="reviewer", grant_id="child")
    with pytest.raises(ValueError):
        execute(v, request_id="new")


def test_unknown_call_never_reexecuted(auth, tmp_path):
    v = vault(auth, tmp_path)
    grant(v)
    once = execute(v)
    with v.store.transaction() as db:
        db.execute("UPDATE data_calls SET state='reserved',receipt=NULL WHERE id='req-1'")
    assert execute(v)["state"] == "unknown"
    assert execute(v)["automatic_retry"] is False
    assert once["state"] == "completed"  # interrupted receipt is not reconstructed as success


def test_concurrent_same_id_calls_only_execute_once(auth, tmp_path):
    calls = []
    v = vault(auth, tmp_path)
    v.processors["summary"] = lambda data, args: calls.append(1) or {"count": 3}
    grant(v)
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(lambda _: execute(v), range(10)))
    assert len(calls) == 1
    assert {r["state"] for r in results} <= {"completed", "unknown"}
    assert execute(v)["state"] == "completed"


@pytest.mark.parametrize("verdict", [False, None, "true", 1, {}])
def test_proofs_require_strict_verification(auth, verdict):
    registry = auth.ProofRegistry()
    registry.register("test-proof", "test-v1", lambda p, c: verdict)
    proof = {"type": "test-proof", "claim_hash": auth.fingerprint({"x": 1}), "scope": "integrity", "expires_at": 1100}
    with pytest.raises(ValueError):
        registry.verify(proof, claim={"x": 1}, scope="integrity", now=1000).require_verified()


def test_unsupported_zk_expired_and_wrong_scope_proofs_fail_closed(auth, tmp_path):
    registry = auth.ProofRegistry()
    assert registry.verify({"type": "zk"}, claim={}, scope="research", now=1000).status == "unsupported"
    registry.register("owner-check", "test-v1", lambda p, c: True)
    valid = {"type": "owner-check", "claim_hash": auth.fingerprint({}), "scope": "research", "expires_at": 1100}
    assert registry.verify(valid, claim={}, scope="research", now=1000).status == "verified"
    for proof in ({**valid, "scope": "clinical-efficacy"}, {**valid, "expires_at": 999}, {**valid, "claim_hash": "fake"}):
        assert registry.verify(proof, claim={}, scope="research", now=1000).status == "invalid"
    v = vault(auth, tmp_path)
    grant(v)
    with pytest.raises(ValueError):
        execute(v, proof={"type": "zk", "proof": [1, 2, 3]})
    with pytest.raises(ValueError, match="rate"):
        execute(v, units=0)


def test_revoked_during_compute_prevents_disclosure(auth, tmp_path):
    v = vault(auth, tmp_path)
    grant(v)
    def processor(data, args):
        v.revoke("rights-owner", "root", "Concurrent withdrawal")
        return {"count": 3}
    v.processors["summary"] = processor
    receipt = execute(v)
    assert receipt["state"] == "revoked" and receipt["output"] is None
