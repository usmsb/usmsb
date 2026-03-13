"""
Negotiation Module

Manages negotiation sessions between agents.
Supports proposal/counter-proposal workflows.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from usmsb_sdk.agent_sdk.platform_client import PlatformClient, APIResponse


logger = logging.getLogger(__name__)


class NegotiationStatus(Enum):
    """Negotiation session status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ProposalType(Enum):
    """Type of proposal"""
    INITIAL = "initial"
    COUNTER = "counter"
    FINAL = "final"


@dataclass
class NegotiationTerms:
    """Terms for a negotiation proposal"""
    price: float
    delivery_time: Optional[datetime] = None
    delivery_description: str = ""
    quality_guarantees: Dict[str, Any] = field(default_factory=dict)
    payment_terms: str = "escrow"  # upfront, escrow, milestone
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    additional_conditions: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "price": self.price,
            "delivery_time": self.delivery_time.isoformat() if self.delivery_time else None,
            "delivery_description": self.delivery_description,
            "quality_guarantees": self.quality_guarantees,
            "payment_terms": self.payment_terms,
            "milestones": self.milestones,
            "additional_conditions": self.additional_conditions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NegotiationTerms":
        delivery_time = None
        if data.get("delivery_time"):
            if isinstance(data["delivery_time"], str):
                delivery_time = datetime.fromisoformat(data["delivery_time"])
            else:
                delivery_time = data["delivery_time"]

        return cls(
            price=data.get("price", 0),
            delivery_time=delivery_time,
            delivery_description=data.get("delivery_description", ""),
            quality_guarantees=data.get("quality_guarantees", {}),
            payment_terms=data.get("payment_terms", "escrow"),
            milestones=data.get("milestones", []),
            additional_conditions=data.get("additional_conditions", {}),
        )


@dataclass
class NegotiationContext:
    """Context for a negotiation"""
    demand_id: Optional[str]
    service_id: Optional[str]
    task_description: str
    initial_terms: Optional[NegotiationTerms]
    constraints: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "demand_id": self.demand_id,
            "service_id": self.service_id,
            "task_description": self.task_description,
            "initial_terms": self.initial_terms.to_dict() if self.initial_terms else None,
            "constraints": self.constraints,
        }


@dataclass
class NegotiationRound:
    """A single round in a negotiation"""
    round_number: int
    proposer_id: str
    terms: NegotiationTerms
    response: str  # pending, accepted, counter, rejected
    responded_at: Optional[datetime]
    notes: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NegotiationRound":
        return cls(
            round_number=data.get("round_number", 0),
            proposer_id=data.get("proposer_id", ""),
            terms=NegotiationTerms.from_dict(data.get("terms", data.get("proposal", {}))),
            response=data.get("response", "pending"),
            responded_at=datetime.fromisoformat(data["responded_at"]) if data.get("responded_at") else None,
            notes=data.get("notes", ""),
        )


@dataclass
class NegotiationSession:
    """A negotiation session between two agents"""
    session_id: str
    initiator_id: str
    counterpart_id: str
    context: NegotiationContext
    status: str
    rounds: List[NegotiationRound]
    final_terms: Optional[NegotiationTerms]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    @property
    def current_round(self) -> int:
        return len(self.rounds)

    @property
    def is_my_turn(self) -> bool:
        """Check if it's this agent's turn to propose"""
        if not self.rounds:
            return True
        last_round = self.rounds[-1]
        return last_round.response == "counter"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NegotiationSession":
        context_data = data.get("context", {})
        if isinstance(context_data, str):
            import json
            context_data = json.loads(context_data)

        context = NegotiationContext(
            demand_id=context_data.get("demand_id"),
            service_id=context_data.get("service_id"),
            task_description=context_data.get("task_description", ""),
            initial_terms=NegotiationTerms.from_dict(context_data["initial_terms"]) if context_data.get("initial_terms") else None,
            constraints=context_data.get("constraints", {}),
        )

        rounds = []
        for r in data.get("rounds", []):
            rounds.append(NegotiationRound.from_dict(r))

        final_terms = None
        if data.get("final_terms"):
            final_terms = NegotiationTerms.from_dict(data["final_terms"])

        return cls(
            session_id=data.get("session_id", ""),
            initiator_id=data.get("initiator_id", ""),
            counterpart_id=data.get("counterpart_id", ""),
            context=context,
            status=data.get("status", "pending"),
            rounds=rounds,
            final_terms=final_terms,
            created_at=datetime.fromtimestamp(data["created_at"]) if isinstance(data.get("created_at"), (int, float)) else None,
            updated_at=datetime.fromtimestamp(data["updated_at"]) if isinstance(data.get("updated_at"), (int, float)) else None,
        )


