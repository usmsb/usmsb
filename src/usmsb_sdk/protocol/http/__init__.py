"""
HTTP Protocol Module

This module provides HTTP protocol implementations for both client and server.

Usage:
    # As client
    from usmsb_sdk.protocol.http import HTTPClient
    client = HTTPClient()
    await client.connect("https://api.example.com")
    response = await client.call_skill("example", {"arg": "value"})

    # As server
    from usmsb_sdk.protocol.http import HTTPServer
    server = HTTPServer(port=8080)
    await server.start()
"""

from usmsb_sdk.protocol.http.client import (
    HTTPAuthConfig,
    HTTPClient,
    HTTPEndpointConfig,
    HTTPRequest,
    HTTPResponse,
    HTTPSkillEndpoint,
)
from usmsb_sdk.protocol.http.server import (
    HTTPRoute,
    HTTPRouter,
    HTTPServer,
    HTTPServerConfig,
)

__all__ = [
    # Client
    "HTTPClient",
    "HTTPEndpointConfig",
    "HTTPAuthConfig",
    "HTTPRequest",
    "HTTPResponse",
    "HTTPSkillEndpoint",

    # Server
    "HTTPServer",
    "HTTPServerConfig",
    "HTTPRoute",
    "HTTPRouter",
]
