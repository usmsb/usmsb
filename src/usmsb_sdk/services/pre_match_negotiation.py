"""
Pre-Match Negotiation Service

Enables agents to negotiate and verify capabilities before formal matching.
Provides:
- Pre-match negotiation sessions
- Clarification Q&A
- Capability verification requests
- Match confirmation/decline
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
Base = declarative_base()


# ==================== Enums ====================

class NegotiationStatus(Enum):
    """Status of pre-match negotiation"""
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    CONFIRMED = "confirmed"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class VerificationType(Enum):
    """Types of capability verification"""
    PORTFOLIO = "portfolio"
    TEST_TASK = "test_task"
    REFERENCE = "reference"
    GENE_CAPSULE = "gene_capsule"
    CERTIFICATE = "certificate"


# ==================== Data Classes ====================

@dataclass
class ClarificationQA:
    """Clarification question and answer"""
    question_id: str
    question: str
    asker_id: str  # demand_agent or supply_agent
    answer: str | None = None
    answerer_id: str | None = None
    asked_at: datetime = field(default_factory=datetime.now)
    answered_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "question": self.question,
            "asker_id": self.asker_id,
            "answer": self.answer,
            "answerer_id": self.answerer_id,
            "asked_at": self.asked_at.isoformat(),
            "answered_at": self.answered_at.isoformat() if self.answered_at else None,
        }


@dataclass
class VerificationRequest:
    """Capability verification request"""
    request_id: str
    capability: str
    verification_type: VerificationType
    request_detail: str
    response: str | None = None
    response_attachments: list[str] = field(default_factory=list)
    status: str = "pending"  # pending, submitted, verified, failed
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "capability": self.capability,
            "verification_type": self.verification_type.value,
            "request_detail": self.request_detail,
            "response": self.response,
            "response_attachments": self.response_attachments,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class ScopeConfirmation:
    """Scope confirmation details"""
    deliverables: list[str] = field(default_factory=list)
    timeline: str | None = None
    milestones: list[dict[str, Any]] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "deliverables": self.deliverables,
            "timeline": self.timeline,
            "milestones": self.milestones,
            "exclusions": self.exclusions,
            "assumptions": self.assumptions,
        }


@dataclass
class GeneCapsuleMatch:
    """Gene capsule match result for negotiation"""
    matched_experiences: list[dict[str, Any]] = field(default_factory=list)
    relevance_score: float = 0.0
    verified_count: int = 0
    total_experience_value: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched_experiences": self.matched_experiences,
            "relevance_score": self.relevance_score,
            "verified_count": self.verified_count,
            "total_experience_value": self.total_experience_value,
        }


# ==================== Database Models ====================

class PreMatchNegotiationDB(Base):
    """Database model for pre-match negotiations"""
    __tablename__ = "pre_match_negotiations"

    negotiation_id = Column(String(64), primary_key=True)
    demand_agent_id = Column(String(64), nullable=False)
    supply_agent_id = Column(String(64), nullable=False)
    demand_id = Column(String(64))

    # Status
    status = Column(String(32), default=NegotiationStatus.INITIATED.value)

    # Clarification Q&A
    clarification_qa = Column(Text)  # JSON

    # Scope confirmation
    scope_confirmation = Column(Text)  # JSON

    # Capability verification
    capability_verification = Column(Text)  # JSON

    # Gene capsule match
    gene_capsule_match = Column(Text)  # JSON

    # Mutual interest
    mutual_interest = Column(Boolean, default=None)

    # FIX: Supply agent consent — negotiation cannot proceed without this
    # None = not yet asked, True = accepted, False = declined
    supply_consent = Column(Boolean, default=None)

    # Terms
    proposed_terms = Column(Text)  # JSON
    agreed_terms = Column(Text)  # JSON

    # Timestamps
    initiated_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)

    # Outcome
    outcome_reason = Column(Text)


# ==================== Main Service ====================

class PreMatchNegotiationService:
    """
    Service for managing pre-match negotiations.

    Allows agents to:
    1. Ask clarifying questions
    2. Request capability verification
    3. Confirm scope and deliverables
    4. Accept or decline match
    """

    DEFAULT_EXPIRATION_HOURS = 24

    def __init__(
        self,
        db_session: Session | None = None,
        gene_capsule_service: Any | None = None,
        logger: logging.Logger | None = None,
    ):
        self.db = db_session
        self.gene_capsule_service = gene_capsule_service
        self.logger = logger or logging.getLogger(__name__)

        # In-memory cache for active negotiations
        self._active_negotiations: dict[str, dict] = {}

    async def initiate(
        self,
        demand_agent_id: str,
        supply_agent_id: str,
        demand_id: str,
        initial_message: str | None = None,
        expiration_hours: int = DEFAULT_EXPIRATION_HOURS,
        initiator_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Initiate a pre-match negotiation.

        Args:
            demand_agent_id: The demand side agent
            supply_agent_id: The supply side agent
            demand_id: Associated demand ID
            initial_message: Optional opening message
            expiration_hours: Hours until negotiation expires
            initiator_id: The agent initiating this (must be demand or supply)
        """
        # Participant validation: initiator must be one of the parties
        if initiator_id and initiator_id not in [demand_agent_id, supply_agent_id]:
            raise PermissionError(
                f"Initiator {initiator_id} is not a party to this negotiation"
            )

        negotiation_id = f"neg-{uuid4().hex[:12]}"

        # Create negotiation record
        negotiation = PreMatchNegotiationDB(
            negotiation_id=negotiation_id,
            demand_agent_id=demand_agent_id,
            supply_agent_id=supply_agent_id,
            demand_id=demand_id,
            status=NegotiationStatus.INITIATED.value,
            clarification_qa=json.dumps([]),
            scope_confirmation=json.dumps({}),
            capability_verification=json.dumps({"requests": []}),
            gene_capsule_match=json.dumps({}),
            initiated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=expiration_hours),
        )

        self.db.add(negotiation)
        self.db.commit()

        # Get gene capsule match for context
        gene_capsule_match = await self._get_gene_capsule_match(supply_agent_id, demand_id)

        self.logger.info(
            f"Initiated negotiation {negotiation_id} "
            f"between {demand_agent_id} and {supply_agent_id}"
        )

        return {
            "negotiation_id": negotiation_id,
            "demand_agent_id": demand_agent_id,
            "supply_agent_id": supply_agent_id,
            "demand_id": demand_id,
            "status": NegotiationStatus.INITIATED.value,
            "supply_consent": None,  # FIX: supply must consent before proceeding
            "initiated_at": negotiation.initiated_at.isoformat(),
            "expires_at": negotiation.expires_at.isoformat(),
            "gene_capsule_match": gene_capsule_match,
        }

    async def get_negotiation(self, negotiation_id: str) -> dict[str, Any] | None:
        """Get negotiation details"""
        negotiation = self.db.query(PreMatchNegotiationDB).filter(
            PreMatchNegotiationDB.negotiation_id == negotiation_id
        ).first()

        if not negotiation:
            return None

        return self._negotiation_to_dict(negotiation)

    # FIX: Supply agent consent — negotiation cannot proceed without consent
    async def request_consent(
        self,
        negotiation_id: str,
        requester_id: str,
    ) -> dict[str, Any]:
        """
        Request supply agent's consent to proceed with negotiation.

        This is typically called by the demand agent to formally request
        the supply agent's agreement before proceeding with Q&A.

        Args:
            negotiation_id: The negotiation ID
            requester_id: Agent requesting consent (must be demand or supply)

        Returns:
            Negotiation dict with consent status
        """
        negotiation = self._get_and_validate_negotiation(negotiation_id)
        if not negotiation:
            raise ValueError(f"Negotiation {negotiation_id} not found or expired")

        # FIX: Only demand agent can request consent
        if requester_id != negotiation.demand_agent_id:
            raise PermissionError(
                f"Only the demand agent can request consent. "
                f"Requester: {requester_id}, Demand: {negotiation.demand_agent_id}"
            )

        # Already declined
        if negotiation.supply_consent is False:
            raise ValueError("Supply agent already declined this negotiation")

        # Already consented
        if negotiation.supply_consent is True:
            return {
                "negotiation_id": negotiation_id,
                "status": negotiation.status,
                "supply_consent": True,
                "message": "Supply agent already consented",
            }

        # Ask for consent
        self.logger.info(
            f"Consent requested for negotiation {negotiation_id} "
            f"from supply {negotiation.supply_agent_id}"
        )

        return {
            "negotiation_id": negotiation_id,
            "status": negotiation.status,
            "supply_consent": negotiation.supply_consent,
            "message": "Consent request sent to supply agent. "
                       "Supply agent must call confirm_consent() or decline_consent().",
        }

    async def confirm_consent(
        self,
        negotiation_id: str,
        supply_agent_id: str,
    ) -> dict[str, Any]:
        """
        Supply agent confirms consent to proceed with negotiation.

        Args:
            negotiation_id: The negotiation ID
            supply_agent_id: Supply agent confirming (must be the supply party)

        Returns:
            Negotiation dict

        Raises:
            PermissionError: If supply_agent_id doesn't match
            ValueError: If already declined or expired
        """
        negotiation = self._get_and_validate_negotiation(negotiation_id)
        if not negotiation:
            raise ValueError(f"Negotiation {negotiation_id} not found or expired")

        # FIX: Validate supply agent
        if supply_agent_id != negotiation.supply_agent_id:
            raise PermissionError(
                f"Only the supply agent can confirm consent. "
                f"Supplier: {negotiation.supply_agent_id}, Caller: {supply_agent_id}"
            )

        if negotiation.supply_consent is False:
            raise ValueError("Negotiation was already declined by supply agent")

        negotiation.supply_consent = True
        negotiation.last_updated = datetime.utcnow()
        self.db.commit()

        self.logger.info(f"Supply agent {supply_agent_id} consented to negotiation {negotiation_id}")

        return {
            "negotiation_id": negotiation_id,
            "status": negotiation.status,
            "supply_consent": True,
            "message": "Consent confirmed. Negotiation can now proceed.",
        }

    async def decline_consent(
        self,
        negotiation_id: str,
        supply_agent_id: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """
        Supply agent declines to participate in negotiation.

        Args:
            negotiation_id: The negotiation ID
            supply_agent_id: Supply agent declining (must be the supply party)
            reason: Optional reason for declining

        Returns:
            Negotiation dict
        """
        negotiation = self._get_and_validate_negotiation(negotiation_id)
        if not negotiation:
            raise ValueError(f"Negotiation {negotiation_id} not found or expired")

        # FIX: Validate supply agent
        if supply_agent_id != negotiation.supply_agent_id:
            raise PermissionError(
                f"Only the supply agent can decline consent. "
                f"Supplier: {negotiation.supply_agent_id}, Caller: {supply_agent_id}"
            )

        negotiation.supply_consent = False
        negotiation.outcome_reason = reason or "Supply agent declined"
        negotiation.status = NegotiationStatus.DECLINED.value
        negotiation.last_updated = datetime.utcnow()
        self.db.commit()

        self.logger.info(f"Supply agent {supply_agent_id} declined negotiation {negotiation_id}")

        return {
            "negotiation_id": negotiation_id,
            "status": NegotiationStatus.DECLINED.value,
            "supply_consent": False,
            "reason": reason,
        }

    async def ask_question(
        self,
        negotiation_id: str,
        question: str,
        asker_id: str,
    ) -> ClarificationQA:
        """
        Ask a clarification question.

        Either agent can ask questions to clarify requirements or capabilities.
        FIX: Requires supply_consent before proceeding.
        """
        negotiation = self._get_and_validate_negotiation(negotiation_id)
        if not negotiation:
            raise ValueError(f"Negotiation {negotiation_id} not found or expired")

        # FIX: Supply agent must have consented before Q&A can begin
        if negotiation.supply_consent is not True:
            raise PermissionError(
                "Supply agent must consent before Q&A can begin. "
                "Call confirm_consent() first."
            )

        qa = ClarificationQA(
            question_id=f"qa-{uuid4().hex[:8]}",
            question=question,
            asker_id=asker_id,
        )

        # Add to clarification list
        clarification_list = json.loads(negotiation.clarification_qa)
        clarification_list.append(qa.to_dict())
        negotiation.clarification_qa = json.dumps(clarification_list)
        negotiation.status = NegotiationStatus.IN_PROGRESS.value
        negotiation.last_updated = datetime.utcnow()

        self.db.commit()

        self.logger.info(f"Question asked in negotiation {negotiation_id} by {asker_id}")

        return qa

    async def answer_question(
        self,
        negotiation_id: str,
        question_id: str,
        answer: str,
        answerer_id: str,
    ) -> ClarificationQA:
        """
        Answer a clarification question.
        """
        negotiation = self._get_and_validate_negotiation(negotiation_id)
        if not negotiation:
            raise ValueError(f"Negotiation {negotiation_id} not found or expired")

        clarification_list = json.loads(negotiation.clarification_qa)

        for qa_data in clarification_list:
            if qa_data["question_id"] == question_id:
                qa_data["answer"] = answer
                qa_data["answerer_id"] = answerer_id
                qa_data["answered_at"] = datetime.utcnow().isoformat()

                negotiation.clarification_qa = json.dumps(clarification_list)
                negotiation.last_updated = datetime.utcnow()

                self.db.commit()

                self.logger.info(f"Question answered in negotiation {negotiation_id}")

                return ClarificationQA(
                    question_id=qa_data["question_id"],
                    question=qa_data["question"],
                    asker_id=qa_data["asker_id"],
                    answer=qa_data["answer"],
                    answerer_id=qa_data["answerer_id"],
                    asked_at=datetime.fromisoformat(qa_data["asked_at"]),
                    answered_at=datetime.fromisoformat(qa_data["answered_at"]),
                )

        raise ValueError(f"Question {question_id} not found")

    async def request_capability_verification(
        self,
        negotiation_id: str,
        capability: str,
        verification_type: VerificationType,
        request_detail: str,
    ) -> VerificationRequest:
        """
        Request capability verification from supply agent.

        Demand agent can request proof of specific capabilities.
        """
        negotiation = self._get_and_validate_negotiation(negotiation_id)
        if not negotiation:
            raise ValueError(f"Negotiation {negotiation_id} not found or expired")

        request = VerificationRequest(
            request_id=f"vr-{uuid4().hex[:8]}",
            capability=capability,
            verification_type=verification_type,
            request_detail=request_detail,
        )

        # Add to verification list
        verification_data = json.loads(negotiation.capability_verification)
        verification_data["requests"].append(request.to_dict())
        negotiation.capability_verification = json.dumps(verification_data)
        negotiation.status = NegotiationStatus.IN_PROGRESS.value
        negotiation.last_updated = datetime.utcnow()

        self.db.commit()

        self.logger.info(
            f"Verification request created in negotiation {negotiation_id} "
            f"for capability {capability}"
        )

        return request

    async def respond_to_verification(
        self,
        negotiation_id: str,
        request_id: str,
        response: str,
        attachments: list[str] | None = None,
    ) -> VerificationRequest:
        """
        Respond to a capability verification request.
        """
        negotiation = self._get_and_validate_negotiation(negotiation_id)
        if not negotiation:
            raise ValueError(f"Negotiation {negotiation_id} not found or expired")

        verification_data = json.loads(negotiation.capability_verification)

        for req_data in verification_data["requests"]:
            if req_data["request_id"] == request_id:
                req_data["response"] = response
                req_data["response_attachments"] = attachments or []
                req_data["status"] = "submitted"
                req_data["resolved_at"] = datetime.utcnow().isoformat()

                negotiation.capability_verification = json.dumps(verification_data)
                negotiation.last_updated = datetime.utcnow()

                self.db.commit()

                self.logger.info(f"Verification response submitted for {request_id}")

                return VerificationRequest(
                    request_id=req_data["request_id"],
                    capability=req_data["capability"],
                    verification_type=VerificationType(req_data["verification_type"]),
                    request_detail=req_data["request_detail"],
                    response=req_data["response"],
                    response_attachments=req_data["response_attachments"],
                    status=req_data["status"],
                    created_at=datetime.fromisoformat(req_data["created_at"]),
                    resolved_at=datetime.fromisoformat(req_data["resolved_at"]),
                )

        raise ValueError(f"Verification request {request_id} not found")

    async def confirm_scope(
        self,
        negotiation_id: str,
        scope: ScopeConfirmation,
    ) -> dict[str, Any]:
        """
        Confirm the scope of the engagement.
        """
        negotiation = self._get_and_validate_negotiation(negotiation_id)
        if not negotiation:
            raise ValueError(f"Negotiation {negotiation_id} not found or expired")

        negotiation.scope_confirmation = json.dumps(scope.to_dict())
        negotiation.last_updated = datetime.utcnow()

        self.db.commit()

        self.logger.info(f"Scope confirmed for negotiation {negotiation_id}")

        return scope.to_dict()

    async def propose_terms(
        self,
        negotiation_id: str,
        terms: dict[str, Any],
        proposer_id: str,
    ) -> dict[str, Any]:
        """
        Propose terms for the engagement.
        """
        negotiation = self._get_and_validate_negotiation(negotiation_id)
        if not negotiation:
            raise ValueError(f"Negotiation {negotiation_id} not found or expired")

        negotiation.proposed_terms = json.dumps({
            "terms": terms,
            "proposer_id": proposer_id,
            "proposed_at": datetime.utcnow().isoformat(),
        })
        negotiation.last_updated = datetime.utcnow()

        self.db.commit()

        self.logger.info(f"Terms proposed for negotiation {negotiation_id}")

        return {"proposed": True, "terms": terms}

    async def agree_to_terms(
        self,
        negotiation_id: str,
        terms: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Agree to proposed terms.
        """
        negotiation = self._get_and_validate_negotiation(negotiation_id)
        if not negotiation:
            raise ValueError(f"Negotiation {negotiation_id} not found or expired")

        agreed = terms or json.loads(negotiation.proposed_terms).get("terms", {})
        negotiation.agreed_terms = json.dumps(agreed)
        negotiation.last_updated = datetime.utcnow()

        self.db.commit()

        return {"agreed": True, "terms": agreed}

    async def confirm_match(
        self,
        negotiation_id: str,
        confirmer_id: str,
    ) -> dict[str, Any]:
        """
        Confirm the match - both parties must confirm.

        Uses atomic UPDATE to prevent TOCTOU race condition:
        Only one confirmation can succeed if mutual_interest is currently NULL.
        """
        negotiation = self._get_and_validate_negotiation(negotiation_id)
        if not negotiation:
            raise ValueError(f"Negotiation {negotiation_id} not found or expired")

        # Validate confirmer is a party
        if confirmer_id not in [negotiation.demand_agent_id, negotiation.supply_agent_id]:
            raise PermissionError(f"Confirmer {confirmer_id} is not a party to this negotiation")

        # Atomic update: only succeeds if mutual_interest is still NULL
        # This prevents TOCTOU race (two simultaneous confirms)
        rows_updated = self.db.query(PreMatchNegotiationDB).filter(
            PreMatchNegotiationDB.negotiation_id == negotiation_id,
            PreMatchNegotiationDB.mutual_interest.is_(None),
        ).update(
            {
                "mutual_interest": True,
                "last_updated": datetime.utcnow(),
            },
            synchronize_session=False,
        )
        self.db.commit()

        if rows_updated == 0:
            # Either already confirmed (mutual_interest = True) or declined (False)
            re_check = self.db.query(PreMatchNegotiationDB).filter(
                PreMatchNegotiationDB.negotiation_id == negotiation_id
            ).first()
            if re_check and re_check.mutual_interest:
                return {
                    "status": "confirmed",
                    "message": "Match already confirmed by both parties",
                    "negotiation": self._negotiation_to_dict(re_check),
                }
            raise ValueError("Match was already declined or another confirmation was processed")

        self.logger.info(f"First confirmation for negotiation {negotiation_id}")

        # Re-fetch to get updated state
        re_check = self.db.query(PreMatchNegotiationDB).filter(
            PreMatchNegotiationDB.negotiation_id == negotiation_id
        ).first()

        # Now do the second confirmation atomically as well
        rows_updated2 = self.db.query(PreMatchNegotiationDB).filter(
            PreMatchNegotiationDB.negotiation_id == negotiation_id,
            PreMatchNegotiationDB.mutual_interest == True,
            PreMatchNegotiationDB.status == NegotiationStatus.INITIATED.value,
        ).update(
            {
                "status": NegotiationStatus.CONFIRMED.value,
                "last_updated": datetime.utcnow(),
            },
            synchronize_session=False,
        )
        self.db.commit()

        if rows_updated2 > 0:
            self.logger.info(f"Match confirmed for negotiation {negotiation_id}")
            return {
                "status": "confirmed",
                "message": "Match confirmed by both parties",
                "negotiation": self._negotiation_to_dict(re_check),
            }

        return {
            "status": "pending_counterpart",
            "message": "Waiting for counterpart confirmation",
        }

    async def decline_match(
        self,
        negotiation_id: str,
        reason: str,
        decliner_id: str,
    ) -> dict[str, Any]:
        """
        Decline the match.
        """
        negotiation = self._get_and_validate_negotiation(negotiation_id)
        if not negotiation:
            raise ValueError(f"Negotiation {negotiation_id} not found or expired")

        negotiation.status = NegotiationStatus.DECLINED.value
        negotiation.mutual_interest = False
        negotiation.outcome_reason = reason
        negotiation.last_updated = datetime.utcnow()

        self.db.commit()

        self.logger.info(f"Match declined for negotiation {negotiation_id}: {reason}")

        return {
            "status": "declined",
            "reason": reason,
        }

    async def cancel_negotiation(
        self,
        negotiation_id: str,
        reason: str,
        canceller_id: str,
    ) -> dict[str, Any]:
        """
        Cancel the negotiation.
        """
        negotiation = self._get_and_validate_negotiation(negotiation_id)
        if not negotiation:
            raise ValueError(f"Negotiation {negotiation_id} not found or expired")

        negotiation.status = NegotiationStatus.CANCELLED.value
        negotiation.outcome_reason = reason
        negotiation.last_updated = datetime.utcnow()

        self.db.commit()

        self.logger.info(f"Negotiation {negotiation_id} cancelled: {reason}")

        return {
            "status": "cancelled",
            "reason": reason,
        }

    async def get_negotiations_for_agent(
        self,
        agent_id: str,
        status: NegotiationStatus | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get all negotiations for an agent.
        """
        query = self.db.query(PreMatchNegotiationDB).filter(
            (PreMatchNegotiationDB.demand_agent_id == agent_id) |
            (PreMatchNegotiationDB.supply_agent_id == agent_id)
        )

        if status:
            query = query.filter(PreMatchNegotiationDB.status == status.value)

        query = query.order_by(PreMatchNegotiationDB.last_updated.desc()).limit(limit)

        negotiations = query.all()

        return [self._negotiation_to_dict(n) for n in negotiations]

    async def check_expired_negotiations(self) -> int:
        """
        Check and mark expired negotiations.
        """
        expired = self.db.query(PreMatchNegotiationDB).filter(
            PreMatchNegotiationDB.status.in_([
                NegotiationStatus.INITIATED.value,
                NegotiationStatus.IN_PROGRESS.value,
            ]),
            PreMatchNegotiationDB.expires_at < datetime.utcnow(),
        ).all()

        for negotiation in expired:
            negotiation.status = NegotiationStatus.EXPIRED.value
            negotiation.outcome_reason = "Negotiation expired"

        self.db.commit()

        if expired:
            self.logger.info(f"Marked {len(expired)} negotiations as expired")

        return len(expired)

    # ==================== Helper Methods ====================

    def _get_and_validate_negotiation(
        self,
        negotiation_id: str,
    ) -> PreMatchNegotiationDB | None:
        """Get negotiation and validate it's not expired"""
        negotiation = self.db.query(PreMatchNegotiationDB).filter(
            PreMatchNegotiationDB.negotiation_id == negotiation_id
        ).first()

        if not negotiation:
            return None

        # Check expiration
        if negotiation.expires_at and datetime.utcnow() > negotiation.expires_at:
            if negotiation.status in [NegotiationStatus.INITIATED.value, NegotiationStatus.IN_PROGRESS.value]:
                negotiation.status = NegotiationStatus.EXPIRED.value
                self.db.commit()
            return None

        # Check if already concluded
        if negotiation.status in [
            NegotiationStatus.CONFIRMED.value,
            NegotiationStatus.DECLINED.value,
            NegotiationStatus.CANCELLED.value,
            NegotiationStatus.EXPIRED.value,
        ]:
            return None

        return negotiation

    async def _get_gene_capsule_match(
        self,
        supply_agent_id: str,
        demand_id: str,
    ) -> GeneCapsuleMatch:
        """Get gene capsule match for context"""
        if not self.gene_capsule_service:
            return GeneCapsuleMatch()

        try:
            # Get demand details and search for matching experiences
            # This would integrate with the gene capsule matching service
            result = GeneCapsuleMatch(
                matched_experiences=[],
                relevance_score=0.0,
                verified_count=0,
                total_experience_value=0.0,
            )
            return result
        except Exception as e:
            self.logger.error(f"Error getting gene capsule match: {e}")
            return GeneCapsuleMatch()

    def _negotiation_to_dict(self, negotiation: PreMatchNegotiationDB) -> dict[str, Any]:
        """Convert negotiation DB model to dict"""
        return {
            "negotiation_id": negotiation.negotiation_id,
            "demand_agent_id": negotiation.demand_agent_id,
            "supply_agent_id": negotiation.supply_agent_id,
            "demand_id": negotiation.demand_id,
            "status": negotiation.status,
            "clarification_qa": json.loads(negotiation.clarification_qa),
            "scope_confirmation": json.loads(negotiation.scope_confirmation),
            "capability_verification": json.loads(negotiation.capability_verification),
            "gene_capsule_match": json.loads(negotiation.gene_capsule_match),
            "mutual_interest": negotiation.mutual_interest,
            "proposed_terms": json.loads(negotiation.proposed_terms) if negotiation.proposed_terms else None,
            "agreed_terms": json.loads(negotiation.agreed_terms) if negotiation.agreed_terms else None,
            "initiated_at": negotiation.initiated_at.isoformat() if negotiation.initiated_at else None,
            "last_updated": negotiation.last_updated.isoformat() if negotiation.last_updated else None,
            "expires_at": negotiation.expires_at.isoformat() if negotiation.expires_at else None,
            "outcome_reason": negotiation.outcome_reason,
        }
