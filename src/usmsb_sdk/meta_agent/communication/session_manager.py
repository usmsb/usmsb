# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
"""
ChatSessionManager - 会话管理器

协调 WebSocketHandler、SSEManager 和 ChatSession

OpenHarness 精髓：
- Facade 模式 - 提供统一入口
- 状态管理 - 协调多个组件
- 事件驱动 - 组件间通过事件通信
"""

import asyncio
import logging
from typing import Any

from .chat_session import ChatSession
from .protocol import TaskType
from .sse_manager import SSEManager
from .websocket_handler import ChatWebSocketHandler

logger = logging.getLogger(__name__)


class ChatSessionManager:
    """
    聊天会话管理器

    职责：
    1. 管理 ChatSession 实例
    2. 协调 WebSocket 和 SSE
    3. 提供统一的会话访问接口

    Facade Pattern - 统一入口
    """

    def __init__(self, meta_agent: Any):
        """
        Args:
            meta_agent: MetaAgent 实例
        """
        self.meta_agent = meta_agent
        self._sessions: dict[str, ChatSession] = {}
        self._sse_manager = SSEManager()
        self._ws_handler = ChatWebSocketHandler(session_manager=self)

    # ==================== Session Management ====================

    async def get_or_create_session(
        self,
        session_id: str,
        wallet_address: str | None,
    ) -> ChatSession:
        """
        获取或创建会话

        Args:
            session_id: 会话 ID
            wallet_address: 钱包地址

        Returns:
            ChatSession 实例
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = ChatSession(
                session_id=session_id,
                wallet_address=wallet_address,
                meta_agent=self.meta_agent,
            )
            logger.info(f"[SessionManager] Created session {session_id}")
        return self._sessions[session_id]

    def get_session(self, session_id: str) -> ChatSession | None:
        """获取会话"""
        return self._sessions.get(session_id)

    def remove_session(self, session_id: str) -> None:
        """移除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            self._sse_manager.unsubscribe(session_id)
            logger.info(f"[SessionManager] Removed session {session_id}")

    # ==================== Event Broadcasting ====================

    async def broadcast_session_events(
        self,
        session_id: str,
        chat_session: ChatSession,
        message: str,
    ) -> None:
        """
        广播会话事件到 SSE

        从 chat_stream 获取事件并推送到 SSE

        Args:
            session_id: 会话 ID
            chat_session: ChatSession 实例
            message: 用户消息
        """
        async for event in chat_session.chat_stream(message):
            await self._sse_manager.push_event(session_id, event)

    async def broadcast_plan_confirmation(
        self,
        session_id: str,
        chat_session: ChatSession,
        plan_id: str,
    ) -> None:
        """
        广播计划确认执行

        Args:
            session_id: 会话 ID
            chat_session: ChatSession 实例
            plan_id: 计划 ID
        """
        async for event in chat_session.confirm_plan(plan_id):
            await self._sse_manager.push_event(session_id, event)

    # ==================== SSE Stream ====================

    async def create_sse_stream(self, session_id: str) -> Any:
        """
        创建 SSE 流

        用于 FastAPI endpoint

        Args:
            session_id: 会话 ID

        Returns:
            AsyncIterator[str] - SSE 事件流
        """
        return self._sse_manager.create_stream(session_id)

    # ==================== WebSocket Handler Access ====================

    @property
    def ws_handler(self) -> ChatWebSocketHandler:
        """获取 WebSocket 处理器"""
        return self._ws_handler

    @property
    def sse_manager(self) -> SSEManager:
        """获取 SSE 管理器"""
        return self._sse_manager

    # ==================== Lifecycle ====================

    async def start(self) -> None:
        """启动管理器"""
        await self._ws_handler.start()
        logger.info("[SessionManager] Started")

    async def stop(self) -> None:
        """停止管理器"""
        await self._ws_handler.stop()

        # 清理所有会话
        for session_id in list(self._sessions.keys()):
            self.remove_session(session_id)

        logger.info("[SessionManager] Stopped")

    # ==================== Stats ====================

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "active_sessions": len(self._sessions),
            "active_sse_connections": self._sse_manager.get_active_count(),
            "sessions": {
                sid: session.get_state()
                for sid, session in self._sessions.items()
            },
        }
