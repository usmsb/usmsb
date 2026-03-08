# Meta Agent Tools 测试详细文档

## 测试公共信息

### 环境准备
- **后端启动**: `cd usmsb-sdk && python run_server.py`
- **Demo启动**: `cd usmsb-sdk/demo/software_dev && python run_demo.py`
- **Chat API**: `POST http://localhost:8000/api/chat`
- **历史消息API**: `GET http://localhost:8000/api/meta-agent/history/{wallet_address}`
- **日志API**: `GET http://localhost:8000/api/meta-agent/debug-logs/{wallet_address}`
- **钱包地址**: `0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777`

### 日志查看方法

#### 方法1: 后端控制台
- 在后端运行的控制台窗口查看输出
- 搜索 `[TOOL_CALL]` - 工具调用
- 搜索 `[TOOL_RESULT]` - 工具返回结果
- 搜索 `[BACKGROUND]` - 后台任务日志

#### 方法2: 日志API
```bash
# 查看所有调试日志
curl "http://localhost:8000/api/meta-agent/debug-logs/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

#### 方法3: 历史消息API
```bash
# 查看对话历史（包括后台任务状态）
curl "http://localhost:8000/api/meta-agent/history/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

### 后台任务验证要点
由于 Chat 启用后台任务执行 tool，需要验证：
1. **任务提交** - Chat API 立即返回 "任务已提交"
2. **任务开始** - 历史消息中出现 `background_task` 角色消息
3. **任务执行** - 调试日志中出现 `[TOOL_CALL]` 和 `[TOOL_RESULT]`
4. **任务完成** - 历史消息中出现 `background_complete` 角色消息，包含最终结果
5. **结果正确** - 后台任务返回的结果与 Tool 输出一致

### 日志格式说明
- `[TOOL_CALL]` - 工具被调用时输出，包含工具名称和参数
- `[TOOL_RESULT]` - 工具执行完成后输出，包含返回结果
- `[BACKGROUND]` - 后台任务执行日志

---

## 测试 #1: health_check

### 测试目标
验证 Monitor 工具 `health_check` 能正确执行并返回系统健康状态

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "检查系统健康状态",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期Chat API响应:**
```json
{
  "success": true,
  "response": "任务已提交后台执行，请稍候..."
}
```
或直接返回结果（简单任务可能同步执行）

### Step 2: 查看后台任务状态
等待几秒后，查询历史消息:
```bash
curl "http://localhost:8000/api/meta-agent/history/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

**预期历史消息:**
- 找到 `background_task` 角色的消息（任务开始）
- 找到 `background_complete` 角色的消息（任务完成，包含最终结果）

### Step 3: 查看工具调用日志
```bash
curl "http://localhost:8000/api/meta-agent/debug-logs/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

**预期日志:**
```
[TOOL_CALL] health_check called with params: {}
[TOOL_RESULT] {"status": "healthy", "target": "system"}
```

### Step 4: 验证返回结果
Chat API 响应或历史消息中的 `background_complete` 应包含:
```json
{
  "status": "success",
  "response": "系统当前状态为 healthy，所有服务运行正常。"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务已提交（出现任务提交消息或直接返回结果）
- [ ] 历史消息中出现 `background_task` 角色（任务开始）
- [ ] 后端日志出现 `[TOOL_CALL] health_check`
- [ ] 日志包含 `params: {}`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 日志包含 `status: healthy`
- [ ] 历史消息中出现 `background_complete` 角色（任务完成）
- [ ] 最终结果包含健康状态说明

---

## 测试 #2: get_system_metrics

### 测试目标
验证 Monitor 工具 `get_system_metrics` 能正确执行并返回系统指标

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查看系统资源使用情况，CPU和内存",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

### Step 2: 查看后台任务状态
```bash
curl "http://localhost:8000/api/meta-agent/history/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

