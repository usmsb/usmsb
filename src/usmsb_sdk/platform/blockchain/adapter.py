"""
Blockchain Adapter

Abstract interface and implementations for blockchain integration.
Supports Ethereum, Hyperledger, and other blockchain networks.
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class BlockchainNetwork(StrEnum):
    """Supported blockchain networks."""
    ETHEREUM_MAINNET = "ethereum_mainnet"
    ETHEREUM_GOERLI = "ethereum_goerli"
    ETHEREUM_SEPOLIA = "ethereum_sepolia"
    POLYGON = "polygon"
    BSC = "bsc"  # Binance Smart Chain
    HYPERLEDGER = "hyperledger"
    CUSTOM = "custom"


class TransactionStatus(StrEnum):
    """Transaction status."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WalletInfo:
    """Wallet information."""
    address: str
    balance: Decimal
    network: BlockchainNetwork
    created_at: float = field(default_factory=lambda: time.time())
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Transaction:
    """Blockchain transaction."""
    id: str
    from_address: str
    to_address: str
    value: Decimal
    data: str | None = None
    gas_price: Decimal | None = None
    gas_limit: int | None = None
    nonce: int | None = None
    status: TransactionStatus = TransactionStatus.PENDING
    tx_hash: str | None = None
    block_number: int | None = None
    created_at: float = field(default_factory=lambda: time.time())
    confirmed_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SmartContract:
    """Smart contract definition."""
    address: str
    name: str
    abi: list[dict[str, Any]]
    bytecode: str | None = None
    network: BlockchainNetwork = BlockchainNetwork.ETHEREUM_MAINNET
    deployed_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class IBlockchainAdapter(ABC):
    """
    Abstract interface for blockchain operations.

    Provides wallet management, transaction handling,
    and smart contract interaction capabilities.
    """

    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> bool:
        """
        Initialize blockchain connection.

        Args:
            config: Network configuration

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown blockchain connection."""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if connected to blockchain network."""
        pass

    @abstractmethod
    async def create_wallet(self, password: str | None = None) -> WalletInfo:
        """
        Create a new wallet.

        Args:
            password: Optional password for wallet encryption

        Returns:
            Created wallet information
        """
        pass

    @abstractmethod
    async def get_wallet(self, address: str) -> WalletInfo | None:
        """
        Get wallet by address.

        Args:
            address: Wallet address

        Returns:
            Wallet info or None if not found
        """
        pass

    @abstractmethod
    async def get_balance(self, address: str) -> Decimal:
        """
        Get wallet balance.

        Args:
            address: Wallet address

        Returns:
            Balance in native token
        """
        pass

    @abstractmethod
    async def transfer(
        self,
        from_address: str,
        to_address: str,
        value: Decimal,
        private_key: str | None = None,
        data: str | None = None,
    ) -> Transaction:
        """
        Transfer tokens between addresses.

        Args:
            from_address: Sender address
            to_address: Recipient address
            value: Amount to transfer
            private_key: Private key for signing (if not stored)
            data: Optional transaction data

        Returns:
            Transaction object
        """
        pass

    @abstractmethod
    async def get_transaction(self, tx_hash: str) -> Transaction | None:
        """
        Get transaction by hash.

        Args:
            tx_hash: Transaction hash

        Returns:
            Transaction or None
        """
        pass

    @abstractmethod
    async def wait_for_confirmation(
        self,
        tx_hash: str,
        timeout: float = 60.0,
        confirmations: int = 1,
    ) -> Transaction:
        """
        Wait for transaction confirmation.

        Args:
            tx_hash: Transaction hash
            timeout: Maximum wait time in seconds
            confirmations: Number of confirmations required

        Returns:
            Confirmed transaction
        """
        pass

    @abstractmethod
    async def deploy_contract(
        self,
        bytecode: str,
        abi: list[dict[str, Any]],
        constructor_args: list[Any] | None = None,
        from_address: str | None = None,
    ) -> SmartContract:
        """
        Deploy a smart contract.

        Args:
            bytecode: Contract bytecode
            abi: Contract ABI
            constructor_args: Constructor arguments
            from_address: Deployer address

        Returns:
            Deployed contract
        """
        pass

    @abstractmethod
    async def call_contract(
        self,
        contract_address: str,
        method: str,
        args: list[Any] | None = None,
        from_address: str | None = None,
    ) -> Any:
        """
        Call a contract method (read-only).

        Args:
            contract_address: Contract address
            method: Method name
            args: Method arguments
            from_address: Caller address

        Returns:
            Method result
        """
        pass

    @abstractmethod
    async def execute_contract(
        self,
        contract_address: str,
        method: str,
        args: list[Any] | None = None,
        from_address: str = None,
        private_key: str | None = None,
        value: Decimal = Decimal("0"),
    ) -> Transaction:
        """
        Execute a contract method (state-changing).

        Args:
            contract_address: Contract address
            method: Method name
            args: Method arguments
            from_address: Sender address
            private_key: Private key for signing
            value: ETH/value to send

        Returns:
            Transaction object
        """
        pass

    @abstractmethod
    async def get_block_number(self) -> int:
        """Get current block number."""
        pass

    @abstractmethod
    async def subscribe_to_events(
        self,
        contract_address: str,
        event_name: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> str:
        """
        Subscribe to contract events.

        Args:
            contract_address: Contract address
            event_name: Event name
            callback: Callback function

        Returns:
            Subscription ID
        """
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events.

        Args:
            subscription_id: Subscription ID

        Returns:
            True if unsubscribed
        """
        pass


