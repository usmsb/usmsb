# Meta Agent Tools 测试详细文档 (续)

---

## 测试 #13: get_recommendation_history

### 测试目标
验证 System Agents 工具 `get_recommendation_history` 能正确返回推荐历史

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查看我的推荐历史记录",
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
[TOOL_CALL] get_recommendation_history called with params: {}
[TOOL_RESULT] {"history": [...], "count": 5}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "您有 5 条推荐历史记录"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] get_recommendation_history`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 日志包含历史记录
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含历史记录说明

---

## 测试 #14: get_load_balance_status

### 测试目标
验证 System Agents 工具 `get_load_balance_status` 能正确返回负载状态

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查看系统负载均衡状态",
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
[TOOL_CALL] get_load_balance_status called with params: {}
[TOOL_RESULT] {"status": "balanced", "servers": [...]}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "系统负载均衡状态：balanced"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] get_load_balance_status`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含负载状态

---

## 测试 #15: query_logs

### 测试目标
验证 System Agents 工具 `query_logs` 能正确查询日志

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查询最近的系统日志",
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
[TOOL_CALL] query_logs called with params: {}
[TOOL_RESULT] {"logs": [...], "count": 100}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "查询到 100 条日志记录"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] query_logs`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含日志信息

---

## 测试 #16: get_all_agent_profiles

### 测试目标
验证 Precise Matching 工具 `get_all_agent_profiles` 能正确获取所有 Agent 档案

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "列出所有可用的 Agent",
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
[TOOL_CALL] get_all_agent_profiles called with params: {}
[TOOL_RESULT] {"profiles": [...], "count": 5}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "共有 5 个 Agent 可用"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] get_all_agent_profiles`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含所有 Agent 列表

---

## 测试 #17: consult_agent

### 测试目标
验证 Precise Matching 工具 `consult_agent` 能正确咨询 Agent

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "咨询 Developer Agent，如何优化数据库查询性能",
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
[TOOL_CALL] consult_agent called with params: {"agent_id": "Developer", "question": "如何优化数据库查询性能"}
[TOOL_RESULT] {"response": "优化数据库查询性能的方法：..."}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "Developer 建议：优化数据库查询性能的方法：..."
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] consult_agent`
- [ ] 日志包含 agent_id 和 question 参数
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含咨询答复

---

## 测试 #18: scan_opportunities

### 测试目标
验证 Precise Matching 工具 `scan_opportunities` 能正确扫描机会

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "扫描有哪些合作机会",
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
[TOOL_CALL] scan_opportunities called with params: {}
[TOOL_RESULT] {"opportunities": [...], "count": 3}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "发现 3 个合作机会"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] scan_opportunities`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含机会列表

---

## 测试 #19: stake

### 测试目标
验证 Blockchain 工具 `stake` 能正确质押代币

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "质押 100 代币",
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
[TOOL_CALL] stake called with params: {"amount": 100}
[TOOL_RESULT] {"status": "success", "amount": 100}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "成功质押 100 代币"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] stake`
- [ ] 日志包含 amount 参数
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含质押成功说明

---

## 测试 #20: vote

### 测试目标
验证 Blockchain 工具 `vote` 能正确投票

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "给提案 1 投赞成票",
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
[TOOL_CALL] vote called with params: {"proposal_id": "1", "vote": "yes"}
[TOOL_RESULT] {"status": "success", "proposal_id": "1"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "成功给提案 1 投了赞成票"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] vote`
- [ ] 日志包含 proposal_id 和 vote 参数
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含投票成功说明

---

## 测试 #21: submit_proposal

### 测试目标
验证 Blockchain 工具 `submit_proposal` 能正确提交提案

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "提交一个提案，标题是测试提案，内容是测试内容",
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
[TOOL_CALL] submit_proposal called with params: {"title": "测试提案", "description": "测试内容"}
[TOOL_RESULT] {"status": "success", "proposal_id": "prop_123"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "提案提交成功，提案ID：prop_123"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] submit_proposal`
- [ ] 日志包含 title 和 description 参数
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含提案ID

---

## 测试 #22: get_chain_info

### 测试目标
验证 Blockchain 工具 `get_chain_info` 能正确获取链信息

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查看当前区块链信息",
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
[TOOL_CALL] get_chain_info called with params: {}
[TOOL_RESULT] {"chain": "ethereum", "block_number": 12345678}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "当前链：以太坊，区块高度：12345678"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] get_chain_info`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 日志包含 chain 和 block_number
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含链信息

---

## 测试 #23: download_from_ipfs

### 测试目标
验证 IPFS 工具 `download_from_ipfs` 能正确下载内容

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "从 IPFS 下载内容，CID 是 QmTest123",
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
[TOOL_CALL] download_from_ipfs called with params: {"cid": "QmTest123"}
[TOOL_RESULT] {"content": "...", "cid": "QmTest123"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "已从 IPFS 下载内容"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] download_from_ipfs`
- [ ] 日志包含 cid 参数
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含下载内容

---

## 测试 #24: list_proposals

### 测试目标
验证 Governance 工具 `list_proposals` 能正确列出提案

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "列出所有治理提案",
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
[TOOL_CALL] list_proposals called with params: {}
[TOOL_RESULT] {"proposals": [...], "count": 3}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "共有 3 个治理提案"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] list_proposals`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含提案列表
