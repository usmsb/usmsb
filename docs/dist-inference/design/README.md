# USMSB 分布式推理平台 - 总体设计文档

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|---------|
| v0.1 | 2026-04-17 | 古军 | 初始版本 |

---

## 1. 架构概述

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USMSB 网络                                      │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     USMSB SDK Agent 网络 (现有)                       │   │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐                            │   │
│  │  │ Agent A │◄─►│ Agent B │◄─►│ Agent C │  (A2A/MCP 通信)           │   │
│  │  └─────────┘   └─────────┘   └─────────┘                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              分布式推理平台超级智能体 (新增)                            │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐     │   │
│  │  │              Global Scheduler Agent (全局调度)               │     │   │
│  │  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  │     │   │
│  │  │  │  API Server   │  │    Router     │  │  GPU Pool     │  │     │   │
│  │  │  │  (OpenAI 兼容) │  │  (请求路由)    │  │  (资源管理)   │  │     │   │
│  │  │  └───────────────┘  └───────────────┘  └───────────────┘  │     │   │
│  │  │  ┌───────────────┐  ┌───────────────┐                     │     │   │
│  │  │  │ Model Registry │  │ Billing Engine│                     │     │   │
│  │  │  │  (模型注册表)   │  │  (Vibe 计费)   │                     │     │   │
│  │  │  └───────────────┘  └───────────────┘                     │     │   │
│  │  └─────────────────────────────────────────────────────────────┘     │   │
│  │                              │                                      │   │
│  │                    HTTP / A2A / MCP                                 │   │
│  │                              │                                      │   │
│  └──────────────────────────────┼──────────────────────────────────────┘   │
│                                 │                                          │
└─────────────────────────────────┼──────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GPU 节点 (Node Executor)                           │
│                                                                             │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                   │
│  │      Node Executor A     │  │      Node Executor B     │                   │
│  │  ┌───────────────────┐  │  │  ┌───────────────────┐  │                   │
│  │  │   vLLM Engine     │  │  │  │   vLLM Engine     │  │                   │
│  │  │  (Qwen2.5-7B)     │  │  │  │  (CogVideoX)     │  │                   │
│  │  └───────────────────┘  │  │  └───────────────────┘  │                   │
│  │  ┌───────────────────┐  │  │  ┌───────────────────┐  │                   │
│  │  │   Model Manager   │  │  │  │   Model Manager   │  │                   │
│  │  └───────────────────┘  │  │  └───────────────────┘  │                   │
│  │  ┌───────────────────┐  │  │  ┌───────────────────┐  │                   │
│  │  │   GPU Monitor     │  │  │  │   GPU Monitor     │  │                   │
│  │  └───────────────────┘  │  │  └───────────────────┘  │                   │
│  └─────────────────────────┘  └─────────────────────────┘                   │
│                                                                             │
│  ┌─────────────────────────┐                                               │
│  │      Node Executor C     │   (更多节点...)                               │
│  │  ┌───────────────────┐  │                                               │
│  │  │   vLLM Engine     │  │                                               │
│  │  │  (HunyuanVideo)   │  │                                               │
│  │  └───────────────────┘  │                                               │
│  └─────────────────────────┘                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 组件职责

| 组件 | 职责 | 部署位置 |
|------|------|---------|
| **Global Scheduler** | 请求接收、路由调度、GPU 资源管理、模型注册、计费结算 | 中心化部署 (可多副本高可用) |
| **Node Executor** | 模型加载/卸载、LLM 推理执行、GPU 监控、状态上报 | 每个 GPU 节点部署一个 |
| **API Server** | OpenAI 兼容 API、胃息队列 (可选) | 集成在 Global Scheduler |
| **GPU Pool** | 管理所有 GPU 节点能力、心跳检测 | 集成在 Global Scheduler |
| **Billing Engine** | Vibe 代币计费、欠费管理、GPU 持有者奖励 | 集成在 Global Scheduler |

---

## 2. 组件设计

### 2.1 Global Scheduler

