"""
Transaction API endpoints for AI Civilization Platform

Implements the complete transaction flow:
1. Create - Buyer creates transaction
2. Escrow - Buyer locks funds in escrow
3. In Progress - Seller works on delivery
4. Delivered - Seller submits delivery
5. Completed - Buyer accepts, funds released
6. Disputed/Cancelled - Exception handling
"""
import logging
import secrets
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Header, Query
from pydantic import BaseModel, Field

from usmsb_sdk.api.database import (
    create_transaction,
    get_transaction,
    get_transactions_by_user,
    get_all_transactions,
    update_transaction_status,
    get_transaction_stats,
    TransactionStatus,
    get_user_by_address,
    get_agent,
    update_user_stake,
    get_db,
)
from usmsb_sdk.api.rest.auth import get_current_user, get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["Transactions"])


# ==================== Pydantic Models ====================

class TransactionCreate(BaseModel):
    """Schema for creating a transaction."""
    seller_id: str
    demand_id: Optional[str] = None
    service_id: Optional[str] = None
    amount: float = Field(..., gt=0)
    title: str
    description: str = ""
    transaction_type: str = "service_payment"


class EscrowRequest(BaseModel):
    """Schema for escrowing funds."""
    transaction_hash: Optional[str] = None


class DeliveryRequest(BaseModel):
    """Schema for submitting delivery."""
    description: str
    files: List[str] = Field(default_factory=list)


class AcceptRequest(BaseModel):
    """Schema for accepting delivery."""
    rating: int = Field(default=5, ge=1, le=5)
    review: str = ""


class DisputeRequest(BaseModel):
    """Schema for raising a dispute."""
    reason: str


class ResolveDisputeRequest(BaseModel):
    """Schema for resolving a dispute (admin only)."""
    resolution: str
    refund_buyer: bool = False


class TransactionResponse(BaseModel):
    """Schema for transaction response."""
    id: str
    buyer_id: str
    seller_id: str
    amount: float
    platform_fee: float
    status: str
    title: str
    description: str
    delivery_description: Optional[str] = None
    rating: Optional[int] = None
    review: Optional[str] = None
    created_at: float
    updated_at: float
    escrowed_at: Optional[float] = None
    delivered_at: Optional[float] = None
    completed_at: Optional[float] = None


class TransactionListResponse(BaseModel):
    """Schema for transaction list response."""
    transactions: List[dict]
    total: int
    stats: dict


# ==================== Helper Functions ====================

def format_transaction(tx: dict) -> dict:
    """Format transaction for response."""
    return {
        "id": tx.get("id"),
        "buyer_id": tx.get("buyer_id"),
        "seller_id": tx.get("seller_id"),
        "demand_id": tx.get("demand_id"),
        "service_id": tx.get("service_id"),
        "amount": tx.get("amount"),
        "platform_fee": tx.get("platform_fee"),
        "status": tx.get("status"),
        "transaction_type": tx.get("transaction_type"),
        "title": tx.get("title"),
        "description": tx.get("description"),
        "delivery_description": tx.get("delivery_description"),
        "delivery_files": tx.get("delivery_files"),
        "rating": tx.get("rating"),
        "review": tx.get("review"),
        "dispute_reason": tx.get("dispute_reason"),
        "escrow_tx_hash": tx.get("escrow_tx_hash"),
        "release_tx_hash": tx.get("release_tx_hash"),
        "created_at": tx.get("created_at"),
        "updated_at": tx.get("updated_at"),
        "escrowed_at": tx.get("escrowed_at"),
        "delivered_at": tx.get("delivered_at"),
        "completed_at": tx.get("completed_at"),
    }


def validate_transaction_participant(tx: dict, user_id: str) -> str:
    """Validate user is a participant and return their role."""
    if tx.get("buyer_id") == user_id:
        return "buyer"
    elif tx.get("seller_id") == user_id:
        return "seller"
    else:
        raise HTTPException(status_code=403, detail="Not authorized for this transaction")


# ==================== API Endpoints ====================

