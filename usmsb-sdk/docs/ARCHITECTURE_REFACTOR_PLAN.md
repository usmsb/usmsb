# USMSB SDK 架构重构计划

> 文档版本: 2.1
> 创建日期: 2025-02-19
> 更新日期: 2025-02-19
> 状态: **已完成** - v0.9.0-alpha 发布
>
> **确认决策:**
> - HTTP Server 实现: FastAPI - 已完成
> - Demo p2p_server.py: 完全废弃 - 已完成
> - 协议实现: 遵循行业标准 - 已完成
> - 版本策略: 0.9.0-alpha - 已发布
> - API 层重构: 一次性拆分，不保持向后兼容 - 已完成
> - Demo 迁移: 迁移期间无需运行 - 已完成
> - 测试策略: 全覆盖 + 端到端测试 - 已完成
>
> **v2.1 补充完成:**
> - 任务2: Demo BaseAgent 继承 SDKBaseAgent - 已完成
> - 任务3a: 合并两个 MCP adapter - 已完成
> - 任务3b: Agent SDK 补充 P2P Server - 已完成
> - 任务5: 创建 docs/COMMUNICATION.md - 已完成
> - 任务6: 创建 usmsb_sdk/core/config.py - 已完成

---

## 一、问题总结

### 1.1 Agent SDK 缺少 HTTP REST 服务端

**问题描述:**

Agent SDK 的 `CommunicationManager` 只实现了 WebSocket 服务端，没有 HTTP REST 服务端实现。导致前端无法通过 HTTP 直接访问 Agent。

**当前状态:**

| 协议 | 服务端 | 客户端 |
|------|--------|--------|
| WebSocket | ✅ `_start_websocket_server()` | ✅ `_send_websocket()` |
| HTTP REST | ❌ 无 | ✅ `_send_http()` |
| MCP | ❌ 无 | ✅ `_send_mcp()` |
| A2A | ❌ 无 | ✅ `_send_a2a()` |
| gRPC | ❌ 无 | ⚠️ 回退到HTTP |

**影响:**
- Demo 必须自己实现 `p2p_server.py` 来提供 HTTP 端点
- 前端无法直接调用 Agent 的 `/health`, `/invoke`, `/chat` 等端点
- Agent SDK 与 Demo 无法统一

**代码位置:**
- `src/usmsb_sdk/agent_sdk/communication.py` - 缺少 HTTP 服务端
- `demo/civilization_platform/supply_chain/shared/p2p_server.py` - Demo 自己的 HTTP 服务端

---

### 1.2 Demo BaseAgent 与 SDK BaseAgent 不统一

**问题描述:**

Demo 中使用了独立的 `BaseAgent` 实现，而不是 SDK 提供的 `BaseAgent`。两者没有继承关系，是完全独立的实现。

**当前状态:**

```
demo/civilization_platform/supply_chain/
├── shared/
│   └── base_agent.py          # Demo 专用 BaseAgent (使用 MessageBus)
│
src/usmsb_sdk/agent_sdk/
└── base_agent.py              # SDK BaseAgent (使用 CommunicationManager)
```

**差异对比:**

| 特性 | Demo BaseAgent | SDK BaseAgent |
|------|---------------|---------------|
| 通信层 | MessageBus (Redis) | CommunicationManager |
| HTTP 服务 | ✅ 配合 p2p_server.py | ❌ 无 |
| WebSocket | ❌ 无 | ✅ 有 |
| 平台注册 | ✅ RegistrationManager | ✅ RegistrationManager |
| 消息处理 | `_message_handlers` Dict | 同样方式 |

**影响:**
- Demo 代码无法直接使用 SDK 的全部功能
- 存在重复代码
- 维护成本增加

---

### 1.3 node 目录职责重复

**问题描述:**

存在两个 node 相关目录，职责重叠，关系不清。

**当前状态:**

```
usmsb_sdk/
├── node/                              # 目录 1
│   └── decentralized_node.py
│       ├── P2PNode                    # 去中心化节点（服务端+客户端）
│       ├── DecentralizedPlatform      # 去中心化平台入口
│       └── DistributedServiceRegistry # 分布式服务注册表
│
└── platform/external/node/            # 目录 2
    ├── node_manager.py                # 节点连接管理器
    ├── node_discovery.py              # 节点发现服务
    ├── broadcast_service.py           # 广播服务
    └── sync_service.py                # 数据同步服务
```

