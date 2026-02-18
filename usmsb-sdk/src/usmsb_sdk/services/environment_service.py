"""
Environment Broadcast Service for AI Civilization Platform

Provides real-time environment state updates:
- Market conditions
- Agent activity
- Transaction statistics
- Trend analysis
- Personalized notifications
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class BroadcastType(str, Enum):
    """Types of broadcast messages."""
    ENVIRONMENT_UPDATE = "environment_update"
    MARKET_CHANGE = "market_change"
    NEW_OPPORTUNITY = "new_opportunity"
    PRICE_ALERT = "price_alert"
    TREND_NOTIFICATION = "trend_notification"
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    AGENT_ONLINE = "agent_online"
    AGENT_OFFLINE = "agent_offline"
    TRANSACTION_COMPLETE = "transaction_complete"
    DEMAND_CREATED = "demand_created"
    SERVICE_CREATED = "service_created"


@dataclass
class BroadcastMessage:
    """A broadcast message."""
    broadcast_type: BroadcastType
    sender_id: str
    sender_name: str
    content: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    priority: int = 0  # Higher = more important
    target_agents: Optional[List[str]] = None  # None = broadcast to all

    def to_dict(self) -> Dict[str, Any]:
        return {
            "broadcastType": self.broadcast_type.value,
            "senderId": self.sender_id,
            "senderName": self.sender_name,
            "content": self.content,
            "timestamp": self.timestamp,
            "priority": self.priority,
            "targetAgents": self.target_agents,
        }


@dataclass
class EnvironmentState:
    """Current state of the platform environment."""
    # Market metrics
    total_supply_listings: int = 0
    total_demand_listings: int = 0
    supply_demand_ratio: float = 1.0
    average_price: float = 0.0
    price_trend: str = "stable"  # "rising", "falling", "stable"

    # Agent metrics
    total_agents: int = 0
    active_agents: int = 0
    human_agents: int = 0
    ai_agents: int = 0
    external_agents: int = 0

    # Transaction metrics
    total_transactions: int = 0
    pending_transactions: int = 0
    completed_today: int = 0
    transaction_volume_24h: float = 0.0
    success_rate: float = 0.95

    # Trending data
    hot_skills: List[str] = field(default_factory=list)
    hot_categories: List[str] = field(default_factory=list)
    trending_tags: List[str] = field(default_factory=list)

    # Timestamp
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market": {
                "totalSupplyListings": self.total_supply_listings,
                "totalDemandListings": self.total_demand_listings,
                "supplyDemandRatio": round(self.supply_demand_ratio, 2),
                "averagePrice": round(self.average_price, 2),
                "priceTrend": self.price_trend,
            },
            "agents": {
                "total": self.total_agents,
                "active": self.active_agents,
                "human": self.human_agents,
                "ai": self.ai_agents,
                "external": self.external_agents,
            },
            "transactions": {
                "total": self.total_transactions,
                "pending": self.pending_transactions,
                "completedToday": self.completed_today,
                "volume24h": round(self.transaction_volume_24h, 2),
                "successRate": round(self.success_rate, 2),
            },
            "trends": {
                "hotSkills": self.hot_skills[:10],
                "hotCategories": self.hot_categories[:5],
                "trendingTags": self.trending_tags[:10],
            },
            "lastUpdated": self.last_updated,
        }


@dataclass
class PriceAlert:
    """A price alert configuration."""
    agent_id: str
    skill: Optional[str] = None
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    change_threshold: Optional[float] = None  # Percentage change
    enabled: bool = True


@dataclass
class AgentSubscription:
    """An agent's broadcast subscriptions."""
    agent_id: str
    subscribed_types: Set[BroadcastType] = field(default_factory=set)
    price_alerts: List[PriceAlert] = field(default_factory=list)
    subscribed_skills: List[str] = field(default_factory=list)
    notification_preferences: Dict[str, bool] = field(default_factory=dict)


