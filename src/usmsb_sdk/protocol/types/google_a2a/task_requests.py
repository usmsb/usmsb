"""
Google A2A Task Requests - 对齐官方 Spec 1.0
"""

from typing import Any

from pydantic import BaseModel, Field

from usmsb_sdk.protocol.types.google_a2a.models import (
    Message,
    SendMessageConfiguration,
    Task,
)


class SendMessageRequest(BaseModel):
    """
    tasks/send 请求 - 对齐官方 SendMessageRequest
    """

    tenant: str = ""
    skill_id: str = ""
    message: Message = Field(default_factory=Message)
    configuration: SendMessageConfiguration = Field(
        default_factory=SendMessageConfiguration
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class GetTaskRequest(BaseModel):
    """
    tasks/get 请求 - 对齐官方 GetTaskRequest
    """

    task_id: str = ""
    history_length: int | None = None


class CancelTaskRequest(BaseModel):
    """
    tasks/cancel 请求 - 对齐官方 CancelTaskRequest
    """

    task_id: str = ""


class ListTasksRequest(BaseModel):
    """
    tasks/list 请求 - 对齐官方 ListTasksRequest
    """

    page: int | None = None
    page_size: int | None = None
    after_id: str | None = None
    query: str | None = None
    include_artifacts: bool = True


class ListTasksResponse(BaseModel):
    """
    tasks/list 响应
    """

    tasks: list[Task] = Field(default_factory=list)
    next_page_token: str | None = None


class SubscribeToTaskRequest(BaseModel):
    """
    tasks/subscribe 请求 - 对齐官方 SubscribeToTaskRequest
    """

    task_id: str = ""


class GetAgentCardRequest(BaseModel):
    """
    agents/card 请求
    """

    pass  # 无参数


class TaskStatusUpdateEvent(BaseModel):
    """
    任务状态更新事件
    """

    task_id: str = ""
    context_id: str = ""
    status: "Task" = Field(default_factory=lambda: Task())
    metadata: dict[str, Any] = Field(default_factory=dict)
