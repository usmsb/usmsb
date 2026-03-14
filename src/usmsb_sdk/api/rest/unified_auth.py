"""
Unified Authentication Module

Supports both authentication methods:
1. SIWE Wallet Auth: Bearer token in Authorization header
2. Agent API Key Auth: X-API-Key + X-Agent-ID headers

This allows human users and AI agents to access the same endpoints.
"""

import json
import time
from typing import Any

from fastapi import Header, HTTPException

from ..database import (
    get_agent_wallet,
    get_db,
    get_session_by_token,
    get_user_by_address,
    update_api_key_last_used,
)
from .api_key_manager import get_stake_tier, get_tier_benefits, verify_api_key


class ErrorCode:
    """Error codes for API responses."""
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_API_KEY = "INVALID_API_KEY"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    KEY_EXPIRED = "KEY_EXPIRED"
    KEY_REVOKED = "KEY_REVOKED"
    INSUFFICIENT_STAKE = "INSUFFICIENT_STAKE"
    NOT_BOUND = "NOT_BOUND"
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


async def get_user_by_bearer_token(
    authorization: str | None = Header(None)
) -> dict[str, Any] | None:
    """
    Authenticate user by Bearer token (SIWE wallet auth).

    Returns user info or None if no valid token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    access_token = authorization[7:]  # Remove "Bearer " prefix

    # Get session by token
    session = get_session_by_token(access_token)
    if not session:
        return None

    # Get user info
    user = get_user_by_address(session['address'])
    if not user:
        return None

    # Get agent_id if user has one
    agent_id = user.get('agent_id')

    # Get wallet info if agent exists
    wallet_info = None
    if agent_id:
        wallet = get_agent_wallet(agent_id)
        if wallet:
            wallet_info = wallet

    staked_amount = wallet_info.get('staked_amount', 0) if wallet_info else 0
    stake_status = wallet_info.get('stake_status', 'none') if wallet_info else 'none'
    stake_tier = get_stake_tier(staked_amount)
    tier_benefits = get_tier_benefits(stake_tier)

    return {
        'auth_type': 'bearer',
        'user_id': user['id'],
        'wallet_address': user['wallet_address'],
        'agent_id': agent_id,
        'did': user.get('did'),
        'stake': user.get('stake', 0),
        'reputation': user.get('reputation', 0.5),
        'is_admin': user.get('is_admin', False),
        'staked_amount': staked_amount,
        'stake_status': stake_status,
        'stake_tier': stake_tier,
        'tier_benefits': tier_benefits,
        'is_bound': bool(wallet_info),
        'session': session,
    }


async def get_agent_by_api_key_headers(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    x_agent_id: str | None = Header(None, alias="X-Agent-ID")
) -> dict[str, Any] | None:
    """
    Authenticate agent by API Key headers.

    Returns agent info or None if no valid credentials.
    """
    if not x_api_key or not x_agent_id:
        return None

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
            return None

        # Verify API key against any valid key for this agent
        verified_key = None
        for key in keys:
            key_dict = dict(key)
            if verify_api_key(x_api_key, key_dict['key_hash']):
                verified_key = key_dict
                break

        if not verified_key:
            return None

        # Check expiration
        if verified_key['expires_at'] and verified_key['expires_at'] < time.time():
            return None

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
            if verified_key.get('capabilities'):
                capabilities = json.loads(verified_key['capabilities'])
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            'auth_type': 'api_key',
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


async def get_current_user_unified(
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    x_agent_id: str | None = Header(None, alias="X-Agent-ID")
) -> dict[str, Any]:
    """
    Unified authentication dependency.

    Tries Bearer token first, then API Key authentication.

    Returns unified user/agent info dict.

    Raises:
        HTTPException: 401 if no valid authentication
    """
    # Try Bearer token first
    user = await get_user_by_bearer_token(authorization)
    if user:
        return user

    # Try API Key authentication
    agent = await get_agent_by_api_key_headers(x_api_key, x_agent_id)
    if agent:
        return agent

    # No valid authentication
    raise HTTPException(
        status_code=401,
        detail={
            "error": "Authentication required",
            "code": ErrorCode.UNAUTHORIZED,
            "message": "Please provide either a Bearer token (Authorization header) or API key credentials (X-API-Key + X-Agent-ID headers)"
        }
    )


async def get_optional_user_unified(
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    x_agent_id: str | None = Header(None, alias="X-Agent-ID")
) -> dict[str, Any] | None:
    """
    Optional unified authentication - returns None if no credentials provided.

    Useful for endpoints that have different behavior for authenticated
    vs unauthenticated requests.
    """
    # Try Bearer token first
    user = await get_user_by_bearer_token(authorization)
    if user:
        return user

    # Try API Key authentication
    agent = await get_agent_by_api_key_headers(x_api_key, x_agent_id)
    if agent:
        return agent

    return None


def require_stake_unified(min_stake: int = 100):
    """
    Dependency factory to require minimum stake (works with both auth types).
    """
    async def stake_checker(user: dict = Depends(get_current_user_unified)) -> dict:
        if user['staked_amount'] < min_stake:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Insufficient stake",
                    "code": ErrorCode.INSUFFICIENT_STAKE,
                    "message": f"This action requires a minimum stake of {min_stake} VIBE. "
                              f"Current stake: {user['staked_amount']} VIBE.",
                    "required": min_stake,
                    "current": user['staked_amount']
                }
            )
        return user
    return stake_checker


def verify_agent_access(user: dict[str, Any], target_agent_id: str) -> None:
    """
    Verify that the authenticated user has access to the target agent.

    For API Key auth: The agent_id must match the authenticated agent.
    For Bearer auth: The user's wallet must be the owner of the target agent,
                   or the user's agent_id must match the target.

    Raises:
        HTTPException: 403 if access is denied
    """
    from ..database import get_db

    auth_type = user.get('auth_type')
    user_agent_id = user.get('agent_id')

    # For API Key auth, agent_id must match exactly
    if auth_type == 'api_key':
        if user_agent_id != target_agent_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Access denied",
                    "code": "ACCESS_DENIED",
                    "message": f"You can only access your own agent resources. "
                              f"Your agent_id: {user_agent_id}, requested: {target_agent_id}"
                }
            )
    # For Bearer auth (wallet), check if user owns the target agent
    elif auth_type == 'bearer':
        # First check: user's agent_id matches target
        if user_agent_id == target_agent_id:
            return

        # Second check: user's wallet is the owner of the target agent
        user_wallet = user.get('wallet_address', '').lower()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT owner_wallet, binding_status
                FROM agents
                WHERE agent_id = ?
            """, (target_agent_id,))
            agent = cursor.fetchone()

            if agent:
                owner_wallet = (agent['owner_wallet'] or '').lower()
                if owner_wallet and owner_wallet == user_wallet:
                    return  # User is the owner of this agent

        # If we get here, access is denied
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Access denied",
                "code": "ACCESS_DENIED",
                "message": f"You don't have access to agent {target_agent_id}. "
                          f"Your wallet: {user_wallet}, your bound agent: {user_agent_id}"
            }
        )
    else:
        # Unknown auth type, deny access
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Access denied",
                "code": "ACCESS_DENIED",
                "message": "Unable to verify agent access"
            }
        )


# Convenience exports
from fastapi import Depends
