"""
Google A2A Types - 对齐官方 Spec 1.0
"""

from usmsb_sdk.protocol.types.google_a2a.enums import (
    TaskState,
    Role,
    MessageType,
)
from usmsb_sdk.protocol.types.google_a2a.models import (
    Part,
    Message,
    TaskStatus,
    Artifact,
    Task,
    SendMessageConfiguration,
    TaskPushNotificationConfig,
    AuthenticationInfo,
)
from usmsb_sdk.protocol.types.google_a2a.agent_card import (
    AgentCapabilities,
    AgentExtension,
    AgentProvider,
    AgentInterface,
    AgentSkill,
    AgentCard,
    AgentCardSignature,
    SecurityScheme,
    SecurityRequirement,
)
from usmsb_sdk.protocol.types.google_a2a.task_requests import (
    SendMessageRequest,
    GetTaskRequest,
    CancelTaskRequest,
    ListTasksRequest,
    SubscribeToTaskRequest,
    GetAgentCardRequest,
)

__all__ = [
    # Enums
    "TaskState",
    "Role",
    "MessageType",
    # Models
    "Part",
    "Message",
    "TaskStatus",
    "Artifact",
    "Task",
    "SendMessageConfiguration",
    "TaskPushNotificationConfig",
    "AuthenticationInfo",
    # AgentCard
    "AgentCapabilities",
    "AgentExtension",
    "AgentProvider",
    "AgentInterface",
    "AgentSkill",
    "AgentCard",
    "AgentCardSignature",
    "SecurityScheme",
    "SecurityRequirement",
    # Requests
    "SendMessageRequest",
    "GetTaskRequest",
    "CancelTaskRequest",
    "ListTasksRequest",
    "SubscribeToTaskRequest",
    "GetAgentCardRequest",
]
