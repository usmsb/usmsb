"""
区块链API端点

提供直接与区块链交互的端点：
- 测试连接
- 查询代币余额
- 查询代币信息
- 查询质押信息
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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
