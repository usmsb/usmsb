"""
Rate Limiting Middleware for USMSB API

Provides rate limiting based on:
- API Key (per-agent limits)
- IP address (for unauthenticated requests)
- Endpoint-specific limits

Tiers have different rate limits:
- NONE: 10 req/min
- BRONZE: 30 req/min
- SILVER: 60 req/min
- GOLD: 120 req/min
- PLATINUM: 300 req/min
"""

import time
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from usmsb_sdk.api.rest.error_handler import rate_limited_error

# Rate limit configuration per tier (requests per minute)
TIER_RATE_LIMITS = {
    "NONE": 600,       # Increased 10x for development
    "BRONZE": 1200,
    "SILVER": 3000,
    "GOLD": 6000,
    "PLATINUM": 12000,
}

# Burst allowance (extra requests for short bursts)
BURST_ALLOWANCE = 200

# Window size in seconds
WINDOW_SIZE = 60


class RateLimitStore:
    """In-memory rate limit tracking."""

    def __init__(self):
        # Structure: {key: [(timestamp, count), ...]}
        self._requests: dict[str, list] = defaultdict(list)

    def cleanup(self, key: str) -> None:
        """Remove expired entries."""
        now = time.time()
        cutoff = now - WINDOW_SIZE
        self._requests[key] = [
            (ts, count) for ts, count in self._requests[key]
            if ts > cutoff
        ]

    def add_request(self, key: str) -> int:
        """Add a request and return current count in window."""
        now = time.time()
        self.cleanup(key)

        # Add current request
        self._requests[key].append((now, 1))

        # Sum requests in window
        return sum(count for _, count in self._requests[key])

    def get_count(self, key: str) -> int:
        """Get current count in window without adding."""
        self.cleanup(key)
        return sum(count for _, count in self._requests[key])

    def get_remaining(self, key: str, limit: int) -> int:
        """Get remaining requests in window."""
        count = self.get_count(key)
        return max(0, limit - count)

    def get_reset_time(self, key: str) -> float:
        """Get time when window resets."""
        if not self._requests[key]:
            return time.time()

        oldest = min(ts for ts, _ in self._requests[key])
        return oldest + WINDOW_SIZE


class RateLimiter:
    """Rate limiter with tier-based limits."""

    def __init__(self):
        self._store = RateLimitStore()
        self._agent_tiers: dict[str, str] = {}  # Cache agent tiers

    def get_tier_limit(self, tier: str) -> int:
        """Get rate limit for tier."""
        return TIER_RATE_LIMITS.get(tier, TIER_RATE_LIMITS["NONE"])

    def update_agent_tier(self, agent_id: str, tier: str) -> None:
        """Update cached agent tier."""
        self._agent_tiers[agent_id] = tier

    def check_rate_limit(
        self,
        key: str,
        tier: str = "NONE"
    ) -> tuple[bool, int, int, int]:
        """
        Check if request is allowed.

        Returns:
            Tuple of (allowed, remaining, limit, retry_after)
        """
        limit = self.get_tier_limit(tier) + BURST_ALLOWANCE
        count = self._store.add_request(key)
        remaining = max(0, limit - count)

        if count > limit:
            retry_after = int(self._store.get_reset_time(key) - time.time())
            return False, 0, limit, max(1, retry_after)

        return True, remaining, limit, 0

    def get_headers(self, key: str, tier: str) -> dict[str, str]:
        """Get rate limit headers for response."""
        limit = self.get_tier_limit(tier) + BURST_ALLOWANCE
        remaining = self._store.get_remaining(key, limit)
        reset_time = int(self._store.get_reset_time(key))

        return {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time),
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""

    # Paths exempt from rate limiting
    EXEMPT_PATHS = {
        "/",
        "/health",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/redoc",
    }

    # Higher limits for read-only endpoints
    READ_ONLY_PATHS = {
        "/agents",
        "/services",
        "/demands",
        "/network",
    }

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""

        # Skip exempt paths
        path = request.url.path
        if path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Skip OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Get API key and agent ID from headers
        api_key = request.headers.get("X-API-Key")
        agent_id = request.headers.get("X-Agent-ID")

        # Determine rate limit key and tier
        if api_key and agent_id:
            # Authenticated request - use agent_id
            key = f"agent:{agent_id}"
            tier = rate_limiter._agent_tiers.get(agent_id, "NONE")
        else:
            # Unauthenticated request - use IP
            client_ip = self._get_client_ip(request)
            key = f"ip:{client_ip}"
            tier = "NONE"

        # Check rate limit
        allowed, remaining, limit, retry_after = rate_limiter.check_rate_limit(key, tier)

        # Get headers
        headers = rate_limiter.get_headers(key, tier)

        if not allowed:
            # Rate limited
            error = rate_limited_error(retry_after)
            response = JSONResponse(
                status_code=429,
                content=error.to_dict(),
                headers={**headers, "Retry-After": str(retry_after)}
            )
            return response

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        for header_name, header_value in headers.items():
            response.headers[header_name] = header_value

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct client
        if request.client:
            return request.client.host

        return "unknown"


def update_rate_limit_tier(agent_id: str, staked_amount: float) -> None:
    """Update rate limit tier based on stake amount."""
    if staked_amount >= 10000:
        tier = "PLATINUM"
    elif staked_amount >= 5000:
        tier = "GOLD"
    elif staked_amount >= 1000:
        tier = "SILVER"
    elif staked_amount >= 100:
        tier = "BRONZE"
    else:
        tier = "NONE"

    rate_limiter.update_agent_tier(agent_id, tier)
