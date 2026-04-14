# -*- coding: utf-8 -*-
"""
Phase 4: Emergence System
"""

from .emergence_system import (
    EmergenceSystem,
    GossipProtocol,
    GossipMessage,
    NodeState,
    TeamFormationAlgorithm,
    Team,
    PatternDetection,
    GlobalCoordination,
    CoordinationAction,
)

from .role_negotiation import (
    RoleNegotiationProtocol,
    Role,
    RoleType,
    RoleBid,
    NegotiationResult,
    DEFAULT_ROLE_TEMPLATES,
)

from .trust_building import (
    TrustBuilding,
    TrustScore,
    Interaction,
)

from .emergence_monitor import (
    EmergenceMonitor,
    EmergenceIndicator,
    EmergenceEvent,
)

__all__ = [
    # Core
    "EmergenceSystem",
    "GossipProtocol",
    "GossipMessage",
    "NodeState",
    "TeamFormationAlgorithm",
    "Team",
    "PatternDetection",
    "GlobalCoordination",
    "CoordinationAction",

    # Role Negotiation
    "RoleNegotiationProtocol",
    "Role",
    "RoleType",
    "RoleBid",
    "NegotiationResult",
    "DEFAULT_ROLE_TEMPLATES",

    # Trust Building
    "TrustBuilding",
    "TrustScore",
    "Interaction",

    # Emergence Monitor
    "EmergenceMonitor",
    "EmergenceIndicator",
    "EmergenceEvent",
]
