"""
USMSB SDK REST API

FastAPI-based REST API for the USMSB SDK.
Provides endpoints for agent management, predictions, simulations, and workflows.
"""

import os
import sys
from pathlib import Path

# Load .env file from various possible locations
# Start from the file location and walk up
module_dir = Path(__file__).resolve().parent  # usmsb_sdk/api/rest
for _ in range(6):  # max 6 levels up
    env_path = module_dir / ".env"
    if env_path.exists():
        break
    module_dir = module_dir.parent

if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)

import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from usmsb_sdk.config.settings import get_settings, Settings
from usmsb_sdk.intelligence_adapters.base import IntelligenceSourceConfig, IntelligenceSourceType
from usmsb_sdk.intelligence_adapters.llm.openai_adapter import OpenAIAdapter
from usmsb_sdk.intelligence_adapters.llm.minimax_adapter import MiniMaxAdapter
from usmsb_sdk.intelligence_adapters.manager import IntelligenceSourceManager, SelectionStrategy
from usmsb_sdk.services.behavior_prediction_service import BehaviorPredictionService
from usmsb_sdk.services.agentic_workflow_service import AgenticWorkflowService
from usmsb_sdk.services.matching_engine import MatchingEngine

# Import database module
from usmsb_sdk.api.database import (
    init_db,
    check_and_mark_offline_agents,
    auto_unregister_inactive_agents,
    AUTO_UNREGISTER_GRACE_PERIOD,
    AUTO_UNREGISTER_CHECK_INTERVAL,
)

# Import existing routers
from usmsb_sdk.api.rest.auth import router as auth_router
from usmsb_sdk.api.rest.transactions import router as transactions_router
from usmsb_sdk.api.rest.environment import router as environment_router
from usmsb_sdk.api.rest.governance import router as governance_router
from usmsb_sdk.api.rest.agent_auth import router as agent_auth_router
from usmsb_sdk.api.rest.quotes import router as quotes_router
from usmsb_sdk.api.rest.dynamic_pricing import router as dynamic_pricing_router

# Import new modular routers
from usmsb_sdk.api.rest.routers import (
    agents_router,
    environments_router,
    demands_router,
    predictions_router,
    workflows_router,
    matching_router,
    network_router,
    collaborations_router,
    learning_router,
    registration_router,
    services_router,
    system_router,
    gene_capsule_router,
    pre_match_negotiation_router,
    meta_agent_matching_router,
    staking_router,
    reputation_router,
    wallet_router,
    heartbeat_router,
)

# Import Meta Agent router
from usmsb_sdk.api.rest.meta_agent import router as meta_agent_router

# Import WebSocket manager
from usmsb_sdk.api.rest.websocket import get_ws_manager

logger = logging.getLogger(__name__)

# Global instances
settings: Settings = None
source_manager: IntelligenceSourceManager = None
prediction_service: BehaviorPredictionService = None
workflow_service: AgenticWorkflowService = None
matching_engine: MatchingEngine = None
heartbeat_monitor_task: asyncio.Task = None
auto_unregister_task: asyncio.Task = None


async def heartbeat_monitor():
    """Background task to monitor agent heartbeats and mark offline agents.

    Runs every 30 seconds to check for agents with expired TTL.
    """
    while True:
        try:
            await asyncio.sleep(30)  # Check every 30 seconds
            offline_count = check_and_mark_offline_agents()
            if offline_count > 0:
                logger.info(f"Heartbeat monitor: marked {offline_count} agents as offline")
        except asyncio.CancelledError:
            logger.info("Heartbeat monitor task cancelled")
            break
        except Exception as e:
            logger.error(f"Heartbeat monitor error: {e}")


