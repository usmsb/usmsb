# USMSB 分布式推理平台 - 详细设计文档

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|---------|
| v0.1 | 2026-04-17 | 古军 | 初始版本 |

---

## 1. 项目结构

```
usmsb-dist-inference/
├── global_scheduler/           # 全局调度器
│   ├── __init__.py
│   ├── main.py                 # 入口
│   ├── api_server.py           # FastAPI 服务
│   ├── router.py                # 请求路由
│   ├── gpu_pool.py             # GPU 资源池
│   ├── model_registry.py       # 模型注册表
│   ├── billing.py              # Vibe 计费
│   └── protocols.py            # 通信协议定义
│
├── node_executor/             # 节点执行器
│   ├── __init__.py
│   ├── main.py                 # 入口
│   ├── vllm_engine.py          # vLLM 封装
│   ├── model_manager.py        # 模型管理
│   ├── gpu_monitor.py         # GPU 监控
│   └── executor.py             # 执行器
│
├── shared/                     # 共享模块
│   ├── __init__.py
│   ├── types.py                # 共享数据类型
│   └── vibe_client.py          # Vibe 客户端 (模拟)
│
├── tests/                      # 测试
│   ├── __init__.py
│   ├── test_gpu_pool.py
│   ├── test_billing.py
│   ├── test_router.py
│   └── test_model_manager.py
│
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 2. 数据类型定义

### 2.1 shared/types.py

```python
"""
共享数据类型定义
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import time
import uuid


class NodeStatus(Enum):
    """节点状态"""
    OFFLINE = "offline"
    IDLE = "idle"
    BUSY = "busy"


class ModelType(Enum):
    """模型类型"""
    CHAT = "chat"
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"


@dataclass
class GPUInfo:
    """单个 GPU 信息"""
    gpu_id: int
    gpu_type: str                          # "A100", "RTX 4090", etc.
    vram_gb: int                          # 总显存大小
    used_vram_gb: float = 0.0             # 已用显存
    utilization: float = 0.0               # 利用率 0.0~1.0


@dataclass
class NodeCapability:
    """节点能力"""
    node_id: str
    hostname: str
    port: int = 8080                      # Node Executor 端口
    status: NodeStatus = NodeStatus.IDLE
    gpu_count: int = 0
    gpus: List[GPUInfo] = field(default_factory=list)
    total_vram_gb: int = 0
    available_vram_gb: int = 0
    loaded_models: List[str] = field(default_factory=list)
    capabilities: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.gpus:
            self.gpus = []


@dataclass
class ModelInfo:
    """模型信息"""
    model_name: str                        # HuggingFace 模型名
    model_type: ModelType = ModelType.CHAT
    min_gpu_count: int = 1                # 最少需要几张卡
    min_vram_per_gpu_gb: int = 16       # 每张卡最少显存
    context_length: int = 4096            # 上下文长度
    is_preloaded: bool = False             # 是否预加载
    model_path: Optional[str] = None      # 本地路径 (如有)


@dataclass
class InferenceRequest:
    """推理请求"""
    request_id: str
    model_name: str
    messages: List[Dict[str, str]]        # OpenAI format
    temperature: float = 0.7
    max_tokens: int = 2048
    user_id: str = "anonymous"

    @classmethod
    def create(cls, model_name: str, messages: List[Dict[str, str]], **kwargs):
        return cls(
            request_id=f"req_{uuid.uuid4().hex[:12]}",
            model_name=model_name,
            messages=messages,
            **kwargs
        )


@dataclass
class InferenceResponse:
    """推理响应"""
    request_id: str
    model_name: str
    content: str
    usage: Dict[str, int]                # {"prompt_tokens": X, "completion_tokens": Y, "total_tokens": Z}
    gpu_seconds: float                   # GPU 卡时
    cost_vibe: float                      # Vibe 费用
    node_id: str
    finish_reason: str = "stop"
    error: Optional[str] = None


@dataclass
class NodeRegisterRequest:
    """节点注册请求"""
    node_id: str
    hostname: str
    port: int = 8080
    gpu_count: int
    gpu_type: str
    total_vram_gb: int
    available_vram_gb: int
    loaded_models: List[str] = field(default_factory=list)
    capabilities: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HeartbeatRequest:
    """心跳请求"""
    node_id: str
    status: str                           # "idle" | "busy" | "offline"
    loaded_models: List[str] = field(default_factory=list)
    gpu_utilization: List[float] = field(default_factory=list)
    available_vram_gb: int = 0
```

---

## 3. Global Scheduler 详细设计

### 3.1 api_server.py

```python
"""
Global Scheduler API Server
OpenAI 兼容 API
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