@router.post("", response_model=TransactionResponse)
async def create_new_transaction(
    request: TransactionCreate,
    user: dict = Depends(get_current_user)
):
    """
    Create a new transaction.

    Buyer initiates a transaction with a seller.
    Status: created
    """
    # Validate seller exists
    seller = get_agent(request.seller_id)
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")

    # Create transaction
    tx_data = {
        "buyer_id": user["id"],
        "seller_id": request.seller_id,
        "demand_id": request.demand_id,
        "service_id": request.service_id,
        "amount": request.amount,
        "title": request.title,
        "description": request.description,
        "transaction_type": request.transaction_type,
    }

    tx = create_transaction(tx_data)
    logger.info(f"Transaction {tx['id']} created by {user['id']}")

    return format_transaction(tx)


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    status: Optional[str] = Query(None),
    role: Optional[str] = Query(None),  # "buyer" or "seller"
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user)
):
    """
    List transactions for the current user.

    Can filter by status and role (buyer/seller).
    """
    transactions = get_transactions_by_user(
        user_id=user["id"],
        role=role,
        status=status,
        limit=limit
    )

    stats = get_transaction_stats(user["id"])

    return {
        "transactions": [format_transaction(tx) for tx in transactions],
        "total": len(transactions),
        "stats": stats,
    }


@router.get("/all", response_model=TransactionListResponse)
async def list_all_transactions(
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    admin: dict = Depends(get_current_admin)
):
    """
    List all transactions (admin view).
    """
    transactions = get_all_transactions(limit=limit)

    if status:
        transactions = [tx for tx in transactions if tx.get("status") == status]

    stats = get_transaction_stats()

    return {
        "transactions": [format_transaction(tx) for tx in transactions],
        "total": len(transactions),
        "stats": stats,
    }


