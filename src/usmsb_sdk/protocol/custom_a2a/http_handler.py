"""
CustomA2A HTTP Handler

Handles HTTP requests to /custom/{path} endpoints.
"""

import json
import logging
from typing import TYPE_CHECKING, Any

from usmsb_sdk.protocol.types.envelope import A2AEnvelope

if TYPE_CHECKING:
    from usmsb_sdk.protocol.custom_a2a.handler import CustomA2AHandler

logger = logging.getLogger(__name__)


class CustomA2AHTTPHandler:
    """
    HTTP Handler for Custom A2A protocol.

    Routes incoming HTTP requests to CustomA2AHandler.handle_envelope().
    """

    def __init__(self, custom_handler: "CustomA2AHandler"):
        self._handler = custom_handler

    async def handle_request(
        self,
        method: str,
        path: str,
        body: bytes,
    ) -> tuple[int, dict[str, Any]]:
        """
        Handle incoming HTTP request.

        Path format: /custom/{message_type}
        Examples:
          /custom/task -> task request
          /custom/query -> query request
          /custom/discovery -> discovery request
        """
        try:
            parts = path.strip("/").split("/")
            if len(parts) < 2 or parts[0] != "custom":
                return 400, {"error": "Invalid path format"}

            message_type = parts[1]

            payload = {}
            if body:
                try:
                    payload = json.loads(body.decode("utf-8"))
                except json.JSONDecodeError:
                    return 400, {"error": "Invalid JSON body"}

            sender_id = payload.pop("_sender_id", "anonymous")

            envelope = A2AEnvelope(
                sender_id=sender_id,
                receiver_id=self._handler.agent_id,
                message_type=message_type,
                payload=payload,
                correlation_id=payload.get("correlation_id", ""),
            )

            response_envelope = await self._handler.handle_envelope(envelope)

            if response_envelope is None:
                return 200, {"status": "accepted"}

            return 200, {
                "sender_id": response_envelope.sender_id,
                "receiver_id": response_envelope.receiver_id,
                "message_type": response_envelope.message_type,
                "payload": response_envelope.payload,
            }

        except Exception as e:
            logger.exception("Error handling custom A2A request")
            return 500, {"error": str(e)}
