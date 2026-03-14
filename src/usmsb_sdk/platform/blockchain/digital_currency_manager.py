"""
Digital Currency Manager

Manages the platform's internal digital currency including
issuance, transfers, staking, and exchange operations.
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any

from usmsb_sdk.platform.blockchain.adapter import (
    IBlockchainAdapter,
    MockBlockchainAdapter,
    TransactionStatus,
)

logger = logging.getLogger(__name__)


class CurrencyType(StrEnum):
    """Types of digital currency."""
    NATIVE = "native"  # Platform native token
    STAKED = "staked"  # Staked tokens
    REWARD = "reward"  # Reward tokens
    GOVERNANCE = "governance"  # Governance tokens


class TransactionType(StrEnum):
    """Types of currency transactions."""
    MINT = "mint"
    BURN = "burn"
    TRANSFER = "transfer"
    STAKE = "stake"
    UNSTAKE = "unstake"
    REWARD = "reward"
    EXCHANGE_IN = "exchange_in"
    EXCHANGE_OUT = "exchange_out"


@dataclass
class CurrencyConfig:
    """Configuration for digital currency."""
    name: str = "USMSB Token"
    symbol: str = "USMSB"
    decimals: int = 18
    total_supply: Decimal = Decimal("1000000000")  # 1 billion
    initial_circulating_supply: Decimal = Decimal("100000000")  # 100 million
    staking_reward_rate: Decimal = Decimal("0.05")  # 5% annual
    min_stake_amount: Decimal = Decimal("100")
    unstake_cooldown_days: int = 7
    max_supply: Decimal = Decimal("10000000000")  # 10 billion cap


@dataclass
class CurrencyBalance:
    """Currency balance information."""
    address: str
    available: Decimal = Decimal("0")
    staked: Decimal = Decimal("0")
    rewards: Decimal = Decimal("0")
    total: Decimal = Decimal("0")
    updated_at: float = field(default_factory=lambda: time.time())

    def calculate_total(self) -> Decimal:
        """Calculate total balance."""
        self.total = self.available + self.staked + self.rewards
        return self.total


@dataclass
class StakeInfo:
    """Staking information."""
    address: str
    amount: Decimal
    staked_at: float
    unlock_at: float
    reward_rate: Decimal
    accumulated_rewards: Decimal = Decimal("0")
    status: str = "active"


@dataclass
class CurrencyTransaction:
    """Currency transaction record."""
    id: str
    type: TransactionType
    from_address: str | None
    to_address: str | None
    amount: Decimal
    currency_type: CurrencyType
    status: TransactionStatus
    blockchain_tx_hash: str | None = None
    created_at: float = field(default_factory=lambda: time.time())
    completed_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class DigitalCurrencyManager:
    """
    Digital Currency Manager.

    Manages the platform's internal digital currency system including:
    - Token issuance and distribution
    - Balance management
    - Staking mechanism
    - Reward distribution
    - Exchange with external currencies
    """

    def __init__(
        self,
        blockchain_adapter: IBlockchainAdapter | None = None,
        config: CurrencyConfig | None = None,
    ):
        """
        Initialize the Digital Currency Manager.

        Args:
            blockchain_adapter: Blockchain adapter for on-chain operations
            config: Currency configuration
        """
        self.blockchain = blockchain_adapter or MockBlockchainAdapter()
        self.config = config or CurrencyConfig()

        # State
        self._balances: dict[str, CurrencyBalance] = {}
        self._stakes: dict[str, StakeInfo] = {}
        self._transactions: dict[str, CurrencyTransaction] = {}
        self._circulating_supply = self.config.initial_circulating_supply
        self._total_minted = self.config.initial_circulating_supply

        # Platform treasury wallet
        self._treasury_address: str | None = None

    async def initialize(self) -> bool:
        """
        Initialize the currency manager.

        Returns:
            True if successful
        """
        # Initialize blockchain adapter
        success = await self.blockchain.initialize({})
        if not success:
            logger.error("Failed to initialize blockchain adapter")
            return False

        # Create treasury wallet
        treasury_wallet = await self.blockchain.create_wallet()
        self._treasury_address = treasury_wallet.address

        # Initialize treasury balance with circulating supply
        self._balances[self._treasury_address] = CurrencyBalance(
            address=self._treasury_address,
            available=self.config.initial_circulating_supply,
        )

        logger.info(f"Digital Currency Manager initialized. Treasury: {self._treasury_address}")
        return True

    async def shutdown(self) -> None:
        """Shutdown the currency manager."""
        await self.blockchain.shutdown()
        self._balances.clear()
        self._stakes.clear()
        self._transactions.clear()

    async def get_balance(self, address: str) -> CurrencyBalance:
        """
        Get currency balance for an address.

        Args:
            address: Wallet address

        Returns:
            Currency balance
        """
        if address not in self._balances:
            self._balances[address] = CurrencyBalance(address=address)

        balance = self._balances[address]
        balance.calculate_total()
        return balance

    async def mint(
        self,
        to_address: str,
        amount: Decimal,
        reason: str = "mint",
    ) -> CurrencyTransaction:
        """
        Mint new tokens.

        Args:
            to_address: Recipient address
            amount: Amount to mint
            reason: Reason for minting

        Returns:
            Transaction record
        """
        # Check max supply
        if self._total_minted + amount > self.config.max_supply:
            raise ValueError("Minting would exceed maximum supply")

        tx_id = self._generate_tx_id("mint", to_address)

        transaction = CurrencyTransaction(
            id=tx_id,
            type=TransactionType.MINT,
            from_address=None,
            to_address=to_address,
            amount=amount,
            currency_type=CurrencyType.NATIVE,
            status=TransactionStatus.PENDING,
            metadata={"reason": reason},
        )

        try:
            # Update balances
            if to_address not in self._balances:
                self._balances[to_address] = CurrencyBalance(address=to_address)

            self._balances[to_address].available += amount
            self._total_minted += amount
            self._circulating_supply += amount

            transaction.status = TransactionStatus.CONFIRMED
            transaction.completed_at = time.time()

        except Exception as e:
            transaction.status = TransactionStatus.FAILED
            transaction.metadata["error"] = str(e)
            logger.error(f"Mint failed: {e}")

        self._transactions[tx_id] = transaction
        return transaction

    async def transfer(
        self,
        from_address: str,
        to_address: str,
        amount: Decimal,
    ) -> CurrencyTransaction:
        """
        Transfer tokens between addresses.

        Args:
            from_address: Sender address
            to_address: Recipient address
            amount: Amount to transfer

        Returns:
            Transaction record
        """
        tx_id = self._generate_tx_id("transfer", from_address, to_address)

        transaction = CurrencyTransaction(
            id=tx_id,
            type=TransactionType.TRANSFER,
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            currency_type=CurrencyType.NATIVE,
            status=TransactionStatus.PENDING,
        )

        # Check balance
        from_balance = await self.get_balance(from_address)
        if from_balance.available < amount:
            transaction.status = TransactionStatus.FAILED
            transaction.metadata["error"] = "Insufficient balance"
            self._transactions[tx_id] = transaction
            return transaction

        try:
            # Update balances
            self._balances[from_address].available -= amount

            if to_address not in self._balances:
                self._balances[to_address] = CurrencyBalance(address=to_address)

            self._balances[to_address].available += amount

            # Record on blockchain (optional)
            blockchain_tx = await self.blockchain.transfer(
                from_address=from_address,
                to_address=to_address,
                value=Decimal("0"),  # Using internal ledger, blockchain tx is for record
                data=f"USMSB Transfer: {amount}",
            )

            transaction.status = TransactionStatus.CONFIRMED
            transaction.blockchain_tx_hash = blockchain_tx.tx_hash
            transaction.completed_at = time.time()

        except Exception as e:
            transaction.status = TransactionStatus.FAILED
            transaction.metadata["error"] = str(e)
            logger.error(f"Transfer failed: {e}")

        self._transactions[tx_id] = transaction
        return transaction

    async def stake(
        self,
        address: str,
        amount: Decimal,
    ) -> CurrencyTransaction:
        """
        Stake tokens for rewards.

        Args:
            address: Staker address
            amount: Amount to stake

        Returns:
            Transaction record
        """
        if amount < self.config.min_stake_amount:
            raise ValueError(f"Minimum stake amount is {self.config.min_stake_amount}")

        tx_id = self._generate_tx_id("stake", address)

        transaction = CurrencyTransaction(
            id=tx_id,
            type=TransactionType.STAKE,
            from_address=address,
            to_address=self._treasury_address,
            amount=amount,
            currency_type=CurrencyType.STAKED,
            status=TransactionStatus.PENDING,
        )

        # Check available balance
        balance = await self.get_balance(address)
        if balance.available < amount:
            transaction.status = TransactionStatus.FAILED
            transaction.metadata["error"] = "Insufficient balance"
            self._transactions[tx_id] = transaction
            return transaction

        try:
            # Update balances
            self._balances[address].available -= amount
            self._balances[address].staked += amount

            # Create stake info
            unlock_at = time.time() + (self.config.unstake_cooldown_days * 86400)
            stake_info = StakeInfo(
                address=address,
                amount=amount,
                staked_at=time.time(),
                unlock_at=unlock_at,
                reward_rate=self.config.staking_reward_rate,
            )
            self._stakes[f"{address}_{tx_id}"] = stake_info

            transaction.status = TransactionStatus.CONFIRMED
            transaction.completed_at = time.time()

        except Exception as e:
            transaction.status = TransactionStatus.FAILED
            transaction.metadata["error"] = str(e)

        self._transactions[tx_id] = transaction
        return transaction

    async def unstake(
        self,
        address: str,
        stake_id: str,
    ) -> CurrencyTransaction:
        """
        Unstake tokens.

        Args:
            address: Staker address
            stake_id: Stake identifier

        Returns:
            Transaction record
        """
        stake_key = f"{address}_{stake_id}"
        if stake_key not in self._stakes:
            raise ValueError("Stake not found")

        stake_info = self._stakes[stake_key]

        # Check lock period
        if time.time() < stake_info.unlock_at:
            remaining_days = (stake_info.unlock_at - time.time()) / 86400
            raise ValueError(f"Stake is locked for {remaining_days:.1f} more days")

        tx_id = self._generate_tx_id("unstake", address)

        transaction = CurrencyTransaction(
            id=tx_id,
            type=TransactionType.UNSTAKE,
            from_address=self._treasury_address,
            to_address=address,
            amount=stake_info.amount,
            currency_type=CurrencyType.STAKED,
            status=TransactionStatus.PENDING,
        )

        try:
            # Calculate and add rewards
            staking_duration = time.time() - stake_info.staked_at
            yearly_fraction = staking_duration / (365.25 * 86400)
            rewards = stake_info.amount * stake_info.reward_rate * Decimal(str(yearly_fraction))

            # Update balances
            self._balances[address].staked -= stake_info.amount
            self._balances[address].available += stake_info.amount
            self._balances[address].rewards += rewards

            # Mark stake as withdrawn
            stake_info.status = "withdrawn"

            transaction.status = TransactionStatus.CONFIRMED
            transaction.completed_at = time.time()
            transaction.metadata["rewards"] = float(rewards)

        except Exception as e:
            transaction.status = TransactionStatus.FAILED
            transaction.metadata["error"] = str(e)

        self._transactions[tx_id] = transaction
        return transaction

    async def claim_rewards(self, address: str) -> CurrencyTransaction:
        """
        Claim accumulated staking rewards.

        Args:
            address: Claimer address

        Returns:
            Transaction record
        """
        balance = await self.get_balance(address)
        if balance.rewards <= 0:
            raise ValueError("No rewards to claim")

        tx_id = self._generate_tx_id("reward", address)

        transaction = CurrencyTransaction(
            id=tx_id,
            type=TransactionType.REWARD,
            from_address=self._treasury_address,
            to_address=address,
            amount=balance.rewards,
            currency_type=CurrencyType.REWARD,
            status=TransactionStatus.PENDING,
        )

        try:
            # Move rewards to available
            rewards = self._balances[address].rewards
            self._balances[address].rewards = Decimal("0")
            self._balances[address].available += rewards

            transaction.status = TransactionStatus.CONFIRMED
            transaction.completed_at = time.time()

        except Exception as e:
            transaction.status = TransactionStatus.FAILED
            transaction.metadata["error"] = str(e)

        self._transactions[tx_id] = transaction
        return transaction

    async def get_stakes(self, address: str) -> list[StakeInfo]:
        """
        Get all stakes for an address.

        Args:
            address: Staker address

        Returns:
            List of stake info
        """
        return [
            stake for key, stake in self._stakes.items()
            if stake.address == address and stake.status == "active"
        ]

    async def get_transaction(self, tx_id: str) -> CurrencyTransaction | None:
        """Get transaction by ID."""
        return self._transactions.get(tx_id)

    async def get_transaction_history(
        self,
        address: str,
        limit: int = 100,
    ) -> list[CurrencyTransaction]:
        """
        Get transaction history for an address.

        Args:
            address: Address to query
            limit: Maximum results

        Returns:
            List of transactions
        """
        transactions = [
            tx for tx in self._transactions.values()
            if tx.from_address == address or tx.to_address == address
        ]
        return sorted(transactions, key=lambda x: x.created_at, reverse=True)[:limit]

    def get_supply_stats(self) -> dict[str, Any]:
        """Get currency supply statistics."""
        total_staked = sum(
            stake.amount for stake in self._stakes.values()
            if stake.status == "active"
        )
        total_rewards = sum(
            balance.rewards for balance in self._balances.values()
        )

        return {
            "name": self.config.name,
            "symbol": self.config.symbol,
            "total_minted": float(self._total_minted),
            "circulating_supply": float(self._circulating_supply),
            "total_staked": float(total_staked),
            "total_rewards_pending": float(total_rewards),
            "max_supply": float(self.config.max_supply),
            "treasury_address": self._treasury_address,
        }

    def _generate_tx_id(self, tx_type: str, *addresses: str) -> str:
        """Generate a unique transaction ID."""
        data = f"{tx_type}:{':'.join(addresses)}:{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
