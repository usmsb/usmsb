"""Host-embedded collaboration ledger, with no execution or global authority.

Actors and controllers MUST come from the embedding host's authentication and
identity system, never from client claims. Reviews/adoptions are attributed
statements, not proof of truth, causal impact, payment or goal completion.
"""

import hashlib
import json

from .contracts import ContractError, _check, _ids, _text, goal_contract, review_checks
from .evolution import SQLiteEvolutionStore
from .goal_revision import REVISION_FIELDS, revision_basis, revision_patch
from .profiles import OPEN_COLLABORATION_V1, artifact_reference, checked_profile

OPERATIONS = frozenset(
    {
        "goal.create",
        "goal.revise",
        "commitment.propose",
        "commitment.accept",
        "artifact.submit",
        "review.record",
        "adoption.record",
    }
)


def canonical(value):
    """Bounded JSON, including depth and interoperable integer limits."""

    def visit(item, depth=0):
        _check(depth <= 16, "JSON too deep")
        if item is None or type(item) is bool:
            return
        if type(item) is int:
            _check(abs(item) <= 2**53 - 1, "JSON integer out of range")
        elif type(item) is str:
            _check(len(item) <= 32000, "JSON string too long")
        elif type(item) in (list, dict):
            _check(len(item) <= 1024, "JSON collection too large")
            if isinstance(item, dict):
                _check(all(type(k) is str and len(k) <= 180 for k in item), "Invalid JSON keys")
                item = item.values()
            for child in item:
                visit(child, depth + 1)
        else:
            raise ContractError(
                "Only bounded JSON strings, integers, booleans and collections allowed"
            )

    visit(value)
    encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    _check(len(encoded) <= 131072, "JSON payload too large")
    return encoded


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def fields(payload, required, optional=()):
    _check(
        type(payload) is dict
        and set(required) <= set(payload)
        and set(payload) <= set(required) | set(optional),
        "Missing or unknown command fields",
    )


