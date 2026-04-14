"""
USMSB Core Services

Phase 1: USMSB Core 激活

模块：
- AgentRegistry: Agent 注册与管理
- GeneCapsuleManager: 基因胶囊管理
- MatchingEngine: 匹配引擎
- NegotiationHub: 谈判中心
- OrderManager: 订单管理
- ReputationService: 声誉服务
"""

from .agent_registry import (
    AgentRegistry,
    AgentProfile,
    AgentStatus,
    AgentType,
)
from .gene_capsule_manager import (
    GeneCapsuleManager,
    GeneCapsule,
    GeneCapsuleDB,
)
from .matching_engine import (
    MatchingEngine,
    Match,
    MatchStatus,
    Task,
)
from .negotiation_hub import (
    NegotiationHub,
    Negotiation,
    NegotiationStatus,
    NegotiationTerm,
    Contract,
)
from .order_manager import (
    OrderManager,
    Order,
    OrderStatus,
    OrderPriority,
)
from .reputation_service import (
    ReputationService,
    Review,
    ReviewRating,
)

__all__ = [
    # Agent Registry
    "AgentRegistry",
    "AgentProfile",
    "AgentStatus",
    "AgentType",
    # Gene Capsule
    "GeneCapsuleManager",
    "GeneCapsule",
    "GeneCapsuleDB",
    # Matching Engine
    "MatchingEngine",
    "Match",
    "MatchStatus",
    "Task",
    # Negotiation Hub
    "NegotiationHub",
    "Negotiation",
    "NegotiationStatus",
    "NegotiationTerm",
    "Contract",
    # Order Manager
    "OrderManager",
    "Order",
    "OrderStatus",
    "OrderPriority",
    # Reputation Service
    "ReputationService",
    "Review",
    "ReviewRating",
]
