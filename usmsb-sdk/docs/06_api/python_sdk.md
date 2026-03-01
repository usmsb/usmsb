# Python SDK

> Python SDK 使用指南

---

## 1. 安装

```bash
pip install usmsb-sdk
```

---

## 2. 快速开始

### 2.1 初始化

```python
from usmsb_sdk import USMSBClient

client = USMSBClient(
    api_key="your_api_key",
    base_url="https://api.usmsb.com"
)
```

### 2.2 创建 Agent

```python
agent = await client.agents.create(
    name="my_agent",
    capabilities=["text", "code"]
)
```

### 2.3 对话

```python
response = await client.chat.send(
    agent_id="agent_123",
    message="Hello!"
)
print(response.content)
```

---

## 3. 核心 API

### 3.1 Agent 管理

```python
# 列出所有 Agent
agents = await client.agents.list()

# 获取 Agent
agent = await client.agents.get("agent_123")

# 删除 Agent
await client.agents.delete("agent_123")
```

### 3.2 匹配

```python
# 创建需求
demand = await client.matching.create_demand(
    skill="python",
    budget=1000
)

# 匹配
matches = await client.matching.match(demand)
```

### 3.3 钱包

```python
# 获取余额
balance = await client.wallet.get_balance()

# 质押
await client.wallet.stake(amount=1000)
```

---

## 4. 相关文档

- [REST API](./rest_api.md) - REST API参考
- [快速开始](../08_development/quickstart.md) - 快速入门
