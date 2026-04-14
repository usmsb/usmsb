# -*- coding: utf-8 -*-
"""
L3: 目的内生硅基生命系统
"""

from .purpose_generator import (
    PurposeGenerator,
    Purpose,
    IntrinsicNeed,
    NeedType,
)

from .intrinsic_motivation import (
    IntrinsicMotivationEngine,
)

from .need_detector import (
    NeedDetector,
    AgentSelfState,
)

from .goal_persistence import (
    GoalPersistence,
)

from .value_self_loop import (
    ValueSelfLoop,
    ServiceType,
)

from .self_replication import (
    SelfReplication,
)

from .emergence_layer import (
    EmergenceLayer,
)

from .collective_goal_emergence import (
    CollectiveGoalEmergence,
    CollectiveGoal,
    ConsensusState,
)

from .emergent_governance import (
    EmergentGovernance,
    Rule,
    RuleState,
)

from .value_seed_engine import (
    ValueSeedEngine,
    ValueType,
    ValuePrinciple,
    ValueJudgment,
    ValueProfile,
)

__all__ = [
    # Core
    "PurposeGenerator",
    "Purpose",
    "IntrinsicNeed",
    "NeedType",

    # Motivation
    "IntrinsicMotivationEngine",

    # Need
    "NeedDetector",
    "AgentSelfState",

    # Persistence
    "GoalPersistence",

    # Value
    "ValueSelfLoop",
    "ServiceType",

    # Replication
    "SelfReplication",

    # Emergence
    "EmergenceLayer",

    # Collective
    "CollectiveGoalEmergence",
    "CollectiveGoal",
    "ConsensusState",

    # Governance
    "EmergentGovernance",
    "Rule",
    "RuleState",

    # Values
    "ValueSeedEngine",
    "ValueType",
    "ValuePrinciple",
    "ValueJudgment",
    "ValueProfile",
]
