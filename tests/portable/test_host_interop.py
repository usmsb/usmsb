"""Exported stdlib gateway: actual token hashing/bytes, synthetic controllers.

This is NOT evidence of independently operated organizations or real payments.
"""

import hashlib
import importlib
import importlib.util
import io
import sys
from copy import deepcopy
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def api(tmp_path_factory):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "interop_export", root / "scripts/export_autonomy.py"
    )
    exporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(exporter)
    folder = tmp_path_factory.mktemp("interop_export")
    exporter.export(folder / "portable_interop")
    sys.path.insert(0, str(folder))
    try:
        yield importlib.import_module("portable_interop.autonomy.interop")
    finally:
        sys.path.remove(str(folder))
        for name in tuple(sys.modules):
            if name == "portable_interop" or name.startswith("portable_interop."):
                del sys.modules[name]


def token(actor):
    # Public fixed test material, never a production default.
    return f"TEST-ONLY-{actor}-" + "x" * 40


@pytest.fixture
def system(api, tmp_path):
    journal_api = importlib.import_module("portable_interop.autonomy.journal")
    grants = {
        actor: {
            "controller": f"test-controller:{actor}",
            "operations": sorted(journal_api.OPERATIONS),
        }
        for actor in ("owner", "provider", "reviewer")
    }
    journal = journal_api.CollaborationJournal(
        tmp_path / "journal.db", host_id="local-test", principals=grants
    )
    now = [100]
    auth = api.TokenAuthenticator(
        {
            hashlib.sha256(token(actor).encode()).hexdigest(): {
                "actor": actor,
                "not_before": 99,
                "expires_at": 200,
            }
            for actor in grants
        },
        clock=lambda: now[0],
    )
    contents = {"urn:test:artifact": b"reproducible research\n"}
    resolved, verified = [], []
    verdict = [True]

    def resolver(actor, descriptor):
        resolved.append((actor, descriptor))
        assert actor == "provider"
        return io.BytesIO(contents[descriptor["uri"]])

    def evidence(actor, operation, payload):
        verified.append((actor, operation, deepcopy(payload)))
        return verdict[0]

    host = api.AuthenticatedCollaborationHost(
        journal,
        authenticate=auth,
        resolve_artifact=resolver,
        verify_evidence=evidence,
        max_artifact_bytes=1024,
    )
    profile = host.offer()["profiles"]["usmsb:open-collaboration"]
    hello = {
        "schema": "usmsb.collaboration-hello.v1",
        "protocols": [api.COMMAND_SCHEMA],
        "profile": {"id": profile["id"], "version": 1, "sha256": api.digest(profile)},
        "required_features": list(api.FEATURES),
    }
    return {
        "host": host,
        "journal": journal,
        "hello": hello,
        "contents": contents,
        "now": now,
        "resolved": resolved,
        "verified": verified,
        "verdict": verdict,
    }


def envelope(api, system, command_id, operation, payload):
    agreement = api.negotiate(system["host"].offer(), system["hello"])
    return {
        "schema": api.COMMAND_SCHEMA,
        "agreement_hash": agreement["agreement_hash"],
        "command_id": command_id,
        "operation": operation,
        "payload": payload,
    }


def send(api, system, actor, cid, operation, payload):
    return system["host"].apply(
        token(actor), system["hello"], envelope(api, system, cid, operation, payload)
    )


def create_goal(api, system):
    payload = {
        "id": "g",
        "intent": {
            "title": "Research",
            "description": "Reproduce a measurement",
            "domain": "research",
            "success_criteria": "Agreed review passes",
        },
    }
    return send(api, system, "owner", "create", "goal.create", payload)


def active_commitment(api, system):
    create_goal(api, system)
    terms = send(
        api,
        system,
        "owner",
        "propose",
        "commitment.propose",
        {
            "id": "c",
            "goal_id": "g",
            "goal_revision": 1,
            "provider_id": "provider",
            "description": "Measurement",
            "terms": "No money; no model calls",
            "criteria": [{"id": "replicable", "description": "Replicable from supplied bytes"}],
            "verifier_ids": ["reviewer"],
            "profile_id": "usmsb:open-collaboration",
        },
    )["result"]["terms_hash"]
    for actor in ("owner", "provider"):
        send(
            api,
            system,
            actor,
            f"accept:{actor}",
            "commitment.accept",
            {"commitment_id": "c", "terms_hash": terms},
        )
    data = system["contents"]["urn:test:artifact"]
    descriptor = api.artifact_reference(
        "a", "text/plain", hashlib.sha256(data).hexdigest(), "urn:test:artifact", len(data)
    )
    return terms, descriptor


def test_authenticated_complete_flow_and_identical_replay(api, system):
    terms, descriptor = active_commitment(api, system)
    payload = {"commitment_id": "c", "terms_hash": terms, "artifact": descriptor}
    submitted = send(api, system, "provider", "submit", "artifact.submit", payload)
    assert len(system["resolved"]) == 1
    system["contents"].clear()  # Original receipt survives unavailable object storage.
    assert send(api, system, "provider", "submit", "artifact.submit", payload) == submitted
    assert len(system["resolved"]) == 1
    send(
        api,
        system,
        "reviewer",
        "review",
        "review.record",
        {
            "id": "r",
            "artifact_id": "a",
            "artifact_sha256": descriptor["sha256"],
            "terms_hash": terms,
            "checks": [
                {
                    "criterion_id": "replicable",
                    "status": "pass",
                    "evidence_ids": ["test:review"],
                    "reason": "Reproduced from the checked bytes",
                }
            ],
        },
    )
    adopted = send(
        api,
        system,
        "owner",
        "adopt",
        "adoption.record",
        {
            "id": "ad",
            "artifact_id": "a",
            "artifact_sha256": descriptor["sha256"],
            "terms_hash": terms,
            "evidence_ids": ["test:adoption"],
            "statement": "Locally used result",
        },
    )
    assert adopted["result"]["goal_revision"] == 1
    assert [item[1] for item in system["verified"]] == ["review.record", "adoption.record"]
    assert system["journal"].get("commitment", "c")["status"] == "adopted"