```
Global Scheduler
├── API Server (FastAPI)
│   ├── POST /v1/chat/completions     # OpenAI 兼容推理接口
│   ├── GET  /v1/models                # 列出可用模型
│   ├── GET  /health                   # 健康检查
│   ├── POST /v1/billing/balance      # 查询余额
│   └── POST /v1/billing/charge        # 充值 (预留)
│
├── Router (请求路由)
│   ├── select_node(model_name)       # 选择最合适的节点
│   ├── estimate_cost()                # 预估成本
│   └── retry_on_failure()             # 故障重试
│
├── GPU Pool (GPU 资源池)
│   ├── register_node()               # 注册节点
│   ├── heartbeat()                    # 心跳检测
│   ├── update_status()                # 更新节点状态
│   └── select_best_node()             # 选择最优节点
│
├── Model Registry (模型注册表)
│   ├── register_model()              # 注册模型能力
│   ├── get_model_requirement()       # 获取模型需求
│   └── list_available_models()       # 列出可用模型
│
└── Billing Engine (Vibe 计费)
    ├── get_balance()                  # 查询余额
    ├── estimate_cost()                # 预估费用
    ├── charge()                       # 扣费
    ├── calculate_node_reward()        # 计算节点奖励
    └── handle_owed()                  # 欠费处理
```

### 2.2 Node Executor

```
Node Executor
├── Executor (执行器)
│   ├── register()                     # 向 Global Scheduler 注册
│   ├── heartbeat()                    # 定期心跳
│   ├── receive_task()                 # 接收调度任务
│   └── report_status()                # 上报状态
│
├── VLLM Engine (vLLM 封装)
│   ├── load_model()                   # 加载模型
│   ├── unload_model()                 # 卸载模型
│   └── generate()                     # 执行推理
│
├── Model Manager (模型管理)
│   ├── preload_models()               # 预加载常用模型
│   ├── load_on_demand()               # 按需加载
│   ├── get_loaded_models()           # 获取已加载模型
│   └── estimate_vram()               # 估算显存需求
│
└── GPU Monitor (GPU 监控)
    ├── get_gpu_info()                 # 获取 GPU 信息
    ├── monitor_utilization()           # 监控利用率
    └── get_available_vram()           # 获取可用显存
```

---

## 3. 通信协议

### 3.1 节点注册协议

```json
// Node Executor -> Global Scheduler (注册)
POST /register
{
    "node_id": "node_001",
    "hostname": "192.168.1.100",
    "gpu_count": 4,
    "gpu_type": "A100",
    "total_vram_gb": 160,
    "available_vram_gb": 160,
    "loaded_models": [],
    "capabilities": {
        "tensor_parallel": true,
        "max_tensor_parallel_size": 4
    }
}

// Global Scheduler -> Node Executor (响应)
{
    "status": "registered",
    "node_id": "node_001",
    "scheduler_url": "http://scheduler:8000"
}
```

### 3.2 推理请求协议

```json
// Global Scheduler -> Node Executor
POST /inference
{
    "request_id": "req_abc123",
    "model_name": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [
        {"role": "user", "content": "Hello, world!"}
    ],
    "temperature": 0.7,
    "max_tokens": 2048
}

// Node Executor -> Global Scheduler (响应)
{
    "request_id": "req_abc123",
    "status": "success",
    "content": "Hello! How can I help you?",
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30
    },
    "gpu_seconds": 0.5,
    "cost_vibe": 0.002
}
```

### 3.3 心跳协议

```json
// Node Executor -> Global Scheduler (定期心跳)
POST /heartbeat
{
    "node_id": "node_001",
    "status": "idle",  // idle | busy | offline
    "loaded_models": ["Qwen/Qwen2.5-7B-Instruct"],
    "gpu_utilization": [0.1, 0.2, 0.15, 0.1],
    "available_vram_gb": 120
}
```

---

## 4. 调度策略

### 4.1 节点选择算法

```
当收到推理请求时:

1. 根据 model_name 查找 Model Registry 获取模型需求
   - min_gpu_count: 最少需要几张卡
   - min_vram_per_gpu: 每张卡最少显存

2. 从 GPU Pool 中筛选符合条件的节点:
   - node.status == IDLE
   - node.gpu_count >= model.min_gpu_count
   - node.available_vram >= model.min_vram_per_gpu * model.min_gpu_count

3. 按以下优先级排序:
   - 优先选择 loaded_models 包含目标模型的节点 (避免冷启动)
   - 其次选择 available_vram 最大的节点 (显存最充裕)
   - 最后选择 gpu_utilization 最低的节点 (最空闲)

4. 如果没有找到合适节点:
   - 返回 503 Service Unavailable
   - 或等待一段时间后重试
```

