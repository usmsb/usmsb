# -*- coding: utf-8 -*-
"""
L5: Collective Super Intelligence - 集体超级智能

L5 = 多个 L4 Agent 形成蜂群意识

核心组件：
1. GlobalWorkspace - 全局工作空间（注意力竞争）
2. CollectiveMemory - 集体记忆（分布式存储 + 共识）
3. CollectiveDecisionMaking - 集体决策（多轮协商）
4. CollectiveCreativity - 集体创造（跨领域碰撞）
5. CollectiveSelfModel - 集体自模型（群体身份）
"""

from usmsb_sdk.l5.global_workspace import (
    AttentionLevel,
    ConsciousnessObject,
    CollectiveMood,
    AttentionBiddingSystem,
    GossipProtocol,
    GlobalWorkspace,
)

from usmsb_sdk.l5.collective_memory import (
    MemoryImportance,
    Memory,
    ConsensusMemory,
    ImportanceIndex,
    DistributedRecall,
    CollectiveMemory,
)

from usmsb_sdk.l5.collective_decision_making import (
    DecisionStatus,
    ConsensusType,
    DecisionTopic,
    Proposal,
    Evaluation,
    CollectiveDecision,
    SupportMatrix,
    CollectiveDecisionMaking,
)

from usmsb_sdk.l5.l5_collective import (
    CollectiveIdentityStatus,
    CollectiveIdentity,
    CollectiveThought,
    CreativeIdea,
    ExpertiseIndex,
    CollectiveCreativity,
    CollectiveSelfModel,
    L5CollectiveIntelligence,
)

__all__ = [
    # GlobalWorkspace
    "AttentionLevel",
    "ConsciousnessObject",
    "CollectiveMood",
    "AttentionBiddingSystem",
    "GossipProtocol",
    "GlobalWorkspace",
    # CollectiveMemory
    "MemoryImportance",
    "Memory",
    "ConsensusMemory",
    "ImportanceIndex",
    "DistributedRecall",
    "CollectiveMemory",
    # CollectiveDecisionMaking
    "DecisionStatus",
    "ConsensusType",
    "DecisionTopic",
    "Proposal",
    "Evaluation",
    "CollectiveDecision",
    "SupportMatrix",
    "CollectiveDecisionMaking",
    # L5 Collective
    "CollectiveIdentityStatus",
    "CollectiveIdentity",
    "CollectiveThought",
    "CreativeIdea",
    "ExpertiseIndex",
    "CollectiveCreativity",
    "CollectiveSelfModel",
    "L5CollectiveIntelligence",
]
