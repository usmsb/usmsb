"""Explicit protocol agreement and an authenticated host boundary (stdlib only).

Transport, TLS, tenant routing, rate limits and identity enrollment are the
embedding host's responsibility. Tokens prove possession, not the independence
of organizations. Evidence callbacks are trusted policy, not client plugins.
No URI is fetched, code executed, credential persisted, or payment performed.
"""

import hashlib
import hmac
import json
import re
import time

from .contracts import ContractError, _check, _ids, _text
from .evolution import fingerprint
from .journal import canonical, digest, fields
from .profiles import CollaborationProfile, artifact_reference

COMMAND_SCHEMA = "usmsb.collaboration-command.v1"
FEATURES = ("durable-idempotency", "evidence-gated", "frozen-consent", "goal-revision-cas")


def _snapshot(value):
    return json.loads(canonical(value))


def protocol_offer(configuration):
    """Public metadata, not credentials or the private principal directory."""
    return {
        "schema": "usmsb.collaboration-offer.v1",
        "host_id": configuration["host_id"],
        "configuration_hash": fingerprint(configuration),
        "protocols": [COMMAND_SCHEMA],
        "features": list(FEATURES),
        "profiles": _snapshot(configuration["profiles"]),
    }


def negotiate(offer, hello):
    """Select an exact installed profile; never silently weaken review rules.

    Host recomputes this from its own offer on every request. Clients must pin
    host/TLS identity, inspect the offer and compare the agreement themselves.
    A matching hash is integrity binding, not a signature or access grant.
    """
    offer, hello = _snapshot(offer), _snapshot(hello)
    fields(offer, ("schema", "host_id", "configuration_hash", "protocols", "features", "profiles"))
    fields(hello, ("schema", "protocols", "profile", "required_features"))
    _check(offer["schema"] == "usmsb.collaboration-offer.v1", "Unsupported offer schema")
    _check(hello["schema"] == "usmsb.collaboration-hello.v1", "Unsupported hello schema")
    _check(COMMAND_SCHEMA in _ids(offer["protocols"], 16), "Unsupported host protocol")
    _check(COMMAND_SCHEMA in _ids(hello["protocols"], 16), "No compatible protocol")
    required = _ids(hello["required_features"], 32)
    supported = _ids(offer["features"], 32)
    _check(set(required) <= set(supported) <= set(FEATURES), "Unsupported required feature")
    chosen = hello["profile"]
    fields(chosen, ("id", "version", "sha256"))
    _check(type(chosen["version"]) is int, "Invalid profile version")
    _check(type(offer["profiles"]) is dict, "Invalid installed profiles")
    profile = offer["profiles"].get(_text(chosen["id"], 180))
    _check(profile is not None, "Profile not installed")
    _check(
        profile["version"] == chosen["version"] and digest(profile) == chosen["sha256"],
        "Profile semantics or version mismatch",
    )
    result = {
        "schema": "usmsb.collaboration-agreement.v1",
        "host_id": offer["host_id"],
        "offer_hash": digest(offer),
        "hello_hash": digest(hello),
        "protocol": COMMAND_SCHEMA,
        "profile": chosen,
        "required_features": sorted(required),
    }
    return {**result, "agreement_hash": digest(result)}


