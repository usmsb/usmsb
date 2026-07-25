# USMSB Distributed Inference Platform

分布式 LLM 推理平台 - USMSB 网络中的超级智能体

## 项目概述

USMSB 分布式推理平台是 USMSB 网络中的一个**超级智能体**，旨在将 USMSB 网络中分布式的 GPU 计算资源整合成一个统一的 LLM 推理服务平台。

**核心定位**：
- 不改变 USMSB SDK 的定位（去中心化 Agent 网络）
- 作为 USMSB 网络中独立存在的超级智能体
- 与 USMSB SDK Agent 通过标准协议 (A2A/MCP) 通信，不耦合

## 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Global Scheduler (全局调度)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  API Server │  │   Router    │  │  GPU Pool   │              │
│  │ (OpenAI兼容) │  │  (请求路由) │  │  (资源管理) │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │Model Registry│  │Billing Engine│                             │
│  │  (模型注册)  │  │  (Vibe计费) │                              │
│  └─────────────┘  └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               Node Executor (节点执行器, 每节点一个)               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  vLLM Engine│  │Model Manager│  │ GPU Monitor │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/usmsb/usmsb.git
cd usmsb
python -m pip install -e .
cd dist-inference
pip install -r requirements.txt
```

源码部署必须让 SDK 与 `dist-inference` 来自同一个 Git revision；不要只从
PyPI 安装旧的 `usmsb-sdk>=0.9.0a0`，否则其中可能还没有
`usmsb_sdk.llm_telemetry`。独立发布 `usmsb-dist-inference` wheel 前，应先发布
包含该模块的 SDK 版本并同步提高 `pyproject.toml` 中的最低版本；运行时若缺少
统一 Telemetry 合同会 fail-closed，而不会绕过审计继续推理。

### 2. 启动 Global Scheduler

```bash
python -m global_scheduler.main --port 8000
```

### 3. 启动 Node Executor (另一终端)

真实 vLLM 节点必须由宿主注入统一的 `LLMInvocationRecorder`。工厂采用
`package.module:callable` 格式，并应在 recorder 上配置 OPC/宿主的非阻塞事件
callback；没有这个配置时节点会 fail-closed，不会暴露无法审计的 LLM 调用。

```bash
export USMSB_DIST_LLM_TELEMETRY_FACTORY="my_runtime.telemetry:build_llm_recorder"
python -m node_executor.main --node-id node_001 --scheduler-url http://localhost:8000 --port 8080
```

工厂的最小合同：

```python
from usmsb_sdk.llm_telemetry import LLMInvocationRecorder

def build_llm_recorder() -> LLMInvocationRecorder:
    return LLMInvocationRecorder(event_callback=publish_event_nowait)
```

每次真实 `vLLM.generate()` 都会生成同一 `provider_attempt_id` 下的
`llm.provider.requested` 与一个终态事件。推理和远程派发均为 single-shot；网络
超时或 Provider 失败不会换节点重放。

### 4. 调用 API

```bash
# 列出可用模型
curl http://localhost:8000/v1/models

# 充值 Vibe (测试用)
curl -X POST http://localhost:8000/v1/billing/deposit/anonymous -d "amount=1000"

# 发送推理请求
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## 项目结构

```
usmsb-dist-inference/
├── global_scheduler/           # 全局调度器
│   ├── __init__.py
│   ├── main.py               # 入口
│   ├── api_server.py         # FastAPI 服务 (OpenAI 兼容 API)
│   ├── router.py              # 请求路由
│   ├── gpu_pool.py           # GPU 资源池
│   ├── model_registry.py     # 模型注册表
│   └── billing.py            # Vibe 计费
│
├── node_executor/             # 节点执行器
│   ├── __init__.py
│   ├── main.py               # 入口
│   ├── vllm_engine.py        # vLLM 封装
│   ├── model_manager.py      # 模型管理
│   ├── gpu_monitor.py        # GPU 监控
│   └── executor.py           # 执行器
│
├── shared/                    # 共享模块
│   ├── __init__.py
│   └── types.py               # 共享数据类型
│
├── tests/                     # 测试
│   ├── test_billing.py
│   ├── test_gpu_pool.py
│   ├── test_model_registry.py
│   └── test_router.py
│
├── docs/                      # 文档
│   ├── prd/                   # 产品需求文档
│   ├── design/                # 设计文档
│   └── api/                   # API 文档
│
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 核心组件

### Global Scheduler

- **API Server**: 提供 OpenAI 兼容的 `/v1/chat/completions` 接口
- **Router**: 请求路由；付费推理单次派发，失败不跨节点重放
- **GPU Pool**: 管理所有 GPU 节点，节点选择算法
- **Model Registry**: 管理可用模型列表
- **Billing Engine**: Vibe 代币计费，平台抽成 30%

### Node Executor

- **vLLM Engine**: vLLM 推理引擎封装
- **Model Manager**: 模型加载/卸载，预加载策略
- **GPU Monitor**: GPU 状态监控

## 计费规则

| 费用类型 | 费率 | 说明 |
|---------|------|------|
| GPU 卡时 | 0.001 Vibe/秒/GPU | 底层资源成本 |
| Token | 0.001 Vibe/1K tokens | 上层服务成本 |
| 平台抽成 | 30% | 从 GPU 持有者收入中抽取 |

## 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单个测试文件
pytest tests/test_billing.py -v
```

## 文档

- [PRD 文档](./docs/prd/README.md)
- [总体设计](./docs/design/README.md)
- [详细设计](./docs/design/detailed-design.md)
- [API 文档](./docs/api/openapi.md)

## 注意事项

1. **Phase 1** 是 MVP 版本，用于快速验证核心流程
2. vLLM 需要 CUDA 支持，开发环境下会使用模拟数据
3. 计费系统目前是简化版本，后续需要与 Vibe SDK 集成
