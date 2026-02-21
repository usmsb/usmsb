"""
gRPC Protocol Handler

This module provides the handler for gRPC protocol,
enabling high-performance communication with external agents.

gRPC Protocol Features:
- High-performance RPC framework
- Streaming support (unary, server, client, bidirectional)
- Protocol buffer serialization
- Strong typing and code generation
- Connection management and load balancing
- Comprehensive error handling
"""

import asyncio
import logging
import time
import uuid
from concurrent import futures
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union, TypeVar

# Import grpc conditionally to handle environments without grpc installed
try:
    import grpc
    from grpc import aio
    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    grpc = None
    aio = None

# Import from base_handler to avoid circular import
from usmsb_sdk.platform.external.protocol.base_handler import (
    BaseProtocolHandler,
    ProtocolConfig,
    ProtocolMessage,
    ProtocolResponse,
    ExternalAgentStatus,
    ExternalAgentResponse,
    SkillDefinition,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class gRPCErrorCode(int, Enum):
    """gRPC standard error codes."""
    OK = 0
    CANCELLED = 1
    UNKNOWN = 2
    INVALID_ARGUMENT = 3
    DEADLINE_EXCEEDED = 4
    NOT_FOUND = 5
    ALREADY_EXISTS = 6
    PERMISSION_DENIED = 7
    RESOURCE_EXHAUSTED = 8
    FAILED_PRECONDITION = 9
    ABORTED = 10
    OUT_OF_RANGE = 11
    UNIMPLEMENTED = 12
    INTERNAL = 13
    UNAVAILABLE = 14
    DATA_LOSS = 15
    UNAUTHENTICATED = 16


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies for gRPC connections."""
    ROUND_ROBIN = "round_robin"
    PICK_FIRST = "pick_first"
    LEAST_LOAD = "least_load"
    RANDOM = "random"


@dataclass
class gRPCConfig:
    """gRPC-specific configuration."""
    use_ssl: bool = False
    verify_ssl: bool = True
    ssl_cert_path: Optional[str] = None
    max_message_length: int = 4 * 1024 * 1024  # 4MB
    max_receive_message_length: int = 4 * 1024 * 1024  # 4MB
    keep_alive_time: float = 30.0
    keep_alive_timeout: float = 10.0
    keep_alive_permit_without_calls: bool = True
    enable_compression: bool = False
    compression_algorithm: str = "gzip"  # gzip, deflate
    metadata: Dict[str, str] = field(default_factory=dict)
    load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    enable_health_check: bool = True
    health_check_interval: float = 60.0
    channel_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class gRPCMethod:
    """gRPC method definition."""
    service: str
    method: str
    request_type: str
    response_type: str
    streaming_request: bool = False
    streaming_response: bool = False

    @property
    def full_name(self) -> str:
        return f"/{self.service}/{self.method}"


@dataclass
class gRPCRequest:
    """gRPC request structure."""
    method: str
    message: Dict[str, Any]
    metadata: Dict[str, str] = field(default_factory=dict)
    timeout: float = 60.0
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "message": self.message,
            "metadata": self.metadata,
            "timeout": self.timeout,
            "request_id": self.request_id,
        }


@dataclass
class gRPCResponse:
    """gRPC response structure."""
    request_id: str
    success: bool
    message: Any = None
    error: Optional[str] = None
    code: int = 0
    details: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)
    elapsed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "success": self.success,
            "message": self.message,
            "error": self.error,
            "code": self.code,
            "details": self.details,
            "metadata": self.metadata,
            "elapsed": self.elapsed,
        }


@dataclass
class gRPCServiceDefinition:
    """gRPC service definition."""
    name: str
    package: str
    methods: List[gRPCMethod] = field(default_factory=list)
    description: str = ""

    def to_skill_definition(self, method: gRPCMethod) -> SkillDefinition:
        """Convert gRPC method to SkillDefinition."""
        return SkillDefinition(
            skill_id=f"grpc-{self.name}-{method.method}",
            name=f"{self.name}.{method.method}",
            description=f"gRPC method: {method.full_name}",
            category="grpc",
            metadata={
                "service": self.name,
                "method": method.method,
                "streaming_request": method.streaming_request,
                "streaming_response": method.streaming_response,
            },
        )


@dataclass
class ConnectionEndpoint:
    """Represents a gRPC endpoint with its state."""
    address: str
    weight: float = 1.0
    is_healthy: bool = True
    last_check: float = 0.0
    active_calls: int = 0
    total_calls: int = 0
    failed_calls: int = 0

    @property
    def load(self) -> float:
        """Calculate current load."""
        if self.total_calls == 0:
            return 0.0
        return self.active_calls / max(1, self.total_calls)

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_calls == 0:
            return 1.0
        return (self.total_calls - self.failed_calls) / self.total_calls


class gRPCError(Exception):
    """Custom gRPC error with detailed information."""

    def __init__(
        self,
        message: str,
        code: int = gRPCErrorCode.UNKNOWN,
        details: str = "",
        retryable: bool = False,
    ):
        super().__init__(message)
        self.code = code
        self.details = details
        self.retryable = retryable

    @classmethod
    def from_grpc_error(cls, error: Exception) -> "gRPCError":
        """Create gRPCError from a grpc.RpcError."""
        if GRPC_AVAILABLE and isinstance(error, grpc.RpcError):
            code = error.code() if hasattr(error, 'code') else gRPCErrorCode.UNKNOWN
            details = error.details() if hasattr(error, 'details') else str(error)

            # Determine if error is retryable
            retryable_codes = {
                gRPCErrorCode.UNAVAILABLE,
                gRPCErrorCode.DEADLINE_EXCEEDED,
                gRPCErrorCode.RESOURCE_EXHAUSTED,
                gRPCErrorCode.ABORTED,
            }
            retryable = code in retryable_codes

            return cls(
                message=str(error),
                code=code,
                details=details,
                retryable=retryable,
            )
        return cls(message=str(error))


class ConnectionPool:
    """
    Manages a pool of gRPC connections with load balancing support.
    """

    def __init__(self, config: gRPCConfig):
        self._config = config
        self._endpoints: Dict[str, ConnectionEndpoint] = {}
        self._channels: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._current_index = 0
        self._health_check_task: Optional[asyncio.Task] = None

    async def add_endpoint(self, address: str, weight: float = 1.0) -> None:
        """Add an endpoint to the pool."""
        async with self._lock:
            if address not in self._endpoints:
                self._endpoints[address] = ConnectionEndpoint(
                    address=address,
                    weight=weight,
                )
                logger.info(f"Added gRPC endpoint: {address}")

    async def remove_endpoint(self, address: str) -> None:
        """Remove an endpoint from the pool."""
        async with self._lock:
            if address in self._endpoints:
                del self._endpoints[address]

            # Close channel if exists
            if address in self._channels:
                channel = self._channels[address]
                if hasattr(channel, 'close'):
                    await channel.close()
                del self._channels[address]

            logger.info(f"Removed gRPC endpoint: {address}")

    async def get_channel(self, address: str) -> Any:
        """Get or create a channel for the given address."""
        if not GRPC_AVAILABLE:
            raise gRPCError("gRPC library not available", code=gRPCErrorCode.UNIMPLEMENTED)

        if address not in self._channels:
            self._channels[address] = await self._create_channel(address)

        return self._channels[address]

    async def _create_channel(self, address: str) -> Any:
        """Create a new gRPC channel."""
        if not GRPC_AVAILABLE:
            raise gRPCError("gRPC library not available", code=gRPCErrorCode.UNIMPLEMENTED)

        options = self._build_channel_options()

        if self._config.use_ssl:
            credentials = await self._get_ssl_credentials()
            channel = aio.secure_channel(address, credentials, options)
        else:
            channel = aio.insecure_channel(address, options)

        logger.debug(f"Created gRPC channel for {address}")
        return channel

    def _build_channel_options(self) -> List[tuple]:
        """Build gRPC channel options."""
        options = [
            ('grpc.max_send_message_length', self._config.max_message_length),
            ('grpc.max_receive_message_length', self._config.max_receive_message_length),
            ('grpc.keepalive_time_ms', int(self._config.keep_alive_time * 1000)),
            ('grpc.keepalive_timeout_ms', int(self._config.keep_alive_timeout * 1000)),
            ('grpc.keepalive_permit_without_calls',
             1 if self._config.keep_alive_permit_without_calls else 0),
        ]

        # Add load balancing configuration
        if self._config.load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN:
            options.append(('grpc.lb_policy_name', 'round_robin'))
        elif self._config.load_balancing_strategy == LoadBalancingStrategy.PICK_FIRST:
            options.append(('grpc.lb_policy_name', 'pick_first'))

        # Add custom options
        for key, value in self._config.channel_options.items():
            options.append((key, value))

        return options

    async def _get_ssl_credentials(self) -> Any:
        """Get SSL credentials for secure channel."""
        if not GRPC_AVAILABLE:
            raise gRPCError("gRPC library not available", code=gRPCErrorCode.UNIMPLEMENTED)

        if self._config.ssl_cert_path:
            with open(self._config.ssl_cert_path, 'rb') as f:
                cert = f.read()
            return grpc.ssl_channel_credentials(cert)
        elif self._config.verify_ssl:
            return grpc.ssl_channel_credentials()
        else:
            return grpc.ssl_channel_credentials()

    async def select_endpoint(self) -> Optional[ConnectionEndpoint]:
        """Select an endpoint based on load balancing strategy."""
        async with self._lock:
            healthy_endpoints = [
                ep for ep in self._endpoints.values()
                if ep.is_healthy
            ]

            if not healthy_endpoints:
                return None

            strategy = self._config.load_balancing_strategy

            if strategy == LoadBalancingStrategy.ROUND_ROBIN:
                self._current_index = (self._current_index + 1) % len(healthy_endpoints)
                return healthy_endpoints[self._current_index]

            elif strategy == LoadBalancingStrategy.LEAST_LOAD:
                return min(healthy_endpoints, key=lambda ep: ep.load)

            elif strategy == LoadBalancingStrategy.RANDOM:
                import random
                return random.choice(healthy_endpoints)

            else:  # PICK_FIRST
                return healthy_endpoints[0]

    def get_endpoints(self) -> List[ConnectionEndpoint]:
        """Get all endpoints."""
        return list(self._endpoints.values())

    async def mark_endpoint_healthy(self, address: str) -> None:
        """Mark an endpoint as healthy."""
        if address in self._endpoints:
            self._endpoints[address].is_healthy = True
            self._endpoints[address].last_check = time.time()

    async def mark_endpoint_unhealthy(self, address: str) -> None:
        """Mark an endpoint as unhealthy."""
        if address in self._endpoints:
            self._endpoints[address].is_healthy = False
            self._endpoints[address].last_check = time.time()
            logger.warning(f"gRPC endpoint marked unhealthy: {address}")

    async def record_call_start(self, address: str) -> None:
        """Record the start of a call to an endpoint."""
        if address in self._endpoints:
            self._endpoints[address].active_calls += 1
            self._endpoints[address].total_calls += 1

    async def record_call_end(self, address: str, success: bool) -> None:
        """Record the end of a call to an endpoint."""
        if address in self._endpoints:
            self._endpoints[address].active_calls = max(
                0, self._endpoints[address].active_calls - 1
            )
            if not success:
                self._endpoints[address].failed_calls += 1

    async def close_all(self) -> None:
        """Close all channels."""
        async with self._lock:
            for address, channel in self._channels.items():
                try:
                    if hasattr(channel, 'close'):
                        await channel.close()
                except Exception as e:
                    logger.warning(f"Error closing channel {address}: {e}")
            self._channels.clear()

    async def start_health_checks(self, check_func: Callable) -> None:
        """Start periodic health checks."""
        if self._config.enable_health_check:
            self._health_check_task = asyncio.create_task(
                self._health_check_loop(check_func)
            )

    async def stop_health_checks(self) -> None:
        """Stop health checks."""
        if self._health_check_task:
            self._health_check_task.cancel()
            self._health_check_task = None

    async def _health_check_loop(self, check_func: Callable) -> None:
        """Health check loop."""
        while True:
            try:
                await asyncio.sleep(self._config.health_check_interval)

                for address in list(self._endpoints.keys()):
                    try:
                        is_healthy = await check_func(address)
                        if is_healthy:
                            await self.mark_endpoint_healthy(address)
                        else:
                            await self.mark_endpoint_unhealthy(address)
                    except Exception as e:
                        logger.debug(f"Health check failed for {address}: {e}")
                        await self.mark_endpoint_unhealthy(address)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")


class gRPCProtocolHandler(BaseProtocolHandler):
    """
    Handler for gRPC protocol.

    This handler implements high-performance communication with
    external agents via gRPC.

    Features:
    - Unary and streaming RPC
    - Protocol buffer serialization
    - SSL/TLS support
    - Metadata propagation
    - Deadline/timeout handling
    - Connection pooling and load balancing
    - Server and client support
    """

    def __init__(
        self,
        config: Optional[ProtocolConfig] = None,
        grpc_config: Optional[gRPCConfig] = None,
    ):
        """
        Initialize the gRPC protocol handler.

        Args:
            config: Protocol configuration.
            grpc_config: gRPC-specific configuration.
        """
        super().__init__(config)
        self._grpc_config = grpc_config or gRPCConfig()
        self._channel: Optional[Any] = None
        self._connection_pool: Optional[ConnectionPool] = None
        self._stubs: Dict[str, Any] = {}
        self._services: Dict[str, gRPCServiceDefinition] = {}
        self._method_cache: Dict[str, gRPCMethod] = {}
        self._server: Optional[Any] = None
        self._server_handlers: Dict[str, Callable] = {}

        # Initialize connection pool if using load balancing
        if self._grpc_config.load_balancing_strategy != LoadBalancingStrategy.PICK_FIRST:
            self._connection_pool = ConnectionPool(self._grpc_config)

        logger.info("gRPCProtocolHandler initialized")

    # ========== Protocol-Specific Implementation ==========

    async def _do_connect(self, endpoint: str) -> bool:
        """
        Establish gRPC connection to the endpoint.

        Args:
            endpoint: The gRPC server address (host:port or comma-separated list).

        Returns:
            True if connection successful.
        """
        try:
            if not GRPC_AVAILABLE:
                logger.warning("gRPC library not available, using mock implementation")
                self._channel = {
                    "target": endpoint,
                    "connected": True,
                    "connected_at": time.time(),
                }
                await self._discover_services()
                return True

            logger.info(f"gRPC connecting to {endpoint}")

            # Handle multiple endpoints for load balancing
            endpoints = [e.strip() for e in endpoint.split(',')]

            if len(endpoints) > 1 and self._connection_pool:
                # Multi-endpoint with load balancing
                for ep in endpoints:
                    await self._connection_pool.add_endpoint(ep)

                # Select initial endpoint
                selected = await self._connection_pool.select_endpoint()
                if selected:
                    self._channel = await self._connection_pool.get_channel(selected.address)

                    # Start health checks
                    await self._connection_pool.start_health_checks(
                        self._check_endpoint_health
                    )
            else:
                # Single endpoint
                self._channel = await self._create_channel(endpoints[0])

            # Discover services (reflection in real implementation)
            await self._discover_services()

            logger.info(f"gRPC connected to {endpoint}")
            return True

        except Exception as e:
            logger.error(f"gRPC connection error: {e}")
            return False

    async def _create_channel(self, address: str) -> Any:
        """Create a gRPC channel for the given address."""
        if not GRPC_AVAILABLE:
            return {"target": address, "connected": True, "connected_at": time.time()}

        options = self._build_channel_options()

        if self._grpc_config.use_ssl:
            credentials = await self._get_ssl_credentials()
            channel = aio.secure_channel(address, credentials, options)
        else:
            channel = aio.insecure_channel(address, options)

        return channel

    def _build_channel_options(self) -> List[tuple]:
        """Build gRPC channel options."""
        options = [
            ('grpc.max_send_message_length', self._grpc_config.max_message_length),
            ('grpc.max_receive_message_length', self._grpc_config.max_receive_message_length),
            ('grpc.keepalive_time_ms', int(self._grpc_config.keep_alive_time * 1000)),
            ('grpc.keepalive_timeout_ms', int(self._grpc_config.keep_alive_timeout * 1000)),
            ('grpc.keepalive_permit_without_calls',
             1 if self._grpc_config.keep_alive_permit_without_calls else 0),
        ]
        return options

    async def _get_ssl_credentials(self) -> Any:
        """Get SSL credentials for secure channel."""
        if not GRPC_AVAILABLE:
            return None

        if self._grpc_config.ssl_cert_path:
            with open(self._grpc_config.ssl_cert_path, 'rb') as f:
                cert = f.read()
            return grpc.ssl_channel_credentials(cert)
        elif self._grpc_config.verify_ssl:
            return grpc.ssl_channel_credentials()
        else:
            return grpc.ssl_channel_credentials()

    async def _do_disconnect(self) -> None:
        """Close the gRPC channel."""
        # Stop health checks
        if self._connection_pool:
            await self._connection_pool.stop_health_checks()
            await self._connection_pool.close_all()

        # Close single channel
        if self._channel and GRPC_AVAILABLE:
            try:
                if hasattr(self._channel, 'close'):
                    await self._channel.close()
            except Exception as e:
                logger.warning(f"Error closing gRPC channel: {e}")

        self._channel = None
        self._stubs.clear()
        self._services.clear()
        self._method_cache.clear()

        # Stop server if running
        if self._server:
            await self.stop_server()

        logger.info("gRPC channel closed")

    async def _do_call_skill(
        self,
        skill_name: str,
        arguments: Dict[str, Any],
        timeout: float,
    ) -> Any:
        """
        Execute a skill (gRPC method) via gRPC.

        Args:
            skill_name: Name of the method to call (Service.Method).
            arguments: Arguments for the method.
            timeout: Timeout for the call.

        Returns:
            Result from the method call.
        """
        # Parse service and method
        if "." in skill_name:
            service, method = skill_name.split(".", 1)
        else:
            raise gRPCError(
                f"Invalid skill name format: {skill_name}",
                code=gRPCErrorCode.INVALID_ARGUMENT,
            )

        # Create request
        request = gRPCRequest(
            method=f"/{service}/{method}",
            message=arguments,
            metadata=self._grpc_config.metadata.copy(),
            timeout=timeout,
        )

        # Execute call with endpoint selection
        endpoint_address = None
        if self._connection_pool:
            endpoint = await self._connection_pool.select_endpoint()
            if endpoint:
                endpoint_address = endpoint.address
                await self._connection_pool.record_call_start(endpoint_address)

        try:
            response = await self._execute_unary(request)

            if response.success:
                if endpoint_address and self._connection_pool:
                    await self._connection_pool.record_call_end(endpoint_address, True)
                return response.message
            else:
                if endpoint_address and self._connection_pool:
                    await self._connection_pool.record_call_end(endpoint_address, False)
                raise gRPCError(
                    response.error or f"gRPC error code: {response.code}",
                    code=response.code,
                    details=response.details,
                )

        except Exception as e:
            if endpoint_address and self._connection_pool:
                await self._connection_pool.record_call_end(endpoint_address, False)
            raise

    async def _do_discover_skills(self) -> List[SkillDefinition]:
        """
        Discover skills (gRPC methods) from the server.

        Returns:
            List of discovered skills.
        """
        skills = []

        for service_name, service in self._services.items():
            for method in service.methods:
                skills.append(service.to_skill_definition(method))
                # Cache method
                self._method_cache[f"{service_name}.{method.method}"] = method

        return skills

    async def _do_check_status(self) -> ExternalAgentStatus:
        """
        Check the gRPC server status.

        Returns:
            Current status of the server.
        """
        if not self._channel:
            return ExternalAgentStatus.OFFLINE

        try:
            if GRPC_AVAILABLE:
                # Try to use health checking service if available
                # grpc.health.v1.Health/Check
                await asyncio.sleep(0.05)

            return ExternalAgentStatus.ONLINE

        except Exception as e:
            logger.error(f"gRPC status check error: {e}")
            return ExternalAgentStatus.ERROR

    async def _check_endpoint_health(self, address: str) -> bool:
        """Check health of a specific endpoint."""
        try:
            if not GRPC_AVAILABLE:
                return True

            channel = await self._connection_pool.get_channel(address)
            # Simple connectivity check
            # In production, use the health checking service
            await asyncio.sleep(0.05)
            return True

        except Exception as e:
            logger.debug(f"Health check failed for {address}: {e}")
            return False

    # ========== gRPC-Specific Methods ==========

    async def _discover_services(self) -> None:
        """
        Discover gRPC services via reflection.

        Uses gRPC server reflection to discover available services.
        """
        # In real implementation, use grpc-reflection
        # For now, add services defined in proto files

        # Node Sync Service
        node_sync_service = gRPCServiceDefinition(
            name="NodeSyncService",
            package="usmsb.node",
            description="Node synchronization service for batch data sync",
            methods=[
                gRPCMethod(
                    service="NodeSyncService",
                    method="FullSync",
                    request_type="SyncRequest",
                    response_type="SyncResponse",
                ),
                gRPCMethod(
                    service="NodeSyncService",
                    method="IncrementalSync",
                    request_type="SyncRequest",
                    response_type="SyncResponse",
                ),
                gRPCMethod(
                    service="NodeSyncService",
                    method="StreamEvents",
                    request_type="BatchEventRequest",
                    response_type="AgentChangeEvent",
                    streaming_response=True,
                ),
                gRPCMethod(
                    service="NodeSyncService",
                    method="HealthCheck",
                    request_type="HealthCheckRequest",
                    response_type="HealthCheckResponse",
                ),
                gRPCMethod(
                    service="NodeSyncService",
                    method="DiscoverNodes",
                    request_type="NodeDiscoveryRequest",
                    response_type="NodeDiscoveryResponse",
                ),
                gRPCMethod(
                    service="NodeSyncService",
                    method="SyncFromIPFS",
                    request_type="IPFSSyncRequest",
                    response_type="IPFSSyncResponse",
                ),
                gRPCMethod(
                    service="NodeSyncService",
                    method="BidirectionalSync",
                    request_type="AgentChangeEvent",
                    response_type="AgentChangeEvent",
                    streaming_request=True,
                    streaming_response=True,
                ),
            ],
        )
        self._services["NodeSyncService"] = node_sync_service

        # Agent Communication Service
        agent_comm_service = gRPCServiceDefinition(
            name="AgentCommunicationService",
            package="usmsb.agent",
            description="Agent-to-agent communication service",
            methods=[
                gRPCMethod(
                    service="AgentCommunicationService",
                    method="SendMessage",
                    request_type="AgentMessage",
                    response_type="AgentMessage",
                ),
                gRPCMethod(
                    service="AgentCommunicationService",
                    method="StreamCommunication",
                    request_type="AgentMessage",
                    response_type="AgentMessage",
                    streaming_request=True,
                    streaming_response=True,
                ),
                gRPCMethod(
                    service="AgentCommunicationService",
                    method="CallSkill",
                    request_type="SkillCallRequest",
                    response_type="SkillCallResponse",
                ),
                gRPCMethod(
                    service="AgentCommunicationService",
                    method="DiscoverAgents",
                    request_type="DiscoveryRequest",
                    response_type="DiscoveryResponse",
                ),
                gRPCMethod(
                    service="AgentCommunicationService",
                    method="Heartbeat",
                    request_type="HeartbeatMessage",
                    response_type="HeartbeatMessage",
                ),
            ],
        )
        self._services["AgentCommunicationService"] = agent_comm_service

        # Default Agent Service
        agent_service = gRPCServiceDefinition(
            name="AgentService",
            package="usmsb.v1",
            description="Agent service for skill execution",
            methods=[
                gRPCMethod(
                    service="AgentService",
                    method="ExecuteSkill",
                    request_type="ExecuteSkillRequest",
                    response_type="ExecuteSkillResponse",
                ),
                gRPCMethod(
                    service="AgentService",
                    method="DiscoverSkills",
                    request_type="DiscoverSkillsRequest",
                    response_type="DiscoverSkillsResponse",
                ),
                gRPCMethod(
                    service="AgentService",
                    method="GetStatus",
                    request_type="GetStatusRequest",
                    response_type="GetStatusResponse",
                ),
            ],
        )
        self._services["AgentService"] = agent_service

        logger.debug(f"gRPC discovered {len(self._services)} services")

    async def _execute_unary(self, request: gRPCRequest) -> gRPCResponse:
        """
        Execute a unary gRPC call.

        Args:
            request: The gRPC request.

        Returns:
            gRPC response.
        """
        if not self._channel:
            raise gRPCError("gRPC channel not connected", code=gRPCErrorCode.UNAVAILABLE)

        start_time = time.time()

        logger.debug(f"gRPC calling {request.method}")

        try:
            if GRPC_AVAILABLE and hasattr(self._channel, 'unary_unary'):
                # Real gRPC call
                metadata = list(request.metadata.items())

                # Create deadline
                deadline = time.time() + request.timeout

                # Make the call
                method = self._channel.unary_unary(request.method)
                response = await method(
                    request.message,
                    metadata=metadata,
                    timeout=request.timeout,
                )

                elapsed = time.time() - start_time

                # Update statistics
                if self._connection_info:
                    self._connection_info.messages_sent += 1

                return gRPCResponse(
                    request_id=request.request_id,
                    success=True,
                    message=response,
                    elapsed=elapsed,
                )
            else:
                # Mock implementation for testing
                await asyncio.sleep(0.1)

                elapsed = time.time() - start_time

                if self._connection_info:
                    self._connection_info.messages_sent += 1

                return gRPCResponse(
                    request_id=request.request_id,
                    success=True,
                    message={"result": f"Executed {request.method}"},
                    elapsed=elapsed,
                )

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            return gRPCResponse(
                request_id=request.request_id,
                success=False,
                error="Deadline exceeded",
                code=gRPCErrorCode.DEADLINE_EXCEEDED,
                elapsed=elapsed,
            )

        except Exception as e:
            elapsed = time.time() - start_time
            grpc_error = gRPCError.from_grpc_error(e)
            return gRPCResponse(
                request_id=request.request_id,
                success=False,
                error=grpc_error.message,
                code=grpc_error.code,
                details=grpc_error.details,
                elapsed=elapsed,
            )

    # ========== Streaming Methods ==========

    async def execute_server_streaming(
        self,
        method: str,
        message: Dict[str, Any],
        timeout: float = 60.0,
        metadata: Optional[Dict[str, str]] = None,
    ) -> AsyncIterator[gRPCResponse]:
        """
        Execute a server-streaming gRPC call.

        Args:
            method: The gRPC method (Service/Method).
            message: Request message.
            timeout: Call timeout.
            metadata: Additional metadata.

        Yields:
            Stream of responses.
        """
        if not self._channel:
            raise gRPCError("gRPC channel not connected", code=gRPCErrorCode.UNAVAILABLE)

        logger.debug(f"gRPC server streaming call: {method}")

        request_id = str(uuid.uuid4())

        try:
            if GRPC_AVAILABLE and hasattr(self._channel, 'unary_stream'):
                # Real gRPC streaming call
                call_metadata = list((metadata or {}).items())
                call_metadata.extend(self._grpc_config.metadata.items())

                stream = self._channel.unary_stream(method)
                call = stream(
                    message,
                    metadata=call_metadata,
                    timeout=timeout,
                )

                async for response in call:
                    yield gRPCResponse(
                        request_id=request_id,
                        success=True,
                        message=response,
                    )
            else:
                # Mock implementation
                for i in range(3):
                    await asyncio.sleep(0.1)
                    yield gRPCResponse(
                        request_id=request_id,
                        success=True,
                        message={"chunk": i, "data": f"Stream chunk {i}"},
                    )

        except Exception as e:
            grpc_error = gRPCError.from_grpc_error(e)
            yield gRPCResponse(
                request_id=request_id,
                success=False,
                error=grpc_error.message,
                code=grpc_error.code,
            )

    async def execute_client_streaming(
        self,
        method: str,
        messages: AsyncIterator[Dict[str, Any]],
        timeout: float = 60.0,
        metadata: Optional[Dict[str, str]] = None,
    ) -> gRPCResponse:
        """
        Execute a client-streaming gRPC call.

        Args:
            method: The gRPC method (Service/Method).
            messages: Async iterator of request messages.
            timeout: Call timeout.
            metadata: Additional metadata.

        Returns:
            Aggregated response.
        """
        if not self._channel:
            raise gRPCError("gRPC channel not connected", code=gRPCErrorCode.UNAVAILABLE)

        logger.debug(f"gRPC client streaming call: {method}")

        request_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            if GRPC_AVAILABLE and hasattr(self._channel, 'stream_unary'):
                # Real gRPC streaming call
                call_metadata = list((metadata or {}).items())
                call_metadata.extend(self._grpc_config.metadata.items())

                stream = self._channel.stream_unary(method)
                response = await stream(
                    messages,
                    metadata=call_metadata,
                    timeout=timeout,
                )

                elapsed = time.time() - start_time
                return gRPCResponse(
                    request_id=request_id,
                    success=True,
                    message=response,
                    elapsed=elapsed,
                )
            else:
                # Mock implementation
                message_count = 0
                async for msg in messages:
                    message_count += 1

                elapsed = time.time() - start_time
                return gRPCResponse(
                    request_id=request_id,
                    success=True,
                    message={"processed": message_count},
                    elapsed=elapsed,
                )

        except Exception as e:
            grpc_error = gRPCError.from_grpc_error(e)
            elapsed = time.time() - start_time
            return gRPCResponse(
                request_id=request_id,
                success=False,
                error=grpc_error.message,
                code=grpc_error.code,
                elapsed=elapsed,
            )

    async def execute_bidirectional_streaming(
        self,
        method: str,
        messages: AsyncIterator[Dict[str, Any]],
        timeout: float = 60.0,
        metadata: Optional[Dict[str, str]] = None,
    ) -> AsyncIterator[gRPCResponse]:
        """
        Execute a bidirectional streaming gRPC call.

        Args:
            method: The gRPC method (Service/Method).
            messages: Async iterator of request messages.
            timeout: Call timeout.
            metadata: Additional metadata.

        Yields:
            Stream of responses.
        """
        if not self._channel:
            raise gRPCError("gRPC channel not connected", code=gRPCErrorCode.UNAVAILABLE)

        logger.debug(f"gRPC bidirectional streaming call: {method}")

        request_id = str(uuid.uuid4())

        try:
            if GRPC_AVAILABLE and hasattr(self._channel, 'stream_stream'):
                # Real gRPC streaming call
                call_metadata = list((metadata or {}).items())
                call_metadata.extend(self._grpc_config.metadata.items())

                stream = self._channel.stream_stream(method)
                call = stream(
                    messages,
                    metadata=call_metadata,
                    timeout=timeout,
                )

                async for response in call:
                    yield gRPCResponse(
                        request_id=request_id,
                        success=True,
                        message=response,
                    )
            else:
                # Mock implementation
                async for msg in messages:
                    await asyncio.sleep(0.05)
                    yield gRPCResponse(
                        request_id=request_id,
                        success=True,
                        message={"echo": msg},
                    )

        except Exception as e:
            grpc_error = gRPCError.from_grpc_error(e)
            yield gRPCResponse(
                request_id=request_id,
                success=False,
                error=grpc_error.message,
                code=grpc_error.code,
            )

    # ========== Server Methods ==========

    async def start_server(
        self,
        port: int,
        host: str = "[::]",
        max_workers: int = 10,
    ) -> bool:
        """
        Start a gRPC server.

        Args:
            port: Port to listen on.
            host: Host to bind to.
            max_workers: Maximum number of worker threads.

        Returns:
            True if server started successfully.
        """
        if not GRPC_AVAILABLE:
            logger.warning("gRPC library not available, cannot start server")
            return False

        try:
            if self._server:
                logger.warning("Server already running")
                return False

            # Create async server
            self._server = aio.server(
                futures.ThreadPoolExecutor(max_workers=max_workers),
                options=[
                    ('grpc.max_send_message_length', self._grpc_config.max_message_length),
                    ('grpc.max_receive_message_length', self._grpc_config.max_receive_message_length),
                ],
            )

            # Register handlers
            await self._register_services()

            # Add secure or insecure port
            if self._grpc_config.use_ssl:
                credentials = await self._get_server_credentials()
                self._server.add_secure_port(f"{host}:{port}", credentials)
            else:
                self._server.add_insecure_port(f"{host}:{port}")

            # Start server
            await self._server.start()

            logger.info(f"gRPC server started on {host}:{port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start gRPC server: {e}")
            return False

    async def _get_server_credentials(self) -> Any:
        """Get SSL credentials for the server."""
        if not GRPC_AVAILABLE:
            return None

        if self._grpc_config.ssl_cert_path:
            # Load certificate and key
            cert_path = self._grpc_config.ssl_cert_path
            key_path = self._grpc_config.channel_options.get('ssl_key_path')

            with open(cert_path, 'rb') as f:
                cert = f.read()

            if key_path:
                with open(key_path, 'rb') as f:
                    key = f.read()
                return grpc.ssl_server_credentials([(key, cert)])
            else:
                return grpc.ssl_server_credentials(None)

        return None

    async def _register_services(self) -> None:
        """Register gRPC services on the server."""
        # In real implementation, register generated service classes
        # This would use the generated pb2_grpc modules
        pass

    def register_handler(
        self,
        service: str,
        method: str,
        handler: Callable,
    ) -> None:
        """
        Register a handler for a gRPC method.

        Args:
            service: Service name.
            method: Method name.
            handler: Async function to handle the call.
        """
        key = f"{service}.{method}"
        self._server_handlers[key] = handler
        logger.debug(f"Registered handler for {key}")

    def unregister_handler(self, service: str, method: str) -> None:
        """Unregister a handler."""
        key = f"{service}.{method}"
        if key in self._server_handlers:
            del self._server_handlers[key]

    async def stop_server(self, grace: float = 5.0) -> None:
        """
        Stop the gRPC server.

        Args:
            grace: Grace period for pending requests.
        """
        if self._server:
            await self._server.stop(grace)
            self._server = None
            logger.info("gRPC server stopped")

    async def wait_server_termination(self) -> None:
        """Wait for server termination."""
        if self._server:
            await self._server.wait_for_termination()

    # ========== Service Registration ==========

    def register_service(self, service: gRPCServiceDefinition) -> None:
        """
        Register a gRPC service definition.

        Args:
            service: Service definition to register.
        """
        self._services[service.name] = service

        for method in service.methods:
            self._method_cache[f"{service.name}.{method.method}"] = method

        logger.debug(f"gRPC service registered: {service.name}")

    def unregister_service(self, service_name: str) -> None:
        """
        Unregister a gRPC service.

        Args:
            service_name: Name of service to remove.
        """
        if service_name in self._services:
            service = self._services[service_name]
            for method in service.methods:
                key = f"{service_name}.{method.method}"
                if key in self._method_cache:
                    del self._method_cache[key]

            del self._services[service_name]

    def get_service(self, service_name: str) -> Optional[gRPCServiceDefinition]:
        """
        Get a service definition by name.

        Args:
            service_name: Name of the service.

        Returns:
            Service definition or None.
        """
        return self._services.get(service_name)

    def get_method(self, service_name: str, method_name: str) -> Optional[gRPCMethod]:
        """
        Get a method definition.

        Args:
            service_name: Name of the service.
            method_name: Name of the method.

        Returns:
            Method definition or None.
        """
        return self._method_cache.get(f"{service_name}.{method_name}")

    # ========== Metadata Management ==========

    def set_metadata(self, key: str, value: str) -> None:
        """
        Set metadata for all gRPC calls.

        Args:
            key: Metadata key.
            value: Metadata value.
        """
        self._grpc_config.metadata[key] = value

    def get_metadata(self) -> Dict[str, str]:
        """Get current metadata."""
        return dict(self._grpc_config.metadata)

    def clear_metadata(self) -> None:
        """Clear all metadata."""
        self._grpc_config.metadata.clear()

    # ========== Utility Methods ==========

    async def _send_keep_alive(self) -> None:
        """Send gRPC keep-alive via health check."""
        try:
            # Use health check service if available
            status = await self._do_check_status()
            if status != ExternalAgentStatus.ONLINE:
                logger.warning("gRPC keep-alive detected offline status")
        except Exception as e:
            logger.warning(f"gRPC keep-alive error: {e}")

    def get_services(self) -> List[gRPCServiceDefinition]:
        """Get list of registered services."""
        return list(self._services.values())

    def get_grpc_stats(self) -> Dict[str, Any]:
        """Get gRPC statistics."""
        stats = {
            "grpc_available": GRPC_AVAILABLE,
            "connected": self._channel is not None,
            "services": len(self._services),
            "methods": len(self._method_cache),
            "use_ssl": self._grpc_config.use_ssl,
            "load_balancing": self._grpc_config.load_balancing_strategy.value,
            "server_running": self._server is not None,
        }

        if self._connection_pool:
            endpoints = self._connection_pool.get_endpoints()
            stats["endpoints"] = [
                {
                    "address": ep.address,
                    "healthy": ep.is_healthy,
                    "load": ep.load,
                    "success_rate": ep.success_rate,
                }
                for ep in endpoints
            ]

        if self._channel and isinstance(self._channel, dict):
            stats["target"] = self._channel.get("target")

        return stats

    def get_endpoint_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all endpoints."""
        if not self._connection_pool:
            return []

        return [
            {
                "address": ep.address,
                "weight": ep.weight,
                "is_healthy": ep.is_healthy,
                "last_check": ep.last_check,
                "active_calls": ep.active_calls,
                "total_calls": ep.total_calls,
                "failed_calls": ep.failed_calls,
                "load": ep.load,
                "success_rate": ep.success_rate,
            }
            for ep in self._connection_pool.get_endpoints()
        ]


# ========== Proto Message Utilities ==========

class ProtoMessageBuilder:
    """
    Utility class for building proto messages from dictionaries.

    This class helps convert Python dictionaries to proto messages
    when generated stubs are available.
    """

    @staticmethod
    def dict_to_message(data: Dict[str, Any], message_class: Any) -> Any:
        """
        Convert a dictionary to a proto message.

        Args:
            data: Dictionary with message data.
            message_class: Proto message class.

        Returns:
            Proto message instance.
        """
        if hasattr(message_class, 'from_dict'):
            return message_class.from_dict(data)

        # Fallback: manual conversion
        message = message_class()
        for key, value in data.items():
            if hasattr(message, key):
                setattr(message, key, value)

        return message

    @staticmethod
    def message_to_dict(message: Any) -> Dict[str, Any]:
        """
        Convert a proto message to a dictionary.

        Args:
            message: Proto message instance.

        Returns:
            Dictionary representation.
        """
        if hasattr(message, 'to_dict'):
            return message.to_dict()

        # Fallback: use MessageToDict from protobuf
        try:
            from google.protobuf.json_format import MessageToDict
            return MessageToDict(message)
        except ImportError:
            # Manual conversion
            result = {}
            for field in message.DESCRIPTOR.fields:
                value = getattr(message, field.name)
                result[field.name] = value
            return result


# ========== Convenience Functions ==========

def create_grpc_handler(
    endpoint: str,
    use_ssl: bool = False,
    timeout: float = 60.0,
    metadata: Optional[Dict[str, str]] = None,
) -> gRPCProtocolHandler:
    """
    Create and connect a gRPC handler.

    Args:
        endpoint: gRPC server address.
        use_ssl: Whether to use SSL.
        timeout: Connection timeout.
        metadata: Initial metadata.

    Returns:
        Connected gRPC handler.
    """
    config = ProtocolConfig(timeout=timeout)
    grpc_config = gRPCConfig(
        use_ssl=use_ssl,
        metadata=metadata or {},
    )

    handler = gRPCProtocolHandler(config, grpc_config)

    # Note: Connection should be done via async context
    return handler


async def call_grpc_method(
    endpoint: str,
    service: str,
    method: str,
    arguments: Dict[str, Any],
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """
    Convenience function to make a single gRPC call.

    Args:
        endpoint: gRPC server address.
        service: Service name.
        method: Method name.
        arguments: Method arguments.
        timeout: Call timeout.

    Returns:
        Response data.
    """
    handler = create_grpc_handler(endpoint)

    try:
        await handler.connect(endpoint)
        result = await handler.call_skill(
            f"{service}.{method}",
            arguments,
            timeout,
        )
        return result

    finally:
        await handler.disconnect()
