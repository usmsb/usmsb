# Meta Agent Tools 测试详细文档 (续三)

---

## 测试 #37: execute_python

### 测试目标
验证 Execution 工具 `execute_python` 能正确执行 Python 代码

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "执行 Python 代码，计算 1+1",
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
[TOOL_CALL] execute_python called with params: {"code": "1+1"}
[TOOL_RESULT] {"status": "success", "stdout": "2\n", "result": 2}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "代码执行结果：2"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] execute_python`
- [ ] 日志包含 code 参数
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 日志包含执行结果
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含代码执行结果

---

## 测试 #38: run_command

### 测试目标
验证 Execution 工具 `run_command` 能正确执行命令行

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "执行命令 echo hello",
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
[TOOL_CALL] run_command called with params: {"command": "echo hello"}
[TOOL_RESULT] {"status": "success", "stdout": "hello\n", "success": true}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "命令执行结果：hello"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] run_command`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含命令输出

---

## 测试 #39: browser_open

### 测试目标
验证 Execution 工具 `browser_open` 能正确打开浏览器

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "打开浏览器访问 python.org",
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
[TOOL_CALL] browser_open called with params: {"url": "https://www.python.org/"}
[TOOL_RESULT] {"status": "success", "url": "https://www.python.org/"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "已打开浏览器，访问 python.org"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] browser_open`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
- [ ] 最终结果包含打开成功说明

---

## 测试 #40: browser_click

### 测试目标
验证 Execution 工具 `browser_click` 能正确点击元素

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "点击登录按钮，选择器 #login",
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
[TOOL_CALL] browser_click called with params: {"selector": "#login"}
[TOOL_RESULT] {"status": "success"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "已点击元素 #login"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] browser_click`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #41: browser_fill

### 测试目标
验证 Execution 工具 `browser_fill` 能正确填写表单

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "在输入框填写用户名，输入值是 testuser",
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
[TOOL_CALL] browser_fill called with params: {"selector": "input[name=username]", "value": "testuser"}
[TOOL_RESULT] {"status": "success"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "已填写表单"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] browser_fill`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #42: browser_get_content

### 测试目标
验证 Execution 工具 `browser_get_content` 能正确获取页面内容

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "获取当前页面内容",
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
[TOOL_CALL] browser_get_content called with params: {}
[TOOL_RESULT] {"status": "success", "content": "<html>..."}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "已获取页面内容"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] browser_get_content`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #43: browser_screenshot

### 测试目标
验证 Execution 工具 `browser_screenshot` 能正确截图

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "截取当前页面截图",
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
[TOOL_CALL] browser_screenshot called with params: {}
[TOOL_RESULT] {"status": "success", "path": "/path/to/screenshot.png"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "截图已保存"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] browser_screenshot`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #44: browser_close

### 测试目标
验证 Execution 工具 `browser_close` 能正确关闭浏览器

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "关闭浏览器",
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
[TOOL_CALL] browser_close called with params: {}
[TOOL_RESULT] {"status": "success"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "浏览器已关闭"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] browser_close`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #45: execute_javascript

### 测试目标
验证 Execution 工具 `execute_javascript` 能正确执行 JavaScript

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "执行 JavaScript 代码 console.log(1+1)",
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
[TOOL_CALL] execute_javascript called with params: {"code": "console.log(1+1)"}
[TOOL_RESULT] {"status": "success", "stdout": "2\n"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "JavaScript 执行结果：2"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] execute_javascript`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #46: start_jupyter

### 测试目标
验证 Execution 工具 `start_jupyter` 能正确启动 Jupyter

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "启动 JupyterLab",
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
[TOOL_CALL] start_jupyter called with params: {"port": 8888}
[TOOL_RESULT] {"status": "success", "jupyter_url": "http://localhost:8888/lab?token=..."}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "JupyterLab 已启动，访问地址：http://localhost:8888/lab"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] start_jupyter`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #47: jupyter_status

### 测试目标
验证 Execution 工具 `jupyter_status` 能正确获取 Jupyter 状态

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查看 JupyterLab 状态",
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
[TOOL_CALL] jupyter_status called with params: {"port": 8888}
[TOOL_RESULT] {"status": "success", "running": true}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "JupyterLab 正在运行"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] jupyter_status`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #48: stop_jupyter

### 测试目标
验证 Execution 工具 `stop_jupyter` 能正确停止 Jupyter

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "停止 JupyterLab",
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
[TOOL_CALL] stop_jupyter called with params: {}
[TOOL_RESULT] {"status": "success"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "JupyterLab 已停止"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] stop_jupyter`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #49: get_alerts

### 测试目标
验证 Monitor 工具 `get_alerts` 能正确获取告警列表

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查看系统告警",
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
[TOOL_CALL] get_alerts called with params: {}
[TOOL_RESULT] {"alerts": [], "count": 0}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "当前无告警"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] get_alerts`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #50: start_node

### 测试目标
验证 Platform 工具 `start_node` 能正确启动节点

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "启动节点",
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
[TOOL_CALL] start_node called with params: {}
[TOOL_RESULT] {"status": "success", "message": "Node started"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "节点已启动"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] start_node`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #51: stop_node

### 测试目标
验证 Platform 工具 `stop_node` 能正确停止节点

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "停止节点",
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
[TOOL_CALL] stop_node called with params: {}
[TOOL_RESULT] {"status": "success", "message": "Node stopped"}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "节点已停止"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] stop_node`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`

---

## 测试 #52: get_node_status

### 测试目标
验证 Platform 工具 `get_node_status` 能正确获取节点状态

### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查看节点状态",
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
[TOOL_CALL] get_node_status called with params: {}
[TOOL_RESULT] {"status": "running", "cpu": 50, "memory": 60}
```

### Step 4: 验证返回结果
**预期最终响应:**
```json
{
  "status": "success",
  "response": "节点状态：running，CPU 50%，内存 60%"
}
```

### 验证清单
- [ ] Chat API 返回成功
- [ ] 后台任务正常执行
- [ ] 后端日志出现 `[TOOL_CALL] get_node_status`
- [ ] 后端日志出现 `[TOOL_RESULT]`
- [ ] 历史消息中出现 `background_complete`