@dataclass
class ProposalResult:
    """Result of a proposal submission"""
    success: bool
    session: Optional[NegotiationSession]
    message: str


class NegotiationManager:
    """
    Manages negotiation sessions.

    Features:
    - Initiate negotiations
    - Submit proposals
    - Accept/reject proposals
    - Track negotiation history
    """

    def __init__(
        self,
        platform_client: PlatformClient,
        agent_id: str,
        logger: Optional[logging.Logger] = None,
    ):
        self._platform = platform_client
        self.agent_id = agent_id
        self.logger = logger or logging.getLogger(__name__)

        # Active sessions cache
        self._sessions: Dict[str, NegotiationSession] = {}

    # ==================== Session Management ====================

    async def initiate(
        self,
        counterpart_id: str,
        context: NegotiationContext,
    ) -> Union[NegotiationSession, None]:
        """
        Initiate a negotiation with another agent.

        Args:
            counterpart_id: Target agent ID
            context: Negotiation context

        Returns:
            NegotiationSession or None on failure
        """
        response = await self._platform.initiate_negotiation(
            counterpart_id=counterpart_id,
            context=context.to_dict(),
        )

        if response.success and response.data:
            session = NegotiationSession.from_dict(response.data)
            self._sessions[session.session_id] = session
            self.logger.info(f"Negotiation initiated: {session.session_id} with {counterpart_id}")
            return session

        self.logger.error(f"Failed to initiate negotiation: {response.error}")
        return None

    async def get_session(self, session_id: str) -> Optional[NegotiationSession]:
        """Get a negotiation session by ID"""
        if session_id in self._sessions:
            return self._sessions[session_id]

        # Fetch from platform
        sessions = await self.list_active()
        for session in sessions:
            if session.session_id == session_id:
                self._sessions[session_id] = session
                return session

        return None

    async def list_active(self) -> List[NegotiationSession]:
        """List all active negotiations for this agent"""
        response = await self._platform.get_negotiations()

        if response.success and response.data:
            sessions = [NegotiationSession.from_dict(s) for s in response.data]
            # Update cache
            for session in sessions:
                self._sessions[session.session_id] = session
            return sessions

        return []

    # ==================== Proposals ====================

    async def propose(
        self,
        session_id: str,
        terms: NegotiationTerms,
    ) -> ProposalResult:
        """
        Submit a proposal in a negotiation.

        Args:
            session_id: Negotiation session ID
            terms: Proposed terms

        Returns:
            ProposalResult with updated session
        """
        response = await self._platform.submit_proposal(
            session_id=session_id,
            proposal=terms.to_dict(),
        )

        if response.success and response.data:
            session = NegotiationSession.from_dict(response.data)
            self._sessions[session_id] = session
            self.logger.info(f"Proposal submitted in session {session_id}")
            return ProposalResult(
                success=True,
                session=session,
                message="Proposal submitted",
            )

        return ProposalResult(
            success=False,
            session=None,
            message=response.error or "Failed to submit proposal",
        )

    async def counter_propose(
        self,
        session_id: str,
        terms: NegotiationTerms,
    ) -> ProposalResult:
        """
        Submit a counter-proposal.
        Same as propose() but semantically different.
        """
        return await self.propose(session_id, terms)

    async def accept(self, session_id: str) -> ProposalResult:
        """
        Accept the current proposal in a negotiation.

        Args:
            session_id: Negotiation session ID

        Returns:
            ProposalResult with accepted status
        """
        # Submit acceptance as a special proposal
        response = await self._platform.submit_proposal(
            session_id=session_id,
            proposal={"action": "accept"},
        )

        if response.success and response.data:
            session = NegotiationSession.from_dict(response.data)
            session.status = "accepted"
            self._sessions[session_id] = session
            self.logger.info(f"Negotiation accepted: {session_id}")
            return ProposalResult(
                success=True,
                session=session,
                message="Negotiation accepted",
            )

        return ProposalResult(
            success=False,
            session=None,
            message=response.error or "Failed to accept",
        )

    async def reject(
        self,
        session_id: str,
        reason: str = "",
    ) -> ProposalResult:
        """
        Reject the current proposal.

        Args:
            session_id: Negotiation session ID
            reason: Reason for rejection

        Returns:
            ProposalResult with rejected status
        """
        response = await self._platform.submit_proposal(
            session_id=session_id,
            proposal={"action": "reject", "reason": reason},
        )

        if response.success and response.data:
            session = NegotiationSession.from_dict(response.data)
            session.status = "rejected"
            self._sessions[session_id] = session
            self.logger.info(f"Negotiation rejected: {session_id}")
            return ProposalResult(
                success=True,
                session=session,
                message="Negotiation rejected",
            )

        return ProposalResult(
            success=False,
            session=None,
            message=response.error or "Failed to reject",
        )

    # ==================== History ====================

    async def get_history(self, session_id: str) -> List[NegotiationRound]:
        """Get negotiation history for a session"""
        session = await self.get_session(session_id)
        if session:
            return session.rounds
        return []

    # ==================== Suggestions ====================

    async def suggest_terms(
        self,
        session_id: str,
    ) -> Optional[NegotiationTerms]:
        """
        Get suggested terms based on negotiation context.
        Uses learning/optimization data if available.
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        # Analyze previous rounds
        if session.rounds:
            last_round = session.rounds[-1]
            counter_terms = last_round.terms

            # Simple suggestion: meet in the middle on price
            if session.context.initial_terms:
                initial_price = session.context.initial_terms.price
                counter_price = counter_terms.price
                suggested_price = (initial_price + counter_price) / 2

                return NegotiationTerms(
                    price=suggested_price,
                    delivery_time=counter_terms.delivery_time,
                    payment_terms=counter_terms.payment_terms,
                )

        # Return initial terms as suggestion
        return session.context.initial_terms

    async def evaluate_proposal(
        self,
        session_id: str,
        terms: NegotiationTerms,
    ) -> float:
        """
        Evaluate a proposal's favorability (0-1 score).

        Returns:
            Score from 0 (unfavorable) to 1 (very favorable)
        """
        session = await self.get_session(session_id)
        if not session:
            return 0.5

        score = 0.5

        # Check against constraints
        constraints = session.context.constraints
        if constraints:
            max_budget = constraints.get("max_budget", float("inf"))
            min_budget = constraints.get("min_budget", 0)

            if terms.price > max_budget:
                score -= 0.3
            elif terms.price < min_budget:
                score += 0.2
            else:
                # Price within range - score based on position
                range_size = max_budget - min_budget if max_budget > min_budget else 1
                position = (terms.price - min_budget) / range_size
                score += 0.2 * (1 - position)  # Lower is better

        return max(0, min(1, score))

    # ==================== Convenience Methods ====================

    async def negotiate(
        self,
        counterpart_id: str,
        task_description: str,
        initial_terms: NegotiationTerms,
        demand_id: Optional[str] = None,
        service_id: Optional[str] = None,
    ) -> Union[NegotiationSession, None]:
        """
        Convenience method to start a negotiation.

        Args:
            counterpart_id: Target agent
            task_description: What is being negotiated
            initial_terms: Initial proposal terms
            demand_id: Related demand ID
            service_id: Related service ID

        Returns:
            NegotiationSession or None
        """
        context = NegotiationContext(
            demand_id=demand_id,
            service_id=service_id,
            task_description=task_description,
            initial_terms=initial_terms,
            constraints={},
        )

        return await self.initiate(counterpart_id, context)
