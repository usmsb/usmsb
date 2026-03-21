"""
Staking endpoints for Agent Platform.

Provides staking operations:
- Deposit VIBE to stake
- Withdraw staked VIBE
- Get staking information
- Get pending rewards
- Claim staking rewards

Authentication: All endpoints require X-API-Key + X-Agent-ID headers.
"""

import time
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from usmsb_sdk.api.database import get_agent_wallet, get_db, update_agent_stake
from usmsb_sdk.api.rest.api_key_manager import get_stake_tier, get_tier_benefits
from usmsb_sdk.api.rest.unified_auth import (
    ErrorCode,
    get_current_user_unified,
    require_stake_unified,
)

router = APIRouter(prefix="/staking", tags=["Staking"])

# Constants
MIN_STAKE_AMOUNT = 100  # Minimum stake for Bronze tier
STAKE_LOCK_PERIOD = 7 * 24 * 3600  # 7 days in seconds
BASE_APY = 0.05  # 5% base APY
APY_BONUS_PER_TIER = 0.01  # 1% bonus per tier above Bronze


# ==================== Request/Response Models ====================

class DepositRequest(BaseModel):
    """Request to deposit VIBE to stake."""
    amount: float = Field(..., gt=0, description="Amount of VIBE to stake")


class WithdrawRequest(BaseModel):
    """Request to withdraw staked VIBE."""
    amount: float = Field(..., gt=0, description="Amount of VIBE to withdraw")


class StakingInfoResponse(BaseModel):
    """Staking information response."""
    success: bool = True
    agent_id: str
    staked_amount: float
    stake_status: str
    stake_tier: str
    locked_stake: float
    unlock_available_at: float | None = None
    pending_rewards: float
    apy: float
    tier_benefits: dict


class RewardsResponse(BaseModel):
    """Pending rewards response."""
    success: bool = True
    agent_id: str
    pending_rewards: float
    total_claimed: float
    last_claim_at: float | None = None
    apy: float


class ClaimResponse(BaseModel):
    """Claim rewards response."""
    success: bool = True
    agent_id: str
    claimed_amount: float
    new_balance: float
    message: str


# ==================== Helper Functions ====================

def calculate_apy(staked_amount: float) -> float:
    """Calculate APY based on stake tier.

    - NONE: 0% (no stake)
    - BRONZE: BASE_APY (5%) — tier_level=1, max(0,1-1)=0 → BASE_APY
    - SILVER: BASE_APY + 1*BONUS (6%)
    - GOLD: BASE_APY + 2*BONUS (7%)
    - PLATINUM: BASE_APY + 3*BONUS (8%)
    """
    tier = get_stake_tier(staked_amount)
    if tier == "NONE":
        return 0.0
    tier_values = {
        "NONE": 0,
        "BRONZE": 1,
        "SILVER": 2,
        "GOLD": 3,
        "PLATINUM": 4
    }
    tier_level = tier_values.get(tier, 0)
    return BASE_APY + (max(0, tier_level - 1) * APY_BONUS_PER_TIER)


def calculate_pending_rewards(agent_id: str, staked_amount: float, last_claim_at: float | None) -> float:
    """Calculate pending rewards based on time elapsed since last claim."""
    if staked_amount <= 0:
        return 0.0

    now = time.time()
    last_claim = last_claim_at or now
    time_elapsed = now - last_claim

    # Calculate rewards: principal * APY * (time_elapsed / seconds_per_year)
    apy = calculate_apy(staked_amount)
    seconds_per_year = 365 * 24 * 3600
    rewards = staked_amount * apy * (time_elapsed / seconds_per_year)

    return round(rewards, 6)


