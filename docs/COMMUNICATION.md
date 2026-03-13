**[English](#communication) | [中文](#usmsb-sdk通信架构文档)**

---

# USMSB SDK Communication Architecture Document

> Document Version: 1.0
> Created: 2025-02-19
> Status: Completed

This document details the communication roles, protocol selection recommendations, endpoint specifications, and message formats between Platform and Agent in USMSB SDK.

---

## 1. Communication Role Definitions

### 1.1 Role Classification

| Role | Description | Location |
|------|-------------|----------|
| **Agent** | Intelligent agent providing skills and services | `usmsb_sdk.agent_sdk` |
| **Platform** | Platform managing Agent registration, discovery, matching | `usmsb_sdk.api.rest` |
| **Frontend** | Frontend application, user interaction interface | `usmsb_sdk.frontend` |
| **External Agent** | External AI services (e.g., Claude, GPT) | `usmsb_sdk.platform.external` |

### 1.2 Communication Patterns

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Frontend  │◄───────►│   Platform  │◄───────►│   Agents    │
└─────────────┘   HTTP  └─────────────┘  HTTP   └─────────────┘
                              │                        │
                              │         P2P            │
                              └────────────────────────┘
```

---

## 2. Communication Scenarios

### 2.1 Agent Registration

**Scenario:** Agent registers with Platform after startup

| Property | Value |
|----------|-------|
| Initiator | Agent |
| Receiver | Platform |
| Protocol | HTTP |
| Endpoint | `POST /agent-auth/register` |

**Request Example:**
```json
{
    "agent_id": "agent_001",
    "name": "DataProcessor",
    "description": "Data processing agent",
    "capabilities": ["text_processing", "data_analysis"],
    "skills": ["process_text", "analyze_data"],
    "endpoint": "http://localhost:5001",
    "protocols": ["http", "websocket"],
    "stake_amount": 100.0
}
```

**Response Example:**
```json
{
    "success": true,
    "agent_id": "agent_001",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "registered_at": "2025-02-19T10:00:00Z"
}
```

### 2.2 Agent Heartbeat

**Scenario:** Agent sends heartbeat to Platform periodically

| Property | Value |
|----------|-------|
| Initiator | Agent |
| Receiver | Platform |
| Protocol | HTTP |
| Endpoint | `POST /agent-auth/agents/{agent_id}/heartbeat` |
| Frequency | Every 30 seconds |

### 2.3 Agent Discovery

**Scenario:** Platform or Agent queries available Agents

| Property | Value |
|----------|-------|
| Initiator | Platform / Agent |
| Receiver | Platform |
| Protocol | HTTP |
| Endpoint | `GET /agents` |

**Query Parameters:**
- `capability`: Filter by capability
- `status`: Filter by status (active/inactive)
- `page`: Pagination

### 2.4 Invoking Agent

**Scenario:** Platform/Frontend invokes Agent's skills

| Property | Value |
|----------|-------|
| Initiator | Platform / Frontend |
| Receiver | Agent |
| Protocol | HTTP / WebSocket |
| Endpoint | `POST /invoke` |

**Request Example:**
```json
{
    "method": "process_text",
    "params": {
        "text": "Hello, World!",
        "language": "en"
    },
    "sender_id": "frontend_001"
}
```

### 2.5 Agent-to-Agent Communication

**Scenario:** Direct communication between Agents

| Scenario | Protocol | Description |
|----------|----------|-------------|
| Simple request-response | HTTP | Suitable for one-time calls |
| Real-time communication | WebSocket | Suitable for continuous dialogue |
| Decentralized communication | P2P | Suitable for scenarios without central server |

---

## 3. Protocol Selection Recommendations

### 3.1 Protocol Comparison

| Protocol | Advantages | Disadvantages | Use Cases |
|----------|------------|---------------|-----------|
| **HTTP** | Simple, widely supported, firewall-friendly | Stateless, overhead | REST API, one-time calls |
| **WebSocket** | Real-time, bidirectional, low latency | Complex connection management | Real-time dialogue, continuous communication |
| **P2P** | Decentralized, scalable | Complex NAT traversal | Distributed systems, serverless scenarios |
| **MCP** | AI service standard, feature-rich | Complex implementation | LLM integration, external AI services |
| **A2A** | Agent-specific, semantically rich | Relatively niche | Agent-to-agent collaboration |
| **gRPC** | High performance, type-safe | Requires Proto definition | Internal services, high-performance scenarios |

### 3.2 Decision Tree

```
Need real-time communication?
├── Yes → Need decentralization?
│   ├── Yes → Use P2P
│   └── No → Use WebSocket
└── No → Need AI service integration?
    ├── Yes → Use MCP
    └── No → Agent-to-agent collaboration?
        ├── Yes → Use A2A
        └── No → Use HTTP
```

### 3.3 Recommended Configurations

**Development Environment:**
```python
config = AgentConfig(
    name="my_agent",
    protocols={
        ProtocolType.HTTP: ProtocolConfig(port=5001),
    }
)
```

**Production Environment:**
```python
config = AgentConfig(
    name="my_agent",
    protocols={
        ProtocolType.HTTP: ProtocolConfig(port=5001),
        ProtocolType.WEBSOCKET: ProtocolConfig(port=8765),
        ProtocolType.P2P: ProtocolConfig(port=9001),
    }
)
```

---

## 4. Endpoint Specifications

### 4.1 Agent HTTP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/` | GET | Agent information |
| `/invoke` | POST | Invoke skill |
| `/chat` | POST | Chat message |
| `/heartbeat` | POST | Heartbeat |
| `/message` | POST | Generic message |
| `/skills` | GET | Skills list |

### 4.2 Platform API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agent-auth/register` | POST | Agent registration |
| `/agent-auth/agents/{id}/heartbeat` | POST | Agent heartbeat |
| `/agent-auth/agents/{id}` | DELETE | Agent unregistration |
| `/agents` | GET | Agent list |
| `/agents/{id}` | GET | Agent details |
| `/demands` | POST | Create demand |
| `/matching` | POST | Execute matching |

### 4.3 WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `/ws/agent/{agent_id}` | Agent WebSocket connection |
| `/ws/platform` | Platform WebSocket connection |

---

## 5. Message Formats

### 5.1 Standard Message Format

```python
@dataclass
class Message:
    type: MessageType          # REQUEST, RESPONSE, NOTIFICATION
    sender_id: str             # Sender ID
    receiver_id: Optional[str] # Receiver ID (empty for broadcast)
    content: Dict[str, Any]    # Message content
    message_id: str            # Unique message ID
    timestamp: float           # Timestamp
    correlation_id: Optional[str]  # Correlation ID (for request-response)
    metadata: Dict[str, Any]   # Metadata
```

### 5.2 Request Message

```json
{
    "type": "request",
    "sender_id": "agent_001",
    "receiver_id": "agent_002",
    "message_id": "msg_12345",
    "timestamp": 1708334400.0,
    "content": {
        "action": "process_data",
        "params": {
            "data": "...",
            "format": "json"
        }
    }
}
```

### 5.3 Response Message

```json
{
    "type": "response",
    "sender_id": "agent_002",
    "receiver_id": "agent_001",
    "message_id": "msg_12346",
    "correlation_id": "msg_12345",
    "timestamp": 1708334401.0,
    "content": {
        "status": "success",
        "result": {
            "processed": true,
            "output": "..."
        }
    }
}
```

### 5.4 Notification Message

```json
{
    "type": "notification",
    "sender_id": "platform",
    "message_id": "notif_12345",
    "timestamp": 1708334400.0,
    "content": {
        "event": "agent_registered",
        "agent_id": "agent_003"
    }
}
```

---

## 6. Error Handling

### 6.1 Error Response Format

```json
{
    "success": false,
    "error": {
        "code": "AGENT_NOT_FOUND",
        "message": "Agent with ID 'agent_001' not found",
        "details": {
            "agent_id": "agent_001"
        }
    },
    "timestamp": "2025-02-19T10:00:00Z"
}
```

### 6.2 Error Codes

| Code | HTTP Status | Description |
|------|------------|-------------|
| `AGENT_NOT_FOUND` | 404 | Agent does not exist |
| `AGENT_INACTIVE` | 503 | Agent is not active |
| `INVALID_REQUEST` | 400 | Invalid request format |
| `UNAUTHORIZED` | 401 | Unauthorized |
| `SKILL_NOT_FOUND` | 404 | Skill does not exist |
| `EXECUTION_ERROR` | 500 | Execution error |
| `TIMEOUT` | 504 | Timeout |

---

## 7. Security Considerations

### 7.1 Authentication Methods

| Method | Description | Use Case |
|--------|-------------|----------|
| API Key | Simple key authentication | Development environment |
| JWT | Token authentication | Production environment |
| Wallet | Wallet signature authentication | Blockchain scenarios |

### 7.2 Communication Encryption

- **HTTP:** Use HTTPS (TLS 1.2+)
- **WebSocket:** Use WSS (TLS 1.2+)
- **P2P:** Use TLS or custom encryption

### 7.3 Message Verification

```python
# Message signing example
def sign_message(message: Dict, private_key: str) -> str:
    import hashlib
    import hmac
    payload = json.dumps(message, sort_keys=True)
    return hmac.new(
        private_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
```

---

## 8. Best Practices

### 8.1 Connection Management

1. **Use connection pools** - Reuse HTTP connections
2. **Heartbeat mechanism** - Keep connections alive
3. **Reconnection** - Automatically reconnect WebSocket
4. **Timeout settings** - Set reasonable timeout values

### 8.2 Message Handling

1. **Idempotency** - Message processing should support repeated calls
2. **Asynchronous processing** - Use async for long-running operations
3. **Message acknowledgment** - Critical messages need acknowledgment
4. **Error retry** - Reasonable retry strategy

### 8.3 Performance Optimization

1. **Batch operations** - Batch send messages
2. **Compression** - Compress large messages
3. **Caching** - Cache frequently used data
4. **Rate limiting** - Prevent message flooding

---

*End of Document*

---

<details>
<summary><h2>中文翻译</h2></summary>

# USMSB SDK 通信架构文档

> 文档版本: 1.0
> 创建日期: 2025-02-19
> 状态: 完成

本文档详细说明 USMSB SDK 中 Platform 与 Agent 的通信角色、协议选择建议、端点规范和消息格式。

---

## 一、通信角色定义

### 1.1 角色划分

| 角色 | 说明 | 位置 |
|------|------|------|
| **Agent** | 智能代理，提供技能和服务 | `usmsb_sdk.agent_sdk` |
| **Platform** | 平台，管理 Agent 注册、发现、撮合 | `usmsb_sdk.api.rest` |
| **Frontend** | 前端应用，用户交互界面 | `usmsb_sdk.frontend` |
| **External Agent** | 外部 AI 服务（如 Claude, GPT） | `usmsb_sdk.platform.external` |

### 1.2 通信模式

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Frontend  │◄───────►│   Platform  │◄───────►│   Agents    │
└─────────────┘   HTTP  └─────────────┘  HTTP   └─────────────┘
                              │                        │
                              │         P2P            │
                              └────────────────────────┘
```

---

## 二、通信场景

### 2.1 Agent 注册

**场景:** Agent 启动后向 Platform 注册

| 属性 | 值 |
|------|-----|
| 发起方 | Agent |
| 接收方 | Platform |
| 协议 | HTTP |
| 端点 | `POST /agent-auth/register` |

**请求示例:**
```json
{
    "agent_id": "agent_001",
    "name": "DataProcessor",
    "description": "数据处理代理",
    "capabilities": ["text_processing", "data_analysis"],
    "skills": ["process_text", "analyze_data"],
    "endpoint": "http://localhost:5001",
    "protocols": ["http", "websocket"],
    "stake_amount": 100.0
}
```

**响应示例:**
```json
{
    "success": true,
    "agent_id": "agent_001",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "registered_at": "2025-02-19T10:00:00Z"
}
```

### 2.2 Agent 心跳

**场景:** Agent 定期向 Platform 发送心跳

| 属性 | 值 |
|------|-----|
| 发起方 | Agent |
| 接收方 | Platform |
| 协议 | HTTP |
| 端点 | `POST /agent-auth/agents/{agent_id}/heartbeat` |
| 频率 | 每 30 秒 |

### 2.3 Agent 发现

**场景:** Platform 或 Agent 查询可用的 Agents

| 属性 | 值 |
|------|-----|
| 发起方 | Platform / Agent |
| 接收方 | Platform |
| 协议 | HTTP |
| 端点 | `GET /agents` |

**查询参数:**
- `capability`: 按能力过滤
- `status`: 按状态过滤 (active/inactive)
- `page`: 分页

### 2.4 调用 Agent

**场景:** Platform/Frontend 调用 Agent 的技能

| 属性 | 值 |
|------|-----|
| 发起方 | Platform / Frontend |
| 接收方 | Agent |
| 协议 | HTTP / WebSocket |
| 端点 | `POST /invoke` |

**请求示例:**
```json
{
    "method": "process_text",
    "params": {
        "text": "Hello, World!",
        "language": "en"
    },
    "sender_id": "frontend_001"
}
```

### 2.5 Agent 间通信

**场景:** Agent 之间直接通信

| 场景 | 协议 | 说明 |
|------|------|------|
| 简单请求-响应 | HTTP | 适合一次性调用 |
| 实时通信 | WebSocket | 适合持续对话 |
| 去中心化通信 | P2P | 适合无中心服务器场景 |

---

## 三、协议选择建议

### 3.1 协议对比

| 协议 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **HTTP** | 简单、广泛支持、防火墙友好 | 无状态、开销较大 | REST API、一次性调用 |
| **WebSocket** | 实时、双向、低延迟 | 连接管理复杂 | 实时对话、持续通信 |
| **P2P** | 去中心化、可扩展 | NAT 穿透复杂 | 分布式系统、无服务器场景 |
| **MCP** | AI 服务标准、功能丰富 | 实现复杂 | LLM 集成、外部 AI 服务 |
| **A2A** | Agent 专用、语义丰富 | 相对小众 | Agent 间协作 |
| **gRPC** | 高性能、类型安全 | 需要 Proto 定义 | 内部服务、高性能场景 |

### 3.2 选择决策树

```
需要实时通信?
├── 是 → 需要去中心化?
│   ├── 是 → 使用 P2P
│   └── 否 → 使用 WebSocket
└── 否 → 需要 AI 服务集成?
    ├── 是 → 使用 MCP
    └── 否 → Agent 间协作?
        ├── 是 → 使用 A2A
        └── 否 → 使用 HTTP
```

### 3.3 推荐配置

**开发环境:**
```python
config = AgentConfig(
    name="my_agent",
    protocols={
        ProtocolType.HTTP: ProtocolConfig(port=5001),
    }
)
```

**生产环境:**
```python
config = AgentConfig(
    name="my_agent",
    protocols={
        ProtocolType.HTTP: ProtocolConfig(port=5001),
        ProtocolType.WEBSOCKET: ProtocolConfig(port=8765),
        ProtocolType.P2P: ProtocolConfig(port=9001),
    }
)
```

---

## 四、端点规范

### 4.1 Agent HTTP 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/` | GET | Agent 信息 |
| `/invoke` | POST | 调用技能 |
| `/chat` | POST | 聊天消息 |
| `/heartbeat` | POST | 心跳 |
| `/message` | POST | 通用消息 |
| `/skills` | GET | 技能列表 |

### 4.2 Platform API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/agent-auth/register` | POST | Agent 注册 |
| `/agent-auth/agents/{id}/heartbeat` | POST | Agent 心跳 |
| `/agent-auth/agents/{id}` | DELETE | Agent 注销 |
| `/agents` | GET | Agent 列表 |
| `/agents/{id}` | GET | Agent 详情 |
| `/demands` | POST | 创建需求 |
| `/matching` | POST | 执行撮合 |

### 4.3 WebSocket 端点

| 端点 | 说明 |
|------|------|
| `/ws/agent/{agent_id}` | Agent WebSocket 连接 |
| `/ws/platform` | Platform WebSocket 连接 |

---

## 五、消息格式

### 5.1 标准消息格式

```python
@dataclass
class Message:
    type: MessageType          # REQUEST, RESPONSE, NOTIFICATION
    sender_id: str             # 发送者 ID
    receiver_id: Optional[str] # 接收者 ID (广播时为空)
    content: Dict[str, Any]    # 消息内容
    message_id: str            # 消息唯一 ID
    timestamp: float           # 时间戳
    correlation_id: Optional[str]  # 关联 ID (用于请求-响应)
    metadata: Dict[str, Any]   # 元数据
```

### 5.2 请求消息

```json
{
    "type": "request",
    "sender_id": "agent_001",
    "receiver_id": "agent_002",
    "message_id": "msg_12345",
    "timestamp": 1708334400.0,
    "content": {
        "action": "process_data",
        "params": {
            "data": "...",
            "format": "json"
        }
    }
}
```

### 5.3 响应消息

```json
{
    "type": "response",
    "sender_id": "agent_002",
    "receiver_id": "agent_001",
    "message_id": "msg_12346",
    "correlation_id": "msg_12345",
    "timestamp": 1708334401.0,
    "content": {
        "status": "success",
        "result": {
            "processed": true,
            "output": "..."
        }
    }
}
```

### 5.4 通知消息

```json
{
    "type": "notification",
    "sender_id": "platform",
    "message_id": "notif_12345",
    "timestamp": 1708334400.0,
    "content": {
        "event": "agent_registered",
        "agent_id": "agent_003"
    }
}
```

---

## 六、错误处理

### 6.1 错误响应格式

```json
{
    "success": false,
    "error": {
        "code": "AGENT_NOT_FOUND",
        "message": "Agent with ID 'agent_001' not found",
        "details": {
            "agent_id": "agent_001"
        }
    },
    "timestamp": "2025-02-19T10:00:00Z"
}
```

### 6.2 错误代码

| 代码 | HTTP 状态码 | 说明 |
|------|------------|------|
| `AGENT_NOT_FOUND` | 404 | Agent 不存在 |
| `AGENT_INACTIVE` | 503 | Agent 未激活 |
| `INVALID_REQUEST` | 400 | 请求格式错误 |
| `UNAUTHORIZED` | 401 | 未授权 |
| `SKILL_NOT_FOUND` | 404 | 技能不存在 |
| `EXECUTION_ERROR` | 500 | 执行错误 |
| `TIMEOUT` | 504 | 超时 |

---

## 七、安全考虑

### 7.1 认证方式

| 方式 | 说明 | 适用场景 |
|------|------|---------|
| API Key | 简单密钥认证 | 开发环境 |
| JWT | 令牌认证 | 生产环境 |
| Wallet | 钱包签名认证 | 区块链场景 |

### 7.2 通信加密

- **HTTP:** 使用 HTTPS (TLS 1.2+)
- **WebSocket:** 使用 WSS (TLS 1.2+)
- **P2P:** 使用 TLS 或自定义加密

### 7.3 消息验证

```python
# 消息签名示例
def sign_message(message: Dict, private_key: str) -> str:
    import hashlib
    import hmac
    payload = json.dumps(message, sort_keys=True)
    return hmac.new(
        private_key.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
```

---

## 八、最佳实践

### 8.1 连接管理

1. **使用连接池** - 复用 HTTP 连接
2. **心跳机制** - 保持连接活跃
3. **断线重连** - 自动重连 WebSocket
4. **超时设置** - 设置合理的超时时间

### 8.2 消息处理

1. **幂等性** - 消息处理应支持重复调用
2. **异步处理** - 长时间操作使用异步
3. **消息确认** - 关键消息需要确认
4. **错误重试** - 合理的重试策略

### 8.3 性能优化

1. **批量操作** - 批量发送消息
2. **压缩** - 大消息使用压缩
3. **缓存** - 缓存常用数据
4. **限流** - 防止消息洪泛

---

*文档结束*

</details>
