"""
Environment-related Pydantic schemas.
"""

from typing import Any, Dict

from pydantic import BaseModel, Field


class GoalCreate(BaseModel):
    """Schema for creating a goal."""

    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    priority: int = Field(default=0, ge=0)


class EnvironmentCreate(BaseModel):
    """Schema for creating an environment."""

    name: str = Field(..., min_length=1)
    type: str = Field(default="social")
    state: Dict[str, Any] = Field(default_factory=dict)


class EnvironmentResponse(BaseModel):
    """Schema for environment response."""

    environment_id: str
    name: str
    type: str = "social"
    state: Dict[str, Any] = {}
    goals: list = []
    created_at: float = 0.0
    updated_at: float = 0.0
