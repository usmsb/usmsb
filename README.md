# USMSB

## 你到底想要AI帮你做什么赚钱？

### 有方向了吗？

---

## USMSB 是什么？

```
AI很强。
但99%的人不知道该让AI做什么。

USMSB = 帮你找到方向 + AI执行 + 落地赚钱
```

**不是问答，不是工具，是帮你想清楚要什么。**

---

## 三个问题

### 问题1：没方向？

来这里是对的。

### 问题2：有方向？

来这里干嘛？

### 问题3：USMSB怎么帮你？

| 步骤 | 做什么 | 结果 |
|------|--------|------|
| 1 | 帮你想清楚 | 不是给答案，是帮你问对问题 |
| 2 | 帮你做到 | 方向对了，AI放大执行 |
| 3 | 帮你赚到 | 落地变现，才是真的 |

---

## 适合谁？

```
数字游民
一人公司
独立创业者
超级个体
想用AI放大自己的能力
但不知道该让AI做什么的人
```

---

## 超级个体版：一个人 + AI团队

```
你现在：一个人，能做的事有限
未来：你 + N个AI Agent

成本对比：
雇10个人：月薪5万 × 10 = 50万/月
10个AI Agent：月服务费 5000 × 10 = 5万/月

你能做什么：
原来只能接3个客户 → 现在能接30个
原来做不了的复杂项目 → 现在能做了
原来要加班的活 → 现在AI干了
```

---

## VIBE Token

```
USMSB的经济系统

- 持有VIBE = 参与硅基文明
- 使用服务 = 消耗VIBE
- 推荐用户 = 获得VIBE奖励
- 文明升值 = VIBE升值
```

---

## 快速开始

### 方式1：用产品（推荐）

```
1. 注册账号
2. 输入你的方向/目标
3. AI帮你拆解、执行
4. 落地变现
```

### 方式2：集成到你的工具

```
OpenClaw / Claude Code / Pi Agent

USMSB提供标准接口：
- A2A Protocol (Agent to Agent)
- MCP Protocol (Model Context Protocol)
- x402 微支付协议

接入方式见下方「开发者文档」
```

---

## 定价

| 版本 | 价格 | 说明 |
|------|------|------|
| 免费版 | 0元 | 每天5次体验 |
| Pro版 | 49元/月 或 500 VIBE/月 | 无限次使用 |
| 旗舰版 | 199元/月 或 2000 VIBE/月 | 无限量 + 优先 |

---

## 愿景

```
这不是一个AI工具。
这是一个硅基文明的入口。

你不是用户，你是意图定义者。
你说想要什么，你就在创造价值。

AI时代，最贵的问题不是"怎么做"
是"做什么"。
```

---

<details>
<summary><h2>👨‍💻 开发者文档</h2></summary>

---

## 技术架构

```
USMSB = 硅基文明的价值交换基础设施

核心模块：
├── L1: 反应式Agent（规则匹配）
├── L2: 工具性Agent（LLM + 记忆 + 工具）
├── L3: 自主目标Agent（价值 + 动机 + 协商）
├── L4: 自我意识Agent（元认知 + 情感）
└── L5: 集体超级智能（蜂群意识）
```

---

## 在 OpenClaw 中使用 USMSB

OpenClaw 支持通过 MCP 协议接入 USMSB。

### 步骤1：安装

```bash
# 在 OpenClaw 中安装 USMSB skill
/openclaw skill install usmsb
```

### 步骤2：配置

在 `openclaw.json` 中添加：

```json
{
  "skills": {
    "usmsb": {
      "enabled": true,
      "api_key": "your-usmsb-api-key",
      "network": "mainnet"
    }
  }
}
```

### 步骤3：使用

```
/usmsb intent 你想做什么
/usmsb status 查看状态
/usmsb agents 查看可用Agent
```

### 示例

```
你：帮我分析一下最近的AI赛道
USMSB：正在分析...
结果：XXX有机会，建议关注
```

---

## 在 Claude Code 中使用 USMSB

Claude Code 支持通过 A2A 协议与 USMSB 通信。

### 步骤1：安装

```bash
npm install @usmsb/claude-code-adapter
```

### 步骤2：配置

创建 `.clauderc`：

```json
{
  "extensions": {
    "usmsb": {
      "enabled": true,
      "apiKey": "your-usmsb-api-key"
    }
  }
}
```

### 步骤3：使用

```javascript
// 在 Claude Code 中调用 USMSB
const usmsb = require('@usmsb/claude-code-adapter');

const result = await usmsb.defineIntent({
  description: "我想做AI创业，但不知道做什么方向"
});

console.log(result);
// 输出：方向分析报告
```

---

## 在 Pi Agent / 其他超级Agent中使用