class TokenAuthenticator:
    """Host-installed SHA256 token allowlist with expiry and no default tokens.

    Provision independent high-entropy (>=32-byte) random tokens over a secure
    channel; never use passwords or client-selected actor/controller mappings.
    Replace/revoke credentials at the host; existing receipts still require a
    currently valid credential. This object does not log raw credentials.
    """

    def __init__(self, entries, *, clock=time.time):
        entries = _snapshot(entries)
        _check(type(entries) is dict and 1 <= len(entries) <= 1024, "Install bounded token hashes")
        for hashed, grant in entries.items():
            _check(bool(re.fullmatch(r"[0-9a-f]{64}", hashed)), "Invalid credential hash")
            fields(grant, ("actor", "not_before", "expires_at"))
            _check(_text(grant["actor"], 180) == grant["actor"], "Noncanonical actor")
            _check(
                type(grant["not_before"]) is int
                and type(grant["expires_at"]) is int
                and 0 <= grant["not_before"] < grant["expires_at"],
                "Invalid credential lifetime",
            )
        self._entries = entries
        self._clock = clock

    def __call__(self, token):
        _check(type(token) is str and 32 <= len(token) <= 4096, "Authentication denied")
        hashed = hashlib.sha256(token.encode()).hexdigest()
        now = self._clock()
        for expected, grant in self._entries.items():
            if (
                hmac.compare_digest(expected, hashed)
                and grant["not_before"] <= now < grant["expires_at"]
            ):
                return grant["actor"]
        raise ContractError("Authentication denied")


def verify_artifact_bytes(descriptor, stream, *, max_bytes=16 * 1024 * 1024):
    """Hash a host-opened binary stream; never interpret/fetch descriptor.uri.

    The host owns stream lifetime and enforces object visibility, path/SSRF
    protection, immutability, malware policy and timeouts on its resolver.
    """
    descriptor = _snapshot(descriptor)
    fields(descriptor, ("id", "media_type", "sha256", "uri", "size_bytes"), ("schema",))
    _check(
        descriptor.get("schema", "usmsb.artifact-reference.v1") == "usmsb.artifact-reference.v1",
        "Unknown artifact schema",
    )
    artifact_reference(
        **{key: value for key, value in descriptor.items() if key not in {"id", "schema"}},
        artifact_id=descriptor["id"],
    )
    _check(type(max_bytes) is int and 0 <= max_bytes <= 1024**3, "Invalid artifact byte budget")
    _check(descriptor["size_bytes"] <= max_bytes, "Artifact byte budget exceeded")
    count, sha = 0, hashlib.sha256()
    while True:
        chunk = stream.read(min(65536, max_bytes - count + 1))
        _check(type(chunk) is bytes, "Resolver must provide a binary stream")
        if not chunk:
            break
        count += len(chunk)
        _check(count <= max_bytes and count <= descriptor["size_bytes"], "Artifact length mismatch")
        sha.update(chunk)
    _check(count == descriptor["size_bytes"], "Artifact length mismatch")
    _check(hmac.compare_digest(sha.hexdigest(), descriptor["sha256"]), "Artifact hash mismatch")
    return {"sha256": sha.hexdigest(), "size_bytes": count}