class CollaborationJournal:
    """Transactional reference mechanism, for a single host and SQLite file.

    ``principals`` is {actor: {controller: identity, operations: [allowlist]}}.
    This is trusted host configuration, NOT an enrollment endpoint. Changes to
    installed principals/profiles require explicit migration to a new ledger.
    ``get``/``events`` are host-only reads; apply a visibility policy at transport.
    """

    def __init__(
        self, path, *, host_id, principals, profiles=(OPEN_COLLABORATION_V1,), max_commands=100000
    ):
        _check(str(path) != ":memory:", "Use a durable SQLite file")
        _text(host_id, 180)
        _check(
            type(principals) is dict and 1 <= len(principals) <= 10000, "Install bounded principals"
        )
        installed = {}
        for actor, grant in principals.items():
            _check(_text(actor, 180) == actor, "Actor must be canonical")
            fields(grant, ("controller", "operations"))
            operations = _ids(grant["operations"], len(OPERATIONS))
            _check(set(operations) <= OPERATIONS, "Unknown capability")
            installed[actor] = {
                "controller": _text(grant["controller"], 180),
                "operations": sorted(operations),
            }
        _check(
            isinstance(profiles, (tuple, list)) and 1 <= len(profiles) <= 32,
            "Install bounded profiles",
        )
        self._profiles = {}
        for profile in profiles:
            profile = checked_profile(profile)
            _check(profile.id not in self._profiles, "Duplicate profile id")
            self._profiles[profile.id] = profile
        _check(type(max_commands) is int and 1 <= max_commands <= 1000000, "Invalid command budget")
        self._principals = installed
        self._max_commands = max_commands
        self.host_id = host_id
        self._store = SQLiteEvolutionStore(path)
        self._store.bind_scope(
            "usmsb.collaboration-journal.v1",
            {
                "host_id": host_id,
                "principals": installed,
                "max_commands": max_commands,
                "profiles": {key: value.record() for key, value in sorted(self._profiles.items())},
            },
        )
        with self._store.transaction() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS collaboration_records ("
                "kind TEXT NOT NULL, id TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(kind,id))"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS collaboration_commands ("
                "sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, "
                "input_hash TEXT NOT NULL, receipt TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS collaboration_revision_impacts ("
                "goal_id TEXT NOT NULL, revision INTEGER NOT NULL, commitment_id TEXT NOT NULL, "
                "PRIMARY KEY(goal_id,revision,commitment_id))"
            )

    @staticmethod
    def _read(db, kind, record_id):
        row = db.execute(
            "SELECT body FROM collaboration_records WHERE kind=? AND id=?",
            (kind, _text(record_id, 180)),
        ).fetchone()
        _check(row is not None, "Record not found")
        return json.loads(row[0])

    @staticmethod
    def _write(db, kind, record_id, record, *, replace=False):
        if not replace:
            _check(
                db.execute(
                    "SELECT 1 FROM collaboration_records WHERE kind=? AND id=?", (kind, record_id)
                ).fetchone()
                is None,
                "Record already exists",
            )
        db.execute(
            "INSERT INTO collaboration_records VALUES (?,?,?) "
            "ON CONFLICT(kind,id) DO UPDATE SET body=excluded.body",
            (kind, record_id, canonical(record)),
        )

    def get(self, kind, record_id):
        """Host-only read. Returns detached data, never credentials."""
        _check(
            kind in {"goal", "commitment", "artifact", "review", "adoption"}, "Unknown record kind"
        )
        with self._store.transaction() as db:
            return self._read(db, kind, record_id)

    def events(self, *, after=0, limit=100):
        _check(
            type(after) is int and after >= 0 and type(limit) is int and 1 <= limit <= 1000,
            "Invalid event cursor",
        )
        with self._store.transaction() as db:
            return [
                json.loads(row[0])
                for row in db.execute(
                    "SELECT receipt FROM collaboration_commands "
                    "WHERE sequence>? ORDER BY sequence LIMIT ?",
                    (after, limit),
                )
            ]

    def apply(self, actor, command_id, operation, payload):
        """Actor is injected by trusted transport, not deserialized from payload."""
        _check(isinstance(actor, str) and actor in self._principals, "Unknown authenticated actor")
        _check(
            isinstance(operation, str) and operation in self._principals[actor]["operations"],
            "Capability denied",
        )
        command_id = _text(command_id, 180)
        # Freeze caller-owned mutable data before hashing, validation or writes.
        payload = json.loads(canonical(payload))
        input_hash = digest({"actor": actor, "operation": operation, "payload": payload})
        handlers = {
            "goal.create": self._goal_create,
            "goal.revise": self._goal_revise,
            "commitment.propose": self._propose,
            "commitment.accept": self._accept,
            "artifact.submit": self._submit,
            "review.record": self._review,
            "adoption.record": self._adopt,
        }
        with self._store.transaction() as db:
            prior = db.execute(
                "SELECT input_hash,receipt FROM collaboration_commands WHERE id=?", (command_id,)
            ).fetchone()
            if prior:
                _check(prior[0] == input_hash, "Command id conflict")
                return json.loads(prior[1])
            _check(
                db.execute("SELECT COUNT(*) FROM collaboration_commands").fetchone()[0]
                < self._max_commands,
                "Command budget exhausted",
            )
            result = handlers[operation](db, actor, payload)
            cursor = db.execute(
                "INSERT INTO collaboration_commands(id,input_hash,receipt) VALUES (?,?,'')",
                (command_id, input_hash),
            )
            receipt = {
                "schema": "usmsb.collaboration-receipt.v1",
                "host_id": self.host_id,
                "sequence": cursor.lastrowid,
                "command_id": command_id,
                "actor": actor,
                "operation": operation,
                "input_hash": input_hash,
                "result": result,
            }
            db.execute(
                "UPDATE collaboration_commands SET receipt=? WHERE id=?",
                (canonical(receipt), command_id),
            )
            return receipt

    def _goal_create(self, db, actor, p):
        fields(p, ("id", "intent"))
        intent = revision_patch(p["intent"])
        _check(set(intent) == set(REVISION_FIELDS), "Supply all intent fields")
        gid = _text(p["id"], 140)
        version = {
            "goal_id": gid,
            "revision": 1,
            "intent": intent,
            "reason": "initial_intent",
            "evidence_ids": [],
        }
        record = {"id": gid, "owner_id": actor, "revision": 1, "version": version}
        self._write(db, "goal", gid, record)
        self._write(db, "goal_version", f"{gid}:1", version)
        return record

    def goal_version(self, goal_id, revision):
        """Read one immutable snapshot; host applies visibility rules."""
        goal_id = _text(goal_id, 140)
        revision_basis(revision)
        with self._store.transaction() as db:
            return self._read(db, "goal_version", f"{goal_id}:{revision}")

    @staticmethod
    def _impact_page(db, goal_id, revision, after, limit):
        ids = [
            row[0]
            for row in db.execute(
                "SELECT commitment_id FROM collaboration_revision_impacts "
                "WHERE goal_id=? AND revision=? AND commitment_id>? "
                "ORDER BY commitment_id LIMIT ?",
                (goal_id, revision, after, limit + 1),
            )
        ]
        return {
            "commitment_ids": ids[:limit],
            "next_after": ids[limit - 1] if len(ids) > limit else None,
        }

    def revision_impacts(self, goal_id, revision, *, after=None, limit=32):
        """Host-only paginated immutable impact snapshot for one goal revision."""
        goal_id = _text(goal_id, 140)
        revision_basis(revision)
        after = "" if after is None else _text(after, 180)
        _check(type(limit) is int and 1 <= limit <= 32, "Invalid impact page size")
        with self._store.transaction() as db:
            self._read(db, "goal_version", f"{goal_id}:{revision}")
            return self._impact_page(db, goal_id, revision, after, limit)

    def _goal_revise(self, db, actor, p):
        fields(p, ("goal_id", "base_revision", "changes", "reason", "evidence_ids"))
        goal = self._read(db, "goal", p["goal_id"])
        _check(goal["owner_id"] == actor, "Only goal owner may revise intent")
        _check(revision_basis(p["base_revision"]) == goal["revision"], "Stale goal revision")
        revision = goal["revision"] + 1
        version = {
            "goal_id": goal["id"],
            "revision": revision,
            "intent": {**goal["version"]["intent"], **revision_patch(p["changes"])},
            "reason": _text(p["reason"]),
            "evidence_ids": _ids(p["evidence_ids"]),
        }
        self._write(db, "goal_version", f"{goal['id']}:{revision}", version)
        goal.update(revision=revision, version=version)
        self._write(db, "goal", goal["id"], goal, replace=True)
        affected_count = 0
        for (body,) in db.execute("SELECT body FROM collaboration_records WHERE kind='commitment'"):
            record = json.loads(body)
            if record["terms"]["goal_id"] == goal["id"] and record["status"] in {
                "proposed",
                "active",
            }:
                db.execute(
                    "INSERT INTO collaboration_revision_impacts VALUES (?,?,?)",
                    (goal["id"], revision, record["id"]),
                )
                affected_count += 1
        page = self._impact_page(db, goal["id"], revision, "", 32)
        return {
            "goal": goal,
            "affected_commitment_ids": page["commitment_ids"],
            "affected_commitment_count": affected_count,
            "affected_next_after": page["next_after"],
            "obligations_changed": False,
        }

    def _propose(self, db, actor, p):
        fields(
            p,
            (
                "id",
                "goal_id",
                "goal_revision",
                "provider_id",
                "description",
                "terms",
                "criteria",
                "verifier_ids",
                "profile_id",
            ),
            ("supersedes",),
        )
        goal = self._read(db, "goal", p["goal_id"])
        _check(goal["owner_id"] == actor, "Only goal owner may propose this commitment")
        _check(
            revision_basis(p["goal_revision"]) == goal["revision"],
            "Propose against current goal revision",
        )
        provider = _text(p["provider_id"], 180)
        _check(provider in self._principals and provider != actor, "Require a known other provider")
        profile_id = _text(p["profile_id"], 180)
        _check(profile_id in self._profiles, "Profile is not installed")
        profile = self._profiles[profile_id]
        contract = goal_contract(p["criteria"], p["verifier_ids"], profile=profile)
        for verifier in contract["verifier_ids"]:
            _check(verifier in self._principals, "Unknown verifier")
            _check(
                "review.record" in self._principals[verifier]["operations"],
                "Verifier lacks review capability",
            )
            controller = self._principals[verifier]["controller"]
            excluded = {self._principals[party]["controller"] for party in (actor, provider)}
            if profile.review_mode == "independent":
                _check(
                    controller not in excluded, "Independent review requires a distinct controller"
                )
            elif profile.review_mode == "peer":
                _check(
                    controller != self._principals[provider]["controller"],
                    "Peer review excludes provider controller",
                )
        parties = {actor, provider}
        supersedes = p.get("supersedes")
        if supersedes is not None:
            supersedes = _text(supersedes, 180)
            old = self._read(db, "commitment", supersedes)
            _check(
                old["status"] == "active" and old["terms"]["goal_id"] == goal["id"],
                "Only an active commitment for the same goal may be amended",
            )
            parties.update(old["required_parties"])
        for party in parties:
            _check(
                "commitment.accept" in self._principals[party]["operations"],
                "Party cannot give consent",
            )
        _check(
            "artifact.submit" in self._principals[provider]["operations"], "Provider cannot submit"
        )
        terms = {
            "id": _text(p["id"], 180),
            "goal_id": goal["id"],
            "goal_revision": goal["revision"],
            "requester_id": actor,
            "provider_id": provider,
            "description": _text(p["description"]),
            "terms": _text(p["terms"], 4000),
            "contract": contract,
            "profile": profile.record(),
            "supersedes": supersedes,
            "required_parties": sorted(parties),
        }
        record = {
            "id": terms["id"],
            "terms": terms,
            "terms_hash": digest(terms),
            "required_parties": sorted(parties),
            "accepted_by": [],
            "status": "proposed",
        }
        self._write(db, "commitment", record["id"], record)
        return record

    def _accept(self, db, actor, p):
        fields(p, ("commitment_id", "terms_hash"))
        record = self._read(db, "commitment", p["commitment_id"])
        _check(record["status"] in {"proposed", "active"}, "Commitment cannot be accepted")
        _check(p["terms_hash"] == record["terms_hash"], "Frozen terms hash mismatch")
        _check(actor in record["required_parties"], "Consent party mismatch")
        _check(
            actor not in record["accepted_by"], "Consent already recorded; replay original command"
        )
        record["accepted_by"].append(actor)
        record["accepted_by"].sort()
        if record["accepted_by"] == record["required_parties"]:
            old_id = record["terms"]["supersedes"]
            if old_id:
                old = self._read(db, "commitment", old_id)
                _check(old["status"] == "active", "Amendment basis is no longer active")
                old.update(status="superseded", superseded_by=record["id"])
                self._write(db, "commitment", old_id, old, replace=True)
            record["status"] = "active"
        self._write(db, "commitment", record["id"], record, replace=True)
        return record

    def _active(self, db, cid, terms_hash):
        c = self._read(db, "commitment", cid)
        _check(c["status"] == "active", "Commitment is not active")
        _check(terms_hash == c["terms_hash"], "Frozen terms hash mismatch")
        return c

    def _submit(self, db, actor, p):
        fields(p, ("commitment_id", "terms_hash", "artifact"))
        c = self._active(db, p["commitment_id"], p["terms_hash"])
        _check(actor == c["terms"]["provider_id"], "Only agreed provider may submit")
        a = p["artifact"]
        fields(a, ("id", "media_type", "sha256", "uri", "size_bytes"), ("schema",))
        _check(
            a.get("schema", "usmsb.artifact-reference.v1") == "usmsb.artifact-reference.v1",
            "Unknown artifact schema",
        )
        artifact = artifact_reference(
            a["id"],
            a["media_type"],
            a["sha256"],
            a["uri"],
            a["size_bytes"],
            profile=self._profiles[c["terms"]["profile"]["id"]],
        )
        record = {
            "id": artifact["id"],
            "commitment_id": c["id"],
            "terms_hash": c["terms_hash"],
            "provider_id": actor,
            "descriptor": artifact,
            "reviews": {},
        }
        self._write(db, "artifact", record["id"], record)
        return record

    def _review(self, db, actor, p):
        fields(p, ("id", "artifact_id", "artifact_sha256", "terms_hash", "checks"))
        artifact = self._read(db, "artifact", p["artifact_id"])
        c = self._active(db, artifact["commitment_id"], p["terms_hash"])
        _check(actor in c["terms"]["contract"]["verifier_ids"], "Not an agreed verifier")
        _check(actor not in artifact["reviews"], "Review immutable; use a new artifact version")
        _check(p["artifact_sha256"] == artifact["descriptor"]["sha256"], "Candidate hash mismatch")
        checks = review_checks(c["terms"]["contract"], p["checks"])
        record = {
            "id": _text(p["id"], 180),
            "artifact_id": artifact["id"],
            "artifact_sha256": p["artifact_sha256"],
            "terms_hash": c["terms_hash"],
            "verifier_id": actor,
            "checks": checks,
            "passed": all(v["status"] == "pass" for v in checks),
        }
        self._write(db, "review", record["id"], record)
        artifact["reviews"][actor] = record["id"]
        self._write(db, "artifact", artifact["id"], artifact, replace=True)
        return record

    def _adopt(self, db, actor, p):
        fields(
            p, ("id", "artifact_id", "artifact_sha256", "terms_hash", "evidence_ids", "statement")
        )
        artifact = self._read(db, "artifact", p["artifact_id"])
        c = self._active(db, artifact["commitment_id"], p["terms_hash"])
        _check(actor == c["terms"]["requester_id"], "Only recipient may record adoption")
        _check(p["artifact_sha256"] == artifact["descriptor"]["sha256"], "Candidate hash mismatch")
        for verifier in c["terms"]["contract"]["verifier_ids"]:
            _check(verifier in artifact["reviews"], "Missing agreed review")
            review = self._read(db, "review", artifact["reviews"][verifier])
            _check(review["passed"], "Acceptance conditions not met")
        refs = _ids(p["evidence_ids"])
        _check(bool(refs), "Adoption statement requires evidence references")
        goal = self._read(db, "goal", c["terms"]["goal_id"])
        record = {
            "id": _text(p["id"], 180),
            "recipient_id": actor,
            "artifact_id": artifact["id"],
            "artifact_sha256": p["artifact_sha256"],
            "terms_hash": c["terms_hash"],
            "goal_id": goal["id"],
            "goal_revision": c["terms"]["goal_revision"],
            "matches_current_goal_revision": c["terms"]["goal_revision"] == goal["revision"],
            "evidence_ids": refs,
            "statement": _text(p["statement"]),
            "semantics": "attributed_adoption_not_causal_impact_or_goal_completion",
        }
        self._write(db, "adoption", record["id"], record)
        c.update(status="adopted", adoption_id=record["id"])
        self._write(db, "commitment", c["id"], c, replace=True)
        return record
