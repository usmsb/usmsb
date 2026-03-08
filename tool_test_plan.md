# 工具测试详细计划表

## 工具总数: 92个

---

### 1. Execution 工具 (18个)

| # | 工具名称 | 测试命令/参数 | 预期结果 | 实际结果 | 状态 |
|---|---------|-------------|---------|---------|------|
| 1 | execute_python | code="print(1+1)" | 输出 2 | | |
| 2 | run_command | command="echo hello" | 输出 hello | | |
| 3 | browser_open | url="http://example.com" | 打开成功 | | |
| 4 | browser_click | selector="#btn" | 点击成功 | | |
| 5 | browser_fill | selector="#input", value="test" | 填写成功 | | |
| 6 | browser_get_content | - | 获取内容 | | |
| 7 | browser_screenshot | - | 截图成功 | | |
| 8 | browser_close | - | 关闭成功 | | |
| 9 | execute_javascript | code="console.log('test')" | 执行成功 | | |
| 10 | start_jupyter | port=8888 | 启动成功 | | |
| 11 | jupyter_status | port=8888 | 返回状态 | | |
| 12 | stop_jupyter | - | 停止成功 | | |
| 13 | start_vscode | - | (Linux only) | | |
| 14 | stop_vscode | - | (Linux only) | | |
| 15 | vscode_status | - | (Linux only) | | |
| 16 | parse_skill_md | file_path="/test/skills.md" | 解析成功 | | |
| 17 | execute_skill | skill_name="test_skill" | 执行成功 | | |
| 18 | list_skills | - | 列出技能 | | |

---

### 2. System 工具 (10个)

| # | 工具名称 | 测试命令/参数 | 预期结果 | 实际结果 | 状态 |
|---|---------|-------------|---------|---------|------|
| 19 | read_file | path="/test/file.txt" | 读取内容 | | |
| 20 | write_file | path="/test/file.txt", content="hello" | 写入成功 | | |
| 21 | list_directory | path="/test" | 列出文件 | | |
| 22 | create_directory | path="/test/newdir" | 创建成功 | | |
| 23 | delete_file | path="/test/file.txt" | 删除成功 | | |
| 24 | copy_file | source="/test/a.txt", dest="/test/b.txt" | 复制成功 | | |
| 25 | move_file | source="/test/a.txt", dest="/test/b.txt" | 移动成功 | | |
| 26 | get_file_info | path="/test/file.txt" | 文件信息 | | |
| 27 | search_files | path="/test", pattern="*.txt" | 搜索结果 | | |
| 28 | download_file | url="http://example.com/file.txt" | 下载成功 | | |

---

### 3. Web 工具 (5个)

| # | 工具名称 | 测试命令/参数 | 预期结果 | 实际结果 | 状态 |
|---|---------|-------------|---------|---------|------|
| 29 | search_web | query="python" | 搜索结果 | | |
| 30 | fetch_url | url="http://example.com" | 获取内容 | | |
| 31 | parse_html | html="<html></html>", selector="body" | 解析结果 | | |
| 32 | download_file | url="http://example.com/file.txt" | 下载成功 | | |
| 33 | get_headers | url="http://example.com" | 获取头信息 | | |

---

### 4. Platform 工具 (9个)

| # | 工具名称 | 测试命令/参数 | 预期结果 | 实际结果 | 状态 |
|---|---------|-------------|---------|---------|------|
| 34 | start_node | - | 启动节点 | | |
| 35 | stop_node | - | 停止节点 | | |
| 36 | get_node_status | - | 节点状态 | | |
| 37 | get_config | key="test" | 配置信息 | | |
| 38 | update_config | key="test", value="value" | 更新成功 | | |
| 39 | bind_wallet | wallet_address="0x123" | 绑定成功 | | |
| 40 | register_agent | name="test_agent" | 注册成功 | | |
| 41 | unregister_agent | agent_id="123" | 注销成功 | | |
| 42 | general_response | input="hello" | 响应结果 | | |

---

### 5. Monitor 工具 (4个)

| # | 工具名称 | 测试命令/参数 | 预期结果 | 实际结果 | 状态 |
|---|---------|-------------|---------|---------|------|
| 43 | health_check | - | healthy | | |
| 44 | get_metrics | - | 指标数据 | | |
| 45 | set_threshold | threshold=0.5 | 设置成功 | | |
| 46 | get_alerts | - | 告警列表 | | |

---

### 6. Blockchain 工具 (8个)

