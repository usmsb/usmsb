"""
Base Agent Module

Provides the abstract BaseAgent class that serves as the foundation
for all intelligent agents in the SDK.

The BaseAgent class implements:
- Lifecycle management (start, stop, restart)
- Multi-protocol registration
- Unified communication interface
- P2P direct connection capability
- Automatic agent discovery
- Skill execution and publishing
- Platform integration (marketplace, wallet, collaboration, etc.)
"""

from abc import ABC, abstractmethod
from asyncio import Lock, Event, create_task, gather, sleep
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
import asyncio
import logging

from usmsb_sdk.agent_sdk.agent_config import (
    AgentConfig,
    CapabilityDefinition,
    ProtocolType,
    SkillDefinition,
)
from usmsb_sdk.agent_sdk.registration import RegistrationManager, RegistrationStatus
from usmsb_sdk.agent_sdk.communication import CommunicationManager, Message, MessageType, Session
from usmsb_sdk.agent_sdk.discovery import DiscoveryManager, AgentInfo, DiscoveryFilter

# New platform integration modules
from usmsb_sdk.agent_sdk.platform_client import PlatformClient, RegistrationResult
from usmsb_sdk.agent_sdk.marketplace import (
    MarketplaceManager,
    ServiceDefinition,
    Service,
    DemandDefinition,
    Demand,
    Opportunity,
    MatchScore,
)
from usmsb_sdk.agent_sdk.wallet import WalletManager, WalletBalance, StakeInfo, StakeResult
from usmsb_sdk.agent_sdk.negotiation import (
    NegotiationManager,
    NegotiationSession,
    NegotiationTerms,
    ProposalResult,
)
from usmsb_sdk.agent_sdk.collaboration import (
    CollaborationManager,
    CollaborationSession,
    CollaborationRole,
    Contribution,
)
from usmsb_sdk.agent_sdk.workflow import WorkflowManager, Workflow, WorkflowResult
from usmsb_sdk.agent_sdk.learning import (
    LearningManager,
    LearningInsight,
    PerformanceAnalysis,
    MarketInsights,
    Experience,
)


