"""
Wallet endpoints for Agent Platform.

Provides wallet operations:
- Get wallet balance
- Get transaction history

Authentication: Supports both Bearer token and API Key authentication.
"""

import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from usmsb_sdk.api.database import get_db, get_agent_wallet
from usmsb_sdk.api.rest.unified_auth import get_current_user_unified, ErrorCode
from usmsb_sdk.api.rest.api_key_manager import get_stake_tier, get_tier_benefits

router = APIRouter(prefix="/wallet", tags=["Wallet"])


# ==================== Request/Response Models ====================

class WalletBalanceResponse(BaseModel):
    """Wallet balance response."""
    success: bool = True
    agent_id: str
    balance: float
    staked_amount: float
    locked_amount: float
    pending_rewards: float
    total_assets: float
    stake_tier: str
    tier_benefits: dict


class TransactionRecord(BaseModel):
    """Single transaction record."""
    id: str
    transaction_type: str
    amount: float
    status: str
    counterparty_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    created_at: float
    completed_at: Optional[float] = None


class TransactionHistoryResponse(BaseModel):
    """Transaction history response."""
    success: bool = True
    agent_id: str
    transactions: List[TransactionRecord]
    total_count: int
    page: int
    page_size: int


# ==================== Helper Functions ====================

def get_pending_rewards(agent_id: str) -> float:
    """Get pending staking rewards for agent."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check if staking_rewards table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='staking_rewards'
        """)

        if cursor.fetchone():
            cursor.execute("""
                SELECT pending_rewards FROM staking_rewards WHERE agent_id = ?
            """, (agent_id,))
            row = cursor.fetchone()
            if row:
                return row["pending_rewards"] or 0

    return 0.0


def get_wallet_transactions(
    agent_id: str,
    tx_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[dict]:
    """Get wallet transactions for agent."""
    with get_db() as conn:
        cursor = conn.cursor()

        if tx_type:
            cursor.execute("""
                SELECT id, transaction_type, amount, status, buyer_id, seller_id,
                       title, description, created_at, completed_at
                FROM transactions
                WHERE (buyer_id = ? OR seller_id = ?) AND transaction_type = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (agent_id, agent_id, tx_type, limit, offset))
        else:
            cursor.execute("""
                SELECT id, transaction_type, amount, status, buyer_id, seller_id,
                       title, description, created_at, completed_at
                FROM transactions
                WHERE buyer_id = ? OR seller_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (agent_id, agent_id, limit, offset))

        return [dict(row) for row in cursor.fetchall()]


def count_wallet_transactions(agent_id: str, tx_type: Optional[str] = None) -> int:
    """Count wallet transactions for agent."""
    with get_db() as conn:
        cursor = conn.cursor()

        if tx_type:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM transactions
                WHERE (buyer_id = ? OR seller_id = ?) AND transaction_type = ?
            """, (agent_id, agent_id, tx_type))
        else:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM transactions
                WHERE buyer_id = ? OR seller_id = ?
            """, (agent_id, agent_id))

        return cursor.fetchone()["count"]


# ==================== Endpoints ====================

@router.get("/balance", response_model=WalletBalanceResponse)
async def get_balance(
    user: dict = Depends(get_current_user_unified)
):
    """
    Get agent's wallet balance.

    Requires:
    - Bearer token (Authorization header) OR
    - X-API-Key + X-Agent-ID headers

    Returns:
    - Available VIBE balance
    - Staked amount
    - Locked amount
    - Pending rewards
    - Total assets
    - Stake tier and benefits
    """
    agent_id = user.get("agent_id") or user.get("user_id")

    # Get wallet info
    wallet = get_agent_wallet(agent_id)

    if not wallet:
        # Return default values for unbound agent
        return WalletBalanceResponse(
            agent_id=agent_id,
            balance=0,
            staked_amount=0,
            locked_amount=0,
            pending_rewards=0,
            total_assets=0,
            stake_tier="NONE",
            tier_benefits=get_tier_benefits("NONE")
        )

    balance = wallet.get("vibe_balance", 0)
    staked_amount = wallet.get("staked_amount", 0)
    locked_amount = wallet.get("locked_stake", 0)
    pending_rewards = get_pending_rewards(agent_id)

    total_assets = balance + staked_amount + pending_rewards

    # Get tier info
    stake_tier = get_stake_tier(staked_amount)
    tier_benefits = get_tier_benefits(stake_tier)

    return WalletBalanceResponse(
        agent_id=agent_id,
        balance=balance,
        staked_amount=staked_amount,
        locked_amount=locked_amount,
        pending_rewards=pending_rewards,
        total_assets=total_assets,
        stake_tier=stake_tier,
        tier_benefits=tier_benefits
    )


