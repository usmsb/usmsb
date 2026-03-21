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
    """Request to mint a Soul-Bound Token."""
    agent_address: str = Field(..., description="Agent address to mint SBT for")
    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    metadata: str = Field(default="{}", description="Metadata JSON string")
    identity_type: int = Field(default=0, ge=0, le=3, description="Identity type: 0=AI_AGENT, 1=HUMAN_PROVIDER, 2=NODE_OPERATOR, 3=GOVERNANCE")


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
    Mint a Soul-Bound Token (SBT) for an agent.

    Requires:
        - X-API-Key header (for agent) OR SIWE wallet authentication
        - Caller must have sufficient permissions

    Args:
        agent_address: Address of the agent to mint SBT for
        name: Agent name
        metadata: JSON metadata string with agent capabilities
        identity_type: 0=AI_AGENT, 1=HUMAN_PROVIDER, 2=NODE_OPERATOR, 3=GOVERNANCE
    """
    from usmsb_sdk.blockchain.contracts.vib_identity import IdentityType, VIBIdentityClient

    # Get user credentials
    address = current_user.get("wallet_address") or current_user.get("address")
    private_key = current_user.get("private_key")

    if not address:
        raise HTTPException(status_code=401, detail="Wallet address not found in authentication")
    if not private_key:
        raise HTTPException(status_code=401, detail="Private key not available for this authentication method")

    try:
        client = VIBIdentityClient()

        # Mint SBT based on identity type
        identity_type = IdentityType(request.identity_type)

        if identity_type == IdentityType.AI_AGENT:
            token_id, tx_hash = await client.register_ai_identity_for(
                agent_address=request.agent_address,
                name=request.name,
                metadata=request.metadata,
                from_address=address,
                private_key=private_key,
            )
        elif identity_type == IdentityType.HUMAN_PROVIDER:
            token_id, tx_hash = await client.register_human_provider(
                name=request.name,
                metadata=request.metadata,
                from_address=address,
                private_key=private_key,
            )
        elif identity_type == IdentityType.NODE_OPERATOR:
            token_id, tx_hash = await client.register_node_operator(
                name=request.name,
                metadata=request.metadata,
                from_address=address,
                private_key=private_key,
            )
        elif identity_type == IdentityType.GOVERNANCE:
            token_id, tx_hash = await client.register_governance(
                name=request.name,
                metadata=request.metadata,
                from_address=address,
                private_key=private_key,
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid identity type")

        return MintSBTResponse(
            success=True,
            token_id=token_id,
            tx_hash=tx_hash,
            agent_address=request.agent_address,
            identity_type=identity_type.name,
            message=f"SBT minted successfully for {request.agent_address}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
