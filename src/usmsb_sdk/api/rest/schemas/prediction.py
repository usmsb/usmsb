"""
Prediction-related Pydantic schemas.
"""

from typing import Any

from pydantic import BaseModel


class PredictionRequest(BaseModel):
    """Schema for prediction request."""

    agent_id: str
    environment_id: str | None = None
    goal_name: str | None = None
    context: dict[str, Any] | None = None


class PredictionResponse(BaseModel):
    """Schema for prediction response."""

    prediction_id: str
    agent_id: str
    predicted_behavior: str
    confidence: float = 0.0
    reasoning: str = ""
    context: dict[str, Any] = {}
    created_at: float = 0.0
