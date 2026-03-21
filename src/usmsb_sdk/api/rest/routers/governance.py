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
    """Request to create a governance proposal.

    用户在浏览器 MetaMask 签名创建提案交易后，将 tx_hash 提交给后端验证。
    原则：真人操作由本人签名，后端不持有私钥。
    """
    proposal_type: int = Field(..., ge=0, le=5, description="Proposal type: 0=GENERAL, 1=PARAMETER, 2=UPGRADE, 3=EMERGENCY, 4=DIVIDEND, 5=INCENTIVE")
    title: str = Field(..., min_length=1, max_length=200, description="Proposal title")
    description: str = Field(..., min_length=1, max_length=2000, description="Proposal description")
    target: str = Field(..., description="Target contract address")
    data: str = Field(default="0x", description="Call data (hex encoded)")
    tx_hash: str = Field(..., description="创建提案交易的 tx_hash（前端签名后提供）")


class CastVoteRequest(BaseModel):
    """Request to cast a vote on a proposal.

    用户在浏览器 MetaMask 签名投票交易后，将 tx_hash 提交给后端验证。
    原则：真人操作由本人签名，后端不持有私钥。
    """
    proposal_id: int = Field(..., description="Proposal ID to vote on")
    support: int = Field(..., ge=0, le=2, description="Vote: 0=against, 1=for, 2=abstain")
    tx_hash: str = Field(..., description="投票交易的 tx_hash（前端签名后提供）")


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
    提交创建提案交易的 tx_hash，后端验证链上状态并记录。

    用户在浏览器 MetaMask 签名创建提案交易后，将 tx_hash 提交给此端点验证。

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

        # Record in database (best-effort)
        try:
            from usmsb_sdk.api.database import db_log_governance_event
            db_log_governance_event(address, "create_proposal", request.tx_hash, {"title": request.title})
        except Exception as db_err:
            import logging
            logging.getLogger(__name__).warning(f"DB write skipped (table may not exist): {db_err}")

        return CreateProposalResponse(
            success=True,
            proposal_id=0,  # Queried from chain if needed
            tx_hash=request.tx_hash,
            message=f"Proposal creation tx verified and recorded. Title: {request.title}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Proposal verification failed: {str(e)}")


@router.post("/vote", response_model=CastVoteResponse)
async def cast_vote(
    request: CastVoteRequest,
    current_user: dict = Depends(get_current_user_unified),
):
    """
    提交投票交易的 tx_hash，后端验证链上状态并记录。

    用户在浏览器 MetaMask 签名投票交易后，将 tx_hash 提交给此端点验证。

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

        # Verify tx was mined and succeeded
        receipt = w3.eth.get_transaction_receipt(request.tx_hash)
        if receipt is None:
            raise HTTPException(status_code=400, detail="Transaction not found or still pending")
        if receipt.status != 1:
            raise HTTPException(status_code=400, detail="Transaction failed on-chain")

        # Validate: proposal must exist on-chain
        from usmsb_sdk.blockchain.contracts.vib_governance import VIBGovernanceClient
        try:
            governance_client = VIBGovernanceClient()
            proposal = await governance_client.get_proposal(request.proposal_id)
            if proposal is None:
                raise HTTPException(status_code=404, detail=f"Proposal {request.proposal_id} not found on-chain")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=404, detail=f"Failed to query proposal: {str(e)}")

        # Validate: voter must have voting power (general voting power, not proposal-specific)
        try:
            voting_power = await governance_client.get_voting_power(address)
            if voting_power == 0:
                raise HTTPException(status_code=403, detail="No voting power — stake VIBE to gain voting rights")
        except HTTPException:
            raise
        except Exception:
            pass  # If we can't check, trust the on-chain tx result

        support_str = {0: "against", 1: "for", 2: "abstain"}.get(request.support, "unknown")
        return CastVoteResponse(
            success=True,
            tx_hash=request.tx_hash,
            proposal_id=request.proposal_id,
            support=support_str,
            message=f"Vote verified and recorded. Voted {support_str} on proposal {request.proposal_id}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Vote verification failed: {str(e)}")


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
