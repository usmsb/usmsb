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
from typing import Optional, List

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
    update_user_balance,
    update_stake_status,
    get_user_balance_info,
    create_or_update_profile,
    get_db,
    create_agent_wallet,
    get_agent_wallet,
    get_agent_wallet_by_address,
    get_agent_wallets_by_owner,
    update_agent_balance,
    update_agent_stake,
    update_agent_limits,
    update_agent_daily_spent,
    register_agent_in_registry,
    delete_agent_wallet,
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


class StakeConfigResponse(BaseModel):
    stakeRequired: bool
    minStakeAmount: float
    defaultBalance: float
    unstakingPeriodDays: int


class BalanceResponse(BaseModel):
    balance: float
    stakedAmount: float
    lockedAmount: float
    totalBalance: float
    stakeStatus: str
    unlockAvailableAt: Optional[int] = None


class UnstakeRequest(BaseModel):
    amount: Optional[float] = None  # None = unstake all


class UnstakeResponse(BaseModel):
    success: bool
    lockedAmount: float
    unlockAvailableAt: int
    message: str


# ==================== Agent Wallet Models ====================

class CreateAgentWalletRequest(BaseModel):
    agent_id: str
    agent_address: str = Field(..., description="AI Agent 后端服务地址")


class AgentWalletResponse(BaseModel):
    success: bool
    agentId: str
    walletAddress: str
    agentAddress: str
    balance: float
    stakedAmount: float
    stakeStatus: str


class AgentDepositRequest(BaseModel):
    amount: float = Field(..., gt=0, description="充值金额")


class AgentDepositResponse(BaseModel):
    success: bool
    agentId: str
    newBalance: float
    newStakedAmount: float
    message: str


class AgentTransferRequest(BaseModel):
    to_address: str = Field(..., description="目标地址")
    amount: float = Field(..., gt=0, description="转账金额")


class AgentTransferResponse(BaseModel):
    success: bool
    agentId: str
    toAddress: str
    amount: float
    newBalance: float
    message: str


class AgentWalletInfoResponse(BaseModel):
    agentId: str
    walletAddress: str
    agentAddress: str
    balance: float
    stakedAmount: float
    stakeStatus: str
    maxPerTx: float
    dailyLimit: float
    dailySpent: float
    remainingDailyLimit: float
    isRegistered: bool


class AgentWalletListResponse(BaseModel):
    wallets: List[AgentWalletInfoResponse]


class AgentLimitsRequest(BaseModel):
    max_per_tx: float = Field(..., gt=0, description="单笔最大限额")
    daily_limit: float = Field(..., gt=0, description="每日限额")


class UpdateWhitelistRequest(BaseModel):
    address: str
    allowed: bool


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


@router.get("/config", response_model=StakeConfigResponse)
async def get_stake_config():
    """Get staking configuration"""
    stake_required = os.environ.get("STAKE_REQUIRED", "true").lower() == "true"
    return StakeConfigResponse(
        stakeRequired=stake_required,
        minStakeAmount=100.0,
        defaultBalance=10000.0,
        unstakingPeriodDays=7
    )


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(user: dict = Depends(get_current_user)):
    """Get user's VIBE balance information"""
    balance_info = get_user_balance_info(user['id'])
    if not balance_info:
        raise HTTPException(status_code=404, detail="User balance not found")

    return BalanceResponse(
        balance=balance_info.get('vibe_balance', 10000.0),
        stakedAmount=user.get('stake', 0),
        lockedAmount=balance_info.get('locked_stake', 0),
        totalBalance=balance_info.get('vibe_balance', 10000.0) + user.get('stake', 0),
        stakeStatus=balance_info.get('stake_status', 'none'),
        unlockAvailableAt=int(balance_info['unlock_available_at']) if balance_info.get('unlock_available_at') else None
    )


