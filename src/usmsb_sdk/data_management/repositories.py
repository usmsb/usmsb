"""
Repository Pattern Implementation

Generic repository pattern for data access abstraction.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from usmsb_sdk.data_management.models import (
    AgentModel,
    Base,
    EnvironmentModel,
    EventLogModel,
    GoalModel,
    InformationModel,
    MetricsModel,
    ResourceModel,
    RiskModel,
    SimulationResultModel,
    WorkflowModel,
)

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=Base)


class IRepository(ABC, Generic[ModelType]):
    """Abstract base repository interface."""

    @abstractmethod
    async def get_by_id(self, id: str) -> ModelType | None:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Get all entities with pagination."""
        pass

    @abstractmethod
    async def create(self, entity: ModelType) -> ModelType:
        """Create a new entity."""
        pass

    @abstractmethod
    async def update(self, entity: ModelType) -> ModelType:
        """Update an existing entity."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete an entity by ID."""
        pass


class BaseRepository(IRepository[ModelType]):
    """Base repository implementation with common operations."""

    def __init__(self, session: AsyncSession, model: type[ModelType]):
        """
        Initialize the repository.

        Args:
            session: Database session
            model: SQLAlchemy model class
        """
        self.session = session
        self.model = model

    async def get_by_id(self, id: str) -> ModelType | None:
        """Get entity by ID."""
        try:
            result = await self.session.execute(
                select(self.model).where(self.model.id == id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by id: {e}")
            return None

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Get all entities with pagination."""
        try:
            result = await self.session.execute(
                select(self.model).offset(skip).limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting all {self.model.__name__}: {e}")
            return []

    async def create(self, entity: ModelType) -> ModelType:
        """Create a new entity."""
        try:
            self.session.add(entity)
            await self.session.commit()
            await self.session.refresh(entity)
            return entity
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise

    async def update(self, entity: ModelType) -> ModelType:
        """Update an existing entity."""
        try:
            await self.session.commit()
            await self.session.refresh(entity)
            return entity
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating {self.model.__name__}: {e}")
            raise

    async def delete(self, id: str) -> bool:
        """Delete an entity by ID."""
        try:
            entity = await self.get_by_id(id)
            if entity:
                await self.session.delete(entity)
                await self.session.commit()
                return True
            return False
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting {self.model.__name__}: {e}")
            return False

    async def exists(self, id: str) -> bool:
        """Check if entity exists."""
        entity = await self.get_by_id(id)
        return entity is not None

    async def count(self) -> int:
        """Count all entities."""
        from sqlalchemy import func
        try:
            result = await self.session.execute(
                select(func.count()).select_from(self.model)
            )
            return result.scalar() or 0
        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            return 0

    async def find_by(
        self,
        filters: dict[str, Any],
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Find entities by filter criteria."""
        try:
            query = select(self.model)
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)
            query = query.offset(skip).limit(limit)
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error finding {self.model.__name__}: {e}")
            return []

    async def find_one_by(self, filters: dict[str, Any]) -> ModelType | None:
        """Find one entity by filter criteria."""
        results = await self.find_by(filters, limit=1)
        return results[0] if results else None


class AgentRepository(BaseRepository[AgentModel]):
    """Repository for Agent entities."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, AgentModel)

    async def get_by_name(self, name: str) -> AgentModel | None:
        """Get agent by name."""
        return await self.find_one_by({"name": name})

    async def get_by_type(self, agent_type: str, skip: int = 0, limit: int = 100) -> list[AgentModel]:
        """Get agents by type."""
        return await self.find_by({"type": agent_type}, skip, limit)

    async def get_by_state(self, state: str, skip: int = 0, limit: int = 100) -> list[AgentModel]:
        """Get agents by state."""
        return await self.find_by({"state": state}, skip, limit)

    async def get_with_goals(self, agent_id: str) -> AgentModel | None:
        """Get agent with goals loaded."""
        from sqlalchemy.orm import selectinload
        try:
            result = await self.session.execute(
                select(AgentModel)
                .options(selectinload(AgentModel.goals))
                .where(AgentModel.id == agent_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting agent with goals: {e}")
            return None

    async def get_with_resources(self, agent_id: str) -> AgentModel | None:
        """Get agent with resources loaded."""
        from sqlalchemy.orm import selectinload
        try:
            result = await self.session.execute(
                select(AgentModel)
                .options(selectinload(AgentModel.resources))
                .where(AgentModel.id == agent_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting agent with resources: {e}")
            return None

    async def search(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AgentModel]:
        """Search agents by name or attributes."""
        try:
            result = await self.session.execute(
                select(AgentModel)
                .where(AgentModel.name.ilike(f"%{query}%"))
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error searching agents: {e}")
            return []


class GoalRepository(BaseRepository[GoalModel]):
    """Repository for Goal entities."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, GoalModel)

    async def get_by_agent(self, agent_id: str, skip: int = 0, limit: int = 100) -> list[GoalModel]:
        """Get goals by agent."""
        return await self.find_by({"agent_id": agent_id}, skip, limit)

    async def get_active_goals(self, agent_id: str) -> list[GoalModel]:
        """Get active goals for an agent."""
        try:
            result = await self.session.execute(
                select(GoalModel)
                .where(GoalModel.agent_id == agent_id)
                .where(GoalModel.status == "active")
                .order_by(GoalModel.priority.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting active goals: {e}")
            return []

    async def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> list[GoalModel]:
        """Get goals by status."""
        return await self.find_by({"status": status}, skip, limit)

    async def update_progress(self, goal_id: str, progress: float) -> GoalModel | None:
        """Update goal progress."""
        try:
            goal = await self.get_by_id(goal_id)
            if goal:
                goal.progress = progress
                return await self.update(goal)
            return None
        except Exception as e:
            logger.error(f"Error updating goal progress: {e}")
            return None


class ResourceRepository(BaseRepository[ResourceModel]):
    """Repository for Resource entities."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, ResourceModel)

    async def get_by_name(self, name: str) -> ResourceModel | None:
        """Get resource by name."""
        return await self.find_one_by({"name": name})

    async def get_by_type(self, resource_type: str, skip: int = 0, limit: int = 100) -> list[ResourceModel]:
        """Get resources by type."""
        return await self.find_by({"type": resource_type}, skip, limit)

    async def get_by_environment(self, environment_id: str, skip: int = 0, limit: int = 100) -> list[ResourceModel]:
        """Get resources by environment."""
        return await self.find_by({"environment_id": environment_id}, skip, limit)

    async def update_quantity(self, resource_id: str, quantity: float) -> ResourceModel | None:
        """Update resource quantity."""
        try:
            resource = await self.get_by_id(resource_id)
            if resource:
                resource.quantity = quantity
                return await self.update(resource)
            return None
        except Exception as e:
            logger.error(f"Error updating resource quantity: {e}")
            return None


class RiskRepository(BaseRepository[RiskModel]):
    """Repository for Risk entities."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, RiskModel)

    async def get_by_agent(self, agent_id: str, skip: int = 0, limit: int = 100) -> list[RiskModel]:
        """Get risks by agent."""
        return await self.find_by({"agent_id": agent_id}, skip, limit)

    async def get_by_level(self, risk_level: str, skip: int = 0, limit: int = 100) -> list[RiskModel]:
        """Get risks by level."""
        return await self.find_by({"risk_level": risk_level}, skip, limit)

    async def get_high_risks(self, skip: int = 0, limit: int = 100) -> list[RiskModel]:
        """Get high and critical risks."""
        try:
            result = await self.session.execute(
                select(RiskModel)
                .where(RiskModel.risk_level.in_(["high", "critical"]))
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting high risks: {e}")
            return []


class EnvironmentRepository(BaseRepository[EnvironmentModel]):
    """Repository for Environment entities."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, EnvironmentModel)

    async def get_by_name(self, name: str) -> EnvironmentModel | None:
        """Get environment by name."""
        return await self.find_one_by({"name": name})

    async def get_by_type(self, env_type: str, skip: int = 0, limit: int = 100) -> list[EnvironmentModel]:
        """Get environments by type."""
        return await self.find_by({"type": env_type}, skip, limit)


class WorkflowRepository(BaseRepository[WorkflowModel]):
    """Repository for Workflow entities."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, WorkflowModel)

    async def get_by_agent(self, agent_id: str, skip: int = 0, limit: int = 100) -> list[WorkflowModel]:
        """Get workflows by agent."""
        return await self.find_by({"agent_id": agent_id}, skip, limit)

    async def get_by_status(self, status: str, skip: int = 0, limit: int = 100) -> list[WorkflowModel]:
        """Get workflows by status."""
        return await self.find_by({"status": status}, skip, limit)

    async def get_pending_workflows(self, skip: int = 0, limit: int = 100) -> list[WorkflowModel]:
        """Get pending workflows."""
        return await self.get_by_status("pending", skip, limit)


class SimulationResultRepository(BaseRepository[SimulationResultModel]):
    """Repository for Simulation Results."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, SimulationResultModel)

    async def get_by_simulation_id(self, simulation_id: str) -> SimulationResultModel | None:
        """Get result by simulation ID."""
        return await self.find_one_by({"simulation_id": simulation_id})


class EventLogRepository(BaseRepository[EventLogModel]):
    """Repository for Event Logs."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, EventLogModel)

    async def get_by_type(
        self,
        event_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EventLogModel]:
        """Get events by type."""
        return await self.find_by({"event_type": event_type}, skip, limit)

    async def get_by_agent(
        self,
        agent_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EventLogModel]:
        """Get events by agent."""
        return await self.find_by({"agent_id": agent_id}, skip, limit)

    async def get_recent(
        self,
        minutes: int = 60,
        skip: int = 0,
        limit: int = 100,
    ) -> list[EventLogModel]:
        """Get recent events."""
        from datetime import datetime, timedelta
        try:
            since = datetime.utcnow() - timedelta(minutes=minutes)
            result = await self.session.execute(
                select(EventLogModel)
                .where(EventLogModel.timestamp >= since)
                .order_by(EventLogModel.timestamp.desc())
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting recent events: {e}")
            return []


class MetricsRepository(BaseRepository[MetricsModel]):
    """Repository for Metrics."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, MetricsModel)

    async def get_by_name(
        self,
        metric_name: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[MetricsModel]:
        """Get metrics by name."""
        return await self.find_by({"metric_name": metric_name}, skip, limit)

    async def get_latest(
        self,
        metric_name: str,
        agent_id: str | None = None,
    ) -> MetricsModel | None:
        """Get latest metric value."""
        try:
            query = select(MetricsModel).where(MetricsModel.metric_name == metric_name)
            if agent_id:
                query = query.where(MetricsModel.agent_id == agent_id)
            query = query.order_by(MetricsModel.timestamp.desc()).limit(1)
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting latest metric: {e}")
            return None

    async def get_time_series(
        self,
        metric_name: str,
        start_time,
        end_time,
        agent_id: str | None = None,
    ) -> list[MetricsModel]:
        """Get metrics as time series."""
        try:
            query = select(MetricsModel).where(
                and_(
                    MetricsModel.metric_name == metric_name,
                    MetricsModel.timestamp >= start_time,
                    MetricsModel.timestamp <= end_time,
                )
            )
            if agent_id:
                query = query.where(MetricsModel.agent_id == agent_id)
            query = query.order_by(MetricsModel.timestamp.asc())
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting time series: {e}")
            return []


class InformationRepository(BaseRepository[InformationModel]):
    """Repository for Information entities."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, InformationModel)

    async def search(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[InformationModel]:
        """Search information by title or content."""
        try:
            result = await self.session.execute(
                select(InformationModel)
                .where(
                    or_(
                        InformationModel.title.ilike(f"%{query}%"),
                        InformationModel.content.ilike(f"%{query}%"),
                    )
                )
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error searching information: {e}")
            return []

    async def get_by_tags(
        self,
        tags: list[str],
        skip: int = 0,
        limit: int = 100,
    ) -> list[InformationModel]:
        """Get information by tags."""
        # This is a simplified implementation
        # For production, use JSON array containment or a proper tag table
        try:
            result = await self.session.execute(
                select(InformationModel)
                .offset(skip)
                .limit(limit)
            )
            all_info = list(result.scalars().all())
            # Filter by tags in Python
            return [
                info for info in all_info
                if any(tag in (info.tags or []) for tag in tags)
            ]
        except Exception as e:
            logger.error(f"Error getting info by tags: {e}")
            return []


class RepositoryFactory:
    """Factory for creating repositories."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the factory.

        Args:
            session: Database session
        """
        self.session = session

    @property
    def agents(self) -> AgentRepository:
        """Get agent repository."""
        return AgentRepository(self.session)

    @property
    def goals(self) -> GoalRepository:
        """Get goal repository."""
        return GoalRepository(self.session)

    @property
    def resources(self) -> ResourceRepository:
        """Get resource repository."""
        return ResourceRepository(self.session)

    @property
    def risks(self) -> RiskRepository:
        """Get risk repository."""
        return RiskRepository(self.session)

    @property
    def environments(self) -> EnvironmentRepository:
        """Get environment repository."""
        return EnvironmentRepository(self.session)

    @property
    def workflows(self) -> WorkflowRepository:
        """Get workflow repository."""
        return WorkflowRepository(self.session)

    @property
    def simulation_results(self) -> SimulationResultRepository:
        """Get simulation result repository."""
        return SimulationResultRepository(self.session)

    @property
    def event_logs(self) -> EventLogRepository:
        """Get event log repository."""
        return EventLogRepository(self.session)

    @property
    def metrics(self) -> MetricsRepository:
        """Get metrics repository."""
        return MetricsRepository(self.session)

    @property
    def information(self) -> InformationRepository:
        """Get information repository."""
        return InformationRepository(self.session)