class EthereumAdapter(IBlockchainAdapter):
    """
    Ethereum blockchain adapter.

    Implements blockchain operations for Ethereum and EVM-compatible chains.
    Uses web3.py for Ethereum interaction.
    """

    def __init__(self, network: BlockchainNetwork = BlockchainNetwork.ETHEREUM_SEPOLIA):
        """
        Initialize Ethereum adapter.

        Args:
            network: Target network
        """
        self.network = network
        self._web3 = None
        self._wallets: dict[str, dict[str, Any]] = {}
        self._subscriptions: dict[str, Any] = {}
        self._contracts: dict[str, SmartContract] = {}

    async def initialize(self, config: dict[str, Any]) -> bool:
        """Initialize Ethereum connection."""
        try:
            # Try to import web3
            try:
                from eth_account import Account
                from web3 import AsyncHTTPProvider, Web3
                from web3.eth import AsyncEth

                # Enable Mnemonic features
                Account.enable_unaudited_hdwallet_features()
                self._Account = Account
                self._Web3 = Web3
            except ImportError:
                logger.warning("web3.py not installed. Using mock implementation - NOT SECURE FOR PRODUCTION. Set WEB3_MODE=mock environment variable to disable.")
                self._web3 = None
                # In production, this should fail or require explicit mock mode
                import os
                if os.environ.get("WEB3_MODE", "required") == "required":
                    raise RuntimeError("web3.py is required but not installed. Please install with: pip install web3 eth-account")
                return True

            # Connect to provider
            rpc_url = config.get("rpc_url")
            if rpc_url:
                self._web3 = Web3(AsyncHTTPProvider(rpc_url))
                is_connected = await self._web3.is_connected()
                if not is_connected:
                    logger.error(f"Failed to connect to Ethereum network: {rpc_url}")
                    return False

            logger.info(f"Ethereum adapter initialized for {self.network.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Ethereum adapter: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown Ethereum connection."""
        self._web3 = None
        self._wallets.clear()
        self._subscriptions.clear()
        logger.info("Ethereum adapter shutdown complete")

    async def is_connected(self) -> bool:
        """Check connection status."""
        if self._web3 is None:
            return True  # Mock mode
        return await self._web3.is_connected()

    async def create_wallet(self, password: str | None = None) -> WalletInfo:
        """Create a new Ethereum wallet."""
        if self._web3 is None:
            # Mock wallet creation
            import secrets
            mock_address = "0x" + secrets.token_hex(20)
            return WalletInfo(
                address=mock_address,
                balance=Decimal("0"),
                network=self.network,
            )

        account = self._Account.create()
        address = account.address

        # Store wallet (in production, use secure key management)
        self._wallets[address] = {
            "address": address,
            "private_key": account.key.hex(),
            "created_at": time.time(),
        }

        return WalletInfo(
            address=address,
            balance=Decimal("0"),
            network=self.network,
        )

    async def get_wallet(self, address: str) -> WalletInfo | None:
        """Get wallet by address."""
        if address not in self._wallets:
            return None

        balance = await self.get_balance(address)
        return WalletInfo(
            address=address,
            balance=balance,
            network=self.network,
        )

    async def get_balance(self, address: str) -> Decimal:
        """Get wallet balance in ETH."""
        if self._web3 is None:
            return Decimal("0")

        balance_wei = await self._web3.eth.get_balance(address)
        balance_eth = self._Web3.from_wei(balance_wei, 'ether')
        return Decimal(str(balance_eth))

    async def transfer(
        self,
        from_address: str,
        to_address: str,
        value: Decimal,
        private_key: str | None = None,
        data: str | None = None,
    ) -> Transaction:
        """Transfer ETH between addresses."""
        tx_id = hashlib.sha256(f"{from_address}{to_address}{value}{time.time()}".encode()).hexdigest()[:16]

        transaction = Transaction(
            id=tx_id,
            from_address=from_address,
            to_address=to_address,
            value=value,
            data=data,
            status=TransactionStatus.PENDING,
        )

        if self._web3 is None:
            # Mock transaction
            transaction.tx_hash = "0x" + hashlib.sha256(tx_id.encode()).hexdigest()
            transaction.status = TransactionStatus.CONFIRMED
            return transaction

        # Real implementation would sign and send transaction
        # This is a simplified version
        try:
            # Get private key
            if private_key is None:
                wallet_data = self._wallets.get(from_address)
                if wallet_data:
                    private_key = wallet_data.get("private_key")

            if private_key is None:
                raise ValueError("No private key available for signing")

            # Build transaction
            nonce = await self._web3.eth.get_transaction_count(from_address)
            gas_price = await self._web3.eth.gas_price

            tx_dict = {
                'nonce': nonce,
                'to': to_address,
                'value': self._Web3.to_wei(float(value), 'ether'),
                'gas': 21000,
                'gasPrice': gas_price,
            }

            if data:
                tx_dict['data'] = data

            # Sign and send
            signed_tx = self._web3.eth.account.sign_transaction(tx_dict, private_key)
            tx_hash = await self._web3.eth.send_raw_transaction(signed_tx.rawTransaction)

            transaction.tx_hash = tx_hash.hex()
            transaction.status = TransactionStatus.SUBMITTED
            transaction.nonce = nonce

        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            transaction.status = TransactionStatus.FAILED
            transaction.metadata["error"] = str(e)

        return transaction

    async def get_transaction(self, tx_hash: str) -> Transaction | None:
        """Get transaction by hash."""
        if self._web3 is None:
            return None

        try:
            receipt = await self._web3.eth.get_transaction_receipt(tx_hash)
            tx = await self._web3.eth.get_transaction(tx_hash)

            status = TransactionStatus.CONFIRMED if receipt.status == 1 else TransactionStatus.FAILED

            return Transaction(
                id=tx_hash[:16],
                from_address=tx['from'],
                to_address=tx['to'],
                value=Decimal(str(self._Web3.from_wei(tx['value'], 'ether'))),
                tx_hash=tx_hash,
                block_number=receipt.blockNumber,
                status=status,
                confirmed_at=time.time(),
            )
        except Exception as e:
            logger.error(f"Failed to get transaction: {e}")
            return None

    async def wait_for_confirmation(
        self,
        tx_hash: str,
        timeout: float = 60.0,
        confirmations: int = 1,
    ) -> Transaction:
        """Wait for transaction confirmation."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            tx = await self.get_transaction(tx_hash)
            if tx and tx.status in (TransactionStatus.CONFIRMED, TransactionStatus.FAILED):
                return tx
            await asyncio.sleep(1)

        raise TimeoutError(f"Transaction {tx_hash} not confirmed within {timeout} seconds")

    async def deploy_contract(
        self,
        bytecode: str,
        abi: list[dict[str, Any]],
        constructor_args: list[Any] | None = None,
        from_address: str | None = None,
    ) -> SmartContract:
        """Deploy a smart contract."""
        contract_id = hashlib.sha256(f"{bytecode}{time.time()}".encode()).hexdigest()[:16]

        # Mock deployment
        contract_address = "0x" + hashlib.sha256(contract_id.encode()).hexdigest()[:40]

        contract = SmartContract(
            address=contract_address,
            name=f"Contract_{contract_id[:8]}",
            abi=abi,
            bytecode=bytecode,
            network=self.network,
            deployed_at=time.time(),
        )

        self._contracts[contract_address] = contract
        return contract

    async def call_contract(
        self,
        contract_address: str,
        method: str,
        args: list[Any] | None = None,
        from_address: str | None = None,
    ) -> Any:
        """Call a contract method (read-only)."""
        # Mock implementation
        return {"result": "mock_value", "method": method}

    async def execute_contract(
        self,
        contract_address: str,
        method: str,
        args: list[Any] | None = None,
        from_address: str = None,
        private_key: str | None = None,
        value: Decimal = Decimal("0"),
    ) -> Transaction:
        """Execute a contract method (state-changing)."""
        tx_id = hashlib.sha256(f"{contract_address}{method}{time.time()}".encode()).hexdigest()[:16]

        return Transaction(
            id=tx_id,
            from_address=from_address or "0x0",
            to_address=contract_address,
            value=value,
            data=json.dumps({"method": method, "args": args}),
            tx_hash="0x" + hashlib.sha256(tx_id.encode()).hexdigest(),
            status=TransactionStatus.SUBMITTED,
        )

    async def get_block_number(self) -> int:
        """Get current block number."""
        if self._web3 is None:
            return int(time.time())  # Mock

        return await self._web3.eth.block_number

    async def subscribe_to_events(
        self,
        contract_address: str,
        event_name: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> str:
        """Subscribe to contract events."""
        import uuid
        subscription_id = str(uuid.uuid4())

        self._subscriptions[subscription_id] = {
            "contract_address": contract_address,
            "event_name": event_name,
            "callback": callback,
        }

        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            return True
        return False


class MockBlockchainAdapter(IBlockchainAdapter):
    """
    Mock blockchain adapter for testing and development.

    Simulates blockchain operations without actual network connection.
    """

    def __init__(self):
        """Initialize mock adapter."""
        self._wallets: dict[str, dict[str, Any]] = {}
        self._transactions: dict[str, Transaction] = {}
        self._contracts: dict[str, SmartContract] = {}
        self._subscriptions: dict[str, Any] = {}
        self._balances: dict[str, Decimal] = {}
        self._block_number = 1000000

    async def initialize(self, config: dict[str, Any]) -> bool:
        """Initialize mock adapter."""
        logger.info("Mock blockchain adapter initialized")
        return True

    async def shutdown(self) -> None:
        """Shutdown mock adapter."""
        self._wallets.clear()
        self._transactions.clear()

    async def is_connected(self) -> bool:
        """Always connected in mock mode."""
        return True

    async def create_wallet(self, password: str | None = None) -> WalletInfo:
        """Create a mock wallet with initial balance."""
        import secrets
        address = "0x" + secrets.token_hex(20)

        # Give initial balance for testing
        initial_balance = Decimal("100.0")
        self._balances[address] = initial_balance
        self._wallets[address] = {
            "address": address,
            "created_at": time.time(),
        }

        return WalletInfo(
            address=address,
            balance=initial_balance,
            network=BlockchainNetwork.CUSTOM,
        )

    async def get_wallet(self, address: str) -> WalletInfo | None:
        """Get mock wallet."""
        if address not in self._wallets:
            return None

        return WalletInfo(
            address=address,
            balance=self._balances.get(address, Decimal("0")),
            network=BlockchainNetwork.CUSTOM,
        )

    async def get_balance(self, address: str) -> Decimal:
        """Get mock balance."""
        return self._balances.get(address, Decimal("0"))

    async def transfer(
        self,
        from_address: str,
        to_address: str,
        value: Decimal,
        private_key: str | None = None,
        data: str | None = None,
    ) -> Transaction:
        """Mock transfer."""
        tx_id = hashlib.sha256(f"{from_address}{to_address}{value}{time.time()}".encode()).hexdigest()[:16]

        # Check balance
        from_balance = self._balances.get(from_address, Decimal("0"))
        if from_balance < value:
            return Transaction(
                id=tx_id,
                from_address=from_address,
                to_address=to_address,
                value=value,
                status=TransactionStatus.FAILED,
                metadata={"error": "Insufficient balance"},
            )

        # Update balances
        self._balances[from_address] = from_balance - value
        self._balances[to_address] = self._balances.get(to_address, Decimal("0")) + value

        transaction = Transaction(
            id=tx_id,
            from_address=from_address,
            to_address=to_address,
            value=value,
            data=data,
            tx_hash="0x" + hashlib.sha256(tx_id.encode()).hexdigest(),
            status=TransactionStatus.CONFIRMED,
            block_number=self._block_number,
            confirmed_at=time.time(),
        )

        self._transactions[transaction.tx_hash] = transaction
        self._block_number += 1

        return transaction

    async def get_transaction(self, tx_hash: str) -> Transaction | None:
        """Get mock transaction."""
        return self._transactions.get(tx_hash)

    async def wait_for_confirmation(
        self,
        tx_hash: str,
        timeout: float = 60.0,
        confirmations: int = 1,
    ) -> Transaction:
        """Instantly confirm in mock mode."""
        tx = self._transactions.get(tx_hash)
        if tx:
            return tx
        raise ValueError(f"Transaction {tx_hash} not found")

    async def deploy_contract(
        self,
        bytecode: str,
        abi: list[dict[str, Any]],
        constructor_args: list[Any] | None = None,
        from_address: str | None = None,
    ) -> SmartContract:
        """Deploy mock contract."""
        import secrets
        address = "0x" + secrets.token_hex(20)

        contract = SmartContract(
            address=address,
            name=f"MockContract_{address[:8]}",
            abi=abi,
            bytecode=bytecode,
            network=BlockchainNetwork.CUSTOM,
            deployed_at=time.time(),
        )

        self._contracts[address] = contract
        return contract

    async def call_contract(
        self,
        contract_address: str,
        method: str,
        args: list[Any] | None = None,
        from_address: str | None = None,
    ) -> Any:
        """Mock contract call."""
        return {"result": "mock_result", "method": method, "args": args}

    async def execute_contract(
        self,
        contract_address: str,
        method: str,
        args: list[Any] | None = None,
        from_address: str = None,
        private_key: str | None = None,
        value: Decimal = Decimal("0"),
    ) -> Transaction:
        """Mock contract execution."""
        tx_id = hashlib.sha256(f"{contract_address}{method}{time.time()}".encode()).hexdigest()[:16]

        transaction = Transaction(
            id=tx_id,
            from_address=from_address or "0x0",
            to_address=contract_address,
            value=value,
            data=json.dumps({"method": method, "args": args}),
            tx_hash="0x" + hashlib.sha256(tx_id.encode()).hexdigest(),
            status=TransactionStatus.CONFIRMED,
            block_number=self._block_number,
            confirmed_at=time.time(),
        )

        self._transactions[transaction.tx_hash] = transaction
        self._block_number += 1

        return transaction

    async def get_block_number(self) -> int:
        """Get mock block number."""
        return self._block_number

    async def subscribe_to_events(
        self,
        contract_address: str,
        event_name: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> str:
        """Subscribe to mock events."""
        import uuid
        return str(uuid.uuid4())

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from mock events."""
        return True
