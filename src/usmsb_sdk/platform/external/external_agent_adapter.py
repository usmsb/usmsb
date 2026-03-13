"""
External Agent Adapter

This module provides unified integration for external AI Agents:
- Support for multiple protocols (A2A, MCP, P2P, HTTP, WebSocket, gRPC)
- Skill discovery and capability matching
- Communication protocol abstraction
- External agent lifecycle management
- Storage layer integration for persistence
- Authentication and session management
- Node-based agent synchronization

Supported Protocols:
1. A2A (Agent-to-Agent): Direct agent communication protocol
2. MCP (Model Context Protocol): Standard AI service protocol
3. P2P: Peer-to-peer decentralized communication
4. HTTP/REST: Standard web API integration
5. WebSocket: Real-time bidirectional communication
6. gRPC: High-performance RPC protocol

New Features (v2.0):
- Protocol handlers from protocol/ module with factory pattern
- Storage layer support for persistent agent registration
- Authentication via wallet and stake verification
- Node synchronization for distributed agent discovery
"""

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union, TypeVar, Generic, TYPE_CHECKING

# Lazy import protocol handlers to avoid circular dependency
# Protocol imports are done via get_protocol_module() when needed
_protocol_module = None

def _get_protocol_module():
    """Lazy load protocol module to avoid circular imports."""
    global _protocol_module
    if _protocol_module is None:
        from usmsb_sdk.platform.external import protocol
        _protocol_module = protocol
    return _protocol_module

# Import ProtocolConfig from base_handler (safe - no circular import)
from usmsb_sdk.platform.external.protocol.base_handler import ProtocolConfig

# Import node management modules
from usmsb_sdk.platform.external.node import (
    NodeManager,
    NodeState,
    NodeConnection,
    ConnectionStatus,
    NodeDiscoveryService,
    DiscoveredNode,
    NodeHealthStatus,
    HealthCheckResult,
    NodeBroadcastService,
    BroadcastMessage,
    BroadcastMessageType,
    SyncService,
    SyncMode,
    SyncStatus,
    SyncResult,
    DataChunk,
    NodeConfig,
)

# Import storage modules
from usmsb_sdk.platform.external.storage import (
    StorageInterface,
    StorageType,
    StorageResult,
    StorageError,
    DataLocation,
    StorageManager,
    CacheStrategy,
    SyncStrategy,
    ConsistencyLevel,
    FileStorage,
    SQLiteStorage,
    IPFSStorage,
)

# Import authentication modules
from usmsb_sdk.platform.external.auth import (
    AuthCoordinator,
    SessionInfo,
    VerificationContext,
    Permission,
    StakeTier,
    AuthContext,
    FullAuthResult,
    WalletAuthResult,
    StakeVerificationResult,
    IWalletAuthenticator,
    MockWalletAuthenticator,
    IStakeVerifier,
    MockStakeVerifier,
    MINIMUM_STAKE_FOR_REGISTRATION,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ExternalAgentProtocol(str, Enum):
    """Supported external agent protocols."""
    A2A = "a2a"           # Agent-to-Agent
    MCP = "mcp"           # Model Context Protocol
    P2P = "p2p"           # Peer-to-Peer
    HTTP = "http"         # HTTP REST
    WEBSOCKET = "websocket"  # WebSocket
    GRPC = "grpc"         # gRPC


class ExternalAgentStatus(str, Enum):
    """Status of external agent."""
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


class SkillMatchLevel(str, Enum):
    """Level of skill matching."""
    EXACT = "exact"
    PARTIAL = "partial"
    COMPATIBLE = "compatible"
    NONE = "none"


@dataclass
class SkillDefinition:
    """Definition of an agent skill."""
    skill_id: str
    name: str
    description: str
    category: str = "general"
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "keywords": self.keywords,
            "prerequisites": self.prerequisites,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillDefinition":
        return cls(
            skill_id=data.get("skill_id", str(uuid.uuid4())),
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            category=data.get("category", "general"),
            input_schema=data.get("input_schema", {}),
            output_schema=data.get("output_schema", {}),
            keywords=data.get("keywords", []),
            prerequisites=data.get("prerequisites", []),
            metadata=data.get("metadata", {}),
        )

    def matches(self, query: str) -> SkillMatchLevel:
        """Check if skill matches a query."""
        query_lower = query.lower()

        # Exact match
        if query_lower == self.name.lower() or query_lower == self.skill_id.lower():
            return SkillMatchLevel.EXACT

        # Check keywords
        for keyword in self.keywords:
            if query_lower == keyword.lower():
                return SkillMatchLevel.EXACT
            if keyword.lower() in query_lower:
                return SkillMatchLevel.PARTIAL

        # Check description
        if query_lower in self.description.lower():
            return SkillMatchLevel.PARTIAL

        # Check category
        if query_lower == self.category.lower():
            return SkillMatchLevel.COMPATIBLE

        return SkillMatchLevel.NONE


@dataclass
class ExternalAgentProfile:
    """Profile of an external agent."""
    agent_id: str
    name: str
    description: str
    protocol: ExternalAgentProtocol
    endpoint: str
    skills: List[SkillDefinition] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    status: ExternalAgentStatus = ExternalAgentStatus.UNKNOWN
    reputation: float = 1.0
    last_seen: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    # New fields for auth integration
    wallet_address: Optional[str] = None
    stake_amount: float = 0.0
    registered_at: Optional[float] = None
    source_node: Optional[str] = None  # Which node this agent was discovered from

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "protocol": self.protocol.value,
            "endpoint": self.endpoint,
            "skills": [s.to_dict() for s in self.skills],
            "capabilities": self.capabilities,
            "status": self.status.value,
            "reputation": self.reputation,
            "last_seen": self.last_seen,
            "metadata": self.metadata,
            "wallet_address": self.wallet_address,
            "stake_amount": self.stake_amount,
            "registered_at": self.registered_at,
            "source_node": self.source_node,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExternalAgentProfile":
        skills = [SkillDefinition.from_dict(s) for s in data.get("skills", [])]
        return cls(
            agent_id=data.get("agent_id", str(uuid.uuid4())),
            name=data.get("name", "Unknown"),
            description=data.get("description", ""),
            protocol=ExternalAgentProtocol(data.get("protocol", "http")),
            endpoint=data.get("endpoint", ""),
            skills=skills,
            capabilities=data.get("capabilities", []),
            status=ExternalAgentStatus(data.get("status", "unknown")),
            reputation=data.get("reputation", 1.0),
            last_seen=data.get("last_seen", 0.0),
            metadata=data.get("metadata", {}),
            wallet_address=data.get("wallet_address"),
            stake_amount=data.get("stake_amount", 0.0),
            registered_at=data.get("registered_at"),
            source_node=data.get("source_node"),
        )


@dataclass
class ExternalAgentCall:
    """A call to an external agent."""
    call_id: str
    agent_id: str
    skill_name: str
    arguments: Dict[str, Any]
    timeout: float = 60.0
    priority: int = 0
    created_at: float = field(default_factory=time.time)
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    # New fields for auth
    session_token: Optional[str] = None
    authenticated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "agent_id": self.agent_id,
            "skill_name": self.skill_name,
            "arguments": self.arguments,
            "timeout": self.timeout,
            "priority": self.priority,
            "created_at": self.created_at,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "session_token": self.session_token,
            "authenticated": self.authenticated,
        }