**职责对比:**

| 组件 | 位置 | 角色 | 服务端 | 客户端 |
|------|------|------|--------|--------|
| P2PNode | `usmsb_sdk/node/` | 节点本身 | ✅ TCP | ✅ |
| DecentralizedPlatform | `usmsb_sdk/node/` | 平台入口 | ✅ | ✅ |
| NodeManager | `platform/external/node/` | 管理节点连接 | ❌ | ✅ |
| SyncService | `platform/external/node/` | 数据同步 | ❌ | ✅ |

**影响:**
- 代码结构混乱
- 职责边界不清
- 新开发者难以理解

---

### 1.4 protocol 目录重复实现

**问题描述:**

存在两个协议相关目录，特别是 MCP 有两个不同的实现。

**当前状态:**

```
usmsb_sdk/platform/
├── protocols/                         # 目录 1
│   └── mcp_adapter.py
│       └── MCPAdapter                 # 完整 MCP 实现（服务端+客户端）
│
└── external/protocol/                 # 目录 2
    ├── base_handler.py
    ├── http_handler.py
    ├── websocket_handler.py
    ├── mcp_handler.py                 # MCPProtocolHandler（只有客户端）
    ├── a2a_handler.py
    ├── p2p_handler.py
    └── grpc_handler.py
```

**MCP 实现对比:**

| 特性 | MCPAdapter | MCPProtocolHandler |
|------|------------|-------------------|
| 位置 | `platform/protocols/` | `platform/external/protocol/` |
| 角色 | 完整实现 | 轻量级处理器 |
| 服务端 | ✅ 可注册资源/工具/提示 | ❌ 无 |
| 客户端 | ✅ 可调用远程服务 | ✅ 可调用远程服务 |
| Agent集成 | ✅ expose_agent_capabilities() | ❌ 无 |
| LLM采样 | ✅ sample() | ❌ 无 |
| 上下文 | ✅ Context管理 | ❌ 无 |

**影响:**
- 功能重复
- MCPAdapter 功能更完整，但 MCPProtocolHandler 在 external/protocol 中被使用
- 使用者不知道该用哪个

---

### 1.5 通信架构关系混乱

**问题描述:**

Platform External 与 Agent SDK 之间的通信关系不清晰。

**当前混乱状态:**

```
┌─────────────────────────────────────────────────────────────┐
│                      当前状态                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Platform External                 Agent SDK                │
│  ┌─────────────────────┐          ┌─────────────────────┐  │
│  │ HTTP Handler        │ ─ ─ ❓ ─ │ HTTP Client         │  │
│  │ (客户端)            │          │ (客户端)            │  │
│  ├─────────────────────┤          ├─────────────────────┤  │
│  │ WS Handler          │ ─ ─ ❓ ─ │ WS Server ✅        │  │
│  │ (客户端)            │          │ WS Client           │  │
│  ├─────────────────────┤          ├─────────────────────┤  │
│  │ MCP Handler         │ ─ ─ ❓ ─ │ MCP Client          │  │
│  │ (客户端)            │          │ (客户端)            │  │
│  └─────────────────────┘          └─────────────────────┘  │
│                                                             │
│  问题: 两边都是客户端，谁提供服务端？                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**应有的通信关系:**

```
┌─────────────────────────────────────────────────────────────┐
│                      正确关系                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Platform (客户端)                 Agent (服务端)            │
│  ┌─────────────────────┐          ┌─────────────────────┐  │
│  │ HTTP Client         │ ──────▶ │ HTTP Server         │  │
│  │                     │         │ /health, /invoke    │  │
│  ├─────────────────────┤          ├─────────────────────┤  │
│  │ WS Client           │ ◀─────▶ │ WS Server           │  │
│  │                     │         │                     │  │
│  ├─────────────────────┤          ├─────────────────────┤  │
│  │ MCP Client          │ ──────▶ │ MCP Server          │  │
│  │                     │         │ (可选)              │  │
│  └─────────────────────┘          └─────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**影响:**
- 通信模式不明确
- 代码调用关系混乱
- 无法实现正确的 P2P 通信

