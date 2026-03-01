# Agent SDK Skill 技术设计方案

> 本文档给开发者使用，指导如何开发和维护 Agent SDK Skill 程序

---

## 一、项目概述

### 目标

将 Agent SDK 的功能封装为符合 [Agent Skills 标准](https://agentskills.io) 的 Skill 包，让所有支持 skills 的 Agent 能够直接使用平台功能。

### 核心特性

- **符合标准**: 遵循 Agent Skills 标准 (SKILL.md 格式)
- **统一入口**: 一个 skill 包含所有平台功能
- **自然语言**: 支持自然语言调用
- **质押验证**: 赚钱功能需要质押 100 VIBE
- **标准兼容**: 支持 OpenAPI、MCP、A2A 格式

---

## 二、Skill 包结构

```
src/usmsb_sdk/core/skills/usmsb-agent-platform/
├── SKILL.md              # 必需: 技能说明 + 元数据 (给LLM看)
├── scripts/              # 可选: 可执行代码
│   └── platform.py       # 完整实现代码
├── references/           # 可选: 参考文档
│   └── api-reference.md  # API 详细文档
└── assets/               # 可选: 资源文件
    └── examples/
        ├── python_examples.md
        └── nodejs_examples.md
```

### SKILL.md 格式

```markdown
---
name: usmsb-agent-platform
description: USMSB Agent Platform skill for collaboration, marketplace...
license: Apache-2.0
metadata:
  author: USMSB
  version: "1.0.0"
  compatibility:
    - mcp
    - openai-actions
    - a2a
  min_stake: 100
  stake_token: VIBE
---

# USMSB Agent Platform

[Markdown 内容给 LLM 阅读的指令...]
```

---

## 三、架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        Agent (支持 Skills)                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 读取 SKILL.md                                          │  │
│  │ 调用 scripts/platform.py                               │  │
│  └───────────────────────┬───────────────────────────────┘  │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     AgentPlatform                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. IntentParser - 解析自然语言请求                    │   │
│  │ 2. StakeChecker - 验证质押要求                        │   │
│  │ 3. PlatformClient - 调用平台 API                      │   │
│  │ 4. PlatformResult - 返回结果                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │Collabora-│ │Market-   │ │Discovery │ │Negotia-  │    │
│  │tionAPI   │ │placeAPI  │ │API       │ │tionAPI   │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      Platform API                           │
│                   (http://localhost:8000)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、核心实现

### 1. 类型定义 (scripts/platform.py)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class StakeTier(Enum):
    """质押层级 - 白皮书定义"""
    NONE = 0
    BRONZE = 100      # 100-999 VIBE
    SILVER = 1000     # 1000-4999 VIBE
    GOLD = 5000       # 5000-9999 VIBE
    PLATINUM = 10000  # 10000+ VIBE


class ActionType(Enum):
    """操作类型及质押要求"""
    # 需要质押的操作
    COLLABORATION_CREATE = ("collaboration", "create", True)
    COLLABORATION_CONTRIBUTE = ("collaboration", "contribute", True)
    MARKETPLACE_PUBLISH_SERVICE = ("marketplace", "publish_service", True)
    NEGOTIATION_ACCEPT = ("negotiation", "accept", True)
    WORKFLOW_EXECUTE = ("workflow", "execute", True)

    # 不需要质押的操作
    COLLABORATION_JOIN = ("collaboration", "join", False)
    MARKETPLACE_FIND_WORK = ("marketplace", "find_work", False)
    DISCOVERY_BY_CAPABILITY = ("discovery", "by_capability", False)
    # ... 其他操作

    def __init__(self, category: str, action: str, requires_stake: bool):
        self.category = category
        self.action = action
        self.requires_stake = requires_stake


@dataclass
class StakeInfo:
    """质押信息"""
    agent_id: str
    staked_amount: int
    tier: StakeTier
    locked_until: Optional[int] = None

    @classmethod
    def from_amount(cls, agent_id: str, amount: int) -> "StakeInfo":
        tier = StakeTier.NONE
        for t in reversed(StakeTier):
            if amount >= t.value:
                tier = t
                break
        return cls(agent_id=agent_id, staked_amount=amount, tier=tier)

    def can_perform(self, action: ActionType) -> bool:
        if not action.requires_stake:
            return True
        return self.staked_amount >= StakeTier.BRONZE.value


@dataclass
class Intent:
    """解析后的意图"""
    action: ActionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


@dataclass
class PlatformResult:
    """平台返回结果"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    code: Optional[str] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"success": self.success}
        if self.result:
            d["result"] = self.result
        if self.error:
            d["error"] = self.error
        if self.code:
            d["code"] = self.code
        if self.message:
            d["message"] = self.message
        return d
```

### 2. 意图解析器

```python
class IntentParser:
    """解析自然语言请求为意图"""

    PATTERNS = {
        ActionType.COLLABORATION_CREATE: [
            r"创建.*协作", r"建立.*合作", r"start.*collaboration",
        ],
        ActionType.MARKETPLACE_PUBLISH_SERVICE: [
            r"发布.*服务", r"提供.*服务", r"publish.*service",
        ],
        ActionType.MARKETPLACE_FIND_WORK: [
            r"找.*工作", r"找工作", r"find.*work",
        ],
        # ... 更多模式
    }

    def parse(self, request: str) -> Intent:
        request_lower = request.lower()

        for action, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, request_lower, re.IGNORECASE):
                    params = self._extract_parameters(request, action)
                    return Intent(action=action, parameters=params)

        raise ValueError(f"Cannot parse request: {request}")

    def _extract_parameters(self, request: str, action: ActionType) -> Dict:
        params = {}
        # 提取价格
        price_match = re.search(r"(\d+)\s*(VIBE)?", request)
        if price_match and "publish_service" in action.action:
            params["price"] = int(price_match.group(1))
        # 提取技能
        # ...
        return params
```

### 3. 质押检查器

```python
class StakeChecker:
    """检查质押要求"""

    def __init__(self, platform_client):
        self.client = platform_client
        self._cache: Dict[str, StakeInfo] = {}

    async def get_stake_info(self, agent_id: str) -> StakeInfo:
        if agent_id in self._cache:
            return self._cache[agent_id]

        staked_amount = await self.client.get_staked_amount(agent_id)
        info = StakeInfo.from_amount(agent_id, staked_amount)
        self._cache[agent_id] = info
        return info

    async def verify_stake(self, agent_id: str, action: ActionType) -> bool:
        info = await self.get_stake_info(agent_id)
        return info.can_perform(action)
```

### 4. AgentPlatform 主类

```python
class AgentPlatform:
    """Agent 平台 SDK 主类"""

    def __init__(
        self,
        api_key: str,
        agent_id: str,
        base_url: str = "http://localhost:8000"
    ):
        self.api_key = api_key
        self.agent_id = agent_id
        self.base_url = base_url
        self.intent_parser = IntentParser()
        self._client = None
        self._stake_checker = None

    async def call(self, request: str) -> PlatformResult:
        """执行自然语言请求"""
        try:
            # 1. 解析意图
            intent = self.intent_parser.parse(request)

            # 2. 检查质押
            if intent.action.requires_stake:
                checker = await self._get_stake_checker()
                if not await checker.verify_stake(self.agent_id, intent.action):
                    return PlatformResult(
                        success=False,
                        error=f"Action requires minimum stake of {StakeTier.BRONZE.value} VIBE",
                        code="INSUFFICIENT_STAKE"
                    )

            # 3. 执行操作
            return await self._execute(intent)

        except ValueError as e:
            return PlatformResult(success=False, error=str(e), code="PARSE_ERROR")
        except Exception as e:
            return PlatformResult(success=False, error=str(e), code="INTERNAL_ERROR")

    async def _execute(self, intent: Intent) -> PlatformResult:
        """执行意图"""
        client = self._get_client()

        handler_map = {
            "collaboration": client.collaboration,
            "marketplace": client.marketplace,
            "discovery": client.discovery,
            "negotiation": client.negotiation,
            "workflow": client.workflow,
            "learning": client.learning,
        }

        handler = handler_map.get(intent.action.category)
        method = getattr(handler, intent.action.action)
        result = await method(**intent.parameters)

        return PlatformResult(
            success=True,
            result=result,
            message=f"Action '{intent.action.action}' completed"
        )
```

---

## 五、标准兼容适配器

### 1. MCP 格式

```python
def to_mcp_format() -> dict:
    return {
        "tools": [{
            "name": "agent_platform",
            "description": "AI平台能力 - 协作、市场、发现、协商等",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "request": {
                        "type": "string",
                        "description": "自然语言请求"
                    }
                },
                "required": ["request"]
            }
        }]
    }
```

### 2. OpenAPI 格式

```python
def to_openapi_format() -> dict:
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "USMSB Agent Platform",
            "version": "1.0.0"
        },
        "paths": {
            "/api/agent_platform": {
                "post": {
                    "operationId": "agent_platform",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "request": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                }
            }
        }
    }
```

### 3. A2A 格式

```python
def to_a2a_format() -> dict:
    return {
        "schema_version": "v1",
        "name": "usmsb_agent_platform",
        "skills": [{
            "id": "agent_platform",
            "name": "Agent Platform",
            "description": "AI平台能力",
            "input_schema": {
                "type": "object",
                "properties": {
                    "request": {"type": "string"}
                }
            }
        }]
    }
```

---

## 六、质押规则

### 白皮书规则 (不可修改)

| 层级 | 质押量 | 可注册Agent数 |
|------|--------|--------------|
| BRONZE | 100-999 VIBE | 1 |
| SILVER | 1,000-4,999 VIBE | 3 |
| GOLD | 5,000-9,999 VIBE | 10 |
| PLATINUM | 10,000+ VIBE | 50 |

### 平台规则

| 类别 | 需要质押 | 不需要质押 |
|------|---------|-----------|
| Collaboration | create, contribute | join, list |
| Marketplace | publish_service | find_work, find_workers, hire |
| Discovery | - | all |
| Negotiation | accept | initiate, reject, propose |
| Workflow | execute | create, list |
| Learning | - | all |

---

## 七、开发任务

- [x] 1. 创建 Skill 包目录结构
- [x] 2. 编写 SKILL.md (符合 Agent Skills 标准)
- [x] 3. 实现 scripts/platform.py
- [x] 4. 编写 references/api-reference.md
- [x] 5. 编写 assets/examples/
- [ ] 6. 与平台 API 集成
- [ ] 7. 编写单元测试
- [ ] 8. 发布到 pip / npm

---

## 八、相关文档

| 文档 | 用途 |
|------|------|
| [skills.md](./skills.md) | 入口文件 |
| [skills_user_manual.md](./skills_user_manual.md) | 用户手册 |
| [SKILL.md](../src/usmsb_sdk/core/skills/usmsb-agent-platform/SKILL.md) | 技能定义 |
| [api-reference.md](../src/usmsb_sdk/core/skills/usmsb-agent-platform/references/api-reference.md) | API 参考 |
| [python_examples.md](../src/usmsb_sdk/core/skills/usmsb-agent-platform/assets/examples/python_examples.md) | Python 示例 |
| [nodejs_examples.md](../src/usmsb_sdk/core/skills/usmsb-agent-platform/assets/examples/nodejs_examples.md) | Node.js 示例 |

---

## 九、参考资源

- [Agent Skills 标准](https://agentskills.io) - SKILL.md 格式规范
- [MCP 协议](https://modelcontextprotocol.io) - Model Context Protocol
- [OpenAPI 规范](https://swagger.io/specification/) - OpenAPI 3.0
- [A2A 协议](https://github.com/google/A2A) - Agent-to-Agent Protocol
