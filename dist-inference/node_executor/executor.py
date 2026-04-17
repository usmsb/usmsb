"""
Node Executor - Executor
"""

import asyncio
import httpx
import time
import uuid
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

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


# ============ FastAPI App ============

app = FastAPI(title="USMSB Node Executor")

# Global components (injected via lifespan, simplified with global vars)
vllm_engine: VLLMEngine = None
model_manager: ModelManager = None
gpu_monitor: GPUMonitor = None
node_id: str = "unknown"  # Default, will be set by NodeExecutor


@app.post("/inference")
async def inference(req: InferenceRequestAPI) -> InferenceResponseAPI:
    """Execute inference"""
    global vllm_engine, model_manager, gpu_monitor, node_id

    start_time = time.time()

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
            max_tokens=req.max_tokens
        )

        # 3. Calculate cost
        gpu_seconds = time.time() - start_time
        total_tokens = result["usage"]["total_tokens"]
        token_cost = (total_tokens / 1000) * 0.001  # Simplified billing
        gpu_cost = gpu_seconds * 0.001
        cost_vibe = token_cost + gpu_cost

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
        return InferenceResponseAPI(
            request_id=req.request_id,
            model_name=req.model_name,
            content="",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            gpu_seconds=time.time() - start_time,
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
        self._running = True

        # Set global variables BEFORE starting uvicorn
        import node_executor.executor as executor_module
        executor_module.node_id = self.node_id
        executor_module.vllm_engine = self.vllm_engine
        executor_module.model_manager = self.model_manager
        executor_module.gpu_monitor = self.gpu_monitor

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
