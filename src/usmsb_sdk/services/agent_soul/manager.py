"""
Agent Soul Manager

Manages the lifecycle of Agent Souls in the USMSB Platform.

Key responsibilities:
- Register new Agent Souls
- Update Declared Souls (with optimistic locking)
- Update Inferred Souls from behavior events (Feedback Loop)
- Query compatible agents (simple filtering, not matching)
- Export Soul data (for Agent exit/portability)
- Delete Soul (Agent exit from platform)

This is Phase 1 of the USMSB Agent Platform implementation.
"""

import logging
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from usmsb_sdk.core.elements import Goal, Resource, Risk, Value
from usmsb_sdk.services.agent_soul.models import AgentSoul, DeclaredSoul, InferredSoul
from usmsb_sdk.services.schema import (
    AgentSoulDB,
    FeedbackEventDB,
    ReputationSnapshotDB,
)

logger = logging.getLogger(__name__)


class AgentSoulManager:
    """
    Manages Agent Soul lifecycle.

    This is the central service for all Soul-related operations in the platform.
    It maintains Soul data in SQLite and provides CRUD operations.
    """

    def __init__(self, db_session: Session):
        """
        Initialize AgentSoulManager.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    # ============== Registration ==============

    # Valid values for enum-like fields
    VALID_COLLABORATION_STYLES = {"conservative", "balanced", "aggressive"}
    VALID_CONTRACT_TYPES = {"task", "project", "any"}
    VALID_PRICING_STRATEGIES = {"fixed", "negotiable", "market"}

    def _validate_declared_soul(self, declared: DeclaredSoul) -> None:
        """
        Validate DeclaredSoul fields.

        L2 Fix: Added basic validation to prevent malicious or invalid declarations.

        Raises:
            ValueError: If any field is invalid
        """
        # Validate risk_tolerance
        if not isinstance(declared.risk_tolerance, (int, float)):
            raise ValueError(f"risk_tolerance must be a number, got {type(declared.risk_tolerance)}")
        if not 0.0 <= declared.risk_tolerance <= 1.0:
            raise ValueError(f"risk_tolerance must be between 0.0 and 1.0, got {declared.risk_tolerance}")

        # Validate collaboration_style
        if declared.collaboration_style not in self.VALID_COLLABORATION_STYLES:
            raise ValueError(
                f"collaboration_style must be one of {self.VALID_COLLABORATION_STYLES}, "
                f"got {declared.collaboration_style}"
            )

        # Validate preferred_contract_type
        if declared.preferred_contract_type not in self.VALID_CONTRACT_TYPES:
            raise ValueError(
                f"preferred_contract_type must be one of {self.VALID_CONTRACT_TYPES}, "
                f"got {declared.preferred_contract_type}"
            )

        # Validate pricing_strategy
        if declared.pricing_strategy not in self.VALID_PRICING_STRATEGIES:
            raise ValueError(
                f"pricing_strategy must be one of {self.VALID_PRICING_STRATEGIES}, "
                f"got {declared.pricing_strategy}"
            )

        # Validate capabilities is a list of strings
        if not isinstance(declared.capabilities, list):
            raise ValueError(f"capabilities must be a list, got {type(declared.capabilities)}")
        for cap in declared.capabilities:
            if not isinstance(cap, str):
                raise ValueError(f"capabilities must contain strings, got {type(cap)}")

        # Validate base_price_vibe if provided
        if declared.base_price_vibe is not None:
            if not isinstance(declared.base_price_vibe, (int, float)):
                raise ValueError(f"base_price_vibe must be a number or None, got {type(declared.base_price_vibe)}")
            if declared.base_price_vibe < 0:
                raise ValueError(f"base_price_vibe must be non-negative, got {declared.base_price_vibe}")

    async def register_soul(
        self,
        agent_id: str,
        declared: DeclaredSoul,
    ) -> AgentSoul:
        """
        Register a new Agent Soul.

        This is called when an Agent first joins the platform.
        The Agent must declare its Soul as part of registration.

        Args:
            agent_id: Unique identifier for the Agent
            declared: The Agent's self-declared Soul profile

        Returns:
            The created AgentSoul

        Raises:
            ValueError: If Agent already has a Soul registered or if validation fails
        """
        # L2 Fix: Validate declared soul before registration
        self._validate_declared_soul(declared)

        # Check if Soul already exists
        existing = self.db.query(AgentSoulDB).filter(
            AgentSoulDB.agent_id == agent_id
        ).first()
        if existing:
            raise ValueError(f"Agent {agent_id} already has a Soul registered")

        now = time.time()

        # Create AgentSoul
        soul = AgentSoul(
            agent_id=agent_id,
            declared=declared,
            inferred=InferredSoul(),
            environment_state={},
            match_history=[],
            negotiation_history=[],
            soul_version=1,
            soul_declared_at=now,
            soul_updated_at=now,
            created_at=now,
            updated_at=now,
        )

        # Persist to DB
        db_record = AgentSoulDB(
            agent_id=agent_id,
            declared_soul=declared.to_dict(),
            inferred_soul=None,
            environment_state={},
            soul_version=1,
            soul_declared_at=now,
            soul_updated_at=now,
            match_history=[],
            negotiation_history=[],
            created_at=now,
            updated_at=now,
        )
        self.db.add(db_record)
        self.db.commit()

        logger.info(f"Registered Soul for Agent {agent_id}")
        return soul

    # ============== Read ==============

    async def get_soul(self, agent_id: str) -> AgentSoul | None:
        """
        Get Agent Soul by agent_id.

        Args:
            agent_id: Agent's unique identifier

        Returns:
            AgentSoul if found, None otherwise
        """
        db_record = self.db.query(AgentSoulDB).filter(
            AgentSoulDB.agent_id == agent_id
        ).first()

        if not db_record:
            return None

        return self._db_to_soul(db_record)

    async def soul_exists(self, agent_id: str) -> bool:
        """Check if an Agent has a Soul registered."""
        return self.db.query(AgentSoulDB).filter(
            AgentSoulDB.agent_id == agent_id
        ).count() > 0

    # ============== Update Declared ==============

    async def update_declared(
        self,
        agent_id: str,
        declared: DeclaredSoul,
        expected_version: int | None = None,
    ) -> AgentSoul:
        """
        Update an Agent's Declared Soul.

        This is called when an Agent wants to update its self-declared profile.

        Args:
            agent_id: Agent's unique identifier
            declared: The new DeclaredSoul
            expected_version: If provided, used for optimistic locking
                           (update fails if current version != expected)

        Returns:
            The updated AgentSoul

        Raises:
            ValueError: If Soul not found or version mismatch
        """
        db_record = self.db.query(AgentSoulDB).filter(
            AgentSoulDB.agent_id == agent_id
        ).first()

        if not db_record:
            raise ValueError(f"Agent {agent_id} has no Soul registered")

        # Optimistic locking check
        if expected_version is not None and db_record.soul_version != expected_version:
            raise ValueError(
                f"Version conflict: expected {expected_version}, "
                f"current {db_record.soul_version}"
            )

        now = time.time()

        # Update
        db_record.declared_soul = declared.to_dict()
        db_record.soul_version += 1
        db_record.soul_updated_at = now
        db_record.updated_at = now

        self.db.commit()

        logger.info(f"Updated DeclaredSoul for Agent {agent_id}, version {db_record.soul_version}")
        return self._db_to_soul(db_record)

    # ============== Update Inferred (from Behavior) ==============

    async def update_inferred_from_event(
        self,
        agent_id: str,
        behavior_event: dict[str, Any],
    ) -> AgentSoul:
        """
        Update an Agent's Inferred Soul from a behavior event.

        This is called by the Feedback Loop when a contract completes.

        Args:
            agent_id: Agent's unique identifier
            behavior_event: Event data from contract completion
                {
                    "contract_id": str,
                    "success": bool,
                    "response_time_minutes": float,
                    "quality_score": float,
                    "value_match_score": float,
                    "timestamp": float,
                    ...
                }

        Returns:
            The updated AgentSoul
        """
        db_record = self.db.query(AgentSoulDB).filter(
            AgentSoulDB.agent_id == agent_id
        ).first()

        if not db_record:
            raise ValueError(f"Agent {agent_id} has no Soul registered")

        # Load current InferredSoul
        current_inferred = InferredSoul.from_dict(db_record.inferred_soul)
        if current_inferred is None:
            current_inferred = InferredSoul()

        # Create full soul object for update_from_behavior
        soul = self._db_to_soul(db_record)

        # Apply behavior event
        soul.update_from_behavior(behavior_event)

        # Persist
        db_record.inferred_soul = soul.inferred.to_dict()
        db_record.soul_version += 1
        db_record.soul_updated_at = soul.soul_updated_at
        db_record.updated_at = time.time()

        # Append to match history
        history = db_record.match_history or []
        history.append({
            "contract_id": behavior_event.get("contract_id"),
            "outcome": {
                "success": behavior_event.get("success"),
                "quality_score": behavior_event.get("quality_score"),
                "value_match_score": behavior_event.get("value_match_score"),
            },
            "timestamp": behavior_event.get("timestamp", time.time()),
        })
        # Keep last 100 entries
        if len(history) > 100:
            history = history[-100:]
        db_record.match_history = history

        self.db.commit()

        logger.info(f"Updated InferredSoul for Agent {agent_id} from event {behavior_event.get('contract_id')}")
        return self._db_to_soul(db_record)

    # ============== Compatibility Query ==============

    async def get_compatible_agents(
        self,
        agent_id: str,
        filter_criteria: dict[str, Any] | None = None,
    ) -> list[AgentSoul]:
        """
        Get agents compatible with a given agent.

        This is a simple filtering query, NOT a full USMSB matching.
        It filters by declared capabilities and other declared attributes.

        Full USMSB matching (Goal+Capability+Value) is handled by USMSBMatchingEngine.

        Args:
            agent_id: The agent to find matches for
            filter_criteria: Optional filters
                {
                    "capabilities": ["coding", "writing"],  # AND match
                    "min_reputation": 0.5,
                    "collaboration_style": "aggressive",
                    ...
                }

        Returns:
            List of compatible AgentSouls (excluding the query agent)
        """
        query = self.db.query(AgentSoulDB).filter(
            AgentSoulDB.agent_id != agent_id
        )

        results = query.all()

        souls = [self._db_to_soul(r) for r in results]

        # Apply in-memory filters (for flexibility)
        if filter_criteria:
            filtered = []
            for soul in souls:
                if self._matches_filter(soul, filter_criteria):
                    filtered.append(soul)
            souls = filtered

        return souls

    def _matches_filter(self, soul: AgentSoul, criteria: dict[str, Any]) -> bool:
        """Check if a soul matches filter criteria."""
        declared = soul.declared

        # Capabilities filter (AND match - must have all)
        if "capabilities" in criteria:
            required = set(criteria["capabilities"])
            actual = set(declared.capabilities)
            if not required.issubset(actual):
                return False

        # Collaboration style filter
        if "collaboration_style" in criteria:
            if declared.collaboration_style != criteria["collaboration_style"]:
                return False

        # Contract type filter
        if "preferred_contract_type" in criteria:
            pct = criteria["preferred_contract_type"]
            if pct != "any" and declared.preferred_contract_type != pct and declared.preferred_contract_type != "any":
                return False

        # Risk tolerance filter
        if "min_risk_tolerance" in criteria:
            if declared.risk_tolerance < criteria["min_risk_tolerance"]:
                return False

        # Inferred reputation filter
        if "min_reputation" in criteria and soul.inferred:
            if soul.inferred.actual_success_rate < criteria["min_reputation"]:
                return False

        return True

    # ============== Negotiation History ==============

    async def add_negotiation_result(
        self,
        agent_id: str,
        negotiation_result: dict[str, Any],
    ) -> None:
        """
        Add a negotiation result to Agent's negotiation history.

        Args:
            agent_id: Agent's unique identifier
            negotiation_result: {
                "session_id": str,
                "result": "success" | "failed" | "cancelled",
                "counterparty_id": str,
                "timestamp": float,
                ...
            }
        """
        db_record = self.db.query(AgentSoulDB).filter(
            AgentSoulDB.agent_id == agent_id
        ).first()

        if not db_record:
            raise ValueError(f"Agent {agent_id} has no Soul registered")

        history = db_record.negotiation_history or []
        history.append(negotiation_result)
        # Keep last 50 entries
        if len(history) > 50:
            history = history[-50:]
        db_record.negotiation_history = history
        db_record.updated_at = time.time()

        self.db.commit()

    # ============== Reputation ==============

    async def get_reputation(self, agent_id: str) -> float:
        """
        Get Agent's reputation score (0.0 ~ 1.0).

        Based on InferredSoul success_rate and value_alignment_score.
        """
        soul = await self.get_soul(agent_id)
        if not soul or not soul.inferred:
            return 0.5  # Default neutral

        inferred = soul.inferred
        # Weighted average: 70% success rate, 30% value alignment
        return 0.7 * inferred.actual_success_rate + 0.3 * inferred.value_alignment_score

    # ============== Export (Portability) ==============

    async def export_soul(self, agent_id: str) -> dict[str, Any]:
        """
        Export complete Soul data for portability.

        This is used when an Agent exits the platform.
        The exported JSON contains all Soul data for migration to another platform.

        Based on OpenClaw negotiation: Agent data sovereignty.

        Args:
            agent_id: Agent's unique identifier

        Returns:
            Full Soul data as dictionary
        """
        soul = await self.get_soul(agent_id)
        if not soul:
            raise ValueError(f"Agent {agent_id} has no Soul registered")

        return soul.to_dict()

    # ============== Delete (Exit) ==============

    async def delete_soul(self, agent_id: str) -> bool:
        """
        Delete an Agent's Soul (exit platform).

        This performs a soft delete - data is retained for audit purposes
        but the Agent is marked as inactive.

        Args:
            agent_id: Agent's unique identifier

        Returns:
            True if deleted, False if not found
        """
        db_record = self.db.query(AgentSoulDB).filter(
            AgentSoulDB.agent_id == agent_id
        ).first()

        if not db_record:
            return False

        # Soft delete: mark environment_state as deleted
        db_record.environment_state = db_record.environment_state or {}
        db_record.environment_state["status"] = "deleted"
        db_record.environment_state["deleted_at"] = time.time()
        db_record.updated_at = time.time()

        self.db.commit()

        logger.info(f"Deleted Soul for Agent {agent_id}")
        return True

    # ============== Environment State ==============

    async def update_environment_state(
        self,
        agent_id: str,
        state_updates: dict[str, Any],
    ) -> AgentSoul:
        """
        Update Agent's environment state.

        This is used to track current situational context like
        busy_level, current_load, online_status, etc.

        Args:
            agent_id: Agent's unique identifier
            state_updates: Key-value pairs to update

        Returns:
            Updated AgentSoul
        """
        db_record = self.db.query(AgentSoulDB).filter(
            AgentSoulDB.agent_id == agent_id
        ).first()

        if not db_record:
            raise ValueError(f"Agent {agent_id} has no Soul registered")

        env_state = db_record.environment_state or {}
        env_state.update(state_updates)
        db_record.environment_state = env_state
        db_record.updated_at = time.time()

        self.db.commit()

        return self._db_to_soul(db_record)

    # ============== Helpers ==============

    def _db_to_soul(self, db_record: AgentSoulDB) -> AgentSoul:
        """Convert database record to AgentSoul object."""
        declared_dict = db_record.declared_soul
        declared = DeclaredSoul.from_dict(declared_dict) if declared_dict else DeclaredSoul()

        inferred_dict = db_record.inferred_soul
        inferred = InferredSoul.from_dict(inferred_dict) if inferred_dict else InferredSoul()

        return AgentSoul(
            agent_id=db_record.agent_id,
            declared=declared,
            inferred=inferred,
            environment_state=db_record.environment_state or {},
            match_history=db_record.match_history or [],
            negotiation_history=db_record.negotiation_history or [],
            soul_version=db_record.soul_version,
            soul_declared_at=db_record.soul_declared_at,
            soul_updated_at=db_record.soul_updated_at,
            created_at=float(db_record.created_at.timestamp()) if db_record.created_at else 0.0,
            updated_at=float(db_record.updated_at.timestamp()) if db_record.updated_at else 0.0,
        )