# 全局组件
gpu_pool = GPUPool()
billing_engine = BillingEngine()
model_registry = ModelRegistry()
router = Router(gpu_pool, model_registry)


# ============ API Endpoints ============

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(req: ChatCompletionRequest):
    """
    OpenAI 兼容的 chat completions 接口
    """
    # 1. 检查余额
    user_id = req.user or "anonymous"
    balance = billing_engine.get_balance(user_id)
    estimated = billing_engine.estimate_cost(req.model, req.max_tokens)
    
    if balance < estimated and balance <= 0:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient Vibe balance. Required: {estimated}, Available: {balance}"
        )

    # 2. 检查模型是否存在
    model_info = model_registry.get_model(req.model)
    if not model_info:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{req.model}' not found"
        )

    # 3. 创建推理请求
    inference_req = InferenceRequest.create(
        model_name=req.model,
        messages=[m.dict() for m in req.messages],
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        user_id=user_id
    )

    # 4. 调度执行
    try:
        response = await router.execute(inference_req)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # 5. 计费
    billing_engine.charge(user_id, response.cost_vibe)

    # 6. 返回 OpenAI 格式响应
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
    """列出所有可用模型"""
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
    """健康检查"""
    return {
        "status": "ok",
        "timestamp": int(time.time()),
        "nodes": gpu_pool.get_summary()
    }


@app.post("/register")
async def register_node(req: NodeRegisterRequest):
    """节点注册"""
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
    """节点心跳"""
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
    """查询用户余额"""
    balance = billing_engine.get_balance(user_id)
    owed = billing_engine.get_owed(user_id)
    return {
        "user_id": user_id,
        "balance": balance,
        "owed": owed,
        "available": balance - owed
    }
```

### 3.2 gpu_pool.py

```python
"""
GPU 资源池管理
"""

import asyncio
from typing import Dict, List, Optional, Tuple
import time
import httpx

from shared.types import NodeCapability, NodeStatus, ModelInfo, GPUInfo


