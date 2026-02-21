# Supply Chain Quote Demo

供应链报价系统 Demo - 基于多智能体协作的供应链报价与交易撮合平台。

## 概述

本 Demo 展示了如何使用 USMSB-SDK 构建一个完整的供应链报价系统，包含以下智能体：

| Agent | 角色 | 职责 | Agent ID | 名称 | HTTP 端口 |
|-------|------|------|----------|------|-----------|
| **SupplierAgent** | 供给报价 Agent | 提供商品报价，响应询价请求 | supplier_new_001 | 钢材供应商Agent | 5101 |
| **BuyerAgent** | 需求询价 Agent | 发起询价请求，接收并比较报价 | buyer_new_001 | 采购商Agent | 5102 |
| **PredictorAgent** | 价格预测 Agent | 基于历史数据预测价格趋势 | predictor_new_001 | 价格预测Agent | 5103 |
| **MatchAgent** | 交易撮合 Agent | 匹配买卖双方，撮合交易 | match_new_001 | 撮合Agent | 5104 |

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Supply Chain Platform (P2P)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐    │
│   │                    USMSB Platform (中央平台)                          │    │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐     │    │
│   │  │  Agent   │  │  Quote   │  │  Match   │  │  WebSocket/API   │     │    │
│   │  │ Registry │  │  Manager │  │  Engine  │  │  (Frontend)      │     │    │
│   │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘     │    │
│   └───────┼─────────────┼─────────────┼─────────────────┼───────────────┘    │
│           │             │             │                 │                     │
│           │  注册/心跳   │   报价请求   │    撮合结果     │   用户交互          │
│           ▼             ▼             ▼                 ▼                     │
│   ┌─────────────────────────────────────────────────────────────────────┐    │
│   │                     P2P Agent Network (去中心化)                      │    │
│   │                                                                       │    │
│   │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐            │    │
│   │  │ :5101        │    │ :5102        │    │ :5103        │            │    │
│   │  │ SupplierAgent│◄──►│ BuyerAgent   │◄──►│PredictorAgent│            │    │
│   │  │ (钢材供应商)  │    │ (采购方)      │    │ (价格预测)    │            │    │
│   │  └──────┬───────┘    └──────┬───────┘    └──────────────┘            │    │
│   │         │                   │     ▲                                   │    │
│   │         │    P2P 直连通信   │     │                                   │    │
│   │         └──────────────────►├─────┘                                   │    │
│   │                             │                                         │    │
│   │                    ┌────────┴────────┐                                │    │
│   │                    │ :5104           │                                │    │
│   │                    │ MatchAgent      │                                │    │
│   │                    │ (交易撮合)       │                                │    │
│   │                    └─────────────────┘                                │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 核心程序说明

### 程序关系图

```
                    ┌─────────────────────────────────────────────────────┐
                    │                 USMSB Platform                       │
                    │              (Backend + Frontend)                    │
                    │                  run_demo.py                         │
                    │                                                      │
                    │    启动: 后端API服务 + 前端界面 + 注册代理            │
                    └──────────────────────┬──────────────────────────────┘
                                           │
                        ┌──────────────────┼──────────────────┐
                        │                  │                  │
                        ▼                  ▼                  ▼
        ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
        │    run_demo.py    │  │   Frontend UI     │  │   Backend API     │
        │                   │  │   (Browser)       │  │   (Port 8000)     │
        │  启动Agent服务     │  │  用户交互界面      │  │                   │
        │  + 自动注册        │  │                   │  │  平台管理          │
        └─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘
                  │                      │                      │
                  │    HTTP REST API      │    P2P 直连          │
                  │    /agents            │    /invoke           │
                  ▼                      ▼                      ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │                      Agent 实例                                   │
        │                                                                   │
        │   :5101 Supplier    :5102 Buyer    :5103 Predictor   :5104 Match │
        │                                                                   │
        └─────────────────────────────────────────────────────────────────┘
```

### 1. run_demo.py - 主启动程序

**用途**: 一键启动完整的 Demo 环境

**功能**:
- 启动后端 API 服务 (端口 8000)
- 启动前端开发服务 (端口 3000)
- 自动注册 Demo Agents
- 初始化数据库

**注意**: Agent 服务不再需要单独启动，已集成在 run_demo.py 中

**运行方式**:
```bash
# 安装 SDK
pip install -e usmsb-sdk/src

# 启动 Demo（会自动启动所有 Agent）
python run_demo.py

# 交互式模式（启动后保持运行）
python run_demo.py -m interactive
```

