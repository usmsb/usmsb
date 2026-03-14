"""
Workflow-related Pydantic schemas.
"""


from pydantic import BaseModel, Field


class WorkflowCreate(BaseModel):
    """Schema for creating a workflow."""

    task_description: str = Field(..., min_length=1)
    agent_id: str
    available_tools: list[str] | None = None


class WorkflowResponse(BaseModel):
    """Schema for workflow response."""

    workflow_id: str
    task_description: str
    agent_id: str
    status: str = "pending"
    result: dict | None = None
    steps: list[dict] = []
    created_at: float = 0.0
