# Meta Agent Tools 测试详细文档 (续二)

---

## 测试 #25: get_user_info

### 测试目标
验证 Governance 工具 `get_user_info` 能正确获取用户信息

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查看当前用户信息",
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
[TOOL_CALL] get_user_info called with params: {"user_id": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"}
[TOOL_RESULT] {"wallet": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777", "role": "HUMAN", "vote_power": 100}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "用户信息：角色HUMAN，投票权100"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] get_user_info`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 日志包含用户信息
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含用户信息

---

## 测试 #26: delegate_vote

### 测试目标
验证 Governance 工具 `delegate_vote` 能正确委托投票权

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "将投票权委托给 0xABC123",
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
[TOOL_CALL] delegate_vote called with params: {"to": "0xABC123"}
[TOOL_RESULT] {"status": "success"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "投票权已委托给 0xABC123"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] delegate_vote`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含委托成功说明

---

## 测试 #27: get_vote_power

### 测试目标
验证 Governance 工具 `get_vote_power` 能正确获取投票权

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查看我的投票权数量",
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
[TOOL_CALL] get_vote_power called with params: {"address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"}
[TOOL_RESULT] {"vote_power": 100, "delegated": 0}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "您的投票权为 100"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] get_vote_power`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含投票权数量

---

## 测试 #28: list_user_agents

### 测试目标
验证 Governance 工具 `list_user_agents` 能正确列出用户的 Agent

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查看我注册的所有 Agent",
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
[TOOL_CALL] list_user_agents called with params: {}
[TOOL_RESULT] {"agents": [...], "count": 2}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "您共注册了 2 个 Agent"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] list_user_agents`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含 Agent 列表

---

## 测试 #29: insert_db

### 测试目标
验证 Database 工具 `insert_db` 能正确插入数据

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "在 users 表插入一条数据，name 是张三",
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
[TOOL_CALL] insert_db called with params: {"table": "users", "data": {"name": "张三"}}
[TOOL_RESULT] {"status": "success", "affected_rows": 1}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "成功插入 1 条记录"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] insert_db`
- [ ] 日志包含 table 和 data 参数
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含插入成功说明

---

## 测试 #30: update_db

### 测试目标
验证 Database 工具 `update_db` 能正确更新数据

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "更新 users 表，name 改成李四，条件是 id=1",
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
[TOOL_CALL] update_db called with params: {"table": "users", "data": {"name": "李四"}, "where": "id=1"}
[TOOL_RESULT] {"status": "success", "affected_rows": 1}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "成功更新 1 条记录"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] update_db`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含更新成功说明

---

## 测试 #31: delete_db

### 测试目标
验证 Database 工具 `delete_db` 能正确删除数据

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "删除 users 表 id=1 的记录",
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
[TOOL_CALL] delete_db called with params: {"table": "users", "where": "id=1"}
[TOOL_RESULT] {"status": "success", "affected_rows": 1}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "成功删除 1 条记录"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] delete_db`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含删除成功说明

---

## 测试 #32: manage_page

### 测试目标
验证 UI 工具 `manage_page` 能正确管理页面

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "刷新当前页面",
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
[TOOL_CALL] manage_page called with params: {"action": "refresh"}
[TOOL_RESULT] {"status": "success"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "页面已刷新"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] manage_page`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含操作成功说明

---

## 测试 #33: search_web

### 测试目标
验证 Web 工具 `search_web` 能正确搜索网页

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "搜索 Python 教程",
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
[TOOL_CALL] search_web called with params: {"query": "Python 教程"}
[TOOL_RESULT] {"results": [...], "count": 10}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "搜索到 10 条结果..."
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] search_web`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含搜索结果

---

## 测试 #34: fetch_url

### 测试目标
验证 Web 工具 `fetch_url` 能正确获取网页内容

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "获取 python.org 网站内容",
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
[TOOL_CALL] fetch_url called with params: {"url": "https://www.python.org/"}
[TOOL_RESULT] {"status_code": 200, "content": "...", "content_length": 48604}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "已获取 python.org 内容，长度 48604 字节"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] fetch_url`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含网页内容

---

## 测试 #35: switch_chain

### 测试目标
验证 Blockchain 工具 `switch_chain` 能正确切换链

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "切换到比特币链",
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
[TOOL_CALL] switch_chain called with params: {"chain": "bitcoin"}
[TOOL_RESULT] {"status": "success", "chain": "bitcoin"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "已成功切换到比特币链"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] switch_chain`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含切换成功说明

---

## 测试 #36: unstake

### 测试目标
验证 Blockchain 工具 `unstake` 能正确解除质押

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "解除质押 50 代币",
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
[TOOL_CALL] unstaking called with params: {"amount": 50}
[TOOL_RESULT] {"status": "success"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "成功解除质押 50 代币"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] unstaking`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含解除质押成功说明
