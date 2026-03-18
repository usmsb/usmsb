"""
Agent Transaction System

This module provides transaction capabilities between agents:
- Agent-to-agent token transfers
- Service payment system
- Escrow and conditional transactions
- Transaction history and tracking
- Cross-chain transaction support
"""

import asyncio
import hashlib
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class TransactionType(StrEnum):
    """Types of agent transactions."""
    TRANSFER = "transfer"              # Direct transfer between agents
    SERVICE_PAYMENT = "service_payment"  # Payment for services
    ESCROW = "escrow"                  # Escrow transaction
    REWARD = "reward"                  # Reward distribution
    STAKE = "stake"                    # Staking tokens
    UNSTAKE = "unstake"                # Unstaking tokens
    DELEGATE = "delegate"              # Delegating tokens
    TIP = "tip"                        # Tip/Donation


class AgentTransactionStatus(StrEnum):
    """Status of agent transactions."""
    PENDING = "pending"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    ESCROWED = "escrowed"
    RELEASED = "released"


@dataclass
class AgentWallet:
    """Agent wallet with multi-chain support."""
    agent_id: str
    address: str
    chain: str  # "ethereum", "custom", etc.
    balance: Decimal = Decimal("0")
    staked: Decimal = Decimal("0")
    delegated: Decimal = Decimal("0")
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTransaction:
    """Transaction between agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    transaction_type: TransactionType = TransactionType.TRANSFER
    from_agent: str = ""  # Agent ID
    to_agent: str = ""    # Agent ID
    from_address: str = ""
    to_address: str = ""
    amount: Decimal = Decimal("0")
    token: str = "USMSB"  # Token symbol
    chain: str = "custom"
    status: AgentTransactionStatus = AgentTransactionStatus.PENDING
    blockchain_tx_hash: str | None = None
    service_id: str | None = None  # For service payments
    escrow_release_condition: str | None = None
    escrow_timeout: float | None = None
    created_at: float = field(default_factory=time.time)
    confirmed_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "transaction_type": self.transaction_type.value,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "amount": str(self.amount),
            "token": self.token,
            "chain": self.chain,
            "status": self.status.value,
            "blockchain_tx_hash": self.blockchain_tx_hash,
            "service_id": self.service_id,
            "created_at": self.created_at,
            "confirmed_at": self.confirmed_at,
            "metadata": self.metadata,
        }


class IAgentTransactionService(ABC):
    """Abstract interface for agent transaction services."""

    @abstractmethod
    async def create_wallet(self, agent_id: str, chain: str = "custom") -> AgentWallet:
        """Create a wallet for an agent."""
        pass

    @abstractmethod
    async def get_wallet(self, agent_id: str) -> AgentWallet | None:
        """Get agent wallet."""
        pass

    @abstractmethod
    async def get_balance(self, agent_id: str) -> Decimal:
        """Get agent balance."""
        pass

    @abstractmethod
    async def transfer(
        self,
        from_agent: str,
        to_agent: str,
        amount: Decimal,
        token: str = "USMSB",
        metadata: dict[str, Any] | None = None,
    ) -> AgentTransaction:
        """Transfer tokens between agents."""
        pass

    @abstractmethod
    async def pay_for_service(
        self,
        payer_agent: str,
        provider_agent: str,
        amount: Decimal,
        service_id: str,
        escrow: bool = False,
    ) -> AgentTransaction:
        """Pay for a service from another agent."""
        pass

    @abstractmethod
    async def create_escrow(
        self,
        payer_agent: str,
        provider_agent: str,
        amount: Decimal,
        release_condition: str,
        timeout: float,
    ) -> AgentTransaction:
        """Create an escrow transaction."""
        pass

    @abstractmethod
    async def release_escrow(self, transaction_id: str) -> AgentTransaction:
        """Release escrow to provider."""
        pass

    @abstractmethod
    async def refund_escrow(self, transaction_id: str) -> AgentTransaction:
        """Refund escrow to payer."""
        pass

    @abstractmethod
    async def get_transaction(self, transaction_id: str) -> AgentTransaction | None:
        """Get transaction by ID."""
        pass

    @abstractmethod
    async def get_agent_transactions(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> list[AgentTransaction]:
        """Get transaction history for an agent."""
        pass


class AgentTransactionService(IAgentTransactionService):
    """
    Implementation of agent transaction service.

    Provides transaction capabilities with blockchain integration.

    FIX: Per-wallet asyncio.Lock prevents double-spend from concurrent transfers.
    """

    def __init__(self, blockchain_adapter=None):
        """
        Initialize transaction service.

        Args:
            blockchain_adapter: Blockchain adapter for on-chain operations
        """
        self.blockchain = blockchain_adapter
        self._wallets: dict[str, AgentWallet] = {}
        self._transactions: dict[str, AgentTransaction] = {}
        self._escrows: dict[str, AgentTransaction] = {}
        self._escrow_handlers: dict[str, Callable] = {}
        # FIX: Per-wallet locks to prevent concurrent double-spend
        self._wallet_locks: dict[str, asyncio.Lock] = {}

    async def create_wallet(self, agent_id: str, chain: str = "custom") -> AgentWallet:
        """Create a wallet for an agent."""
        if agent_id in self._wallets:
            return self._wallets[agent_id]

        # Create blockchain wallet if adapter available
        if self.blockchain:
            blockchain_wallet = await self.blockchain.create_wallet()
            address = blockchain_wallet.address
        else:
            # Generate mock address
            address = "0x" + hashlib.sha256(f"{agent_id}{time.time()}".encode()).hexdigest()[:40]

        wallet = AgentWallet(
            agent_id=agent_id,
            address=address,
            chain=chain,
            balance=Decimal("100.0"),  # Initial balance for testing
        )

        self._wallets[agent_id] = wallet
        logger.info(f"Created wallet for agent {agent_id}: {address}")

        return wallet

    async def get_wallet(self, agent_id: str) -> AgentWallet | None:
        """Get agent wallet."""
        return self._wallets.get(agent_id)

    async def get_balance(self, agent_id: str) -> Decimal:
        """Get agent balance."""
        wallet = self._wallets.get(agent_id)
        return wallet.balance if wallet else Decimal("0")

    async def transfer(
        self,
        from_agent: str,
        to_agent: str,
        amount: Decimal,
        token: str = "USMSB",
        metadata: dict[str, Any] | None = None,
    ) -> AgentTransaction:
        """
        Transfer tokens between agents with double-spend protection.

        FIX: Per-wallet asyncio.Lock prevents concurrent double-spend.
        """
        wallet_lock = self._wallet_locks.setdefault(from_agent, asyncio.Lock())
        async with wallet_lock:
            return await self._do_transfer(from_agent, to_agent, amount, token, metadata)

    async def _do_transfer(
        self,
        from_agent: str,
        to_agent: str,
        amount: Decimal,
        token: str,
        metadata: dict[str, Any] | None,
    ) -> AgentTransaction:
        """Internal transfer (called within wallet lock)."""
        # Get wallets
        from_wallet = self._wallets.get(from_agent)
        to_wallet = self._wallets.get(to_agent)

        if not from_wallet:
            raise ValueError(f"Sender wallet not found: {from_agent}")
        if not to_wallet:
            raise ValueError(f"Recipient wallet not found: {to_agent}")

        # Check balance
        if from_wallet.balance < amount:
            return AgentTransaction(
                transaction_type=TransactionType.TRANSFER,
                from_agent=from_agent,
                to_agent=to_agent,
                from_address=from_wallet.address,
                to_address=to_wallet.address,
                amount=amount,
                token=token,
                status=AgentTransactionStatus.FAILED,
                metadata={"error": "Insufficient balance"},
            )

        # Create transaction
        transaction = AgentTransaction(
            transaction_type=TransactionType.TRANSFER,
            from_agent=from_agent,
            to_agent=to_agent,
            from_address=from_wallet.address,
            to_address=to_wallet.address,
            amount=amount,
            token=token,
            chain=from_wallet.chain,
            status=AgentTransactionStatus.PROCESSING,
            metadata=metadata or {},
        )

        # Execute blockchain transfer if available
        if self.blockchain:
            try:
                blockchain_tx = await self.blockchain.transfer(
                    from_address=from_wallet.address,
                    to_address=to_wallet.address,
                    value=amount,
                )
                transaction.blockchain_tx_hash = blockchain_tx.tx_hash
            except Exception as e:
                logger.error(f"Blockchain transfer failed: {e}")
                transaction.status = AgentTransactionStatus.FAILED
                transaction.metadata["error"] = str(e)
                return transaction

        # Update balances
        from_wallet.balance -= amount
        to_wallet.balance += amount

        transaction.status = AgentTransactionStatus.CONFIRMED
        transaction.confirmed_at = time.time()

        self._transactions[transaction.id] = transaction
        logger.info(f"Transfer complete: {from_agent} -> {to_agent}: {amount} {token}")

        return transaction

    async def pay_for_service(
        self,
        payer_agent: str,
        provider_agent: str,
        amount: Decimal,
        service_id: str,
        escrow: bool = False,
    ) -> AgentTransaction:
        """Pay for a service from another agent."""
        if escrow:
            return await self.create_escrow(
                payer_agent=payer_agent,
                provider_agent=provider_agent,
                amount=amount,
                release_condition=f"service_completion:{service_id}",
                timeout=3600.0,  # 1 hour default
            )

        # Direct payment
        transaction = await self.transfer(
            from_agent=payer_agent,
            to_agent=provider_agent,
            amount=amount,
            metadata={"service_id": service_id, "type": "service_payment"},
        )
        transaction.transaction_type = TransactionType.SERVICE_PAYMENT
        transaction.service_id = service_id

        return transaction

    async def create_escrow(
        self,
        payer_agent: str,
        provider_agent: str,
        amount: Decimal,
        release_condition: str,
        timeout: float,
    ) -> AgentTransaction:
        """Create an escrow transaction."""
        payer_wallet = self._wallets.get(payer_agent)
        provider_wallet = self._wallets.get(provider_agent)

        if not payer_wallet:
            raise ValueError(f"Payer wallet not found: {payer_agent}")
        if not provider_wallet:
            raise ValueError(f"Provider wallet not found: {provider_agent}")

        # Check balance
        if payer_wallet.balance < amount:
            return AgentTransaction(
                transaction_type=TransactionType.ESCROW,
                from_agent=payer_agent,
                to_agent=provider_agent,
                amount=amount,
                status=AgentTransactionStatus.FAILED,
                metadata={"error": "Insufficient balance"},
            )

        # Create escrow transaction
        transaction = AgentTransaction(
            transaction_type=TransactionType.ESCROW,
            from_agent=payer_agent,
            to_agent=provider_agent,
            from_address=payer_wallet.address,
            to_address=provider_wallet.address,
            amount=amount,
            escrow_release_condition=release_condition,
            escrow_timeout=time.time() + timeout,
            status=AgentTransactionStatus.ESCROWED,
        )

        # Lock funds in escrow
        payer_wallet.balance -= amount
        self._escrows[transaction.id] = transaction
        self._transactions[transaction.id] = transaction

        # Set up timeout handler
        asyncio.create_task(self._handle_escrow_timeout(transaction.id))

        logger.info(f"Created escrow: {payer_agent} -> {provider_agent}: {amount}")

        return transaction

    async def release_escrow(self, transaction_id: str) -> AgentTransaction:
        """Release escrow to provider."""
        transaction = self._escrows.get(transaction_id)
        if not transaction:
            raise ValueError(f"Escrow not found: {transaction_id}")

        if transaction.status != AgentTransactionStatus.ESCROWED:
            raise ValueError(f"Escrow not in escrowed state: {transaction.status}")

        provider_wallet = self._wallets.get(transaction.to_agent)
        if not provider_wallet:
            raise ValueError(f"Provider wallet not found: {transaction.to_agent}")

        # Release funds to provider
        provider_wallet.balance += transaction.amount
        transaction.status = AgentTransactionStatus.RELEASED
        transaction.confirmed_at = time.time()

        del self._escrows[transaction_id]
        self._transactions[transaction_id] = transaction

        logger.info(f"Released escrow {transaction_id} to {transaction.to_agent}")

        return transaction

    async def refund_escrow(self, transaction_id: str) -> AgentTransaction:
        """Refund escrow to payer."""
        transaction = self._escrows.get(transaction_id)
        if not transaction:
            raise ValueError(f"Escrow not found: {transaction_id}")

        if transaction.status != AgentTransactionStatus.ESCROWED:
            raise ValueError(f"Escrow not in escrowed state: {transaction.status}")

        payer_wallet = self._wallets.get(transaction.from_agent)
        if not payer_wallet:
            raise ValueError(f"Payer wallet not found: {transaction.from_agent}")

        # Refund funds to payer
        payer_wallet.balance += transaction.amount
        transaction.status = AgentTransactionStatus.REFUNDED
        transaction.confirmed_at = time.time()

        del self._escrows[transaction_id]
        self._transactions[transaction_id] = transaction

        logger.info(f"Refunded escrow {transaction_id} to {transaction.from_agent}")

        return transaction

    async def _handle_escrow_timeout(self, transaction_id: str) -> None:
        """Handle escrow timeout."""
        while transaction_id in self._escrows:
            transaction = self._escrows[transaction_id]
            if time.time() > transaction.escrow_timeout:
                logger.warning(f"Escrow {transaction_id} timed out, refunding...")
                try:
                    await self.refund_escrow(transaction_id)
                except Exception as e:
                    logger.error(f"Failed to refund timed out escrow: {e}")
                break
            await asyncio.sleep(60)  # Check every minute

    async def get_transaction(self, transaction_id: str) -> AgentTransaction | None:
        """Get transaction by ID."""
        return self._transactions.get(transaction_id)

    async def get_agent_transactions(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> list[AgentTransaction]:
        """Get transaction history for an agent."""
        transactions = [
            tx for tx in self._transactions.values()
            if tx.from_agent == agent_id or tx.to_agent == agent_id
        ]
        transactions.sort(key=lambda x: x.created_at, reverse=True)
        return transactions[:limit]

    async def stake_tokens(
        self,
        agent_id: str,
        amount: Decimal,
    ) -> AgentTransaction:
        """Stake tokens for validation/consensus participation."""
        wallet = self._wallets.get(agent_id)
        if not wallet:
            raise ValueError(f"Wallet not found: {agent_id}")

        if wallet.balance < amount:
            return AgentTransaction(
                transaction_type=TransactionType.STAKE,
                from_agent=agent_id,
                to_agent=agent_id,
                amount=amount,
                status=AgentTransactionStatus.FAILED,
                metadata={"error": "Insufficient balance"},
            )

        wallet.balance -= amount
        wallet.staked += amount

        transaction = AgentTransaction(
            transaction_type=TransactionType.STAKE,
            from_agent=agent_id,
            to_agent=agent_id,
            from_address=wallet.address,
            to_address=wallet.address,
            amount=amount,
            status=AgentTransactionStatus.CONFIRMED,
            confirmed_at=time.time(),
        )

        self._transactions[transaction.id] = transaction
        logger.info(f"Agent {agent_id} staked {amount} tokens")

        return transaction

    async def unstake_tokens(
        self,
        agent_id: str,
        amount: Decimal,
    ) -> AgentTransaction:
        """Unstake tokens."""
        wallet = self._wallets.get(agent_id)
        if not wallet:
            raise ValueError(f"Wallet not found: {agent_id}")

        if wallet.staked < amount:
            return AgentTransaction(
                transaction_type=TransactionType.UNSTAKE,
                from_agent=agent_id,
                to_agent=agent_id,
                amount=amount,
                status=AgentTransactionStatus.FAILED,
                metadata={"error": "Insufficient staked balance"},
            )

        wallet.staked -= amount
        wallet.balance += amount

        transaction = AgentTransaction(
            transaction_type=TransactionType.UNSTAKE,
            from_agent=agent_id,
            to_agent=agent_id,
            from_address=wallet.address,
            to_address=wallet.address,
            amount=amount,
            status=AgentTransactionStatus.CONFIRMED,
            confirmed_at=time.time(),
        )

        self._transactions[transaction.id] = transaction
        logger.info(f"Agent {agent_id} unstaked {amount} tokens")

        return transaction

    async def tip_agent(
        self,
        from_agent: str,
        to_agent: str,
        amount: Decimal,
        message: str | None = None,
    ) -> AgentTransaction:
        """Send a tip/donation to another agent."""
        transaction = await self.transfer(
            from_agent=from_agent,
            to_agent=to_agent,
            amount=amount,
            metadata={"type": "tip", "message": message},
        )
        transaction.transaction_type = TransactionType.TIP
        return transaction
