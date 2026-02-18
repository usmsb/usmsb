# USMSB SDK - AI 文明新世界平台

Universal System Model of Social Behavior (USMSB) SDK - 构建去中心化 AI 文明新世界平台的完整解决方案。

## 项目概述

USMSB SDK 是一个完全去中心化的分布式平台，每个部署的节点自动成为：
- **服务发现节点** - 自动发现网络中的其他节点和服务
- **服务注册节点** - 注册本地服务供其他节点发现
- **服务提供节点** - 提供 LLM 推理、Agent 托管、计算、区块链等服务
- **客户端节点** - 消费其他节点提供的服务

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        USMSB 去中心化节点架构                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   Frontend   │  │  Backend API │  │   P2P Node   │  │  Blockchain  │   │
│  │  (React+TS)  │  │  (FastAPI)   │  │   (9001)     │  │   Node       │   │
│  │   Port 3000  │  │   Port 8000  │  │              │  │              │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │                 │           │
│  ┌──────┴─────────────────┴─────────────────┴─────────────────┴──────┐    │
│  │                    分布式服务注册表 (Gossip Protocol)               │    │
│  └────────────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        LLM 适配器层                                  │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │   │
│  │  │   OpenAI   │ │   GLM-5    │ │   Gemini   │ │   Custom   │       │   │
│  │  │  (GPT-4)   │ │  (智谱AI)  │ │  (Google)  │ │  (Local)   │       │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Agent 能力层                                  │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐       │   │
│  │  │   Skills   │ │Communication│ │Transaction │ │  Chains    │       │   │
│  │  │  技能系统  │ │ Agent通信  │ │ Agent交易  │ │ 双链支持   │       │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 核心功能

### 1. LLM 适配器
- **OpenAI** - GPT-4, GPT-3.5-turbo 支持
- **GLM-5** - 智谱AI国产模型支持（中文原生NLU）
- **Gemini** - Google AI 模型支持
- **自定义适配器** - 支持本地模型

### 2. Agent 技能系统
- 技能注册、发现和执行
- 输入/输出验证
- 内置技能：文本分析、数据转换、Web搜索、代码执行
- 技能市场基础架构

### 3. Agent 间通信
- P2P 消息传递（直接/广播模式）
- Pub/Sub 事件驱动模式
- Request-Reply 同步模式
- 任务委托、共识投票、资源共享协议

### 4. Agent 间交易系统
- Agent 间代币转账
- 服务支付系统
- 托管交易与条件释放
- 质押/解质押机制

### 5. 双区块链支持
- **以太坊生态** - 通过 Web3.py 集成
- **自建 USMSB Chain**:
  - 2秒出块时间，专为 Agent 交易优化
  - Agent 身份注册与声誉系统
  - 链上治理与投票
  - 跨链桥支持

### 6. 去中心化 P2P 节点
- Gossip 协议服务发现
- 自动服务注册
- 负载均衡服务路由
- 节点声誉系统

### 7. 9 大通用行动接口 (NEW)
- **IPerceptionService** - 感知服务接口
- **IDecisionService** - 决策服务接口
- **IExecutionService** - 执行服务接口
- **IInteractionService** - 交互服务接口
- **ITransformationService** - 转化服务接口
- **IEvaluationService** - 评估服务接口
- **IFeedbackService** - 反馈服务接口
- **ILearningService** - 学习服务接口
- **IRiskManagementService** - 风险管理服务接口

### 8. 6 大核心逻辑引擎 (NEW)
- **GoalActionOutcomeEngine** - 目标-行动-结果循环引擎
- **ResourceTransformationValueEngine** - 资源-转化-价值链引擎
- **InformationDecisionControlEngine** - 信息-决策-控制循环引擎
- **SystemEnvironmentEngine** - 系统-环境交互引擎
- **EmergenceSelfOrganizationEngine** - 涌现与自组织引擎
- **AdaptationEvolutionEngine** - 适应与进化引擎

### 9. 知识库适配器 (NEW)
- **VectorDB 适配器** - 支持 Chroma, Pinecone, Weaviate, Milvus, FAISS
- **GraphDB 适配器** - 支持 Neo4j, ArangoDB
- **RAG 支持** - 检索增强生成集成
- **内存模式** - 无需外部依赖的快速开发

### 10. 决策支持服务 (NEW)
- 多准则决策分析 (MCDA)
- 风险评估决策支持
- 目标对齐推荐生成
- 资源感知优化
- 敏感性分析

### 11. 系统仿真服务 (NEW)
- Agent-Based Modeling (ABM)
- 离散事件仿真 (DES)
- Monte Carlo 仿真
- 涌现行为检测
- 仿真结果分析

### 12. 数据管理模块 (NEW)
- SQLAlchemy 异步模型
- Repository 模式抽象
- 支持多种数据库 (SQLite, PostgreSQL, MySQL)
- 数据迁移支持

