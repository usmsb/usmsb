"""
HTTPClient - HTTP Client for A2A Protocol

用于向 A2A Server 发送请求。
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator

import httpx

from usmsb_sdk.protocol.transport.base import HTTPTransportConfig


logger = logging.getLogger(__name__)


class HTTPClient:
    """
    HTTP Client for A2A Protocol

    用法：
    ```python
    client = HTTPClient("http://localhost:8080")

    # 发送 JSON-RPC 请求
    response = await client.rpc("tasks/send", {
        "message": {"role": "user", "parts": [{"text": "Hello"}]}
    })

    # 获取 AgentCard
    card = await client.get_agent_card()

    # SSE 订阅
    async for event in client.subscribe("task-123"):
        print(event)
    ```
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        """关闭客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def rpc(self, method: str, params: dict[str, Any] | None = None) -> dict:
        """
        发送 JSON-RPC 请求

        Args:
            method: 方法名
            params: 参数

        Returns:
            响应结果
        """
        client = await self._get_client()

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {},
        }

        try:
            response = await client.post(
                "/rpc",
                json=request,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                raise Exception(f"JSON-RPC error: {result['error']}")

            return result.get("result", {})
        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            raise

    async def get_agent_card(self) -> dict:
        """获取 AgentCard"""
        client = await self._get_client()

        response = await client.get("/.well-known/agent.json")
        response.raise_for_status()
        return response.json()

    async def send_task(
        self,
        message: dict,
        skill_id: str = "",
        configuration: dict | None = None,
    ) -> dict:
        """
        发送任务

        Args:
            message: 消息内容
            skill_id: 技能 ID
            configuration: 配置

        Returns:
            任务信息
        """
        params = {
            "message": message,
        }
        if skill_id:
            params["skillId"] = skill_id
        if configuration:
            params["configuration"] = configuration

        return await self.rpc("tasks/send", params)

    async def get_task(self, task_id: str, history_length: int | None = None) -> dict:
        """
        获取任务

        Args:
            task_id: 任务 ID
            history_length: 历史长度

        Returns:
            任务信息
        """
        params = {"taskId": task_id}
        if history_length is not None:
            params["historyLength"] = history_length

        return await self.rpc("tasks/get", params)

    async def cancel_task(self, task_id: str) -> dict:
        """
        取消任务

        Args:
            task_id: 任务 ID

        Returns:
            取消结果
        """
        return await self.rpc("tasks/cancel", {"taskId": task_id})

    async def list_tasks(
        self,
        page: int = 0,
        page_size: int = 50,
        query: str | None = None,
    ) -> dict:
        """
        列出任务

        Args:
            page: 页码
            page_size: 每页数量
            query: 查询条件

        Returns:
            任务列表
        """
        params = {
            "page": page,
            "pageSize": page_size,
        }
        if query:
            params["query"] = query

        return await self.rpc("tasks/list", params)

    async def subscribe(self, task_id: str) -> AsyncIterator[dict]:
        """
        订阅任务更新 (SSE)

        Args:
            task_id: 任务 ID

        Yields:
            事件数据
        """
        client = await self._get_client()

        async with client.stream(
            "GET",
            f"/tasks/{task_id}/events",
            headers={"Accept": "text/event-stream"},
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data:
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            pass

    async def __aenter__(self) -> "HTTPClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