**注意**: Agent 注册和启动功能已集成到 run_demo.py 中，无需单独运行其他脚本。

**注册的 Agent 信息**:
```python
AGENTS = [
    {
        "agent_id": "supplier_new_001",
        "name": "钢材供应商Agent",
        "capabilities": ["supply", "quotation", "inventory"],
        "endpoint": "http://localhost:5101",
        "protocols": ["http", "websocket"],
        "stake_amount": 100.0
    },
    {
        "agent_id": "buyer_new_001", 
        "name": "采购商Agent",
        "capabilities": ["purchase", "quote_request"],
        "endpoint": "http://localhost:5102",
        "protocols": ["http", "websocket"],
        "stake_amount": 100.0
    },
    {
        "agent_id": "predictor_new_001",
        "name": "价格预测Agent",
        "capabilities": ["price_prediction", "analytics"],
        "endpoint": "http://localhost:5103",
        "protocols": ["http", "websocket"],
        "stake_amount": 100.0
    },
    {
        "agent_id": "match_new_001",
        "name": "撮合Agent",
        "capabilities": ["matching", "negotiation"],
        "endpoint": "http://localhost:5104",
        "protocols": ["http", "websocket"],
        "stake_amount": 100.0
    },
]
```

**服务端口映射**:
- HTTP 端口:
  - :5101 - Supplier Agent (钢材供应商Agent)
  - :5102 - Buyer Agent (采购商Agent)
  - :5103 - Predictor Agent (价格预测Agent)
  - :5104 - Match Agent (撮合Agent)
- P2P 端口:
  - :9101 - Supplier Agent P2P
  - :9102 - Buyer Agent P2P
  - :9103 - Predictor Agent P2P
  - :9104 - Match Agent P2P

**P2P 通信协议**:
```python
# 发送消息到 Agent
POST http://localhost:5101/invoke
{
    "method": "chat",
    "params": {
        "message": "你好，请问钢板报价"
    }
}

# Agent 响应
{
    "success": true,
    "result": {
        "message_type": "chat_response",
        "response": "感谢您的询价！目前Q235钢板报价4500元/吨...",
        "agent_id": "supplier_new_001"
    },
    "agent_id": "supplier_new_001",
    "agent_name": "钢材供应商Agent"
}
```

### 程序启动顺序

```
1. run_demo.py
   │
   ├──► 启动后端服务 (port 8000)
   │
   ├──► 启动前端服务 (port 3000) [可选]
   │
   └──► 启动并注册所有 Agent 服务
        │
        ├── :5101 - SupplierAgent (钢材供应商Agent)
        ├── :5102 - BuyerAgent (采购商Agent)
        ├── :5103 - PredictorAgent (价格预测Agent)
        └── :5104 - MatchAgent (撮合Agent)

2. 前端交互
   │
   ├──► 查询 Agents 列表 (GET /api/agents)
   │
   └──► P2P 直连 Agent (POST http://localhost:5101/invoke)
```

## 快速开始

### 环境要求

- Python 3.9+
- Docker & Docker Compose (推荐)
- Redis (可选，用于分布式部署)

### 方式一：Docker Compose 启动（推荐）

```bash
# 1. 复制环境变量配置
cp .env.example .env

# 2. 修改 .env 中的配置（如需要）
vim .env

# 3. 一键启动所有服务
./scripts/start.sh docker

# 或者直接使用 docker-compose
docker-compose up -d

# 4. 查看日志
./scripts/logs.sh

# 5. 停止服务
./scripts/stop.sh
```

### 方式二：本地开发启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动 Redis（如果需要）
redis-server

# 3. 运行 Demo
python run_demo.py --mode interactive

# 或运行测试
python test_scenario.py
```

## 使用说明

### 运行 Demo

```bash
# 交互式模式
python run_demo.py --mode interactive

# 自动运行所有场景
python run_demo.py --mode auto --scenario all

# 运行特定场景
python run_demo.py --mode auto --scenario 1  # 简单询价
python run_demo.py --mode auto --scenario 4  # 完整交易
```

### 运行测试

```bash
# 运行所有测试
python test_scenario.py

