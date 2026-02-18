"""
Custom Blockchain Adapter for USMSB Platform

This module provides a custom blockchain implementation specifically designed
for the AI Civilization New World Platform. It features:
- Fast block times optimized for agent transactions
- Native support for agent identity and reputation
- Built-in governance and voting mechanisms
- Cross-chain bridge support for Ethereum ecosystem
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class CustomChainNetwork(str, Enum):
    """Custom chain network types."""
    MAINNET = "usmsb_mainnet"
    TESTNET = "usmsb_testnet"
    LOCAL = "usmsb_local"


@dataclass
class Block:
    """Block in the custom blockchain."""
    number: int
    hash: str
    parent_hash: str
    timestamp: float
    transactions: List[Dict[str, Any]]
    state_root: str
    validator: str
    signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "hash": self.hash,
            "parent_hash": self.parent_hash,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "state_root": self.state_root,
            "validator": self.validator,
        }


@dataclass
class AgentIdentity:
    """Agent identity on the custom chain."""
    agent_id: str
    address: str
    public_key: str
    reputation: Decimal = Decimal("0")
    stake: Decimal = Decimal("0")
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CustomChainAdapter:
    """
    Custom blockchain adapter for the USMSB platform.

    Provides a lightweight, fast blockchain optimized for:
    - Agent identity management
    - Micro-transactions between agents
    - Governance and voting
    - Cross-chain bridges to Ethereum
    """

    BLOCK_TIME = 2.0  # 2 second block time
    MIN_STAKE = Decimal("1000")  # Minimum stake for validators

    def __init__(self, network: CustomChainNetwork = CustomChainNetwork.LOCAL):
        self.network = network
        self._chain: List[Block] = []
        self._state: Dict[str, Any] = {}  # World state
        self._identities: Dict[str, AgentIdentity] = {}
        self._wallets: Dict[str, Dict[str, Any]] = {}
        self._validators: Dict[str, Decimal] = {}  # address -> stake
        self._pending_txs: List[Dict[str, Any]] = []
        self._subscriptions: Dict[str, Callable] = {}
        self._running = False
        self._block_task: Optional[asyncio.Task] = None
        self._node_id = str(uuid.uuid4())[:8]

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the custom chain."""
        try:
            # Create genesis block
            genesis = Block(
                number=0,
                hash="0x" + "0" * 64,
                parent_hash="0x" + "0" * 64,
                timestamp=time.time(),
                transactions=[],
                state_root=hashlib.sha256(b"genesis").hexdigest(),
                validator="genesis",
            )
            self._chain.append(genesis)

            # Initialize state
            self._state = {
                "balances": {},
                "stakes": {},
                "governance": {
                    "proposals": {},
                    "votes": {},
                },
            }

            logger.info(f"Custom chain initialized: {self.network.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize custom chain: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown the chain."""
        self._running = False
        if self._block_task:
            self._block_task.cancel()

    async def is_connected(self) -> bool:
        """Always connected for local chain."""
        return True

    async def create_wallet(self, password: Optional[str] = None) -> Dict[str, Any]:
        """Create a new wallet."""
        address = "usmsb_" + hashlib.sha256(f"{time.time()}{uuid.uuid4()}".encode()).hexdigest()[:32]
        private_key = hashlib.sha256(f"{address}{password or ''}".encode()).hexdigest()

        self._wallets[address] = {
            "address": address,
            "private_key": private_key,
            "balance": Decimal("1000.0"),  # Initial balance
        }

        self._state["balances"][address] = Decimal("1000.0")

        return {
            "address": address,
            "balance": Decimal("1000.0"),
        }

    async def register_agent_identity(
        self,
        agent_id: str,
        public_key: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentIdentity:
        """Register an agent identity on the chain."""
        # Create address from agent_id
        address = "agent_" + hashlib.sha256(agent_id.encode()).hexdigest()[:28]

        identity = AgentIdentity(
            agent_id=agent_id,
            address=address,
            public_key=public_key,
            metadata=metadata or {},
        )

        self._identities[agent_id] = identity
        self._state["balances"][address] = Decimal("100.0")  # Initial balance for agents

        # Create registration transaction
        tx = {
            "type": "identity_register",
            "agent_id": agent_id,
            "address": address,
            "public_key": public_key,
            "timestamp": time.time(),
        }
        self._pending_txs.append(tx)

        logger.info(f"Registered agent identity: {agent_id} -> {address}")
        return identity

    async def get_agent_identity(self, agent_id: str) -> Optional[AgentIdentity]:
        """Get agent identity."""
        return self._identities.get(agent_id)

    async def transfer(
        self,
        from_address: str,
        to_address: str,
        value: Decimal,
        private_key: Optional[str] = None,
        data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Transfer tokens."""
        # Check balance
        from_balance = self._state["balances"].get(from_address, Decimal("0"))
        if from_balance < value:
            return {
                "status": "failed",
                "error": "Insufficient balance",
            }

        # Create transaction
        tx = {
            "id": str(uuid.uuid4()),
            "type": "transfer",
            "from": from_address,
            "to": to_address,
            "value": str(value),
            "data": data,
            "timestamp": time.time(),
        }

        self._pending_txs.append(tx)

        # Update state
        self._state["balances"][from_address] = from_balance - value
        self._state["balances"][to_address] = self._state["balances"].get(to_address, Decimal("0")) + value

        return {
            "id": tx["id"],
            "status": "confirmed",
            "tx_hash": hashlib.sha256(json.dumps(tx).encode()).hexdigest(),
        }

    async def get_balance(self, address: str) -> Decimal:
        """Get balance."""
        return self._state["balances"].get(address, Decimal("0"))

    async def stake(self, address: str, amount: Decimal) -> Dict[str, Any]:
        """Stake tokens for validation."""
        balance = self._state["balances"].get(address, Decimal("0"))
        if balance < amount:
            return {"status": "failed", "error": "Insufficient balance"}

        self._state["balances"][address] = balance - amount
        self._state["stakes"][address] = self._state["stakes"].get(address, Decimal("0")) + amount

        tx = {
            "id": str(uuid.uuid4()),
            "type": "stake",
            "address": address,
            "amount": str(amount),
            "timestamp": time.time(),
        }
        self._pending_txs.append(tx)

        return {"status": "confirmed", "stake": str(self._state["stakes"][address])}

    async def unstake(self, address: str, amount: Decimal) -> Dict[str, Any]:
        """Unstake tokens."""
        staked = self._state["stakes"].get(address, Decimal("0"))
        if staked < amount:
            return {"status": "failed", "error": "Insufficient staked amount"}

        self._state["stakes"][address] = staked - amount
        self._state["balances"][address] = self._state["balances"].get(address, Decimal("0")) + amount

        return {"status": "confirmed", "stake": str(self._state["stakes"][address])}

    async def create_proposal(
        self,
        proposer: str,
        title: str,
        description: str,
        proposal_type: str = "general",
    ) -> Dict[str, Any]:
        """Create a governance proposal."""
        proposal_id = hashlib.sha256(f"{title}{time.time()}".encode()).hexdigest()[:16]

        proposal = {
            "id": proposal_id,
            "proposer": proposer,
            "title": title,
            "description": description,
            "type": proposal_type,
            "status": "active",
            "votes_for": Decimal("0"),
            "votes_against": Decimal("0"),
            "created_at": time.time(),
            "ends_at": time.time() + 7 * 24 * 3600,  # 7 days
        }

        self._state["governance"]["proposals"][proposal_id] = proposal

        tx = {
            "id": str(uuid.uuid4()),
            "type": "proposal_create",
            "proposal_id": proposal_id,
            "proposer": proposer,
            "timestamp": time.time(),
        }
        self._pending_txs.append(tx)

        return proposal

    async def vote(
        self,
        voter: str,
        proposal_id: str,
        support: bool,
        weight: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """Vote on a proposal."""
        proposal = self._state["governance"]["proposals"].get(proposal_id)
        if not proposal:
            return {"status": "failed", "error": "Proposal not found"}

        if proposal["status"] != "active":
            return {"status": "failed", "error": "Proposal not active"}

        # Calculate voting weight based on stake
        stake = self._state["stakes"].get(voter, Decimal("0"))
        vote_weight = weight or (stake if stake > 0 else Decimal("1"))

        # Record vote
        vote_key = f"{proposal_id}:{voter}"
        self._state["governance"]["votes"][vote_key] = {
            "voter": voter,
            "proposal_id": proposal_id,
            "support": support,
            "weight": str(vote_weight),
        }

        # Update proposal
        if support:
            proposal["votes_for"] = Decimal(proposal["votes_for"]) + vote_weight
        else:
            proposal["votes_against"] = Decimal(proposal["votes_against"]) + vote_weight

        tx = {
            "id": str(uuid.uuid4()),
            "type": "vote",
            "voter": voter,
            "proposal_id": proposal_id,
            "support": support,
            "weight": str(vote_weight),
            "timestamp": time.time(),
        }
        self._pending_txs.append(tx)

        return {"status": "confirmed", "vote_weight": str(vote_weight)}

    async def get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Get proposal by ID."""
        return self._state["governance"]["proposals"].get(proposal_id)

    async def get_block_number(self) -> int:
        """Get current block number."""
        return len(self._chain) - 1

    async def get_block(self, block_number: int) -> Optional[Block]:
        """Get block by number."""
        if 0 <= block_number < len(self._chain):
            return self._chain[block_number]
        return None

    async def subscribe_to_events(
        self,
        event_type: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> str:
        """Subscribe to chain events."""
        subscription_id = str(uuid.uuid4())
        self._subscriptions[subscription_id] = {
            "event_type": event_type,
            "callback": callback,
        }
        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            return True
        return False

    async def start_block_production(self) -> None:
        """Start producing blocks."""
        self._running = True
        self._block_task = asyncio.create_task(self._block_production_loop())
        logger.info(f"Started block production on {self._node_id}")

    async def stop_block_production(self) -> None:
        """Stop producing blocks."""
        self._running = False
        if self._block_task:
            self._block_task.cancel()

    async def _block_production_loop(self) -> None:
        """Produce blocks at regular intervals."""
        while self._running:
            try:
                await asyncio.sleep(self.BLOCK_TIME)
                await self._produce_block()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in block production: {e}")

    async def _produce_block(self) -> Block:
        """Produce a new block."""
        if not self._chain:
            return None

        parent = self._chain[-1]

        # Get pending transactions
        txs = self._pending_txs.copy()
        self._pending_txs.clear()

        # Calculate state root
        state_root = hashlib.sha256(json.dumps(self._state, default=str).encode()).hexdigest()

        # Create block
        block_number = len(self._chain)
        block_hash = hashlib.sha256(
            f"{block_number}{parent.hash}{time.time()}{len(txs)}".encode()
        ).hexdigest()

        block = Block(
            number=block_number,
            hash=block_hash,
            parent_hash=parent.hash,
            timestamp=time.time(),
            transactions=txs,
            state_root=state_root,
            validator=self._node_id,
        )

        self._chain.append(block)

        # Notify subscribers
        for sub in self._subscriptions.values():
            if sub["event_type"] == "new_block":
                try:
                    await sub["callback"](block.to_dict())
                except Exception as e:
                    logger.error(f"Error in block subscriber: {e}")

        logger.debug(f"Produced block {block_number} with {len(txs)} transactions")
        return block

    async def get_chain_info(self) -> Dict[str, Any]:
        """Get chain information."""
        return {
            "network": self.network.value,
            "node_id": self._node_id,
            "block_height": len(self._chain) - 1,
            "total_identities": len(self._identities),
            "total_validators": len(self._validators),
            "pending_transactions": len(self._pending_txs),
        }


# Cross-chain bridge for Ethereum ecosystem
class CrossChainBridge:
    """
    Bridge for cross-chain transactions between USMSB chain and Ethereum.
    """

    def __init__(
        self,
        usmsb_chain: CustomChainAdapter,
        ethereum_adapter: Optional[Any] = None,
    ):
        self.usmsb_chain = usmsb_chain
        self.ethereum = ethereum_adapter
        self._pending_bridges: Dict[str, Dict] = {}
        self._bridge_contracts = {}

    async def bridge_to_ethereum(
        self,
        from_address: str,
        to_eth_address: str,
        amount: Decimal,
        token: str = "USMSB",
    ) -> Dict[str, Any]:
        """Bridge tokens from USMSB chain to Ethereum."""
        # Lock tokens on USMSB chain
        balance = await self.usmsb_chain.get_balance(from_address)
        if balance < amount:
            return {"status": "failed", "error": "Insufficient balance"}

        # Create bridge transaction
        bridge_id = hashlib.sha256(f"{from_address}{to_eth_address}{amount}{time.time()}".encode()).hexdigest()[:16]

        self._pending_bridges[bridge_id] = {
            "id": bridge_id,
            "type": "usmsb_to_eth",
            "from_address": from_address,
            "to_address": to_eth_address,
            "amount": str(amount),
            "token": token,
            "status": "pending",
            "created_at": time.time(),
        }

        # Lock tokens
        self.usmsb_chain._state["balances"][from_address] = balance - amount

        # In production, would interact with bridge contracts
        # For now, simulate completion
        self._pending_bridges[bridge_id]["status"] = "completed"

        return {
            "bridge_id": bridge_id,
            "status": "pending",
            "estimated_time": "10-30 minutes",
        }

    async def bridge_from_ethereum(
        self,
        from_eth_address: str,
        to_usmsb_address: str,
        amount: Decimal,
        token: str = "USMSB",
        eth_tx_hash: str = "",
    ) -> Dict[str, Any]:
        """Bridge tokens from Ethereum to USMSB chain."""
        bridge_id = hashlib.sha256(f"{from_eth_address}{to_usmsb_address}{amount}{time.time()}".encode()).hexdigest()[:16]

        self._pending_bridges[bridge_id] = {
            "id": bridge_id,
            "type": "eth_to_usmsb",
            "from_address": from_eth_address,
            "to_address": to_usmsb_address,
            "amount": str(amount),
            "token": token,
            "eth_tx_hash": eth_tx_hash,
            "status": "pending",
            "created_at": time.time(),
        }

        # Mint tokens on USMSB chain (simplified)
        self.usmsb_chain._state["balances"][to_usmsb_address] = (
            self.usmsb_chain._state["balances"].get(to_usmsb_address, Decimal("0")) + amount
        )

        self._pending_bridges[bridge_id]["status"] = "completed"

        return {
            "bridge_id": bridge_id,
            "status": "completed",
        }

    async def get_bridge_status(self, bridge_id: str) -> Optional[Dict[str, Any]]:
        """Get bridge transaction status."""
        return self._pending_bridges.get(bridge_id)
