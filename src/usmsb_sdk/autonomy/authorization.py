"""Owner-local data collaboration and fail-closed proof extension contracts.

The vault is an application boundary, not encryption against its OS owner, ZK,
or a general sandbox. Only owner-installed processors can see originals. Units
are explicitly local processing limits, never money or invented revenue.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import time

from .contracts import _check, _text, _ids
from .evolution import SQLiteEvolutionStore, _json, clone, fingerprint, timestamp


@dataclass(frozen=True)
class ProofVerification:
    status: str
    proof_type: str
    claim_hash: str
    scope: str
    verifier: str | None
    reason: str

    def require_verified(self):
        _check(self.status == "verified", "Proof did not verify: " + self.status)
        return asdict(self)


class ProofRegistry:
    """Verifiers are trusted local code. A signature alone is not claim truth."""
    def __init__(self):
        self.verifiers = {}

    def register(self, proof_type, version, verify):
        _text(proof_type, 180)
        _text(version, 180)
        _check(proof_type not in self.verifiers and callable(verify), "Duplicate or invalid verifier")
        self.verifiers[proof_type] = (version, verify)

    def verify(self, proof, *, claim, scope, now=None):
        now = time.time() if now is None else now
        expected = fingerprint(claim)
        kind = proof.get("type") if isinstance(proof, dict) else "missing"
        def result(status, reason, verifier=None):
            return ProofVerification(status, str(kind), expected, scope, verifier, reason)
        if not isinstance(kind, str) or kind not in self.verifiers:
            return result("unsupported", "No trusted verifier installed for this proof type")
        version, check = self.verifiers[kind]
        if proof.get("claim_hash") != expected or proof.get("scope") != scope:
            return result("invalid", "Claim or scope mismatch", version)
        try:
            if now >= timestamp(proof.get("expires_at")):
                return result("invalid", "Proof expired", version)
            verdict = check(clone(proof), clone(claim))
        except Exception:
            return result("error", "Verifier could not establish validity", version)
        if verdict is not True:
            return result("invalid", "Verifier did not return strict true", version)
        return result("verified", "Valid only for the declared claim and scope", version)


def _nonnegative(value, label, positive=False):
    _check(type(value) is int and (1 if positive else 0) <= value <= 1000000, "Invalid " + label)
    return value


class PrivateDataVault:
    def __init__(self, path, owner_id, processors, *, proofs=None, unit_costs=None, clock=time.time):
        self.owner_id = _text(owner_id, 180)
        self.processors = dict(processors)
        _check(all(isinstance(k, str) and callable(v) for k, v in self.processors.items()), "Invalid owner processor registry")
        self.unit_costs = {k: 1 for k in self.processors} if unit_costs is None else dict(unit_costs)
        _check(self.unit_costs.keys() == self.processors.keys(), "Owner rates must cover every installed processor")
        for value in self.unit_costs.values():
            _nonnegative(value, "owner unit cost", True)
        self.proofs, self.clock = proofs or ProofRegistry(), clock
        self.store = SQLiteEvolutionStore(path)
        self.store.bind_scope("private-vault-owner", {"owner": owner_id})
        self.store.bind_scope("private-vault-rates", self.unit_costs)
        with self.store.transaction() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS private_data(id TEXT PRIMARY KEY, metadata TEXT NOT NULL, original TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS data_grants(id TEXT PRIMARY KEY, payload TEXT NOT NULL, revoked TEXT);
                CREATE TABLE IF NOT EXISTS data_calls(id TEXT PRIMARY KEY, grant_id TEXT NOT NULL, request TEXT NOT NULL, state TEXT NOT NULL, receipt TEXT);
            """)

    def add(self, actor, *, data_id, original, title, rights):
        _check(actor == self.owner_id, "Only the rights owner can add originals")
        _text(data_id, 180)
        _text(title, 500)
        _text(rights, 2000)
        _check(isinstance(original, dict) and len(_json(original).encode()) <= 2000000, "Expected bounded original JSON")
        # Caller supplies only explicitly public title/rights, not arbitrary metadata.
        metadata = {"schema": "usmsb.private-data.v1", "id": data_id, "owner_id": actor,
                    "title": title, "rights": rights, "content_hash": fingerprint(original),
                    "original_access": "owner-local-only", "created_at": self.clock()}
        with self.store.transaction() as db:
            prior = db.execute("SELECT metadata,original FROM private_data WHERE id=?", (data_id,)).fetchone()
            if prior:
                prior_meta = json.loads(prior[0])
                _check(prior[1] == _json(original) and all(prior_meta[k] == metadata[k] for k in metadata if k != "created_at"), "Original version is immutable")
                return prior_meta
            db.execute("INSERT INTO private_data VALUES (?,?,?)", (data_id, _json(metadata), _json(original)))
        return metadata

    def metadata(self, data_id):
        with self.store.transaction() as db:
            row = db.execute("SELECT metadata FROM private_data WHERE id=?", (data_id,)).fetchone()
            _check(row is not None, "Unknown data")
            return json.loads(row[0])

    def _grant(self, db, grant_id, *, active=True):
        row = db.execute("SELECT payload,revoked FROM data_grants WHERE id=?", (grant_id,)).fetchone()
        _check(row is not None, "Unknown grant")
        item = json.loads(row[0])
        if active:
            _check(not row[1] and item["not_before"] <= self.clock() < item["expires_at"], "Grant inactive or revoked")
            if item["parent_id"]:
                self._grant(db, item["parent_id"])
        return item

    def grant(self, actor, *, grant_id, data_id, grantee, purposes, operations, disclosures,
              max_calls, max_units, expires_at, not_before=None, parent_id=None, required_proof_type=None):
        now = self.clock()
        _text(grant_id, 180)
        _text(grantee, 180)
        _text(data_id, 180)
        operations, purposes, disclosures = [_ids(x) for x in (operations, purposes, disclosures)]
        _check(bool(operations) and bool(purposes) and bool(disclosures), "Grant needs explicit purposes, operations and output fields")
        _check(set(operations) <= self.processors.keys(), "Operation not installed by owner")
        if required_proof_type is not None:
            _text(required_proof_type, 180)
            _check(required_proof_type in self.proofs.verifiers, "Required proof has no trusted verifier")
        item = {"id": grant_id, "data_id": data_id, "issuer": actor, "owner_id": self.owner_id,
                "grantee": grantee, "purposes": purposes, "operations": operations, "disclosures": disclosures,
                "max_calls": _nonnegative(max_calls, "max_calls", True), "max_units": _nonnegative(max_units, "max_units"),
                "not_before": timestamp(now if not_before is None else not_before), "expires_at": timestamp(expires_at),
                "parent_id": parent_id, "required_proof_type": required_proof_type, "unit": "local_processing_unit", "depth": 0}
        _check(item["not_before"] < item["expires_at"] and now < item["expires_at"], "Invalid grant interval")
        with self.store.transaction() as db:
            _check(db.execute("SELECT 1 FROM private_data WHERE id=?", (data_id,)).fetchone(), "Unknown data")
            prior = db.execute("SELECT payload FROM data_grants WHERE id=?", (grant_id,)).fetchone()
            if prior and not_before is None:
                item["not_before"] = json.loads(prior[0])["not_before"]
            parent = self._grant(db, parent_id) if parent_id else None
            if parent:
                item["depth"] = parent["depth"] + 1
                _check(item["depth"] <= 8 and parent["grantee"] == actor and data_id == parent["data_id"], "Not authorized to delegate this data")
                _check(item["not_before"] >= parent["not_before"] and item["expires_at"] <= parent["expires_at"], "Delegation expands time range")
                _check(not parent["required_proof_type"] or required_proof_type == parent["required_proof_type"], "Delegation weakens proof requirement")
                for field in ("purposes", "operations", "disclosures"):
                    _check(set(item[field]) <= set(parent[field]), "Delegation expands " + field)
            else:
                _check(actor == self.owner_id, "Only the owner can issue a root grant")
            if prior:
                _check(prior[0] == _json(item), "Grant id is immutable")
                return self._grant(db, grant_id)
            if parent:
                calls, units = self._allocated(db, parent_id)
                _check(calls + max_calls <= parent["max_calls"] and units + max_units <= parent["max_units"], "Delegation exceeds remaining allocation")
                count = db.execute("SELECT COUNT(*) FROM data_grants WHERE json_extract(payload,'$.parent_id')=?", (parent_id,)).fetchone()[0]
                _check(count < 12, "Delegation fanout exceeded")
            db.execute("INSERT INTO data_grants VALUES (?,?,NULL)", (grant_id, _json(item)))
        return item

    def _allocated(self, db, grant_id):
        children = [json.loads(r[0]) for r in db.execute("SELECT payload FROM data_grants WHERE json_extract(payload,'$.parent_id')=?", (grant_id,))]
        calls = [json.loads(r[0]) for r in db.execute("SELECT request FROM data_calls WHERE grant_id=?", (grant_id,))]
        # Child allocations and all started/unknown calls remain reserved. Revoking
        # permission is not a refund or evidence of unused external resources.
        return len(calls) + sum(c["max_calls"] for c in children), sum(c["units"] for c in calls) + sum(c["max_units"] for c in children)

    def revoke(self, actor, grant_id, reason):
        _text(reason, 2000)
        with self.store.transaction() as db:
            grant = self._grant(db, grant_id, active=False)
            _check(actor in {self.owner_id, grant["issuer"]}, "Cannot revoke another issuer's grant")
            event = {"by": actor, "reason": reason, "at": self.clock(), "published_outputs_retractable": False}
            db.execute("UPDATE data_grants SET revoked=COALESCE(revoked,?) WHERE id=?", (_json(event), grant_id))
            return {"grant_id": grant_id, "future_execution": "denied_including_descendants", "already_disclosed": "cannot_be_recalled"}

    def execute(self, actor, *, grant_id, request_id, operation, purpose, disclosures, arguments, units, proof=None):
        _text(request_id, 180)
        _check(isinstance(arguments, dict), "Expected arguments object")
        wanted = _ids(disclosures)
        request = {"actor": actor, "grant_id": grant_id, "request_id": request_id, "operation": operation,
                   "purpose": purpose, "disclosures": wanted, "arguments": clone(arguments),
                   "units": _nonnegative(units, "units"), "proof": clone(proof)}
        _check(len(_json(request).encode()) <= 100000, "Request too large")
        with self.store.transaction() as db:
            grant = self._grant(db, grant_id)
            _check(actor == grant["grantee"], "Caller is not the authorized subject")
            _check(operation in grant["operations"] and purpose in grant["purposes"] and bool(wanted) and set(wanted) <= set(grant["disclosures"]), "Use or disclosure outside grant")
            _check(units == self.unit_costs[operation], "Requested units differ from the owner-installed rate")
            row = db.execute("SELECT metadata,original FROM private_data WHERE id=?", (grant["data_id"],)).fetchone()
            metadata = json.loads(row[0])
            expected_claim = {"grant_id": grant_id, "subject": actor, "data_hash": metadata["content_hash"], "operation": operation, "purpose": purpose}
            verification = None
            if proof is not None or grant["required_proof_type"]:
                _check(not grant["required_proof_type"] or isinstance(proof, dict) and proof.get("type") == grant["required_proof_type"], "Required proof missing")
                verification = self.proofs.verify(proof, claim=expected_claim, scope=purpose, now=self.clock()).require_verified()
            prior = db.execute("SELECT request,state,receipt FROM data_calls WHERE id=?", (request_id,)).fetchone()
            if prior:
                _check(prior[0] == _json(request), "Request id already binds another input")
                if prior[2]:
                    return json.loads(prior[2])
                return {"id": request_id, "state": "unknown", "automatic_retry": False, "reason": "Existing local reservation has no durable result"}
            calls, allocated = self._allocated(db, grant_id)
            _check(calls < grant["max_calls"] and allocated + units <= grant["max_units"], "Processing allocation exhausted")
            db.execute("INSERT INTO data_calls VALUES (?,?,?,'reserved',NULL)", (request_id, grant_id, _json(request)))
            original = json.loads(row[1])
        started = time.monotonic()
        try:
            result = self.processors[operation](original, clone(arguments))
            _check(isinstance(result, dict) and set(wanted) <= result.keys(), "Processor did not return allowed output fields")
            output = {key: result[key] for key in wanted}
            _check(len(_json(output).encode()) <= 200000, "Disclosure exceeds size limit")
            state, error = "completed", None
        except Exception as exc:
            state, error, output = "failed", type(exc).__name__, None
        with self.store.transaction() as db:
            try:
                self._grant(db, grant_id)
            except ValueError:
                state, error, output = "revoked", "Grant ceased to permit disclosure during processing", None
            receipt = {"id": request_id, "state": state, "grant_id": grant_id, "owner_id": self.owner_id,
                       "input_hash": fingerprint(request), "data_hash": metadata["content_hash"], "operation": operation,
                       "elapsed_ms": (time.monotonic() - started) * 1000, "units": units, "unit": "local_processing_unit",
                       "output": output, "output_hash": fingerprint(output) if output is not None else None,
                       "error": error, "proof_verification": verification, "automatic_retry": False,
                       "meaning": "Owner-installed local program result; not scientific or clinical validation"}
            db.execute("UPDATE data_calls SET state=?,receipt=? WHERE id=?", (state, _json(receipt), request_id))
            return receipt