class AuthenticatedCollaborationHost:
    """Opt-in, fail-closed gateway; the journal's direct API remains host-only.

    authenticate(credential) returns a trusted actor ID. resolve_artifact(actor,
    descriptor) returns a context manager of a binary stream. verify_evidence(
    actor, operation, payload) must return exactly True for goal.revise,
    review.record and adoption.record, after authenticating scoped evidence.
    Exceptions propagate without writes; transport must redact them for clients.
    """

    def __init__(
        self,
        journal,
        *,
        authenticate,
        resolve_artifact,
        verify_evidence,
        max_artifact_bytes=16 * 1024 * 1024,
    ):
        for callback in (authenticate, resolve_artifact, verify_evidence):
            _check(callable(callback), "Install trusted host adapters")
        _check(
            type(max_artifact_bytes) is int and 0 <= max_artifact_bytes <= 1024**3,
            "Invalid artifact byte budget",
        )
        self.journal = journal
        self._configuration = journal.configuration()
        self._authenticate = authenticate
        self._resolve_artifact = resolve_artifact
        self._verify_evidence = verify_evidence
        self._max_artifact_bytes = max_artifact_bytes

    def offer(self):
        return protocol_offer(self._configuration)

    def apply(self, credential, hello, envelope):
        # Freeze before calling any plugin: a plugin must not swap checked data.
        hello, envelope = _snapshot(hello), _snapshot(envelope)
        actor = self._authenticate(credential)
        _check(
            type(actor) is str and actor in self._configuration["principals"],
            "Unknown authenticated actor",
        )
        fields(envelope, ("schema", "agreement_hash", "command_id", "operation", "payload"))
        _check(envelope["schema"] == COMMAND_SCHEMA, "Unsupported command schema")
        agreement = negotiate(self.offer(), hello)
        _check(envelope["agreement_hash"] == agreement["agreement_hash"], "Agreement mismatch")
        operation, payload = envelope["operation"], envelope["payload"]
        # Authenticated identical replays need not re-fetch now-expired evidence.
        prior = self.journal.receipt(actor, envelope["command_id"], operation, payload)
        if prior is not None:
            return prior
        profile_id = agreement["profile"]["id"]
        _check(type(payload) is dict, "Invalid command payload")
        if operation == "commitment.propose":
            _check(payload.get("profile_id") == profile_id, "Unnegotiated profile")
        elif operation in {"commitment.accept", "artifact.submit"}:
            commitment = self.journal.get("commitment", payload.get("commitment_id"))
            _check(commitment["terms"]["profile"]["id"] == profile_id, "Unnegotiated profile")
        elif operation in {"review.record", "adoption.record"}:
            artifact = self.journal.get("artifact", payload.get("artifact_id"))
            commitment = self.journal.get("commitment", artifact["commitment_id"])
            _check(commitment["terms"]["profile"]["id"] == profile_id, "Unnegotiated profile")
        # Refuse unauthorized work before invoking trusted storage/evidence
        # adapters, not merely after their potential I/O. The journal rechecks
        # all final state atomically; this preliminary guard grants no rights.
        if operation in {"artifact.submit", "review.record", "adoption.record"}:
            _check(commitment["status"] == "active", "Commitment is not active")
            _check(
                payload.get("terms_hash") == commitment["terms_hash"], "Frozen terms hash mismatch"
            )
            if operation == "artifact.submit":
                _check(
                    actor == commitment["terms"]["provider_id"], "Only agreed provider may submit"
                )
            elif operation == "review.record":
                _check(
                    actor in commitment["terms"]["contract"]["verifier_ids"],
                    "Not an agreed verifier",
                )
            else:
                _check(
                    actor == commitment["terms"]["requester_id"],
                    "Only recipient may record adoption",
                )
        elif operation == "goal.revise":
            goal = self.journal.get("goal", payload.get("goal_id"))
            _check(actor == goal["owner_id"], "Only goal owner may revise intent")
        if operation == "artifact.submit":
            descriptor = payload.get("artifact")
            # Check schema and the installed media policy before opening content.
            policy = dict(self._configuration["profiles"][profile_id])
            policy["media_types"] = tuple(policy["media_types"])
            profile = CollaborationProfile(**policy)
            _check(type(descriptor) is dict, "Invalid artifact descriptor")
            fields(descriptor, ("schema", "id", "media_type", "sha256", "uri", "size_bytes"))
            _check(descriptor["schema"] == "usmsb.artifact-reference.v1", "Unknown artifact schema")
            artifact_reference(
                descriptor["id"],
                descriptor["media_type"],
                descriptor["sha256"],
                descriptor["uri"],
                descriptor["size_bytes"],
                profile=profile,
            )
            _check(
                descriptor["size_bytes"] <= self._max_artifact_bytes,
                "Artifact byte budget exceeded",
            )
            with self._resolve_artifact(actor, _snapshot(descriptor)) as stream:
                verify_artifact_bytes(descriptor, stream, max_bytes=self._max_artifact_bytes)
        if operation in {"goal.revise", "review.record", "adoption.record"}:
            _check(
                self._verify_evidence(actor, operation, _snapshot(payload)) is True,
                "Evidence verification denied",
            )
        return self.journal.apply(actor, envelope["command_id"], operation, payload)
