"""
Stake Verification Module

Provides stake amount verification and tier management interfaces.
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from usmsb_sdk.platform.external.auth.base_auth import (
    IAuthProvider,
    StakeTier,
    StakeVerificationResult,
)


@dataclass
class StakeInfo:
    """
    Detailed stake information for a wallet.

    Attributes:
        wallet_address: The wallet address
        total_stake: Total staked amount
        active_stake: Currently active stake
        locked_stake: Locked stake (cannot be withdrawn)
        pending_stake: Stake pending confirmation
        stake_tier: Current stake tier
        staked_at: When stake was made
        unlock_at: When stake can be unlocked
        rewards: Accumulated staking rewards
    """
    wallet_address: str
    total_stake: float = 0.0
    active_stake: float = 0.0
    locked_stake: float = 0.0
    pending_stake: float = 0.0
    stake_tier: StakeTier = StakeTier.NONE
    staked_at: datetime | None = None
    unlock_at: datetime | None = None
    rewards: float = 0.0


@dataclass
class AgentRegistration:
    """
    Represents an agent registration tied to stake.

    Attributes:
        agent_id: The agent identifier
        wallet_address: Owning wallet address
        registered_at: When the agent was registered
        required_stake: Minimum required stake for this agent
        is_active: Whether the agent is currently active
    """
    agent_id: str
    wallet_address: str
    registered_at: datetime = field(default_factory=datetime.now)
    required_stake: float = 100.0
    is_active: bool = True


# Constants for stake requirements
MINIMUM_STAKE_FOR_REGISTRATION = 100.0
STAKE_LOCK_PERIOD_DAYS = 30


class IStakeVerifier(IAuthProvider):
    """
    Abstract interface for stake verification.

    Provides methods for verifying stake amounts, managing stake tiers,
    and checking agent registration eligibility.
    """

    @abstractmethod
    async def verify_stake(
        self,
        wallet_address: str,
        minimum_amount: float = MINIMUM_STAKE_FOR_REGISTRATION
    ) -> StakeVerificationResult:
        """
        Verify that a wallet has sufficient stake.

        Args:
            wallet_address: The wallet address to verify
            minimum_amount: Minimum required stake amount

        Returns:
            StakeVerificationResult with verification details
        """
        pass

    @abstractmethod
    async def get_stake_info(
        self,
        wallet_address: str
    ) -> StakeInfo:
        """
        Get detailed stake information for a wallet.

        Args:
            wallet_address: The wallet address

        Returns:
            StakeInfo with detailed stake data
        """
        pass

    @abstractmethod
    async def get_stake_tier(
        self,
        wallet_address: str
    ) -> StakeTier:
        """
        Get the stake tier for a wallet.

        Args:
            wallet_address: The wallet address

        Returns:
            Current StakeTier
        """
        pass

    @abstractmethod
    async def can_register_agent(
        self,
        wallet_address: str
    ) -> bool:
        """
        Check if a wallet can register a new agent.

        This checks both sufficient stake and that the wallet
        hasn't exceeded the agent limit for its tier.

        Args:
            wallet_address: The wallet address

        Returns:
            True if wallet can register a new agent
        """
        pass

    @abstractmethod
    async def register_agent(
        self,
        wallet_address: str,
        agent_id: str,
        required_stake: float = MINIMUM_STAKE_FOR_REGISTRATION
    ) -> AgentRegistration:
        """
        Register an agent for a wallet.

        Args:
            wallet_address: The wallet address
            agent_id: The agent identifier
            required_stake: Required stake for this agent

        Returns:
            AgentRegistration object

        Raises:
            ValueError: If registration requirements not met
        """
        pass

    @abstractmethod
    async def unregister_agent(
        self,
        wallet_address: str,
        agent_id: str
    ) -> bool:
        """
        Unregister an agent from a wallet.

        Args:
            wallet_address: The wallet address
            agent_id: The agent identifier

        Returns:
            True if unregistration successful
        """
        pass

    @abstractmethod
    async def get_wallet_agents(
        self,
        wallet_address: str
    ) -> list[AgentRegistration]:
        """
        Get all agents registered to a wallet.

        Args:
            wallet_address: The wallet address

        Returns:
            List of AgentRegistration objects
        """
        pass

    @abstractmethod
    async def lock_stake(
        self,
        wallet_address: str,
        amount: float,
        duration_days: int = STAKE_LOCK_PERIOD_DAYS
    ) -> StakeInfo:
        """
        Lock a portion of stake for a specified duration.

        Args:
            wallet_address: The wallet address
            amount: Amount to lock
            duration_days: Lock duration in days

        Returns:
            Updated StakeInfo

        Raises:
            ValueError: If insufficient stake to lock
        """
        pass

    @abstractmethod
    async def unlock_stake(
        self,
        wallet_address: str,
        amount: float | None = None
    ) -> StakeInfo:
        """
        Unlock staked tokens.

        Args:
            wallet_address: The wallet address
            amount: Amount to unlock (None = all unlocked)

        Returns:
            Updated StakeInfo
        """
        pass


class MockStakeVerifier(IStakeVerifier):
    """
    Mock implementation of IStakeVerifier for testing.

    This implementation stores all data in memory and simulates
    stake operations without blockchain interaction.
    """

    def __init__(self):
        """Initialize the mock stake verifier."""
        self._initialized: bool = False
        self._stakes: dict[str, StakeInfo] = {}  # wallet -> stake info
        self._agent_registrations: dict[str, list[AgentRegistration]] = {}  # wallet -> agents
        self._agent_to_wallet: dict[str, str] = {}  # agent_id -> wallet

    async def initialize(self) -> bool:
        """Initialize the mock verifier."""
        self._initialized = True
        return True

    async def shutdown(self) -> bool:
        """Shutdown the mock verifier."""
        self._initialized = False
        return True

    def is_ready(self) -> bool:
        """Check if the provider is ready."""
        return self._initialized

    def _get_or_create_stake_info(self, wallet_address: str) -> StakeInfo:
        """Get or create stake info for a wallet."""
        wallet_address = wallet_address.lower()
        if wallet_address not in self._stakes:
            self._stakes[wallet_address] = StakeInfo(
                wallet_address=wallet_address,
                total_stake=0.0,
                stake_tier=StakeTier.NONE
            )
        return self._stakes[wallet_address]

    async def verify_stake(
        self,
        wallet_address: str,
        minimum_amount: float = MINIMUM_STAKE_FOR_REGISTRATION
    ) -> StakeVerificationResult:
        """Verify that a wallet has sufficient stake."""
        if not self._initialized:
            return StakeVerificationResult(
                success=False,
                error_code="NOT_INITIALIZED",
                error_message="Verifier not initialized"
            )

        wallet_address = wallet_address.lower()
        stake_info = self._get_or_create_stake_info(wallet_address)

        active_agents = len([
            a for a in self._agent_registrations.get(wallet_address, [])
            if a.is_active
        ])

        has_sufficient = stake_info.active_stake >= minimum_amount
        tier = StakeTier.from_amount(stake_info.active_stake)
        max_agents = tier.max_agents
        can_register = has_sufficient and active_agents < max_agents

        return StakeVerificationResult(
            success=has_sufficient,
            wallet_address=wallet_address,
            stake_amount=stake_info.active_stake,
            stake_tier=tier,
            can_register=can_register,
            active_agents=active_agents,
            max_agents=max_agents,
            locked_until=stake_info.unlock_at,
            error_code=None if has_sufficient else "INSUFFICIENT_STAKE",
            error_message=None if has_sufficient else (
                f"Stake {stake_info.active_stake} is below minimum {minimum_amount}"
            )
        )

    async def get_stake_info(
        self,
        wallet_address: str
    ) -> StakeInfo:
        """Get detailed stake information for a wallet."""
        wallet_address = wallet_address.lower()
        return self._get_or_create_stake_info(wallet_address)

    async def get_stake_tier(
        self,
        wallet_address: str
    ) -> StakeTier:
        """Get the stake tier for a wallet."""
        wallet_address = wallet_address.lower()
        stake_info = self._get_or_create_stake_info(wallet_address)
        return stake_info.stake_tier

    async def can_register_agent(
        self,
        wallet_address: str
    ) -> bool:
        """Check if a wallet can register a new agent."""
        result = await self.verify_stake(wallet_address)
        return result.can_register

    async def register_agent(
        self,
        wallet_address: str,
        agent_id: str,
        required_stake: float = MINIMUM_STAKE_FOR_REGISTRATION
    ) -> AgentRegistration:
        """Register an agent for a wallet."""
        wallet_address = wallet_address.lower()

        # Verify can register
        can_register = await self.can_register_agent(wallet_address)
        if not can_register:
            raise ValueError(f"Wallet {wallet_address} cannot register more agents")

        # Check agent not already registered
        if agent_id in self._agent_to_wallet:
            raise ValueError(f"Agent {agent_id} is already registered")

        # Create registration
        registration = AgentRegistration(
            agent_id=agent_id,
            wallet_address=wallet_address,
            required_stake=required_stake,
            is_active=True
        )

        # Store registration
        if wallet_address not in self._agent_registrations:
            self._agent_registrations[wallet_address] = []
        self._agent_registrations[wallet_address].append(registration)
        self._agent_to_wallet[agent_id] = wallet_address

        return registration

    async def unregister_agent(
        self,
        wallet_address: str,
        agent_id: str
    ) -> bool:
        """Unregister an agent from a wallet."""
        wallet_address = wallet_address.lower()

        if agent_id not in self._agent_to_wallet:
            return False

        if self._agent_to_wallet[agent_id] != wallet_address:
            return False

        # Mark as inactive instead of removing
        for reg in self._agent_registrations.get(wallet_address, []):
            if reg.agent_id == agent_id:
                reg.is_active = False
                break

        del self._agent_to_wallet[agent_id]
        return True

    async def get_wallet_agents(
        self,
        wallet_address: str
    ) -> list[AgentRegistration]:
        """Get all agents registered to a wallet."""
        wallet_address = wallet_address.lower()
        return list(self._agent_registrations.get(wallet_address, []))

    async def lock_stake(
        self,
        wallet_address: str,
        amount: float,
        duration_days: int = STAKE_LOCK_PERIOD_DAYS
    ) -> StakeInfo:
        """Lock a portion of stake."""
        wallet_address = wallet_address.lower()
        stake_info = self._get_or_create_stake_info(wallet_address)

        available = stake_info.total_stake - stake_info.locked_stake
        if amount > available:
            raise ValueError(
                f"Cannot lock {amount}, only {available} available"
            )

        stake_info.locked_stake += amount
        stake_info.active_stake = stake_info.total_stake - stake_info.locked_stake
        stake_info.unlock_at = datetime.now() + timedelta(days=duration_days)
        stake_info.stake_tier = StakeTier.from_amount(stake_info.active_stake)

        return stake_info

    async def unlock_stake(
        self,
        wallet_address: str,
        amount: float | None = None
    ) -> StakeInfo:
        """Unlock staked tokens."""
        wallet_address = wallet_address.lower()
        stake_info = self._get_or_create_stake_info(wallet_address)

        # Check if lock period has ended
        if stake_info.unlock_at and datetime.now() < stake_info.unlock_at:
            raise ValueError(
                f"Stake is locked until {stake_info.unlock_at}"
            )

        unlock_amount = amount if amount is not None else stake_info.locked_stake
        unlock_amount = min(unlock_amount, stake_info.locked_stake)

        stake_info.locked_stake -= unlock_amount
        stake_info.active_stake = stake_info.total_stake - stake_info.locked_stake
        stake_info.stake_tier = StakeTier.from_amount(stake_info.active_stake)

        if stake_info.locked_stake == 0:
            stake_info.unlock_at = None

        return stake_info

    # Testing utilities
    def set_stake(
        self,
        wallet_address: str,
        amount: float
    ) -> StakeInfo:
        """
        Directly set stake amount for testing purposes.

        Args:
            wallet_address: The wallet address
            amount: Stake amount to set

        Returns:
            Updated StakeInfo
        """
        wallet_address = wallet_address.lower()
        stake_info = self._get_or_create_stake_info(wallet_address)
        stake_info.total_stake = amount
        stake_info.active_stake = amount - stake_info.locked_stake
        stake_info.stake_tier = StakeTier.from_amount(stake_info.active_stake)
        stake_info.staked_at = datetime.now()
        return stake_info

    def clear_all(self) -> None:
        """Clear all stake data - useful for testing."""
        self._stakes.clear()
        self._agent_registrations.clear()
        self._agent_to_wallet.clear()
