"""
Governance API endpoints for AI Civilization Platform

Provides proposal management, voting, and governance statistics.
"""
import os
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
import time
import uuid

from usmsb_sdk.api.database import (
    create_proposal as db_create_proposal,
    get_proposals as db_get_proposals,
    vote_proposal as db_vote_proposal,
    get_user_by_address,
    get_session_by_token,
    get_db,
)

router = APIRouter(prefix="/governance", tags=["Governance"])


async def get_current_admin(authorization: Optional[str] = Header(None)) -> dict:
    """Dependency to get current admin user - requires admin privileges."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    access_token = authorization[7:]
    session = get_session_by_token(access_token)

    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    user = get_user_by_address(session['address'])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Check for admin privileges
    # Admin addresses can be configured via environment variable
    admin_addresses = os.environ.get("ADMIN_ADDRESSES", "").split(",")
    admin_addresses = [addr.strip().lower() for addr in admin_addresses if addr.strip()]

    if not admin_addresses:
        # If no admin addresses configured, check for is_admin flag
        if not user.get('is_admin'):
            raise HTTPException(status_code=403, detail="Admin access required")
    else:
        if user.get('wallet_address', '').lower() not in admin_addresses and not user.get('is_admin'):
            raise HTTPException(status_code=403, detail="Admin access required")

    return {**user, 'session': session}


# Pydantic models
class ProposalCreate(BaseModel):
    """Proposal creation request."""
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    proposal_type: str = "community_initiative"
    proposer_id: str
    changes: Dict[str, Any] = {}
    tags: List[str] = []


class ProposalResponse(BaseModel):
    """Proposal response."""
    id: str
    title: str
    description: str
    proposal_type: str
    proposer_id: str
    status: str
    votes_for: int
    votes_against: int
    quorum: float
    deadline: Optional[str]
    created_at: float


class VoteRequest(BaseModel):
    """Vote request."""
    voter_id: str
    support: bool  # True = for, False = against
    reason: Optional[str] = None


class GovernanceStats(BaseModel):
    """Governance statistics."""
    total_proposals: int
    active_proposals: int
    total_votes: int
    participation_rate: float


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """Dependency to get current user from access token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    access_token = authorization[7:]
    session = get_session_by_token(access_token)

    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    user = get_user_by_address(session['address'])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {**user, 'session': session}


@router.get("/proposals")
async def list_proposals(
    status: Optional[str] = None,
    limit: int = 50
):
    """List all proposals."""
    proposals = db_get_proposals()

    # Filter by status if provided
    if status:
        proposals = [p for e in proposals if p.get('status') == status]

    # Sort by created_at descending
    proposals.sort(key=lambda x: x.get('created_at', 0) or 0, reverse=True)

    return proposals[:limit]


@router.post("/proposals")
async def create_proposal(
    proposal: ProposalCreate,
    user: dict = Depends(get_current_user)
):
    """Create a new governance proposal."""
    # Check if user has enough stake (minimum 100 VIBE)
    user_stake = user.get('stake', 0)
    if user_stake < 100:
        raise HTTPException(
            status_code=403,
            detail="Minimum 100 VIBE stake required to create proposals"
        )

    # Create proposal
    now = time.time()
    deadline = now + (7 * 86400)  # 7 days

    proposal_data = {
        'title': proposal.title,
        'description': proposal.description,
        'proposer_id': user['id'],
        'status': 'voting',
        'deadline': str(deadline),
    }

    created = db_create_proposal(proposal_data)

    return {
        "success": True,
        "proposal": created,
        "message": "Proposal created successfully",
    }


@router.get("/proposals/{proposal_id}")
async def get_proposal(proposal_id: str):
    """Get a specific proposal."""
    proposals = db_get_proposals()
    for p in proposals:
        if p.get('id') == proposal_id:
            return p

    raise HTTPException(status_code=404, detail="Proposal not found")


@router.post("/proposals/{proposal_id}/vote")
async def cast_vote(
    proposal_id: str,
    vote: VoteRequest,
    user: dict = Depends(get_current_user)
):
    """Cast a vote on a proposal."""
    # Check if user has enough stake
    user_stake = user.get('stake', 0)
    if user_stake < 10:
        raise HTTPException(
            status_code=403,
            detail="Minimum 10 VIBE stake required to vote"
        )

    # Cast vote (1 = for, 0 = against)
    vote_value = 1 if vote.support else 0

    success = db_vote_proposal(proposal_id, user['id'], vote_value)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to cast vote")

    return {
        "success": True,
        "message": f"Vote cast: {'FOR' if vote.support else 'AGAINST'}",
        "proposal_id": proposal_id,
    }


@router.get("/stats")
async def get_governance_stats():
    """Get governance statistics."""
    proposals = db_get_proposals()

    total_proposals = len(proposals)
    active_proposals = sum(1 for p in proposals if p.get('status') in ['voting', 'pending'])
    total_votes = sum(p.get('votes_for', 0) + p.get('votes_against', 0) for p in proposals)

    return {
        "total_proposals": total_proposals,
        "active_proposals": active_proposals,
        "total_votes": total_votes,
        "participation_rate": 0.0,  # Would need more data to calculate
    }


@router.get("/my-proposals")
async def get_my_proposals(user: dict = Depends(get_current_user)):
    """Get proposals created by the current user."""
    proposals = db_get_proposals()
    my_proposals = [p for p in proposals if p.get('proposer_id') == user['id']]

    return my_proposals


@router.get("/my-votes")
async def get_my_votes(user: dict = Depends(get_current_user)):
    """Get votes cast by the current user."""
    # In production, would query a votes table filtered by user
    # For now, return empty list
    return []