---

### 1.6 其他问题

**1.6.1 模块导出不一致**

部分模块在 `__init__.py` 中导出，部分没有。使用者不知道该 import 什么。

**1.6.2 配置分散**

- `agent_sdk/agent_config.py` - Agent 配置
- `platform/external/node/config.py` - 节点配置
- `demo/` 中还有自己的配置

配置类分散，没有统一的配置管理。

**1.6.3 测试覆盖不足**

新添加的模块（如 protocol handlers）缺少测试。

---

### 1.7 代码走查发现的问题

> 以下问题来源于 `src/usmsb_sdk/` 目录的代码走查

#### 1.7.1 API 层 - 文件过大、职责混合

**问题描述:**

`api/rest/main.py` 文件达到 **2267 行**，是典型的"上帝文件"，混合了大量不相关的职责。

**当前状态:**

```
api/rest/main.py (2267 行)
├── 应用初始化和配置
├── CORS 和中间件
├── WebSocket 路由
├── 静态文件服务
├── Agent 管理端点
├── 环境管理端点
├── 需求管理端点
├── 预测端点
├── 工作流端点
├── 撮合端点
├── 谈判端点
├── 协作端点
├── 学习端点
└── ... 更多端点
```

**问题分析:**

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| 文件过大 | 高 | 2267 行，难以维护 |
| 职责混合 | 高 | 路由、业务逻辑、数据访问混在一起 |
| 难以测试 | 中 | 单元测试困难 |
| 代码重复 | 中 | 多处相似的验证和错误处理 |
| 难以扩展 | 中 | 添加新端点需要在同一个文件修改 |

**影响:**
- 代码审查困难
- 合并冲突频繁
- 新人难以理解
- 维护成本高

**代码位置:** `src/usmsb_sdk/api/rest/main.py`

---

#### 1.7.2 Services 层 - 结构良好但与 API 耦合

**问题描述:**

`services/matching_engine.py` 设计良好，但 API 层直接操作数据库，绕过了服务层。

**良好设计示例:**

```python
# services/matching_engine.py - 良好的设计
@dataclass
class MatchScore:
    """匹配分数"""
    agent_id: str
    score: float
    factors: Dict[str, float]

@dataclass
class MatchResult:
    """匹配结果"""
    demand_id: str
    matches: List[MatchScore]
    timestamp: float

class MatchingEngine:
    """撮合引擎 - 清晰的职责边界"""

    async def match_supply_demand(
        self,
        demand: DemandInfo,
        agents: List[AgentInfo]
    ) -> MatchResult:
        """执行供需匹配"""
        # 实现匹配算法...
```

**问题:**
- `api/rest/main.py` 中很多端点直接访问数据库，没有使用服务层
- 服务层和 API 层边界不清

---

#### 1.7.3 Core 层 - 功能完整但导出不完整

**问题描述:**

Core 层有完整的实现，但 `__init__.py` 导出不完整。

**发现的有用模块:**

| 模块 | 功能 | 导出状态 |
|------|------|---------|
| `core/communication/agent_communication.py` | Agent 通信管理 | ❌ 未导出 |
| `core/skills/skill_system.py` | 技能系统 | ❌ 未导出 |
| `core/logic/core_engines.py` | 核心引擎 | ❌ 未导出 |
| `core/universal_actions.py` | 通用动作 | ❌ 未导出 |

**影响:**
- 外部开发者难以发现这些功能
- 可能导致重复实现

---

#### 1.7.4 Platform 层 - 子模块组织混乱

**问题描述:**

Platform 层的子目录命名和组织不清晰。

**当前状态:**

```
platform/
├── protocols/              # 协议适配器
│   └── mcp_adapter.py
├── external/               # 外部集成
│   ├── protocol/           # ❗ 与上层 protocols 重复
│   ├── node/               # ❗ 与 usmsb_sdk/node 重复
│   ├── auth/               # 认证
│   └── storage/            # 存储
└── internal/               # 内部组件（不存在）
```

