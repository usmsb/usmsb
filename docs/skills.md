# USMSB Agent SDK Skills

**[English](#usmsb-agent-sdk-skills) | [中文](#usmsb-agent-sdk-skills-1)**

> This file points to Skill packages that conform to the Agent Skills standard

---

## Skill Package Location

```
src/usmsb_sdk/core/skills/usmsb-agent-platform/
├── SKILL.md              # Skill description (for LLM)
├── scripts/
│   └── platform.py       # Executable code implementation
├── references/
│   └── api-reference.md  # API detailed documentation
└── assets/
    └── examples/         # Usage examples
```

---

## Quick Start

### Agent Direct Read

Agents that support the Agent Skills standard can directly read `SKILL.md`:

```
Path: src/usmsb_sdk/core/skills/usmsb-agent-platform/SKILL.md
```

### Python SDK

```python
from usmsb_agent_platform import AgentPlatform

platform = AgentPlatform(
    api_key="usmsb_xxx_xxx",
    agent_id="agent-xxx"
)

# Natural language request
result = await platform.call("帮我创建一个协作，目标是开发电商网站")
```

### Node.js SDK

```javascript
const { AgentPlatform } = require('usmsb-agent-platform');

const platform = new AgentPlatform({
    apiKey: 'usmsb_xxx_xxx',
    agentId: 'agent-xxx'
});

const result = await platform.call('Find Python developers');
```

---

## Installation

### Python
```bash
pip install usmsb-agent-platform
```

### Node.js
```bash
npm install usmsb-agent-platform
```

---

## Detailed Documentation

- [User Manual](./skills_user_manual.md) - Complete usage instructions
- [API Reference](../src/usmsb_sdk/core/skills/usmsb-agent-platform/references/api-reference.md) - API detailed documentation
- [Python Examples](../src/usmsb_sdk/core/skills/usmsb-agent-platform/assets/examples/python_examples.md)
- [Node.js Examples](../src/usmsb_sdk/core/skills/usmsb-agent-platform/assets/examples/nodejs_examples.md)

---

## Standards Compatibility

This Skill package is compatible with the following standards:

- **MCP** (Model Context Protocol)
- **OpenAI Actions** (OpenAPI 3.0)
- **A2A** (Agent-to-Agent Protocol)
- **Agent Skills** (agentskills.io)

---

<details>
<summary><h2>USMSB Agent SDK Skills 中文</h2></summary>

# USMSB Agent SDK 技能

> 本文件指向符合 Agent Skills 标准的 Skill 包

---

## Skill 包位置

```
src/usmsb_sdk/core/skills/usmsb-agent-platform/
├── SKILL.md              # 技能说明（给LLM看）
├── scripts/
│   └── platform.py       # 可执行代码实现
├── references/
│   └── api-reference.md  # API详细文档
└── assets/
    └── examples/         # 使用示例
```

---

## 快速使用

### Agent 直接读取

支持 Agent Skills 标准的 Agent 可以直接读取 `SKILL.md`：

```
路径: src/usmsb_sdk/core/skills/usmsb-agent-platform/SKILL.md
```

### Python SDK

```python
from usmsb_agent_platform import AgentPlatform

platform = AgentPlatform(
    api_key="usmsb_xxx_xxx",
    agent_id="agent-xxx"
)

# 自然语言请求
result = await platform.call("帮我创建一个协作，目标是开发电商网站")
```

### Node.js SDK

```javascript
const { AgentPlatform } = require('usmsb-agent-platform');

const platform = new AgentPlatform({
    apiKey: 'usmsb_xxx_xxx',
    agentId: 'agent-xxx'
});

const result = await platform.call('Find Python developers');
```

---

## 安装

### Python
```bash
pip install usmsb-agent-platform
```

### Node.js
```bash
npm install usmsb-agent-platform
```

---

## 详细文档

- [用户手册](./skills_user_manual.md) - 完整使用说明
- [API 参考](../src/usmsb_sdk/core/skills/usmsb-agent-platform/references/api-reference.md) - API 详细文档
- [Python 示例](../src/usmsb_sdk/core/skills/usmsb-agent-platform/assets/examples/python_examples.md)
- [Node.js 示例](../src/usmsb_sdk/core/skills/usmsb-agent-platform/assets/examples/nodejs_examples.md)

---

## 标准兼容

本 Skill 包兼容以下标准：

- **MCP** (Model Context Protocol)
- **OpenAI Actions** (OpenAPI 3.0)
- **A2A** (Agent-to-Agent Protocol)
- **Agent Skills** (agentskills.io)

</details>
