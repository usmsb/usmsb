# Component Design

> USMSB SDK Core Component Design

<div style="background: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0;">

**Language / 语言:** <a href="#chinese-translation">English</a> | <a href="#chinese-translation">中文</a>

*Click the link above to jump to the Chinese translation section below.*

</div>

---

<a id="chinese-translation"></a>

<details id="chinese-translation">
<summary><h2>中文翻译 (Click to expand / 点击展开)</h2></summary>

# 组件设计

> USMSB SDK 核心组件设计

---

## 1. 组件概览

### 1.1 Core Components

| Component | Path | Status | Description |
|-----------|------|--------|-------------|
| **Meta Agent** | `platform/external/meta_agent/` | ✅ Implemented | Super Agent |
| **Agent SDK** | `agent_sdk/` | ✅ Implemented | Agent Development Kit |
| **LLM Adapter** | `intelligence_adapters/llm/` | ✅ Implemented | Multi-LLM Support |
| **Skill System** | `core/skills/` | ✅ Implemented | Dynamic Skills |
| **Memory System** | `platform/external/meta_agent/memory/` | ✅ Implemented | Context Management |
| **Reasoning Engine** | `reasoning/` | ✅ Implemented | Multi-Engine Reasoning |
| **Tool Registry** | `platform/external/meta_agent/tools/` | ✅ Implemented | Tool Management |
| **Wallet Module** | `agent_sdk/wallet.py` | ✅ Implemented | Blockchain Wallet |
| **Governance Service** | `services/governance_service.py` | ✅ Implemented | Decentralized Governance |
| **Matching Service** | `services/matching_engine.py` | ✅ Implemented | Intelligent Matching |
| **Collaboration Service** | `agent_sdk/collaboration.py` | ✅ Implemented | Multi-Agent Collaboration |

### 1.2 Pending Components

| Component | Path | Status | Description |
|-----------|------|--------|-------------|
| **Goal Engine** | `platform/external/meta_agent/goals/` | 🔄 Planning | Goal Management |
| **Autonomous Learning** | `platform/external/meta_agent/learning/` | 🔄 Planning | Autonomous Evolution |
| **Emergent Behavior** | - | 🔄 Planning | Multi-Agent Emergence |

---

## 2. Meta Agent Component

### 2.1 Architecture

```
meta_agent/
├── agent.py              # Main Agent Class
├── config.yaml           # Configuration
├── core/                 # Core Capabilities
│   ├── perception.py    # Perception
│   ├── decision.py      # Decision Making
│   ├── execution.py     # Execution
│   ├── learning.py      # Learning
│   └── risk_manager.py  # Risk Management
├── info/                 # Information Extraction
│   ├── extractor.py     # Information Extractor
│   ├── intent_analyzer.py
│   ├── candidate_search.py
│   └── validator.py
├── memory/              # Memory System
├── tools/               # Tool Set
├── skills/              # Skills
├── wallet/              # Wallet
└── workspace/           # Workspace
```

### 2.2 Core Class

```python
class MetaAgent:
    def __init__(self, config: AgentConfig):
        self.llm_manager = LLMManager()
        self.tool_registry = ToolRegistry()
        self.skill_manager = SkillManager()
        self.memory = MemoryContext()
        self.wallet = AgentWallet()

    async def chat(self, message: str): ...
    async def execute_task(self, task: Task): ...
```

---

## 3. Agent SDK Component

### 3.1 Modules

```
agent_sdk/
├── base_agent.py        # Base Agent
├── discovery.py        # Agent Discovery
├── registration.py     # Agent Registration
├── workflow.py         # Workflow
├── collaboration.py    # Collaboration
├── negotiation.py      # Negotiation
├── wallet.py          # Wallet
├── marketplace.py     # Marketplace
├── communication.py   # Communication
└── templates/         # Templates
```

---

## 4. Service Layer Components

### 4.1 Core Services

| Service | Path | Function |
|---------|------|----------|
| **Matching Engine** | `services/matching_engine.py` | Intelligent Matching |
| **Governance Service** | `services/governance_service.py` | Governance |
| **Learning Service** | `services/learning_service.py` | Learning |
| **Environment Service** | `services/environment_service.py` | Environment |
| **Reputation Service** | `services/reputation_service.py` | Reputation |
| **Active Matching** | `services/active_matching_service.py` | Active Matching |

---

## 5. Reasoning Engine

### 5.1 Architecture

```
reasoning/
├── base.py            # Base Class
├── interfaces.py     # Interfaces
├── chain_manager.py   # Chain Management
├── knowledge_integration.py  # Knowledge Integration
├── uncertainty.py    # Uncertainty
└── engines/          # Reasoning Engines
    ├── meta.py       # Meta Reasoning
    ├── commonsense.py # Commonsense Reasoning
    ├── temporal.py   # Temporal Reasoning
    ├── spatial.py    # Spatial Reasoning
    ├── analogical.py # Analogical Reasoning
    ├── causal.py     # Causal Reasoning
    └── logical.py    # Logical Reasoning
```

