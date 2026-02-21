"""
Authentication Base Module

Provides base types, enums, and dataclasses for the authentication layer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class Permission(Enum):
    """Permission levels for authenticated entities."""

    NONE = "none"
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"
    OWNER = "owner"

    @classmethod
    def from_stake_amount(cls, amount: float) -> "Permission":
        """
        Determine permission level based on stake amount.

        Args:
            amount: Stake amount in tokens

        Returns:
            Permission level
        """
        if amount >= 10000:
            return cls.OWNER
        elif amount >= 5000:
            return cls.ADMIN
        elif amount >= 1000:
            return cls.EXECUTE
        elif amount >= 100:
            return cls.WRITE
        elif amount > 0:
            return cls.READ
        return cls.NONE


class StakeTier(Enum):
    """Stake tier levels for agents."""

    NONE = "none"
    BRONZE = "bronze"      # 100 - 999 tokens
    SILVER = "silver"      # 1000 - 4999 tokens
    GOLD = "gold"          # 5000 - 9999 tokens
    PLATINUM = "platinum"  # 10000+ tokens

    @classmethod
    def from_amount(cls, amount: float) -> "StakeTier":
        """
        Determine stake tier from amount.

        Args:
            amount: Stake amount in tokens

        Returns:
            StakeTier level
        """
        if amount >= 10000:
            return cls.PLATINUM
        elif amount >= 5000:
            return cls.GOLD
        elif amount >= 1000:
            return cls.SILVER
        elif amount >= 100:
            return cls.BRONZE
        return cls.NONE

    @property
    def minimum_stake(self) -> float:
        """Get minimum stake amount for this tier."""
        return {
            StakeTier.NONE: 0,
            StakeTier.BRONZE: 100,
            StakeTier.SILVER: 1000,
            StakeTier.GOLD: 5000,
            StakeTier.PLATINUM: 10000,
        }[self]

    @property
    def max_agents(self) -> int:
        """Get maximum number of agents allowed for this tier."""
        return {
            StakeTier.NONE: 0,
            StakeTier.BRONZE: 1,
            StakeTier.SILVER: 3,
            StakeTier.GOLD: 10,
            StakeTier.PLATINUM: 50,
        }[self]


@dataclass
class AuthContext:
    """
    Authentication context containing all information needed for verification.

    Attributes:
        wallet_address: Wallet address to authenticate
        agent_id: Optional agent identifier
        signature: Cryptographic signature
        message: Message that was signed
        nonce: Optional nonce for replay protection
        timestamp: When the auth request was made
        metadata: Additional metadata
    """
    wallet_address: str
    agent_id: Optional[str] = None
    signature: Optional[str] = None
    message: Optional[str] = None
    nonce: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BaseAuthResult:
    """
    Base class for authentication results.

    Attributes:
        success: Whether the authentication was successful
        error_code: Error code if failed
        error_message: Human-readable error message
        timestamp: When the result was generated
    """
    success: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class WalletAuthResult(BaseAuthResult):
    """
    Result of wallet authentication.

    Attributes:
        wallet_address: Verified wallet address
        is_verified: Whether wallet ownership was verified
        did: Decentralized identifier for the wallet
        permissions: Granted permission level
        expires_at: When the authentication expires
    """
    wallet_address: Optional[str] = None
    is_verified: bool = False
    did: Optional[str] = None
    permissions: Permission = Permission.NONE
    expires_at: Optional[datetime] = None


@dataclass
class StakeVerificationResult(BaseAuthResult):
    """
    Result of stake verification.

    Attributes:
        wallet_address: Wallet address that was verified
        stake_amount: Current stake amount
        stake_tier: Current stake tier
        can_register: Whether the wallet can register a new agent
        active_agents: Number of currently active agents
        max_agents: Maximum agents allowed for this tier
        locked_until: When locked stake becomes available (if any)
    """
    wallet_address: Optional[str] = None
    stake_amount: float = 0.0
    stake_tier: StakeTier = StakeTier.NONE
    can_register: bool = False
    active_agents: int = 0
    max_agents: int = 0
    locked_until: Optional[datetime] = None


@dataclass
class FullAuthResult(BaseAuthResult):
    """
    Complete authentication result combining all verification results.

    Attributes:
        wallet_auth: Wallet authentication result
        stake_verification: Stake verification result
        agent_id: Associated agent ID if any
        session_token: Session token for authenticated session
        permissions: Combined permission set
        valid_until: When the full authentication expires
    """
    wallet_auth: Optional[WalletAuthResult] = None
    stake_verification: Optional[StakeVerificationResult] = None
    agent_id: Optional[str] = None
    session_token: Optional[str] = None
    permissions: List[Permission] = field(default_factory=list)
    valid_until: Optional[datetime] = None


class IAuthProvider(ABC):
    """
    Base interface for authentication providers.

    All authentication components should inherit from this interface.
    """

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the authentication provider.

        Returns:
            True if initialization successful
        """
        pass

    @abstractmethod
    async def shutdown(self) -> bool:
        """
        Shutdown the authentication provider.

        Returns:
            True if shutdown successful
        """
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """
        Check if the provider is ready for use.

        Returns:
            True if ready
        """
        pass