class AgentState(Enum):
    """Agent lifecycle states"""
    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    This class provides the core functionality for agent lifecycle management,
    multi-protocol communication, registration, discovery, and skill execution.

    Subclasses must implement:
        - initialize(): Custom initialization logic
        - handle_message(): Message handling logic
        - execute_skill(): Skill execution logic
        - shutdown(): Cleanup logic

    Example:
        class MyAgent(BaseAgent):
            async def initialize(self):
                self.logger.info("Initializing MyAgent")
                # Setup resources

            async def handle_message(self, message: Message, session: Optional[Session]) -> Optional[Message]:
                self.logger.info(f"Received: {message.content}")
                return Message(
                    type=MessageType.RESPONSE,
                    sender_id=self.agent_id,
                    content={"status": "acknowledged"}
                )

            async def execute_skill(self, skill_name: str, params: Dict[str, Any]) -> Any:
                if skill_name == "process":
                    return await self._process(params)
                raise ValueError(f"Unknown skill: {skill_name}")

            async def shutdown(self):
                self.logger.info("Shutting down MyAgent")
                # Cleanup resources
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize the base agent.

        Args:
            config: Agent configuration containing identity, protocols, skills, etc.
        """
        self.config = config
        self.agent_id = config.agent_id
        self.name = config.name
        self.description = config.description
        self.version = config.version

        # State management
        self._state = AgentState.CREATED
        self._state_lock = Lock()
        self._running = False
        self._ready_event = Event()

        # Logger setup
        self.logger = logging.getLogger(f"agent.{self.name}")
        self.logger.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))

        # Core components
        self._registration_manager: Optional[RegistrationManager] = None
        self._communication_manager: Optional[CommunicationManager] = None
        self._discovery_manager: Optional[DiscoveryManager] = None

        # Platform integration components
        self._platform_client: Optional[PlatformClient] = None
        self._marketplace: Optional[MarketplaceManager] = None
        self._wallet: Optional[WalletManager] = None
        self._negotiation: Optional[NegotiationManager] = None
        self._collaboration: Optional[CollaborationManager] = None
        self._workflow: Optional[WorkflowManager] = None
        self._learning: Optional[LearningManager] = None

        # Platform URL for integration
        self._platform_url: str = "http://localhost:8000"

        # Skill and capability registries
        self._skills: Dict[str, SkillDefinition] = {s.name: s for s in config.skills}
        self._capabilities: Dict[str, CapabilityDefinition] = {c.name: c for c in config.capabilities}

        # Message handlers
        self._message_handlers: Dict[str, Callable] = {}
        self._skill_handlers: Dict[str, Callable] = {}

        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()

        # Metrics
        self._metrics = {
            "messages_received": 0,
            "messages_sent": 0,
            "skills_executed": 0,
            "errors": 0,
            "start_time": None,
            "last_activity": None,
        }

        # Event hooks
        self._on_state_change_hooks: List[Callable] = []
        self._on_message_hooks: List[Callable] = []
        self._on_skill_hooks: List[Callable] = []
        self._on_error_hooks: List[Callable] = []

    @property
    def state(self) -> AgentState:
        """Get current agent state"""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if agent is running"""
        return self._running and self._state == AgentState.RUNNING

    @property
    def skills(self) -> List[SkillDefinition]:
        """Get list of available skills"""
        return list(self._skills.values())

    @property
    def capabilities(self) -> List[CapabilityDefinition]:
        """Get list of capabilities"""
        return list(self._capabilities.values())

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get agent metrics"""
        return {
            **self._metrics,
            "state": self._state.value,
            "uptime": self._calculate_uptime(),
        }

    async def _set_state(self, new_state: AgentState) -> None:
        """Set agent state and notify hooks"""
        async with self._state_lock:
            old_state = self._state
            self._state = new_state
            self.logger.debug(f"State changed: {old_state.value} -> {new_state.value}")

            # Notify state change hooks
            for hook in self._on_state_change_hooks:
                try:
                    if asyncio.iscoroutinefunction(hook):
                        await hook(old_state, new_state)
                    else:
                        hook(old_state, new_state)
                except Exception as e:
                    self.logger.error(f"Error in state change hook: {e}")

    def _calculate_uptime(self) -> Optional[float]:
        """Calculate agent uptime in seconds"""
        if self._metrics["start_time"]:
            return (datetime.now() - self._metrics["start_time"]).total_seconds()
        return None

    # ==================== Lifecycle Methods ====================

    async def start(self) -> None:
        """
        Start the agent.

        This method:
        1. Transitions state to INITIALIZING
        2. Calls user-defined initialize()
        3. Initializes core components (registration, communication, discovery)
        4. Registers with platform nodes
        5. Starts background tasks
        6. Transitions to RUNNING
        """
        if self._running:
            self.logger.warning("Agent is already running")
            return

        try:
            await self._set_state(AgentState.INITIALIZING)
            self._metrics["start_time"] = datetime.now()

            # User-defined initialization
            self.logger.info(f"Initializing agent: {self.name}")
            await self.initialize()

            # Initialize core components
            await self._initialize_components()

            # Auto-register if enabled
            if self.config.auto_register:
                await self._registration_manager.register()

            # Start background tasks
            self._running = True
            self._start_background_tasks()

            await self._set_state(AgentState.RUNNING)
            self._ready_event.set()

            self.logger.info(f"Agent {self.name} started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start agent: {e}")
            self._metrics["errors"] += 1
            await self._set_state(AgentState.ERROR)
            await self._handle_error(e, "start")
            raise

    async def stop(self) -> None:
        """
        Stop the agent gracefully.

        This method:
        1. Transitions to STOPPING
        2. Stops background tasks
        3. Unregisters from platform
        4. Calls user-defined shutdown()
        5. Cleans up resources
        6. Transitions to STOPPED
        """
        if not self._running:
            return

        try:
            await self._set_state(AgentState.STOPPING)
            self._running = False

            # Stop background tasks
            await self._stop_background_tasks()

            # Unregister
            if self._registration_manager:
                await self._registration_manager.unregister()

            # Cleanup components
            if self._communication_manager:
                await self._communication_manager.close()
            if self._discovery_manager:
                await self._discovery_manager.close()

            # User-defined shutdown
            self.logger.info(f"Shutting down agent: {self.name}")
            await self.shutdown()

            await self._set_state(AgentState.STOPPED)
            self.logger.info(f"Agent {self.name} stopped")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
            self._metrics["errors"] += 1
            await self._set_state(AgentState.ERROR)
            raise

    async def restart(self) -> None:
        """Restart the agent"""
        self.logger.info(f"Restarting agent: {self.name}")
        await self.stop()
        await self.start()

    async def start_with_http(
        self,
        host: str = "0.0.0.0",
        port: int = 5001,
        platform_url: str = "http://localhost:8000",
        cors_origins: list = None,
    ) -> "HTTPServer":
        """
        Start the agent with HTTP REST server.

        This method starts the agent and initializes an HTTP server
        for REST API access.

        Args:
            host: HTTP server host address
            port: HTTP server port
            platform_url: Platform API URL for registration
            cors_origins: List of allowed CORS origins

        Returns:
            HTTPServer instance

        Example:
            agent = MyAgent(config)
            http_server = await agent.start_with_http(port=5001)
            # Agent is now accessible via HTTP REST API
        """
        from usmsb_sdk.agent_sdk.http_server import HTTPServer

        # Start the agent first
        await self.start()

        # Create and start HTTP server
        self._http_server = HTTPServer(
            agent=self,
            host=host,
            port=port,
            platform_url=platform_url,
            cors_origins=cors_origins,
        )

        await self._http_server.start()

        self.logger.info(f"Agent {self.name} started with HTTP server on port {port}")
        self.logger.info(f"  Health endpoint: http://{host}:{port}/health")
        self.logger.info(f"  Invoke endpoint: http://{host}:{port}/invoke")

        return self._http_server

    async def stop_http(self) -> None:
        """Stop the HTTP server if running"""
        if hasattr(self, "_http_server") and self._http_server:
            await self._http_server.stop()
            self._http_server = None
            self.logger.info(f"HTTP server stopped for {self.name}")

    async def pause(self) -> None:
        """Pause the agent (stop processing but keep connections)"""
        if self._state == AgentState.RUNNING:
            await self._set_state(AgentState.PAUSED)
            self.logger.info(f"Agent {self.name} paused")

    async def resume(self) -> None:
        """Resume a paused agent"""
        if self._state == AgentState.PAUSED:
            await self._set_state(AgentState.RUNNING)
            self.logger.info(f"Agent {self.name} resumed")

    # ==================== Abstract Methods ====================

    @abstractmethod
    async def initialize(self) -> None:
        """
        User-defined initialization logic.

        Override this method to:
        - Load resources
        - Setup connections
        - Initialize internal state
        - Register custom handlers
        """
        pass

    @abstractmethod
    async def handle_message(self, message: Message, session: Optional[Session] = None) -> Optional[Message]:
        """
        Handle incoming messages.

        Args:
            message: The incoming message
            session: Optional session context

        Returns:
            Optional response message
        """
        pass

    @abstractmethod
    async def execute_skill(self, skill_name: str, params: Dict[str, Any]) -> Any:
        """
        Execute a skill by name.

        Args:
            skill_name: Name of the skill to execute
            params: Parameters for the skill

        Returns:
            Skill execution result

        Raises:
            ValueError: If skill not found
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        User-defined cleanup logic.

        Override this method to:
        - Save state
        - Close connections
        - Release resources
        """
        pass

    # ==================== Component Initialization ====================

    async def _initialize_components(self) -> None:
        """Initialize core components"""
        # Initialize registration manager
        self._registration_manager = RegistrationManager(
            agent_id=self.agent_id,
            agent_config=self.config,
            logger=self.logger,
        )

        # Initialize communication manager
        self._communication_manager = CommunicationManager(
            agent_id=self.agent_id,
            agent_config=self.config,
            logger=self.logger,
            message_handler=self._handle_internal_message,
        )
        await self._communication_manager.initialize()

        # Initialize discovery manager
        self._discovery_manager = DiscoveryManager(
            agent_id=self.agent_id,
            agent_config=self.config,
            communication_manager=self._communication_manager,
            logger=self.logger,
        )
        await self._discovery_manager.initialize()

        # Initialize platform integration
        await self._initialize_platform_integration()

    async def _initialize_platform_integration(self) -> None:
        """Initialize platform integration components"""
        # Get platform URL from config
        self._platform_url = (
            self.config.network.platform_endpoints[0]
            if self.config.network.platform_endpoints
            else "http://localhost:8000"
        )

        # Initialize platform client
        self._platform_client = PlatformClient(
            platform_url=self._platform_url,
            api_key=self.config.security.api_key,
            agent_id=self.agent_id,
            logger=self.logger,
        )

        # Initialize marketplace manager
        self._marketplace = MarketplaceManager(
            platform_client=self._platform_client,
            logger=self.logger,
        )

        # Initialize wallet manager
        self._wallet = WalletManager(
            platform_client=self._platform_client,
            logger=self.logger,
        )

        # Initialize negotiation manager
        self._negotiation = NegotiationManager(
            platform_client=self._platform_client,
            agent_id=self.agent_id,
            logger=self.logger,
        )

        # Initialize collaboration manager
        self._collaboration = CollaborationManager(
            platform_client=self._platform_client,
            agent_id=self.agent_id,
            logger=self.logger,
        )

        # Initialize workflow manager
        self._workflow = WorkflowManager(
            platform_client=self._platform_client,
            agent_id=self.agent_id,
            logger=self.logger,
        )

        # Initialize learning manager
        self._learning = LearningManager(
            platform_client=self._platform_client,
            agent_id=self.agent_id,
            logger=self.logger,
        )

        self.logger.info("Platform integration components initialized")

    # ==================== Background Tasks ====================

    def _start_background_tasks(self) -> None:
        """Start all background tasks"""
        # Heartbeat task
        if self.config.heartbeat_interval > 0:
            task = create_task(self._heartbeat_loop())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        # Health check task
        if self.config.health_check_interval > 0:
            task = create_task(self._health_check_loop())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

        # Discovery task
        if self.config.auto_discover and self.config.network.discovery_interval > 0:
            task = create_task(self._discovery_loop())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def _stop_background_tasks(self) -> None:
        """Stop all background tasks"""
        for task in self._background_tasks:
            task.cancel()

        if self._background_tasks:
            await gather(*self._background_tasks, return_exceptions=True)

        self._background_tasks.clear()

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats"""
        while self._running:
            try:
                if self._registration_manager:
                    await self._registration_manager.send_heartbeat()
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")

            await sleep(self.config.heartbeat_interval)

    async def _health_check_loop(self) -> None:
        """Periodic health checks"""
        while self._running:
            try:
                await self._perform_health_check()
            except Exception as e:
                self.logger.error(f"Health check error: {e}")

            await sleep(self.config.health_check_interval)

    async def _discovery_loop(self) -> None:
        """Periodic agent discovery"""
        while self._running:
            try:
                if self._discovery_manager:
                    await self._discovery_manager.refresh_discoveries()
            except Exception as e:
                self.logger.error(f"Discovery error: {e}")

            await sleep(self.config.network.discovery_interval)

    async def _perform_health_check(self) -> Dict[str, Any]:
        """Perform internal health check"""
        health = {
            "status": "healthy",
            "state": self._state.value,
            "timestamp": datetime.now().isoformat(),
            "checks": {},
        }

        # Check registration status
        if self._registration_manager:
            health["checks"]["registration"] = self._registration_manager.status.value

        # Check communication channels
        if self._communication_manager:
            health["checks"]["communication"] = await self._communication_manager.health_check()

        # Check P2P connections
        if self._communication_manager:
            health["checks"]["p2p_connections"] = len(self._communication_manager.p2p_connections)

        return health

    # ==================== Message Handling ====================

    async def _handle_internal_message(self, message: Message, session: Optional[Session] = None) -> Optional[Message]:
        """Internal message handler with hooks and metrics"""
        self._metrics["messages_received"] += 1
        self._metrics["last_activity"] = datetime.now()

        # Notify message hooks
        for hook in self._on_message_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(message, session)
                else:
                    hook(message, session)
            except Exception as e:
                self.logger.error(f"Error in message hook: {e}")

        # Check for registered handlers
        handler = self._message_handlers.get(message.type.value if hasattr(message.type, 'value') else message.type)
        if handler:
            try:
                return await handler(message, session)
            except Exception as e:
                self.logger.error(f"Handler error for {message.type}: {e}")
                raise

        # Delegate to user handler
        try:
            return await self.handle_message(message, session)
        except Exception as e:
            self._metrics["errors"] += 1
            await self._handle_error(e, f"message handling: {message.type}")
            raise

    # ==================== Skill Management ====================

    def register_skill(self, skill: SkillDefinition, handler: Optional[Callable] = None) -> None:
        """Register a skill with optional handler"""
        self._skills[skill.name] = skill
        if handler:
            self._skill_handlers[skill.name] = handler
        self.logger.info(f"Registered skill: {skill.name}")

    def unregister_skill(self, skill_name: str) -> None:
        """Unregister a skill"""
        if skill_name in self._skills:
            del self._skills[skill_name]
            self._skill_handlers.pop(skill_name, None)
            self.logger.info(f"Unregistered skill: {skill_name}")

    async def call_skill(self, skill_name: str, params: Dict[str, Any] = None) -> Any:
        """Execute a skill by name"""
        params = params or {}

        if skill_name not in self._skills:
            raise ValueError(f"Unknown skill: {skill_name}")

        skill = self._skills[skill_name]

        # Check if deprecated
        if skill.deprecated:
            self.logger.warning(f"Using deprecated skill: {skill_name}")

        # Validate parameters
        self._validate_skill_params(skill, params)

        self._metrics["skills_executed"] += 1
        self._metrics["last_activity"] = datetime.now()

        # Notify skill hooks
        for hook in self._on_skill_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(skill_name, params)
                else:
                    hook(skill_name, params)
            except Exception as e:
                self.logger.error(f"Error in skill hook: {e}")

        # Check for registered handler
        handler = self._skill_handlers.get(skill_name)
        if handler:
            try:
                if asyncio.iscoroutinefunction(handler):
                    return await handler(params)
                else:
                    return handler(params)
            except Exception as e:
                self._metrics["errors"] += 1
                raise

        # Delegate to user implementation
        return await self.execute_skill(skill_name, params)

    def _validate_skill_params(self, skill: SkillDefinition, params: Dict[str, Any]) -> None:
        """Validate skill parameters against definition"""
        for param in skill.parameters:
            if param.required and param.name not in params:
                raise ValueError(f"Missing required parameter: {param.name}")

            if param.name in params:
                value = params[param.name]

                # Type validation
                if param.type == "integer" and not isinstance(value, int):
                    raise TypeError(f"Parameter {param.name} must be an integer")
                elif param.type == "float" and not isinstance(value, (int, float)):
                    raise TypeError(f"Parameter {param.name} must be a number")
                elif param.type == "boolean" and not isinstance(value, bool):
                    raise TypeError(f"Parameter {param.name} must be a boolean")
                elif param.type == "string" and not isinstance(value, str):
                    raise TypeError(f"Parameter {param.name} must be a string")

                # Range validation
                if param.min_value is not None and value < param.min_value:
                    raise ValueError(f"Parameter {param.name} must be >= {param.min_value}")
                if param.max_value is not None and value > param.max_value:
                    raise ValueError(f"Parameter {param.name} must be <= {param.max_value}")

                # Enum validation
                if param.enum and value not in param.enum:
                    raise ValueError(f"Parameter {param.name} must be one of {param.enum}")

                # Pattern validation
                if param.pattern and isinstance(value, str):
                    import re
                    if not re.match(param.pattern, value):
                        raise ValueError(f"Parameter {param.name} does not match pattern {param.pattern}")

    # ==================== Capability Management ====================

    def add_capability(self, capability: CapabilityDefinition) -> None:
        """Add a capability"""
        self._capabilities[capability.name] = capability
        self.logger.info(f"Added capability: {capability.name}")

    def remove_capability(self, capability_name: str) -> None:
        """Remove a capability"""
        if capability_name in self._capabilities:
            del self._capabilities[capability_name]
            self.logger.info(f"Removed capability: {capability_name}")

    def has_capability(self, capability_name: str) -> bool:
        """Check if agent has a specific capability"""
        return capability_name in self._capabilities

    def get_capability(self, capability_name: str) -> Optional[CapabilityDefinition]:
        """Get capability by name"""
        return self._capabilities.get(capability_name)

    # ==================== Communication ====================

    async def send_message(
        self,
        target_id: str,
        content: Any,
        message_type: MessageType = MessageType.REQUEST,
        protocol: Optional[ProtocolType] = None,
        use_p2p: bool = False,
        **kwargs,
    ) -> Optional[Message]:
        """
        Send a message to another agent.

        Args:
            target_id: Target agent ID
            content: Message content
            message_type: Type of message
            protocol: Preferred protocol (auto-select if None)
            use_p2p: Whether to use P2P direct connection
            **kwargs: Additional message attributes

        Returns:
            Response message if request/response pattern
        """
        if not self._communication_manager:
            raise RuntimeError("Communication manager not initialized")

        message = Message(
            type=message_type,
            sender_id=self.agent_id,
            receiver_id=target_id,
            content=content,
            **kwargs,
        )

        self._metrics["messages_sent"] += 1

        if use_p2p:
            return await self._communication_manager.send_p2p(message, target_id)
        else:
            return await self._communication_manager.send(message, protocol)

    async def broadcast(
        self,
        content: Any,
        filter_criteria: Optional[DiscoveryFilter] = None,
        protocol: Optional[ProtocolType] = None,
    ) -> List[Message]:
        """
        Broadcast a message to multiple agents.

        Args:
            content: Message content
            filter_criteria: Filter for target agents
            protocol: Preferred protocol

        Returns:
            List of response messages
        """
        if not self._communication_manager:
            raise RuntimeError("Communication manager not initialized")

        # Discover agents matching filter
        if filter_criteria and self._discovery_manager:
            agents = await self._discovery_manager.discover(filter_criteria)
            target_ids = [a.agent_id for a in agents]
        else:
            # Broadcast to all known agents
            target_ids = await self._discovery_manager.get_all_agent_ids() if self._discovery_manager else []

        # Send to all targets
        tasks = [
            self.send_message(
                target_id=target_id,
                content=content,
                message_type=MessageType.BROADCAST,
                protocol=protocol,
            )
            for target_id in target_ids
        ]

        responses = await gather(*tasks, return_exceptions=True)
        return [r for r in responses if isinstance(r, Message)]

    # ==================== Discovery ====================

    async def discover_agents(
        self,
        filter_criteria: Optional[DiscoveryFilter] = None,
    ) -> List[AgentInfo]:
        """
        Discover agents matching criteria.

        Args:
            filter_criteria: Filter for discovery

        Returns:
            List of matching agents
        """
        if not self._discovery_manager:
            raise RuntimeError("Discovery manager not initialized")

        return await self._discovery_manager.discover(filter_criteria)

    async def discover_by_skill(self, skill_name: str) -> List[AgentInfo]:
        """Discover agents with a specific skill"""
        if not self._discovery_manager:
            raise RuntimeError("Discovery manager not initialized")

        return await self._discovery_manager.discover_by_skill(skill_name)

    async def discover_by_capability(self, capability_name: str) -> List[AgentInfo]:
        """Discover agents with a specific capability"""
        if not self._discovery_manager:
            raise RuntimeError("Discovery manager not initialized")

        return await self._discovery_manager.discover_by_capability(capability_name)

    async def get_recommended_agents(
        self,
        task_description: str,
        limit: int = 5,
    ) -> List[AgentInfo]:
        """Get recommended agents for a task"""
        if not self._discovery_manager:
            raise RuntimeError("Discovery manager not initialized")

        return await self._discovery_manager.get_recommendations(task_description, limit)

    # ==================== P2P Connection ====================

    async def establish_p2p(self, target_id: str) -> bool:
        """
        Establish a P2P connection with another agent.

        Args:
            target_id: Target agent ID

        Returns:
            True if connection established successfully
        """
        if not self._communication_manager:
            raise RuntimeError("Communication manager not initialized")

        return await self._communication_manager.establish_p2p(target_id)

    async def close_p2p(self, target_id: str) -> None:
        """Close P2P connection with an agent"""
        if self._communication_manager:
            await self._communication_manager.close_p2p(target_id)

    def get_p2p_connections(self) -> List[str]:
        """Get list of active P2P connections"""
        if self._communication_manager:
            return list(self._communication_manager.p2p_connections.keys())
        return []

    # ==================== Event Hooks ====================

    def on_state_change(self, hook: Callable) -> None:
        """Register a state change hook"""
        self._on_state_change_hooks.append(hook)

    def on_message(self, hook: Callable) -> None:
        """Register a message hook"""
        self._on_message_hooks.append(hook)

    def on_skill(self, hook: Callable) -> None:
        """Register a skill execution hook"""
        self._on_skill_hooks.append(hook)

    def on_error(self, hook: Callable) -> None:
        """Register an error hook"""
        self._on_error_hooks.append(hook)

    async def _handle_error(self, error: Exception, context: str) -> None:
        """Handle errors with hooks"""
        self.logger.error(f"Error in {context}: {error}")

        for hook in self._on_error_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(error, context)
                else:
                    hook(error, context)
            except Exception as e:
                self.logger.error(f"Error in error hook: {e}")

    # ==================== Registration Info ====================

    async def get_registration_status(self) -> RegistrationStatus:
        """Get current registration status"""
        if self._registration_manager:
            return self._registration_manager.status
        return RegistrationStatus.NOT_REGISTERED

    async def get_registered_protocols(self) -> List[ProtocolType]:
        """Get list of registered protocols"""
        if self._registration_manager:
            return self._registration_manager.registered_protocols
        return []

    # ==================== Serialization ====================

    def to_dict(self) -> Dict[str, Any]:
        """Convert agent info to dictionary"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "state": self._state.value,
            "skills": [s.to_dict() for s in self.skills],
            "capabilities": [c.to_dict() for c in self.capabilities],
            "metrics": self.metrics,
            "protocols": [p.value for p in self.config.get_enabled_protocols()],
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.agent_id}, name={self.name}, state={self._state.value})>"

    # ==================== Platform Integration ====================

    @property
    def platform(self) -> Optional[PlatformClient]:
        """Get platform client"""
        return self._platform_client

    @property
    def marketplace(self) -> Optional[MarketplaceManager]:
        """Get marketplace manager"""
        return self._marketplace

    @property
    def wallet(self) -> Optional[WalletManager]:
        """Get wallet manager"""
        return self._wallet

    @property
    def negotiation(self) -> Optional[NegotiationManager]:
        """Get negotiation manager"""
        return self._negotiation

    @property
    def collaboration(self) -> Optional[CollaborationManager]:
        """Get collaboration manager"""
        return self._collaboration

    @property
    def workflow(self) -> Optional[WorkflowManager]:
        """Get workflow manager"""
        return self._workflow

    @property
    def learning(self) -> Optional[LearningManager]:
        """Get learning manager"""
        return self._learning

    # --- Registration ---

    async def register_to_platform(self) -> RegistrationResult:
        """
        Register agent to the platform.

        Returns:
            RegistrationResult with status
        """
        if not self._platform_client:
            raise RuntimeError("Platform client not initialized")

        return await self._platform_client.register(
            name=self.name,
            agent_type="ai_agent",
            capabilities=[c.name for c in self.capabilities],
            skills=[s.to_dict() for s in self.skills],
            endpoint=self._get_endpoint(),
            protocol="standard",
            description=self.description,
        )

    async def unregister_from_platform(self) -> bool:
        """Unregister from platform"""
        if self._platform_client:
            return await self._platform_client.unregister()
        return False

    async def send_platform_heartbeat(self, status: str = "online") -> bool:
        """Send heartbeat to platform"""
        if self._platform_client:
            return await self._platform_client.send_heartbeat(status)
        return False

    # --- Service Management ---

    async def offer_service(self, service_def: ServiceDefinition) -> Optional[Service]:
        """
        Publish a service to the marketplace.

        Args:
            service_def: Service definition

        Returns:
            Published Service or None
        """
        if not self._marketplace:
            raise RuntimeError("Marketplace not initialized")
        return await self._marketplace.publish_service(service_def)

    async def update_service(self, service_id: str, **updates) -> bool:
        """Update a published service"""
        if self._marketplace:
            return await self._marketplace.update_service(service_id, **updates)
        return False

    async def stop_service(self, service_id: str) -> bool:
        """Stop offering a service"""
        if self._marketplace:
            return await self._marketplace.unpublish_service(service_id)
        return False

    async def list_my_services(self) -> List[Service]:
        """List my published services"""
        if self._marketplace:
            return await self._marketplace.list_my_services()
        return []

    # --- Demand Management ---

    async def request_service(self, demand_def: DemandDefinition) -> Optional[Demand]:
        """
        Publish a service request/demand.

        Args:
            demand_def: Demand definition

        Returns:
            Published Demand or None
        """
        if not self._marketplace:
            raise RuntimeError("Marketplace not initialized")
        return await self._marketplace.publish_demand(demand_def)

    async def cancel_demand(self, demand_id: str) -> bool:
        """Cancel a published demand"""
        if self._marketplace:
            return await self._marketplace.cancel_demand(demand_id)
        return False

    async def list_my_demands(self) -> List[Demand]:
        """List my published demands"""
        if self._marketplace:
            return await self._marketplace.list_my_demands()
        return []

    # --- Matching & Opportunities ---

    async def find_work(self, capabilities: Optional[List[str]] = None) -> List[Opportunity]:
        """
        Find work opportunities matching agent's capabilities.

        Args:
            capabilities: Specific capabilities to match (uses own if None)

        Returns:
            List of matching opportunities
        """
        if not self._marketplace:
            raise RuntimeError("Marketplace not initialized")

        if capabilities is None:
            capabilities = [c.name for c in self.capabilities]

        return await self._marketplace.find_work(capabilities)

    async def find_workers(
        self,
        required_skills: List[str],
        budget_range: Optional[tuple] = None,
    ) -> List[Opportunity]:
        """
        Find workers/suppliers for a task.

        Args:
            required_skills: Required skills
            budget_range: (min, max) budget

        Returns:
            List of matching suppliers
        """
        if not self._marketplace:
            raise RuntimeError("Marketplace not initialized")

        return await self._marketplace.find_workers(required_skills, budget_range)

    async def get_opportunities(self) -> List[Opportunity]:
        """Get all available opportunities"""
        if self._marketplace:
            return await self._marketplace.get_all_opportunities()
        return []

    # --- Negotiation ---

    async def negotiate(
        self,
        opportunity_id: str,
    ) -> Optional[NegotiationSession]:
        """
        Start negotiating for an opportunity.

        Args:
            opportunity_id: Opportunity to negotiate

        Returns:
            NegotiationSession
        """
        if not self._negotiation:
            raise RuntimeError("Negotiation manager not initialized")

        # Get opportunity details
        opportunity = None
        if self._marketplace:
            opportunity = await self._marketplace.get_opportunity(opportunity_id)

        if not opportunity:
            self.logger.error(f"Opportunity not found: {opportunity_id}")
            return None

        # Initiate negotiation
        return await self._negotiation.negotiate(
            counterpart_id=opportunity.counterpart_id,
            task_description=opportunity.details.get("description", ""),
            initial_terms=NegotiationTerms(price=opportunity.details.get("price", 100)),
            demand_id=opportunity.details.get("id") if opportunity.type == "demand" else None,
            service_id=opportunity.details.get("id") if opportunity.type == "supply" else None,
        )

    async def propose_terms(
        self,
        session_id: str,
        terms: NegotiationTerms,
    ) -> ProposalResult:
        """Submit a proposal in negotiation"""
        if self._negotiation:
            return await self._negotiation.propose(session_id, terms)
        return ProposalResult(success=False, session=None, message="Negotiation manager not initialized")

    async def accept_deal(self, session_id: str) -> ProposalResult:
        """Accept current proposal and close deal"""
        if self._negotiation:
            return await self._negotiation.accept(session_id)
        return ProposalResult(success=False, session=None, message="Negotiation manager not initialized")

    async def reject_deal(self, session_id: str, reason: str = "") -> ProposalResult:
        """Reject current proposal"""
        if self._negotiation:
            return await self._negotiation.reject(session_id, reason)
        return ProposalResult(success=False, session=None, message="Negotiation manager not initialized")

    # --- Collaboration ---

    async def start_collaboration(
        self,
        goal: str,
        required_skills: List[str],
        mode: str = "parallel",
    ) -> Optional[CollaborationSession]:
        """
        Start a multi-agent collaboration.

        Args:
            goal: Goal description
            required_skills: Skills needed
            mode: Collaboration mode

        Returns:
            CollaborationSession
        """
        if not self._collaboration:
            raise RuntimeError("Collaboration manager not initialized")

        return await self._collaboration.start_collaboration(goal, required_skills, mode)

    async def join_collaboration(
        self,
        session_id: str,
        role: str = "support",
    ) -> bool:
        """Join an existing collaboration"""
        if self._collaboration:
            return await self._collaboration.join(session_id, role)
        return False

    async def contribute(
        self,
        session_id: str,
        output: Any,
        role: Optional[str] = None,
    ) -> bool:
        """Submit contribution to collaboration"""
        if self._collaboration:
            return await self._collaboration.contribute(session_id, output, role)
        return False

    async def list_collaborations(self) -> List[CollaborationSession]:
        """List active collaborations"""
        if self._collaboration:
            return await self._collaboration.list_active()
        return []

    # --- Workflow ---

    async def plan_workflow(
        self,
        task: str,
        tools: Optional[List[str]] = None,
    ) -> Optional[Workflow]:
        """
        Create a workflow for a task.

        Args:
            task: Task description
            tools: Available tools

        Returns:
            Workflow
        """
        if not self._workflow:
            raise RuntimeError("Workflow manager not initialized")

        return await self._workflow.create(task, tools)

    async def run_workflow(self, workflow_id: str) -> Optional[WorkflowResult]:
        """Execute a workflow"""
        if self._workflow:
            return await self._workflow.execute(workflow_id)
        return None

    async def run_task(self, task: str, tools: Optional[List[str]] = None) -> Optional[WorkflowResult]:
        """
        Convenience: Create and run a workflow in one call.

        Args:
            task: Task description
            tools: Available tools

        Returns:
            WorkflowResult
        """
        if self._workflow:
            return await self._workflow.run(task, tools)
        return None

    # --- Wallet ---

    async def get_balance(self) -> Optional[WalletBalance]:
        """Get wallet balance"""
        if self._wallet:
            return await self._wallet.get_balance()
        return None

    async def stake_tokens(self, amount: float) -> StakeResult:
        """
        Stake tokens to increase reputation.

        Args:
            amount: Amount to stake

        Returns:
            StakeResult
        """
        if not self._wallet:
            raise RuntimeError("Wallet manager not initialized")
        return await self._wallet.stake(amount)

    async def unstake_tokens(self, amount: float) -> StakeResult:
        """Unstake tokens"""
        if self._wallet:
            return await self._wallet.unstake(amount)
        return StakeResult(success=False, amount=amount, total_staked=0, new_reputation=0.5, message="Wallet not initialized")

    async def get_stake_info(self) -> Optional[StakeInfo]:
        """Get stake information"""
        if self._wallet:
            return await self._wallet.get_stake_info()
        return None

    # --- Learning ---

    async def get_insights(self) -> List[LearningInsight]:
        """Get learning insights"""
        if self._learning:
            return await self._learning.get_insights()
        return []

    async def analyze_performance(self) -> Optional[PerformanceAnalysis]:
        """Analyze own performance"""
        if self._learning:
            return await self._learning.analyze_performance()
        return None

    async def optimize_strategy(self) -> Optional[Dict[str, Any]]:
        """Get optimized matching strategy"""
        if self._learning:
            strategy = await self._learning.get_optimized_strategy()
            return {
                "optimal_price_range": strategy.optimal_price_range,
                "best_contact_timing": strategy.best_contact_timing,
                "focus_capabilities": strategy.focus_capabilities,
                "negotiation_approach": strategy.negotiation_approach,
            }
        return None

    async def analyze_market(self) -> Optional[MarketInsights]:
        """Get market insights"""
        if self._learning:
            return await self._learning.get_market_insights()
        return None

    async def report_experience(
        self,
        experience_type: str,
        outcome: str,
        details: Dict[str, Any],
        lessons: Optional[List[str]] = None,
    ) -> bool:
        """
        Report an experience for learning.

        Args:
            experience_type: Type (transaction, negotiation, collaboration)
            outcome: Result (success, failure, partial)
            details: Experience details
            lessons: Lessons learned

        Returns:
            True if reported
        """
        if self._learning:
            from usmsb_sdk.agent_sdk.learning import Experience
            experience = Experience(
                experience_type=experience_type,
                outcome=outcome,
                details=details,
                lessons_learned=lessons or [],
            )
            return await self._learning.report_experience(experience)
        return False

    # --- Utility ---

    def _get_endpoint(self) -> str:
        """Get agent's HTTP endpoint"""
        http_config = self.config.protocols.get(ProtocolType.HTTP)
        if http_config:
            host = http_config.host or "localhost"
            port = http_config.port or 5001
            return f"http://{host}:{port}"
        return ""
