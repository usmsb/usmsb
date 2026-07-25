"""
Node Executor - Executor
"""

import asyncio
import httpx
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from shared.types import InferenceRequest, InferenceResponse
from .gpu_monitor import GPUMonitor
from .model_manager import ModelManager
from .vllm_engine import VLLMEngine


# ============ API Models ============

class InferenceRequestAPI(BaseModel):
    request_id: str
    model_name: str
    messages: List[Dict[str, str]]
    temperature: float = 0.7
    max_tokens: int = 2048
    llm_context: Dict[str, Any]


class InferenceResponseAPI(BaseModel):
    request_id: str
    model_name: str
    content: str
    usage: Dict[str, int]
    gpu_seconds: float
    cost_vibe: float
    node_id: str
    finish_reason: str = "stop"
    error: Optional[str] = None


class LoadModelRequest(BaseModel):
    model_id: str


class NodeSettingsUpdate(BaseModel):
    wallet_address: Optional[str] = None
    preload_models: Optional[List[str]] = None
    gpu_threshold: Optional[int] = None
    maintenance_mode: Optional[str] = None
    maintenance_reason: Optional[str] = None


# ============ Node State ============

# Global state (set by NodeExecutor.start() before uvicorn serves)
vllm_engine: VLLMEngine = None
model_manager: ModelManager = None
gpu_monitor: GPUMonitor = None
node_id: str = "unknown"
start_time: float = time.time()
VERSION: str = "0.1.0"
scheduler_url: str = "http://localhost:8000"

# Node settings
node_settings: Dict[str, Any] = {
    "wallet_address": "",
    "preload_models": [],
    "gpu_threshold": 80,
    "maintenance_mode": "normal",  # normal | maintenance | offline
    "maintenance_reason": "",
}

# Inference history (capped at 1000)
inference_history: List[Dict[str, Any]] = []

# Model stats
model_stats: Dict[str, Dict[str, Any]] = {}  # {model_name: {total_requests, total_tokens, total_gpu_seconds}}


# ============ FastAPI App ============

app = FastAPI(title="USMSB Node Executor")


@app.post("/inference")
async def inference(req: InferenceRequestAPI) -> InferenceResponseAPI:
    """Execute inference"""
    global vllm_engine, model_manager, gpu_monitor, node_id, inference_history, model_stats

    start_time_exec = time.time()

    # Check maintenance mode
    if node_settings.get("maintenance_mode") == "offline":
        return InferenceResponseAPI(
            request_id=req.request_id,
            model_name=req.model_name,
            content="",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            gpu_seconds=0,
            cost_vibe=0,
            node_id=node_id,
            error="Node is offline"
        )

    try:
        # 1. Check/load model
        if not model_manager.load_model(req.model_name):
            return InferenceResponseAPI(
                request_id=req.request_id,
                model_name=req.model_name,
                content="",
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                gpu_seconds=0,
                cost_vibe=0,
                node_id=node_id,
                error=f"Failed to load model: {req.model_name}"
            )

        # 2. Execute inference
        result = await vllm_engine.generate_async(
            messages=req.messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            telemetry_context=req.llm_context,
        )

        # 3. Calculate cost
        gpu_seconds = time.time() - start_time_exec
        total_tokens = result["usage"]["total_tokens"]
        token_cost = (total_tokens / 1000) * 0.001  # Simplified billing
        gpu_cost = gpu_seconds * 0.001
        cost_vibe = token_cost + gpu_cost

        # 4. Record in history
        record = {
            "request_id": req.request_id,
            "model_name": req.model_name,
            "prompt_tokens": result["usage"].get("prompt_tokens", 0),
            "completion_tokens": result["usage"].get("completion_tokens", 0),
            "total_tokens": total_tokens,
            "gpu_seconds": gpu_seconds,
            "cost_vibe": cost_vibe,
            "latency_ms": int(gpu_seconds * 1000),
            "timestamp": time.time(),
            "status": "completed",
        }
        inference_history.append(record)
        if len(inference_history) > 1000:
            inference_history[:] = inference_history[-1000:]

        # 5. Update model stats
        if req.model_name not in model_stats:
            model_stats[req.model_name] = {
                "total_requests": 0,
                "total_tokens": 0,
                "total_gpu_seconds": 0.0,
            }
        model_stats[req.model_name]["total_requests"] += 1
        model_stats[req.model_name]["total_tokens"] += total_tokens
        model_stats[req.model_name]["total_gpu_seconds"] += gpu_seconds

        return InferenceResponseAPI(
            request_id=req.request_id,
            model_name=req.model_name,
            content=result["content"],
            usage=result["usage"],
            gpu_seconds=gpu_seconds,
            cost_vibe=cost_vibe,
            node_id=node_id,
            finish_reason="stop"
        )

    except Exception as e:
        gpu_seconds = time.time() - start_time_exec
        return InferenceResponseAPI(
            request_id=req.request_id,
            model_name=req.model_name,
            content="",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            gpu_seconds=gpu_seconds,
            cost_vibe=0,
            node_id=node_id,
            error=str(e)
        )


