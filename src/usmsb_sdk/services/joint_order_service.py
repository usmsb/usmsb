"""
Joint Order Service for AI Civilization Platform

Implements the off-chain logic for joint orders:
- Demand aggregation
- Bid evaluation
- Pool management
- Contract interaction
"""

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class PoolStatus(StrEnum):
    """Pool status enumeration."""

    CREATED = "created"
    FUNDED = "funded"
    BIDDING = "bidding"
    AWARDED = "awarded"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class Demand:
    """A demand listing."""

    demand_id: str
    user_id: str
    service_type: str
    budget: float
    requirements: dict[str, Any]
    deadline: float | None = None
    created_at: float = field(default_factory=time.time)
    status: str = "active"

    def to_dict(self) -> dict[str, Any]:
        return {
            "demandId": self.demand_id,
            "userId": self.user_id,
            "serviceType": self.service_type,
            "budget": self.budget,
            "requirements": self.requirements,
            "deadline": self.deadline,
            "createdAt": self.created_at,
            "status": self.status,
        }


@dataclass
class OrderPool:
    """An aggregated order pool."""

    pool_id: str
    service_type: str
    creator_id: str
    demands: list[Demand]
    total_budget: float
    min_budget: float
    participant_count: int
    created_at: float
    funding_deadline: float
    bidding_ends_at: float
    delivery_deadline: float
    status: PoolStatus
    bids: list["Bid"] = field(default_factory=list)
    winning_bid_id: str | None = None
    winning_provider: str | None = None
    winning_price: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "poolId": self.pool_id,
            "serviceType": self.service_type,
            "creatorId": self.creator_id,
            "totalBudget": self.total_budget,
            "minBudget": self.min_budget,
            "participantCount": self.participant_count,
            "createdAt": self.created_at,
            "fundingDeadline": self.funding_deadline,
            "biddingEndsAt": self.bidding_ends_at,
            "deliveryDeadline": self.delivery_deadline,
            "status": self.status.value,
            "bidCount": len(self.bids),
            "winningBidId": self.winning_bid_id,
            "winningProvider": self.winning_provider,
            "winningPrice": self.winning_price,
        }


@dataclass
class Bid:
    """A bid from a service provider."""

    bid_id: str
    pool_id: str
    provider_id: str
    price: float
    delivery_time_hours: int
    reputation_score: float
    computed_score: float
    proposal: str
    created_at: float = field(default_factory=time.time)
    is_winner: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "bidId": self.bid_id,
            "poolId": self.pool_id,
            "providerId": self.provider_id,
            "price": self.price,
            "deliveryTimeHours": self.delivery_time_hours,
            "reputationScore": self.reputation_score,
            "computedScore": self.computed_score,
            "proposal": self.proposal,
            "createdAt": self.created_at,
            "isWinner": self.is_winner,
        }


@dataclass
class ServiceStats:
    """Statistics for the joint order service."""

    total_demands: int = 0
    total_pools: int = 0
    active_pools: int = 0
    completed_pools: int = 0
    total_volume: float = 0.0
    total_bids: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "totalDemands": self.total_demands,
            "totalPools": self.total_pools,
            "activePools": self.active_pools,
            "completedPools": self.completed_pools,
            "totalVolume": self.total_volume,
            "totalBids": self.total_bids,
        }


