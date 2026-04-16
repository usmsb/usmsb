# =============================================================================
# IL5 Interface - 集体超级智能接口定义 (v2.0)
# =============================================================================
# L5 = 多个 L4 Agent 协调形成蜂群意识
#
# External agents access L5 capabilities via SkillPlatform:
#
#   from usmsb_sdk.l5 import L5CollectiveIntelligence
#
# Core IL5 Methods:
#   coordinate(agents, task)          -> CoordinationResult
#       Multi-agent coordination: dispatch task to agents, aggregate results
#
#   collective_think(problem)        -> CollectiveThought
#       Parallel thinking + global workspace competition + synthesis
#
#   decide(topic, proposals)         -> CollectiveDecision
#       Multi-round negotiation + consensus formation
#
#   create_together(prompt, agents)  -> CreativeIdea
#       Cross-domain collision for creative output
#
#   share_memory(key, value, ttl)   -> None
#       Write to global workspace, visible to all agents
#
#   recall_collective(query, top_k) -> list[Memory]
#       Retrieve shared memories across the collective
#
#   detect_collective_mood()         -> CollectiveMood
#       Aggregate emotional states of all agents
#
#   evolve_identity(insight)        -> CollectiveIdentity
#       Update collective identity based on new learnings
# =============================================================================

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
