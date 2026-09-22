"""Private subject journal for replaceable, evidence-driven USMSB policies.

Effects are proposals until an embedding host attaches an actual protocol result.
The host owns authorization and at-most-once external execution. This journal
must stay in the participant's private storage.
"""
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time

from .contracts import ContractError, _check, _text, _ids, remote_status
from .open_world import feedback_decision

SCHEMA = "usmsb.evolution.v1"
DECISIONS = {"wait", "create_goal", "reconsider", "request_resource", "request_capability", "propose_action"}


def _json(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ContractError("Expected finite JSON") from exc


def fingerprint(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def clone(value):
    return json.loads(_json(value))


def timestamp(value):
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            _check(parsed.tzinfo is not None, "Timestamp needs timezone")
            value = parsed.timestamp()
        except ValueError:
            raise ContractError("Invalid timestamp") from None
    _check(type(value) in {int, float} and math.isfinite(value) and value > 0, "Invalid timestamp")
    return value


@dataclass(frozen=True)
class EnvironmentObservation:
    id: str
    source_id: str
    source_version: str
    observed_at: str | float
    fetched_at: str | float
    validity: str = "unknown"
    access: str = "public"
    payload: dict | None = None
    evidence_ids: tuple = ()
    owner_id: str | None = None
    authorized_subjects: tuple = ()
    expires_at: float | None = None

    def record(self):
        return observation_record(asdict(self))


def observation_record(value):
    item = clone(dict(value))
    for key in ("id", "source_id", "source_version"):
        item[key] = _text(item.get(key), 180)
    for key in ("observed_at", "fetched_at"):
        item[key] = timestamp(item.get(key))
    for key, default, allowed in (
        ("validity", "unknown", {"valid", "unknown", "stale", "retracted"}),
        ("access", "public", {"public", "private", "authorized"}),
    ):
        item.setdefault(key, default)
        _check(isinstance(item[key], str) and item[key] in allowed, "Invalid " + key)
    for key in ("evidence_ids", "authorized_subjects"):
        _check(isinstance(item.get(key, []), list), "Invalid " + key)
        item[key] = _ids(item.get(key, []))
    if item.get("owner_id") is not None:
        _text(item["owner_id"], 180)
    if item.get("expires_at") is not None:
        item["expires_at"] = timestamp(item["expires_at"])
    item["payload"] = item.get("payload") if item.get("payload") is not None else {}
    _check(isinstance(item["payload"], dict), "Expected object payload")
    _check(len(_json(item).encode()) <= 200000, "Observation exceeds 200KB")
    item["content_hash"] = fingerprint(item["payload"])
    return item


@dataclass(frozen=True)
class SubjectSnapshot:
    subject_id: str
    goals: tuple = ()
    capabilities: tuple = ()
    resources: dict | None = None
    commitments: tuple = ()
    values: dict | None = None
    rules: dict | None = None
    private_memory_refs: tuple = ()
    objects: tuple = ()
    risks: tuple = ()

    @classmethod
    def from_agent(cls, agent, **context):
        return cls(subject_id=agent.id, goals=tuple(asdict(g) for g in agent.goals),
                   capabilities=tuple(agent.capabilities),
                   resources={"availability": "unknown", "records": [asdict(r) for r in agent.resources]},
                   rules={"records": [asdict(r) for r in agent.rules]}, **context)

    def record(self):
        _text(self.subject_id, 180)
        record = clone(asdict(self))
        record["resources"] = record["resources"] or {"availability": "unknown"}
        record["rules"] = record["rules"] or {}
        record["values"] = record["values"] or {}
        return record


class ReferenceDecisionPolicy:
    """An engineering policy, not an empirical USMSB law or global scheduler."""
    version = "usmsb.environment-reference.v2"

    def decide(self, context):
        subject, memory = context["subject"], context["memory"]
        pending_reviews = [r for r in memory.get("experience_invalidations", []) if r["id"] not in memory.get("handled_invalidations", [])]
        if pending_reviews:
            return {"decision": "reconsider", "reason": "experience_evidence_invalidated", "causal_claim": False,
                    "invalidation_ids": [r["id"] for r in pending_reviews],
                    "experience_ids": sorted({eid for r in pending_reviews for eid in r["impacted_experience_ids"]})}
        observations = {o["id"]: o for o in context["observations"]}
        for assessment in context["environment"].get("assessments", []):
            if assessment.get("actor_id") != subject["subject_id"]:
                continue
            source = observations.get(assessment.get("observation_id"))
            if not source or source["effective_validity"] != "valid":
                continue
            cid = _text(assessment.get("concern_id"), 180)
            response = feedback_decision(assessment, memory["concerns"].get(cid, {}),
                                         max_episodes=context["limits"]["max_episodes"])
            if response["decision"] == "investigate":
                return {"decision": "create_goal", "reason": "subject_condition_gap",
                        "evidence_ids": [source["id"]], "concern_id": cid, "assessment_id": assessment["id"],
                        "goal": {"title": _text(assessment.get("title"), 160),
                                 "origin_observation_id": source["id"],
                                 "success_criteria": assessment.get("verification", "Compare subsequent evidence with this condition")}}
            if response["decision"] in {"reconsider", "assess_effect", "observe"}:
                return {"decision": "reconsider", "reason": response["decision"], "evidence_ids": [source["id"]],
                        "concern_id": cid, "assessment_id": assessment["id"], "causal_claim": False}
        if any(r["state"] == "unknown" for r in memory["remotes"]):
            return {"decision": "wait", "reason": "reconcile_original_execution"}
        active = [g for g in subject["goals"] if g.get("status") in {"active", "in_progress", "pending"}]
        if active and subject["resources"].get("availability") == "insufficient":
            return {"decision": "request_resource", "reason": "observed_resource_shortfall", "goal_id": active[0]["id"]}
        if active and context["environment"].get("missing_capabilities"):
            return {"decision": "request_capability", "reason": "capability_unavailable", "goal_id": active[0]["id"],
                    "capabilities": context["environment"]["missing_capabilities"]}
        return {"decision": "wait", "reason": "no_new_actionable_evidence"}


class SQLiteEvolutionStore:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS evolution_binding(subject TEXT PRIMARY KEY, config TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evolution_decisions(
                    input_hash TEXT PRIMARY KEY, context TEXT NOT NULL, result TEXT NOT NULL, receipt TEXT);
                CREATE TABLE IF NOT EXISTS evolution_journal(
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, event_key TEXT UNIQUE NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evolution_remote_state(run_ref TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evolution_observations(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evolution_scopes(name TEXT PRIMARY KEY, binding TEXT NOT NULL);
            """)

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=20)
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def bind(self, db, subject, config):
        prior = db.execute("SELECT subject,config FROM evolution_binding").fetchone()
        _check(not prior or prior == (subject, _json(config)), "Private identity/policy/budget mismatch; explicit migration required")
        if not prior:
            db.execute("INSERT INTO evolution_binding VALUES (?,?)", (subject, _json(config)))

    def check_subject(self, db, subject):
        prior = db.execute("SELECT subject FROM evolution_binding").fetchone()
        _check(prior and prior[0] == subject, "Journal is not bound to this subject")

    def bind_scope(self, name, binding):
        """Bind a host's storage/authority boundary; never silently migrate it."""
        _text(name, 180)
        encoded = _json(binding)
        with self.transaction() as db:
            prior = db.execute("SELECT binding FROM evolution_scopes WHERE name=?", (name,)).fetchone()
            _check(not prior or prior[0] == encoded, "Host scope changed; explicit migration required")
            db.execute("INSERT OR IGNORE INTO evolution_scopes VALUES (?,?)", (name, encoded))

    def journal(self, db, key, event):
        prior = db.execute("SELECT payload FROM evolution_journal WHERE event_key=?", (key,)).fetchone()
        _check(not prior or prior[0] == _json(event), "Event key binds different evidence")
        db.execute("INSERT OR IGNORE INTO evolution_journal(event_key,payload) VALUES (?,?)", (key, _json(event)))

    def latest_cycle(self, subject):
        with self.transaction() as db:
            self.check_subject(db, subject)
            row = db.execute("SELECT payload FROM evolution_journal ORDER BY seq DESC LIMIT 1").fetchone()
            return json.loads(row[0]) if row else None

    def memory(self, db):
        concerns, feedback, handled_invalidations = {}, [], set()
        for row in db.execute("SELECT payload FROM evolution_journal ORDER BY seq"):
            event = json.loads(row[0])
            if event["type"] == "feedback":
                feedback.append(event)
            if event["type"] == "decision_applied" and event.get("concern_id"):
                state = concerns.setdefault(event["concern_id"], {"episodes": 0})
                state.update(event["state"])
                state["episodes"] += int(event["decision"] == "create_goal")
            if event["type"] == "decision_applied":
                handled_invalidations.update(event.get("invalidation_ids", []))
        experiences, invalidations = [], []
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='learning_experiences'").fetchone():
            experiences = [json.loads(r[0]) for r in db.execute("SELECT record FROM learning_experiences ORDER BY id")]
            invalidations = [json.loads(r[0]) for r in db.execute("SELECT event FROM learning_invalidations ORDER BY rowid")]
        return {"concerns": concerns, "feedback": feedback, "experiences": experiences,
                "experience_invalidations": invalidations, "handled_invalidations": sorted(handled_invalidations),
                "applicable_experiences": [r for r in experiences if r["state"] in {"validated", "promoted_skill"} and not r["metadata"].get("review_required")],
                "remotes": [json.loads(r[0]) for r in db.execute("SELECT payload FROM evolution_remote_state ORDER BY run_ref")]}


class MemoryEvolutionStore(SQLiteEvolutionStore):
    """Temporary SQLite: identical transaction semantics to the durable store."""
    def __init__(self):
        import tempfile
        self._temporary = tempfile.TemporaryDirectory(prefix="usmsb-evolution-")
        super().__init__(Path(self._temporary.name) / "private.sqlite")


class EvolutionEngine:
    def __init__(self, store, policy=None, *, max_episodes=12, max_decisions=1000, clock=time.time):
        for limit in (max_episodes, max_decisions):
            _check(type(limit) is int and 1 <= limit <= 10000, "Invalid persistent decision budget")
        self.store, self.policy, self.clock = store, policy or ReferenceDecisionPolicy(), clock
        self.limits = {"max_episodes": max_episodes, "max_decisions": max_decisions}
        self.version = _text(getattr(self.policy, "version", None), 180)

    def cycle(self, subject, observations, *, environment=None):
        _check(isinstance(subject, SubjectSnapshot), "Invalid subject")
        visible, now = [], self.clock()
        for raw in observations:
            item = raw.record() if isinstance(raw, EnvironmentObservation) else observation_record(raw)
            allowed = item["access"] == "public" or item.get("owner_id") == subject.subject_id
            allowed |= item["access"] == "authorized" and subject.subject_id in item["authorized_subjects"]
            if not allowed:
                continue
            validity = item["validity"]
            if item["observed_at"] > now + 30 or item["fetched_at"] > now + 30:
                validity = "unknown"
            elif item.get("expires_at") is not None and now >= item["expires_at"]:
                validity = "stale"
            visible.append({**item, "effective_validity": validity})
        visible.sort(key=lambda o: o["id"])
        _check(len({o["id"] for o in visible}) == len(visible), "Duplicate observation")
        with self.store.transaction() as db:
            self.store.bind(db, subject.subject_id, {"policy_version": self.version, **self.limits})
            for item in visible:
                original = {k: v for k, v in item.items() if k != "effective_validity"}
                prior = db.execute("SELECT payload FROM evolution_observations WHERE id=?", (item["id"],)).fetchone()
                _check(not prior or prior[0] == _json(original), "Observation version cannot overwrite history")
                db.execute("INSERT OR IGNORE INTO evolution_observations VALUES (?,?)", (item["id"], _json(original)))
            context = {"schema": SCHEMA, "subject": subject.record(), "observations": visible,
                       "environment": clone(dict(environment or {})), "memory": self.store.memory(db),
                       "policy_version": self.version, "limits": self.limits}
            input_hash = fingerprint(context)
            prior = db.execute("SELECT result,receipt FROM evolution_decisions WHERE input_hash=?", (input_hash,)).fetchone()
            if prior:
                return {**json.loads(prior[0]), "replayed": True,
                        "receipt": json.loads(prior[1]) if prior[1] else None}
            pending = db.execute("SELECT result FROM evolution_decisions WHERE receipt IS NULL AND json_extract(result,'$.decision')!='wait' ORDER BY rowid LIMIT 1").fetchone()
            if pending:
                return {**json.loads(pending[0]), "replayed": True, "reason_pending": "recover_original_command"}
            count, episodes = db.execute("SELECT COUNT(*),COALESCE(SUM(json_extract(result,'$.decision')='create_goal'),0) FROM evolution_decisions").fetchone()
            if count >= self.limits["max_decisions"]:
                return {"decision": "wait", "reason": "decision_budget", "subject_id": subject.subject_id}
            raw = clone(dict(self.policy.decide(clone(context))))
            decision = raw.get("decision")
            _check(isinstance(decision, str) and decision in DECISIONS, "Unknown decision")
            reserved = {"schema", "type", "id", "subject_id", "input_hash", "effect", "at", "policy_version", "replayed"}
            _check(not (reserved & raw.keys()), "Policy cannot replace journal identity or evidence")
            _text(raw.get("reason"), 2000)
            evidence = _ids(raw.get("evidence_ids", []))
            _check(set(evidence) <= {o["id"] for o in visible}, "Evidence outside visible snapshot")
            if decision == "create_goal":
                _check(bool(evidence) and all(next(o for o in visible if o["id"] == eid)["effective_validity"] == "valid" for eid in evidence), "New goal requires fresh visible evidence")
                if episodes >= self.limits["max_episodes"]:
                    raw = {"decision": "wait", "reason": "episode_budget"}
            result = {**raw, "schema": SCHEMA, "type": "decision", "subject_id": subject.subject_id,
                      "input_hash": input_hash, "id": "decision_" + input_hash[:48], "policy_version": self.version,
                      "observation_ids": [o["id"] for o in visible], "at": now, "effect": "proposal_only"}
            db.execute("INSERT INTO evolution_decisions VALUES (?,?,?,NULL)", (input_hash, _json(context), _json(result)))
            self.store.journal(db, result["id"], result)
            return result

    def acknowledge(self, subject_id, decision_id, receipt):
        _check(isinstance(receipt, dict) and isinstance(receipt.get("id"), str) and receipt["id"], "Actual protocol result required")
        with self.store.transaction() as db:
            self.store.check_subject(db, subject_id)
            row = db.execute("SELECT input_hash,result,receipt,context FROM evolution_decisions WHERE json_extract(result,'$.id')=?", (decision_id,)).fetchone()
            _check(row is not None, "Unknown decision")
            _check(not row[2] or row[2] == _json(receipt), "Decision receipt is immutable")
            if row[2]:
                return json.loads(row[2])
            decision, context = json.loads(row[1]), json.loads(row[3])
            event = {"type": "decision_applied", "decision_id": decision_id, "decision": decision["decision"],
                     "receipt": clone(receipt), "concern_id": decision.get("concern_id"), "state": {},
                     "invalidation_ids": decision.get("invalidation_ids", [])}
            assessment = next((a for a in context["environment"].get("assessments", []) if a["id"] == decision.get("assessment_id")), None)
            if assessment:
                event["state"] = {"assessment_id": assessment["id"], "phase": assessment["status"]}
                if decision["decision"] == "create_goal":
                    event["state"]["goal_id"] = receipt["id"]
            db.execute("UPDATE evolution_decisions SET receipt=? WHERE input_hash=?", (_json(receipt), row[0]))
            self.store.journal(db, decision_id + ":applied", event)
            return clone(receipt)

    def record_remote(self, subject_id, result):
        normalized = {**remote_status(dict(result)), "automatic_retry": False}
        with self.store.transaction() as db:
            self.store.check_subject(db, subject_id)
            row = db.execute("SELECT payload FROM evolution_remote_state WHERE run_ref=?", (normalized["run_ref"],)).fetchone()
            if row:
                previous = json.loads(row[0])
                if previous["state"] in {"completed", "failed"}:
                    _check(previous == normalized, "Terminal receipt is immutable")
                _check(not (previous["state"] in {"running", "unknown"} and normalized["state"] == "accepted"), "Remote state cannot regress")
            db.execute("INSERT INTO evolution_remote_state VALUES (?,?) ON CONFLICT(run_ref) DO UPDATE SET payload=excluded.payload", (normalized["run_ref"], _json(normalized)))
            self.store.journal(db, "remote:" + fingerprint(normalized), {"type": "remote_result", **normalized})
        return normalized

    def feedback(self, subject_id, *, observation_id, status, evidence_ids, effect="unknown"):
        _text(observation_id, 180)
        _check(isinstance(status, str) and status in {"aligned", "gap", "unknown", "retracted"}, "Unknown feedback status")
        _check(isinstance(effect, str) and effect in {"improved", "unchanged", "worse", "unknown"}, "Unknown observed effect")
        evidence = _ids(evidence_ids)
        _check(bool(evidence), "Feedback needs attributable evidence")
        event = {"type": "feedback", "observation_id": observation_id, "status": status, "effect": effect,
                 "evidence_ids": evidence, "causal_claim": False, "next": "reconsider" if status in {"gap", "retracted"} else "observe"}
        with self.store.transaction() as db:
            self.store.check_subject(db, subject_id)
            _check(db.execute("SELECT 1 FROM evolution_observations WHERE id=?", (observation_id,)).fetchone(), "Unknown feedback observation")
            self.store.journal(db, "feedback:" + fingerprint(event), event)
        return event