### 13. 日志与监控模块 (NEW)
- 结构化 JSON 日志
- 事件总线 (Pub/Sub)
- 指标收集 (Counter, Gauge, Histogram, Timer)
- Prometheus 格式导出
- 请求追踪与关联 ID

## 目录结构

```
usmsb-sdk/
├── src/usmsb_sdk/
│   ├── core/                      # 核心模块
│   │   ├── elements.py            # 9大核心元素
│   │   ├── interfaces.py          # 服务接口
│   │   ├── universal_actions.py   # 9大通用行动接口 (NEW)
│   │   ├── logic/
│   │   │   ├── goal_action_outcome.py
│   │   │   └── core_engines.py    # 6大核心逻辑引擎 (NEW)
│   │   ├── skills/                # Agent 技能系统
│   │   └── communication/         # Agent 通信系统
│   ├── intelligence_adapters/     # 智能源适配器
│   │   ├── llm/
│   │   │   ├── openai_adapter.py  # OpenAI 适配器
│   │   │   └── glm_adapter.py     # GLM-5 适配器
│   │   ├── knowledge_base/
│   │   │   └── adapters.py        # VectorDB/GraphDB 适配器 (NEW)
│   │   └── manager.py             # 智能源管理器
│   ├── services/                  # 应用服务
│   │   ├── behavior_prediction_service.py
│   │   ├── agentic_workflow_service.py
│   │   ├── decision_support_service.py    # 决策支持服务 (NEW)
│   │   └── system_simulation_service.py   # 系统仿真服务 (NEW)
│   ├── data_management/           # 数据管理模块 (NEW)
│   │   ├── models.py              # SQLAlchemy 数据模型
│   │   └── repositories.py        # Repository 模式实现
│   ├── logging_monitoring/        # 日志监控模块 (NEW)
│   │   ├── logger.py              # 结构化日志
│   │   ├── metrics.py             # 指标收集
│   │   └── event_bus.py           # 事件总线
│   ├── platform/                  # 平台扩展
│   │   ├── blockchain/            # 区块链模块
│   │   │   ├── adapter.py         # 以太坊适配器
│   │   │   ├── custom_chain_adapter.py  # 自建链
│   │   │   └── agent_transactions.py    # Agent 交易
│   │   ├── compute/               # 计算资源
│   │   ├── registry/              # 模型/数据注册
│   │   ├── human/                 # 人机协作
│   │   └── governance/            # 治理模块
│   ├── node/                      # 去中心化节点
│   │   └── decentralized_node.py
│   ├── config/
│   │   └── settings.py            # 配置管理
│   └── api/
│       └── rest/main.py           # REST API
├── frontend/                      # React 前端
│   ├── src/
│   │   ├── pages/                 # 页面组件
│   │   ├── components/            # UI 组件
│   │   ├── store/                 # 状态管理
│   │   └── lib/api.ts             # API 客户端
├── docker/                        # Docker 配置
├── tests/                         # 测试目录
├── run_server.py                  # 启动后端
├── run_p2p_node.py                # 启动 P2P 节点
├── run_blockchain.py              # 启动区块链
├── Dockerfile                     # Docker 镜像
└── docker-compose.yml             # Docker 编排
```

## 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- npm 或 yarn

### 安装依赖

```bash
# 安装 Python 依赖
pip install pydantic pydantic-settings python-dotenv pyyaml httpx aiohttp aiofiles fastapi uvicorn python-multipart sqlalchemy aiosqlite structlog click rich

# 安装前端依赖
cd frontend && npm install
```

### 启动服务

#### 方式一：分别启动各服务

```bash
# 1. 启动后端 API (端口 8000)
python run_server.py

# 2. 启动前端 (端口 3000)
cd frontend && npm run dev

# 3. 启动 P2P 节点 (端口 9001)
python run_p2p_node.py

# 4. 启动区块链节点
python run_blockchain.py
```

#### 方式二：Docker 部署

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端界面 | http://localhost:3000 | React Dashboard |
| API 文档 | http://localhost:8000/docs | Swagger UI |
| API 健康检查 | http://localhost:8000/health | 服务状态 |
| P2P 节点 | http://localhost:9001 | P2P 服务 |

## 调试过程

### 1. 后端 API 调试

**测试健康检查：**
```bash
curl http://localhost:8000/health
```

**成功响应：**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": 1771067804.483002,
  "services": {
    "llm": "unavailable",
    "prediction": "unavailable",
    "workflow": "unavailable"
  }
}
```

**创建 Agent：**
```bash
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{"name": "TestAgent", "type": "ai_agent", "capabilities": ["reasoning", "planning"]}'
```

**成功响应：**
```json
{
  "id": "7fad6015-a203-4df8-b63a-963b85f8451d",
  "name": "TestAgent",
  "type": "ai_agent",
  "capabilities": ["reasoning", "planning"],
  "state": {},
  "goals_count": 0,
  "resources_count": 0,
  "created_at": 1771067153.371745
}
```

### 2. P2P 节点调试

**测试 P2P 节点启动：**
```python
import asyncio
import sys
sys.path.insert(0, 'src')
from usmsb_sdk.node.decentralized_node import DecentralizedPlatform

