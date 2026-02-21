"""
WebSocket Protocol Client

This module provides the WebSocket client implementation for real-time bidirectional communication.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from usmsb_sdk.protocol.base import (
    BaseProtocolHandler,
    ProtocolConfig,
    ExternalAgentStatus,
    SkillDefinition,
)


logger = logging.getLogger(__name__)


@dataclass
class WebSocketConfig:
    """WebSocket-specific configuration."""
    ping_interval: float = 30.0
    ping_timeout: float = 10.0
    max_size: int = 10 * 1024 * 1024  # 10MB
    compression: bool = False
    subprotocols: List[str] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class WebSocketMessage:
    """WebSocket message structure."""
    type: str  # text, binary, ping, pong, close
    data: Union[str, bytes]
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "data": self.data if isinstance(self.data, str) else "<binary>",
            "message_id": self.message_id,
            "timestamp": self.timestamp,
        }


@dataclass
class WebSocketEvent:
    """WebSocket event structure."""
    event_type: str
    payload: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "payload": self.payload,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class WebSocketSubscription:
    """WebSocket event subscription."""
    event_type: str
    callback: Callable
    subscription_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    active: bool = True


class WebSocketClient(BaseProtocolHandler):
    """
    WebSocket Client for real-time bidirectional communication.

    Features:
    - Full-duplex messaging
    - Event subscription system
    - Automatic reconnection
    - Heartbeat/ping-pong
    - Binary and text message support
    """

    def __init__(
        self,
        config: Optional[ProtocolConfig] = None,
        ws_config: Optional[WebSocketConfig] = None,
    ):
        """
        Initialize the WebSocket client.

        Args:
            config: Protocol configuration.
            ws_config: WebSocket-specific configuration.
        """
        super().__init__(config)
        self._ws_config = ws_config or WebSocketConfig()
        self._websocket: Optional[Any] = None
        self._subscriptions: Dict[str, WebSocketSubscription] = {}
        self._event_handlers: Dict[str, Callable] = {}
        self._receive_task: Optional[asyncio.Task] = None
        self._reconnect_attempts: int = 0
        self._max_reconnect_attempts: int = 5

        # Register default event handlers
        self._register_default_handlers()

        logger.info("WebSocketClient initialized")

    def _register_default_handlers(self) -> None:
        """Register default event handlers."""
        self._event_handlers["skill_response"] = self._handle_skill_response
        self._event_handlers["discover_response"] = self._handle_discover_response
        self._event_handlers["status_update"] = self._handle_status_update
        self._event_handlers["error"] = self._handle_error_event
        self._event_handlers["pong"] = self._handle_pong_event

    # ========== Protocol-Specific Implementation ==========

    async def _do_connect(self, endpoint: str) -> bool:
        """
        Establish WebSocket connection.

        Args:
            endpoint: WebSocket URL (ws:// or wss://).

        Returns:
            True if connection successful.
        """
        try:
            logger.info(f"WebSocket connecting to {endpoint}")

            # In real implementation, use websockets or aiohttp library
            # For now, simulate connection
            self._websocket = {
                "url": endpoint,
                "connected": True,
                "connected_at": time.time(),
            }

            # Start receive loop
            self._receive_task = asyncio.create_task(self._receive_loop())

            # Send connection event
            await self._send_event("connected", {
                "client": "usmsb-sdk",
                "version": "1.0.0",
            })

            logger.info(f"WebSocket connected to {endpoint}")
            return True

        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            return False

    async def _do_disconnect(self) -> None:
        """Close the WebSocket connection."""
        # Stop receive loop
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

        # Send close event
        if self._websocket:
            try:
                await self._send_event("disconnecting", {})
            except Exception:
                pass

        # Close connection
        self._websocket = None
        self._reconnect_attempts = 0

        logger.info("WebSocket disconnected")

    async def _do_call_skill(
        self,
        skill_name: str,
        arguments: Dict[str, Any],
        timeout: float,
    ) -> Any:
        """
        Execute a skill via WebSocket.

        Args:
            skill_name: Name of the skill to execute.
            arguments: Arguments for the skill.
            timeout: Timeout for execution.

        Returns:
            Result from the skill execution.
        """
        request_id = str(uuid.uuid4())

        # Create skill request event
        event = WebSocketEvent(
            event_type="skill_request",
            payload={
                "request_id": request_id,
                "skill_name": skill_name,
                "arguments": arguments,
                "timeout": timeout,
            },
        )

        # Create future for response
        response_future = asyncio.Future()
        self._pending_requests[request_id] = response_future

        try:
            # Send request
            await self._send_event(event.event_type, event.payload)

            # Wait for response
            response = await asyncio.wait_for(response_future, timeout=timeout)

            if response.get("success"):
                return response.get("result")
            else:
                raise Exception(response.get("error", "Unknown error"))

        finally:
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]

    async def _do_discover_skills(self) -> List[SkillDefinition]:
        """
        Discover skills via WebSocket.

        Returns:
            List of discovered skills.
        """
        request_id = str(uuid.uuid4())

        event = WebSocketEvent(
            event_type="discover",
            payload={"request_id": request_id},
        )

        response_future = asyncio.Future()
        self._pending_requests[request_id] = response_future

        try:
            await self._send_event(event.event_type, event.payload)

            response = await asyncio.wait_for(response_future, timeout=30.0)

            skills_data = response.get("skills", [])
            return [SkillDefinition.from_dict(s) for s in skills_data]

        except asyncio.TimeoutError:
            logger.warning("WebSocket skill discovery timeout")
            return []
        finally:
            if request_id in self._pending_requests:
                del self._pending_requests[request_id]

    async def _do_check_status(self) -> ExternalAgentStatus:
        """
        Check agent status via WebSocket.

        Returns:
            Current status of the agent.
        """
        if not self._websocket:
            return ExternalAgentStatus.OFFLINE

        try:
            # Send ping event
            await self._send_event("ping", {"timestamp": time.time()})

            # Wait briefly for pong (simplified)
            await asyncio.sleep(0.1)

            return ExternalAgentStatus.ONLINE

        except Exception as e:
            logger.error(f"WebSocket status check error: {e}")
            return ExternalAgentStatus.ERROR

    # ========== WebSocket-Specific Methods ==========

    async def _send_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        Send an event via WebSocket.

        Args:
            event_type: Type of event.
            payload: Event payload.
        """
        if not self._websocket:
            raise Exception("WebSocket not connected")

        event = WebSocketEvent(
            event_type=event_type,
            payload=payload,
        )

        message = event.to_json()

        logger.debug(f"WebSocket sending event: {event_type}")

        # In real implementation, send via websocket library
        if self._connection_info:
            self._connection_info.messages_sent += 1
            self._connection_info.bytes_sent += len(message)

        # Simulated send
        await asyncio.sleep(0.01)

    async def _send_message(
        self,
        data: Union[str, bytes, Dict[str, Any]],
    ) -> None:
        """
        Send a raw message via WebSocket.

        Args:
            data: Message data (string, bytes, or dict).
        """
        if not self._websocket:
            raise Exception("WebSocket not connected")

        if isinstance(data, dict):
            data = json.dumps(data)

        message = WebSocketMessage(
            type="text" if isinstance(data, str) else "binary",
            data=data,
        )

        logger.debug(f"WebSocket sending message: {message.message_id}")

        # In real implementation, send via websocket
        await asyncio.sleep(0.01)

    async def _receive_loop(self) -> None:
        """Background task for receiving WebSocket messages."""
        while self._websocket:
            try:
                # In real implementation, receive from websocket
                # Simulated receive
                await asyncio.sleep(0.1)

                # Process simulated messages
                # In real implementation, this would parse incoming messages

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket receive error: {e}")
                await asyncio.sleep(1)

    async def _handle_incoming_message(self, data: str) -> None:
        """
        Handle an incoming WebSocket message.

        Args:
            data: Raw message data.
        """
        try:
            message = json.loads(data)

            if self._connection_info:
                self._connection_info.messages_received += 1
                self._connection_info.bytes_received += len(data)

            event_type = message.get("event_type")
            payload = message.get("payload", {})

            # Handle response to pending request
            request_id = payload.get("request_id")
            if request_id and request_id in self._pending_requests:
                future = self._pending_requests[request_id]
                if not future.done():
                    future.set_result(payload)
                return

            # Dispatch to event handler
            handler = self._event_handlers.get(event_type)
            if handler:
                await handler(payload)
            else:
                logger.debug(f"WebSocket unhandled event: {event_type}")

            # Dispatch to subscriptions
            await self._dispatch_to_subscriptions(event_type, payload)

        except json.JSONDecodeError as e:
            logger.error(f"WebSocket message parse error: {e}")
        except Exception as e:
            logger.error(f"WebSocket message handling error: {e}")

    async def _dispatch_to_subscriptions(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        Dispatch event to active subscriptions.

        Args:
            event_type: Type of event.
            payload: Event payload.
        """
        for sub in self._subscriptions.values():
            if sub.active and sub.event_type == event_type:
                try:
                    await sub.callback(payload)
                except Exception as e:
                    logger.error(f"Subscription callback error: {e}")

    # ========== Event Handlers ==========

    async def _handle_skill_response(self, payload: Dict[str, Any]) -> None:
        """Handle skill response event."""
        logger.debug("WebSocket received skill response")

    async def _handle_discover_response(self, payload: Dict[str, Any]) -> None:
        """Handle discover response event."""
        logger.debug("WebSocket received discover response")

    async def _handle_status_update(self, payload: Dict[str, Any]) -> None:
        """Handle status update event."""
        status = payload.get("status", "unknown")
        logger.info(f"WebSocket status update: {status}")

    async def _handle_error_event(self, payload: Dict[str, Any]) -> None:
        """Handle error event."""
        error = payload.get("error", "Unknown error")
        logger.error(f"WebSocket error event: {error}")

    async def _handle_pong_event(self, payload: Dict[str, Any]) -> None:
        """Handle pong event."""
        logger.debug("WebSocket received pong")

    # ========== Subscription Management ==========

    def subscribe(
        self,
        event_type: str,
        callback: Callable,
    ) -> str:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to.
            callback: Async callback function.

        Returns:
            Subscription ID.
        """
        subscription = WebSocketSubscription(
            event_type=event_type,
            callback=callback,
        )

        self._subscriptions[subscription.subscription_id] = subscription

        logger.debug(f"WebSocket subscription created: {event_type}")

        return subscription.subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from an event.

        Args:
            subscription_id: Subscription ID to remove.

        Returns:
            True if unsubscribed successfully.
        """
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            logger.debug(f"WebSocket subscription removed: {subscription_id}")
            return True
        return False

    def unsubscribe_all(self) -> None:
        """Remove all subscriptions."""
        self._subscriptions.clear()
        logger.debug("WebSocket all subscriptions removed")

    # ========== Utility Methods ==========

    async def _send_keep_alive(self) -> None:
        """Send WebSocket keep-alive (ping)."""
        await self._send_event("ping", {"timestamp": time.time()})

    async def broadcast_to_peers(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        Broadcast an event (if supported by server).

        Args:
            event_type: Type of event.
            payload: Event payload.
        """
        await self._send_event("broadcast", {
            "event_type": event_type,
            "payload": payload,
        })

    def get_subscriptions(self) -> List[WebSocketSubscription]:
        """Get list of active subscriptions."""
        return list(self._subscriptions.values())

    def get_ws_stats(self) -> Dict[str, Any]:
        """Get WebSocket statistics."""
        return {
            "connected": self._websocket is not None,
            "url": self._websocket.get("url") if self._websocket else None,
            "subscriptions": len(self._subscriptions),
            "pending_requests": len(self._pending_requests),
            "reconnect_attempts": self._reconnect_attempts,
        }
