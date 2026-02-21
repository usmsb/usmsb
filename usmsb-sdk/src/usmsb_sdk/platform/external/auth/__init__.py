"""
Authentication Module

Provides authentication interfaces and implementations for the USMSB SDK.
This module includes wallet verification, stake verification, and coordinated
authentication flows.

Usage:
    from usmsb_sdk.platform.external.auth import (
        AuthCoordinator,
        MockWalletAuthenticator,
        MockStakeVerifier,
        Permission,
        StakeTier,
    )

    # Create coordinator with mock implementations
    coordinator = AuthCoordinator(
        wallet_authenticator=MockWalletAuthenticator(),
        stake_verifier=MockStakeVerifier()
    )

    # Initialize
    await coordinator.initialize()

    # Verify for registration
    result = await coordinator.verify_for_registration(context)
"""

# Base types and enums
from usmsb_sdk.platform.external.auth.base_auth import (
    Permission,
    StakeTier,
    AuthContext,
    BaseAuthResult,
    WalletAuthResult,
    StakeVerificationResult,
    FullAuthResult,
    IAuthProvider,
)

# Wallet authentication
from usmsb_sdk.platform.external.auth.wallet_auth import (
    WalletBinding,
    IWalletAuthenticator,
    MockWalletAuthenticator,
)

# Stake verification
from usmsb_sdk.platform.external.auth.stake_verifier import (
    StakeInfo,
    AgentRegistration,
    IStakeVerifier,
    MockStakeVerifier,
    MINIMUM_STAKE_FOR_REGISTRATION,
    STAKE_LOCK_PERIOD_DAYS,
)

# Coordinator
from usmsb_sdk.platform.external.auth.auth_coordinator import (
    SessionInfo,
    VerificationContext,
    AuthCoordinator,
    SESSION_DURATION_HOURS,
    MAX_SESSION_DURATION_HOURS,
)

__all__ = [
    # Enums
    "Permission",
    "StakeTier",

    # Base types
    "AuthContext",
    "BaseAuthResult",
    "WalletAuthResult",
    "StakeVerificationResult",
    "FullAuthResult",
    "IAuthProvider",

    # Wallet authentication
    "WalletBinding",
    "IWalletAuthenticator",
    "MockWalletAuthenticator",

    # Stake verification
    "StakeInfo",
    "AgentRegistration",
    "IStakeVerifier",
    "MockStakeVerifier",
    "MINIMUM_STAKE_FOR_REGISTRATION",
    "STAKE_LOCK_PERIOD_DAYS",

    # Coordinator
    "SessionInfo",
    "VerificationContext",
    "AuthCoordinator",
    "SESSION_DURATION_HOURS",
    "MAX_SESSION_DURATION_HOURS",
]