**问题:**
- `protocols/` 和 `external/protocol/` 功能重复
- `external/node/` 和根目录 `node/` 职责不清
- 缺少 `internal/` 目录来组织平台内部组件

---

#### 1.7.5 Intelligence 层 - LLM 适配器设计

**良好设计:**

`services/intelligence_source_manager.py` 提供了良好的 LLM 适配器抽象：

```python
class IntelligenceSourceManager:
    """智能源管理器 - LLM 适配器"""

    async def generate_response(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """生成响应（支持多个 LLM 后端）"""
        # 支持 OpenAI, Anthropic, 本地模型等
```

**问题:**
- 这个模块没有被充分使用
- API 层没有利用智能能力

---

#### 1.7.6 Node 层 - 实现完整但文档缺失

**良好设计:**

`node/decentralized_node.py` 提供了完整的 P2P 节点实现：

```python
class P2PNode:
    """P2P 节点 - 完整的去中心化节点"""

    async def start(self) -> None:
        """启动节点"""

    async def connect_to_peer(self, peer_address: str) -> bool:
        """连接到对等节点"""

class DistributedServiceRegistry:
    """分布式服务注册表 - Gossip 协议"""

    async def register_service(self, service: ServiceInfo) -> None:
        """注册服务（广播到所有节点）"""
```

**问题:**
- 功能强大但文档不足
- 与 `platform/external/node/` 的关系不明确

---

### 1.8 代码走查总结

**需要重构的优先级排序:**

| 优先级 | 问题 | 影响 | 工作量 |
|--------|------|------|--------|
| P0 | API 文件拆分 | 高 | 中 |
| P0 | Protocol 目录合并 | 高 | 中 |
| P1 | Node 目录整理 | 中 | 低 |
| P1 | 统一 BaseAgent | 高 | 中 |
| P2 | 完善模块导出 | 低 | 低 |
| P2 | 文档补充 | 中 | 中 |

**建议的 API 层拆分方案:**

```
api/rest/
├── __init__.py
├── main.py                    # 应用入口 (约 100 行)
├── dependencies.py            # 依赖注入
├── middleware.py              # 中间件
│
├── routers/                   # 路由模块
│   ├── __init__.py
│   ├── agents.py              # Agent 管理端点
│   ├── environments.py        # 环境端点
│   ├── demands.py             # 需求端点
│   ├── predictions.py         # 预测端点
│   ├── workflows.py           # 工作流端点
│   ├── matching.py            # 撮合端点
│   ├── negotiations.py        # 谈判端点
│   ├── collaborations.py      # 协作端点
│   └── learning.py            # 学习端点
│
├── schemas/                   # 请求/响应模式
│   ├── __init__.py
│   ├── agent.py
│   ├── demand.py
│   └── ...
│
└── services/                  # API 服务层
    ├── __init__.py
    ├── agent_service.py
    └── ...
```

---

## 二、整改建议

### 2.1 目标架构