@router.post("/stake", response_model=StakeResponse)
async def stake_tokens(
    request: StakeRequest,
    user: dict = Depends(get_current_user)
):
    """Stake VIBE tokens (simulated for now)"""
    stake_required = os.environ.get("STAKE_REQUIRED", "true").lower() == "true"

    # If staking is disabled, return success without actual staking
    if not stake_required:
        tx_hash = f"0x{secrets.token_hex(32)}"
        return StakeResponse(
            success=True,
            transactionHash=tx_hash,
            newStake=user.get('stake', 0),
            newReputation=user.get('reputation', 0.5),
        )

    # Validation 1: Minimum amount
    if request.amount < 100:
        raise HTTPException(status_code=400, detail="Minimum stake is 100 VIBE")

    # Validation 2: Check user balance
    balance_info = get_user_balance_info(user['id'])
    if not balance_info or balance_info.get('vibe_balance', 0) < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient VIBE balance")

    # Validation 3: Check stake status (cannot stake while unstaking)
    stake_status = balance_info.get('stake_status', 'none')
    if stake_status == 'unstaking':
        raise HTTPException(status_code=400, detail="Cannot stake while unstaking. Cancel unstake first.")

    # Deduct from balance
    balance_result = update_user_balance(user['id'], request.amount, deduct=True)
    if not balance_result:
        raise HTTPException(status_code=400, detail="Failed to deduct balance")

    # Update user stake
    result = update_user_stake(user['id'], request.amount)

    # Update stake status to 'staked'
    update_stake_status(user['id'], 'staked')

    # Generate mock transaction hash
    tx_hash = f"0x{secrets.token_hex(32)}"

    return StakeResponse(
        success=True,
        transactionHash=tx_hash,
        newStake=result['stake'],
        newReputation=result['reputation'],
    )


@router.post("/unstake", response_model=UnstakeResponse)
async def unstake_tokens(
    request: UnstakeRequest,
    user: dict = Depends(get_current_user)
):
    """Request to unstake VIBE tokens (starts 7-day unlock period)"""
    stake_required = os.environ.get("STAKE_REQUIRED", "true").lower() == "true"

    # If staking is disabled, return success immediately
    if not stake_required:
        return UnstakeResponse(
            success=True,
            lockedAmount=0,
            unlockAvailableAt=0,
            message="Stake requirement is disabled in current mode"
        )

    # Check stake status
    balance_info = get_user_balance_info(user['id'])
    if not balance_info:
        raise HTTPException(status_code=404, detail="User not found")

    stake_status = balance_info.get('stake_status', 'none')
    if stake_status != 'staked':
        raise HTTPException(status_code=400, detail="No active stake to unstake")

    current_stake = user.get('stake', 0)
    if current_stake <= 0:
        raise HTTPException(status_code=400, detail="No stake to unstake")

    # Calculate amount to lock (all if not specified)
    locked_amount = request.amount if request.amount else current_stake
    if locked_amount > current_stake:
        raise HTTPException(status_code=400, detail="Cannot unstake more than current stake")

    # Set unlock time (7 days from now)
    unstaking_period_days = int(os.environ.get("UNSTAKING_PERIOD_DAYS", "7"))
    unlock_available_at = datetime.now() + timedelta(days=unstaking_period_days)

    # Update stake status
    update_stake_status(
        user['id'],
        'unstaking',
        locked_stake=locked_amount,
        unlock_available_at=unlock_available_at.timestamp()
    )

    return UnstakeResponse(
        success=True,
        lockedAmount=locked_amount,
        unlockAvailableAt=int(unlock_available_at.timestamp()),
        message=f"Unstake initiated. Tokens will be available in {unstaking_period_days} days."
    )


@router.post("/unstake/cancel")
async def cancel_unstake(user: dict = Depends(get_current_user)):
    """Cancel pending unstake request"""
    balance_info = get_user_balance_info(user['id'])
    if not balance_info:
        raise HTTPException(status_code=404, detail="User not found")

    stake_status = balance_info.get('stake_status', 'none')
    if stake_status != 'unstaking':
        raise HTTPException(status_code=400, detail="No pending unstake to cancel")

    # Restore to staked status
    update_stake_status(user['id'], 'staked', locked_stake=0, unlock_available_at=None)

    return {
        "success": True,
        "message": "Unstake cancelled. Your tokens remain staked."
    }


