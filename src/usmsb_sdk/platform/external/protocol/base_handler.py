"""
Base Protocol Handler

This module provides the base class for all protocol handlers,
extending the ProtocolHandler abstract class from external_agent_adapter.
"""

import asyncio
import logging
import time
import uuid
from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from usmsb_sdk.platform.external.external_agent_adapter import (
        ProtocolHandler,
        ExternalAgentStatus,
        ExternalAgentResponse,
        SkillDefinition,
    )


# Define local base classes to avoid circular import
class ExternalAgentStatus(Enum):
    """Agent status enum."""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class ExternalAgentResponse:
    """Response from an external agent."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    status: ExternalAgentStatus = ExternalAgentStatus.ONLINE


@dataclass
class SkillDefinition:
    """Definition of an agent skill."""
    skill_id: str
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProtocolHandler(ABC):
    """Base protocol handler abstract class."""

    @abstractmethod
    async def connect(self, endpoint: str, **kwargs) -> bool:
        """Connect to endpoint."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from endpoint."""
        pass

    @abstractmethod
    async def call_skill(self, skill_name: str, params: Dict[str, Any]) -> ExternalAgentResponse:
        """Call a skill on the remote agent."""
        pass

    @abstractmethod
    async def get_status(self) -> ExternalAgentStatus:
        """Get connection status."""
        pass

logger = logging.getLogger(__name__)