@app.get("/health")
async def health():
    """Health check"""
    gpu_info = gpu_monitor.get_gpu_info()
    return {
        "status": "ok",
        "node_id": node_id,
        "loaded_models": model_manager.get_loaded_models(),
        "gpu_info": gpu_info
    }


# ============ Node Management Endpoints ============

@app.get("/node/status")
async def get_node_status():
    """Get node status"""
    gpu_info = gpu_monitor.get_gpu_info()
    uptime_seconds = time.time() - start_time

    # Calculate current GPU utilization
    current_util = [g["utilization"] for g in gpu_info.get("gpus", [])]

    return {
        "node_id": node_id,
        "status": node_settings.get("maintenance_mode", "normal"),
        "wallet_address": node_settings.get("wallet_address", ""),
        "uptime_seconds": int(uptime_seconds),
        "version": VERSION,
        "gpu_info": gpu_info,
        "loaded_models": model_manager.get_loaded_models(),
        "gpu_threshold": node_settings.get("gpu_threshold", 80),
        "maintenance_reason": node_settings.get("maintenance_reason", ""),
    }


@app.get("/node/earnings")
async def get_node_earnings(days: int = Query(7, ge=1, le=90)):
    """Get this node's earnings breakdown"""
    global inference_history

    now = time.time()
    cutoff = now - (days * 86400)

    # Filter recent records
    recent = [r for r in inference_history if r.get("timestamp", 0) >= cutoff]

    total_revenue = sum(r.get("cost_vibe", 0) * 0.7 for r in recent)  # 70% to node
    total_requests = len(recent)
    total_tokens = sum(r.get("total_tokens", 0) for r in recent)
    total_gpu_seconds = sum(r.get("gpu_seconds", 0) for r in recent)

    # Group by day
    daily: Dict[str, Dict[str, Any]] = {}
    for r in recent:
        date_str = datetime.fromtimestamp(r.get("timestamp", now)).strftime("%Y-%m-%d")
        if date_str not in daily:
            daily[date_str] = {"date": date_str, "revenue_vibe": 0.0, "requests": 0, "gpu_seconds": 0.0}
        daily[date_str]["revenue_vibe"] += r.get("cost_vibe", 0) * 0.7
        daily[date_str]["requests"] += 1
        daily[date_str]["gpu_seconds"] += r.get("gpu_seconds", 0)

    trend = sorted(daily.values(), key=lambda x: x["date"])

    return {
        "total_revenue_vibe": total_revenue,
        "total_requests": total_requests,
        "total_tokens": total_tokens,
        "total_gpu_seconds": total_gpu_seconds,
        "trend": trend,
    }


@app.get("/node/models")
async def get_node_models():
    """List available and loaded models"""
    loaded = model_manager.get_loaded_models()
    available = [
        "Qwen/Qwen2.5-7B-Instruct",
        "Qwen/Qwen2.5-14B-Instruct",
        "Qwen/Qwen2.5-72B-Instruct",
        "THUDM/CogVideoX-5b",
    ]

    result = []
    for model_name in available:
        stats = model_stats.get(model_name, {"total_requests": 0, "total_tokens": 0})
        result.append({
            "model_id": model_name,
            "name": model_name.split("/")[-1] if "/" in model_name else model_name,
            "is_loaded": model_name in loaded,
            "vram_required_gb": 16,  # Simplified
            "total_requests": stats.get("total_requests", 0),
            "total_tokens": stats.get("total_tokens", 0),
            "avg_latency_ms": 0,  # Would need to calculate
        })

    return {"models": result}


