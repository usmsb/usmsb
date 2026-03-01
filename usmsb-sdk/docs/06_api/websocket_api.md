# WebSocket API

> WebSocket 实时通信

---

## 1. 概述

WebSocket API 提供实时双向通信能力。

---

## 2. 连接

```
ws://api.usmsb.com/ws?token=YOUR_TOKEN
```

---

## 3. 消息格式

### 3.1 发送消息

```json
{
  "type": "message",
  "content": "Hello Agent",
  "conversation_id": "conv_123"
}
```

### 3.2 接收消息

```json
{
  "type": "message",
  "content": "Hello! How can I help?",
  "from": "agent_1"
}
```

---

## 4. 事件

| 事件 | 说明 |
|------|------|
| `message` | 消息事件 |
| `typing` | 正在输入 |
| `online` | Agent上线 |
| `offline` | Agent下线 |
