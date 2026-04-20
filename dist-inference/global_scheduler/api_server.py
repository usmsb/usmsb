"""
Global Scheduler API Server
OpenAI Compatible API + Management API
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import time
import uuid

from shared.types import (
    InferenceRequest, InferenceResponse,
    NodeRegisterRequest, HeartbeatRequest,
    NodeCapability, NodeStatus, GPUInfo,
    RequestStatus, DailyEarningItem, RevenueStats,
    RevenueTrendItem, NodeEarningsRankingItem, WithdrawalRecord,
    UserInfo, NodeDetail, InferenceRequestRecord,
    ModelDetail, GpuPoolSummary, PlatformSettingsData,
)
from .gpu_pool import GPUPool
from .billing import BillingEngine
from .router import Router
from .model_registry import ModelRegistry
from . import ledgers


# ============ Pydantic Models ============

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = Field(default=2048, le=4096)
    stream: bool = False
    user: Optional[str] = None


class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionChoice(BaseModel):
    index: int
    message: Dict[str, str]
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: UsageInfo


# Settings update request
class SettingsUpdateRequest(BaseModel):
    platform_name: Optional[str] = None
    scheduler_url: Optional[str] = None
    gpu_rate: Optional[float] = None
    token_rate: Optional[float] = None
    platform_share: Optional[float] = None


# Node settings update
class NodeSettingsUpdate(BaseModel):
    wallet_address: Optional[str] = None
    preload_models: Optional[List[str]] = None
    gpu_threshold: Optional[int] = None
    maintenance_mode: Optional[str] = None
    maintenance_reason: Optional[str] = None


# Load model request
class LoadModelRequest(BaseModel):
    model_id: str


# Withdrawal request
class WithdrawRequest(BaseModel):
    wallet_address: str
    amount_vibe: float


# ============ App ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize SQLite
    from global_scheduler import db as db_module
    await db_module.init_db()
    # Load persisted state into in-memory caches
    await gpu_pool.load_from_db()
    model_registry.load_from_db()
    yield
    # Shutdown: close SQLite
    await db_module.close_db()


app = FastAPI(
    title="USMSB Distributed Inference API",
    description="OpenAI compatible API for distributed LLM inference",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global components
gpu_pool = GPUPool()
billing_engine = BillingEngine()
model_registry = ModelRegistry()
router = Router(gpu_pool, model_registry)


# ============ OpenAI-Compatible Endpoints ============

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(req: ChatCompletionRequest):
    """
    OpenAI compatible chat completions endpoint
    """
    user_id = req.user or "anonymous"

    # 1. Check balance
    balance = billing_engine.get_balance(user_id)
    estimated = billing_engine.estimate_cost(req.model, req.max_tokens)

    if balance < estimated and balance <= 0:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient Vibe balance. Required: {estimated}, Available: {balance}"
        )

    # 2. Check if model exists
    model_info = model_registry.get(req.model)
    if not model_info:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{req.model}' not found"
        )

    # 3. Create inference request
    inference_req = InferenceRequest.create(
        model_name=req.model,
        messages=[m.dict() for m in req.messages],
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        user_id=user_id
    )

    # 4. Dispatch and execute
    try:
        response = await router.execute(inference_req)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # 5. Charge user
    await billing_engine.charge(user_id, response.cost_vibe)

    # 6. Record in ledgers for revenue tracking
    node_reward = billing_engine.calculate_node_reward(
        response.gpu_seconds,
        response.usage.get("gpu_count", 1)
    )

    # Record inference
    await ledgers.inference_ledger.record(
        request_id=response.request_id,
        node_id=response.node_id,
        user_id=user_id,
        model_name=response.model_name,
        prompt_tokens=response.usage.get("prompt_tokens", 0),
        completion_tokens=response.usage.get("completion_tokens", 0),
        gpu_seconds=response.gpu_seconds,
        cost_vibe=response.cost_vibe,
        node_reward_vibe=node_reward,
    )

    # Update node earnings
    node_earnings = await ledgers.node_earnings_ledger.get_earnings(response.node_id)
    wallet_address = node_earnings.wallet_address if node_earnings else ""
    await ledgers.node_earnings_ledger.add_inference(
        node_id=response.node_id,
        wallet_address=wallet_address,
        cost_vibe=response.cost_vibe,
        node_reward_vibe=node_reward,
    )

    # Update user consumption
    await ledgers.user_ledger.record_consumption(
        wallet_address=user_id,
        cost_vibe=response.cost_vibe,
    )

    # 7. Return OpenAI format response
    return ChatCompletionResponse(
        id=response.request_id,
        created=int(time.time()),
        model=response.model_name,
        choices=[ChatCompletionChoice(
            index=0,
            message={"role": "assistant", "content": response.content},
            finish_reason=response.finish_reason
        )],
        usage=UsageInfo(
            prompt_tokens=response.usage.get("prompt_tokens", 0),
            completion_tokens=response.usage.get("completion_tokens", 0),
            total_tokens=response.usage.get("total_tokens", 0)
        )
    )


@app.get("/v1/models")
async def list_models():
    """List all available models (OpenAI format)"""
    models = model_registry.list_models()
    return {
        "object": "list",
        "data": [
            {
                "id": m.model_name,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "usmsb-dist-inference",
                "permission": []
            }
            for m in models
        ]
    }


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "ok",
        "timestamp": int(time.time()),
        "nodes": gpu_pool.get_summary()
    }


@app.post("/register")
async def register_node(req: NodeRegisterRequest):
    """Node registration"""
    node = NodeCapability(
        node_id=req.node_id,
        hostname=req.hostname,
        port=req.port,
        status=NodeStatus.IDLE,
        gpu_count=req.gpu_count,
        total_vram_gb=req.total_vram_gb,
        available_vram_gb=req.available_vram_gb,
        loaded_models=req.loaded_models,
        capabilities=req.capabilities,
        gpus=[
            GPUInfo(gpu_id=i, gpu_type=req.gpu_type, vram_gb=req.total_vram_gb // req.gpu_count)
            for i in range(req.gpu_count)
        ]
    )
    await gpu_pool.register_node(node)

    # Ensure node earnings record exists
    await ledgers.node_earnings_ledger.ensure_node(req.node_id, req.wallet_address or "")

    return {"status": "registered", "node_id": req.node_id}


@app.post("/heartbeat")
async def heartbeat(req: HeartbeatRequest):
    """Node heartbeat"""
    await gpu_pool.heartbeat(
        req.node_id,
        req.status,
        req.loaded_models,
        req.gpu_utilization,
        req.available_vram_gb
    )
    # Update last_active on node earnings
    node_earnings = await ledgers.node_earnings_ledger.get_earnings(req.node_id)
    if node_earnings:
        node_earnings.last_active = time.time()
    return {"status": "ok"}


class NodeWalletUpdateRequest(BaseModel):
    node_id: str
    wallet_address: str


@app.post("/node/wallet-update")
async def node_wallet_update(req: NodeWalletUpdateRequest):
    """Node notifies scheduler of wallet address change"""
    await ledgers.node_earnings_ledger.update_wallet(req.node_id, req.wallet_address)
    return {"status": "ok"}


@app.get("/v1/billing/balance/{user_id}")
async def get_balance(user_id: str):
    """Query user balance"""
    balance = billing_engine.get_balance(user_id)
    owed = billing_engine.get_owed(user_id)
    return {
        "user_id": user_id,
        "balance": balance,
        "owed": owed,
        "available": balance - owed
    }


@app.post("/v1/billing/deposit/{user_id}")
async def deposit(user_id: str, amount: float):
    """Deposit Vibe for testing"""
    await billing_engine.deposit(user_id, amount)
    return {"status": "ok", "new_balance": billing_engine.get_balance(user_id)}


# ============ Management API (/api prefix) ============

from fastapi import APIRouter

api_router = APIRouter(prefix="/api")


# GPU Pool
@api_router.get("/gpu-pool")
async def get_gpu_pool():
    """Get all GPU nodes with earnings data"""
    nodes = gpu_pool.get_all_nodes()
    result = []

    for node in nodes:
        earnings = await ledgers.node_earnings_ledger.get_earnings(node.node_id)
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_earn = 0.0
        if earnings:
            for d in earnings.daily_earnings:
                if d.date == today_str:
                    today_earn = d.revenue_vibe
                    break

        result.append(NodeDetail(
            node_id=node.node_id,
            wallet_address=earnings.wallet_address if earnings else "",
            hostname=node.hostname,
            port=node.port,
            status=node.status.value,
            gpu_count=node.gpu_count,
            gpus=node.gpus,
            total_vram_gb=node.total_vram_gb,
            available_vram_gb=node.available_vram_gb,
            loaded_models=node.loaded_models,
            last_heartbeat=node.last_heartbeat,
            registered_at=node.last_heartbeat,  # Simplified
            today_earnings=today_earn,
            total_earnings=earnings.total_revenue_vibe if earnings else 0.0,
            total_requests=earnings.total_requests if earnings else 0,
        ))

    summary = gpu_pool.get_summary()
    # Calculate today's requests
    today_str = datetime.now().strftime("%Y-%m-%d")
    total_requests_today = 0
    for n in result:
        earnings = await ledgers.node_earnings_ledger.get_earnings(n.node_id)
        if earnings:
            for d in earnings.daily_earnings:
                if d.date == today_str:
                    total_requests_today += d.requests

    return {
        "nodes": [n.__dict__ for n in result],
        "summary": GpuPoolSummary(
            total_nodes=summary["total_nodes"],
            idle_nodes=summary["idle_nodes"],
            busy_nodes=summary["busy_nodes"],
            offline_nodes=summary["offline_nodes"],
            total_gpus=sum(n.gpu_count for n in result),
            total_vram_gb=sum(n.total_vram_gb for n in result),
            total_requests_today=total_requests_today,
        ).__dict__,
    }


@api_router.get("/nodes/{node_id}")
async def get_node(node_id: str):
    """Get single node detail"""
    node = gpu_pool.nodes.get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    earnings = await ledgers.node_earnings_ledger.get_earnings(node_id)
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_earn = 0.0
    if earnings:
        for d in earnings.daily_earnings:
            if d.date == today_str:
                today_earn = d.revenue_vibe
                break

    return NodeDetail(
        node_id=node.node_id,
        wallet_address=earnings.wallet_address if earnings else "",
        hostname=node.hostname,
        port=node.port,
        status=node.status.value,
        gpu_count=node.gpu_count,
        gpus=node.gpus,
        total_vram_gb=node.total_vram_gb,
        available_vram_gb=node.available_vram_gb,
        loaded_models=node.loaded_models,
        last_heartbeat=node.last_heartbeat,
        registered_at=node.last_heartbeat,
        today_earnings=today_earn,
        total_earnings=earnings.total_revenue_vibe if earnings else 0.0,
        total_requests=earnings.total_requests if earnings else 0,
    ).__dict__


# Models
@api_router.get("/models")
async def get_models():
    """Get model registry in frontend format"""
    models = model_registry.list_models()
    result = []

    for m in models:
        # Count loaded nodes
        loaded_on = []
        total_req = 0
        for node in gpu_pool.get_all_nodes():
            if m.model_name in node.loaded_models:
                loaded_on.append(node.node_id)

        # Get stats from inference ledger
        stats = await ledgers.inference_ledger.get_total_stats()
        # This is global - for per-model we'd need to filter

        result.append(ModelDetail(
            model_id=m.model_name,
            name=m.model_name.split("/")[-1] if "/" in m.model_name else m.model_name,
            vram_required_gb=float(m.min_vram_per_gpu_gb * m.min_gpu_count),
            gpu_count_needed=m.min_gpu_count,
            is_preloaded=m.is_preloaded,
            loaded_on_nodes=loaded_on,
            total_requests=total_req,
            avg_latency_ms=0.0,
            description=f"{m.model_type.value.capitalize()} model",
        ))

    return {"models": [m.__dict__ for m in result]}


# Inference Requests
@api_router.get("/requests")
async def get_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    query: Optional[str] = None,
):
    """Get inference request history"""
    offset = (page - 1) * page_size

    # Get all records and filter
    records = await ledgers.inference_ledger.get_records(limit=1000)

    # Apply filters
    if query:
        query_lower = query.lower()
        records = [r for r in records if query_lower in r.request_id or query_lower in r.model_name]

    total = len(records)
    paged = records[offset:offset + page_size]

    def ts_to_iso(ts: float) -> str:
        from datetime import datetime
        return datetime.fromtimestamp(ts).isoformat()

    return {
        "requests": [
            InferenceRequestRecord(
                request_id=r.request_id,
                model_name=r.model_name,
                user_wallet=r.user_id,
                node_id=r.node_id,
                status="completed",
                input_tokens=r.prompt_tokens,
                output_tokens=r.completion_tokens,
                latency_ms=int(r.gpu_seconds * 1000),
                cost_vibe=r.cost_vibe,
                created_at=ts_to_iso(r.timestamp),
                completed_at=ts_to_iso(r.timestamp),
            ).__dict__
            for r in paged
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@api_router.get("/requests/{request_id}")
async def get_request(request_id: str):
    """Get single inference request"""
    records = await ledgers.inference_ledger.get_records(request_id=request_id, limit=1)
    if not records:
        raise HTTPException(status_code=404, detail="Request not found")

    r = records[0]
    return InferenceRequestRecord(
        request_id=r.request_id,
        model_name=r.model_name,
        user_wallet=r.user_id,
        node_id=r.node_id,
        status="completed",
        input_tokens=r.prompt_tokens,
        output_tokens=r.completion_tokens,
        latency_ms=int(r.gpu_seconds * 1000),
        cost_vibe=r.cost_vibe,
        created_at=datetime.fromtimestamp(r.timestamp).isoformat(),
        completed_at=datetime.fromtimestamp(r.timestamp).isoformat(),
    ).__dict__


# Revenue
@api_router.get("/revenue/stats")
async def get_revenue_stats():
    """Get revenue statistics"""
    stats = await ledgers.node_earnings_ledger.get_revenue_stats()
    inference_stats = await ledgers.inference_ledger.get_total_stats()

    return RevenueStats(
        total_revenue_vibe=stats["total_revenue_vibe"],
        today_revenue_vibe=stats["today_revenue_vibe"],
        month_revenue_vibe=stats["month_revenue_vibe"],
        gpu_time_revenue_vibe=stats["total_revenue_vibe"] * 0.7,  # Estimated
        token_fee_revenue_vibe=stats["total_revenue_vibe"] * 0.3,  # Estimated
        platform_share_vibe=stats["total_revenue_vibe"] * 0.30,
        node_payout_vibe=stats["total_revenue_vibe"] * 0.70,
    ).__dict__


@api_router.get("/revenue/trend")
async def get_revenue_trend(days: int = Query(30, ge=1, le=365)):
    """Get daily revenue trend"""
    trend = await ledgers.node_earnings_ledger.get_revenue_trend(days)
    return {"trend": trend}


@api_router.get("/revenue/nodes")
async def get_revenue_nodes():
    """Get node earnings rankings"""
    rankings = await ledgers.node_earnings_ledger.get_all_rankings()
    return {"rankings": rankings}


@api_router.get("/revenue/withdrawals")
async def get_withdrawals(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
):
    """Get withdrawal records"""
    offset = (page - 1) * page_size

    ws_status = None
    if status:
        from ledgers import WithdrawalStatus
        try:
            ws_status = WithdrawalStatus[status.upper()]
        except KeyError:
            pass

    withdrawals = await ledgers.withdrawal_ledger.get_withdrawals(
        status=ws_status,
        limit=page_size,
        offset=offset,
    )

    return {
        "withdrawals": [
            WithdrawalRecord(
                id=w.id,
                wallet_address=w.wallet_address,
                amount_vibe=w.amount_vibe,
                status=w.status.value,
                created_at=datetime.fromtimestamp(w.created_at).isoformat(),
                completed_at=datetime.fromtimestamp(w.completed_at).isoformat() if w.completed_at else None,
                tx_hash=w.tx_hash,
            ).__dict__
            for w in withdrawals
        ],
        "total": len(withdrawals),
        "page": page,
        "page_size": page_size,
    }


@api_router.post("/revenue/withdraw")
async def create_withdrawal(req: WithdrawRequest):
    """Create withdrawal request"""
    withdrawal = await ledgers.withdrawal_ledger.create(
        wallet_address=req.wallet_address,
        amount_vibe=req.amount_vibe,
    )
    return {
        "id": withdrawal.id,
        "status": withdrawal.status.value,
        "wallet_address": withdrawal.wallet_address,
        "amount_vibe": withdrawal.amount_vibe,
        "created_at": datetime.fromtimestamp(withdrawal.created_at).isoformat(),
    }


# Users
@api_router.get("/users")
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
):
    """Get user list"""
    offset = (page - 1) * page_size

    users = await ledgers.user_ledger.get_users(
        search=search,
        limit=page_size,
        offset=offset,
    )
    total = await ledgers.user_ledger.count(search=search)

    return {
        "users": [
            UserInfo(
                wallet_address=u.wallet_address,
                vibe_balance=billing_engine.get_balance(u.wallet_address),
                total_consumption=u.total_consumption_vibe,
                total_requests=u.total_requests,
                created_at=datetime.fromtimestamp(u.created_at).isoformat(),
                last_active=datetime.fromtimestamp(u.last_active).isoformat(),
            ).__dict__
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@api_router.get("/users/{wallet}")
async def get_user(wallet: str):
    """Get single user detail"""
    user = await ledgers.user_ledger.get_user(wallet)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserInfo(
        wallet_address=user.wallet_address,
        vibe_balance=billing_engine.get_balance(user.wallet_address),
        total_consumption=user.total_consumption_vibe,
        total_requests=user.total_requests,
        created_at=datetime.fromtimestamp(user.created_at).isoformat(),
        last_active=datetime.fromtimestamp(user.last_active).isoformat(),
    ).__dict__


# Settings
@api_router.get("/settings")
async def get_settings():
    """Get platform settings"""
    settings = await ledgers.settings_store.get()
    return PlatformSettingsData(
        platform_name=settings.platform_name,
        scheduler_url=settings.scheduler_url,
        gpu_rate=settings.gpu_rate,
        token_rate=settings.token_rate,
        platform_share=settings.platform_share,
    ).__dict__


@api_router.put("/settings")
async def update_settings(req: SettingsUpdateRequest):
    """Update platform settings"""
    update_data = req.dict(exclude_none=True)
    settings = await ledgers.settings_store.update(**update_data)
    return PlatformSettingsData(
        platform_name=settings.platform_name,
        scheduler_url=settings.scheduler_url,
        gpu_rate=settings.gpu_rate,
        token_rate=settings.token_rate,
        platform_share=settings.platform_share,
    ).__dict__


# Mount the API router
app.include_router(api_router)


# Get the global instances for testing
def get_gpu_pool() -> GPUPool:
    return gpu_pool


def get_billing_engine() -> BillingEngine:
    return billing_engine


def get_model_registry() -> ModelRegistry:
    return model_registry


def get_router() -> Router:
    return router
