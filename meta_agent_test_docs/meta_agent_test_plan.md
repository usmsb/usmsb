# Meta Agent + Software Dev Demo 完整测试计划

## 测试目标
1. 启动 Software Dev Demo (5个Agent协作)
2. 通过 Meta Agent 的 chat 接口与 Agent 协作
3. 测试所有 Tools 在业务流程中的正确性
4. 验证结果准确

---

## 第一阶段：环境准备

### 1.1 检查环境
- [ ] Python 环境正常
- [ ] 依赖包已安装 (agent_sdk, demo 模块等)
- [ ] Meta Agent 服务可启动

### 1.2 启动 Meta Agent 服务
```bash
# 启动 meta agent 服务（后台运行）
cd usmsb-sdk/src
python run_server.py
```

---

## 第二阶段：启动 Software Dev Demo

### 2.1 运行 Demo
```bash
cd usmsb-sdk/demo/software_dev
python run_demo.py
```

### 2.2 预期输出
```
✅ ProductOwner (产品经理 AI Agent)
✅ Architect (架构师 AI Agent)  
✅ Developer (开发者 AI Agent)
✅ Reviewer (代码审查 AI Agent)
✅ DevOps (运维 AI Agent)

共 5 个 Agent
```

### 2.3 记录 Agent IDs
| Agent | Agent ID | 端口 |
|-------|----------|------|
| ProductOwner | ? | 9081 |
| Architect | ? | 9082 |
| Developer | ? | 9083 |
| Reviewer | ? | 9084 |
| DevOps | ? | 9085 |

---

## 第三阶段：Meta Agent Chat 测试

### 3.1 测试场景：创建新功能需求

**输入:**
```
"帮我创建一个用户登录功能，ProductOwner 分析需求，Architect 设计架构"
```

**预期流程:**
1. Meta Agent 调用 search_agents 找到 ProductOwner
2. Meta Agent 调用 send_agent_message 发送需求
3. ProductOwner 返回需求分析
4. Meta Agent 调用 send_agent_message 给 Architect
5. Architect 返回架构设计

**验证点:**
- [ ] search_agents 返回正确的 Agent 列表
- [ ] send_agent_message 消息发送成功
- [ ] receive_agent_showcase 收到响应

### 3.2 测试场景：代码开发

**输入:**
```
"让 Developer 实现登录 API"
```

**预期流程:**
1. Meta Agent 调用 send_agent_message 给 Developer
2. Developer 返回代码实现
3. Meta Agent 调用 rate_agent 评分

**验证点:**
- [ ] send_agent_message 发送成功
- [ ] Developer 返回代码
- [ ] rate_agent 评分成功

### 3.3 测试场景：代码审查

**输入:**
```
"让 Reviewer 审查刚才的代码"
```

**预期流程:**
1. Meta Agent 调用 send_agent_message 给 Reviewer
2. Reviewer 返回审查结果

**验证点:**
- [ ] send_agent_message 发送成功
- [ ] Reviewer 返回审查意见

### 3.4 测试场景：部署

**输入:**
```
"让 DevOps 部署代码"
```

**预期流程:**
1. Meta Agent 调用 send_agent_message 给 DevOps
2. DevOps 返回部署结果

---

## 第四阶段：Tools 详细测试

### 4.1 System Agents Tools 测试

| # | 工具名称 | 测试方法 | 验证点 |
|---|---------|---------|--------|
| 1 | recommend_agents | `recommend_agents({"query": "python"})` | 返回推荐列表 |
| 2 | search_agents | `search_agents({"query": "developer"})` | 返回搜索结果 |
| 3 | rate_agent | `rate_agent({"agent_id": "dev_id", "rating": 5, "reviewer_id": "user1"})` | 评分成功 |
| 4 | get_recommendation_history | `get_recommendation_history({})` | 返回历史记录 |
| 5 | route_message | `route_message({"to": "agent1", "message_type": "text", "content": "hello"})` | 路由成功 |
| 6 | get_load_balance_status | `get_load_balance_status({})` | 返回负载状态 |
| 7 | get_route_info | `get_route_info({})` | 返回路由信息 |
| 8 | get_system_health | `get_system_health({})` | 返回系统健康 |
| 9 | get_system_metrics | `get_system_metrics({})` | 返回系统指标 |
| 10 | query_logs | `query_logs({})` | 返回日志 |

### 4.2 Precise Matching Tools 测试

| # | 工具名称 | 测试方法 | 验证点 |
|---|---------|---------|--------|
| 1 | get_agent_profile | `get_agent_profile({"agent_id": "Developer"})` | 返回档案 |
| 2 | get_all_agent_profiles | `get_all_agent_profiles({})` | 返回所有档案 |
| 3 | recommend_agents_for_demand | `recommend_agents_for_demand({"demand": "login"})` | 需求推荐 |
| 4 | match_by_gene_capsule | `match_by_gene_capsule({"gene_capsule": "..."})` | 基因匹配 |
| 5 | generate_recommendation_explanation | `generate_recommendation_explanation({"recommendation_id": "..."})` | 生成解释 |
| 6 | proactively_notify_opportunity | `proactively_notify_opportunity({"opportunity": "..."})` | 主动通知 |
| 7 | scan_opportunities | `scan_opportunities({})` | 扫描机会 |
| 8 | auto_match_and_notify | `auto_match_and_notify({})` | 自动匹配 |
| 9 | consult_agent | `consult_agent({"agent_id": "Developer", "question": "how to?"})` | 咨询代理 |
| 10 | interview_agent | `interview_agent({"agent_id": "Developer"})` | 面试代理 |
| 11 | send_agent_message | `send_agent_message({"agent_id": "Developer", "message": "hi"})` | 发送消息 |
| 12 | receive_agent_showcase | `receive_agent_showcase({"showcase_id": "..."})` | 接收展示 |

