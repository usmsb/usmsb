"""
Agent API Key Authentication

Provides authentication dependency for agent API endpoints using X-API-Key and X-Agent-ID headers.
"""

import json
import time
from typing import Any

from fastapi import Depends, Header, HTTPException

from ..database import (
    get_db,
    update_api_key_last_used,
)
from .api_key_manager import get_stake_tier, get_tier_benefits, verify_api_key


class ErrorCode:
    """Error codes for API responses."""
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_API_KEY = "INVALID_API_KEY"
    KEY_EXPIRED = "KEY_EXPIRED"
    KEY_REVOKED = "KEY_REVOKED"
    INSUFFICIENT_STAKE = "INSUFFICIENT_STAKE"
    NOT_BOUND = "NOT_BOUND"
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


async def get_agent_by_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    x_agent_id: str | None = Header(None, alias="X-Agent-ID")
) -> dict[str, Any]:
    """
    Dependency to authenticate agent by API Key.

    Headers required:
        X-API-Key: The agent's API key (usmsb_xxx_xxx)
        X-Agent-ID: The agent's ID (agent-xxx)

    Returns:
        Agent info dict with stake info

    Raises:
        HTTPException: 401 if authentication fails
    """
    if not x_api_key or not x_agent_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Missing authentication headers",
                "code": ErrorCode.UNAUTHORIZED,
                "message": "Both X-API-Key and X-Agent-ID headers are required"
            }
        )

    with get_db() as conn:
        cursor = conn.cursor()

        # Find all active API keys for this agent
        cursor.execute("""
            SELECT k.id, k.agent_id, k.key_hash, k.key_prefix, k.name,
                   k.permissions, k.level, k.expires_at, k.last_used_at,
                   k.created_at, k.revoked_at,
                   a.name as agent_name, a.status, a.capabilities, a.description,
                   a.binding_status, a.owner_wallet, a.bound_at
            FROM agent_api_keys k
            JOIN agents a ON k.agent_id = a.agent_id
            WHERE k.agent_id = ? AND k.revoked_at IS NULL
        """, (x_agent_id,))

        keys = cursor.fetchall()

        if not keys:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "No valid API keys found for this agent",
                    "code": ErrorCode.INVALID_API_KEY,
                    "message": "Agent not found or has no active API keys"
                }
            )

        # Verify API key against any valid key for this agent
        verified_key = None
        for key in keys:
            key_dict = dict(key)
            if verify_api_key(x_api_key, key_dict['key_hash']):
                verified_key = key_dict
                break

        if not verified_key:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "Invalid API key",
                    "code": ErrorCode.INVALID_API_KEY,
                    "message": "The provided API key does not match any active keys for this agent"
                }
            )

        # Check expiration
        if verified_key['expires_at'] and verified_key['expires_at'] < time.time():
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "API key has expired",
                    "code": ErrorCode.KEY_EXPIRED,
                    "message": "Please generate a new API key"
                }
            )

        # Update last used timestamp
        update_api_key_last_used(verified_key['id'])

        # Get stake info from agent wallet
        cursor.execute("""
            SELECT staked_amount, stake_status
            FROM agent_wallets
            WHERE agent_id = ?
        """, (x_agent_id,))
        wallet = cursor.fetchone()

        staked_amount = wallet['staked_amount'] if wallet else 0
        stake_status = wallet['stake_status'] if wallet else 'none'

        # Get stake tier
        stake_tier = get_stake_tier(staked_amount)
        tier_benefits = get_tier_benefits(stake_tier)

        # Parse permissions
        permissions = []
        try:
            if verified_key['permissions']:
                permissions = json.loads(verified_key['permissions'])
        except (json.JSONDecodeError, TypeError):
            pass

        # Parse capabilities
        capabilities = []
        try:
            if verified_key['capabilities']:
                capabilities = json.loads(verified_key['capabilities'])
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            'agent_id': verified_key['agent_id'],
            'agent_name': verified_key['agent_name'],
            'description': verified_key['description'],
            'status': verified_key['status'],
            'capabilities': capabilities,
            'api_key_id': verified_key['id'],
            'api_key_name': verified_key['name'],
            'level': verified_key['level'],
            'permissions': permissions,
            'binding_status': verified_key['binding_status'],
            'owner_wallet': verified_key['owner_wallet'],
            'bound_at': verified_key['bound_at'],
            'staked_amount': staked_amount,
            'stake_status': stake_status,
            'stake_tier': stake_tier,
            'tier_benefits': tier_benefits,
            'is_bound': verified_key['binding_status'] == 'bound',
        }


async def get_optional_agent(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    x_agent_id: str | None = Header(None, alias="X-Agent-ID")
) -> dict[str, Any] | None:
    """
    Optional agent authentication - returns None if no credentials provided.

    This is useful for endpoints that have different behavior for authenticated
    vs unauthenticated requests.
    """
    if not x_api_key or not x_agent_id:
        return None

    try:
        return await get_agent_by_api_key(x_api_key, x_agent_id)
    except HTTPException:
        return None


