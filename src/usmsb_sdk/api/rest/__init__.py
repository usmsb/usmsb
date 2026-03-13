"""
USMSB SDK REST API Module

This module provides the FastAPI-based REST API for the USMSB SDK,
including endpoints for agent management, predictions, simulations,
workflows, and more.

Key Components:
- app: FastAPI application instance
- Routers: Modular routers for different API domains
- Schemas: Pydantic models for request/response validation
- Services: Business logic layer

Usage:
    # Run the API server
    uvicorn usmsb_sdk.api.rest.main:app --host 0.0.0.0 --port 8000

    # Import app for custom applications
    from usmsb_sdk.api.rest.main import app

    # Import routers for custom applications
    from usmsb_sdk.api.rest.routers import (
        agents_router,
        environments_router,
        demands_router,
    )
"""

# Note: Due to circular import issues, import directly from submodules:
#   from usmsb_sdk.api.rest.main import app, run_server
#   from usmsb_sdk.api.rest.routers import agents_router, ...
#   from usmsb_sdk.api.rest.auth import router as auth_router