async def test():
    config = {
        'port': 9001,
        'capabilities': ['llm', 'agent_hosting', 'compute', 'blockchain'],
    }
    platform = DecentralizedPlatform(config)
    success = await platform.start()
    if success:
        info = await platform.node.get_node_info()
        print(f"Node ID: {info['node_id']}")
        print(f"Status: {info['status']}")
        print(f"Port: {info['identity']['port']}")
        await platform.stop()
        return True
    return False

asyncio.run(test())
```

**成功输出：**
```
P2P Node Started!
Node ID: node_12a4a8ce075f5dc8
Status: active
Port: 9001
P2P Node tested successfully!
```

### 3. 区块链节点调试

**测试区块链启动：**
```python
import asyncio
import sys
sys.path.insert(0, 'src')
from usmsb_sdk.platform.blockchain.custom_chain_adapter import CustomChainAdapter, CustomChainNetwork

async def test():
    chain = CustomChainAdapter(CustomChainNetwork.LOCAL)
    success = await chain.initialize({})
    if success:
        info = await chain.get_chain_info()
        print(f"Network: {info['network']}")
        print(f"Node ID: {info['node_id']}")
        print(f"Block Height: {info['block_height']}")
        wallet = await chain.create_wallet()
        print(f"Wallet: {wallet['address']}")
        print(f"Balance: {wallet['balance']} USMSB")
        await chain.shutdown()
        return True
    return False

asyncio.run(test())
```

**成功输出：**
```
Blockchain Node Started!
Network: usmsb_local
Node ID: 8dd4a8f3
Block Height: 0
Test Wallet: usmsb_0afb1abd5655d805c89d1f99d3dbc332
Balance: 1000.0 USMSB
Blockchain node tested successfully!
```

### 4. 前端调试

**启动前端开发服务器：**
```bash
cd frontend && npm run dev
```

**成功输出：**
```
VITE v5.4.21  ready in 801 ms

➜  Local:   http://localhost:3000/
➜  Network: use --host to expose
```

**验证前端状态：**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
# 应返回: 200
```

## 状态说明

### 服务状态指标

| 状态 | 说明 |
|------|------|
| `healthy` | 服务正常运行 |
| `active` | P2P 节点已激活 |
| `unavailable` | 服务未配置（如 LLM 需要配置 API Key） |

### LLM 服务状态

LLM 服务显示 `unavailable` 是正常现象，需要配置 API Key：

```bash
# 创建 .env 文件
cat > .env << EOF
# 使用 OpenAI
OPENAI_API_KEY=sk-your-key-here

# 或使用国产 GLM-5
ZHIPU_API_KEY=your-zhipu-key-here
EOF
```

配置后重启服务，LLM 状态将变为 `available`。

### 端口占用问题

如果遇到端口占用错误：
```
[Errno 10048] error while attempting to bind on address
```

解决方案：
1. 检查端口占用：`netstat -an | grep LISTEN | grep 8080`
2. 修改配置文件中的端口号
3. 或关闭占用端口的进程

## USMSB 核心模型

### 9 大核心元素

1. **Agent（智能体）** - 具有感知、决策和行动能力的实体
2. **Object（对象）** - 智能体行为的目标
3. **Goal（目标）** - 智能体期望达到的状态
4. **Resource（资源）** - 活动所需的输入
5. **Rule（规则）** - 智能体行为的规范和约束
6. **Information（信息）** - 系统中的数据和知识
7. **Value（价值）** - 活动产生的收益
8. **Risk（风险）** - 潜在的负面影响
9. **Environment（环境）** - 外部环境和条件

### 6 大核心逻辑

1. **目标-行动-结果循环** - 持续的目标驱动行为周期
2. **资源-转化-价值链** - 资源配置和价值创造
3. **信息-决策-控制循环** - 信息驱动的决策制定
4. **系统-环境交互** - 环境状态管理
5. **涌现与自组织** - 宏观行为模式识别
6. **适应与进化** - 长期系统优化

## 配置说明

创建 `.env` 文件：

```env
# LLM 配置
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4-turbo-preview

# 或使用国产 GLM-5
ZHIPU_API_KEY=your-zhipu-key
GLM_MODEL=glm-4

# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./usmsb.db

# Redis 配置 (可选)
REDIS_URL=redis://localhost:6379/0

# API 配置
API_HOST=0.0.0.0
API_PORT=8000

# 日志配置
LOG_LEVEL=INFO
```

## 开发指南

### 运行测试

```bash
pytest tests/ -v --cov=usmsb_sdk
```

### 代码风格

```bash
# 格式化代码
black src/usmsb_sdk

# 类型检查
mypy src/usmsb_sdk
```

## 许可证

MIT License

---

**AI 文明新世界平台** - 构建去中心化的 AI 智能体生态系统
