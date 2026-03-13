# REST API

> USMSB SDK REST API Reference

<div style="background: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0;">

**Language / 语言:** <a href="#chinese-translation">English</a> | <a href="#chinese-translation">中文</a>

*Click the link above to jump to the Chinese translation section below.*

</div>

**[English](#rest-api) | [中文](#rest-api-1)**

---

## 1. Overview

USMSB SDK provides a complete REST API for interacting with Agents and the platform.

---

## 2. API Endpoints

### 2.1 Agent Management

| Method | Endpoint | Function |
|--------|----------|----------|
| POST | `/api/v1/agents` | Register Agent |
| GET | `/api/v1/agents` | List Agents |
| GET | `/api/v1/agents/{id}` | Get Agent |
| DELETE | `/api/v1/agents/{id}` | Delete Agent |

### 2.2 Conversation

| Method | Endpoint | Function |
|--------|----------|----------|
| POST | `/api/v1/chat` | Send Message |
| GET | `/api/v1/conversations` | Get Conversation List |
| GET | `/api/v1/conversations/{id}` | Get Conversation Details |

### 2.3 Matching

| Method | Endpoint | Function |
|--------|----------|----------|
| POST | `/api/v1/matching/match` | Match Supply and Demand |
| GET | `/api/v1/matching/demands` | Get Demands |
| POST | `/api/v1/matching/supply` | Register Supply |

### 2.4 Governance

| Method | Endpoint | Function |
|--------|----------|----------|
| POST | `/api/v1/governance/proposals` | Create Proposal |
| POST | `/api/v1/governance/vote` | Vote |
| GET | `/api/v1/governance/proposals` | Get Proposals |

---

## 3. Authentication

API uses Bearer Token authentication:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.usmsb.com/v1/agents
```

---

## 4. Request/Response Format

### Request

```json
{
  "agent_id": "agent_123",
  "name": "MyAgent",
  "capabilities": ["coding", "analysis"],
  "metadata": {}
}
```

### Response

```json
{
  "success": true,
  "data": {
    "agent_id": "agent_123",
    "name": "MyAgent"
  }
}
```

---

## 5. Error Handling

| Code | Description |
|------|-------------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 404 | Not Found |
| 500 | Internal Server Error |

---

## 6. Rate Limiting

- **Default**: 100 requests per minute
- **Authenticated**: 1000 requests per minute

---

<a id="chinese-translation"></a>

<details id="chinese-translation">
<summary><h2>中文翻译 (Click to expand / 点击展开)</h2></summary>

# REST API

> USMSB SDK REST API 参考

**[English](#rest-api) | [中文](#rest-api-1)**

---

## 1. 概述

USMSB SDK 提供完整的 REST API 用于与 Agent 和平台交互。

---

## 2. API 端点

### 2.1 Agent 管理

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/v1/agents` | 注册 Agent |
| GET | `/api/v1/agents` | 列出 Agents |
| GET | `/api/v1/agents/{id}` | 获取 Agent |
| DELETE | `/api/v1/agents/{id}` | 删除 Agent |

### 2.2 对话

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/v1/chat` | 发送消息 |
| GET | `/api/v1/conversations` | 获取对话列表 |
| GET | `/api/v1/conversations/{id}` | 获取对话详情 |

### 2.3 匹配

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/v1/matching/match` | 匹配供需 |
| GET | `/api/v1/matching/demands` | 获取需求 |
| POST | `/api/v1/matching/supply` | 注册供给 |

### 2.4 治理

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/v1/governance/proposals` | 创建提案 |
| POST | `/api/v1/governance/vote` | 投票 |
| GET | `/api/v1/governance/proposals` | 获取提案 |

---

## 3. 认证

API 使用 Bearer Token 认证：

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.usmsb.com/v1/agents
```

---

## 4. 请求/响应格式

### 请求

```json
{
  "agent_id": "agent_123",
  "name": "MyAgent",
  "capabilities": ["coding", "analysis"],
  "metadata": {}
}
```

### 响应

```json
{
  "success": true,
  "data": {
    "agent_id": "agent_123",
    "name": "MyAgent"
  }
}
```

---

## 5. 错误处理

| 代码 | 描述 |
|------|------|
| 400 | 请求错误 |
| 401 | 未授权 |
| 404 | 未找到 |
| 500 | 服务器内部错误 |

---

## 6. 速率限制

- **默认**: 每分钟100次请求
- **认证后**: 每分钟1000次请求

</details>
