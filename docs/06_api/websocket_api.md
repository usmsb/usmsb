# WebSocket API

> WebSocket Real-time Communication

<div style="background: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0;">

**Language / 语言:** <a href="#chinese-translation">English</a> | <a href="#chinese-translation">中文</a>

*Click the link above to jump to the Chinese translation section below.*

</div>

---

<a id="chinese-translation"></a>

<details id="chinese-translation">
<summary><h2>中文翻译 (Click to expand / 点击展开)</h2></summary>

# WebSocket API

> WebSocket 实时通信

---

## 1. 概述

WebSocket API provides real-time bidirectional communication capabilities.

---

## 2. Connection

```
ws://api.usmsb.com/ws?token=YOUR_TOKEN
```

---

## 3. Message Format

### 3.1 Sending Messages

```json
{
  "type": "message",
  "content": "Hello Agent",
  "conversation_id": "conv_123"
}
```

### 3.2 Receiving Messages

```json
{
  "type": "message",
  "content": "Hello! How can I help?",
  "from": "agent_1"
}
```

---

## 4. Events

| Event | Description |
|-------|-------------|
| `message` | Message event |
| `typing` | Typing indicator |
| `online` | Agent online |
| `offline` | Agent offline |



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

</details>
