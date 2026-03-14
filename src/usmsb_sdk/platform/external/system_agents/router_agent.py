"""
Router Agent Module

Provides message routing and load balancing capabilities including:
    - Intelligent message routing between agents
    - Load balancing across multiple targets
    - Request queue management
    - Route configuration and monitoring

Skills:
    - route: Route a message to appropriate target(s)
    - balance: Get load balancing status and statistics
    - queue_status: Get request queue status
    - get_routes: Get configured routing information
"""

import asyncio
import random
from datetime import datetime
from enum import Enum
from typing import Any

from usmsb_sdk.agent_sdk.agent_config import (
    AgentConfig,
    CapabilityDefinition,
    SkillDefinition,
    SkillParameter,
)
from usmsb_sdk.agent_sdk.communication import Message, MessageType, Session
from usmsb_sdk.platform.external.system_agents.base_system_agent import (
    BaseSystemAgent,
    SystemAgentConfig,
)


class LoadBalanceStrategy(Enum):
    """Load balancing strategies"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    RANDOM = "random"
    LEAST_RESPONSE_TIME = "least_response_time"
    CONSISTENT_HASH = "consistent_hash"


class RouteStatus(Enum):
    """Route status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"


class QueuedRequest:
    """Represents a queued routing request"""

    def __init__(
        self,
        request_id: str,
        message: Message,
        target_agents: list[str],
        priority: int = 0,
    ):
        self.request_id = request_id
        self.message = message
        self.target_agents = target_agents
        self.priority = priority
        self.created_at = datetime.now()
        self.started_at: datetime | None = None
        self.completed_at: datetime | None = None
        self.status = "pending"
        self.result: Any | None = None
        self.error: str | None = None

    @property
    def wait_time(self) -> float:
        """Get time spent waiting in queue (seconds)"""
        if self.started_at:
            return (self.started_at - self.created_at).total_seconds()
        return (datetime.now() - self.created_at).total_seconds()

    @property
    def processing_time(self) -> float | None:
        """Get processing time (seconds)"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "request_id": self.request_id,
            "message_type": self.message.type.value if hasattr(self.message.type, 'value') else str(self.message.type),
            "target_agents": self.target_agents,
            "priority": self.priority,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status,
            "wait_time": self.wait_time,
            "processing_time": self.processing_time,
            "error": self.error,
        }


class RouteTarget:
    """Represents a routing target (agent)"""

    def __init__(
        self,
        agent_id: str,
        weight: int = 1,
        max_connections: int = 100,
    ):
        self.agent_id = agent_id
        self.weight = weight
        self.max_connections = max_connections
        self.active_connections = 0
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_response_time = 0.0
        self.last_request_time: datetime | None = None
        self.status = RouteStatus.ACTIVE

    @property
    def current_load(self) -> float:
        """Get current load percentage"""
        if self.max_connections == 0:
            return 100.0
        return (self.active_connections / self.max_connections) * 100

    @property
    def success_rate(self) -> float:
        """Get success rate"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests

    @property
    def average_response_time(self) -> float:
        """Get average response time in ms"""
        if self.successful_requests == 0:
            return 0.0
        return self.total_response_time / self.successful_requests

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "agent_id": self.agent_id,
            "weight": self.weight,
            "max_connections": self.max_connections,
            "active_connections": self.active_connections,
            "current_load": self.current_load,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.success_rate,
            "average_response_time_ms": self.average_response_time,
            "status": self.status.value,
        }


