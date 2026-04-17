# USMSB 分布式推理平台 - API 文档

## 1. OpenAI 兼容 API

### 1.1 POST /v1/chat/completions

OpenAI 兼容的对话补全接口。

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

**Response (200 OK):**
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

**Error Response (402):**
```json
{
    "detail": "Insufficient Vibe balance. Required: 0.005, Available: 0.0"
}
```

**Error Response (404):**
```json
{
    "detail": "Model 'Unknown-Model' not found"
}
```

**Error Response (503):**
```json
{
    "detail": "No available GPU node for model 'Qwen/Qwen2.5-7B-Instruct'"
}
```

---

### 1.2 GET /v1/models

列出所有可用模型。

**Response (200 OK):**
```json
{
    "object": "list",
    "data": [
        {
            "id": "Qwen/Qwen2.5-7B-Instruct",
            "object": "model",
            "created": 1713344000,
            "owned_by": "usmsb-dist-inference",
            "permission": []
        },
        {
            "id": "Qwen/Qwen2.5-14B-Instruct",
            "object": "model",
            "created": 1713344000,
            "owned_by": "usmsb-dist-inference",
            "permission": []
        }
    ]
}
```

---

### 1.3 GET /health

健康检查接口。

**Response (200 OK):**
```json
{
    "status": "ok",
    "timestamp": 1713344000,
    "nodes": {
        "total_nodes": 2,
        "idle_nodes": 1,
        "busy_nodes": 1,
        "offline_nodes": 0
    }
}
```

---

## 2. 内部管理 API

### 2.1 POST /register

节点注册接口。

**Request:**
```json
{
    "node_id": "node_001",
    "hostname": "192.168.1.100",
    "port": 8080,
    "gpu_count": 4,
    "gpu_type": "A100",
    "total_vram_gb": 160,
    "available_vram_gb": 160,
    "loaded_models": ["Qwen/Qwen2.5-7B-Instruct"],
    "capabilities": {
        "tensor_parallel": true,
        "max_tensor_parallel_size": 4
    }
}
```

**Response (200 OK):**
```json
{
    "status": "registered",
    "node_id": "node_001"
}
```

---

### 2.2 POST /heartbeat

节点心跳接口。

**Request:**
```json
{
    "node_id": "node_001",
    "status": "idle",
    "loaded_models": ["Qwen/Qwen2.5-7B-Instruct"],
    "gpu_utilization": [0.1, 0.15, 0.2, 0.1],
    "available_vram_gb": 120
}
```

**Response (200 OK):**
```json
{
    "status": "ok"
}
```

---

### 2.3 GET /v1/billing/balance/{user_id}

查询用户余额。

**Response (200 OK):**
```json
{
    "user_id": "user_123",
    "balance": 1000.0,
    "owed": 0.0,
    "available": 1000.0
}
```

---

## 3. Node Executor API

### 3.1 POST /inference

执行推理任务 (内部接口，由 Global Scheduler 调用)。

**Request:**
```json
{
    "request_id": "req_abc123",
    "model_name": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [
        {"role": "user", "content": "Hello!"}
    ],
    "temperature": 0.7,
    "max_tokens": 2048
}
```

**Response (200 OK):**
```json
{
    "request_id": "req_abc123",
    "model_name": "Qwen/Qwen2.5-7B-Instruct",
    "content": "Hello! How can I help you?",
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30
    },
    "gpu_seconds": 0.523,
    "cost_vibe": 0.000523,
    "node_id": "node_001",
    "finish_reason": "stop"
}
```

---

### 3.2 GET /health

节点健康检查。

**Response (200 OK):**
```json
{
    "status": "ok",
    "node_id": "node_001",
    "loaded_models": ["Qwen/Qwen2.5-7B-Instruct"],
    "gpu_info": {
        "gpu_count": 4,
        "gpu_type": "A100",
        "total_vram_gb": 160,
        "gpus": [
            {"id": 0, "vram_gb": 40, "utilization": 0.1, "used_vram_gb": 14},
            {"id": 1, "vram_gb": 40, "utilization": 0.1, "used_vram_gb": 14},
            {"id": 2, "vram_gb": 40, "utilization": 0.0, "used_vram_gb": 0},
            {"id": 3, "vram_gb": 40, "utilization": 0.0, "used_vram_gb": 0}
        ]
    }
}
```

---

## 4. 错误码对照表

| HTTP 状态码 | 错误码 | 说明 |
|-------------|--------|------|
| 400 | BAD_REQUEST | 请求参数错误 |
| 402 | INSUFFICIENT_BALANCE | Vibe 余额不足 |
| 404 | MODEL_NOT_FOUND | 模型不存在 |
| 500 | INTERNAL_ERROR | 内部错误 |
| 503 | NO_AVAILABLE_NODE | 没有可用的 GPU 节点 |