### 4.3 Governance Tools 测试

| # | 工具名称 | 测试方法 | 验证点 |
|---|---------|---------|--------|
| 1 | get_user_info | `get_user_info({"user_id": "user1"})` | 返回用户信息 |
| 2 | list_user_agents | `list_user_agents({})` | 返回用户Agent列表 |
| 3 | delegate_vote | `delegate_vote({"to": "0x..."})` | 委托投票成功 |
| 4 | get_vote_power | `get_vote_power({"address": "0x..."})` | 返回投票权 |
| 5 | list_proposals | `list_proposals({})` | 返回提案列表 |

### 4.4 Blockchain Tools 测试

| # | 工具名称 | 测试方法 | 验证点 |
|---|---------|---------|--------|
| 1 | create_wallet | `create_wallet({})` | 创建钱包 |
| 2 | get_balance | `get_balance({"address": "0x..."})` | 返回余额 |
| 3 | stake | `stake({"amount": 100})` | 质押成功 |
| 4 | unstake | `unstake({"amount": 50})` | 解除质押 |
| 5 | vote | `vote({"proposal_id": "1", "vote": "yes"})` | 投票成功 |
| 6 | submit_proposal | `submit_proposal({"title": "test", "description": "desc"})` | 提交成功 |
| 7 | switch_chain | `switch_chain({"chain": "ethereum"})` | 切换链 |
| 8 | get_chain_info | `get_chain_info({})` | 返回链信息 |

### 4.5 Platform Tools 测试

| # | 工具名称 | 测试方法 | 验证点 |
|---|---------|---------|--------|
| 1 | start_node | `start_node({})` | 启动节点 |
| 2 | stop_node | `stop_node({})` | 停止节点 |
| 3 | get_node_status | `get_node_status({})` | 返回状态 |
| 4 | get_config | `get_config({"key": "test"})` | 获取配置 |
| 5 | update_config | `update_config({"key": "test", "value": "v"})` | 更新配置 |
| 6 | bind_wallet | `bind_wallet({"wallet_address": "0x..."})` | 绑定钱包 |
| 7 | register_agent | `register_agent({"name": "TestAgent"})` | 注册Agent |
| 8 | unregister_agent | `unregister_agent({"agent_id": "..."})` | 注销Agent |
| 9 | general_response | `general_response({"input": "hello"})` | 返回响应 |

### 4.6 其他工具类别

| 类别 | 工具数 | 测试重点 |
|------|--------|---------|
| Monitor | 4 | health_check, metrics, alerts |
| IPFS | 3 | upload, download, sync |
| Database | 4 | CRUD 操作 |
| UI | 3 | generate_component, manage_page, call_api |
| Web | 4 | search, fetch, parse |
| Execution | 10+ | python, command, browser, jupyter |

---

## 第五阶段：业务场景测试

### 5.1 完整业务流程测试

**场景：开发一个用户管理系统**

1. **需求分析阶段**
   - Chat: "创建一个用户管理系统"
   - Tool: send_agent_message → ProductOwner
   - Tool: receive_agent_showcase → 接收需求分析
   - Tool: recommend_agents_for_demand → 推荐合适的 Agent

2. **架构设计阶段**
   - Tool: send_agent_message → Architect
   - Tool: get_agent_profile → 获取架构师档案
   - Tool: rate_agent → 评价架构设计

3. **开发阶段**
   - Tool: send_agent_message → Developer
   - Tool: search_agents → 搜索相关开发者
   - Tool: consult_agent → 咨询开发问题

4. **审查阶段**
   - Tool: send_agent_message → Reviewer
   - Tool: scan_opportunities → 扫描改进机会

5. **部署阶段**
   - Tool: send_agent_message → DevOps
   - Tool: get_system_health → 检查系统健康

### 5.2 异常处理测试

- [ ] 无效 agent_id 的处理
- [ ] 网络超时的处理
- [ ] 参数缺失的处理

---

## 第六阶段：结果验证

### 6.1 测试结果汇总表

| 类别 | 总数 | 通过 | 失败 | 通过率 |
|------|------|------|------|--------|
| System Agents | 10 | | | |
| Precise Matching | 12 | | | |
| Governance | 5 | | | |
| Blockchain | 8 | | | |
| Platform | 9 | | | |
| Monitor | 4 | | | |
| IPFS | 3 | | | |
| Database | 4 | | | |
| UI | 3 | | | |
| Web | 4 | | | |
| Execution | 10+ | | | |
| **总计** | **~85** | | | |

### 6.2 问题记录

| # | 问题描述 | 严重程度 | 状态 |
|---|---------|---------|------|
| 1 | | | |
| 2 | | | |

---

## 执行命令

```bash
# 1. 安装依赖
pip install -e usmsb-sdk/

# 2. 启动 Meta Agent API 服务
cd usmsb-sdk/src
python run_server.py

# 3. 启动 Software Dev Demo
cd usmsb-sdk/demo/software_dev
python run_demo.py

# 4. 通过 API 调用测试
# POST /api/chat
# {
#   "message": "帮我创建一个用户登录功能",
#   "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
# }
```
