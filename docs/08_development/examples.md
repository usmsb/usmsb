# 示例代码

> USMSB SDK 示例代码

---

## 1. Agent 对话

```python
from usmsb_sdk import USMSBClient

client = USMSBClient(api_key="your_api_key")

# 简单对话
response = await client.chat.send(
    message="帮我写一个Python函数"
)
print(response.content)
```

---

## 2. 创建自定义 Agent

```python
from usmsb_sdk import AgentBuilder

agent = (
    AgentBuilder("my_agent")
    .capabilities(["text", "code"])
    .tools(["python", "web_search"])
    .build()
)

await agent.register()
```

---

## 3. 多 Agent 协作

```python
from usmsb_sdk import Collaboration

collaboration = Collaboration()

# 创建任务组
task = await collaboration.create_task(
    name="数据分析",
    agents=["analyzer", "visualizer", "reporter"]
)

# 执行
result = await task.execute(data)
```

---

## 4. 相关文档

- [快速开始](./quickstart.md) - 快速入门
- [Python SDK](../06_api/python_sdk.md) - SDK详细用法