| # | 工具名称 | 测试命令/参数 | 预期结果 | 实际结果 | 状态 |
|---|---------|-------------|---------|---------|------|
| 47 | create_wallet | - | 创建钱包 | | |
| 48 | get_balance | address="0x123" | 余额信息 | | |
| 49 | stake | amount=100 | 质押成功 | | |
| 50 | unstake | amount=100 | 解除质押 | | |
| 51 | vote | proposal_id="1", vote="yes" | 投票成功 | | |
| 52 | submit_proposal | title="test", description="desc" | 提交成功 | | |
| 53 | switch_chain | chain="ethereum" | 切换成功 | | |
| 54 | get_chain_info | - | 链信息 | | |

---

### 7. IPFS 工具 (3个)

| # | 工具名称 | 测试命令/参数 | 预期结果 | 实际结果 | 状态 |
|---|---------|-------------|---------|---------|------|
| 55 | upload_to_ipfs | content="test content" | 上传成功 | | |
| 56 | download_from_ipfs | cid="QmTest" | 下载成功 | | |
| 57 | sync_to_ipfs | path="/test" | 同步成功 | | |

---

### 8. Database 工具 (4个)

| # | 工具名称 | 测试命令/参数 | 预期结果 | 实际结果 | 状态 |
|---|---------|-------------|---------|---------|------|
| 58 | query_db | query="SELECT * FROM test" | 查询结果 | | |
| 59 | insert_db | table="test", data={"key":"value"} | 插入成功 | | |
| 60 | update_db | table="test", data={"key":"value"}, where="id=1" | 更新成功 | | |
| 61 | delete_db | table="test", where="id=1" | 删除成功 | | |

---

### 9. UI 工具 (3个)

| # | 工具名称 | 测试命令/参数 | 预期结果 | 实际结果 | 状态 |
|---|---------|-------------|---------|---------|------|
| 62 | generate_component | component_name="Button" | 生成组件 | | |
| 63 | manage_page | action="refresh" | 操作成功 | | |
| 64 | call_api | endpoint="/test" | API调用 | | |

---

### 10. Governance 工具 (5个)

| # | 工具名称 | 测试命令/参数 | 预期结果 | 实际结果 | 状态 |
|---|---------|-------------|---------|---------|------|
| 65 | get_user_info | user_id="123" | 用户信息 | | |
| 66 | list_user_agents | - | 列出代理 | | |
| 67 | delegate_vote | to="0x123" | 委托成功 | | |
| 68 | get_vote_power | address="0x123" | 投票权 | | |
| 69 | list_proposals | - | 提案列表 | | |

---

### 11. System Agents 工具 (11个)

| # | 工具名称 | 测试命令/参数 | 预期结果 | 实际结果 | 状态 |
|---|---------|-------------|---------|---------|------|
| 70 | recommend_agents | query="test" | 推荐结果 | | |
| 71 | search_agents | query="test" | 搜索结果 | | |
| 72 | rate_agent | agent_id="123", rating=5 | 评分成功 | | |
| 73 | get_recommendation_history | - | 历史记录 | | |
| 74 | route_message | to="user123", message="hello" | 路由消息 | | |
| 75 | get_load_balance_status | - | 负载状态 | | |
| 76 | get_route_info | - | 路由信息 | | |
| 77 | get_system_health | - | 系统健康 | | |
| 78 | get_system_metrics | - | 系统指标 | | |
| 79 | query_logs | - | 查询日志 | | |
| 80 | get_alerts | - | 告警列表 | | |

---

### 12. Precise Matching 工具 (12个)

| # | 工具名称 | 测试命令/参数 | 预期结果 | 实际结果 | 状态 |
|---|---------|-------------|---------|---------|------|
| 81 | interview_agent | agent_id="123" | 面试代理 | | |
| 82 | send_agent_message | agent_id="123", message="hello" | 发送消息 | | |
| 83 | receive_agent_showcase | showcase_id="123" | 接收展示 | | |
| 84 | get_agent_profile | agent_id="123" | 代理档案 | | |
| 85 | get_all_agent_profiles | - | 所有档案 | | |
| 86 | recommend_agents_for_demand | demand="test" | 需求推荐 | | |
| 87 | match_by_gene_capsule | gene_capsule="test" | 基因匹配 | | |
| 88 | generate_recommendation_explanation | recommendation_id="123" | 生成解释 | | |
| 89 | proactively_notify_opportunity | opportunity="test" | 主动通知 | | |
| 90 | scan_opportunities | - | 扫描机会 | | |
| 91 | auto_match_and_notify | - | 自动匹配 | | |
| 92 | consult_agent | agent_id="123", question="test?" | 咨询代理 | | |

---

## 测试说明
- ✓ = 通过
- ✗ = 失败  
- (Linux only) = 仅 Linux 可用
- 空白 = 未测试