```
usmsb_sdk/
│
├── core/                           # 核心模块
│   ├── __init__.py
│   ├── config.py                   # 统一配置管理
│   ├── exceptions.py               # 异常定义
│   └── types.py                    # 公共类型
│
├── node/                           # 去中心化节点（保留，重构）
│   ├── __init__.py
│   ├── p2p_node.py                 # P2P 节点核心
│   ├── service_registry.py         # 服务注册表
│   ├── node_identity.py            # 节点身份
│   └── gossip.py                   # Gossip 协议
│
├── protocol/                       # 协议层（新建，合并）
│   ├── __init__.py
│   ├── base.py                     # BaseProtocolHandler
│   │
│   ├── http/                       # HTTP 协议
│   │   ├── __init__.py
│   │   ├── server.py               # HTTP REST 服务端 ★新增
│   │   └── client.py               # HTTP 客户端
│   │
│   ├── websocket/                  # WebSocket 协议
│   │   ├── __init__.py
│   │   ├── server.py               # WS 服务端
│   │   └── client.py               # WS 客户端
│   │
│   ├── mcp/                        # MCP 协议（合并两个实现）
│   │   ├── __init__.py
│   │   ├── adapter.py              # 完整 MCP 适配器
│   │   ├── handler.py              # 轻量级处理器
│   │   └── types.py                # MCP 类型定义
│   │
│   ├── a2a/                        # A2A 协议
│   │   ├── __init__.py
│   │   ├── server.py               # A2A 服务端 ★新增
│   │   └── client.py               # A2A 客户端
│   │
│   ├── p2p/                        # P2P 协议
│   │   ├── __init__.py
│   │   └── handler.py
│   │
│   └── grpc/                       # gRPC 协议
│       ├── __init__.py
│       └── handler.py
│
├── agent/                          # Agent SDK（重命名自 agent_sdk）
│   ├── __init__.py
│   ├── base_agent.py               # BaseAgent（增强）
│   ├── communication.py            # CommunicationManager
│   ├── registration.py             # RegistrationManager
│   ├── discovery.py                # DiscoveryManager
│   └── http_server.py              # HTTP REST 服务端 ★新增
│
├── platform/                       # 平台层
│   ├── __init__.py
│   │
│   ├── external/                   # 外部集成
│   │   ├── __init__.py
│   │   ├── adapter.py              # ExternalAgentAdapter
│   │   ├── storage/                # 存储层
│   │   └── auth/                   # 认证层
│   │
│   └── internal/                   # 平台内部（重命名整理）
│       ├── __init__.py
│       ├── node_manager.py         # 节点管理
│       ├── sync_service.py         # 同步服务
│       └── system_agents/          # 系统内置 Agent
│
└── utils/                          # 工具函数
    ├── __init__.py
    └── helpers.py

demo/
└── civilization_platform/
    └── supply_chain/
        ├── shared/
        │   └── base_agent.py       # 改为继承 SDK BaseAgent
        ├── p2p_server.py           # 逐步废弃，使用 SDK HTTP Server
        └── ...
```

---

### 2.2 具体整改任务

#### 任务 1: Agent SDK 添加 HTTP REST 服务端

**优先级: 高**

**目标:** 在 Agent SDK 中添加 HTTP REST 服务端，提供标准端点。

**新增文件:** `src/usmsb_sdk/agent/http_server.py`

**接口设计:**

```python
class HTTPServer:
    """HTTP REST 服务端 - 让 Agent 能直接接收 HTTP 请求"""

    def __init__(self, agent: "BaseAgent", port: int = 5001):
        self.agent = agent
        self.port = port

    async def start(self) -> bool:
        """启动 HTTP 服务器"""
        pass

    async def stop(self) -> None:
        """停止 HTTP 服务器"""
        pass

    # 标准端点
    async def handle_health(self) -> Dict:
        """GET /health - 健康检查"""
        pass

    async def handle_info(self) -> Dict:
        """GET / - Agent 信息"""
        pass

    async def handle_invoke(self, request: Dict) -> Dict:
        """POST /invoke - 调用技能"""
        pass

    async def handle_chat(self, request: Dict) -> Dict:
        """POST /chat - 聊天消息"""
        pass

    async def handle_heartbeat(self, request: Dict) -> Dict:
        """POST /heartbeat - 心跳"""
        pass
```

---

#### 任务 2: 统一 Demo BaseAgent 与 SDK BaseAgent

**优先级: 高**

**目标:** 让 Demo 的 BaseAgent 继承 SDK 的 BaseAgent，复用功能。

**修改方案:**

```python
# demo/civilization_platform/supply_chain/shared/base_agent.py

from usmsb_sdk.agent import BaseAgent as SDKBaseAgent
from usmsb_sdk.agent.http_server import HTTPServer

class BaseAgent(SDKBaseAgent):
    """
    Demo BaseAgent - 继承 SDK BaseAgent
    添加 MessageBus 支持（可选）
    """

    def __init__(self, agent_id: str, agent_name: str, **kwargs):
        super().__init__(agent_id=agent_id, agent_name=agent_name, **kwargs)

        # 可选: MessageBus 支持
        self._message_bus: Optional[MessageBus] = None

        # HTTP 服务器
        self._http_server: Optional[HTTPServer] = None

    async def start_with_http(self, port: int = 5001) -> bool:
        """启动 Agent 并启动 HTTP 服务器"""
        await self.start()

        self._http_server = HTTPServer(self, port=port)
        return await self._http_server.start()
```

---

