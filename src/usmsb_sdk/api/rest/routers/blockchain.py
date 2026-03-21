"""
区块链API端点

提供直接与区块链交互的端点：
- 测试连接
- 查询代币余额
- 查询代币信息
- 查询质押信息
- VIBE代币转账和授权
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from usmsb_sdk.api.rest.unified_auth import get_current_user_unified

router = APIRouter(prefix="/blockchain", tags=["Blockchain"])


class TokenBalanceResponse(BaseModel):
    """代币余额响应"""
    address: str
    balance_wei: int
    balance_vibe: float
    symbol: str
    name: str
    decimals: int


class BlockchainStatusResponse(BaseModel):
    """区块链状态响应"""
    connected: bool
    chain_id: int
    network_name: str
    block_number: int
    token_address: str
    token_name: str
    token_symbol: str


class TaxBreakdownResponse(BaseModel):
    """交易税明细"""
    amount_vibe: float
    tax_rate: float
    tax_vibe: float
    net_vibe: float


@router.get("/status", response_model=BlockchainStatusResponse)
async def get_blockchain_status():
    """
    获取区块链连接状态

    无需认证，直接查询区块链状态
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    try:
        client = VIBEBlockchainClient()

        # 测试连接
        connection = client.test_connection()

        # 获取代币信息
        token_name = client.token.name()
        token_symbol = client.token.symbol()
        client.token.decimals()

        return BlockchainStatusResponse(
            connected=connection["connected"],
            chain_id=connection["chain_id"],
            network_name=client.config.network_name,
            block_number=connection.get("block_number", 0),
            token_address=client.config.get_contract_address("VIBEToken"),
            token_name=token_name,
            token_symbol=token_symbol,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/balance/{address}", response_model=TokenBalanceResponse)
async def get_token_balance(address: str):
    """
    查询指定地址的VIBE代币余额

    无需认证，直接从区块链查询
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    try:
        client = VIBEBlockchainClient()

        # 查询余额
        balance_wei = client.token.balance_of(address)
        balance_vibe = client.token.balance_of_vibe(address)

        # 获取代币信息
        token_symbol = client.token.symbol()
        token_name = client.token.name()

        return TokenBalanceResponse(
            address=address,
            balance_wei=balance_wei,
            balance_vibe=balance_vibe,
            symbol=token_symbol,
            name=token_name,
            decimals=18,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tax/{amount}", response_model=TaxBreakdownResponse)
async def get_tax_breakdown(amount: float):
    """
    计算交易税明细

    Args:
        amount: VIBE金额
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    try:
        client = VIBEBlockchainClient()

        # 转换为wei
        amount_wei = int(amount * (10 ** 18))

        # 计算税费
        breakdown = client.token.get_tax_breakdown(amount_wei)

        return TaxBreakdownResponse(
            amount_vibe=breakdown["amount_vibe"],
            tax_rate=breakdown["tax_rate"],
            tax_vibe=breakdown["tax_vibe"],
            net_vibe=breakdown["net_vibe"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/total-supply")
async def get_total_supply():
    """
    查询VIBE代币总供应量
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    try:
        client = VIBEBlockchainClient()
        supply = client.token.total_supply_vibe()
        return {"total_supply_vibe": supply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== VIBE Token Transfer/Approve Endpoints ====================

class TransferRequest(BaseModel):
    """VIBE代币转账请求"""
    to: str = Field(..., description="接收方地址")
    amount: float = Field(..., gt=0, description="转账金额（VIBE）")


class TransferResponse(BaseModel):
    """VIBE代币转账响应"""
    success: bool
    tx_hash: str
    from_address: str
    to_address: str
    amount_vibe: float
    message: str


class ApproveRequest(BaseModel):
    """VIBE代币授权请求"""
    spender: str = Field(..., description="被授权地址")
    amount: float = Field(..., gt=0, description="授权金额（VIBE），使用0撤销授权")


class ApproveResponse(BaseModel):
    """VIBE代币授权响应"""
    success: bool
    tx_hash: str
    owner: str
    spender: str
    amount_vibe: float
    message: str


class AllowanceResponse(BaseModel):
    """授权额度查询响应"""
    owner: str
    spender: str
    allowance_wei: int
    allowance_vibe: float


@router.post("/transfer", response_model=TransferResponse)
async def transfer_vibe(
    request: TransferRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    转账VIBE代币

    需要认证。转账会扣除0.8%的交易税。

    Args:
        to: 接收方地址
        amount: 转账金额（VIBE）
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    # Get sender address from authenticated user
    sender_address = current_user.get("wallet_address") or current_user.get("address")
    if not sender_address:
        raise HTTPException(status_code=401, detail="Wallet address not found in authentication")

    # Get private key - this should be securely retrieved based on auth type
    # For API key auth, we need to get the private key from secure storage
    private_key = current_user.get("private_key")
    if not private_key:
        raise HTTPException(status_code=401, detail="Private key not available for this authentication method")

    try:
        client = VIBEBlockchainClient()

        # Convert VIBE to wei
        amount_wei = int(request.amount * (10 ** 18))

        # Execute transfer
        tx_hash = client.token.transfer(
            to=request.to,
            amount=amount_wei,
            from_address=sender_address,
            private_key=private_key,
        )

        return TransferResponse(
            success=True,
            tx_hash=tx_hash,
            from_address=sender_address,
            to_address=request.to,
            amount_vibe=request.amount,
            message=f"Successfully transferred {request.amount} VIBE to {request.to}",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/approve", response_model=ApproveResponse)
async def approve_vibe(
    request: ApproveRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    授权代币消费

    需要认证。授权后，被授权地址可以使用您的VIBE代币。

    Args:
        spender: 被授权地址
        amount: 授权金额（VIBE），使用0撤销授权
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    # Get owner address from authenticated user
    owner_address = current_user.get("wallet_address") or current_user.get("address")
    if not owner_address:
        raise HTTPException(status_code=401, detail="Wallet address not found in authentication")

    # Get private key
    private_key = current_user.get("private_key")
    if not private_key:
        raise HTTPException(status_code=401, detail="Private key not available for this authentication method")

    try:
        client = VIBEBlockchainClient()

        # Convert VIBE to wei
        amount_wei = int(request.amount * (10 ** 18))

        # Execute approve
        tx_hash = client.token.approve(
            spender=request.spender,
            amount=amount_wei,
            from_address=owner_address,
            private_key=private_key,
        )

        action = "revoked" if request.amount == 0 else "approved"
        return ApproveResponse(
            success=True,
            tx_hash=tx_hash,
            owner=owner_address,
            spender=request.spender,
            amount_vibe=request.amount,
            message=f"Successfully {action} {request.spender} to spend {request.amount} VIBE",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/allowance/{owner}/{spender}", response_model=AllowanceResponse)
async def get_allowance(owner: str, spender: str):
    """
    查询授权额度

    无需认证，直接从区块链查询。

    Args:
        owner: 代币所有者地址
        spender: 被授权地址
    """
    from usmsb_sdk.blockchain import VIBEBlockchainClient

    try:
        client = VIBEBlockchainClient()

        allowance_wei = client.token.allowance(owner, spender)
        allowance_vibe = float(client.token.w3.from_wei(allowance_wei, "ether"))

        return AllowanceResponse(
            owner=owner,
            spender=spender,
            allowance_wei=allowance_wei,
            allowance_vibe=allowance_vibe,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
