"""
System endpoints (health, metrics).
"""

from datetime import datetime
from typing import Dict

from fastapi import APIRouter

from usmsb_sdk.api.database import get_metrics as db_get_metrics
from usmsb_sdk.api.rest.schemas.system import HealthResponse

router = APIRouter(tags=["System"])

# Global references (set by main.py)
_source_manager = None
_prediction_service = None
_workflow_service = None


def set_global_references(source_manager=None, prediction_service=None, workflow_service=None):
    """Set global service references."""
    global _source_manager, _prediction_service, _workflow_service
    _source_manager = source_manager
    _prediction_service = prediction_service
    _workflow_service = workflow_service


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health status."""
    services = {
        "llm": "available" if _source_manager and _source_manager.get_llm() else "unavailable",
        "prediction": "available" if _prediction_service else "unavailable",
        "workflow": "available" if _workflow_service else "unavailable",
    }

    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.now().timestamp(),
        services=services,
    )


@router.get("/metrics")
async def get_metrics_endpoint():
    """Get system metrics."""
    # Get metrics from database
    db_metrics = db_get_metrics()

    # Get registered external agents count
    external_agents_count = 0
    try:
        from usmsb_sdk.api.rest.agent_auth import _registered_agents
        external_agents_count = len(_registered_agents)
    except ImportError:
        pass

    metrics = {
        "agents_count": db_metrics.get('agents_count', 0) + external_agents_count,
        "environments_count": db_metrics.get('environments_count', 0),
        "ai_agents_count": db_metrics.get('ai_agents_count', 0) + external_agents_count,
        "services_count": db_metrics.get('active_services', 0),
        "demands_count": db_metrics.get('active_demands', 0),
        "opportunities_count": db_metrics.get('opportunities_count', 0),
        "negotiations_count": db_metrics.get('pending_negotiations', 0),
        "collaborations_count": db_metrics.get('collaborations_count', 0),
        "workflows_count": db_metrics.get('workflows_count', 0),
        "external_agents_count": external_agents_count,
    }

    if _source_manager:
        metrics["intelligence_sources"] = _source_manager.get_metrics()

    return metrics