class GPUPool:
    """
    管理所有 GPU 节点
    """

    def __init__(self):
        self.nodes: Dict[str, NodeCapability] = {}
        self.lock = asyncio.Lock()
        self.heartbeat_timeout = 30  # 秒

    async def register_node(self, node: NodeCapability):
        """注册新节点"""
        async with self.lock:
            self.nodes[node.node_id] = node
            print(f"[GPUPool] Node registered: {node.node_id} @ {node.hostname}:{node.port}")
            print(f"         GPUs: {node.gpu_count}x {node.gpus[0].gpu_type if node.gpus else 'Unknown'}")
            print(f"         VRAM: {node.total_vram_gb}GB total, {node.available_vram_gb}GB available")

    async def heartbeat(
        self,
        node_id: str,
        status: str,
        loaded_models: List[str],
        gpu_utilization: List[float],
        available_vram_gb: int
    ):
        """更新节点心跳"""
        async with self.lock:
            if node_id not in self.nodes:
                return

            node = self.nodes[node_id]
            node.status = NodeStatus[status.upper()]
            node.loaded_models = loaded_models
            node.available_vram_gb = available_vram_gb
            node.last_heartbeat = time.time()

            # 更新 GPU 利用率
            for i, util in enumerate(gpu_utilization):
                if i < len(node.gpus):
                    node.gpus[i].utilization = util

    async def select_node(self, model_name: str, model_registry) -> Optional[Tuple["NodeExecutor", int]]:
        """
        选择最适合执行某个模型的节点
        
        Returns:
            (NodeExecutor, estimated_gpu_seconds) or None
        """
        async with self.lock:
            # 清理超时节点
            self._cleanup_timeout_nodes()

            # 获取模型需求
            model_info = model_registry.get_model(model_name)
            if not model_info:
                # 未知模型，找一个有余量的节点
                candidates = [
                    n for n in self.nodes.values()
                    if n.status == NodeStatus.IDLE and n.available_vram_gb > 0
                ]
            else:
                # 筛选满足条件的节点
                required_vram = model_info.min_vram_per_gpu_gb * model_info.min_gpu_count
                candidates = [
                    n for n in self.nodes.values()
                    if n.status == NodeStatus.IDLE
                    and n.gpu_count >= model_info.min_gpu_count
                    and n.available_vram_gb >= required_vram
                ]

            if not candidates:
                return None

            # 排序策略:
            # 1. 已加载目标模型的优先 (避免冷启动)
            # 2. 可用显存多的优先
            # 3. GPU 利用率低的优先
            def score(node: NodeCapability) -> Tuple[int, int, float]:
                model_loaded = 1 if model_name in node.loaded_models else 0
                return (
                    model_loaded,
                    node.available_vram_gb,
                    -sum(g.utilization for g in node.gpus)  # 利用率越低越好
                )

            candidates.sort(key=score, reverse=True)
            selected = candidates[0]

            # 估算 GPU 使用时间 (简化版)
            estimated_seconds = 1.0  # TODO: 根据模型和 token 数估算

            return NodeExecutor(selected, self), estimated_seconds

    def _cleanup_timeout_nodes(self):
        """清理心跳超时的节点"""
        now = time.time()
        for node_id, node in list(self.nodes.items()):
            if now - node.last_heartbeat > self.heartbeat_timeout:
                print(f"[GPUPool] Node timed out: {node_id}")
                node.status = NodeStatus.OFFLINE

    def get_all_nodes(self) -> List[NodeCapability]:
        return list(self.nodes.values())

    def get_summary(self) -> Dict:
        return {
            "total_nodes": len(self.nodes),
            "idle_nodes": len([n for n in self.nodes.values() if n.status == NodeStatus.IDLE]),
            "busy_nodes": len([n for n in self.nodes.values() if n.status == NodeStatus.BUSY]),
            "offline_nodes": len([n for n in self.nodes.values() if n.status == NodeStatus.OFFLINE]),
        }


class NodeExecutor:
    """
    代表一个远端节点执行器
    """

    def __init__(self, capability: NodeCapability, pool: GPUPool):
        self.capability = capability
        self.pool = pool
        self.base_url = f"http://{capability.hostname}:{capability.port}"

    async def execute(self, request) -> "InferenceResponse":
        """通过 HTTP 调用远端节点执行推理"""
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                resp = await client.post(
                    f"{self.base_url}/inference",
                    json={
                        "request_id": request.request_id,
                        "model_name": request.model_name,
                        "messages": request.messages,
                        "temperature": request.temperature,
                        "max_tokens": request.max_tokens
                    }
                )
                resp.raise_for_status()
                data = resp.json()
                
                # 转换字典到 InferenceResponse
                from shared.types import InferenceResponse
                return InferenceResponse(**data)
                
            except httpx.HTTPError as e:
                raise RuntimeError(f"Node {self.capability.node_id} execution failed: {e}")

    async def set_busy(self):
        """标记节点为忙碌"""
        async with self.pool.lock:
            self.capability.status = NodeStatus.BUSY

    async def set_idle(self):
        """标记节点为空闲"""
        async with self.pool.lock:
            self.capability.status = NodeStatus.IDLE
```

### 3.3 router.py

```python
"""
请求路由器
"""

import asyncio
from typing import Optional

from shared.types import InferenceRequest, InferenceResponse
from .gpu_pool import GPUPool
from .model_registry import ModelRegistry


