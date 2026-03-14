"""
Dynamic Pricing API Endpoints

Provides REST API for intelligent pricing calculations.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from usmsb_sdk.api.rest.auth import get_current_user
from usmsb_sdk.services.dynamic_pricing_service import (
    PricingStrategy,
    ServiceCategory,
    get_dynamic_pricing_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pricing", tags=["Dynamic Pricing"])


class PriceCalculationRequest(BaseModel):
    """Request for price calculation."""

    base_price: float = Field(..., gt=0, description="Base reference price")
    service_type: str = Field(..., description="Type of service")
    supplier_id: str = Field(..., description="Service provider ID")
    demander_id: str | None = Field(None, description="Service requester ID")
    supplier_reputation: float = Field(0.5, ge=0, le=1, description="Supplier reputation score")
    demander_urgency: float = Field(0, ge=0, le=1, description="Request urgency (0-1)")
    service_category: str = Field("general", description="Service category")
    strategy: str = Field("dynamic", description="Pricing strategy")
    context: dict[str, Any] | None = Field(None, description="Additional context")


class ServiceStatsUpdateRequest(BaseModel):
    """Request to update service statistics."""

    suppliers: int | None = None
    demanders: int | None = None
    listings: int | None = None


class TransactionRecordRequest(BaseModel):
    """Request to record a transaction."""

    price: float = Field(..., gt=0)
    volume: float = Field(1.0, gt=0)


class PriceRecommendationRequest(BaseModel):
    """Request for price recommendation."""

    target_position: str = Field("market", description="budget, market, or premium")


@router.post("/calculate")
async def calculate_price(request: PriceCalculationRequest, user: dict = Depends(get_current_user)):
    """
    Calculate intelligent price based on market conditions.

    Factors considered:
    - Supply-demand equilibrium
    - Quality/reputation factor
    - Market momentum
    - Time urgency
    - Service scarcity
    - Competitive positioning
    """
    try:
        service = await get_dynamic_pricing_service()

        try:
            category = ServiceCategory(request.service_category.lower())
        except ValueError:
            category = ServiceCategory.GENERAL

        try:
            strategy = PricingStrategy(request.strategy.lower())
        except ValueError:
            strategy = PricingStrategy.DYNAMIC

        result = await service.calculate_price(
            base_price=request.base_price,
            service_type=request.service_type,
            supplier_id=request.supplier_id,
            demander_id=request.demander_id,
            supplier_reputation=request.supplier_reputation,
            demander_urgency=request.demander_urgency,
            service_category=category,
            strategy=strategy,
            context=request.context or {},
        )

        return result.to_dict()

    except Exception as e:
        logger.error(f"Price calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{service_type}/stats")
async def update_service_stats(
    service_type: str, request: ServiceStatsUpdateRequest, user: dict = Depends(get_current_user)
):
    """Update market statistics for a service type."""
    service = await get_dynamic_pricing_service()

    service.update_service_stats(
        service_type=service_type,
        suppliers=request.suppliers,
        demanders=request.demanders,
        listings=request.listings,
    )

    return {"success": True, "service_type": service_type}


@router.post("/{service_type}/transaction")
async def record_transaction(
    service_type: str, request: TransactionRecordRequest, user: dict = Depends(get_current_user)
):
    """Record a transaction for price history tracking."""
    service = await get_dynamic_pricing_service()

    service.record_transaction(
        service_type=service_type,
        price=request.price,
        volume=request.volume,
    )

    return {
        "success": True,
        "service_type": service_type,
        "recorded_price": request.price,
    }


@router.post("/{service_type}/recommendation")
async def get_price_recommendation(
    service_type: str,
    request: PriceRecommendationRequest,
):
    """Get price recommendation for a service type."""
    service = await get_dynamic_pricing_service()

    result = service.get_price_recommendation(
        service_type=service_type,
        target_position=request.target_position,
    )

    if not result:
        raise HTTPException(
            status_code=404, detail=f"No price history available for service type: {service_type}"
        )

    return {
        "service_type": service_type,
        **result,
    }


@router.get("/{service_type}/history")
async def get_price_history(
    service_type: str,
    days: int = Query(7, ge=1, le=30, description="Number of days"),
):
    """Get price history for a service type."""
    service = await get_dynamic_pricing_service()

    history = service.get_service_price_history(
        service_type=service_type,
        days=days,
    )

    return {
        "service_type": service_type,
        "days": days,
        "count": len(history),
        "history": history,
    }


@router.get("/{service_type}/market")
async def get_market_conditions(
    service_type: str,
):
    """Get current market conditions for a service type."""
    service = await get_dynamic_pricing_service()

    conditions = service._get_market_conditions_summary(service_type)

    return conditions


@router.get("/stats")
async def get_pricing_stats():
    """Get overall pricing service statistics."""
    service = await get_dynamic_pricing_service()

    return service.get_statistics()


@router.get("/strategies")
async def list_pricing_strategies():
    """List available pricing strategies."""
    return {
        "strategies": [
            {
                "name": "conservative",
                "description": "Lower prices, faster deals",
                "use_case": "When you want to close deals quickly",
            },
            {
                "name": "balanced",
                "description": "Market equilibrium pricing",
                "use_case": "Standard market-aligned pricing",
            },
            {
                "name": "aggressive",
                "description": "Higher prices, maximize profit",
                "use_case": "When you have strong reputation and demand",
            },
            {
                "name": "dynamic",
                "description": "Auto-adjust based on conditions",
                "use_case": "Let the system optimize pricing",
            },
            {
                "name": "auction",
                "description": "Competitive bidding mode",
                "use_case": "When multiple buyers compete",
            },
        ]
    }


@router.get("/categories")
async def list_service_categories():
    """List available service categories."""
    return {
        "categories": [
            {
                "name": "general",
                "description": "Common services with many providers",
                "scarcity_factor": "0.95x (competitive)",
            },
            {
                "name": "specialized",
                "description": "Requires specific skills",
                "scarcity_factor": "1.10x (moderate premium)",
            },
            {
                "name": "rare",
                "description": "Very few providers available",
                "scarcity_factor": "1.30x (significant premium)",
            },
            {
                "name": "unique",
                "description": "One-of-a-kind capabilities",
                "scarcity_factor": "1.50x (high premium)",
            },
        ]
    }
