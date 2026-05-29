"""
USMSB Protocol Types - 统一类型系统

包含：
- A2AEnvelope: 所有协议的统一信封
- Google A2A 类型: 对齐官方 Spec 1.0
- Custom A2A 类型: USMSB 私有协议
"""

from usmsb_sdk.protocol.types.envelope import A2AEnvelope

# Google A2A types
from usmsb_sdk.protocol.types.google_a2a import (
    TaskState,
    Role,
    MessageType,
    Part,
    Message,
    TaskStatus,
    Artifact,
    Task,
    SendMessageConfiguration,
    TaskPushNotificationConfig,
    AuthenticationInfo,
    AgentCapabilities,
    AgentExtension,
    AgentProvider,
    AgentInterface,
    AgentSkill,
    AgentCard,
    GetTaskRequest,
    CancelTaskRequest,
    ListTasksRequest,
    SendMessageRequest,
    SubscribeToTaskRequest,
)

# Custom A2A types
from usmsb_sdk.protocol.types.custom_a2a import (
    CustomTaskStatus,
    CustomMessageType,
    CustomPart,
    CustomMessage,
    CustomTask,
    CustomAgentCard,
)

# Backward compatibility alias
GoogleAgentCard = AgentCard  # Google A2A AgentCard

__all__ = [
    # Envelope
    "A2AEnvelope",
    # Google A2A enums
    "TaskState",
    "Role",
    "MessageType",
    # Google A2A models
    "Part",
    "Message",
    "TaskStatus",
    "Artifact",
    "Task",
    "SendMessageConfiguration",
    "TaskPushNotificationConfig",
    "AuthenticationInfo",
    # Google A2A AgentCard
    "AgentCapabilities",
    "AgentExtension",
    "AgentProvider",
    "AgentInterface",
    "AgentSkill",
    "AgentCard",
    # Google A2A requests
    "GetTaskRequest",
    "CancelTaskRequest",
    "ListTasksRequest",
    "SendMessageRequest",
    "SubscribeToTaskRequest",
    # Custom A2A
    "CustomTaskStatus",
    "CustomMessageType",
    "CustomPart",
    "CustomMessage",
    "CustomTask",
    "CustomAgentCard",
    # Backward compatibility
    "GoogleAgentCard",
]
