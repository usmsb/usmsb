"""
CustomA2A Transport Adapter

Handles actual network transmission for Custom A2A messages.
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx
    from usmsb_sdk.protocol.types.envelope import A2AEnvelope

logger = logging.getLogger(__name__)


class CustomA2ATransport:
    """
    Transport adapter for Custom A2A.

    Supports:
    - HTTP transport (via HTTPClient)
    - Internal queue (for same-process agents)
    """

    def __init__(
        self,
        agent_id: str,
        http_client: "httpx.AsyncClient | None" = None,
        peer_registry: dict[str, str] | None = None,
    ):
        self._agent_id = agent_id
        self._http_client = http_client
        self._peer_registry = peer_registry or {}

    def register_peer(self, agent_id: str, url: str) -> None:
        """Register a peer agent's HTTP URL."""
        self._peer_registry[agent_id] = url

    def unregister_peer(self, agent_id: str) -> None:
        """Unregister a peer agent."""
        self._peer_registry.pop(agent_id, None)

    async def send(self, envelope: "A2AEnvelope") -> bool:
        """Send an envelope to its destination."""
        receiver = envelope.receiver_id

        if self._http_client and receiver in self._peer_registry:
            url = f"{self._peer_registry[receiver]}/custom/{envelope.message_type}"
            try:
                await self._http_client.post(
                    url,
                    json=envelope.model_dump(),
                    headers={"Content-Type": "application/json"},
                )
                logger.debug(f"Sent envelope to {receiver} at {url}")
                return True
            except Exception as e:
                logger.warning(f"Failed to send to {receiver} via HTTP: {e}")

        # No transport configured - log only
        logger.debug(f"Would send to {receiver}: {envelope.message_type}")
        return False
