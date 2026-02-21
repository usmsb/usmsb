"""
Demand-related Pydantic schemas.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class DemandCreate(BaseModel):
    """Schema for creating a demand."""

    agent_id: str
    title: str
    description: str = ""
    category: str = ""
    required_skills: List[str] = Field(default_factory=list)
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    deadline: str = ""
    priority: str = "medium"
    quality_requirements: str = ""


class SearchDemandsRequest(BaseModel):
    """Schema for searching demands."""

    agent_id: str
    capabilities: List[str]
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None


class SearchSuppliersRequest(BaseModel):
    """Schema for searching suppliers."""

    agent_id: str
    required_skills: List[str]
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None


class DemandResponse(BaseModel):
    """Schema for demand response."""

    demand_id: str
    agent_id: str
    title: str
    description: str = ""
    category: str = ""
    required_skills: List[str] = []
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    deadline: str = ""
    priority: str = "medium"
    quality_requirements: str = ""
    status: str = "open"
    created_at: float = 0.0
