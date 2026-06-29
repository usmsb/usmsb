"""A2A HTTP 客户端：按 URL 对远程 PEA 派单（跨进程/跨机器）。

与 LocalA2ARuntime 在 PeaMarket 里可互换：本地供应商走 runtime.submit（进程内），
远程供应商走 A2AClient.submit（HTTP/JSON-RPC）。metadata（vibe_amount、转包深度/预算）
透明透传，远程 runtime 自行托管/交付/结算。
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx


class A2ARemoteError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class A2AClient:
    """远程 A2A 端点客户端。

    transport 仅用于测试（httpx.ASGITransport 把请求直送 ASGI app，不开真实端口）；
    生产留空，按 base_url 走真实网络。
    """

    def __init__(self, base_url: str, *, transport: Any = None, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self._transport = transport
        self.timeout = timeout

    def _client(self) -> httpx.AsyncClient:
        if self._transport is not None:
            return httpx.AsyncClient(transport=self._transport, base_url=self.base_url, timeout=self.timeout)
        return httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)

    async def get_agent_card(self) -> dict[str, Any]:
        async with self._client() as c:
            r = await c.get("/.well-known/agent.json")
            r.raise_for_status()
            return r.json()

    async def health(self) -> dict[str, Any]:
        async with self._client() as c:
            r = await c.get("/health")
            r.raise_for_status()
            return r.json()

    async def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = {"jsonrpc": "2.0", "id": uuid.uuid4().hex, "method": method, "params": params}
        async with self._client() as c:
            r = await c.post("/a2a", json=payload)
            r.raise_for_status()
            data = r.json()
        if isinstance(data, dict) and data.get("error"):
            err = data["error"]
            raise A2ARemoteError(int(err.get("code", -1)), str(err.get("message", "remote error")))
        return data.get("result", {}) if isinstance(data, dict) else {}

    async def submit(self, params: dict[str, Any]) -> dict[str, Any]:
        """params = {"message": {...}, "metadata": {...}}，同 LocalA2ARuntime.submit 入参。"""
        return await self._rpc("message/send", params)

    async def get_task(self, task_id: str) -> dict[str, Any]:
        return await self._rpc("tasks/get", {"taskId": task_id})
