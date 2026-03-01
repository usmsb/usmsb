"""
API Key Management for Agents

Provides secure API key generation, validation, and management.
"""

import hashlib
import secrets
import time
from typing import Optional, Tuple, Dict, Any, List
from dataclasses import dataclass, asdict, field

# API Key Configuration
API_KEY_PREFIX = "usmsb"
API_KEY_HASH_LENGTH = 16  # 8 bytes = 16 hex chars
API_KEY_TIMESTAMP_LENGTH = 8  # 4 bytes = 8 hex chars
API_KEY_BINDING_CODE_PREFIX = "bind-"
API_KEY_BINDING_EXPIRY_SECONDS = 600  # 10 minutes
API_KEY_DEFAULT_EXPIRY_DAYS = 365


@dataclass
class APIKeyInfo:
    """API Key information (for display purposes, never includes the full key)."""
    id: str
    agent_id: str
    key_prefix: str
    name: str
    level: int
    permissions: List[str]
    expires_at: Optional[float]
    last_used_at: Optional[float]
    created_at: float
    is_revoked: bool = False

    def to_dict(self) -> Dict[str, Any]:
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


def generate_api_key(agent_id: str) -> Tuple[str, str, str]:
    """
    Generate a new API key for an agent.

    The API key format is: usmsb_{16-char-hash}_{8-char-timestamp}

    Args:
        agent_id: The agent's ID

    Returns:
        Tuple of (api_key, key_hash, key_prefix)
        - api_key: The full key to return to agent (usmsb_xxx_xxx)
        - key_hash: SHA-256 hash for storage
        - key_prefix: First 16 chars for identification
    """
    # Generate random hash (8 bytes = 16 hex chars)
    random_hash = secrets.token_hex(8)

    # Generate timestamp (4 bytes = 8 hex chars)
    timestamp = hex(int(time.time()))[2:].zfill(API_KEY_TIMESTAMP_LENGTH)

    # Build API key: usmsb_{hash}_{timestamp}
    api_key = f"{API_KEY_PREFIX}_{random_hash}_{timestamp}"

    # Hash for storage (never store plain key)
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # Prefix for identification (first 16 chars including prefix)
    key_prefix = api_key[:16]

    return api_key, key_hash, key_prefix


def generate_binding_code() -> Tuple[str, float]:
    """
    Generate a binding code for owner binding.

    The binding code format is: bind-{12-char-random}

    Returns:
        Tuple of (binding_code, expires_at)
    """
    random_part = secrets.token_hex(6)  # 6 bytes = 12 hex chars
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
    """Hash an API key using SHA-256."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """
    Verify an API key against stored hash using constant-time comparison.

    Args:
        api_key: The API key to verify
        stored_hash: The stored SHA-256 hash

    Returns:
        True if the key matches, False otherwise
    """
    if not api_key or not stored_hash:
        return False

    computed_hash = hash_api_key(api_key)
    return secrets.compare_digest(computed_hash, stored_hash)


def validate_api_key_format(api_key: str) -> bool:
    """
    Validate API key format.

    Expected format: usmsb_{16-hex-chars}_{8-hex-chars}
    """
    if not api_key:
        return False

    parts = api_key.split('_')
    if len(parts) != 3:
        return False

    prefix, hash_part, timestamp_part = parts

    if prefix != API_KEY_PREFIX:
        return False

    if len(hash_part) != API_KEY_HASH_LENGTH:
        return False

    if len(timestamp_part) != API_KEY_TIMESTAMP_LENGTH:
        return False

    # Check if hash and timestamp are valid hex
    try:
        int(hash_part, 16)
        int(timestamp_part, 16)
    except ValueError:
        return False

    return True


def validate_binding_code_format(binding_code: str) -> bool:
    """
    Validate binding code format.

    Expected format: bind-{12-hex-chars}
    """
    if not binding_code:
        return False

    if not binding_code.startswith(API_KEY_BINDING_CODE_PREFIX):
        return False

    code_part = binding_code[len(API_KEY_BINDING_CODE_PREFIX):]

    if len(code_part) != 12:
        return False

    try:
        int(code_part, 16)
    except ValueError:
        return False

    return True


def get_stake_tier(staked_amount: float) -> str:
    """
    Get stake tier based on staked amount.

    Args:
        staked_amount: Amount of VIBE staked

    Returns:
        Tier name: NONE, BRONZE, SILVER, GOLD, or PLATINUM
    """
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


def get_tier_benefits(tier: str) -> Dict[str, Any]:
    """
    Get benefits for a stake tier.

    Args:
        tier: Tier name

    Returns:
        Dict with max_agents and discount
    """
    benefits = {
        "NONE": {"max_agents": 0, "discount": 0.0, "min_stake": 0},
        "BRONZE": {"max_agents": 1, "discount": 0.0, "min_stake": 100},
        "SILVER": {"max_agents": 3, "discount": 0.05, "min_stake": 1000},
        "GOLD": {"max_agents": 10, "discount": 0.10, "min_stake": 5000},
        "PLATINUM": {"max_agents": 50, "discount": 0.20, "min_stake": 10000}
    }
    return benefits.get(tier, benefits["NONE"])


def calculate_reputation(staked_amount: float) -> float:
    """
    Calculate reputation based on staked amount.

    Formula: min(0.5 + staked_amount/1000, 1.0)

    Args:
        staked_amount: Amount of VIBE staked

    Returns:
        Reputation score between 0.5 and 1.0
    """
    return min(0.5 + (staked_amount / 1000), 1.0)


class APIKeyManager:
    """
    Manager class for API key operations.

    This class provides a high-level interface for API key management,
    including creation, validation, and revocation.
    """

    def __init__(self):
        """Initialize the API Key Manager."""
        pass

    @staticmethod
    def create_key_for_agent(agent_id: str, name: str = "Primary",
                             expires_in_days: Optional[int] = None,
                             level: int = 0) -> Dict[str, Any]:
        """
        Create a new API key for an agent.

        Args:
            agent_id: The agent's ID
            name: Human-readable name for the key
            expires_in_days: Number of days until expiration (None = never)
            level: Permission level (0=unbound, 1+=bound)

        Returns:
            Dict with api_key, key_hash, key_prefix, and metadata
        """
        api_key, key_hash, key_prefix = generate_api_key(agent_id)
        key_id = generate_key_id()

        expires_at = None
        if expires_in_days:
            expires_at = time.time() + (expires_in_days * 86400)

        return {
            'id': key_id,
            'agent_id': agent_id,
            'api_key': api_key,  # This is the only time the full key is available
            'key_hash': key_hash,
            'key_prefix': key_prefix,
            'name': name,
            'level': level,
            'expires_at': expires_at,
            'created_at': time.time()
        }

    @staticmethod
    def create_binding_request(agent_id: str, base_url: str,
                               message: str = "") -> Dict[str, Any]:
        """
        Create a new binding request.

        Args:
            agent_id: The agent's ID
            base_url: Base URL for the binding page
            message: Optional message to the owner

        Returns:
            Dict with binding_code, binding_url, and expiration info
        """
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
    def is_expired(expires_at: Optional[float]) -> bool:
        """Check if a key has expired."""
        if expires_at is None:
            return False
        return time.time() > expires_at