### 4.2 多卡并行 (Tensor Parallelism)

```
模型需要多卡时:
1. 查找满足 gpu_count >= 需求的节点
2. TP size = min(节点 GPU 数, 模型最大 TP 数)
3. vLLM 启动时指定 --tensor-parallel-size

示例:
- 模型需要 4 卡
- 节点 A 有 4 卡 -> TP=4, 独占节点
- 节点 B 有 8 卡 -> TP=4, 预留 4 卡给其他任务
```

---

## 5. 计费设计

### 5.1 计费流程

```
1. 请求进入时:
   ├── 检查用户余额
   ├── 预估 GPU 卡时 + Token 费用
   └── 如果余额不足，返回 402

2. 推理执行中:
   └── 记录开始时间

3. 推理完成后:
   ├── 计算实际 GPU 卡时
   ├── 统计实际 Token 数
   ├── 计算总费用 = GPU 卡时费 + Token 费
   ├── 扣除用户费用
   └── 记录 GPU 持有者奖励 (平台抽 30%)

4. 欠费处理:
   ├── 如果余额不足，先完成任务
   ├── 记录欠费金额到用户账户
   └── 下次使用时检查并要求还清欠费
```

### 5.2 费率表 (Phase 1)

| 费用类型 | 费率 | 说明 |
|---------|------|------|
| GPU 卡时 | 0.001 Vibe/秒/GPU | 底层资源成本 |
| Token | 0.001 Vibe/1K tokens | 上层服务成本 |
| 平台抽成 | 30% | 从 GPU 持有者收入中抽取 |

### 5.3 节点奖励计算

```python
def calculate_node_reward(gpu_seconds: float) -> float:
    gross_cost = gpu_seconds * GPU_COST_PER_SECOND  # 0.001 Vibe/s
    net_cost = gross_cost * (1 - PLATFORM_FEE_RATIO)  # 70%
    return net_cost

# 示例: 100 GPU 秒
# gross = 100 * 0.001 = 0.1 Vibe
# net = 0.1 * 0.7 = 0.07 Vibe (节点获得)
```

---

## 6. 数据流

### 6.1 完整请求流程

```
┌──────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌───────────────┐
│  C 端    │     │ Global Scheduler │     │  Node Executor  │     │    vLLM       │
│  用户    │     │                  │     │                  │     │               │
└────┬─────┘     └────────┬─────────┘     └────────┬─────────┘     └──────┬────────┘
     │                    │                        │                       │
     │ POST /v1/chat/...  │                        │                       │
     │───────────────────►│                        │                       │
     │                    │                        │                       │
     │                    │ 1. 检查余额             │                       │
     │                    │ 2. 预估费用             │                       │
     │                    │                        │                       │
     │                    │ 3. select_node()       │                       │
     │                    │◄───────────────────────│                       │
     │                    │  (返回最优节点)          │                       │
     │                    │                        │                       │
     │                    │ POST /inference         │                       │
     │                    │────────────────────────►│                       │
     │                    │                        │                       │
     │                    │                        │ 4. 检查模型是否加载     │
     │                    │                        │◄───────────────────────│
     │                    │                        │                        │
     │                    │                        │ 5. vLLM.generate()     │
     │                    │                        │───────────────────────►│
     │                    │                        │                        │
     │                    │                        │ 6. 返回推理结果         │
     │                    │                        │◄───────────────────────│
     │                    │                        │                       │
     │                    │ 7. 返回 InferenceResp  │                       │
     │                    │◄────────────────────────│                       │
     │                    │                        │                       │
     │                    │ 8. charge() 扣费        │                       │
     │                    │                        │                       │
     │                    │ 9. 返回 OpenAI 格式     │                       │
     │◄───────────────────│                        │                       │
     │                    │                        │                       │
     │  200 OK (结果)     │                        │                       │
```

### 6.2 节点注册流程

```
┌──────────────────┐     ┌─────────────────┐
│ Global Scheduler │     │ Node Executor   │
│                  │     │                 │
└───────┬──────────┘     └────────┬────────┘
        │                         │
        │ 1. 启动时: POST /register
        │◄────────────────────────│
        │                         │
        │ 2. 返回 registered      │
        │────────────────────────►│
        │                         │
        │ 3. 定期 POST /heartbeat
        │◄────────────────────────│
        │                         │
        │ 4. 更新 GPU Pool        │
        │                         │
        ▼                         ▼
```

