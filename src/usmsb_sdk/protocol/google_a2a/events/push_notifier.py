"""
PushNotifier - Webhook 推送通知
"""

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class PushNotifier:
    """
    Push Notification 推送器

    当任务状态变更时，通过 Webhook 通知第三方。
    """

    def __init__(self, timeout: float = 10.0):
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def notify(
        self,
        url: str,
        task_id: str,
        event_type: str,
        data: dict[str, Any],
        token: str | None = None,
        auth: dict | None = None,
    ) -> bool:
        """
        发送 Webhook 通知

        Args:
            url: Webhook URL
            task_id: 任务 ID
            event_type: 事件类型 (task_status_update, artifact_update)
            data: 事件数据
            token: 推送配置中的 token
            auth: 认证信息

        Returns:
            bool: 是否发送成功
        """
        payload = {
            "task_id": task_id,
            "event_type": event_type,
            "data": data,
        }

        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            client = await self._get_client()
            response = await client.post(
                url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            logger.info(f"Push notification sent successfully: task_id={task_id}")
            return True
        except Exception as e:
            logger.warning(f"Push notification failed: task_id={task_id}, error={e}")
            return False

    async def notify_task_status(
        self,
        url: str,
        task_id: str,
        status_data: dict[str, Any],
        token: str | None = None,
        auth: dict | None = None,
    ) -> bool:
        """通知任务状态变更"""
        return await self.notify(
            url=url,
            task_id=task_id,
            event_type="task_status_update",
            data=status_data,
            token=token,
            auth=auth,
        )

    async def notify_artifact_update(
        self,
        url: str,
        task_id: str,
        artifact_data: dict[str, Any],
        token: str | None = None,
        auth: dict | None = None,
    ) -> bool:
        """通知产物更新"""
        return await self.notify(
            url=url,
            task_id=task_id,
            event_type="artifact_update",
            data=artifact_data,
            token=token,
            auth=auth,
        )

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
