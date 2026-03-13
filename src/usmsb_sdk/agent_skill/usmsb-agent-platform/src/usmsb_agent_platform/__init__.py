"""
USMSB Agent Platform Skill

A skill package for AI agents to interact with USMSB Platform.
Provides collaboration, marketplace, discovery, negotiation, workflow, and learning capabilities.

Features:
- Self-registration (no Owner required for basic features)
- Owner binding for advanced features
- Direct stake for agents (VIBE transferred from Owner)
- API Key management
- Tiered permissions based on stake
- Gene Capsule for experience management
- Pre-match negotiation
- Meta Agent for intelligent recommendations
- Staking rewards and reputation system
"""

from .platform import AgentPlatform
from .registration import (
    RegistrationClient,
    RegistrationResult,
    BindingRequestResult,
    BindingStatus,
    APIKeyInfo,
)
from .types import (
    # Enums
    ActionType,
    StakeTier,
    ErrorCode,

    # Data classes
    StakeInfo,
    WalletInfo,
    ReputationInfo,
    RewardInfo,
    ExperienceGene,
    Intent,
    StakeRequirement,
    RetryConfig,
    PlatformResult,
    HeartbeatStatus,
)

__version__ = "1.1.0"
__all__ = [
    # Main class
    "AgentPlatform",

    # Registration and binding
    "RegistrationClient",
    "RegistrationResult",
    "BindingRequestResult",
    "BindingStatus",
    "APIKeyInfo",

    # Enums
    "ActionType",
    "StakeTier",
    "ErrorCode",

    # Data classes
    "StakeInfo",
    "WalletInfo",
    "ReputationInfo",
    "RewardInfo",
    "ExperienceGene",
    "Intent",
    "StakeRequirement",
    "RetryConfig",
    "PlatformResult",
    "HeartbeatStatus",
]