@router.get("/transactions", response_model=TransactionHistoryResponse)
async def get_transactions(
    type: Optional[str] = Query(None, description="Filter by transaction type"),
    limit: int = Query(50, ge=1, le=200, description="Number of transactions per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    user: dict = Depends(get_current_user_unified)
):
    """
    Get agent's transaction history.

    Requires:
    - Bearer token (Authorization header) OR
    - X-API-Key + X-Agent-ID headers

    Query Parameters:
    - type: Filter by transaction type (optional)
      - service_payment: Payment for services
      - stake_deposit: Staking deposit
      - stake_withdraw: Staking withdrawal
      - reward_claim: Staking reward claim
      - collaboration: Collaboration payment
    - limit: Number of transactions to return (default: 50, max: 200)
    - offset: Number of transactions to skip (for pagination)

    Returns:
    - List of transactions
    - Total count
    - Pagination info
    """
    agent_id = user.get("agent_id") or user.get("user_id")

    # Get transactions
    transactions = get_wallet_transactions(agent_id, type, limit, offset)
    total_count = count_wallet_transactions(agent_id, type)

    records = []
    for tx in transactions:
        # Determine counterparty
        if tx["buyer_id"] == agent_id:
            counterparty = tx["seller_id"]
        else:
            counterparty = tx["buyer_id"]

        records.append(TransactionRecord(
            id=tx["id"],
            transaction_type=tx["transaction_type"] or "service_payment",
            amount=tx["amount"],
            status=tx["status"],
            counterparty_id=counterparty,
            title=tx["title"],
            description=tx["description"],
            created_at=tx["created_at"] or 0,
            completed_at=tx["completed_at"]
        ))

    page = (offset // limit) + 1 if limit > 0 else 1

    return TransactionHistoryResponse(
        agent_id=agent_id,
        transactions=records,
        total_count=total_count,
        page=page,
        page_size=limit
    )


@router.get("/transactions/{transaction_id}", response_model=TransactionRecord)
async def get_transaction(
    transaction_id: str,
    user: dict = Depends(get_current_user_unified)
):
    """
    Get details of a specific transaction.

    Requires:
    - Bearer token (Authorization header) OR
    - X-API-Key + X-Agent-ID headers

    The agent must be either the buyer or seller in the transaction.
    """
    agent_id = user.get("agent_id") or user.get("user_id")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, transaction_type, amount, status, buyer_id, seller_id,
                   title, description, created_at, completed_at
            FROM transactions
            WHERE id = ? AND (buyer_id = ? OR seller_id = ?)
        """, (transaction_id, agent_id, agent_id))

        tx = cursor.fetchone()

        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Transaction not found",
                    "code": "NOT_FOUND",
                    "message": "Transaction not found or you don't have access to it"
                }
            )

        tx_dict = dict(tx)

        # Determine counterparty
        if tx_dict["buyer_id"] == agent_id:
            counterparty = tx_dict["seller_id"]
        else:
            counterparty = tx_dict["buyer_id"]

        return TransactionRecord(
            id=tx_dict["id"],
            transaction_type=tx_dict["transaction_type"] or "service_payment",
            amount=tx_dict["amount"],
            status=tx_dict["status"],
            counterparty_id=counterparty,
            title=tx_dict["title"],
            description=tx_dict["description"],
            created_at=tx_dict["created_at"] or 0,
            completed_at=tx_dict["completed_at"]
        )
