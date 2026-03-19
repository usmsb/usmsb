"""
Value Negotiation Service

Phase 2 of USMSB Agent Platform implementation.

Provides negotiation capabilities for Value Contracts:
- Start negotiation sessions
- Submit counter-proposals
- AI-to-AI auto-negotiation (LLM driven)
- Agree on terms and finalize contract

Negotiation flow:
1. Start session with initial contract proposal
2. Exchange counter-proposals (optional)
3. AI-to-AI auto-negotiate variable terms (optional)
4. Agree and finalize
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from usmsb_sdk.services.schema import NegotiationSessionDB
from usmsb_sdk.services.value_contract.models import TaskValueContract
from usmsb_sdk.services.value_contract.service import ValueContractService
from usmsb_sdk.services.value_contract.templates import ContractTemplate, get_template

logger = logging.getLogger(__name__)


@dataclass
class NegotiationRound:
    """A single round of negotiation."""
    round: int
    proposer_id: str
    proposed_changes: dict[str, Any]  # {term: new_value}
    status: str = "pending"  # pending | accepted | rejected
    responded_at: float = 0.0


@dataclass
class ValueNegotiationSession:
    """
    Represents a negotiation session between agents.

    A session is created when:
    - A demand agent wants to negotiate contract terms with a supply agent
    - Agents want to adjust variable terms of a template

    The session tracks all rounds of negotiation until agreement or cancellation.
    """
    session_id: str = ""
    contract_id: str | None = None  # Contract being negotiated (if exists)
    participants: list[str] = field(default_factory=list)

    # Current negotiation state
    negotiation_rounds: list[NegotiationRound] = field(default_factory=list)

    # Template being used
    template_id: str = "simple_task"
    template: ContractTemplate | None = None

    # Status: active | agreed | failed | cancelled | expired
    status: str = "active"

    # Timestamps
    started_at: float = 0.0
    expires_at: float = 0.0
    agreed_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "contract_id": self.contract_id,
            "participants": self.participants,
            "negotiation_rounds": [
                {
                    "round": r.round,
                    "proposer_id": r.proposer_id,
                    "proposed_changes": r.proposed_changes,
                    "status": r.status,
                    "responded_at": r.responded_at,
                }
                for r in self.negotiation_rounds
            ],
            "template_id": self.template_id,
            "status": self.status,
            "started_at": self.started_at,
            "expires_at": self.expires_at,
            "agreed_at": self.agreed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValueNegotiationSession":
        session = cls(
            session_id=data.get("session_id", ""),
            contract_id=data.get("contract_id"),
            participants=data.get("participants", []),
            template_id=data.get("template_id", "simple_task"),
            status=data.get("status", "active"),
            started_at=data.get("started_at", 0.0),
            expires_at=data.get("expires_at", 0.0),
            agreed_at=data.get("agreed_at", 0.0),
        )

        for r in data.get("negotiation_rounds", []):
            session.negotiation_rounds.append(
                NegotiationRound(
                    round=r["round"],
                    proposer_id=r["proposer_id"],
                    proposed_changes=r["proposed_changes"],
                    status=r.get("status", "pending"),
                    responded_at=r.get("responded_at", 0.0),
                )
            )

        return session


class ValueNegotiationService:
    """
    Service for negotiating Value Contracts.

    Handles negotiation sessions, counter-proposals, and auto-negotiation.
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.contract_service = ValueContractService(db_session)

    async def start_negotiation(
        self,
        demand_agent_id: str,
        supply_agent_id: str,
        initial_terms: dict[str, Any] | None = None,
        template_id: str = "simple_task",
        contract_id: str | None = None,
        timeout_seconds: int = 300,
    ) -> ValueNegotiationSession:
        """
        Start a new negotiation session.

        Args:
            demand_agent_id: Agent requesting the task
            supply_agent_id: Agent who will perform the task
            initial_terms: Initial proposed terms {price_vibe: 5.0, deadline: 86400, ...}
            template_id: Template to use for negotiation
            contract_id: Existing contract ID to negotiate (optional)
            timeout_seconds: Session timeout (default 5 minutes)

        Returns:
            New NegotiationSession
        """
        session_id = f"neg-{uuid.uuid4().hex[:12]}"
        now = time.time()

        template = get_template(template_id)
        if not template:
            template = get_template("simple_task")

        session = ValueNegotiationSession(
            session_id=session_id,
            contract_id=contract_id,
            participants=[demand_agent_id, supply_agent_id],
            template_id=template_id,
            template=template,
            negotiation_rounds=[],
            status="active",
            started_at=now,
            expires_at=now + timeout_seconds,
        )

        # If initial terms provided, create first round
        if initial_terms:
            session.negotiation_rounds.append(
                NegotiationRound(
                    round=1,
                    proposer_id=demand_agent_id,
                    proposed_changes=initial_terms,
                    status="pending",
                )
            )

        # Persist to DB
        await self._save_session(session)

        logger.info(f"Started negotiation session {session_id}: {demand_agent_id} <-> {supply_agent_id}")
        return session

    async def submit_counter_proposal(
        self,
        session_id: str,
        agent_id: str,
        counter_changes: dict[str, Any],
    ) -> ValueNegotiationSession:
        """
        Submit a counter-proposal to an active negotiation.

        Args:
            session_id: Negotiation session ID
            agent_id: Agent submitting counter-proposal
            counter_changes: Terms to change {price_vibe: 4.5, deadline: 172800, ...}

        Returns:
            Updated NegotiationSession
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Negotiation session {session_id} not found")

        if session.status != "active":
            raise ValueError(f"Session {session_id} is not active (status: {session.status})")

        if agent_id not in session.participants:
            raise ValueError(f"Agent {agent_id} is not a participant")

        # Check if last round was by this agent (can't propose twice in a row)
        if session.negotiation_rounds:
            last_round = session.negotiation_rounds[-1]
            if last_round.proposer_id == agent_id and last_round.status == "pending":
                raise ValueError("Cannot propose twice in a row, wait for response")

        # Add new round
        new_round = NegotiationRound(
            round=len(session.negotiation_rounds) + 1,
            proposer_id=agent_id,
            proposed_changes=counter_changes,
            status="pending",
        )
        session.negotiation_rounds.append(new_round)

        # Mark previous round as responded
        if len(session.negotiation_rounds) > 1:
            session.negotiation_rounds[-2].status = "responded"
            session.negotiation_rounds[-2].responded_at = time.time()

        session.expires_at = time.time() + 300  # Reset timeout
        await self._save_session(session)

        logger.info(f"Counter-proposal in session {session_id} by {agent_id}: {counter_changes}")
        return session

    async def agree_on_terms(
        self,
        session_id: str,
        agent_id: str,
    ) -> tuple[ValueNegotiationSession, dict[str, Any]]:
        """
        Agree on terms and finalize negotiation.

        Args:
            session_id: Negotiation session ID
            agent_id: Agent agreeing to terms

        Returns:
            Tuple of (NegotiationSession, agreed_terms_dict)
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Negotiation session {session_id} not found")

        if session.status != "active":
            raise ValueError(f"Session {session_id} is not active")

        if agent_id not in session.participants:
            raise ValueError(f"Agent {agent_id} is not a participant")

        # Mark last round as accepted
        if session.negotiation_rounds:
            session.negotiation_rounds[-1].status = "accepted"
            session.negotiation_rounds[-1].responded_at = time.time()

        session.status = "agreed"
        session.agreed_at = time.time()

        # Extract agreed terms from rounds
        agreed_terms = await self._extract_agreed_terms(session)

        await self._save_session(session)

        logger.info(f"Negotiation {session_id} agreed by {agent_id}: {agreed_terms}")
        return session, agreed_terms

    async def cancel_negotiation(
        self,
        session_id: str,
        agent_id: str,
        reason: str = "",
    ) -> None:
        """Cancel a negotiation session."""
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Negotiation session {session_id} not found")

        if session.status != "active":
            raise ValueError(f"Session {session_id} is not active")

        if agent_id not in session.participants:
            raise ValueError(f"Agent {agent_id} is not a participant")

        session.status = "cancelled"
        await self._save_session(session)

        logger.info(f"Negotiation {session_id} cancelled by {agent_id}: {reason}")

    async def auto_negotiate(
        self,
        session_id: str,
        agent_a_soul: dict[str, Any],
        agent_b_soul: dict[str, Any],
    ) -> tuple[ValueNegotiationSession, dict[str, Any]]:
        """
        AI-to-AI auto-negotiation using LLM.

        This method uses the agents' Soul profiles to drive automatic
        negotiation of variable terms within template ranges.

        Args:
            session_id: Negotiation session ID
            agent_a_soul: Soul profile of first agent
            agent_b_soul: Soul profile of second agent

        Returns:
            Tuple of (NegotiationSession, agreed_terms_dict)
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Negotiation session {session_id} not found")

        if session.status != "active":
            raise ValueError(f"Session {session_id} is not active")

        if not session.template:
            session.template = get_template(session.template_id)

        # Extract current terms from negotiation history
        current_terms = await self._extract_current_terms(session)
        template = session.template

        # Determine acceptable ranges based on agent souls
        # This is a simplified version - real implementation would use LLM

        # Agent A preferences (demand side)
        a_risk_tolerance = agent_a_soul.get("declared", {}).get("risk_tolerance", 0.5)
        a_preferred_price = agent_a_soul.get("declared", {}).get("base_price_vibe")

        # Agent B preferences (supply side)
        b_risk_tolerance = agent_b_soul.get("declared", {}).get("risk_tolerance", 0.5)
        b_preferred_price = agent_b_soul.get("declared", {}).get("base_price_vibe")

        # Simple midpoint negotiation on price
        agreed_terms = current_terms.copy()
        ranges = template.get_variable_ranges()

        if "price_vibe" in ranges and a_preferred_price and b_preferred_price:
            # Midpoint between preferred prices
            midpoint = (a_preferred_price + b_preferred_price) / 2
            # Clamp to template range
            price_range = ranges["price_vibe"]
            min_price = price_range.get("min", 0.01)
            max_price = price_range.get("max", 10000)
            agreed_price = max(min_price, min(max_price, midpoint))
            agreed_terms["price_vibe"] = round(agreed_price, 2)

        if "deadline" in ranges:
            # Prefer shorter deadline for demand, longer for supply
            deadline_range = ranges["deadline"]
            # Use midpoint as starting point
            min_dl = deadline_range.get("min", 3600)
            max_dl = deadline_range.get("max", 604800)
            agreed_terms["deadline"] = (min_dl + max_dl) // 2

        # Add final round
        proposer = session.participants[0]
        session.negotiation_rounds.append(
            NegotiationRound(
                round=len(session.negotiation_rounds) + 1,
                proposer_id="AUTO",
                proposed_changes=agreed_terms,
                status="accepted",
                responded_at=time.time(),
            )
        )

        session.status = "agreed"
        session.agreed_at = time.time()

        await self._save_session(session)

        logger.info(f"Auto-negotiation for session {session_id} completed: {agreed_terms}")
        return session, agreed_terms

    async def get_session(self, session_id: str) -> ValueNegotiationSession | None:
        """Get a negotiation session by ID."""
        db_record = self.db.query(NegotiationSessionDB).filter(
            NegotiationSessionDB.session_id == session_id
        ).first()

        if not db_record:
            return None

        return ValueNegotiationSession.from_dict({
            "session_id": db_record.session_id,
            "contract_id": db_record.contract_id,
            "participants": db_record.participants or [],
            "negotiation_rounds": db_record.negotiation_rounds or [],
            "template_id": "simple_task",
            "status": db_record.status,
            "started_at": float(db_record.started_at.timestamp()) if db_record.started_at else 0.0,
            "expires_at": float(db_record.expires_at.timestamp()) if db_record.expires_at else 0.0,
        })

    async def get_active_sessions_for_agent(self, agent_id: str) -> list[ValueNegotiationSession]:
        """Get all active negotiation sessions for an agent."""
        db_records = self.db.query(NegotiationSessionDB).filter(
            NegotiationSessionDB.status == "active"
        ).all()

        sessions = []
        for record in db_records:
            participants = record.participants or []
            if agent_id in participants:
                session = await self.get_session(record.session_id)
                if session:
                    sessions.append(session)

        return sessions

    # ============== Helpers ==============

    async def _save_session(self, session: ValueNegotiationSession) -> None:
        """Save negotiation session to database."""
        existing = self.db.query(NegotiationSessionDB).filter(
            NegotiationSessionDB.session_id == session.session_id
        ).first()

        if existing:
            existing.status = session.status
            existing.negotiation_rounds = session.to_dict().get("negotiation_rounds", [])
        else:
            db_record = NegotiationSessionDB(
                session_id=session.session_id,
                contract_id=session.contract_id,
                participants=session.participants,
                negotiation_rounds=session.to_dict().get("negotiation_rounds", []),
                status=session.status,
                started_at=session.started_at,
                expires_at=session.expires_at,
            )
            self.db.add(db_record)

        self.db.commit()

    async def _extract_agreed_terms(self, session: ValueNegotiationSession) -> dict[str, Any]:
        """Extract the final agreed terms from negotiation rounds."""
        if not session.negotiation_rounds:
            return {}

        # Start with template defaults
        template = session.template or get_template(session.template_id)
        agreed = template.default_terms.copy() if template else {}

        # Apply changes from each accepted round
        for round in session.negotiation_rounds:
            if round.status in ("accepted", "responded"):
                agreed.update(round.proposed_changes)

        return agreed

    async def _extract_current_terms(self, session: ValueNegotiationSession) -> dict[str, Any]:
        """Extract the current terms from negotiation history."""
        if not session.negotiation_rounds:
            template = session.template or get_template(session.template_id)
            return template.default_terms.copy() if template else {}

        return session.negotiation_rounds[-1].proposed_changes.copy()
