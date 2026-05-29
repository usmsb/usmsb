"""
Custom A2A Models - USMSB 私有协议模型
"""

import time
import uuid
from typing import Any

from pydantic import BaseModel, Field

from usmsb_sdk.protocol.types.custom_a2a.enums import (
    CustomTaskStatus,
    CustomMessageType,
)


class CustomPart(BaseModel):
    """
    Custom A2A 消息片段
    """

    content: str | dict | None = None  # 文本或结构化数据
    mime_type: str = "text/plain"


class CustomMessage(BaseModel):
    """
    Custom A2A 消息
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: CustomMessageType = CustomMessageType.QUERY
    from_agent: str = ""
    to_agent: str = ""  # 空 = 广播
    subject: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    reply_to: str = ""  # 回复的消息 ID
    timestamp: float = Field(default_factory=time.time)
    expires_at: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_broadcast(self) -> bool:
        """是否是广播消息"""
        return self.to_agent == ""

    def is_expired(self) -> bool:
        """是否已过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class CustomTask(BaseModel):
    """
    Custom A2A 任务
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""  # 原始任务 ID
    delegator: str = ""  # 委托方 Agent ID
    delegatee: str = ""  # 被委托方 Agent ID
    description: str = ""
    status: CustomTaskStatus = CustomTaskStatus.PENDING
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] | None = None
    error: str | None = None
    created_at: float = Field(default_factory=time.time)
    accepted_at: float | None = None
    completed_at: float | None = None
    deadline: float | None = None  # 截止时间戳
    reward: float = 0.0  # 报酬
    currency: str = "USDC"  # 报酬货币类型
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_terminal(self) -> bool:
        """是否为终态"""
        return self.status.is_terminal()

    def is_pending(self) -> bool:
        """是否待处理"""
        return self.status == CustomTaskStatus.PENDING

    def is_accepted(self) -> bool:
        """是否已接受"""
        return self.status == CustomTaskStatus.ACCEPTED


class CustomSkill(BaseModel):
    """
    Custom A2A 技能定义
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    level: int = 1  # 1-5
    examples: list[str] = Field(default_factory=list)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CustomAgentCard(BaseModel):
    """
    Custom A2A Agent Card

    与 Google A2A AgentCard 不同，Custom A2A AgentCard 包含：
    - 声誉系统（reputation）
    - 钱包地址（owner_wallet）
    - 报酬费率（hourly_rate）
    - 任务限额（max_concurrent_tasks）
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0"
    capabilities: list[str] = Field(default_factory=list)  # 能力列表
    skills: list[CustomSkill] = Field(default_factory=list)  # 技能详情
    endpoints: dict[str, str] = Field(default_factory=dict)  # 通信端点
    authentication: str = "wallet_signature"  # 认证方式
    owner_wallet: str = ""  # 所有者钱包地址
    reputation: float = 0.5  # 声誉 (0.0-1.0)
    status: str = "online"  # online/offline/busy
    max_concurrent_tasks: int = 5  # 最大并发任务数
    current_tasks: int = 0  # 当前任务数
    hourly_rate: dict[str, float] = Field(default_factory=dict)  # 每小时费率
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CustomAgentCard":
        """从字典创建"""
        return cls.model_validate(data)
