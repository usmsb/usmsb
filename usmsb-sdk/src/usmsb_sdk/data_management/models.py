"""
Data Management Models

SQLAlchemy models for persistent storage of USMSB SDK entities.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class AgentModel(Base):
    """SQLAlchemy model for Agent entity."""
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # AgentType enum value
    state: Mapped[str] = mapped_column(String(50), default="idle")  # AgentState enum value
    capabilities: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    goals: Mapped[List["GoalModel"]] = relationship("GoalModel", back_populates="agent", cascade="all, delete-orphan")
    resources: Mapped[List["AgentResourceModel"]] = relationship("AgentResourceModel", back_populates="agent", cascade="all, delete-orphan")
    rules: Mapped[List["AgentRuleModel"]] = relationship("AgentRuleModel", back_populates="agent", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<AgentModel(id={self.id}, name={self.name}, type={self.type})>"


class GoalModel(Base):
    """SQLAlchemy model for Goal entity."""
    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    priority: Mapped[float] = mapped_column(Float, default=0.5)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # GoalStatus enum value
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    target_metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    parent_goal_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("goals.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    agent: Mapped["AgentModel"] = relationship("AgentModel", back_populates="goals")
    sub_goals: Mapped[List["GoalModel"]] = relationship("GoalModel", remote_side=[id], backref="parent_goal")

    def __repr__(self) -> str:
        return f"<GoalModel(id={self.id}, name={self.name}, status={self.status})>"


class ResourceModel(Base):
    """SQLAlchemy model for Resource entity (global resources)."""
    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # ResourceType enum value
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    max_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    environment_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("environments.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<ResourceModel(id={self.id}, name={self.name}, quantity={self.quantity})>"


class AgentResourceModel(Base):
    """SQLAlchemy model for Agent's resources."""
    __tablename__ = "agent_resources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    max_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    agent: Mapped["AgentModel"] = relationship("AgentModel", back_populates="resources")

    def __repr__(self) -> str:
        return f"<AgentResourceModel(id={self.id}, name={self.name}, quantity={self.quantity})>"


class RuleModel(Base):
    """SQLAlchemy model for Rule entity (global rules)."""
    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    rule_type: Mapped[str] = mapped_column(String(50), default="constraint")  # constraint, permission, obligation
    conditions: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    actions: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    priority: Mapped[float] = mapped_column(Float, default=0.5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    environment_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("environments.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<RuleModel(id={self.id}, name={self.name}, type={self.rule_type})>"


class AgentRuleModel(Base):
    """SQLAlchemy model for Agent's rules."""
    __tablename__ = "agent_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    rule_type: Mapped[str] = mapped_column(String(50), default="constraint")
    conditions: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    actions: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    priority: Mapped[float] = mapped_column(Float, default=0.5)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    agent: Mapped["AgentModel"] = relationship("AgentModel", back_populates="rules")

    def __repr__(self) -> str:
        return f"<AgentRuleModel(id={self.id}, name={self.name})>"


class RiskModel(Base):
    """SQLAlchemy model for Risk entity."""
    __tablename__ = "risks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    probability: Mapped[float] = mapped_column(Float, default=0.5)
    impact: Mapped[float] = mapped_column(Float, default=0.5)
    risk_level: Mapped[str] = mapped_column(String(50), default="medium")  # low, medium, high, critical
    mitigation_strategy: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="identified")  # identified, mitigating, resolved, accepted
    agent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True)
    environment_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("environments.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<RiskModel(id={self.id}, name={self.name}, risk_level={self.risk_level})>"


class InformationModel(Base):
    """SQLAlchemy model for Information entity."""
    __tablename__ = "information"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    info_type: Mapped[str] = mapped_column(String(50), default="general")  # fact, opinion, instruction, etc.
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    credibility: Mapped[float] = mapped_column(Float, default=0.5)
    relevance: Mapped[float] = mapped_column(Float, default=0.5)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    agent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<InformationModel(id={self.id}, title={self.title})>"


class EnvironmentModel(Base):
    """SQLAlchemy model for Environment entity."""
    __tablename__ = "environments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="general")  # EnvironmentType enum value
    state: Mapped[str] = mapped_column(String(50), default="active")  # EnvironmentState enum value
    constraints: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    attributes: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    parent_environment_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("environments.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    resources: Mapped[List["ResourceModel"]] = relationship("ResourceModel", back_populates="environment")
    rules: Mapped[List["RuleModel"]] = relationship("RuleModel", back_populates="environment")
    risks: Mapped[List["RiskModel"]] = relationship("RiskModel", back_populates="environment")

    def __repr__(self) -> str:
        return f"<EnvironmentModel(id={self.id}, name={self.name}, type={self.type})>"


class WorkflowModel(Base):
    """SQLAlchemy model for Workflow entity."""
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # WorkflowStatus enum value
    steps: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<WorkflowModel(id={self.id}, name={self.name}, status={self.status})>"


class SimulationResultModel(Base):
    """SQLAlchemy model for Simulation Results."""
    __tablename__ = "simulation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    simulation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    final_state: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    agent_stats: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    resource_stats: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    emergent_patterns: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    steps_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<SimulationResultModel(id={self.id}, simulation_id={self.simulation_id})>"


class EventLogModel(Base):
    """SQLAlchemy model for Event Logs."""
    __tablename__ = "event_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(255), nullable=False)
    target: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    agent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True)
    environment_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("environments.id"), nullable=True)

    def __repr__(self) -> str:
        return f"<EventLogModel(id={self.id}, type={self.event_type})>"


class MetricsModel(Base):
    """SQLAlchemy model for Metrics."""
    __tablename__ = "metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    metric_name: Mapped[str] = mapped_column(String(255), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tags: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)
    agent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True)
    environment_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("environments.id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<MetricsModel(id={self.id}, name={self.metric_name}, value={self.metric_value})>"


# Database initialization functions
async def init_db(database_url: str = "sqlite+aiosqlite:///./usmsb.db") -> None:
    """Initialize the database and create tables."""
    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session(database_url: str = "sqlite+aiosqlite:///./usmsb.db") -> AsyncSession:
    """Get a database session."""
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
