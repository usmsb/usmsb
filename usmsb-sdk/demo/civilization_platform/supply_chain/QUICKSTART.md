# Agent SDK 快速开始指南

本文档介绍如何使用 USMSB Agent SDK 创建、注册和通信 Agent。

## 安装

```bash
pip install usmsb-sdk
```

## 创建你的第一个 Agent

### 1. 简单 Agent

```python
import asyncio
from usmsb_sdk import BaseAgent, AgentConfig, create_agent

# 方式一：使用工厂函数
agent = create_agent(
    agent_id="my-agent-001",
    name="MyFirstAgent",
    description="My first AI agent",
)

# 方式二：继承 BaseAgent
class MyAgent(BaseAgent):
    async def initialize(self):
        print(f"{self.name} initialized")

    async def handle_message(self, message, session=None):
        print(f"Received: {message.content}")
        return {"status": "received"}

    async def execute_skill(self, skill_name, params):
        if skill_name == "greet":
            return f"Hello, {params.get('name', 'World')}!"
        raise ValueError(f"Unknown skill: {skill_name}")

    async def shutdown(self):
        print(f"{self.name} shutting down")

# 创建配置
config = AgentConfig(
    agent_id="my-agent-002",
    name="CustomAgent",
    description="A custom agent",
    version="1.0.0",
)

# 实例化
agent = MyAgent(config)
```

### 2. 配置 Agent 技能

```python
from usmsb_sdk import SkillDefinition, AgentCapability

# 定义技能
greet_skill = SkillDefinition(
    skill_id="skill-greet",
    name="greet",
    description="Generate a greeting message",
    category="communication",
    input_schema={
        "name": {"type": "string", "description": "Name to greet"}
    },
    output_schema={
        "message": {"type": "string"}
    },
    keywords=["greeting", "hello", "hi"],
)

# 定义能力
chat_capability = AgentCapability(
    name="chat",
    description="Chat and conversation capability",
    level="advanced",
)

# 创建带技能的配置
config = AgentConfig(
    agent_id="chat-agent-001",
    name="ChatAgent",
    skills=[greet_skill],
    capabilities=[chat_capability],
)
```

### 3. 配置通信协议

```python
from usmsb_sdk import ProtocolConfig, ProtocolType

# HTTP 协议
http_config = ProtocolConfig(
    protocol_type=ProtocolType.HTTP,
    endpoint="http://localhost:8000",
    enabled=True,
)

# WebSocket 协议
ws_config = ProtocolConfig(
    protocol_type=ProtocolType.WEBSOCKET,
    endpoint="ws://localhost:8001",
    enabled=True,
)

# MCP 协议
mcp_config = ProtocolConfig(
    protocol_type=ProtocolType.MCP,
    endpoint="http://localhost:8002/sse",
    enabled=True,
)

# P2P 协议
p2p_config = ProtocolConfig(
    protocol_type=ProtocolType.P2P,
    endpoint="0.0.0.0:9000",
    enabled=True,
)

# 多协议配置
config = AgentConfig(
    agent_id="multi-protocol-agent",
    name="MultiProtocolAgent",
    protocols=[http_config, ws_config, mcp_config, p2p_config],
)
```

## 启动和注册 Agent

```python
async def main():
    # 创建 Agent
    agent = MyAgent(config)

    # 启动 Agent
    await agent.start()
    print(f"Agent {agent.name} is running")

    # 注册到平台
    registration_result = await agent.register(
        platform_endpoint="http://platform.example.com",
        protocol=ProtocolType.HTTP,
    )

    if registration_result.success:
        print("Registered successfully!")
    else:
        print(f"Registration failed: {registration_result.error}")

    # 执行技能
    result = await agent.call_skill("greet", {"name": "Alice"})
    print(f"Skill result: {result}")

    # 停止 Agent
    await agent.stop()

asyncio.run(main())
```

## Agent 间通信

### 发送消息

```python
# 发送消息给其他 Agent
message = await agent.send_message(
    target_agent_id="other-agent-001",
    content={"type": "request", "data": "Hello!"},
    protocol=ProtocolType.WEBSOCKET,
)
```

### 发现其他 Agent

```python
# 按技能发现
agents = await agent.discover_agents(
    skill_name="data_processing",
    min_reputation=0.8,
)

# 按能力发现
agents = await agent.discover_agents(
    capability="ml_inference",
    limit=10,
)

# 按关键词发现
agents = await agent.discover_agents(
    keywords=["nlp", "translation"],
)
```

## P2P 直连通信

```python
# 发现后建立 P2P 连接
target_agent = agents[0]

# 建立 P2P 连接
connection = await agent.establish_p2p_connection(
    target_agent_id=target_agent.agent_id,
    target_endpoint=target_agent.endpoint,
)

# 直接通信
response = await connection.send({
    "type": "direct_message",
    "content": "Hello via P2P!",
})
```

## Docker 部署

### 1. 创建 Agent 目录结构

```
my_agent/
├── agent.py
├── config.yaml
├── requirements.txt
└── Dockerfile
```

### 2. Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "-m", "agent", "--auto-register"]
```

### 3. 运行

```bash
# 构建镜像
docker build -t my-agent .

# 运行容器
docker run -d \
    -e PLATFORM_ENDPOINT=http://platform.example.com \
    -e AGENT_ID=my-agent-001 \
    my-agent
```

## 完整示例

参见 `demo/civilization_platform/supply_chain/` 目录下的供应链报价 Demo。

## 更多信息

- [API 参考](/docs/api-reference.md)
- [概念说明](/docs/concepts.md)
- [需求对接文档](/docs/agent_protocol_需求对接.md)