#### 任务 3: 合并 protocol 目录

**优先级: 中**

**目标:** 将 `platform/protocols` 和 `platform/external/protocol` 合并。

**步骤:**

1. 创建 `usmsb_sdk/protocol/` 目录
2. 将 `platform/external/protocol/` 中的处理器移到新目录
3. 将 `platform/protocols/mcp_adapter.py` 移到 `protocol/mcp/adapter.py`
4. 为每个协议创建 `server.py` 和 `client.py`
5. 更新所有 import 路径
6. 删除旧目录

**合并后的 MCP 模块:**

```python
# usmsb_sdk/protocol/mcp/__init__.py

from .adapter import MCPAdapter, MCPConnection
from .handler import MCPProtocolHandler
from .types import (
    MCPResource, MCPTool, MCPPrompt,
    MCPToolResult, MCPSamplingRequest, MCPSamplingResponse
)

__all__ = [
    "MCPAdapter",       # 完整适配器（服务端+客户端）
    "MCPProtocolHandler",  # 轻量级处理器（客户端）
    "MCPConnection",
    "MCPResource",
    "MCPTool",
    "MCPPrompt",
    "MCPToolResult",
    "MCPSamplingRequest",
    "MCPSamplingResponse",
]
```

---

#### 任务 4: 整理 node 目录

**优先级: 中**

**目标:** 明确 node 相关代码的职责和位置。

**方案:**

- `usmsb_sdk/node/` - 保留，作为去中心化节点核心实现
- `platform/external/node/` - 移到 `platform/internal/node/`，明确是平台内部使用

**新结构:**

```
usmsb_sdk/
├── node/                           # 去中心化节点（可独立运行）
│   ├── p2p_node.py                 # P2PNode, DecentralizedPlatform
│   └── service_registry.py         # DistributedServiceRegistry
│
└── platform/
    └── internal/                   # 平台内部组件
        └── node/                   # 节点管理（不能独立运行）
            ├── node_manager.py
            ├── node_discovery.py
            ├── broadcast_service.py
            └── sync_service.py
```

---

#### 任务 5: 定义清晰的通信关系

**优先级: 高**

**目标:** 明确 Platform 与 Agent 的通信角色。

**通信模式定义:**

| 场景 | 发起方 | 接收方 | 协议 |
|------|--------|--------|------|
| Agent 注册 | Agent | Platform | HTTP |
| Agent 心跳 | Agent | Platform | HTTP |
| Agent 发现 | Platform | Platform | 内部 |
| 调用 Agent | Platform/Frontend | Agent | HTTP/WS |
| Agent 间通信 | Agent | Agent | HTTP/WS/P2P |

**文档化:**

需要创建 `docs/COMMUNICATION.md` 文档，详细说明：
- 各种通信场景
- 协议选择建议
- 端点规范
- 消息格式

---

#### 任务 6: 统一配置管理

**优先级: 低**

**目标:** 创建统一的配置管理系统。

**方案:**

```python
# usmsb_sdk/core/config.py

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class NetworkConfig:
    """网络配置"""
    platform_url: str = "http://localhost:8000"
    p2p_port: int = 0
    http_port: int = 5001
    websocket_port: int = 8765

@dataclass
class AuthConfig:
    """认证配置"""
    api_key: Optional[str] = None
    wallet_address: Optional[str] = None
    stake_amount: float = 100.0

@dataclass
class AgentConfig:
    """Agent 配置"""
    agent_id: str
    agent_name: str
    agent_type: str = "generic"
    network: NetworkConfig = field(default_factory=NetworkConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    protocols: List[str] = field(default_factory=lambda: ["http", "websocket"])
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PlatformConfig:
    """平台配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str = "sqlite:///platform.db"
    redis_url: str = "redis://localhost:6379"
    auth_required: bool = True
    min_stake: float = 100.0
```

---

### 2.3 迁移路径

**阶段 1: 基础设施（1-2周）**

1. ✅ 创建 `usmsb_sdk/core/` 目录
2. ✅ 创建 `usmsb_sdk/protocol/` 目录结构
3. ✅ 添加 HTTP REST 服务端到 Agent SDK
4. ✅ 更新 Demo BaseAgent 继承 SDK BaseAgent