def require_stake(min_stake: int = 100):
    """
    Dependency factory to require minimum stake.

    Usage:
        @router.post("/create")
        async def create(agent: dict = Depends(require_stake(100))):
            ...

    Args:
        min_stake: Minimum required stake amount in VIBE

    Returns:
        Dependency function that validates stake
    """
    async def stake_checker(agent: dict = Depends(get_agent_by_api_key)) -> dict:
        if agent['staked_amount'] < min_stake:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Insufficient stake",
                    "code": ErrorCode.INSUFFICIENT_STAKE,
                    "message": f"This action requires a minimum stake of {min_stake} VIBE. "
                              f"Current stake: {agent['staked_amount']} VIBE. "
                              f"Please ask your owner to stake more tokens.",
                    "required": min_stake,
                    "current": agent['staked_amount']
                }
            )
        return agent
    return stake_checker


def require_bound():
    """
    Dependency factory to require agent to be bound to owner.

    Usage:
        @router.post("/publish")
        async def publish(agent: dict = Depends(require_bound())):
            ...

    Returns:
        Dependency function that validates binding
    """
    async def binding_checker(agent: dict = Depends(get_agent_by_api_key)) -> dict:
        if not agent['is_bound']:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Agent must be bound to owner",
                    "code": ErrorCode.NOT_BOUND,
                    "message": "This action requires the agent to be bound to an owner. "
                              "Please request owner binding first.",
                    "binding_status": agent['binding_status']
                }
            )
        return agent
    return binding_checker


def require_tier(min_tier: str):
    """
    Dependency factory to require minimum stake tier.

    Args:
        min_tier: Minimum required tier (NONE, BRONZE, SILVER, GOLD, PLATINUM)

    Returns:
        Dependency function that validates tier
    """
    tier_order = ["NONE", "BRONZE", "SILVER", "GOLD", "PLATINUM"]

    async def tier_checker(agent: dict = Depends(get_agent_by_api_key)) -> dict:
        current_idx = tier_order.index(agent['stake_tier']) if agent['stake_tier'] in tier_order else 0
        required_idx = tier_order.index(min_tier) if min_tier in tier_order else 0

        if current_idx < required_idx:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Insufficient stake tier",
                    "code": ErrorCode.INSUFFICIENT_STAKE,
                    "message": f"This action requires {min_tier} tier or higher. "
                              f"Current tier: {agent['stake_tier']}",
                    "required_tier": min_tier,
                    "current_tier": agent['stake_tier']
                }
            )
        return agent
    return tier_checker


def require_permission(permission: str):
    """
    Dependency factory to require specific permission.

    Args:
        permission: Required permission string

    Returns:
        Dependency function that validates permission
    """
    async def permission_checker(agent: dict = Depends(get_agent_by_api_key)) -> dict:
        if permission not in agent['permissions'] and '*' not in agent['permissions']:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Permission denied",
                    "code": ErrorCode.UNAUTHORIZED,
                    "message": f"This action requires the '{permission}' permission",
                    "required_permission": permission
                }
            )
        return agent
    return permission_checker


def verify_agent_access(agent: dict[str, Any], target_agent_id: str) -> bool:
    """
    Verify that the authenticated agent/user has access to the target agent's resources.

    Access is granted if:
    1. The agent_id matches exactly (agent accessing its own resources)
    2. For Bearer auth: The user's wallet is the owner of the target agent

    Args:
        agent: The authenticated agent/user dict
        target_agent_id: The agent ID being accessed

    Returns:
        True if access is allowed

    Raises:
        HTTPException: If access is denied
    """
    from ..database import get_db

    # If agent_id matches, always allow
    if agent.get('agent_id') == target_agent_id:
        return True

    # For Bearer auth, check if user's wallet owns the target agent
    auth_type = agent.get('auth_type')
    if auth_type == 'bearer':
        user_wallet = agent.get('wallet_address', '').lower()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT owner_wallet, binding_status
                FROM agents
                WHERE agent_id = ?
            """, (target_agent_id,))
            target_agent = cursor.fetchone()

            if target_agent:
                owner_wallet = (target_agent['owner_wallet'] or '').lower()
                if owner_wallet and owner_wallet == user_wallet:
                    return True  # User is the owner of this agent

    # Access denied
    raise HTTPException(
        status_code=403,
        detail={
            "error": "Access denied",
            "code": ErrorCode.UNAUTHORIZED,
            "message": "You can only access your own resources or resources of agents you own",
            "your_agent_id": agent.get('agent_id'),
            "your_wallet": agent.get('wallet_address') if auth_type == 'bearer' else None,
            "requested_agent_id": target_agent_id
        }
    )


# Convenience functions for route handlers

def agent_id_matches(agent: dict[str, Any], target_id: str) -> bool:
    """Check if agent ID matches the target ID."""
    return agent['agent_id'] == target_id


def get_agent_id(agent: dict[str, Any]) -> str:
    """Get agent ID from agent dict."""
    return agent['agent_id']


def is_agent_bound(agent: dict[str, Any]) -> bool:
    """Check if agent is bound to owner."""
    return agent.get('is_bound', False)


def get_stake_amount(agent: dict[str, Any]) -> float:
    """Get staked amount from agent dict."""
    return agent.get('staked_amount', 0)


def get_tier(agent: dict[str, Any]) -> str:
    """Get stake tier from agent dict."""
    return agent.get('stake_tier', 'NONE')


def has_minimum_stake(agent: dict[str, Any], min_stake: float) -> bool:
    """Check if agent has minimum stake."""
    return agent.get('staked_amount', 0) >= min_stake
