# Python SDK

> Python SDK 使用指南

---

## 1. 安装

```bash
pip install usmsb-sdk
```

或从源码安装：

```bash
pip install -e .
```

---

## 2. 快速开始

### 2.1 初始化

```python
from usmsb_sdk import USMSBManager

sdk = USMSBManager(config_path="./config.yaml")
await sdk.initialize()
```

### 2.2 创建 Agent

```python
from usmsb_sdk import AgentBuilder

agent = (AgentBuilder()
    .with_name("MyAgent")
    .with_type("ai_agent")
    .with_capabilities(["reasoning", "planning"])
    .build())
```

### 2.3 使用服务

```python
# 获取行为预测服务
prediction_service = sdk.get_service("behavior_prediction")
prediction = await prediction_service.predict_agent_behavior(agent, environment)
```

---

## 3. 核心 API

### 3.1 USMSBManager

```python
from usmsb_sdk import USMSBManager

# 初始化
sdk = USMSBManager(config_path="./config.yaml")
await sdk.initialize()

# 获取服务
service = sdk.get_service("behavior_prediction")
service = sdk.get_service("agentic_workflow")

# 关闭
await sdk.shutdown()
```

### 3.2 AgentBuilder

```python
from usmsb_sdk import AgentBuilder, AgentType

agent = (AgentBuilder()
    .with_name("MyAgent")
    .with_type(AgentType.AI_AGENT)
    .with_capabilities(["reasoning", "planning", "coding"])
    .build())
```

### 3.3 EnvironmentBuilder

```python
from usmsb_sdk import EnvironmentBuilder

env = (EnvironmentBuilder()
    .with_name("TestEnvironment")
    .with_type(EnvironmentType.VIRTUAL)
    .with_state({"key": "value"})
    .build())
```

### 3.4 核心要素

```python
from usmsb_sdk import Agent, Goal, Resource, Rule, Environment

# 创建目标
goal = Goal(name="完成任务", priority=1)

# 创建资源
resource = Resource(
    name="计算资源",
    type=ResourceType.COMPUTATIONAL,
    quantity=100.0
)

# 创建规则
rule = Rule(
    name="权限规则",
    type=RuleType.LEGAL,
    scope=["data_access"]
)
```

---

## 4. 服务列表

| 服务名 | 说明 |
|--------|------|
| behavior_prediction | 行为预测服务 |
| agentic_workflow | Agentic工作流服务 |
| decision_support | 决策支持服务 |
| system_simulation | 系统模拟服务 |
| active_matching | 主动匹配服务 |
| supply_demand_matching | 供需匹配服务 |
| agent_network_explorer | Agent网络探索服务 |
| collaborative_matching | 协作匹配服务 |
| proactive_learning | 主动学习服务 |
| dynamic_pricing | 动态定价服务 |
| joint_order | 联合订单服务 |
| asset_fractionalization | 资产碎片化服务 |
| zk_credential | ZK凭证服务 |

---

## 5. 相关文档

- [REST API](./rest_api.md) - REST API参考
- [WebSocket API](./websocket_api.md) - WebSocket API参考