@router.get("/{transaction_id}")
async def get_transaction_details(
    transaction_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Get transaction details.
    """
    tx = get_transaction(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Validate user is participant
    validate_transaction_participant(tx, user["id"])

    return format_transaction(tx)


@router.post("/{transaction_id}/escrow")
async def escrow_funds(
    transaction_id: str,
    request: EscrowRequest,
    user: dict = Depends(get_current_user)
):
    """
    Lock funds in escrow.

    Buyer confirms they have locked the payment amount.
    Status: created -> escrowed
    """
    tx = get_transaction(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Only buyer can escrow
    role = validate_transaction_participant(tx, user["id"])
    if role != "buyer":
        raise HTTPException(status_code=403, detail="Only buyer can escrow funds")

    # Validate status
    if tx["status"] != TransactionStatus.CREATED:
        raise HTTPException(status_code=400, detail=f"Cannot escrow from status: {tx['status']}")

    # Check buyer has sufficient balance/stake
    buyer = get_user_by_address(user.get("wallet_address", ""))
    if buyer and buyer.get("stake", 0) < tx["amount"]:
        raise HTTPException(status_code=400, detail="Insufficient balance for escrow")

    # Use database transaction for atomicity
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            now = datetime.now().timestamp()

            # Update transaction status
            cursor.execute('''
                UPDATE transactions
                SET status = ?, escrow_tx_hash = ?, escrowed_at = ?, updated_at = ?
                WHERE id = ? AND status = ?
            ''', (TransactionStatus.ESCROWED, request.transaction_hash, now, now, transaction_id, TransactionStatus.CREATED))

            if cursor.rowcount == 0:
                raise HTTPException(status_code=400, detail="Transaction status changed, please retry")

            # Deduct from buyer's stake
            if buyer:
                cursor.execute('''
                    UPDATE users SET stake = stake - ?, updated_at = ? WHERE id = ?
                ''', (tx["amount"], now, buyer["id"]))

            conn.commit()

        # Get updated transaction
        updated_tx = get_transaction(transaction_id)
        logger.info(f"Transaction {transaction_id} escrowed by {user['id']}")

        return {
            "success": True,
            "transaction": format_transaction(updated_tx),
            "message": "Funds escrowed successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Escrow failed for transaction {transaction_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Escrow failed: {str(e)}")


@router.post("/{transaction_id}/start")
async def start_transaction(
    transaction_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Mark transaction as in progress.

    Seller confirms they are working on the delivery.
    Status: escrowed -> in_progress
    """
    tx = get_transaction(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Only seller can start
    role = validate_transaction_participant(tx, user["id"])
    if role != "seller":
        raise HTTPException(status_code=403, detail="Only seller can start transaction")

    # Validate status
    if tx["status"] != TransactionStatus.ESCROWED:
        raise HTTPException(status_code=400, detail=f"Cannot start from status: {tx['status']}")

    # Update transaction
    updated_tx = update_transaction_status(transaction_id, TransactionStatus.IN_PROGRESS)

    logger.info(f"Transaction {transaction_id} started by seller {user['id']}")

    return {
        "success": True,
        "transaction": format_transaction(updated_tx),
    }


@router.post("/{transaction_id}/deliver")
async def submit_delivery(
    transaction_id: str,
    request: DeliveryRequest,
    user: dict = Depends(get_current_user)
):
    """
    Submit delivery.

    Seller submits the completed work.
    Status: in_progress -> delivered
    """
    tx = get_transaction(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Only seller can deliver
    role = validate_transaction_participant(tx, user["id"])
    if role != "seller":
        raise HTTPException(status_code=403, detail="Only seller can submit delivery")

    # Validate status
    if tx["status"] not in [TransactionStatus.IN_PROGRESS, TransactionStatus.ESCROWED]:
        raise HTTPException(status_code=400, detail=f"Cannot deliver from status: {tx['status']}")

    # Update transaction
    updated_tx = update_transaction_status(
        transaction_id,
        TransactionStatus.DELIVERED,
        {
            "delivery_description": request.description,
            "delivery_files": request.files,
        }
    )

    logger.info(f"Transaction {transaction_id} delivered by seller {user['id']}")

    return {
        "success": True,
        "transaction": format_transaction(updated_tx),
        "message": "Delivery submitted successfully",
    }


@router.post("/{transaction_id}/accept")
async def accept_delivery(
    transaction_id: str,
    request: AcceptRequest,
    user: dict = Depends(get_current_user)
):
    """
    Accept delivery and release funds.

    Buyer confirms satisfaction with the delivery.
    Status: delivered -> completed
    """
    tx = get_transaction(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Only buyer can accept
    role = validate_transaction_participant(tx, user["id"])
    if role != "buyer":
        raise HTTPException(status_code=403, detail="Only buyer can accept delivery")

    # Validate status
    if tx["status"] != TransactionStatus.DELIVERED:
        raise HTTPException(status_code=400, detail=f"Cannot accept from status: {tx['status']}")

    # Calculate amounts
    amount = tx["amount"]
    platform_fee = tx.get("platform_fee", amount * 0.03)
    seller_amount = amount - platform_fee

    # Generate mock release transaction hash
    release_tx_hash = f"0x{secrets.token_hex(32)}"

    # Update transaction
    updated_tx = update_transaction_status(
        transaction_id,
        TransactionStatus.COMPLETED,
        {
            "rating": request.rating,
            "review": request.review,
            "release_tx_hash": release_tx_hash,
        }
    )

    # Credit seller (simulated)
    seller = get_user_by_address(tx["seller_id"])
    if seller:
        update_user_stake(seller["id"], seller_amount)

    # Update seller reputation based on rating
    if request.rating >= 4:
        # Positive rating
        logger.info(f"Seller {tx['seller_id']} received positive rating {request.rating}")
    else:
        # Negative rating
        logger.info(f"Seller {tx['seller_id']} received negative rating {request.rating}")

    logger.info(f"Transaction {transaction_id} completed, funds released to seller")

    return {
        "success": True,
        "transaction": format_transaction(updated_tx),
        "release_amount": seller_amount,
        "release_tx_hash": release_tx_hash,
        "message": "Delivery accepted, funds released",
    }


@router.post("/{transaction_id}/dispute")
async def raise_dispute(
    transaction_id: str,
    request: DisputeRequest,
    user: dict = Depends(get_current_user)
):
    """
    Raise a dispute.

    Either party can raise a dispute if there's an issue.
    Status: delivered/escrowed/in_progress -> disputed
    """
    tx = get_transaction(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Validate user is participant
    validate_transaction_participant(tx, user["id"])

    # Validate status
    if tx["status"] not in [TransactionStatus.ESCROWED, TransactionStatus.IN_PROGRESS, TransactionStatus.DELIVERED]:
        raise HTTPException(status_code=400, detail=f"Cannot dispute from status: {tx['status']}")

    # Update transaction
    updated_tx = update_transaction_status(
        transaction_id,
        TransactionStatus.DISPUTED,
        {"dispute_reason": request.reason}
    )

    logger.info(f"Transaction {transaction_id} disputed by {user['id']}: {request.reason}")

    return {
        "success": True,
        "transaction": format_transaction(updated_tx),
        "message": "Dispute raised successfully",
    }


@router.post("/{transaction_id}/resolve")
async def resolve_dispute(
    transaction_id: str,
    request: ResolveDisputeRequest,
    admin: dict = Depends(get_current_admin)
):
    """
    Resolve a dispute (admin only).

    Admin decides the outcome and either refunds buyer or pays seller.
    Status: disputed -> completed or refunded
    """
    tx = get_transaction(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Validate status
    if tx["status"] != TransactionStatus.DISPUTED:
        raise HTTPException(status_code=400, detail="Transaction is not disputed")

    amount = tx["amount"]
    platform_fee = tx.get("platform_fee", amount * 0.03)

    if request.refund_buyer:
        # Refund buyer
        final_status = TransactionStatus.REFUNDED
        buyer = get_user_by_address(tx["buyer_id"])
        if buyer:
            update_user_stake(buyer["id"], amount)
    else:
        # Pay seller
        final_status = TransactionStatus.COMPLETED
        seller_amount = amount - platform_fee
        seller = get_user_by_address(tx["seller_id"])
        if seller:
            update_user_stake(seller["id"], seller_amount)

    # Update transaction
    updated_tx = update_transaction_status(
        transaction_id,
        final_status,
        {"dispute_resolution": request.resolution}
    )

    logger.info(f"Transaction {transaction_id} dispute resolved: {request.resolution}")

    return {
        "success": True,
        "transaction": format_transaction(updated_tx),
        "resolution": request.resolution,
        "refunded": request.refund_buyer,
    }


@router.post("/{transaction_id}/cancel")
async def cancel_transaction(
    transaction_id: str,
    user: dict = Depends(get_current_user)
):
    """
    Cancel a transaction.

    Can only cancel if not yet completed.
    Refunds buyer if funds were escrowed.
    """
    tx = get_transaction(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Validate user is participant
    validate_transaction_participant(tx, user["id"])

    # Validate status
    if tx["status"] in [TransactionStatus.COMPLETED, TransactionStatus.CANCELLED, TransactionStatus.REFUNDED]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel from status: {tx['status']}")

    # Refund buyer if escrowed
    if tx["status"] in [TransactionStatus.ESCROWED, TransactionStatus.IN_PROGRESS, TransactionStatus.DISPUTED]:
        buyer = get_user_by_address(tx["buyer_id"])
        if buyer:
            update_user_stake(buyer["id"], tx["amount"])

    # Update transaction
    updated_tx = update_transaction_status(transaction_id, TransactionStatus.CANCELLED)

    logger.info(f"Transaction {transaction_id} cancelled by {user['id']}")

    return {
        "success": True,
        "transaction": format_transaction(updated_tx),
        "refunded": tx["status"] in [TransactionStatus.ESCROWED, TransactionStatus.IN_PROGRESS],
    }


@router.get("/stats/summary")
async def get_stats(
    user: dict = Depends(get_current_user)
):
    """
    Get transaction statistics.
    """
    stats = get_transaction_stats(user["id"])
    return stats
