"""Evidence-gated Experience / Evolution state transitions.

The policy below governs whether an experience may influence future runs.  It
does not decide *what* the lesson is or encode a business workflow.  Promotion
is intentionally reversible and every transition carries an append-only audit
record so a host can explain, deprecate or revoke a harmful learned behavior.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from uuid import uuid4

from usmsb_sdk.growth_economic_harness.models import (
    ExperienceDraft,
    ExperienceRecord,
    ExperienceState,
)


class ExperienceTransitionError(ValueError):
    pass


_ALLOWED_TRANSITIONS: dict[ExperienceState, set[ExperienceState]] = {
    ExperienceState.RAW_EPISODE: {ExperienceState.CANDIDATE, ExperienceState.DEPRECATED},
    ExperienceState.CANDIDATE: {
        ExperienceState.PROBATION,
        ExperienceState.DEPRECATED,
        ExperienceState.REVOKED,
    },
    ExperienceState.PROBATION: {
        ExperienceState.VALIDATED,
        ExperienceState.DEPRECATED,
        ExperienceState.REVOKED,
    },
    ExperienceState.VALIDATED: {
        ExperienceState.PROMOTED_SKILL,
        ExperienceState.DEPRECATED,
        ExperienceState.REVOKED,
    },
    ExperienceState.PROMOTED_SKILL: {ExperienceState.DEPRECATED, ExperienceState.REVOKED},
    ExperienceState.DEPRECATED: {ExperienceState.PROBATION, ExperienceState.REVOKED},
    ExperienceState.REVOKED: set(),
}


@dataclass(frozen=True)
class PromotionEvidence:
    evaluation_ref: str
    repeated_outcomes: int = 0
    independent_evidence_refs: tuple[str, ...] = ()
    counterfactual_ref: str | None = None
    scope: str = ""
    k_threshold_passed: bool = False
    policy_version: str = ""
    observed_run_ids: tuple[str, ...] = ()
    outcome_refs: tuple[str, ...] = ()
    counter_evidence_resolved: bool = False
    approved_by: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_ref, str) or not 1 <= len(self.evaluation_ref) <= 1_000:
            raise ValueError("promotion evaluation reference is invalid")
        if (
            isinstance(self.repeated_outcomes, bool)
            or not isinstance(self.repeated_outcomes, int)
            or self.repeated_outcomes < 0
        ):
            raise ValueError("promotion repeated outcomes must be a non-negative integer")
        for name, values in (
            ("independent_evidence_refs", self.independent_evidence_refs),
            ("observed_run_ids", self.observed_run_ids),
            ("outcome_refs", self.outcome_refs),
        ):
            if (
                not isinstance(values, tuple)
                or len(values) > 10_000
                or any(not isinstance(item, str) or not 1 <= len(item) <= 1_000 for item in values)
            ):
                raise ValueError(f"promotion {name} is invalid")
        for name, value in (
            ("k_threshold_passed", self.k_threshold_passed),
            ("counter_evidence_resolved", self.counter_evidence_resolved),
        ):
            if type(value) is not bool:
                raise ValueError(f"promotion {name} must be a boolean")
        for name, value, maximum in (
            ("counterfactual_ref", self.counterfactual_ref, 1_000),
            ("scope", self.scope, 2_000),
            ("policy_version", self.policy_version, 200),
            ("approved_by", self.approved_by, 200),
        ):
            if value is not None and (
                not isinstance(value, str) or len(value) > maximum
            ):
                raise ValueError(f"promotion {name} is invalid")


@dataclass(frozen=True)
class ExperiencePromotionPolicy:
    """Configurable safety gate; never a substitute for model judgement."""

    version: str = "growth-experience-policy.v1"
    probation_min_distinct_runs: int = 1
    validation_min_distinct_runs: int = 2
    promotion_min_distinct_runs: int = 3
    validation_min_independent_evidence: int = 1
    promotion_requires_counterfactual: bool = True
    promotion_requires_k_gate: bool = True
    promotion_requires_approval: bool = False

    def __post_init__(self) -> None:
        values = (
            self.probation_min_distinct_runs,
            self.validation_min_distinct_runs,
            self.promotion_min_distinct_runs,
            self.validation_min_independent_evidence,
        )
        if any(
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
            for value in values
        ):
            raise ValueError("experience promotion thresholds must be non-negative")
        if any(
            type(value) is not bool
            for value in (
                self.promotion_requires_counterfactual,
                self.promotion_requires_k_gate,
                self.promotion_requires_approval,
            )
        ):
            raise ValueError("experience promotion policy flags must be booleans")
        if not isinstance(self.version, str) or not self.version.strip():
            raise ValueError("experience promotion policy version is required")


class ExperienceLoop:
    def __init__(self, policy: ExperiencePromotionPolicy | None = None) -> None:
        self.policy = policy or ExperiencePromotionPolicy()

    def candidate_from(self, draft: ExperienceDraft, *, run_id: str) -> ExperienceRecord:
        return ExperienceRecord(
            experience_id=f"exp_{uuid4().hex}",
            state=ExperienceState.CANDIDATE,
            lesson=draft.lesson,
            applicability=draft.applicability,
            evidence_refs=draft.evidence_refs,
            counter_evidence_refs=draft.counter_evidence_refs,
            confidence=draft.confidence,
            source_run_id=run_id,
        )

    def transition(
        self,
        record: ExperienceRecord,
        target: ExperienceState,
        evidence: PromotionEvidence,
    ) -> ExperienceRecord:
        if target not in _ALLOWED_TRANSITIONS[record.state]:
            raise ExperienceTransitionError(
                f"experience transition {record.state.value}->{target.value} is not allowed"
            )
        if not evidence.evaluation_ref or not evidence.policy_version:
            raise ExperienceTransitionError("evaluation_ref and policy_version are required")
        if evidence.policy_version != self.policy.version:
            raise ExperienceTransitionError("promotion evidence policy version is not active")

        distinct_runs = {item for item in evidence.observed_run_ids if item}
        if (
            target == ExperienceState.PROBATION
            and evidence.repeated_outcomes
            and not distinct_runs
        ):
            # Backwards compatible evidence can enter probation, but cannot be
            # validated or promoted without independently attributable runs.
            distinct_runs = {f"legacy-observation-{index}" for index in range(evidence.repeated_outcomes)}
        if target == ExperienceState.PROBATION:
            self._require_runs(distinct_runs, self.policy.probation_min_distinct_runs, target)
        if target in {ExperienceState.VALIDATED, ExperienceState.PROMOTED_SKILL}:
            required_runs = (
                self.policy.promotion_min_distinct_runs
                if target == ExperienceState.PROMOTED_SKILL
                else self.policy.validation_min_distinct_runs
            )
            self._require_runs(distinct_runs, required_runs, target)
            attributable_outcomes = {item for item in evidence.outcome_refs if item}
            if len(attributable_outcomes) < required_runs:
                raise ExperienceTransitionError(
                    f"{target.value} requires at least {required_runs} attributable outcomes"
                )
            if len(set(evidence.independent_evidence_refs)) < self.policy.validation_min_independent_evidence:
                raise ExperienceTransitionError("validated experience requires independent evidence")
            if not evidence.scope:
                raise ExperienceTransitionError("validated experience requires an applicability scope")
            if record.counter_evidence_refs and not evidence.counter_evidence_resolved:
                raise ExperienceTransitionError("counter evidence must be resolved before validation")
        if target == ExperienceState.PROMOTED_SKILL:
            if self.policy.promotion_requires_k_gate and not evidence.k_threshold_passed:
                raise ExperienceTransitionError(
                    "promoted customer-outcome skill requires k/experiment gate"
                )
            if self.policy.promotion_requires_counterfactual and not evidence.counterfactual_ref:
                raise ExperienceTransitionError("promoted skill requires counterfactual evidence")
            if self.policy.promotion_requires_approval and not evidence.approved_by:
                raise ExperienceTransitionError("promoted skill requires explicit approval")

        transition = {
            "from": record.state.value,
            "to": target.value,
            "policy": asdict(self.policy),
            "evidence": self._evidence_dict(evidence),
        }
        history = list(record.metadata.get("transition_history") or [])
        history.append(transition)
        metadata: dict[str, Any] = {
            **record.metadata,
            "promotion_evidence": self._evidence_dict(evidence),
            "transition_history": history,
        }
        return record.model_copy(update={"state": target, "metadata": metadata})

    @staticmethod
    def _require_runs(
        observed_run_ids: set[str],
        minimum: int,
        target: ExperienceState,
    ) -> None:
        if len(observed_run_ids) < minimum:
            raise ExperienceTransitionError(
                f"{target.value} requires at least {minimum} distinct attributable runs"
            )

    @staticmethod
    def _evidence_dict(evidence: PromotionEvidence) -> dict[str, Any]:
        return {
            "evaluation_ref": evidence.evaluation_ref,
            "repeated_outcomes": evidence.repeated_outcomes,
            "independent_evidence_refs": list(evidence.independent_evidence_refs),
            "counterfactual_ref": evidence.counterfactual_ref,
            "scope": evidence.scope,
            "k_threshold_passed": evidence.k_threshold_passed,
            "policy_version": evidence.policy_version,
            "observed_run_ids": list(evidence.observed_run_ids),
            "outcome_refs": list(evidence.outcome_refs),
            "counter_evidence_resolved": evidence.counter_evidence_resolved,
            "approved_by": evidence.approved_by,
        }
