"""Evidence-gated Experience / Evolution state transitions."""

from __future__ import annotations

from dataclasses import dataclass
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


class ExperienceLoop:
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
        if target in {ExperienceState.VALIDATED, ExperienceState.PROMOTED_SKILL}:
            if evidence.repeated_outcomes < 2:
                raise ExperienceTransitionError("validated experience requires repeated outcomes")
            if not evidence.independent_evidence_refs:
                raise ExperienceTransitionError(
                    "validated experience requires independent evidence"
                )
            if not evidence.scope:
                raise ExperienceTransitionError(
                    "validated experience requires an applicability scope"
                )
        if target == ExperienceState.PROMOTED_SKILL and not evidence.k_threshold_passed:
            raise ExperienceTransitionError(
                "promoted customer-outcome skill requires k/experiment gate"
            )

        metadata = {
            **record.metadata,
            "promotion_evidence": {
                "evaluation_ref": evidence.evaluation_ref,
                "repeated_outcomes": evidence.repeated_outcomes,
                "independent_evidence_refs": list(evidence.independent_evidence_refs),
                "counterfactual_ref": evidence.counterfactual_ref,
                "scope": evidence.scope,
                "k_threshold_passed": evidence.k_threshold_passed,
                "policy_version": evidence.policy_version,
            },
        }
        return record.model_copy(update={"state": target, "metadata": metadata})
