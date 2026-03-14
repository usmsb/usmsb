"""
Collaboration-related Pydantic schemas.
"""


from pydantic import BaseModel


class CollaborationCreateRequest(BaseModel):
    """Schema for creating a collaboration."""

    goal_description: str
    required_skills: list[str]
    collaboration_mode: str = "hybrid"
    coordinator_agent_id: str


class CollaborationRoleAssignRequest(BaseModel):
    """Schema for assigning a role."""

    role_id: str
    agent_id: str


class CollaborationResponse(BaseModel):
    """Schema for collaboration response."""

    collaboration_id: str
    goal_description: str
    required_skills: list[str]
    collaboration_mode: str = "hybrid"
    coordinator_agent_id: str
    status: str = "forming"
    participants: list[str] = []
    created_at: float = 0.0
