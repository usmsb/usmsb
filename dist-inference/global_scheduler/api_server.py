"""
Global Scheduler API Server
OpenAI Compatible API
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import time
import uuid

from shared.types import (
    InferenceRequest, InferenceResponse,
    NodeRegisterRequest, HeartbeatRequest,
    NodeCapability, NodeStatus, GPUInfo
)
from .gpu_pool import GPUPool
from .billing import BillingEngine
from .router import Router
from .model_registry import ModelRegistry


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


# ============ App ============

app = FastAPI(
    title="USMSB Distributed Inference API",
    description="OpenAI compatible API for distributed LLM inference",
    version="0.1.0"
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


# ============ API Endpoints ============

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(req: ChatCompletionRequest):
    """
    OpenAI compatible chat completions endpoint
    """
    # 1. Check balance
    user_id = req.user or "anonymous"
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

    # 5. Charge
    billing_engine.charge(user_id, response.cost_vibe)

    # 6. Return OpenAI format response
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
            prompt_tokens=response.usage["prompt_tokens"],
            completion_tokens=response.usage["completion_tokens"],
            total_tokens=response.usage["total_tokens"]
        )
    )


@app.get("/v1/models")
async def list_models():
    """List all available models"""
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


# For testing - allow setting balance
@app.post("/v1/billing/deposit/{user_id}")
async def deposit(user_id: str, amount: float):
    """Deposit Vibe for testing"""
    billing_engine.deposit(user_id, amount)
    return {"status": "ok", "new_balance": billing_engine.get_balance(user_id)}


# Get the global instances for testing
def get_gpu_pool() -> GPUPool:
    return gpu_pool


def get_billing_engine() -> BillingEngine:
    return billing_engine


def get_model_registry() -> ModelRegistry:
    return model_registry


def get_router() -> Router:
    return router
