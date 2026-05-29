"""
JSONRPCHandler - JSON-RPC 2.0 请求处理

将 JSON-RPC 请求分发给 GoogleA2AHandler
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from usmsb_sdk.protocol.google_a2a.handler import GoogleA2AHandler


logger = logging.getLogger(__name__)


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 请求"""
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str = ""
    params: dict[str, Any] = {}


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 响应"""
    jsonrpc: str = "2.0"
    id: str | int | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class JSONRPCError(Exception):
    """JSON-RPC 错误"""
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class JSONRPCHandler:
    """
    JSON-RPC 请求处理器

    支持的 Google A2A 方法：
    - tasks/send     → on_send_task
    - tasks/get      → on_get_task
    - tasks/cancel   → on_cancel_task
    - tasks/list     → on_list_tasks
    - tasks/subscribe → on_subscribe_task (SSE)
    - agents/card    → on_get_agent_card
    - agents/extended_card → on_get_extended_agent_card
    """

    # 错误码
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    def __init__(self, google_a2a_handler: "GoogleA2AHandler"):
        self._handler = google_a2a_handler

    async def handle(self, request: dict) -> dict:
        """
        处理 JSON-RPC 请求

        Args:
            request: JSON-RPC 请求对象

        Returns:
            JSON-RPC 响应对象
        """
        # 验证 JSON-RPC 版本
        if request.get("jsonrpc") != "2.0":
            return self._error_response(
                request.get("id"),
                self.INVALID_REQUEST,
                "Invalid JSON-RPC version",
            )

        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        try:
            if method == "tasks/send":
                result = await self._handle_send_task(params)
            elif method == "tasks/get":
                result = await self._handle_get_task(params)
            elif method == "tasks/cancel":
                result = await self._handle_cancel_task(params)
            elif method == "tasks/list":
                result = await self._handle_list_tasks(params)
            elif method == "agents/card":
                result = await self._handle_get_agent_card()
            elif method == "agents/extended_card":
                result = await self._handle_get_extended_agent_card()
            else:
                return self._error_response(
                    req_id,
                    self.METHOD_NOT_FOUND,
                    f"Method not found: {method}",
                )

            return JSONRPCResponse(
                jsonrpc="2.0",
                id=req_id,
                result=result if isinstance(result, dict) else result,
            ).model_dump(exclude_none=True)

        except JSONRPCError as e:
            return self._error_response(req_id, e.code, e.message, e.data)
        except Exception as e:
            logger.exception(f"Internal error handling {method}")
            return self._error_response(
                req_id,
                self.INTERNAL_ERROR,
                f"Internal error: {e}",
            )

    def _error_response(
        self,
        req_id: str | int | None,
        code: int,
        message: str,
        data: Any = None,
    ) -> dict:
        """构建错误响应"""
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return JSONRPCResponse(
            jsonrpc="2.0",
            id=req_id,
            error=error,
        ).model_dump(exclude_none=True)

    async def _handle_send_task(self, params: dict) -> dict:
        """处理 tasks/send"""
        from usmsb_sdk.protocol.types.google_a2a import (
            SendMessageRequest,
            Message,
        )

        msg_data = params.get("message", {})
        message = Message.model_validate(msg_data)

        config_data = params.get("configuration")
        from usmsb_sdk.protocol.types.google_a2a import SendMessageConfiguration

        req = SendMessageRequest(
            tenant=params.get("tenant", ""),
            skill_id=params.get("skillId", ""),
            message=message,
            configuration=SendMessageConfiguration.model_validate(config_data) if config_data else SendMessageConfiguration(),
            metadata=params.get("metadata", {}),
        )

        result = await self._handler.on_send_task(req)

        # 如果是异步迭代器（流式），返回任务 ID
        if asyncio.iscoroutine(result) or hasattr(result, "__aiter__"):
            if asyncio.iscoroutine(result):
                result = await result
            return result.model_dump() if hasattr(result, "model_dump") else {}
        return result.model_dump() if hasattr(result, "model_dump") else {}

    async def _handle_get_task(self, params: dict) -> dict:
        """处理 tasks/get"""
        from usmsb_sdk.protocol.types.google_a2a import GetTaskRequest

        req = GetTaskRequest(
            task_id=params.get("taskId", ""),
            history_length=params.get("historyLength"),
        )

        task = await self._handler.on_get_task(req)
        if not task:
            raise JSONRPCError(
                self.METHOD_NOT_FOUND,
                f"Task not found: {params.get('taskId')}",
            )
        return task.model_dump()

    async def _handle_cancel_task(self, params: dict) -> dict:
        """处理 tasks/cancel"""
        from usmsb_sdk.protocol.types.google_a2a import CancelTaskRequest

        req = CancelTaskRequest(
            task_id=params.get("taskId", ""),
        )

        task = await self._handler.on_cancel_task(req)
        if not task:
            raise JSONRPCError(
                self.METHOD_NOT_FOUND,
                f"Task not found: {params.get('taskId')}",
            )
        return task.model_dump()

    async def _handle_list_tasks(self, params: dict) -> dict:
        """处理 tasks/list"""
        from usmsb_sdk.protocol.types.google_a2a import ListTasksRequest

        req = ListTasksRequest(
            page=params.get("page"),
            page_size=params.get("pageSize"),
            query=params.get("query"),
            include_artifacts=params.get("includeArtifacts", True),
        )

        tasks, total = await self._handler.on_list_tasks(req)
        return {
            "tasks": [t.model_dump() for t in tasks],
            "total": total,
        }

    async def _handle_get_agent_card(self) -> dict:
        """处理 agents/card"""
        card = await self._handler.on_get_agent_card()
        return card.model_dump()

    async def _handle_get_extended_agent_card(self) -> dict:
        """处理 agents/extended_card"""
        card = await self._handler.on_get_extended_agent_card()
        if not card:
            raise JSONRPCError(
                self.METHOD_NOT_FOUND,
                "Extended agent card not configured",
            )
        return card.model_dump()