### Step 3: 查看工具调用日志
```bash
curl "http://localhost:8000/api/meta-agent/debug-logs/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

**预期日志:**
```
[TOOL_CALL] get_system_metrics called with params: {}
[TOOL_RESULT] {"cpu": 45.5, "memory": 62.3, "disk": 38.1}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "当前系统资源使用情况：CPU 45.5%，内存使用 62.3%，磁盘使用 38.1%。"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] get_system_metrics`
- [ ] 日志包含 `cpu`, `memory`, `disk` 字段
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含系统指标说明

---

## 测试 #3: search_agents

### 测试目标
验证 System Agents 工具 `search_agents` 能正确搜索 Agent

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "搜索擅长 Python 开发的开发者 Agent",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

### Step 2: 查看后台任务状态
```bash
curl "http://localhost:8000/api/meta-agent/history/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

### Step 3: 查看工具调用日志
```bash
curl "http://localhost:8000/api/meta-agent/debug-logs/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

**预期日志:**
```
[TOOL_CALL] search_agents called with params: {"query": "python"}
[TOOL_RESULT] {"results": [...], "count": 1}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "我找到了擅长 Python 开发的 Agent"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] search_agents`
- [ ] 日志包含正确的 query 参数
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 日志包含搜索结果
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含搜索结果说明

---

## 测试 #4: send_agent_message

### 测试目标
验证 Precise Matching 工具 `send_agent_message` 能正确发送消息给 Agent

### 前置条件
- Demo 已启动，Developer Agent 运行中

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "给 Developer Agent 发送消息，询问如何实现用户登录功能",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

### Step 2: 查看后台任务状态
```bash
curl "http://localhost:8000/api/meta-agent/history/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

**预期历史消息:**
- 包含 `background_task` 消息
- 包含 `background_complete` 消息，结果为 Developer 的回复

### Step 3: 查看工具调用日志
```bash
curl "http://localhost:8000/api/meta-agent/debug-logs/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

**预期日志:**
```
[TOOL_CALL] send_agent_message called with params: {"agent_id": "Developer", "message": "如何实现用户登录功能"}
[TOOL_RESULT] {"status": "success", "response": "实现用户登录功能需要..."}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "Developer 回复：实现用户登录功能需要..."
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] send_agent_message`
- [ ] 日志包含 agent_id 和 message 参数
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 日志包含 status: success
- [ ] 日志包含 Developer 的响应
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含 Developer 回复

---

## 测试 #5: get_agent_profile

### 测试目标
验证 Precise Matching 工具 `get_agent_profile` 能正确获取 Agent 档案

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查看 Developer Agent 的详细信息和能力",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

### Step 2: 查看后台任务状态
```bash
curl "http://localhost:8000/api/meta-agent/history/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

### Step 3: 查看工具调用日志
```bash
curl "http://localhost:8000/api/meta-agent/debug-logs/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

**预期日志:**
```
[TOOL_CALL] get_agent_profile called with params: {"agent_id": "Developer"}
[TOOL_RESULT] {"agent_id": "Developer", "name": "Developer", "capabilities": [...], "rating": 4.5}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "Developer Agent 的档案如下：..."
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] get_agent_profile`
- [ ] 日志包含 agent_id 参数
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 日志包含完整的 Agent 档案信息
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含档案详细说明

---

## 测试 #6: rate_agent

### 测试目标
验证 System Agents 工具 `rate_agent` 能正确评价 Agent

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "给 Developer Agent 评分 5 分，评价很棒",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

### Step 2: 查看后台任务状态
```bash
curl "http://localhost:8000/api/meta-agent/history/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

### Step 3: 查看工具调用日志
```bash
curl "http://localhost:8000/api/meta-agent/debug-logs/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

**预期日志:**
```
[TOOL_CALL] rate_agent called with params: {"agent_id": "Developer", "rating": 5, "reviewer_id": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777", "comment": "很棒"}
[TOOL_RESULT] {"status": "success", "rating": 5}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "已成功给 Developer Agent 打出 5 分评价。"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] rate_agent`
- [ ] 日志包含 agent_id 和 rating 参数
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 日志包含 status: success
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含评分成功说明

---

## 测试 #7: recommend_agents

### 测试目标
验证 System Agents 工具 `recommend_agents` 能正确推荐 Agent

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "推荐适合做 Web 开发的 Agent",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

### Step 2: 查看后台任务状态
```bash
curl "http://localhost:8000/api/meta-agent/history/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

