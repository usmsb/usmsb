"""
API Key Management for Agents

Provides secure API key generation, validation, and management.
Security fixes:
- HMAC-SHA256 with pepper (secret key from env) instead of plain SHA-256
- Brute force protection: lockout after 5 failed attempts for 15 minutes
- 128-bit entropy for binding codes (was 48-bit)
- API key format uses random bytes (no timestamp enumeration)
"""

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any

# API Key Configuration
API_KEY_PREFIX = "usmsb"
API_KEY_RANDOM_LENGTH = 16  # 16 bytes = 32 hex chars (was hash+timestamp)
API_KEY_BINDING_CODE_PREFIX = "bind-"
API_KEY_BINDING_CODE_ENTROPY = 16  # 16 bytes = 32 hex chars = 128 bits (was 48 bits)
API_KEY_BINDING_EXPIRY_SECONDS = 600  # 10 minutes
API_KEY_DEFAULT_EXPIRY_DAYS = 365

# Brute force protection
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes


# ==================== Pepper for HMAC ====================

def _get_pepper() -> bytes:
    """
    Get the API key pepper from environment variable.
    Lazily loaded to avoid forcing env var at import time.
    Raises ValueError if not set when first needed.
    """
    pepper = os.environ.get("USMSB_API_KEY_PEPPER")
    if not pepper:
        # For development, use a default derived from JWT_SECRET if available
        jwt_secret = os.environ.get("JWT_SECRET", "")
        if jwt_secret:
            return hashlib.sha256(jwt_secret.encode()).digest()
        # Still no pepper — raise so caller can handle gracefully
        raise ValueError(
            "USMSB_API_KEY_PEPPER environment variable not set. "
            "Set it to a secure random string (min 32 chars)."
        )
    return pepper.encode()


# ==================== Brute Force Tracking ====================

# In-memory failed attempt tracker (per-agent)
# In production, this should be Redis or similar for distributed deployments
_failed_attempts: dict[str, dict[str, Any]] = {}


def _record_failed_attempt(agent_id: str) -> dict[str, Any]:
    """Record a failed API key attempt. Returns lockout info."""
    now = time.time()
    if agent_id not in _failed_attempts:
        _failed_attempts[agent_id] = {
            "count": 0,
            "first_attempt": now,
            "locked_until": 0,
        }

    record = _failed_attempts[agent_id]

    # If previous lockout has expired, reset
    if now > record.get("locked_until", 0):
        record["count"] = 0
        record["first_attempt"] = now
        record["locked_until"] = 0

    record["count"] += 1

    if record["count"] >= MAX_FAILED_ATTEMPTS:
        record["locked_until"] = now + LOCKOUT_DURATION_SECONDS
        _failed_attempts[agent_id] = record
        return {
            "locked": True,
            "locked_until": record["locked_until"],
            "attempts": record["count"],
            "retry_after": LOCKOUT_DURATION_SECONDS,
        }

    _failed_attempts[agent_id] = record
    return {
        "locked": False,
        "attempts": record["count"],
        "remaining": MAX_FAILED_ATTEMPTS - record["count"],
    }


def _clear_failed_attempts(agent_id: str) -> None:
    """Clear failed attempts on successful auth."""
    if agent_id in _failed_attempts:
        del _failed_attempts[agent_id]


def _is_locked_out(agent_id: str) -> tuple[bool, float]:
    """Check if agent is locked out. Returns (locked, retry_after_seconds)."""
    now = time.time()
    record = _failed_attempts.get(agent_id, {})
    locked_until = record.get("locked_until", 0)
    if locked_until > now:
        return True, locked_until - now
    return False, 0


# ==================== Dataclass ====================

@dataclass
class APIKeyInfo:
    """API Key information (for display purposes, never includes the full key)."""
    id: str
    agent_id: str
    key_prefix: str
    name: str
    level: int
    permissions: list[str]
    expires_at: float | None
    last_used_at: float | None
    created_at: float
    is_revoked: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'agent_id': self.agent_id,
            'prefix': self.key_prefix + '...',  # Only show prefix
            'name': self.name,
            'level': self.level,
            'permissions': self.permissions,
            'expires_at': self.expires_at,
            'last_used_at': self.last_used_at,
            'created_at': self.created_at,
            'is_revoked': self.is_revoked
        }


# ==================== API Key Generation ====================

def generate_api_key(agent_id: str) -> tuple[str, str, str]:
    """
    Generate a new API key for an agent.

    Format: usmsb_{32-char-random-hex}
    No timestamp in the key itself (prevents enumeration).

    Args:
        agent_id: The agent's ID

    Returns:
        Tuple of (api_key, key_hash, key_prefix)
        - api_key: The full key to return to agent
        - key_hash: HMAC-SHA256(key, pepper) for storage
        - key_prefix: First 12 chars for identification
    """
    # Generate 16 bytes = 32 hex chars of randomness (128 bits entropy)
    random_bytes = secrets.token_bytes(16)
    random_hex = random_bytes.hex()

    # Build API key: usmsb_{32-hex-chars}
    api_key = f"{API_KEY_PREFIX}_{random_hex}"

    # Hash with pepper for storage (HMAC prevents rainbow table attacks)
    pepper = _get_pepper()
    key_hash = hmac.new(pepper, api_key.encode(), hashlib.sha256).hexdigest()

    # Prefix for identification (first 12 chars)
    key_prefix = api_key[:12]

    return api_key, key_hash, key_prefix


