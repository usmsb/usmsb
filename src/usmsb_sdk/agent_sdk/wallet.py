"""
Wallet Module

Manages agent wallet, staking, and transactions.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from usmsb_sdk.agent_sdk.platform_client import PlatformClient, APIResponse


logger = logging.getLogger(__name__)


class StakeStatus(Enum):
    """Stake status"""
    NONE = "none"
    STAKED = "staked"
    UNSTAKING = "unstaking"
    LOCKED = "locked"


class TransactionStatus(Enum):
    """Transaction status"""
    CREATED = "created"
    ESCROWED = "escrowed"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    DISPUTED = "disputed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class TransactionType(Enum):
    """Transaction type"""
    SERVICE_PAYMENT = "service_payment"
    STAKE = "stake"
    UNSTAKE = "unstake"
    REFUND = "refund"
    REWARD = "reward"


@dataclass
class WalletBalance:
    """Wallet balance information"""
    available_balance: float
    staked_amount: float
    locked_amount: float
    pending_incoming: float
    pending_outgoing: float

    @property
    def total_balance(self) -> float:
        return self.available_balance + self.staked_amount + self.locked_amount

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WalletBalance":
        return cls(
            available_balance=data.get("available_balance", data.get("vibe_balance", 0)),
            staked_amount=data.get("staked_amount", data.get("stake", 0)),
            locked_amount=data.get("locked_amount", data.get("locked_stake", 0)),
            pending_incoming=data.get("pending_incoming", 0),
            pending_outgoing=data.get("pending_outgoing", 0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "available_balance": self.available_balance,
            "staked_amount": self.staked_amount,
            "locked_amount": self.locked_amount,
            "pending_incoming": self.pending_incoming,
            "pending_outgoing": self.pending_outgoing,
            "total_balance": self.total_balance,
        }


@dataclass
class StakeInfo:
    """Stake information"""
    staked_amount: float
    stake_status: str
    locked_stake: float
    unlock_available_at: Optional[datetime]
    reputation_boost: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StakeInfo":
        unlock_at = None
        if data.get("unlock_available_at"):
            if isinstance(data["unlock_available_at"], (int, float)):
                unlock_at = datetime.fromtimestamp(data["unlock_available_at"])
            else:
                unlock_at = data["unlock_available_at"]

        staked = data.get("staked_amount", data.get("stake", 0))
        reputation = min(0.5 + (staked / 1000), 1.0)

        return cls(
            staked_amount=staked,
            stake_status=data.get("stake_status", "none"),
            locked_stake=data.get("locked_stake", 0),
            unlock_available_at=unlock_at,
            reputation_boost=reputation,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "staked_amount": self.staked_amount,
            "stake_status": self.stake_status,
            "locked_stake": self.locked_stake,
            "unlock_available_at": self.unlock_available_at.isoformat() if self.unlock_available_at else None,
            "reputation_boost": self.reputation_boost,
        }


@dataclass
class Transaction:
    """Transaction record"""
    tx_id: str
    tx_type: str
    amount: float
    counterparty_id: str
    status: str
    title: Optional[str]
    description: Optional[str]
    platform_fee: float
    created_at: Optional[datetime]
    completed_at: Optional[datetime]
    rating: Optional[int]
    review: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        created_at = None
        if data.get("created_at"):
            if isinstance(data["created_at"], (int, float)):
                created_at = datetime.fromtimestamp(data["created_at"])
            else:
                created_at = data["created_at"]

        completed_at = None
        if data.get("completed_at"):
            if isinstance(data["completed_at"], (int, float)):
                completed_at = datetime.fromtimestamp(data["completed_at"])
            else:
                completed_at = data["completed_at"]

        return cls(
            tx_id=data.get("id", ""),
            tx_type=data.get("transaction_type", "service_payment"),
            amount=data.get("amount", 0),
            counterparty_id=data.get("seller_id") if data.get("seller_id") != data.get("buyer_id") else data.get("buyer_id"),
            status=data.get("status", "created"),
            title=data.get("title"),
            description=data.get("description"),
            platform_fee=data.get("platform_fee", 0),
            created_at=created_at,
            completed_at=completed_at,
            rating=data.get("rating"),
            review=data.get("review"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "tx_type": self.tx_type,
            "amount": self.amount,
            "counterparty_id": self.counterparty_id,
            "status": self.status,
            "title": self.title,
            "description": self.description,
            "platform_fee": self.platform_fee,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "rating": self.rating,
            "review": self.review,
        }


@dataclass
class WalletLimits:
    """Wallet spending limits"""
    max_per_tx: float
    daily_limit: float
    daily_spent: float

    @property
    def daily_remaining(self) -> float:
        return max(0, self.daily_limit - self.daily_spent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WalletLimits":
        return cls(
            max_per_tx=data.get("max_per_tx", 500),
            daily_limit=data.get("daily_limit", 1000),
            daily_spent=data.get("daily_spent", 0),
        )


@dataclass
class StakeResult:
    """Result of a stake operation"""
    success: bool
    amount: float
    total_staked: float
    new_reputation: float
    message: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StakeResult":
        return cls(
            success=data.get("success", False),
            amount=data.get("amount", 0),
            total_staked=data.get("total_stake", 0),
            new_reputation=data.get("reputation", 0.5),
            message=data.get("message", ""),
        )


class WalletManager:
    """
    Manages agent wallet operations.

    Features:
    - Balance queries
    - Staking/unstaking
    - Transaction history
    - Spending limits
    """

    def __init__(
        self,
        platform_client: PlatformClient,
        logger: Optional[logging.Logger] = None,
    ):
        self._platform = platform_client
        self.logger = logger or logging.getLogger(__name__)

        # Local cache
        self._balance_cache: Optional[WalletBalance] = None
        self._stake_cache: Optional[StakeInfo] = None

    # ==================== Balance ====================

    async def get_balance(self, use_cache: bool = False) -> WalletBalance:
        """
        Get wallet balance.

        Args:
            use_cache: Return cached value if available

        Returns:
            WalletBalance object
        """
        if use_cache and self._balance_cache:
            return self._balance_cache

        # Query platform for balance
        # Note: This would need a dedicated platform endpoint
        # For now, use registration status which includes stake
        response = await self._platform.get_registration_status()

        if response.success and response.data:
            self._balance_cache = WalletBalance.from_dict(response.data)
        else:
            self._balance_cache = WalletBalance(
                available_balance=0,
                staked_amount=0,
                locked_amount=0,
                pending_incoming=0,
                pending_outgoing=0,
            )

        return self._balance_cache

    async def refresh_balance(self) -> WalletBalance:
        """Force refresh balance from platform"""
        return await self.get_balance(use_cache=False)

    # ==================== Staking ====================

    async def get_stake_info(self) -> StakeInfo:
        """Get stake information"""
        response = await self._platform.get_registration_status()

        if response.success and response.data:
            self._stake_cache = StakeInfo.from_dict(response.data)
        else:
            self._stake_cache = StakeInfo(
                staked_amount=0,
                stake_status="none",
                locked_stake=0,
                unlock_available_at=None,
                reputation_boost=0.5,
            )

        return self._stake_cache

    async def stake(self, amount: float) -> StakeResult:
        """
        Stake tokens to increase reputation.

        Args:
            amount: Amount to stake

        Returns:
            StakeResult with operation status
        """
        if amount <= 0:
            return StakeResult(
                success=False,
                amount=0,
                total_staked=0,
                new_reputation=0.5,
                message="Amount must be positive",
            )

        response = await self._platform.stake(amount)

        if response.success and response.data:
            result = StakeResult.from_dict(response.data)
            result.amount = amount
            self.logger.info(f"Staked {amount} tokens. Total: {result.total_staked}, Reputation: {result.new_reputation}")

            # Clear cache
            self._balance_cache = None
            self._stake_cache = None

            return result

        return StakeResult(
            success=False,
            amount=amount,
            total_staked=0,
            new_reputation=0.5,
            message=response.error or "Staking failed",
        )

    async def unstake(self, amount: float) -> StakeResult:
        """
        Unstake tokens.

        Args:
            amount: Amount to unstake

        Returns:
            StakeResult with operation status
        """
        # TODO: Implement when platform API supports unstaking
        self.logger.warning("Unstaking not yet implemented in platform API")
        return StakeResult(
            success=False,
            amount=amount,
            total_staked=0,
            new_reputation=0.5,
            message="Unstaking not yet supported",
        )

    async def get_unstake_status(self) -> Dict[str, Any]:
        """Get unstaking status and unlock time"""
        stake_info = await self.get_stake_info()
        return {
            "status": stake_info.stake_status,
            "locked_amount": stake_info.locked_stake,
            "unlock_available_at": stake_info.unlock_available_at.isoformat() if stake_info.unlock_available_at else None,
        }

    # ==================== Transactions ====================

    async def get_transaction_history(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Transaction]:
        """
        Get transaction history.

        Args:
            status: Filter by status
            limit: Maximum results

        Returns:
            List of Transaction objects
        """
        # TODO: Implement when platform has transaction history endpoint
        # For now, return empty list
        self.logger.debug("Transaction history not yet available from platform")
        return []

    async def get_pending_transactions(self) -> List[Transaction]:
        """Get pending (non-completed) transactions"""
        all_tx = await self.get_transaction_history()
        pending_statuses = ["created", "escrowed", "in_progress", "delivered", "disputed"]
        return [tx for tx in all_tx if tx.status in pending_statuses]

    async def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        """Get a specific transaction"""
        # TODO: Implement when platform has transaction endpoint
        return None

    # ==================== Limits ====================

    async def get_limits(self) -> WalletLimits:
        """Get wallet spending limits"""
        # TODO: Get from platform
        return WalletLimits(
            max_per_tx=500,
            daily_limit=1000,
            daily_spent=0,
        )

    async def check_can_spend(self, amount: float) -> Dict[str, Any]:
        """
        Check if agent can spend specified amount.

        Returns:
            Dict with 'can_spend' boolean and 'reason' if not
        """
        balance = await self.get_balance()
        limits = await self.get_limits()

        if amount > balance.available_balance:
            return {"can_spend": False, "reason": "Insufficient balance"}

        if amount > limits.max_per_tx:
            return {"can_spend": False, "reason": f"Amount exceeds per-transaction limit of {limits.max_per_tx}"}

        if amount > limits.daily_remaining:
            return {"can_spend": False, "reason": f"Amount exceeds remaining daily limit of {limits.daily_remaining}"}

        return {"can_spend": True, "reason": None}

    # ==================== Summary ====================

    async def get_wallet_summary(self) -> Dict[str, Any]:
        """Get complete wallet summary"""
        balance = await self.get_balance()
        stake_info = await self.get_stake_info()
        limits = await self.get_limits()

        return {
            "balance": balance.to_dict(),
            "stake": stake_info.to_dict(),
            "limits": {
                "max_per_tx": limits.max_per_tx,
                "daily_limit": limits.daily_limit,
                "daily_spent": limits.daily_spent,
                "daily_remaining": limits.daily_remaining,
            },
            "reputation": stake_info.reputation_boost,
        }
