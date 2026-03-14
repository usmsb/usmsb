"""
Blockchain Service for AI Civilization Platform

Provides blockchain integration for:
- Token transfers
- Escrow contracts
- Staking
- Reputation (on-chain)

In development mode, simulates blockchain operations.
In production, connects to actual blockchain (Ethereum/Polygon).
"""
import asyncio
import logging
import secrets
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class ChainStatus(StrEnum):
    """Blockchain connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class TransactionStatus(StrEnum):
    """On-chain transaction status."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


@dataclass
class Block:
    """A block in the simulated chain."""
    number: int
    hash: str
    parent_hash: str
    timestamp: float
    transactions: list[dict[str, Any]]
    miner: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "hash": self.hash,
            "parentHash": self.parent_hash,
            "timestamp": self.timestamp,
            "transactionCount": len(self.transactions),
            "miner": self.miner,
        }


@dataclass
class OnChainTransaction:
    """A transaction on the simulated chain."""
    hash: str
    from_address: str
    to_address: str
    value: float
    data: dict[str, Any]
    status: TransactionStatus
    block_number: int | None
    timestamp: float
    gas_used: int = 21000
    gas_price: float = 0.000001  # 1 Gwei in ETH

    def to_dict(self) -> dict[str, Any]:
        return {
            "hash": self.hash,
            "from": self.from_address,
            "to": self.to_address,
            "value": self.value,
            "data": self.data,
            "status": self.status.value,
            "blockNumber": self.block_number,
            "timestamp": self.timestamp,
            "gasUsed": self.gas_used,
            "gasPrice": self.gas_price,
        }


@dataclass
class EscrowContract:
    """Simulated escrow contract."""
    contract_address: str
    buyer: str
    seller: str
    amount: float
    status: str  # "active", "released", "refunded"
    created_at: float
    release_tx: str | None = None
    refund_tx: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "contractAddress": self.contract_address,
            "buyer": self.buyer,
            "seller": self.seller,
            "amount": self.amount,
            "status": self.status,
            "createdAt": self.created_at,
            "releaseTx": self.release_tx,
            "refundTx": self.refund_tx,
        }


