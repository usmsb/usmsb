"""Opt-in finite-model evidence calculator, NOT a semantic planner or authority.

Known Bernoulli observation kernels and a fixed hypothesis family are required.
An AI may choose probes adaptively, but cannot turn its guesses into calibrated
kernels, verified receipts, or permissions. No network, model or paid calls occur.
See docs/research/2026-10-18-minimal-revalidation/03-mathematics.md.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Mapping


class EvidenceError(ValueError):
    """Invalid evidence, model, scope or budget; never a semantic verdict."""


def _name(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"{field} must be a nonempty string")
    return value


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceError(f"{field} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise EvidenceError(f"{field} must be finite")
    return result


@dataclass(frozen=True)
class Probe:
    id: str
    cost: float
    scope: str


@dataclass(frozen=True)
class Hypothesis:
    id: str
    probabilities: tuple[float, ...]


@dataclass(frozen=True)
class FiniteModel:
    """Immutable, explicitly supplied model; scope labels are not drift proofs."""

    family_id: str
    probes: tuple[Probe, ...]
    hypotheses: tuple[Hypothesis, ...]

    def __post_init__(self) -> None:
        _name(self.family_id, "family_id")
        if not isinstance(self.probes, tuple) or not isinstance(self.hypotheses, tuple):
            raise EvidenceError("model collections must be immutable tuples")
        if not self.probes or not self.hypotheses:
            raise EvidenceError("a model needs probes and hypotheses")
        if len({p.id for p in self.probes}) != len(self.probes):
            raise EvidenceError("duplicate probe id")
        if len({h.id for h in self.hypotheses}) != len(self.hypotheses):
            raise EvidenceError("duplicate hypothesis id")
        for probe in self.probes:
            _name(probe.id, "probe.id")
            _name(probe.scope, "probe.scope")
            if _number(probe.cost, "probe.cost") <= 0:
                raise EvidenceError("probe cost must be positive")
        for hypothesis in self.hypotheses:
            _name(hypothesis.id, "hypothesis.id")
            if not isinstance(hypothesis.probabilities, tuple):
                raise EvidenceError("probabilities must be immutable tuples")
            if len(hypothesis.probabilities) != len(self.probes):
                raise EvidenceError("every hypothesis must specify every probe")
            if any(not 0 < _number(p, "probability") < 1 for p in hypothesis.probabilities):
                raise EvidenceError("Bernoulli probabilities must lie strictly in (0,1)")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> FiniteModel:
        probes = tuple(Probe(p["id"], p["cost"], p["scope"]) for p in data["probes"])
        ids = {p.id for p in probes}
        hypotheses = []
        for hypothesis in data["hypotheses"]:
            if set(hypothesis["probabilities"]) != ids:
                raise EvidenceError("probability keys must equal probe ids")
            hypotheses.append(Hypothesis(hypothesis["id"], tuple(
                hypothesis["probabilities"][p.id] for p in probes)))
        return cls(data["family_id"], probes, tuple(hypotheses))

    def to_dict(self) -> dict[str, Any]:
        return {"family_id": self.family_id,
                "probes": [{"id": p.id, "cost": p.cost, "scope": p.scope} for p in self.probes],
                "hypotheses": [{"id": h.id, "probabilities": dict(zip(
                    [p.id for p in self.probes], h.probabilities, strict=True))}
                    for h in self.hypotheses]}

    @property
    def digest(self) -> str:
        encoded = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Observation:
    id: str
    probe_id: str
    scope: str
    outcome: int
    source_ref: str


class RevalidationSession:
    """Anytime confidence set using pairwise likelihood-ratio e-processes.

    For the true fixed h, each L(h')/L(h) is a martingale. Ville plus a union
    over the H-1 alternatives bounds any exclusion of h by delta, independent
    of the adaptive probe policy. This is a standard construction, not a new
    optimal algorithm. Model misspecification/semantic errors are NOT covered.

    Host must authenticate observations, enforce authority BEFORE executing
    probes, and supply the full enrolled stream (no favorable-only filtering).
    This calculator's allowlist/budget are defense-in-depth, not execution auth.
    """

    def __init__(self, model: FiniteModel, *, delta: float = 0.05,
                 allowed_probes: set[str] | frozenset[str] | None = None,
                 max_cost: float = 1000.0) -> None:
        if not 0 < _number(delta, "delta") < 1:
            raise EvidenceError("delta must lie in (0,1)")
        if _number(max_cost, "max_cost") <= 0:
            raise EvidenceError("max_cost must be positive")
        self.model = model
        self.delta = delta
        self.max_cost = max_cost
        self._probe_indices = {p.id: i for i, p in enumerate(model.probes)}
        self.allowed_probes = frozenset(allowed_probes if allowed_probes is not None
                                        else self._probe_indices)
        if not self.allowed_probes <= self._probe_indices.keys():
            raise EvidenceError("unknown allowed probe")
        self._scores = [0.0] * len(model.hypotheses)
        self._retained = set(range(len(model.hypotheses)))
        self._observations: dict[str, Observation] = {}
        self._sources: set[str] = set()
        self.cost = 0.0
        self.threshold = math.log(max(1, len(model.hypotheses) - 1) / delta)

    def observe(self, observation: Observation) -> bool:
        """Register one authentic receipt once; replay is idempotent, not new data."""
        _name(observation.id, "observation.id")
        _name(observation.source_ref, "source_ref")
        if type(observation.outcome) is not int or observation.outcome not in (0, 1):
            raise EvidenceError("outcome must be integer 0 or 1; missing is not zero")
        previous = self._observations.get(observation.id)
        if previous is not None:
            if previous != observation:
                raise EvidenceError("receipt id replayed with different contents")
            return False
        if observation.source_ref in self._sources:
            raise EvidenceError("same source receipt cannot be counted under a new id or probe")
        if observation.probe_id not in self.allowed_probes:
            raise EvidenceError("probe is not allowed in this session")
        index = self._probe_indices[observation.probe_id]
        probe = self.model.probes[index]
        if observation.scope != probe.scope:
            raise EvidenceError("scope mismatch: old evidence needs an explicit joint model")
        if self.cost + probe.cost > self.max_cost:
            raise EvidenceError("evidence budget exceeded")
        scores = [score + (math.log(h.probabilities[index]) if observation.outcome
                          else math.log1p(-h.probabilities[index]))
                  for score, h in zip(self._scores, self.model.hypotheses, strict=True)]
        best = max(scores)
        retained = {i for i in self._retained if best - scores[i] < self.threshold}
        self._scores = scores
        self._retained = retained
        self.cost += probe.cost
        self._observations[observation.id] = observation
        self._sources.add(observation.source_ref)
        return True

    @property
    def retained_ids(self) -> tuple[str, ...]:
        return tuple(h.id for i, h in enumerate(self.model.hypotheses) if i in self._retained)

    @property
    def log_likelihoods(self) -> dict[str, float]:
        return dict(zip((h.id for h in self.model.hypotheses), self._scores, strict=True))

    def evaluate(self, goal_revision: str, acceptable_actions: Mapping[str, set[str]]) -> dict:
        """Evaluate a supplied formal goal, never infer or authorize its semantics.

        All retained hypotheses must admit the SAME action. Pairwise overlap is
        insufficient. A goal may change without replaying evidence; a new model,
        new measurement or changed kernel cannot inherit this guarantee.
        """
        _name(goal_revision, "goal_revision")
        if set(acceptable_actions) != {h.id for h in self.model.hypotheses}:
            raise EvidenceError("goal must explicitly cover the full hypothesis family")
        for actions in acceptable_actions.values():
            if not isinstance(actions, (set, frozenset)) or not actions:
                raise EvidenceError("every hypothesis needs a nonempty action set")
            for action in actions:
                _name(action, "action")
        retained = self.retained_ids
        common = set.intersection(*(set(acceptable_actions[h]) for h in retained)) if retained else set()
        status = "model_conflict" if not retained else (
            "conditional_conclusion" if common else "inconclusive")
        return {"schema": "usmsb.finite-revalidation.v1", "status": status,
                "goal_revision": goal_revision, "model_digest": self.model.digest,
                "retained_hypotheses": list(retained), "common_actions": sorted(common),
                "receipt_count": len(self._observations), "registered_probe_cost": self.cost,
                "delta": self.delta, "semantic_validation": "not_provided",
                "authorization": "not_provided", "model_coverage": "assumed_not_verified",
                "scope": "fixed finite Bernoulli family; complete authenticated stream"}

    def snapshot(self) -> dict:
        """Portable, replayable evidence; digest detects mismatch, not forgery."""
        return {"schema": "usmsb.finite-revalidation-session.v1", "model": self.model.to_dict(),
                "model_digest": self.model.digest, "delta": self.delta,
                "allowed_probes": sorted(self.allowed_probes), "max_cost": self.max_cost,
                "observations": [{"id": o.id, "probe_id": o.probe_id, "scope": o.scope,
                                  "outcome": o.outcome, "source_ref": o.source_ref}
                                 for o in self._observations.values()]}

    @classmethod
    def restore(cls, data: Mapping[str, Any], *, expected_model_digest: str,
                allowed_probes: set[str], max_cost: float, delta: float) -> RevalidationSession:
        """Host supplies limits independently; snapshots cannot expand them."""
        if data.get("schema") != "usmsb.finite-revalidation-session.v1":
            raise EvidenceError("unknown snapshot schema")
        model = FiniteModel.from_dict(data["model"])
        if model.digest != expected_model_digest or data.get("model_digest") != model.digest:
            raise EvidenceError("model digest mismatch")
        if data.get("delta") != delta:
            raise EvidenceError("snapshot cannot change the host's error budget")
        session = cls(model, delta=delta, allowed_probes=allowed_probes, max_cost=max_cost)
        for row in data["observations"]:
            if not session.observe(Observation(**row)):
                raise EvidenceError("snapshot contains duplicate evidence")
        return session