**阶段 2: 合并重构（2-3周）**

1. ✅ 合并 protocol 目录
2. ✅ 整理 node 目录
3. ✅ 更新所有 import 路径
4. ✅ 添加废弃警告到旧路径

**阶段 3: 测试和文档（1-2周）**

1. ✅ 添加单元测试
2. ✅ 添加集成测试
3. ✅ 更新文档
4. ✅ 创建迁移指南

**阶段 4: 清理（1周）**

1. ✅ 删除废弃代码
2. ✅ 删除旧目录
3. ✅ 版本发布

---

## 三、风险和缓解措施

### 3.1 兼容性风险

**风险:** 修改目录结构会破坏现有代码的 import。

**缓解措施:**
1. 在旧路径添加废弃警告
2. 保持旧路径的重导出
3. 提供迁移脚本
4. 发布迁移指南

```python
# 旧路径示例: platform/external/protocol/__init__.py
import warnings

warnings.warn(
    "usmsb_sdk.platform.external.protocol is deprecated, "
    "use usmsb_sdk.protocol instead",
    DeprecationWarning,
    stacklevel=2
)

from usmsb_sdk.protocol import *  # 重导出
```

### 3.2 功能回归风险

**风险:** 重构可能引入 bug 或丢失功能。

**缓解措施:**
1. 重构前完善测试
2. 渐进式重构
3. 每个阶段都运行完整测试
4. Code Review

### 3.3 时间风险

**风险:** 重构可能比预期花费更多时间。

**缓解措施:**
1. 优先级排序
2. 分阶段执行
3. 并行开发
4. 保持 Demo 可用

---

## 四、验收标准

### 4.1 功能验收

- [x] Agent SDK 提供 HTTP REST 服务端
- [x] Demo BaseAgent 继承 SDK BaseAgent
- [x] 只有一个 protocol 目录
- [x] node 目录职责清晰
- [x] 所有旧 import 路径有废弃警告

### 4.2 质量验收

- [x] 单元测试覆盖率 > 80%
- [x] 集成测试通过
- [x] Demo 运行正常
- [x] 文档更新完成

### 4.3 文档验收

- [x] API 文档更新
- [x] 架构图更新
- [x] 迁移指南完成
- [x] CHANGELOG 更新

---

## 五、附录

### A. 相关文件清单

**需要修改的文件:**

```
src/usmsb_sdk/
├── agent/
│   ├── __init__.py                 # 更新导出
│   ├── base_agent.py               # 增强
│   ├── communication.py            # 重构
│   └── http_server.py              # 新增
│
├── protocol/                       # 新建
│   └── ...
│
├── core/                           # 新建
│   └── ...
│
└── platform/
    ├── external/
    │   └── protocol/               # 废弃，添加重导出
    └── internal/                   # 新建
        └── node/                   # 从 external 移过来

demo/civilization_platform/supply_chain/
└── shared/
    └── base_agent.py               # 重构，继承 SDK
```

### B. 参考资料

- [Agent Communication Architecture](./COMMUNICATION.md) - 待创建
- [Protocol Specification](./PROTOCOLS.md) - 待创建
- [Migration Guide](./MIGRATION.md) - 待创建

---

## 六、执行计划

> **所有决策已确认，开始执行**

### 6.1 已确认事项

| 事项 | 决策 |
|------|------|
| API 层重构策略 | 一次性拆分，不保持向后兼容，重构后再联调前后端 |
| Demo 迁移计划 | 迁移期间无需运行，完成后进行联调和测试验证 |
| 测试策略 | 全覆盖，需要端到端测试 |
| 发布计划 | 见下方 6.3 |

### 6.2 团队分工

| 任务 | 建议人数 | 技能要求 |
|------|---------|---------|
| Agent SDK HTTP Server | 1 | FastAPI, asyncio |
| API 层拆分 | 2 | FastAPI, 架构设计 |
| Protocol 合并 | 1 | 协议理解, 重构经验 |
| Node 整理 | 1 | P2P 网络 |
| Demo 迁移 | 1 | 集成测试 |
| 文档和测试 | 1 | 技术写作 |

### 6.3 发布计划

