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
# Coordinator
from usmsb_sdk.platform.external.auth.auth_coordinator import (
    MAX_SESSION_DURATION_HOURS,
    SESSION_DURATION_HOURS,
    AuthCoordinator,
    SessionInfo,
    VerificationContext,
)
from usmsb_sdk.platform.external.auth.base_auth import (
    AuthContext,
    BaseAuthResult,
    FullAuthResult,
    IAuthProvider,
    Permission,
    StakeTier,
    StakeVerificationResult,
    WalletAuthResult,
)

# Stake verification
from usmsb_sdk.platform.external.auth.stake_verifier import (
    MINIMUM_STAKE_FOR_REGISTRATION,
    STAKE_LOCK_PERIOD_DAYS,
    AgentRegistration,
    IStakeVerifier,
    MockStakeVerifier,
    StakeInfo,
)

# Wallet authentication
from usmsb_sdk.platform.external.auth.wallet_auth import (
    IWalletAuthenticator,
    MockWalletAuthenticator,
    WalletBinding,
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
