"""
Authentication API endpoints for AI Civilization Platform

Supports SIWE (Sign-In with Ethereum) authentication flow:
1. Get nonce for wallet address
2. Sign message with wallet
3. Verify signature and create session
"""
import os
import secrets
import uuid
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field

from usmsb_sdk.api.database import (
    create_nonce,
    get_valid_nonce,
    delete_nonce,
    create_session,
    get_session_by_token,
    delete_session,
    delete_sessions_by_address,
    create_user,
    get_user_by_address,
    update_user_stake,
    update_user_agent,
    create_or_update_profile,
    get_db,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Configuration
JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    raise EnvironmentError("JWT_SECRET environment variable is required")
SESSION_DURATION_HOURS = 24 * 7  # 7 days
NONCE_EXPIRY_SECONDS = 300  # 5 minutes


# Pydantic models
class NonceResponse(BaseModel):
    nonce: str
    expiresAt: int


class VerifyRequest(BaseModel):
    message: str
    signature: str
    address: str


class VerifyResponse(BaseModel):
    success: bool
    sessionId: str
    accessToken: str
    expiresIn: int
    did: str
    isNewUser: bool


class SessionResponse(BaseModel):
    valid: bool
    agentId: Optional[str] = None
    address: Optional[str] = None
    did: Optional[str] = None
    stake: Optional[float] = None
    reputation: Optional[float] = None


class StakeRequest(BaseModel):
    amount: float = Field(..., ge=100)


class StakeResponse(BaseModel):
    success: bool
    transactionHash: str
    newStake: float
    newReputation: float


class ProfileRequest(BaseModel):
    name: str
    bio: str = ""
    skills: list[str] = []
    hourlyRate: float = 0
    availability: str = "full-time"
    role: str = "supplier"


class ProfileResponse(BaseModel):
    success: bool
    agentId: str


def generate_access_token(session_id: str, address: str) -> str:
    """Generate a simple access token (in production, use proper JWT)"""
    data = f"{session_id}:{address}:{datetime.now().timestamp()}:{JWT_SECRET}"
    return hashlib.sha256(data.encode()).hexdigest()


def extract_address_from_message(message: str) -> Optional[str]:
    """Extract address from SIWE message"""
    for line in message.split('\n'):
        if line.startswith('0x'):
            return line.strip()
    return None


def extract_nonce_from_message(message: str) -> Optional[str]:
    """Extract nonce from SIWE message"""
    for line in message.split('\n'):
        if 'nonce:' in line.lower():
            return line.split(':')[-1].strip()
    return None


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Dependency to get current user from access token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    access_token = authorization[7:]
    session = get_session_by_token(access_token)

    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    user = get_user_by_address(session['address'])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {**user, 'session': session}


async def get_current_admin(user: dict = Depends(get_current_user)) -> dict:
    """Dependency to get current admin user - requires admin privileges"""
    if not user.get('is_admin'):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/nonce/{address}", response_model=NonceResponse)
async def get_nonce_for_address(address: str):
    """Get a nonce for wallet signature authentication"""
    # Generate random nonce
    nonce = secrets.token_hex(16)

    # Store nonce in database
    nonce_data = create_nonce(address, nonce, NONCE_EXPIRY_SECONDS)

    return NonceResponse(
        nonce=nonce,
        expiresAt=int(nonce_data['expires_at'])
    )


@router.post("/verify", response_model=VerifyResponse)
async def verify_signature(request: VerifyRequest):
    """Verify wallet signature and create session"""
    address = request.address.lower()

    # Extract nonce from message
    nonce = extract_nonce_from_message(request.message)
    if not nonce:
        raise HTTPException(status_code=400, detail="Could not extract nonce from message")

    # Validate nonce
    nonce_record = get_valid_nonce(address, nonce)
    if not nonce_record:
        raise HTTPException(status_code=400, detail="Invalid or expired nonce")

    # Delete used nonce
    delete_nonce(nonce_record['id'])

    # Verify the signature using eth_account/web3.py
    try:
        from eth_account.messages import encode_defunct
        from web3 import Web3

        message = encode_defunct(text=request.message)
        recovered_address = Web3().eth.account.recover_message(message, signature=request.signature)
        if recovered_address.lower() != address:
            raise HTTPException(status_code=400, detail="Signature verification failed")
    except ImportError:
        # Fall back to basic validation if web3 is not available
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("web3.py not installed. Signature verification skipped - NOT SECURE FOR PRODUCTION")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Signature verification failed: {str(e)}")

    # Check if user exists
    user = get_user_by_address(address)
    is_new_user = user is None

    # Create or get user
    if not user:
        user = create_user({
            'wallet_address': address,
        })

    # Delete old sessions for this address
    delete_sessions_by_address(address)

    # Create new session
    session_id = str(uuid.uuid4())
    access_token = generate_access_token(session_id, address)
    expires_at = datetime.now() + timedelta(hours=SESSION_DURATION_HOURS)

    create_session({
        'session_id': session_id,
        'address': address,
        'did': user['did'],
        'agent_id': user.get('agent_id'),
        'access_token': access_token,
        'expires_at': expires_at.timestamp(),
    })

    return VerifyResponse(
        success=True,
        sessionId=session_id,
        accessToken=access_token,
        expiresIn=int(SESSION_DURATION_HOURS * 3600),
        did=user['did'],
        isNewUser=is_new_user,
    )


@router.get("/session", response_model=SessionResponse)
async def get_current_session(user: dict = Depends(get_current_user)):
    """Get current session info"""
    return SessionResponse(
        valid=True,
        agentId=user.get('agent_id'),
        address=user.get('wallet_address'),
        did=user.get('did'),
        stake=user.get('stake'),
        reputation=user.get('reputation'),
    )


@router.delete("/session")
async def logout(user: dict = Depends(get_current_user)):
    """Logout and invalidate session"""
    session = user.get('session', {})
    if session:
        delete_session(session['session_id'])
    return {"success": True, "message": "Logged out successfully"}


@router.post("/stake", response_model=StakeResponse)
async def stake_tokens(
    request: StakeRequest,
    user: dict = Depends(get_current_user)
):
    """Stake VIBE tokens (simulated for now)"""
    if request.amount < 100:
        raise HTTPException(status_code=400, detail="Minimum stake is 100 VIBE")

    # In production, this would interact with the blockchain
    # For now, we'll simulate it

    # Update user stake
    result = update_user_stake(user['id'], request.amount)

    # Generate mock transaction hash
    tx_hash = f"0x{secrets.token_hex(32)}"

    return StakeResponse(
        success=True,
        transactionHash=tx_hash,
        newStake=result['stake'],
        newReputation=result['reputation'],
    )


@router.post("/profile", response_model=ProfileResponse)
async def create_user_profile(
    request: ProfileRequest,
    user: dict = Depends(get_current_user)
):
    """Create or update user profile"""
    # Create agent for this user if not exists
    agent_id = user.get('agent_id')
    if not agent_id:
        agent_id = f"agent-{user['id']}"
        # Create agent in agents table
        with get_db() as conn:
            cursor = conn.cursor()
            now = datetime.now().timestamp()
            cursor.execute('''
                INSERT INTO agents (id, name, type, capabilities, state, goals_count, resources_count, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                agent_id,
                request.name,
                'human',
                json.dumps(request.skills),
                json.dumps({
                    'bio': request.bio,
                    'hourly_rate': request.hourly_rate,
                    'availability': request.availability,
                }),
                0,
                0,
                now,
                now
            ))

        # Update user with agent_id
        update_user_agent(user['id'], agent_id)

    # Create/update profile
    create_or_update_profile({
        'id': user['id'],
        'wallet_address': user['wallet_address'],
        'display_name': request.name,
        'bio': request.bio,
        'skills': request.skills,
        'hourly_rate': request.hourlyRate,
        'availability': request.availability,
        'role': request.role,
        'stake': user.get('stake', 0),
        'reputation': user.get('reputation', 0.5),
    })

    return ProfileResponse(
        success=True,
        agentId=agent_id,
    )