@app.post("/node/models/load")
async def load_model_endpoint(req: LoadModelRequest):
    """Load a model"""
    global model_manager, model_stats

    model_id = req.model_id

    # Check if already loaded
    if model_manager.load_model(model_id):
        if model_id not in model_stats:
            model_stats[model_id] = {
                "total_requests": 0,
                "total_tokens": 0,
                "total_gpu_seconds": 0.0,
            }
        return {"status": "success", "model_id": model_id, "message": "Model loaded"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to load model: {model_id}")


@app.post("/node/models/unload")
async def unload_model_endpoint(req: LoadModelRequest):
    """Unload a model (no-op for vLLM, but returns success)"""
    # vLLM doesn't support dynamic model unloading, so this is a no-op
    # In production, you'd need to restart the vLLM engine
    return {"status": "success", "model_id": req.model_id, "message": "Unload requested (vLLM limitation: models cannot be dynamically unloaded)"}


@app.get("/node/history")
async def get_node_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Get inference history for this node"""
    global inference_history

    offset = (page - 1) * page_size
    total = len(inference_history)

    # Most recent first
    sorted_history = sorted(inference_history, key=lambda x: x.get("timestamp", 0), reverse=True)
    paged = sorted_history[offset:offset + page_size]

    return {
        "history": paged,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.put("/node/settings")
async def update_node_settings(req: NodeSettingsUpdate):
    """Update node settings"""
    global node_settings, scheduler_url, node_id

    if req.wallet_address is not None:
        node_settings["wallet_address"] = req.wallet_address
        # Notify scheduler of wallet change
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{scheduler_url}/node/wallet-update",
                    json={"node_id": node_id, "wallet_address": req.wallet_address}
                )
        except Exception as e:
            print(f"[NodeExecutor] Failed to notify scheduler of wallet update: {e}")
    if req.preload_models is not None:
        node_settings["preload_models"] = req.preload_models
    if req.gpu_threshold is not None:
        node_settings["gpu_threshold"] = req.gpu_threshold
    if req.maintenance_mode is not None:
        node_settings["maintenance_mode"] = req.maintenance_mode
    if req.maintenance_reason is not None:
        node_settings["maintenance_reason"] = req.maintenance_reason

    return {"status": "success", "settings": node_settings}


# ============ Node Executor ============

class NodeExecutor:
    """
    Node Executor main class

    Responsible for:
    - Register to Global Scheduler
    - Send periodic heartbeats
    - Receive and execute inference tasks
    """

    def __init__(
        self,
        node_id: str,
        scheduler_url: str,
        port: int,
        gpu_count: int,
        gpu_type: str,
        total_vram_gb: int,
        vllm_engine: VLLMEngine,
        model_manager: ModelManager,
        gpu_monitor: GPUMonitor
    ):
        self.node_id = node_id
        self.scheduler_url = scheduler_url
        self.port = port
        self.gpu_count = gpu_count
        self.gpu_type = gpu_type
        self.total_vram_gb = total_vram_gb
        self.vllm_engine = vllm_engine
        self.model_manager = model_manager
        self.gpu_monitor = gpu_monitor

        self.status = "idle"
        self._running = False

    async def start(self):
        """Start Node Executor"""
        global vllm_engine, model_manager, gpu_monitor, node_id, start_time, scheduler_url

        self._running = True

        # Set global variables BEFORE starting uvicorn
        import node_executor.executor as executor_module
        executor_module.node_id = self.node_id
        executor_module.vllm_engine = self.vllm_engine
        executor_module.model_manager = self.model_manager
        executor_module.gpu_monitor = self.gpu_monitor
        executor_module.start_time = time.time()
        executor_module.scheduler_url = self.scheduler_url

        # Register to Global Scheduler
        await self._register()

        # Preload models
        self.model_manager.preload_models()

        # Start heartbeat task
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Start HTTP server (using uvicorn)
        import uvicorn
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

        self._running = False

    async def _register(self):
        """Register to Global Scheduler"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.scheduler_url}/register",
                json={
                    "node_id": self.node_id,
                    "hostname": "localhost",  # Simplified, should detect actual IP
                    "port": self.port,
                    "gpu_count": self.gpu_count,
                    "gpu_type": self.gpu_type,
                    "total_vram_gb": self.total_vram_gb,
                    "available_vram_gb": self.total_vram_gb,
                    "loaded_models": self.model_manager.get_loaded_models(),
                    "capabilities": {
                        "tensor_parallel": True,
                        "max_tensor_parallel_size": self.gpu_count
                    }
                }
            )
            resp.raise_for_status()
            print(f"[NodeExecutor] Registered to scheduler: {resp.json()}")

    async def _heartbeat_loop(self):
        """Heartbeat loop"""
        global node_settings

        while self._running:
            try:
                gpu_info = self.gpu_monitor.get_gpu_info()
                available_vram = self.gpu_monitor.get_available_vram()

                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(
                        f"{self.scheduler_url}/heartbeat",
                        json={
                            "node_id": self.node_id,
                            "status": "idle",
                            "loaded_models": self.model_manager.get_loaded_models(),
                            "gpu_utilization": [g["utilization"] for g in gpu_info["gpus"]],
                            "available_vram_gb": available_vram
                        }
                    )
            except Exception as e:
                print(f"[NodeExecutor] Heartbeat failed: {e}")

            await asyncio.sleep(10)  # Heartbeat every 10 seconds