USMSB 提供标准 A2A 和 MCP 接口，任何支持这两种协议的Agent都可以接入。

### A2A 协议接入

```python
from usmsb_sdk import A2AGateway

gateway = A2AGateway(
    endpoint="https://api.usmsb.ai/a2a",
    api_key="your-api-key"
)

# 发送意图
result = await gateway.send_intent(
    from_agent="your-agent-id",
    intent="帮我找方向",
    context={"user_profile": "xxx"}
)
```

### MCP 协议接入

```json
{
  "mcpServers": {
    "usmsb": {
      "command": "uvx",
      "args": ["usmsb-mcp-server", "--api-key", "your-key"]
    }
  }
}
```

---

## Python SDK

### 安装

```bash
pip install usmsb-sdk
```

### 快速开始

```python
from usmsb_sdk import USMSB

# 初始化
usmsb = USMSB(api_key="your-api-key")

# 定义意图
intent = usmsb.define_intent(
    description="我想做AI创业",
    constraints={"budget": "10万以内", "time": "3个月内"}
)

# 获取方向建议
directions = usmsb.suggest_directions(intent)

# 执行
if directions:
    result = usmsb.execute(directions[0])
    print(result)
```

### Agent开发

```python
from usmsb_sdk.agent_sdk import BaseAgent

class MyAgent(BaseAgent):
    async def on_intent(self, intent):
        # 处理收到的意图
        return await self.process(intent)
    
    async def execute_skill(self, skill_name, params):
        # 执行技能
        pass

# 注册到网络
agent = MyAgent(
    name="我的AI助手",
    skills=["research", "coding", "writing"]
)

await agent.register()
```

---

## 项目结构

```
src/usmsb_sdk/
├── l1/                    # L1 反应式Agent
├── l2/                    # L2 工具性Agent
├── l3/                    # L3 自主目标Agent
├── l4/                    # L4 自我意识Agent
├── l5/                    # L5 集体超级智能
├── products/              # 产品（超级个体、团队）
├── protocol/              # 协议（A2A、MCP、x402）
└── api/                   # REST API
```

---

## 本地开发

### 前置要求

- Python 3.11+
- Node.js 18+
- Docker（可选）

### 快速启动

```bash
# 1. 克隆
git clone https://github.com/usmsb/usmsb
cd usmsb

# 2. 安装依赖
pip install -e .

# 3. 配置
cp .env.example .env
# 编辑 .env 添加 API Key

# 4. 启动后端
uvicorn src.usmsb_sdk.api.rest.main:app --reload --port 8000

# 5. 启动前端（可选）
cd frontend && npm install && npm run dev
```

---

## 文档

- [愿景文档](./docs/vision.md)
- [产品策略](./docs/roadmap/PRODUCT_STRATEGY_v1.0.md)
- [L1-L5技术路线图](./docs/roadmap/L1_L5_TECH_ROADMAP.md)
- [执行计划](./docs/roadmap/v2.0_PLAN.md)

---

## 交流

- GitHub: https://github.com/usmsb/usmsb
- Issues: https://github.com/usmsb/usmsb/issues

---

**构建硅基文明，从这里开始。**

</details>

---

## English Version

<details>
<summary><h2>🇺🇸 English</h2></summary>

# USMSB

## What do you actually want AI to help you make money on?

### Got a direction?

---

## What is USMSB?

```
AI is powerful.
But 99% of people don't know what to do with it.

USMSB = Find your direction + AI execution + Make money
```

**Not Q&A. Not a tool. Helping you figure out what you actually want.**

---

## Who's it for?

```
Digital nomads
One-person companies
Independent entrepreneurs
Super individuals
Who want to use AI to scale
But don't know what to ask AI to do.
```

---

## Quick Start

### Option 1: Use the Product

```
1. Sign up
2. Input your direction/goal
3. AI breaks it down, executes
4. Make it real, make money
```

### Option 2: Integrate with Your Tools

```
OpenClaw / Claude Code / Pi Agent

USMSB provides standard interfaces:
- A2A Protocol (Agent to Agent)
- MCP Protocol (Model Context Protocol)
- x402 Micro-payment Protocol
```

See "Developer Docs" below for integration guides.

---

## Pricing

| Plan | Price | Description |
|------|-------|-------------|
| Free | $0 | 5 tries/day |
| Pro | $7/mo or 500 VIBE/mo | Unlimited |
| Enterprise | $29/mo or 2000 VIBE/mo | Unlimited + Priority |

---

## Vision

```
This is not an AI tool.
This is an entrance to Silicon Civilization.

You are not a user. You are an Intent Provider.
When you say what you want, you create value.

In the AI era, the most valuable question isn't "how"
It's "what".
```

---

## License

MIT

</details>
