"""
SQLite Storage Implementation

Provides SQLite-based persistent storage for structured data including:
- Agent registration information
- Session state management
- Transaction records
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    and_,
    delete,
    func,
    or_,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from usmsb_sdk.platform.external.storage.base_storage import (
    DataExistsError,
    DataLocation,
    DataNotFoundError,
    StorageError,
    StorageInterface,
    StorageResult,
    StorageType,
)

logger = logging.getLogger(__name__)


class StorageBase(DeclarativeBase):
    """Base class for storage models."""
    pass


class AgentRegistryModel(StorageBase):
    """Model for agent registration information."""
    __tablename__ = "agent_registry"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    protocol: Mapped[str] = mapped_column(String(50), default="a2a")
    endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(50), default="offline", index=True)
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "agent_type": self.agent_type,
            "protocol": self.protocol,
            "endpoint": self.endpoint,
            "capabilities": self.capabilities,
            "attributes": self.attributes,
            "status": self.status,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "metadata": self.extra_data,
        }


class SessionStateModel(StorageBase):
    """Model for session state management."""
    __tablename__ = "session_states"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(50), default="active", index=True)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    conversation_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    variables: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "state": self.state,
            "context": self.context,
            "conversation_history": self.conversation_history,
            "variables": self.variables,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.extra_data,
        }


class TransactionRecordModel(StorageBase):
    """Model for transaction records."""
    __tablename__ = "transaction_records"

    transaction_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    from_agent: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    to_agent: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    block_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "transaction_type": self.transaction_type,
            "resource_type": self.resource_type,
            "amount": self.amount,
            "unit": self.unit,
            "status": self.status,
            "payload": self.payload,
            "signature": self.signature,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "block_height": self.block_height,
            "metadata": self.extra_data,
        }


class KeyValueModel(StorageBase):
    """Generic key-value storage model."""
    __tablename__ = "key_value_store"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    namespace: Mapped[str] = mapped_column(String(100), default="default", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AgentRegistryManager:
    """Manager for agent registration operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(
        self,
        agent_id: str,
        name: str,
        agent_type: str,
        protocol: str = "a2a",
        endpoint: str | None = None,
        capabilities: dict | None = None,
        attributes: dict | None = None,
        metadata: dict | None = None,
    ) -> AgentRegistryModel:
        """Register a new agent."""
        agent = AgentRegistryModel(
            id=agent_id,
            name=name,
            agent_type=agent_type,
            protocol=protocol,
            endpoint=endpoint,
            capabilities=capabilities or {},
            attributes=attributes or {},
            metadata=metadata or {},
            status="online",
        )
        self.session.add(agent)
        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def get(self, agent_id: str) -> AgentRegistryModel | None:
        """Get agent by ID."""
        result = await self.session.execute(
            select(AgentRegistryModel).where(AgentRegistryModel.id == agent_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> AgentRegistryModel | None:
        """Get agent by name."""
        result = await self.session.execute(
            select(AgentRegistryModel).where(AgentRegistryModel.name == name)
        )
        return result.scalar_one_or_none()

    async def list_by_type(
        self,
        agent_type: str,
        status: str | None = None,
        limit: int = 100,
    ) -> list[AgentRegistryModel]:
        """List agents by type."""
        query = select(AgentRegistryModel).where(AgentRegistryModel.agent_type == agent_type)
        if status:
            query = query.where(AgentRegistryModel.status == status)
        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_status(
        self,
        status: str,
        limit: int = 100,
    ) -> list[AgentRegistryModel]:
        """List agents by status."""
        result = await self.session.execute(
            select(AgentRegistryModel)
            .where(AgentRegistryModel.status == status)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        agent_id: str,
        status: str,
    ) -> AgentRegistryModel | None:
        """Update agent status."""
        agent = await self.get(agent_id)
        if agent:
            agent.status = status
            agent.last_seen = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(agent)
        return agent

    async def update_heartbeat(self, agent_id: str) -> bool:
        """Update agent heartbeat."""
        result = await self.session.execute(
            update(AgentRegistryModel)
            .where(AgentRegistryModel.id == agent_id)
            .values(last_seen=datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount > 0

    async def search(
        self,
        query: str,
        limit: int = 100,
    ) -> list[AgentRegistryModel]:
        """Search agents by name or capabilities."""
        result = await self.session.execute(
            select(AgentRegistryModel)
            .where(AgentRegistryModel.name.ilike(f"%{query}%"))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete(self, agent_id: str) -> bool:
        """Delete agent registration."""
        result = await self.session.execute(
            delete(AgentRegistryModel).where(AgentRegistryModel.id == agent_id)
        )
        await self.session.commit()
        return result.rowcount > 0


class SessionStateManager:
    """Manager for session state operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        session_id: str,
        agent_id: str,
        context: dict | None = None,
        variables: dict | None = None,
        ttl_seconds: int | None = None,
        metadata: dict | None = None,
    ) -> SessionStateModel:
        """Create a new session."""
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

        session_state = SessionStateModel(
            session_id=session_id,
            agent_id=agent_id,
            context=context or {},
            variables=variables or {},
            expires_at=expires_at,
            metadata=metadata or {},
        )
        self.session.add(session_state)
        await self.session.commit()
        await self.session.refresh(session_state)
        return session_state

    async def get(self, session_id: str) -> SessionStateModel | None:
        """Get session by ID."""
        result = await self.session.execute(
            select(SessionStateModel).where(SessionStateModel.session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_by_agent(
        self,
        agent_id: str,
        state: str | None = None,
        limit: int = 100,
    ) -> list[SessionStateModel]:
        """Get sessions by agent."""
        query = select(SessionStateModel).where(SessionStateModel.agent_id == agent_id)
        if state:
            query = query.where(SessionStateModel.state == state)
        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_context(
        self,
        session_id: str,
        context: dict[str, Any],
        merge: bool = True,
    ) -> SessionStateModel | None:
        """Update session context."""
        session = await self.get(session_id)
        if session:
            if merge:
                session.context = {**session.context, **context}
            else:
                session.context = context
            session.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(session)
        return session

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict | None = None,
    ) -> SessionStateModel | None:
        """Add a message to conversation history."""
        session = await self.get(session_id)
        if session:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
            }
            session.conversation_history = session.conversation_history or []
            session.conversation_history.append(message)
            session.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(session)
        return session

    async def update_variables(
        self,
        session_id: str,
        variables: dict[str, Any],
        merge: bool = True,
    ) -> SessionStateModel | None:
        """Update session variables."""
        session = await self.get(session_id)
        if session:
            if merge:
                session.variables = {**session.variables, **variables}
            else:
                session.variables = variables
            session.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(session)
        return session

    async def set_state(
        self,
        session_id: str,
        state: str,
    ) -> SessionStateModel | None:
        """Set session state."""
        session = await self.get(session_id)
        if session:
            session.state = state
            session.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(session)
        return session

    async def delete(self, session_id: str) -> bool:
        """Delete session."""
        result = await self.session.execute(
            delete(SessionStateModel).where(SessionStateModel.session_id == session_id)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def cleanup_expired(self) -> int:
        """Clean up expired sessions."""
        result = await self.session.execute(
            delete(SessionStateModel).where(
                and_(
                    SessionStateModel.expires_at.isnot(None),
                    SessionStateModel.expires_at < datetime.utcnow(),
                )
            )
        )
        await self.session.commit()
        return result.rowcount


class TransactionRecordManager:
    """Manager for transaction record operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        transaction_id: str,
        from_agent: str,
        transaction_type: str,
        to_agent: str | None = None,
        resource_type: str | None = None,
        amount: float = 0.0,
        unit: str | None = None,
        payload: dict | None = None,
        signature: str | None = None,
        metadata: dict | None = None,
    ) -> TransactionRecordModel:
        """Create a new transaction record."""
        transaction = TransactionRecordModel(
            transaction_id=transaction_id,
            from_agent=from_agent,
            to_agent=to_agent,
            transaction_type=transaction_type,
            resource_type=resource_type,
            amount=amount,
            unit=unit,
            payload=payload or {},
            signature=signature,
            metadata=metadata or {},
            status="pending",
        )
        self.session.add(transaction)
        await self.session.commit()
        await self.session.refresh(transaction)
        return transaction

    async def get(self, transaction_id: str) -> TransactionRecordModel | None:
        """Get transaction by ID."""
        result = await self.session.execute(
            select(TransactionRecordModel).where(
                TransactionRecordModel.transaction_id == transaction_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_agent(
        self,
        agent_id: str,
        as_sender: bool = True,
        as_receiver: bool = True,
        status: str | None = None,
        limit: int = 100,
    ) -> list[TransactionRecordModel]:
        """Get transactions by agent."""
        conditions = []
        if as_sender and as_receiver:
            conditions.append(
                or_(
                    TransactionRecordModel.from_agent == agent_id,
                    TransactionRecordModel.to_agent == agent_id,
                )
            )
        elif as_sender:
            conditions.append(TransactionRecordModel.from_agent == agent_id)
        elif as_receiver:
            conditions.append(TransactionRecordModel.to_agent == agent_id)

        query = select(TransactionRecordModel).where(and_(*conditions))
        if status:
            query = query.where(TransactionRecordModel.status == status)
        query = query.order_by(TransactionRecordModel.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_status(
        self,
        transaction_id: str,
        status: str,
        block_height: int | None = None,
    ) -> TransactionRecordModel | None:
        """Update transaction status."""
        transaction = await self.get(transaction_id)
        if transaction:
            transaction.status = status
            if status == "completed":
                transaction.completed_at = datetime.utcnow()
            if block_height:
                transaction.block_height = block_height
            await self.session.commit()
            await self.session.refresh(transaction)
        return transaction

    async def get_pending(self, limit: int = 100) -> list[TransactionRecordModel]:
        """Get all pending transactions."""
        result = await self.session.execute(
            select(TransactionRecordModel)
            .where(TransactionRecordModel.status == "pending")
            .order_by(TransactionRecordModel.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_type(
        self,
        transaction_type: str,
        limit: int = 100,
    ) -> list[TransactionRecordModel]:
        """Get transactions by type."""
        result = await self.session.execute(
            select(TransactionRecordModel)
            .where(TransactionRecordModel.transaction_type == transaction_type)
            .order_by(TransactionRecordModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def calculate_balance(
        self,
        agent_id: str,
        resource_type: str,
    ) -> float:
        """Calculate agent balance for a resource type."""
        # Sum incoming
        incoming_result = await self.session.execute(
            select(func.sum(TransactionRecordModel.amount)).where(
                and_(
                    TransactionRecordModel.to_agent == agent_id,
                    TransactionRecordModel.resource_type == resource_type,
                    TransactionRecordModel.status == "completed",
                )
            )
        )
        incoming = incoming_result.scalar() or 0.0

        # Sum outgoing
        outgoing_result = await self.session.execute(
            select(func.sum(TransactionRecordModel.amount)).where(
                and_(
                    TransactionRecordModel.from_agent == agent_id,
                    TransactionRecordModel.resource_type == resource_type,
                    TransactionRecordModel.status == "completed",
                )
            )
        )
        outgoing = outgoing_result.scalar() or 0.0

        return incoming - outgoing

    async def delete(self, transaction_id: str) -> bool:
        """Delete transaction."""
        result = await self.session.execute(
            delete(TransactionRecordModel).where(
                TransactionRecordModel.transaction_id == transaction_id
            )
        )
        await self.session.commit()
        return result.rowcount > 0


class SQLiteStorage(StorageInterface[dict[str, Any]]):
    """
    SQLite-based storage implementation.

    Provides persistent storage for:
    - Agent registration information
    - Session state management
    - Transaction records
    - Generic key-value store
    """

    def __init__(
        self,
        database_path: str | Path,
        echo: bool = False,
    ):
        """
        Initialize SQLite storage.

        Args:
            database_path: Path to SQLite database file.
            echo: Whether to echo SQL statements.
        """
        self.database_path = Path(database_path)
        self.echo = echo
        self._engine = None
        self._session_factory = None
        self._connected = False

    async def initialize(self) -> bool:
        """Initialize the storage backend."""
        try:
            # Ensure directory exists
            self.database_path.parent.mkdir(parents=True, exist_ok=True)

            # Create async engine
            db_url = f"sqlite+aiosqlite:///{self.database_path}"
            self._engine = create_async_engine(db_url, echo=self.echo)

            # Create session factory
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Create tables
            async with self._engine.begin() as conn:
                await conn.run_sync(StorageBase.metadata.create_all)

            self._connected = True
            logger.info(f"SQLiteStorage initialized at {self.database_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize SQLiteStorage: {e}")
            return False

    async def close(self) -> None:
        """Close the storage backend."""
        if self._engine:
            await self._engine.dispose()
        self._connected = False
        logger.info("SQLiteStorage closed")

    @property
    def storage_type(self) -> StorageType:
        return StorageType.SQLITE

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _get_session(self) -> AsyncSession:
        """Get a new database session."""
        if not self._session_factory:
            raise StorageError("Storage not initialized")
        return self._session_factory()

    async def store(
        self,
        key: str,
        data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> StorageResult:
        """Store data in key-value store."""
        try:
            async with self._get_session() as session:
                # Check if exists
                result = await session.execute(
                    select(KeyValueModel).where(KeyValueModel.key == key)
                )
                existing = result.scalar_one_or_none()

                if existing and not overwrite:
                    raise DataExistsError(f"Key already exists: {key}")

                if existing:
                    existing.value = data
                    existing.updated_at = datetime.utcnow()
                    if metadata:
                        existing.extra_data = metadata
                else:
                    kv = KeyValueModel(
                        key=key,
                        value=data,
                        extra_data=metadata or {},
                    )
                    session.add(kv)

                await session.commit()

                location = DataLocation(
                    storage_type=StorageType.SQLITE,
                    key=key,
                    path=str(self.database_path),
                )

                return StorageResult(
                    success=True,
                    location=location,
                    metadata=metadata or {},
                )

        except DataExistsError as e:
            return StorageResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error storing data for key {key}: {e}")
            return StorageResult(success=False, error=str(e))

    async def retrieve(self, key: str) -> StorageResult:
        """Retrieve data from key-value store."""
        try:
            async with self._get_session() as session:
                result = await session.execute(
                    select(KeyValueModel).where(KeyValueModel.key == key)
                )
                kv = result.scalar_one_or_none()

                if not kv:
                    raise DataNotFoundError(f"Key not found: {key}")

                # Check expiration
                if kv.expires_at and kv.expires_at < datetime.utcnow():
                    await session.delete(kv)
                    await session.commit()
                    raise DataNotFoundError(f"Key expired: {key}")

                location = DataLocation(
                    storage_type=StorageType.SQLITE,
                    key=key,
                    path=str(self.database_path),
                )

                return StorageResult(
                    success=True,
                    data=kv.value,
                    location=location,
                    metadata=kv.extra_data,
                )

        except DataNotFoundError as e:
            return StorageResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error retrieving data for key {key}: {e}")
            return StorageResult(success=False, error=str(e))

    async def delete(self, key: str) -> StorageResult:
        """Delete data from key-value store."""
        try:
            async with self._get_session() as session:
                result = await session.execute(
                    delete(KeyValueModel).where(KeyValueModel.key == key)
                )
                await session.commit()

                if result.rowcount == 0:
                    raise DataNotFoundError(f"Key not found: {key}")

                return StorageResult(success=True)

        except DataNotFoundError as e:
            return StorageResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error deleting data for key {key}: {e}")
            return StorageResult(success=False, error=str(e))

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            async with self._get_session() as session:
                result = await session.execute(
                    select(KeyValueModel.key).where(KeyValueModel.key == key)
                )
                return result.scalar_one_or_none() is not None
        except Exception:
            return False

    async def list_keys(
        self,
        prefix: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[str]:
        """List keys in store."""
        try:
            async with self._get_session() as session:
                query = select(KeyValueModel.key)
                if prefix:
                    query = query.where(KeyValueModel.key.startswith(prefix))
                query = query.offset(offset).limit(limit)
                result = await session.execute(query)
                return [row[0] for row in result.all()]
        except Exception as e:
            logger.error(f"Error listing keys: {e}")
            return []

    async def get_metadata(self, key: str) -> dict[str, Any] | None:
        """Get metadata for a key."""
        try:
            async with self._get_session() as session:
                result = await session.execute(
                    select(KeyValueModel).where(KeyValueModel.key == key)
                )
                kv = result.scalar_one_or_none()
                return kv.extra_data if kv else None
        except Exception:
            return None

    async def update_metadata(
        self,
        key: str,
        metadata: dict[str, Any],
        merge: bool = True,
    ) -> StorageResult:
        """Update metadata for a key."""
        try:
            async with self._get_session() as session:
                result = await session.execute(
                    select(KeyValueModel).where(KeyValueModel.key == key)
                )
                kv = result.scalar_one_or_none()

                if not kv:
                    raise DataNotFoundError(f"Key not found: {key}")

                if merge:
                    kv.extra_data = {**kv.extra_data, **metadata}
                else:
                    kv.extra_data = metadata
                kv.updated_at = datetime.utcnow()

                await session.commit()
                return StorageResult(success=True, metadata=kv.extra_data)

        except DataNotFoundError as e:
            return StorageResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"Error updating metadata for key {key}: {e}")
            return StorageResult(success=False, error=str(e))

    # Specialized managers

    def get_agent_registry(self, session: AsyncSession) -> AgentRegistryManager:
        """Get agent registry manager for a session."""
        return AgentRegistryManager(session)

    def get_session_state_manager(self, session: AsyncSession) -> SessionStateManager:
        """Get session state manager for a session."""
        return SessionStateManager(session)

    def get_transaction_manager(self, session: AsyncSession) -> TransactionRecordManager:
        """Get transaction record manager for a session."""
        return TransactionRecordManager(session)

    async def get_session(self) -> AsyncSession:
        """Get a database session for use with managers."""
        return self._get_session()

    async def store_with_ttl(
        self,
        key: str,
        data: dict[str, Any],
        ttl_seconds: int,
        metadata: dict[str, Any] | None = None,
    ) -> StorageResult:
        """Store data with time-to-live."""
        try:
            async with self._get_session() as session:
                expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

                # Check if exists
                result = await session.execute(
                    select(KeyValueModel).where(KeyValueModel.key == key)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    existing.value = data
                    existing.expires_at = expires_at
                    existing.updated_at = datetime.utcnow()
                    if metadata:
                        existing.extra_data = metadata
                else:
                    kv = KeyValueModel(
                        key=key,
                        value=data,
                        expires_at=expires_at,
                        extra_data=metadata or {},
                    )
                    session.add(kv)

                await session.commit()

                location = DataLocation(
                    storage_type=StorageType.SQLITE,
                    key=key,
                    path=str(self.database_path),
                )

                return StorageResult(
                    success=True,
                    location=location,
                    metadata={"ttl_seconds": ttl_seconds, **(metadata or {})},
                )

        except Exception as e:
            logger.error(f"Error storing data with TTL for key {key}: {e}")
            return StorageResult(success=False, error=str(e))

    async def cleanup_expired(self) -> int:
        """Clean up expired entries."""
        try:
            async with self._get_session() as session:
                result = await session.execute(
                    delete(KeyValueModel).where(
                        and_(
                            KeyValueModel.expires_at.isnot(None),
                            KeyValueModel.expires_at < datetime.utcnow(),
                        )
                    )
                )
                await session.commit()
                return result.rowcount
        except Exception as e:
            logger.error(f"Error cleaning up expired entries: {e}")
            return 0

    async def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        try:
            async with self._get_session() as session:
                # Count key-value entries
                kv_count_result = await session.execute(
                    select(func.count()).select_from(KeyValueModel)
                )
                kv_count = kv_count_result.scalar() or 0

                # Count agents
                agent_count_result = await session.execute(
                    select(func.count()).select_from(AgentRegistryModel)
                )
                agent_count = agent_count_result.scalar() or 0

                # Count sessions
                session_count_result = await session.execute(
                    select(func.count()).select_from(SessionStateModel)
                )
                session_count = session_count_result.scalar() or 0

                # Count transactions
                tx_count_result = await session.execute(
                    select(func.count()).select_from(TransactionRecordModel)
                )
                tx_count = tx_count_result.scalar() or 0

                return {
                    "storage_type": self.storage_type.value,
                    "connected": self.is_connected,
                    "database_path": str(self.database_path),
                    "key_value_count": kv_count,
                    "agent_count": agent_count,
                    "session_count": session_count,
                    "transaction_count": tx_count,
                }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                "storage_type": self.storage_type.value,
                "connected": self.is_connected,
                "error": str(e),
            }
