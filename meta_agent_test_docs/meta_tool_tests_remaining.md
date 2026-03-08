# Meta Agent Tools 详细测试补充

---

## 测试 #58: call_api

### 测试目标
验证 UI 工具 `call_api` 能正确调用 API

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "调用API /api/test",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

### Step 2-4: 查看日志和验证
- 历史消息: `GET /api/meta-agent/history/{wallet}`
- 工具日志: `GET /api/meta-agent/debug-logs/{wallet}`

**预期日志:**
```
[TOOL_CALL] call_api called with params: {"endpoint": "/api/test", "method": "GET"}
[TOOL_RESULT] {"result": {...}, "status": "success"}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] call_api`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #61: parse_html

### 测试目标
验证 Web 工具 `parse_html` 能正确解析 HTML

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "解析HTML内容，选择器#test",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] parse_html called with params: {"html": "...", "selector": "#test"}
[TOOL_RESULT] {"content": "...", "status": "success"}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] parse_html`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #62: download_file (Web)

### 测试目标
验证 Web 工具 `download_file` 能正确下载文件

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "下载文件 http://example.com/test.zip",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] download_file called with params: {"url": "http://example.com/test.zip"}
[TOOL_RESULT] {"status": "success", "path": "..."}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] download_file`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #63: get_headers

### 测试目标
验证 Web 工具 `get_headers` 能正确获取 HTTP 头

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "获取python.org的HTTP头信息",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] get_headers called with params: {"url": "https://www.python.org/"}
[TOOL_RESULT] {"headers": {...}, "status": "success"}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] get_headers`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #76: start_vscode

### 测试目标
验证 Execution 工具 `start_vscode` 能正确启动 VSCode Server（仅Linux）

### 前提
- 运行环境: Linux
- 需要安装 VSCode Server

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "启动VSCode Server",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] start_vscode called with params: {}
[TOOL_RESULT] {"status": "success", "url": "http://localhost:8080"}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] start_vscode`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

### 注意
- Windows 环境会返回错误："VSCode Server 仅在 Linux 环境下可用"

---

## 测试 #77: stop_vscode

### 测试目标
验证 Execution 工具 `stop_vscode` 能正确停止 VSCode Server（仅Linux）

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "停止VSCode Server",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] stop_vscode called with params: {}
[TOOL_RESULT] {"status": "success"}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] stop_vscode`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #78: vscode_status

### 测试目标
验证 Execution 工具 `vscode_status` 能正确获取 VSCode 状态（仅Linux）

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查看VSCode Server状态",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] vscode_status called with params: {}
[TOOL_RESULT] {"running": true, "url": "http://localhost:8080"}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] vscode_status`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #79: parse_skill_md

### 测试目标
验证 Execution 工具 `parse_skill_md` 能正确解析技能文件

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "解析技能文件skills.md",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] parse_skill_md called with params: {"file_path": "/path/to/skills.md"}
[TOOL_RESULT] {"skills": [...], "count": 5}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] parse_skill_md`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #80: execute_skill

### 测试目标
验证 Execution 工具 `execute_skill` 能正确执行技能

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "执行技能test_skill",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] execute_skill called with params: {"skill_name": "test_skill"}
[TOOL_RESULT] {"status": "success", "result": "..."}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] execute_skill`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #81: list_skills

### 测试目标
验证 Execution 工具 `list_skills` 能正确列出所有技能

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "列出所有技能",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

**预期日志:**
```
[TOOL_CALL] list_skills called with params: {}
[TOOL_RESULT] {"skills": [...], "count": 10}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后端日志出现 `[TOOL_CALL] list_skills`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