@dataclass
class ExternalAgentResponse:
    """Response from an external agent."""
    call_id: str
    agent_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    # New fields for auth
    authenticated: bool = False
    permissions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "call_id": self.call_id,
            "agent_id": self.agent_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
            "authenticated": self.authenticated,
            "permissions": self.permissions,
        }


class ProtocolHandler(ABC):
    """Abstract base class for protocol handlers."""

    @abstractmethod
    async def connect(self, endpoint: str) -> bool:
        """Connect to the agent endpoint."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the agent."""
        pass

    @abstractmethod
    async def call_skill(
        self,
        skill_name: str,
        arguments: Dict[str, Any],
        timeout: float = 60.0,
    ) -> ExternalAgentResponse:
        """Call a skill on the external agent."""
        pass

    @abstractmethod
    async def discover_skills(self) -> List[SkillDefinition]:
        """Discover available skills from the agent."""
        pass

    @abstractmethod
    async def check_status(self) -> ExternalAgentStatus:
        """Check the agent's status."""
        pass


# Legacy handlers for backward compatibility
class A2AProtocolHandler(ProtocolHandler):
    """Handler for A2A (Agent-to-Agent) protocol - Legacy implementation."""

    def __init__(self):
        self._connected = False
        self._endpoint: Optional[str] = None

    async def connect(self, endpoint: str) -> bool:
        """Connect to A2A agent."""
        self._endpoint = endpoint
        # In real implementation, establish A2A connection
        self._connected = True
        logger.info(f"A2A connection established to {endpoint}")
        return True

    async def disconnect(self) -> None:
        """Disconnect from A2A agent."""
        self._connected = False
        logger.info("A2A connection closed")

    async def call_skill(
        self,
        skill_name: str,
        arguments: Dict[str, Any],
        timeout: float = 60.0,
    ) -> ExternalAgentResponse:
        """Call skill via A2A protocol."""
        if not self._connected:
            return ExternalAgentResponse(
                call_id=str(uuid.uuid4()),
                agent_id="",
                success=False,
                error="Not connected",
            )

        call_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            # In real implementation, send A2A message
            await asyncio.sleep(0.1)  # Simulate network delay

            return ExternalAgentResponse(
                call_id=call_id,
                agent_id="",
                success=True,
                result={"output": f"Executed {skill_name}"},
                metadata={"execution_time": time.time() - start_time},
            )

        except asyncio.TimeoutError:
            return ExternalAgentResponse(
                call_id=call_id,
                agent_id="",
                success=False,
                error="Timeout",
            )

        except Exception as e:
            return ExternalAgentResponse(
                call_id=call_id,
                agent_id="",
                success=False,
                error=str(e),
            )

    async def discover_skills(self) -> List[SkillDefinition]:
        """Discover skills via A2A protocol."""
        # In real implementation, query agent for skills
        return []

    async def check_status(self) -> ExternalAgentStatus:
        """Check A2A agent status."""
        if self._connected:
            return ExternalAgentStatus.ONLINE
        return ExternalAgentStatus.OFFLINE


class HTTPProtocolHandler(ProtocolHandler):
    """Handler for HTTP REST protocol - Legacy implementation."""

    def __init__(self):
        self._connected = False
        self._endpoint: Optional[str] = None

    async def connect(self, endpoint: str) -> bool:
        """Connect to HTTP agent."""
        self._endpoint = endpoint
        self._connected = True
        logger.info(f"HTTP connection established to {endpoint}")
        return True

    async def disconnect(self) -> None:
        """Disconnect from HTTP agent."""
        self._connected = False
        logger.info("HTTP connection closed")

    async def call_skill(
        self,
        skill_name: str,
        arguments: Dict[str, Any],
        timeout: float = 60.0,
    ) -> ExternalAgentResponse:
        """Call skill via HTTP."""
        if not self._connected:
            return ExternalAgentResponse(
                call_id=str(uuid.uuid4()),
                agent_id="",
                success=False,
                error="Not connected",
            )

        call_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            # In real implementation, make HTTP request
            # POST {endpoint}/skills/{skill_name}
            await asyncio.sleep(0.2)  # Simulate HTTP delay

            return ExternalAgentResponse(
                call_id=call_id,
                agent_id="",
                success=True,
                result={"output": f"HTTP executed {skill_name}"},
                metadata={"execution_time": time.time() - start_time},
            )

        except Exception as e:
            return ExternalAgentResponse(
                call_id=call_id,
                agent_id="",
                success=False,
                error=str(e),
            )

    async def discover_skills(self) -> List[SkillDefinition]:
        """Discover skills via HTTP."""
        # GET {endpoint}/skills
        return []

    async def check_status(self) -> ExternalAgentStatus:
        """Check HTTP agent status."""
        # GET {endpoint}/health
        if self._connected:
            return ExternalAgentStatus.ONLINE
        return ExternalAgentStatus.OFFLINE