class Router:
    """
    请求路由: 选择节点 -> 发送请求 -> 返回结果
    """

    def __init__(self, gpu_pool: GPUPool, model_registry: ModelRegistry):
        self.gpu_pool = gpu_pool
        self.model_registry = model_registry
        self.max_retries = 3

    async def execute(self, request: InferenceRequest) -> InferenceResponse:
        """
        执行推理请求，包含重试逻辑
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # 选择节点
                result = await self.gpu_pool.select_node(
                    request.model_name,
                    self.model_registry
                )

                if not result:
                    raise RuntimeError(
                        f"No available GPU node for model '{request.model_name}'"
                    )

                node_executor, estimated_seconds = result

                # 标记节点忙碌
                await node_executor.set_busy()

                try:
                    # 执行推理
                    response = await node_executor.execute(request)
                    return response

                finally:
                    # 标记节点空闲
                    await node_executor.set_idle()

            except Exception as e:
                last_error = e
                print(f"[Router] Attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(0.5)  # 短暂等待后重试

        # 所有重试都失败
        raise RuntimeError(
            f"All {self.max_retries} attempts failed. Last error: {last_error}"
        )
```

### 3.4 billing.py

```python
"""
Vibe 计费引擎
"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class UserBalance:
    """用户余额信息"""
    user_id: str
    vibe_balance: float = 1000.0          # Vibe 余额 (测试用默认值)
    owed_vibe: float = 0.0                # 欠费金额


class BillingEngine:
    """
    Vibe 计费引擎

    计费规则:
    - GPU 卡时: 0.001 Vibe/秒/GPU
    - Token: 0.001 Vibe/1K tokens
    - 平台抽成: 30%
    """

    GPU_COST_PER_SECOND = 0.001            # Vibe/秒/GPU
    TOKEN_COST_PER_1K = 0.001             # Vibe/1K tokens
    PLATFORM_FEE_RATIO = 0.30             # 平台抽成 30%

    def __init__(self):
        self.balances: Dict[str, UserBalance] = {}

    def get_balance(self, user_id: str) -> float:
        """获取用户余额 (扣除欠费后)"""
        if user_id not in self.balances:
            self.balances[user_id] = UserBalance(user_id=user_id)
        balance = self.balances[user_id]
        return balance.vibe_balance - balance.owed_vibe

    def get_owed(self, user_id: str) -> float:
        """获取用户欠费金额"""
        if user_id not in self.balances:
            return 0.0
        return self.balances[user_id].owed_vibe

    def estimate_cost(self, model_name: str, max_tokens: int) -> float:
        """
        预估费用

        简化版: 假设输入 500 tokens
        """
        estimated_tokens = 500 + max_tokens
        token_cost = (estimated_tokens / 1000) * self.TOKEN_COST_PER_1K

        # GPU 卡时预估值 (简化: 假设 1 秒)
        gpu_cost = 1.0 * self.GPU_COST_PER_SECOND

        return token_cost + gpu_cost

    def calculate_cost(
        self,
        gpu_seconds: float,
        prompt_tokens: int,
        completion_tokens: int,
        gpu_count: int = 1
    ) -> float:
        """
        计算实际费用

        Args:
            gpu_seconds: GPU 使用秒数
            prompt_tokens: 输入 token 数
            completion_tokens: 输出 token 数
            gpu_count: 使用的 GPU 卡数
        """
        gpu_cost = gpu_seconds * gpu_count * self.GPU_COST_PER_SECOND
        total_tokens = prompt_tokens + completion_tokens
        token_cost = (total_tokens / 1000) * self.TOKEN_COST_PER_1K

        total = gpu_cost + token_cost
        print(f"[Billing] Cost calculation: GPU({gpu_seconds}s x {gpu_count})={gpu_cost:.6f}, "
              f"Token({total_tokens})={token_cost:.6f}, Total={total:.6f} Vibe")

        return total

    def charge(self, user_id: str, cost_vibe: float) -> Dict[str, float]:
        """
        扣费

        Returns:
            {"charged": xxx, "remaining": yyy, "new_owed": zzz}
        """
        if user_id not in self.balances:
            self.balances[user_id] = UserBalance(user_id=user_id)

        balance = self.balances[user_id]
        total_cost = cost_vibe + balance.owed_vibe

        if balance.vibe_balance >= total_cost:
            # 足够支付
            balance.vibe_balance -= total_cost
            balance.owed_vibe = 0.0
        else:
            # 欠费执行
            balance.owed_vibe = total_cost - balance.vibe_balance
            balance.vibe_balance = 0.0

        print(f"[Billing] Charged {cost_vibe:.6f} Vibe from {user_id}, "
              f"remaining: {balance.vibe_balance:.6f}, owed: {balance.owed_vibe:.6f}")

        return {
            "charged": cost_vibe,
            "remaining": balance.vibe_balance,
            "new_owed": balance.owed_vibe
        }

    def calculate_node_reward(self, gpu_seconds: float, gpu_count: int = 1) -> float:
        """
        计算 GPU 持有者奖励 (平台抽 30% 后)
        """
        gross = gpu_seconds * gpu_count * self.GPU_COST_PER_SECOND
        net = gross * (1 - self.PLATFORM_FEE_RATIO)
        return net

    def deposit(self, user_id: str, amount: float):
        """充值"""
        if user_id not in self.balances:
            self.balances[user_id] = UserBalance(user_id=user_id)
        self.balances[user_id].vibe_balance += amount
        print(f"[Billing] Deposited {amount} Vibe to {user_id}, "
              f"new balance: {self.balances[user_id].vibe_balance:.6f}")