# 使用脚本
./scripts/test.sh
```

## Agent SDK 集成说明

本 Demo 中的所有 Agent 均基于 **USMSB Agent SDK** 构建，完全使用 SDK 提供的功能实现。

### SDK 核心组件

```python
from usmsb_sdk.agent_sdk import BaseAgent as SDKBaseAgent
from usmsb_sdk.agent_sdk import AgentConfig as SDKAgentConfig
from usmsb_sdk.agent_sdk.http_server import HTTPServer, run_agent_with_http
from usmsb_sdk.agent_sdk.p2p_server import P2PServer, run_agent_with_p2p
from usmsb_sdk.agent_sdk.communication import Message as SDKMessage
```

### Agent 实现架构

```
BaseAgent (Demo自定义)
    │
    ├── 继承自 SDKBaseAgent
    │
    ├── 使用 SDK 的 HTTPServer 提供 HTTP 服务
    │
    ├── 使用 SDK 的 P2PServer 提供 P2P 通信
    │
    └── 自定义业务逻辑（询价、报价、撮合等）
```

### 关键特性

1. **自动平台注册**: Agent 启动时自动注册到新文明平台
2. **心跳保活**: 自动向平台发送心跳，维持 online 状态
3. **P2P 通信**: Agent 之间可直接进行 P2P 通信
4. **消息处理**: 基于 SDK 的消息总线实现异步消息处理

### 开发自己的 Agent

```python
from shared.base_agent import BaseAgent

class MyAgent(BaseAgent):
    async def on_start(self):
        # 初始化逻辑
        pass
    
    async def handle_message(self, message):
        # 处理消息逻辑
        pass

# 启动 Agent
agent = MyAgent("config.yaml")
await agent.start_with_both(
    http_port=5201,
    p2p_port=9201,
    platform_url="http://localhost:8000"
)
```

## 通信协议

### P2P 去中心化通信

本 Demo 支持两种通信模式：

#### 1. 平台中转模式 (传统)
```
Frontend → Platform API → Agent
         ←              ←
```

#### 2. P2P 直连模式 (推荐)
```
Frontend ←→ Agent (直接通信)
```

**P2P 模式优势**:
- 降低平台负载
- 提高通信效率
- 支持离线场景
- 真正的去中心化

**P2P 端点规范**:

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/heartbeat` | POST | 心跳保活 |
| `/invoke` | POST | 调用 Agent 技能 |
| `/chat` | POST | 聊天消息 |
| `/` | GET | Agent 信息 |

系统使用以下消息类型进行 Agent 间通信：

### 1. 询价请求 (QuoteRequest)

```python
{
    "message_type": "quote_request",
    "buyer_id": "buyer_001",
    "product_id": "steel_001",
    "product_name": "钢板 Q235",
    "quantity": 100,
    "unit": "吨",
    "delivery_date": "2024-03-15",
    "delivery_location": "上海市浦东新区",
    "requirements": {
        "quality_standard": "GB/T 700-2006",
        "target_price": 4500.0
    }
}
```

### 2. 报价响应 (QuoteResponse)

```python
{
    "message_type": "quote_response",
    "supplier_id": "supplier_001",
    "request_id": "req_123456",
    "product_id": "steel_001",
    "unit_price": 4500.00,
    "currency": "CNY",
    "total_price": 450000.00,
    "valid_until": "2024-02-20T18:00:00Z",
    "delivery_lead_time": 7,
    "terms": {
        "payment_method": "银行转账",
        "warranty": "质保一年"
    }
}
```

### 3. 价格预测 (PricePrediction)

```python
{
    "message_type": "price_prediction",
    "predictor_id": "predictor_001",
    "product_id": "steel_001",
    "current_price": 4500.00,
    "predicted_prices": [
        {"date": "2024-02-21", "price": 4520.00, "confidence": 0.85},
        {"date": "2024-02-22", "price": 4535.00, "confidence": 0.80}
    ],
    "trend": "up",
    "recommendation": "建议尽快采购"
}
```

### 4. 撮合结果 (MatchResult)

```python
{
    "message_type": "match_result",
    "match_id": "match_789",
    "buyer_id": "buyer_001",
    "supplier_id": "supplier_001",
    "product_id": "steel_001",
    "matched_quantity": 100,
    "matched_price": 4480.00,
    "total_amount": 448000.00,
    "status": "pending",
    "match_score": 0.85
}
```

## 测试场景

### 场景1: 简单询价报价
验证基本的询价和报价流程。

### 场景2: 多供应商竞争
验证多供应商报价比较和排序功能。

### 场景3: 价格预测辅助决策
验证价格预测功能对采购决策的支持。

### 场景4: 完整交易流程
验证完整的询价-报价-撮合-确认流程。

## 配置说明