@pytest.mark.parametrize(
    "mutation",
    ["major", "profile-version", "profile-hash", "feature", "unknown-field", "bool-version"],
)
def test_negotiation_fails_closed(api, system, mutation):
    hello = deepcopy(system["hello"])
    if mutation == "major":
        hello["protocols"] = ["usmsb.collaboration-command.v999"]
    elif mutation == "profile-version":
        hello["profile"]["version"] = 2
    elif mutation == "profile-hash":
        hello["profile"]["sha256"] = "0" * 64
    elif mutation == "feature":
        hello["required_features"].append("automatic-payment")
    elif mutation == "bool-version":
        hello["profile"]["version"] = True
    else:
        hello["controller"] = "attacker"
    with pytest.raises(api.ContractError):
        api.negotiate(system["host"].offer(), hello)
    assert system["journal"].events() == []


@pytest.mark.parametrize("mutation", ["actor", "controller", "schema", "agreement_hash"])
def test_client_cannot_inject_identity_or_downgrade(api, system, mutation):
    packet = envelope(api, system, "cmd", "goal.create", {})
    packet[mutation] = "forged"
    with pytest.raises(api.ContractError):
        system["host"].apply(token("owner"), system["hello"], packet)
    assert system["journal"].events() == []


@pytest.mark.parametrize("when", [98, 200, 300])
def test_expired_or_not_yet_valid_credentials_cannot_replay(api, system, when):
    first = create_goal(api, system)
    system["now"][0] = when
    with pytest.raises(api.ContractError, match="Authentication denied"):
        create_goal(api, system)
    assert system["journal"].events() == [first]


@pytest.mark.parametrize("credential", [None, {}, "short", "wrong" * 20])
def test_bad_credentials_are_rejected_without_writes(api, system, credential):
    with pytest.raises(api.ContractError):
        system["host"].apply(
            credential, system["hello"], envelope(api, system, "cmd", "goal.create", {})
        )
    assert system["journal"].events() == []


@pytest.mark.parametrize("verdict", [False, None, 1, "verified", {}])
def test_evidence_must_be_strictly_verified(api, system, verdict):
    first = create_goal(api, system)
    system["verdict"][0] = verdict
    with pytest.raises(api.ContractError, match="Evidence verification denied"):
        send(
            api,
            system,
            "owner",
            "revision",
            "goal.revise",
            {
                "goal_id": "g",
                "base_revision": 1,
                "changes": {"title": "Revised"},
                "reason": "Observation",
                "evidence_ids": ["test:observation"],
            },
        )
    assert system["journal"].events() == [first]
    assert system["journal"].get("goal", "g")["revision"] == 1


@pytest.mark.parametrize("mutation", ["hash", "short", "long", "budget", "schema"])
def test_artifact_bytes_checked_before_receipt(api, system, mutation):
    terms, descriptor = active_commitment(api, system)
    if mutation == "hash":
        descriptor["sha256"] = "0" * 64
    elif mutation == "short":
        system["contents"]["urn:test:artifact"] = b""
    elif mutation == "long":
        system["contents"]["urn:test:artifact"] *= 2
    elif mutation == "budget":
        descriptor["size_bytes"] = 1025
    else:
        descriptor["schema"] = "unknown"
    before = system["journal"].events()
    with pytest.raises(api.ContractError):
        send(
            api,
            system,
            "provider",
            "submit",
            "artifact.submit",
            {"commitment_id": "c", "terms_hash": terms, "artifact": descriptor},
        )
    assert system["journal"].events() == before
    if mutation in {"budget", "schema"}:
        assert system["resolved"] == []


def test_callbacks_cannot_mutate_verified_command(api, system):
    create_goal(api, system)

    def verify(actor, operation, payload):
        payload["changes"]["title"] = "tampered"
        return True

    system["host"]._verify_evidence = verify
    result = send(
        api,
        system,
        "owner",
        "revision",
        "goal.revise",
        {
            "goal_id": "g",
            "base_revision": 1,
            "changes": {"title": "Revised"},
            "reason": "Observation",
            "evidence_ids": ["test:observation"],
        },
    )
    assert result["result"]["goal"]["version"]["intent"]["title"] == "Revised"


def test_no_unnegotiated_profile_can_be_proposed(api, system):
    create_goal(api, system)
    with pytest.raises(api.ContractError, match="Unnegotiated profile"):
        send(api, system, "owner", "propose", "commitment.propose", {"profile_id": "self-review"})


def test_no_cross_actor_replay(api, system):
    create_goal(api, system)
    packet = envelope(
        api,
        system,
        "create",
        "goal.create",
        {
            "id": "g",
            "intent": {
                "title": "Research",
                "description": "Reproduce a measurement",
                "domain": "research",
                "success_criteria": "Agreed review passes",
            },
        },
    )
    with pytest.raises(api.ContractError, match="Command id conflict"):
        system["host"].apply(token("provider"), system["hello"], packet)


def test_resolver_binary_stream_and_empty_objects(api):
    empty = api.artifact_reference(
        "empty", "text/plain", hashlib.sha256(b"").hexdigest(), "urn:empty", 0
    )
    assert api.verify_artifact_bytes(empty, io.BytesIO(b""), max_bytes=0)["size_bytes"] == 0
    with pytest.raises(api.ContractError, match="binary stream"):
        api.verify_artifact_bytes(empty, io.StringIO(""))