---

## 6. Related Documentation

- [System Architecture](./system_architecture.md) - Overall System Architecture
- [Meta Agent Design](../04_core_modules/meta_agent_design.md) - Super Agent System Design
- [Agent SDK](../04_core_modules/agent_sdk.md) - Agent Development Kit



> USMSB SDK 核心组件设计

---

## 1. 组件概览

### 1.1 核心组件

| 组件 | 路径 | 状态 | 说明 |
|------|------|------|------|
| **Meta Agent** | `platform/external/meta_agent/` | ✅ 已实现 | 超级Agent |
| **Agent SDK** | `agent_sdk/` | ✅ 已实现 | Agent开发包 |
| **LLM 适配器** | `intelligence_adapters/llm/` | ✅ 已实现 | 多LLM支持 |
| **技能系统** | `core/skills/` | ✅ 已实现 | 动态技能 |
| **记忆系统** | `platform/external/meta_agent/memory/` | ✅ 已实现 | 上下文管理 |
| **推理引擎** | `reasoning/` | ✅ 已实现 | 多引擎推理 |
| **工具注册表** | `platform/external/meta_agent/tools/` | ✅ 已实现 | 工具管理 |
| **钱包模块** | `agent_sdk/wallet.py` | ✅ 已实现 | 区块链钱包 |
| **治理服务** | `services/governance_service.py` | ✅ 已实现 | 去中心化治理 |
| **匹配服务** | `services/matching_engine.py` | ✅ 已实现 | 智能匹配 |
| **协作服务** | `agent_sdk/collaboration.py` | ✅ 已实现 | 多Agent协作 |

### 1.2 待实现组件

| 组件 | 路径 | 状态 | 说明 |
|------|------|------|------|
| **目标引擎** | `platform/external/meta_agent/goals/` | 🔄 规划中 | 目标管理 |
| **自主学习** | `platform/external/meta_agent/learning/` | 🔄 规划中 | 自主进化 |
| **涌现行为** | - | 🔄 规划中 | 多Agent涌现 |

---

## 2. Meta Agent 组件

### 2.1 架构

```
meta_agent/
├── agent.py              # 主Agent类
├── config.yaml           # 配置
├── core/                 # 核心能力
│   ├── perception.py    # 感知
│   ├── decision.py      # 决策
│   ├── execution.py     # 执行
│   ├── learning.py      # 学习
│   └── risk_manager.py  # 风险管理
├── info/                 # 信息提取
│   ├── extractor.py     # 信息提取器
│   ├── intent_analyzer.py
│   ├── candidate_search.py
│   └── validator.py
├── memory/              # 记忆系统
├── tools/               # 工具集
├── skills/              # 技能
├── wallet/              # 钱包
└── workspace/           # 工作空间
```

### 2.2 核心类

```python
class MetaAgent:
    def __init__(self, config: AgentConfig):
        self.llm_manager = LLMManager()
        self.tool_registry = ToolRegistry()
        self.skill_manager = SkillManager()
        self.memory = MemoryContext()
        self.wallet = AgentWallet()

    async def chat(self, message: str): ...
    async def execute_task(self, task: Task): ...
```

---

## 3. Agent SDK 组件

### 3.1 模块

```
agent_sdk/
├── base_agent.py        # 基础Agent
├── discovery.py        # Agent发现
├── registration.py     # Agent注册
├── workflow.py         # 工作流
├── collaboration.py    # 协作
├── negotiation.py      # 协商
├── wallet.py          # 钱包
├── marketplace.py     # 市场
├── communication.py   # 通信
└── templates/         # 模板
```

---

## 4. 服务层组件

### 4.1 核心服务

| 服务 | 路径 | 功能 |
|------|------|------|
| **Matching Engine** | `services/matching_engine.py` | 智能匹配 |
| **Governance Service** | `services/governance_service.py` | 治理 |
| **Learning Service** | `services/learning_service.py` | 学习 |
| **Environment Service** | `services/environment_service.py` | 环境 |
| **Reputation Service** | `services/reputation_service.py` | 信誉 |
| **Active Matching** | `services/active_matching_service.py` | 主动匹配 |

---

## 5. 推理引擎

### 5.1 架构

```
reasoning/
├── base.py            # 基类
├── interfaces.py     # 接口
├── chain_manager.py   # 链管理
├── knowledge_integration.py  # 知识集成
├── uncertainty.py    # 不确定性
└── engines/          # 推理引擎
    ├── meta.py       # 元推理
    ├── commonsense.py # 常识推理
    ├── temporal.py   # 时间推理
    ├── spatial.py    # 空间推理
    ├── analogical.py # 类比推理
    ├── causal.py     # 因果推理
    └── logical.py    # 逻辑推理
```

---

## 6. 相关文档

- [系统架构](./system_architecture.md) - 整体系统架构
- [Meta Agent设计](../04_core_modules/meta_agent_design.md) - 超级Agent系统设计
- [Agent SDK](../04_core_modules/agent_sdk.md) - Agent开发包

</details>
