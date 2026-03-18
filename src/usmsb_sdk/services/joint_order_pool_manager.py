"""
Joint Order Pool Manager

Bridges the OrderService (off-chain) with JointOrderClient (on-chain).
Handles:
- Creating JointOrder pools from Orders
- Submitting bids on behalf of supply agents
- Accepting bids and triggering fund distribution
- Confirming delivery and triggering completion

This is the on-chain execution layer for the off-chain order flow.
"""

import logging
from dataclasses import dataclass
from typing import Any

from usmsb_sdk.blockchain.contracts.joint_order import JointOrderClient, PoolStatus
from usmsb_sdk.blockchain.web3_client import Web3Client
from usmsb_sdk.config import BlockchainConfig

logger = logging.getLogger(__name__)


@dataclass
class PoolCreationResult:
    """Result of creating a JointOrder pool from an Order"""
    success: bool
    pool_id: str | None
    chain_order_id: str | None  # bytes32 hex
    tx_hash: str | None
    message: str
    pool_status: PoolStatus | None = None


@dataclass
class BidSubmissionResult:
    """Result of submitting a bid"""
    success: bool
    bid_id: str | None
    tx_hash: str | None
    message: str


@dataclass
class BidAcceptanceResult:
    """Result of accepting a bid"""
    success: bool
    tx_hash: str | None
    message: str


