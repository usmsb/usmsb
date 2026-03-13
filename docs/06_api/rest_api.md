# REST API

> USMSB SDK REST API 参考

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

## 4. 相关文档

- [Python SDK](./python_sdk.md) - Python SDK使用指南
- [WebSocket API](./websocket_api.md) - WebSocket实时通信