### Step 3: 查看工具调用日志
```bash
curl "http://localhost:8000/api/meta-agent/debug-logs/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

**预期日志:**
```
[TOOL_CALL] recommend_agents called with params: {"query": "web development"}
[TOOL_RESULT] {"results": [...], "count": 2}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "我推荐以下适合 Web 开发的 Agent：..."
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] recommend_agents`
- [ ] 日志包含正确的 query 参数
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 日志包含推荐结果列表
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含推荐说明

---

## 测试 #8: create_wallet

### 测试目标
验证 Blockchain 工具 `create_wallet` 能正确创建钱包

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "帮我创建一个区块链钱包",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

### Step 2: 查看后台任务状态
```bash
curl "http://localhost:8000/api/meta-agent/history/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

### Step 3: 查看工具调用日志
```bash
curl "http://localhost:8000/api/meta-agent/debug-logs/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

**预期日志:**
```
[TOOL_CALL] create_wallet called with params: {}
[TOOL_RESULT] {"address": "0x...", "chain": "ethereum", "status": "created"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "已成功创建以太坊钱包，地址：0x..."
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] create_wallet`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 日志包含钱包地址
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含创建成功说明

---

## 测试 #9: get_balance

### 测试目标
验证 Blockchain 工具 `get_balance` 能正确查询余额

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查询我的钱包余额",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

### Step 2: 查看后台任务状态
```bash
curl "http://localhost:8000/api/meta-agent/history/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

### Step 3: 查看工具调用日志
```bash
curl "http://localhost:8000/api/meta-agent/debug-logs/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

**预期日志:**
```
[TOOL_CALL] get_balance called with params: {"address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"}
[TOOL_RESULT] {"balance": 100.0, "symbol": "VIBE"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "您的钱包余额为 100.0 VIBE"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] get_balance`
- [ ] 日志包含正确的 address 参数
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 日志包含 balance 和 symbol
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含余额说明

---

## 测试 #10: upload_to_ipfs

### 测试目标
验证 IPFS 工具 `upload_to_ipfs` 能正确上传内容

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "将 Hello World 上传到 IPFS",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

### Step 2: 查看后台任务状态
```bash
curl "http://localhost:8000/api/meta-agent/history/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

### Step 3: 查看工具调用日志
```bash
curl "http://localhost:8000/api/meta-agent/debug-logs/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

**预期日志:**
```
[TOOL_CALL] upload_to_ipfs called with params: {"content": "Hello World"}
[TOOL_RESULT] {"cid": "Qm...", "size": 11, "status": "success"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "内容已成功上传到 IPFS，CID: Qm..."
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] upload_to_ipfs`
- [ ] 日志包含 content 参数
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 日志包含 IPFS CID
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含上传成功说明

---

## 测试 #11: query_db

### 测试目标
验证 Database 工具 `query_db` 能正确执行查询

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查询所有用户数据",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

### Step 2: 查看后台任务状态
```bash
curl "http://localhost:8000/api/meta-agent/history/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

### Step 3: 查看工具调用日志
```bash
curl "http://localhost:8000/api/meta-agent/debug-logs/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

**预期日志:**
```
[TOOL_CALL] query_db called with params: {"query": "SELECT * FROM users"}
[TOOL_RESULT] {"rows": [...], "count": 10}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "查询结果：..."
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] query_db`
- [ ] 日志包含 SQL 查询语句
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 日志包含查询结果
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含查询结果说明

---

## 测试 #12: generate_component

### 测试目标
验证 UI 工具 `generate_component` 能正确生成 UI 组件

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "生成一个登录按钮组件",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

### Step 2: 查看后台任务状态
```bash
curl "http://localhost:8000/api/meta-agent/history/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

### Step 3: 查看工具调用日志
```bash
curl "http://localhost:8000/api/meta-agent/debug-logs/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

**预期日志:**
```
[TOOL_CALL] generate_component called with params: {"component_name": "Button"}
[TOOL_RESULT] {"code": "<button>登录</button>", "status": "success"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "已生成登录按钮组件：<button>登录</button>"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] generate_component`
- [ ] 日志包含 component_name 参数
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 日志包含生成的代码
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含生成的组件代码