class JointOrderPoolManager:
    """
    Manages JointOrder pool lifecycle from Order creation to completion.

    This class coordinates between:
    - OrderService (off-chain order state)
    - JointOrderClient (on-chain pool state)
    - VIBE token (funds)

    Flow:
        Order (off-chain, status=CONFIRMED)
              ↓ create_pool()
        JointOrder pool (on-chain, status=FUNDED/BIDDING)
              ↓ submit_bid()  [by supply agent]
        Bid submitted
              ↓ accept_bid()  [by demand agent]
        Pool awarded (status=AWARDED)
              ↓ confirm_delivery()  [by demand agent]
        Funds released to supply agent
    """

    def __init__(
        self,
        web3_client: Web3Client | None = None,
        config: BlockchainConfig | None = None,
        joint_order_client: JointOrderClient | None = None,
        vibe_token_address: str | None = None,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize the JointOrder Pool Manager.

        Args:
            web3_client: Web3 client instance
            config: Blockchain configuration
            joint_order_client: Pre-configured JointOrderClient (takes priority)
            vibe_token_address: VIBE token contract address
            logger: Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

        if joint_order_client:
            self._client = joint_order_client
        elif web3_client and config:
            self._client = JointOrderClient(
                web3_client=web3_client,
                config=config,
            )
        else:
            self._client = None
            self.logger.warning("JointOrderClient not initialized - on-chain features disabled")

        self._vibe_token = vibe_token_address

    @property
    def is_available(self) -> bool:
        """Check if on-chain client is available."""
        return self._client is not None

    # ==================== Pool Creation ====================

    async def create_pool_from_order(
        self,
        order_id: str,
        service_type: str,
        total_budget: float,
        delivery_hours: int,
        from_address: str,
        private_key: str,
        min_budget: float | None = None,
        gas_limit: int | None = None,
    ) -> PoolCreationResult:
        """
        Create a JointOrder pool for an order.

        This locks the order's budget as VIBE in the smart contract.

        Args:
            order_id: Off-chain order ID (for tracking)
            service_type: Type of service (e.g., "python_development")
            total_budget: Total budget in VIBE (wei)
            delivery_hours: Delivery deadline in hours from now
            from_address: Payer's wallet address
            private_key: Payer's private key (for signing)
            min_budget: Minimum pool budget (defaults to total_budget)
            gas_limit: Optional gas limit

        Returns:
            PoolCreationResult with chain details
        """
        if not self._client:
            return PoolCreationResult(
                success=False,
                pool_id=None,
                chain_order_id=None,
                tx_hash=None,
                message="JointOrderClient not available",
            )

        import time

        bidding_duration = delivery_hours * 3600  # Convert to seconds
        funding_duration = 24 * 3600  # 24 hours to fund

        try:
            # Build metadata hash from order_id
            import hashlib
            metadata_hash = hashlib.sha256(order_id.encode()).digest()

            tx_hash = await self._client.create_pool(
                service_type=service_type,
                min_budget=int(min_budget or total_budget),
                bidding_duration=bidding_duration,
                from_address=from_address,
                private_key=private_key,
                funding_duration=funding_duration,
                delivery_deadline=int(time.time()) + funding_duration + bidding_duration,
                metadata_hash=metadata_hash,
                gas_limit=gas_limit,
            )

            # Get pool info to retrieve the pool_id
            # The pool_id is returned from the transaction events
            # Verify transaction success on-chain
            receipt = self._client.wait_for_transaction(tx_hash, timeout=120)
            if not receipt or receipt.get("status") != 1:
                tx_hash_str = str(tx_hash) if tx_hash else "unknown"
                self.logger.error(
                    f"create_pool transaction failed on-chain: tx={tx_hash_str}, "
                    f"receipt={receipt}"
                )
                return PoolCreationResult(
                    success=False,
                    pool_id=None,
                    chain_order_id=None,
                    tx_hash=tx_hash_str,
                    message=f"Transaction failed on-chain (status={receipt.get('status') if receipt else 'none'}). Check tx {tx_hash_str}.",
                )

            pool_id = None
            chain_order_id = None
            if receipt.get("logs"):
                for log in receipt["logs"]:
                    if len(log.get("topics", [])) > 1:
                        # PoolCreated event: topics[1] = poolId (bytes32)
                        raw_pool_id = log["topics"][1]
                        chain_order_id = "0x" + raw_pool_id.hex()
                        # Derive a readable pool_id
                        pool_id = f"pool-{chain_order_id[2:18]}"

            self.logger.info(
                f"Created JointOrder pool for order {order_id}: "
                f"pool_id={pool_id}, chain_order_id={chain_order_id}, tx={tx_hash}"
            )

            return PoolCreationResult(
                success=True,
                pool_id=pool_id,
                chain_order_id=chain_order_id,
                tx_hash=tx_hash,
                message="Pool created successfully",
                pool_status=PoolStatus.CREATED,
            )

        except Exception as e:
            self.logger.error(f"Failed to create pool for order {order_id}: {e}")
            return PoolCreationResult(
                success=False,
                pool_id=None,
                chain_order_id=None,
                tx_hash=None,
                message=f"Pool creation failed: {e}",
            )

    # ==================== Bidding ====================

    async def submit_bid(
        self,
        pool_id: str,
        chain_pool_id: str,
        price: float,
        delivery_hours: int,
        reputation_score: int,
        from_address: str,
        private_key: str,
        proposal: str = "",
        reputation_signature: bytes | None = None,
        gas_limit: int | None = None,
    ) -> BidSubmissionResult:
        """
        Submit a bid on a pool (supply agent responds to an order).

        Args:
            pool_id: Readable pool ID
            chain_pool_id: On-chain pool ID (bytes32 hex)
            price: Bid price in wei
            delivery_hours: Promised delivery time in hours
            reputation_score: Agent's reputation score (0-100)
            from_address: Provider's wallet address
            private_key: Provider's private key
            proposal: Proposal description
            reputation_signature: Optional reputation proof signature
            gas_limit: Optional gas limit

        Returns:
            BidSubmissionResult with bid details
        """
        if not self._client:
            return BidSubmissionResult(
                success=False,
                bid_id=None,
                tx_hash=None,
                message="JointOrderClient not available",
            )

        try:
            # Convert pool_id to bytes32 format
            if chain_pool_id.startswith("0x"):
                chain_pool_id_bytes = chain_pool_id
            else:
                chain_pool_id_bytes = "0x" + chain_pool_id

            tx_hash = await self._client.submit_bid(
                pool_id=chain_pool_id_bytes,
                price=int(price),
                delivery_time=delivery_hours,
                reputation=reputation_score,
                from_address=from_address,
                private_key=private_key,
                proposal=proposal,
                reputation_signature=reputation_signature,
                gas_limit=gas_limit,
            )

            # Verify transaction success on-chain
            receipt = self._client.wait_for_transaction(tx_hash, timeout=60)
            if not receipt or receipt.get("status") != 1:
                tx_hash_str = str(tx_hash) if tx_hash else "unknown"
                self.logger.error(
                    f"submit_bid transaction failed on-chain: tx={tx_hash_str}"
                )
                return BidSubmissionResult(
                    success=False,
                    bid_id=None,
                    tx_hash=tx_hash_str,
                    message=f"Transaction failed on-chain (status={receipt.get('status') if receipt else 'none'})",
                )

            bid_id = None
            if receipt.get("logs"):
                for log in receipt["logs"]:
                    if len(log.get("topics", [])) > 2:
                        # BidSubmitted event: topics[2] = bidId
                        bid_id = "0x" + log["topics"][2].hex()
                        break

            self.logger.info(
                f"Bid submitted on pool {pool_id}: "
                f"bid_id={bid_id}, price={price}, from={from_address}"
            )

            return BidSubmissionResult(
                success=True,
                bid_id=bid_id,
                tx_hash=tx_hash,
                message="Bid submitted successfully",
            )

        except Exception as e:
            self.logger.error(f"Failed to submit bid on pool {pool_id}: {e}")
            return BidSubmissionResult(
                success=False,
                bid_id=None,
                tx_hash=None,
                message=f"Bid submission failed: {e}",
            )

    async def accept_bid(
        self,
        pool_id: str,
        chain_pool_id: str,
        bid_id: str,
        from_address: str,
        private_key: str,
        gas_limit: int | None = None,
    ) -> BidAcceptanceResult:
        """
        Accept a bid and award the pool (demand agent selects a provider).

        Args:
            pool_id: Readable pool ID
            chain_pool_id: On-chain pool ID (bytes32 hex)
            bid_id: On-chain bid ID (bytes32 hex)
            from_address: Awarder's wallet address
            private_key: Awarder's private key
            gas_limit: Optional gas limit

        Returns:
            BidAcceptanceResult
        """
        if not self._client:
            return BidAcceptanceResult(
                success=False,
                tx_hash=None,
                message="JointOrderClient not available",
            )

        try:
            # Normalize to bytes32
            if not chain_pool_id.startswith("0x"):
                chain_pool_id = "0x" + chain_pool_id
            if not bid_id.startswith("0x"):
                bid_id = "0x" + bid_id

            tx_hash = await self._client.accept_bid(
                pool_id=chain_pool_id,
                bid_id=bid_id,
                from_address=from_address,
                private_key=private_key,
                gas_limit=gas_limit,
            )

            self.logger.info(
                f"Bid {bid_id} accepted on pool {pool_id}: tx={tx_hash}"
            )

            return BidAcceptanceResult(
                success=True,
                tx_hash=tx_hash,
                message="Bid accepted, pool awarded",
            )

        except Exception as e:
            self.logger.error(f"Failed to accept bid {bid_id} on pool {pool_id}: {e}")
            return BidAcceptanceResult(
                success=False,
                tx_hash=None,
                message=f"Bid acceptance failed: {e}",
            )

    # ==================== Delivery & Completion ====================

    async def confirm_delivery(
        self,
        pool_id: str,
        chain_pool_id: str,
        rating: int,
        from_address: str,
        private_key: str,
        gas_limit: int | None = None,
    ) -> BidAcceptanceResult:
        """
        Confirm delivery and release funds to the provider.

        Args:
            pool_id: Readable pool ID
            chain_pool_id: On-chain pool ID (bytes32 hex)
            rating: Delivery rating (1-5)
            from_address: Confirmer's wallet address
            private_key: Confirmer's private key
            gas_limit: Optional gas limit

        Returns:
            BidAcceptanceResult
        """
        if not self._client:
            return BidAcceptanceResult(
                success=False,
                tx_hash=None,
                message="JointOrderClient not available",
            )

        try:
            if not chain_pool_id.startswith("0x"):
                chain_pool_id = "0x" + chain_pool_id

            tx_hash = await self._client.confirm_delivery(
                pool_id=chain_pool_id,
                rating=rating,
                from_address=from_address,
                private_key=private_key,
                gas_limit=gas_limit,
            )

            self.logger.info(
                f"Delivery confirmed on pool {pool_id}, rating={rating}: tx={tx_hash}"
            )

            return BidAcceptanceResult(
                success=True,
                tx_hash=tx_hash,
                message="Delivery confirmed, funds released",
            )

        except Exception as e:
            self.logger.error(f"Failed to confirm delivery on pool {pool_id}: {e}")
            return BidAcceptanceResult(
                success=False,
                tx_hash=None,
                message=f"Delivery confirmation failed: {e}",
            )

    async def withdraw_provider_earnings(
        self,
        pool_id: str,
        chain_pool_id: str,
        from_address: str,
        private_key: str,
        gas_limit: int | None = None,
    ) -> BidAcceptanceResult:
        """
        Withdraw earnings after delivery is confirmed (provider calls this).

        Args:
            pool_id: Readable pool ID
            chain_pool_id: On-chain pool ID (bytes32 hex)
            from_address: Provider's wallet address
            private_key: Provider's private key
            gas_limit: Optional gas limit

        Returns:
            BidAcceptanceResult
        """
        if not self._client:
            return BidAcceptanceResult(
                success=False,
                tx_hash=None,
                message="JointOrderClient not available",
            )

        try:
            if not chain_pool_id.startswith("0x"):
                chain_pool_id = "0x" + chain_pool_id

            tx_hash = await self._client.withdraw_earnings(
                pool_id=chain_pool_id,
                from_address=from_address,
                private_key=private_key,
                gas_limit=gas_limit,
            )

            self.logger.info(f"Provider earnings withdrawn for pool {pool_id}: tx={tx_hash}")

            return BidAcceptanceResult(
                success=True,
                tx_hash=tx_hash,
                message="Earnings withdrawn successfully",
            )

        except Exception as e:
            self.logger.error(f"Failed to withdraw earnings for pool {pool_id}: {e}")
            return BidAcceptanceResult(
                success=False,
                tx_hash=None,
                message=f"Withdrawal failed: {e}",
            )

    # ==================== Queries ====================

    async def get_pool_status(
        self,
        chain_pool_id: str,
    ) -> PoolStatus | None:
        """Get the current status of a pool on-chain."""
        if not self._client:
            return None

        try:
            if not chain_pool_id.startswith("0x"):
                chain_pool_id = "0x" + chain_pool_id

            info = await self._client.get_pool_info(chain_pool_id)
            return info.get("status")
        except Exception as e:
            self.logger.error(f"Failed to get pool status for {chain_pool_id}: {e}")
            return None

    async def get_pool_bids(
        self,
        chain_pool_id: str,
    ) -> list[dict[str, Any]]:
        """Get all bids on a pool."""
        if not self._client:
            return []

        try:
            if not chain_pool_id.startswith("0x"):
                chain_pool_id = "0x" + chain_pool_id

            return await self._client.get_bids(chain_pool_id)
        except Exception as e:
            self.logger.error(f"Failed to get bids for pool {chain_pool_id}: {e}")
            return []

    async def get_chain_stats(self) -> dict[str, Any]:
        """Get on-chain JointOrder statistics."""
        if not self._client:
            return {}

        try:
            return await self._client.get_stats()
        except Exception as e:
            self.logger.error(f"Failed to get chain stats: {e}")
            return {}