```

### 3.5 model_registry.py

```python
"""
模型注册表
"""

from typing import Dict, List, Optional

from shared.types import ModelInfo, ModelType


class ModelRegistry:
    """
    管理可用模型列表
    """

    # Phase 1 预置模型
    DEFAULT_MODELS: Dict[str, ModelInfo] = {
        "Qwen/Qwen2.5-7B-Instruct": ModelInfo(
            model_name="Qwen/Qwen2.5-7B-Instruct",
            model_type=ModelType.CHAT,
            min_gpu_count=1,
            min_vram_per_gpu_gb=16,
            context_length=8192,
            is_preloaded=True,
        ),
        "Qwen/Qwen2.5-14B-Instruct": ModelInfo(
            model_name="Qwen/Qwen2.5-14B-Instruct",
            model_type=ModelType.CHAT,
            min_gpu_count=1,
            min_vram_per_gpu_gb=28,
            context_length=8192,
            is_preloaded=False,
        ),
        "Qwen/Qwen2.5-72B-Instruct": ModelInfo(
            model_name="Qwen/Qwen2.5-72B-Instruct",
            model_type=ModelType.CHAT,
            min_gpu_count=4,
            min_vram_per_gpu_gb=40,
            context_length=32768,
            is_preloaded=False,
        ),
        # 视频生成模型 (后续)
        "THUDM/CogVideoX-5b": ModelInfo(
            model_name="THUDM/CogVideoX-5b",
            model_type=ModelType.VIDEO,
            min_gpu_count=2,
            min_vram_per_gpu_gb=24,
            context_length=2048,
            is_preloaded=False,
        ),
    }

    def __init__(self):
        self.models: Dict[str, ModelInfo] = dict(self.DEFAULT_MODELS)

    def get(self, model_name: str) -> Optional[ModelInfo]:
        """获取模型信息"""
        return self.models.get(model_name)

    def list_models(self) -> List[ModelInfo]:
        """列出所有模型"""
        return list(self.models.values())

    def register_model(self, model_info: ModelInfo):
        """注册新模型"""
        self.models[model_info.model_name] = model_info

    def unregister_model(self, model_name: str):
        """取消注册模型"""
        if model_name in self.models:
            del self.models[model_name]
```

---

## 4. Node Executor 详细设计

### 4.1 main.py

```python
"""
Node Executor 入口
"""

import asyncio
import argparse
import os
from .executor import NodeExecutor
from .gpu_monitor import GPUMonitor
from .model_manager import ModelManager
from .vllm_engine import VLLMEngine


async def main():
    parser = argparse.ArgumentParser(description="USMSB Node Executor")
    parser.add_argument("--node-id", required=True, help="Node ID")
    parser.add_argument("--scheduler-url", default="http://localhost:8000", help="Global Scheduler URL")
    parser.add_argument("--port", type=int, default=8080, help="Executor HTTP port")
    parser.add_argument("--gpu-count", type=int, help="GPU count (auto-detect if not set)")
    args = parser.parse_args()

    # 检测 GPU
    gpu_monitor = GPUMonitor()
    gpu_info = gpu_monitor.get_gpu_info()

    node_id = args.node_id
    gpu_count = args.gpu_count or gpu_info["gpu_count"]
    gpu_type = gpu_info["gpu_type"]
    total_vram = gpu_info["total_vram_gb"]

    print(f"[NodeExecutor] Starting node: {node_id}")
    print(f"               GPUs: {gpu_count}x {gpu_type}")
    print(f"               Total VRAM: {total_vram}GB")

    # 初始化组件
    vllm_engine = VLLMEngine()
    model_manager = ModelManager(vllm_engine, total_vram, gpu_count)
    executor = NodeExecutor(
        node_id=node_id,
        scheduler_url=args.scheduler_url,
        port=args.port,
        gpu_count=gpu_count,
        gpu_type=gpu_type,
        total_vram_gb=total_vram,
        vllm_engine=vllm_engine,
        model_manager=model_manager,
        gpu_monitor=gpu_monitor
    )

    # 启动
    await executor.start()


