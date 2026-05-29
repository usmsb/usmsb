"""
Google A2A Models - 对齐官方 Spec 1.0
"""

import time
from typing import Any

from pydantic import BaseModel, Field

from usmsb_sdk.protocol.types.google_a2a.enums import TaskState, Role


class Part(BaseModel):
    """
    消息片段 - 对齐官方 Part 定义

    支持多种内容格式：文本、二进制、URL、结构化数据
    """

    text: str | None = None  # 文本内容
    raw: bytes | None = None  # 原始二进制
    url: str | None = None  # URL 引用
    data: dict | None = None  # 结构化数据（JSON 对象）
    metadata: dict[str, Any] = Field(default_factory=dict)  # 元数据
    filename: str | None = None  # 文件名
    media_type: str | None = None  # MIME 类型

    def has_content(self) -> bool:
        """是否有任何内容"""
        return any([self.text, self.raw, self.url, self.data])


class Message(BaseModel):
    """
    A2A 消息 - 对齐官方 Message 定义
    """

    message_id: str = ""
    context_id: str = ""
    task_id: str = ""
    role: Role = Role.UNSPECIFIED
    parts: list[Part] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    extensions: list[str] = Field(default_factory=list)
    reference_task_ids: list[str] = Field(default_factory=list)


class TaskStatus(BaseModel):
    """
    任务状态 - 对齐官方 TaskStatus
    """

    state: TaskState = TaskState.UNSPECIFIED
    message: Message | None = None
    timestamp: float = Field(default_factory=time.time)


class Artifact(BaseModel):
    """
    任务产物 - 对齐官方 Artifact

    Agent 执行过程中产生的文件和结构化数据
    """

    artifact_id: str = ""
    name: str = ""
    description: str = ""
    parts: list[Part] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    extensions: list[str] = Field(default_factory=list)


class Task(BaseModel):
    """
    A2A 任务 - 对齐官方 Task
    """

    id: str = ""
    context_id: str = ""
    status: TaskStatus = Field(default_factory=TaskStatus)
    artifacts: list[Artifact] = Field(default_factory=list)
    history: list[Message] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SendMessageConfiguration(BaseModel):
    """
    发送消息配置 - 对齐官方 SendMessageConfiguration
    """

    accepted_output_modes: list[str] = Field(default_factory=list)
    task_push_notification_config: "TaskPushNotificationConfig | None" = None
    history_length: int | None = None
    return_immediately: bool = False


class TaskPushNotificationConfig(BaseModel):
    """
    任务推送通知配置 - 对齐官方 TaskPushNotificationConfig
    """

    tenant: str = ""
    id: str = ""
    task_id: str = ""
    url: str = ""
    token: str = ""
    authentication: "AuthenticationInfo | None" = None


class AuthenticationInfo(BaseModel):
    """
    认证信息
    """

    scheme: str = ""
    credentials: str = ""
