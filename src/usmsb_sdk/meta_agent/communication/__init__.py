# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
"""
MetaAgent Communication Module

This module implements the communication layer for MetaAgent using
OpenHarness's streaming event pattern.

Architecture:
- WebSocket: Command channel (user messages, plan confirmation, task cancellation)
- SSE: Progress channel (streaming text, tool calls, progress updates)

OpenHarness 精髓:
- StreamEvent pattern: async iterator yielding incremental events
- Event types: text_delta, tool_call, tool_result, progress, complete, error
- Hook mechanism for self-observation
"""

from .protocol import (
    ChatMessageType,
    ChatEventType,
    ChatStreamEvent,
    ChatCommand,
    ChatSessionState,
    TaskType,
)
from .chat_session import ChatSession
from .websocket_handler import ChatWebSocketHandler
from .sse_manager import SSEManager

__all__ = [
    "ChatMessageType",
    "ChatEventType",
    "ChatStreamEvent",
    "ChatCommand",
    "ChatSessionState",
    "TaskType",
    "ChatSession",
    "ChatWebSocketHandler",
    "SSEManager",
]
