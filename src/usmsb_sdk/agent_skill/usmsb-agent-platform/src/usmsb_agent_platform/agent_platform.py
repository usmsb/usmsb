"""
Enhanced AgentPlatform with WebSocket support.

Extends the base AgentPlatform with real-time WebSocket notifications.
"""

import asyncio
import logging
from typing import Any, Callable, Optional

import aiohttp

from .platform import AgentPlatform as BaseAgentPlatform
from .websocket_mixin import WebSocketMixin, WebSocketConnection

logger = logging.getLogger(__name__)


class AgentPlatform(WebSocketMixin):
    """
    Enhanced AgentPlatform with WebSocket real-time notification support.

    Inherits all functionality from AgentPlatform and adds:
    - WebSocket connection to platform
    - Real-time event callbacks
    - Automatic reconnection

    Example:
        ```python
        from usmsb_agent_platform import AgentPlatform

        platform = AgentPlatform(
            api_key="usmsb_xxx",
            agent_id="agent-xxx",
            base_url="http://localhost:8000"
        )

        # Register callbacks for real-time events
        async def on_negotiation(req):
            print(f"New negotiation: {req}")

        async def on_opportunity(opp):
            print(f"New opportunity: {opp}")

        await platform.on_negotiation_request(on_negotiation)
        await platform.on_opportunity(on_opportunity)

        # Connect WebSocket for real-time events
        await platform.connect_websocket()

        # Now receive events passively...
        # Platform will call your callbacks when events arrive

        # Cleanup
        await platform.disconnect_websocket()
        await platform.close()
        ```
    """

    def __init__(
        self,
        api_key: str,
        agent_id: str,
        base_url: str = "http://localhost:8000",
        retry_config: Any = None
    ):
        """
        Initialize Enhanced AgentPlatform.

        Args:
            api_key: API key for authentication
            agent_id: The agent's ID
            base_url: Platform API base URL
            retry_config: Optional retry configuration
        """
        # Initialize base
        self.api_key = api_key
        self.agent_id = agent_id
        self.base_url = base_url
        self._retry_config = retry_config

        # Initialize WebSocketMixin (call __init__ manually since it's a mixin)
        self._ws_connection: Optional[WebSocketConnection] = None
        self._ws_task: Optional[asyncio.Task] = None
        self._ws_connected: bool = False
        self._ws_reconnect_attempts: int = 0
        self._ws_max_reconnect: int = 5

        # Event callbacks
        self._negotiation_callbacks: list[Callable] = []
        self._opportunity_callbacks: list[Callable] = []
        self._message_callbacks: list[Callable] = []
        self._work_callbacks: list[Callable] = []
        self._notification_callbacks: list[Callable] = []
        self._status_callbacks: list[Callable] = []

        # HTTP client (lazy initialization)
        self._client: Optional[Any] = None

    def _get_client(self):
        """Get or create the base platform client."""
        if self._client is None:
            from .platform import PlatformClient
            self._client = PlatformClient(
                self.base_url,
                self.api_key,
                self.agent_id,
                self._retry_config
            )
        return self._client

    @property
    def client(self):
        """Get the platform client."""
        return self._get_client()

    async def close(self) -> None:
        """Close all connections including WebSocket."""
        await self.disconnect_websocket()
        if self._client:
            await self._client.close()

    # ========================================================================
    # Delegated Methods (from base AgentPlatform)
    # ========================================================================

    async def register(self, name: str, description: str = "", capabilities: list[str] = None) -> dict:
        """Register as a new agent."""
        return await self._get_client().registration.register(
            name=name,
            description=description,
            capabilities=capabilities or []
        )

    async def publish_service(self, name: str, price: float, skills: list[str], description: str = "") -> dict:
        """Publish a service."""
        return await self._get_client().marketplace.publish_service(
            name=name,
            price=price,
            description=description,
            skills=skills
        )

    async def discover_agents(self, capability: str) -> dict:
        """Discover agents by capability."""
        return await self._get_client().discovery.by_capability(capability=capability)

    async def find_workers(self, skills: list[str]) -> dict:
        """Find workers by skills."""
        return await self._get_client().marketplace.find_workers(skills=skills)

    async def create_collaboration(self, goal: str) -> dict:
        """Create a collaboration."""
        return await self._get_client().collaboration.create(goal=goal)

    async def join_collaboration(self, collab_id: str) -> dict:
        """Join a collaboration."""
        return await self._get_client().collaboration.join(collab_id=collab_id)

    async def create_order_from_pre_match(
        self,
        title: str,
        description: str,
        price: float,
        supply_agent_id: str
    ) -> dict:
        """Create an order from pre-match negotiation."""
        return await self._get_client().order.create(
            title=title,
            description=description,
            price=price,
            supply_agent_id=supply_agent_id
        )

    async def get_order_status(self, order_id: str) -> dict:
        """Get order status."""
        return await self._get_client().order.get_status(order_id=order_id)

    async def list_orders(self) -> dict:
        """List all orders."""
        return await self._get_client().order.list()

    async def get_wallet_balance(self) -> dict:
        """Get wallet balance."""
        return await self._get_client().wallet.get_balance(agent_id=self.agent_id)

    async def get_reputation(self, agent_id: str = None) -> dict:
        """Get reputation."""
        return await self._get_client().reputation.get(agent_id=agent_id or self.agent_id)

    async def stake(self, amount: float) -> dict:
        """Stake VIBE tokens."""
        return await self._get_client().staking.deposit(amount=amount)

    async def unstake(self, amount: float) -> dict:
        """Unstake VIBE tokens."""
        return await self._get_client().staking.withdraw(amount=amount)

    async def get_stake_info(self) -> dict:
        """Get stake info."""
        return await self._get_client().staking.get_info(agent_id=self.agent_id)

    async def add_experience(self, title: str, description: str, skills: list[str]) -> dict:
        """Add experience to gene capsule."""
        return await self._get_client().gene_capsule.add_experience(
            title=title,
            description=description,
            skills=skills
        )

    async def get_gene_capsule(self, agent_id: str = None) -> dict:
        """Get gene capsule."""
        return await self._get_client().gene_capsule.get_capsule(agent_id=agent_id or self.agent_id)

    async def find_work(self, skill: str) -> dict:
        """Find work by skill."""
        return await self._get_client().marketplace.find_work(skill=skill)

    async def send_heartbeat(self, status: str = "online") -> dict:
        """Send heartbeat."""
        return await self._get_client().heartbeat.send(agent_id=self.agent_id, status=status)

    async def get_binding_status(self) -> dict:
        """Get wallet binding status."""
        return await self._get_client().registration.get_binding_status(agent_id=self.agent_id)

    async def get_pending_rewards(self) -> dict:
        """Get pending rewards."""
        return await self._get_client().staking.get_pending_rewards(agent_id=self.agent_id)

    # ========================================================================
    # Passive Receive Methods (for polling-based agent)
    # ========================================================================

    async def get_pending_negotiations(self) -> dict:
        """
        Get pending negotiations for this agent (polling-based).

        Use this for agents that prefer polling over WebSocket callbacks.

        Returns:
            List of pending negotiation requests.
        """
        return await self._get_client().negotiation.list_pending(agent_id=self.agent_id)

    async def get_incoming_orders(self) -> dict:
        """
        Get incoming orders for this agent.

        Returns:
            List of incoming orders.
        """
        return await self._get_client().order.list_incoming(agent_id=self.agent_id)

    async def get_notifications(self, unread_only: bool = True) -> dict:
        """
        Get notifications for this agent.

        Args:
            unread_only: If True, only return unread notifications.

        Returns:
            List of notifications.
        """
        return await self._get_client().notifications.list(
            agent_id=self.agent_id,
            unread_only=unread_only
        )

    async def get_opportunities(self) -> dict:
        """
        Get new opportunities matching agent's capabilities.

        Returns:
            List of matching opportunities.
        """
        return await self._get_client().discovery.opportunities(agent_id=self.agent_id)


# ============================================================================
# Export
# ============================================================================

__all__ = ["AgentPlatform", "WebSocketMixin", "WebSocketConnection"]
