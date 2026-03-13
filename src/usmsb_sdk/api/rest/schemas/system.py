"""
System-related Pydantic schemas.
"""

from typing import Dict

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    version: str
    timestamp: float
    services: Dict[str, str]
