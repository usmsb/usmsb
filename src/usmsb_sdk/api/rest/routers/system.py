"""
System endpoints (health, metrics, status).
"""

import platform
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter

from usmsb_sdk.api.database import get_db
from usmsb_sdk.api.database import get_metrics as db_get_metrics
from usmsb_sdk.api.rest.schemas.system import HealthResponse

router = APIRouter(tags=["System"])

# Global references (set by main.py)
_source_manager = None
_prediction_service = None
_workflow_service = None
_meta_agent = None
_start_time = time.time()


def set_global_references(
    source_manager=None,
    prediction_service=None,
    workflow_service=None,
    meta_agent=None
):
    """Set global service references."""
    global _source_manager, _prediction_service, _workflow_service, _meta_agent
    _source_manager = source_manager
    _prediction_service = prediction_service
    _workflow_service = workflow_service
    _meta_agent = meta_agent


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health status."""
    services = {
        "llm": "available" if _source_manager and _source_manager.get_llm() else "unavailable",
        "prediction": "available" if _prediction_service else "unavailable",
        "workflow": "available" if _workflow_service else "unavailable",
        "meta_agent": "available" if _meta_agent else "unavailable",
    }

    # Check database
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            services["database"] = "available"
    except Exception:
        services["database"] = "unavailable"

    # Determine overall status
    all_available = all(s == "available" for s in services.values())
    status = "healthy" if all_available else "degraded"

    return HealthResponse(
        status=status,
        version="1.1.0",
        timestamp=datetime.now().timestamp(),
        services=services,
    )


@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe - checks if the service is running."""
    return {"status": "alive", "timestamp": time.time()}


@router.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe - checks if the service is ready to accept traffic."""
    checks = {
        "database": False,
        "llm": False,
    }

    # Check database
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            checks["database"] = True
    except Exception:
        pass

    # Check LLM
    if _source_manager and _source_manager.get_llm():
        checks["llm"] = True

    ready = all(checks.values())
    return {
        "ready": ready,
        "checks": checks,
        "timestamp": time.time()
    }


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


@router.get("/status")
async def get_system_status() -> dict[str, Any]:
    """Get detailed system status."""
    # Calculate uptime
    uptime_seconds = time.time() - _start_time
    uptime_hours = uptime_seconds / 3600
    uptime_days = uptime_hours / 24

    # Get agent statistics by status
    agent_stats = {"online": 0, "offline": 0, "busy": 0}
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM agents
                WHERE unregistered_at IS NULL
                GROUP BY status
            """)
            for row in cursor.fetchall():
                status = row["status"]
                if status in agent_stats:
                    agent_stats[status] = row["count"]
    except Exception:
        pass

    # Get stake distribution
    stake_distribution = {"none": 0, "bronze": 0, "silver": 0, "gold": 0, "platinum": 0}
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    CASE
                        WHEN staked_amount >= 10000 THEN 'platinum'
                        WHEN staked_amount >= 5000 THEN 'gold'
                        WHEN staked_amount >= 1000 THEN 'silver'
                        WHEN staked_amount >= 100 THEN 'bronze'
                        ELSE 'none'
                    END as tier,
                    COUNT(*) as count
                FROM agent_wallets
                GROUP BY tier
            """)
            for row in cursor.fetchall():
                tier = row["tier"]
                if tier in stake_distribution:
                    stake_distribution[tier] = row["count"]
    except Exception:
        pass

    return {
        "version": "1.1.0",
        "uptime": {
            "seconds": int(uptime_seconds),
            "hours": round(uptime_hours, 2),
            "days": round(uptime_days, 2),
        },
        "platform": {
            "system": platform.system(),
            "python": platform.python_version(),
        },
        "agents": agent_stats,
        "stake_distribution": stake_distribution,
        "services": {
            "llm": _source_manager is not None and _source_manager.get_llm() is not None,
            "prediction": _prediction_service is not None,
            "workflow": _workflow_service is not None,
            "meta_agent": _meta_agent is not None,
        },
        "timestamp": time.time(),
    }


@router.get("/stats/summary")
async def get_stats_summary() -> dict[str, Any]:
    """Get summary statistics for dashboard."""
    stats = {
        "total_agents": 0,
        "online_agents": 0,
        "bound_agents": 0,
        "total_stake": 0,
        "total_balance": 0,
        "active_services": 0,
        "active_demands": 0,
        "active_collaborations": 0,
    }

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Agent counts
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'online' THEN 1 ELSE 0 END) as online,
                    SUM(CASE WHEN binding_status = 'bound' THEN 1 ELSE 0 END) as bound
                FROM agents
                WHERE unregistered_at IS NULL
            """)
            row = cursor.fetchone()
            if row:
                stats["total_agents"] = row["total"] or 0
                stats["online_agents"] = row["online"] or 0
                stats["bound_agents"] = row["bound"] or 0

            # Wallet totals
            cursor.execute("""
                SELECT
                    SUM(staked_amount) as total_stake,
                    SUM(vibe_balance) as total_balance
                FROM agent_wallets
            """)
            row = cursor.fetchone()
            if row:
                stats["total_stake"] = row["total_stake"] or 0
                stats["total_balance"] = row["total_balance"] or 0

            # Active services
            cursor.execute("""
                SELECT COUNT(*) as count FROM services WHERE status = 'active'
            """)
            row = cursor.fetchone()
            if row:
                stats["active_services"] = row["count"] or 0

            # Active demands
            cursor.execute("""
                SELECT COUNT(*) as count FROM demands WHERE status = 'active'
            """)
            row = cursor.fetchone()
            if row:
                stats["active_demands"] = row["count"] or 0

            # Active collaborations
            cursor.execute("""
                SELECT COUNT(*) as count FROM collaborations
                WHERE status IN ('analyzing', 'active', 'executing')
            """)
            row = cursor.fetchone()
            if row:
                stats["active_collaborations"] = row["count"] or 0

    except Exception:
        pass

    return stats

