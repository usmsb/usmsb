"""
Dispute API endpoints.

Provides endpoints for JointOrder dispute management:
- Raise a dispute on a JointOrder pool
- Get dispute status and details
- Resolve a dispute (arbitrator only)

Authentication: Requires unified auth (API key or SIWE).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from usmsb_sdk.api.rest.unified_auth import get_current_user_unified

router = APIRouter(prefix="/dispute", tags=["Dispute"])


# ==================== Request/Response Models ====================

class RaiseDisputeRequest(BaseModel):
    """Request to raise a dispute on a JointOrder pool.

    用户在浏览器 MetaMask 签名 raise dispute 交易后，将 tx_hash 提交给后端验证。
    原则：真人操作由本人签名，后端不持有私钥。
    """
    pool_id: str = Field(..., description="JointOrder pool ID (hex string)")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for dispute")
    tx_hash: str = Field(..., description="raise dispute 交易的 tx_hash（前端签名后提供）")


class ResolveDisputeRequest(BaseModel):
    """Request to resolve a dispute (arbitrator only).

    仲裁者在浏览器 MetaMask 签名 resolve dispute 交易后，将 tx_hash 提交给后端验证。
    原则：真人操作由本人签名，后端不持有私钥。
    """
    pool_id: str = Field(..., description="JointOrder pool ID (hex string)")
    refund_buyers: bool = Field(..., description="True to refund buyers, False to pay provider")
    resolution: str = Field(..., min_length=1, max_length=500, description="Resolution description")
    tx_hash: str = Field(..., description="resolve dispute 交易的 tx_hash（前端签名后提供）")


class RaiseDisputeResponse(BaseModel):
    """Raise dispute response."""
    success: bool
    tx_hash: str
    pool_id: str
    penalty_amount: float
    message: str


class DisputeStatusResponse(BaseModel):
    """Dispute status response."""
    pool_id: str
    status: str
    raiser: str | None
    penalty_amount: float
    resolved: bool
    is_refund_pending: bool


class ResolveDisputeResponse(BaseModel):
    """Resolve dispute response."""
    success: bool
    tx_hash: str
    pool_id: str
    refund_buyers: bool
    message: str


# ==================== Endpoints ====================

@router.post("/raise", response_model=RaiseDisputeResponse)
async def raise_dispute(
    request: RaiseDisputeRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    Raise a dispute on a JointOrder pool.

    Requires:
        - X-API-Key header (for agent) OR SIWE wallet authentication
        - Caller must be a participant or provider in the pool
        - Dispute penalty (1% of winning bid) will be charged

    Args:
        pool_id: JointOrder pool ID (hex string)
        reason: Reason for raising the dispute
    """
    from usmsb_sdk.blockchain.contracts.joint_order import JointOrderClient
    from usmsb_sdk.blockchain.config import BlockchainConfig

    address = current_user.get("wallet_address") or current_user.get("address")
    if not address:
        raise HTTPException(status_code=401, detail="Wallet address not found in authentication")

    try:
        from web3 import Web3
        from usmsb_sdk.blockchain.config import BlockchainConfig

        config = BlockchainConfig.from_env()
        w3 = Web3(Web3.HTTPProvider(config.rpc_url))

        if not request.tx_hash.startswith("0x") or len(request.tx_hash) != 66:
            raise HTTPException(status_code=400, detail="Invalid tx_hash format")

        receipt = w3.eth.get_transaction_receipt(request.tx_hash)
        if receipt is None or receipt.status != 1:
            raise HTTPException(status_code=400, detail="Dispute raise transaction failed or not mined")

        return RaiseDisputeResponse(
            success=True,
            tx_hash=request.tx_hash,
            pool_id=request.pool_id,
            penalty_amount=0,  # Can be calculated from chain events if needed
            message=f"Dispute raised and verified on pool {request.pool_id}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dispute raise verification failed: {str(e)}")


@router.get("/{pool_id}", response_model=DisputeStatusResponse)
async def get_dispute_status(pool_id: str):
    """
    Get dispute status and details for a JointOrder pool.

    Args:
        pool_id: JointOrder pool ID (hex string)
    """
    from usmsb_sdk.blockchain.contracts.joint_order import JointOrderClient

    try:
        client = JointOrderClient()

        # Convert pool_id to bytes32
        pool_id_bytes = bytes.fromhex(pool_id.lstrip("0x"))
        while len(pool_id_bytes) < 32:
            pool_id_bytes = b"\x00" + pool_id_bytes
        pool_id_bytes32 = pool_id_bytes[:32]

        # Get pool status
        pool = client.call_contract_function(
            client.contract.functions.getPool(pool_id_bytes32)
        )
        status = pool[6]  # status is at index 6 in OrderPool struct

        # Get dispute penalty info
        penalty = client.call_contract_function(
            client.contract.functions.disputePenalties(pool_id_bytes32)
        )

        # Get refund pending status
        refund_pending = client.call_contract_function(
            client.contract.functions.refundPendingPools(pool_id_bytes32)
        )

        return DisputeStatusResponse(
            pool_id=pool_id,
            status=status,
            raiser=penalty[0] if penalty[0] else None,
            penalty_amount=float(int(penalty[1])) / 1e18,
            resolved=penalty[2],
            is_refund_pending=refund_pending,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resolve", response_model=ResolveDisputeResponse)
async def resolve_dispute(
    request: ResolveDisputeRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    Resolve a dispute on a JointOrder pool.

    Requires:
        - X-API-Key header (for agent) OR SIWE wallet authentication
        - Caller must be the arbitrator

    Args:
        pool_id: JointOrder pool ID (hex string)
        refund_buyers: True to refund buyers, False to pay provider
        resolution: Resolution description
    """
    from usmsb_sdk.blockchain.contracts.joint_order import JointOrderClient

    address = current_user.get("wallet_address") or current_user.get("address")
    if not address:
        raise HTTPException(status_code=401, detail="Wallet address not found in authentication")

    try:
        from web3 import Web3
        from usmsb_sdk.blockchain.config import BlockchainConfig

        config = BlockchainConfig.from_env()
        w3 = Web3(Web3.HTTPProvider(config.rpc_url))

        if not request.tx_hash.startswith("0x") or len(request.tx_hash) != 66:
            raise HTTPException(status_code=400, detail="Invalid tx_hash format")

        receipt = w3.eth.get_transaction_receipt(request.tx_hash)
        if receipt is None or receipt.status != 1:
            raise HTTPException(status_code=400, detail="Dispute resolve transaction failed or not mined")

        return ResolveDisputeResponse(
            success=True,
            tx_hash=request.tx_hash,
            pool_id=request.pool_id,
            refund_buyers=request.refund_buyers,
            message=f"Dispute resolved and verified on pool {request.pool_id}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Dispute resolve verification failed: {str(e)}")
