"""
HTTPServer - HTTP Server for A2A Protocol

端点设计：
- POST /rpc                    # JSON-RPC 入口 (Google A2A)
- GET  /.well-known/agent.json # AgentCard 发现 (Google A2A)
- GET  /tasks/{id}             # 获取任务状态 (REST 兼容)
- GET  /tasks/{id}/events      # SSE 流式推送
- POST /tasks/{id}/cancel       # 取消任务
- GET  /tasks                  # 任务列表
- POST /custom/{path}           # Custom A2A
"""

import asyncio
import json
import logging
from typing import Any

from pydantic import BaseModel

from usmsb_sdk.protocol.transport.base import HTTPTransportConfig
from usmsb_sdk.protocol.google_a2a import GoogleA2AHandler
from usmsb_sdk.protocol.google_a2a.request_handlers import JSONRPCHandler
from usmsb_sdk.protocol.google_a2a.events.sse_streamer import SSEStreamer
from usmsb_sdk.protocol.custom_a2a.http_handler import CustomA2AHTTPHandler


logger = logging.getLogger(__name__)


class HTTPServer:
    """
    HTTP Server for A2A Protocol

    支持 Google A2A 和 Custom A2A 协议。
    """

    WELL_KNOWN_PATH = "/.well-known/agent.json"

    def __init__(
        self,
        config: HTTPTransportConfig | None = None,
        google_a2a_handler: GoogleA2AHandler | None = None,
        custom_a2a_handler: Any = None,  # CustomA2AHandler
    ):
        self._config = config or HTTPTransportConfig()
        self._google_handler = google_a2a_handler
        self._custom_handler = custom_a2a_handler
        self._server: asyncio.Server | None = None
        self._running = False

        # JSON-RPC 处理器
        self._rpc_handler: JSONRPCHandler | None = None
        if google_a2a_handler:
            self._rpc_handler = JSONRPCHandler(google_a2a_handler)

        # SSE 流式推送
        self._sse_streamer: SSEStreamer | None = None
        if google_a2a_handler:
            self._sse_streamer = google_a2a_handler._sse_streamer

        # Custom A2A HTTP Handler
        self._custom_http_handler: CustomA2AHTTPHandler | None = None
        if custom_a2a_handler:
            self._custom_http_handler = CustomA2AHTTPHandler(custom_a2a_handler)

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self) -> None:
        """启动 HTTP Server"""
        if self._running:
            return

        self._running = True

        if self._config.unix_socket:
            self._server = await asyncio.start_server(
                self._handle_connection,
                self._config.unix_socket,
                None,
            )
            logger.info(f"HTTP Server started on {self._config.unix_socket}")
        else:
            self._server = await asyncio.start_server(
                self._handle_connection,
                self._config.host,
                self._config.port,
            )
            logger.info(f"HTTP Server started on {self._config.host}:{self._config.port}")

    async def stop(self) -> None:
        """停止 HTTP Server"""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        self._running = False
        logger.info("HTTP Server stopped")

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """处理连接"""
        try:
            request_line = await reader.readline()
            if not request_line:
                return

            request_str = request_line.decode("utf-8").strip()
            parts = request_str.split(" ")
            if len(parts) < 2:
                await self._send_error(writer, 400, "Bad Request")
                return

            method, path = parts[0], parts[1]

            # 读取 headers
            headers = {}
            content_length = 0
            while True:
                line = await reader.readline()
                if not line or line == b"\r\n":
                    break
                header_line = line.decode("utf-8").strip()
                if ":" in header_line:
                    key, value = header_line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()
                    if key.strip().lower() == "content-length":
                        content_length = int(value.strip())

            # 读取 body
            body = b""
            if content_length > 0:
                body = await reader.readexactly(content_length)

            # 处理请求
            await self._handle_request(writer, method, path, headers, body)

        except Exception as e:
            logger.exception(f"Error handling connection: {e}")
            try:
                await self._send_error(writer, 500, "Internal Server Error")
            except Exception:
                pass

    async def _handle_request(
        self,
        writer: asyncio.StreamWriter,
        method: str,
        path: str,
        headers: dict,
        body: bytes,
    ) -> None:
        """处理请求"""
        # CORS headers
        cors_headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }

        # OPTIONS 预检请求
        if method == "OPTIONS":
            await self._send_response(writer, 204, {}, "", cors_headers)
            return

        # AgentCard 发现
        if method == "GET" and path == self.WELL_KNOWN_PATH:
            await self._handle_agent_card(writer, cors_headers)
            return

        # SSE 流式推送
        if method == "GET" and path.startswith("/tasks/") and path.endswith("/events"):
            task_id = path.split("/")[2]
            await self._handle_sse(writer, task_id, cors_headers)
            return

        # JSON-RPC
        if method == "POST" and path == "/rpc":
            await self._handle_jsonrpc(writer, body, cors_headers)
            return

        # REST 兼容
        if method == "GET" and path == "/tasks":
            await self._handle_list_tasks(writer, cors_headers)
            return

        if method == "GET" and path.startswith("/tasks/"):
            task_id = path.split("/")[2]
            await self._handle_get_task(writer, task_id, cors_headers)
            return

        if method == "POST" and path.startswith("/tasks/") and path.endswith("/cancel"):
            task_id = path.split("/")[2]
            await self._handle_cancel_task(writer, task_id, body, cors_headers)
            return

        # Custom A2A
        if path.startswith("/custom/"):
            await self._handle_custom_a2a(writer, method, path, body, cors_headers)
            return

        await self._send_error(writer, 404, "Not Found")

    async def _handle_agent_card(self, writer: asyncio.StreamWriter, cors_headers: dict) -> None:
        """处理 AgentCard 请求"""
        if not self._google_handler:
            await self._send_error(writer, 404, "AgentCard not configured")
            return

        card = await self._google_handler.on_get_agent_card()
        card_json = card.model_dump_json()

        await self._send_response(
            writer, 200,
            {"Content-Type": "application/json", **cors_headers},
            card_json,
        )

    async def _handle_jsonrpc(self, writer: asyncio.StreamWriter, body: bytes, cors_headers: dict) -> None:
        """处理 JSON-RPC 请求"""
        if not self._rpc_handler:
            await self._send_error(writer, 404, "JSON-RPC not configured")
            return

        try:
            request = json.loads(body.decode("utf-8"))
            response = await self._rpc_handler.handle(request)
            response_json = json.dumps(response)

            await self._send_response(
                writer, 200,
                {"Content-Type": "application/json", **cors_headers},
                response_json,
            )
        except json.JSONDecodeError:
            await self._send_error(writer, 400, "Invalid JSON")
        except Exception as e:
            logger.exception(f"JSON-RPC error: {e}")
            await self._send_error(writer, 500, "Internal Error")

    async def _handle_sse(self, writer: asyncio.StreamWriter, task_id: str, cors_headers: dict) -> None:
        """处理 SSE 流式推送"""
        if not self._sse_streamer:
            await self._send_error(writer, 404, "SSE not configured")
            return

        # SSE headers
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            **cors_headers,
        }

        await self._send_response(writer, 200, headers, "", is_sse=True)

        try:
            async for event in self._sse_streamer.stream(task_id):
                writer.write(event.encode("utf-8"))
                await writer.drain()
        except Exception:
            pass

    async def _handle_list_tasks(self, writer: asyncio.StreamWriter, cors_headers: dict) -> None:
        """处理任务列表请求"""
        if not self._google_handler:
            await self._send_error(writer, 404, "Handler not configured")
            return

        from usmsb_sdk.protocol.types.google_a2a import ListTasksRequest

        try:
            req = ListTasksRequest()
            tasks, total = await self._google_handler.on_list_tasks(req)
            response = {
                "tasks": [t.model_dump() for t in tasks],
                "total": total,
            }
            await self._send_response(
                writer, 200,
                {"Content-Type": "application/json", **cors_headers},
                json.dumps(response),
            )
        except Exception as e:
            logger.exception(f"Error listing tasks: {e}")
            await self._send_error(writer, 500, "Internal Error")

    async def _handle_get_task(self, writer: asyncio.StreamWriter, task_id: str, cors_headers: dict) -> None:
        """处理获取任务请求"""
        if not self._google_handler:
            await self._send_error(writer, 404, "Handler not configured")
            return

        from usmsb_sdk.protocol.types.google_a2a import GetTaskRequest

        try:
            req = GetTaskRequest(task_id=task_id)
            task = await self._google_handler.on_get_task(req)
            if not task:
                await self._send_error(writer, 404, "Task not found")
                return
            await self._send_response(
                writer, 200,
                {"Content-Type": "application/json", **cors_headers},
                task.model_dump_json(),
            )
        except Exception as e:
            logger.exception(f"Error getting task: {e}")
            await self._send_error(writer, 500, "Internal Error")

    async def _handle_cancel_task(self, writer: asyncio.StreamWriter, task_id: str, body: bytes, cors_headers: dict) -> None:
        """处理取消任务请求"""
        if not self._google_handler:
            await self._send_error(writer, 404, "Handler not configured")
            return

        from usmsb_sdk.protocol.types.google_a2a import CancelTaskRequest

        try:
            req = CancelTaskRequest(task_id=task_id)
            task = await self._google_handler.on_cancel_task(req)
            if not task:
                await self._send_error(writer, 404, "Task not found")
                return
            await self._send_response(
                writer, 200,
                {"Content-Type": "application/json", **cors_headers},
                task.model_dump_json(),
            )
        except Exception as e:
            logger.exception(f"Error canceling task: {e}")
            await self._send_error(writer, 500, "Internal Error")

    async def _handle_custom_a2a(
        self,
        writer: asyncio.StreamWriter,
        method: str,
        path: str,
        body: bytes,
        cors_headers: dict,
    ) -> None:
        """处理 Custom A2A 请求"""
        if not self._custom_http_handler:
            await self._send_error(writer, 501, "Custom A2A not configured")
            return

        try:
            status, response = await self._custom_http_handler.handle_request(
                method, path, body
            )
            await self._send_response(
                writer,
                status,
                {"Content-Type": "application/json", **cors_headers},
                json.dumps(response),
            )
        except Exception as e:
            logger.exception("Error in custom A2A handler")
            await self._send_error(writer, 500, f"Internal error: {e}")

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status: int,
        headers: dict,
        body: str,
        cors_headers: dict | None = None,
        is_sse: bool = False,
    ) -> None:
        """发送响应"""
        status_text = {
            200: "OK",
            204: "No Content",
            400: "Bad Request",
            404: "Not Found",
            500: "Internal Server Error",
        }.get(status, "Unknown")

        response_headers = headers.copy()
        if cors_headers:
            response_headers.update(cors_headers)

        if not is_sse and body:
            response_headers["Content-Length"] = str(len(body.encode("utf-8")))

        response_lines = [f"HTTP/1.1 {status} {status_text}"]
        for key, value in response_headers.items():
            response_lines.append(f"{key}: {value}")

        response_lines.append("")
        response_lines.append("")

        writer.write("".join(response_lines).encode("utf-8"))
        if body:
            writer.write(body.encode("utf-8"))
        await writer.drain()

    async def _send_error(
        self,
        writer: asyncio.StreamWriter,
        status: int,
        message: str,
    ) -> None:
        """发送错误响应"""
        body = json.dumps({"error": message})
        await self._send_response(
            writer, status,
            {"Content-Type": "application/json"},
            body,
        )
