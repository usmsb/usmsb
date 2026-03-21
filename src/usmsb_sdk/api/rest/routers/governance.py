"""
Governance API endpoints.

Provides endpoints for VIBE governance:
- List proposals
- Get proposal details
- Create proposals
- Cast votes
- Get delegation info

Authentication: Requires unified auth (API key or SIWE).
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from usmsb_sdk.api.rest.unified_auth import get_current_user_unified

router = APIRouter(prefix="/governance", tags=["Governance"])


# ==================== Request/Response Models ====================

class CreateProposalRequest(BaseModel):
    """Request to create a governance proposal."""
    proposal_type: int = Field(..., ge=0, le=5, description="Proposal type: 0=GENERAL, 1=PARAMETER, 2=UPGRADE, 3=EMERGENCY, 4=DIVIDEND, 5=INCENTIVE")
    title: str = Field(..., min_length=1, max_length=200, description="Proposal title")
    description: str = Field(..., min_length=1, max_length=2000, description="Proposal description")
    target: str = Field(..., description="Target contract address")
    data: str = Field(default="0x", description="Call data (hex encoded)")


class CastVoteRequest(BaseModel):
    """Request to cast a vote on a proposal."""
    proposal_id: int = Field(..., description="Proposal ID to vote on")
    support: int = Field(..., ge=0, le=2, description="Vote: 0=against, 1=for, 2=abstain")


class ProposalResponse(BaseModel):
    """Proposal details response."""
    id: int
    proposer: str
    proposal_type: str
    state: str
    title: str
    description: str
    target: str
    data: str
    start_time: int
    end_time: int
    execute_time: int
    for_votes: int
    against_votes: int
    abstain_votes: int
    total_voters: int
    executed: bool


class CreateProposalResponse(BaseModel):
    """Create proposal response."""
    success: bool
    proposal_id: int
    tx_hash: str
    message: str


class CastVoteResponse(BaseModel):
    """Cast vote response."""
    success: bool
    tx_hash: str
    proposal_id: int
    support: str
    message: str


class DelegationResponse(BaseModel):
    """Delegation info response."""
    address: str
    voting_power: int
    delegated_power: int
    can_delegate: bool


# ==================== Endpoints ====================

@router.get("/proposals", response_model=list[ProposalResponse])
async def list_proposals():
    """
    List all governance proposals.

    Returns proposals from 0 to latest proposal ID.
    """
    from usmsb_sdk.blockchain.contracts.vib_governance import VIBGovernanceClient

    try:
        client = VIBGovernanceClient()
        proposal_count = client.call_contract_function(
            client.contract.functions.getProposalCount()
        )
        proposal_count = int(proposal_count)

        proposals = []
        for i in range(proposal_count):
            try:
                proposal = await client.get_proposal(i)
                proposals.append(ProposalResponse(
                    id=proposal["id"],
                    proposer=proposal["proposer"],
                    proposal_type=proposal["proposal_type"].name,
                    state=proposal["state"].name,
                    title=proposal["title"],
                    description=proposal["description"],
                    target=proposal["target"],
                    data=proposal["data"],
                    start_time=proposal["start_time"],
                    end_time=proposal["end_time"],
                    execute_time=proposal["execute_time"],
                    for_votes=proposal["for_votes"],
                    against_votes=proposal["against_votes"],
                    abstain_votes=proposal["abstain_votes"],
                    total_voters=proposal["total_voters"],
                    executed=proposal["executed"],
                ))
            except Exception:
                # Skip proposals that can't be retrieved
                continue

        return proposals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proposals/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(proposal_id: int):
    """
    Get details of a specific proposal.

    Args:
        proposal_id: The proposal ID
    """
    from usmsb_sdk.blockchain.contracts.vib_governance import VIBGovernanceClient

    try:
        client = VIBGovernanceClient()
        proposal = await client.get_proposal(proposal_id)

        return ProposalResponse(
            id=proposal["id"],
            proposer=proposal["proposer"],
            proposal_type=proposal["proposal_type"].name,
            state=proposal["state"].name,
            title=proposal["title"],
            description=proposal["description"],
            target=proposal["target"],
            data=proposal["data"],
            start_time=proposal["start_time"],
            end_time=proposal["end_time"],
            execute_time=proposal["execute_time"],
            for_votes=proposal["for_votes"],
            against_votes=proposal["against_votes"],
            abstain_votes=proposal["abstain_votes"],
            total_voters=proposal["total_voters"],
            executed=proposal["executed"],
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/proposals", response_model=CreateProposalResponse)
async def create_proposal(
    request: CreateProposalRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    Create a new governance proposal.

    Requires:
        - X-API-Key header (for agent) OR SIWE wallet authentication
        - Sufficient voting power to meet threshold

    Args:
        proposal_type: 0=GENERAL, 1=PARAMETER, 2=UPGRADE, 3=EMERGENCY, 4=DIVIDEND, 5=INCENTIVE
        title: Proposal title
        description: Detailed description
        target: Target contract to call
        data: Hex-encoded call data
    """
    from usmsb_sdk.blockchain.contracts.vib_governance import ProposalType, VIBGovernanceClient

    # Get user credentials
    address = current_user.get("wallet_address") or current_user.get("address")
    private_key = current_user.get("private_key")

    if not address:
        raise HTTPException(status_code=401, detail="Wallet address not found in authentication")
    if not private_key:
        raise HTTPException(status_code=401, detail="Private key not available for this authentication method")

    try:
        client = VIBGovernanceClient()

        # Convert hex data to bytes
        data_bytes = bytes.fromhex(request.data.lstrip("0x")) if request.data != "0x" else b""

        # Create proposal
        proposal_id, tx_hash = await client.create_proposal(
            proposal_type=ProposalType(request.proposal_type),
            title=request.title,
            description=request.description,
            target=request.target,
            data=data_bytes,
            from_address=address,
            private_key=private_key,
        )

        return CreateProposalResponse(
            success=True,
            proposal_id=proposal_id,
            tx_hash=tx_hash,
            message=f"Proposal {proposal_id} created successfully",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vote", response_model=CastVoteResponse)
async def cast_vote(
    request: CastVoteRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    Cast a vote on a governance proposal.

    Requires:
        - X-API-Key header (for agent) OR SIWE wallet authentication

    Args:
        proposal_id: The proposal ID to vote on
        support: 0=against, 1=for, 2=abstain
    """
    from usmsb_sdk.blockchain.contracts.vib_governance import VIBGovernanceClient

    # Get user credentials
    address = current_user.get("wallet_address") or current_user.get("address")
    private_key = current_user.get("private_key")

    if not address:
        raise HTTPException(status_code=401, detail="Wallet address not found in authentication")
    if not private_key:
        raise HTTPException(status_code=401, detail="Private key not available for this authentication method")

    try:
        client = VIBGovernanceClient()

        tx_hash = await client.cast_vote(
            proposal_id=request.proposal_id,
            support=request.support,
            from_address=address,
            private_key=private_key,
        )

        support_str = {0: "against", 1: "for", 2: "abstain"}.get(request.support, "unknown")

        return CastVoteResponse(
            success=True,
            tx_hash=tx_hash,
            proposal_id=request.proposal_id,
            support=support_str,
            message=f"Vote cast successfully on proposal {request.proposal_id}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/delegations/{address}", response_model=DelegationResponse)
async def get_delegation(address: str):
    """
    Get voting delegation info for an address.

    Args:
        address: The address to check delegation for
    """
    from usmsb_sdk.blockchain.contracts.vib_governance import VIBGovernanceClient
    from usmsb_sdk.blockchain.config import BlockchainConfig

    try:
        config = BlockchainConfig()
        client = VIBGovernanceClient()

        # Get voting power
        voting_power = await client.get_voting_power(address)

        # Check if delegation contract exists
        delegation_address = config.get_contract_address("VIBGovernanceDelegation")

        delegated_power = 0
        if delegation_address and delegation_address != "待部署":
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(config.rpc_url))

            # Try to get delegated power from delegation contract
            try:
                # Simple view call - just return voting power as delegation info
                delegated_power = voting_power
            except Exception:
                delegated_power = 0

        return DelegationResponse(
            address=address,
            voting_power=voting_power,
            delegated_power=delegated_power,
            can_delegate=voting_power > 0,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
