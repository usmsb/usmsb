# Meta Agent Tools 完整测试文档

## 文档版本
- 版本: 1.0
- 创建日期: 2026-03-03
- 钱包地址: `0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777`

---

## 第一部分：测试环境与启动

### 1.1 环境准备

#### 启动 Meta Agent 后端
```bash
cd usmsb-sdk
python run_server.py
```
- 服务地址: `http://localhost:8000`
- Chat API: `POST http://localhost:8000/api/chat`
- 历史消息API: `GET http://localhost:8000/api/meta-agent/history/{wallet_address}`
- 日志API: `GET http://localhost:8000/api/meta-agent/debug-logs/{wallet_address}`

#### 启动 Software Dev Demo
```bash
cd usmsb-sdk/demo/software_dev
python run_demo.py
```

**预期输出:**
```
✅ ProductOwner (产品经理 AI Agent)
✅ Architect (架构师 AI Agent)  
✅ Developer (开发者 AI Agent)
✅ Reviewer (代码审查 AI Agent)
✅ DevOps (运维 AI Agent)

共 5 个 Agent
```

---

## 第二部分：每个测试的通用步骤

### 通用验证流程

#### Step 1: 发送 Chat 请求
```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "测试消息",
    "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
  }'
```

#### Step 2: 查看后台任务状态
```bash
curl "http://localhost:8000/api/meta-agent/history/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

**验证:**
- [ ] 出现 `background_task` 角色（任务开始）
- [ ] 出现 `background_complete` 角色（任务完成）

#### Step 3: 查看工具调用日志
```bash
curl "http://localhost:8000/api/meta-agent/debug-logs/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
```

**验证:**
- [ ] 出现 `[TOOL_CALL] 工具名 called with params: {...}`
- [ ] 日志包含正确的参数
- [ ] 出现 `[TOOL_RESULT] {...}`
- [ ] 日志包含正确的返回数据

#### Step 4: 验证返回结果
**验证:**
- [ ] Chat API 返回 `success: true`
- [ ] LLM 生成了自然语言回复

---

## 第三部分：工具测试详细列表

### 3.1 Monitor 工具 (4个)

| # | 工具名称 | 测试消息 |
|---|---------|---------|
| 1 | health_check | "检查系统健康状态" |
| 2 | get_system_metrics | "查看系统资源使用情况" |
| 3 | get_alerts | "查看系统告警" |
| 4 | set_threshold | "设置阈值为 0.8" |

### 3.2 System Agents 工具 (11个)

| # | 工具名称 | 测试消息 |
|---|---------|---------|
| 5 | recommend_agents | "推荐适合做Web开发的Agent" |
| 6 | search_agents | "搜索擅长Python开发的开发者Agent" |
| 7 | rate_agent | "给Developer Agent评分5分" |
| 8 | get_recommendation_history | "查看推荐历史记录" |
| 9 | route_message | "发送消息给用户user1" |
| 10 | get_load_balance_status | "查看系统负载均衡状态" |
| 11 | get_route_info | "查看路由信息" |
| 12 | get_system_health | "查看系统健康状态" |
| 13 | get_system_metrics | "查看系统指标" |
| 14 | query_logs | "查询最近的系统日志" |

### 3.3 Precise Matching 工具 (12个)

| # | 工具名称 | 测试消息 |
|---|---------|---------|
| 15 | get_agent_profile | "查看Developer Agent的详细信息" |
| 16 | get_all_agent_profiles | "列出所有可用的Agent" |
| 17 | recommend_agents_for_demand | "推荐适合做登录功能的Agent" |
| 18 | match_by_gene_capsule | "通过基因匹配查找Agent" |
| 19 | generate_recommendation_explanation | "生成推荐解释" |
| 20 | proactively_notify_opportunity | "通知有新的合作机会" |
| 21 | scan_opportunities | "扫描有哪些合作机会" |
| 22 | auto_match_and_notify | "执行自动匹配并通知" |
| 23 | consult_agent | "咨询Developer Agent，如何优化数据库" |
| 24 | interview_agent | "面试Developer Agent" |
| 25 | send_agent_message | "给Developer Agent发送消息" |
| 26 | receive_agent_showcase | "接收展示ID showcase-001" |

### 3.4 Blockchain 工具 (8个)

| # | 工具名称 | 测试消息 |
|---|---------|---------|
| 27 | create_wallet | "帮我创建一个区块链钱包" |
| 28 | get_balance | "查询我的钱包余额" |
| 29 | stake | "质押100代币" |
| 30 | unstake | "解除质押50代币" |
| 31 | vote | "给提案1投赞成票" |
| 32 | submit_proposal | "提交一个测试提案" |
| 33 | switch_chain | "切换到比特币链" |
| 34 | get_chain_info | "查看当前区块链信息" |

### 3.5 Governance 工具 (5个)

| # | 工具名称 | 测试消息 |
|---|---------|---------|
| 35 | get_user_info | "查看当前用户信息" |
| 36 | list_user_agents | "查看我注册的所有Agent" |
| 37 | delegate_vote | "将投票权委托给0xABC123" |
| 38 | get_vote_power | "查看我的投票权数量" |
| 39 | list_proposals | "列出所有治理提案" |

### 3.6 Platform 工具 (9个)

| # | 工具名称 | 测试消息 |
|---|---------|---------|
| 40 | start_node | "启动节点" |
| 41 | stop_node | "停止节点" |
| 42 | get_node_status | "查看节点状态" |
| 43 | get_config | "获取test配置" |
| 44 | update_config | "设置test配置值为hello" |
| 45 | bind_wallet | "绑定钱包地址0xABC123" |
| 46 | register_agent | "注册一个叫TestBot的Agent" |
| 47 | unregister_agent | "注销Agent abc123" |
| 48 | general_response | "你好" |

### 3.7 IPFS 工具 (3个)

| # | 工具名称 | 测试消息 |
|---|---------|---------|
| 49 | upload_to_ipfs | "将Hello World上传到IPFS" |
| 50 | download_from_ipfs | "从IPFS下载内容，CID是QmTest123" |
| 51 | sync_to_ipfs | "同步/test目录到IPFS" |

### 3.8 Database 工具 (4个)

| # | 工具名称 | 测试消息 |
|---|---------|---------|
| 52 | query_db | "查询所有用户数据" |
| 53 | insert_db | "在users表插入一条数据" |
| 54 | update_db | "更新users表name为李四" |
| 55 | delete_db | "删除users表id=1的记录" |

### 3.9 UI 工具 (3个)

| # | 工具名称 | 测试消息 |
|---|---------|---------|
| 56 | generate_component | "生成一个登录按钮组件" |
| 57 | manage_page | "刷新当前页面" |
| 58 | call_api | "调用API /api/test" |

### 3.10 Web 工具 (5个)

| # | 工具名称 | 测试消息 |
|---|---------|---------|
| 59 | search_web | "搜索Python教程" |
| 60 | fetch_url | "获取python.org网站内容" |
| 61 | parse_html | "解析HTML内容，选择器#test" |
| 62 | download_file | "下载文件 http://example.com/test.zip" |
| 63 | get_headers | "获取python.org的HTTP头" |

### 3.11 Execution 工具 (12个)

| # | 工具名称 | 测试消息 | 备注 |
|---|---------|---------|------|
| 64 | execute_python | "执行Python代码，计算1+1" | |
| 65 | run_command | "执行命令echo hello" | |
| 66 | browser_open | "打开浏览器访问python.org" | |
| 67 | browser_click | "点击登录按钮#login" | |
| 68 | browser_fill | "在输入框填写用户名testuser" | |
| 69 | browser_get_content | "获取当前页面内容" | |
| 70 | browser_screenshot | "截取当前页面截图" | |
| 71 | browser_close | "关闭浏览器" | |
| 72 | execute_javascript | "执行JavaScript代码console.log(1+1)" | |
| 73 | start_jupyter | "启动JupyterLab" | |
| 74 | jupyter_status | "查看JupyterLab状态" | |
| 75 | stop_jupyter | "停止JupyterLab" | |

### 3.12 VSCode 工具 (3个，仅Linux)

| # | 工具名称 | 测试消息 | 备注 |
|---|---------|---------|------|
| 76 | start_vscode | "启动VSCode" | 仅Linux |
| 77 | stop_vscode | "停止VSCode" | 仅Linux |
| 78 | vscode_status | "查看VSCode状态" | 仅Linux |

### 3.13 Skill 工具 (3个)

| # | 工具名称 | 测试消息 |
|---|---------|---------|
| 79 | parse_skill_md | "解析技能文件skills.md" |
| 80 | execute_skill | "执行技能test_skill" |
| 81 | list_skills | "列出所有技能" |

---

## 第四部分：业务场景测试

### 场景1: 开发一个用户管理系统

| 阶段 | Chat消息 | 调用工具 |
|------|---------|---------|
| 需求分析 | "创建一个用户管理系统" | send_agent_message → ProductOwner |
| 架构设计 | "设计用户管理系统架构" | send_agent_message → Architect |
| 开发实现 | "实现用户登录API" | send_agent_message → Developer |
| 代码审查 | "审查用户登录代码" | send_agent_message → Reviewer |
| 部署上线 | "部署用户管理系统" | send_agent_message → DevOps |

### 场景2: Agent协作测试

| 测试项 | Chat消息 | 调用工具 |
|--------|---------|---------|
| 搜索Agent | "搜索Python开发者" | search_agents |
| 推荐Agent | "推荐Web开发Agent" | recommend_agents |
| 咨询Agent | "咨询Developer如何优化数据库" | consult_agent |
| 评价Agent | "给Developer评分5分" | rate_agent |
| 查看档案 | "查看Developer档案" | get_agent_profile |

---

## 第五部分：测试验证检查清单

### 5.1 API调用验证
- [ ] Chat API 返回 `success: true`
- [ ] Chat API 返回 `response` 字段非空

### 5.2 后台任务验证
- [ ] 历史消息中出现 `background_task` 角色
- [ ] 历史消息中出现 `background_complete` 角色

### 5.3 工具日志验证
- [ ] 出现 `[TOOL_CALL] 工具名 called with params:`
- [ ] params 包含正确的参数值
- [ ] 出现 `[TOOL_RESULT]`
- [ ] result 包含预期的返回数据

### 5.4 结果验证
- [ ] LLM 生成了自然语言回复
- [ ] 回复内容与工具结果一致

---

## 第六部分：问题记录表

| # | 测试编号 | 问题描述 | 严重程度 | 状态 |
|---|---------|---------|---------|------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

---

## 第七部分：测试结果汇总

| 类别 | 总数 | 通过 | 失败 | 通过率 |
|------|------|------|------|--------|
| Monitor | 4 | | | |
| System Agents | 11 | | | |
| Precise Matching | 12 | | | |
| Blockchain | 8 | | | |
| Governance | 5 | | | |
| Platform | 9 | | | |
| IPFS | 3 | | | |
| Database | 4 | | | |
| UI | 3 | | | |
| Web | 5 | | | |
| Execution | 12 | | | |
| VSCode | 3 | | | |
| Skill | 3 | | | |
| **总计** | **~81** | | | |