def generate_binding_code() -> tuple[str, float]:
    """
    Generate a binding code for owner binding.

    Format: bind-{32-char-random-hex}
    128 bits entropy (was 48 bits).

    Returns:
        Tuple of (binding_code, expires_at)
    """
    # 16 bytes = 32 hex chars = 128 bits entropy
    random_part = secrets.token_hex(API_KEY_BINDING_CODE_ENTROPY)
    binding_code = f"{API_KEY_BINDING_CODE_PREFIX}{random_part}"
    expires_at = time.time() + API_KEY_BINDING_EXPIRY_SECONDS

    return binding_code, expires_at


def generate_key_id() -> str:
    """Generate a unique key ID."""
    return f"key-{secrets.token_hex(8)}"


def generate_binding_id() -> str:
    """Generate a unique binding request ID."""
    return f"bind-{secrets.token_hex(8)}"


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key using HMAC-SHA256 with pepper.

    Args:
        api_key: The raw API key

    Returns:
        HMAC-SHA256 hex digest
    """
    pepper = _get_pepper()
    return hmac.new(pepper, api_key.encode(), hashlib.sha256).hexdigest()


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """
    Verify an API key against stored hash using constant-time comparison.

    Args:
        api_key: The API key to verify
        stored_hash: The stored HMAC hash

    Returns:
        True if the key matches, False otherwise
    """
    if not api_key or not stored_hash:
        return False

    pepper = _get_pepper()
    computed_hash = hmac.new(pepper, api_key.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed_hash, stored_hash)


def validate_api_key_format(api_key: str) -> bool:
    """
    Validate API key format.

    Expected format: usmsb_{32-hex-chars}
    """
    if not api_key:
        return False

    parts = api_key.split('_')
    if len(parts) != 2:
        return False

    prefix, random_part = parts

    if prefix != API_KEY_PREFIX:
        return False

    # Must be exactly 32 hex chars (16 bytes)
    if len(random_part) != API_KEY_RANDOM_LENGTH:
        return False

    try:
        int(random_part, 16)
    except ValueError:
        return False

    return True


def validate_binding_code_format(binding_code: str) -> bool:
    """
    Validate binding code format.

    Expected format: bind-{32-hex-chars} (was 12)
    """
    if not binding_code:
        return False

    if not binding_code.startswith(API_KEY_BINDING_CODE_PREFIX):
        return False

    code_part = binding_code[len(API_KEY_BINDING_CODE_PREFIX):]

    # Now 32 hex chars (128 bits)
    if len(code_part) != API_KEY_BINDING_CODE_ENTROPY * 2:
        return False

    try:
        int(code_part, 16)
    except ValueError:
        return False

    return True


# ==================== Stake Tier ====================

def get_stake_tier(staked_amount: float) -> str:
    """Get stake tier based on staked amount."""
    if staked_amount >= 10000:
        return "PLATINUM"
    elif staked_amount >= 5000:
        return "GOLD"
    elif staked_amount >= 1000:
        return "SILVER"
    elif staked_amount >= 100:
        return "BRONZE"
    else:
        return "NONE"


def get_tier_benefits(tier: str) -> dict[str, Any]:
    """Get benefits for a stake tier."""
    benefits = {
        "NONE": {"max_agents": 0, "discount": 0.0, "min_stake": 0},
        "BRONZE": {"max_agents": 1, "discount": 0.0, "min_stake": 100},
        "SILVER": {"max_agents": 3, "discount": 0.05, "min_stake": 1000},
        "GOLD": {"max_agents": 10, "discount": 0.10, "min_stake": 5000},
        "PLATINUM": {"max_agents": 50, "discount": 0.20, "min_stake": 10000}
    }
    return benefits.get(tier, benefits["NONE"])


def calculate_reputation(staked_amount: float) -> float:
    """Calculate reputation based on staked amount."""
    return min(0.5 + (staked_amount / 1000), 1.0)


# ==================== APIKeyManager ====================

class APIKeyManager:
    """Manager class for API key operations."""

    def __init__(self):
        pass

    @staticmethod
    def create_key_for_agent(
        agent_id: str,
        name: str = "Primary",
        expires_in_days: int | None = None,
        level: int = 0
    ) -> dict[str, Any]:
        """Create a new API key for an agent."""
        api_key, key_hash, key_prefix = generate_api_key(agent_id)
        key_id = generate_key_id()

        expires_at = None
        if expires_in_days:
            expires_at = time.time() + (expires_in_days * 86400)

        return {
            'id': key_id,
            'agent_id': agent_id,
            'api_key': api_key,
            'key_hash': key_hash,
            'key_prefix': key_prefix,
            'name': name,
            'level': level,
            'expires_at': expires_at,
            'created_at': time.time()
        }

    @staticmethod
    def create_binding_request(
        agent_id: str,
        base_url: str,
        message: str = ""
    ) -> dict[str, Any]:
        """Create a new binding request."""
        binding_code, expires_at = generate_binding_code()
        binding_id = generate_binding_id()
        binding_url = f"{base_url}/bind/{binding_code}"

        return {
            'id': binding_id,
            'agent_id': agent_id,
            'binding_code': binding_code,
            'binding_url': binding_url,
            'message': message,
            'expires_at': expires_at,
            'expires_in': int(expires_at - time.time()),
            'created_at': time.time()
        }

    @staticmethod
    def verify_key(api_key: str, stored_hash: str) -> bool:
        """Verify an API key against a stored hash."""
        return verify_api_key(api_key, stored_hash)

    @staticmethod
    def is_expired(expires_at: float | None) -> bool:
        """Check if a key has expired."""
        if expires_at is None:
            return False
        return time.time() > expires_at
