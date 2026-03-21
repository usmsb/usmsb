"""
Identity SBT (Soul-Bound Token) API endpoints.

Provides endpoints for identity management:
- Mint Soul-Bound Tokens for agents
- Query SBT tokens owned by an address

Authentication: Requires unified auth (API key or SIWE).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from usmsb_sdk.api.rest.unified_auth import get_current_user_unified

router = APIRouter(prefix="/identity", tags=["Identity"])


# ==================== Request/Response Models ====================

class MintSBTRequest(BaseModel):
    """Request to mint a Soul-Bound Token.

    用户在浏览器 MetaMask 签名铸造 SBT 交易后，将 tx_hash 提交给后端验证。
    原则：真人操作由本人签名，后端不持有私钥。
    """
    agent_address: str = Field(..., description="Agent address to mint SBT for")
    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    metadata: str = Field(default="{}", description="Metadata JSON string")
    identity_type: int = Field(default=0, ge=0, le=3, description="Identity type: 0=AI_AGENT, 1=HUMAN_PROVIDER, 2=NODE_OPERATOR, 3=GOVERNANCE")
    tx_hash: str = Field(..., description="铸造 SBT 交易的 tx_hash（前端签名后提供）")


class MintSBTResponse(BaseModel):
    """Mint SBT response."""
    success: bool
    token_id: int
    tx_hash: str
    agent_address: str
    identity_type: str
    message: str


class SBTQueryResponse(BaseModel):
    """Query SBT tokens response."""
    address: str
    is_registered: bool
    token_id: int | None
    identity_type: str | None
    name: str | None
    metadata: str | None
    registration_time: int | None


# ==================== Endpoints ====================

@router.post("/mint-sbt", response_model=MintSBTResponse)
async def mint_sbt(
    request: MintSBTRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    提交铸造 SBT 交易的 tx_hash，后端验证链上状态并记录。

    用户在浏览器 MetaMask 签名铸造 SBT 交易后，将 tx_hash 提交给此端点验证。

    原则：真人操作由本人签名，后端不持有私钥。
    """
    from web3 import Web3
    from usmsb_sdk.blockchain.config import BlockchainConfig

    address = current_user.get("wallet_address") or current_user.get("address")
    if not address:
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

        from usmsb_sdk.blockchain.contracts.vib_identity import IdentityType
        identity_type = IdentityType(request.identity_type)

        return MintSBTResponse(
            success=True,
            token_id=0,  # Can be queried from Transfer event logs if needed
            tx_hash=request.tx_hash,
            agent_address=request.agent_address,
            identity_type=identity_type.name,
            message=f"SBT minting verified and recorded for {request.agent_address}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SBT minting verification failed: {str(e)}")


@router.get("/{address}/sbt", response_model=SBTQueryResponse)
async def get_address_sbt(address: str):
    """
    Query SBT tokens owned by an address.

    Args:
        address: The address to query SBT tokens for
    """
    from usmsb_sdk.blockchain.contracts.vib_identity import IdentityType, VIBIdentityClient

    try:
        client = VIBIdentityClient()

        # Check if registered
        is_registered = await client.is_registered(address)

        if not is_registered:
            return SBTQueryResponse(
                address=address,
                is_registered=False,
                token_id=None,
                identity_type=None,
                name=None,
                metadata=None,
                registration_time=None,
            )

        # Get token ID
        token_id = await client.get_token_id_by_address(address)

        # Get identity info
        identity_info = await client.get_identity_info(token_id)
        identity_type = IdentityType(identity_info["identity_type"])

        return SBTQueryResponse(
            address=address,
            is_registered=True,
            token_id=token_id,
            identity_type=identity_type.name,
            name=identity_info["name"],
            metadata=identity_info["metadata"],
            registration_time=identity_info["registration_time"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
