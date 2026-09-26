"""Durable adapter for the EXISTING Harness ExperienceLoop, not a new ladder.

The evidence resolver is owner-installed code verifying original receipts and
authority; data supplied by a model or caller must never act as that resolver.
Pydantic is needed only when this optional experience adapter is imported.
"""
from dataclasses import asdict
import json

from ..growth_economic_harness.experience_loop import ExperienceLoop, PromotionEvidence
from ..growth_economic_harness.models import ExperienceDraft, ExperienceRecord, ExperienceState
from .contracts import _check, _text
from .evolution import _json, clone, fingerprint


class ExperienceJournal:
    def __init__(self, store, subject_id, resolver, policy=None):
        self.store, self.subject_id, self.resolver = store, _text(subject_id, 180), resolver
        _check(callable(resolver), "An owner-installed evidence resolver is required")
        self.loop = ExperienceLoop(policy)
        store.bind_scope("experience-policy", {"subject": subject_id, "policy": asdict(self.loop.policy)})
        with store.transaction() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS learning_experiences(id TEXT PRIMARY KEY, original TEXT NOT NULL, record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS learning_dependencies(experience TEXT NOT NULL, dependency TEXT NOT NULL, PRIMARY KEY(experience,dependency));
                CREATE TABLE IF NOT EXISTS learning_transitions(id TEXT PRIMARY KEY, record TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS learning_invalidations(id TEXT PRIMARY KEY, event TEXT NOT NULL);
            """)

    def _evidence(self, ref):
        _text(ref, 1000)
        resolved = clone(self.resolver(ref))
        _check(isinstance(resolved, dict) and resolved.get("ref") == ref and resolved.get("verified") is True
               and resolved.get("validity") == "valid", "Evidence is not currently verified: " + ref)
        for key in ("issuer", "kind", "content_hash"):
            _text(resolved.get(key), 180)
        return resolved

    def candidate(self, draft, *, run_id, experience_id, depends_on=()):
        draft = ExperienceDraft.model_validate(draft)
        _check(bool(draft.evidence_refs), "Experience needs resolved original evidence")
        resolved = [self._evidence(ref) for ref in draft.evidence_refs + draft.counter_evidence_refs]
        _check(any(r.get("unit_id") == run_id for r in resolved), "Source run is not bound to the evidence")
        record = self.loop.candidate_from(draft, run_id=run_id, experience_id=experience_id)
        original = {"record": record.model_dump(mode="json"), "dependencies": sorted(set(depends_on)), "evidence": resolved}
        with self.store.transaction() as db:
            prior = db.execute("SELECT original,record FROM learning_experiences WHERE id=?", (experience_id,)).fetchone()
            if prior:
                _check(prior[0] == _json(original), "Experience candidate is immutable")
                return json.loads(prior[1])
            for dep in original["dependencies"]:
                row = db.execute("SELECT record FROM learning_experiences WHERE id=?", (dep,)).fetchone()
                _check(row and json.loads(row[0])["state"] in {"validated", "promoted_skill"}, "Dependent experience is not validated")
                db.execute("INSERT INTO learning_dependencies VALUES (?,?)", (experience_id, dep))
            db.execute("INSERT INTO learning_experiences VALUES (?,?,?)", (experience_id, _json(original), _json(record.model_dump(mode="json"))))
        return record.model_dump(mode="json")

    def transition(self, experience_id, target, evidence):
        target = ExperienceState(target)
        _check(isinstance(evidence, PromotionEvidence), "Existing PromotionEvidence contract required")
        evaluation = self._evidence(evidence.evaluation_ref)
        _check(evaluation["kind"] == "evaluation", "Expected a real evaluation receipt")
        outcomes = [self._evidence(ref) for ref in evidence.outcome_refs]
        _check(all(r["kind"] in {"execution", "outcome"} for r in outcomes), "Outcome references need actual execution/result records")
        units = {r.get("unit_id") for r in outcomes if r.get("unit_id")}
        _check(set(evidence.observed_run_ids) <= units, "Claimed observation units are not in resolved outcomes")
        independent = [self._evidence(ref) for ref in evidence.independent_evidence_refs]
        producers = {r["issuer"] for r in outcomes} | {self.subject_id}
        _check(all(r["issuer"] not in producers and r["kind"] == "evaluation" for r in independent), "Independent evidence must come from a different evaluator")
        if evidence.counterfactual_ref:
            _check(self._evidence(evidence.counterfactual_ref)["kind"] == "counterfactual", "Counterfactual reference is not a counterfactual record")
        if evidence.k_threshold_passed:
            _check(evaluation.get("gates", {}).get("k_threshold_passed") is True, "K gate not established by evaluation")
        if evidence.counter_evidence_resolved:
            _check(evaluation.get("gates", {}).get("counter_evidence_resolved") is True, "Counter evidence not resolved by evaluation")
        if evidence.approved_by:
            _check(evaluation.get("approved_by") == evidence.approved_by, "Approval not bound to evaluation")
        request = {"experience": experience_id, "target": target.value, "evidence": asdict(evidence)}
        key = fingerprint(request)
        with self.store.transaction() as db:
            row = db.execute("SELECT record FROM learning_experiences WHERE id=?", (experience_id,)).fetchone()
            _check(row is not None, "Unknown experience")
            record = ExperienceRecord.model_validate_json(row[0])
            if target not in {ExperienceState.DEPRECATED, ExperienceState.REVOKED}:
                _check(not record.metadata.get("review_required"), "Invalidated experience needs a new evidence-grounded candidate")
                for ref in record.evidence_refs:
                    self._evidence(ref)
            prior = db.execute("SELECT record FROM learning_transitions WHERE id=?", (key,)).fetchone()
            if prior:
                return json.loads(prior[0])
            revised = self.loop.transition(record, target, evidence).model_dump(mode="json")
            db.execute("INSERT INTO learning_transitions VALUES (?,?)", (key, _json(revised)))
            db.execute("UPDATE learning_experiences SET record=? WHERE id=?", (_json(revised), experience_id))
            return revised

    def invalidate(self, evidence_ref, *, correction_ref, reason, license_revoked=False):
        _text(reason, 2000)
        correction = self._evidence(correction_ref)
        _check(correction["kind"] == ("license_revocation" if license_revoked else "correction")
               and evidence_ref in correction.get("supersedes", []), "Correction does not concern this evidence")
        key = "invalidation_" + fingerprint({"source": evidence_ref, "correction": correction_ref, "reason": reason, "license": license_revoked})
        with self.store.transaction() as db:
            prior = db.execute("SELECT event FROM learning_invalidations WHERE id=?", (key,)).fetchone()
            if prior:
                return json.loads(prior[0])
            records = {r[0]: ExperienceRecord.model_validate_json(r[1]) for r in db.execute("SELECT id,record FROM learning_experiences")}
            impacted = {eid for eid, rec in records.items() if evidence_ref in rec.evidence_refs}
            edges = list(db.execute("SELECT experience,dependency FROM learning_dependencies"))
            while True:
                extended = impacted | {eid for eid, dep in edges if dep in impacted}
                if extended == impacted:
                    break
                impacted = extended
            for eid in sorted(impacted):
                rec = records[eid]
                refs = sorted(set(rec.counter_evidence_refs) | {correction_ref})
                rec = rec.model_copy(update={"counter_evidence_refs": refs,
                    "metadata": {**rec.metadata, "review_required": True, "invalidation_refs": sorted(set(rec.metadata.get("invalidation_refs", [])) | {key})}})
                target = ExperienceState.REVOKED if license_revoked else ExperienceState.DEPRECATED
                if rec.state != ExperienceState.REVOKED and rec.state != target:
                    rec = self.loop.transition(rec, target, PromotionEvidence(evaluation_ref=correction_ref, policy_version=self.loop.policy.version))
                db.execute("UPDATE learning_experiences SET record=? WHERE id=?", (_json(rec.model_dump(mode="json")), eid))
            event = {"id": key, "type": "experience_invalidation", "evidence_ref": evidence_ref, "correction_ref": correction_ref,
                     "reason": reason, "license_revoked": license_revoked, "impacted_experience_ids": sorted(impacted),
                     "state": "review_required", "published_information_recalled": False}
            db.execute("INSERT INTO learning_invalidations VALUES (?,?)", (key, _json(event)))
        return event