---

## 7. 部署架构

### 7.1 Phase 1 部署 (MVP)

```
开发机器 (笔记本)
├── Global Scheduler (localhost:8000)
└── Node Executor (localhost:8080, 模拟单节点)
```

### 7.2 Phase 2 部署 (生产)

```
┌─────────────────────────────────────────────────────────┐
│                    Global Scheduler                       │
│                    (2+ 副本, 高可用)                     │
│                    (Kubernetes / Docker Swarm)           │
└─────────────────────────────────────────────────────────┘
                          │
                          │ 负载均衡
                          ▼
┌─────────────────────────────────────────────────────────┐
│                    GPU 节点 1                            │
│  Node Executor A (4x A100 80GB)                         │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│                    GPU 节点 2                            │
│  Node Executor B (2x RTX 4090 24GB)                    │
└─────────────────────────────────────────────────────────┘
                          ...
┌─────────────────────────────────────────────────────────┐
│                    GPU 节点 N                            │
│  Node Executor N (8x H100)                              │
└─────────────────────────────────────────────────────────┘
```

---

## 8. 模型管理

### 8.1 预置模型 (Phase 1)

| 模型名称 | 类型 | 显存需求 | GPU 数 | 来源 |
|---------|------|---------|--------|------|
| Qwen/Qwen2.5-7B-Instruct | 文本对话 | ~14GB | 1 | HuggingFace |
| Qwen/Qwen2.5-14B-Instruct | 文本对话 | ~28GB | 1 | HuggingFace |

### 8.2 后续计划模型

| 模型名称 | 类型 | 显存需求 | GPU 数 | 来源 |
|---------|------|---------|--------|------|
| CogVideoX-5b | 视频生成 | ~48GB | 2+ | HuggingFace |
| HunyuanVideo | 视频生成 | ~80GB | 4+ | HuggingFace |
| Qwen/Qwen2.5-72B-Instruct | 文本对话 | ~145GB | 4+ | HuggingFace |
| LLaVA | 多模态 | ~20GB | 1 | HuggingFace |

### 8.3 模型加载策略

```
启动时 (Preload):
├── 常用对话模型预加载
├── 占用固定显存
└── 持续保持

按需加载 (On-demand):
├── 非预置模型
├── 请求到达时加载
├── 有冷启动延迟 (下载模型 + 加载权重)
└── 空闲一段时间后可卸载
```

---

## 9. 容错设计

### 9.1 节点故障处理

```
1. 节点故障检测:
   ├── 心跳超时 (默认 30s)
   └── GPU 利用率异常

2. 处理流程:
   ├── 标记节点为 OFFLINE
   ├── 将正在执行的任务加入重试队列
   ├── 重新调度到其他节点
   └── 最多重试 3 次

3. 故障节点恢复:
   ├── 心跳恢复后标记为 IDLE
   └── 重新接收任务
```

### 9.2 单节点内故障

```
vLLM 进程崩溃:
├── 捕获异常
├── 重新启动 vLLM 进程
├── 重新加载模型
└── 返回错误给 Global Scheduler
```

---

## 10. 安全性 (Phase 2)

### 10.1 待实现

- API Key 认证
- 节点身份验证
- 请求加密
- 资源隔离 (容器化)

---

## 11. 监控与日志

### 11.1 监控指标

| 指标 | 说明 |
|------|------|
| GPU 利用率 | 每张卡的利用率 |
| GPU 显存使用 | 已用/总显存 |
| 请求延迟 | API 响应时间 |
| 推理延迟 | 模型推理时间 |
| 错误率 | 请求失败率 |
| 余额预警 | 余额低于阈值 |

### 11.2 日志

- 结构化日志 (JSON)
- 请求日志 (request_id, model, latency)
- 错误日志 (stack trace)
- 计费日志 (charge 记录)

---

## 12. 未来扩展

### 12.1 Phase 3+ 功能

- WebSocket 流式输出
- 用户自安装模型
- 去中心化模型分发 (IPFS)
- 模型版本管理
- A/B 测试
- 模型微调服务

### 12.2 与 USMSB SDK 深度集成

- Agent 可以通过 A2A/MCP 调用 LLM 服务
- GPU 资源作为 USMSB 网络的一种能力输出
- Vibe 计费与 USMSB 经济系统打通
