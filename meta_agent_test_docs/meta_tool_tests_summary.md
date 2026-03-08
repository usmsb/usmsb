# Meta Agent Tools 测试文档汇总

## 测试文档清单

| 文件 | 测试数量 | 包含测试 |
|------|---------|---------|
| `meta_agent_tool_tests.md` | 12 | #1-12 |
| `meta_tool_tests_2.md` | 12 | #13-24 |
| `meta_tool_tests_3.md` | 12 | #25-36 |
| `meta_tool_tests_4.md` | 20 | #37-52 |
| `meta_tool_tests_5.md` | 18 | #53-70 |

**总计: 70 个工具测试**

---

## 覆盖的工具列表

### Monitor 工具 (4个)
- [x] health_check (#1)
- [x] get_system_metrics (#2)
- [x] get_alerts (#49)
- [x] set_threshold (#68)

### System Agents 工具 (11个)
- [x] recommend_agents (#7)
- [x] search_agents (#3)
- [x] rate_agent (#6)
- [x] get_recommendation_history (#13)
- [x] route_message (#69)
- [x] get_load_balance_status (#14)
- [x] get_route_info (#60)
- [x] get_system_health (#59)
- [x] get_system_metrics (同Monitor)
- [x] query_logs (#15)

### Precise Matching 工具 (12个)
- [x] get_agent_profile (#5)
- [x] get_all_agent_profiles (#16)
- [x] recommend_agents_for_demand (#62)
- [x] match_by_gene_capsule (#70)
- [x] generate_recommendation_explanation (#64)
- [x] proactively_notify_opportunity (#65)
- [x] scan_opportunities (#18)
- [x] auto_match_and_notify (#63)
- [x] consult_agent (#17)
- [x] interview_agent (#61)
- [x] send_agent_message (#4)
- [x] receive_agent_showcase (#66)

### Blockchain 工具 (8个)
- [x] create_wallet (#8)
- [x] get_balance (#9)
- [x] stake (#19)
- [x] unstake (#36)
- [x] vote (#20)
- [x] submit_proposal (#21)
- [x] switch_chain (#35)
- [x] get_chain_info (#22)

### Governance 工具 (5个)
- [x] get_user_info (#25)
- [x] list_user_agents (#28)
- [x] delegate_vote (#26)
- [x] get_vote_power (#27)
- [x] list_proposals (#24)

### Platform 工具 (9个)
- [x] start_node (#50)
- [x] stop_node (#51)
- [x] get_node_status (#52)
- [x] get_config (#53)
- [x] update_config (#54)
- [x] bind_wallet (#55)
- [x] register_agent (#56)
- [x] unregister_agent (#57)
- [x] general_response (#58)

### IPFS 工具 (3个)
- [x] upload_to_ipfs (#10)
- [x] download_from_ipfs (#23)
- [x] sync_to_ipfs (#67)

### Database 工具 (4个)
- [x] query_db (#11)
- [x] insert_db (#29)
- [x] update_db (#30)
- [x] delete_db (#31)

### UI 工具 (3个)
- [x] generate_component (#12)
- [x] manage_page (#32)
- [x] call_api (见原测试文档)

### Web 工具 (5个)
- [x] search_web (#33)
- [x] fetch_url (#34)
- [x] parse_html
- [x] download_file (web)
- [x] get_headers

### Execution 工具 (部分)
- [x] execute_python (#37)
- [x] run_command (#38)
- [x] browser_open (#39)
- [x] browser_click (#40)
- [x] browser_fill (#41)
- [x] browser_get_content (#42)
- [x] browser_screenshot (#43)
- [x] browser_close (#44)
- [x] execute_javascript (#45)
- [x] start_jupyter (#46)
- [x] jupyter_status (#47)
- [x] stop_jupyter (#48)

---

## 测试方法总结

### 每个测试的验证步骤

1. **Step 1: 发送 Chat 请求**
   ```bash
   curl -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "...", "wallet_address": "0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"}'
   ```

2. **Step 2: 查看后台任务状态**
   ```bash
   curl "http://localhost:8000/api/meta-agent/history/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
   ```
   - 验证出现 `background_task` 角色（任务开始）
   - 验证出现 `background_complete` 角色（任务完成）

3. **Step 3: 查看工具调用日志**
   ```bash
   curl "http://localhost:8000/api/meta-agent/debug-logs/0x0931b04d001fEa59E1e18A6331b56C1B9Dd79777"
   ```
   - 验证出现 `[TOOL_CALL] 工具名`
   - 验证日志包含正确参数
   - 验证出现 `[TOOL_RESULT]`
   - 验证日志包含正确返回数据

4. **Step 4: 验证返回结果**
   - 验证 Chat API 返回成功
   - 验证 LLM 生成了自然语言回复

---

## 启动命令

```bash
# 1. 启动 Meta Agent 后端
cd usmsb-sdk
python run_server.py

# 2. 启动 Software Dev Demo (另一个终端)
cd usmsb-sdk/demo/software_dev
python run_demo.py

# 3. 执行测试
# 按照上述测试文档中的步骤执行
```

---

## 注意事项

1. 每个测试完成后需要等待几秒让后台任务完成
2. 可以同时查看控制台日志和 API 日志
3. 部分工具需要 Demo 中的 Agent 运行才能测试
4. VSCode 工具仅 Linux 可用