class EnvironmentBroadcastService:
    """
    Environment Broadcast Service.

    Collects platform state and broadcasts updates to agents.
    """

    # Update intervals
    ENVIRONMENT_UPDATE_INTERVAL = 60.0  # seconds
    MARKET_CHECK_INTERVAL = 30.0
    TREND_UPDATE_INTERVAL = 300.0  # 5 minutes

    def __init__(self, db_connection=None, metrics_collector=None):
        """
        Initialize the service.

        Args:
            db_connection: Database for querying data
            metrics_collector: Service for collecting metrics
        """
        self.db = db_connection
        self.metrics = metrics_collector

        # Current state
        self._state = EnvironmentState()
        self._previous_state: Optional[EnvironmentState] = None

        # Subscriptions
        self._subscriptions: Dict[str, AgentSubscription] = {}

        # Callbacks for broadcast
        self._broadcast_callback: Optional[Callable[[BroadcastMessage], None]] = None

        # Background tasks
        self._running = False
        self._tasks: List[asyncio.Task] = []

        # Price history for alerts
        self._price_history: Dict[str, List[float]] = {}

    def set_broadcast_callback(self, callback: Callable[[BroadcastMessage], None]) -> None:
        """Set the callback for broadcasting messages."""
        self._broadcast_callback = callback

    async def start(self) -> None:
        """Start background tasks."""
        if self._running:
            return

        self._running = True

        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._environment_update_loop()),
            asyncio.create_task(self._market_check_loop()),
            asyncio.create_task(self._trend_update_loop()),
        ]

        logger.info("Environment broadcast service started")

    async def stop(self) -> None:
        """Stop background tasks."""
        self._running = False

        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks = []
        logger.info("Environment broadcast service stopped")

    async def _environment_update_loop(self) -> None:
        """Periodically update and broadcast environment state."""
        while self._running:
            try:
                await asyncio.sleep(self.ENVIRONMENT_UPDATE_INTERVAL)
                await self._collect_and_broadcast_environment()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Environment update error: {e}")

    async def _market_check_loop(self) -> None:
        """Check for market changes and price alerts."""
        while self._running:
            try:
                await asyncio.sleep(self.MARKET_CHECK_INTERVAL)
                await self._check_market_changes()
                await self._check_price_alerts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Market check error: {e}")

    async def _trend_update_loop(self) -> None:
        """Update trending data."""
        while self._running:
            try:
                await asyncio.sleep(self.TREND_UPDATE_INTERVAL)
                await self._update_trends()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Trend update error: {e}")

    async def _collect_and_broadcast_environment(self) -> None:
        """Collect environment data and broadcast update."""
        # Store previous state
        self._previous_state = self._state

        # Collect new state
        await self._collect_environment_state()

        # Broadcast update
        await self.broadcast(
            broadcast_type=BroadcastType.ENVIRONMENT_UPDATE,
            sender_id="environment_service",
            sender_name="Environment Service",
            content=self._state.to_dict(),
        )

        logger.debug("Environment state updated and broadcasted")

    async def _collect_environment_state(self) -> None:
        """Collect current environment state from database."""
        if not self.db:
            # Use mock data if no database
            self._collect_mock_state()
            return

        try:
            # Get metrics from database
            # This would be replaced with actual database queries
            cursor = self.db.cursor()

            # Agent counts
            cursor.execute("SELECT COUNT(*) FROM agents")
            self._state.total_agents = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM ai_agents WHERE status = 'online'")
            self._state.active_agents = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM agents WHERE type = 'human'")
            self._state.human_agents = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM agents WHERE type = 'ai_agent'")
            self._state.ai_agents = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM agents WHERE type = 'external'")
            self._state.external_agents = cursor.fetchone()[0]

            # Listings
            cursor.execute("SELECT COUNT(*) FROM services WHERE status = 'active'")
            self._state.total_supply_listings = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM demands WHERE status = 'active'")
            self._state.total_demand_listings = cursor.fetchone()[0]

            # Transactions
            cursor.execute("SELECT COUNT(*) FROM transactions WHERE status = 'completed'")
            self._state.total_transactions = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) FROM transactions
                WHERE status IN ('created', 'escrowed', 'in_progress')
            """)
            self._state.pending_transactions = cursor.fetchone()[0]

            # Calculate ratios
            if self._state.total_demand_listings > 0:
                self._state.supply_demand_ratio = (
                    self._state.total_supply_listings / self._state.total_demand_listings
                )

            self._state.last_updated = time.time()

        except Exception as e:
            logger.error(f"Error collecting environment state: {e}")
            self._collect_mock_state()

    def _collect_mock_state(self) -> None:
        """Collect mock state for testing."""
        import random

        self._state.total_agents = 100 + random.randint(-10, 10)
        self._state.active_agents = int(self._state.total_agents * 0.7)
        self._state.human_agents = int(self._state.total_agents * 0.3)
        self._state.ai_agents = int(self._state.total_agents * 0.5)
        self._state.external_agents = int(self._state.total_agents * 0.2)

        self._state.total_supply_listings = 50 + random.randint(-5, 5)
        self._state.total_demand_listings = 30 + random.randint(-3, 3)

        if self._state.total_demand_listings > 0:
            self._state.supply_demand_ratio = (
                self._state.total_supply_listings / self._state.total_demand_listings
            )

        self._state.average_price = 100 + random.uniform(-10, 10)

        self._state.total_transactions = 500 + random.randint(-50, 50)
        self._state.pending_transactions = 10 + random.randint(-2, 2)
        self._state.completed_today = 25 + random.randint(-5, 5)
        self._state.transaction_volume_24h = 10000 + random.uniform(-1000, 1000)

        self._state.hot_skills = [
            "AI Development", "Web3", "Data Science",
            "UI/UX Design", "Blockchain", "Smart Contracts",
            "Machine Learning", "Cloud Architecture", "DevOps",
            "Mobile Development"
        ]
        self._state.hot_categories = [
            "AI Services", "Development", "Consulting",
            "Design", "Security"
        ]
        self._state.trending_tags = [
            "#AI", "#Web3", "#DeFi", "#NFT", "#Metaverse",
            "#Blockchain", "#SmartContracts", "#DAO", "#GPT",
            "#Automation"
        ]

        self._state.last_updated = time.time()

    async def _check_market_changes(self) -> None:
        """Check for significant market changes."""
        if not self._previous_state:
            return

        # Check supply/demand ratio change
        ratio_change = abs(
            self._state.supply_demand_ratio - self._previous_state.supply_demand_ratio
        )
        if ratio_change > 0.2:
            await self.broadcast(
                broadcast_type=BroadcastType.MARKET_CHANGE,
                sender_id="environment_service",
                sender_name="Market Monitor",
                content={
                    "changeType": "supply_demand_ratio",
                    "previousValue": self._previous_state.supply_demand_ratio,
                    "currentValue": self._state.supply_demand_ratio,
                    "changePercent": ratio_change / self._previous_state.supply_demand_ratio * 100,
                },
                priority=2,
            )

        # Check price trend
        price_change = abs(self._state.average_price - self._previous_state.average_price)
        if price_change > 0:
            change_percent = price_change / self._previous_state.average_price * 100
            if change_percent > 10:
                self._state.price_trend = "rising" if self._state.average_price > self._previous_state.average_price else "falling"
                await self.broadcast(
                    broadcast_type=BroadcastType.PRICE_ALERT,
                    sender_id="environment_service",
                    sender_name="Price Monitor",
                    content={
                        "alertType": "significant_change",
                        "previousPrice": self._previous_state.average_price,
                        "currentPrice": self._state.average_price,
                        "changePercent": change_percent,
                        "trend": self._state.price_trend,
                    },
                    priority=3,
                )

    async def _check_price_alerts(self) -> None:
        """Check and trigger price alerts for subscribed agents."""
        # This would check each agent's price alert configurations
        pass

    async def _update_trends(self) -> None:
        """Update trending skills and categories."""
        # This would analyze recent activity to determine trends
        pass

    # ==================== Public API ====================

    async def broadcast(
        self,
        broadcast_type: BroadcastType,
        sender_id: str,
        sender_name: str,
        content: Dict[str, Any],
        priority: int = 0,
        target_agents: Optional[List[str]] = None,
    ) -> None:
        """
        Broadcast a message to relevant agents.
        """
        message = BroadcastMessage(
            broadcast_type=broadcast_type,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            priority=priority,
            target_agents=target_agents,
        )

        if self._broadcast_callback:
            await self._broadcast_callback(message)
        else:
            logger.warning(f"No broadcast callback set, message not sent: {broadcast_type}")

    async def notify_opportunity(
        self,
        agent_id: str,
        opportunity: Dict[str, Any],
    ) -> None:
        """Notify an agent of a new opportunity."""
        await self.broadcast(
            broadcast_type=BroadcastType.NEW_OPPORTUNITY,
            sender_id="matching_service",
            sender_name="Matching Service",
            content=opportunity,
            priority=2,
            target_agents=[agent_id],
        )

    async def broadcast_agent_online(self, agent_id: str, agent_name: str) -> None:
        """Broadcast that an agent came online."""
        await self.broadcast(
            broadcast_type=BroadcastType.AGENT_ONLINE,
            sender_id=agent_id,
            sender_name=agent_name,
            content={"agentId": agent_id, "agentName": agent_name},
            priority=1,
        )

    async def broadcast_agent_offline(self, agent_id: str, agent_name: str) -> None:
        """Broadcast that an agent went offline."""
        await self.broadcast(
            broadcast_type=BroadcastType.AGENT_OFFLINE,
            sender_id=agent_id,
            sender_name=agent_name,
            content={"agentId": agent_id, "agentName": agent_name},
            priority=1,
        )

    async def broadcast_transaction_complete(
        self,
        buyer_id: str,
        seller_id: str,
        transaction_id: str,
        amount: float,
    ) -> None:
        """Broadcast a completed transaction."""
        await self.broadcast(
            broadcast_type=BroadcastType.TRANSACTION_COMPLETE,
            sender_id="transaction_service",
            sender_name="Transaction Service",
            content={
                "transactionId": transaction_id,
                "amount": amount,
            },
            priority=2,
            target_agents=[buyer_id, seller_id],
        )

    def subscribe_agent(
        self,
        agent_id: str,
        broadcast_types: List[BroadcastType] = None,
        skills: List[str] = None,
    ) -> AgentSubscription:
        """Subscribe an agent to broadcasts."""
        subscription = AgentSubscription(
            agent_id=agent_id,
            subscribed_types=set(broadcast_types) if broadcast_types else set(BroadcastType),
            subscribed_skills=skills or [],
        )
        self._subscriptions[agent_id] = subscription
        logger.info(f"Agent {agent_id} subscribed to broadcasts")
        return subscription

    def unsubscribe_agent(self, agent_id: str) -> None:
        """Unsubscribe an agent from broadcasts."""
        if agent_id in self._subscriptions:
            del self._subscriptions[agent_id]
            logger.info(f"Agent {agent_id} unsubscribed from broadcasts")

    def add_price_alert(self, agent_id: str, alert: PriceAlert) -> None:
        """Add a price alert for an agent."""
        if agent_id not in self._subscriptions:
            self.subscribe_agent(agent_id)
        self._subscriptions[agent_id].price_alerts.append(alert)

    def get_state(self) -> EnvironmentState:
        """Get current environment state."""
        return self._state

    def get_agent_subscription(self, agent_id: str) -> Optional[AgentSubscription]:
        """Get an agent's subscription."""
        return self._subscriptions.get(agent_id)


# Global instance
_environment_service: Optional[EnvironmentBroadcastService] = None


async def get_environment_service() -> EnvironmentBroadcastService:
    """Get or create environment service instance."""
    global _environment_service
    if _environment_service is None:
        _environment_service = EnvironmentBroadcastService()
        await _environment_service.start()
    return _environment_service