@router.post("/unstake/confirm")
async def confirm_unstake(user: dict = Depends(get_current_user)):
    """Confirm unstake after unlock period"""
    balance_info = get_user_balance_info(user['id'])
    if not balance_info:
        raise HTTPException(status_code=404, detail="User not found")

    stake_status = balance_info.get('stake_status', 'none')
    if stake_status != 'unstaking':
        raise HTTPException(status_code=400, detail="No pending unstake")

    unlock_available_at = balance_info.get('unlock_available_at')
    if not unlock_available_at:
        raise HTTPException(status_code=400, detail="Invalid unstake state")

    # Check if unlock period has passed
    if datetime.now().timestamp() < unlock_available_at:
        remaining_seconds = int(unlock_available_at - datetime.now().timestamp())
        remaining_days = remaining_seconds // 86400
        remaining_hours = (remaining_seconds % 86400) // 3600
        raise HTTPException(
            status_code=400,
            detail=f"Unlock period not completed. {remaining_days}d {remaining_hours}h remaining."
        )

    # Return staked tokens to balance
    locked_stake = balance_info.get('locked_stake', user.get('stake', 0))

    # Add back to balance
    update_user_balance(user['id'], locked_stake, deduct=False)

    # Reset stake to 0 and status to unlocked
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().timestamp()
        cursor.execute('''
            UPDATE users SET stake = 0, stake_status = 'unlocked', locked_stake = 0,
                   unlock_available_at = NULL, updated_at = ? WHERE id = ?
        ''', (now, user['id']))

    # Update reputation based on new stake (0)
    new_reputation = 0.5
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET reputation = ? WHERE id = ?', (new_reputation, user['id']))

    return {
        "success": True,
        "unlockedAmount": locked_stake,
        "message": f"Successfully unstaked {locked_stake} VIBE tokens."
    }


@router.post("/profile", response_model=ProfileResponse)
async def create_user_profile(
    request: ProfileRequest,
    user: dict = Depends(get_current_user)
):
    """Create or update user profile"""
    # Create agent for this user if not exists
    agent_id = user.get('agent_id')
    wallet_address = None
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
                    'hourly_rate': request.hourlyRate,
                    'availability': request.availability,
                }),
                0,
                0,
                now,
                now
            ))

        # Update user with agent_id
        update_user_agent(user['id'], agent_id)

        # [方案B] 自动创建 Agent 钱包
        # 在注册时自动创建钱包
        agent_wallet_address = f"0x{secrets.token_hex(20)}"
        agent_address = f"0x{secrets.token_hex(20)}"  # Agent 后端服务地址

        wallet_data = {
            'id': f"wallet_{agent_id}",
            'agent_id': agent_id,
            'owner_id': user['id'],
            'wallet_address': agent_wallet_address,
            'agent_address': agent_address,
            'vibe_balance': 0,
            'staked_amount': 0,
            'stake_status': 'none',
            'locked_stake': 0,
            'max_per_tx': 500,
            'daily_limit': 1000,
            'daily_spent': 0,
            'registry_registered': 0,
        }

        try:
            create_agent_wallet(wallet_data)
            wallet_address = agent_wallet_address
        except Exception as e:
            # 如果创建失败（如已存在），尝试获取已存在的钱包
            existing_wallet = get_agent_wallet(agent_id)
            if existing_wallet:
                wallet_address = existing_wallet.get('wallet_address')

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


# ==================== Agent Wallet APIs ====================

@router.post("/agent/wallet", response_model=AgentWalletResponse)
async def create_agent_wallet(
    request: CreateAgentWalletRequest,
    user: dict = Depends(get_current_user)
):
    """Create a new agent wallet"""
    # 检查是否已存在钱包
    existing = get_agent_wallet(request.agent_id)
    if existing:
        raise HTTPException(status_code=400, detail="Agent wallet already exists")

    # 生成钱包地址 (模拟)
    # 在实际部署时，这里会调用合约部署
    wallet_address = f"0x{secrets.token_hex(20)}"

    wallet_data = {
        'id': f"wallet_{request.agent_id}",
        'agent_id': request.agent_id,
        'owner_id': user['id'],
        'wallet_address': wallet_address,
        'agent_address': request.agent_address,
        'vibe_balance': 0,
        'staked_amount': 0,
        'stake_status': 'none',
        'locked_stake': 0,
        'max_per_tx': 500,
        'daily_limit': 1000,
        'daily_spent': 0,
        'registry_registered': 0,
    }

    create_agent_wallet(wallet_data)

    return AgentWalletResponse(
        success=True,
        agentId=request.agent_id,
        walletAddress=wallet_address,
        agentAddress=request.agent_address,
        balance=0,
        stakedAmount=0,
        stakeStatus='none',
    )