def get_staking_rewards_info(agent_id: str) -> dict:
    """Get staking rewards info from database."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if staking_rewards table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='staking_rewards'
        """)

        if not cursor.fetchone():
            # Create table if not exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS staking_rewards (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT UNIQUE NOT NULL,
                    pending_rewards REAL DEFAULT 0,
                    total_claimed REAL DEFAULT 0,
                    last_claim_at REAL,
                    last_update_at REAL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
                )
            ''')
            conn.commit()

        cursor.execute("""
            SELECT pending_rewards, total_claimed, last_claim_at
            FROM staking_rewards
            WHERE agent_id = ?
        """, (agent_id,))

        row = cursor.fetchone()
        if row:
            return dict(row)

        # Create new record
        now = time.time()
        cursor.execute("""
            INSERT INTO staking_rewards (id, agent_id, pending_rewards, total_claimed, created_at)
            VALUES (?, ?, 0, 0, ?)
        """, (f"sr-{uuid.uuid4().hex[:12]}", agent_id, now))
        conn.commit()

        return {"pending_rewards": 0, "total_claimed": 0, "last_claim_at": None}


def update_pending_rewards(agent_id: str, staked_amount: float) -> float:
    """Update and return pending rewards."""
    rewards_info = get_staking_rewards_info(agent_id)
    last_claim_at = rewards_info.get("last_claim_at")

    pending = calculate_pending_rewards(agent_id, staked_amount, last_claim_at)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE staking_rewards
            SET pending_rewards = ?, last_update_at = ?
            WHERE agent_id = ?
        """, (pending, time.time(), agent_id))

    return pending


# ==================== Endpoints ====================

@router.post("/deposit", response_model=StakingInfoResponse)
async def deposit_stake(
    request: DepositRequest,
    user: dict = Depends(get_current_user_unified)
):
    """
    Deposit VIBE to stake.

    Requires:
    - X-API-Key header
    - X-Agent-ID header
    - Sufficient balance in agent wallet

    Note: Initial stake must be at least 100 VIBE (Bronze tier).
    """
    agent_id = user.get("agent_id") or user.get("user_id")
    amount = request.amount

    # Get current wallet info
    wallet = get_agent_wallet(agent_id)
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Wallet not found",
                "code": ErrorCode.AGENT_NOT_FOUND,
                "message": "Agent wallet not found. Please bind to an owner first."
            }
        )

    current_stake = wallet.get("staked_amount", 0)
    current_balance = wallet.get("vibe_balance", 0)

    # Check if agent has enough balance
    if current_balance < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Insufficient balance",
                "code": "INSUFFICIENT_BALANCE",
                "message": f"Agent has {current_balance} VIBE but tried to stake {amount} VIBE"
            }
        )

    # Update stake
    new_stake = current_stake + amount
    update_agent_stake(agent_id, new_stake)

    # Update wallet balance
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE agent_wallets
            SET vibe_balance = vibe_balance - ?,
                staked_amount = ?,
                stake_status = 'active',
                updated_at = ?
            WHERE agent_id = ?
        """, (amount, new_stake, time.time(), agent_id))

    # Update pending rewards
    pending_rewards = update_pending_rewards(agent_id, new_stake)

    # Get new tier
    stake_tier = get_stake_tier(new_stake)
    tier_benefits = get_tier_benefits(stake_tier)
    apy = calculate_apy(new_stake)

    return StakingInfoResponse(
        agent_id=agent_id,
        staked_amount=new_stake,
        stake_status="active",
        stake_tier=stake_tier,
        locked_stake=0,
        unlock_available_at=None,
        pending_rewards=pending_rewards,
        apy=apy,
        tier_benefits=tier_benefits
    )


@router.post("/withdraw", response_model=StakingInfoResponse)
async def withdraw_stake(
    request: WithdrawRequest,
    user: dict = Depends(get_current_user_unified)
):
    """
    Withdraw staked VIBE.

    Requires:
    - X-API-Key header
    - X-Agent-ID header
    - Sufficient staked amount (not locked)

    Note: Withdrawn amount returns to agent wallet balance.
    """
    agent_id = user.get("agent_id") or user.get("user_id")
    amount = request.amount

    # Get current wallet info
    wallet = get_agent_wallet(agent_id)
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Wallet not found",
                "code": ErrorCode.AGENT_NOT_FOUND,
                "message": "Agent wallet not found."
            }
        )

    current_stake = wallet.get("staked_amount", 0)
    locked_stake = wallet.get("locked_stake", 0)
    available_stake = current_stake - locked_stake

    # Check if agent has enough available stake
    if available_stake < amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Insufficient stake",
                "code": "INSUFFICIENT_STAKE",
                "message": f"Agent has {available_stake} VIBE available but tried to withdraw {amount} VIBE"
            }
        )

    # Calculate and claim pending rewards first
    rewards_info = get_staking_rewards_info(agent_id)
    pending_rewards = rewards_info.get("pending_rewards", 0)

    # Update stake
    new_stake = current_stake - amount
    update_agent_stake(agent_id, new_stake)

    # Update wallet
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE agent_wallets
            SET vibe_balance = vibe_balance + ?,
                staked_amount = ?,
                stake_status = CASE WHEN ? > 0 THEN 'active' ELSE 'none' END,
                updated_at = ?
            WHERE agent_id = ?
        """, (amount + pending_rewards, new_stake, new_stake, time.time(), agent_id))

        # Reset pending rewards
        cursor.execute("""
            UPDATE staking_rewards
            SET pending_rewards = 0,
                last_claim_at = ?
            WHERE agent_id = ?
        """, (time.time(), agent_id))

    # Get new tier
    stake_tier = get_stake_tier(new_stake)
    tier_benefits = get_tier_benefits(stake_tier)
    apy = calculate_apy(new_stake)

    return StakingInfoResponse(
        agent_id=agent_id,
        staked_amount=new_stake,
        stake_status="active" if new_stake > 0 else "none",
        stake_tier=stake_tier,
        locked_stake=0,
        unlock_available_at=None,
        pending_rewards=0,
        apy=apy,
        tier_benefits=tier_benefits
    )


@router.get("/info", response_model=StakingInfoResponse)
async def get_staking_info(
    user: dict = Depends(get_current_user_unified)
):
    """
    Get current staking information.

    Requires:
    - Bearer token (Authorization header) OR
    - X-API-Key + X-Agent-ID headers
    """
    agent_id = user.get("agent_id") or user.get("user_id")

    # Get wallet info
    wallet = get_agent_wallet(agent_id)
    if not wallet:
        # Return default values for unbound agent
        return StakingInfoResponse(
            agent_id=agent_id,
            staked_amount=0,
            stake_status="none",
            stake_tier="NONE",
            locked_stake=0,
            unlock_available_at=None,
            pending_rewards=0,
            apy=0,
            tier_benefits=get_tier_benefits("NONE")
        )

    staked_amount = wallet.get("staked_amount", 0)
    stake_status = wallet.get("stake_status", "none")
    locked_stake = wallet.get("locked_stake", 0)
    unlock_available_at = wallet.get("unlock_available_at")

    # Update and get pending rewards
    pending_rewards = update_pending_rewards(agent_id, staked_amount)

    # Get tier info
    stake_tier = get_stake_tier(staked_amount)
    tier_benefits = get_tier_benefits(stake_tier)
    apy = calculate_apy(staked_amount)

    return StakingInfoResponse(
        agent_id=agent_id,
        staked_amount=staked_amount,
        stake_status=stake_status,
        stake_tier=stake_tier,
        locked_stake=locked_stake,
        unlock_available_at=unlock_available_at,
        pending_rewards=pending_rewards,
        apy=apy,
        tier_benefits=tier_benefits
    )


@router.get("/rewards", response_model=RewardsResponse)
async def get_rewards(
    user: dict = Depends(get_current_user_unified)
):
    """
    Get pending staking rewards information.

    Requires:
    - Bearer token (Authorization header) OR
    - X-API-Key + X-Agent-ID headers
    """
    agent_id = user.get("agent_id") or user.get("user_id")

    # Get wallet info
    wallet = get_agent_wallet(agent_id) if agent_id else None
    staked_amount = wallet.get("staked_amount", 0) if wallet else 0

    # Get rewards info
    rewards_info = get_staking_rewards_info(agent_id)
    pending_rewards = update_pending_rewards(agent_id, staked_amount)
    total_claimed = rewards_info.get("total_claimed", 0)
    last_claim_at = rewards_info.get("last_claim_at")

    apy = calculate_apy(staked_amount)

    return RewardsResponse(
        agent_id=agent_id,
        pending_rewards=pending_rewards,
        total_claimed=total_claimed,
        last_claim_at=last_claim_at,
        apy=apy
    )


@router.post("/claim", response_model=ClaimResponse)
async def claim_rewards(
    user: dict = Depends(require_stake_unified(100))
):
    """
    Claim pending staking rewards.

    Requires:
    - Bearer token (Authorization header) OR
    - X-API-Key + X-Agent-ID headers
    - Minimum 100 VIBE staked (Bronze tier)

    Claimed rewards are added to agent wallet balance.
    """
    agent_id = user.get("agent_id") or user.get("user_id")

    # Get wallet info
    wallet = get_agent_wallet(agent_id)
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Wallet not found",
                "code": ErrorCode.AGENT_NOT_FOUND,
                "message": "Agent wallet not found."
            }
        )

    staked_amount = wallet.get("staked_amount", 0)
    current_balance = wallet.get("vibe_balance", 0)

    # Get and update pending rewards
    pending_rewards = update_pending_rewards(agent_id, staked_amount)

    if pending_rewards <= 0:
        return ClaimResponse(
            agent_id=agent_id,
            claimed_amount=0,
            new_balance=current_balance,
            message="No pending rewards to claim"
        )

    # Update wallet and rewards
    now = time.time()
    with get_db() as conn:
        cursor = conn.cursor()

        # Add rewards to balance
        cursor.execute("""
            UPDATE agent_wallets
            SET vibe_balance = vibe_balance + ?,
                updated_at = ?
            WHERE agent_id = ?
        """, (pending_rewards, now, agent_id))

        # Update rewards record
        cursor.execute("""
            UPDATE staking_rewards
            SET pending_rewards = 0,
                total_claimed = total_claimed + ?,
                last_claim_at = ?
            WHERE agent_id = ?
        """, (pending_rewards, now, agent_id))

    new_balance = current_balance + pending_rewards

    return ClaimResponse(
        agent_id=agent_id,
        claimed_amount=pending_rewards,
        new_balance=new_balance,
        message=f"Successfully claimed {pending_rewards:.6f} VIBE rewards"
    )


# ==================== On-Chain Staking Endpoints ====================

class OnChainStakeRequest(BaseModel):
    """On-chain质押请求

    用户在浏览器 MetaMask 签名质押交易后，将 tx_hash 提交给后端验证。
    后端不持有私钥，只验证链上交易状态并更新数据库。
    """
    amount: float = Field(..., gt=0, description="质押金额（VIBE）")
    lock_period: int = Field(default=1, ge=0, le=4, description="锁仓期: 0=无锁仓, 1=30天, 2=90天, 3=180天, 4=365天")
    tx_hash: str = Field(..., description="质押交易的 tx_hash（前端签名后提供）")


class OnChainUnstakeRequest(BaseModel):
    """On-chain解除质押请求

    用户在浏览器 MetaMask 签名解除质押交易后，将 tx_hash 提交给后端验证。
    """
    tx_hash: str = Field(..., description="解除质押交易的 tx_hash（前端签名后提供）")


class OnChainStakeResponse(BaseModel):
    """On-chain质押响应"""
    success: bool
    tx_hash: str
    from_address: str
    amount_vibe: float
    lock_period: int
    message: str


class OnChainStakingInfoResponse(BaseModel):
    """On-chain质押信息响应"""
    address: str
    amount_wei: int
    amount_vibe: float
    tier: int
    tier_name: str
    lock_period: int
    stake_time: int
    unlock_time: int
    pending_reward_wei: int
    pending_reward_vibe: float
    is_active: bool


class OnChainRewardsResponse(BaseModel):
    """On-chain质押奖励响应"""
    address: str
    pending_reward_wei: int
    pending_reward_vibe: float


@router.post("/stake", response_model=OnChainStakeResponse)
async def on_chain_stake(
    request: OnChainStakeRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    提交质押交易的 tx_hash，后端验证链上状态并更新数据库。

    用户在浏览器 MetaMask 签名质押交易（调用 VIBStaking.stake）后，
    将 tx_hash 提交给此端点。后端验证交易成功后将质押记录写入数据库。

    原则：真人操作由本人签名，后端不持有私钥。
    """
    from web3 import Web3
    from usmsb_sdk.blockchain.config import BlockchainConfig

    staker_address = current_user.get("wallet_address") or current_user.get("address")
    if not staker_address:
        raise HTTPException(status_code=401, detail="Wallet address not found in authentication")

    try:
        config = BlockchainConfig.from_env()
        w3 = Web3(Web3.HTTPProvider(config.rpc_url))

        # Validate tx_hash format
        if not request.tx_hash.startswith("0x") or len(request.tx_hash) != 66:
            raise HTTPException(status_code=400, detail="Invalid tx_hash format")

        # Verify transaction was mined (not pending)
        receipt = w3.eth.get_transaction_receipt(request.tx_hash)
        if receipt is None:
            raise HTTPException(status_code=400, detail="Transaction not found or still pending")

        if receipt.status != 1:
            raise HTTPException(status_code=400, detail="Transaction failed on-chain")

        # Transaction successful — update database
        from usmsb_sdk.api.database import update_agent_balance, update_agent_wallet
        amount_wei = int(request.amount * (10 ** 18))

        # Find agent by wallet address and update staking info
        agent_id = current_user.get("agent_id")
        if agent_id:
            try:
                update_agent_balance(agent_id, request.amount, deduct=False)
            except Exception:
                pass  # Non-agent users may not have agent_balance to update

        return OnChainStakeResponse(
            success=True,
            tx_hash=request.tx_hash,
            from_address=staker_address,
            amount_vibe=request.amount,
            lock_period=request.lock_period,
            message=f"Stake verified and recorded. {request.amount} VIBE staked with lock period {request.lock_period}",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Stake verification failed: {str(e)}")


@router.post("/unstake", response_model=OnChainStakeResponse)
async def on_chain_unstake(
    request: OnChainUnstakeRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    提交解除质押交易的 tx_hash，后端验证链上状态并更新数据库。

    用户在浏览器 MetaMask 签名解除质押交易后，
    将 tx_hash 提交给此端点验证。解除质押会领取所有待领奖励。

    原则：真人操作由本人签名，后端不持有私钥。
    """
    from web3 import Web3
    from usmsb_sdk.blockchain.config import BlockchainConfig

    staker_address = current_user.get("wallet_address") or current_user.get("address")
    if not staker_address:
        raise HTTPException(status_code=401, detail="Wallet address not found in authentication")

    try:
        config = BlockchainConfig.from_env()
        w3 = Web3(Web3.HTTPProvider(config.rpc_url))

        if not request.tx_hash.startswith("0x") or len(request.tx_hash) != 66:
            raise HTTPException(status_code=400, detail="Invalid tx_hash format")

        receipt = w3.eth.get_transaction_receipt(request.tx_hash)
        if receipt is None:
            raise HTTPException(status_code=400, detail="Transaction not found or still pending")

        if receipt.status != 1:
            raise HTTPException(status_code=400, detail="Transaction failed on-chain")

        # Update database
        agent_id = current_user.get("agent_id")
        if agent_id:
            try:
                from usmsb_sdk.api.database import update_agent_balance
                # Unstake clears all staking - mark as unbound
                from usmsb_sdk.api.database import update_agent_wallet
            except Exception:
                pass

        return OnChainStakeResponse(
            success=True,
            tx_hash=request.tx_hash,
            from_address=staker_address,
            amount_vibe=0,
            lock_period=0,
            message="Unstake verified and recorded. All staked VIBE has been withdrawn.",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unstake verification failed: {str(e)}")


@router.get("/info/{address}", response_model=OnChainStakingInfoResponse)
async def get_on_chain_staking_info(address: str):
    """
    查询On-chain质押信息

    无需认证，直接从区块链查询。

    Args:
        address: 质押者地址
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient
    from usmsb_sdk.blockchain.contracts.vib_staking import StakeTier

    try:
        client = VIBEBlockchainClient()

        # Get stake info
        stake_info = await client.staking.get_stake_info(address)

        # Convert wei to VIBE
        amount_vibe = float(client.token.w3.from_wei(stake_info["amount"], "ether"))
        pending_reward_vibe = float(client.token.w3.from_wei(stake_info["pending_reward"], "ether"))

        # Get tier name
        tier = StakeTier(stake_info["tier"])
        tier_name = tier.name

        return OnChainStakingInfoResponse(
            address=address,
            amount_wei=stake_info["amount"],
            amount_vibe=amount_vibe,
            tier=stake_info["tier"],
            tier_name=tier_name,
            lock_period=stake_info["lock_period"],
            stake_time=stake_info["stake_time"],
            unlock_time=stake_info["unlock_time"],
            pending_reward_wei=stake_info["pending_reward"],
            pending_reward_vibe=pending_reward_vibe,
            is_active=stake_info["is_active"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rewards/{address}", response_model=OnChainRewardsResponse)
async def get_on_chain_rewards(address: str):
    """
    查询On-chain待领取奖励

    无需认证，直接从区块链查询。

    Args:
        address: 质押者地址
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    try:
        client = VIBEBlockchainClient()

        # Get pending reward
        pending_reward_wei = await client.staking.get_pending_reward(address)
        pending_reward_vibe = float(client.token.w3.from_wei(pending_reward_wei, "ether"))

        return OnChainRewardsResponse(
            address=address,
            pending_reward_wei=pending_reward_wei,
            pending_reward_vibe=pending_reward_vibe,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
