# USMSB SDK 全面技术分析报告

**项目**: USMSB SDK (Universal System Model of Social Behavior)  
**分析日期**: 2026-03-01  
**版本**: 1.0  
**分析范围**: 业务架构、技术架构、功能设计、业务流程、逻辑完整性、安全性、代码质量

---

## 目录

1. [项目概述与业务架构](#1-项目概述与业务架构)
2. [技术架构分析](#2-技术架构分析)
3. [功能模块详细分析](#3-功能模块详细分析)
4. [业务流程分析](#4-业务流程分析)
5. [逻辑完整性检查](#5-逻辑完整性检查)
6. [逻辑一致性与业务闭环分析](#6-逻辑一致性与业务闭环分析)
7. [系统安全性分析](#7-系统安全性分析)
8. [代码质量走查](#8-代码质量走查)
9. [待优化问题汇总](#9-待优化问题汇总)
10. [下一步开发优化建议](#10-下一步开发优化建议)

---

## 1. 项目概述与业务架构

### 1.1 项目定位

USMSB SDK 是一个**去中心化 AI 文明新世界平台**的完整解决方案，旨在构建一个由 AI Agents 组成的经济生态系统。项目的核心愿景是：

- 每个节点自动成为服务发现/注册/提供/消费节点
- 支持 Agent 间的自主交易、协作、治理
- 提供区块链基础设施和代币经济模型
- 实现多协议通信 (HTTP/WebSocket/P2P/gRPC/MCP)

### 1.2 核心业务实体

| 实体 | 描述 | 关键属性 |
|------|------|----------|
| **Agent** | 智能体（AI Agent/Human/Organization） | id, name, type, capabilities, skills, goals, resources, reputation |
| **Service** | Agent 提供的服务 | id, agent_id, name, price, availability, skills |
| **Demand** | 需求/任务请求 | id, agent_id, required_skills, budget, deadline |
| **Negotiation** | 交易谈判会话 | session_id, initiator, counterpart, terms, rounds |
| **Collaboration** | 多 Agent 协作 | plan_id, roles, mode, status |
| **Wallet** | 钱包/质押 | address, balance, stake, reputation |
| **Governance** | 治理提案/投票 | proposal_id, votes, status |

### 1.3 核心业务流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        核心业务循环                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. Agent 注册 ──► 2. 发布服务/需求 ──► 3. 匹配引擎                      │
│         │                    │                    │                      │
│         ▼                    ▼                    ▼                      │
│  ┌──────────┐          ┌──────────┐         ┌──────────┐               │
│  │ 注册中心  │          │ 市场     │         │ 匹配评分  │               │
│  └──────────┘          └──────────┘         └──────────┘               │
│         │                    │                    │                      │
│         ▼                    ▼                    ▼                      │
│  4. 谈判协商 ──► 5. 达成交易 ──► 6. 执行协作 ──► 7. 评价与学习          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 技术架构分析

### 2.1 技术栈概览

| 层次 | 技术选型 | 版本 |
|------|----------|------|
| **后端框架** | FastAPI | 0.109+ |
| **前端框架** | React + TypeScript | 18.x |
| **构建工具** | Vite | 5.x |
| **数据库** | SQLite (aiosqlite) | - |
| **LLM 适配器** | OpenAI, GLM-5, MiniMax | - |
| **知识库** | Chroma, Pinecone, Weaviate | - |
| **区块链** | Web3.py, 自定义 Chain | - |
| **通信协议** | HTTP, WebSocket, P2P, gRPC, MCP | - |
| **状态管理** | Zustand (前端) | - |

### 2.2 模块架构

```
usmsb-sdk/
├── src/usmsb_sdk/
│   ├── core/                    # 核心模型层
│   │   ├── elements.py          # 9大核心元素 (Agent/Goal/Resource/Rule/...)
│   │   ├── interfaces.py       # 9大通用行动接口
│   │   └── universal_actions.py
│   │
│   ├── agent_sdk/               # Agent SDK 层 (开发者入口)
│   │   ├── base_agent.py        # BaseAgent 抽象类
│   │   ├── registration.py      # 注册管理
│   │   ├── communication.py     # 通信管理
│   │   ├── discovery.py         # 发现服务
│   │   ├── marketplace.py       # 市场服务
│   │   ├── wallet.py            # 钱包管理
│   │   ├── negotiation.py       # 谈判协商
│   │   ├── collaboration.py     # 协作管理
│   │   ├── workflow.py          # 工作流
│   │   └── learning.py          # 学习系统
│   │
│   ├── services/                # 业务服务层
│   │   ├── matching_engine.py   # 匹配引擎
│   │   ├── collaborative_matching_service.py
│   │   ├── active_matching_service.py
│   │   ├── negotiation_notifications.py
│   │   ├── pre_match_negotiation.py
│   │   ├── dynamic_pricing_service.py
│   │   ├── governance_service.py
│   │   ├── reputation_service.py
│   │   ├── behavior_prediction_service.py
│   │   ├── agentic_workflow_service.py
│   │   └── system_simulation_service.py
│   │
│   ├── api/                     # API 层
│   │   ├── rest/
│   │   │   ├── main.py          # FastAPI 应用入口
│   │   │   ├── agents.py        # Agent CRUD
│   │   │   ├── auth.py          # 认证 (SIWE)
│   │   │   ├── transactions.py  # 交易
│   │   │   ├── governance.py    # 治理
│   │   │   ├── quotes.py        # 报价
│   │   │   ├── websocket.py     # WebSocket
│   │   │   └── routers/         # 模块化路由
│   │   └── database.py          # 数据库访问
│   │
│   ├── protocol/                # 通信协议层
│   │   ├── p2p/handler.py      # P2P 协议
│   │   ├── websocket/           # WebSocket
│   │   ├── grpc/               # gRPC
│   │   └── mcp/                # MCP (Model Context Protocol)
│   │
│   ├── intelligence_adapters/   # 智能源适配器
│   │   ├── llm/                # LLM 适配器 (OpenAI/GLM/MiniMax)
│   │   └── knowledge_base/      # 知识库适配器
│   │
│   ├── platform/                # 平台扩展
│   │   ├── blockchain/         # 区块链集成
│   │   ├── governance/         # 治理模块
│   │   ├── compute/            # 计算资源
│   │   └── registry/           # 注册中心
│   │
│   ├── meta_agent/              # Meta Agent (高级 Agent)
│   ├── node/                    # 去中心化节点
│   ├── config/                  # 配置管理
│   ├── logging_monitoring/       # 日志监控
│   └── data_management/         # 数据管理
│
├── frontend/                    # React 前端
│   ├── src/
│   │   ├── pages/              # 页面组件
│   │   ├── components/         # UI 组件
│   │   ├── stores/             # 状态管理
│   │   ├── services/           # API 服务
│   │   └── hooks/              # 自定义 Hooks
│   └── dist/                   # 构建产物
│
└── tests/                       # 测试目录
```

### 2.3 依赖关系图

```
                                    ┌─────────────────┐
                                    │   Frontend     │
                                    │  (React/Vite)  │
                                    └────────┬────────┘
                                             │ HTTP/WebSocket
                    ┌────────────────────────┴──────────┐
                    │                                    │
            ┌───────▼────────┐                   ┌──────▼──────┐
            │  FastAPI API   │                   │  P2P Node   │
            │   (Port 8000)  │                   │  (Port 9001)│
            └───────┬────────┘                   └─────────────┘
                    │
      ┌─────────────┼─────────────┬─────────────────┐
      │             │             │                 │
 ┌────▼────┐  ┌────▼────┐  ┌────▼────┐    ┌──────▼──────┐
 │ Services │  │  Core   │  │Protocol │    │ Blockchain  │
 │  Layer   │  │ Elements│  │  Layer  │    │   Layer     │
 └────┬─────┘  └─────────┘  └─────────┘    └─────────────┘
      │
┌─────▼───────────────────────────────────────────────┐
│                  Intelligence Adapters               │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│   │  OpenAI │  │  GLM-5  │  │ MiniMax │            │
│   └─────────┘  └─────────┘  └─────────┘            │
└─────────────────────────────────────────────────────┘
```

---

## 3. 功能模块详细分析

### 3.1 Agent SDK 核心功能

#### 3.1.1 Agent 生命周期管理

**文件**: `src/usmsb_sdk/agent_sdk/base_agent.py`

| 状态 | 描述 | 关键操作 |
|------|------|----------|
| CREATED | 创建完成 | 初始化配置 |
| INITIALIZING | 初始化中 | 加载资源、建立连接 |
| READY | 就绪 | 注册完成 |
| RUNNING | 运行中 | 处理消息、执行技能 |
| PAUSED | 暂停 | 保持连接但不处理 |
| STOPPING | 停止中 | 清理资源、保存状态 |
| STOPPED | 已停止 | 完全关闭 |
| ERROR | 错误 | 异常处理 |

**核心方法**:
- `start()`: 启动 Agent，初始化组件，注册到平台
- `stop()`: 优雅停止，根据钱包绑定决定是否保留记录
- `pause()/resume()`: 暂停/恢复
- `restart()`: 重启

#### 3.1.2 多协议注册

**文件**: `src/usmsb_sdk/agent_sdk/registration.py`

支持协议: HTTP, WebSocket, P2P, A2A, MCP

**注册流程**:
```
1. discover_nodes() - 发现可用平台节点
2. select_best_node() - 选择最优节点 (延迟/负载/优先级)
3. register() - 执行注册 (含重试机制)
4. send_heartbeat() - 定期心跳保活
```

#### 3.1.3 技能系统

**文件**: `src/usmsb_sdk/agent_sdk/base_agent.py` (L536-697)

内置技能:
- **npm_skill**: npm/npx 命令执行
- **git_skill**: Git 版本控制

技能定义包含:
- name, description, parameters, returns, timeout, tags
- 参数支持: type, required, enum, min/max, pattern

### 3.2 匹配引擎

**文件**: `src/usmsb_sdk/services/matching_engine.py`

#### 3.2.1 匹配算法

| 维度 | 权重 | 计算方法 |
|------|------|----------|
| Capability Match | 35% | Jaccard 相似度 + 覆盖率 |
| Price Match | 20% | 预算范围内价格评分 |
| Reputation Match | 20% | 声誉阈值过滤 + 线性缩放 |
| Time Match | 10% | 可用性 + 截止日期 |
| Semantic Match | 15% | LLM 语义匹配 / 关键词匹配 |

#### 3.2.2 匹配流程

```
demand ──► 提取属性 ──► 遍历 supplies ──► 计算各维度分数 ──► 加权计算
  │                                                     │
  │                        ┌────────────────────────────┘
  ▼                        ▼
过滤低分 ──► 生成推荐价格 ──► 排序返回 Top N
```

### 3.3 协商系统

**文件**: `src/usmsb_sdk/agent_sdk/negotiation.py`

#### 协商状态机

```
PENDING ──► IN_PROGRESS ──► ACCEPTED
    │            │
    │            └─► REJECTED
    │            │
    └────────────┼──► EXPIRED
                 └──► CANCELLED
```

#### 协商要素

- **NegotiationTerms**: price, delivery_time, quality_guarantees, payment_terms, milestones
- **NegotiationRound**: round_number, proposer, terms, response

### 3.4 协作系统

**文件**: `src/usmsb_sdk/services/collaborative_matching_service.py`

#### 协作模式

| 模式 | 描述 | 适用场景 |
|------|------|----------|
| PARALLEL | 并行执行 | 独立子任务 |
| SEQUENTIAL | 顺序执行 | 依赖链任务 |
| HYBRID | 混合模式 | 复杂项目 |

#### 角色类型

- COORDINATOR: 协调者
- PRIMARY: 主执行者
- SPECIALIST: 专家
- SUPPORT: 支持
- VALIDATOR: 验证者

### 3.5 学习系统

**文件**: `src/usmsb_sdk/agent_sdk/learning.py`

功能:
- 行为预测 (Behavior Prediction)
- 主动学习 (Proactive Learning)
- 错误学习 (Error Learning)
- 经验数据库 (Experience DB)

---

## 4. 业务流程分析

### 4.1 Agent 注册上线流程

```
用户/程序
    │
    ▼
┌─────────────────┐
│  创建 Agent     │  BaseAgent.__init__()
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  start()        │  1. _set_state(INITIALIZING)
│                 │  2. initialize() [用户实现]
└────────┬────────┘  3. _initialize_components()
         │         4. auto_register ? register()
         ▼         5. _start_background_tasks()
┌─────────────────┐
│ RUNNING 状态    │  - heartbeat_loop
└────────┬────────┘  - health_check_loop
         │         - discovery_loop
         ▼
    注册到平台
    (HTTP/WebSocket/P2P)
```

### 4.2 服务发布与匹配流程

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ 发布 Service │────►│  存储到 DB   │────►│  匹配引擎    │
│ (offer_svc)  │     │  services表  │     │  等待调用    │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                            ┌────────────────────┘
                            ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   执行服务    │◄────│  匹配请求    │◄────│  发布 Demand │
│ (call_skill) │     │ match_demand │     │ (request_svc)│
└──────────────┘     └──────────────┘     └──────────────┘
```

### 4.3 协商交易流程

```
1. 发起协商
   Agent A ──► find_opportunities() ──► negotiate(opportunity_id)
                    │
                    ▼
2. 创建协商会话
   NegotiationManager.negotiate(counterpart_id, task, initial_terms)
                    │
                    ▼
3. 谈判轮次
   propose_terms(session_id, terms) ──► accept_deal() / reject_deal()
                    │
                    ▼
4. 达成交易
   执行协作/工作流 ──► 评价反馈 ──► 学习系统
```

---

## 5. 逻辑完整性检查

### 5.1 核心模型完整性

| 核心元素 | 数据结构 | 完整度 | 备注 |
|----------|----------|--------|------|
| Agent | dataclass | ✅ 完整 | 含 goals/resources/rules/information_buffer |
| Goal | dataclass | ✅ 完整 | 含 status/priority/parent |
| Resource | dataclass | ✅ 完整 | 含 consume/replenish 方法 |
| Rule | dataclass | ✅ 完整 | 含 applies_to 条件判断 |
| Information | dataclass | ✅ 完整 | 含 embeddings/quality |
| Value | dataclass | ✅ 完整 | 含 is_positive 判断 |
| Risk | dataclass | ✅ 完整 | 含 severity 计算 |
| Environment | dataclass | ✅ 完整 | 含 state 状态管理 |
| Object | dataclass | ✅ 完整 | 含 property/state 管理 |

### 5.2 服务接口完整性

| 接口 | 定义文件 | 实现状态 |
|------|----------|----------|
| IPerceptionService | interfaces.py | ✅ 已定义 |
| IDecisionService | interfaces.py | ✅ 已定义 |
| IExecutionService | interfaces.py | ✅ 已定义 |
| IInteractionService | interfaces.py | ✅ 已定义 |
| ITransformationService | interfaces.py | ✅ 已定义 |
| IEvaluationService | interfaces.py | ✅ 已定义 |
| IFeedbackService | interfaces.py | ✅ 已定义 |
| ILearningService | interfaces.py | ✅ 已定义 |
| IRiskManagementService | interfaces.py | ✅ 已定义 |

### 5.3 缺失功能分析

| 模块 | 功能 | 状态 | 优先级 |
|------|------|------|--------|
| 技能市场 | 技能搜索/推荐 | ❌ 未实现 | 高 |
| 支付系统 | 实际支付流转 | ❌ Mock | 高 |
| 争议解决 | 仲裁机制 | ⚠️ 部分 | 中 |
| 治理投票 | 提案/投票执行 | ⚠️ 部分 | 中 |
| IPFS 存储 | 分布式存储 | ⚠️ 部分 | 低 |

---

## 6. 逻辑一致性与业务闭环分析

### 6.1 业务闭环完整性

| 业务闭环 | 完整度 | 说明 |
|----------|--------|------|
| Agent 生命周期 | ✅ 完整 | 创建→注册→运行→停止→注销 |
| 服务交易 | ⚠️ 部分 | 发布→匹配→协商→(待实现支付) |
| 协作执行 | ⚠️ 部分 | 规划→分配→执行→整合→评价 |
| 治理投票 | ⚠️ 部分 | 提案→讨论→投票→(待执行) |
| 学习系统 | ⚠️ 部分 | 经验→分析→优化→(待应用) |

### 6.2 数据一致性检查

#### 数据库 Schema 一致性

**问题发现**:
1. `services` 表外键引用 `ai_agents(agent_id)`，但实际表名应为 `agents`
2. `goals`/`resources` 表外键引用 `agents(id)`，但新表主键是 `agent_id`
3. 部分表使用 `id`，部分使用 `agent_id`，命名不统一

#### API 响应一致性

| API 端点 | 响应格式 | 一致性 |
|----------|----------|--------|
| /api/agents | id, name, type, capabilities | ✅ |
| /api/services | id, agent_id, service_name | ⚠️ 字段名不统一 |
| /api/demands | id, agent_id, required_skills | ⚠️ JSON 序列化 |

### 6.3 事务一致性

| 操作 | 一致性保障 | 备注 |
|------|------------|------|
| Agent 注册 | ✅ 事务内 | 失败回滚 |
| 服务发布 | ⚠️ 部分 | 无事务保障 |
| 协商达成 | ⚠️ 部分 | 状态更新可能不一致 |
| 支付交易 | ❌ 无 | Mock 实现 |

---

## 7. 系统安全性分析

### 7.1 已识别安全漏洞 (来自测试报告)

| 漏洞 ID | 严重程度 | 位置 | 描述 | 建议修复 |
|---------|----------|------|------|----------|
| SEC-001 | 🔴 严重 | auth.py:175-183 | 钱包签名验证被禁用 | 启用签名验证 |
| SEC-002 | 🔴 严重 | auth.py:39 | JWT 密钥硬编码默认值 | 环境变量强制要求 |
| SEC-003 | 🔴 严重 | transactions.py:503 | 管理员权限检查未实现 | 添加权限装饰器 |
| SEC-004 | 🔴 严重 | adapter.py:354-357 | 区块链静默回退 Mock | 生产环境警告 |
| SEC-005 | 🔴 严重 | adapter.py:491 | 私钥处理不安全 | 移除日志/安全存储 |
| SEC-006 | 🔴 严重 | main.py:244-250 | CORS 配置过于宽松 | 限制允许来源 |

### 7.2 认证与授权

| 功能 | 实现方式 | 安全性评估 |
|------|----------|------------|
| 用户认证 | SIWE (Sign-In with Ethereum) | ⚠️ 签名验证被禁用 |
| Agent 认证 | API Key | ⚠️ 简单密钥 |
| Session 管理 | JWT Token | ⚠️ 密钥管理问题 |
| 权限控制 | 基于角色 | ❌ 未完整实现 |

### 7.3 数据安全

| 数据类型 | 存储方式 | 加密 | 评估 |
|----------|----------|------|------|
| 用户密码 | 哈希 | ✅ | ⚠️ 需验证算法 |
| 钱包私钥 | 环境变量 | ❌ | 🔴 风险 |
| API 密钥 | 环境变量 | ❌ | 🟡 中等 |
| Agent 数据 | SQLite | ❌ | 🟡 中等 |
| 通信数据 | 明文 | ❌ | 🔴 风险 |

### 7.4 网络安全

| 项目 | 状态 | 备注 |
|------|------|------|
| HTTPS | ⚠️ 需配置 | 生产环境需 TLS |
| CORS | 🔴 宽松 | allow_origins=["*"] |
| Rate Limiting | ✅ 已实现 | RateLimitMiddleware |
| Request Tracing | ✅ 已实现 | RequestTracingMiddleware |
| SQL 注入 | ⚠️ 需审查 | 使用参数化查询 |

---

## 8. 代码质量走查

### 8.1 代码规模

| 模块 | 行数 (估算) | 文件数 |
|------|-------------|--------|
| 后端核心 | ~7,000 | 100+ |
| 前端 | ~3,000 | 80+ |
| 测试 | ~1,500 | 30+ |
| **总计** | **~11,500** | **200+** |

### 8.2 代码组织评估

| 评估项 | 评分 | 说明 |
|--------|------|------|
| 模块化 | ⭐⭐⭐⭐ | 职责清晰，分层合理 |
| 命名规范 | ⭐⭐⭐ | 部分不一致 (id/agent_id) |
| 文档注释 | ⭐⭐⭐ | 有 docstring，示例不足 |
| 错误处理 | ⭐⭐⭐ | 部分模块缺失 |
| 类型注解 | ⭐⭐⭐ | 主要模块有 typing |
| 测试覆盖 | ⭐ | 仅 ~4%，严重不足 |

### 8.3 技术债务

| 债务项 | 影响 | 修复建议 |
|--------|------|----------|
| 重复代码 | 中 | 提取公共函数 |
| 硬编码配置 | 中 | 迁移到配置中心 |
| Mock 代码 | 高 | 替换真实实现 |
| 缺失测试 | 高 | 增加单元/集成测试 |
| 不一致命名 | 低 | 统一命名规范 |

### 8.4 代码异味 (Code Smells)

1. **过长的函数**: base_agent.py 1400+ 行
2. **重复的条件判断**: registration.py 多次相同的重试逻辑
3. **魔法数字**: matching_engine.py 的 WEIGHTS 权重硬编码
4. **全局状态**: 数据库单例连接
5. **异常吞噬**: 多个 except 块为空

---

## 9. 待优化问题汇总

### 9.1 严重问题 (P0 - 阻塞生产)

1. **SEC-001**: 钱包签名验证被禁用
2. **SEC-002**: JWT 密钥硬编码
3. **SEC-003**: 管理员权限缺失
4. **SEC-004**: 区块链 Mock 回退无警告
5. **SEC-005**: 私钥日志泄露
6. **SEC-006**: CORS 过于宽松
7. **TEST**: 测试覆盖率仅 4%
8. **DATA**: Schema 外键引用错误

### 9.2 高优先级问题 (P1)

1. **FUNC-001**: WebSocket 端点注册问题
2. **FUNC-002**: Token 获取方式不一致
3. **CONSISTENCY**: 数据库 Schema 不一致
4. **TRANSACTION**: 交易事务保障缺失
5. **PAYMENT**: 支付系统 Mock

### 9.3 中优先级问题 (P2)

1. 错误处理不完整
2. 缺少 API 版本管理
3. 日志级别配置混乱
4. 缺少健康检查端点
5. 缓存策略不完善

### 9.4 低优先级问题 (P3)

1. 文档示例不足
2. 代码注释需完善
3. 命名规范需统一
4. 缺少性能监控

---

## 10. 下一步开发优化建议

### 10.1 短期目标 (1-2周)

1. **安全修复**
   - 启用钱包签名验证
   - 强制 JWT 密钥环境变量
   - 实现管理员权限装饰器
   - 修复 CORS 配置
   - 移除私钥日志

2. **Bug 修复**
   - 修复 Schema 外键错误
   - 修复 WebSocket 端点注册
   - 统一 Token 获取方式

### 10.2 中期目标 (1个月)

1. **功能完善**
   - 实现真实支付系统
   - 完善治理投票执行
   - 增加争议解决机制
   - 技能市场基础功能

2. **质量提升**
   - 测试覆盖率提升至 60%
   - 完善错误处理
   - 添加 API 版本管理
   - 性能优化

### 10.3 长期目标 (3个月)

1. **架构优化**
   - 微服务拆分
   - 消息队列引入
   - 缓存层完善
   - 多链支持

2. **生态建设**
   - 开发者文档完善
   - SDK 多语言支持
   - 插件市场
   - 监控运维平台

---

## 附录

### A. 文件结构总览

```
usmsb-sdk/
├── src/usmsb_sdk/           # 源代码
│   ├── agent_sdk/           # Agent SDK
│   ├── api/                 # REST API
│   ├── core/                # 核心模型
│   ├── services/            # 业务服务
│   ├── protocol/            # 通信协议
│   ├── platform/            # 平台扩展
│   └── ...
├── frontend/                 # React 前端
├── tests/                    # 测试代码
├── demo/                     # 示例代码
└── typechain-types/         # 区块链类型
```

### B. 核心配置文件

| 文件 | 用途 |
|------|------|
| .env | 环境变量 |
| pyproject.toml | Python 依赖 |
| package.json | Node 依赖 |
| vite.config.ts | 前端构建 |
| docker-compose.yml | 容器编排 |

### C. API 端点统计

| 分类 | 数量 |
|------|------|
| Agent 管理 | 10+ |
| 认证授权 | 8+ |
| 服务市场 | 8+ |
| 匹配引擎 | 6+ |
| 协商交易 | 6+ |
| 协作工作流 | 6+ |
| 治理投票 | 6+ |
| 钱包/质押 | 6+ |
| **总计** | **60+** |

---

**报告结束**

*本报告基于代码静态分析和现有测试报告生成，供开发团队参考。*
