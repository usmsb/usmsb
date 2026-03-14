"""
Dynamic Pricing Service for AI Civilization Platform

Implements intelligent pricing based on:
1. Supply-demand equilibrium
2. Quality/reputation factor
3. Market momentum
4. Time urgency
5. Service scarcity
6. Historical transaction data
7. Competitive positioning

Core Formula:
    Final Price = Base Price × SupplyDemandFactor × QualityFactor ×
                  MomentumFactor × UrgencyFactor × ScarcityFactor × PositioningFactor
"""

import asyncio
import logging
import math
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class PricingStrategy(StrEnum):
    """Pricing strategy modes."""

    CONSERVATIVE = "conservative"  # Lower prices, faster deals
    BALANCED = "balanced"  # Market equilibrium
    AGGRESSIVE = "aggressive"  # Higher prices, maximize profit
    DYNAMIC = "dynamic"  # Auto-adjust based on conditions
    AUCTION = "auction"  # Competitive bidding


class ServiceCategory(StrEnum):
    """Service categories for scarcity calculation."""

    GENERAL = "general"  # Common services
    SPECIALIZED = "specialized"  # Requires specific skills
    RARE = "rare"  # Few providers available
    UNIQUE = "unique"  # One-of-a-kind capabilities


@dataclass
class MarketSnapshot:
    """Snapshot of market conditions at a point in time."""

    timestamp: float
    service_type: str
    total_suppliers: int
    total_demanders: int
    active_listings: int
    avg_price: float
    min_price: float
    max_price: float
    transaction_volume_24h: float
    price_change_24h: float

    @property
    def supply_demand_ratio(self) -> float:
        """Calculate supply-demand ratio."""
        if self.total_demanders == 0:
            return 1.0
        return self.total_suppliers / self.total_demanders


@dataclass
class PricingFactor:
    """A single factor affecting price."""

    name: str
    value: float  # Multiplier value
    weight: float  # Importance weight
    confidence: float  # How confident we are in this factor
    reasoning: str  # Human-readable explanation

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "value": round(self.value, 4),
            "weight": self.weight,
            "confidence": round(self.confidence, 4),
            "reasoning": self.reasoning,
        }


@dataclass
class PricingResult:
    """Result of pricing calculation."""

    base_price: float
    final_price: float
    price_range: dict[str, float]  # min, max, recommended
    factors: list[PricingFactor]
    market_conditions: dict[str, Any]
    confidence: float
    strategy_used: PricingStrategy
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "basePrice": round(self.base_price, 4),
            "finalPrice": round(self.final_price, 4),
            "priceRange": {
                "min": round(self.price_range.get("min", 0), 4),
                "max": round(self.price_range.get("max", 0), 4),
                "recommended": round(self.price_range.get("recommended", 0), 4),
            },
            "factors": [f.to_dict() for f in self.factors],
            "marketConditions": self.market_conditions,
            "confidence": round(self.confidence, 4),
            "strategyUsed": self.strategy_used.value,
            "timestamp": self.timestamp,
        }


@dataclass
class PriceHistory:
    """Historical price data for analysis."""

    service_type: str
    prices: list[dict[str, Any]]  # [{price, volume, timestamp}, ...]
    avg_price: float
    price_volatility: float
    trend_direction: float  # -1 to 1 (falling to rising)
    last_updated: float

    def add_price(self, price: float, volume: float = 1.0) -> None:
        """Add a price entry."""
        self.prices.append(
            {
                "price": price,
                "volume": volume,
                "timestamp": time.time(),
            }
        )

        if len(self.prices) > 1000:
            self.prices = self.prices[-500:]

        self._recalculate()

    def _recalculate(self) -> None:
        """Recalculate statistics."""
        if not self.prices:
            return

        recent_prices = [p["price"] for p in self.prices[-100:]]
        self.avg_price = sum(recent_prices) / len(recent_prices)

        if len(recent_prices) > 1:
            variance = sum((p - self.avg_price) ** 2 for p in recent_prices) / len(recent_prices)
            self.price_volatility = (
                math.sqrt(variance) / self.avg_price if self.avg_price > 0 else 0
            )

        if len(recent_prices) >= 10:
            old_avg = sum(recent_prices[:10]) / 10
            new_avg = sum(recent_prices[-10:]) / 10
            self.trend_direction = (new_avg - old_avg) / old_avg if old_avg > 0 else 0

        self.last_updated = time.time()


