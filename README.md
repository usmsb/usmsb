# USMSB - AI 文明新世界平台

> 构建去中心化的 AI 智能体生态系统

## 项目简介

USMSB 是一个基于 **USMSB（Universal System Model of Social Behavior，通用社会行为系统模型）** 的去中心化 AI 文明新世界平台。每个部署的节点自动成为服务发现节点，服务注册节点，服务提供节点和客户端节点，共同构建一个自主、开放，智能的分布式系统。

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USMSB 整体架构                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         前端层 (Frontend)                             │   │
│  │                    React + TypeScript + Vite                         │   │
│  │                      Port 3000                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         后端层 (Backend)                              │   │
│  │                    FastAPI + SQLAlchemy                             │   │
│  │                      Port 8000                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │   P2P Node   │  │  Blockchain   │  │    LLM       │  │   Agent    │  │
│  │    9001      │  │    Node       │  │   Adapters   │  │   Core     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    分布式服务注册表 (Gossip Protocol)                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 📁 项目结构

```
usmsb/                           # 项目根目录
├── src/usmsb_sdk/              # 核心代码
│   ├── core/                   # 9大核心元素与逻辑引擎
│   ├── api/                    # REST API
│   ├── blockchain/              # 区块链模块
│   ├── agent_sdk/              # Agent SDK
│   ├── intelligence_adapters/   # LLM 适配器
│   ├── services/               # 业务服务
│   ├── data_management/        # 数据管理
│   ├── logging_monitoring/     # 日志监控
│   └── node/                   # P2P 节点
├── frontend/                   # React 前端
├── contracts/                   # 智能合约
├── tests/                       # 测试用例
├── docs/                        # 文档
├── scripts/                     # 脚本工具
├── meta_agent_test_docs/        # Meta Agent 测试文档
│   ├── meta_agent_complete_test.md
│   ├── meta_agent_test_plan.md
│   └── meta_agent_tool_tests.md
├── typechain-types/             # TypeChain 类型定义
│
└── README.md                   # 项目说明
```

## 🔑 核心功能

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

### 7. 9 大通用行动接口
| 接口 | 说明 |
|------|------|
| IPerceptionService | 感知服务接口 |
| IDecisionService | 决策服务接口 |
| IExecutionService | 执行服务接口 |
| IInteractionService | 交互服务接口 |
| ITransformationService | 转化服务接口 |
| IEvaluationService | 评估服务接口 |
| IFeedbackService | 反馈服务接口 |
| ILearningService | 学习服务接口 |
| IRiskManagementService | 风险管理服务接口 |

### 8. 6 大核心逻辑引擎
| 引擎 | 说明 |
|------|------|
| GoalActionOutcomeEngine | 目标-行动-结果循环引擎 |
| ResourceTransformationValueEngine | 资源-转化-价值链引擎 |
| InformationDecisionControlEngine | 信息-决策-控制循环引擎 |
| SystemEnvironmentEngine | 系统-环境交互引擎 |
| EmergenceSelfOrganizationEngine | 涌现与自组织引擎 |
| AdaptationEvolutionEngine | 适应与进化引擎 |

### 9. 知识库适配器
- **VectorDB 适配器** - 支持 Chroma, Pinecone, Weaviate, Milvus, FAISS
- **GraphDB 适配器** - 支持 Neo4j, ArangoDB
- **RAG 支持** - 检索增强生成集成
- **内存模式** - 无需外部依赖的快速开发

### 10. 决策支持服务
- 多准则决策分析 (MCDA)
- 风险评估决策支持
- 目标对齐推荐生成
- 资源感知优化
- 敏感性分析

### 11. 系统仿真服务
- Agent-Based Modeling (ABM)
- 离散事件仿真 (DES)
- Monte Carlo 仿真
- 涌现行为检测
- 仿真结果分析

### 12. 数据管理模块
- SQLAlchemy 异步模型
- Repository 模式抽象
- 支持多种数据库 (SQLite, PostgreSQL, MySQL)
- 数据迁移支持

### 13. 日志与监控模块
- 结构化 JSON 日志
- 事件总线 (Pub/Sub)
- 指标收集 (Counter, Gauge, Histogram, Timer)
- Prometheus 格式导出
- 请求追踪与关联 ID

## 🤖 Meta Agent

Meta Agent 是基于 USMSB 模型的超级 AI 智能体，具备九大核心能力：

| 能力 | 说明 |
|------|------|
| 🧠 感知 | 理解用户意图、情感、实体 |
| 🎯 决策 | 分析问题、制定执行计划 |
| ⚡ 执行 | 调用工具完成任务 |
| 💬 交互 | 自然语言对话、协作 |
| 🔄 转化 | 数据格式转换，信息提炼 |
| 📊 评估 | 结果质量评估、风险分析 |
| 📣 反馈 | 执行结果反馈、错误报告 |
| 📚 学习 | 从交互中学习、优化行为 |
| 🛡️ 风控 | 安全策略、异常检测 |

Meta Agent 可以：
- 🖥️ 管理节点，执行区块链操作
- 📊 数据分析、报告生成
- 🗳️ 参与治理投票
- 🤝 AI Agent 间协作
- 💻 执行代码（Python/JavaScript）
- 📁 文件管理
- 🌐 网页抓取与API调用

## 🚀 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- npm 或 yarn

### 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

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
docker-compose up -d
```

### 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端界面 | http://localhost:3000 | React Dashboard |
| API 文档 | http://localhost:8000/docs | Swagger UI |
| API 健康检查 | http://localhost:8000/health | 服务状态 |
| P2P 节点 | http://localhost:9001 | P2P 服务 |

## 📖 USMSB 核心模型

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

## ⚙️ 配置说明

在项目根目录下创建 `.env` 文件：

```env
# LLM 配置
OPENAI_API_KEY=your-openai-key
OPENAI_MODEL=gpt-4-turbo-preview

# 或使用国产 GLM-5
ZHIPU_API_KEY=your-zhipu-key
GLM_MODEL=glm-4

# 数据库配置
DATABASE_URL=sqlite+aiosqlite:///./usmsb.db

# API 配置
API_HOST=0.0.0.0
API_PORT=8000

# 日志配置
LOG_LEVEL=INFO
```

## 📚 文档

- [USMSB SDK 详细文档](./src/usmsb_sdk/README.md)
- [Meta Agent 介绍](./src/usmsb_sdk/meta_agent_intro.md)
- [测试文档](./meta_agent_test_docs/)

## 🧪 运行测试

```bash
pytest tests/ -v
```

## 📄 许可证

MIT License

---

**AI 文明新世界平台** - 构建去中心化的 AI 智能体生态系统
