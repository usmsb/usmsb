"""
Prediction-related Pydantic schemas.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel


class PredictionRequest(BaseModel):
    """Schema for prediction request."""

    agent_id: str
    environment_id: Optional[str] = None
    goal_name: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class PredictionResponse(BaseModel):
    """Schema for prediction response."""

    prediction_id: str
    agent_id: str
    predicted_behavior: str
    confidence: float = 0.0
    reasoning: str = ""
    context: Dict[str, Any] = {}
    created_at: float = 0.0
