"""
WebSocket Mixin for AgentPlatform.

Adds real-time notification support to AgentPlatform.
"""

import asyncio
import logging
from typing import Any, Callable

import aiohttp

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """
    WebSocket connection to the platform.

    Handles authentication and message routing.
    """

    def __init__(self, url: str, agent_id: str, api_key: str):
        self.url = url
        self.agent_id = agent_id
        self.api_key = api_key
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._session: aiohttp.ClientSession | None = None

    async def connect(self) -> bool:
        """Connect to WebSocket and authenticate."""
        try:
            self._session = aiohttp.ClientSession()

            headers = {
                "X-Agent-ID": self.agent_id,
                "X-API-Key": self.api_key,
            }

            self._ws = await self._session.ws_connect(
                self.url,
                headers=headers,
                autoping=True,
                heartbeat=30,
            )

            await self._ws.send_json({
                "type": "auth",
                "agent_id": self.agent_id,
                "api_key": self.api_key,
            })

            msg = await self._ws.receive_json()
            if msg.get("type") == "auth_success":
                return True
            else:
                logger.error(f"WebSocket auth failed: {msg}")
                return False

        except Exception as e:
            logger.error(f"WebSocket connect error: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        if self._ws:
            await self._ws.close()
            self._ws = None
        if self._session:
            await self._session.close()
            self._session = None

    async def receive(self) -> dict | None:
        """Receive a message from WebSocket."""
        if not self._ws:
            return None

        try:
            msg = await self._ws.receive_json()
            return msg
        except aiohttp.WSServerDisconnected:
            return None
        except Exception as e:
            logger.error(f"WebSocket receive error: {e}")
            return None

    async def send(self, message: dict) -> bool:
        """Send a message via WebSocket."""
        if not self._ws:
            return False

        try:
            await self._ws.send_json(message)
            return True
        except Exception as e:
            logger.error(f"WebSocket send error: {e}")
            return False


class WebSocketMixin:
    """
    Mixin class that adds WebSocket notification support.

    Use with AgentPlatform:
        class EnhancedAgentPlatform(WebSocketMixin, AgentPlatform):
            pass
    """

    def __init__(self, *args, **kwargs):
        # WebSocket support
        self._ws_connection: WebSocketConnection | None = None
        self._ws_task: asyncio.Task | None = None
        self._ws_connected: bool = False
        self._ws_reconnect_attempts: int = 0
        self._ws_max_reconnect: int = 5

        # Event callbacks
        self._negotiation_callbacks: list[Callable] = []
        self._opportunity_callbacks: list[Callable] = []
        self._message_callbacks: list[Callable] = []
        self._work_callbacks: list[Callable] = []
        self._notification_callbacks: list[Callable] = []
        self._status_callbacks: list[Callable] = []

    async def connect_websocket(self) -> bool:
        """
        Connect to the platform WebSocket for real-time events.

        Returns:
            True if connection successful.
        """
        if self._ws_connected:
            logger.warning("WebSocket already connected")
            return True

        try:
            ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
            ws_url = f"{ws_url}/ws"

            self._ws_connection = WebSocketConnection(
                url=ws_url,
                agent_id=self.agent_id,
                api_key=self.api_key,
            )

            connected = await self._ws_connection.connect()
            if connected:
                self._ws_connected = True
                self._ws_reconnect_attempts = 0
                self._ws_task = asyncio.create_task(self._ws_receive_loop())
                logger.info(f"WebSocket connected: {ws_url}")
                return True
            else:
                logger.error("Failed to connect WebSocket")
                return False

        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            return False

    async def disconnect_websocket(self) -> None:
        """Disconnect from the platform WebSocket."""
        self._ws_connected = False

        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
            self._ws_task = None

        if self._ws_connection:
            await self._ws_connection.disconnect()
            self._ws_connection = None

        logger.info("WebSocket disconnected")

    async def _ws_receive_loop(self) -> None:
        """Background loop to receive WebSocket messages."""
        while self._ws_connected and self._ws_connection:
            try:
                message = await self._ws_connection.receive()
                if message is None:
                    break
                await self._dispatch_ws_message(message)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket receive error: {e}")
                await asyncio.sleep(1)

        if self._ws_connected and self._ws_reconnect_attempts < self._ws_max_reconnect:
            self._ws_reconnect_attempts += 1
            logger.info(f"Attempting WebSocket reconnect ({self._ws_reconnect_attempts}/{self._ws_max_reconnect})")
            await asyncio.sleep(2)
            if self._ws_connected:
                await self.connect_websocket()

    async def _dispatch_ws_message(self, message: dict) -> None:
        """Dispatch WebSocket message to appropriate callbacks."""
        msg_type = message.get("type", "")

        handlers = {
            "negotiation_request": self._negotiation_callbacks,
            "opportunity": self._opportunity_callbacks,
            "message": self._message_callbacks,
            "work_assignment": self._work_callbacks,
            "notification": self._notification_callbacks,
            "status_update": self._status_callbacks,
        }

        callbacks = handlers.get(msg_type, [])
        for cb in callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(message.get("data", {}))
                else:
                    cb(message.get("data", {}))
            except Exception as e:
                logger.error(f"Callback error for {msg_type}: {e}")

    async def on_negotiation_request(self, callback: Callable) -> None:
        """Register callback for incoming negotiation requests."""
        self._negotiation_callbacks.append(callback)

    async def on_opportunity(self, callback: Callable) -> None:
        """Register callback for new opportunities."""
        self._opportunity_callbacks.append(callback)

    async def on_message(self, callback: Callable) -> None:
        """Register callback for incoming messages."""
        self._message_callbacks.append(callback)

    async def on_work_assignment(self, callback: Callable) -> None:
        """Register callback for work assignments."""
        self._work_callbacks.append(callback)

    async def on_notification(self, callback: Callable) -> None:
        """Register callback for general notifications."""
        self._notification_callbacks.append(callback)

    async def on_status_update(self, callback: Callable) -> None:
        """Register callback for status updates."""
        self._status_callbacks.append(callback)
