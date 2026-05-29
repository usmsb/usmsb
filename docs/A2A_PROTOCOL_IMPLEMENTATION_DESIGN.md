# A2A 协议实现设计方案

> 版本: v1.0
> 日期: 2026-05-20
> 状态: 设计中

---

## 目录

1. [背景与目标](#1-背景与目标)
2. [现状分析](#2-现状分析)
3. [架构设计](#3-架构设计)
4. [类型系统设计](#4-类型系统设计)
5. [传输层设计](#5-传输层设计)
6. [Google A2A 协议实现](#6-google-a2a-协议实现)
7. [Custom A2A 协议实现](#7-custom-a2a-协议实现)
8. [测试策略](#8-测试策略)
9. [文件结构](#9-文件结构)
10. [实施计划](#10-实施计划)

---

## 1. 背景与目标

### 1.1 项目背景

USMSB 是一个基于 Silicon-based Life 的多智能体系统，需要支持 Agent 之间的标准通信。目前代码中存在以下问题：

- **三套并行的 A2A 实现**：自定义 A2A（`a2a_adapter.py` + `a2a_card.py`）、Google A2A（`google_a2a.py`）、A2A Client/Server（`a2a/` 目录），彼此独立，无法互通
- **`A2AEnvelope` 重复定义 3 次**：分别在 `a2a/client.py`、`platform/external/protocol/a2a_handler.py`、`protocol/base.py`
- **TaskStatus 枚举重复定义 3 次**：含义不一致
- **传输层未实现**：所有 `send_*` 方法都是 `asyncio.sleep(0.01)` 占位
- **Google A2A 实现不完整**：缺少 SSE、Push Notifications、完整 AgentCard、安全认证等
- **自定义 A2A 未与 server/client 框架集成**

### 1.2 参考标准

| 标准 | 版本 | 来源 |
|------|------|------|
| A2A Protocol Specification | 1.0.0 | [a2a-protocol.org](https://a2a-protocol.org) |
| A2A Python SDK (a2a-sdk) | 1.0+ | [a2aproject/a2a-python](https://github.com/a2aproject/a2a-python) |
| Google A2A Agent Card | 1.0 | 官方规范 |

### 1.3 设计目标

1. **完整支持 Google A2A Spec 1.0**：所有特性 100% 覆盖，包括 SSE 流式推送、Push Notifications、安全认证
2. **完善 Custom A2A 协议**：基于现有 `a2a_adapter.py` 和 `a2a_card.py`，补全缺失的 Task 状态机、消息类型、传输层
3. **统一信封格式**：只保留一套 `A2AEnvelope`，不复用
4. **传输层可插拔**：HTTP/JSON-RPC、gRPC、WebSocket、SSE，支持双协议共存
5. **持久化可选**：SQLite、PostgreSQL、MySQL 支持

---

## 2. 现状分析

### 2.1 现有文件清单

```
src/usmsb_sdk/protocol/
├── __init__.py                     # Phase 0 统一导出
├── base.py                         # BaseProtocolHandler（含重复的 A2AEnvelope）
├── a2a_adapter.py                  # Custom A2A: A2AMessage, DelegatedTask, A2AAdapter
├── a2a_card.py                     # Custom A2A: AgentCard, AgentCardRegistry
├── google_a2a.py                   # Google A2A: GoogleAgentCard, GoogleA2AHandler
├── mcp_gateway.py                  # MCP 网关
├── mcp_registry.py                 # MCP 工具注册
├── multi_wallet.py                 # 多币种钱包
├── x402_router.py                  # x402 支付路由
├── a2a/
│   ├── __init__.py                 # 导出 A2AClient, A2AEnvelope, A2AServer
│   ├── client.py                   # A2AClient（传输层未实现）+ 重复 A2AEnvelope
│   └── server.py                   # A2AServer（传输层未实现）
├── http/
│   ├── __init__.py
│   ├── client.py                   # HTTPClient
│   └── server.py                  # HTTPServer
├── grpc/
│   ├── __init__.py
│   ├── handler.py                  # gRPCHandler
├── websocket/
│   ├── __init__.py
│   ├── client.py                  # WebSocketClient
│   └── server.py                  # WebSocketServer
├── mcp/
│   ├── __init__.py
│   ├── types.py                   # MCP 类型定义
│   ├── adapter.py                 # MCP 适配器
│   └── handler.py                 # MCP 处理器
└── p2p/
    └── handler.py                 # P2P 处理器

src/usmsb_sdk/platform/external/protocol/   # 已废弃，复用 protocol/ 的代码
```

### 2.2 问题清单

| # | 问题 | 影响 |
|---|------|------|
| 1 | `A2AEnvelope` 在 3 处重复定义 | 维护困难，语义不一致 |
| 2 | `TaskStatus` 在 3 处重复定义 | `a2a_adapter.py` vs `google_a2a.py` vs `base.py` |
| 3 | 传输层都是占位代码 | 无法真正通信 |
| 4 | Google A2A 缺少 SSE/Push Notifications | 不完整 |
| 5 | Custom A2A 未使用 server/client 框架 | 架构不统一 |
| 6 | `platform/external/protocol/` 已废弃但未清理 | 冗余 |
| 7 | 缺少 Protobuf .proto 定义 | 无法生成 gRPC 代码 |
| 8 | 没有Interceptor机制 | 无法扩展 |
| 9 | 没有持久化层 | 状态只存内存 |
| 10 | 测试覆盖不完整 | 质量风险 |

---

## 3. 架构设计

### 3.1 整体架构

```
                            ┌─────────────────────────────────────────┐
                            │              USMSB Agent                │
                            │                                         │
  ┌──────────┐             │  ┌─────────────────────────────────┐   │
  │ 外部 Agent │◄──────────►│  │       Protocol Router           │   │
  │ (Google A2A)│          │  │  (分发到对应协议处理器)          │   │
  └──────────┘             │  └──────────┬──────────────┬──────┘   │
                            │             │              │           │
  ┌──────────┐             │  ┌──────────▼──┐   ┌──────▼───────┐   │
  │ 外部 Agent │◄──────────►│  │ Google A2A  │   │  Custom A2A  │   │
  │ (Custom A2A)│          │  │  Handler    │   │   Handler    │   │
  └──────────┘             │  └──────┬──────┘   └──────┬───────┘   │
                            │         │                   │           │
                            │  ┌──────▼───────────────────▼──────┐   │
                            │  │         A2A Envelope           │   │
                            │  │  (统一信封，协议无关)           │   │
                            │  └──────────────┬──────────────────┘   │
                            │                 │                      │
                            │  ┌──────────────▼──────────────────┐   │
                            │  │        Transport Layer         │   │
                            │  │  HTTP  gRPC  WebSocket  SSE   │   │
                            │  └─────────────────────────────────┘   │
                            └─────────────────────────────────────────┘
```

### 3.2 核心原则

1. **信封统一，协议多样**：传输层只认识 `A2AEnvelope`，上层协议格式由 handler 决定
2. **传输可插拔**：HTTP/gRPC/WebSocket/SSE 按需启用
3. **协议可切换**：一个 Agent 可以同时支持 Google A2A 和 Custom A2A
4. **向后兼容**：现有 API 不破坏

### 3.3 协议选择流程

**核心区分原则**：按 **payload 结构**（而非传输层）区分协议。

```
接收消息（传输层 agnostic）
    │
    ├── payload 是 JSON-RPC 2.0 格式
    │   └── Google A2A Handler
    │       （method ∈ {tasks/send, tasks/get, tasks/cancel, tasks/list,
    │                   agents/card, ...}）
    │
    └── payload 是 A2AEnvelope 格式（含 sender_id/receiver_id/correlation_id）
        └── Custom A2A Handler
```

**按传输层的路由规则**：

| 传输层 | 端点 | 协议 |
|--------|------|------|
| HTTP POST | `/rpc` | Google A2A (JSON-RPC) |
| HTTP GET | `/.well-known/agent.json` | Google A2A (AgentCard) |
| HTTP GET | `/tasks/{id}/events` | Google A2A (SSE) |
| HTTP POST | `/custom/{path}` | Custom A2A |
| WebSocket | `/ws` | 根据首帧 payload 判断 |
| gRPC | `AgentCommunicationService.*` | Google A2A 或 Custom A2A（按方法名区分） |

**gRPC 方法名区分**：
- `tasks/*` 或 `agents/*` → Google A2A Handler
- `custom/*` → Custom A2A Handler

---

## 4. 类型系统设计

### 4.1 设计原则

- **对齐官方 Protobuf**：Google A2A 的类型定义与官方 `a2a_pb2.py` 完全一致
- **Pydantic优先**：不使用 Protobuf 生成代码，用 Pydantic model 替代
- **Custom A2A 独立**：自定义协议有自己的类型定义，不依赖 Google A2A 类型

### 4.2 Google A2A 类型（对齐官方 Spec 1.0）

#### 4.2.1 枚举

```python
# protocol/google_a2a/types/enums.py

class TaskState(str, Enum):
    """Task 状态机 - 对齐官方 Spec"""
    UNSPECIFIED = ""           # 未指定
    SUBMITTED = "submitted"    # 任务已提交
    WORKING = "working"        # 任务执行中
    COMPLETED = "completed"    # 任务已完成
    FAILED = "failed"          # 任务失败
    CANCELED = "canceled"      # 任务已取消
    INPUT_REQUIRED = "input-required"   # 需要更多输入
    REJECTED = "rejected"      # 任务被拒绝（新增，补齐官方）
    AUTH_REQUIRED = "auth-required"     # 需要认证（新增，补齐官方）


class Role(str, Enum):
    """消息角色"""
    UNSPECIFIED = ""
    USER = "user"
    AGENT = "agent"


class MessageType(str, Enum):
    """消息类型"""
    TASK = "task"
    TASK_RESPONSE = "task_response"
    TASK_STATUS_UPDATE = "task_status_update"
    AGENT_CARD = "agent_card"
    ERROR = "error"
    CANCEL = "cancel"
```

#### 4.2.2 核心类型

```python
# protocol/google_a2a/types/models.py

class Part(BaseModel):
    """消息片段 - 对齐官方 Part 定义"""
    text: str | None = None           # 文本内容
    raw: bytes | None = None          # 原始二进制
    url: str | None = None             # URL 引用
    data: dict | None = None          # 结构化数据
    metadata: dict = {}                 # 元数据
    filename: str | None = None        # 文件名
    media_type: str | None = None      # MIME 类型


class Message(BaseModel):
    """A2A 消息 - 对齐官方 Message 定义"""
    message_id: str = ""
    context_id: str = ""
    task_id: str = ""
    role: Role = Role.UNSPECIFIED
    parts: list[Part] = []
    metadata: dict = {}
    extensions: list[str] = []
    reference_task_ids: list[str] = []


class TaskStatus(BaseModel):
    """任务状态 - 对齐官方 TaskStatus"""
    state: TaskState = TaskState.UNSPECIFIED
    message: Message | None = None
    timestamp: float = Field(default_factory=time.time)


class Artifact(BaseModel):
    """任务产物 - 对齐官方 Artifact"""
    artifact_id: str = ""
    name: str = ""
    description: str = ""
    parts: list[Part] = []
    metadata: dict = {}
    extensions: list[str] = []


class Task(BaseModel):
    """A2A 任务 - 对齐官方 Task"""
    id: str = ""
    context_id: str = ""
    status: TaskStatus = TaskState.UNSPECIFIED
    artifacts: list[Artifact] = []
    history: list[Message] = []
    metadata: dict = {}


class SendMessageConfiguration(BaseModel):
    """发送消息配置 - 对齐官方 SendMessageConfiguration"""
    accepted_output_modes: list[str] = []
    task_push_notification_config: "TaskPushNotificationConfig | None" = None
    history_length: int | None = None
    return_immediately: bool = False


class TaskPushNotificationConfig(BaseModel):
    """任务推送通知配置 - 对齐官方"""
    tenant: str = ""
    id: str = ""
    task_id: str = ""
    url: str = ""
    token: str = ""
    authentication: "AuthenticationInfo | None" = None


class AuthenticationInfo(BaseModel):
    """认证信息"""
    scheme: str = ""
    credentials: str = ""
```

#### 4.2.3 AgentCard 类型（对齐官方 Spec 1.0）

```python
# protocol/google_a2a/types/agent_card.py

class AgentCapabilities(BaseModel):
    """Agent 能力 - 对齐官方 AgentCapabilities"""
    streaming: bool = True
    push_notifications: bool = False
    extensions: list["AgentExtension"] = []
    extended_agent_card: bool = False


class AgentExtension(BaseModel):
    """Agent 扩展"""
    uri: str = ""
    description: str = ""
    required: bool = False
    params: dict = {}


class AgentProvider(BaseModel):
    """Agent 提供者"""
    url: str = ""
    organization: str = ""


class AgentInterface(BaseModel):
    """Agent 接口"""
    url: str = ""
    protocol_binding: str = ""
    tenant: str = ""
    protocol_version: str = ""


class AgentSkill(BaseModel):
    """Agent 技能 - 对齐官方 AgentSkill"""
    id: str = ""
    name: str = ""
    description: str = ""
    tags: list[str] = []
    examples: list[str] = []
    input_modes: list[str] = []
    output_modes: list[str] = []
    security_requirements: list["SecurityRequirement"] = []


class AgentCard(BaseModel):
    """Agent Card - 对齐官方 AgentCard

    用于 Agent 发现和协作。
    端点: GET /.well-known/agent.json
    """
    name: str = ""
    description: str = ""
    supported_interfaces: list[AgentInterface] = []
    provider: AgentProvider = AgentProvider()
    version: str = "1.0"
    documentation_url: str = ""
    capabilities: AgentCapabilities = AgentCapabilities()
    security_schemes: dict[str, "SecurityScheme"] = {}
    security_requirements: list["SecurityRequirement"] = []
    default_input_modes: list[str] = ["text"]
    default_output_modes: list[str] = ["text"]
    skills: list[AgentSkill] = []
    signatures: list["AgentCardSignature"] = []
    icon_url: str = ""
```

#### 4.2.4 安全类型

```python
# protocol/google_a2a/types/security.py

class SecurityScheme(BaseModel):
    """安全方案 - 对齐官方 SecurityScheme"""
    api_key_security_scheme: "APIKeySecurityScheme | None" = None
    http_auth_security_scheme: "HTTPAuthSecurityScheme | None" = None
    oauth2_security_scheme: "OAuth2SecurityScheme | None" = None
    open_id_connect_security_scheme: "OpenIdConnectSecurityScheme | None" = None
    mtls_security_scheme: "MutualTlsSecurityScheme | None" = None


class APIKeySecurityScheme(BaseModel):
    description: str = ""
    location: str = ""   # "header" | "query" | "cookie"
    name: str = ""


class HTTPAuthSecurityScheme(BaseModel):
    description: str = ""
    scheme: str = ""     # "basic" | "bearer" | ...
    bearer_format: str = ""


class OAuth2SecurityScheme(BaseModel):
    description: str = ""
    flows: "OAuthFlows" = OAuthFlows()
    oauth2_metadata_url: str = ""


class AgentCardSignature(BaseModel):
    """Agent Card 签名"""
    protected: str = ""
    signature: str = ""
    header: dict = {}
```

### 4.3 Custom A2A 类型（独立设计）

```python
# protocol/custom_a2a/types/models.py

class CustomTaskStatus(str, Enum):
    """Custom A2A 任务状态 - 自定义状态机"""
    PENDING = "pending"           # 待处理
    ACCEPTED = "accepted"         # 已接受
    IN_PROGRESS = "in_progress"   # 进行中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消


class CustomMessageType(str, Enum):
    """Custom A2A 消息类型"""
    TASK = "task"
    QUERY = "query"
    RESPONSE = "response"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    DISCOVERY = "discovery"
    NEGOTIATION = "negotiation"


class CustomPart(BaseModel):
    """Custom A2A 消息片段"""
    content: str | dict | None = None  # 文本或结构化数据
    mime_type: str = "text/plain"


class CustomMessage(BaseModel):
    """Custom A2A 消息"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: CustomMessageType = CustomMessageType.QUERY
    from_agent: str = ""
    to_agent: str = ""       # 空 = 广播
    subject: str = ""
    payload: dict = {}
    reply_to: str = ""
    timestamp: float = Field(default_factory=time.time)
    expires_at: float | None = None
    metadata: dict = {}


class CustomTask(BaseModel):
    """Custom A2A 任务"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""       # 原始任务 ID
    delegator: str = ""     # 委托方
    delegatee: str = ""      # 被委托方
    description: str = ""
    status: CustomTaskStatus = CustomTaskStatus.PENDING
    input_data: dict = {}
    output_data: dict | None = None
    error: str | None = None
    created_at: float = Field(default_factory=time.time)
    accepted_at: float | None = None
    completed_at: float | None = None
    deadline: float | None = None
    reward: float = 0.0
    currency: str = "USDC"
```

### 4.4 统一 A2AEnvelope

```python
# protocol/types/envelope.py

class A2AEnvelope(BaseModel):
    """统一 A2A 信封 - 所有协议共用

    设计原则：
    - sender_id / receiver_id: 全局唯一 Agent ID
    - message_type: 消息类型（协议无关）
    - payload: 协议特定内容（Google A2A 或 Custom A2A 格式）
    - correlation_id: 请求-响应关联
    - timestamp / ttl: 时间相关
    - signature: 签名（可选）
    - metadata: 扩展元数据
    """
    version: str = "1.0"
    sender_id: str = ""
    receiver_id: str = ""
    message_type: str = ""         # task | query | response | error | heartbeat | discovery
    payload: dict = {}            # 协议特定 payload
    correlation_id: str = ""       # 用于匹配请求和响应
    timestamp: float = Field(default_factory=time.time)
    ttl: int = 3600               # 秒
    signature: str | None = None
    metadata: dict = {}

    def is_broadcast(self) -> bool:
        return self.receiver_id == ""

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
```

### 4.5 类型文件结构

```
protocol/
├── types/
│   ├── __init__.py
│   ├── envelope.py              # 统一 A2AEnvelope
│   │
│   ├── google_a2a/
│   │   ├── __init__.py
│   │   ├── enums.py            # TaskState, Role, MessageType
│   │   ├── models.py           # Part, Message, Task, TaskStatus, Artifact
│   │   ├── agent_card.py       # AgentCard, AgentCapabilities, AgentSkill
│   │   ├── task_requests.py    # SendMessageRequest, GetTaskRequest, CancelTaskRequest
│   │   └── security.py         # SecurityScheme, AuthenticationInfo
│   │
│   └── custom_a2a/
│       ├── __init__.py
│       ├── enums.py            # CustomTaskStatus, CustomMessageType
│       └── models.py           # CustomMessage, CustomTask, CustomPart
```

---

## 5. 传输层设计

### 5.1 设计原则

- **信封驱动**：传输层只负责 `A2AEnvelope` 的发送和接收，不关心 payload 内容
- **可插拔**：按需启用 HTTP、gRPC、WebSocket、SSE
- **双工支持**：支持请求-响应和推送两种模式

### 5.2 HTTP/JSON-RPC 传输

#### 5.2.1 Server

```python
# protocol/transport/http_server.py

class HTTPServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8080
    unix_socket: str | None = None
    ssl_cert: str | None = None
    ssl_key: str | None = None
    num_workers: int = 1


class HTTPServer:
    """HTTP Server for A2A Protocol

    端点设计：
    - POST /rpc                    # JSON-RPC 入口
    - GET  /.well-known/agent.json # AgentCard 发现
    - GET  /tasks/{id}             # 获取任务状态（REST 兼容）
    - GET  /tasks/{id}/events      # SSE 流式推送
    - POST /tasks/{id}/cancel       # 取消任务
    - GET  /tasks                  # 任务列表
    """

    def __init__(
        self,
        config: HTTPServerConfig,
        google_a2a_handler: "GoogleA2AHandler | None" = None,
        custom_a2a_handler: "CustomA2AHandler | None" = None,
    ):
        ...

    async def start(self) -> None:
        """启动 HTTP Server"""

    async def stop(self) -> None:
        """停止 HTTP Server"""

    def register_google_a2a_handler(self, handler: "GoogleA2AHandler") -> None:
        """注册 Google A2A 处理器"""
        self._google_handler = handler

    def register_custom_a2a_handler(self, handler: "CustomA2AHandler") -> None:
        """注册 Custom A2A 处理器"""
        self._custom_handler = handler
```

#### 5.2.2 JSON-RPC 调度

```python
# protocol/transport/jsonrpc_dispatcher.py

class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 请求"""
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int | None = None
    method: str = ""
    params: dict = {}


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 响应"""
    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int | None = None
    result: dict | None = None
    error: "JSONRPCError | None" = None


class JSONRPCError(BaseModel):
    code: int
    message: str
    data: Any | None = None


class JSONRPCDispatcher:
    """JSON-RPC 请求调度器

    支持的方法（Google A2A）：
    - tasks/send     → on_send_task
    - tasks/get      → on_get_task
    - tasks/cancel   → on_cancel_task
    - tasks/list     → on_list_tasks
    - tasks/subscribe → on_subscribe_task (SSE)
    - agents/card    → on_get_agent_card
    - agents/extended_card → on_get_extended_agent_card
    """

    def __init__(
        self,
        google_a2a_handler: "GoogleA2AHandler | None" = None,
        custom_a2a_handler: "CustomA2AHandler | None" = None,
    ):
        ...

    async def dispatch(self, request: JSONRPCRequest) -> JSONRPCResponse:
        """调度 JSON-RPC 请求"""
        ...
```

### 5.3 SSE 流式传输

```python
# protocol/transport/sse.py

class SSEEvent(BaseModel):
    """Server-Sent Event 事件"""
    event: str = ""       # 事件类型: task_status | artifact_update | message
    data: dict = {}
    id: str = ""
    retry: int = 5000


class SSEStreamer:
    """SSE 流式推送

    用于：
    - 任务状态实时更新推送
    - 产物（Artifact）增量推送
    - 消息推送

    客户端订阅：GET /tasks/{task_id}/events
    响应：text/event-stream
    """

    def __init__(self, task_manager: "TaskManager"):
        ...

    async def subscribe(self, task_id: str) -> AsyncIterator[SSEEvent]:
        """订阅任务事件流"""
        ...

    async def push_status_update(self, task_id: str, status: "TaskStatus") -> None:
        """推送任务状态更新"""
        ...

    async def push_artifact(self, task_id: str, artifact: "Artifact") -> None:
        """推送产物更新"""
        ...
```

### 5.4 gRPC 传输

```python
# protocol/transport/grpc_server.py

class A2AgRPCServer:
    """gRPC Server for A2A Protocol

    使用 Protobuf 定义服务：
    - AgentCommunicationService.SendMessage
    - AgentCommunicationService.StreamCommunication
    - AgentCommunicationService.CallSkill
    - AgentCommunicationService.DiscoverAgents
    - AgentCommunicationService.Heartbeat

    对齐现有 proto/agent_communication.proto
    """

    def __init__(
        self,
        port: int = 50051,
        google_a2a_handler: "GoogleA2AHandler | None" = None,
        custom_a2a_handler: "CustomA2AHandler | None" = None,
    ):
        ...
```

### 5.5 WebSocket 传输

```python
# protocol/transport/websocket_server.py

class WebSocketServer:
    """WebSocket Server for A2A Protocol

    端点: WS /ws

    用途：
    - 实时双向通信
    - 任务状态推送
    - 跨防火墙通信
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8081,
        google_a2a_handler: "GoogleA2AHandler | None" = None,
        custom_a2a_handler: "CustomA2AHandler | None" = None,
    ):
        ...
```

### 5.6 传输层文件结构

```
protocol/
├── transport/
│   ├── __init__.py
│   ├── base.py                 # TransportHandler 基类
│   ├── envelope.py             # A2AEnvelope 定义（统一信封）
│   │
│   ├── http_server.py          # HTTP Server
│   ├── http_client.py          # HTTP Client
│   ├── jsonrpc_dispatcher.py   # JSON-RPC 调度器
│   │
│   ├── grpc_server.py          # gRPC Server
│   ├── grpc_client.py          # gRPC Client
│   │
│   ├── websocket_server.py     # WebSocket Server
│   ├── websocket_client.py     # WebSocket Client
│   │
│   ├── sse.py                  # SSE 流式推送
│   │
│   └── factories.py             # 传输层工厂
```

---

## 6. Google A2A 协议实现

### 6.1 架构

```
GoogleA2AHandler
    │
    ├── TaskStore (任务持久化)
    │   ├── InMemoryTaskStore     # 默认
    │   ├── SQLiteTaskStore       # 可选
    │   ├── PostgreSQLTaskStore   # 可选
    │   └── MySQLTaskStore        # 可选
    │
    ├── TaskManager (任务生命周期)
    │   ├── create_task()
    │   ├── update_status()
    │   ├── add_artifact()
    │   └── cancel_task()
    │
    ├── QueueManager (SSE 事件队列)
    │   ├── InMemoryQueueManager  # 默认
    │   └── RedisQueueManager     # 可选（未来）
    │
    ├── AgentExecutor (执行器接口)
    │   └── 用户实现 execute(), cancel()
    │
    └── PushNotifier (推送通知)
        └── 第三方 Webhook 调用
```

### 6.2 GoogleA2AHandler 核心实现

```python
# protocol/google_a2a/handler.py

class GoogleA2AHandler:
    """Google A2A 协议处理器 - 完整实现 Spec 1.0

    核心方法：
    - on_send_task()         → 处理 tasks/send
    - on_get_task()          → 处理 tasks/get
    - on_cancel_task()       → 处理 tasks/cancel
    - on_list_tasks()        → 处理 tasks/list
    - on_subscribe_task()    → 处理 tasks/subscribe (SSE)
    - on_get_agent_card()    → 处理 agents/card
    - on_get_extended_agent_card() → 处理 agents/extended_card

    Task 状态机（Spec 1.0）：
    submitted → working → completed
                      → failed
                      → input-required (等待用户输入)
                      → canceled
                      → rejected
                      → auth-required
    """

    WELL_KNOWN_PATH = "/.well-known/agent.json"

    def __init__(
        self,
        agent_card: "AgentCard",
        agent_executor: "AgentExecutor",
        task_store: "TaskStore | None" = None,
        queue_manager: "QueueManager | None" = None,
        push_notifier: "PushNotifier | None" = None,
        extended_agent_card: "AgentCard | None" = None,
    ):
        self._agent_card = agent_card
        self._agent_executor = agent_executor
        self._task_store = task_store or InMemoryTaskStore()
        self._queue_manager = queue_manager or InMemoryQueueManager()
        self._push_notifier = push_notifier
        self._extended_agent_card = extended_agent_card
        self._running_tasks: dict[str, asyncio.Task] = {}

    # === JSON-RPC 请求处理 ===

    async def on_send_task(
        self,
        params: "SendMessageRequest",
        context: "ServerCallContext",
    ) -> "Task | AsyncIterator[Task]":
        """处理 tasks/send 请求

        流程：
        1. 验证请求
        2. 创建或获取 Task
        3. 启动 AgentExecutor.execute()
        4. 返回 Task 或 SSE 流
        """
        ...

    async def on_get_task(
        self,
        params: "GetTaskRequest",
        context: "ServerCallContext",
    ) -> "Task | None":
        ...

    async def on_cancel_task(
        self,
        params: "CancelTaskRequest",
        context: "ServerCallContext",
    ) -> "Task | None":
        ...

    async def on_list_tasks(
        self,
        params: "ListTasksRequest",
        context: "ServerCallContext",
    ) -> "ListTasksResponse":
        ...

    async def on_subscribe_task(
        self,
        params: "SubscribeToTaskRequest",
        context: "ServerCallContext",
    ) -> AsyncIterator["TaskStatusUpdateEvent"]:
        """SSE 流式订阅任务更新

        响应：text/event-stream
        事件类型：
        - task_status: 状态变更
        - artifact_update: 新产物
        - message: 新消息
        """
        ...

    async def on_get_agent_card(
        self,
        context: "ServerCallContext",
    ) -> "AgentCard":
        return self._agent_card

    async def on_get_extended_agent_card(
        self,
        context: "ServerCallContext",
    ) -> "AgentCard | None":
        return self._extended_agent_card

    # === 内部方法 ===

    async def _execute_task(self, task_id: str) -> None:
        """异步执行任务，更新状态"""
        ...

    async def _push_status_update(
        self,
        task_id: str,
        status: "TaskStatus",
    ) -> None:
        """推送状态更新到 SSE 队列"""
        ...
```

### 6.3 TaskStore 持久化

```python
# protocol/google_a2a/persistence/task_store.py

class TaskStore(ABC):
    """Task 持久化接口"""

    @abstractmethod
    async def get(self, task_id: str, context) -> "Task | None":
        ...

    @abstractmethod
    async def save(self, task: "Task", context) -> None:
        ...

    @abstractmethod
    async def update(self, task_id: str, task: "Task", context) -> None:
        ...

    @abstractmethod
    async def list(self, request: "ListTasksRequest", context) -> "ListTasksResponse":
        ...


class InMemoryTaskStore(TaskStore):
    """内存存储（默认）"""
    _tasks: dict[str, Task] = {}


class SQLiteTaskStore(TaskStore):
    """SQLite 持久化"""
    _db_path: str = "a2a_tasks.db"


class PostgreSQLTaskStore(TaskStore):
    """PostgreSQL 持久化"""
    _conn: asyncpg.Connection


class MySQLTaskStore(TaskStore):
    """MySQL 持久化"""
    _conn: aiomysql.Connection
```

### 6.4 Google A2A 文件结构

```
protocol/
└── google_a2a/
    ├── __init__.py
    ├── handler.py               # GoogleA2AHandler 核心实现
    │
    ├── types/
    │   ├── __init__.py
    │   ├── enums.py            # TaskState, Role, MessageType
    │   ├── models.py           # Part, Message, Task, TaskStatus, Artifact
    │   ├── agent_card.py       # AgentCard, AgentCapabilities, AgentSkill
    │   ├── task_requests.py    # SendMessageRequest, GetTaskRequest 等
    │   └── security.py         # 安全类型
    │
    ├── persistence/
    │   ├── __init__.py
    │   ├── base.py             # TaskStore 抽象接口
    │   ├── memory.py            # InMemoryTaskStore
    │   ├── sqlite.py            # SQLiteTaskStore
    │   ├── postgresql.py        # PostgreSQLTaskStore
    │   └── mysql.py            # MySQLTaskStore
    │
    ├── execution/
    │   ├── __init__.py
    │   ├── agent_executor.py   # AgentExecutor 接口
    │   ├── simple_executor.py  # 简单同步执行器
    │   └── async_executor.py   # 异步执行器
    │
    ├── events/
    │   ├── __init__.py
    │   ├── event_queue.py      # 事件队列
    │   ├── sse_streamer.py     # SSE 推送
    │   └── push_notifier.py    # Webhook 推送
    │
    └── request_handlers/
        ├── __init__.py
        ├── jsonrpc_handler.py   # JSON-RPC 请求处理
        ├── rest_handler.py     # REST 兼容处理
        └── interceptor.py      # Interceptor 链
```

---

## 7. Custom A2A 协议实现

### 7.1 设计原则与定位

Custom A2A 是 USMSB 的私有协议，与 Google A2A 的选择依据：

| 场景 | 协议选择 | 原因 |
|------|---------|------|
| 与外部开源 Agent 通信 | **Google A2A** | 标准化、互操作 |
| 内部 Agent 间高性能通信 | **Custom A2A** | 更轻量、无 Protobuf 依赖 |
| 需要任务委托 + 报酬机制 | **Custom A2A** | 内置 `reward`/`currency`/`deadline` |
| 需要钱包签名认证 | **Custom A2A** | 内置 `wallet_signature` 认证方案 |
| 需要 Agent Card 发现 + 声誉系统 | **Custom A2A** | 内置 `AgentCardRegistry` + `reputation` 评分 |
| 需要广播消息 | **Custom A2A** | `to_agent=""` 支持广播 |
| 需要协商流程 | **Custom A2A** | 内置 `NEGOTIATION` 消息类型 |
| 需要流式 SSE | **Google A2A** | 官方 Spec 原生支持 |

**设计原则**：
- **独立于 Google A2A**：自己的类型系统、状态机、消息格式
- **与传输层集成**：复用 `A2AServer` / `A2AClient` 框架
- **功能完整**：消息收发、任务委托、状态追踪、协商

### 7.2 CustomA2AHandler 核心实现

```python
# protocol/custom_a2a/handler.py

class CustomA2AHandler:
    """Custom A2A 协议处理器

    核心方法：
    - on_task_request()    → 处理任务请求
    - on_query()           → 处理查询
    - on_discovery()       → 处理发现请求
    - on_heartbeat()       → 处理心跳
    - on_negotiation()     → 处理协商

    Task 状态机：
    pending → accepted → in_progress → completed
                                  → failed
                                  → canceled
    """

    def __init__(
        self,
        agent_card: "CustomAgentCard",
        skill_handlers: dict[str, Callable],
        task_store: "CustomTaskStore | None" = None,
        message_queue: "MessageQueue | None" = None,
    ):
        ...

    async def on_task_request(
        self,
        envelope: "A2AEnvelope",
    ) -> "A2AEnvelope":
        """处理任务请求"""
        ...

    async def on_query(
        self,
        envelope: "A2AEnvelope",
    ) -> "A2AEnvelope":
        """处理查询消息"""
        ...

    async def on_discovery(
        self,
        envelope: "A2AEnvelope",
    ) -> "A2AEnvelope":
        """处理发现请求，返回 AgentCard"""
        ...

    async def on_negotiation(
        self,
        envelope: "A2AEnvelope",
    ) -> "A2AEnvelope":
        """处理协商消息"""
        ...

    async def send_task_result(
        self,
        task_id: str,
        result: dict,
    ) -> None:
        """发送任务结果"""
        ...
```

### 7.3 Custom A2A 文件结构

```
protocol/
└── custom_a2a/
    ├── __init__.py
    ├── handler.py               # CustomA2AHandler 核心实现
    │
    ├── types/
    │   ├── __init__.py
    │   ├── enums.py            # CustomTaskStatus, CustomMessageType
    │   └── models.py           # CustomMessage, CustomTask, CustomPart
    │
    ├── registry/
    │   ├── __init__.py
    │   ├── agent_card.py       # CustomAgentCard, CustomSkill
    │   └── agent_registry.py   # AgentCardRegistry（完善现有）
    │
    ├── adapter/
    │   ├── __init__.py
    │   ├── message_adapter.py  # A2AAdapter（完善现有 a2a_adapter.py）
    │   └── skill_dispatcher.py # Skill 分发器
    │
    ├── persistence/
    │   ├── __init__.py
    │   ├── base.py
    │   ├── memory.py
    │   ├── sqlite.py
    │   └── postgres.py
    │
    └── server/
        ├── __init__.py
        ├── custom_server.py    # CustomA2AServer
        └── custom_client.py    # CustomA2AClient
```

---

## 8. 测试策略

### 8.1 单元测试

| 模块 | 测试文件 | 覆盖内容 |
|------|---------|---------|
| 类型系统 | `tests/unit/test_protocol/test_google_a2a_types.py` | 所有 Google A2A 类型 |
| 类型系统 | `tests/unit/test_protocol/test_custom_a2a_types.py` | 所有 Custom A2A 类型 |
| 传输层 | `tests/unit/test_protocol/test_envelope.py` | A2AEnvelope 序列化/反序列化 |
| Google A2A Handler | `tests/unit/test_protocol/test_google_a2a_handler.py` | 任务状态机、请求处理 |
| Custom A2A Handler | `tests/unit/test_protocol/test_custom_a2a_handler.py` | 消息收发、任务委托 |

### 8.2 集成测试

| 测试 | 说明 |
|------|------|
| `test_http_google_a2a` | HTTP + JSON-RPC + Google A2A |
| `test_http_custom_a2a` | HTTP + Custom A2A |
| `test_sse_streaming` | SSE 流式推送 |
| `test_websocket_google_a2a` | WebSocket + Google A2A |
| `test_grpc_google_a2a` | gRPC + Google A2A |
| `test_dual_protocol` | 同时支持双协议 |
| `test_task_persistence` | 任务持久化 |
| `test_push_notifications` | Push Notification |

### 8.3 协议一致性测试

- 使用官方 [a2a-inspector](https://github.com/a2aproject/a2a-inspector) 验证 Google A2A 实现
- 测试与官方 a2a-sdk 的互操作性

---

## 9. 文件结构

### 9.1 完整目标文件结构

```
src/usmsb_sdk/protocol/
├── __init__.py                     # 统一导出（更新）
│
├── types/                          # ★ 新建：统一类型系统
│   ├── __init__.py
│   ├── envelope.py                 # A2AEnvelope（统一信封）
│   │
│   ├── google_a2a/                 # Google A2A 类型
│   │   ├── __init__.py
│   │   ├── enums.py
│   │   ├── models.py
│   │   ├── agent_card.py
│   │   ├── task_requests.py
│   │   └── security.py
│   │
│   └── custom_a2a/                 # Custom A2A 类型
│       ├── __init__.py
│       ├── enums.py
│       └── models.py
│
├── transport/                      # ★ 新建/重构：传输层
│   ├── __init__.py
│   ├── base.py                     # TransportHandler 基类
│   ├── http_server.py              # HTTP Server（重构）
│   ├── http_client.py              # HTTP Client（重构）
│   ├── jsonrpc_dispatcher.py       # JSON-RPC 调度（新建）
│   ├── grpc_server.py              # gRPC Server（完善）
│   ├── grpc_client.py              # gRPC Client（完善）
│   ├── websocket_server.py         # WebSocket Server（完善）
│   ├── websocket_client.py         # WebSocket Client（完善）
│   ├── sse.py                      # SSE 流式推送（新建）
│   └── factories.py                # 传输层工厂（新建）
│
├── google_a2a/                   # ★ 重构：Google A2A 完整实现
│   ├── __init__.py
│   ├── handler.py                  # GoogleA2AHandler 核心实现
│   │                             # 类型统一放在 protocol/types/google_a2a/
│   ├── persistence/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── memory.py
│   │   ├── sqlite.py
│   │   └── postgres.py
│   │
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── agent_executor.py
│   │   └── simple_executor.py
│   │
│   ├── events/
│   │   ├── __init__.py
│   │   ├── event_queue.py
│   │   ├── sse_streamer.py
│   │   └── push_notifier.py
│   │
│   └── request_handlers/
│       ├── __init__.py
│       ├── jsonrpc_handler.py
│       ├── rest_handler.py
│       └── interceptor.py
│
├── custom_a2a/                   # ★ 重构：Custom A2A 完整实现
│   ├── __init__.py
│   ├── handler.py                 # CustomA2AHandler 核心实现
│   │                             # 类型统一放在 protocol/types/custom_a2a/
│   ├── registry/
│   │   ├── __init__.py
│   │   ├── agent_card.py
│   │   └── agent_registry.py
│   │
│   ├── adapter/
│   │   ├── __init__.py
│   │   ├── message_adapter.py
│   │   └── skill_dispatcher.py
│   │
│   ├── persistence/
│   │   ├── __init__.py
│   │   └── memory.py
│   │
│   └── server/
│       ├── __init__.py
│       ├── custom_server.py
│       └── custom_client.py
│
├── mcp/                            # 保持现状（独立协议）
│   ├── __init__.py
│   ├── types.py
│   ├── adapter.py
│   └── handler.py
│
├── base.py                         # ★ 重构：移除重复的 A2AEnvelope
│                                  # 保留 BaseProtocolHandler
├── a2a_adapter.py                 # ★ 废弃：迁移到 custom_a2a/
├── a2a_card.py                    # ★ 废弃：迁移到 custom_a2a/registry/
├── google_a2a.py                  # ★ 废弃：迁移到 google_a2a/
│
├── a2a/                           # ★ 废弃：迁移到 transport/
│   ├── __init__.py
│   ├── client.py
│   └── server.py
│
├── http/                          # ★ 废弃：迁移到 transport/
├── grpc/                         # ★ 废弃：迁移到 transport/
├── websocket/                   # ★ 废弃：迁移到 transport/
└── p2p/                          # 保持现状

src/usmsb_sdk/platform/external/protocol/  # ★ 重新导出 protocol/ 的新模块
```

### 9.2 向后兼容策略

**核心原则**：废弃文件**不删除**，改为兼容别名导入，附 DeprecationWarning。

```python
# a2a_adapter.py（旧文件，保留为兼容别名）
"""已废弃，请使用 custom_a2a.adapter.message_adapter"""
import warnings
warnings.warn(
    "a2a_adapter is deprecated, use custom_a2a.adapter.message_adapter",
    DeprecationWarning,
    stacklevel=2,
)

from usmsb_sdk.protocol.types.custom_a2a.models import (
    A2AMessage as A2AMessage,
    DelegatedTask as DelegatedTask,
)
from usmsb_sdk.protocol.custom_a2a.adapter.message_adapter import (
    A2AAdapter as A2AAdapter,
)

__all__ = ["A2AMessage", "DelegatedTask", "A2AAdapter"]
```

### 9.3 迁移映射

| 旧路径（保留为兼容别名） | 新路径（真实来源） |
|---------|--------|
| `a2a_adapter.py` | `custom_a2a/adapter/message_adapter.py` |
| `a2a_card.py` | `custom_a2a/registry/agent_card.py` |
| `google_a2a.py` | `google_a2a/handler.py` |
| `a2a/client.py` | `transport/` |
| `a2a/server.py` | `transport/` |
| `http/client.py`, `http/server.py` | `transport/` |
| `grpc/handler.py` | `transport/` |
| `websocket/client.py`, `websocket/server.py` | `transport/` |
| `platform/external/protocol/a2a_handler.py` | 重新导出 `protocol/types/envelope.py` |

---

## 10. 实施计划

### 10.1 阶段划分

```
Phase 1: 类型系统重构（基础设施）
Phase 2: Google A2A Handler 完善
Phase 3: Custom A2A Handler 完善
Phase 4: 传输层实现
Phase 5: 集成测试与清理
```

### Phase 1: 类型系统重构（预计 3-5 天）

| 步骤 | 任务 | 交付物 |
|------|------|--------|
| 1.1 | 新建 `protocol/types/` 目录结构 | 目录框架 |
| 1.2 | 实现 `A2AEnvelope` 统一信封 | `types/envelope.py` |
| 1.3 | 实现 Google A2A 类型（对齐官方） | `types/google_a2a/` |
| 1.4 | 实现 Custom A2A 类型 | `types/custom_a2a/` |
| 1.5 | 更新 `protocol/base.py`，移除重复定义 | `base.py` |
| 1.6 | 更新 `protocol/__init__.py` | 导出更新 |
| 1.7 | 编写类型系统单元测试 | `tests/unit/protocol/test_types/` |

### Phase 2: Google A2A Handler 完善（预计 5-7 天）

| 步骤 | 任务 | 交付物 |
|------|------|--------|
| 2.1 | 创建 `google_a2a/handler.py` 核心实现 | GoogleA2AHandler |
| 2.2 | 实现 TaskStore 接口和内存实现 | persistence/ |
| 2.3 | 实现 SSE 流式推送 | events/sse_streamer.py |
| 2.4 | 实现 Push Notification | events/push_notifier.py |
| 2.5 | 实现 TaskManager | 任务状态机 |
| 2.6 | 实现 Interceptor 机制 | request_handlers/interceptor.py |
| 2.7 | 添加 SQLite/PostgreSQL/MySQL 支持 | persistence/sqlite.py 等 |
| 2.8 | 编写 Google A2A Handler 单元测试 | `tests/unit/protocol/test_google_a2a/` |

### Phase 3: Custom A2A Handler 完善（预计 3-5 天）

| 步骤 | 任务 | 交付物 |
|------|------|--------|
| 3.1 | 创建 `custom_a2a/handler.py` | CustomA2AHandler |
| 3.2 | 完善 AgentCardRegistry | registry/agent_registry.py |
| 3.3 | 完善 A2AAdapter | adapter/message_adapter.py |
| 3.4 | 实现 Custom A2A Server/Client | server/ |
| 3.5 | 编写 Custom A2A Handler 单元测试 | `tests/unit/protocol/test_custom_a2a/` |

### Phase 4: 传输层实现（预计 5-7 天）

| 步骤 | 任务 | 交付物 |
|------|------|--------|
| 4.1 | 实现 HTTP Server + JSON-RPC Dispatcher | transport/http_server.py |
| 4.2 | 实现 HTTP Client | transport/http_client.py |
| 4.3 | 实现 SSE Server | transport/sse.py |
| 4.4 | 实现 gRPC Server/Client | transport/grpc_server.py |
| 4.5 | 实现 WebSocket Server/Client | transport/websocket_server.py |
| 4.6 | 实现传输层工厂 | transport/factories.py |
| 4.7 | 编写传输层单元测试 | `tests/unit/protocol/test_transport/` |

### Phase 5: 集成测试与清理（预计 3-5 天）

| 步骤 | 任务 | 交付物 |
|------|------|--------|
| 5.1 | 编写端到端集成测试 | `tests/agent_protocol/integration/test_a2a_e2e.py` |
| 5.2 | 与官方 a2a-sdk 互操作测试 | 验证兼容性 |
| 5.3 | 清理废弃文件 | 删除重复文件 |
| 5.4 | 更新 `protocol/__init__.py` 导出 | API 对齐 |
| 5.5 | 运行完整测试套件 | 100% 通过 |

### 10.2 总工期估算

| 阶段 | 工期 |
|------|------|
| Phase 1 | 3-5 天 |
| Phase 2 | 5-7 天 |
| Phase 3 | 3-5 天 |
| Phase 4 | 5-7 天 |
| Phase 5 | 3-5 天 |
| **总计** | **19-29 天** |

### 10.3 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 官方 a2a-sdk 规范变化 | 需同步更新 | 隔离类型定义，模块化更新 |
| 传输层实现复杂 | 工期超期 | 优先实现 HTTP+gRPC，WebSocket 后续 |
| 破坏现有 API | 用户受影响 | 保持 `__init__.py` 导出兼容 |
| 测试覆盖不足 | 质量风险 | 每阶段必须测试通过才能下一阶段 |

---

## 附录

### A. 与官方 a2a-sdk 功能对比

| 功能 | 官方 a2a-sdk | 本实现 | 备注 |
|------|:---:|:---:|:---|
| Spec 1.0 完整支持 | ✅ | ✅ | - |
| HTTP + JSON-RPC | ✅ | ✅ | - |
| HTTP + REST | ✅ | ✅ | - |
| gRPC | ✅ | ✅ | - |
| SSE Streaming | ✅ | ✅ | - |
| Push Notifications | ✅ | ✅ | - |
| SQLite 持久化 | ✅ | ✅ | - |
| PostgreSQL | ✅ | ✅ | - |
| MySQL | ✅ | ✅ | - |
| Interceptor | ✅ | ✅ | - |
| OpenTelemetry | ✅ | ❌ | 未来考虑 |
| v0.3 兼容 | ✅ | ❌ | 未来考虑 |
| **Custom A2A** | ❌ | ✅ | 我们的特色 |

### B. Google A2A JSON-RPC API 完整列表

| Method | 说明 | 实现状态 |
|--------|------|---------|
| `tasks/send` | 发送消息/创建任务 | 待完善 |
| `tasks/get` | 获取任务状态 | 待完善 |
| `tasks/cancel` | 取消任务 | 待完善 |
| `tasks/list` | 列出任务 | 待完善 |
| `tasks/subscribe` | SSE 订阅任务更新 | 待实现 |
| `agents/card` | 获取 AgentCard | 待完善 |
| `agents/extended_card` | 获取扩展 AgentCard | 待实现 |
| `tasks/push_notification_config/get` | 获取推送配置 | 待实现 |
| `tasks/push_notification_config/create` | 创建推送配置 | 待实现 |
| `tasks/push_notification_config/delete` | 删除推送配置 | 待实现 |
| `tasks/push_notification_config/list` | 列出推送配置 | 待实现 |

### C. 参考资料

- [A2A Protocol Specification 1.0](https://a2a-protocol.org)
- [a2aproject/a2a-python](https://github.com/a2aproject/a2a-python)
- [A2A Inspector](https://github.com/a2aproject/a2a-inspector)
- [A2A Samples](https://github.com/a2aproject/a2a-samples)
