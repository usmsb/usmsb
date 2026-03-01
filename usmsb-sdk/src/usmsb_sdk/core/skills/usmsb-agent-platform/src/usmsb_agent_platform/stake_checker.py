"""
Stake checker for verifying stake requirements.
"""

from typing import Dict, Optional, Tuple

from .types import ActionType, StakeInfo, StakeTier, StakeRequirement


class StakeChecker:
    """
    Check stake requirements for platform actions.

    Rules follow the whitepaper:
    - Bronze (100 VIBE) is the minimum for "earning" features
    - "Spending" features don't require stake
    """

    # Minimum stake required for earning features (whitepaper rule)
    MIN_STAKE_WHITEPAPER: int = 100  # Bronze tier

    # Tier configuration
    TIER_CONFIG: Dict[StakeTier, Dict[str, int]] = {
        StakeTier.NONE: {"min": 0, "max_agents": 0, "discount": 0},
        StakeTier.BRONZE: {"min": 100, "max_agents": 1, "discount": 0},
        StakeTier.SILVER: {"min": 1000, "max_agents": 3, "discount": 5},
        StakeTier.GOLD: {"min": 5000, "max_agents": 10, "discount": 10},
        StakeTier.PLATINUM: {"min": 10000, "max_agents": 50, "discount": 20},
    }

    def __init__(self, platform_client: Optional[object] = None):
        """
        Initialize stake checker.

        Args:
            platform_client: Optional platform client for fetching stake info
        """
        self.client = platform_client
        self._cache: Dict[str, StakeInfo] = {}

    async def get_stake_info(self, agent_id: str) -> StakeInfo:
        """
        Get stake information for an agent.

        Args:
            agent_id: The agent's ID

        Returns:
            StakeInfo object with stake details
        """
        # Check cache first
        if agent_id in self._cache:
            return self._cache[agent_id]

        # Fetch from platform if client available
        if self.client and hasattr(self.client, 'get_staked_amount'):
            staked_amount = await self.client.get_staked_amount(agent_id)
        else:
            # Default to 0 if no client
            staked_amount = 0

        info = StakeInfo.from_amount(agent_id, staked_amount)
        self._cache[agent_id] = info
        return info

    async def verify_stake(self, agent_id: str, action: ActionType) -> Tuple[bool, Optional[str]]:
        """
        Verify if an agent has sufficient stake for an action.

        Args:
            agent_id: The agent's ID
            action: The action to verify

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Actions that don't require stake pass immediately
        if not action.requires_stake:
            return True, None

        # Get stake info
        stake_info = await self.get_stake_info(agent_id)

        # Check if stake is sufficient
        if stake_info.staked_amount < self.MIN_STAKE_WHITEPAPER:
            return False, (
                f"Insufficient stake: action '{action.action}' requires "
                f"minimum {self.MIN_STAKE_WHITEPAPER} VIBE, "
                f"but agent has {stake_info.staked_amount} VIBE"
            )

        return True, None

    async def get_stake_requirement(
        self, agent_id: str, action: ActionType
    ) -> Optional[StakeRequirement]:
        """
        Get detailed stake requirement for an action.

        Args:
            agent_id: The agent's ID
            action: The action to check

        Returns:
            StakeRequirement if stake is required and insufficient, None otherwise
        """
        # Actions that don't require stake
        if not action.requires_stake:
            return None

        # Get stake info
        stake_info = await self.get_stake_info(agent_id)

        # If stake is sufficient, no requirement info needed
        if stake_info.staked_amount >= self.MIN_STAKE_WHITEPAPER:
            return None

        # Return detailed requirement info
        shortfall = self.MIN_STAKE_WHITEPAPER - stake_info.staked_amount
        return StakeRequirement(
            required=self.MIN_STAKE_WHITEPAPER,
            current=stake_info.staked_amount,
            shortfall=shortfall,
            action=f"{action.category}.{action.action}"
        )

    async def verify_stake_with_detail(
        self, agent_id: str, action: ActionType
    ) -> Tuple[bool, Optional[StakeRequirement]]:
        """
        Verify stake and return detailed requirement info on failure.

        Args:
            agent_id: The agent's ID
            action: The action to verify

        Returns:
            Tuple of (is_valid, stake_requirement_or_none)
        """
        # Actions that don't require stake pass immediately
        if not action.requires_stake:
            return True, None

        # Get stake info
        stake_info = await self.get_stake_info(agent_id)

        # Check if stake is sufficient
        if stake_info.staked_amount >= self.MIN_STAKE_WHITEPAPER:
            return True, None

        # Return failure with detailed requirement
        shortfall = self.MIN_STAKE_WHITEPAPER - stake_info.staked_amount
        requirement = StakeRequirement(
            required=self.MIN_STAKE_WHITEPAPER,
            current=stake_info.staked_amount,
            shortfall=shortfall,
            action=f"{action.category}.{action.action}"
        )
        return False, requirement

    @classmethod
    def get_tier(cls, stake_amount: int) -> StakeTier:
        """
        Determine stake tier from amount.

        Args:
            stake_amount: Amount of VIBE staked

        Returns:
            Corresponding StakeTier
        """
        if stake_amount >= StakeTier.PLATINUM.value:
            return StakeTier.PLATINUM
        elif stake_amount >= StakeTier.GOLD.value:
            return StakeTier.GOLD
        elif stake_amount >= StakeTier.SILVER.value:
            return StakeTier.SILVER
        elif stake_amount >= StakeTier.BRONZE.value:
            return StakeTier.BRONZE
        else:
            return StakeTier.NONE

    @classmethod
    def get_max_agents(cls, tier: StakeTier) -> int:
        """Get maximum number of agents for a tier."""
        return cls.TIER_CONFIG.get(tier, {}).get("max_agents", 0)

    @classmethod
    def get_discount(cls, tier: StakeTier) -> int:
        """Get discount percentage for a tier."""
        return cls.TIER_CONFIG.get(tier, {}).get("discount", 0)

    @classmethod
    def calculate_reputation(cls, stake_amount: int) -> float:
        """
        Calculate reputation score from stake amount.

        Formula from whitepaper: reputation = min(0.5 + (staked / 1000), 1.0)

        Args:
            stake_amount: Amount of VIBE staked

        Returns:
            Reputation score between 0.5 and 1.0
        """
        return min(0.5 + (stake_amount / 1000), 1.0)

    def clear_cache(self, agent_id: Optional[str] = None):
        """
        Clear stake info cache.

        Args:
            agent_id: Specific agent to clear, or None to clear all
        """
        if agent_id:
            self._cache.pop(agent_id, None)
        else:
            self._cache.clear()