### 环境变量 (.env)

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| PLATFORM_URL | 平台服务地址 | http://localhost:8080 |
| REDIS_URL | Redis 连接地址 | redis://localhost:6379 |
| LOG_LEVEL | 日志级别 | INFO |
| AGENT_TIMEOUT | Agent 超时时间(秒) | 30 |

### Agent 配置文件

每个 Agent 都有自己的 `config.yaml` 配置文件，位于各自的目录下：

- `supplier_agent/config.yaml` - 供应商配置
- `buyer_agent/config.yaml` - 采购商配置
- `predictor_agent/config.yaml` - 预测器配置
- `match_agent/config.yaml` - 撮合器配置

## API 接口

### RESTful API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/quotes/request` | POST | 发起询价请求 |
| `/api/quotes/response` | POST | 提交报价 |
| `/api/predictions/{product_id}` | GET | 获取价格预测 |
| `/api/matches` | POST | 执行撮合 |
| `/api/matches/{match_id}` | GET | 查询撮合结果 |

### 消息类型

| 消息类型 | 方向 | 说明 |
|----------|------|------|
| `quote_request` | Buyer -> Supplier | 询价请求 |
| `quote_response` | Supplier -> Buyer | 报价响应 |
| `price_prediction` | Predictor -> All | 价格预测 |
| `match_result` | Match -> Buyer/Supplier | 撮合结果 |
| `match_confirm` | Buyer/Supplier -> Match | 确认撮合 |

## 脚本说明

| 脚本 | 说明 |
|------|------|
| `scripts/start.sh` | 启动服务 (docker/local) |
| `scripts/stop.sh` | 停止服务 (docker/all/local) |
| `scripts/logs.sh` | 查看日志 |
| `scripts/test.sh` | 运行测试 |

## 故障排除

### 常见问题

1. **Redis 连接失败**
   ```
   检查 Redis 是否运行: redis-cli ping
   检查 REDIS_URL 配置是否正确
   ```

2. **Agent 启动失败**
   ```
   检查配置文件路径是否正确
   检查依赖是否安装: pip install -r requirements.txt
   ```

3. **消息传递失败**
   ```
   检查消息总线是否正常
   检查 Agent 是否已注册到消息总线
   ```

### 日志调试

```bash
# 设置详细日志
export LOG_LEVEL=DEBUG

# 查看特定 Agent 日志
docker-compose logs -f supplier_agent
```

## 目录结构

```
supply_chain/
├── shared/                  # 共享模块
│   ├── __init__.py
│   ├── base_agent.py        # Agent 基类
│   ├── message_bus.py       # 消息总线
│   ├── models.py            # 数据模型
│   └── protocols.py         # 通信协议
├── supplier_agent/          # 供给报价 Agent
│   ├── __init__.py
│   ├── agent.py
│   ├── config.yaml
│   └── Dockerfile
├── buyer_agent/             # 需求询价 Agent
│   ├── __init__.py
│   ├── agent.py
│   ├── config.yaml
│   └── Dockerfile
├── predictor_agent/         # 价格预测 Agent
│   ├── __init__.py
│   ├── agent.py
│   ├── config.yaml
│   └── Dockerfile
├── match_agent/             # 交易撮合 Agent
│   ├── __init__.py
│   ├── agent.py
│   ├── config.yaml
│   └── Dockerfile
├── scripts/                 # 运行脚本
│   ├── start.sh
│   ├── stop.sh
│   ├── logs.sh
│   └── test.sh
├── run_demo.py              # 🔵 Demo 主程序 - 一键启动完整环境
├── test_scenario.py         # 测试场景
├── docker-compose.yml       # Docker 配置
├── requirements.txt         # Python 依赖
├── .env.example             # 环境变量示例
├── README.md                # 本文档
└── QUICKSTART.md            # 快速开始指南
```

### 核心程序详解

| 程序 | 图标 | 类型 | 说明 |
|------|------|------|------|
| `run_demo.py` | 🔵 | 主程序 | 启动后端+前端+Agent服务+自动注册，一站式启动 |

## 扩展开发

### 添加新的 Agent

1. 创建新的 Agent 目录
2. 继承 `BaseAgent` 类
3. 实现必要的消息处理器
4. 添加到 `docker-compose.yml`

### 自定义消息类型

在 `shared/protocols.py` 中定义新的消息类型：

```python
@dataclass
class CustomMessage(BaseMessage):
    message_type: str = "custom"
    # 添加自定义字段
```

## 许可证

MIT License

## 联系方式

如有问题或建议，请联系开发团队。
