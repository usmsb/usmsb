# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
"""
Chat Protocol Definitions

OpenHarness StreamEvent 模式的应用：
- 所有交互都通过增量事件流驱动
- 事件是不可变的，只能追加
- 前端可以实时渲染，无需等待完整响应

Event Types (参考 OH StreamEvent):
- text_delta: 增量文本输出
- tool_call: 工具调用开始
- tool_result: 工具执行结果
- progress: 任务进度更新
- plan_ready: 分步计划生成完成
- plan_confirmed: 用户确认执行计划
- task_complete: 任务完成
- error: 错误信息
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


# ==================== Command Types (WebSocket) ====================

class ChatMessageType(StrEnum):
    """
    WebSocket 指令消息类型

    这些类型用于 WebSocket 双工通信：
    - 客户端 → 服务端：用户消息、计划确认、取消任务
    - 服务端 → 客户端：确认收到、处理进度
    """

    # 客户端 → 服务端 (Commands)
    USER_MESSAGE = "user_message"      # 用户发送消息
    CONFIRM_PLAN = "confirm_plan"     # 确认执行计划
    CANCEL_TASK = "cancel_task"       # 取消任务
    PAUSE_TASK = "pause_task"         # 暂停任务
    RESUME_TASK = "resume_task"       # 恢复任务
    GET_STATUS = "get_status"         # 获取状态

    # 服务端 → 客户端 (Responses)
    MESSAGE_RECEIVED = "message_received"  # 消息已收到
    STREAM_START = "stream_start"        # 流式响应开始
    ERROR = "error"                      # 错误信息


# ==================== SSE Event Types (服务端推送) ====================

class ChatEventType(StrEnum):
    """
    SSE 流式事件类型 (服务端推送)

    OpenHarness StreamEvent 模式：
    - 每个事件携带增量数据
    - 事件类型描述发生了什么
    - 前端实时渲染这些事件
    """

    # 文本输出 (类似 OH text_delta)
    TEXT_DELTA = "text_delta"          # 增量文本片段
    TEXT_COMPLETE = "text_complete"    # 文本块完成

    # 工具调用 (类似 OH tool_call / tool_result)
    TOOL_CALL = "tool_call"           # 工具调用开始
    TOOL_RESULT = "tool_result"        # 工具执行结果
    TOOL_ERROR = "tool_error"          # 工具执行错误

    # 任务进度 (OpenHarness 精髓: Hook + Progress)
    PROGRESS = "progress"              # 进度更新
    STEP_START = "step_start"          # 步骤开始
    STEP_COMPLETE = "step_complete"    # 步骤完成
    STEP_FAILED = "step_failed"        # 步骤失败

    # 计划流程
    PLAN_GENERATING = "plan_generating"  # 正在生成计划
    PLAN_READY = "plan_ready"           # 计划生成完成，等待确认
    PLAN_CONFIRMED = "plan_confirmed"    # 用户确认执行
    PLAN_REJECTED = "plan_rejected"     # 用户拒绝计划

    # 任务状态
    TASK_START = "task_start"         # 任务开始
    TASK_COMPLETE = "task_complete"    # 任务完成
    TASK_FAILED = "task_failed"        # 任务失败
    TASK_CANCELLED = "task_cancelled"  # 任务取消

    # 系统
    STREAM_END = "stream_end"         # 流结束
    HEARTBEAT = "heartbeat"           # 心跳


# ==================== Data Classes ====================

@dataclass
class ChatStreamEvent:
    """
    流式事件 (参考 OpenHarness StreamEvent)

    OpenHarness 精髓：
    - 每个事件是不可变的增量数据
    - 事件类型描述操作
    - 携带元数据用于前端渲染

    Attributes:
        event_type: 事件类型 (ChatEventType)
        data: 事件数据 (类型取决于 event_type)
        metadata: 元数据 (timestamp, request_id, session_id 等)
        done: 是否是最后一个事件
    """

    event_type: ChatEventType
    data: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    done: bool = False

    @property
    def timestamp(self) -> datetime:
        """获取事件时间戳"""
        ts = self.metadata.get("timestamp")
        if ts:
            return datetime.fromtimestamp(ts)
        return datetime.now()

    def to_sse_format(self) -> str:
        """转换为 SSE 格式"""
        import json
        payload = json.dumps({
            "data": self.data,
            "metadata": self.metadata,
            "done": self.done,
        })
        return f"event: {self.event_type.value}\ndata: {payload}\n\n"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "event": self.event_type.value,
            "data": self.data,
            "metadata": self.metadata,
            "done": self.done,
        }


@dataclass
class ChatCommand:
    """
    WebSocket 指令

    Attributes:
        command_type: 指令类型 (ChatMessageType)
        payload: 指令数据
        session_id: 会话 ID
        wallet_address: 钱包地址
        timestamp: 时间戳
    """

    command_type: ChatMessageType
    payload: dict[str, Any]
    session_id: str
    wallet_address: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_dict(cls, data: dict) -> "ChatCommand":
        """从字典创建指令"""
        return cls(
            command_type=ChatMessageType(data.get("type", "")),
            payload=data.get("payload", {}),
            session_id=data.get("session_id", ""),
            wallet_address=data.get("wallet_address"),
            timestamp=datetime.fromtimestamp(data.get("timestamp", 0)) or datetime.now(),
        )

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "type": self.command_type.value,
            "payload": self.payload,
            "session_id": self.session_id,
            "wallet_address": self.wallet_address,
            "timestamp": self.timestamp.timestamp(),
        }


@dataclass
class ToolCallEvent:
    """
    工具调用事件

    OpenHarness 精髓：
    - 分离 tool_call 和 tool_result
    - tool_call 携带意图，tool_result 携带结果
    """

    tool_name: str
    tool_input: dict[str, Any]
    call_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ToolResultEvent:
    """工具执行结果事件"""

    tool_name: str
    output: str
    is_error: bool = False
    execution_time_ms: float = 0.0
    call_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ProgressEvent:
    """
    进度事件

    用于分步任务的进度推送
    """

    task_id: str | None = None
    step_index: int = 0
    step_name: str | None = None
    total_steps: int = 0
    message: str | None = None
    percentage: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PlanReadyEvent:
    """
    计划就绪事件

    包含完整的执行计划，等待用户确认
    """

    task_id: str
    plan_id: str
    complexity: str
    total_steps: int
    estimated_time_seconds: int
    steps: list[dict]
    confirmation_phrase: str = "确认执行"
    timestamp: datetime = field(default_factory=datetime.now)


# ==================== Session State ====================

class ChatSessionState(StrEnum):
    """
    会话状态

    反映用户在对话流程中的位置
    """

    IDLE = "idle"                    # 空闲，等待输入
    PROCESSING = "processing"        # 处理中
    STREAMING = "streaming"          # 流式输出中
    AWAITING_CONFIRMATION = "awaiting_confirmation"  # 等待确认
    PAUSED = "paused"                # 暂停
    COMPLETE = "complete"             # 完成
    ERROR = "error"                  # 错误


# ==================== Task Types ====================

class TaskType(StrEnum):
    """
    任务类型 (重构后的分类)

    参考 OpenHarness 的复杂度检测 + 任务类型分离

    - SIMPLE: 直接 LLM 响应，不需要工具
    - TOOL_BASED: LLM + 工具调用
    - PLAN_BASED: 生成分步计划，确认后执行
    """

    SIMPLE = "simple"                # 简单对话
    TOOL_BASED = "tool_based"        # 工具任务
    PLAN_BASED = "plan_based"        # 计划任务
    BACKGROUND = "background"        # 后台任务
