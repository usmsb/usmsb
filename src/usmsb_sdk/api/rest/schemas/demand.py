"""
Demand-related Pydantic schemas.
"""


from pydantic import BaseModel, Field


class DemandCreate(BaseModel):
    """Schema for creating a demand."""

    agent_id: str
    title: str
    description: str = ""
    category: str = ""
    required_skills: list[str] = Field(default_factory=list)
    budget_min: float | None = None
    budget_max: float | None = None
    deadline: str = ""
    priority: str = "medium"
    quality_requirements: str = ""


class SearchDemandsRequest(BaseModel):
    """Schema for searching demands."""

    agent_id: str
    capabilities: list[str]
    budget_min: float | None = None
    budget_max: float | None = None


class SearchSuppliersRequest(BaseModel):
    """Schema for searching suppliers."""

    agent_id: str
    required_skills: list[str]
    budget_min: float | None = None
    budget_max: float | None = None


class DemandResponse(BaseModel):
    """Schema for demand response."""

    demand_id: str
    agent_id: str
    title: str
    description: str = ""
    category: str = ""
    required_skills: list[str] = []
    budget_min: float | None = None
    budget_max: float | None = None
    deadline: str = ""
    priority: str = "medium"
    quality_requirements: str = ""
    status: str = "open"
    created_at: float = 0.0
