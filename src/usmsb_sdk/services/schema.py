"""
USMSB Agent Platform Database Schema

Defines SQLite database tables for:
- Agent Souls
- Value Contracts
- Contract Value Flows
- Contract Risks

Uses SQLAlchemy ORM models.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

Base = declarative_base()

# Database path (configurable via environment)
DEFAULT_DB_PATH = "sqlite:///./usmsb_platform.db"


# ============== Agent Soul Tables ==============


class AgentSoulDB(Base):
    """Agent Soul database model."""

    __tablename__ = "agent_souls"

    agent_id = Column(String(64), primary_key=True)
    declared_soul = Column(JSON, nullable=False)  # DeclaredSoul JSON
    inferred_soul = Column(JSON, nullable=True)  # InferredSoul JSON
    environment_state = Column(JSON, nullable=True)  # Environment state JSON
    soul_version = Column(Integer, default=1)

    # Match history for learning
    match_history = Column(JSON, nullable=True)  # [{contract_id, outcome, timestamp}]

    # Negotiation history
    negotiation_history = Column(JSON, nullable=True)  # [{session_id, result, timestamp}]

    # Timestamps
    soul_declared_at = Column(Float, nullable=True)
    soul_updated_at = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============== Value Contract Tables ==============


class ValueContractDB(Base):
    """Value Contract database model."""

    __tablename__ = "value_contracts"

    contract_id = Column(String(64), primary_key=True)
    contract_type = Column(String(16), nullable=False)  # "task" | "project"

    # Parties involved (Agent IDs)
    parties = Column(JSON, nullable=False)  # [agent_id, ...]

    # USMSB transformation path description
    transformation_path = Column(Text, nullable=True)

    # Status: draft | proposed | accepted | active | completed | disputed | cancelled
    status = Column(String(32), default="draft")

    # Contract data (Task or Project specific)
    contract_data = Column(JSON, nullable=True)

    # Version for optimistic locking
    version = Column(Integer, default=1)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Soft delete
    is_cancelled = Column(Boolean, default=False)


class ContractValueFlowDB(Base):
    """Contract Value Flow database model."""

    __tablename__ = "contract_value_flows"

    flow_id = Column(String(64), primary_key=True)
    contract_id = Column(
        String(64), ForeignKey("value_contracts.contract_id"), nullable=False
    )

    from_agent_id = Column(String(64), nullable=False)
    to_agent_id = Column(String(64), nullable=False)

    # USMSB Resource definition
    resource_definition = Column(JSON, nullable=True)
    # USMSB Value definition
    value_definition = Column(JSON, nullable=True)

    # Trigger: on_delivery | on_completion | on_milestone
    trigger = Column(String(32), default="on_delivery")

    # Status: pending | executed | failed
    flow_status = Column(String(16), default="pending")

    executed_at = Column(DateTime, nullable=True)


class ContractRiskDB(Base):
    """Contract Risk database model."""

    __tablename__ = "contract_risks"

    risk_id = Column(String(64), primary_key=True)
    contract_id = Column(
        String(64), ForeignKey("value_contracts.contract_id"), nullable=False
    )

    # USMSB Risk type
    risk_type = Column(String(32), nullable=False)

    # Probability and impact (0.0 ~ 1.0)
    probability = Column(Float, default=0.0)
    impact = Column(Float, default=0.0)

    # Mitigation strategy
    mitigation = Column(Text, nullable=True)
    fallback_action = Column(Text, nullable=True)


class ContractMilestoneDB(Base):
    """Contract Milestone database model."""

    __tablename__ = "contract_milestones"

    milestone_id = Column(String(64), primary_key=True)
    contract_id = Column(
        String(64), ForeignKey("value_contracts.contract_id"), nullable=False
    )

    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)

    # Payment percentage at this milestone (0.0 ~ 1.0)
    payment_percentage = Column(Float, default=0.0)

    # Status: pending | completed | failed
    status = Column(String(16), default="pending")

    # Criteria for completion
    criteria = Column(JSON, nullable=True)

    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============== Negotiation Tables ==============


class NegotiationSessionDB(Base):
    """Negotiation Session database model."""

    __tablename__ = "negotiation_sessions"

    session_id = Column(String(64), primary_key=True)
    contract_id = Column(
        String(64), ForeignKey("value_contracts.contract_id"), nullable=True
    )

    # Participants (Agent IDs)
    participants = Column(JSON, nullable=False)

    # Current negotiation rounds
    negotiation_rounds = Column(JSON, nullable=True)  # [{round, proposer, changes, status}]

    # Status: active | agreed | failed | cancelled | expired
    status = Column(String(32), default="active")

    started_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


# ============== Reputation & Feedback Tables ==============


class ReputationSnapshotDB(Base):
    """Reputation snapshot for audit trail."""

    __tablename__ = "reputation_snapshots"

    snapshot_id = Column(String(64), primary_key=True)
    agent_id = Column(String(64), nullable=False, index=True)

    # Reputation score components
    success_rate = Column(Float, default=0.0)
    response_time_score = Column(Float, default=0.0)
    value_alignment_score = Column(Float, default=0.5)
    collaboration_count = Column(Integer, default=0)

    # Overall score (weighted)
    overall_score = Column(Float, default=0.5)

    # Source: "inferred_from_behavior" | "manual_adjustment"
    source = Column(String(32), default="inferred_from_behavior")

    created_at = Column(DateTime, default=datetime.utcnow)


class FeedbackEventDB(Base):
    """Feedback event for Feedback Loop processing."""

    __tablename__ = "feedback_events"

    event_id = Column(String(64), primary_key=True)
    contract_id = Column(String(64), nullable=False, index=True)

    # Agent IDs involved
    demand_agent_id = Column(String(64), nullable=False)
    supply_agent_id = Column(String(64), nullable=False)

    # Event type
    event_type = Column(String(32), nullable=False)  # completion | delivery_confirmed | dispute

    # Event data
    event_data = Column(JSON, nullable=True)

    # Processing status: pending | processed | failed
    process_status = Column(String(16), default="pending")

    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============== Emergence Broadcast Tables ==============


class BroadcastDB(Base):
    """
    Agent broadcast for decentralized opportunity discovery.

    D4 Fix: Persist broadcasts to DB so they survive restarts.
    """

    __tablename__ = "broadcasts"

    broadcast_id = Column(String(64), primary_key=True)
    agent_id = Column(String(64), nullable=False, index=True)

    # Broadcast type: seeking | offering
    broadcast_type = Column(String(16), nullable=False)

    # Content: {goal, capability, requirements}
    content = Column(JSON, nullable=False)

    # Response count
    response_count = Column(Integer, default=0)

    # Status: active | expired | fulfilled
    status = Column(String(16), default="active")

    # Timestamps
    timestamp = Column(Float, nullable=False)
    expires_at = Column(Float, nullable=False)
    fulfilled_at = Column(Float, nullable=True)


class BroadcastResponseDB(Base):
    """Response to a broadcast."""

    __tablename__ = "broadcast_responses"

    response_id = Column(String(64), primary_key=True)
    broadcast_id = Column(
        String(64), ForeignKey("broadcasts.broadcast_id"), nullable=False, index=True
    )
    responding_agent_id = Column(String(64), nullable=False)

    # Match score and proposed terms
    match_score = Column(Float, default=0.0)
    proposed_terms = Column(JSON, nullable=True)

    # Agent soul snapshot at time of response
    agent_soul_snapshot = Column(JSON, nullable=True)

    timestamp = Column(Float, nullable=False)


# ============== Database Utilities ==============


def create_db(db_url: str | None = None) -> "Engine":
    """Create database engine and tables."""
    db_path = db_url or DEFAULT_DB_PATH
    engine = create_engine(db_path, echo=False)
    Base.metadata.create_all(engine)
    return engine


def create_session(db_url: str | None = None) -> Session:
    """Create a new database session."""
    engine = create_db(db_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


# ============== Migration Utilities ==============


def get_table_names(engine) -> list[str]:
    """Get all table names in the database."""
    from sqlalchemy import inspect

    inspector = inspect(engine)
    return inspector.get_table_names()


def table_exists(engine, table_name: str) -> bool:
    """Check if a table exists."""
    return table_name in get_table_names(engine)