@router.get("/agent/wallet/{agent_id}", response_model=AgentWalletInfoResponse)
async def get_agent_wallet_info(
    agent_id: str,
    user: dict = Depends(get_current_user)
):
    """Get agent wallet information"""
    wallet = get_agent_wallet(agent_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Agent wallet not found")

    # 验证是否是钱包的主人
    if wallet['owner_id'] != user['id']:
        raise HTTPException(status_code=403, detail="Not authorized to view this wallet")

    remaining = wallet['daily_limit'] - wallet['daily_spent']
    if remaining < 0:
        remaining = 0

    return AgentWalletInfoResponse(
        agentId=wallet['agent_id'],
        walletAddress=wallet['wallet_address'],
        agentAddress=wallet['agent_address'],
        balance=wallet['vibe_balance'],
        stakedAmount=wallet['staked_amount'],
        stakeStatus=wallet['stake_status'],
        maxPerTx=wallet['max_per_tx'],
        dailyLimit=wallet['daily_limit'],
        dailySpent=wallet['daily_spent'],
        remainingDailyLimit=remaining,
        isRegistered=bool(wallet['registry_registered']),
    )


@router.get("/agent/wallets", response_model=AgentWalletListResponse)
async def get_agent_wallets(user: dict = Depends(get_current_user)):
    """Get all agent wallets for current user"""
    wallets = get_agent_wallets_by_owner(user['id'])

    result = []
    for wallet in wallets:
        remaining = wallet['daily_limit'] - wallet['daily_spent']
        if remaining < 0:
            remaining = 0

        result.append(AgentWalletInfoResponse(
            agentId=wallet['agent_id'],
            walletAddress=wallet['wallet_address'],
            agentAddress=wallet['agent_address'],
            balance=wallet['vibe_balance'],
            stakedAmount=wallet['staked_amount'],
            stakeStatus=wallet['stake_status'],
            maxPerTx=wallet['max_per_tx'],
            dailyLimit=wallet['daily_limit'],
            dailySpent=wallet['daily_spent'],
            remainingDailyLimit=remaining,
            isRegistered=bool(wallet['registry_registered']),
        ))

    return AgentWalletListResponse(wallets=result)


@router.post("/agent/wallet/{agent_id}/deposit", response_model=AgentDepositResponse)
async def deposit_to_agent(
    agent_id: str,
    request: AgentDepositRequest,
    user: dict = Depends(get_current_user)
):
    """Deposit VIBE to agent wallet (from owner's balance)"""
    # 获取钱包信息
    wallet = get_agent_wallet(agent_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Agent wallet not found")

    # 验证是否是钱包的主人
    if wallet['owner_id'] != user['id']:
        raise HTTPException(status_code=403, detail="Not authorized")

    # 检查用户余额
    balance_info = get_user_balance_info(user['id'])
    if not balance_info or balance_info.get('vibe_balance', 0) < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # 扣除用户余额
    update_user_balance(user['id'], request.amount, deduct=True)

    # 增加 Agent 钱包余额
    update_agent_balance(agent_id, request.amount, deduct=False)

    # 自动质押
    MIN_STAKE = 100
    new_staked = wallet['staked_amount']
    if wallet['staked_amount'] < MIN_STAKE:
        stake_amount = min(request.amount, MIN_STAKE - wallet['staked_amount'])
        update_agent_balance(agent_id, stake_amount, deduct=True)
        update_agent_stake(agent_id, stake_amount, deduct=False)
        new_staked += stake_amount

    # 获取更新后的余额
    updated_wallet = get_agent_wallet(agent_id)

    return AgentDepositResponse(
        success=True,
        agentId=agent_id,
        newBalance=updated_wallet['vibe_balance'],
        newStakedAmount=updated_wallet['staked_amount'],
        message=f"Deposited {request.amount} VIBE to agent wallet"
    )


@router.post("/agent/wallet/{agent_id}/transfer", response_model=AgentTransferResponse)
async def transfer_from_agent(
    agent_id: str,
    request: AgentTransferRequest,
    user: dict = Depends(get_current_user)
):
    """Transfer VIBE from agent wallet (auto within limits, needs approval for large amounts)"""
    stake_required = os.environ.get("STAKE_REQUIRED", "true").lower() == "true"

    # 如果关闭了质押限制，直接返回模拟成功
    if not stake_required:
        return AgentTransferResponse(
            success=True,
            agentId=agent_id,
            toAddress=request.to_address,
            amount=request.amount,
            newBalance=0,
            message="Stake requirement is disabled"
        )

    # 获取钱包信息
    wallet = get_agent_wallet(agent_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Agent wallet not found")

    # 验证是否是钱包的主人
    if wallet['owner_id'] != user['id']:
        raise HTTPException(status_code=403, detail="Not authorized")

    # 检查余额
    if wallet['vibe_balance'] < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # 检查是否需要审批
    needs_approval = request.amount > wallet['max_per_tx']
    daily_spent = wallet['daily_spent']
    if wallet.get('last_reset_time'):
        import time
        if time.time() - wallet['last_reset_time'] >= 86400:
            daily_spent = 0

    if daily_spent + request.amount > wallet['daily_limit']:
        raise HTTPException(status_code=400, detail="Exceeds daily limit")

    # 执行转账
    update_agent_balance(agent_id, request.amount, deduct=True)
    update_agent_daily_spent(agent_id, request.amount)

    # 获取更新后的余额
    updated_wallet = get_agent_wallet(agent_id)

    return AgentTransferResponse(
        success=True,
        agentId=agent_id,
        toAddress=request.to_address,
        amount=request.amount,
        newBalance=updated_wallet['vibe_balance'],
        message="Transfer successful" if not needs_approval else "Large transfer processed"
    )


@router.post("/agent/wallet/{agent_id}/stake")
async def stake_agent(
    agent_id: str,
    request: AgentDepositRequest,
    user: dict = Depends(get_current_user)
):
    """Stake VIBE from agent wallet"""
    stake_required = os.environ.get("STAKE_REQUIRED", "true").lower() == "true"

    if not stake_required:
        return {"success": True, "message": "Stake requirement is disabled"}

    # 获取钱包信息
    wallet = get_agent_wallet(agent_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Agent wallet not found")

    if wallet['owner_id'] != user['id']:
        raise HTTPException(status_code=403, detail="Not authorized")

    if wallet['vibe_balance'] < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # 扣除余额并增加质押
    update_agent_balance(agent_id, request.amount, deduct=True)
    update_agent_stake(agent_id, request.amount, deduct=False)

    updated_wallet = get_agent_wallet(agent_id)

    return {
        "success": True,
        "agentId": agent_id,
        "newBalance": updated_wallet['vibe_balance'],
        "newStakedAmount": updated_wallet['staked_amount'],
        "message": f"Staked {request.amount} VIBE"
    }


@router.post("/agent/wallet/{agent_id}/unstake")
async def unstake_agent(
    agent_id: str,
    request: AgentDepositRequest,
    user: dict = Depends(get_current_user)
):
    """Unstake VIBE from agent wallet (starts unlock period)"""
    stake_required = os.environ.get("STAKE_REQUIRED", "true").lower() == "true"

    if not stake_required:
        return {"success": True, "message": "Stake requirement is disabled"}

    wallet = get_agent_wallet(agent_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Agent wallet not found")

    if wallet['owner_id'] != user['id']:
        raise HTTPException(status_code=403, detail="Not authorized")

    if wallet['staked_amount'] < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient staked amount")

    if wallet['stake_status'] != 'staked':
        raise HTTPException(status_code=400, detail="No active stake")

    import time
    unstaking_period_days = int(os.environ.get("UNSTAKING_PERIOD_DAYS", "7"))
    unlock_available_at = time.time() + unstaking_period_days * 86400

    # 执行解除质押
    update_agent_stake(agent_id, request.amount, deduct=True)
    update_agent_balance(agent_id, request.amount, deduct=False)

    return {
        "success": True,
        "agentId": agent_id,
        "unlockedAmount": request.amount,
        "unlockAvailableAt": int(unlock_available_at),
        "message": f"Unstake initiated. Tokens will be available in {unstaking_period_days} days."
    }


@router.post("/agent/wallet/{agent_id}/limits")
async def update_agent_wallet_limits(
    agent_id: str,
    request: AgentLimitsRequest,
    user: dict = Depends(get_current_user)
):
    """Update agent wallet limits"""
    wallet = get_agent_wallet(agent_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Agent wallet not found")

    if wallet['owner_id'] != user['id']:
        raise HTTPException(status_code=403, detail="Not authorized")

    update_agent_limits(agent_id, request.max_per_tx, request.daily_limit)

    return {
        "success": True,
        "agentId": agent_id,
        "maxPerTx": request.max_per_tx,
        "dailyLimit": request.daily_limit,
        "message": "Limits updated successfully"
    }


@router.delete("/agent/wallet/{agent_id}")
async def delete_agent_wallet(
    agent_id: str,
    user: dict = Depends(get_current_user)
):
    """Delete agent wallet (emergency)"""
    wallet = get_agent_wallet(agent_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Agent wallet not found")

    if wallet['owner_id'] != user['id']:
        raise HTTPException(status_code=403, detail="Not authorized")

    delete_agent_wallet(agent_id)

    return {"success": True, "message": "Agent wallet deleted"}
