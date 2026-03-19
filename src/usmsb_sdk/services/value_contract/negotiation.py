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
        AI-to-AI auto-negotiation using Soul-driven strategy.

        D2 Fix: Replaced stub with Soul-driven multi-strategy negotiation.
        Uses agent Soul profiles to drive intelligent negotiation,
        not just naive midpoint calculation.

        Strategy selection based on Soul compatibility:
        - Aggressive + Aggressive → Competitive
        - Conservative + Conservative → Cooperative
        - Aggressive + Conservative → Mixed (aggressive wins more)
        - Balanced + Balanced → Fair split
        - High risk variance → Creative (explore alternatives)

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

        current_terms = await self._extract_current_terms(session)
        template = session.template
        ranges = template.get_variable_ranges()

        # Extract Soul profile preferences
        a_declared = agent_a_soul.get("declared", {})
        b_declared = agent_b_soul.get("declared", {})

        a_style = a_declared.get("collaboration_style", "balanced")
        b_style = b_declared.get("collaboration_style", "balanced")
        a_risk = a_declared.get("risk_tolerance", 0.5)
        b_risk = b_declared.get("risk_tolerance", 0.5)
        a_preferred_price = a_declared.get("base_price_vibe")
        b_preferred_price = b_declared.get("base_price_vibe")

        # Determine negotiation strategy based on Soul compatibility
        strategy = self._determine_negotiation_strategy(a_style, b_style, a_risk, b_risk)

        logger.info(
            f"Auto-negotiate {session_id}: strategy={strategy}, "
            f"a_style={a_style}, b_style={b_style}"
        )

        # Calculate agreed terms using strategy
        agreed_terms = self._apply_negotiation_strategy(
            strategy=strategy,
            current_terms=current_terms,
            ranges=ranges,
            a_preferred_price=a_preferred_price,
            b_preferred_price=b_preferred_price,
            a_risk=a_risk,
            b_risk=b_risk,
            a_style=a_style,
            b_style=b_style,
            template=template,
        )

        # Add final round with AUTO proposer
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

    def _determine_negotiation_strategy(
        self,
        a_style: str,
        b_style: str,
        a_risk: float,
        b_risk: float,
    ) -> str:
        """
        Determine negotiation strategy based on Soul profiles.

        D2 Fix: Multi-strategy negotiation based on Soul compatibility.
        """
        if a_style == "aggressive" and b_style == "aggressive":
            return "competitive"
        elif a_style == "conservative" and b_style == "conservative":
            return "cooperative"
        elif a_style in ("aggressive", "conservative") or b_style in ("aggressive", "conservative"):
            return "mixed"
        elif abs(a_risk - b_risk) > 0.4:
            return "creative"
        else:
            return "fair_split"

    def _apply_negotiation_strategy(
        self,
        strategy: str,
        current_terms: dict,
        ranges: dict,
        a_preferred_price: float | None,
        b_preferred_price: float | None,
        a_risk: float,
        b_risk: float,
        a_style: str,
        b_style: str,
        template,
    ) -> dict[str, Any]:
        """
        Apply negotiation strategy to determine agreed terms.

        D2 Fix: Strategy-aware negotiation, not just midpoint.
        """
        agreed = current_terms.copy()

        # Cooperative: both conservative → slow, safe adjustments
        if strategy == "cooperative":
            if "price_vibe" in ranges and a_preferred_price and b_preferred_price:
                midpoint = (a_preferred_price + b_preferred_price) / 2
                current = current_terms.get("price_vibe", midpoint)
                agreed["price_vibe"] = round(current + (midpoint - current) * 0.3, 2)
            if "deadline" in ranges:
                dl_range = ranges["deadline"]
                agreed["deadline"] = int(dl_range.get("max", 604800) * 0.8)

        # Competitive: both aggressive → push toward own preferred
        elif strategy == "competitive":
            if "price_vibe" in ranges and a_preferred_price and b_preferred_price:
                midpoint = (a_preferred_price + b_preferred_price) / 2
                agreed["price_vibe"] = round(midpoint, 2)
            if "deadline" in ranges:
                dl_range = ranges["deadline"]
                agreed["deadline"] = int(dl_range.get("min", 3600) * 1.5)

        # Mixed: one aggressive, one conservative
        elif strategy == "mixed":
            if "price_vibe" in ranges and a_preferred_price and b_preferred_price:
                if a_style == "aggressive":
                    agreed["price_vibe"] = round(a_preferred_price * 0.6 + b_preferred_price * 0.4, 2)
                else:
                    agreed["price_vibe"] = round(a_preferred_price * 0.4 + b_preferred_price * 0.6, 2)
            if "deadline" in ranges:
                dl_range = ranges["deadline"]
                agreed["deadline"] = int((dl_range.get("min", 3600) + dl_range.get("max", 604800)) / 2)

        # Creative: high risk variance → explore alternatives
        elif strategy == "creative":
            if "price_vibe" in ranges and a_preferred_price and b_preferred_price:
                midpoint = (a_preferred_price + b_preferred_price) / 2
                agreed["price_vibe"] = round(midpoint, 2)
            if "payment_schedule" in ranges:
                agreed["payment_schedule"] = "milestone_based"

        # Fair split: balanced → straightforward middle ground
        else:
            if "price_vibe" in ranges and a_preferred_price and b_preferred_price:
                midpoint = (a_preferred_price + b_preferred_price) / 2
                price_range = ranges["price_vibe"]
                min_p = price_range.get("min", 0.01)
                max_p = price_range.get("max", 10000)
                agreed["price_vibe"] = round(max(min_p, min(max_p, midpoint)), 2)
            if "deadline" in ranges:
                dl_range = ranges["deadline"]
                agreed["deadline"] = int((dl_range.get("min", 3600) + dl_range.get("max", 604800)) / 2)

        # Clamp all terms to template ranges
        for term_name, term_range in ranges.items():
            if term_name in agreed:
                min_val = term_range.get("min", 0)
                max_val = term_range.get("max", float("inf"))
                agreed[term_name] = max(min_val, min(max_val, agreed[term_name]))

        return agreed

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