class BlockchainService:
    """
    Blockchain Service for token operations.

    In development mode:
    - Simulates blockchain locally
    - Instant transaction confirmation
    - No real gas fees

    In production mode:
    - Connects to Ethereum/Polygon
    - Uses real smart contracts
    - Real gas fees and confirmations
    """

    # Token configuration
    TOKEN_NAME = "VIBE"
    TOKEN_SYMBOL = "VIBE"
    TOKEN_DECIMALS = 18
    INITIAL_SUPPLY = 1_000_000_000  # 1 billion tokens

    # Blockchain configuration
    BLOCK_TIME = 2.0  # seconds (simulated)
    CONFIRMATION_BLOCKS = 3

    def __init__(
        self,
        rpc_url: str | None = None,
        chain_id: int = 1,
        simulation_mode: bool = True,
    ):
        """
        Initialize blockchain service.

        Args:
            rpc_url: RPC endpoint URL
            chain_id: Chain ID (1=mainnet, 137=polygon, etc.)
            simulation_mode: If True, simulate blockchain locally
        """
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.simulation_mode = simulation_mode
        self.status = ChainStatus.DISCONNECTED

        # Simulated state
        self._balances: dict[str, float] = {}
        self._escrows: dict[str, EscrowContract] = {}
        self._stakes: dict[str, float] = {}
        self._reputation: dict[str, float] = {}
        self._transactions: dict[str, OnChainTransaction] = {}
        self._blocks: list[Block] = []
        self._pending_txs: list[OnChainTransaction] = []

        # Block production
        self._current_block = 0
        self._block_task: asyncio.Task | None = None

    async def connect(self) -> bool:
        """Connect to blockchain."""
        self.status = ChainStatus.CONNECTING

        if self.simulation_mode:
            # Initialize simulated chain
            await self._init_simulation()
            self.status = ChainStatus.CONNECTED
            logger.info("Connected to simulated blockchain")
            return True
        else:
            # Connect to real blockchain
            try:
                # TODO: Implement real blockchain connection
                # from web3 import Web3
                # self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
                # if self.w3.is_connected():
                #     self.status = ChainStatus.CONNECTED
                #     return True
                raise NotImplementedError("Real blockchain connection not implemented")
            except Exception as e:
                logger.error(f"Failed to connect to blockchain: {e}")
                self.status = ChainStatus.ERROR
                return False

    async def disconnect(self) -> None:
        """Disconnect from blockchain."""
        if self._block_task:
            self._block_task.cancel()
            try:
                await self._block_task
            except asyncio.CancelledError:
                pass
        self.status = ChainStatus.DISCONNECTED
        logger.info("Disconnected from blockchain")

    async def _init_simulation(self) -> None:
        """Initialize simulated blockchain state."""
        # Create genesis block
        genesis = Block(
            number=0,
            hash="0x" + "0" * 64,
            parent_hash="0x" + "0" * 64,
            timestamp=time.time(),
            transactions=[],
            miner="0x0000000000000000000000000000000000000000",
        )
        self._blocks.append(genesis)
        self._current_block = 1

        # Start block production
        self._block_task = asyncio.create_task(self._produce_blocks())

    async def _produce_blocks(self) -> None:
        """Produce blocks in simulation mode."""
        while True:
            try:
                await asyncio.sleep(self.BLOCK_TIME)

                # Create new block with pending transactions
                parent = self._blocks[-1]
                txs = [tx.to_dict() for tx in self._pending_txs]

                block = Block(
                    number=self._current_block,
                    hash="0x" + secrets.token_hex(32),
                    parent_hash=parent.hash,
                    timestamp=time.time(),
                    transactions=txs,
                    miner="0x" + secrets.token_hex(20),
                )

                # Confirm pending transactions
                for tx in self._pending_txs:
                    tx.status = TransactionStatus.CONFIRMED
                    tx.block_number = block.number
                    self._execute_transaction(tx)

                self._blocks.append(block)
                self._pending_txs = []
                self._current_block += 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error producing block: {e}")

    def _execute_transaction(self, tx: OnChainTransaction) -> None:
        """Execute a transaction (update balances)."""
        if tx.to_address.lower() == "escrow":
            # Escrow creation
            pass
        else:
            # Token transfer
            if tx.from_address in self._balances:
                self._balances[tx.from_address] -= tx.value
            if tx.to_address not in self._balances:
                self._balances[tx.to_address] = 0
            self._balances[tx.to_address] += tx.value

    # ==================== Balance Operations ====================

    async def get_balance(self, address: str) -> float:
        """Get token balance for an address."""
        return self._balances.get(address.lower(), 0.0)

    async def mint_tokens(self, address: str, amount: float) -> str:
        """Mint tokens to an address (admin only)."""
        addr = address.lower()
        if addr not in self._balances:
            self._balances[addr] = 0
        self._balances[addr] += amount

        # Create transaction record
        tx = OnChainTransaction(
            hash="0x" + secrets.token_hex(32),
            from_address="0x0000000000000000000000000000000000000000",
            to_address=addr,
            value=amount,
            data={"type": "mint"},
            status=TransactionStatus.CONFIRMED,
            block_number=self._current_block,
            timestamp=time.time(),
        )
        self._transactions[tx.hash] = tx

        logger.info(f"Minted {amount} VIBE to {address}")
        return tx.hash

    async def transfer(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        private_key: str | None = None,
    ) -> str:
        """
        Transfer tokens between addresses.

        Returns transaction hash.
        """
        from_addr = from_address.lower()
        to_addr = to_address.lower()

        # Check balance
        balance = await self.get_balance(from_addr)
        if balance < amount:
            raise ValueError(f"Insufficient balance: {balance} < {amount}")

        # Create pending transaction
        tx = OnChainTransaction(
            hash="0x" + secrets.token_hex(32),
            from_address=from_addr,
            to_address=to_addr,
            value=amount,
            data={"type": "transfer"},
            status=TransactionStatus.PENDING,
            block_number=None,
            timestamp=time.time(),
        )

        self._transactions[tx.hash] = tx
        self._pending_txs.append(tx)

        logger.info(f"Transfer {amount} VIBE from {from_address} to {to_address}")
        return tx.hash

    # ==================== Escrow Operations ====================

    async def create_escrow(
        self,
        buyer: str,
        seller: str,
        amount: float,
    ) -> EscrowContract:
        """Create an escrow contract."""
        buyer_addr = buyer.lower()
        seller_addr = seller.lower()

        # Check buyer balance
        balance = await self.get_balance(buyer_addr)
        if balance < amount:
            raise ValueError(f"Insufficient balance for escrow: {balance} < {amount}")

        # Create escrow
        contract_address = "0xescrow" + secrets.token_hex(18)
        escrow = EscrowContract(
            contract_address=contract_address,
            buyer=buyer_addr,
            seller=seller_addr,
            amount=amount,
            status="active",
            created_at=time.time(),
        )

        # Lock funds
        self._balances[buyer_addr] -= amount
        self._escrows[contract_address] = escrow

        # Create transaction
        tx = OnChainTransaction(
            hash="0x" + secrets.token_hex(32),
            from_address=buyer_addr,
            to_address="escrow",
            value=amount,
            data={"type": "escrow_create", "contract": contract_address},
            status=TransactionStatus.CONFIRMED,
            block_number=self._current_block,
            timestamp=time.time(),
        )
        self._transactions[tx.hash] = tx

        logger.info(f"Created escrow {contract_address} for {amount} VIBE")
        return escrow

    async def release_escrow(
        self,
        contract_address: str,
        caller: str,
    ) -> str:
        """Release escrow funds to seller."""
        escrow = self._escrows.get(contract_address)
        if not escrow:
            raise ValueError(f"Escrow not found: {contract_address}")

        if escrow.status != "active":
            raise ValueError(f"Escrow not active: {escrow.status}")

        # Only buyer can release (or dispute resolution)
        if caller.lower() != escrow.buyer:
            raise ValueError("Only buyer can release escrow")

        # Release to seller
        if escrow.seller not in self._balances:
            self._balances[escrow.seller] = 0
        self._balances[escrow.seller] += escrow.amount
        escrow.status = "released"

        # Create transaction
        tx = OnChainTransaction(
            hash="0x" + secrets.token_hex(32),
            from_address=contract_address,
            to_address=escrow.seller,
            value=escrow.amount,
            data={"type": "escrow_release", "contract": contract_address},
            status=TransactionStatus.CONFIRMED,
            block_number=self._current_block,
            timestamp=time.time(),
        )
        self._transactions[tx.hash] = tx
        escrow.release_tx = tx.hash

        logger.info(f"Released escrow {contract_address} to seller")
        return tx.hash

    async def refund_escrow(
        self,
        contract_address: str,
        caller: str,
    ) -> str:
        """Refund escrow funds to buyer."""
        escrow = self._escrows.get(contract_address)
        if not escrow:
            raise ValueError(f"Escrow not found: {contract_address}")

        if escrow.status != "active":
            raise ValueError(f"Escrow not active: {escrow.status}")

        # Refund to buyer
        if escrow.buyer not in self._balances:
            self._balances[escrow.buyer] = 0
        self._balances[escrow.buyer] += escrow.amount
        escrow.status = "refunded"

        # Create transaction
        tx = OnChainTransaction(
            hash="0x" + secrets.token_hex(32),
            from_address=contract_address,
            to_address=escrow.buyer,
            value=escrow.amount,
            data={"type": "escrow_refund", "contract": contract_address},
            status=TransactionStatus.CONFIRMED,
            block_number=self._current_block,
            timestamp=time.time(),
        )
        self._transactions[tx.hash] = tx
        escrow.refund_tx = tx.hash

        logger.info(f"Refunded escrow {contract_address} to buyer")
        return tx.hash

    def get_escrow(self, contract_address: str) -> EscrowContract | None:
        """Get escrow contract details."""
        return self._escrows.get(contract_address)

    # ==================== Staking Operations ====================

    async def stake(self, address: str, amount: float) -> str:
        """Stake tokens."""
        addr = address.lower()

        # Check balance
        balance = await self.get_balance(addr)
        if balance < amount:
            raise ValueError(f"Insufficient balance for staking: {balance} < {amount}")

        # Lock tokens
        self._balances[addr] -= amount
        if addr not in self._stakes:
            self._stakes[addr] = 0
        self._stakes[addr] += amount

        # Update reputation based on stake
        self._reputation[addr] = min(0.5 + (self._stakes[addr] / 1000), 1.0)

        # Create transaction
        tx = OnChainTransaction(
            hash="0x" + secrets.token_hex(32),
            from_address=addr,
            to_address="stake",
            value=amount,
            data={"type": "stake"},
            status=TransactionStatus.CONFIRMED,
            block_number=self._current_block,
            timestamp=time.time(),
        )
        self._transactions[tx.hash] = tx

        logger.info(f"Staked {amount} VIBE from {address}")
        return tx.hash

    async def unstake(self, address: str, amount: float) -> str:
        """Unstake tokens."""
        addr = address.lower()

        # Check staked amount
        staked = self._stakes.get(addr, 0)
        if staked < amount:
            raise ValueError(f"Insufficient staked amount: {staked} < {amount}")

        # Unlock tokens
        self._stakes[addr] -= amount
        if addr not in self._balances:
            self._balances[addr] = 0
        self._balances[addr] += amount

        # Update reputation
        self._reputation[addr] = min(0.5 + (self._stakes[addr] / 1000), 1.0)

        # Create transaction
        tx = OnChainTransaction(
            hash="0x" + secrets.token_hex(32),
            from_address="stake",
            to_address=addr,
            value=amount,
            data={"type": "unstake"},
            status=TransactionStatus.CONFIRMED,
            block_number=self._current_block,
            timestamp=time.time(),
        )
        self._transactions[tx.hash] = tx

        logger.info(f"Unstaked {amount} VIBE for {address}")
        return tx.hash

    async def get_stake(self, address: str) -> float:
        """Get staked amount for an address."""
        return self._stakes.get(address.lower(), 0.0)

    # ==================== Reputation Operations ====================

    async def get_reputation(self, address: str) -> float:
        """Get on-chain reputation for an address."""
        return self._reputation.get(address.lower(), 0.5)

    async def update_reputation(
        self,
        address: str,
        delta: float,
        reason: str = "",
    ) -> str:
        """Update reputation (admin or contract only)."""
        addr = address.lower()

        if addr not in self._reputation:
            self._reputation[addr] = 0.5

        self._reputation[addr] = max(0.0, min(1.0, self._reputation[addr] + delta))

        # Create transaction
        tx = OnChainTransaction(
            hash="0x" + secrets.token_hex(32),
            from_address="system",
            to_address=addr,
            value=0,
            data={"type": "reputation_update", "delta": delta, "reason": reason},
            status=TransactionStatus.CONFIRMED,
            block_number=self._current_block,
            timestamp=time.time(),
        )
        self._transactions[tx.hash] = tx

        logger.info(f"Updated reputation for {address}: {delta:+.2f}")
        return tx.hash

    # ==================== Transaction Operations ====================

    async def get_transaction(self, tx_hash: str) -> OnChainTransaction | None:
        """Get transaction by hash."""
        return self._transactions.get(tx_hash)

    async def wait_for_confirmation(
        self,
        tx_hash: str,
        timeout: float = 30.0,
    ) -> OnChainTransaction:
        """Wait for transaction confirmation."""
        start = time.time()
        while time.time() - start < timeout:
            tx = self._transactions.get(tx_hash)
            if tx and tx.status == TransactionStatus.CONFIRMED:
                return tx
            await asyncio.sleep(0.5)

        raise TimeoutError(f"Transaction {tx_hash} not confirmed within {timeout}s")

    # ==================== Block Operations ====================

    async def get_block(self, block_number: int) -> Block | None:
        """Get block by number."""
        if 0 <= block_number < len(self._blocks):
            return self._blocks[block_number]
        return None

    async def get_latest_block(self) -> Block:
        """Get latest block."""
        return self._blocks[-1] if self._blocks else None

    # ==================== Utility Methods ====================

    def get_status(self) -> dict[str, Any]:
        """Get blockchain status."""
        return {
            "status": self.status.value,
            "chainId": self.chain_id,
            "simulationMode": self.simulation_mode,
            "currentBlock": self._current_block,
            "totalTransactions": len(self._transactions),
            "totalEscrows": len(self._escrows),
            "totalStaked": sum(self._stakes.values()),
        }

    def get_address_info(self, address: str) -> dict[str, Any]:
        """Get comprehensive info for an address."""
        addr = address.lower()
        return {
            "address": addr,
            "balance": self._balances.get(addr, 0.0),
            "staked": self._stakes.get(addr, 0.0),
            "reputation": self._reputation.get(addr, 0.5),
        }


# Global blockchain service instance
_blockchain_service: BlockchainService | None = None


async def get_blockchain_service() -> BlockchainService:
    """Get or create blockchain service instance."""
    global _blockchain_service
    if _blockchain_service is None:
        _blockchain_service = BlockchainService(simulation_mode=True)
        await _blockchain_service.connect()
    return _blockchain_service
