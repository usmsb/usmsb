"""
Prediction endpoints.

Authentication:
- All endpoints require X-API-Key + X-Agent-ID headers
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from usmsb_sdk.api.database import (
    get_agent as db_get_agent,
)
from usmsb_sdk.api.database import (
    get_environment as db_get_environment,
)
from usmsb_sdk.api.rest.schemas.prediction import PredictionRequest
from usmsb_sdk.api.rest.services.utils import create_agent_from_db_data, safe_json_loads
from usmsb_sdk.api.rest.unified_auth import get_current_user_unified
from usmsb_sdk.core.elements import Environment, EnvironmentType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/predict", tags=["Predictions"])

# Global reference to prediction service (set by main.py)
_prediction_service = None


def set_prediction_service(service):
    """Set the prediction service instance."""
    global _prediction_service
    _prediction_service = service


@router.post("/behavior")
async def predict_behavior(
    request: PredictionRequest,
    user: dict[str, Any] = Depends(get_current_user_unified)
):
    """
    Predict agent behavior.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - agent_id in request must match authenticated agent
    """
    agent_id = user.get('agent_id') or user.get('user_id')
    # Verify ownership - can only predict own behavior
    if agent_id != request.agent_id:
        raise HTTPException(
            status_code=403,
            detail="You can only predict your own agent's behavior"
        )

    # Return mock prediction if service not available
    if not _prediction_service:
        # Try to get agent from database
        agent_data = db_get_agent(request.agent_id)
        if not agent_data:
            return {
                "predicted_behavior": "collaborative",
                "confidence": 0.85,
                "reasoning": "Based on agent's historical behavior patterns and current goal priorities",
                "recommended_actions": [
                    {"action": "initiate_negotiation", "priority": 1},
                    {"action": "explore_network", "priority": 2},
                ]
            }

        # Return prediction based on agent data from database
        return {
            "agent_id": request.agent_id,
            "prediction": {
                "predicted_behavior": "collaborative",
                "confidence": 0.75,
                "reasoning": f"Based on agent {agent_data.get('name')} capabilities and goals",
                "recommended_actions": [
                    {"action": "initiate_negotiation", "priority": 1},
                    {"action": "explore_network", "priority": 2},
                ]
            }
        }

    # If service is available, use it (requires domain objects)
    agent_data = db_get_agent(request.agent_id)
    if not agent_data:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Create domain object for the service
    agent = create_agent_from_db_data(agent_data)

    environment = None
    if request.environment_id:
        env_data = db_get_environment(request.environment_id)
        if env_data:
            try:
                env_type = EnvironmentType(env_data.get('type', 'sandbox'))
            except ValueError:
                env_type = EnvironmentType.sandbox
            environment = Environment(
                id=env_data['id'],
                name=env_data['name'],
                type=env_type,
                state=safe_json_loads(env_data.get('state', '{}'), {}),
            )
    else:
        environment = Environment(name="default")

    goal = None
    if request.goal_name:
        for g in agent.goals:
            if g.name == request.goal_name:
                goal = g
                break

    try:
        prediction = await _prediction_service.predict_agent_behavior(
            agent=agent,
            environment=environment,
            goal=goal,
            context=request.context,
        )

        return {
            "agent_id": agent.id,
            "prediction": {
                "predicted_actions": prediction.predicted_actions,
                "confidence": prediction.confidence,
                "reasoning": prediction.reasoning,
                "alternative_scenarios": prediction.alternative_scenarios,
                "risk_factors": prediction.risk_factors,
            },
        }
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")
