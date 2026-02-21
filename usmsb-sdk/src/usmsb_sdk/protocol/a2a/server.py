"""
A2A Protocol Server

This module provides the A2A server implementation for agent-to-agent communication.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from usmsb_sdk.protocol.a2a.client import (
    A2AEnvelope,
    A2ASkillRequest,
    A2ASkillResponse,
    A2AAgentInfo,
)


logger = logging.getLogger(__name__)


@dataclass
class A2AServerConfig:
    """A2A server configuration."""
    host: str = "0.0.0.0"
    port: int = 9000
    agent_id: Optional[str] = None
    agent_name: str = "A2A Agent"
    agent_version: str = "1.0.0"
    max_connections: int = 100
    timeout: float = 60.0


class A2AServer:
    """
    A2A Server for agent-to-agent communication.

    Features:
    - Agent discovery
    - Skill execution
    - Status monitoring
    - Multiple connections
    """

    def __init__(
        self,
        config: Optional[A2AServerConfig] = None,
        host: str = "0.0.0.0",
        port: int = 9000,
    ):
        """
        Initialize the A2A server.

        Args:
            config: Server configuration.
            host: Host to bind to (overrides config).
            port: Port to listen on (overrides config).
        """
        self._config = config or A2AServerConfig(host=host, port=port)
        self._agent_id = self._config.agent_id or f"agent-{uuid.uuid4().hex[:8]}"
        self._server: Optional[Any] = None
        self._running = False
        self._connections: Dict[str, Any] = {}
        self._skills: Dict[str, Callable] = {}
        self._message_handlers: Dict[str, Callable] = {}

        # Register default handlers
        self._register_default_handlers()

        logger.info(f"A2AServer initialized on {self._config.host}:{self._config.port}")

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running

    @property
    def agent_id(self) -> str:
        """Get the agent ID."""
        return self._agent_id

    def _register_default_handlers(self) -> None:
        """Register default message handlers."""
        self._message_handlers["discover"] = self._handle_discover
        self._message_handlers["skill_request"] = self._handle_skill_request
        self._message_handlers["ping"] = self._handle_ping

    # ========== Server Control ==========

    async def start(self) -> bool:
        """
        Start the A2A server.

        Returns:
            True if server started successfully.
        """
        try:
            logger.info(f"Starting A2A server on {self._config.host}:{self._config.port}")

            # In real implementation, create TCP/WebSocket server
            self._running = True
            self._server = {
                "host": self._config.host,
                "port": self._config.port,
                "started_at": time.time(),
            }

            logger.info(f"A2A server started on {self._config.host}:{self._config.port}")
            return True

        except Exception as e:
            logger.error(f"Failed to start A2A server: {e}")
            return False

    async def stop(self) -> None:
        """Stop the A2A server."""
        if not self._running:
            return

        logger.info("Stopping A2A server")

        # Close all connections
        for connection_id in list(self._connections.keys()):
            await self._close_connection(connection_id)

        self._running = False
        self._server = None

        logger.info("A2A server stopped")

    async def serve_forever(self) -> None:
        """Run the server until interrupted."""
        if not self._running:
            await self.start()

        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await self.stop()

    # ========== Connection Management ==========

    async def _add_connection(self, remote_address: str) -> str:
        """Add a new connection."""
        connection_id = str(uuid.uuid4())
        self._connections[connection_id] = {
            "id": connection_id,
            "remote_address": remote_address,
            "connected_at": time.time(),
        }
        logger.info(f"A2A connection added: {connection_id} from {remote_address}")
        return connection_id

    async def _close_connection(self, connection_id: str) -> None:
        """Close a connection."""
        if connection_id in self._connections:
            del self._connections[connection_id]
            logger.info(f"A2A connection closed: {connection_id}")

    # ========== Skill Registration ==========

    def register_skill(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a skill.

        Args:
            name: Skill name.
            handler: Async function to handle the skill.
            description: Skill description.
            input_schema: JSON Schema for input.
        """
        self._skills[name] = {
            "handler": handler,
            "description": description,
            "input_schema": input_schema or {},
        }
        logger.info(f"A2A skill registered: {name}")

    def unregister_skill(self, name: str) -> None:
        """Unregister a skill."""
        if name in self._skills:
            del self._skills[name]

    # ========== Message Handlers ==========

    async def _handle_discover(
        self,
        connection_id: str,
        envelope: A2AEnvelope,
    ) -> A2AEnvelope:
        """Handle discover request."""
        skills_list = [
            {
                "name": name,
                "description": skill["description"],
                "input_schema": skill["input_schema"],
            }
            for name, skill in self._skills.items()
        ]

        return A2AEnvelope(
            sender_id=self._agent_id,
            receiver_id=envelope.sender_id,
            message_type="discover_response",
            payload={
                "agent_id": self._agent_id,
                "name": self._config.agent_name,
                "version": self._config.agent_version,
                "skills": skills_list,
                "capabilities": list(self._skills.keys()),
            },
            correlation_id=envelope.correlation_id,
        )

    async def _handle_skill_request(
        self,
        connection_id: str,
        envelope: A2AEnvelope,
    ) -> A2AEnvelope:
        """Handle skill request."""
        payload = envelope.payload
        skill_name = payload.get("skill_name")
        arguments = payload.get("arguments", {})

        if skill_name not in self._skills:
            return A2AEnvelope(
                sender_id=self._agent_id,
                receiver_id=envelope.sender_id,
                message_type="skill_response",
                payload={
                    "skill_id": payload.get("skill_id"),
                    "success": False,
                    "error": f"Skill not found: {skill_name}",
                },
                correlation_id=envelope.correlation_id,
            )

        skill = self._skills[skill_name]
        handler = skill["handler"]

        try:
            start_time = time.time()

            if asyncio.iscoroutinefunction(handler):
                result = await handler(arguments)
            else:
                result = handler(arguments)

            execution_time = time.time() - start_time

            return A2AEnvelope(
                sender_id=self._agent_id,
                receiver_id=envelope.sender_id,
                message_type="skill_response",
                payload={
                    "skill_id": payload.get("skill_id"),
                    "success": True,
                    "result": result,
                    "execution_time": execution_time,
                },
                correlation_id=envelope.correlation_id,
            )

        except Exception as e:
            logger.error(f"Skill execution error: {e}")
            return A2AEnvelope(
                sender_id=self._agent_id,
                receiver_id=envelope.sender_id,
                message_type="skill_response",
                payload={
                    "skill_id": payload.get("skill_id"),
                    "success": False,
                    "error": str(e),
                },
                correlation_id=envelope.correlation_id,
            )

    async def _handle_ping(
        self,
        connection_id: str,
        envelope: A2AEnvelope,
    ) -> A2AEnvelope:
        """Handle ping request."""
        return A2AEnvelope(
            sender_id=self._agent_id,
            receiver_id=envelope.sender_id,
            message_type="pong",
            payload={"timestamp": time.time()},
            correlation_id=envelope.correlation_id,
        )

    # ========== Message Handling ==========

    async def handle_message(
        self,
        connection_id: str,
        message: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Handle an incoming message.

        Args:
            connection_id: Connection that sent the message.
            message: The message.

        Returns:
            Optional response.
        """
        envelope = A2AEnvelope.from_dict(message)

        handler = self._message_handlers.get(envelope.message_type)
        if handler:
            try:
                response = await handler(connection_id, envelope)
                if response:
                    return response.to_dict()
            except Exception as e:
                logger.error(f"Message handler error: {e}")

        return None

    # ========== Utility Methods ==========

    def get_agent_info(self) -> A2AAgentInfo:
        """Get this agent's info."""
        return A2AAgentInfo(
            agent_id=self._agent_id,
            name=self._config.agent_name,
            description="A2A Agent Server",
            version=self._config.agent_version,
            capabilities=list(self._skills.keys()),
            skills=[
                {"name": name, "description": skill["description"]}
                for name, skill in self._skills.items()
            ],
            status="online" if self._running else "offline",
            endpoint=f"{self._config.host}:{self._config.port}",
        )

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        return {
            "host": self._config.host,
            "port": self._config.port,
            "running": self._running,
            "agent_id": self._agent_id,
            "connections": len(self._connections),
            "skills": len(self._skills),
            "uptime": time.time() - self._server["started_at"] if self._server else 0,
        }
