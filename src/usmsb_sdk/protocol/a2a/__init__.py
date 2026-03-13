"""
A2A (Agent-to-Agent) Protocol Module

This module provides A2A protocol implementations for direct agent communication.

Usage:
    # As client
    from usmsb_sdk.protocol.a2a import A2AClient
    client = A2AClient()
    await client.connect("https://agent.example.com/a2a")
    response = await client.call_skill("example", {"arg": "value"})

    # As server
    from usmsb_sdk.protocol.a2a import A2AServer
    server = A2AServer(port=9000)
    await server.start()
"""

from usmsb_sdk.protocol.a2a.client import (
    A2AClient,
    A2AEnvelope,
    A2ASkillRequest,
    A2ASkillResponse,
    A2AAgentInfo,
)

from usmsb_sdk.protocol.a2a.server import A2AServer


__all__ = [
    # Client
    "A2AClient",
    "A2AEnvelope",
    "A2ASkillRequest",
    "A2ASkillResponse",
    "A2AAgentInfo",

    # Server
    "A2AServer",
]