async def auto_unregister_monitor():
    """Background task to auto-unregister inactive agents without wallet binding.

    Auto-unregister rules:
    - AI agents WITHOUT wallet binding: Auto-unregister (DELETE) after grace period
    - AI agents WITH wallet binding: Keep but mark as offline
    - Human agents: Never auto-unregister
    - System agents: Never auto-unregister

    Grace period: 24 hours by default (configurable via AUTO_UNREGISTER_GRACE_PERIOD)
    Check interval: 1 hour by default (configurable via AUTO_UNREGISTER_CHECK_INTERVAL)
    """
    while True:
        try:
            # Check interval (default: 1 hour)
            await asyncio.sleep(AUTO_UNREGISTER_CHECK_INTERVAL)

            result = auto_unregister_inactive_agents()

            if result["unregistered"] > 0:
                logger.info(
                    f"Auto-unregister: removed {result['unregistered']} inactive agents without wallet binding"
                )
            if result["kept"] > 0:
                logger.debug(f"Auto-unregister: kept {result['kept']} agents with wallet binding")
            if result["errors"]:
                for error in result["errors"]:
                    logger.error(f"Auto-unregister error for {error['agent_id']}: {error['error']}")

        except asyncio.CancelledError:
            logger.info("Auto-unregister monitor task cancelled")
            break
        except Exception as e:
            logger.error(f"Auto-unregister monitor error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global \
        settings, \
        source_manager, \
        prediction_service, \
        workflow_service, \
        matching_engine, \
        heartbeat_monitor_task

    # Startup
    logger.info("Starting USMSB SDK API...")

    # Initialize database
    logger.info("Initializing SQLite database...")
    init_db()
    logger.info("Database initialized successfully!")

    settings = get_settings()
    logger.info(f"Loaded settings for environment: {settings.environment}")

    # Initialize intelligence source manager
    source_manager = IntelligenceSourceManager(selection_strategy=SelectionStrategy.PRIORITY)

    # Register MiniMax adapter if API key is available
    minimax_api_key = os.getenv("MINIMAX_API_KEY")
    if minimax_api_key:
        llm_config = IntelligenceSourceConfig(
            name="minimax",
            type=IntelligenceSourceType.LLM,
            api_key=minimax_api_key,
            model="MiniMax-M2.5",
            extra_params={
                "temperature": settings.llm.temperature,
                "max_tokens": settings.llm.max_tokens,
                "base_url": os.getenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/anthropic"),
            },
        )
        adapter = MiniMaxAdapter(llm_config)
        await adapter.initialize()
        await source_manager.register_source(
            name="minimax",
            source=adapter,
            priority=1,
            is_primary=True,
        )
        logger.info("MiniMax adapter registered")

    # Initialize services
    llm = source_manager.get_llm()
    if llm:
        prediction_service = BehaviorPredictionService(llm)
        workflow_service = AgenticWorkflowService(llm)
        logger.info("Application services initialized")

    # Initialize matching engine
    matching_engine = MatchingEngine(llm_adapter=llm if llm else None)
    logger.info("Matching engine initialized")

    # Set service references in routers
    from usmsb_sdk.api.rest.routers.predictions import set_prediction_service
    from usmsb_sdk.api.rest.routers.workflows import set_workflow_service
    from usmsb_sdk.api.rest.routers.matching import set_matching_engine
    from usmsb_sdk.api.rest.routers.system import set_global_references

    set_prediction_service(prediction_service)
    set_workflow_service(workflow_service)
    set_matching_engine(matching_engine)
    set_global_references(
        source_manager=source_manager,
        prediction_service=prediction_service,
        workflow_service=workflow_service,
    )

    # Initialize Meta Agent
    from usmsb_sdk.platform.external.meta_agent.agent import MetaAgent
    from usmsb_sdk.platform.external.meta_agent.meta_agent_config import MetaAgentConfig
    from usmsb_sdk.platform.external.meta_agent.permission import PermissionManager
    from usmsb_sdk.api.rest.meta_agent import set_meta_agent, set_permission_manager

    meta_agent = MetaAgent(MetaAgentConfig.from_env())
    await meta_agent._init_components()
    await meta_agent._register_default_tools()
    set_meta_agent(meta_agent)
    logger.info("Meta Agent initialized")

    # Initialize Permission Manager
    try:
        permission_manager = PermissionManager("meta_agent.db")
        await permission_manager.init()
        set_permission_manager(permission_manager)
        logger.info("Permission Manager initialized")
    except Exception as e:
        import traceback

        logger.error(f"Failed to initialize Permission Manager: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        set_permission_manager(None)

    # Initialize MetaAgentService for precise matching
    from usmsb_sdk.platform.external.meta_agent.services.meta_agent_service import MetaAgentService
    from usmsb_sdk.platform.external.meta_agent.tools.precise_matching import set_meta_agent_service

    meta_agent_service = MetaAgentService(meta_agent=meta_agent)
    set_meta_agent_service(meta_agent_service)
    logger.info("MetaAgentService initialized")

    logger.info("USMSB SDK API started successfully")

    # Start heartbeat monitor background task
    heartbeat_monitor_task = asyncio.create_task(heartbeat_monitor())
    logger.info("Heartbeat monitor started")

    # Start auto-unregister monitor background task
    auto_unregister_task = asyncio.create_task(auto_unregister_monitor())
    logger.info(
        f"Auto-unregister monitor started (grace period: {AUTO_UNREGISTER_GRACE_PERIOD}s, check interval: {AUTO_UNREGISTER_CHECK_INTERVAL}s)"
    )

    yield

    # Shutdown
    logger.info("Shutting down USMSB SDK API...")

    # Cancel heartbeat monitor task
    if heartbeat_monitor_task:
        heartbeat_monitor_task.cancel()
        try:
            await heartbeat_monitor_task
        except asyncio.CancelledError:
            pass
        logger.info("Heartbeat monitor stopped")

    # Cancel auto-unregister monitor task
    if auto_unregister_task:
        auto_unregister_task.cancel()
        try:
            await auto_unregister_task
        except asyncio.CancelledError:
            pass
        logger.info("Auto-unregister monitor stopped")

    if source_manager:
        await source_manager.shutdown_all()
    logger.info("USMSB SDK API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="USMSB SDK API",
    description="REST API for the USMSB (Universal System Model of Social Behavior) SDK",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Request Tracing Middleware
from usmsb_sdk.api.rest.request_tracing import RequestTracingMiddleware
app.add_middleware(RequestTracingMiddleware)

# Add Rate Limiting Middleware
from usmsb_sdk.api.rest.rate_limiter import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware)

# Import error handler
from usmsb_sdk.api.rest.error_handler import APIError, api_error_handler
app.add_exception_handler(APIError, api_error_handler)

# Include existing routers
app.include_router(auth_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(environment_router, prefix="/api")
app.include_router(governance_router, prefix="/api")
app.include_router(agent_auth_router, prefix="/api")
app.include_router(quotes_router, prefix="/api")
app.include_router(dynamic_pricing_router, prefix="/api")

# Include new modular routers
app.include_router(agents_router, prefix="/api")
app.include_router(environments_router, prefix="/api")
app.include_router(demands_router, prefix="/api")
app.include_router(predictions_router, prefix="/api")
app.include_router(workflows_router, prefix="/api")
app.include_router(matching_router, prefix="/api")
app.include_router(network_router, prefix="/api")
app.include_router(collaborations_router, prefix="/api")
app.include_router(learning_router, prefix="/api")
app.include_router(registration_router, prefix="/api")
app.include_router(services_router, prefix="/api")
app.include_router(system_router, prefix="/api")
app.include_router(gene_capsule_router, prefix="/api")
app.include_router(pre_match_negotiation_router, prefix="/api")
app.include_router(meta_agent_router, prefix="/api")
app.include_router(meta_agent_matching_router, prefix="/api")
app.include_router(staking_router, prefix="/api")
app.include_router(reputation_router, prefix="/api")
app.include_router(wallet_router, prefix="/api")
app.include_router(heartbeat_router, prefix="/api")


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication."""
    manager = await get_ws_manager()
    client = await manager.connect(websocket)
    try:
        while True:
            try:
                data = await websocket.receive_json()
                await manager.handle_message(websocket, data)
            except WebSocketDisconnect:
                break
    finally:
        await manager.disconnect(websocket)


# Metrics endpoint for Prometheus scraping
@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint for monitoring auto-unregister mechanism."""
    from usmsb_sdk.api.rest.metrics import get_auto_unregister_metrics
    from fastapi.responses import PlainTextResponse

    metrics_text = get_auto_unregister_metrics()
    return PlainTextResponse(content=metrics_text, media_type="text/plain")


# Cache statistics endpoint
@app.get("/cache-stats")
async def cache_stats_endpoint():
    """Get cache statistics for monitoring cache performance."""
    from usmsb_sdk.api.cache import cache_manager

    return cache_manager.get_stats()


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "timestamp": datetime.now().isoformat()},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "timestamp": datetime.now().isoformat()},
    )


def run_server():
    """Run the API server."""
    import uvicorn

    uvicorn.run(
        "usmsb_sdk.api.rest.main:app",
        host=settings.api.host if settings else "0.0.0.0",
        port=settings.api.port if settings else 8000,
        reload=settings.api.debug if settings else False,
    )


if __name__ == "__main__":
    run_server()