class Route:
    """Represents a routing configuration"""

    def __init__(
        self,
        route_id: str,
        name: str,
        pattern: str,
        targets: list[RouteTarget],
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
        enabled: bool = True,
    ):
        self.route_id = route_id
        self.name = name
        self.pattern = pattern  # Pattern to match message types or content
        self.targets = {t.agent_id: t for t in targets}
        self.strategy = strategy
        self.enabled = enabled
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # Round-robin index
        self._rr_index = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "route_id": self.route_id,
            "name": self.name,
            "pattern": self.pattern,
            "targets": [t.to_dict() for t in self.targets.values()],
            "strategy": self.strategy.value,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class RouterAgent(BaseSystemAgent):
    """
    Message routing and load balancing agent.

    This agent provides intelligent message routing services including:
    - Pattern-based message routing
    - Multiple load balancing strategies
    - Request queue management
    - Performance monitoring for routes

    Skills:
        - route: Route a message to appropriate target(s)
        - balance: Get load balancing status
        - queue_status: Get queue status
        - get_routes: Get routing configuration

    Example:
        config = AgentConfig(
            agent_id="router-001",
            name="MessageRouter",
            # ... other config
        )
        router = RouterAgent(config)
        await router.start()

        # Route a message
        result = await router.call_skill("route", {
            "message_type": "task_request",
            "content": {"task": "process_data"},
            "strategy": "least_connections"
        })
    """

    SYSTEM_AGENT_TYPE = "router"

    def __init__(
        self,
        config: AgentConfig,
        system_config: SystemAgentConfig | None = None,
    ):
        """Initialize the router agent"""
        super().__init__(config, system_config)

        # Routes configuration
        self._routes: dict[str, Route] = {}
        self._default_strategy = LoadBalanceStrategy.LEAST_CONNECTIONS

        # Request queue
        self._request_queue: list[QueuedRequest] = []
        self._active_requests: dict[str, QueuedRequest] = {}
        self._completed_requests: list[QueuedRequest] = []
        self._request_counter = 0
        self._max_queue_size = 1000
        self._max_concurrent_requests = 100

        # Queue processing
        self._queue_lock = asyncio.Lock()
        self._processing = False

        # Statistics
        self._stats = {
            "total_routed": 0,
            "successful_routes": 0,
            "failed_routes": 0,
            "total_queued": 0,
            "queue_timeouts": 0,
        }

        # Register router skills
        self._register_router_skills()

    def _register_router_skills(self) -> None:
        """Register router skills"""
        skills = [
            SkillDefinition(
                name="route",
                description="Route a message to appropriate target(s)",
                parameters=[
                    SkillParameter(
                        name="message_type",
                        type="string",
                        description="Type of message to route",
                        required=True,
                    ),
                    SkillParameter(
                        name="content",
                        type="object",
                        description="Message content",
                        required=True,
                    ),
                    SkillParameter(
                        name="target_pattern",
                        type="string",
                        description="Pattern to match route",
                        required=False,
                    ),
                    SkillParameter(
                        name="strategy",
                        type="string",
                        description="Load balancing strategy",
                        required=False,
                        default="least_connections",
                        enum=["round_robin", "least_connections", "weighted", "random", "least_response_time"],
                    ),
                    SkillParameter(
                        name="targets",
                        type="array",
                        description="Specific target agent IDs (optional)",
                        required=False,
                    ),
                    SkillParameter(
                        name="priority",
                        type="integer",
                        description="Request priority (higher = more urgent)",
                        required=False,
                        default=0,
                    ),
                    SkillParameter(
                        name="queue",
                        type="boolean",
                        description="Whether to queue if no targets available",
                        required=False,
                        default=True,
                    ),
                ],
                returns="dict",
                tags=["routing", "messaging"],
            ),
            SkillDefinition(
                name="balance",
                description="Get load balancing status and statistics",
                parameters=[
                    SkillParameter(
                        name="route_id",
                        type="string",
                        description="Specific route ID (optional)",
                        required=False,
                    ),
                    SkillParameter(
                        name="agent_id",
                        type="string",
                        description="Specific agent ID (optional)",
                        required=False,
                    ),
                ],
                returns="dict",
                tags=["monitoring", "load_balancing"],
            ),
            SkillDefinition(
                name="queue_status",
                description="Get request queue status",
                parameters=[
                    SkillParameter(
                        name="include_pending",
                        type="boolean",
                        description="Include pending requests",
                        required=False,
                        default=True,
                    ),
                    SkillParameter(
                        name="include_active",
                        type="boolean",
                        description="Include active requests",
                        required=False,
                        default=True,
                    ),
                    SkillParameter(
                        name="include_completed",
                        type="boolean",
                        description="Include recently completed requests",
                        required=False,
                        default=False,
                    ),
                    SkillParameter(
                        name="limit",
                        type="integer",
                        description="Limit number of results",
                        required=False,
                        default=50,
                    ),
                ],
                returns="dict",
                tags=["monitoring", "queue"],
            ),
            SkillDefinition(
                name="get_routes",
                description="Get configured routing information",
                parameters=[
                    SkillParameter(
                        name="route_id",
                        type="string",
                        description="Specific route ID (optional)",
                        required=False,
                    ),
                    SkillParameter(
                        name="pattern",
                        type="string",
                        description="Filter by pattern",
                        required=False,
                    ),
                    SkillParameter(
                        name="enabled_only",
                        type="boolean",
                        description="Only return enabled routes",
                        required=False,
                        default=True,
                    ),
                ],
                returns="list",
                tags=["configuration", "routing"],
            ),
        ]

        for skill in skills:
            self.register_skill(skill)

    # ==================== Lifecycle Methods ====================

    async def initialize(self) -> None:
        """Initialize the router agent"""
        self.logger.info("Initializing Router Agent")

        # Register capabilities
        capabilities = [
            CapabilityDefinition(
                name="message_routing",
                description="Route messages to appropriate agents",
                version="1.0.0",
            ),
            CapabilityDefinition(
                name="load_balancing",
                description="Balance load across multiple agents",
                version="1.0.0",
            ),
            CapabilityDefinition(
                name="queue_management",
                description="Manage request queues",
                version="1.0.0",
            ),
        ]

        for cap in capabilities:
            self.add_capability(cap)

        # Initialize default routes
        await self._init_default_routes()

        # Start queue processor
        self._processing = True
        asyncio.create_task(self._process_queue_loop())

    async def handle_message(
        self,
        message: Message,
        session: Session | None = None
    ) -> Message | None:
        """Handle incoming messages"""
        await self.audit_operation("message_received", {
            "message_type": message.type.value if hasattr(message.type, 'value') else str(message.type),
            "sender": message.sender_id,
        })

        content = message.content if isinstance(message.content, dict) else {"data": message.content}

        # Handle routing requests
        if content.get("type") == "route_request":
            result = await self._route_message(
                content.get("message_type"),
                content.get("content"),
                content.get("options", {}),
            )
            return Message(
                type=MessageType.RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                content=result,
            )

        return None

    async def execute_skill(self, skill_name: str, params: dict[str, Any]) -> Any:
        """Execute router skills"""
        await self.audit_operation("skill_execution", {
            "skill": skill_name,
        })

        if skill_name == "route":
            return await self._skill_route(params)
        elif skill_name == "balance":
            return await self._skill_balance(params)
        elif skill_name == "queue_status":
            return await self._skill_queue_status(params)
        elif skill_name == "get_routes":
            return await self._skill_get_routes(params)
        else:
            raise ValueError(f"Unknown skill: {skill_name}")

    async def shutdown(self) -> None:
        """Shutdown the router agent"""
        self.logger.info("Shutting down Router Agent")
        self._processing = False

        # Process remaining queue items
        await self._flush_queue()

    # ==================== Skill Implementations ====================

    async def _skill_route(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute route skill"""
        message_type = params.get("message_type")
        content = params.get("content")
        target_pattern = params.get("target_pattern")
        strategy_str = params.get("strategy", "least_connections")
        targets = params.get("targets")
        priority = params.get("priority", 0)
        queue = params.get("queue", True)

        if not message_type or content is None:
            raise ValueError("message_type and content are required")

        # Convert strategy string to enum
        try:
            strategy = LoadBalanceStrategy(strategy_str)
        except ValueError:
            strategy = self._default_strategy

        options = {
            "target_pattern": target_pattern,
            "strategy": strategy,
            "targets": targets,
            "priority": priority,
            "queue": queue,
        }

        return await self._route_message(message_type, content, options)

    async def _skill_balance(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute balance skill"""
        route_id = params.get("route_id")
        agent_id = params.get("agent_id")

        result = {
            "timestamp": datetime.now().isoformat(),
            "strategy": self._default_strategy.value,
            "routes": {},
            "overall": {
                "total_targets": 0,
                "total_connections": 0,
                "total_capacity": 0,
                "average_load": 0.0,
            },
        }

        routes_to_check = [self._routes[route_id]] if route_id else list(self._routes.values())

        total_load = 0.0
        total_connections = 0
        total_capacity = 0

        for route in routes_to_check:
            route_data = route.to_dict()

            if agent_id:
                if agent_id in route.targets:
                    route_data["target"] = route.targets[agent_id].to_dict()
                else:
                    continue

            result["routes"][route.route_id] = route_data

            for target in route.targets.values():
                result["overall"]["total_targets"] += 1
                total_connections += target.active_connections
                total_capacity += target.max_connections
                total_load += target.current_load

        result["overall"]["total_connections"] = total_connections
        result["overall"]["total_capacity"] = total_capacity
        if result["overall"]["total_targets"] > 0:
            result["overall"]["average_load"] = total_load / result["overall"]["total_targets"]

        return result

    async def _skill_queue_status(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute queue_status skill"""
        include_pending = params.get("include_pending", True)
        include_active = params.get("include_active", True)
        include_completed = params.get("include_completed", False)
        limit = params.get("limit", 50)

        result = {
            "timestamp": datetime.now().isoformat(),
            "pending_count": len(self._request_queue),
            "active_count": len(self._active_requests),
            "completed_count": len(self._completed_requests),
            "max_queue_size": self._max_queue_size,
            "max_concurrent": self._max_concurrent_requests,
            "statistics": self._stats,
            "requests": {},
        }

        if include_pending:
            result["requests"]["pending"] = [
                r.to_dict() for r in self._request_queue[:limit]
            ]

        if include_active:
            result["requests"]["active"] = [
                r.to_dict() for r in list(self._active_requests.values())[:limit]
            ]

        if include_completed:
            result["requests"]["completed"] = [
                r.to_dict() for r in self._completed_requests[-limit:]
            ]

        return result

    async def _skill_get_routes(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """Execute get_routes skill"""
        route_id = params.get("route_id")
        pattern = params.get("pattern")
        enabled_only = params.get("enabled_only", True)

        routes = list(self._routes.values())

        if route_id:
            routes = [r for r in routes if r.route_id == route_id]

        if pattern:
            routes = [r for r in routes if pattern in r.pattern]

        if enabled_only:
            routes = [r for r in routes if r.enabled]

        return [r.to_dict() for r in routes]

    # ==================== Internal Methods ====================

    async def _init_default_routes(self) -> None:
        """Initialize default routes"""
        # Default route for all messages
        default_route = Route(
            route_id="default",
            name="Default Route",
            pattern="*",
            targets=[],
            strategy=LoadBalanceStrategy.LEAST_CONNECTIONS,
        )
        self._routes["default"] = default_route

    async def _route_message(
        self,
        message_type: str,
        content: Any,
        options: dict[str, Any]
    ) -> dict[str, Any]:
        """Route a message to appropriate targets"""
        self._stats["total_routed"] += 1

        target_pattern = options.get("target_pattern", message_type)
        strategy = options.get("strategy", self._default_strategy)
        specific_targets = options.get("targets")
        priority = options.get("priority", 0)
        queue = options.get("queue", True)

        # Find matching route
        route = self._find_matching_route(target_pattern)

        # Get target agents
        if specific_targets:
            target_agents = specific_targets
        elif route and route.targets:
            target_agents = list(route.targets.keys())
        else:
            # Discover agents by message type
            target_agents = await self._discover_targets(message_type)

        if not target_agents:
            return {
                "status": "error",
                "error": "No targets available",
                "message_type": message_type,
            }

        # Select target using load balancing
        selected_target = await self._select_target(
            target_agents,
            strategy,
            route,
        )

        if not selected_target:
            if queue:
                # Queue the request
                request = await self._queue_request(
                    message_type,
                    content,
                    target_agents,
                    priority,
                )
                return {
                    "status": "queued",
                    "request_id": request.request_id,
                    "queue_position": len(self._request_queue),
                    "target_count": len(target_agents),
                }
            else:
                self._stats["failed_routes"] += 1
                return {
                    "status": "error",
                    "error": "No available targets",
                    "message_type": message_type,
                }

        # Create request
        self._request_counter += 1
        request_id = f"req-{self._request_counter:06d}"

        # Create message for routing
        message = Message(
            type=MessageType.REQUEST,
            sender_id=self.agent_id,
            receiver_id=selected_target,
            content={
                "original_type": message_type,
                "content": content,
                "routed_by": self.agent_id,
                "request_id": request_id,
            },
        )

        # Track the request
        request = QueuedRequest(
            request_id=request_id,
            message=message,
            target_agents=[selected_target],
            priority=priority,
        )
        request.started_at = datetime.now()
        request.status = "routing"
        self._active_requests[request_id] = request

        # Update target stats
        if route and selected_target in route.targets:
            route.targets[selected_target].active_connections += 1
            route.targets[selected_target].total_requests += 1
            route.targets[selected_target].last_request_time = datetime.now()

        try:
            # Send message to target
            if self._communication_manager:
                response = await self._communication_manager.send(message)
                request.status = "completed"
                request.completed_at = datetime.now()
                request.result = response.content if response else None
                self._stats["successful_routes"] += 1

                # Update success stats
                if route and selected_target in route.targets:
                    route.targets[selected_target].successful_requests += 1
                    response_time = (request.completed_at - request.started_at).total_seconds() * 1000
                    route.targets[selected_target].total_response_time += response_time

                return {
                    "status": "success",
                    "request_id": request_id,
                    "target": selected_target,
                    "response": request.result,
                    "response_time_ms": request.processing_time * 1000 if request.processing_time else None,
                }
            else:
                raise RuntimeError("Communication manager not initialized")

        except Exception as e:
            request.status = "failed"
            request.error = str(e)
            self._stats["failed_routes"] += 1

            if route and selected_target in route.targets:
                route.targets[selected_target].failed_requests += 1

            return {
                "status": "error",
                "request_id": request_id,
                "error": str(e),
                "target": selected_target,
            }

        finally:
            # Update connection count
            if route and selected_target in route.targets:
                route.targets[selected_target].active_connections -= 1

            # Move to completed
            if request_id in self._active_requests:
                del self._active_requests[request_id]
                self._completed_requests.append(request)

                # Keep only last 100 completed requests
                if len(self._completed_requests) > 100:
                    self._completed_requests = self._completed_requests[-100:]

    def _find_matching_route(self, pattern: str) -> Route | None:
        """Find a route matching the pattern"""
        for route in self._routes.values():
            if not route.enabled:
                continue

            # Simple pattern matching
            if route.pattern == "*" or route.pattern == pattern:
                return route

            # Wildcard matching
            if route.pattern.endswith("*"):
                prefix = route.pattern[:-1]
                if pattern.startswith(prefix):
                    return route

        return self._routes.get("default")

    async def _discover_targets(self, message_type: str) -> list[str]:
        """Discover target agents for a message type"""
        if self._discovery_manager:
            try:
                agents = await self._discovery_manager.discover_by_skill(message_type)
                return [a.agent_id for a in agents]
            except Exception as e:
                self.logger.error(f"Discovery failed: {e}")

        return []

    async def _select_target(
        self,
        targets: list[str],
        strategy: LoadBalanceStrategy,
        route: Route | None
    ) -> str | None:
        """Select a target using the specified strategy"""
        if not targets:
            return None

        if strategy == LoadBalanceStrategy.RANDOM:
            return random.choice(targets)

        elif strategy == LoadBalanceStrategy.ROUND_ROBIN:
            if route:
                route._rr_index = (route._rr_index + 1) % len(targets)
                return targets[route._rr_index]
            return targets[0]

        elif strategy == LoadBalanceStrategy.WEIGHTED:
            if route:
                # Weighted random selection
                weights = []
                valid_targets = []
                for t in targets:
                    if t in route.targets:
                        weights.append(route.targets[t].weight)
                        valid_targets.append(t)

                if valid_targets:
                    total = sum(weights)
                    r = random.uniform(0, total)
                    cumulative = 0
                    for target, weight in zip(valid_targets, weights, strict=False):
                        cumulative += weight
                        if r <= cumulative:
                            return target
            return random.choice(targets)

        elif strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            if route:
                min_conn = float('inf')
                best_target = None
                for t in targets:
                    if t in route.targets:
                        target = route.targets[t]
                        if target.active_connections < target.max_connections:
                            if target.active_connections < min_conn:
                                min_conn = target.active_connections
                                best_target = t
                return best_target
            return targets[0]

        elif strategy == LoadBalanceStrategy.LEAST_RESPONSE_TIME:
            if route:
                min_time = float('inf')
                best_target = None
                for t in targets:
                    if t in route.targets:
                        target = route.targets[t]
                        if target.average_response_time < min_time:
                            min_time = target.average_response_time
                            best_target = t
                return best_target
            return targets[0]

        return targets[0]

    async def _queue_request(
        self,
        message_type: str,
        content: Any,
        target_agents: list[str],
        priority: int,
    ) -> QueuedRequest:
        """Queue a request for later processing"""
        async with self._queue_lock:
            if len(self._request_queue) >= self._max_queue_size:
                self._stats["queue_timeouts"] += 1
                raise RuntimeError("Queue is full")

            self._request_counter += 1
            request_id = f"req-{self._request_counter:06d}"

            message = Message(
                type=MessageType.REQUEST,
                sender_id=self.agent_id,
                content={
                    "original_type": message_type,
                    "content": content,
                },
            )

            request = QueuedRequest(
                request_id=request_id,
                message=message,
                target_agents=target_agents,
                priority=priority,
            )

            # Insert by priority (higher priority first)
            inserted = False
            for i, queued in enumerate(self._request_queue):
                if priority > queued.priority:
                    self._request_queue.insert(i, request)
                    inserted = True
                    break

            if not inserted:
                self._request_queue.append(request)

            self._stats["total_queued"] += 1

            return request

    async def _process_queue_loop(self) -> None:
        """Background task to process queued requests"""
        while self._processing:
            try:
                await self._process_next_queued()
                await asyncio.sleep(0.1)  # Small delay to prevent busy loop
            except Exception as e:
                self.logger.error(f"Queue processing error: {e}")
                await asyncio.sleep(1)

    async def _process_next_queued(self) -> None:
        """Process the next queued request"""
        if not self._request_queue:
            return

        if len(self._active_requests) >= self._max_concurrent_requests:
            return

        async with self._queue_lock:
            if not self._request_queue:
                return

            request = self._request_queue.pop(0)
            request.started_at = datetime.now()
            request.status = "processing"
            self._active_requests[request.request_id] = request

        # Process the request
        try:
            result = await self._route_message(
                request.message.content.get("original_type", "unknown"),
                request.message.content.get("content"),
                {"targets": request.target_agents}
            )
            request.result = result
            request.status = "completed" if result.get("status") == "success" else "failed"
        except Exception as e:
            request.error = str(e)
            request.status = "failed"
        finally:
            request.completed_at = datetime.now()
            if request.request_id in self._active_requests:
                del self._active_requests[request.request_id]
            self._completed_requests.append(request)

    async def _flush_queue(self) -> None:
        """Process all remaining queued requests"""
        while self._request_queue:
            await self._process_next_queued()
            await asyncio.sleep(0.01)

    # ==================== Public Helper Methods ====================

    def add_route(
        self,
        route_id: str,
        name: str,
        pattern: str,
        target_agents: list[str],
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
        weights: dict[str, int] | None = None,
    ) -> Route:
        """Add or update a route"""
        targets = []
        for agent_id in target_agents:
            weight = weights.get(agent_id, 1) if weights else 1
            targets.append(RouteTarget(agent_id=agent_id, weight=weight))

        route = Route(
            route_id=route_id,
            name=name,
            pattern=pattern,
            targets=targets,
            strategy=strategy,
        )

        self._routes[route_id] = route
        self.logger.info(f"Added route: {route_id}")

        return route

    def remove_route(self, route_id: str) -> bool:
        """Remove a route"""
        if route_id in self._routes and route_id != "default":
            del self._routes[route_id]
            return True
        return False

    def update_target_status(
        self,
        agent_id: str,
        status: RouteStatus,
        route_id: str | None = None
    ) -> None:
        """Update the status of a route target"""
        routes_to_update = [self._routes[route_id]] if route_id else list(self._routes.values())

        for route in routes_to_update:
            if agent_id in route.targets:
                route.targets[agent_id].status = status