if __name__ == "__main__":
    asyncio.run(main())
```

### 4.2 gpu_monitor.py

```python
"""
GPU 监控
"""

import subprocess
from typing import Dict, List, Optional


class GPUMonitor:
    """
    GPU 信息监控
    """

    def __init__(self):
        self.has_nvidia_smi = self._check_nvidia_smi()

    def _check_nvidia_smi(self) -> bool:
        """检查 nvidia-smi 是否可用"""
        try:
            subprocess.run(
                ["nvidia-smi", "--version"],
                capture_output=True,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_gpu_info(self) -> Dict:
        """
        获取 GPU 信息

        Returns:
            {
                "gpu_count": int,
                "gpu_type": str,
                "total_vram_gb": int,
                "gpus": [{"id": 0, "vram_gb": 80, "utilization": 0.1}, ...]
            }
        """
        if not self.has_nvidia_smi:
            # 没有 GPU，返回模拟数据 (用于开发测试)
            return {
                "gpu_count": 1,
                "gpu_type": "RTX 4090",
                "total_vram_gb": 24,
                "gpus": [{"id": 0, "vram_gb": 24, "utilization": 0.0}]
            }

        # 解析 nvidia-smi
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,utilization.gpu,memory.used",
                "--format=csv,noheader,nounits"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        gpus = []
        total_vram = 0

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                continue

            idx, name, mem_total, util, mem_used = parts[:5]
            vram = int(mem_total)
            total_vram += vram

            gpus.append({
                "id": int(idx),
                "name": name,
                "vram_gb": vram,
                "utilization": float(util) / 100.0,
                "used_vram_gb": int(mem_used)
            })

        gpu_type = gpus[0]["name"] if gpus else "Unknown"

        return {
            "gpu_count": len(gpus),
            "gpu_type": gpu_type,
            "total_vram_gb": total_vram,
            "gpus": gpus
        }

    def get_available_vram(self) -> int:
        """获取可用 VRAM (GB)"""
        info = self.get_gpu_info()
        total = info["total_vram_gb"]
        used = sum(g["used_vram_gb"] for g in info["gpus"])
        return total - used
```

### 4.3 model_manager.py

```python
"""
模型管理器
"""

import os
from typing import List, Dict, Optional
import time

from shared.types import ModelInfo, ModelType


class ModelManager:
    """
    管理模型的加载/卸载
    """

    # 常用模型 (预加载)
    PRELOADED_MODELS = [
        "Qwen/Qwen2.5-7B-Instruct",
    ]

    def __init__(
        self,
        vllm_engine,  # VLLMEngine
        total_vram_gb: int,
        gpu_count: int
    ):
        self.vllm_engine = vllm_engine
        self.total_vram_gb = total_vram_gb
        self.gpu_count = gpu_count
        self.loaded_models: Dict[str, ModelInfo] = {}
        self.preloaded_models: List[str] = []

    def preload_models(self):
        """预加载常用模型"""
        for model_name in self.PRELOADED_MODELS:
            if model_name in self.vllm_engine.get_supported_models():
                try:
                    self.vllm_engine.load_model(model_name)
                    self.preloaded_models.append(model_name)
                    print(f"[ModelManager] Preloaded: {model_name}")
                except Exception as e:
                    print(f"[ModelManager] Failed to preload {model_name}: {e}")

    def load_model(self, model_name: str) -> bool:
        """按需加载模型"""
        if model_name in self.loaded_models:
            return True

        try:
            self.vllm_engine.load_model(model_name)
            self.loaded_models[model_name] = ModelInfo(
                model_name=model_name,
                model_type=ModelType.CHAT  # 简化
            )
            return True
        except Exception as e:
            print(f"[ModelManager] Failed to load {model_name}: {e}")
            return False

    def unload_model(self, model_name: str):
        """卸载模型"""
        if model_name in self.loaded_models:
            # vLLM 不支持动态卸载，需要重启进程
            # 简化版: 暂不支持
            pass

    def get_loaded_models(self) -> List[str]:
        """获取已加载模型列表"""
        return list(self.loaded_models.keys()) + self.preloaded_models


# 显存估算表 (GB)
VRAM_ESTIMATES = {
    "Qwen/Qwen2.5-7B-Instruct": 14,
    "Qwen/Qwen2.5-14B-Instruct": 28,
    "Qwen/Qwen2.5-72B-Instruct": 145,
    "THUDM/CogVideoX-5b": 48,
    "tencent/HunyuanVideo": 80,
}


def estimate_vram(model_name: str) -> int:
    """估算模型显存需求"""
    return VRAM_ESTIMATES.get(model_name, 20)
```

### 4.4 vllm_engine.py

```python
"""
vLLM 引擎封装
"""

import os
from typing import List, Dict, Optional, Any
import asyncio
from threading import Thread
import time

try:
    from vllm import LLM, SamplingParams
    VLLM_AVAILABLE = True
except ImportError:
    VLLM_AVAILABLE = False
    LLM = None
    SamplingParams = None


class VLLMEngine:
    """
    vLLM 引擎封装

    提供:
    - 模型加载/卸载
    - 同步/异步推理
    """

    def __init__(
        self,
        tensor_parallel_size: int = 1,
        gpu_memory_utilization: float = 0.9
    ):
        self.tensor_parallel_size = tensor_parallel_size
        self.gpu_memory_utilization = gpu_memory_utilization
        self.llm = None
        self.loaded_model_name: Optional[str] = None
        self._loading = False

    def is_available(self) -> bool:
        """检查 vLLM 是否可用"""
        return VLLM_AVAILABLE

    def get_supported_models(self) -> List[str]:
        """获取支持的模型列表"""
        # 简化: 返回预定义的模型
        return list(VRAM_ESTIMATES.keys())

    def load_model(self, model_name: str):
        """
        加载模型
        """
        if self._loading:
            raise RuntimeError("Model loading in progress")

        if self.loaded_model_name == model_name:
            print(f"[VLLM] Model already loaded: {model_name}")
            return

        if not VLLM_AVAILABLE:
            raise RuntimeError("vLLM not available. Install with: pip install vllm")

        print(f"[VLLM] Loading model: {model_name}")

        self._loading = True
        try:
            # 解析模型路径
            model_path = self._resolve_model_path(model_name)

            self.llm = LLM(
                model=model_path,
                tensor_parallel_size=self.tensor_parallel_size,
                gpu_memory_utilization=self.gpu_memory_utilization,
                trust_remote_code=True,
                enforce_eager=False  # 允许 CUDA graph
            )
            self.loaded_model_name = model_name
            print(f"[VLLM] Model loaded: {model_name}")

        finally:
            self._loading = False

    def _resolve_model_path(self, model_name: str) -> str:
        """解析模型路径"""
        # HuggingFace 模型
        return model_name

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        同步生成

        Returns:
            {
                "content": str,
                "usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
            }
        """
        if not self.llm:
            raise RuntimeError("Model not loaded")

        # 转换 messages 为 prompt
        prompt = self._messages_to_prompt(messages)

        sampling_params = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
            stop=None
        )

        outputs = self.llm.generate([prompt], sampling_params)
        output = outputs[0]

        return {
            "content": output.outputs[0].text,
            "usage": {
                "prompt_tokens": len(output.prompt_token_ids),
                "completion_tokens": len(output.outputs[0].token_ids),
                "total_tokens": len(output.prompt_token_ids) + len(output.outputs[0].token_ids)
            }
        }

    async def generate_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        异步生成 (在线程池中执行同步 vLLM 调用)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.generate(messages, temperature, max_tokens)
        )

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        OpenAI messages 格式转 prompt

        简化实现，实际应该用 tokenizer
        """
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt += f"System: {content}\n"
            elif role == "user":
                prompt += f"User: {content}\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n"
        prompt += "Assistant: "
        return prompt


# 显存估算
VRAM_ESTIMATES = {
    "Qwen/Qwen2.5-7B-Instruct": 14,
    "Qwen/Qwen2.5-14B-Instruct": 28,
    "Qwen/Qwen2.5-72B-Instruct": 145,
    "THUDM/CogVideoX-5b": 48,
    "tencent/HunyuanVideo": 80,
}
```

### 4.5 executor.py

```python
"""
Node Executor - 执行器
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

# 全局组件 (通过 lifespan 注入，简化起见用全局变量)
vllm_engine: VLLMEngine = None
model_manager: ModelManager = None
gpu_monitor: GPUMonitor = None
node_id: str = None


@app.post("/inference")
async def inference(req: InferenceRequestAPI) -> InferenceResponseAPI:
    """执行推理"""
    global vllm_engine, model_manager, gpu_monitor, node_id

    start_time = time.time()

    try:
        # 1. 检查/加载模型
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

        # 2. 执行推理
        result = await vllm_engine.generate_async(
            messages=req.messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens
        )

        # 3. 计算费用
        gpu_seconds = time.time() - start_time
        total_tokens = result["usage"]["total_tokens"]
        token_cost = (total_tokens / 1000) * 0.001  # 简化计费
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
    """健康检查"""
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
    Node Executor 主类
    负责:
    - 向 Global Scheduler 注册
    - 定期发送心跳
    - 接收并执行推理任务
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
        """启动 Node Executor"""
        self._running = True

        # 注册到 Global Scheduler
        await self._register()

        # 预加载模型
        self.model_manager.preload_models()

        # 启动心跳任务
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # 启动 HTTP 服务器 (使用 uvicorn)
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
        """注册到 Global Scheduler"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.scheduler_url}/register",
                json={
                    "node_id": self.node_id,
                    "hostname": "localhost",  # 简化，实际应该检测
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
        """心跳循环"""
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

            await asyncio.sleep(10)  # 每 10 秒心跳一次
```

---

## 5. API 详细规格

### 5.1 OpenAI 兼容接口

#### POST /v1/chat/completions

**Request:**
```json
{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    "temperature": 0.7,
    "max_tokens": 2048,
    "stream": false,
    "user": "user_123"
}
```

**Response:**
```json
{
    "id": "req_abc123",
    "object": "chat.completion",
    "created": 1713344000,
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Hello! How can I help you today?"
            },
            "finish_reason": "stop"
        }
    ],
    "usage": {
        "prompt_tokens": 30,
        "completion_tokens": 20,
        "total_tokens": 50
    }
}
```

#### GET /v1/models

**Response:**
```json
{
    "object": "list",
    "data": [
        {
            "id": "Qwen/Qwen2.5-7B-Instruct",
            "object": "model",
            "created": 1713344000,
            "owned_by": "usmsb-dist-inference"
        }
    ]
}
```

### 5.2 内部接口

#### POST /register

节点注册接口。

#### POST /heartbeat

节点心跳接口。

#### GET /health

健康检查接口。

---

## 6. 错误码

| HTTP 状态码 | 错误码 | 说明 |
|-------------|--------|------|
| 400 | BAD_REQUEST | 请求参数错误 |
| 402 | INSUFFICIENT_BALANCE | Vibe 余额不足 |
| 404 | MODEL_NOT_FOUND | 模型不存在 |
| 500 | INTERNAL_ERROR | 内部错误 |
| 503 | NO_AVAILABLE_NODE | 没有可用的 GPU 节点 |

---

## 7. 测试方案

### 7.1 单元测试

| 测试文件 | 测试内容 |
|---------|---------|
| test_gpu_pool.py | GPU 池的注册、心跳、选择逻辑 |
| test_billing.py | 计费的计算、扣费、欠费逻辑 |
| test_router.py | 路由的重试、故障转移逻辑 |
| test_model_manager.py | 模型的加载、卸载、预加载逻辑 |

### 7.2 集成测试

```
1. 启动 Global Scheduler
2. 启动 Node Executor (模拟)
3. 发送 /v1/chat/completions 请求
4. 验证返回结果
5. 验证计费记录
```

### 7.3 端到端测试

```
1. 部署完整环境 (Scheduler + Node Executor)
2. 调用 OpenAI 兼容 API
3. 验证完整流程
4. 验证 GPU 使用情况
```
