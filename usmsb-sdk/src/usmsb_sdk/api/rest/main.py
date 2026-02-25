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
from usmsb_sdk.api.database import init_db

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global settings, source_manager, prediction_service, workflow_service, matching_engine

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
    permission_manager = PermissionManager("meta_agent.db")
    await permission_manager.init()
    set_permission_manager(permission_manager)
    logger.info("Permission Manager initialized")

    # Initialize MetaAgentService for precise matching
    from usmsb_sdk.platform.external.meta_agent.services.meta_agent_service import MetaAgentService
    from usmsb_sdk.platform.external.meta_agent.tools.precise_matching import set_meta_agent_service

    meta_agent_service = MetaAgentService(meta_agent=meta_agent)
    set_meta_agent_service(meta_agent_service)
    logger.info("MetaAgentService initialized")

    logger.info("USMSB SDK API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down USMSB SDK API...")
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

# Include existing routers
app.include_router(auth_router)
app.include_router(transactions_router)
app.include_router(environment_router)
app.include_router(governance_router)
app.include_router(agent_auth_router)
app.include_router(quotes_router)
app.include_router(dynamic_pricing_router)

# Include new modular routers
app.include_router(agents_router)
app.include_router(environments_router)
app.include_router(demands_router)
app.include_router(predictions_router)
app.include_router(workflows_router)
app.include_router(matching_router)
app.include_router(network_router)
app.include_router(collaborations_router)
app.include_router(learning_router)
app.include_router(registration_router)
app.include_router(services_router)
app.include_router(system_router)
app.include_router(gene_capsule_router)
app.include_router(pre_match_negotiation_router)
app.include_router(meta_agent_router)
app.include_router(meta_agent_matching_router)


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
