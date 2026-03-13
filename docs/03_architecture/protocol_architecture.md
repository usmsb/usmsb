# Protocol Architecture

> USMSB SDK Communication Protocol Architecture

**[English](#1-protocol-overview) | [中文](#1-协议概述)**

---

## 1. Protocol Overview

USMSB SDK supports multiple communication protocols to meet different scenario requirements:

| Protocol | Use Case | Features |
|----------|----------|----------|
| **A2A** | Agent-to-Agent Communication | Designed specifically for Agents |
| **MCP** | Model Context Protocol | Model Context Protocol |
| **WebSocket** | Real-time Bidirectional Communication | Low latency, persistent connection |
| **P2P** | Peer-to-Peer Communication | Decentralized |
| **gRPC** | High-Performance RPC | Efficient, type-safe |
| **HTTP** | RESTful API | General-purpose, standard |

---

## 2. Agent-to-Agent (A2A) Protocol

### 2.1 Overview

A2A protocol is designed by USMSB SDK specifically for communication between Agents.

### 2.2 Message Format

```json
{
  "id": "msg_123",
  "type": "request",
  "sender": "agent_1",
  "receiver": "agent_2",
  "action": "delegate_task",
  "payload": {
    "task": "...",
    "context": "..."
  },
  "timestamp": "2026-02-26T10:00:00Z"
}
```

### 2.3 Code Implementation

```python
# src/usmsb_sdk/protocol/a2a/
client.py  # A2A Client
server.py  # A2A Server
```

---

## 3. Model Context Protocol (MCP)

### 3.1 Overview

MCP protocol is used for context interaction between models and external systems.

### 3.2 Core Features

- Tool Calling
- Resource Access
- Prompt Management

### 3.3 Code Implementation

```python
# src/usmsb_sdk/protocol/mcp/
types.py      # Type Definitions
handler.py    # Message Handler
adapter.py    # Protocol Adapter
```

---

## 4. WebSocket Communication

### 4.1 Overview

WebSocket is used for scenarios requiring real-time bidirectional communication.

### 4.2 Features

- Persistent Connection
- Bidirectional Communication
- Heartbeat Keep-alive
- Auto Reconnection

### 4.3 Code Implementation

```python
# src/usmsb_sdk/protocol/websocket/
client.py  # WebSocket Client
server.py  # WebSocket Server
```

---

## 5. P2P Communication

### 5.1 Overview

P2P protocol is used for decentralized Agent networks.

### 5.2 Features

- Decentralization
- Peer-to-Peer Encryption
- Node Discovery
- Message Routing

### 5.3 Code Implementation

```python
# src/usmsb_sdk/protocol/p2p/
handler.py  # P2P Message Handler
```

---

## 6. gRPC

### 6.1 Overview

gRPC is used for high-performance RPC calls.

### 6.2 Features

- Efficient Serialization (Protocol Buffers)
- Streaming Support
- Type Safety

### 6.3 Code Implementation

```python
# src/usmsb_sdk/protocol/grpc/
handler.py  # gRPC Handler
```

---

## 7. HTTP/REST

### 7.1 Overview

HTTP is used for standard RESTful API interactions.

### 7.2 Code Implementation

```python
# src/usmsb_sdk/protocol/http/
client.py  # HTTP Client
server.py  # HTTP Server
```

---

## 8. Protocol Selection Guide

| Scenario | Recommended Protocol |
|----------|---------------------|
| Agent Task Delegation | A2A |
| LLM Context Interaction | MCP |
| Real-time Chat | WebSocket |
| Decentralized Network | P2P |
| High-Performance Service Calls | gRPC |
| General API | HTTP/REST |

---

## 9. Related Documentation

- [System Architecture](./system_architecture.md) - Overall System Architecture
- [REST API](../06_api/rest_api.md) - REST API Reference

<details>
<summary><h2>中文翻译</h2></summary>

# 协议架构

> USMSB SDK 通信协议架构

---

## 1. 协议概述

USMSB SDK 支持多种通信协议，以满足不同场景的需求：

| 协议 | 用途 | 特点 |
|------|------|------|
| **A2A** | Agent-to-Agent 通信 | 专门为Agent设计 |
| **MCP** | Model Context Protocol | 模型上下文协议 |
| **WebSocket** | 实时双向通信 | 低延迟、持久连接 |
| **P2P** | 点对点通信 | 去中心化 |
| **gRPC** | 高性能RPC | 高效、类型安全 |
| **HTTP** | RESTful API | 通用、标准 |

---

## 2. Agent-to-Agent (A2A) 协议

### 2.1 概述

A2A 协议是 USMSB SDK 专为 Agent 间通信设计的协议。

### 2.2 消息格式

```json
{
  "id": "msg_123",
  "type": "request",
  "sender": "agent_1",
  "receiver": "agent_2",
  "action": "delegate_task",
  "payload": {
    "task": "...",
    "context": "..."
  },
  "timestamp": "2026-02-26T10:00:00Z"
}
```

### 2.3 代码实现

```python
# src/usmsb_sdk/protocol/a2a/
client.py  # A2A 客户端
server.py  # A2A 服务器
```

---

## 3. Model Context Protocol (MCP)

### 3.1 概述

MCP 协议用于模型与外部系统之间的上下文交互。

### 3.2 核心功能

- 工具调用
- 资源访问
- 提示管理

### 3.3 代码实现

```python
# src/usmsb_sdk/protocol/mcp/
types.py      # 类型定义
handler.py    # 消息处理
adapter.py    # 协议适配器
```

---

## 4. WebSocket 通信

### 4.1 概述

WebSocket 用于需要实时双向通信的场景。

### 4.2 特性

- 持久连接
- 双向通信
- 心跳保活
- 自动重连

### 4.3 代码实现

```python
# src/usmsb_sdk/protocol/websocket/
client.py  # WebSocket 客户端
server.py  # WebSocket 服务器
```

---

## 5. P2P 通信

### 5.1 概述

P2P 协议用于去中心化的 Agent 网络。

### 5.2 特性

- 去中心化
- 点对点加密
- 节点发现
- 消息路由

### 5.3 代码实现

```python
# src/usmsb_sdk/protocol/p2p/
handler.py  # P2P 消息处理
```

---

## 6. gRPC

### 6.1 概述

gRPC 用于高性能场景的 RPC 调用。

### 6.2 特性

- 高效序列化 (Protocol Buffers)
- 流式支持
- 类型安全

### 6.3 代码实现

```python
# src/usmsb_sdk/protocol/grpc/
handler.py  # gRPC 处理
```

---

## 7. HTTP/REST

### 7.1 概述

HTTP 用于标准的 RESTful API 交互。

### 7.2 代码实现

```python
# src/usmsb_sdk/protocol/http/
client.py  # HTTP 客户端
server.py  # HTTP 服务器
```

---

## 8. 协议选择指南

| 场景 | 推荐协议 |
|------|----------|
| Agent 间任务委托 | A2A |
| LLM 上下文交互 | MCP |
| 实时聊天 | WebSocket |
| 去中心化网络 | P2P |
| 高性能服务调用 | gRPC |
| 通用 API | HTTP/REST |

---

## 9. 相关文档

- [系统架构](./system_architecture.md) - 整体系统架构
- [REST API](../06_api/rest_api.md) - REST API参考

</details>
