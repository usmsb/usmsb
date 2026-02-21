"""
Conversation Models - 基于 USMSB 模型的对话数据结构

对话是 Information 的特殊形式，包含：
- 会话上下文 (Environment)
- 参与者 (Agents)
- 消息流 (Information flow)
- 目标追踪 (Goals)
- 学习产出 (Knowledge)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class ParticipantType(str, Enum):
    """参与者类型"""

    HUMAN = "human"
    AI_AGENT = "ai_agent"
    META_AGENT = "meta_agent"
    SYSTEM_AGENT = "system_agent"


class ConversationStatus(str, Enum):
    """会话状态"""

    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


class MessageRole(str, Enum):
    """消息角色"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    BACKGROUND_TASK = "background_task"  # 后台任务执行过程
    BACKGROUND_COMPLETE = "background_complete"  # 后台任务完成
    BACKGROUND_ERROR = "background_error"  # 后台任务错误


@dataclass
class Participant:
    """会话参与者"""

    id: str
    type: ParticipantType
    name: Optional[str] = None
    wallet_address: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = ParticipantType(self.type)


@dataclass
class Message:
    """
    消息 - USMSB Information 的具体实现

    每条消息都是一个 Information 对象，包含：
    - content: 消息内容
    - type: 信息类型
    - quality: 消息质量评分
    - embeddings: 向量嵌入（用于语义检索）
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    role: MessageRole = MessageRole.USER
    content: str = ""
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())

    # USMSB Information 属性
    information_type: str = "text"
    quality: float = 1.0
    relevance: float = 1.0
    embeddings: Optional[List[float]] = None

    # 元数据
    intent: Optional[str] = None
    entities: List[Dict[str, Any]] = field(default_factory=list)
    sentiment: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.role, str):
            self.role = MessageRole(self.role)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "intent": self.intent,
            "sentiment": self.sentiment,
            "tool_calls": self.tool_calls,
        }


@dataclass
class ConversationGoal:
    """
    会话目标 - USMSB Goal 的具体实现

    每个会话可以有多个目标，追踪对话的进展
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    status: str = "pending"  # pending, in_progress, completed, failed
    priority: int = 0
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningOutcome:
    """
    学习产出 - 从对话中提取的知识

    基于 USMSB Learning 动作，每次对话都可以产出：
    - 新知识
    - 行为调整建议
    - 能力提升
    """

    id: str = field(default_factory=lambda: str(uuid4()))
    conversation_id: str = ""
    knowledge_type: str = "insight"  # insight, fact, skill, preference, pattern
    content: str = ""
    confidence: float = 0.5
    applicable_contexts: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    applied_count: int = 0
    effectiveness: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """
    会话 - 完整的对话单元

    基于 USMSB 模型，一个会话包含：
    - Environment: 会话环境/上下文
    - Agents: 参与者
    - Information: 消息流
    - Goals: 会话目标
    - Rules: 会话规则（隐私隔离）
    - Learning: 学习产出
    - Value: 产生的价值
    """

    id: str = field(default_factory=lambda: str(uuid4()))

    # 参与者
    participants: List[Participant] = field(default_factory=list)

    # 隐私隔离：每个会话属于特定的用户/Agent
    owner_id: str = ""  # 钱包地址或 Agent ID
    owner_type: ParticipantType = ParticipantType.HUMAN

    # 会话状态
    status: ConversationStatus = ConversationStatus.ACTIVE
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    ended_at: Optional[float] = None

    # 消息流
    messages: List[Message] = field(default_factory=list)

    # 会话目标
    goals: List[ConversationGoal] = field(default_factory=list)

    # 学习产出
    learning_outcomes: List[LearningOutcome] = field(default_factory=list)

    # 会话上下文 (Environment)
    context: Dict[str, Any] = field(default_factory=dict)

    # 隐私规则
    is_private: bool = True  # 默认私有
    access_list: List[str] = field(default_factory=list)  # 有权访问的 ID 列表

    # 元数据
    summary: Optional[str] = None
    total_tokens: int = 0
    satisfaction_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = ConversationStatus(self.status)
        if isinstance(self.owner_type, str):
            self.owner_type = ParticipantType(self.owner_type)

    def add_message(self, message: Message) -> None:
        """添加消息"""
        self.messages.append(message)
        self.updated_at = datetime.now().timestamp()

    def get_last_n_messages(self, n: int = 10) -> List[Message]:
        """获取最近 N 条消息"""
        return self.messages[-n:] if self.messages else []

    def get_messages_for_llm(self, max_tokens: int = 4000) -> List[Dict[str, str]]:
        """获取用于 LLM 的消息格式（过滤掉后台任务消息）"""
        background_roles = {
            MessageRole.BACKGROUND_TASK,
            MessageRole.BACKGROUND_COMPLETE,
            MessageRole.BACKGROUND_ERROR,
        }

        filtered_messages = [msg for msg in self.messages if msg.role not in background_roles]

        messages = []
        total_length = 0

        for msg in reversed(filtered_messages):
            msg_length = len(msg.content)
            if total_length + msg_length > max_tokens:
                break
            messages.insert(0, {"role": msg.role.value, "content": msg.content})
            total_length += msg_length

        return messages

    def can_access(self, accessor_id: str) -> bool:
        """检查是否有权访问此会话"""
        if not self.is_private:
            return True
        return accessor_id == self.owner_id or accessor_id in self.access_list

    def end(self) -> None:
        """结束会话"""
        self.status = ConversationStatus.ENDED
        self.ended_at = datetime.now().timestamp()
        self.updated_at = self.ended_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "owner_type": self.owner_type.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": len(self.messages),
            "goals": [{"name": g.name, "status": g.status} for g in self.goals],
            "summary": self.summary,
        }
