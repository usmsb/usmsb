"""
System-related Pydantic schemas.
"""


from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    version: str
    timestamp: float
    services: dict[str, str]
