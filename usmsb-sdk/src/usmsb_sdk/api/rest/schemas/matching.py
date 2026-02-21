"""
Matching-related Pydantic schemas.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class NegotiationRequest(BaseModel):
    """Schema for initiating negotiation."""

    initiator_id: str
    counterpart_id: str
    context: Dict[str, Any]


class ProposalRequest(BaseModel):
    """Schema for submitting a proposal."""

    price: float
    delivery_time: str
    payment_terms: str
    quality_guarantee: str = ""


class NetworkExploreRequest(BaseModel):
    """Schema for network exploration."""

    agent_id: str
    target_capabilities: Optional[List[str]] = None
    exploration_depth: int = 2


class RecommendationRequest(BaseModel):
    """Schema for requesting recommendations."""

    agent_id: str
    target_capability: str


class MatchRequest(BaseModel):
    """Schema for match request."""

    demand_id: str
    supplier_ids: List[str]
    criteria: Dict[str, Any] = {}


class MatchResponse(BaseModel):
    """Schema for match response."""

    match_id: str
    demand_id: str
    supplier_id: str
    score: float = 0.0
    status: str = "pending"
    created_at: float = 0.0
