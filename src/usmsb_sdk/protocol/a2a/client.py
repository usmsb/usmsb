"""
A2A Protocol Client

This module provides the A2A client implementation for agent-to-agent communication.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from usmsb_sdk.protocol.base import (
    BaseProtocolHandler,
    ExternalAgentStatus,
    ProtocolConfig,
    SkillDefinition,
)

logger = logging.getLogger(__name__)


@dataclass
class A2AEnvelope:
    """Envelope for A2A protocol messages."""
    version: str = "1.0"
    sender_id: str = ""
    receiver_id: str = ""
    message_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    timestamp: float = field(default_factory=time.time)
    ttl: int = 3600  # Time-to-live in seconds
    signature: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message_type": self.message_type,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "signature": self.signature,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "A2AEnvelope":
        return cls(
            version=data.get("version", "1.0"),
            sender_id=data.get("sender_id", ""),
            receiver_id=data.get("receiver_id", ""),
            message_type=data.get("message_type", ""),
            payload=data.get("payload", {}),
            correlation_id=data.get("correlation_id", ""),
            timestamp=data.get("timestamp", time.time()),
            ttl=data.get("ttl", 3600),
            signature=data.get("signature"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class A2ASkillRequest:
    """Request to execute a skill via A2A."""
    skill_id: str
    skill_name: str
    arguments: dict[str, Any]
    timeout: float = 60.0
    priority: int = 0
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "arguments": self.arguments,
            "timeout": self.timeout,
            "priority": self.priority,
            "context": self.context,
        }


@dataclass
class A2ASkillResponse:
    """Response from a skill execution via A2A."""
    skill_id: str
    success: bool
    result: Any = None
    error: str | None = None
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
        }


@dataclass
class A2AAgentInfo:
    """Information about an A2A agent."""
    agent_id: str
    name: str
    description: str
    version: str
    capabilities: list[str] = field(default_factory=list)
    skills: list[dict[str, Any]] = field(default_factory=list)
    status: str = "unknown"
    endpoint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class A2AClient(BaseProtocolHandler):
    """
    Client for A2A (Agent-to-Agent) protocol.

    This client implements direct agent-to-agent communication following
    the A2A protocol specification.

    Features:
    - Direct messaging between agents
    - Skill discovery and execution
    - Status monitoring
    - Secure message envelopes
    """

    MESSAGE_TYPES = {
        "ping": "Ping request for health check",
        "pong": "Pong response for health check",
        "discover": "Request to discover agent capabilities",
        "discover_response": "Response with agent capabilities",
        "skill_request": "Request to execute a skill",
        "skill_response": "Response from skill execution",
        "status": "Status request",
        "status_response": "Status response",
        "error": "Error message",
    }

    def __init__(
        self,
        config: ProtocolConfig | None = None,
        agent_id: str | None = None,
    ):
        """
        Initialize the A2A client.

        Args:
            config: Protocol configuration.
            agent_id: Local agent ID for message envelopes.
        """
        super().__init__(config)
        self._agent_id = agent_id or f"agent-{uuid.uuid4().hex[:8]}"
        self._remote_agent_info: A2AAgentInfo | None = None
        self._session: Any | None = None

        # Register default message handlers
        self._register_default_handlers()

        logger.info(f"A2AClient initialized with agent_id={self._agent_id}")

    def _register_default_handlers(self) -> None:
        """Register default message handlers."""
        self.register_message_handler("pong", self._handle_pong)
        self.register_message_handler("discover_response", self._handle_discover_response)
        self.register_message_handler("skill_response", self._handle_skill_response)
        self.register_message_handler("status_response", self._handle_status_response)
        self.register_message_handler("error", self._handle_error)

    # ========== Protocol-Specific Implementation ==========

    async def _do_connect(self, endpoint: str) -> bool:
        """
        Establish A2A connection to the endpoint.

        Args:
            endpoint: The A2A endpoint URL.

        Returns:
            True if connection successful.
        """
        try:
            # In real implementation, establish WebSocket or HTTP connection
            # For now, simulate connection setup
            self._session = {"connected": True, "endpoint": endpoint}

            # Perform initial handshake
            agent_info = await self._perform_handshake()

            if agent_info:
                self._remote_agent_info = agent_info
                return True

            return False

        except Exception as e:
            logger.error(f"A2A connection error: {e}")
            return False

    async def _do_disconnect(self) -> None:
        """Close the A2A connection."""
        if self._session:
            # In real implementation, close the connection properly
            self._session = None
            self._remote_agent_info = None

    async def _do_call_skill(
        self,
        skill_name: str,
        arguments: dict[str, Any],
        timeout: float,
    ) -> Any:
        """
        Execute a skill via A2A protocol.

        Args:
            skill_name: Name of the skill to execute.
            arguments: Arguments for the skill.
            timeout: Timeout for execution.

        Returns:
            Result from the skill execution.
        """
        skill_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())

        # Create skill request
        request = A2ASkillRequest(
            skill_id=skill_id,
            skill_name=skill_name,
            arguments=arguments,
            timeout=timeout,
        )

        # Create A2A envelope
        envelope = A2AEnvelope(
            sender_id=self._agent_id,
            receiver_id=self._remote_agent_info.agent_id if self._remote_agent_info else "",
            message_type="skill_request",
            payload=request.to_dict(),
            correlation_id=correlation_id,
        )

        # Send request and wait for response
        response_future = asyncio.Future()
        self._pending_requests[correlation_id] = response_future

        try:
            # In real implementation, send via WebSocket/HTTP
            await self._send_envelope(envelope)

            # Wait for response
            response = await asyncio.wait_for(response_future, timeout=timeout)

            if response.get("success"):
                return response.get("result")
            else:
                raise Exception(response.get("error", "Unknown error"))

        finally:
            if correlation_id in self._pending_requests:
                del self._pending_requests[correlation_id]

    async def _do_discover_skills(self) -> list[SkillDefinition]:
        """
        Discover skills from the remote agent.

        Returns:
            List of discovered skills.
        """
        if not self._remote_agent_info:
            # Request discovery
            correlation_id = str(uuid.uuid4())

            envelope = A2AEnvelope(
                sender_id=self._agent_id,
                receiver_id="",
                message_type="discover",
                payload={},
                correlation_id=correlation_id,
            )

            response_future = asyncio.Future()
            self._pending_requests[correlation_id] = response_future

            try:
                await self._send_envelope(envelope)
                response = await asyncio.wait_for(response_future, timeout=30.0)

                # Parse skills from response
                skills_data = response.get("skills", [])
                return [SkillDefinition.from_dict(s) for s in skills_data]

            finally:
                if correlation_id in self._pending_requests:
                    del self._pending_requests[correlation_id]

        # Return cached skills
        return [
            SkillDefinition.from_dict(s)
            for s in self._remote_agent_info.skills
        ]

    async def _do_check_status(self) -> ExternalAgentStatus:
        """
        Check the remote agent's status.

        Returns:
            Current status of the remote agent.
        """
        correlation_id = str(uuid.uuid4())

        envelope = A2AEnvelope(
            sender_id=self._agent_id,
            receiver_id=self._remote_agent_info.agent_id if self._remote_agent_info else "",
            message_type="ping",
            payload={},
            correlation_id=correlation_id,
        )

        try:
            await self._send_envelope(envelope)
            # Wait for pong response
            await asyncio.sleep(0.1)  # Simulated response time
            return ExternalAgentStatus.ONLINE

        except Exception as e:
            logger.error(f"A2A status check error: {e}")
            return ExternalAgentStatus.ERROR

    # ========== A2A-Specific Methods ==========

    async def _perform_handshake(self) -> A2AAgentInfo | None:
        """
        Perform A2A handshake with the remote agent.

        Returns:
            Remote agent information if successful.
        """
        try:
            # Send discover request
            correlation_id = str(uuid.uuid4())

            envelope = A2AEnvelope(
                sender_id=self._agent_id,
                receiver_id="",
                message_type="discover",
                payload={"request_agent_info": True},
                correlation_id=correlation_id,
            )

            response_future = asyncio.Future()
            self._pending_requests[correlation_id] = response_future

            await self._send_envelope(envelope)

            # Wait for response
            response = await asyncio.wait_for(response_future, timeout=10.0)

            return A2AAgentInfo(
                agent_id=response.get("agent_id", ""),
                name=response.get("name", "Unknown"),
                description=response.get("description", ""),
                version=response.get("version", "1.0"),
                capabilities=response.get("capabilities", []),
                skills=response.get("skills", []),
                status="online",
                endpoint=self.endpoint or "",
            )

        except Exception as e:
            logger.error(f"A2A handshake error: {e}")
            return None
        finally:
            if correlation_id in self._pending_requests:
                del self._pending_requests[correlation_id]

    async def _send_envelope(self, envelope: A2AEnvelope) -> None:
        """
        Send an A2A envelope to the remote agent.

        Args:
            envelope: The envelope to send.
        """
        if self._connection_info:
            self._connection_info.messages_sent += 1
            self._connection_info.bytes_sent += len(json.dumps(envelope.to_dict()))

        logger.debug(f"A2A sending envelope: {envelope.message_type}")

        # In real implementation, send via WebSocket/HTTP
        # Simulated by just logging
        await asyncio.sleep(0.01)

    async def _receive_envelope(self, data: dict[str, Any]) -> None:
        """
        Handle a received A2A envelope.

        Args:
            data: The received envelope data.
        """
        envelope = A2AEnvelope.from_dict(data)

        if self._connection_info:
            self._connection_info.messages_received += 1
            self._connection_info.bytes_received += len(json.dumps(data))

        logger.debug(f"A2A received envelope: {envelope.message_type}")

        # Handle response messages
        if envelope.correlation_id and envelope.correlation_id in self._pending_requests:
            future = self._pending_requests[envelope.correlation_id]
            if not future.done():
                future.set_result(envelope.payload)

    # ========== Message Handlers ==========

    async def _handle_pong(self, message) -> None:
        """Handle pong response."""
        logger.debug("A2A received pong")

    async def _handle_discover_response(self, message) -> None:
        """Handle discover response."""
        logger.debug("A2A received discover response")

    async def _handle_skill_response(self, message) -> None:
        """Handle skill execution response."""
        logger.debug("A2A received skill response")

    async def _handle_status_response(self, message) -> None:
        """Handle status response."""
        logger.debug("A2A received status response")

    async def _handle_error(self, message) -> None:
        """Handle error message."""
        error = message.payload.get("error", "Unknown error") if hasattr(message, 'payload') else "Unknown error"
        logger.error(f"A2A received error: {error}")

    async def _send_keep_alive(self) -> None:
        """Send A2A keep-alive (ping)."""
        envelope = A2AEnvelope(
            sender_id=self._agent_id,
            receiver_id=self._remote_agent_info.agent_id if self._remote_agent_info else "",
            message_type="ping",
            payload={},
        )
        await self._send_envelope(envelope)

    # ========== Utility Methods ==========

    def get_remote_agent_info(self) -> A2AAgentInfo | None:
        """Get information about the remote agent."""
        return self._remote_agent_info

    def get_agent_id(self) -> str:
        """Get the local agent ID."""
        return self._agent_id
