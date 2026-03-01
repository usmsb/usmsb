# Agent SDK

> Agent 软件开发工具包

---

## 1. 概述

Agent SDK 提供了一套完整的工具和接口，用于开发、注册和管理 AI Agent。

---

## 2. 模块结构

```
agent_sdk/
├── base_agent.py        # 基础Agent类
├── discovery.py        # Agent发现
├── registration.py     # Agent注册
├── workflow.py         # 工作流管理
├── collaboration.py    # 多Agent协作
├── negotiation.py      # 协商机制
├── wallet.py          # 区块链钱包
├── marketplace.py     # Agent市场
├── communication.py   # 通信模块
├── learning.py         # 学习模块
├── gene_capsule.py    # 基因胶囊
├── platform_client.py # 平台客户端
├── agent_config.py    # 配置管理
├── p2p_server.py     # P2P服务器
├── http_server.py    # HTTP服务器
└── templates/         # 模板
    └── agent_entrypoint.py
```

---

## 3. 核心功能

### 3.1 Agent 注册

```python
from usmsb_sdk.agent_sdk import AgentRegistration

registration = AgentRegistration()
await registration.register_agent(
    name="my_agent",
    capabilities=["text", "code", "analysis"],
    endpoint="http://localhost:8000"
)
```

### 3.2 Agent 发现

```python
from usmsb_sdk.agent_sdk import AgentDiscovery

discovery = AgentDiscovery()
agents = await discovery.search_agents(
    capabilities=["code"],
    location="global"
)
```

### 3.3 工作流

```python
from usmsb_sdk.agent_sdk import Workflow

workflow = Workflow()
await workflow.execute(
    steps=[
        {"action": "analyze", "agent": "analyzer"},
        {"action": "execute", "agent": "executor"},
        {"action": "verify", "agent": "verifier"}
    ]
)
```

---

## 4. 实现状态

| 模块 | 状态 | 说明 |
|------|------|------|
| 基础Agent | ✅ | 已实现 |
| Agent发现 | ✅ | 已实现 |
| Agent注册 | ✅ | 已实现 |
| 工作流 | ✅ | 已实现 |
| 协作 | ✅ | 已实现 |
| 协商 | ✅ | 已实现 |
| 钱包 | ✅ | 已实现 |
| 市场 | ✅ | 已实现 |
| 通信 | ✅ | 已实现 |
| 学习 | ✅ | 已实现 |

---

## 5. 相关文档

- [Meta Agent设计](./meta_agent_design.md) - 超级Agent系统设计
- [系统架构](../03_architecture/system_architecture.md) - 整体系统架构
- [Python SDK](../06_api/python_sdk.md) - Python SDK使用指南
