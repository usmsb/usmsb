# 组件设计

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
