"""
Request Tracing Middleware for USMSB API

Provides:
- Request ID generation and tracking
- Request timing
- Structured logging

Headers:
- X-Request-ID: Unique identifier for each request
- X-Response-Time: Request processing time in milliseconds
"""

import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracing and logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tracing."""

        # Generate or get request ID
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store request ID in state
        request.state.request_id = request_id

        # Record start time
        start_time = time.time()

        # Log incoming request
        await self._log_request(request, request_id)

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {request_id} "
                f"{request.method} {request.url.path} "
                f"duration={duration_ms:.2f}ms error={str(e)}"
            )
            raise

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Add headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        # Log response
        self._log_response(request, response, request_id, duration_ms)

        return response

    async def _log_request(self, request: Request, request_id: str) -> None:
        """Log incoming request."""
        # Get agent info if available
        agent_id = request.headers.get("X-Agent-ID", "anonymous")

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Log basic request info
        logger.info(
            f"Request started: {request_id} "
            f"{request.method} {request.url.path} "
            f"agent={agent_id} ip={client_ip}"
        )

    def _log_response(
        self,
        request: Request,
        response: Response,
        request_id: str,
        duration_ms: float
    ) -> None:
        """Log outgoing response."""
        agent_id = request.headers.get("X-Agent-ID", "anonymous")

        # Determine log level based on status code
        status_code = response.status_code
        if status_code < 400:
            log_func = logger.info
        elif status_code < 500:
            log_func = logger.warning
        else:
            log_func = logger.error

        log_func(
            f"Request completed: {request_id} "
            f"{request.method} {request.url.path} "
            f"status={status_code} duration={duration_ms:.2f}ms "
            f"agent={agent_id}"
        )

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        if request.client:
            return request.client.host

        return "unknown"


def get_request_id(request: Request) -> str:
    """Get request ID from request state."""
    return getattr(request.state, "request_id", str(uuid.uuid4()))


class RequestContext:
    """Context manager for request-scoped data."""

    _current_request_id: str = ""

    @classmethod
    def set_request_id(cls, request_id: str) -> None:
        """Set current request ID."""
        cls._current_request_id = request_id

    @classmethod
    def get_request_id(cls) -> str:
        """Get current request ID."""
        return cls._current_request_id or str(uuid.uuid4())

    @classmethod
    def clear(cls) -> None:
        """Clear context."""
        cls._current_request_id = ""
