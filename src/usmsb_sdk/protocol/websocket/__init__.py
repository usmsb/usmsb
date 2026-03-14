"""
WebSocket Protocol Module

This module provides WebSocket protocol implementations for both client and server.

Usage:
    # As client
    from usmsb_sdk.protocol.websocket import WebSocketClient
    client = WebSocketClient()
    await client.connect("wss://api.example.com/ws")
    response = await client.call_skill("example", {"arg": "value"})

    # As server
    from usmsb_sdk.protocol.websocket import WebSocketServer
    server = WebSocketServer(port=8765)
    await server.start()
"""

from usmsb_sdk.protocol.websocket.client import (
    WebSocketClient,
    WebSocketConfig,
    WebSocketEvent,
    WebSocketMessage,
    WebSocketSubscription,
)
from usmsb_sdk.protocol.websocket.server import (
    WebSocketConnection,
    WebSocketServer,
    WebSocketServerConfig,
)

__all__ = [
    # Client
    "WebSocketClient",
    "WebSocketConfig",
    "WebSocketMessage",
    "WebSocketEvent",
    "WebSocketSubscription",

    # Server
    "WebSocketServer",
    "WebSocketServerConfig",
    "WebSocketConnection",
]