class DynamicPricingService:
    """
    Intelligent Dynamic Pricing Service.

    Features:
    - Multi-factor pricing model
    - Real-time market analysis
    - Supply-demand equilibrium
    - Quality-based adjustments
    - Historical trend analysis
    - Competitive positioning
    - Auction support
    """

    FACTOR_WEIGHTS = {
        "supply_demand": 0.25,
        "quality": 0.20,
        "momentum": 0.15,
        "urgency": 0.15,
        "scarcity": 0.15,
        "positioning": 0.10,
    }

    def __init__(
        self,
        reputation_service=None,
        matching_service=None,
        db_connection=None,
    ):
        """
        Initialize dynamic pricing service.

        Args:
            reputation_service: Service for reputation scores
            matching_service: Service for market data
            db_connection: Database for price history
        """
        self.reputation = reputation_service
        self.matching = matching_service
        self.db = db_connection

        self._market_snapshots: dict[str, MarketSnapshot] = {}
        self._price_history: dict[str, PriceHistory] = {}
        self._service_stats: dict[str, dict[str, Any]] = defaultdict(dict)

        self._running = False
        self._tasks: list[asyncio.Task] = []

        self.on_price_updated: Callable[[str, float], None] | None = None

    async def start(self) -> None:
        """Start background analysis tasks."""
        self._running = True
        self._tasks = [
            asyncio.create_task(self._market_analysis_loop()),
            asyncio.create_task(self._price_history_cleanup_loop()),
        ]
        logger.info("Dynamic pricing service started")

    async def stop(self) -> None:
        """Stop background tasks."""
        self._running = False
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("Dynamic pricing service stopped")

    async def _market_analysis_loop(self) -> None:
        """Periodically analyze market conditions."""
        while self._running:
            try:
                await asyncio.sleep(60)
                await self._analyze_market_conditions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Market analysis error: {e}")

    async def _price_history_cleanup_loop(self) -> None:
        """Clean up old price history entries."""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Every hour
                cutoff = time.time() - (30 * 86400)  # 30 days
                for history in self._price_history.values():
                    history.prices = [p for p in history.prices if p["timestamp"] > cutoff]
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Price history cleanup error: {e}")

    async def _analyze_market_conditions(self) -> None:
        """Analyze current market conditions for all service types."""
        for service_type, _history in list(self._price_history.items()):
            await self._update_market_snapshot(service_type)

    async def _update_market_snapshot(self, service_type: str) -> MarketSnapshot | None:
        """Update market snapshot for a service type."""
        history = self._price_history.get(service_type)
        if not history or not history.prices:
            return None

        recent = [p for p in history.prices if p["timestamp"] > time.time() - 86400]

        if not recent:
            return None

        prices = [p["price"] for p in recent]
        volume = sum(p.get("volume", 1) for p in recent)

        old_prices = [
            p["price"]
            for p in history.prices
            if time.time() - 172800 < p["timestamp"] < time.time() - 86400
        ]
        old_avg = sum(old_prices) / len(old_prices) if old_prices else prices[0]
        new_avg = sum(prices) / len(prices)
        price_change = (new_avg - old_avg) / old_avg if old_avg > 0 else 0

        stats = self._service_stats.get(service_type, {})

        snapshot = MarketSnapshot(
            timestamp=time.time(),
            service_type=service_type,
            total_suppliers=stats.get("suppliers", 1),
            total_demanders=stats.get("demanders", 1),
            active_listings=stats.get("listings", len(recent)),
            avg_price=new_avg,
            min_price=min(prices),
            max_price=max(prices),
            transaction_volume_24h=volume,
            price_change_24h=price_change,
        )

        self._market_snapshots[service_type] = snapshot
        return snapshot

    def update_service_stats(
        self,
        service_type: str,
        suppliers: int = None,
        demanders: int = None,
        listings: int = None,
    ) -> None:
        """Update statistics for a service type."""
        stats = self._service_stats[service_type]
        if suppliers is not None:
            stats["suppliers"] = suppliers
        if demanders is not None:
            stats["demanders"] = demanders
        if listings is not None:
            stats["listings"] = listings

    def record_transaction(
        self,
        service_type: str,
        price: float,
        volume: float = 1.0,
    ) -> None:
        """Record a transaction for price history."""
        if service_type not in self._price_history:
            self._price_history[service_type] = PriceHistory(
                service_type=service_type,
                prices=[],
                avg_price=price,
                price_volatility=0,
                trend_direction=0,
                last_updated=time.time(),
            )

        self._price_history[service_type].add_price(price, volume)

        if self.on_price_updated:
            self.on_price_updated(service_type, price)

    # ==================== Core Pricing Calculation ====================

    async def calculate_price(
        self,
        base_price: float,
        service_type: str,
        supplier_id: str,
        demander_id: str | None = None,
        supplier_reputation: float = 0.5,
        demander_urgency: float = 0.0,
        service_category: ServiceCategory = ServiceCategory.GENERAL,
        strategy: PricingStrategy = PricingStrategy.DYNAMIC,
        context: dict[str, Any] | None = None,
    ) -> PricingResult:
        """
        Calculate intelligent price based on multiple factors.

        Args:
            base_price: Base/reference price for the service
            service_type: Type of service being priced
            supplier_id: ID of the service provider
            demander_id: ID of the service requester
            supplier_reputation: Reputation score of supplier (0-1)
            demander_urgency: How urgent is the request (0-1)
            service_category: Category affecting scarcity
            strategy: Pricing strategy to use
            context: Additional context for pricing

        Returns:
            PricingResult with final price and all factor breakdowns
        """
        factors: list[PricingFactor] = []
        context = context or {}

        factor_1 = await self._calculate_supply_demand_factor(service_type, context)
        factors.append(factor_1)

        factor_2 = self._calculate_quality_factor(supplier_reputation, context)
        factors.append(factor_2)

        factor_3 = await self._calculate_momentum_factor(service_type, context)
        factors.append(factor_3)

        factor_4 = self._calculate_urgency_factor(demander_urgency, context)
        factors.append(factor_4)

        factor_5 = self._calculate_scarcity_factor(service_type, service_category, context)
        factors.append(factor_5)

        factor_6 = await self._calculate_positioning_factor(
            base_price, service_type, supplier_reputation, strategy, context
        )
        factors.append(factor_6)

        total_weighted_value = sum(f.value * f.weight * f.confidence for f in factors)
        total_weight = sum(f.weight * f.confidence for f in factors)

        combined_multiplier = total_weighted_value / total_weight if total_weight > 0 else 1.0

        if strategy == PricingStrategy.CONSERVATIVE:
            combined_multiplier *= 0.9
        elif strategy == PricingStrategy.AGGRESSIVE:
            combined_multiplier *= 1.15
        elif strategy == PricingStrategy.AUCTION:
            combined_multiplier *= 1.0 + (demander_urgency * 0.3)

        final_price = base_price * combined_multiplier

        min_price = base_price * 0.5
        max_price = base_price * 2.0

        if factor_1.value < 0.8:
            max_price = base_price * 1.5
        elif factor_1.value > 1.2:
            min_price = base_price * 0.8

        if history := self._price_history.get(service_type):
            min_price = max(min_price, history.avg_price * 0.6)
            max_price = min(max_price, history.avg_price * 1.8)

        final_price = max(min_price, min(final_price, max_price))

        confidence = sum(f.confidence for f in factors) / len(factors)

        market_conditions = self._get_market_conditions_summary(service_type)

        result = PricingResult(
            base_price=base_price,
            final_price=final_price,
            price_range={
                "min": min_price,
                "max": max_price,
                "recommended": final_price,
            },
            factors=factors,
            market_conditions=market_conditions,
            confidence=confidence,
            strategy_used=strategy,
        )

        logger.debug(
            f"Calculated price for {service_type}: "
            f"{base_price:.2f} -> {final_price:.2f} "
            f"(factor: {combined_multiplier:.3f})"
        )

        return result

    # ==================== Factor Calculations ====================

    async def _calculate_supply_demand_factor(
        self,
        service_type: str,
        context: dict[str, Any],
    ) -> PricingFactor:
        """
        Calculate supply-demand factor.

        Formula: Factor = (Demand / Supply)^0.5

        - Ratio > 1: More demand than supply -> Higher prices
        - Ratio < 1: More supply than demand -> Lower prices
        - Ratio = 1: Balanced market -> Neutral prices
        """
        snapshot = self._market_snapshots.get(service_type)

        if not snapshot:
            stats = self._service_stats.get(service_type, {})
            suppliers = stats.get("suppliers", 1)
            demanders = stats.get("demanders", 1)
        else:
            suppliers = max(snapshot.total_suppliers, 1)
            demanders = snapshot.total_demanders

        if suppliers > 0 and demanders > 0:
            ratio = demanders / suppliers
        elif demanders > 0:
            ratio = 2.0  # High demand, no supply
        else:
            ratio = 0.5  # Low demand

        factor_value = math.pow(ratio, 0.5)

        factor_value = max(0.5, min(factor_value, 2.0))

        if ratio > 1.5:
            reasoning = f"High demand ({demanders}) vs low supply ({suppliers}): premium pricing"
        elif ratio < 0.67:
            reasoning = (
                f"Low demand ({demanders}) vs high supply ({suppliers}): competitive pricing"
            )
        else:
            reasoning = f"Balanced market: {demanders} demanders, {suppliers} suppliers"

        return PricingFactor(
            name="supply_demand",
            value=factor_value,
            weight=self.FACTOR_WEIGHTS["supply_demand"],
            confidence=0.8 if snapshot else 0.5,
            reasoning=reasoning,
        )

    def _calculate_quality_factor(
        self,
        reputation: float,
        context: dict[str, Any],
    ) -> PricingFactor:
        """
        Calculate quality factor based on reputation.

        Higher reputation -> Higher justified price
        Uses sigmoid function for smooth scaling
        """
        reputation = max(0, min(1, reputation))

        quality_score = 0.8 + 0.4 * reputation

        if reputation >= 0.9:
            reasoning = "Excellent reputation (top 10%): premium quality premium"
        elif reputation >= 0.75:
            reasoning = "Strong reputation: quality premium applied"
        elif reputation >= 0.5:
            reasoning = "Average reputation: standard pricing"
        elif reputation >= 0.3:
            reasoning = "Below average reputation: discount applied"
        else:
            reasoning = "Low reputation: significant discount for risk"

        return PricingFactor(
            name="quality",
            value=quality_score,
            weight=self.FACTOR_WEIGHTS["quality"],
            confidence=0.9,
            reasoning=reasoning,
        )

    async def _calculate_momentum_factor(
        self,
        service_type: str,
        context: dict[str, Any],
    ) -> PricingFactor:
        """
        Calculate market momentum factor.

        Based on recent price trends:
        - Rising prices -> Buyers expect higher prices, accept them
        - Falling prices -> Buyers expect lower prices, negotiate harder
        """
        history = self._price_history.get(service_type)

        if not history or len(history.prices) < 10:
            return PricingFactor(
                name="momentum",
                value=1.0,
                weight=self.FACTOR_WEIGHTS["momentum"],
                confidence=0.3,
                reasoning="Insufficient history: neutral momentum",
            )

        trend = history.trend_direction

        momentum_factor = 1.0 + (trend * 0.3)
        momentum_factor = max(0.85, min(momentum_factor, 1.15))

        if trend > 0.1:
            reasoning = f"Rising market (+{trend * 100:.1f}%): price increase momentum"
        elif trend < -0.1:
            reasoning = f"Falling market ({trend * 100:.1f}%): price decrease momentum"
        else:
            reasoning = "Stable market: no strong momentum"

        return PricingFactor(
            name="momentum",
            value=momentum_factor,
            weight=self.FACTOR_WEIGHTS["momentum"],
            confidence=min(0.9, 0.5 + history.price_volatility * 2),
            reasoning=reasoning,
        )

    def _calculate_urgency_factor(
        self,
        urgency: float,
        context: dict[str, Any],
    ) -> PricingFactor:
        """
        Calculate urgency factor.

        High urgency from demander -> Higher willingness to pay
        Urgency range: 0 (no rush) to 1 (critical)
        """
        urgency = max(0, min(1, urgency))

        deadline_hours = context.get("deadline_hours")
        if deadline_hours is not None:
            if deadline_hours < 24:
                urgency = max(urgency, 0.8)
            elif deadline_hours < 72:
                urgency = max(urgency, 0.5)

        urgency_factor = 1.0 + (urgency * 0.5)

        if urgency >= 0.8:
            reasoning = "Critical urgency: rush premium applied"
        elif urgency >= 0.5:
            reasoning = "High urgency: moderate premium"
        elif urgency >= 0.2:
            reasoning = "Some urgency: slight premium"
        else:
            reasoning = "No urgency: standard pricing"

        return PricingFactor(
            name="urgency",
            value=urgency_factor,
            weight=self.FACTOR_WEIGHTS["urgency"],
            confidence=0.7,
            reasoning=reasoning,
        )

    def _calculate_scarcity_factor(
        self,
        service_type: str,
        category: ServiceCategory,
        context: dict[str, Any],
    ) -> PricingFactor:
        """
        Calculate scarcity factor.

        Based on how rare the service is:
        - General: Many providers, competitive
        - Specialized: Fewer providers, moderate premium
        - Rare: Very few providers, significant premium
        - Unique: One-of-a-kind, high premium
        """
        base_factors = {
            ServiceCategory.GENERAL: 0.95,
            ServiceCategory.SPECIALIZED: 1.10,
            ServiceCategory.RARE: 1.30,
            ServiceCategory.UNIQUE: 1.50,
        }

        scarcity_factor = base_factors.get(category, 1.0)

        stats = self._service_stats.get(service_type, {})
        providers = stats.get("suppliers", 0)

        if providers <= 1:
            scarcity_factor *= 1.2
        elif providers <= 3:
            scarcity_factor *= 1.1
        elif providers <= 10:
            scarcity_factor *= 1.0
        else:
            scarcity_factor *= 0.95

        scarcity_factor = max(0.9, min(scarcity_factor, 1.8))

        category_names = {
            ServiceCategory.GENERAL: "common",
            ServiceCategory.SPECIALIZED: "specialized",
            ServiceCategory.RARE: "rare",
            ServiceCategory.UNIQUE: "unique",
        }

        reasoning = f"{category_names.get(category, 'unknown')} service ({providers} providers): "
        reasoning += "scarcity premium" if scarcity_factor > 1.05 else "competitive market"

        return PricingFactor(
            name="scarcity",
            value=scarcity_factor,
            weight=self.FACTOR_WEIGHTS["scarcity"],
            confidence=0.75,
            reasoning=reasoning,
        )

    async def _calculate_positioning_factor(
        self,
        base_price: float,
        service_type: str,
        reputation: float,
        strategy: PricingStrategy,
        context: dict[str, Any],
    ) -> PricingFactor:
        """
        Calculate competitive positioning factor.

        Compares base price with market average and adjusts
        based on desired positioning strategy.
        """
        history = self._price_history.get(service_type)

        if not history or history.avg_price == 0:
            return PricingFactor(
                name="positioning",
                value=1.0,
                weight=self.FACTOR_WEIGHTS["positioning"],
                confidence=0.3,
                reasoning="No market benchmark: neutral positioning",
            )

        market_avg = history.avg_price
        price_ratio = base_price / market_avg

        if strategy == PricingStrategy.CONSERVATIVE:
            if price_ratio > 1.0:
                positioning = 1.0 - ((price_ratio - 1.0) * 0.3)
            else:
                positioning = 1.0
            reasoning = "Conservative strategy: price aligned with market"

        elif strategy == PricingStrategy.AGGRESSIVE:
            if reputation > 0.7:
                positioning = 1.0 + (reputation - 0.5) * 0.3
            else:
                positioning = 1.0
            reasoning = "Aggressive strategy: premium positioning for high reputation"

        elif strategy == PricingStrategy.AUCTION:
            positioning = 1.0 + (reputation * 0.2)
            reasoning = "Auction strategy: reputation-weighted positioning"

        else:
            positioning = 1.0
            reasoning = f"Market average: {market_avg:.2f}, base price: {base_price:.2f}"

        positioning = max(0.85, min(positioning, 1.25))

        return PricingFactor(
            name="positioning",
            value=positioning,
            weight=self.FACTOR_WEIGHTS["positioning"],
            confidence=0.85 if history else 0.4,
            reasoning=reasoning,
        )

    # ==================== Utility Methods ====================

    def _get_market_conditions_summary(self, service_type: str) -> dict[str, Any]:
        """Get summary of current market conditions."""
        snapshot = self._market_snapshots.get(service_type)
        history = self._price_history.get(service_type)

        return {
            "serviceType": service_type,
            "hasMarketData": snapshot is not None,
            "avgPrice": history.avg_price if history else None,
            "priceVolatility": history.price_volatility if history else None,
            "trend": history.trend_direction if history else None,
            "supplyDemandRatio": snapshot.supply_demand_ratio if snapshot else None,
            "volume24h": snapshot.transaction_volume_24h if snapshot else None,
        }

    def get_price_recommendation(
        self,
        service_type: str,
        target_position: str = "market",  # "budget", "market", "premium"
    ) -> dict[str, Any] | None:
        """Get price recommendation for a service type."""
        history = self._price_history.get(service_type)

        if not history or history.avg_price == 0:
            return None

        base = history.avg_price

        if target_position == "budget":
            return {
                "recommended": base * 0.8,
                "range": {"min": base * 0.6, "max": base * 0.9},
                "positioning": "Below market - competitive pricing",
            }
        elif target_position == "premium":
            return {
                "recommended": base * 1.25,
                "range": {"min": base * 1.1, "max": base * 1.5},
                "positioning": "Above market - premium positioning",
            }
        else:
            return {
                "recommended": base,
                "range": {"min": base * 0.9, "max": base * 1.1},
                "positioning": "Market-aligned pricing",
            }

    def get_statistics(self) -> dict[str, Any]:
        """Get pricing service statistics."""
        return {
            "trackedServiceTypes": len(self._price_history),
            "marketSnapshots": len(self._market_snapshots),
            "totalTransactions": sum(len(h.prices) for h in self._price_history.values()),
            "serviceStats": dict(self._service_stats),
        }

    def get_service_price_history(
        self,
        service_type: str,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """Get price history for a service type."""
        history = self._price_history.get(service_type)

        if not history:
            return []

        cutoff = time.time() - (days * 86400)
        return [p for p in history.prices if p["timestamp"] > cutoff]


_dynamic_pricing_service: DynamicPricingService | None = None


async def get_dynamic_pricing_service() -> DynamicPricingService:
    """Get or create dynamic pricing service instance."""
    global _dynamic_pricing_service
    if _dynamic_pricing_service is None:
        _dynamic_pricing_service = DynamicPricingService()
        await _dynamic_pricing_service.start()
    return _dynamic_pricing_service
