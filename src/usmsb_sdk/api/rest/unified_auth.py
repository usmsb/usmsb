"""
Unified Authentication Module

Supports both authentication methods:
1. SIWE Wallet Auth: Bearer token in Authorization header
2. Agent API Key Auth: X-API-Key + X-Agent-ID headers

Security:
- Brute force protection: lockout after 5 failed attempts for 15 minutes
- HMAC-SHA256 API key hashing with pepper
- No global mutable state (uses dependency injection via request state)

This allows human users and AI agents to access the same endpoints.
"""

import json
import time
from typing import Any

from fastapi import Depends, Header, HTTPException

from ..database import (
    get_agent_wallet,
    get_db,
    get_session_by_token,
    get_user_by_address,
    update_api_key_last_used,
)
from .api_key_manager import (
    _clear_failed_attempts,
    _is_locked_out,
    _record_failed_attempt,
    get_stake_tier,
    get_tier_benefits,
    verify_api_key,
)


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
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"


async def get_user_by_bearer_token(
    authorization: str | None = Header(None)
) -> dict[str, Any] | None:
    """
    Authenticate user by Bearer token (SIWE wallet auth).

    Returns user info or None if no valid token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    access_token = authorization[7:]

    session = get_session_by_token(access_token)
    if not session:
        return None

    user = get_user_by_address(session['address'])
    if not user:
        return None

    agent_id = user.get('agent_id')

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

    Includes brute force protection: lockout after MAX_FAILED_ATTEMPTS.

    Returns agent info or None if no valid credentials.
    Raises HTTPException 429 if locked out.
    """
    if not x_api_key or not x_agent_id:
        return None

    # Check lockout first (before doing any DB work)
    locked, retry_after = _is_locked_out(x_agent_id)
    if locked:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Too many failed attempts",
                "code": ErrorCode.ACCOUNT_LOCKED,
                "message": f"Account locked due to multiple failed authentication attempts. "
                           f"Retry after {int(retry_after)} seconds.",
                "retry_after": int(retry_after),
            }
        )

    with get_db() as conn:
        cursor = conn.cursor()

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
            # Agent not found — record failed attempt
            lockout_info = _record_failed_attempt(x_agent_id)
            if lockout_info["locked"]:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Too many failed attempts",
                        "code": ErrorCode.ACCOUNT_LOCKED,
                        "message": f"Account locked. Retry after {lockout_info['retry_after']} seconds.",
                        "retry_after": lockout_info["retry_after"],
                    }
                )
            return None

        # Verify API key against any valid key for this agent
        verified_key = None
        for key in keys:
            key_dict = dict(key)
            if verify_api_key(x_api_key, key_dict['key_hash']):
                verified_key = key_dict
                break

        if not verified_key:
            # Record failed attempt
            lockout_info = _record_failed_attempt(x_agent_id)
            if lockout_info["locked"]:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Too many failed attempts",
                        "code": ErrorCode.ACCOUNT_LOCKED,
                        "message": f"Account locked. Retry after {lockout_info['retry_after']} seconds.",
                        "retry_after": lockout_info["retry_after"],
                    }
                )
            return None

        # Check expiration
        if verified_key['expires_at'] and verified_key['expires_at'] < time.time():
            return None

        # Clear failed attempts on success
        _clear_failed_attempts(x_agent_id)

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
    """Optional unified auth - returns None if no valid credentials."""
    user = await get_user_by_bearer_token(authorization)
    if user:
        return user

    try:
        agent = await get_agent_by_api_key_headers(x_api_key, x_agent_id)
        if agent:
            return agent
    except HTTPException:
        # Don't expose lockout in optional auth — just treat as unauthenticated
        pass

    return None


def require_stake_unified(min_stake: int = 100):
    """Dependency factory to require minimum stake (works with both auth types)."""
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
    """Verify that the authenticated user has access to the target agent."""
    from ..database import get_db

    auth_type = user.get('auth_type')
    user_agent_id = user.get('agent_id')

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
    elif auth_type == 'bearer':
        if user_agent_id == target_agent_id:
            return

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
                    return

        raise HTTPException(
            status_code=403,
            detail={
                "error": "Access denied",
                "code": "ACCESS_DENIED",
                "message": f"You don't have access to agent {target_agent_id}."
            }
        )
    else:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Access denied",
                "code": "ACCESS_DENIED",
                "message": "Unable to verify agent access"
            }
        )


from fastapi import Depends