class JointOrderService:
    """
    Joint Order Service.

    Handles demand aggregation, reverse auction, and contract interaction.
    """

    MIN_POOL_BUDGET = 100.0
    DEFAULT_FUNDING_DURATION = 86400  # 24 hours
    DEFAULT_BIDDING_DURATION = 86400  # 24 hours
    MAX_PARTICIPANTS = 50
    MAX_BIDS = 20

    BID_EVAL_WEIGHTS = {
        "price": 0.40,
        "delivery_time": 0.20,
        "reputation": 0.40,
    }

    def __init__(
        self,
        web3_provider=None,
        contract_address: str | None = None,
        reputation_service=None,
        matching_engine=None,
    ):
        """
        Initialize the joint order service.

        Args:
            web3_provider: Web3 provider for blockchain interaction
            contract_address: JointOrder contract address
            reputation_service: Service for reputation scores
            matching_engine: Service for demand matching
        """
        self.web3 = web3_provider
        self.contract_address = contract_address
        self.reputation = reputation_service
        self.matching_engine = matching_engine

        self._demands: dict[str, Demand] = {}
        self._pools: dict[str, OrderPool] = {}
        self._user_demands: dict[str, list[str]] = {}
        self._service_pools: dict[str, list[str]] = {}

        self._stats = ServiceStats()

        self.on_pool_created: Callable[[OrderPool], None] | None = None
        self.on_pool_funded: Callable[[OrderPool], None] | None = None
        self.on_bid_submitted: Callable[[Bid], None] | None = None
        self.on_pool_awarded: Callable[[OrderPool, Bid], None] | None = None

        self._running = False
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        """Start background tasks."""
        self._running = True
        self._tasks = [
            asyncio.create_task(self._pool_status_loop()),
            asyncio.create_task(self._expired_pools_loop()),
        ]
        logger.info("Joint order service started")

    async def stop(self) -> None:
        """Stop background tasks."""
        self._running = False
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("Joint order service stopped")

    async def _pool_status_loop(self) -> None:
        """Periodically check and update pool statuses."""
        while self._running:
            try:
                await asyncio.sleep(60)
                await self._update_pool_statuses()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Pool status update error: {e}")

    async def _expired_pools_loop(self) -> None:
        """Clean up expired pools."""
        while self._running:
            try:
                await asyncio.sleep(3600)
                await self._expire_old_pools()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Pool expiration error: {e}")

    async def _update_pool_statuses(self) -> None:
        """Update pool statuses based on time."""
        now = time.time()

        for pool in self._pools.values():
            if pool.status == PoolStatus.CREATED:
                if now > pool.funding_deadline:
                    if pool.total_budget >= pool.min_budget:
                        pool.status = PoolStatus.BIDDING
                    else:
                        pool.status = PoolStatus.EXPIRED

            elif pool.status == PoolStatus.BIDDING:
                if now > pool.bidding_ends_at:
                    if pool.bids:
                        await self._auto_award_pool(pool)
                    else:
                        pool.status = PoolStatus.EXPIRED

    async def _expire_old_pools(self) -> None:
        """Mark old pools as expired."""
        now = time.time()
        expiration_threshold = 30 * 86400

        for pool in self._pools.values():
            if pool.status in [PoolStatus.COMPLETED, PoolStatus.CANCELLED]:
                continue
            if now - pool.created_at > expiration_threshold:
                pool.status = PoolStatus.EXPIRED

    # ==================== Demand Management ====================

    async def create_demand(
        self,
        user_id: str,
        service_type: str,
        budget: float,
        requirements: dict[str, Any],
        deadline: float | None = None,
    ) -> Demand:
        """
        Create a new demand.

        Args:
            user_id: User creating the demand
            service_type: Type of service needed
            budget: Budget amount
            requirements: Specific requirements
            deadline: Optional deadline

        Returns:
            Created demand
        """
        demand_id = f"demand-{uuid.uuid4().hex[:8]}"

        demand = Demand(
            demand_id=demand_id,
            user_id=user_id,
            service_type=service_type,
            budget=budget,
            requirements=requirements,
            deadline=deadline,
        )

        self._demands[demand_id] = demand

        if user_id not in self._user_demands:
            self._user_demands[user_id] = []
        self._user_demands[user_id].append(demand_id)

        self._stats.total_demands += 1

        logger.info(f"Created demand: {demand_id}")

        return demand

    def get_demand(self, demand_id: str) -> Demand | None:
        """Get a demand by ID."""
        return self._demands.get(demand_id)

    def get_user_demands(self, user_id: str) -> list[Demand]:
        """Get all demands for a user."""
        demand_ids = self._user_demands.get(user_id, [])
        return [self._demands[did] for did in demand_ids if did in self._demands]

    # ==================== Pool Management ====================

    async def create_pool(
        self,
        creator_id: str,
        service_type: str,
        min_budget: float,
        funding_duration: float | None = None,
        bidding_duration: float | None = None,
        delivery_deadline: float | None = None,
    ) -> OrderPool:
        """
        Create a new order pool.

        Args:
            creator_id: Pool creator
            service_type: Type of service
            min_budget: Minimum budget threshold
            funding_duration: Time for funding (seconds)
            bidding_duration: Time for bidding (seconds)
            delivery_deadline: Delivery deadline

        Returns:
            Created pool
        """
        pool_id = f"pool-{uuid.uuid4().hex[:8]}"

        now = time.time()
        funding_duration = funding_duration or self.DEFAULT_FUNDING_DURATION
        bidding_duration = bidding_duration or self.DEFAULT_BIDDING_DURATION

        pool = OrderPool(
            pool_id=pool_id,
            service_type=service_type,
            creator_id=creator_id,
            demands=[],
            total_budget=0.0,
            min_budget=min_budget,
            participant_count=0,
            created_at=now,
            funding_deadline=now + funding_duration,
            bidding_ends_at=now + funding_duration + bidding_duration,
            delivery_deadline=delivery_deadline
            or (now + funding_duration + bidding_duration + 7 * 86400),
            status=PoolStatus.CREATED,
        )

        self._pools[pool_id] = pool

        if service_type not in self._service_pools:
            self._service_pools[service_type] = []
        self._service_pools[service_type].append(pool_id)

        self._stats.total_pools += 1

        if self.on_pool_created:
            self.on_pool_created(pool)

        logger.info(f"Created pool: {pool_id}")

        return pool

    async def join_pool(
        self,
        pool_id: str,
        demand: Demand,
    ) -> bool:
        """
        Add a demand to a pool.

        Args:
            pool_id: Pool to join
            demand: Demand to add

        Returns:
            True if successful
        """
        pool = self._pools.get(pool_id)
        if not pool:
            logger.warning(f"Pool not found: {pool_id}")
            return False

        if pool.status != PoolStatus.CREATED:
            logger.warning(f"Pool not in created status: {pool.status}")
            return False

        if pool.participant_count >= self.MAX_PARTICIPANTS:
            logger.warning(f"Pool full: {pool_id}")
            return False

        pool.demands.append(demand)
        pool.total_budget += demand.budget
        pool.participant_count += 1

        demand.status = "pooled"

        if pool.total_budget >= pool.min_budget and pool.status == PoolStatus.CREATED:
            pool.status = PoolStatus.FUNDED
            if self.on_pool_funded:
                self.on_pool_funded(pool)

        logger.info(f"Demand {demand.demand_id} joined pool {pool_id}")

        return True

    async def aggregate_demands(
        self,
        new_demand: Demand,
        similarity_threshold: float = 0.7,
    ) -> tuple[OrderPool | None, bool]:
        """
        Try to aggregate a new demand into an existing pool.

        Args:
            new_demand: New demand to aggregate
            similarity_threshold: Threshold for matching

        Returns:
            (Pool joined, whether created new pool)
        """
        existing_pools = self._service_pools.get(new_demand.service_type, [])

        for pool_id in existing_pools:
            pool = self._pools.get(pool_id)
            if not pool or pool.status != PoolStatus.CREATED:
                continue

            similarity = self._calculate_demand_similarity(new_demand, pool)
            if similarity >= similarity_threshold:
                success = await self.join_pool(pool_id, new_demand)
                if success:
                    return pool, False

        new_pool = await self.create_pool(
            creator_id=new_demand.user_id,
            service_type=new_demand.service_type,
            min_budget=self.MIN_POOL_BUDGET,
        )

        await self.join_pool(new_pool.pool_id, new_demand)

        return new_pool, True

    def _calculate_demand_similarity(
        self,
        demand: Demand,
        pool: OrderPool,
    ) -> float:
        """Calculate similarity between demand and pool."""
        if not pool.demands:
            return 0.0

        total_similarity = 0.0
        for pool_demand in pool.demands:
            similarity = self._calculate_single_demand_similarity(demand, pool_demand)
            total_similarity += similarity

        return total_similarity / len(pool.demands)

    def _calculate_single_demand_similarity(
        self,
        demand1: Demand,
        demand2: Demand,
    ) -> float:
        """Calculate similarity between two demands."""
        score = 0.0

        budget_ratio = min(demand1.budget, demand2.budget) / max(demand1.budget, demand2.budget)
        score += budget_ratio * 0.4

        req1 = {str(v) for v in demand1.requirements.values()}
        req2 = {str(v) for v in demand2.requirements.values()}
        if req1 or req2:
            req_similarity = len(req1 & req2) / len(req1 | req2)
            score += req_similarity * 0.4

        if demand1.deadline and demand2.deadline:
            deadline_diff = abs(demand1.deadline - demand2.deadline)
            deadline_similarity = max(0, 1 - deadline_diff / (7 * 86400))
            score += deadline_similarity * 0.2
        else:
            score += 0.1

        return score

    # ==================== Bid Management ====================

    async def submit_bid(
        self,
        pool_id: str,
        provider_id: str,
        price: float,
        delivery_time_hours: int,
        proposal: str,
        reputation_score: float | None = None,
    ) -> Bid | None:
        """
        Submit a bid for a pool.

        Args:
            pool_id: Pool to bid on
            provider_id: Provider making the bid
            price: Bid price
            delivery_time_hours: Promised delivery time
            proposal: Proposal description
            reputation_score: Provider reputation (fetched if not provided)

        Returns:
            Created bid or None
        """
        pool = self._pools.get(pool_id)
        if not pool:
            logger.warning(f"Pool not found: {pool_id}")
            return None

        if pool.status not in [PoolStatus.FUNDED, PoolStatus.BIDDING]:
            logger.warning(f"Pool not in bidding status: {pool.status}")
            return None

        if len(pool.bids) >= self.MAX_BIDS:
            logger.warning(f"Pool has max bids: {pool_id}")
            return None

        if reputation_score is None:
            if self.reputation:
                reputation_score = await self.reputation.get_reputation(provider_id)
            else:
                reputation_score = 0.5

        computed_score = self._calculate_bid_score(
            price=price,
            delivery_time_hours=delivery_time_hours,
            reputation_score=reputation_score,
            pool_budget=pool.total_budget,
        )

        bid_id = f"bid-{uuid.uuid4().hex[:8]}"

        bid = Bid(
            bid_id=bid_id,
            pool_id=pool_id,
            provider_id=provider_id,
            price=price,
            delivery_time_hours=delivery_time_hours,
            reputation_score=reputation_score,
            computed_score=computed_score,
            proposal=proposal,
        )

        pool.bids.append(bid)

        if pool.status == PoolStatus.FUNDED:
            pool.status = PoolStatus.BIDDING

        self._stats.total_bids += 1

        if self.on_bid_submitted:
            self.on_bid_submitted(bid)

        logger.info(f"Bid submitted: {bid_id} for pool {pool_id}")

        return bid

    def _calculate_bid_score(
        self,
        price: float,
        delivery_time_hours: int,
        reputation_score: float,
        pool_budget: float,
    ) -> float:
        """Calculate overall bid score."""
        price_score = pool_budget / price if price > 0 else 0
        price_score = min(price_score, 2.0)

        max_delivery = 168
        time_score = max_delivery / max(delivery_time_hours, 1)
        time_score = min(time_score, 2.0)

        reputation_normalized = reputation_score

        weighted_score = (
            price_score * self.BID_EVAL_WEIGHTS["price"]
            + time_score * self.BID_EVAL_WEIGHTS["delivery_time"]
            + reputation_normalized * self.BID_EVAL_WEIGHTS["reputation"]
        )

        return weighted_score

    async def evaluate_bids(
        self,
        pool_id: str,
    ) -> Bid | None:
        """
        Evaluate bids and select the winner.

        Args:
            pool_id: Pool to evaluate

        Returns:
            Winning bid or None
        """
        pool = self._pools.get(pool_id)
        if not pool or not pool.bids:
            return None

        winning_bid = max(pool.bids, key=lambda b: b.computed_score)

        return winning_bid

    async def award_pool(
        self,
        pool_id: str,
        bid_id: str | None = None,
    ) -> Bid | None:
        """
        Award the pool to a provider.

        Args:
            pool_id: Pool to award
            bid_id: Specific bid to award (auto-select if None)

        Returns:
            Winning bid or None
        """
        pool = self._pools.get(pool_id)
        if not pool:
            return None

        if bid_id:
            winning_bid = next((b for b in pool.bids if b.bid_id == bid_id), None)
        else:
            winning_bid = await self.evaluate_bids(pool_id)

        if not winning_bid:
            return None

        winning_bid.is_winner = True
        pool.winning_bid_id = winning_bid.bid_id
        pool.winning_provider = winning_bid.provider_id
        pool.winning_price = winning_bid.price
        pool.status = PoolStatus.AWARDED

        self._stats.active_pools += 1

        if self.on_pool_awarded:
            self.on_pool_awarded(pool, winning_bid)

        logger.info(f"Pool {pool_id} awarded to {winning_bid.provider_id}")

        return winning_bid

    async def _auto_award_pool(self, pool: OrderPool) -> None:
        """Automatically award a pool to the best bid."""
        if pool.bids:
            await self.award_pool(pool.pool_id)

    # ==================== Status Management ====================

    async def confirm_delivery(
        self,
        pool_id: str,
        user_id: str,
        rating: int,
    ) -> bool:
        """Confirm delivery for a pool."""
        pool = self._pools.get(pool_id)
        if not pool:
            return False

        if rating < 1 or rating > 5:
            return False

        logger.info(f"Delivery confirmed for pool {pool_id} by {user_id}")

        all_confirmed = True
        for demand in pool.demands:
            if demand.status != "confirmed":
                all_confirmed = False
                break

        if all_confirmed:
            pool.status = PoolStatus.COMPLETED
            self._stats.completed_pools += 1
            self._stats.active_pools -= 1
            self._stats.total_volume += pool.winning_price or 0

        return True

    async def raise_dispute(
        self,
        pool_id: str,
        user_id: str,
        reason: str,
    ) -> bool:
        """Raise a dispute for a pool."""
        pool = self._pools.get(pool_id)
        if not pool:
            return False

        pool.status = PoolStatus.DISPUTED
        logger.info(f"Dispute raised for pool {pool_id}")

        return True

    # ==================== Utility Methods ====================

    def get_pool(self, pool_id: str) -> OrderPool | None:
        """Get a pool by ID."""
        return self._pools.get(pool_id)

    def get_pools_by_service(self, service_type: str) -> list[OrderPool]:
        """Get all pools for a service type."""
        pool_ids = self._service_pools.get(service_type, [])
        return [self._pools[pid] for pid in pool_ids if pid in self._pools]

    def get_active_pools(self) -> list[OrderPool]:
        """Get all active pools."""
        return [
            p
            for p in self._pools.values()
            if p.status
            in [PoolStatus.CREATED, PoolStatus.FUNDED, PoolStatus.BIDDING, PoolStatus.AWARDED]
        ]

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        return self._stats.to_dict()


_joint_order_service: JointOrderService | None = None


async def get_joint_order_service() -> JointOrderService:
    """Get or create joint order service instance."""
    global _joint_order_service
    if _joint_order_service is None:
        _joint_order_service = JointOrderService()
        await _joint_order_service.start()
    return _joint_order_service
