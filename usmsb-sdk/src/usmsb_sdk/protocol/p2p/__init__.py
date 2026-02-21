"""
P2P (Peer-to-Peer) Protocol Module

This module provides P2P protocol implementation for decentralized communication.

Usage:
    from usmsb_sdk.protocol.p2p import P2PHandler
    handler = P2PHandler()
    await handler.connect("bootstrap.example.com:9000")
    result = await handler.call_skill("example", {"arg": "value"})
"""

from usmsb_sdk.protocol.p2p.handler import (
    P2PHandler,
    P2PNodeInfo,
    P2PMessage,
    P2PSkillRequest,
    P2PSkillResponse,
    P2PDHTEntry,
)


__all__ = [
    "P2PHandler",
    "P2PNodeInfo",
    "P2PMessage",
    "P2PSkillRequest",
    "P2PSkillResponse",
    "P2PDHTEntry",
]