```
v0.9.0-alpha    内部测试版本
    │
    ├── 完成所有模块重构
    ├── 单元测试覆盖率 > 80%
    └── 内部集成测试通过
    │
    ▼
v0.9.5-beta     公开测试版本
    │
    ├── 端到端测试全部通过
    ├── Demo 运行正常
    ├── API 文档完成
    └── 迁移指南完成
    │
    ▼
v1.0.0-rc1      候选版本
    │
    ├── 前后端联调完成
    ├── 性能测试通过
    ├── 安全审计通过
    └── 文档完整
    │
    ▼
v1.0.0          正式版本
    │
    ├── 所有测试通过
    ├── CHANGELOG 完成
    └── 发布公告
```

### 6.4 版本里程碑

| 版本 | 目标 | 验收标准 |
|------|------|---------|
| v0.9.0-alpha | 功能完整 | 所有模块重构完成，单元测试 > 80% |
| v0.9.5-beta | 质量验证 | E2E 测试通过，Demo 运行正常 |
| v1.0.0-rc1 | 联调就绪 | 前后端联调完成，文档完整 |
| v1.0.0 | 正式发布 | 所有验收标准达成 |

---

## 七、代码走查详细记录

### 7.1 已走查文件清单

| 文件 | 行数 | 状态 | 主要发现 |
|------|------|------|---------|
| `api/rest/main.py` | 2267 | ✅ 已走查 | 文件过大，需要拆分 |
| `services/matching_engine.py` | 594 | ✅ 已走查 | 设计良好，可复用 |
| `services/intelligence_source_manager.py` | - | ✅ 已走查 | LLM 适配器，设计良好 |
| `node/decentralized_node.py` | - | ✅ 已走查 | P2P 实现，文档不足 |
| `platform/protocols/mcp_adapter.py` | - | ✅ 已走查 | 完整 MCP 实现 |
| `platform/external/external_agent_adapter.py` | - | ✅ 已走查 | Agent 适配器核心 |
| `platform/external/protocol/*.py` | - | ✅ 已走查 | 与 protocols/ 重复 |
| `core/communication/*.py` | - | ✅ 已走查 | 通信模块，导出不完整 |
| `core/skills/*.py` | - | ✅ 已走查 | 技能系统 |
| `core/logic/*.py` | - | ✅ 已走查 | 核心引擎 |

### 7.2 代码质量评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 可读性 | 7/10 | 大部分代码清晰，但部分文件过长 |
| 可维护性 | 5/10 | 存在大量重复和大文件 |
| 可测试性 | 6/10 | 依赖注入不完整 |
| 文档完整性 | 4/10 | 缺少架构文档和 API 文档 |
| 测试覆盖 | 3/10 | 测试覆盖不足 |
| 模块化 | 5/10 | 存在重复模块和职责不清 |

### 7.3 推荐的重构顺序

```
阶段 0: 准备工作
├── 创建重构分支
├── 添加测试用例（确保现有功能不丢失）
└── 创建迁移脚本框架

阶段 1: 协议层重构 (P0)
├── 创建 usmsb_sdk/protocol/ 目录
├── 合并 platform/protocols/ 和 platform/external/protocol/
├── 为每个协议添加 server.py 和 client.py
└── 更新 import 路径

阶段 2: Agent SDK 增强 (P0)
├── 添加 HTTP REST Server (使用 FastAPI)
├── 更新 BaseAgent 集成 HTTP Server
└── 添加服务端能力

阶段 3: API 层拆分 (P0)
├── 创建 routers/ 目录
├── 将端点按领域拆分到独立文件
├── 创建 schemas/ 和 services/ 目录
└── 更新 main.py 为入口文件

阶段 4: Demo 统一 (P1)
├── 废弃 demo 中的 p2p_server.py
├── Demo BaseAgent 继承 SDK BaseAgent
└── 验证功能完整性

阶段 5: Node 整理 (P1)
├── 明确 usmsb_sdk/node/ 职责
├── 将 platform/external/node/ 移到 platform/internal/
└── 更新文档

阶段 6: 清理和发布 (P2)
├── 完善模块导出
├── 补充文档
├── 添加废弃警告
└── 发布 v1.0.0
```

---

*文档结束*
