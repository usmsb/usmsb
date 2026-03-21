# USMSB 完整任务追踪

## 状态说明
- [ ] = 未开始
- [W] = 进行中
- [D] = 完成待验收
- [X] = 已验收

---

## 第一部分：合约审计修复 (14项)

### Critical (7项)
- [D] C1: VIBEToken blacklist 无解锁机制 (代码中不存在blacklist功能)
- [D] C2: VIBStaking 重入攻击风险 (_unstake 先转账后更新状态) - CEI模式修复
- [D] C3: VIBVesting initialize() 可重复调用 (代码中非可升级合约，无initialize)
- [D] C4: VIBGovernance 提案通过后立即执行无时间锁 - 紧急提案时间锁设为48小时
- [D] C5: VIBIdentity SBT 转移保护有漏洞 - 添加合约地址检查
- [D] C6: AgentWallet 权限过大 (代码中不存在executeCall函数)
- [D] C7: 跨合约调用校验不足 - VIBDividend.notifyDividendReceived已修复

### High (7项)
- [D] H1: VIBEToken 税收分配数学未验证 - 构造函数中添加验证
- [D] H2: VIBStaking 提现顺序攻击 - 添加合约余额检查
- [D] H3: JointOrder 争议解决可被滥用 - 添加1%押金机制
- [D] H4: VIBDividend notifyDividendReceived 无上限 - 添加10%cap和caller限制
- [D] H5: AgentRegistry 注册信息可被修改 (代码中无update函数)
- [D] H6: VIBCollaboration 分成比例可被 owner 单方修改 (已是常量)
- [D] H7: EmissionController 增发无硬顶 - 添加MAX_EMISSION_TOTAL

---

## 第二部分：业务合约对接 (无数量限制，全面对接)

### P0 Critical
- [ ] B1: Agent 注册时自动创建 AgentWallet (register_agent_v2)
- [ ] B2: confirm_delivery 的 joint_order_pool_manager 传参修复
- [D] B3: 前端集成 viem/ethers.js 连接钱包

### P1 Core
- [ ] B4: JointOrder 完整 API (create/submit/accept/confirm/cancel pool)
- [ ] B5: 质押/解除质押 API (stake/unstake)
- [ ] B6: VIBEToken 转账 API (transfer/approve/allowance)
- [ ] B7: 治理 API (propose/vote/query)
- [ ] B8: 注册时调用 AgentRegistry 链上注册

### P2 Extended
- [ ] B9:  身份 SBT 铸造 API
- [ ] B10: 协作分成 API
- [D] B11: 前端质押界面
- [D] B12: 前端治理投票界面
- [D] B13: 前端交易历史
- [ ] B14: 绑定 owner 时真实调用 VIBStaking 质押
- [D] B15: 前端显示 VIBE 余额

### P3 体验优化
- [ ] B16: 交易状态通知 (pending → confirmed)
- [ ] B17: Gas 估算与显示
- [ ] B18: 争议处理 API (raise/resolve dispute)

---

## 验收标准
1. 合约代码通过编译 (npx hardhat compile)
2. Python SDK 单元测试通过
3. API 端点集成测试通过
4. 前端构建通过 (npm run build)
5. 所有改动 commit 到 feature/order-management 分支
