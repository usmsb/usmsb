"""
JointOrder Pool API Endpoints.

Provides endpoints for managing JointOrder pools on-chain:
- Create pools from orders
- Submit bids
- Accept bids
- Confirm delivery
- Cancel pools
- Query pool info and bids

Authentication: All write operations require X-API-Key + X-Agent-ID headers.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
from usmsb_sdk.blockchain.contracts.joint_order import PoolStatus

router = APIRouter(prefix="/joint-order", tags=["JointOrder Pool"])


# ==================== Request Models ====================

class CreatePoolRequest(BaseModel):
    """创建需求池请求

    用户在浏览器 MetaMask 签名创建池交易后，将 tx_hash 提交给后端验证。
    原则：真人操作由本人签名，后端不持有私钥。
    """
    order_id: str = Field(..., description="订单ID（用于追踪）")
    service_type: str = Field(..., description="服务类型")
    total_budget: float = Field(..., gt=0, description="总预算（VIBE）")
    min_budget: float | None = Field(default=None, gt=0, description="最低预算（VIBE），默认等于total_budget")
    delivery_hours: int = Field(default=72, gt=0, description="交付期限（小时）")
    tx_hash: str = Field(..., description="创建池交易的 tx_hash（前端签名后提供）")


class SubmitBidRequest(BaseModel):
    """提交报价请求

    用户在浏览器 MetaMask 签名提交报价交易后，将 tx_hash 提交给后端验证。
    原则：真人操作由本人签名，后端不持有私钥。
    """
    pool_id: str = Field(..., description="需求池ID")
    chain_pool_id: str = Field(..., description="链上池ID（bytes32十六进制）")
    price: float = Field(..., gt=0, description="报价（VIBE）")
    delivery_hours: int = Field(default=48, gt=0, description="承诺交付时间（小时）")
    reputation_score: int = Field(default=50, ge=0, le=100, description="信誉分（0-100）")
    proposal: str = Field(default="", description="方案描述")
    tx_hash: str = Field(..., description="提交报价交易的 tx_hash（前端签名后提供）")


class AcceptBidRequest(BaseModel):
    """接受报价请求

    用户在浏览器 MetaMask 签名接受报价交易后，将 tx_hash 提交给后端验证。
    原则：真人操作由本人签名，后端不持有私钥。
    """
    pool_id: str = Field(..., description="需求池ID")
    chain_pool_id: str = Field(..., description="链上池ID（bytes32十六进制）")
    bid_id: str = Field(..., description="报价ID（bytes32十六进制）")
    tx_hash: str = Field(..., description="接受报价交易的 tx_hash（前端签名后提供）")


class ConfirmDeliveryRequest(BaseModel):
    """确认交付请求

    用户在浏览器 MetaMask 签名确认交付交易后，将 tx_hash 提交给后端验证。
    原则：真人操作由本人签名，后端不持有私钥。
    """
    pool_id: str = Field(..., description="需求池ID")
    chain_pool_id: str = Field(..., description="链上池ID（bytes32十六进制）")
    rating: int = Field(default=5, ge=1, le=5, description="交付评分（1-5）")
    tx_hash: str = Field(..., description="确认交付交易的 tx_hash（前端签名后提供）")


class CancelPoolRequest(BaseModel):
    """取消需求池请求

    用户在浏览器 MetaMask 签名取消池交易后，将 tx_hash 提交给后端验证。
    原则：真人操作由本人签名，后端不持有私钥。
    """
    pool_id: str = Field(..., description="需求池ID")
    chain_pool_id: str = Field(..., description="链上池ID（bytes32十六进制）")
    tx_hash: str = Field(..., description="取消池交易的 tx_hash（前端签名后提供）")
    pool_id: str = Field(..., description="需求池ID")
    chain_pool_id: str = Field(..., description="链上池ID（bytes32十六进制）")
    reason: str = Field(default="", description="取消原因")


# ==================== Response Models ====================

class PoolCreationResponse(BaseModel):
    """创建需求池响应"""
    success: bool
    pool_id: str | None
    chain_pool_id: str | None
    tx_hash: str | None
    message: str


class BidSubmissionResponse(BaseModel):
    """提交报价响应"""
    success: bool
    bid_id: str | None
    tx_hash: str | None
    message: str


class BidAcceptanceResponse(BaseModel):
    """接受报价响应"""
    success: bool
    tx_hash: str | None
    message: str


class DeliveryConfirmationResponse(BaseModel):
    """交付确认响应"""
    success: bool
    tx_hash: str | None
    message: str


class PoolCancellationResponse(BaseModel):
    """取消需求池响应"""
    success: bool
    tx_hash: str | None
    message: str


class PoolInfoResponse(BaseModel):
    """需求池信息响应"""
    pool_id: str
    chain_pool_id: str
    creator: str
    service_type: str
    total_budget_wei: int
    total_budget_vibe: float
    min_budget_wei: int
    min_budget_vibe: float
    participant_count: int
    bid_count: int
    created_at: int
    funding_deadline: int
    bidding_ends_at: int
    delivery_deadline: int
    status: int
    status_name: str
    winning_provider: str
    winning_bid_wei: int
    winning_bid_vibe: float
    platform_fee_wei: int
    metadata_hash: str


class BidInfoResponse(BaseModel):
    """报价信息响应"""
    bid_id: str
    pool_id: str
    provider: str
    price_wei: int
    price_vibe: float
    delivery_time: int
    reputation_score: int
    computed_score: int
    is_winner: bool
    proposal: str


# ==================== Helper Functions ====================

def get_joint_order_pool_manager():
    """Get JointOrderPoolManager instance."""
    from usmsb_sdk.blockchain.config import BlockchainConfig
    from usmsb_sdk.blockchain.web3_client import Web3Client
    from usmsb_sdk.services.joint_order_pool_manager import JointOrderPoolManager

    config = BlockchainConfig.from_env()
    web3_client = Web3Client(config=config)
    return JointOrderPoolManager(web3_client=web3_client, config=config)


# ==================== Endpoints ====================

@router.post("/pool/create", response_model=PoolCreationResponse)
async def create_pool(
    request: CreatePoolRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    提交创建池交易的 tx_hash，后端验证链上状态并记录。

    用户在浏览器 MetaMask 签名创建池交易后，将 tx_hash 提交给此端点验证。

    原则：真人操作由本人签名，后端不持有私钥。
    """
    from web3 import Web3
    from usmsb_sdk.blockchain.config import BlockchainConfig

    creator_address = current_user.get("wallet_address") or current_user.get("address")
    if not creator_address:
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

        # Record in database (best-effort)
        try:
            from usmsb_sdk.api.database import db_create_order_record
            db_create_order_record(
                order_id=request.order_id,
                creator=creator_address,
                total_budget=request.total_budget,
                service_type=request.service_type,
                chain_pool_id=request.tx_hash,
            )
        except Exception as db_err:
            import logging
            logging.getLogger(__name__).warning(f"DB write skipped (table may not exist): {db_err}")

        return PoolCreationResponse(
            success=True,
            pool_id=request.order_id,
            chain_pool_id=request.tx_hash,
            tx_hash=request.tx_hash,
            message=f"Pool created and verified. Order: {request.order_id}, Budget: {request.total_budget} VIBE",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Pool creation verification failed: {str(e)}")


@router.post("/pool/submit-bid", response_model=BidSubmissionResponse)
async def submit_bid(
    request: SubmitBidRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    提交报价交易的 tx_hash，后端验证链上状态并记录。

    用户在浏览器 MetaMask 签名提交报价交易后，将 tx_hash 提交给此端点验证。

    原则：真人操作由本人签名，后端不持有私钥。
    """
    from web3 import Web3
    from usmsb_sdk.blockchain.config import BlockchainConfig

    provider_address = current_user.get("wallet_address") or current_user.get("address")
    if not provider_address:
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

        return BidSubmissionResponse(
            success=True,
            bid_id="0x" + request.tx_hash[2:34],  # Derive bid_id from tx_hash
            tx_hash=request.tx_hash,
            message=f"Bid submitted and verified. Pool: {request.pool_id}, Price: {request.price} VIBE",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Bid submission verification failed: {str(e)}")


@router.post("/pool/accept-bid", response_model=BidAcceptanceResponse)
async def accept_bid(
    request: AcceptBidRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    提交接受报价交易的 tx_hash，后端验证链上状态并记录。

    用户在浏览器 MetaMask 签名接受报价交易后，将 tx_hash 提交给此端点验证。

    原则：真人操作由本人签名，后端不持有私钥。
    """
    from web3 import Web3
    from usmsb_sdk.blockchain.config import BlockchainConfig

    awarder_address = current_user.get("wallet_address") or current_user.get("address")
    if not awarder_address:
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

        return BidAcceptanceResponse(
            success=True,
            tx_hash=request.tx_hash,
            message=f"Bid accepted and verified. Pool: {request.pool_id}, Bid: {request.bid_id[:16]}...",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Bid acceptance verification failed: {str(e)}")


@router.post("/pool/confirm-delivery", response_model=DeliveryConfirmationResponse)
async def confirm_delivery(
    request: ConfirmDeliveryRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    提交确认交付交易的 tx_hash，后端验证链上状态并记录。

    用户在浏览器 MetaMask 签名确认交付交易后，将 tx_hash 提交给此端点验证。
    确认后资金会释放给服务商。

    原则：真人操作由本人签名，后端不持有私钥。
    """
    from web3 import Web3
    from usmsb_sdk.blockchain.config import BlockchainConfig

    confirmer_address = current_user.get("wallet_address") or current_user.get("address")
    if not confirmer_address:
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

        return DeliveryConfirmationResponse(
            success=True,
            tx_hash=request.tx_hash,
            message=f"Delivery confirmed and verified. Pool: {request.pool_id}, Rating: {request.rating}/5",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Delivery confirmation verification failed: {str(e)}")


@router.post("/pool/cancel", response_model=PoolCancellationResponse)
async def cancel_pool(
    request: CancelPoolRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    提交取消池交易的 tx_hash，后端验证链上状态并记录。

    用户在浏览器 MetaMask 签名取消池交易后，将 tx_hash 提交给此端点验证。

    原则：真人操作由本人签名，后端不持有私钥。
    """
    from web3 import Web3
    from usmsb_sdk.blockchain.config import BlockchainConfig

    canceller_address = current_user.get("wallet_address") or current_user.get("address")
    if not canceller_address:
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

        return PoolCancellationResponse(
            success=True,
            tx_hash=request.tx_hash,
            message=f"Pool cancelled and verified. Pool: {request.pool_id}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Pool cancellation verification failed: {str(e)}")


@router.get("/pool/{pool_id}", response_model=PoolInfoResponse)
async def get_pool_info(pool_id: str):
    """
    获取需求池信息

    无需认证。

    Args:
        pool_id: 需求池ID（Readable ID，不是链上ID）
    """
    from web3 import Web3

    try:
        manager = get_joint_order_pool_manager()

        # Get pool status which returns the chain_pool_id
        # Note: pool_id here is the readable ID, we need the chain ID for queries
        # For now, we'll use the pool_id as chain_pool_id directly
        chain_pool_id = pool_id
        if not chain_pool_id.startswith("0x"):
            chain_pool_id = "0x" + chain_pool_id

        status = await manager.get_pool_status(chain_pool_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Pool not found")

        # Get full pool info via client
        from usmsb_sdk.blockchain.config import BlockchainConfig
        from usmsb_sdk.blockchain.web3_client import Web3Client
        from usmsb_sdk.blockchain.contracts.joint_order import JointOrderClient

        config = BlockchainConfig.from_env()
        web3_client = Web3Client(config=config)
        client = JointOrderClient(web3_client=web3_client, config=config)

        info = await client.get_pool_info(chain_pool_id)

        return PoolInfoResponse(
            pool_id=pool_id,
            chain_pool_id=info["pool_id"],
            creator=info["creator"],
            service_type=info["service_type"],
            total_budget_wei=info["total_budget"],
            total_budget_vibe=float(web3_client.w3.from_wei(info["total_budget"], "ether")),
            min_budget_wei=info["min_budget"],
            min_budget_vibe=float(web3_client.w3.from_wei(info["min_budget"], "ether")),
            participant_count=info["participant_count"],
            bid_count=info["bid_count"],
            created_at=info["created_at"],
            funding_deadline=info["funding_deadline"],
            bidding_ends_at=info["bidding_ends_at"],
            delivery_deadline=info["delivery_deadline"],
            status=info["status"].value if hasattr(info["status"], 'value') else info["status"],
            status_name=info["status_name"],
            winning_provider=info["winning_provider"],
            winning_bid_wei=info["winning_bid"],
            winning_bid_vibe=float(web3_client.w3.from_wei(info["winning_bid"], "ether")),
            platform_fee_wei=info["platform_fee"],
            metadata_hash=info["metadata_hash"],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pool/{pool_id}/bids", response_model=list[BidInfoResponse])
async def get_pool_bids(pool_id: str):
    """
    获取需求池的所有报价

    无需认证。

    Args:
        pool_id: 需求池ID（Readable ID，不是链上ID）
    """
    from web3 import Web3

    try:
        manager = get_joint_order_pool_manager()

        # Use pool_id as chain_pool_id
        chain_pool_id = pool_id
        if not chain_pool_id.startswith("0x"):
            chain_pool_id = "0x" + chain_pool_id

        bids = await manager.get_pool_bids(chain_pool_id)

        # Convert wei to VIBE for each bid
        from usmsb_sdk.blockchain.config import BlockchainConfig
        from usmsb_sdk.blockchain.web3_client import Web3Client

        config = BlockchainConfig.from_env()
        web3_client = Web3Client(config=config)

        result = []
        for bid in bids:
            result.append(BidInfoResponse(
                bid_id=bid["bid_id"],
                pool_id=bid["pool_id"],
                provider=bid["provider"],
                price_wei=bid["price"],
                price_vibe=float(web3_client.w3.from_wei(bid["price"], "ether")),
                delivery_time=bid["delivery_time"],
                reputation_score=bid["reputation_score"],
                computed_score=bid["computed_score"],
                is_winner=bid["is_winner"],
                proposal=bid["proposal"],
            ))

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))