# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
"""
ChatWebSocketHandler - WebSocket 指令通道

WebSocket 通道职责：
- 接收用户指令 (user_message, confirm_plan, cancel_task)
- 发送指令确认 (message_received, error)

OpenHarness 精髓：
- 全双工通信
- 事件驱动处理
- 状态机管理
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from .protocol import (
    ChatMessageType,
    ChatCommand,
    ChatSessionState,
)

logger = logging.getLogger(__name__)


@dataclass
class WSClient:
    """WebSocket 客户端"""
    websocket: WebSocket
    session_id: str
    wallet_address: str | None
    connected_at: float = field(default_factory=time.time)
    last_ping: float = field(default_factory=time.time)


class ChatWebSocketHandler:
    """
    WebSocket 指令处理器

    职责：
    1. 管理 WebSocket 连接
    2. 接收和解析指令
    3. 路由到 ChatSession 处理
    4. 发送指令确认

    OpenHarness 精髓：
    - 全双工事件驱动
    - 连接状态管理
    - 心跳检测
    """

    def __init__(self, session_manager: Any = None):  # ChatSessionManager
        """
        Args:
            session_manager: ChatSessionManager 实例
        """
        self._session_manager = session_manager
        self._clients: dict[str, WSClient] = {}  # session_id -> WSClient
        self._running = False
        self._ping_task: asyncio.Task | None = None
        self._tasks: dict[str, asyncio.Task] = {}  # 跟踪每个 session_id 的活跃任务

    async def start(self) -> None:
        """启动处理器"""
        self._running = True
        self._ping_task = asyncio.create_task(self._ping_loop())
        logger.info("[WSHandler] ChatWebSocketHandler started")

    async def stop(self) -> None:
        """停止处理器"""
        self._running = False

        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass

        # 关闭所有连接
        for client in list(self._clients.values()):
            try:
                await client.websocket.close()
            except Exception:
                pass

        self._clients.clear()
        logger.info("[WSHandler] ChatWebSocketHandler stopped")

    async def handle_connection(
        self,
        websocket: WebSocket,
        wallet_address: str,
        frontend_session_id: str | None = None,
    ) -> None:
        """
        处理新的 WebSocket 连接

        Args:
            websocket: WebSocket 连接
            wallet_address: 钱包地址
            frontend_session_id: 前端传递的 session_id，确保与 SSE 一致
        """
        # 优先使用前端传递的 session_id，确保与 SSE 使用同一 session_id
        # 如果前端未传递，则派生一个（兼容旧版本）
        if frontend_session_id:
            session_id = frontend_session_id
        else:
            import time
            ts = int(time.time() // 60) * 60 * 1000
            session_id = f"ws_{wallet_address}_{ts}"
            logger.warning(f"[WSHandler] 前端未传递 session_id，使用派生值: {session_id}")

        logger.info(f"[WSHandler] handle_connection START: session_id={session_id}, wallet={wallet_address}")
        
        # 拒绝重复连接：如果已有同 session_id 的连接，先关闭旧连接
        existing = self._clients.get(session_id)
        if existing:
            logger.warning(f"[WSHandler] Duplicate WS connection for session_id={session_id}, closing old connection")
            try:
                await existing.websocket.close(code=1000, reason="Replaced by new connection")
            except Exception:
                pass
        
        try:
            await websocket.accept()
            logger.info(f"[WSHandler] WebSocket accepted: {session_id}")

            client = WSClient(
                websocket=websocket,
                session_id=session_id,
                wallet_address=wallet_address,
            )
            self._clients[session_id] = client

            logger.info(f"[WSHandler] Client connected: {session_id} ({wallet_address})")

            # 发送连接确认
            await self._send(
                websocket,
                ChatMessageType.MESSAGE_RECEIVED,
                {
                    "session_id": session_id,
                    "status": "connected",
                    "message": "WebSocket 连接已建立",
                },
            )

            # 消息循环
            while True:
                try:
                    data = await websocket.receive_json()
                    logger.info(f"[WSHandler] RECEIVED MESSAGE: {data}")
                    logger.info(f"[WSHandler] Current clients BEFORE _handle_message: {list(self._clients.keys())}")
                    await self._handle_message(session_id, data)
                except WebSocketDisconnect:
                    logger.info(f"[WSHandler] Client disconnected: {session_id}")
                    break
                except json.JSONDecodeError:
                    await self._send_error(
                        websocket,
                        "Invalid JSON format",
                    )
                except Exception as e:
                    logger.error(f"[WSHandler] Error in message loop: {e}", exc_info=True)
                    await self._send_error(websocket, f"Error: {e}")

        except Exception as e:
            logger.error(f"[WSHandler] Connection error: {e}")
        finally:
            if session_id in self._clients:
                del self._clients[session_id]
            # 取消该 session_id 的活跃任务
            if session_id in self._tasks:
                task = self._tasks.pop(session_id)
                task.cancel()
                logger.info(f"[WSHandler] Cancelled task on disconnect for session_id={session_id}")

    async def _handle_message(
        self,
        session_id: str,
        data: dict,
    ) -> None:
        """
        处理收到的消息

        Args:
            session_id: 会话 ID
            data: 消息数据
        """
        client = self._clients.get(session_id)
        if not client:
            return

        try:
            command = ChatCommand.from_dict(data)
        except Exception as e:
            logger.error(f"[WSHandler] Invalid command: {e}")
            await self._send_error(client.websocket, f"Invalid command: {e}")
            return

        logger.info(f"[WSHandler] Command: {command.command_type.value} for {session_id}")

        # 根据指令类型处理
        if command.command_type == ChatMessageType.USER_MESSAGE:
            await self._handle_user_message(session_id, command)
        elif command.command_type == ChatMessageType.CONFIRM_PLAN:
            await self._handle_confirm_plan(session_id, command)
        elif command.command_type == ChatMessageType.CANCEL_TASK:
            await self._handle_cancel_task(session_id, command)
        elif command.command_type == ChatMessageType.PAUSE_TASK:
            await self._handle_pause_task(session_id, command)
        elif command.command_type == ChatMessageType.RESUME_TASK:
            await self._handle_resume_task(session_id, command)
        elif command.command_type == ChatMessageType.GET_STATUS:
            await self._handle_get_status(session_id, command)
        else:
            await self._send_error(
                client.websocket,
                f"Unknown command type: {command.command_type}",
            )

    async def _handle_user_message(
        self,
        session_id: str,
        command: ChatCommand,
    ) -> None:
        """
        处理用户消息

        触发流程：
        1. 发送消息确认
        2. 获取或创建 ChatSession
        3. 启动 chat_stream
        4. SSE 连接监听同一 session
        """
        logger.info(f"[WSHandler] _handle_user_message ENTRY: session_id={session_id}, clients={list(self._clients.keys())}")
        client = self._clients.get(session_id)
        if not client:
            logger.warning(f"[WSHandler] _handle_user_message: client not found for session_id={session_id}")
            return

        message = command.payload.get("message", "")
        if not message:
            await self._send_error(client.websocket, "Empty message")
            return

        # 发送确认
        await self._send(
            client.websocket,
            ChatMessageType.MESSAGE_RECEIVED,
            {
                "session_id": session_id,
                "message": "消息已收到，正在处理...",
                "message_preview": message[:50],
            },
        )

        # 获取或创建 session
        if self._session_manager:
            chat_session = await self._session_manager.get_or_create_session(
                session_id=session_id,
                wallet_address=client.wallet_address,
            )
        else:
            logger.warning("[WSHandler] No session manager, cannot process message")
            await self._send_error(client.websocket, "Session manager not available")
            return

        # 通知 SSE 管理器有新的 chat_stream
        # (SSE 管理器会负责推送事件到前端)
        if self._session_manager:
            # 取消该 session_id 的旧任务（如果有）
            if session_id in self._tasks:
                old_task = self._tasks.pop(session_id)
                old_task.cancel()
                logger.info(f"[WSHandler] Cancelled old task for session_id={session_id}")

            async def broadcast_with_error_handling():
                try:
                    async for event in chat_session.chat_stream(message):
                        await self._session_manager._sse_manager.push_event(session_id, event)
                except asyncio.CancelledError:
                    logger.info(f"[WSHandler] Broadcast task cancelled for session_id={session_id}")
                    raise
                except Exception as e:
                    logger.error(f"[WSHandler] broadcast_session_events error: {e}", exc_info=True)

            task = asyncio.create_task(broadcast_with_error_handling())
            self._tasks[session_id] = task

    async def _handle_confirm_plan(
        self,
        session_id: str,
        command: ChatCommand,
    ) -> None:
        """处理计划确认"""
        client = self._clients.get(session_id)
        if not client:
            return

        plan_id = command.payload.get("plan_id")
        if not plan_id:
            await self._send_error(client.websocket, "Missing plan_id")
            return

        await self._send(
            client.websocket,
            ChatMessageType.MESSAGE_RECEIVED,
            {
                "type": "plan_confirmed",
                "plan_id": plan_id,
                "message": "计划确认，正在执行...",
            },
        )

        # 执行计划
        if self._session_manager:
            chat_session = self._session_manager.get_session(session_id)
            if chat_session:
                asyncio.create_task(
                    self._session_manager.broadcast_plan_confirmation(session_id, chat_session, plan_id)
                )

    async def _handle_cancel_task(
        self,
        session_id: str,
        command: ChatCommand,
    ) -> None:
        """处理取消任务"""
        client = self._clients.get(session_id)
        if not client:
            return

        task_id = command.payload.get("task_id")
        if not task_id:
            await self._send_error(client.websocket, "Missing task_id")
            return

        if self._session_manager:
            chat_session = self._session_manager.get_session(session_id)
            if chat_session:
                success = chat_session.cancel_task(task_id)
                await self._send(
                    client.websocket,
                    ChatMessageType.MESSAGE_RECEIVED,
                    {
                        "type": "task_cancelled",
                        "task_id": task_id,
                        "success": success,
                    },
                )

    async def _handle_pause_task(
        self,
        session_id: str,
        command: ChatCommand,
    ) -> None:
        """处理暂停任务"""
        client = self._clients.get(session_id)
        if not client:
            return

        await self._send(
            client.websocket,
            ChatMessageType.MESSAGE_RECEIVED,
            {"type": "task_paused"},
        )

    async def _handle_resume_task(
        self,
        session_id: str,
        command: ChatCommand,
    ) -> None:
        """处理恢复任务"""
        client = self._clients.get(session_id)
        if not client:
            return

        await self._send(
            client.websocket,
            ChatMessageType.MESSAGE_RECEIVED,
            {"type": "task_resumed"},
        )

    async def _handle_get_status(
        self,
        session_id: str,
        command: ChatCommand,
    ) -> None:
        """处理获取状态"""
        client = self._clients.get(session_id)
        if not client:
            return

        status = {}
        if self._session_manager:
            chat_session = self._session_manager.get_session(session_id)
            if chat_session:
                status = chat_session.get_state()

        await self._send(
            client.websocket,
            ChatMessageType.MESSAGE_RECEIVED,
            {"type": "status", "status": status},
        )

    async def _send(
        self,
        websocket: WebSocket,
        message_type: ChatMessageType,
        data: dict,
    ) -> None:
        """发送消息"""
        try:
            await websocket.send_json({
                "type": message_type.value,
                "data": data,
                "timestamp": time.time(),
            })
        except Exception as e:
            logger.error(f"[WSHandler] Send error: {e}")

    async def _send_error(
        self,
        websocket: WebSocket,
        error: str,
    ) -> None:
        """发送错误"""
        await self._send(
            websocket,
            ChatMessageType.ERROR,
            {"error": error},
        )

    async def _ping_loop(self) -> None:
        """心跳检测循环"""
        while self._running:
            try:
                await asyncio.sleep(30)
                current_time = time.time()

                # 检测超时连接
                stale_sessions = []
                for session_id, client in self._clients.items():
                    if current_time - client.last_ping > 60:
                        stale_sessions.append(session_id)

                # 关闭超时连接
                for session_id in stale_sessions:
                    client = self._clients.get(session_id)
                    if client:
                        try:
                            await client.websocket.close()
                        except Exception:
                            pass
                        logger.info(f"[WSHandler] Stale connection removed: {session_id}")

                    if session_id in self._clients:
                        del self._clients[session_id]

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[WSHandler] Ping loop error: {e}")