class ExternalAgentAdapter:
    """
    Unified Adapter for External AI Agents.

    This adapter provides a unified interface for integrating external
    AI agents regardless of their communication protocol.

    Features:
    - Multi-protocol support (A2A, MCP, P2P, HTTP, WebSocket, gRPC)
    - Skill discovery and capability matching
    - Connection management
    - Call routing and load balancing
    - Error handling and retries
    - Storage layer integration for persistence
    - Authentication and session management
    - Node-based agent synchronization

    Version 2.0 Enhancements:
    - Uses protocol factory from protocol/ module
    - Integrates storage manager for persistence
    - Supports wallet and stake-based authentication
    - Can sync agents from other network nodes
    """

    def __init__(
        self,
        storage_manager: Optional[StorageManager] = None,
        auth_coordinator: Optional[AuthCoordinator] = None,
        node_manager: Optional[NodeManager] = None,
        sync_service: Optional[SyncService] = None,
        use_new_handlers: bool = True,
    ):
        """
        Initialize the External Agent Adapter.

        Args:
            storage_manager: Storage manager for persistence (optional)
            auth_coordinator: Authentication coordinator (optional)
            node_manager: Node manager for distributed operations (optional)
            sync_service: Sync service for agent synchronization (optional)
            use_new_handlers: Whether to use new protocol handlers from protocol/ module
        """
        # Registered external agents
        self._agents: Dict[str, ExternalAgentProfile] = {}

        # Protocol handlers
        self._handlers: Dict[str, ProtocolHandler] = {}

        # Pending calls
        self._pending_calls: Dict[str, ExternalAgentCall] = {}

        # Call history
        self._call_history: List[ExternalAgentCall] = []

        # Skill index for quick lookup
        self._skill_index: Dict[str, List[str]] = {}  # skill_name -> agent_ids

        # Callbacks
        self.on_agent_registered: Optional[Callable[[ExternalAgentProfile], None]] = None
        self.on_agent_status_changed: Optional[Callable[[str, ExternalAgentStatus], None]] = None
        self.on_call_completed: Optional[Callable[[ExternalAgentCall], None]] = None

        # New: Storage manager
        self._storage_manager = storage_manager
        self._storage_enabled = storage_manager is not None

        # New: Authentication coordinator
        self._auth_coordinator = auth_coordinator
        self._auth_enabled = auth_coordinator is not None

        # New: Node manager for distributed operations
        self._node_manager = node_manager

        # New: Sync service for agent synchronization
        self._sync_service = sync_service

        # New: Use new protocol handlers
        self._use_new_handlers = use_new_handlers

        # New: Flag for initialization state
        self._initialized = False

    async def initialize(self) -> bool:
        """
        Initialize the adapter and its components.

        Returns:
            True if initialization successful
        """
        if self._initialized:
            return True

        try:
            # Initialize storage manager
            if self._storage_manager:
                await self._storage_manager.initialize()
                # Load persisted agents
                await self._load_agents_from_storage()

            # Initialize auth coordinator
            if self._auth_coordinator:
                await self._auth_coordinator.initialize()

            self._initialized = True
            logger.info("ExternalAgentAdapter initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize ExternalAgentAdapter: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown the adapter and cleanup resources."""
        # Disconnect all handlers
        for agent_id, handler in list(self._handlers.items()):
            try:
                await handler.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting handler for {agent_id}: {e}")

        # Shutdown auth coordinator
        if self._auth_coordinator:
            await self._auth_coordinator.shutdown()

        # Close storage manager
        if self._storage_manager:
            await self._storage_manager.close()

        self._initialized = False
        logger.info("ExternalAgentAdapter shutdown complete")

    async def _load_agents_from_storage(self) -> None:
        """Load persisted agents from storage."""
        if not self._storage_manager:
            return

        try:
            # Try to load agents from storage
            result = await self._storage_manager.retrieve("registered_agents")
            if result.success and result.data:
                agents_data = result.data
                for agent_data in agents_data:
                    try:
                        profile = ExternalAgentProfile.from_dict(agent_data)
                        self._agents[profile.agent_id] = profile

                        # Rebuild skill index
                        for skill in profile.skills:
                            skill_key = skill.name.lower()
                            if skill_key not in self._skill_index:
                                self._skill_index[skill_key] = []
                            self._skill_index[skill_key].append(profile.agent_id)

                    except Exception as e:
                        logger.warning(f"Failed to load agent from storage: {e}")

                logger.info(f"Loaded {len(self._agents)} agents from storage")

        except Exception as e:
            logger.debug(f"No persisted agents found or error loading: {e}")

    async def _save_agents_to_storage(self) -> None:
        """Save registered agents to storage."""
        if not self._storage_manager:
            return

        try:
            agents_data = [profile.to_dict() for profile in self._agents.values()]
            await self._storage_manager.store(
                "registered_agents",
                agents_data,
                metadata={"type": "agent_registry"},
            )
        except Exception as e:
            logger.error(f"Failed to save agents to storage: {e}")

    def _get_protocol_handler(
        self,
        protocol: ExternalAgentProtocol,
        config: Optional[ProtocolConfig] = None,
    ) -> ProtocolHandler:
        """
        Get or create a protocol handler.

        Uses the new protocol factory if enabled, otherwise falls back to
        legacy handlers for backward compatibility.

        Args:
            protocol: The protocol type
            config: Optional protocol configuration

        Returns:
            Protocol handler instance
        """
        if self._use_new_handlers:
            # Use the new protocol factory (lazy import to avoid circular dependency)
            protocol_module = _get_protocol_module()
            return protocol_module.create_protocol_handler(protocol.value, config=config)

        # Legacy handler creation (use local classes defined in this file)
        if protocol == ExternalAgentProtocol.A2A:
            return A2AProtocolHandler()
        elif protocol == ExternalAgentProtocol.HTTP:
            return HTTPProtocolHandler()
        else:
            # Default to HTTP
            return HTTPProtocolHandler()

    # ========== Agent Registration ==========

    async def register_agent(
        self,
        agent_id: str,
        name: str,
        description: str,
        protocol: ExternalAgentProtocol,
        endpoint: str,
        skills: Optional[List[SkillDefinition]] = None,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ExternalAgentProfile:
        """
        Register an external agent.

        Args:
            agent_id: Unique identifier
            name: Agent name
            description: Agent description
            protocol: Communication protocol
            endpoint: Agent endpoint
            skills: List of skills
            capabilities: List of capabilities
            metadata: Additional metadata

        Returns:
            The registered agent profile
        """
        profile = ExternalAgentProfile(
            agent_id=agent_id,
            name=name,
            description=description,
            protocol=protocol,
            endpoint=endpoint,
            skills=skills or [],
            capabilities=capabilities or [],
            status=ExternalAgentStatus.UNKNOWN,
            metadata=metadata or {},
        )

        # Create and connect protocol handler
        handler = self._get_protocol_handler(protocol)
        connected = await handler.connect(endpoint)

        if connected:
            profile.status = ExternalAgentStatus.ONLINE
            profile.last_seen = time.time()

            # Discover skills if not provided
            if not profile.skills:
                try:
                    profile.skills = await handler.discover_skills()
                except Exception as e:
                    logger.warning(f"Failed to discover skills for {agent_id}: {e}")

        self._agents[agent_id] = profile
        self._handlers[agent_id] = handler

        # Index skills
        for skill in profile.skills:
            skill_key = skill.name.lower()
            if skill_key not in self._skill_index:
                self._skill_index[skill_key] = []
            if agent_id not in self._skill_index[skill_key]:
                self._skill_index[skill_key].append(agent_id)

        # Persist to storage
        await self._save_agents_to_storage()

        logger.info(f"Registered external agent: {agent_id} ({protocol.value})")

        if self.on_agent_registered:
            self.on_agent_registered(profile)

        return profile

    async def register_agent_with_storage(
        self,
        agent_id: str,
        name: str,
        description: str,
        protocol: ExternalAgentProtocol,
        endpoint: str,
        wallet_address: str,
        auth_context: AuthContext,
        skills: Optional[List[SkillDefinition]] = None,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        minimum_stake: float = MINIMUM_STAKE_FOR_REGISTRATION,
    ) -> Union[ExternalAgentProfile, FullAuthResult]:
        """
        Register an external agent with storage persistence and authentication.

        This method combines agent registration with:
        1. Wallet signature verification
        2. Stake verification
        3. Persistent storage

        Args:
            agent_id: Unique identifier
            name: Agent name
            description: Agent description
            protocol: Communication protocol
            endpoint: Agent endpoint
            wallet_address: Wallet address of the agent owner
            auth_context: Authentication context with signature
            skills: List of skills
            capabilities: List of capabilities
            metadata: Additional metadata
            minimum_stake: Minimum required stake for registration

        Returns:
            ExternalAgentProfile if successful, FullAuthResult if auth failed
        """
        # Step 1: Verify authentication if coordinator is available
        if self._auth_coordinator:
            verification_context = VerificationContext(
                auth_context=auth_context,
                require_stake=True,
                minimum_stake=minimum_stake,
                require_agent_binding=True,
                agent_id=agent_id,
            )

            auth_result = await self._auth_coordinator.verify_for_registration(
                verification_context
            )

            if not auth_result.success:
                logger.warning(f"Authentication failed for agent {agent_id}: {auth_result.error_message}")
                return auth_result

        # Step 2: Register the agent
        profile = await self.register_agent(
            agent_id=agent_id,
            name=name,
            description=description,
            protocol=protocol,
            endpoint=endpoint,
            skills=skills,
            capabilities=capabilities,
            metadata=metadata or {},
        )

        # Step 3: Add authentication info to profile
        profile.wallet_address = wallet_address
        profile.registered_at = time.time()

        if self._auth_coordinator:
            # Get stake info from auth result
            if auth_result.stake_verification:
                profile.stake_amount = auth_result.stake_verification.stake_amount

        # Step 4: Persist to storage with enhanced metadata
        if self._storage_manager:
            try:
                # Store in SQLite for structured queries
                await self._storage_manager.store_to_sqlite(
                    f"agent:{agent_id}",
                    profile.to_dict(),
                    metadata={
                        "type": "agent_registration",
                        "wallet_address": wallet_address,
                        "registered_at": profile.registered_at,
                    },
                )

                # Also store in IPFS for decentralized backup if significant stake
                if profile.stake_amount >= minimum_stake * 10:
                    await self._storage_manager.store_to_ipfs(
                        f"agent:{agent_id}:backup",
                        profile.to_dict(),
                        metadata={"type": "agent_backup"},
                    )

            except Exception as e:
                logger.error(f"Failed to persist agent to storage: {e}")

        # Update local cache
        self._agents[agent_id] = profile
        await self._save_agents_to_storage()

        logger.info(
            f"Registered agent {agent_id} with storage and auth "
            f"(wallet={wallet_address}, stake={profile.stake_amount})"
        )

        return profile

    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an external agent."""
        if agent_id not in self._agents:
            return False

        # Disconnect handler
        if agent_id in self._handlers:
            await self._handlers[agent_id].disconnect()
            del self._handlers[agent_id]

        # Remove from skill index
        profile = self._agents[agent_id]
        for skill in profile.skills:
            skill_key = skill.name.lower()
            if skill_key in self._skill_index:
                if agent_id in self._skill_index[skill_key]:
                    self._skill_index[skill_key].remove(agent_id)

        del self._agents[agent_id]

        # Remove from storage
        if self._storage_manager:
            try:
                await self._storage_manager.delete(f"agent:{agent_id}")
            except Exception as e:
                logger.warning(f"Failed to remove agent from storage: {e}")

        await self._save_agents_to_storage()

        logger.info(f"Unregistered external agent: {agent_id}")
        return True

    def get_agent(self, agent_id: str) -> Optional[ExternalAgentProfile]:
        """Get an agent profile by ID."""
        return self._agents.get(agent_id)

    def list_agents(
        self,
        protocol: Optional[ExternalAgentProtocol] = None,
        status: Optional[ExternalAgentStatus] = None,
        wallet_address: Optional[str] = None,
        min_stake: Optional[float] = None,
    ) -> List[ExternalAgentProfile]:
        """
        List registered agents with optional filtering.

        Args:
            protocol: Filter by protocol type
            status: Filter by status
            wallet_address: Filter by wallet address
            min_stake: Filter by minimum stake amount

        Returns:
            List of matching agent profiles
        """
        agents = list(self._agents.values())

        if protocol:
            agents = [a for a in agents if a.protocol == protocol]

        if status:
            agents = [a for a in agents if a.status == status]

        if wallet_address:
            agents = [a for a in agents if a.wallet_address == wallet_address]

        if min_stake is not None:
            agents = [a for a in agents if a.stake_amount >= min_stake]

        return agents

    # ========== Skill Discovery ==========

    def find_agents_by_skill(
        self,
        skill_name: str,
        match_level: SkillMatchLevel = SkillMatchLevel.PARTIAL,
    ) -> List[ExternalAgentProfile]:
        """
        Find agents that have a specific skill.

        Args:
            skill_name: Skill to search for
            match_level: Minimum match level required

        Returns:
            List of matching agent profiles
        """
        skill_lower = skill_name.lower()
        matching_agents = []

        for agent in self._agents.values():
            for skill in agent.skills:
                match = skill.matches(skill_name)

                # Check if match level is sufficient
                levels = {
                    SkillMatchLevel.EXACT: 4,
                    SkillMatchLevel.PARTIAL: 3,
                    SkillMatchLevel.COMPATIBLE: 2,
                    SkillMatchLevel.NONE: 1,
                }

                if levels[match] >= levels[match_level]:
                    matching_agents.append(agent)
                    break

        return matching_agents

    def find_agents_by_capability(
        self,
        capability: str,
    ) -> List[ExternalAgentProfile]:
        """Find agents that have a specific capability."""
        capability_lower = capability.lower()
        return [
            agent for agent in self._agents.values()
            if any(capability_lower in c.lower() for c in agent.capabilities)
        ]

    def get_skill(self, agent_id: str, skill_name: str) -> Optional[SkillDefinition]:
        """Get a specific skill from an agent."""
        agent = self._agents.get(agent_id)
        if not agent:
            return None

        for skill in agent.skills:
            if skill.name.lower() == skill_name.lower():
                return skill

        return None

    # ========== Agent Calls ==========

    async def call_agent(
        self,
        agent_id: str,
        skill_name: str,
        arguments: Dict[str, Any],
        timeout: float = 60.0,
        priority: int = 0,
    ) -> ExternalAgentResponse:
        """
        Call a skill on an external agent.

        Args:
            agent_id: Target agent ID
            skill_name: Skill to call
            arguments: Arguments for the skill
            timeout: Call timeout
            priority: Call priority

        Returns:
            The response from the agent
        """
        if agent_id not in self._agents:
            return ExternalAgentResponse(
                call_id=str(uuid.uuid4()),
                agent_id=agent_id,
                success=False,
                error="Agent not found",
            )

        if agent_id not in self._handlers:
            return ExternalAgentResponse(
                call_id=str(uuid.uuid4()),
                agent_id=agent_id,
                success=False,
                error="No handler for agent",
            )

        # Create call record
        call = ExternalAgentCall(
            call_id=str(uuid.uuid4()),
            agent_id=agent_id,
            skill_name=skill_name,
            arguments=arguments,
            timeout=timeout,
            priority=priority,
        )

        self._pending_calls[call.call_id] = call

        # Execute call
        handler = self._handlers[agent_id]
        start_time = time.time()

        try:
            response = await handler.call_skill(skill_name, arguments, timeout)

            call.status = "completed" if response.success else "failed"
            call.result = response.result
            call.error = response.error
            call.execution_time = time.time() - start_time

            # Update agent last seen
            self._agents[agent_id].last_seen = time.time()

        except asyncio.TimeoutError:
            call.status = "timeout"
            call.error = "Call timed out"
            call.execution_time = time.time() - start_time

            response = ExternalAgentResponse(
                call_id=call.call_id,
                agent_id=agent_id,
                success=False,
                error="Timeout",
            )

        except Exception as e:
            call.status = "error"
            call.error = str(e)
            call.execution_time = time.time() - start_time

            response = ExternalAgentResponse(
                call_id=call.call_id,
                agent_id=agent_id,
                success=False,
                error=str(e),
            )

        # Move to history
        self._call_history.append(call)
        if call.call_id in self._pending_calls:
            del self._pending_calls[call.call_id]

        if self.on_call_completed:
            self.on_call_completed(call)

        return response

    async def call_agent_with_auth(
        self,
        agent_id: str,
        skill_name: str,
        arguments: Dict[str, Any],
        session_token: str,
        auth_context: Optional[AuthContext] = None,
        timeout: float = 60.0,
        priority: int = 0,
        required_permissions: Optional[List[Permission]] = None,
    ) -> ExternalAgentResponse:
        """
        Call a skill on an external agent with authentication.

        This method verifies the session and permissions before making the call.

        Args:
            agent_id: Target agent ID
            skill_name: Skill to call
            arguments: Arguments for the skill
            session_token: Session token for authentication
            auth_context: Optional auth context for additional verification
            timeout: Call timeout
            priority: Call priority
            required_permissions: List of required permissions

        Returns:
            The response from the agent with authentication status
        """
        # Step 1: Validate session
        if not self._auth_coordinator:
            return ExternalAgentResponse(
                call_id=str(uuid.uuid4()),
                agent_id=agent_id,
                success=False,
                error="Authentication not configured",
                authenticated=False,
            )

        session = await self._auth_coordinator.validate_session(session_token)
        if not session:
            return ExternalAgentResponse(
                call_id=str(uuid.uuid4()),
                agent_id=agent_id,
                success=False,
                error="Invalid or expired session",
                authenticated=False,
            )

        # Step 2: Check permissions
        if required_permissions:
            for perm in required_permissions:
                if perm not in session.permissions:
                    return ExternalAgentResponse(
                        call_id=str(uuid.uuid4()),
                        agent_id=agent_id,
                        success=False,
                        error=f"Missing required permission: {perm.value}",
                        authenticated=True,
                        permissions=[p.value for p in session.permissions],
                    )

        # Step 3: Additional auth context verification if provided
        if auth_context:
            verify_context = VerificationContext(
                auth_context=auth_context,
                require_stake=False,  # Already verified in session
                require_agent_binding=(agent_id is not None),
                agent_id=agent_id,
            )
            auth_result = await self._auth_coordinator.verify_for_communication(verify_context)
            if not auth_result.success:
                return ExternalAgentResponse(
                    call_id=str(uuid.uuid4()),
                    agent_id=agent_id,
                    success=False,
                    error=f"Communication verification failed: {auth_result.error_message}",
                    authenticated=False,
                )

        # Step 4: Make the actual call
        response = await self.call_agent(
            agent_id=agent_id,
            skill_name=skill_name,
            arguments=arguments,
            timeout=timeout,
            priority=priority,
        )

        # Step 5: Add authentication info to response
        response.authenticated = True
        response.permissions = [p.value for p in session.permissions]

        return response

    async def call_best_agent(
        self,
        skill_name: str,
        arguments: Dict[str, Any],
        selection_criteria: str = "reputation",
        timeout: float = 60.0,
    ) -> ExternalAgentResponse:
        """
        Find and call the best agent for a skill.

        Args:
            skill_name: Skill to call
            arguments: Arguments for the skill
            selection_criteria: How to select agent (reputation, load, random)
            timeout: Call timeout

        Returns:
            The response from the selected agent
        """
        # Find agents with the skill
        agents = self.find_agents_by_skill(skill_name, SkillMatchLevel.PARTIAL)

        # Filter online agents
        online_agents = [a for a in agents if a.status == ExternalAgentStatus.ONLINE]

        if not online_agents:
            return ExternalAgentResponse(
                call_id=str(uuid.uuid4()),
                agent_id="",
                success=False,
                error="No online agents with required skill",
            )

        # Select best agent
        if selection_criteria == "reputation":
            # Consider both reputation and stake
            best_agent = max(online_agents, key=lambda a: a.reputation + (a.stake_amount / 1000))
        elif selection_criteria == "stake":
            best_agent = max(online_agents, key=lambda a: a.stake_amount)
        elif selection_criteria == "random":
            import random
            best_agent = random.choice(online_agents)
        else:
            best_agent = online_agents[0]

        return await self.call_agent(
            agent_id=best_agent.agent_id,
            skill_name=skill_name,
            arguments=arguments,
            timeout=timeout,
        )

    async def broadcast_to_skill(
        self,
        skill_name: str,
        arguments: Dict[str, Any],
        max_responses: int = 5,
        timeout: float = 30.0,
    ) -> List[ExternalAgentResponse]:
        """
        Broadcast a call to all agents with a skill.

        Args:
            skill_name: Skill to call
            arguments: Arguments for the skill
            max_responses: Maximum responses to wait for
            timeout: Total timeout for all responses

        Returns:
            List of responses
        """
        agents = self.find_agents_by_skill(skill_name)
        online_agents = [a for a in agents if a.status == ExternalAgentStatus.ONLINE]

        if not online_agents:
            return []

        # Make concurrent calls
        tasks = [
            self.call_agent(a.agent_id, skill_name, arguments, timeout / 2)
            for a in online_agents[:max_responses * 2]
        ]

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter valid responses
        valid_responses = [
            r for r in responses
            if isinstance(r, ExternalAgentResponse) and r.success
        ]

        return valid_responses[:max_responses]

    # ========== Node Synchronization ==========

    async def sync_agents_from_nodes(
        self,
        node_ids: Optional[List[str]] = None,
        sync_mode: SyncMode = SyncMode.INCREMENTAL,
        since: Optional[float] = None,
    ) -> SyncResult:
        """
        Synchronize agent registrations from other network nodes.

        This method discovers and registers agents from other nodes in the network,
        enabling distributed agent discovery.

        Args:
            node_ids: Specific node IDs to sync from (None for all known nodes)
            sync_mode: Synchronization mode (incremental, full, etc.)
            since: Timestamp for incremental sync
            None for full sync

        Returns:
            SyncResult with synchronization details
        """
        if not self._sync_service:
            return SyncResult(
                operation_id=str(uuid.uuid4()),
                success=False,
                synced_count=0,
                failed_count=0,
                conflicts_count=0,
                bytes_transferred=0,
                duration_seconds=0.0,
                errors=["Sync service not configured"],
            )

        # Register data provider for agents
        self._sync_service.register_data_provider(
            data_type="agents",
            provider=self._get_agent_changes,
            applier=self._apply_agent_changes,
            conflict_resolver=self._resolve_agent_conflicts,
        )

        # Get target nodes
        target_nodes = node_ids
        if not target_nodes and self._node_manager:
            # Get all connected nodes
            connections = self._node_manager.get_connections()
            target_nodes = [conn.remote_node_id for conn in connections]

        if not target_nodes:
            return SyncResult(
                operation_id=str(uuid.uuid4()),
                success=True,
                synced_count=0,
                failed_count=0,
                conflicts_count=0,
                bytes_transferred=0,
                duration_seconds=0.0,
                errors=["No nodes to sync from"],
            )

        # Sync with each node
        total_synced = 0
        total_failed = 0
        total_conflicts = 0
        total_bytes = 0
        errors = []
        start_time = time.time()

        for node_id in target_nodes:
            try:
                result = await self._sync_service.sync_with_peer(
                    peer_id=node_id,
                    data_type="agents",
                    mode=sync_mode,
                    since=since,
                )

                total_synced += result.synced_count
                total_failed += result.failed_count
                total_conflicts += result.conflicts_count
                total_bytes += result.bytes_transferred

                if not result.success:
                    errors.extend(result.errors)

            except Exception as e:
                errors.append(f"Failed to sync with {node_id}: {e}")
                total_failed += 1

        # Save synced agents to storage
        await self._save_agents_to_storage()

        return SyncResult(
            operation_id=str(uuid.uuid4()),
            success=len(errors) == 0,
            synced_count=total_synced,
            failed_count=total_failed,
            conflicts_count=total_conflicts,
            bytes_transferred=total_bytes,
            duration_seconds=time.time() - start_time,
            errors=errors,
        )

    def _get_agent_changes(
        self,
        since: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get agent changes for synchronization.

        This is a data provider function for the sync service.

        Args:
            since: Get changes since timestamp
            limit: Maximum number of changes

        Returns:
            List of agent changes
        """
        changes = []
        for agent in self._agents.values():
            if since is None or (agent.registered_at and agent.registered_at > since):
                changes.append({
                    "key": agent.agent_id,
                    "value": agent.to_dict(),
                    "timestamp": agent.registered_at or agent.last_seen,
                    "node_id": agent.source_node,
                })

        if limit:
            changes = changes[:limit]

        return changes

    def _apply_agent_changes(self, changes: List[Dict[str, Any]]) -> int:
        """
        Apply agent changes from synchronization.

        This is a data applier function for the sync service.

        Args:
            changes: List of agent changes to apply

        Returns:
            Number of changes applied
        """
        applied = 0
        for change in changes:
            try:
                agent_data = change.get("value", {})
                agent_id = change.get("key")

                if not agent_id or not agent_data:
                    continue

                # Create profile from data
                profile = ExternalAgentProfile.from_dict(agent_data)
                profile.source_node = change.get("node_id")

                # Add or update agent
                if agent_id not in self._agents:
                    self._agents[agent_id] = profile

                    # Index skills
                    for skill in profile.skills:
                        skill_key = skill.name.lower()
                        if skill_key not in self._skill_index:
                            self._skill_index[skill_key] = []
                        if agent_id not in self._skill_index[skill_key]:
                            self._skill_index[skill_key].append(agent_id)

                    applied += 1
                else:
                    # Update existing agent
                    existing = self._agents[agent_id]
                    existing.last_seen = profile.last_seen
                    existing.status = profile.status
                    if profile.skills:
                        existing.skills = profile.skills
                    applied += 1

            except Exception as e:
                logger.warning(f"Failed to apply agent change: {e}")

        return applied

    def _resolve_agent_conflicts(self, conflict_info: Any) -> Any:
        """
        Resolve conflicts during agent synchronization.

        Uses last-write-wins strategy by default, but prefers higher stake.

        Args:
            conflict_info: Conflict information

        Returns:
            Resolved value
        """
        local = conflict_info.local_value
        remote = conflict_info.remote_value

        if isinstance(local, dict) and isinstance(remote, dict):
            local_stake = local.get("stake_amount", 0)
            remote_stake = remote.get("stake_amount", 0)

            # Prefer higher stake
            if remote_stake > local_stake:
                return remote

            # If equal stake, use timestamp
            if conflict_info.remote_timestamp > conflict_info.local_timestamp:
                return remote

        return local

    # ========== Status Management ==========

    async def check_agent_status(self, agent_id: str) -> ExternalAgentStatus:
        """Check the status of an agent."""
        if agent_id not in self._agents or agent_id not in self._handlers:
            return ExternalAgentStatus.UNKNOWN

        handler = self._handlers[agent_id]
        status = await handler.check_status()

        old_status = self._agents[agent_id].status
        self._agents[agent_id].status = status

        if status == ExternalAgentStatus.ONLINE:
            self._agents[agent_id].last_seen = time.time()

        if old_status != status and self.on_agent_status_changed:
            self.on_agent_status_changed(agent_id, status)

        return status

    async def check_all_agents_status(self) -> Dict[str, ExternalAgentStatus]:
        """Check status of all registered agents."""
        tasks = {aid: self.check_agent_status(aid) for aid in self._agents}
        results = {}

        for aid, task in tasks.items():
            results[aid] = await task

        return results

    # ========== Utility Methods ==========

    def get_statistics(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        successful_calls = sum(1 for c in self._call_history if c.status == "completed")
        failed_calls = sum(1 for c in self._call_history if c.status != "completed")

        stats = {
            "total_agents": len(self._agents),
            "online_agents": sum(
                1 for a in self._agents.values()
                if a.status == ExternalAgentStatus.ONLINE
            ),
            "total_skills": sum(len(a.skills) for a in self._agents.values()),
            "total_calls": len(self._call_history),
            "pending_calls": len(self._pending_calls),
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": successful_calls / max(1, len(self._call_history)),
            "storage_enabled": self._storage_enabled,
            "auth_enabled": self._auth_enabled,
            "use_new_handlers": self._use_new_handlers,
            "authenticated_agents": sum(
                1 for a in self._agents.values() if a.wallet_address is not None
            ),
            "total_stake": sum(a.stake_amount for a in self._agents.values()),
        }

        # Add storage stats if available
        if self._storage_manager:
            try:
                storage_stats = asyncio.get_event_loop().run_until_complete(
                    self._storage_manager.get_stats()
                )
                stats["storage_stats"] = storage_stats
            except Exception:
                pass

        return stats

    def get_call_history(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[ExternalAgentCall]:
        """Get call history."""
        history = self._call_history

        if agent_id:
            history = [c for c in history if c.agent_id == agent_id]

        return history[-limit:]

    def clear_history(self) -> None:
        """Clear call history."""
        self._call_history.clear()

    # ========== Configuration ==========

    def set_storage_manager(self, storage_manager: StorageManager) -> None:
        """Set the storage manager."""
        self._storage_manager = storage_manager
        self._storage_enabled = True

    def set_auth_coordinator(self, auth_coordinator: AuthCoordinator) -> None:
        """Set the authentication coordinator."""
        self._auth_coordinator = auth_coordinator
        self._auth_enabled = True

    def set_node_manager(self, node_manager: NodeManager) -> None:
        """Set the node manager."""
        self._node_manager = node_manager

    def set_sync_service(self, sync_service: SyncService) -> None:
        """Set the sync service."""
        self._sync_service = sync_service


# ========== Convenience Functions ==========

def create_skill_from_dict(data: Dict[str, Any]) -> SkillDefinition:
    """Create a SkillDefinition from a dictionary."""
    return SkillDefinition.from_dict(data)


def create_agent_from_skill_md(skill_md_content: str) -> Optional[ExternalAgentProfile]:
    """
    Parse a skill.md file and create an agent profile.

    Args:
        skill_md_content: Content of skill.md file

    Returns:
        ExternalAgentProfile or None if parsing fails
    """
    # Simple markdown parsing for skill definitions
    # Expected format:
    # # Agent Name
    # Description: ...
    # Protocol: ...
    # Endpoint: ...
    # ## Skills
    # - skill_name: description

    try:
        lines = skill_md_content.split('\n')
        name = ""
        description = ""
        protocol = ExternalAgentProtocol.HTTP
        endpoint = ""
        skills = []

        for i, line in enumerate(lines):
            line = line.strip()

            if line.startswith('# ') and not name:
                name = line[2:].strip()

            elif line.lower().startswith('description:'):
                description = line.split(':', 1)[1].strip()

            elif line.lower().startswith('protocol:'):
                proto_str = line.split(':', 1)[1].strip().lower()
                protocol = ExternalAgentProtocol(proto_str)

            elif line.lower().startswith('endpoint:'):
                endpoint = line.split(':', 1)[1].strip()

            elif line.startswith('- ') and ':' in line:
                skill_parts = line[2:].split(':', 1)
                if len(skill_parts) == 2:
                    skills.append(SkillDefinition(
                        skill_id=str(uuid.uuid4()),
                        name=skill_parts[0].strip(),
                        description=skill_parts[1].strip(),
                    ))

        if name and endpoint:
            return ExternalAgentProfile(
                agent_id=str(uuid.uuid4()),
                name=name,
                description=description,
                protocol=protocol,
                endpoint=endpoint,
                skills=skills,
            )

    except Exception as e:
        logger.error(f"Failed to parse skill.md: {e}")

    return None


async def create_external_agent_adapter(
    storage_base_path: Optional[str] = None,
    enable_auth: bool = False,
    wallet_authenticator: Optional[IWalletAuthenticator] = None,
    stake_verifier: Optional[IStakeVerifier] = None,
    use_new_handlers: bool = True,
) -> ExternalAgentAdapter:
    """
    Factory function to create and initialize an ExternalAgentAdapter.

    Args:
        storage_base_path: Base path for storage (None to disable storage)
        enable_auth: Whether to enable authentication
        wallet_authenticator: Custom wallet authenticator
        stake_verifier: Custom stake verifier
        use_new_handlers: Whether to use new protocol handlers

    Returns:
        Initialized ExternalAgentAdapter instance
    """
    storage_manager = None
    auth_coordinator = None

    # Create storage manager if path provided
    if storage_base_path:
        from pathlib import Path
        storage_manager = await create_storage_manager(
            base_path=Path(storage_base_path),
            cache_strategy=CacheStrategy.WRITE_THROUGH,
            sync_strategy=SyncStrategy.HYBRID,
        )

    # Create auth coordinator if enabled
    if enable_auth:
        auth_coordinator = AuthCoordinator(
            wallet_authenticator=wallet_authenticator or MockWalletAuthenticator(),
            stake_verifier=stake_verifier or MockStakeVerifier(),
        )

    # Create adapter
    adapter = ExternalAgentAdapter(
        storage_manager=storage_manager,
        auth_coordinator=auth_coordinator,
        use_new_handlers=use_new_handlers,
    )

    # Initialize
    await adapter.initialize()

    return adapter
