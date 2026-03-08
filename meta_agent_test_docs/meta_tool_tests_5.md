# Meta Agent Tools 测试详细文档 (续四)

---

## 测试 #53: get_config

### 测试目标
验证 Platform 工具 `get_config` 能正确获取配置

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "获取 test 配置",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

### Step 2-4: 查看日志和验证
- 后台任务状态: `GET /api/meta-agent/history/{wallet}`
- 工具日志: `GET /api/meta-agent/debug-logs/{wallet}`

**预期日志:**
```
[TOOL_CALL] get_config called with params: {"key": "test"}
[TOOL_RESULT] {"config": {"test": "value"}}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] get_config`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #54: update_config

### 测试目标
验证 Platform 工具 `update_config` 能正确更新配置

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "设置 test 配置值为 hello",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] update_config called with params: {"key": "test", "value": "hello"}
[TOOL_RESULT] {"status": "success"}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] update_config`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #55: bind_wallet

### 测试目标
验证 Platform 工具 `bind_wallet` 能正确绑定钱包

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "绑定钱包地址 0xABC123",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] bind_wallet called with params: {"wallet_address": "0xABC123"}
[TOOL_RESULT] {"status": "success", "wallet": "0xABC123"}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] bind_wallet`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #56: register_agent

### 测试目标
验证 Platform 工具 `register_agent` 能正确注册 Agent

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "注册一个叫 TestBot 的 Agent",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] register_agent called with params: {"name": "TestBot"}
[TOOL_RESULT] {"status": "success", "agent_id": "..."}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] register_agent`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #57: unregister_agent

### 测试目标
验证 Platform 工具 `unregister_agent` 能正确注销 Agent

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "注销 Agent abc123",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] unregister_agent called with params: {"agent_id": "abc123"}
[TOOL_RESULT] {"status": "success"}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] unregister_agent`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #58: general_response

### 测试目标
验证 Platform 工具 `general_response` 能正确返回通用响应

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "你好",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] general_response called with params: {"input": "你好"}
[TOOL_RESULT] {"response": "你好，我是助手"}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] general_response`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #59: get_system_health

### 测试目标
验证 System Agents 工具 `get_system_health` 能正确获取系统健康状态

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查看系统健康状态",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] get_system_health called with params: {}
[TOOL_RESULT] {"status": "healthy", "components": {...}}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] get_system_health`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #60: get_route_info

### 测试目标
验证 System Agents 工具 `get_route_info` 能正确获取路由信息

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查看路由信息",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] get_route_info called with params: {}
[TOOL_RESULT] {"routes": [...], "count": 5}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] get_route_info`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #61: interview_agent

### 测试目标
验证 Precise Matching 工具 `interview_agent` 能正确面试 Agent

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "面试 Developer Agent",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] interview_agent called with params: {"agent_id": "Developer"}
[TOOL_RESULT] {"questions": [...], "count": 5}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] interview_agent`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #62: recommend_agents_for_demand

### 测试目标
验证 Precise Matching 工具 `recommend_agents_for_demand` 能正确为需求推荐 Agent

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "推荐适合做登录功能的 Agent",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] recommend_agents_for_demand called with params: {"demand": "登录功能"}
[TOOL_RESULT] {"recommendations": [...], "count": 3}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] recommend_agents_for_demand`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #63: auto_match_and_notify

### 测试目标
验证 Precise Matching 工具 `auto_match_and_notify` 能正确自动匹配

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "执行自动匹配并通知",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] auto_match_and_notify called with params: {}
[TOOL_RESULT] {"matches": [...], "notified": 5}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] auto_match_and_notify`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #64: generate_recommendation_explanation

### 测试目标
验证 Precise Matching 工具 `generate_recommendation_explanation` 能正确生成推荐解释

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "生成推荐解释，推荐ID是 rec-001",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] generate_recommendation_explanation called with params: {"recommendation_id": "rec-001"}
[TOOL_RESULT] {"explanation": "..."}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] generate_recommendation_explanation`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #65: proactively_notify_opportunity

### 测试目标
验证 Precise Matching 工具 `proactively_notify_opportunity` 能正确主动通知机会

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "通知有一个新的合作机会",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] proactively_notify_opportunity called with params: {"opportunity": "..."}
[TOOL_RESULT] {"status": "notified"}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] proactively_notify_opportunity`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #66: receive_agent_showcase

### 测试目标
验证 Precise Matching 工具 `receive_agent_showcase` 能正确接收 Agent 展示

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "接收展示 ID showcase-001",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] receive_agent_showcase called with params: {"showcase_id": "showcase-001"}
[TOOL_RESULT] {"showcase": {...}}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] receive_agent_showcase`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #67: sync_to_ipfs

### 测试目标
验证 IPFS 工具 `sync_to_ipfs` 能正确同步到 IPFS

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "同步 /test 目录到 IPFS",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] sync_to_ipfs called with params: {"path": "/test"}
[TOOL_RESULT] {"status": "success", "cid": "Qm..."}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] sync_to_ipfs`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #68: set_threshold

### 测试目标
验证 Monitor 工具 `set_threshold` 能正确设置阈值

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "设置阈值为 0.8",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] set_threshold called with params: {"threshold": 0.8}
[TOOL_RESULT] {"status": "success"}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] set_threshold`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #69: route_message

### 测试目标
验证 System Agents 工具 `route_message` 能正确路由消息

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "发送消息给用户 user1，内容是 hello",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] route_message called with params: {"to": "user1", "message_type": "text", "content": "hello"}
[TOOL_RESULT] {"status": "success"}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] route_message`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #70: match_by_gene_capsule

### 测试目标
验证 Precise Matching 工具 `match_by_gene_capsule` 能正确通过基因匹配

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "通过基因匹配查找 Agent",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] match_by_gene_capsule called with params: {"gene_capsule": "..."}
[TOOL_RESULT] {"matches": [...], "count": 3}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] match_by_gene_capsule`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
