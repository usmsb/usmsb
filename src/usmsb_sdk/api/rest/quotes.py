"""
Quotes Router

Provides endpoints for supply chain quote management.
"""

import logging
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quotes", tags=["Quotes"])


class QuoteRequest(BaseModel):
    """Quote request model."""
    request_id: str | None = None
    buyer_id: str
    product_id: str
    product_name: str
    quantity: float
    unit: str = "pieces"
    target_price: float | None = None
    delivery_date: str | None = None
    delivery_location: str | None = None
    requirements: dict = Field(default_factory=dict)


class QuoteResponse(BaseModel):
    """Quote response model."""
    quote_id: str | None = None
    request_id: str
    supplier_id: str
    product_id: str
    unit_price: float
    total_price: float
    currency: str = "USD"
    valid_until: str | None = None
    delivery_time_days: int | None = None
    terms: dict = Field(default_factory=dict)


# In-memory storage
_quote_requests = {}
_quotes = {}
_match_results = {}


@router.post("/request")
async def create_quote_request(request: QuoteRequest):
    """Create a new quote request."""
    request_id = request.request_id or str(uuid4())
    request.request_id = request_id

    _quote_requests[request_id] = {
        **request.dict(),
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending"
    }

    logger.info(f"Created quote request: {request_id}")

    return {"request_id": request_id, "status": "created"}


@router.get("/requests")
async def list_quote_requests():
    """List all quote requests."""
    return {"requests": list(_quote_requests.values())}


@router.get("/requests/{request_id}")
async def get_quote_request(request_id: str):
    """Get quote request by ID."""
    if request_id not in _quote_requests:
        raise HTTPException(status_code=404, detail="Quote request not found")
    return _quote_requests[request_id]


@router.post("/response")
async def submit_quote_response(response: QuoteResponse):
    """Submit a quote response."""
    quote_id = response.quote_id or str(uuid4())
    response.quote_id = quote_id

    _quotes[quote_id] = {
        **response.dict(),
        "created_at": datetime.utcnow().isoformat(),
        "status": "active"
    }

    logger.info(f"Submitted quote: {quote_id}")

    return {"quote_id": quote_id, "status": "submitted"}


@router.get("/responses")
async def list_quotes():
    """List all quotes."""
    return {"quotes": list(_quotes.values())}


@router.get("/responses/{quote_id}")
async def get_quote(quote_id: str):
    """Get quote by ID."""
    if quote_id not in _quotes:
        raise HTTPException(status_code=404, detail="Quote not found")
    return _quotes[quote_id]


@router.get("/requests/{request_id}/quotes")
async def get_quotes_for_request(request_id: str):
    """Get all quotes for a request."""
    quotes = [q for q in _quotes.values() if q.get("request_id") == request_id]
    return {"request_id": request_id, "quotes": quotes}


@router.post("/match/{request_id}")
async def create_match(request_id: str, quote_id: str):
    """Create a match between request and quote."""
    if request_id not in _quote_requests:
        raise HTTPException(status_code=404, detail="Quote request not found")
    if quote_id not in _quotes:
        raise HTTPException(status_code=404, detail="Quote not found")

    match_id = str(uuid4())
    _match_results[match_id] = {
        "match_id": match_id,
        "request_id": request_id,
        "quote_id": quote_id,
        "created_at": datetime.utcnow().isoformat(),
        "status": "matched"
    }

    _quote_requests[request_id]["status"] = "matched"
    _quotes[quote_id]["status"] = "matched"

    return {"match_id": match_id, "status": "matched"}


@router.get("/matches")
async def list_matches():
    """List all matches."""
    return {"matches": list(_match_results.values())}
