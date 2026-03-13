"""
Workflow-related Pydantic schemas.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class WorkflowCreate(BaseModel):
    """Schema for creating a workflow."""

    task_description: str = Field(..., min_length=1)
    agent_id: str
    available_tools: Optional[List[str]] = None


class WorkflowResponse(BaseModel):
    """Schema for workflow response."""

    workflow_id: str
    task_description: str
    agent_id: str
    status: str = "pending"
    result: Optional[dict] = None
    steps: List[dict] = []
    created_at: float = 0.0