@dataclass
class ProtocolConfig:
    """Configuration for a protocol handler."""
    timeout: float = 60.0
    retry_count: int = 3
    retry_delay: float = 1.0
    keep_alive: bool = True
    keep_alive_interval: float = 30.0
    max_message_size: int = 10 * 1024 * 1024  # 10MB
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProtocolMessage:
    """Base message structure for protocol communication."""
    message_id: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    headers: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "message_type": self.message_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "headers": self.headers,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProtocolMessage":
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            message_type=data.get("message_type", "unknown"),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", time.time()),
            headers=data.get("headers", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ProtocolResponse:
    """Base response structure for protocol communication."""
    message_id: str
    request_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "request_id": self.request_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProtocolResponse":
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            request_id=data.get("request_id", ""),
            success=data.get("success", False),
            result=data.get("result"),
            error=data.get("error"),
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ConnectionInfo:
    """Information about a protocol connection."""
    endpoint: str
    connected: bool = False
    connected_at: Optional[float] = None
    last_activity: Optional[float] = None
    bytes_sent: int = 0
    bytes_received: int = 0
    messages_sent: int = 0
    messages_received: int = 0
    errors: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseProtocolHandler(ProtocolHandler):
    """
    Base class for all protocol handlers.

    This class extends the ProtocolHandler abstract class and provides
    common functionality for all protocol implementations including:
    - Connection management
    - Message tracking
    - Error handling
    - Logging
    """

    def __init__(self, config: Optional[ProtocolConfig] = None):
        """
        Initialize the base protocol handler.

        Args:
            config: Protocol configuration. If None, uses defaults.
        """
        self._config = config or ProtocolConfig()
        self._connection_info: Optional[ConnectionInfo] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._message_handlers: Dict[str, callable] = {}
        self._keep_alive_task: Optional[asyncio.Task] = None

        logger.debug(f"{self.__class__.__name__} initialized with config: {self._config}")

    @property
    def is_connected(self) -> bool:
        """Check if the handler is connected."""
        return self._connection_info is not None and self._connection_info.connected

    @property
    def endpoint(self) -> Optional[str]:
        """Get the current endpoint."""
        return self._connection_info.endpoint if self._connection_info else None

    @property
    def connection_info(self) -> Optional[ConnectionInfo]:
        """Get connection information."""
        return self._connection_info

    async def connect(self, endpoint: str) -> bool:
        """
        Connect to the agent endpoint.

        Args:
            endpoint: The endpoint URL/address to connect to.

        Returns:
            True if connection successful, False otherwise.
        """
        logger.info(f"{self.__class__.__name__} connecting to {endpoint}")

        try:
            # Initialize connection info
            self._connection_info = ConnectionInfo(
                endpoint=endpoint,
                connected=False,
            )

            # Perform protocol-specific connection
            success = await self._do_connect(endpoint)

            if success:
                self._connection_info.connected = True
                self._connection_info.connected_at = time.time()
                self._connection_info.last_activity = time.time()

                # Start keep-alive if enabled
                if self._config.keep_alive:
                    self._start_keep_alive()

                logger.info(f"{self.__class__.__name__} connected to {endpoint}")
            else:
                logger.warning(f"{self.__class__.__name__} failed to connect to {endpoint}")

            return success

        except Exception as e:
            logger.error(f"{self.__class__.__name__} connection error: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from the agent."""
        logger.info(f"{self.__class__.__name__} disconnecting")

        # Stop keep-alive
        self._stop_keep_alive()

        # Cancel pending requests
        for request_id, future in self._pending_requests.items():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

        # Perform protocol-specific disconnection
        await self._do_disconnect()

        # Update connection info
        if self._connection_info:
            self._connection_info.connected = False

        logger.info(f"{self.__class__.__name__} disconnected")

    async def call_skill(
        self,
        skill_name: str,
        arguments: Dict[str, Any],
        timeout: float = 60.0,
    ) -> ExternalAgentResponse:
        """
        Call a skill on the external agent.

        Args:
            skill_name: Name of the skill to call.
            arguments: Arguments to pass to the skill.
            timeout: Timeout for the call.

        Returns:
            ExternalAgentResponse with the result or error.
        """
        if not self.is_connected:
            logger.warning(f"{self.__class__.__name__} call_skill failed: not connected")
            return ExternalAgentResponse(
                call_id=str(uuid.uuid4()),
                agent_id="",
                success=False,
                error="Not connected",
            )

        call_id = str(uuid.uuid4())
        start_time = time.time()

        logger.debug(
            f"{self.__class__.__name__} calling skill '{skill_name}' "
            f"with call_id={call_id}"
        )

        try:
            # Update activity
            if self._connection_info:
                self._connection_info.last_activity = time.time()

            # Perform the actual skill call with retry logic
            result = await self._execute_with_retry(
                lambda: self._do_call_skill(skill_name, arguments, timeout),
                timeout,
            )

            execution_time = time.time() - start_time

            # Update statistics
            if self._connection_info:
                self._connection_info.messages_sent += 1

            logger.debug(
                f"{self.__class__.__name__} skill '{skill_name}' completed "
                f"in {execution_time:.3f}s"
            )

            return ExternalAgentResponse(
                call_id=call_id,
                agent_id="",
                success=True,
                result=result,
                metadata={"execution_time": execution_time},
            )

        except asyncio.TimeoutError:
            logger.warning(
                f"{self.__class__.__name__} skill '{skill_name}' timed out"
            )
            return ExternalAgentResponse(
                call_id=call_id,
                agent_id="",
                success=False,
                error="Timeout",
            )

        except Exception as e:
            logger.error(
                f"{self.__class__.__name__} skill '{skill_name}' error: {e}"
            )
            if self._connection_info:
                self._connection_info.errors += 1

            return ExternalAgentResponse(
                call_id=call_id,
                agent_id="",
                success=False,
                error=str(e),
            )

    async def discover_skills(self) -> List[SkillDefinition]:
        """
        Discover available skills from the agent.

        Returns:
            List of discovered skill definitions.
        """
        if not self.is_connected:
            logger.warning(f"{self.__class__.__name__} discover_skills failed: not connected")
            return []

        logger.debug(f"{self.__class__.__name__} discovering skills")

        try:
            skills = await self._do_discover_skills()
            logger.info(
                f"{self.__class__.__name__} discovered {len(skills)} skills"
            )
            return skills

        except Exception as e:
            logger.error(f"{self.__class__.__name__} skill discovery error: {e}")
            return []

    async def check_status(self) -> ExternalAgentStatus:
        """
        Check the agent's status.

        Returns:
            Current status of the external agent.
        """
        if not self.is_connected:
            return ExternalAgentStatus.OFFLINE

        try:
            status = await self._do_check_status()

            # Update activity
            if self._connection_info:
                self._connection_info.last_activity = time.time()

            return status

        except Exception as e:
            logger.error(f"{self.__class__.__name__} status check error: {e}")
            return ExternalAgentStatus.ERROR

    # ========== Abstract Methods for Protocol-Specific Implementation ==========

    @abstractmethod
    async def _do_connect(self, endpoint: str) -> bool:
        """
        Perform protocol-specific connection.

        Args:
            endpoint: The endpoint to connect to.

        Returns:
            True if connection successful, False otherwise.
        """
        pass

    @abstractmethod
    async def _do_disconnect(self) -> None:
        """Perform protocol-specific disconnection."""
        pass

    @abstractmethod
    async def _do_call_skill(
        self,
        skill_name: str,
        arguments: Dict[str, Any],
        timeout: float,
    ) -> Any:
        """
        Perform protocol-specific skill call.

        Args:
            skill_name: Name of the skill to call.
            arguments: Arguments for the skill.
            timeout: Timeout for the call.

        Returns:
            The result of the skill call.
        """
        pass

    @abstractmethod
    async def _do_discover_skills(self) -> List[SkillDefinition]:
        """
        Perform protocol-specific skill discovery.

        Returns:
            List of discovered skills.
        """
        pass

    @abstractmethod
    async def _do_check_status(self) -> ExternalAgentStatus:
        """
        Perform protocol-specific status check.

        Returns:
            Current agent status.
        """
        pass

    # ========== Utility Methods ==========

    async def _execute_with_retry(
        self,
        operation: callable,
        timeout: float,
    ) -> Any:
        """
        Execute an operation with retry logic.

        Args:
            operation: Async function to execute.
            timeout: Timeout for each attempt.

        Returns:
            Result of the operation.

        Raises:
            Exception: If all retries fail.
        """
        last_error = None

        for attempt in range(self._config.retry_count):
            try:
                return await asyncio.wait_for(
                    operation(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                raise  # Don't retry on timeout
            except Exception as e:
                last_error = e
                if attempt < self._config.retry_count - 1:
                    logger.warning(
                        f"{self.__class__.__name__} operation failed, "
                        f"retrying ({attempt + 1}/{self._config.retry_count}): {e}"
                    )
                    await asyncio.sleep(self._config.retry_delay)

        raise last_error

    def _start_keep_alive(self) -> None:
        """Start the keep-alive background task."""
        if self._keep_alive_task is None or self._keep_alive_task.done():
            self._keep_alive_task = asyncio.create_task(self._keep_alive_loop())

    def _stop_keep_alive(self) -> None:
        """Stop the keep-alive background task."""
        if self._keep_alive_task and not self._keep_alive_task.done():
            self._keep_alive_task.cancel()
            self._keep_alive_task = None

    async def _keep_alive_loop(self) -> None:
        """Background task for sending keep-alive messages."""
        while self.is_connected:
            try:
                await asyncio.sleep(self._config.keep_alive_interval)

                if self.is_connected:
                    await self._send_keep_alive()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"{self.__class__.__name__} keep-alive error: {e}")

    async def _send_keep_alive(self) -> None:
        """
        Send a keep-alive message.

        Override this method in subclasses to implement protocol-specific
        keep-alive functionality.
        """
        pass

    def register_message_handler(self, message_type: str, handler: callable) -> None:
        """
        Register a handler for a specific message type.

        Args:
            message_type: Type of message to handle.
            handler: Async function to handle the message.
        """
        self._message_handlers[message_type] = handler
        logger.debug(
            f"{self.__class__.__name__} registered handler for message type: {message_type}"
        )

    def unregister_message_handler(self, message_type: str) -> None:
        """
        Unregister a message handler.

        Args:
            message_type: Type of message to stop handling.
        """
        if message_type in self._message_handlers:
            del self._message_handlers[message_type]

    async def _handle_message(self, message: ProtocolMessage) -> Optional[ProtocolResponse]:
        """
        Handle an incoming message.

        Args:
            message: The message to handle.

        Returns:
            Optional response to the message.
        """
        handler = self._message_handlers.get(message.message_type)

        if handler:
            try:
                return await handler(message)
            except Exception as e:
                logger.error(
                    f"{self.__class__.__name__} message handler error: {e}"
                )
        else:
            logger.warning(
                f"{self.__class__.__name__} no handler for message type: {message.message_type}"
            )

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get handler statistics.

        Returns:
            Dictionary with handler statistics.
        """
        if not self._connection_info:
            return {"connected": False}

        return {
            "connected": self._connection_info.connected,
            "endpoint": self._connection_info.endpoint,
            "connected_at": self._connection_info.connected_at,
            "last_activity": self._connection_info.last_activity,
            "bytes_sent": self._connection_info.bytes_sent,
            "bytes_received": self._connection_info.bytes_received,
            "messages_sent": self._connection_info.messages_sent,
            "messages_received": self._connection_info.messages_received,
            "errors": self._connection_info.errors,
            "pending_requests": len(self._pending_requests),
        }
